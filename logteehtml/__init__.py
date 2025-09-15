"""
LogTeeHTML - A logging utility that captures terminal output while preserving appearance and creating structured HTML logs.

Features:
- HTML and text log generation with dark mode
- Interactive table of contents with timestamps
- Image embedding (PIL support)
- Stream redirection for automatic capture
- Rich library integration
- ANSI color code preservation
"""

from .logteehtml import LogTeeHTML

__version__ = "0.1.0"
__all__ = ['LogTeeHTML']
