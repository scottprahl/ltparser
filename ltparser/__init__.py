"""Simple parser for converting LTspice `.asc` files to netlists."""

__version__ = "0.1.0"
__author__ = "Scott Prahl"
__email__ = "scott.prahl@oit.edu"
__copyright__ = "2022-25, Scott Prahl"
__license__ = "MIT"
__url__ = "https://github.com/scottprahl/ltparser"


class LTspiceFileError(ValueError):
    """Raised when file is not a valid LTspice file."""


from .ltparser import *  # noqa: F403, pylint: disable=wrong-import-position

__all__ = ["LTspiceFileError"]
