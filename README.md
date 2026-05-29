# StructDiff Studio

StructDiff Studio is a cross-platform desktop comparator for structured files. The first release focuses on high-performance XML and HTML comparison with rule-based normalization, native diff acceleration, and interactive HTML reports.

Current version: `0.5.0`

## What's New in 0.5.0

Version 0.5.0 focuses on safer document pairing for ZIP/folder comparisons. Earlier builds could treat files with the same logical group prefix as comparable even when their document IDs differed. That behavior was risky for report accuracy because unrelated split segments could be compared and produce misleading differences.

- Added explicit file pairing modes in the UI.
- Exact matching now uses the full basename/document ID instead of sorted group order.
- Unmatched files remain visible in the dashboard as `[missing in v1]` or `[missing in v2]`.
- Candidate mode can compare every unmatched v1 x v2 combination for manual review.
- Candidate reports include both source filenames to avoid report overwrite collisions.
- Added regression tests for document ID pairing and unmatched candidate generation.

See `CHANGELOG.md` for the 0.5.0 vs 0.4.0 change history.

## Highlights

- Compare folders or ZIP archives containing XML, HTML, and HTM files.
- Normalize noisy values such as generated URLs before diffing.
- Skip identical files with raw hash preflight.
- Skip structurally equivalent files with normalized structural hash preflight.
- Use native diff acceleration when available, with Python `difflib` fallback.
- Classify XML/HTML changes into XPath-style node, attribute, and text summaries.
- Ignore volatile tags, attributes, and text patterns such as timestamps, UUIDs, generated fields, and URLs.
- Pair files by exact document ID, with an optional unmatched-candidate review mode.
- Generate side-by-side HTML reports and a dashboard for changed groups.

## File Pairing Logic

StructDiff Studio groups related files by the portion before the first underscore, then pairs files inside each group using the selected mode.

| Mode | Behavior | Best for |
|---|---|---|
| `Same document ID only` | Compares only files whose full basename matches on both sides. Files found on only one side are reported as missing. | Normal regression checks where document IDs should be stable |
| `Same ID + all unmatched candidates` | Keeps the exact matches and missing rows, then compares every remaining unmatched v1 file against every remaining unmatched v2 file. | Investigation cases where document IDs changed or split files may have been renamed |

Example:

```text
v1 unmatched: A.xml, B.xml
v2 unmatched: C.xml, D.xml
candidate comparisons: A-C, A-D, B-C, B-D
```

This prevents accidental one-by-one sorted pairing from hiding possible relationships between renamed or regenerated split documents.

## Platform Support

| Platform | Status | Diff Engine |
|---|---|---|
| Windows | Supported | Bundled `tools/windows/diff.exe` or `difflib` fallback |
| macOS | Supported for source run and local build | System `diff` or `difflib` fallback |
| Linux | Planned | System `diff` or `difflib` fallback |

## Project Direction

This project is designed as a portfolio-ready foundation for a broader structured comparison product:

- XML/HTML today
- JSON/YAML/CSV parsers next
- Rule builder for ignored paths, attributes, timestamps, GUIDs, and URLs
- CLI mode for automation
- Export formats such as CSV, JSON summary, and Markdown
- Tree-based diff visualization

## Source Layout

```text
src/
  structdiff_studio.py      # Compatibility launcher
  structdiff/
    app.py                  # Tkinter application workflow
    config.py               # Shared constants and versioned settings
    engine.py               # XML normalization, hashing, and diff engine selection
    reports.py              # HTML report and dashboard generation
    resources.py            # Resource lookup for source and packaged builds
    widgets.py              # Reusable Tkinter UI widgets
    main.py                 # Application entry point
```

## Run Locally

```bash
python src/structdiff_studio.py
```

Install dependencies first:

```bash
pip install -r requirements.txt
```

## Native Diff Engines

For the fastest Windows build, place these files in `tools/windows/`:

```text
tools/windows/diff.exe
tools/windows/msys-2.0.dll
```

If `diff.exe` is missing, StructDiff Studio automatically falls back to Python's built-in `difflib`.

## Build Windows EXE

Run this from the project root on Windows:

```bat
scripts\build_windows_exe.bat
```

The executable will be created at:

```text
dist\StructDiffStudio.exe
```

## Build macOS App

Run this from the project root on macOS:

```bash
scripts/build_macos.sh
```

## Demo

Use `samples/v1` and `samples/v2` as the two folders in the app. They include a small XML change that produces a side-by-side HTML report.

## Author

Built by Noah Nam.

- GitHub: [@sanghoo83](https://github.com/sanghoo83)
- Email: n83.noah@gmail.com
