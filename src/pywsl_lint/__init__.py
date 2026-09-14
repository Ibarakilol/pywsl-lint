"""pywsl-lint — whitespace linter and formatter for Python."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pywsl-lint")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
