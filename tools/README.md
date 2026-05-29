# Native Diff Tools

This directory is intentionally kept free of bundled binaries in source control.

For a faster Windows build, place these files in `tools/windows/` before running `scripts/build_windows_exe.bat`:

```text
tools/windows/diff.exe
tools/windows/msys-2.0.dll
```

macOS and Linux use the system `diff` command when available. StructDiff Studio still works without native diff by falling back to Python's built-in `difflib`.
