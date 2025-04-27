# teach_plugin.py

import threading
from tkinter import messagebox
from .chatgpt_selenium import send_and_get_reply  # your helper

def teach_callback(prompt_entry, rounds_entry, conv_widget, teach_button, root):
    """
    Reads the prompt & rounds from the two Entry widgets,
    sends them to ChatGPT via Selenium, and posts back the reply.
    """
    prompt = prompt_entry.get().strip()
    rounds = rounds_entry.get().strip()
    if not prompt or not rounds.isdigit():
        messagebox.showerror("Error", "Enter a prompt and valid rounds")  # :contentReference[oaicite:0]{index=0}
        return

    # Log the user’s teaching prompt
    conv_widget.insert("end", f"You (teach {rounds}): {prompt}\n")
    conv_widget.see("end")

    # Disable the button so it can’t be clicked again until done
    teach_button.config(state="disabled")

    # Worker thread to avoid blocking the GUI mainloop
    def worker():
        try:
            reply = send_and_get_reply(prompt)
        except Exception as e:
            reply = f"[Error talking to ChatGPT] {e}"
        # Back on the GUI thread, append the reply and re-enable button
        def finish():
            conv_widget.insert("end", f"ChatGPT: {reply}\n\n")
            conv_widget.see("end")
            teach_button.config(state="normal")
        root.after(0, finish)  # schedule on main thread :contentReference[oaicite:1]{index=1}

    threading.Thread(target=worker, daemon=True).start()  # :contentReference[oaicite:2]{index=2}
