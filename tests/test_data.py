import os
from pathlib import Path

import pytest
from app import (
    compute_checksum,
    load_checksums,
    load_packages,
    verify_data_integrity,
    validate_package_schema,
)

DATA_DIR = Path(__file__).parent.parent / "data"


def test_load_packages():
    data = load_packages()
    assert isinstance(data, dict)
    assert len(data) > 0


def test_validate_package_schema_valid():
    valid_pkg = {
        "name": "test-package",
        "category": "framework",
        "description": "A test package",
        "license": "MIT",
        "downloads": 1000,
        "dependencies": [],
        "dependents_count": 0,
        "maintainers": ["test@example.com"],
        "registry": "npm",
    }
    assert validate_package_schema(valid_pkg) is True


def test_validate_package_schema_invalid_missing_keys():
    invalid_pkg = {
        "name": "test-package",
        "category": "framework",
    }
    assert validate_package_schema(invalid_pkg) is False


def test_validate_package_schema_invalid_not_dict():
    assert validate_package_schema("not a dict") is False


def test_validate_package_schema_invalid_dependencies_not_list():
    pkg = {
        "name": "test-package",
        "category": "framework",
        "description": "A test package",
        "license": "MIT",
        "downloads": 1000,
        "dependencies": "not a list",
        "dependents_count": 0,
        "maintainers": ["test@example.com"],
        "registry": "npm",
    }
    assert validate_package_schema(pkg) is False


def test_load_checksums():
    checksums = load_checksums()
    assert isinstance(checksums, dict)
    assert "packages.json" in checksums


def test_compute_checksum():
    data_path = DATA_DIR / "packages.json"
    assert data_path.exists()
    checksum = compute_checksum(data_path)
    assert isinstance(checksum, str)
    assert len(checksum) == 64


def test_verify_data_integrity():
    is_valid, message = verify_data_integrity()
    assert is_valid is True
    assert message == "OK"


def test_sha256_files_in_data_dir():
    sha256_files = list(DATA_DIR.glob("*.sha256"))
    assert isinstance(sha256_files, list)