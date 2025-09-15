#!/usr/bin/env python3
"""
Setup script for logteehtml package.
"""

import os
from setuptools import setup, find_packages

# Read version
version_file = os.path.join(os.path.dirname(__file__), 'logteehtml', '__version__.py')
version_dict = {}
with open(version_file) as f:
    exec(f.read(), version_dict)

# Read README if it exists
long_description = "Comprehensive HTML logging with content support"
readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
if os.path.exists(readme_path):
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

setup(
    name="logteehtml",
    version="0.1.0",
    author="André Aichert",
    author_email="aaichert@gmail.com",
    description="A simple but powerful HTML logging module with stream redirection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aaichert/logteehtml",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "Pillow>=8.0.0",
        "rich>=10.0.0",
    ],
    extras_require={
        "dev": ["pytest>=6.0.0", "black", "flake8"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Logging",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="logging html pillow documentation",
    project_urls={
        "Bug Reports": "https://github.com/aaichert/logteehtml/issues",
        "Source": "https://github.com/aaichert/logteehtml",
        "Documentation": "https://github.com/aaichert/logteehtml#readme",
    },
)
