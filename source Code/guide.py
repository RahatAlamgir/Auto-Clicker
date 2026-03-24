import tkinter as tk


def show_guide(parent):
    guide_win = tk.Toplevel(parent)
    guide_win.title("Guide")
    guide_win.geometry("500x600")
    guide_win.configure(bg="#1a1a1a")

    help_text = """
MACRO COMMAND LIST
---------------------------------

loop [n]
Repeat script n times (-1 = infinite)

wait [time]
Wait time supports:
500ms, 2s, 1m, 1m30s

random_wait [a] [b]
Random delay between a and b

---------------- Keyboard ----------------

tap [key]
Press and release key

press [key]
Hold key

end [key]
Release key

---------------- Mouse ----------------

press mouse [left/right/middle]
Hold mouse button

end mouse [left/right/middle]
Release mouse button

click [left/right/middle]
Single click

dclick [left/right/middle]
Double click

move [x] [y]
Move mouse to position

scroll [value]
Scroll mouse wheel (e.g. 500 or -500)
"""

    text_widget = tk.Text(
        guide_win,
        bg="#1a1a1a",
        fg="white",
        font=("Consolas", 10),
        wrap="word",
        relief="flat",
        padx=15,
        pady=15
    )

    text_widget.insert("1.0", help_text)
    text_widget.config(state="disabled")
    text_widget.pack(fill="both", expand=True)