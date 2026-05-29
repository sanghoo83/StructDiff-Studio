"""
StructDiff Studio
Author: Noah Nam
Contact: n83.noah@gmail.com
Version: 0.3.0
Purpose: Reusable Tkinter widgets used by the desktop UI.
"""

import math
import tkinter as tk

from .config import COLORS

def draw_perfect_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    x2 -= 1; y2 -= 1
    max_radius = min(x2 - x1, y2 - y1) / 2
    radius = min(radius, max_radius)
    points = []
    for i in range(180, 270, 5):
        rad = math.radians(i)
        points.extend([x1 + radius + radius * math.cos(rad), y1 + radius + radius * math.sin(rad)])
    for i in range(270, 360, 5):
        rad = math.radians(i)
        points.extend([x2 - radius + radius * math.cos(rad), y1 + radius + radius * math.sin(rad)])
    for i in range(0, 90, 5):
        rad = math.radians(i)
        points.extend([x2 - radius + radius * math.cos(rad), y2 - radius + radius * math.sin(rad)])
    for i in range(90, 180, 5):
        rad = math.radians(i)
        points.extend([x1 + radius + radius * math.cos(rad), y2 - radius + radius * math.sin(rad)])
    return canvas.create_polygon(points, smooth=False, **kwargs)

class RoundedFrame(tk.Canvas):
    def __init__(self, parent, radius=15, bg_color=COLORS["BG_CARD"], border_color=COLORS["ACCENT"], border_width=2):
        super().__init__(parent, borderwidth=0, relief="flat", highlightthickness=0, bg=parent["bg"])
        self.radius = radius
        self.bg_color = bg_color
        self.border_color = border_color
        self.border_width = border_width
        self.inner_frame = tk.Frame(self, bg=bg_color)
        self.window_id = self.create_window(0, 0, window=self.inner_frame, anchor="nw")
        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        w, h = event.width, event.height
        self.delete("bg")
        draw_perfect_rounded_rect(self, 0, 0, w, h, self.radius, fill=self.bg_color, outline=self.border_color, width=self.border_width, tags="bg")
        self.tag_lower("bg")
        pad = 12
        self.itemconfigure(self.window_id, width=w-(2*pad), height=h-(2*pad))
        self.coords(self.window_id, pad, pad)

class RoundedButton(tk.Canvas):
    def __init__(self, parent, text: str, command, width=280, height=36, radius=18, bg_color=COLORS["ACCENT"], text_color="white", state="normal"):
        super().__init__(parent, borderwidth=0, relief="flat", highlightthickness=0, bg=COLORS["BG_CARD"], width=width, height=height)
        self.command = command
        self.bg_color = bg_color
        self.hover_color = COLORS["ACCENT_HOVER"] if bg_color == COLORS["ACCENT"] else "#E0E0E0"
        self.text_color = text_color
        self.state = state
        self.rect = draw_perfect_rounded_rect(self, 0, 0, width, height, radius, fill=bg_color, outline="")
        self.text = self.create_text(width/2, height/2, text=text, fill=text_color, font=("Helvetica", 9, "bold"))
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.set_state(state)

    def _on_click(self, event):
        if self.state == "normal": self.command()

    def _on_enter(self, event):
        if self.state == "normal": self.itemconfig(self.rect, fill=self.hover_color)

    def _on_leave(self, event):
        if self.state == "normal": self.itemconfig(self.rect, fill=self.bg_color)

    def set_state(self, state: str):
        self.state = state
        fill = "#E5E5E5" if state == "disabled" else self.bg_color
        text_fill = "#999999" if state == "disabled" else self.text_color
        self.itemconfig(self.rect, fill=fill)
        self.itemconfig(self.text, fill=text_fill)

    def config(self, state):
        self.set_state(state)
