"""
HTML Logger - A comprehensive Python logging module that creates beautiful HTML logs.

Features:
- HTML and text log generation with dark mode
- Interactive table of contents with timestamps
- Image embedding (PIL support)
- Rich library integration for advanced formatting
- Stream redirection for automatic capture
- Responsive design for various screen sizes
"""

from .core import LogTeeHTML
from .__version__ import __version__

__all__ = ['LogTeeHTML']
__author__ = "Your Name"
__email__ = "your.email@example.com"
