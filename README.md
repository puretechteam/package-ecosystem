# Package Ecosystem Visualizer

A web-based interactive visualization tool for exploring dependency graphs across multiple package registries (npm, PyPI, crates.io). Built with Flask, D3.js, and Python.

## Features

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
   pip install -r requirements.txt
   ```

2. Run the Flask development server:
   ```
   python app.py
   ```

3. Open http://localhost:5000 in your browser.

### PyInstaller Build

1. Ensure dependencies are installed (see above).

2. Run the build script:
   ```
   build.bat
   ```

   The output executable will be placed in `dist/package-ecosystem-<VERSION>/`.

3. The `cache/` directory is included in the bundle for runtime data caching.

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

## Configuration

Set `FLASK_ENV=production` to run in production mode (disables debug mode and hides internal error details).

## Version

See the `VERSION` file for the current version number.