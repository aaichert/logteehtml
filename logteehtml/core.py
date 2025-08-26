import sys
import os
import json
import re
import time
import atexit
import base64
from datetime import datetime
from io import StringIO
from typing import Dict, Any, Optional

class LogTeeHTML:
    def __init__(self, name: str, prefix: Optional[str] = None, logfile_prefix: Optional[str] = None):
        # Setup file paths
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M_%S") + f"{now.microsecond:06d}"[:3]
        self.basename = f"{prefix or timestamp}_{name}"
        self.logfile_prefix = logfile_prefix or os.path.abspath(".")
        
        # File paths
        self.txt_path = f"{self.basename}.txt"
        self.json_path = f"{self.basename}.json"
        self.html_path = f"{self.basename}.html"
        
        # Internal state
        self.data: Dict[str, Dict[float, Dict[str, str]]] = {}
        self.current_stage = self.basename
        self.anchor_counter = 0
        
        # Stream capture
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self._setup_stream_capture()
        
        # Initialize with first stage
        self.start(self.current_stage)
        
        # Register cleanup
        atexit.register(self._cleanup)
    
    def _setup_stream_capture(self):
        sys.stdout = StreamCapture(self, 'stdout')
        sys.stderr = StreamCapture(self, 'stderr')
    
    def _generate_anchor_id(self, name: str) -> str:
        # Simple slugify
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        
        # Always append counter to ensure uniqueness
        self.anchor_counter += 1
        return f"{slug}-{self.anchor_counter}"
    
    def start(self, stage_name: str):
        timestamp = time.time()
        
        # Create stage if not exists
        if stage_name not in self.data:
            self.data[stage_name] = {}
        
        self.current_stage = stage_name
        anchor_id = self._generate_anchor_id(stage_name)
        
        # Add anchor entry
        self.data[stage_name][timestamp] = {
            "stream": "anchor",
            "data": stage_name,
            "anchor_id": anchor_id,
            "anchor_text": stage_name
        }
        
        # Write to console and txt
        full_path = os.path.abspath(self.html_path)
        link = f"file://{full_path}#{anchor_id}"
        console_msg = f"\n=== {stage_name} === [🔗 {link}]\n"
        self._write_to_console(console_msg)
        self._update_txt()
    
    def print(self, data: str, stderr: bool = False):
        timestamp = time.time()
        stream = "stderr" if stderr else "stdout"
        
        if self.current_stage not in self.data:
            self.data[self.current_stage] = {}
        
        # Ensure proper newlines
        if not data.endswith('\n'):
            data += '\n'
        
        self.data[self.current_stage][timestamp] = {
            "stream": stream,
            "data": data
        }
        
        self._write_to_console(data, stderr)
        self._update_txt()
    
    def inject_html(self, html: str, anchor_name: Optional[str] = None):
        timestamp = time.time()
        stage_slug = re.sub(r'[^\w\s-]', '', self.current_stage.lower())
        stage_slug = re.sub(r'[-\s]+', '-', stage_slug).strip('-')
        anchor_id = self._generate_anchor_id(f"{stage_slug}")
        anchor_text = anchor_name or "HTML Content"
        
        if self.current_stage not in self.data:
            self.data[self.current_stage] = {}
        
        self.data[self.current_stage][timestamp] = {
            "stream": "html",
            "data": html,
            "anchor_id": anchor_id,
            "anchor_text": anchor_text
        }
        
        # Show link in console
        full_path = os.path.abspath(self.html_path)
        link = f"file://{full_path}#{anchor_id}"
        console_msg = f"🔗 {link}\n"
        self._write_to_console(console_msg)
        self._update_txt()
    
    def inject_image(self, pil_image, anchor_name: Optional[str] = None):
        # Convert PIL to base64
        import io
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        img_data = base64.b64encode(buffer.getvalue()).decode()
        html = f'<img src="data:image/png;base64,{img_data}" style="max-width: 100%;">'
        self.inject_html(html, anchor_name or "Image")
    
    def _write_to_console(self, data: str, stderr: bool = False):
        stream = self._original_stderr if stderr else self._original_stdout
        stream.write(data)
        stream.flush()
    
    def _update_txt(self):
        with open(self.txt_path, 'w') as f:
            for stage_name, entries in self.data.items():
                f.write(f"\n=== {stage_name} ===\n")
                for timestamp in sorted(entries.keys()):
                    entry = entries[timestamp]
                    if entry["stream"] == "anchor":
                        continue  # Skip anchor entries in txt
                    elif entry["stream"] == "html":
                        anchor_id = entry.get("anchor_id", "")
                        full_path = os.path.abspath(self.html_path)
                        link = f"file://{full_path}#{anchor_id}"
                        f.write(f"🔗 {link}\n")
                    else:
                        prefix = "[STDERR] " if entry["stream"] == "stderr" else ""
                        # Ensure proper newlines
                        data = entry['data']
                        if not data.endswith('\n'):
                            data += '\n'
                        f.write(f"{prefix}{data}")
    
    def _update_html(self):
        html = self._generate_html()
        with open(self.html_path, 'w') as f:
            f.write(html)
    
    def _update_json(self):
        with open(self.json_path, 'w') as f:
            json.dump({
                'basename': self.basename,
                'logfile_prefix': self.logfile_prefix,
                'data': self.data
            }, f, indent=2)
    
    def _generate_html(self) -> str:
        # Simple HTML generation without templates
        toc_items = []
        content_sections = []
        
        for stage_name, entries in self.data.items():
            # Find the stage anchor and earliest timestamp
            stage_anchor = None
            stage_timestamp = None
            for timestamp, entry in sorted(entries.items()):
                if entry.get("stream") == "anchor":
                    stage_anchor = entry.get("anchor_id")
                if stage_timestamp is None:
                    stage_timestamp = timestamp
                    break
            
            if not stage_anchor:
                stage_anchor = stage_name.lower().replace(" ", "-")
            
            # Format timestamp for tooltip
            stage_time_str = ""
            if stage_timestamp:
                dt = datetime.fromtimestamp(stage_timestamp)
                stage_time_str = dt.strftime("%H:%M:%S")
            
            # Add stage to TOC with timestamp tooltip
            toc_items.append(f'<div class="toc-stage"><a href="#{stage_anchor}" title="Started: {stage_time_str}"> {stage_name}</a></div>')
            
            # Add stage content
            content_sections.append(f'<h1 id="{stage_anchor}">{stage_name}</h1>')
            
            # Collect HTML anchors for this stage and group content
            html_anchors = []
            current_text_content = []
            current_text_timestamps = []
            
            for timestamp in sorted(entries.keys()):
                entry = entries[timestamp]
                if entry["stream"] == "anchor":
                    continue
                elif entry["stream"] == "html":
                    # Flush any accumulated text content before HTML injection
                    if current_text_content:
                        combined_text = ''.join(current_text_content)
                        if combined_text.strip():
                            # Get timestamp range for tooltip
                            start_time = datetime.fromtimestamp(current_text_timestamps[0]).strftime("%H:%M:%S")
                            end_time = datetime.fromtimestamp(current_text_timestamps[-1]).strftime("%H:%M:%S")
                            time_tooltip = f"Time: {start_time}" if start_time == end_time else f"Time: {start_time} - {end_time}"
                            content_sections.append(f'<div class="text-block" title="{time_tooltip}">{self._ansi_to_html(combined_text)}</div>')
                        current_text_content = []
                        current_text_timestamps = []
                    
                    # Add HTML content
                    anchor_id = entry.get("anchor_id", "")
                    anchor_text = entry.get("anchor_text", "HTML Content")
                    # Format timestamp for tooltip
                    dt = datetime.fromtimestamp(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                    html_anchors.append((anchor_id, anchor_text, time_str))
                    content_sections.append(f'<h2 id="{anchor_id}">{anchor_text}</h2>')
                    content_sections.append(entry["data"])
                else:
                    # Accumulate text content with timestamps
                    content = entry["data"]
                    if entry["stream"] == "stderr":
                        content = f'<span class="stderr">❗ {content}</span>'
                    current_text_content.append(content)
                    current_text_timestamps.append(timestamp)
            
            # Flush any remaining text content
            if current_text_content:
                combined_text = ''.join(current_text_content)
                if combined_text.strip():
                    # Get timestamp range for tooltip
                    start_time = datetime.fromtimestamp(current_text_timestamps[0]).strftime("%H:%M:%S")
                    end_time = datetime.fromtimestamp(current_text_timestamps[-1]).strftime("%H:%M:%S")
                    time_tooltip = f"Time: {start_time}" if start_time == end_time else f"Time: {start_time} - {end_time}"
                    content_sections.append(f'<div class="text-block" title="{time_tooltip}">{self._ansi_to_html(combined_text)}</div>')
            
            # Add HTML anchors to TOC with indentation and timestamps
            for anchor_id, anchor_text, time_str in html_anchors:
                toc_items.append(f'<div class="toc-html"><a href="#{anchor_id}" title="Added: {time_str}">🔗 {anchor_text}</a></div>')
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{self.basename} - Log</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
            margin: 0; 
            display: flex; 
            background: #1a1a1a;
            color: #e0e0e0;
            line-height: 1.4;
        }}
        .sidebar {{ 
            position: fixed;
            top: 0;
            left: 0;
            height: 100vh;
            width: 250px; 
            background: linear-gradient(135deg, #1a1a1a 0%, #252525 100%); 
            color: #e0e0e0;
            padding: 15px; 
            overflow-y: auto; 
            box-shadow: 3px 0 10px rgba(0,0,0,0.3);
            z-index: 1000;
        }}
        .sidebar::-webkit-scrollbar {{ width: 6px; }}
        .sidebar::-webkit-scrollbar-track {{ background: rgba(255,255,255,0.1); }}
        .sidebar::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.3); border-radius: 3px; }}
        .sidebar h3 {{ 
            margin-top: 0; 
            margin-bottom: 8px;
            color: #f0f0f0; 
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 6px;
            font-size: 1.1em;
        }}
        .toc-stage {{ 
            margin: 6px 0; 
            padding: 6px 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 6px;
            border-left: 3px solid #888;
            transition: all 0.2s ease;
        }}
        .toc-stage:hover {{
            background: rgba(255,255,255,0.15);
            transform: translateX(2px);
        }}
        .toc-stage a {{ 
            color: #f0f0f0; 
            text-decoration: none; 
            font-weight: bold;
            display: block;
            font-size: 0.8em;
        }}
        .toc-stage a:hover {{ 
            color: #fff; 
            text-shadow: 0 0 8px rgba(255,255,255,0.4);
        }}
        .toc-html {{ 
            margin: 3px 0 3px 18px; 
            padding: 3px 6px;
            background: rgba(255,255,255,0.05);
            border-radius: 4px;
            border-left: 2px solid rgba(136,136,136,0.6);
            transition: all 0.2s ease;
        }}
        .toc-html:hover {{
            background: rgba(255,255,255,0.1);
            transform: translateX(2px);
        }}
        .toc-html a {{ 
            color: #d0d0d0; 
            text-decoration: none; 
            font-size: 0.7em;
        }}
        .toc-html a:hover {{ 
            color: #f0f0f0; 
        }}
        .content {{ 
            flex: 1; 
            margin-left: 250px;
            padding: 20px; 
            background: #151515;
            min-height: 100vh;
            max-width: calc(100vw - 270px);
            overflow-x: auto;
            word-wrap: break-word;
            font-size: 0.9em;
        }}
        .stderr {{ color: #ff6b6b; font-weight: bold; }}
        .text-block {{ 
            margin: 6px 0; 
            background: #1f1f1f;
            color: #d0d0d0;
            padding: 6px 10px;
            border-radius: 4px;
            border-left: 3px solid #444;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
            line-height: 1.3;
            white-space: pre-wrap;
            font-family: inherit;
            font-size: 0.85em;
        }}
        pre {{ 
            margin: 4px 0; 
            background: #1f1f1f;
            color: #d0d0d0;
            padding: 6px;
            border-radius: 4px;
            border-left: 3px solid #555;
            overflow-x: auto;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            line-height: 1.2;
        }}
        h1 {{ 
            color: #f0f0f0; 
            border-bottom: 2px solid #888; 
            padding-bottom: 6px;
            margin-top: 25px;
            margin-bottom: 12px;
            font-size: 1.6em;
        }}
        h2 {{ 
            color: #d0d0d0; 
            border-left: 4px solid #666; 
            padding: 6px 12px;
            margin-top: 15px;
            margin-bottom: 8px;
            background: rgba(102,102,102,0.1);
            border-radius: 3px;
            font-size: 1.2em;
        }}
        /* Dark mode styling for injected content */
        .content table {{
            background: #2a2a2a;
            color: #e0e0e0;
            border-collapse: collapse;
            width: 100%;
        }}
        .content table th {{
            background: #3a3a3a;
            color: #f0f0f0;
            padding: 8px 12px;
            border: 1px solid #555;
        }}
        .content table td {{
            padding: 6px 12px;
            border: 1px solid #444;
        }}
        .content table caption {{
            color: #d0d0d0;
            margin-bottom: 8px;
            font-weight: bold;
        }}
        .content img {{
            border-radius: 6px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        /* Override injected content colors for better readability */
        .content div {{
            color: #e0e0e0 !important;
        }}
        .content h3 {{
            color: #f0f0f0 !important;
        }}
        .content p {{
            color: #d0d0d0 !important;
        }}
        .content ul li {{
            color: #d0d0d0 !important;
        }}
        .content div[style*="background-color"] {{
            background-color: #2a2a2a !important;
            border-left-color: #888 !important;
        }}
    </style>
</head>
<body>
    <div class="sidebar">
        <h3>📋 Table of Contents</h3>
        {''.join(toc_items)}
    </div>
    <div class="content">
        {''.join(content_sections)}
    </div>
</body>
</html>"""
    
    def _ansi_to_html(self, text: str) -> str:
        # Skip ANSI conversion if text already contains HTML tags
        if re.search(r'<[^>]+>', text):
            return text
            
        # ANSI color code to HTML conversion
        color_map = {
            '30': 'black', '31': 'red', '32': 'green', '33': 'yellow',
            '34': 'blue', '35': 'magenta', '36': 'cyan', '37': 'white',
            '90': 'darkgray', '91': 'lightred', '92': 'lightgreen', '93': 'lightyellow',
            '94': 'lightblue', '95': 'lightmagenta', '96': 'lightcyan', '97': 'white'
        }
        
        # Convert color codes
        for code, color in color_map.items():
            text = re.sub(f'\x1b\\[{code}m', f'<span style="color: {color}">', text)
        
        # Handle reset codes
        text = re.sub(r'\x1b\[0m', '</span>', text)
        text = re.sub(r'\x1b\[m', '</span>', text)
        
        # Remove other escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _cleanup(self):
        # Restore streams
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        
        # Final save
        self._update_html()
        self._update_json()

class StreamCapture:
    def __init__(self, logger: LogTeeHTML, stream_type: str):
        self.logger = logger
        self.stream_type = stream_type
        self.buffer = ""
    
    def write(self, data: str):
        self.buffer += data
        if '\n' in data or '\r' in data:
            self.flush()
    
    def flush(self):
        if self.buffer:
            self.logger.print(self.buffer, stderr=(self.stream_type == 'stderr'))
            self.buffer = ""
    
    def __getattr__(self, name):
        # Delegate other methods to original stream
        original = self.logger._original_stdout if self.stream_type == 'stdout' else self.logger._original_stderr
        return getattr(original, name)