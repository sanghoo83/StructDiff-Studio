"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.2.0
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

