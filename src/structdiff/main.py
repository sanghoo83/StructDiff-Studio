"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.5.0
Purpose: Application entry point.
"""

import tkinter as tk

from .app import StructDiffStudioApp


def main():
    root = tk.Tk()
    StructDiffStudioApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
