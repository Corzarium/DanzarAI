#!/usr/bin/env python
# gui.py

import os
import re
import threading
import tkinter as tk                               # Tkinter GUI toolkit :contentReference[oaicite:5]{index=5}
from tkinter import ttk, messagebox                # ttk themed widgets & message boxes :contentReference[oaicite:6]{index=6}
import pyautogui

from .teach import research_session, teaching_session
from .teach_plugin import teach_callback          # External plugin for “Teach” logic

# ——————————————————————————————————————————————
# Main window setup
# ——————————————————————————————————————————————
root = tk.Tk()                                     # Create the main application window :contentReference[oaicite:7]{index=7}
root.title("DanzarAI Teaching")

# Conversation display (multi-line)
conv = tk.Text(root, wrap="word", height=20)       # Text widget for chat history :contentReference[oaicite:8]{index=8}
conv.pack(fill="both", expand=True, padx=10, pady=10)

# Frame for input controls
frm = ttk.Frame(root)
frm.pack(fill="x", padx=10)

# Entry for teaching prompt
ttk.Label(frm, text="Teach Prompt:").grid(row=0, column=0, sticky="w")
teach_ent = ttk.Entry(frm, width=50)               # Single-line Entry widget :contentReference[oaicite:9]{index=9}
teach_ent.grid(row=0, column=1, padx=5)

# Entry for number of rounds (optional)
ttk.Label(frm, text="Rounds:").grid(row=0, column=2, sticky="w", padx=(10,0))
teach_rounds = ttk.Entry(frm, width=5)
teach_rounds.grid(row=0, column=3)

# Buttons for various actions
btn_frame = ttk.Frame(root)
btn_frame.pack(fill="x", padx=10, pady=(0,10))

send_btn       = ttk.Button(btn_frame, text="Send")
screenshot_btn = ttk.Button(btn_frame, text="Screenshot")
research_btn   = ttk.Button(btn_frame, text="Research")
teach_btn      = ttk.Button(btn_frame, text="Teach")

send_btn.pack(side="left")
screenshot_btn.pack(side="left", padx=5)
research_btn.pack(side="left", padx=5)
teach_btn.pack(side="right")

# ——————————————————————————————————————————————
# Existing feature callbacks (left intact)
# ——————————————————————————————————————————————
def on_send():
    # Your existing send logic goes here
    pass

def on_screenshot():
    # Your existing screenshot logic goes here
    pass

def on_research():
    # Your existing research logic goes here
    pass

# ——————————————————————————————————————————————
# Wire up the commands to callbacks
# ——————————————————————————————————————————————
send_btn      .config(command=on_send)             # Standard button callback :contentReference[oaicite:10]{index=10}
screenshot_btn.config(command=on_screenshot)
research_btn  .config(command=on_research)

# Teach button now calls the external plugin’s function,
# passing in all relevant widgets and the root window
teach_btn.config(
    command=lambda: teach_callback(
        teach_ent,      # Entry widget for prompt :contentReference[oaicite:11]{index=11}
        teach_rounds,   # Entry widget for rounds
        conv,           # Text widget for conversation
        teach_btn,      # Teach button (to disable/re-enable)
        root            # Root window (for .after scheduling) :contentReference[oaicite:12]{index=12}
    )
)

# ——————————————————————————————————————————————
# Start the GUI event loop
# ——————————————————————————————————————————————
root.mainloop()                                    # Begin Tkinter’s main loop :contentReference[oaicite:13]{index=13}
