.PHONY: install install-dev run build test lint format clean all

PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)
PIP := $(shell command -v pip3 2>/dev/null || command -v pip 2>/dev/null)
VENV_PYTHON := .venv/bin/python
VENV_PIP := .venv/bin/pip
VERSION := $(strip $(shell cat VERSION))

install:
	@test -d .venv || $(PYTHON) -m venv .venv
	$(VENV_PIP) install -r requirements.txt

install-dev: install
	$(VENV_PIP) install pytest flake8 black ruff

run:
	$(VENV_PYTHON) app.py

build:
	$(VENV_PYTHON) -m PyInstaller --noconfirm \
		--name "package-ecosystem-$(VERSION)" \
		--add-data "data:data" \
		--add-data "static:static" \
		--add-data "cache:cache" \
		--distpath=dist \
		--workpath=build \
		app.py

test:
	$(VENV_PYTHON) -m pytest

lint:
	$(VENV_PYTHON) -m ruff check . 2>/dev/null || $(VENV_PYTHON) -m flake8 .

format:
	$(VENV_PYTHON) -m black .

clean:
	rm -rf __pycache__ build/ dist/ .venv/ cache/

all: install lint test build