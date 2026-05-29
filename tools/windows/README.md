# Windows Native Diff

Place optional Windows native diff binaries here before building:

```text
tools/windows/diff.exe
tools/windows/msys-2.0.dll
```

These binaries are intentionally ignored by git. StructDiff Studio falls back to Python `difflib` when they are not present.
