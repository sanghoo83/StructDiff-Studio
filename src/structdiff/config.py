"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.5.0
Purpose: Shared application constants and visual settings.
"""

import os
import re

COLORS = {
    "BG_PAGE": "#153B50",
    "BG_CARD": "#FFFFFF",
    "TEXT_HEAD": "#1D1D1F",
    "TEXT_BODY": "#86868B",
    "ACCENT": "#0071E3",
    "ACCENT_HOVER": "#0077ED",
    "INPUT_BG": "#F5F5F7",
    "BORDER": "#D2D2D7",
    "WHITE": "#FFFFFF",
    "ALERT": "#FF3B30",
    "SUCCESS": "#34C759",
    "WARNING": "#FF9F0A",
}

FONT_HEAD = ("Helvetica", 16, "bold")
FONT_SUB = ("Helvetica", 9)
FONT_BOLD = ("Helvetica", 10, "bold")
FONT_INPUT = ("Menlo", 10)
FONT_LIST = ("Menlo", 9)

URL_PATTERN = re.compile(r'https?://[^\s"\'<>]+')
ISO_DATETIME_PATTERN = re.compile(r'\b\d{4}-\d{2}-\d{2}(?:[T ][0-2]\d:[0-5]\d(?::[0-5]\d(?:\.\d+)?)?(?:Z|[+-][0-2]\d:?[0-5]\d)?)?\b')
UUID_PATTERN = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b')
INVALID_WINDOWS_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
HASH_CHUNK_SIZE = 1024 * 1024
USE_NATIVE_DIFF_ENGINE = True
STRUCTURAL_HASH_PREFLIGHT = True
WINDOWS_DIFF_RELATIVE_PATH = os.path.join("tools", "windows", "diff.exe")
FOOTER_LOGO_RELATIVE_PATH = os.path.join("assets", "code_by_noah_logo.png")

IGNORE_TAGS = {
    "GeneratedAt",
    "GeneratedDate",
    "LastModified",
    "Timestamp",
}
IGNORE_ATTRIBUTES = {
    "generatedAt",
    "generated_at",
    "id",
    "timestamp",
    "updatedAt",
    "updated_at",
    "uuid",
}
IGNORE_TEXT_PATTERNS = [
    (URL_PATTERN, "[IGNORED_URI]"),
    (ISO_DATETIME_PATTERN, "[IGNORED_DATETIME]"),
    (UUID_PATTERN, "[IGNORED_UUID]"),
]
