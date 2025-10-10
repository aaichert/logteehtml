import io
import os
import re
import sys
import uuid
import json
import base64
from datetime import datetime
from typing import Optional
import fcntl
import threading
from PIL import Image
import rich

_FOOTER_MARKER = "<!-- LOGTEEHTML_FOOTER -->"
_CHUNK_CLOSER = "</pre></div>\n"

# Regex: Rich panel top border e.g. "╭─ Title ─────────╮"
_RICH_PANEL_TOP_RE = re.compile(r'^╭─\s*(.*?)\s*─*╮\s*$')
# Regex: Markdown-style heading lines we want to auto-anchor, e.g. "### Some Title" (3+ leading #)
_MARKDOWN_HEADING_RE = re.compile(r'^(#{3,})\s+(.+?)\s*$')


def _slugify(s: str) -> str:
	s = s.lower()
	s = re.sub(r"[^a-z0-9_-]+", "-", s)
	s = re.sub(r"-+", "-", s).strip("-")
	return s or "anchor"


def _strip_ansi(text: str) -> str:
	# Minimal ANSI escape removal. For complex SGR->HTML mapping a dedicated parser would be better.
	return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)

_ANSI_COLOR_MAP = {
	30: '#000000', 31: '#aa0000', 32: '#00aa00', 33: '#aa5500',
	34: '#0000aa', 35: '#aa00aa', 36: '#00aaaa', 37: '#aaaaaa',
    90: '#555555', 91: '#ff5555', 92: '#55ff55', 93: '#ffff55',
    94: '#5555ff', 95: '#ff55ff', 96: '#55ffff', 97: '#ffffff',
    40: '#000000', 41: '#aa0000', 42: '#00aa00', 43: '#aa5500',
    44: '#0000aa', 45: '#aa00aa', 46: '#00aaaa', 47: '#aaaaaa',
    100: '#555555', 101: '#ff5555', 102: '#55ff55', 103: '#ffff55',
    104: '#5555ff', 105: '#ff55ff', 106: '#55ffff', 107: '#ffffff',
}

def _escape_html(text: str) -> str:
	return (
		text.replace("&", "&amp;")
		.replace("<", "&lt;")
		.replace(">", "&gt;")
	)

class _StreamProxy:
	"""Proxy for sys.stdout/sys.stderr that writes to the terminal and also forwards to LogTeeHTML."""
	def __init__(self, logger, chunk_type: str, orig):
		self._logger = logger
		self._chunk_type = chunk_type
		self._orig = orig
		self._buf = ''

	def write(self, s):
		# write to original terminal first (best-effort)
		self._orig.write(s)
		self._orig.flush()

		if s.startswith('[🔗') and '](file://' in s:
			return
		# Forward the full chunk as-is; LogTeeHTML will decide merge semantics.
		self._logger.print(s, chunk_type=self._chunk_type)

	def flush(self):
		self._orig.flush()

	def isatty(self):
		return getattr(self._orig, 'isatty', lambda: False)()

	@property
	def encoding(self):
		return getattr(self._orig, 'encoding', 'utf-8')



def _is_non_printable_only(text: str) -> bool:
	# Returns True if text contains only whitespace or non-printable characters
	return not text.strip() or all(ord(c) < 32 or ord(c) == 127 for c in text if c != '\n')

class LogTeeHTML:
	"""Append-only HTML logger that keeps on-disk file a valid HTML document by seek-and-rewrite of a small footer region.

	Behavior notes (Version 1):
	- The file contains a unique footer marker. Every append finds that marker, reads the trailing footer bytes,
	  seeks back to the marker position and writes `new_bytes + marker + footer_tail`.
	- Consecutive mergeable writes (stdout/stderr/ansi-cursor) are implemented by inserting inner content before the
	  last chunk's closing tag; this is achieved by locating the footer marker and overwriting the closing tag region.
	"""

	def __init__(self, log_name: str, suffix: Optional[str] = None, path_prefix: Optional[str] = None, logfile_prefix: Optional[str] = None, template: str = 'pretty.html'):
		if suffix is None:
			suffix = datetime.now().strftime("_%Y%m%d_%H%M")
		self.suffix = suffix
		self.path_prefix = path_prefix
		self.logfile_prefix = logfile_prefix
		template_dir = os.path.dirname(os.path.abspath(__file__))
		template_path = os.path.join(template_dir, template)
		with open(template_path, "r", encoding="utf-8") as f:
			self.template = f.read()
		# apply title placeholder into the template (assign result)
		self.template = self.template.replace("{title}", log_name)
		self.filepath = f"{log_name}{self.suffix}.html"
		self._fh = None
		self._last_chunk_type = None
		self._last_chunk_base: Optional[str] = None
		self._marker_pos_cache: Optional[int] = None
		
		# ANSI state tracking for color persistence
		self._ansi_state = {
			'bold': False,
			'dim': False, 
			'underline': False,
			'fg_color': None,
			'bg_color': None
		}

		# Per-instance re-entrant lock for thread-safety around actual file writes
		# Use RLock so the same thread can re-enter if needed.
		self._file_lock = threading.RLock()

	def __enter__(self):
		dirname = os.path.dirname(self.filepath)
		if dirname:
			os.makedirs(dirname, exist_ok=True)
		with open(self.filepath, 'wb') as f:
			f.write(self.template.encode('utf8'))
		self._fh = open(self.filepath, 'r+b')
		os.set_inheritable(self._fh.fileno(), False)
		if _FOOTER_MARKER.encode('utf8') not in self._fh.read():
			raise RuntimeError('Footer marker missing in template')
		self._fh.seek(0, io.SEEK_SET)
		self._marker_pos_cache = self._find_marker()

		self._orig_stdout = sys.stdout
		self._orig_stderr = sys.stderr
		sys.stdout = _StreamProxy(self, 'stdout', self._orig_stdout)
		sys.stderr = _StreamProxy(self, 'stderr', self._orig_stderr)
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		# If an exception occurred inside the context, capture and write traceback
		# to the HTML log before restoring original streams. This ensures it is
		# persisted even though Python prints the traceback only after __exit__.
		if exc_type is not None and self._fh and not self._fh.closed:
			try:
				import traceback
				# Break any current mergeable chunk so traceback starts a fresh stderr chunk
				self._last_chunk_type = None
				self._last_chunk_base = None
				self.print("\n--- Unhandled Exception (will be re-raised) ---\n", chunk_type='stderr')
				for line in traceback.format_exception(exc_type, exc_val, exc_tb):
					self.print(line, chunk_type='stderr')
			except Exception:
				# Best effort: never let logging of traceback itself raise
				pass
		# restore stdout/stderr
		sys.stdout = getattr(self, '_orig_stdout', sys.stdout)
		sys.stderr = getattr(self, '_orig_stderr', sys.stderr)
		# close file handle
		if self._fh and not self._fh.closed:
			self._fh.close()

	# --- low-level helpers ---
	def _find_marker(self) -> int:
		# Prefer cached marker position when available and valid
		if self._marker_pos_cache is not None:
			self._fh.seek(self._marker_pos_cache)
			probe = self._fh.read(len(_FOOTER_MARKER.encode('utf8')))
			if probe == _FOOTER_MARKER.encode('utf8'):
				return self._marker_pos_cache
		self._fh.seek(0, io.SEEK_END)
		filesize = self._fh.tell()
		# read tail up to 32KiB to find marker quickly
		read_size = min(filesize, 32 * 1024)
		self._fh.seek(filesize - read_size)
		tail = self._fh.read(read_size)
		idx = tail.rfind(_FOOTER_MARKER.encode('utf8'))
		if idx >= 0:
			pos = filesize - read_size + idx
			self._marker_pos_cache = pos
			return pos
		# fallback: search whole file (rare)
		self._fh.seek(0)
		data = self._fh.read()
		idx = data.rfind(_FOOTER_MARKER.encode('utf8'))
		if idx < 0:
			raise RuntimeError('Footer marker not found')
		self._marker_pos_cache = idx
		return idx

	def _read_footer_tail(self, marker_pos: int) -> bytes:
		after = marker_pos + len(_FOOTER_MARKER.encode('utf8'))
		self._fh.seek(after)
		return self._fh.read()

	def _rewrite_at(self, pos: int, new_bytes: bytes):
		# Overwrite starting at pos with new_bytes and then truncate remainder.
		# Acquire an advisory flock for the write and ensure it is always released.
		fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
		try:
			self._fh.seek(pos)
			self._fh.write(new_bytes)
			self._fh.truncate()
			self._fh.flush()
			os.fsync(self._fh.fileno())
		finally:
			fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)

	def _ansi_to_html_stateful(self, text: str) -> str:
		"""Convert ANSI to HTML while maintaining state across calls"""
		parts = re.split(r'(\x1b\[[0-9;]*m)', text)
		out = []
		
		# Start with current state if any colors are active
		if self._ansi_state['fg_color'] or self._ansi_state['bg_color'] or self._ansi_state['bold'] or self._ansi_state['dim'] or self._ansi_state['underline']:
			styles = []
			if self._ansi_state['bold']:
				styles.append('font-weight:700')
			if self._ansi_state['dim']:
				styles.append('opacity:0.7')
			if self._ansi_state['underline']:
				styles.append('text-decoration:underline')
			if self._ansi_state['fg_color']:
				styles.append(f'color:{self._ansi_state["fg_color"]}')
			if self._ansi_state['bg_color']:
				styles.append(f'background-color:{self._ansi_state["bg_color"]}')
			if styles:
				out.append(f'<span style="{";".join(styles)}">')
		
		span_open = bool(self._ansi_state['fg_color'] or self._ansi_state['bg_color'] or self._ansi_state['bold'] or self._ansi_state['dim'] or self._ansi_state['underline'])
		
		for p in parts:
			if not p:
				continue
			m = re.match(r'\x1b\[([0-9;]*)m', p)
			if m:
				codes = [int(x) for x in m.group(1).split(';') if x]
				if not codes:
					codes = [0]
				
				for code in codes:
					if code == 0:
						# reset all
						if span_open:
							out.append('</span>')
							span_open = False
						self._ansi_state = {
							'bold': False,
							'dim': False,
							'underline': False, 
							'fg_color': None,
							'bg_color': None
						}
					elif code == 1:
						self._ansi_state['bold'] = True
					elif code == 2:
						self._ansi_state['dim'] = True
					elif code == 4:
						self._ansi_state['underline'] = True
					elif 30 <= code <= 37:
						self._ansi_state['fg_color'] = _ANSI_COLOR_MAP.get(code)
					elif 90 <= code <= 97:
						self._ansi_state['fg_color'] = _ANSI_COLOR_MAP.get(code)
					elif 40 <= code <= 47:
						self._ansi_state['bg_color'] = _ANSI_COLOR_MAP.get(code)
					elif 100 <= code <= 107:
						self._ansi_state['bg_color'] = _ANSI_COLOR_MAP.get(code)
				
				# Close old span and open new one with updated styles
				if span_open:
					out.append('</span>')
				
				# Build new span with current state
				styles = []
				if self._ansi_state['bold']:
					styles.append('font-weight:700')
				if self._ansi_state['dim']:
					styles.append('opacity:0.7')
				if self._ansi_state['underline']:
					styles.append('text-decoration:underline')
				if self._ansi_state['fg_color']:
					styles.append(f'color:{self._ansi_state["fg_color"]}')
				if self._ansi_state['bg_color']:
					styles.append(f'background-color:{self._ansi_state["bg_color"]}')
				
				if styles:
					out.append(f'<span style="{";".join(styles)}">')
					span_open = True
				else:
					span_open = False
			else:
				out.append(_escape_html(p))
		
		# Don't close the span here - leave it open for state persistence
		return ''.join(out)

	def _close_ansi_spans(self) -> str:
		"""Close any open ANSI spans and reset state"""
		if self._ansi_state['fg_color'] or self._ansi_state['bg_color'] or self._ansi_state['bold'] or self._ansi_state['dim'] or self._ansi_state['underline']:
			self._ansi_state = {
				'bold': False,
				'dim': False,
				'underline': False,
				'fg_color': None,
				'bg_color': None
			}
			return '</span>'
		return ''

	# --- public API ---
	def start(self, section_name: str):
		self.end_chunk()
		sid = _slugify(section_name)
		h = f'<h1 id="{sid}">{section_name}</h1>\n'
		self._insert_bytes(h.encode('utf8'))
		# track current section id for anchors
		self._current_section_id = sid

	def anchor(self, anchor_text: str, anchor_name: Optional[str] = None, print_link: bool = True):
		# close any open mergeable chunk and ANSI spans
		self.end_chunk()
		if anchor_name is None:
			base = _slugify(anchor_text)
			anchor_name = f"{base}-{uuid.uuid4().hex[:6]}"
		# attach timestamp metadata and render a small timestamp next to the anchor text
		ts = datetime.now().isoformat()
		data_section = getattr(self, '_current_section_id', anchor_name) or anchor_name
		h = (
			f'<h2 id="{anchor_name}" data-section="{data_section}" '
			f'data-timestamp="{ts}" title="{ts}">{_escape_html(anchor_text)}</h2>\n'
		)
		self._insert_bytes(h.encode('utf8'))
		# Print clickable file:// link to terminal (no redirection)
		path = os.path.abspath(self.filepath)
		if self.logfile_prefix:
			link_path = os.path.join(self.logfile_prefix, self.filepath)
		else:
			link_path = path
		if print_link:
			# write directly to the real stdout to avoid re-capture by the proxy
			real = getattr(sys, '__stdout__', None)
			url=os.path.normpath(f"{link_path}#{anchor_name}")
			if real and hasattr(real, 'fileno'):
				os.write(real.fileno(), "\n".encode('utf8'))
				os.write(real.fileno(), f"[🔗{anchor_text}]( file://{url} )\n".encode('utf8'))
			else:
				if hasattr(self, '_orig_stdout') and self._orig_stdout:
					self._orig_stdout.write(f"[🔗{anchor_text}]( file://{url} )\n")
					self._orig_stdout.flush()

	def end_chunk(self):
		"""Force termination of the current mergeable chunk.

		Any subsequent print / inject call will start a new chunk. Also closes
		any open ANSI span so style state does not leak into the next chunk.
		Safe to call even if no chunk is open (idempotent).
		"""
		self._last_chunk_type = None
		self._last_chunk_base = None
		close_span = self._close_ansi_spans()
		if close_span:
			self._insert_bytes(close_span.encode('utf8'))


	def _find_last_chunk_start(self, chunk_type: str) -> Optional[int]:
		# Search backwards in file tail for last <div class="{chunk_type}" occurrence
		marker_pos = self._find_marker()
		# read a reasonable tail before the marker (includes last chunks)
		read_size = min(marker_pos, 512 * 1024)
		self._fh.seek(marker_pos - read_size)
		tail = self._fh.read(read_size)
		needle = f'<div class="{chunk_type}"'.encode('utf8')
		idx = tail.rfind(needle)
		if idx >= 0:
			return marker_pos - read_size + idx
		return None

	def _find_pos_of_last(self, pattern: bytes, before_pos: Optional[int] = None, max_search: int = 512 * 1024) -> Optional[int]:
		"""Find last occurrence of pattern before before_pos (defaults to footer marker).
		Searches up to max_search bytes backward from before_pos."""
		if before_pos is None:
			before_pos = self._find_marker()
		search_bytes = min(before_pos, max_search)
		self._fh.seek(before_pos - search_bytes)
		tail = self._fh.read(search_bytes)
		idx = tail.rfind(pattern)
		if idx >= 0:
			return before_pos - search_bytes + idx
		return None

	def _apply_carriage_return(self, text: str, chunk_type: str):
		# Apply simple carriage return semantics by replacing the last line of the last chunk
		# Protect entire read-modify-write operation to prevent race conditions
		with self._file_lock:
			# determine base stream for CR handling
			base = 'stderr' if chunk_type == 'stderr' else 'stdout'
			last_start = self._find_last_chunk_start(base)
			if last_start is None:
				# fallback: append as new chunk
				fallback_bytes = f'<div class="{chunk_type}"><pre>{_escape_html(_strip_ansi(text))}</pre></div>\n'.encode('utf8')
				self._marker_pos_cache = None
				marker_pos = self._find_marker()
				footer_tail = self._read_footer_tail(marker_pos)
				new_bytes = fallback_bytes + _FOOTER_MARKER.encode('utf8') + footer_tail
				self._rewrite_at(marker_pos, new_bytes)
				self._marker_pos_cache = marker_pos + len(fallback_bytes)
				return
			marker_pos = self._find_marker()
			footer_tail = self._read_footer_tail(marker_pos)

			# read existing chunk content
			self._fh.seek(last_start)
			chunk_bytes = self._fh.read(marker_pos - last_start)
			# Defensive: tolerate invalid utf-8 bytes to avoid crashing when reading file fragments.
			# Replace invalid sequences so the HTML remains valid and processing can continue.
			chunk_text = chunk_bytes.decode('utf8', errors='replace')

			# extract pre content
			m = re.search(r'<pre>(.*?)</pre>', chunk_text, flags=re.DOTALL)
			if not m:
				# cannot parse, fallback to details
				details = _escape_html(text)
				det = f'<details><summary>ANSI cursor</summary><pre>{details}</pre></details>\n'
				det_bytes = det.encode('utf8')
				self._marker_pos_cache = None
				marker_pos = self._find_marker()
				footer_tail = self._read_footer_tail(marker_pos)
				new_bytes = det_bytes + _FOOTER_MARKER.encode('utf8') + footer_tail
				self._rewrite_at(marker_pos, new_bytes)
				self._marker_pos_cache = marker_pos + len(det_bytes)
				return

			pre_content = m.group(1)
			# determine replacement text (take last segment after last \r)
			new_segment = text.split('\r')[-1]
			new_segment = _escape_html(_strip_ansi(new_segment))
			# replace last line in pre_content
			lines = pre_content.split('\n')
			if lines:
				lines[-1] = new_segment
			new_pre = '\n'.join(lines)
			new_chunk_text = chunk_text[:m.start(1)] + new_pre + chunk_text[m.end(1):]

			# write head up to last_start, then new_chunk_text, then marker + footer_tail
			head_pos = last_start
			# Use the existing file lock protection with flock
			fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
			try:
				self._fh.seek(head_pos)
				self._fh.write(new_chunk_text.encode('utf8'))
				self._fh.write(_FOOTER_MARKER.encode('utf8'))
				self._fh.write(footer_tail)
				self._fh.truncate()
				self._fh.flush()
				os.fsync(self._fh.fileno())
			finally:
				fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
			# refresh marker cache after modifying the file
			self._marker_pos_cache = self._find_marker()


	def print(self, data, chunk_type: str = 'stdout'):
		text = data if isinstance(data, str) else str(data)
		
		# Auto-anchor detection for Rich panel headers and markdown-like headings.
		# This is done before ANSI/state handling and merging decisions.
		if text:
			# Fast pre-check to avoid per-line loops when unnecessary
			if text.startswith('╭─') or text.startswith('###') or ('\n╭─' in text) or ('\n###' in text):
				for raw_line in text.splitlines():
					# Ignore overly long lines for auto anchor detection
					if len(raw_line) > 160:
						continue
					line = raw_line.strip('\r')
					if line.startswith('╭─'):
						m_panel = _RICH_PANEL_TOP_RE.match(line)
						if m_panel:
							title = m_panel.group(1)
							if title:
								self.anchor(title, print_link=False)
							continue
					m_md = _MARKDOWN_HEADING_RE.match(line)
					if m_md:
						_, title = m_md.groups()
						if title:
							self.anchor(title, print_link=False)
						continue
		# detect cursor/control sequences conservatively
		has_ansi = False
		only_m = True
		if '\x1b[' in text:
			seqs = re.findall(r'\x1b\[[0-9;]*[A-Za-z]', text)
			for s in seqs:
				has_ansi = True
				final = s[-1]
				if final != 'm':
					only_m = False
			if not only_m:
				chunk_type = 'ansi-cursor'

		# If we're already in ansi-cursor mode, stay in it until we can exit
		if self._last_chunk_type == 'ansi-cursor':
			chunk_type = 'ansi-cursor'

		# If previous chunk was 'ansi-cursor', only exit when we get a complete line (ending with \n) with no complex ANSI or control chars
		has_control_chars = '\r' in text or '\b' in text
		if (self._last_chunk_type == 'ansi-cursor' and 
			text.endswith('\n') and 
			(not has_ansi or only_m) and
			not has_control_chars):
			self._last_chunk_type = None
			self._last_chunk_base = None
			chunk_type = 'stdout'  # Reset to stdout after exiting ansi-cursor

		# convert ANSI to HTML where possible, otherwise escape
		if '\x1b[' in text:
			if chunk_type == 'ansi-cursor':
				stripped = re.sub(r'\x1b\[[0-9;]*[A-Za-z](?<!m)', '', text)
				escaped = self._ansi_to_html_stateful(stripped)
			else:
				escaped = self._ansi_to_html_stateful(text)
		else:
			escaped = _escape_html(text)

		# Decide merge vs new chunk
		mergeable = chunk_type in ('stdout', 'stderr', 'ansi-cursor')
		# Always merge consecutive mergeable chunks, even for non-printable-only data
		if '\r' in text and mergeable and self._last_chunk_base == chunk_type:
			self._apply_carriage_return(text, chunk_type)
			return
		if mergeable and self._last_chunk_base == chunk_type:
			# If data is only non-printable, just append
			if _is_non_printable_only(text):
				self._insert_before_closer(escaped.encode('utf8'))
				return
			# Otherwise, merge as usual
			inner = escaped
			self._insert_before_closer(inner.encode('utf8'))
			return
		# Otherwise, start a new chunk
		wrapper = f'<div class="{chunk_type}"><pre>{escaped}</pre></div>\n'
		self._insert_bytes(wrapper.encode('utf8'))
		self._last_chunk_type = chunk_type if mergeable else None
		self._last_chunk_base = chunk_type if mergeable else None

	def inject_html(self, html_content: str, anchor_text: Optional[str] = None, anchor_name: Optional[str] = None, print_link: bool = True):
		# inject HTML fragment wrapped in a collapsible chunk
		# Ensure we don't merge this injection into any open stdout/stderr chunk and close ANSI spans
		self._last_chunk_type = None
		self._last_chunk_base = None
		close_span = self._close_ansi_spans()
		if close_span:
			self._insert_bytes(close_span.encode('utf8'))
		if anchor_text is not None:
			if anchor_name is None:
				anchor_name = f"{_slugify(anchor_text)}-{uuid.uuid4().hex[:6]}"
			self.anchor(anchor_text, anchor_name, print_link=print_link)
		
		# Wrap HTML content in a chunk without pre tags
		wrapper = f'<div class="html-injection">{html_content}</div>\n'
		self._insert_bytes(wrapper.encode('utf8'))
		# ensure marker cache is updated after the explicit insert
		self._marker_pos_cache = self._find_marker()

	def inject_image(self, pil_image, anchor_text: str, anchor_name: Optional[str] = None):
		if Image is None:
			raise RuntimeError('PIL not available')
		bio = io.BytesIO()
		pil_image.save(bio, format='PNG')
		b64 = base64.b64encode(bio.getvalue()).decode('ascii')
		html = f'<img src="data:image/png;base64,{b64}" alt="{anchor_text}"/>\n'
		self.inject_html(html, anchor_text, anchor_name)

	def inject_table(self, table_data, anchor_text: str, text_preview: bool = False):
		# simple HTML table
		if not table_data:
			html = '<div><em>empty table</em></div>\n'
			self.inject_html(html, anchor_text, print_link=False)
			return
		keys = list(table_data[0].keys())
		rows = []
		for r in table_data:
			cols = ''.join(f'<td>{_escape_html(str(r.get(k, "")))}</td>' for k in keys)
			rows.append(f'<tr>{cols}</tr>')
		html = '<table border="1"><thead><tr>' + ''.join(f'<th>{_escape_html(k)}</th>' for k in keys) + '</tr></thead><tbody>' + '\n'.join(rows) + '</tbody></table>\n'
		self.inject_html(html, anchor_text)
		if text_preview:
			console = rich.console.Console(file=sys.__stdout__)
			rich_table = rich.table.Table(show_header=True, header_style="bold")
			for k in keys:
				rich_table.add_column(str(k))
			for row in table_data:
				rich_table.add_row(*[str(row.get(k, "")) for k in keys])
			console.print(f"Table: {anchor_text}")
			console.print(rich_table)

	def inject_json(self, data: dict, anchor_text: str, line_numbers: bool = False):
		txt = json.dumps(data, indent=2)
		if line_numbers:
			lines = txt.splitlines()
			numbered = '\n'.join(f'{i+1:4d}: {l}' for i, l in enumerate(lines))
			html = f'<pre>{_escape_html(numbered)}</pre>\n'
		else:
			html = f'<pre>{_escape_html(txt)}</pre>\n'
		self.inject_html(html, anchor_text)

	def _insert_bytes(self, b: bytes):
		# Insert b just before the footer marker
		# Protect entire read-modify-write operation to prevent race conditions
		with self._file_lock:
			# Force fresh marker lookup, then write the bytes and update the cached marker position.
			self._marker_pos_cache = None
			marker_pos = self._find_marker()
			footer_tail = self._read_footer_tail(marker_pos)
			new_bytes = b + _FOOTER_MARKER.encode('utf8') + footer_tail
			self._rewrite_at(marker_pos, new_bytes)
			# After inserting `b` the footer marker moves forward by len(b) bytes.
			self._marker_pos_cache = marker_pos + len(b)

	def _insert_before_closer(self, inner: bytes):
		# Insert inner before the last chunk closing tag that occurs before the footer marker.
		# Protect entire read-modify-write operation to prevent race conditions
		with self._file_lock:
			marker_pos = self._find_marker()
			closer = _CHUNK_CLOSER.encode('utf8')
			pos_closer = self._find_pos_of_last(closer, before_pos=marker_pos)
			if pos_closer is None:
				# fallback to simple insert - need to call unlocked version to avoid deadlock
				self._marker_pos_cache = None
				marker_pos = self._find_marker()
				footer_tail = self._read_footer_tail(marker_pos)
				new_bytes = inner + _FOOTER_MARKER.encode('utf8') + footer_tail
				self._rewrite_at(marker_pos, new_bytes)
				self._marker_pos_cache = marker_pos + len(inner)
				return
			footer_tail = self._read_footer_tail(marker_pos)
			# write: keep file up to pos_closer, then inner + closer + marker + footer_tail
			new_tail = inner + closer + _FOOTER_MARKER.encode('utf8') + footer_tail
			# perform rewrite starting at pos_closer (preserves head)
			self._rewrite_at(pos_closer, new_tail)
			# refresh cached marker position after rewrite
			self._marker_pos_cache = self._find_marker()

