"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.3.0
Purpose: HTML dashboard and side-by-side report generation.
"""

import html as py_html
import os


class ReportWriterMixin:
    def write_structural_summary(self, out, summary):
        if not summary:
            return

        out.write("<section class='struct-summary'>")
        out.write("<h3>Structural Change Summary</h3>")

        if not summary.get("available", False):
            out.write(f"<p class='summary-error'>Summary unavailable: {py_html.escape(summary.get('error', 'unknown error'))}</p>")
            out.write("</section>")
            return

        counts = summary.get("counts", {})
        count_labels = [
            ("Nodes added", counts.get("nodes_added", 0)),
            ("Nodes removed", counts.get("nodes_removed", 0)),
            ("Attributes added", counts.get("attrs_added", 0)),
            ("Attributes removed", counts.get("attrs_removed", 0)),
            ("Attributes changed", counts.get("attrs_changed", 0)),
            ("Text added", counts.get("texts_added", 0)),
            ("Text removed", counts.get("texts_removed", 0)),
            ("Text changed", counts.get("texts_changed", 0)),
        ]
        out.write("<div class='summary-grid'>")
        for label, value in count_labels:
            out.write(f"<div class='summary-card'><span>{py_html.escape(label)}</span><strong>{value}</strong></div>")
        out.write("</div>")

        items = summary.get("items", [])
        if not items:
            out.write("<p class='summary-empty'>No node, attribute, or text-level changes were classified.</p>")
            out.write("</section>")
            return

        out.write("<table class='summary-table'>")
        out.write("<thead><tr><th>Type</th><th>Path</th><th>Name</th><th>v1</th><th>v2</th></tr></thead><tbody>")
        for item in items:
            out.write("<tr>")
            out.write(f"<td>{py_html.escape(item.get('type', ''))}</td>")
            out.write(f"<td class='path'>{py_html.escape(item.get('path', ''))}</td>")
            out.write(f"<td>{py_html.escape(item.get('name', ''))}</td>")
            out.write(f"<td>{py_html.escape(str(item.get('left', '')))}</td>")
            out.write(f"<td>{py_html.escape(str(item.get('right', '')))}</td>")
            out.write("</tr>")
        out.write("</tbody></table>")
        if summary.get("truncated"):
            out.write("<p class='summary-note'>Summary truncated. Open the line diff below for full context.</p>")
        out.write("</section>")

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

    def write_part_html_report(self, report_path, diff_lines, file_left, file_right, v1_label, v2_label, title, structural_summary=None):
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
                .struct-summary {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 14px; margin: 12px 0 18px; }}
                .struct-summary h3 {{ margin: 0 0 10px; font-size: 14px; color: #1d1d1f; }}
                .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 8px; margin-bottom: 12px; }}
                .summary-card {{ background: #f8f9fa; border: 1px solid #edf0f2; border-radius: 6px; padding: 8px; }}
                .summary-card span {{ display: block; color: #6c757d; font-size: 11px; }}
                .summary-card strong {{ display: block; color: #1d1d1f; font-size: 18px; margin-top: 2px; }}
                table.summary-table {{ width: 100%; border-collapse: collapse; font-size: 12px; table-layout: fixed; }}
                table.summary-table th {{ background: #f1f3f5; }}
                table.summary-table td {{ border: 1px solid #f1f3f5; vertical-align: top; }}
                table.summary-table td.path {{ color: #0056b3; font-family: Consolas, monospace; }}
                .summary-empty, .summary-note, .summary-error {{ color: #6c757d; font-size: 12px; margin: 8px 0 0; }}
                .floating-creator-badge {{ position: fixed; bottom: 20px; right: 20px; background-color: rgba(29, 29, 31, 0.75); color: #ffffff; padding: 8px 16px; border-radius: 20px; font-size: 11px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,0.15); backdrop-filter: blur(4px); cursor: pointer; user-select: none; transition: all 0.2s ease-in-out; z-index: 9999; }}
                .floating-creator-badge:hover {{ background-color: rgba(0, 113, 227, 0.95); transform: translateY(-2px); }}
            </style>
        </head>
        <body>
            <h2>Segment Slice View: {py_html.escape(title)}</h2>
            """)
            self.write_structural_summary(out, structural_summary)
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
