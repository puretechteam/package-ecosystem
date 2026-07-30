import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from flask import Flask, Response, jsonify, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="/static")

CACHE_DIR = Path(__file__).parent / "cache"
DATA_DIR = Path(__file__).parent / "data"
STATIC_DIR = Path(__file__).parent / "static"

PRODUCTION = os.environ.get("APP_ENV", "development") == "production"

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    CACHE_DIR = Path.home() / ".package-ecosystem" / "cache"
else:
    BASE_DIR = Path(__file__).parent
    CACHE_DIR = BASE_DIR / "cache"

DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

CACHE_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_SCHEMA_KEYS = {"name", "category", "description", "license", "downloads", "dependencies", "dependents_count", "maintainers", "registry"}

logging.basicConfig(
    level=logging.INFO if PRODUCTION else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(CACHE_DIR / "app.log")),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


def _make_request_with_retry(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
    max_retries: int = 3,
) -> requests.Response:
    """Make an HTTP GET request with exponential backoff retry logic.

    Args:
        url: The URL to request.
        headers: Optional headers to include in the request.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.

    Returns:
        The HTTP response object.

    Raises:
        requests.RequestException: If all retry attempts fail.
    """
    last_exception: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                wait_time = (2 ** attempt) * 0.5
                logger.warning("Rate limited (429) on %s, retrying in %.1fs (attempt %d/%d)", url, wait_time, attempt + 1, max_retries)
                last_exception = Exception("Rate limited: 429")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                raise last_exception
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exception = exc
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 0.5
                logger.warning("Request to %s failed (attempt %d/%d): %s, retrying in %.1fs", url, attempt + 1, max_retries, exc, wait_time)
                time.sleep(wait_time)
            else:
                logger.error("Request to %s failed after %d attempts: %s", url, max_retries, exc)
    raise last_exception  # type: ignore[misc]


@app.after_request
def add_cors_headers(response: Response) -> Response:
    """Add CORS headers to all responses.

    Args:
        response: The Flask response object to modify.

    Returns:
        The response with CORS headers added.
    """
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/")
def index() -> Response:
    """Serve the main index.html page.

    Returns:
        The index.html response.
    """
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/static/<path:path>")
def serve_static(path: str) -> Response:
    """Serve static files from the static directory.

    Args:
        path: The relative path to the static file.

    Returns:
        The static file response.
    """
    return send_from_directory(str(STATIC_DIR), path)


@app.route("/data/<path:filename>")
def serve_data(filename: str) -> Response:
    """Serve files from the data directory for bundled data fallback.

    Args:
        filename: The relative path to the data file.

    Returns:
        The data file response.
    """
    return send_from_directory(str(DATA_DIR), filename)


@app.route("/api/data")
def api_data() -> Response:
    """Return the bundled package data as JSON.

    Returns:
        JSON response with package data, or 500 on failure.
    """
    try:
        data = load_packages()
        return jsonify(data)
    except Exception:
        if PRODUCTION:
            return jsonify({}), 500
        return jsonify({"error": "Failed to load data"}), 500


@app.route("/api/registries")
def api_registries() -> Response:
    """Return a sorted list of available registries.

    Returns:
        JSON response with registry names, or 500 on failure.
    """
    try:
        data = load_packages()
        registries = sorted(
            set(
                pkg["registry"]
                for pkgs in data.values()
                for pkg in pkgs
            )
        )
        return jsonify(registries)
    except Exception:
        return jsonify([]), 500


@app.route("/api/stats")
def api_stats() -> Response:
    """Return aggregate statistics about the package data.

    Returns:
        JSON response with total packages, downloads, registries, and categories.
    """
    try:
        data = load_packages()
        total_packages = sum(len(pkgs) for pkgs in data.values())
        total_downloads = sum(
            pkg["downloads"]
            for pkgs in data.values()
            for pkg in pkgs
        )
        registries = sorted(
            set(
                pkg["registry"]
                for pkgs in data.values()
                for pkg in pkgs
            )
        )
        categories = sorted(
            set(
                pkg["category"]
                for pkgs in data.values()
                for pkg in pkgs
            )
        )
        return jsonify(
            {
                "total_packages": total_packages,
                "total_downloads": total_downloads,
                "registries": registries,
                "categories": categories,
            }
        )
    except Exception:
        return jsonify({}), 500


@app.route("/api/fetch/npm/<path:package>")
def fetch_npm(package: str) -> Response:
    """Fetch package metadata from the npm registry with caching and retry.

    Args:
        package: The npm package name.

    Returns:
        JSON response with package metadata, or 404 if not found.
    """
    cache_key = f"npm_{package}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        url = f"https://registry.npmjs.org/{package}"
        resp = _make_request_with_retry(
            url,
            headers={"User-Agent": "PackageEcosystemVisualizer"},
        )
        npm_data = resp.json()
        result = {
            "name": npm_data.get("name", package),
            "registry": "npm",
            "version": npm_data.get("dist-tags", {}).get("latest", "unknown"),
            "description": npm_data.get("description", ""),
            "license": _extract_npm_license(npm_data),
            "downloads": npm_data.get("downloads", {}).get("last-week", 0),
            "homepage": npm_data.get("homepage", ""),
            "repository": _extract_npm_repo(npm_data),
        }
        set_cached_response(cache_key, result)
        return jsonify(result)
    except Exception:
        cached = get_cached_response(cache_key)
        if cached is not None:
            return jsonify(cached)
        return jsonify({"error": "Package not found and no cached data available"}), 404


@app.route("/api/fetch/pypi/<path:package>")
def fetch_pypi(package: str) -> Response:
    """Fetch package metadata from PyPI with caching and retry.

    Args:
        package: The PyPI package name.

    Returns:
        JSON response with package metadata, or 404 if not found.
    """
    cache_key = f"pypi_{package}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        url = f"https://pypi.org/pypi/{package}/json"
        resp = _make_request_with_retry(
            url,
            headers={"User-Agent": "PackageEcosystemVisualizer"},
        )
        pypi_data = resp.json()
        info = pypi_data.get("info", {})
        result = {
            "name": info.get("name", package),
            "registry": "pypi",
            "version": info.get("version", "unknown"),
            "description": info.get("summary", ""),
            "license": info.get("license", ""),
            "downloads": pypi_data.get("urls", [{}])[0].get("downloads", 0) if pypi_data.get("urls") else 0,
            "homepage": info.get("home_page", ""),
            "repository": _extract_pypi_repo(info),
        }
        set_cached_response(cache_key, result)
        return jsonify(result)
    except Exception:
        cached = get_cached_response(cache_key)
        if cached is not None:
            return jsonify(cached)
        return jsonify({"error": "Package not found and no cached data available"}), 404


@app.route("/api/fetch/crates/<path:package>")
def fetch_crates(package: str) -> Response:
    """Fetch package metadata from crates.io with caching and retry.

    Args:
        package: The crates.io package name.

    Returns:
        JSON response with package metadata, or 404 if not found.
    """
    cache_key = f"crates_{package}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        url = f"https://crates.io/api/v1/crates/{package}"
        resp = _make_request_with_retry(
            url,
            headers={"User-Agent": "PackageEcosystemVisualizer"},
        )
        crates_data = resp.json()
        crate = crates_data.get("crate", {})
        result = {
            "name": crate.get("name", package),
            "registry": "crates",
            "version": crate.get("newest_version", "unknown"),
            "description": crate.get("description", ""),
            "license": crate.get("license", ""),
            "downloads": crate.get("downloads", 0),
            "homepage": crate.get("homepage", ""),
            "repository": crate.get("repository", ""),
        }
        set_cached_response(cache_key, result)
        return jsonify(result)
    except Exception:
        cached = get_cached_response(cache_key)
        if cached is not None:
            return jsonify(cached)
        return jsonify({"error": "Package not found and no cached data available"}), 404


def load_packages() -> dict[str, list[dict[str, Any]]]:
    """Load and validate package data from the bundled JSON file.

    Returns:
        A dictionary mapping registry names to lists of package dicts.
    """
    data_path = DATA_DIR / "packages.json"
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Failed to load packages: %s", e)
        return {}

    for registry_name, packages in data.items():
        if not isinstance(packages, list):
            data[registry_name] = []
            continue
        valid = []
        for pkg in packages:
            if validate_package_schema(pkg):
                valid.append(pkg)
        data[registry_name] = valid

    return data


def compute_checksum(filepath: str | Path) -> str:
    """Compute the SHA-256 checksum of a file.

    Args:
        filepath: Path to the file to checksum.

    Returns:
        The hex-encoded SHA-256 digest.
    """
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_checksums() -> dict[str, str]:
    """Load the checksums manifest from disk.

    Returns:
        A dictionary mapping filenames to their expected SHA-256 checksums.
    """
    checksum_file = DATA_DIR / "checksums.json"
    if checksum_file.exists():
        with open(checksum_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def verify_data_integrity() -> tuple[bool, str]:
    """Verify the integrity of the bundled data file against its checksum.

    Returns:
        A tuple of (is_valid, message).
    """
    checksums = load_checksums()
    data_path = DATA_DIR / "packages.json"
    if not data_path.exists():
        return False, "packages.json not found"
    actual = compute_checksum(data_path)
    expected = checksums.get("packages.json")
    if expected and actual != expected:
        return False, f"packages.json checksum mismatch (expected {expected[:12]}..., got {actual[:12]}...)"
    return True, "OK"


def validate_package_schema(pkg: Any) -> bool:
    """Validate that a package dict conforms to the required schema.

    Args:
        pkg: The package data to validate.

    Returns:
        True if the package is valid, False otherwise.
    """
    if not isinstance(pkg, dict):
        return False
    missing = REQUIRED_SCHEMA_KEYS - set(pkg.keys())
    if missing:
        return False
    if not isinstance(pkg.get("dependencies"), list):
        return False
    if not isinstance(pkg.get("maintainers"), list):
        return False
    if not isinstance(pkg.get("downloads"), (int, float)):
        return False
    return True


def get_cached_response(cache_key: str) -> dict[str, Any] | None:
    """Retrieve a cached API response from disk.

    Args:
        cache_key: The cache key identifying the response.

    Returns:
        The cached data dict, or None if not found or invalid.
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def set_cached_response(cache_key: str, data: dict[str, Any]) -> None:
    """Persist an API response to the cache directory.

    Args:
        cache_key: The cache key to store under.
        data: The response data to cache.
    """
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def _extract_npm_license(npm_data: dict[str, Any]) -> str:
    """Extract the license string from npm registry metadata.

    Args:
        npm_data: The raw npm registry response.

    Returns:
        The license identifier string.
    """
    license_field = npm_data.get("license")
    if isinstance(license_field, dict):
        return license_field.get("type", "")
    if isinstance(license_field, str):
        return license_field
    return ""


def _extract_npm_repo(npm_data: dict[str, Any]) -> str:
    """Extract the repository URL from npm registry metadata.

    Args:
        npm_data: The raw npm registry response.

    Returns:
        The repository URL string.
    """
    repo = npm_data.get("repository")
    if isinstance(repo, dict):
        return repo.get("url", "")
    if isinstance(repo, str):
        return repo
    return ""


def _extract_pypi_repo(info: dict[str, Any]) -> str:
    """Extract the repository URL from PyPI package metadata.

    Args:
        info: The PyPI info dict.

    Returns:
        The repository URL string.
    """
    project_urls = info.get("project_urls", {})
    if isinstance(project_urls, dict):
        for key, url in project_urls.items():
            if "github" in key.lower() or "repository" in key.lower():
                return url
    return info.get("home_page", "")


@app.errorhandler(404)
def not_found(e: Exception) -> Response:
    """Handle 404 errors with a JSON response.

    Args:
        e: The exception that triggered the error handler.

    Returns:
        A JSON 404 response.
    """
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e: Exception) -> Response:
    """Handle 500 errors with a JSON response.

    Args:
        e: The exception that triggered the error handler.

    Returns:
        A JSON 500 response.
    """
    if PRODUCTION:
        return jsonify({"error": "Internal server error"}), 500
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    integrity_ok, integrity_msg = verify_data_integrity()
    if not integrity_ok:
        logger.warning("Data integrity check failed: %s", integrity_msg)
    else:
        logger.info("Data integrity check passed.")
    app.run(host="0.0.0.0", port=5000, debug=not PRODUCTION)