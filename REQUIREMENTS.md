# LogTeeHTML Requirements

## Core Features

- `LogTeeHTML` class logs to a HTML file, leaving terminal output **identical**. 
- Do not keep data in memory. Write to file immediately. In case of HTML this means all the closing tags have to be kept track of and re-written every time.
- Log file:
  - User-defined name; no output directory creation. optional `suffix=None`.  
  - Default suffix: current datetime `_YYYYMMDD_HHMM`.  
  - Class has a `self.print(...)` function which adds to the HTML log - this should be the only function to write to the HTML.
  - Use a template file which contains a string `INSERT_LOG` where all the HTML snippets should be inserted by `self.print`.
    - \write the full HTML document (header + TOC JS + placeholder + footer) at creation. On every append, perform a small seek-and-rewrite of the footer region so the file on disk remains a valid, closed HTML document. This keeps the TOC/JS usable while preserving the desired "merge consecutive writes" behavior.
    - Rationale: this approach preserves merge/overwrite semantics and lets the file be inspected in a browser while logging is active. It requires rewriting only a small footer region on each append (cheap) rather than holding the whole log in memory or leaving tags unclosed.
  - Includes CSS: Monospace font, dark theme.
  - Javascript at the top to create a two-level table of contents with Sections (`<h1>`) and named anchors (`<h2>`) based on the DOM on pageload. Make sure that the anchors really are on a second level below the sections in the TOC.
  - The TOC should be a sidebar and clickable to go to the respective anchor. Because the file on disk is kept as a valid HTML document (header + footer) at all times, the TOC/JS can run once when the document is opened in a browser and will reflect appended chunks after each append (the footer rewrite preserves document validity).
- Support for anchors to structure log:
  - Anchors print a clickable `file://` link in markdown format to the terminal: `[🔗Anchor Name](file://path/log.html#anchor-id)`.  
  - Links are relative paths with `path_prefix` for anchor references.
  - Section HTML starts with `<h1>` and an anchor; The default section is basename.  
  - Anchors generate `<h2>`s with a name and a **slugified ID** (append short UID if conflicts).

## Logging API
- stderr and stdout redirection
  - print to terminal as usual
  - NO CHANGE -> colors etc preserved in terminal
  - HTML log is written incrementally. Keep file open.
  - HTML log understands chunks of stderr, stdout, as well as special chunks.
    - injected HTML via inject_html function (described below)
    - 'ANSI cursor movements' chunks, which groups terminal lines with cursor movements, e.g. from progress bars. These should be shown in a `<details><pre>` tag with the first 20 characters followed by `...` if longer and never any newlines.
  - Keep track of `last_chunk_type` if the chunks of chunk_type can be merged. This should be done for 'stdout', 'stderr' and 'ANSI cursor movements' chunk_types. Other chunk_types set `last_chunk_type` to `None`.
  - When `last_chunk_type` and incoming `chunk_type` are identical, the implementation SHOULD merge the new data into the previous on-disk chunk by performing a seek-and-rewrite of the footer region: remove the footer, amend the last chunk content/closing tag, append new content, then re-write the footer. This preserves the intended "single chunk for consecutive writes" semantics while keeping the file a valid HTML document at all times.
    - Example: when a line is written to stdout and the previous lines were also stdout they appear as a single `<div class="stdout">...</div>` in the file. The class locates the footer marker, seeks to just before it, removes the footer bytes, appends the new content into the existing stdout chunk, and re-writes the footer.
  - Keep track of open tags and chunk boundaries so each write produces a valid HTML document on disk. The class must ensure that required closing tags (e.g., `</div>`, `</body>`, `</html>`) are present after each write.
- Only these functions print to logs:  
  - `start(section_name)`: new section, adds anchor. Sets chunk_type to None.
  - `print(data, chunk_type: str = 'stdout')`: append to logs. Check for cursor movements. If any, chunk_type is 'ANSI cursor movements'. Else chunk_type is stderr or stdout. If chunk_type of last `print(...)` statement was the same and no other writing function (i.e. start, anchor and inject_html) have been called, then the data is merged into the last chunk. Else it will be written as a new chunk.
    - merging is implemented by seeking back to remove the footer, updating the last chunk's closing tag/content, and re-writing the footer. This maintains on-disk validity without buffering the whole log in memory.
  - `anchor(anchor_text, anchor_name=None)`: add `<h2>` with anchor text and anchor to HTML, print link with `[🔗{anchor_text}](file://...index.html#{anchor_name})` to terminal (directly, no redirection). Sets chunk_type to None.
  - `inject_html(html_content, anchor_text, anchor_name=None)`: add anchor (unless neither anchor_text nor anchor_name are given), and append html_content to HTML file as a separate unique chunk that will never be appended to. Sets chunk_type to None.
    - Implementation note: `inject_html` should use the same seek-and-rewrite-footer flow so that each append produces a valid document on disk.
- Utility functions (use `inject_html` internally):  
  - `inject_image(pil_image, anchor_text, anchor_name=None)`: embed PIL image as Base64.  
  - `inject_table(table_data, anchor_text, text_preview=False)`: HTML table for log; Rich table to terminal.  
  - `inject_json(dict, anchor_text, line_numbers=False)`: pretty, syntax-highlighted JSON.

## Streams & Control Sequences
- Capture both `stdout` and `stderr` into a single HTML log.  
- Convert ANSI color (SGR) codes to HTML styles; preserve colors.
- Font and text-style control sequences:
    - Translate standard ANSI SGR attributes to HTML/CSS: bold, dim, italic, underline, blink, inverse, strikethrough and color foreground/background.
    - Map common OSC or SGR hints for font-family/size/weight when present to equivalent CSS where possible; if an OSC font request cannot be mapped deterministically, fall back to preserving the raw text or grouping into an ANSI cursor-movement block.
- Simple cursor & line control handling:
    - Carriage return (`\r`): update the current open stdout/stderr chunk by replacing content after the last line-start up to the current write position (i.e., emulate terminal behavior in HTML). If a chunk is already closed, start a new chunk and apply overwrite semantics there.
    - Delete-last-line / cursor-up + erase-line sequences (e.g., ESC [1A, ESC [K]): interpret these to remove or modify the previous line(s) in the current open chunk when possible. If interpretation is ambiguous or complex, group the raw sequence into an `ANSI cursor movements` chunk and render in `<details><pre>`.
    - Backspace and similar single-character deletions should edit the current line in the open chunk.
    - All interpreted edits must maintain HTML validity (i.e., overwrite without leaving unclosed tags). Complex cursor manipulations that cannot be applied safely are captured as `ANSI cursor movements` details blocks instead.
- Remove control sequences (or translate them) before adding to plain HTML text. Preserve terminal appearance for terminal output.

## Navigation & Anchors
- HTML uses `<h1>` for sections, `<h2>` for anchors.  
- Movable dark-themed sidebar TOC with clickable navigation.  
- TOC includes timestamp tooltips.  
- Console/terminal log includes clickable `file://` links to HTML anchors.
- Keep CSS clean and simple but modern.

## Performance
- Group text content to reduce HTML bloat and improve readability.  
- Batch file writes (append lines, not per character).
- Open HTML log file in a+ mode.
- Assume that rich and PIL are available - no optional dependencies.
- Do not be defensive in coding. Rather fail fast and be concise.

## Example Usage

```python

import rich
from rich.progress import Progress
from tqdm import tqdm

with LogTeeHTML("Test Log", logfile_prefix='./') as logger:
    logger.inject_html(extra_css)
    logger.start("Training")

    print("A colored rich panel should also look correct in HTML")
    rich.print(rich.Panel("Training Pipeline Started", title="Status", border_style="green"))
    print("Note that the panel should not have produced any <detail> tag with control sequences.")
    
    print("A table is special, since it renders differently to the terminal and to HTML.")
    print("The table, when written to the t erminal, should NOT also be redirected to the HTML!")
    print("Else, the table would be suplicated in the HTML, once as proper <table> and once as stdout chunk.")
    table_data = [ 
        {'sample_id': 'A01', 'loss': 0.12, 'error [mm]': 1.5},
        {'sample_id': 'A02', 'loss': 0.09, 'error [mm]': 2.1},
        {'sample_id': 'A03', 'loss': 0.15, 'error [mm]': 0.8},
    ]
    logger.inject_table(table_data, "Epoch 0 Validation", text_preview=True)

    print("The tqdm progress bar is shown as a single <details> tag in HTML")
    print("Reason: all lines containing terminal control characters are grouped this way!")
    for i in tqdm(range(10)):
        pass
    
    print("Same thing different library:")
    with Progress() as progress:
        task = progress.add_task("[cyan]Processing...", total=10)
        while not progress.finished:
            progress.update(task, advance=1)  # move bar forward
            time.sleep(0.1)  # simulate work

    print("Here is an image injection")
    # Create a simple test image
    img = Image.new('RGB', (200, 100), color='blue')
    draw = ImageDraw.Draw(img)
    draw.text((10, 40), "Test Image", fill='white')
    logger.inject_image(img, anchor_text="Test Image", anchor_name="test-image")
    
    print("Here is some stderr that should correctly be captured in the HTML")
    try:
        print("About to crash...")
        raise RuntimeError("Simulated crash for stderr logging!")
    except Exception as e:
        print("Caught exception, printing to stderr:", file=sys.stderr)
        traceback.print_exc()
    print("Test Done.")
```

## Basic (incomplete) Interface:

```python
class LogTeeHTML:
    def __init__(self, log_name: str, suffix: str = None, path_prefix: str = None, logfile_prefix: str = None):
        # log_name is slugified and used as a HTML log file name.
        # suffix is appended to filename before extension. If suffix is None, it will become "_YYYYMMDD_HHMM"
        # logfile_prefix is used ONLY for printing to terminal.
        # It replaces the absolute path to the HTML file with just prefix/local/path.html
        # The default section name is log_name.
        pass

    def start(self, section_name: str):
        # Adds an <h1> with the section name and an anchor as well. Uses self.print(...) internally.
        pass

    def print(self, data, chunk_type: str = 'stdout'):
        # Prints standard stdout and stderr stuff to the HTML log - but also all other stuff, such as injected HTML
        # Consecutive lines for stdout, stderr and those lines containing cursor movements are grouped together if they are directly behind one another
        # This means the function must be able to overwrite the closing tag of the previous chunk to merge the contents of the last chunk with the new data.
        # Should use a variable that is a dict mapping from chunk_type to closing tag for mergeable chunk_types
        pass

    def anchor(self, anchor_text: str, anchor_name: str = None):
        # Inserts an <h2> to the HTML log that has a tooltip with current time. Uses self.print(...) internally.
        # Also prints a link to the log like so: "[🔗{anchor_text}](file://{path}/index.html#{anchor_name})"
        # path is either the relative path to the logfile, or if path_prefix is given it will be path_prefix/logdir
        pass

    def inject_html(self, html_content: str, anchor_text: str, anchor_name: str = None):
        # Create an anchor
        # Then insert the html_content directly into the HTML log.
        # Uses self.print(...) internally.
        pass

    def inject_image(self, pil_image, anchor_text: str, anchor_name: str = None):
        # Encodes the pil_image as base64 and calls inject_html with an <img> tag
        pass

    def inject_table(self, table_data: list[dict], anchor_text: str, text_preview: bool = False):
        # Calls inject_html with an html table given table_data
        # if text_preview is given, it also prints to the terminal (WITHOUT redirection) using rich.
        # The table will NOT be printed to the HTML log twice.
        pass

    def inject_json(self, data: dict, anchor_text: str, line_numbers: bool = False):
        # Exports data to json (text representation) with indentation and prints it in the panel.
        # The rich panel with line-numbered and syntax-highlighted source code
        pass
    
    def __enter__(self):
        pass
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    ```
\