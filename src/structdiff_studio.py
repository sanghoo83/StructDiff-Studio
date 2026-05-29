"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.3.0
Purpose: Compatibility launcher for the packaged application entry point.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structdiff.main import main


if __name__ == "__main__":
    main()
