# Native Diff Tools

This directory is intentionally kept free of bundled binaries in source control.

For a faster Windows build, place these files here before running `build_windows_exe.bat`:

```text
tools/diff.exe
tools/msys-2.0.dll
```

StructDiff Studio still works without them by falling back to Python's built-in `difflib`.
