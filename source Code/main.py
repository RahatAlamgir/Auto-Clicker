import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pyautogui
import keyboard
import time
import random
import os
import ctypes
import webbrowser
from pynput import mouse, keyboard as pynput_key

# ---------- TASKBAR & ICON LOGIC ----------
def set_app_id():
    try:
        # Unique ID so Windows handles taskbar icons correctly
        myappid = 'rahat.autoclicker.pro.v3'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass

def change_taskbar_icon(icon_name):
    """Swaps the window and taskbar icon dynamically."""
    try:
        if os.path.exists(icon_name):
            root.iconbitmap(icon_name)
    except:
        pass

set_app_id()

# ---------- GLOBAL STATE & TRACKER ----------
running = False
recording = False
active_keys = set()
active_mouse = set()
recorded_commands = []
last_event_time = 0
is_mouse_dragging = False


# ---------- FOLDER GUARD ----------
if not os.path.exists("configs"): os.makedirs("configs")

# ---------- ENGINE ----------
def execute_command(cmd):
    global active_keys, active_mouse
    try:
        parts = cmd.split()
        if not parts: return

        if parts[0] == "press":
            if parts[1] == "mouse":
                pyautogui.mouseDown(button=parts[2])
                active_mouse.add(parts[2])
            else:
                pyautogui.keyDown(parts[1])
                active_keys.add(parts[1])
        elif parts[0] == "end":
            if parts[1] == "mouse":
                pyautogui.mouseUp(button=parts[2])
                active_mouse.discard(parts[2])
            else:
                pyautogui.keyUp(parts[1])
                active_keys.discard(parts[1])
        elif parts[0] == "tap":
            pyautogui.press(parts[1])
        elif parts[0] == "wait":
            smart_sleep(int(parts[1]))
        elif parts[0] == "random_wait":
            delay = random.randint(int(parts[1]), int(parts[2]))
            smart_sleep(delay)
        elif parts[0] == "move":
            pyautogui.moveTo(int(parts[1]), int(parts[2]))
        elif parts[0] == "click":
            pyautogui.click(button=parts[1])
        elif parts[0] == "scroll":
            pyautogui.scroll(int(parts[1]))
        elif parts[0] == "dclick":
            pyautogui.doubleClick(button=parts[1])
    except Exception as e:
        log(f"Engine Error: {e}")

def smart_sleep(ms):
    global running
    remaining = ms / 1000
    while remaining > 0 and running:
        time.sleep(min(0.05, remaining))
        remaining -= 0.05

def release_all_safe():
    """Smart release to prevent sticky keys when stopping."""
    global active_keys, active_mouse
    for btn in list(active_mouse):
        pyautogui.mouseUp(button=btn)
    for key in list(active_keys):
        pyautogui.keyUp(key)
    active_keys.clear()
    active_mouse.clear()
    log("Safety: All inputs released.")

# ---------- RECORDER LOGIC ----------
def add_recorded_cmd(cmd):
    global last_event_time, recorded_commands
    now = time.time()
    if last_event_time != 0:
        delay = int((now - last_event_time) * 1000)
        if delay > 20: # Ignore tiny delays
            recorded_commands.append(f"wait {delay}")
    recorded_commands.append(cmd)
    last_event_time = now

def on_rec_press(key):
    if not recording: return
    try: k = key.char
    except AttributeError: k = str(key).replace("Key.", "")
    
    # NEW: Filter out the control hotkeys so they don't record themselves
    if k.lower() in ['f6', 'f7']: return 
    
    add_recorded_cmd(f"press {k}")

def on_rec_release(key):
    if not recording: return
    try: k = key.char
    except AttributeError: k = str(key).replace("Key.", "")
    
    # NEW: Filter out the control hotkeys
    if k.lower() in ['f6', 'f7']: return
    
    add_recorded_cmd(f"end {k}")



last_click_time = 0

def on_rec_click(x, y, button, pressed):
    global is_mouse_dragging, last_click_time
    if not recording: return

    btn = str(button).replace("Button.", "")

    if pressed:
        now = time.time()
        if now - last_click_time < 0.3:  # double-click threshold
            add_recorded_cmd(f"move {int(x)} {int(y)}")
            add_recorded_cmd(f"dclick {btn}")
            last_click_time = 0
        else:
            add_recorded_cmd(f"move {int(x)} {int(y)}")
            add_recorded_cmd(f"press mouse {btn}")
            last_click_time = now
    else:
        if last_click_time != 0:
            add_recorded_cmd(f"end mouse {btn}")

def on_rec_move(x, y):
    if recording and is_mouse_dragging:
        add_recorded_cmd(f"move {int(x)} {int(y)}")

def on_rec_scroll(x, y, dx, dy):
    if not recording: return
    add_recorded_cmd(f"scroll {int(dy * 120)}")

def toggle_record():
    global recording, recorded_commands, last_event_time, running
    
    if running: 
        log("Cannot record while script is running!")
        return 
    
    if not recording:
        recorded_commands = []
        last_event_time = time.time()
        recording = True
        update_ui_status()
        log("🔴 RECORDING STARTED (F7 to stop)")
    else:
        recording = False
        update_ui_status()
        log("✅ RECORDING FINISHED")
        # Added a small separator in the editor
        editor.insert(tk.END, f"\n# --- Recorded at {time.strftime('%H:%M:%S')} ---\n")
        editor.insert(tk.END, "\n".join(recorded_commands) + "\n")

# Start background listeners
m_listener = mouse.Listener(on_click=on_rec_click, on_move=on_rec_move, on_scroll=on_rec_scroll)
k_listener = pynput_key.Listener(on_press=on_rec_press, on_release=on_rec_release)
m_listener.start(); k_listener.start()

# ---------- SCRIPT RUNNER ----------
def run_script(commands):
    global running
    loop_count = 1
    clean_cmds = []
    for c in commands:
        if c.startswith("loop"):
            try: loop_count = int(c.split()[1])
            except: pass
        else: clean_cmds.append(c)

    def run_once():
        for cmd in clean_cmds:
            if not running: return
            execute_command(cmd)

    if loop_count == -1:
        while running: run_once()
    else:
        for _ in range(loop_count):
            if not running: break
            run_once()
    root.after(0, stop_ui_state)

def stop_ui_state():
    global running
    running = False
    update_ui_status()
    release_all_safe()
    log("Session Finished.")

# ---------- UI LOGIC ----------
def log(msg):
    log_box.insert(tk.END, f" {msg}\n")
    log_box.see(tk.END)

def update_ui_status():
    if recording:
        status_label.config(text="● RECORDING", fg="#f39c12")
        change_taskbar_icon("ico/rec.ico") # Optional: use a red icon
    elif running:
        status_label.config(text="● RUNNING", fg="#00ff88")
        change_taskbar_icon("ico/busy.ico")
    else:
        status_label.config(text="○ STOPPED", fg="#ff5555")
        change_taskbar_icon("ico/idle.ico")

def toggle_run():
    global running
    if recording: return
    if not running:
        name = config_var.get()
        if not name or not os.path.exists(os.path.join("configs", name)):
            log("Error: Select a script first!")
            return
        running = True
        update_ui_status()
        threading.Thread(target=worker, args=(name,), daemon=True).start()
    else:
        running = False
        update_ui_status()

def worker(name):
    with open(os.path.join("configs", name)) as f:
        cmds = [l.strip().lower() for l in f if l.strip()]
    log(f"Started: {name}")
    run_script(cmds)

# ---------- FILE OPERATIONS ----------
def load_configs():
    return [f for f in os.listdir("configs") if f.endswith(".txt")]

def save_config():
    name = config_var.get()
    if not name: return
    if not name.endswith(".txt"): name += ".txt"
    with open(os.path.join("configs", name), "w") as f:
        f.write(editor.get("1.0", tk.END).strip())
    log(f"Saved: {name}")
    config_dropdown['values'] = load_configs()

def create_new():
    editor.delete("1.0", tk.END)
    config_var.set("new_script.txt")
    log("Ready for new script.")

def delete_config():
    name = config_var.get()
    path = os.path.join("configs", name)
    if os.path.exists(path):
        if messagebox.askyesno("Delete", f"Delete {name}?"):
            os.remove(path)
            editor.delete("1.0", tk.END)
            config_var.set("")
            log(f"Deleted {name}")
            config_dropdown['values'] = load_configs()

def load_selected():
    path = os.path.join("configs", config_var.get())
    if os.path.exists(path):
        with open(path, "r") as f:
            editor.delete("1.0", tk.END)
            editor.insert(tk.END, f.read())
        log(f"Loaded {config_var.get()}")

def on_dropdown_change(*args):
    if config_var.get() and config_var.get() in load_configs():
        delete_btn.pack(fill="x", padx=20, pady=5, after=save_btn)
    else:
        delete_btn.pack_forget()

# ---------- INFO WINDOWS ----------
def show_help():
    help_win = tk.Toplevel(root); help_win.title("Guide"); help_win.geometry("500x600"); help_win.configure(bg="#1a1a1a")
    help_text = """
    MACRO COMMAND LIST
    ---------------------------------
    loop [n]            : Repeat n times (-1 for infinite)
    wait [ms]           : Wait (1000 = 1 second)
    random_wait [a] [b] : Wait between a and b ms


    --------- Keyboard --------
    tap [key]           : Press and release a key
    press [key]         : Hold a key down
    end [key]           : Release a held key

    ---------- Mouse  ---------

    press mouse [left/right/middle] : Hold button
    end mouse [left/right/middle]   : Release button
    
    click [left/right/middle]       : Click mouse
    dclick [left/right/middle]      : double click Mouse
    move [x] [y]                    : Move mouse to coordinates
    scroll [n]                      : Scroll wheel (eg: 500 or -500)
    
    """
    tk.Label(help_win, text=help_text, fg="white", bg="#1a1a1a", font=("Consolas", 10), justify="left", padx=20, pady=20).pack()

def show_about():
    about_win = tk.Toplevel(root); about_win.title("About"); about_win.geometry("300x250"); about_win.configure(bg="#1a1a1a")
    tk.Label(about_win, text="AUTO CLICKER PRO", fg="#00ff88", bg="#1a1a1a", font=("Segoe UI", 14, "bold")).pack(pady=20)
    tk.Label(about_win, text="Created by: Md Rahat Alamgir", fg="white", bg="#1a1a1a", font=("Segoe UI", 11)).pack()
    tk.Button(about_win, text="GitHub", fg="#3498db", bg="#1a1a1a", relief="flat", command=lambda: webbrowser.open("https://github.com/RahatAlamgir")).pack(pady=10)

# ---------- MAIN UI ----------
root = tk.Tk()
root.title("Auto Clicker Pro")
root.geometry("1000x750")
root.configure(bg="#0f0f0f")

change_taskbar_icon("ico/idle.ico")

sidebar = tk.Frame(root, bg="#1a1a1a", width=250); sidebar.pack(side="left", fill="y"); sidebar.pack_propagate(False)
status_label = tk.Label(sidebar, text="○ STOPPED", fg="#ff5555", bg="#1a1a1a", font=("Segoe UI", 18, "bold")); status_label.pack(pady=30)

config_var = tk.StringVar(); config_var.trace_add("write", on_dropdown_change)
config_dropdown = ttk.Combobox(sidebar, textvariable=config_var, values=load_configs()); config_dropdown.pack(pady=5, padx=20, fill="x")

btn_style = {"relief": "flat", "font": ("Segoe UI", 9, "bold"), "cursor": "hand2"}
tk.Button(sidebar, text="📂 Load Selected", bg="#333", fg="white", **btn_style, command=load_selected).pack(fill="x", padx=20, pady=2)

tk.Button(sidebar, text="➕ New Script", bg="#3498db", fg="white", **btn_style, command=create_new).pack(fill="x", padx=20, pady=2)
save_btn = tk.Button(sidebar, text="💾 Save / Update", bg="#2ecc71", fg="black", **btn_style, command=save_config); save_btn.pack(fill="x", padx=20, pady=2)
delete_btn = tk.Button(sidebar, text="🗑️ Delete Script", bg="#e74c3c", fg="white", **btn_style, command=delete_config)


tk.Button(sidebar, text="❓ How to Script", bg="#D6CB30", fg="black", **btn_style, command=show_help).pack(fill="x", padx=20, pady=(20, 2))
tk.Button(sidebar, text="👤 About Developer", bg="#9b59b6", fg="white", **btn_style, command=show_about).pack(fill="x", padx=20, pady=2)

info_box = tk.Frame(sidebar, bg="#111", pady=15); info_box.pack(side="bottom", fill="x", padx=15, pady=20)
tk.Label(info_box, text="F6: RUN / STOP", fg="#00ff88", bg="#111", font=("Segoe UI", 10, "bold")).pack()
tk.Label(info_box, text="F7: REC / STOP", fg="#f39c12", bg="#111", font=("Segoe UI", 10, "bold")).pack()

main = tk.Frame(root, bg="#0f0f0f"); main.pack(side="right", fill="both", expand=True, padx=20, pady=20)
editor = tk.Text(main, bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", font=("Consolas", 12), relief="flat", padx=15, pady=15); editor.pack(fill="both", expand=True)
log_box = tk.Text(main, height=8, bg="#000", fg="#00ff88", font=("Consolas", 10), relief="flat", padx=15, pady=15); log_box.pack(fill="x", pady=(20, 0))

keyboard.add_hotkey('f6', toggle_run)
keyboard.add_hotkey('f7', toggle_record)
root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

log("Auto Clicker Pro Ready.")
root.mainloop()