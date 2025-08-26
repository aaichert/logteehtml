# LogTeeHTML

A comprehensive Python logging package that creates beautiful HTML logs with rich content support.

## Overview

LogTeeHTML automatically captures your program's output and creates interactive HTML logs with a professional dark theme, making it easy to review and share your results.

## Features

- 📊 **Multiple output formats** - HTML, JSON, and TXT files
- 🎨 **Dark theme** with responsive design  
- 🔗 **Interactive navigation** - Fixed sidebar with clickable table of contents
- ⏰ **Timestamp tooltips** - Hover to see exact timing
- 📷 **Image embedding** - Embed PIL images directly
- 🌈 **Rich integration** - Tables, progress bars, syntax highlighting
- 📱 **Stream capture** - Automatically logs `print()` and errors

## Quick Start

```python
from logteehtml import LogTeeHTML

# Create logger
logger = LogTeeHTML("my_experiment")

# Start a stage
logger.start("Data Processing")
print("Loading data...")  # Automatically captured

# Add custom content
logger.inject_html("<h3>Results Summary</h3>", "Summary")

# Add images
from PIL import Image
img = Image.new('RGB', (100, 100), 'blue')
logger.inject_image(img, "Test Plot")
```

This generates:
- `my_experiment.html` - Interactive log with dark theme
- `my_experiment.json` - Structured data
- `my_experiment.txt` - Plain text version

## Installation

```bash
pip install logteehtml
```

**Dependencies:**
- Pillow (required)
- Rich (optional, for advanced formatting)

## Documentation

See `REQUIREMENTS.md` for detailed technical specifications.

---

**Note:** This project was created entirely by VS Code's AI Agent (GitHub Copilot) as a test case for AI-driven software development.
