import os
import sys
import json
import hashlib
from pathlib import Path
from flask import Flask, jsonify, send_from_directory

import requests

app = Flask(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
DATA_DIR = Path(__file__).parent / "data"
STATIC_DIR = Path(__file__).parent / "static"

PRODUCTION = os.environ.get("FLASK_ENV", "development") == "production"

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


def get_data_path():
    return BASE_DIR


def compute_checksum(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_checksums():
    checksum_file = DATA_DIR / "checksums.json"
    if checksum_file.exists():
        with open(checksum_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def verify_data_integrity():
    checksums = load_checksums()
    data_path = DATA_DIR / "packages.json"
    if not data_path.exists():
        return False, "packages.json not found"
    actual = compute_checksum(data_path)
    expected = checksums.get("packages.json")
    if expected and actual != expected:
        return False, f"packages.json checksum mismatch (expected {expected[:12]}..., got {actual[:12]}...)"
    return True, "OK"


def validate_package_schema(pkg):
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


def load_packages():
    data_path = DATA_DIR / "packages.json"
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        if PRODUCTION:
            return {}
        raise

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


def get_cached_response(cache_key):
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    return None


def set_cached_response(cache_key, data):
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except IOError:
        pass


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(str(STATIC_DIR), path)


@app.route("/api/data")
def api_data():
    try:
        data = load_packages()
        return jsonify(data)
    except Exception:
        if PRODUCTION:
            return jsonify({}), 500
        return jsonify({"error": "Failed to load data"}), 500


@app.route("/api/registries")
def api_registries():
    try:
        data = load_packages()
        registries = sorted(set(
            pkg["registry"]
            for pkgs in data.values()
            for pkg in pkgs
        ))
        return jsonify(registries)
    except Exception:
        return jsonify([]), 500


@app.route("/api/stats")
def api_stats():
    try:
        data = load_packages()
        total_packages = sum(len(pkgs) for pkgs in data.values())
        total_downloads = sum(
            pkg["downloads"]
            for pkgs in data.values()
            for pkg in pkgs
        )
        registries = sorted(set(
            pkg["registry"]
            for pkgs in data.values()
            for pkg in pkgs
        ))
        categories = sorted(set(
            pkg["category"]
            for pkgs in data.values()
            for pkg in pkgs
        ))
        return jsonify({
            "total_packages": total_packages,
            "total_downloads": total_downloads,
            "registries": registries,
            "categories": categories,
        })
    except Exception:
        return jsonify({}), 500


@app.route("/api/fetch/npm/<path:package>")
def fetch_npm(package):
    cache_key = f"npm_{package}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        url = f"https://registry.npmjs.org/{package}"
        resp = requests.get(url, headers={"User-Agent": "PackageEcosystemVisualizer"}, timeout=10)
        resp.raise_for_status()
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
def fetch_pypi(package):
    cache_key = f"pypi_{package}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        url = f"https://pypi.org/pypi/{package}/json"
        resp = requests.get(url, headers={"User-Agent": "PackageEcosystemVisualizer"}, timeout=10)
        resp.raise_for_status()
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
def fetch_crates(package):
    cache_key = f"crates_{package}"
    cached = get_cached_response(cache_key)
    if cached is not None:
        return jsonify(cached)

    try:
        url = f"https://crates.io/api/v1/crates/{package}"
        resp = requests.get(url, headers={"User-Agent": "PackageEcosystemVisualizer"}, timeout=10)
        resp.raise_for_status()
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


def _extract_npm_license(npm_data):
    license_field = npm_data.get("license")
    if isinstance(license_field, dict):
        return license_field.get("type", "")
    if isinstance(license_field, str):
        return license_field
    return ""


def _extract_npm_repo(npm_data):
    repo = npm_data.get("repository")
    if isinstance(repo, dict):
        return repo.get("url", "")
    if isinstance(repo, str):
        return repo
    return ""


def _extract_pypi_repo(info):
    project_urls = info.get("project_urls", {})
    if isinstance(project_urls, dict):
        for key, url in project_urls.items():
            if "github" in key.lower() or "repository" in key.lower():
                return url
    return info.get("home_page", "")


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    if PRODUCTION:
        return jsonify({"error": "Internal server error"}), 500
    return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    integrity_ok, integrity_msg = verify_data_integrity()
    if not integrity_ok:
        print(f"WARNING: Data integrity check failed: {integrity_msg}")
    else:
        print("Data integrity check passed.")
    app.run(host="0.0.0.0", port=5000, debug=not PRODUCTION)