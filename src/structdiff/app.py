"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.3.0
Purpose: Tkinter application shell and batch comparison workflow.
"""

import itertools
import os
import threading
import time
import zipfile
from collections import defaultdict
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from lxml import etree

from .config import (
    COLORS,
    FONT_BOLD,
    FONT_HEAD,
    FONT_LIST,
    FONT_SUB,
    FOOTER_LOGO_RELATIVE_PATH,
)
from .engine import CompareEngineMixin
from .reports import ReportWriterMixin
from .resources import app_resource_path
from .widgets import RoundedButton, RoundedFrame


class StructDiffStudioApp(CompareEngineMixin, ReportWriterMixin):
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

                summary_start = time.perf_counter()
                structural_summary = self.build_structural_change_summary(f_left, f_right)
                self._log_timing(f"{f_left} vs {f_right} structural summary", summary_start)

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
                            f"{f_left} (Part {chunk_idx+1})",
                            structural_summary if chunk_idx == 0 else None
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
