"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.3.0
Purpose: Resolve application resources in source and PyInstaller builds.
"""

import os
import sys


def app_resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    candidates = [
        os.path.join(script_dir, relative_path),
        os.path.join(os.path.dirname(script_dir), relative_path),
        os.path.join(project_root, relative_path),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[-1]
