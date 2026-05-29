# Platform Support

StructDiff Studio is organized as a cross-platform Python desktop app with platform-specific native diff acceleration.

## Windows

- Preferred engine: bundled `tools/windows/diff.exe`
- Runtime dependency: `tools/windows/msys-2.0.dll`
- Fallback: Python `difflib`
- Build script: `scripts/build_windows_exe.bat`

## macOS

- Preferred engine: system `diff`
- Fallback: Python `difflib`
- Build script: `scripts/build_macos.sh`

## Linux

- Planned packaging target
- Preferred engine: system `diff`
- Fallback: Python `difflib`

## Why One Repository?

The project keeps Windows, macOS, and future Linux support in one codebase so the comparison engine, normalization rules, report generator, and UI can evolve together.
