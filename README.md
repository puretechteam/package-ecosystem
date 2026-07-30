# Package Ecosystem Visualizer

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey)](https://flask.palletsprojects.com/)

A web-based interactive visualization tool for exploring dependency graphs across multiple package registries (npm, PyPI, crates.io). Built with Flask, D3.js, and Python.

## Contents

- [Features](#features)
- [Setup](#setup)
- [Data Sources](#data-sources)
- [Usage Notes](#usage-notes)
- [Configuration](#configuration)
- [Version](#version)
- [Contributing](#contributing)
- [License](#license)
- [Security](#security)

## Development

### Prerequisites

- Python 3.12+
- pip

### Setup

1. Install dependencies:
   ```
   make install
   ```
   Or manually:
   ```
   pip install -r requirements.txt
   ```

### Running the App

```
make run
```

### Building the Executable

```
make build
```

### Running Tests

```
make test
```

### Linting

```
make lint
```

### Formatting

```
make format
```

### Docker

```
make docker-run
```
Or:
```
docker-compose up
```

> **Note:** The Makefile is the preferred build tool and provides cross-platform support for all development workflows.

## Testing

### Running Tests

Run the full test suite with:

```
make test
```

Or run pytest directly:

```
pytest
```

### Test Structure

Tests are located in the `tests/` directory and are organized as follows:

- `tests/test_app.py` — Tests for the Flask application routes and app creation
- `tests/test_data.py` — Tests for data loading, schema validation, and checksum verification

### Test Dependencies

Development dependencies for testing are listed in `requirements-dev.txt` and include `pytest` and `pytest-cov`. Install them with:

```
make install-dev
```

- Force-directed graph visualization of package dependencies
- Filter by registry, category, popularity, and search
- Dark theme with consistent CSS custom properties
- Live data fetching from public APIs with cached fallback
- Data integrity verification on startup
- Self-sustaining data pipeline with graceful degradation
- Interactive node selection with detail panel showing name, version, registry, category, and description
- Clicking a node highlights its connections and dims unrelated nodes

## Setup

### Development Server

1. Install dependencies:
   ```
   make install
   ```

2. Run the Flask development server:
   ```
   make run
   ```

3. Open http://localhost:5000 in your browser.

### Development Dependencies

For development and testing, install:
```
make install-dev
```

### PyInstaller Build

1. Ensure dependencies are installed (see above).

2. Run the build:
   ```
   make build
   ```

   The output executable will be placed in `dist/package-ecosystem-<VERSION>/`.

## Docker

### Building the Image

```
docker build -t package-ecosystem .
```

### Running the Container

```
docker run -p 5000:5000 package-ecosystem
```

### Using Docker Compose

```
docker-compose up -d
```

This starts the Flask app in development mode with source code mounted for live reloading.

## Data Sources

- **Bundled data**: `data/packages.json` — static package data bundled with the application
- **npm registry**: https://registry.npmjs.org/ (proxied via `/api/fetch/npm/<package>`)
- **PyPI**: https://pypi.org/pypi/ (proxied via `/api/fetch/pypi/<package>`)
- **crates.io**: https://crates.io/api/v1/crates/ (proxied via `/api/fetch/crates/<package>`)

Fetched data is cached in the `cache/` directory. If a live fetch fails, the application falls back to bundled static data and displays a "Data may be stale" indicator.

## Usage Notes

- **Search**: Type a package name in the search bar to filter the graph.
- **Registry filter**: Select a specific registry (npm, PyPI, crates.io) or view all.
- **Category filter**: Filter by category (framework, library, tool, utility).
- **Popularity slider**: Filter packages by minimum download count.
- **Zoom controls**: Use the +, -, and reset buttons in the bottom-right corner of the graph.
- **Node selection**: Click a node to view its details in the right panel. The panel displays name, version, registry, category, license, downloads, dependents, maintainers, description, and dependencies. Connected nodes are highlighted and unrelated nodes are dimmed.
- **Stale data**: If live data is unavailable, cached data is shown with a warning indicator.

## Project Structure

```
package-ecosystem/
├── app.py                  # Flask backend with graph visualization
├── build.bat               # PyInstaller build script
├── dependencies.bat        # Dependency installer
├── requirements.txt        # Runtime dependencies
├── requirements-build.txt  # Build-time dependencies (PyInstaller)
├── requirements-dev.txt    # Development dependencies
├── VERSION                 # Version number
├── .gitignore              # Git ignore rules
├── README.md               # This file
├── data/
│   ├── packages.json       # Bundled package data
│   └── checksums.json      # Integrity checksums
├── cache/                  # Runtime cache for fetched data
└── static/
    ├── index.html          # Main HTML page
    ├── css/
    │   └── style.css       # Stylesheet (dark theme)
    └── js/
        ├── graph.js        # D3.js force-directed graph logic
        ├── detail.js       # Detail panel logic
        └── filters.js      # Search and filter logic
```

## Roadmap

- Add vulnerability scanning for dependencies
- Support for private registry integration
- Dependency update notifications
- Bundle size analysis and optimization suggestions
- Multi-platform compatibility matrix view

## Configuration

Set `APP_ENV=production` to run in production mode (disables debug mode and hides internal error details).

## Version

See the `VERSION` file for the current version number.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Security

If you discover a security vulnerability, please report it responsibly. See [SECURITY.md](SECURITY.md) for our security policy and reporting instructions.