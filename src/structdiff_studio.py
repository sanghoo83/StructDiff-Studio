# =============================================================================
# PROGRAM: StructDiff Studio
# DESCRIPTION: High-performance structured file comparison and report generator
# =============================================================================

import os
import zipfile
import io
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import defaultdict
from contextlib import contextmanager
import threading
import difflib
import hashlib
import itertools
import shutil
import subprocess
import tempfile
import time
import html as py_html
import sys
import math
import re  # 💡 Required for Regex Masking
from datetime import datetime

try:
    from lxml import etree
except ImportError:
    import tkinter.messagebox as mb
    root = tk.Tk()
    root.withdraw()
    mb.showerror("Error", "The 'lxml' library is required.\nPlease run 'pip install lxml' in your terminal.")
    exit()

# --- Configuration & Constants ---
COLORS = {
    "BG_PAGE":     "#153B50",
    "BG_CARD":     "#FFFFFF",
    "TEXT_HEAD":   "#1D1D1F",
    "TEXT_BODY":   "#86868B",
    "ACCENT":      "#0071E3",
    "ACCENT_HOVER":"#0077ED",
    "INPUT_BG":    "#F5F5F7",
    "BORDER":      "#D2D2D7",
    "WHITE":       "#FFFFFF",
    "ALERT":       "#FF3B30",
    "SUCCESS":     "#34C759",
    "WARNING":     "#FF9F0A"
}

FONT_HEAD = ("Helvetica", 16, "bold")
FONT_SUB  = ("Helvetica", 9)
FONT_BOLD = ("Helvetica", 10, "bold")
FONT_INPUT= ("Menlo", 10)
FONT_LIST = ("Menlo", 9) 

URL_PATTERN = re.compile(r'https?://[^\s"\'<>]+')
INVALID_WINDOWS_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
HASH_CHUNK_SIZE = 1024 * 1024
USE_NATIVE_DIFF_ENGINE = True
STRUCTURAL_HASH_PREFLIGHT = True
WINDOWS_DIFF_RELATIVE_PATH = os.path.join("tools", "windows", "diff.exe")
FOOTER_LOGO_RELATIVE_PATH = os.path.join("assets", "code_by_noah_logo.png")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def app_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, relative_path),
        os.path.join(os.path.dirname(script_dir), relative_path),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]

def draw_perfect_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    x2 -= 1; y2 -= 1
    max_radius = min(x2 - x1, y2 - y1) / 2
    radius = min(radius, max_radius)
    points = []
    for i in range(180, 270, 5):
        rad = math.radians(i)
        points.extend([x1 + radius + radius * math.cos(rad), y1 + radius + radius * math.sin(rad)])
    for i in range(270, 360, 5):
        rad = math.radians(i)
        points.extend([x2 - radius + radius * math.cos(rad), y1 + radius + radius * math.sin(rad)])
    for i in range(0, 90, 5):
        rad = math.radians(i)
        points.extend([x2 - radius + radius * math.cos(rad), y2 - radius + radius * math.sin(rad)])
    for i in range(90, 180, 5):
        rad = math.radians(i)
        points.extend([x1 + radius + radius * math.cos(rad), y2 - radius + radius * math.sin(rad)])
    return canvas.create_polygon(points, smooth=False, **kwargs)

class RoundedFrame(tk.Canvas):
    def __init__(self, parent, radius=15, bg_color=COLORS["BG_CARD"], border_color=COLORS["ACCENT"], border_width=2):
        super().__init__(parent, borderwidth=0, relief="flat", highlightthickness=0, bg=parent["bg"])
        self.radius = radius
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.inner_frame = tk.Frame(self, bg=bg_color)
        self.window_id = self.create_window(0, 0, window=self.inner_frame, anchor="nw")
        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        w, h = event.width, event.height
        self.delete("bg")
        draw_perfect_rounded_rect(self, 0, 0, w, h, self.radius, fill=self.bg_color, outline=self.border_color, width=self.border_width, tags="bg")
        self.tag_lower("bg")
        pad = 12
        self.itemconfigure(self.window_id, width=w-(2*pad), height=h-(2*pad))
        self.coords(self.window_id, pad, pad)

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text: str, command, width=280, height=36, radius=18, bg_color=COLORS["ACCENT"], text_color="white", state="normal"):
        super().__init__(parent, borderwidth=0, relief="flat", highlightthickness=0, bg=COLORS["BG_CARD"], width=width, height=height)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = COLORS["ACCENT_HOVER"] if bg_color == COLORS["ACCENT"] else "#E0E0E0"
        self.text_color = text_color
        self.state = state
        self.rect = draw_perfect_rounded_rect(self, 0, 0, width, height, radius, fill=bg_color, outline="")
        self.text = self.create_text(width/2, height/2, text=text, fill=text_color, font=("Helvetica", 9, "bold"))
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.set_state(state)

    def _on_click(self, event):
        if self.state == "normal": self.command()

    def _on_enter(self, event):
        if self.state == "normal": self.itemconfig(self.rect, fill=self.hover_color)

    def _on_leave(self, event):
        if self.state == "normal": self.itemconfig(self.rect, fill=self.bg_color)

    def set_state(self, state: str):
        self.state = state
        fill = "#E5E5E5" if state == "disabled" else self.bg_color
        text_fill = "#999999" if state == "disabled" else self.text_color
        self.itemconfig(self.rect, fill=fill)
        self.itemconfig(self.text, fill=text_fill)

    def config(self, state):
        self.set_state(state)

class StructDiffStudioApp:
    def __init__(self, root):
        self.root = root
        self._setup_window()
        self._init_variables()
        self._setup_ui()

    def _setup_window(self):
        self.root.title("StructDiff Studio")
        self.root.geometry("700x760")
        self.root.configure(bg=COLORS["BG_PAGE"])
        self.root.eval('tk::PlaceWindow . center')

    def _init_variables(self):
        self.path_left = ""
        self.type_left = ""
        self.path_right = ""
        self.type_right = ""

        self.left_files = []
        self.right_files = []
        self.left_dict = defaultdict(list)
        self.right_dict = defaultdict(list)
        self.common_prefixes = []

    def get_prefix(self, filename):
        return os.path.basename(filename).split('_')[0]

    def _get_primary_xml(self, files_list):
        for f in files_list:
            if f.lower().endswith('.xml'): return f
        return files_list[0] if files_list else ""

    def _setup_ui(self):
        self._create_header()
        self.card = RoundedFrame(self.root, radius=15, bg_color=COLORS["BG_CARD"])
        self.card.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        content = self.card.inner_frame

        self._create_path_selectors(content)
        self._create_listbox_area(content)
        self._create_action_buttons(content)
        self._create_footer()

    def _create_header(self):
        frame = tk.Frame(self.root, bg=COLORS["BG_PAGE"])
        frame.pack(fill="x", pady=(15, 10), padx=20)

        self.logo_lbl = tk.Label(frame, text="StructDiff Studio", font=FONT_HEAD, bg=COLORS["BG_PAGE"], fg=COLORS["WHITE"])
        self.logo_lbl.pack(side="left")
        tk.Label(frame, text="Structured File\nComparator", font=FONT_SUB,
                 bg=COLORS["BG_PAGE"], fg=COLORS["WHITE"], justify="right").pack(side="right")

    def _create_path_selectors(self, parent):
        f1 = tk.Frame(parent, bg=COLORS["BG_CARD"])
        f1.pack(fill="x", pady=(5, 5))
        tk.Label(f1, text="Version 1 (v1):", width=16, font=FONT_BOLD, bg=COLORS["BG_CARD"], fg=COLORS["TEXT_HEAD"], anchor="w").pack(side='left')
        RoundedButton(f1, "Open ZIP", lambda: self.load_path('left', 'zip'), width=80, height=24, radius=12, bg_color="#E8E8ED", text_color=COLORS["ACCENT"]).pack(side='left', padx=3)
        RoundedButton(f1, "Open Folder", lambda: self.load_path('left', 'folder'), width=80, height=24, radius=12, bg_color="#E8E8ED", text_color=COLORS["ACCENT"]).pack(side='left', padx=3)
        self.lbl_left = tk.Label(f1, text="Not Selected", font=FONT_SUB, bg=COLORS["BG_CARD"], fg=COLORS["TEXT_BODY"])
        self.lbl_left.pack(side='left', padx=10)

        f2 = tk.Frame(parent, bg=COLORS["BG_CARD"])
        f2.pack(fill="x", pady=(0, 10))
        tk.Label(f2, text="Version 2 (v2):", width=16, font=FONT_BOLD, bg=COLORS["BG_CARD"], fg=COLORS["TEXT_HEAD"], anchor="w").pack(side='left')
        RoundedButton(f2, "Open ZIP", lambda: self.load_path('right', 'zip'), width=80, height=24, radius=12, bg_color="#E8E8ED", text_color=COLORS["ACCENT"]).pack(side='left', padx=3)
        RoundedButton(f2, "Open Folder", lambda: self.load_path('right', 'folder'), width=80, height=24, radius=12, bg_color="#E8E8ED", text_color=COLORS["ACCENT"]).pack(side='left', padx=3)
        self.lbl_right = tk.Label(f2, text="Not Selected", font=FONT_SUB, bg=COLORS["BG_CARD"], fg=COLORS["TEXT_BODY"])
        self.lbl_right.pack(side='left', padx=10)

        tk.Frame(parent, height=1, bg=COLORS["BORDER"]).pack(fill="x", pady=(5, 10))

    def _create_listbox_area(self, parent):
        tk.Label(parent, text="Auto-Matched File Groups", font=FONT_BOLD, bg=COLORS["BG_CARD"], fg=COLORS["TEXT_HEAD"]).pack(anchor='w', pady=(0, 5))
        
        list_frame = tk.Frame(parent, bg=COLORS["BORDER"], padx=1, pady=1)
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        scroll = ttk.Scrollbar(list_frame, orient="vertical")
        scroll.pack(side='right', fill='y')
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Custom.Treeview", font=FONT_LIST, rowheight=24, background=COLORS["INPUT_BG"], fieldbackground=COLORS["INPUT_BG"])
        style.configure("Custom.Treeview.Heading", font=("Helvetica", 9, "bold"))
        style.map("Custom.Treeview", background=[('selected', COLORS["ACCENT"])], foreground=[('selected', COLORS["WHITE"])])

        self.tree = ttk.Treeview(list_frame, columns=("Group", "Status", "Counts"), show="headings", style="Custom.Treeview", yscrollcommand=scroll.set, selectmode="extended")
        
        self.tree.heading("Group", text="Target File / Group Name", anchor="w")
        self.tree.heading("Status", text="Status", anchor="center")
        self.tree.heading("Counts", text="File Version / Counts", anchor="e")

        self.tree.column("Group", width=320, anchor="w")
        self.tree.column("Status", width=130, anchor="center")
        self.tree.column("Counts", width=170, anchor="e")

        self.tree.pack(side='left', fill='both', expand=True)
        scroll.config(command=self.tree.yview)

        self.tree.tag_configure('ready', background=COLORS["INPUT_BG"], foreground=COLORS["TEXT_HEAD"])
        self.tree.tag_configure('analyzing', background='#FFF59D', foreground='black')
        self.tree.tag_configure('different', background='#C8E6C9', foreground='black')
        self.tree.tag_configure('identical', background='#EEEEEE', foreground='#9E9E9E')

    def _create_action_buttons(self, parent):
        btn_frame = tk.Frame(parent, bg=COLORS["BG_CARD"])
        btn_frame.pack(fill='x', pady=(10, 5))
        
        center_frame = tk.Frame(btn_frame, bg=COLORS["BG_CARD"])
        center_frame.pack(anchor="center")

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        self.btn_single = RoundedButton(center_frame, "Compare Selected Group(s)", self.execute_single_comparison, 
                                        width=280, height=36, radius=18, bg_color=COLORS["ACCENT"])
        self.btn_single.grid(row=0, column=0, sticky="e", padx=(0, 12))
                  
        self.btn_batch = RoundedButton(center_frame, "Batch Compare All Groups", self.execute_batch_comparison, 
                                       width=280, height=36, radius=18, bg_color=COLORS["SUCCESS"])
        self.btn_batch.grid(row=0, column=1, sticky="w", padx=(12, 0))

    def _create_footer(self):
        footer_frame = tk.Frame(self.root, bg=COLORS["BG_PAGE"])
        footer_frame.pack(side="bottom", pady=(6, 12))
        try:
            self.footer_logo_img = tk.PhotoImage(file=app_resource_path(FOOTER_LOGO_RELATIVE_PATH))
            tk.Label(
                footer_frame,
                image=self.footer_logo_img,
                bg=COLORS["BG_PAGE"],
                borderwidth=0,
                highlightthickness=0
            ).pack()
        except Exception:
            tk.Label(
                footer_frame,
                text="CODE by NOAH",
                bg=COLORS["BG_PAGE"],
                fg=COLORS["WHITE"],
                font=("Helvetica", 10, "bold")
            ).pack()

    def _get_xml_version(self, base_path, base_type, file_name) -> str:
        is_html = file_name.lower().endswith(('.html', '.htm'))
        if is_html: return ""
        try:
            if base_type == 'zip':
                with zipfile.ZipFile(base_path, 'r') as z:
                    with z.open(file_name, 'r') as f:
                        context = etree.iterparse(f, events=('end',))
                        for event, elem in context:
                            if elem.tag.split('}')[-1] == "DocumentTypeVersion":
                                version = elem.text.strip() if elem.text else "unknown"
                                elem.clear(); return version
                            elem.clear()
            else:
                file_path = os.path.join(base_path, file_name)
                with open(file_path, 'rb') as f:
                    context = etree.iterparse(f, events=('end',))
                    for event, elem in context:
                        if elem.tag.split('}')[-1] == "DocumentTypeVersion":
                            version = elem.text.strip() if elem.text else "unknown"
                            elem.clear(); return version
                        elem.clear()
        except Exception: pass
        return ""

    def load_path(self, side, load_type):
        path = filedialog.askopenfilename(filetypes=[("ZIP Files", "*.zip")]) if load_type == 'zip' else filedialog.askdirectory()
        if not path: return

        files = []
        try:
            if load_type == 'zip':
                with zipfile.ZipFile(path, 'r') as z:
                    files = [f for f in z.namelist() if not f.endswith('/') and f.lower().endswith(('.xml', '.html', '.htm'))]
            else:
                for root_dir, _, filenames in os.walk(path):
                    for f in filenames:
                        if f.lower().endswith(('.xml', '.html', '.htm')):
                            rel_path = os.path.relpath(os.path.join(root_dir, f), path)
                            files.append(rel_path.replace('\\', '/'))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load path:\n{e}")
            return

        disp_name = os.path.basename(path)
        if len(disp_name) > 30: disp_name = disp_name[:27] + "..."

        if side == 'left':
            self.path_left, self.type_left, self.left_files = path, load_type, files
            self.lbl_left.config(text=disp_name, fg=COLORS["TEXT_HEAD"])
        else:
            self.path_right, self.type_right, self.right_files = path, load_type, files
            self.lbl_right.config(text=disp_name, fg=COLORS["TEXT_HEAD"])

        self.update_match_list()

    def update_match_list(self):
        if not self.left_files or not self.right_files: return
        self.left_dict.clear()
        self.right_dict.clear()

        for f in self.left_files: self.left_dict[self.get_prefix(f)].append(f)
        for f in self.right_files: self.right_dict[self.get_prefix(f)].append(f)

        common = sorted(set(self.left_dict.keys()) & set(self.right_dict.keys()))
        self.common_prefixes = common

        self.tree.delete(*self.tree.get_children())
        for i, prefix in enumerate(common):
            self.left_dict[prefix].sort()
            self.right_dict[prefix].sort()
            l_count = len(self.left_dict[prefix])
            r_count = len(self.right_dict[prefix])
            
            all_group_files = self.left_dict[prefix] + self.right_dict[prefix]
            exts = sorted(list(set(os.path.splitext(f)[1][1:].lower() for f in all_group_files)))
            ext_str = ", ".join(exts)
            
            sample_l = self._get_primary_xml(self.left_dict[prefix])
            sample_r = self._get_primary_xml(self.right_dict[prefix])
            v1_str = self._get_xml_version(self.path_left, self.type_left, sample_l) or "v1"
            v2_str = self._get_xml_version(self.path_right, self.type_right, sample_r) or "v2"
            
            self.tree.insert("", "end", iid=str(i), 
                             values=(f"[{prefix}][{ext_str}]", "⏳ [Ready]", f"({v1_str}: {l_count} | {v2_str}: {r_count})"), 
                             tags=('ready',))

    # 💡 [Regex Pre-Processor] Masks volatile strings like dynamic URLs to prevent false positives in diff output
    def _normalize_text(self, text):
        if not text:
            return text
        # Overrides http:// and https:// URLs (including IPs and ports) with a generic placeholder
        return URL_PATTERN.sub('[IGNORED_URI]', text)

    def _safe_report_name(self, value, max_len=120):
        safe = INVALID_WINDOWS_FILENAME_CHARS.sub('_', value).strip(' .')
        return safe[:max_len] or "report"

    def _log_timing(self, label, start_time):
        elapsed = time.perf_counter() - start_time
        print(f"[TIMING] {label}: {elapsed:.3f}s")

    @contextmanager
    def _open_binary_source(self, base_path, base_type, file_name):
        if base_type == 'zip':
            with zipfile.ZipFile(base_path, 'r') as z:
                with z.open(file_name, 'r') as f:
                    yield f
        else:
            with open(os.path.join(base_path, file_name), 'rb') as f:
                yield f

    def _raw_file_size(self, base_path, base_type, file_name):
        if base_type == 'zip':
            with zipfile.ZipFile(base_path, 'r') as z:
                return z.getinfo(file_name).file_size
        return os.path.getsize(os.path.join(base_path, file_name))

    def _raw_file_hash(self, base_path, base_type, file_name):
        digest = hashlib.blake2b(digest_size=16)
        with self._open_binary_source(base_path, base_type, file_name) as f:
            while True:
                chunk = f.read(HASH_CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.digest()

    def raw_files_are_identical(self, left_file, right_file):
        try:
            left_size = self._raw_file_size(self.path_left, self.type_left, left_file)
            right_size = self._raw_file_size(self.path_right, self.type_right, right_file)
            if left_size != right_size:
                return False
            return (
                self._raw_file_hash(self.path_left, self.type_left, left_file)
                == self._raw_file_hash(self.path_right, self.type_right, right_file)
            )
        except Exception as e:
            print(f"[{left_file} vs {right_file}] Raw fast-path skipped: {e}")
            return False

    def _structural_hash(self, base_path, base_type, file_name):
        digest = hashlib.blake2b(digest_size=16)

        def update_hash(line):
            digest.update(line.encode('utf-8', errors='ignore'))
            digest.update(b'\n')

        with self._open_binary_source(base_path, base_type, file_name) as f:
            self._process_xml_stream(f, update_hash, file_name)
        return digest.digest()

    def structurally_identical_by_hash(self, left_file, right_file):
        if not STRUCTURAL_HASH_PREFLIGHT:
            return False
        try:
            return (
                self._structural_hash(self.path_left, self.type_left, left_file)
                == self._structural_hash(self.path_right, self.type_right, right_file)
            )
        except Exception as e:
            print(f"[{left_file} vs {right_file}] Structural hash skipped: {e}")
            return False

    def _native_diff_command(self, left_path, right_path):
        if os.name == 'nt':
            windows_diff = app_resource_path(WINDOWS_DIFF_RELATIVE_PATH)
            if os.path.exists(windows_diff):
                return [windows_diff, '-U', '3', left_path, right_path]
            return None

        system_diff = shutil.which('diff')
        if system_diff:
            return [system_diff, '-U', '3', left_path, right_path]
        return None

    def _subprocess_run_kwargs(self):
        if os.name != 'nt':
            return {}
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}

    def _unified_diff_lines(self, left_lines, right_lines, file_left, file_right):
        if USE_NATIVE_DIFF_ENGINE:
            t1 = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', newline='\n')
            t2 = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', newline='\n')
            try:
                t1.write("\n".join(left_lines))
                t1.write("\n")
                t1.close()
                t2.write("\n".join(right_lines))
                t2.write("\n")
                t2.close()

                cmd = self._native_diff_command(t1.name, t2.name)
                if cmd:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='ignore',
                        **self._subprocess_run_kwargs()
                    )
                    if result.stdout:
                        return result.stdout.splitlines()
                    if result.returncode in (0, 1):
                        return []
            except Exception as e:
                print(f"[{file_left} vs {file_right}] Native diff fallback: {e}")
            finally:
                if os.path.exists(t1.name):
                    os.remove(t1.name)
                if os.path.exists(t2.name):
                    os.remove(t2.name)

        return difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile=file_left,
            tofile=file_right,
            n=3,
            lineterm=''
        )

    def stream_xml_to_memory_lines(self, base_path, base_type, file_name):
        lines = []
        try:
            with self._open_binary_source(base_path, base_type, file_name) as f:
                self._process_xml_stream(f, lines.append, file_name)
            
            return lines
        except Exception as e:
            print(f"[{file_name}] Memory stream parsing failed: {e}")
            if base_type == 'zip':
                with zipfile.ZipFile(base_path, 'r') as z, z.open(file_name, 'r') as f:
                    return io.TextIOWrapper(f, encoding='utf-8', errors='ignore').read().splitlines()
            else:
                with open(os.path.join(base_path, file_name), 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read().splitlines()

    def _process_xml_stream(self, file_pointer, line_sink, file_name):
        is_html = file_name.lower().endswith(('.html', '.htm'))
        context = etree.iterparse(file_pointer, events=('start', 'end'), recover=True, html=is_html)
        depth = 0
        tag_counts = [{}] 

        for event, elem in context:
            tag_name = elem.tag.split('}')[-1]
            if event == 'start':
                counts = tag_counts[-1]
                counts[tag_name] = counts.get(tag_name, 0) + 1
                idx = counts[tag_name]
                tag_counts.append({}) 
                indent = "  " * depth
                
                # Apply normalization masking to all attribute values
                attrib_list = []
                for k, v in elem.attrib.items():
                    masked_v = self._normalize_text(v)
                    attrib_list.append(f' {k}="{masked_v}"')
                attribs = "".join(attrib_list)
                
                line_sink(f"{indent}<{tag_name}[{idx}]{attribs}>")
                depth += 1
            elif event == 'end':
                depth -= 1
                tag_counts.pop() 
                idx = tag_counts[-1][tag_name]
                indent = "  " * depth
                
                # Apply normalization masking to internal node text
                if elem.text and elem.text.strip():
                    masked_text = self._normalize_text(elem.text.strip())
                    line_sink(f"{indent}  {masked_text}  ")
                    
                line_sink(f"{indent}</{tag_name}[{idx}]>")
                elem.clear()
                if elem.getparent() is not None:
                    while elem.getprevious() is not None: 
                        del elem.getparent()[0]

    def split_memory_lines_to_bytes_chunks(self, lines, max_bytes=20971520):
        chunks = []
        current_chunk = []
        current_bytes = 0
        
        for line in lines:
            line_bytes = len(line.encode('utf-8')) + 1
            if current_bytes + line_bytes > max_bytes and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [line]
                current_bytes = line_bytes
            else:
                current_chunk.append(line)
                current_bytes += line_bytes
                
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def parse_diff_to_side_by_side_html(self, diff_text, file_left, file_right, v1_label, v2_label):
        lines = diff_text.splitlines() if isinstance(diff_text, str) else diff_text
        table_html = []
        table_html.append("<table class='diff'>")
        table_html.append("<colgroup><col style='width: 60px;'><col><col style='width: 60px;'><col></colgroup>")
        table_html.append(f"<tr><th colspan='2'>{v1_label.upper()}: {file_left}</th><th colspan='2'>{v2_label.upper()}: {file_right}</th></tr>")
        
        i = 0
        old_line_num = 1
        new_line_num = 1
        
        while i < len(lines):
            line = lines[i]
            if line.startswith('---') or line.startswith('+++'):
                i += 1; continue
            elif line.startswith('@@'):
                try:
                    parts = line.split()
                    if len(parts) >= 3:
                        old_part = parts[1][1:].split(',')
                        new_part = parts[2][1:].split(',')
                        old_line_num = int(old_part[0])
                        new_line_num = int(new_part[0])
                except Exception: pass
                table_html.append(f"<tr class='info'><td colspan='4'>{py_html.escape(line)}</td></tr>")
                i += 1; continue
                
            deletes, adds = [], []
            while i < len(lines) and (lines[i].startswith('-') or lines[i].startswith('+')):
                if lines[i].startswith('-'): deletes.append(lines[i][1:])
                elif lines[i].startswith('+'): adds.append(lines[i][1:])
                i += 1
                
            if deletes or adds:
                for k in range(max(len(deletes), len(adds))):
                    table_html.append("<tr>")
                    if k < len(deletes):
                        table_html.append(f"<td class='num'>{old_line_num}</td><td class='del'>{py_html.escape(deletes[k])}</td>")
                        old_line_num += 1
                    else: table_html.append("<td class='num'></td><td></td>")
                        
                    if k < len(adds):
                        table_html.append(f"<td class='num'>{new_line_num}</td><td class='add'>{py_html.escape(adds[k])}</td>")
                        new_line_num += 1
                    else: table_html.append("<td class='num'></td><td></td>")
                    table_html.append("</tr>")
                continue
                
            if line.startswith(' '):
                txt = line[1:]
                table_html.append(f"<tr><td class='num'>{old_line_num}</td><td>{py_html.escape(txt)}</td><td class='num'>{new_line_num}</td><td>{py_html.escape(txt)}</td></tr>")
                old_line_num += 1; new_line_num += 1; i += 1
            else: i += 1
                
        table_html.append("</table><br>")
        return "".join(table_html)

    def write_side_by_side_diff_table(self, out, diff_lines, file_left, file_right, v1_label, v2_label):
        out.write("<table class='diff'>")
        out.write("<colgroup><col style='width: 60px;'><col><col style='width: 60px;'><col></colgroup>")
        out.write(f"<tr><th colspan='2'>{py_html.escape(v1_label.upper())}: {py_html.escape(file_left)}</th><th colspan='2'>{py_html.escape(v2_label.upper())}: {py_html.escape(file_right)}</th></tr>")

        lines = iter(diff_lines)
        old_line_num = 1
        new_line_num = 1
        pending = None

        while True:
            if pending is not None:
                line = pending
                pending = None
            else:
                try:
                    line = next(lines)
                except StopIteration:
                    break

            if line.startswith('---') or line.startswith('+++'):
                continue

            if line.startswith('@@'):
                try:
                    parts = line.split()
                    if len(parts) >= 3:
                        old_line_num = int(parts[1][1:].split(',')[0])
                        new_line_num = int(parts[2][1:].split(',')[0])
                except Exception:
                    pass
                out.write(f"<tr class='info'><td colspan='4'>{py_html.escape(line)}</td></tr>")
                continue

            deletes, adds = [], []
            while line.startswith('-') or line.startswith('+'):
                if line.startswith('-'):
                    deletes.append(line[1:])
                else:
                    adds.append(line[1:])
                try:
                    line = next(lines)
                except StopIteration:
                    line = None
                    break

            if deletes or adds:
                for k in range(max(len(deletes), len(adds))):
                    out.write("<tr>")
                    if k < len(deletes):
                        out.write(f"<td class='num'>{old_line_num}</td><td class='del'>{py_html.escape(deletes[k])}</td>")
                        old_line_num += 1
                    else:
                        out.write("<td class='num'></td><td></td>")

                    if k < len(adds):
                        out.write(f"<td class='num'>{new_line_num}</td><td class='add'>{py_html.escape(adds[k])}</td>")
                        new_line_num += 1
                    else:
                        out.write("<td class='num'></td><td></td>")
                    out.write("</tr>")

                if line is not None:
                    pending = line
                continue

            if line.startswith(' '):
                txt = line[1:]
                escaped = py_html.escape(txt)
                out.write(f"<tr><td class='num'>{old_line_num}</td><td>{escaped}</td><td class='num'>{new_line_num}</td><td>{escaped}</td></tr>")
                old_line_num += 1
                new_line_num += 1

        out.write("</table><br>")

    def write_part_html_report(self, report_path, diff_lines, file_left, file_right, v1_label, v2_label, title):
        with open(report_path, 'w', encoding='utf-8') as out:
            out.write(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{py_html.escape(title)}</title>
            <style type="text/css">
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #fafafa; padding-bottom: 60px; }}
                h2 {{ color: #0056b3; margin-top: 10px; font-size: 15px; background: #e9ecef; padding: 8px; border-radius: 4px; }}
                table.diff {{ font-family: Consolas, monospace; border: 1px solid #ddd; width: 100%; border-collapse: collapse; font-size: 12px; background: #fff; table-layout: fixed; }}
                th {{ background-color: #f1f3f5; padding: 6px; border: 1px solid #dee2e6; text-align: left; font-size: 13px; }}
                td {{ padding: 2px 6px; border-right: 1px solid #f1f3f5; word-break: break-all; white-space: pre-wrap; }}
                td.num {{ text-align: right; background: #f8f9fa; color: #adb5bd; border-right: 1px solid #ced4da; user-select: none; font-size: 11px; }}
                td.del {{ background-color: #ffeef0; color: #b31412; }}
                td.add {{ background-color: #e6ffed; color: #22863a; }}
                tr.info td {{ background-color: #f1f8ff; color: #0366d6; padding: 4px 10px; font-style: italic; border-top: 1px solid #dbedff; border-bottom: 1px solid #dbedff; }}
                .floating-creator-badge {{ position: fixed; bottom: 20px; right: 20px; background-color: rgba(29, 29, 31, 0.75); color: #ffffff; padding: 8px 16px; border-radius: 20px; font-size: 11px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.15); backdrop-filter: blur(4px); cursor: pointer; user-select: none; transition: all 0.2s ease-in-out; z-index: 9999; }}
                .floating-creator-badge:hover {{ background-color: rgba(0, 113, 227, 0.95); transform: translateY(-2px); }}
            </style>
        </head>
        <body>
            <h2>Segment Slice View: {py_html.escape(title)}</h2>
            """)
            self.write_side_by_side_diff_table(out, diff_lines, file_left, file_right, v1_label, v2_label)
            out.write("""
            <div class="floating-creator-badge">
                StructDiff Studio
            </div>
        </body>
        </html>
        """)

    def write_index_dashboard(self, target_dir, prefix, results_meta, current_time, v1_str, v2_str):
        rows_html = []
        for meta in results_meta:
            status_cls = "status-diff" if meta["has_diff"] else "status-same"
            status_txt = "Differences Detected" if meta["has_diff"] else "Identical Structure"
            
            rows_html.append(f"""
            <tr>
                <td>{meta['pair']}</td>
                <td><span class='badge {status_cls}'>{status_txt}</span></td>
                <td><a class='view-link' href='{meta['file']}' target='_blank'>Open Part Report &rarr;</a></td>
            </tr>
            """)

        index_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Master Dashboard: {prefix}</title>
            <style type="text/css">
                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #fafafa; padding-bottom: 60px; }}
                h1 {{ color: #1d1d1f; margin-bottom: 2px; }}
                .report-metadata {{ font-size: 11px; color: #ffffff; margin-bottom: 25px; padding: 6px 10px; background-color: rgba(29, 29, 31, 0.75); border-radius: 4px; }}
                table.dashboard {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow: hidden; }}
                th {{ background-color: #f1f3f5; padding: 12px; border-bottom: 2px solid #dee2e6; text-align: left; font-size: 13px; color: #495057; }}
                td {{ padding: 12px; border-bottom: 1px solid #f1f3f5; font-size: 13px; color: #212529; }}
                .badge {{ padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }}
                .status-diff {{ background-color: #ffeef0; color: #b31412; }}
                .status-same {{ background-color: #e6ffed; color: #22863a; }}
                .view-link {{ color: #0071E3; text-decoration: none; font-weight: bold; }}
                .view-link:hover {{ text-decoration: underline; }}
                .floating-creator-badge {{ position: fixed; bottom: 20px; right: 20px; background-color: rgba(29, 29, 31, 0.75); color: #ffffff; padding: 8px 16px; border-radius: 20px; font-size: 11px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.15); backdrop-filter: blur(4px); cursor: pointer; user-select: none; transition: all 0.2s ease-in-out; z-index: 9999; }}
                .floating-creator-badge:hover {{ background-color: rgba(0, 113, 227, 0.95); transform: translateY(-2px); }}
            </style>
        </head>
        <body>
            <h1>StructDiff Dashboard: {prefix}</h1>
            <div class="report-metadata">
                StructDiff Studio | Generated on {current_time} | Target: {v1_str} vs {v2_str}
            </div>
            <table class="dashboard">
                <thead>
                    <tr>
                        <th>Split Segment Reference Pair</th>
                        <th>Structural Verification Status</th>
                        <th>Action Link</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows_html)}
                </tbody>
            </table>
            <div class="floating-creator-badge">
                StructDiff Studio
            </div>
        </body>
        </html>
        """
        with open(os.path.join(target_dir, "index.html"), "w", encoding="utf-8") as idx_f:
            idx_f.write(index_html)

    def build_part_html_body(self, diff_content, title):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{title}</title>
            <style type="text/css">
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #fafafa; padding-bottom: 60px; }}
                h2 {{ color: #0056b3; margin-top: 10px; font-size: 15px; background: #e9ecef; padding: 8px; border-radius: 4px; }}
                table.diff {{ font-family: Consolas, monospace; border: 1px solid #ddd; width: 100%; border-collapse: collapse; font-size: 12px; background: #fff; table-layout: fixed; }}
                th {{ background-color: #f1f3f5; padding: 6px; border: 1px solid #dee2e6; text-align: left; font-size: 13px; }}
                td {{ padding: 2px 6px; border-right: 1px solid #f1f3f5; word-break: break-all; white-space: pre-wrap; }}
                td.num {{ text-align: right; background: #f8f9fa; color: #adb5bd; border-right: 1px solid #ced4da; user-select: none; font-size: 11px; }}
                td.del {{ background-color: #ffeef0; color: #b31412; }}
                td.add {{ background-color: #e6ffed; color: #22863a; }}
                tr.info td {{ background-color: #f1f8ff; color: #0366d6; padding: 4px 10px; font-style: italic; border-top: 1px solid #dbedff; border-bottom: 1px solid #dbedff; }}
                .floating-creator-badge {{ position: fixed; bottom: 20px; right: 20px; background-color: rgba(29, 29, 31, 0.75); color: #ffffff; padding: 8px 16px; border-radius: 20px; font-size: 11px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.15); backdrop-filter: blur(4px); cursor: pointer; user-select: none; transition: all 0.2s ease-in-out; z-index: 9999; }}
                .floating-creator-badge:hover {{ background-color: rgba(0, 113, 227, 0.95); transform: translateY(-2px); }}
            </style>
        </head>
        <body>
            <h2>Segment Slice View: {title}</h2>
            {diff_content}
            <div class="floating-creator-badge">
                StructDiff Studio
            </div>
        </body>
        </html>
        """

    def _process_selected_items_thread(self, selected_iids, output_dir, mode="single"):
        diff_count = 0
        total_items = len(selected_iids)
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for idx_str in selected_iids:
            idx = int(idx_str)
            prefix = self.common_prefixes[idx]
            l_count = len(self.left_dict[prefix])
            r_count = len(self.right_dict[prefix])
            
            all_group_files = self.left_dict[prefix] + self.right_dict[prefix]
            exts = sorted(list(set(os.path.splitext(f)[1][1:].lower() for f in all_group_files)))
            disp_name = f"[{prefix}][{', '.join(exts)}]"
            
            sample_l = self._get_primary_xml(self.left_dict[prefix])
            sample_r = self._get_primary_xml(self.right_dict[prefix])
            v1_str = self._get_xml_version(self.path_left, self.type_left, sample_l) or "v1"
            v2_str = self._get_xml_version(self.path_right, self.type_right, sample_r) or "v2"
            
            group_folder_path = os.path.join(output_dir, f"DiffReport_{self._safe_report_name(prefix)}")

            results_meta_collection = []
            has_any_structural_mismatch = False

            def update_ui_split(i=idx_str, name=disp_name):
                self.tree.item(i, values=(name, "✂️ Splitting...", f"({v1_str}: {l_count} | {v2_str}: {r_count})"), tags=('analyzing',))
            self.root.after(0, update_ui_split)

            for f_left, f_right in zip(self.left_dict[prefix], self.right_dict[prefix]):
                pair_start = time.perf_counter()
                if self.raw_files_are_identical(f_left, f_right):
                    results_meta_collection.append({
                        "pair": f"{f_left} ➔ {f_right} (Exact Match)",
                        "has_diff": False,
                        "file": "index.html"
                    })
                    self._log_timing(f"{f_left} vs {f_right} exact raw match", pair_start)
                    continue

                hash_start = time.perf_counter()
                if self.structurally_identical_by_hash(f_left, f_right):
                    results_meta_collection.append({
                        "pair": f"{f_left} ➔ {f_right} (Structural Hash Match)",
                        "has_diff": False,
                        "file": "index.html"
                    })
                    self._log_timing(f"{f_left} vs {f_right} structural hash", hash_start)
                    self._log_timing(f"{f_left} vs {f_right} total", pair_start)
                    continue

                parse_start = time.perf_counter()
                lines1 = self.stream_xml_to_memory_lines(self.path_left, self.type_left, f_left)
                lines2 = self.stream_xml_to_memory_lines(self.path_right, self.type_right, f_right)
                self._log_timing(f"{f_left} vs {f_right} parse to lines", parse_start)

                if lines1 == lines2:
                    results_meta_collection.append({
                        "pair": f"{f_left} ➔ {f_right} (Structural Match)",
                        "has_diff": False,
                        "file": "index.html"
                    })
                    self._log_timing(f"{f_left} vs {f_right} total", pair_start)
                    continue

                chunks1 = self.split_memory_lines_to_bytes_chunks(lines1, max_bytes=20971520)
                chunks2 = self.split_memory_lines_to_bytes_chunks(lines2, max_bytes=20971520)
                max_chunks = max(len(chunks1), len(chunks2))

                for chunk_idx in range(max_chunks):
                    status_text = f"⚡ Diffing ({chunk_idx+1}/{max_chunks})..."
                    def update_ui_diff(i=idx_str, name=disp_name, st=status_text):
                        self.tree.item(i, values=(name, st, f"({v1_str}: {l_count} | {v2_str}: {r_count})"), tags=('analyzing',))
                    self.root.after(0, update_ui_diff)

                    c1_lines = chunks1[chunk_idx] if chunk_idx < len(chunks1) else []
                    c2_lines = chunks2[chunk_idx] if chunk_idx < len(chunks2) else []

                    if c1_lines == c2_lines:
                        results_meta_collection.append({
                            "pair": f"{f_left} ➔ {f_right} (Part {chunk_idx+1})",
                            "has_diff": False,
                            "file": "index.html"
                        })
                        continue

                    diff_start = time.perf_counter()
                    diff_iter = iter(self._unified_diff_lines(
                        c1_lines,
                        c2_lines,
                        f_left,
                        f_right
                    ))
                    first_diff_line = next(diff_iter, None)
                    self._log_timing(f"{f_left} vs {f_right} part {chunk_idx+1} diff", diff_start)

                    if first_diff_line is not None:
                        if not has_any_structural_mismatch:
                            os.makedirs(group_folder_path, exist_ok=True)
                            has_any_structural_mismatch = True

                        filename_base = self._safe_report_name(f_left.replace('/', '_'))
                        filename_part = f"DiffReport_{filename_base}_part{chunk_idx+1}.html"
                        report_path = os.path.join(group_folder_path, filename_part)
                        full_diff_iter = itertools.chain([first_diff_line], diff_iter)
                        report_start = time.perf_counter()
                        self.write_part_html_report(
                            report_path,
                            full_diff_iter,
                            f_left,
                            f_right,
                            v1_str,
                            v2_str,
                            f"{f_left} (Part {chunk_idx+1})"
                        )
                        self._log_timing(f"{f_left} vs {f_right} part {chunk_idx+1} report", report_start)

                        results_meta_collection.append({
                            "pair": f"{f_left} ➔ {f_right} (Part {chunk_idx+1})",
                            "has_diff": True,
                            "file": filename_part
                        })
                self._log_timing(f"{f_left} vs {f_right} total", pair_start)

            if has_any_structural_mismatch:
                diff_count += 1
                def update_ui_index(i=idx_str, name=disp_name):
                    self.tree.item(i, values=(name, "✍️ Indexing...", f"({v1_str}: {l_count} | {v2_str}: {r_count})"), tags=('analyzing',))
                self.root.after(0, update_ui_index)

                self.write_index_dashboard(group_folder_path, prefix, results_meta_collection, current_time_str, v1_str, v2_str)

                def update_ui_success(i=idx_str, name=disp_name):
                    self.tree.item(i, values=(name, "✅ [Different]", f"({v1_str}: {l_count} | {v2_str}: {r_count})"), tags=('different',))
                self.root.after(0, update_ui_success)
            else:
                def update_ui_nodiff(i=idx_str, name=disp_name):
                    self.tree.item(i, values=(name, "➖ [Identical]", f"({v1_str}: {l_count} | {v2_str}: {r_count})"), tags=('identical',))
                self.root.after(0, update_ui_nodiff)

        def finish_work():
            msg = f"✅ Completed {total_items} group comparisons!\n\nMismatched folders generated inside target path:\n{output_dir}"
            messagebox.showinfo("Complete", msg)
            self.btn_single.config("normal")
            self.btn_batch.config("normal")
            
        self.root.after(0, finish_work)

    def execute_single_comparison(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select group(s) from the list first.")
            return
        output_dir = filedialog.askdirectory(title=f"Select target container directory to generate reports")
        if not output_dir: return
        self.btn_single.config("disabled")
        self.btn_batch.config("disabled")
        threading.Thread(target=self._process_selected_items_thread, args=(selection, output_dir, "single"), daemon=True).start()

    def execute_batch_comparison(self):
        if not self.common_prefixes:
            messagebox.showwarning("Warning", "No items to compare.")
            return
        output_dir = filedialog.askdirectory(title="Select target container directory to generate batch reports")
        if not output_dir: return 
        self.btn_single.config("disabled")
        self.btn_batch.config("disabled")
        all_iids = [str(i) for i in range(len(self.common_prefixes))]
        threading.Thread(target=self._process_selected_items_thread, args=(all_iids, output_dir, "batch"), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = StructDiffStudioApp(root)
    root.mainloop()
