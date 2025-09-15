# LogTeeHTML

This package provides `LogTeeHTML`, a context-managed HTML logger that keeps the on-disk file valid by seeking and rewriting a small footer region on each append.

Quick usage:

```python
from logteehtml.core import LogTeeHTML

with LogTeeHTML('mylog') as logger:
    logger.start('Training')
    logger.print('Progress 1')
    logger.anchor('Epoch 1')
    logger.inject_json({'a':1}, 'metadata')
```

Notes:
- Version 1 uses a seek-and-rewrite-footer strategy so the file on disk is always a valid HTML document and the TOC/JS can run while logging.
- The implementation uses simple ANSI->HTML mapping and basic carriage-return handling. For higher fidelity colors use a dedicated converter.

Tests:
- A basic test is included under `tests/test_logteehtml_basic.py` (creates a temporary file). Run tests with `pytest`.
