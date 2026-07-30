# Contributing

## How to Contribute

We welcome contributions from the community. Here are some ways you can help:

- Report bugs or feature requests by opening an issue
- Submit pull requests with bug fixes or new features
- Improve documentation
- Share feedback on the project

## Development Setup

1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```
   git clone https://github.com/<your-username>/package-ecosystem.git
   ```
3. Navigate to the project directory:
   ```
   cd package-ecosystem
   ```
4. Create a virtual environment:
   ```
   python -m venv venv
   ```
5. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
6. Install dependencies:
   ```
   pip install -r requirements.txt
   pip install -e ".[dev]"
   ```
7. Run the development server:
   ```
   python app.py
   ```

## Submitting Changes

1. Create a new branch for your feature or bug fix:
   ```
   git checkout -b my-feature
   ```
2. Make your changes and commit them with a clear, descriptive commit message.
3. Push your branch to your fork:
   ```
   git push origin my-feature
   ```
4. Open a pull request against the `main` branch of the repository.
5. Ensure all checks pass and your PR is approved by a maintainer.

## Code Style Guidelines

- Follow PEP 8 for Python code.
- Use 4 spaces for indentation (no tabs).
- Use `black` for code formatting.
- Use `flake8` or `ruff` for linting.
- Write docstrings for all public functions and classes.
- Keep line length to 88 characters or fewer.
- Use meaningful variable and function names.
- Add comments where the logic is not immediately obvious.