# Danzar/gui.py

import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui

SCREENSHOT_PATH = os.path.join(os.getcwd(), "gui_screenshot.png")

class DummyMessage:
    def __init__(self, conv, rsn):
        self.conv = conv
        self.rsn  = rsn

    async def edit(self, *, content):
        thought = re.search(r"<think>(.*?)</think>", content, flags=re.DOTALL)
        if thought:
            t = thought.group(1).strip()
            self.rsn.insert(tk.END, f"AI-THINK: {t}\n")
            self.rsn.see(tk.END)
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        self.conv.insert(tk.END, f"{content}\n")
        self.conv.see(tk.END)

class GUIChannel:
    def __init__(self, conv, rsn):
        self.conv = conv
        self.rsn  = rsn

    async def send(self, msg):
        thought = re.search(r"<think>(.*?)</think>", msg, flags=re.DOTALL)
        if thought:
            t = thought.group(1).strip()
            self.rsn.insert(tk.END, f"AI-THINK: {t}\n")
            self.rsn.see(tk.END)
            msg = re.sub(r"<think>.*?</think>", "", msg, flags=re.DOTALL).strip()
        self.conv.insert(tk.END, f"AI: {msg}\n")
        self.conv.see(tk.END)
        return DummyMessage(self.conv, self.rsn)

def run_gui(bot, request_queue, settings, save_settings):
    root = tk.Tk()
    root.title("Danzar Control Panel")

    nb = ttk.Notebook(root)
    main_frame     = ttk.Frame(nb, padding=10)
    settings_frame = ttk.Frame(nb, padding=10)
    nb.add(main_frame,     text="Main")
    nb.add(settings_frame, text="Settings")
    nb.pack(fill="both", expand=True)

    # ─── Main Tab ─────────────────────────────────────────────
    conv = tk.Text(main_frame, height=10, wrap="word")
    conv.grid(row=0, column=0, columnspan=4, sticky="nsew")

    rsn = tk.Text(main_frame, height=6, wrap="word", fg="blue")
    rsn.grid(row=1, column=0, columnspan=4, sticky="nsew")

    var = tk.BooleanVar(value=False, master=main_frame)
    ttk.Checkbutton(
        main_frame, text="Commentator Mode (auto-screenshot every 10s)",
        variable=var
    ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(5,0))

    # Chat entry
    chat_ent = ttk.Entry(main_frame)
    chat_ent.grid(row=3, column=0, columnspan=3, sticky="we", padx=(0,5), pady=5)
    send_btn = ttk.Button(main_frame, text="Send")
    send_btn.grid(row=3, column=3, sticky="e", pady=5)
    screenshot_btn = ttk.Button(main_frame, text="Screenshot")
    screenshot_btn.grid(row=4, column=0, columnspan=4, pady=(0,10))

    # Research panel
    ttk.Label(main_frame, text="🔍 Research:").grid(row=5, column=0, sticky="w", pady=(10,2))
    research_ent  = ttk.Entry(main_frame)
    research_ent.grid(row=6, column=0, columnspan=2, sticky="we", padx=(0,5))
    ttk.Label(main_frame, text="mins").grid(row=6, column=2, sticky="e")
    research_mins = tk.Spinbox(main_frame, from_=1, to=60, width=5)
    research_mins.grid(row=6, column=3, sticky="w")
    research_btn  = ttk.Button(main_frame, text="Research")
    research_btn.grid(row=7, column=0, columnspan=4, sticky="we", pady=(2,10))

    # Teach panel
    ttk.Label(main_frame, text="🎓 Teach:").grid(row=8, column=0, sticky="w", pady=(10,2))
    teach_ent     = ttk.Entry(main_frame)
    teach_ent.grid(row=9, column=0, columnspan=2, sticky="we", padx=(0,5))
    ttk.Label(main_frame, text="rounds").grid(row=9, column=2, sticky="e")
    teach_rounds  = tk.Spinbox(main_frame, from_=1, to=20, width=5)
    teach_rounds.grid(row=9, column=3, sticky="w")
    teach_btn     = ttk.Button(main_frame, text="Teach")
    teach_btn.grid(row=10, column=0, columnspan=4, sticky="we")

    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    main_frame.rowconfigure(0, weight=2)
    main_frame.rowconfigure(1, weight=1)

    # ─── Settings Tab ─────────────────────────────────────────
    ttk.Label(settings_frame, text="Voice:").grid(row=0, column=0, sticky="w", pady=(0,5))
    voice_entry = ttk.Entry(settings_frame)
    voice_entry.insert(0, settings.get("voice", "p231"))   # ← fixed here
    voice_entry.grid(row=0, column=1, sticky="we", pady=(0,5))

    ttk.Label(settings_frame, text="Volume:").grid(row=1, column=0, sticky="w", pady=(0,5))
    volume_scale = ttk.Scale(settings_frame, from_=0, to=20, orient="horizontal")
    volume_scale.set(settings.get("volume", 4))
    volume_scale.grid(row=1, column=1, sticky="we", pady=(0,5))

    ttk.Label(settings_frame, text="Personality Prompt:").grid(row=2, column=0, sticky="nw")
    personality_box = tk.Text(settings_frame, height=6, wrap="word")
    personality_box.insert("1.0", settings.get("personality", ""))
    personality_box.grid(row=2, column=1, sticky="nsew", pady=(0,5))

    def on_save():
        settings["voice"]       = voice_entry.get().strip()
        settings["volume"]      = volume_scale.get()
        settings["personality"] = personality_box.get("1.0", tk.END).strip()
        save_settings(settings)
        messagebox.showinfo("Settings", "Saved!")

    ttk.Button(settings_frame, text="Save Settings", command=on_save)\
       .grid(row=3, column=1, sticky="e")

    settings_frame.columnconfigure(1, weight=1)
    settings_frame.rowconfigure(2, weight=1)

    def on_send():
        text = chat_ent.get().strip()
        if not text: return
        conv.insert(tk.END, f"You: {text}\n"); conv.see(tk.END)
        chat_ent.delete(0, tk.END)
        ch = GUIChannel(conv, rsn)
        request_queue.put_nowait((bot.user, text, ch))

    def on_screenshot():
        path = os.path.abspath(SCREENSHOT_PATH)
        pyautogui.screenshot(path)
        conv.insert(tk.END, "You: <Screenshot sent>\n"); conv.see(tk.END)
        ch = GUIChannel(conv, rsn)
        request_queue.put_nowait((bot.user, path, ch))

    def on_research():
        q    = research_ent.get().strip()
        mins = research_mins.get().strip()
        if not q or not mins.isdigit():
            messagebox.showerror("Error", "Enter a question and valid minutes")
            return
        conv.insert(tk.END, f"You (research for {mins}m): {q}\n"); conv.see(tk.END)
        from .teach import research_session
        ch = GUIChannel(conv, rsn)
        bot.loop.create_task(research_session(q, int(mins), ch))

    def on_teach():
        q     = teach_ent.get().strip()
        rnds  = teach_rounds.get().strip()
        if not q or not rnds.isdigit():
            messagebox.showerror("Error", "Enter a topic and valid rounds")
            return
        conv.insert(tk.END, f"You (teach {rnds} rounds): {q}\n"); conv.see(tk.END)
        from .teach import teaching_session
        ch = GUIChannel(conv, rsn)
        bot.loop.create_task(teaching_session(q, int(rnds), ch))

    send_btn.config(command=on_send)
    screenshot_btn.config(command=on_screenshot)
    research_btn.config(command=on_research)
    teach_btn.config(command=on_teach)

    def periodic():
        if var.get():
            on_screenshot()
        root.after(10000, periodic)
    root.after(10000, periodic)

    root.mainloop()
