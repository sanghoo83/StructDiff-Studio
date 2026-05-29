"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.3.0
Purpose: File loading, XML normalization, hashing, and diff engine selection.
"""

import difflib
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from contextlib import contextmanager

from lxml import etree

from .config import (
    HASH_CHUNK_SIZE,
    STRUCTURAL_HASH_PREFLIGHT,
    URL_PATTERN,
    USE_NATIVE_DIFF_ENGINE,
    WINDOWS_DIFF_RELATIVE_PATH,
    INVALID_WINDOWS_FILENAME_CHARS,
)
from .resources import app_resource_path


class CompareEngineMixin:
    def _local_tag_name(self, tag):
        return str(tag).split('}')[-1]

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

    def _collect_structural_records(self, base_path, base_type, file_name):
        nodes = set()
        attrs = {}
        texts = {}
        is_html = file_name.lower().endswith(('.html', '.htm'))

        with self._open_binary_source(base_path, base_type, file_name) as f:
            context = etree.iterparse(f, events=('start', 'end'), recover=True, html=is_html)
            path_stack = []
            sibling_counts_stack = [{}]

            for event, elem in context:
                tag_name = self._local_tag_name(elem.tag)
                if event == 'start':
                    counts = sibling_counts_stack[-1]
                    counts[tag_name] = counts.get(tag_name, 0) + 1
                    path = "/" + "/".join(path_stack + [f"{tag_name}[{counts[tag_name]}]"])
                    path_stack.append(f"{tag_name}[{counts[tag_name]}]")
                    sibling_counts_stack.append({})
                    nodes.add(path)

                    for attr_name, attr_value in sorted(elem.attrib.items()):
                        attrs[(path, attr_name)] = self._normalize_text(attr_value)

                elif event == 'end':
                    if path_stack:
                        path = "/" + "/".join(path_stack)
                        if elem.text and elem.text.strip():
                            texts[path] = self._normalize_text(elem.text.strip())
                        path_stack.pop()
                    if len(sibling_counts_stack) > 1:
                        sibling_counts_stack.pop()

                    elem.clear()
                    if elem.getparent() is not None:
                        while elem.getprevious() is not None:
                            del elem.getparent()[0]

        return {"nodes": nodes, "attrs": attrs, "texts": texts}

    def build_structural_change_summary(self, left_file, right_file, max_items=160):
        try:
            left = self._collect_structural_records(self.path_left, self.type_left, left_file)
            right = self._collect_structural_records(self.path_right, self.type_right, right_file)
        except Exception as e:
            print(f"[{left_file} vs {right_file}] Structural summary skipped: {e}")
            return {"available": False, "error": str(e), "items": [], "counts": {}}

        items = []

        def add_item(change_type, path, name="", left_value="", right_value=""):
            if len(items) < max_items:
                items.append({
                    "type": change_type,
                    "path": path,
                    "name": name,
                    "left": left_value,
                    "right": right_value,
                })

        left_nodes = left["nodes"]
        right_nodes = right["nodes"]
        left_attrs = left["attrs"]
        right_attrs = right["attrs"]
        left_texts = left["texts"]
        right_texts = right["texts"]

        removed_nodes = sorted(left_nodes - right_nodes)
        added_nodes = sorted(right_nodes - left_nodes)
        for path in removed_nodes:
            add_item("Node removed", path)
        for path in added_nodes:
            add_item("Node added", path)

        attr_keys = sorted(set(left_attrs) | set(right_attrs))
        attr_added = attr_removed = attr_changed = 0
        for key in attr_keys:
            path, attr_name = key
            in_left = key in left_attrs
            in_right = key in right_attrs
            if in_left and not in_right:
                attr_removed += 1
                add_item("Attribute removed", path, attr_name, left_attrs[key], "")
            elif in_right and not in_left:
                attr_added += 1
                add_item("Attribute added", path, attr_name, "", right_attrs[key])
            elif left_attrs[key] != right_attrs[key]:
                attr_changed += 1
                add_item("Attribute changed", path, attr_name, left_attrs[key], right_attrs[key])

        text_keys = sorted(set(left_texts) | set(right_texts))
        text_added = text_removed = text_changed = 0
        for path in text_keys:
            in_left = path in left_texts
            in_right = path in right_texts
            if in_left and not in_right:
                text_removed += 1
                add_item("Text removed", path, "", left_texts[path], "")
            elif in_right and not in_left:
                text_added += 1
                add_item("Text added", path, "", "", right_texts[path])
            elif left_texts[path] != right_texts[path]:
                text_changed += 1
                add_item("Text changed", path, "", left_texts[path], right_texts[path])

        counts = {
            "nodes_added": len(added_nodes),
            "nodes_removed": len(removed_nodes),
            "attrs_added": attr_added,
            "attrs_removed": attr_removed,
            "attrs_changed": attr_changed,
            "texts_added": text_added,
            "texts_removed": text_removed,
            "texts_changed": text_changed,
        }
        total = sum(counts.values())
        return {
            "available": True,
            "counts": counts,
            "items": items,
            "total": total,
            "truncated": total > len(items),
        }

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
