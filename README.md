# StructDiff Studio

StructDiff Studio is a desktop comparator for structured files. The first release focuses on high-performance XML and HTML comparison with rule-based normalization, bundled native diff acceleration, and interactive HTML reports.

## Highlights

- Compare folders or ZIP archives containing XML, HTML, and HTM files.
- Normalize noisy values such as generated URLs before diffing.
- Skip identical files with raw hash preflight.
- Skip structurally equivalent files with normalized structural hash preflight.
- Use a bundled `diff.exe` on Windows for faster reports, with Python `difflib` fallback.
- Generate side-by-side HTML reports and a dashboard for changed groups.

## Project Direction

This project is designed as a portfolio-ready foundation for a broader structured comparison product:

- XML/HTML today
- JSON/YAML/CSV parsers next
- Rule builder for ignored paths, attributes, timestamps, GUIDs, and URLs
- CLI mode for automation
- Export formats such as CSV, JSON summary, and Markdown
- Tree-based diff visualization

## Run Locally

```bash
python src/structdiff_studio.py
```

Install dependencies first:

```bash
pip install -r requirements.txt
```

## Windows Native Diff Bundle

For the fastest Windows build, place these files in `tools/`:

```text
tools/diff.exe
tools/msys-2.0.dll
```

If `diff.exe` is missing, StructDiff Studio automatically falls back to Python's built-in `difflib`.

## Build Windows EXE

Run this from the project root on Windows:

```bat
build_windows_exe.bat
```

The executable will be created at:

```text
dist\StructDiffStudio.exe
```

## Demo

Use `samples/v1` and `samples/v2` as the two folders in the app. They include a small XML change that produces a side-by-side HTML report.

## Author

Built by Noah Nam.

- GitHub: [@sanghoo83](https://github.com/sanghoo83)
- Email: n83.noah@gmail.com
