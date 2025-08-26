# Requirements: LogTeeHTML Package (`LoggerHTML`)

## Core Functionality

- Provide a `LoggerHTML` class to handle logging to:
  - Text file (`<basename>.txt`)
  - JSON file (`<basename>.json`) — complete serialization of the logger object
  - HTML file (`<basename>.html`)
- Accept a user-defined name for the log; this becomes the basename for all outputs.
- Accept an optional prefix=None for the basename which is per default using the current datetime YYYMMDD_HHMM
- Allow optional user override of `logfile_prefix`
    (default: absolute path of log creation. Example: "./" to just show relative path of logfile.)
- Maintain an efficient internal dictionary representation:
  ```python
  [
    stage:{
        timestamp: {
        "stream": "stdout" | "stderr" | "html" | "anchor",
        "data": "<string|html|anchor_name>"
        }
    }
  }
  ```
- Every new stage should start with an anchor. The default stage is the basename, unless specified differently during construction.
- The internal dictionary representation should only be changed by the member functions:
    * start(stage_name) which adds a new stage and adds an achor to it based on the stage name
    * print(data, stderr=False) which means by default it assumes stdout
    * inject_html(html_content, anchor_text) which also automatically adds a new anchor to the current stage.
    * inject_image(pil_image, anchor_text) which converts PIL images to base64 and embeds them inline.
- HTML export should use `<h1>` for stages, `<h2>` for anchors and create a fixed dark-themed sidepanel with a TOC that allows jumping to all anchors. The HTML should feature:
    * Professional dark mode styling with responsive design
    * Timestamp tooltips on hover for stages and content blocks
    * ANSI color code preservation in HTML output
    * Rich library integration support (tables, progress bars, panels)
    * Text content grouping for better readability

## Streams & Data Handling

- Redirect and capture both `stdout` and `stderr` into a single log:
  - Write entries on flush and newlines using print(...)
- Correctly handle:
  - ANSI escape/control sequences (converted to HTML styling)
    * Preserve terminal colors in HTML output
    * Skip ANSI processing for content already containing HTML tags
  - Output from the `rich` library — full support for Rich HTML exports
    * Tables, progress bars, panels, syntax highlighting
    * Automatic detection and preservation of Rich-generated HTML
- Ensure a single coherent log (no duplicate or separate streams).

## Persistence & Sync

- Keep `.txt` log and console output always up-to-date.
- Update `.json` and `.html`:
  - Every few seconds (configurable)
  - On program exit or crash
  - On logger deletion/removal

## Chapters & Anchors

- `logger.start("Stage Name")` starts a new chapter:
  - Creates a slugified anchor ID (append short UID on conflicts).
  - Anchor is visible in `.txt` log and linked in `.html`.
  - HTML export includes a fixed dark-themed side-panel with timestamp tooltips for navigation.
  - Console and `.txt` log include clickable file:// links referencing the `.html#anchor`

## HTML Injection

- `inject_html(html_content, anchor_text)`:
  - In console and `.txt` → shows clickable file:// link + anchor placeholder.
  - In `.html` → inserts raw HTML block at correct position with navigation anchor.
- `inject_image(pil_image, anchor_text)`:
  - Convert PIL images → Base64 → embed inline in HTML with proper anchor.
  - Console and `.txt` show file:// link to the HTML anchor.
- (Future extensions: inject tables, 3D visualizations, etc.)

## Performance

- Efficient internal representation using a dict keyed by timestamp.
- Text content grouping to reduce HTML bloat and improve readability.
- Lightweight and minimal file writes (batch updates rather than per-character).
- Smart HTML detection to avoid double-processing Rich library outputs.

## Technical Requirements

- ANSI escape sequence handling with HTML conversion.
- Stream redirection and automatic capture setup/cleanup.
- Graceful error handling and recovery.
- Support for responsive design (mobile-friendly HTML output).
- Package installation as `logteehtml` with Pillow dependency.