import pyautogui
import time
import random


# These will be controlled from UI
running = False

# Track active inputs (for safety release)
active_keys = set()
active_mouse = set()


# ---------- CORE EXECUTION ----------

def execute_command(cmd, log):
    global active_keys, active_mouse

    parts = cmd.split()
    if not parts:
        return

    try:
        cmd_type = parts[0].lower()

        # ---------- SAFETY CHECKS ----------
        if cmd_type in ["press", "end"] and len(parts) < 2:
            log("Syntax error. Line incomplete","error")
            return
        if cmd_type == ["move","random_wait","click","dclick","scroll"] and len(parts) < 3:
            log("Syntax error. Line incomplete","error")
            return
        if cmd_type in ["tap"] and len(parts) < 2:
            log("Syntax error. Line incomplete","error")
            return
        
        if cmd_type == "drag" and len(parts) < 5:
            log("Syntax error. Line incomplete","error")
            return

        # ---------- COMMANDS ----------

        if cmd_type == "press":
            parts[1] = parts[1].lower()
            
            if parts[1] == "mouse":
                parts[2] = parts[2].lower()
                pyautogui.mouseDown(button=parts[2])
                active_mouse.add(parts[2])
            else:
                pyautogui.keyDown(parts[1])
                active_keys.add(parts[1])

        elif cmd_type == "end":
            parts[1] = parts[1].lower()
            
            if parts[1] == "mouse":
                parts[2] = parts[2].lower()
                pyautogui.mouseUp(button=parts[2])
                active_mouse.discard(parts[2])
            else:
                pyautogui.keyUp(parts[1])
                active_keys.discard(parts[1])

        elif cmd_type == "tap":
            pyautogui.press(parts[1])


        elif cmd_type == "move":
            pyautogui.moveTo(int(parts[1]), int(parts[2]))

        elif cmd_type == "click":
            pyautogui.click(button=parts[1].lower())

        elif cmd_type == "scroll":
            pyautogui.scroll(int(parts[1]))

        elif cmd_type == "dclick":
            pyautogui.doubleClick(button=parts[1].lower())
        elif cmd_type == "drag":
            _, x1, y1, x2, y2, duration = cmd.split()

            x1, y1 = int(x1), int(y1)
            x2, y2 = int(x2), int(y2)
            duration = float(duration)

            pyautogui.moveTo(x1, y1)
            pyautogui.moveTo(x2, y2, duration=duration)

        elif cmd_type == "text":
            text = cmd[len("text "):]
            pyautogui.write(text, interval=0.02)

        elif cmd_type == "hotkey":
            keys = parts[1:]
            pyautogui.hotkey(*keys)

        elif cmd_type == "wait" and len(parts) >= 3 and parts[1].lower() == "color":

            # ---------- DEFAULTS ----------
            x, y = None, None
            target_color = None
            tolerance = 0
            timeout = 10  # seconds
            skip_lines = 0

            i = 2

            # ---------- POSITION ----------
            if parts[i].lower() == "center":
                screen_w, screen_h = pyautogui.size()
                x, y = screen_w // 2, screen_h // 2
                i += 1
            else:
                x = int(parts[i])
                y = int(parts[i + 1])
                i += 2

            # ---------- COLOR ----------
            target_color = parts[i].lower()
            i += 1

            def hex_to_rgb(h):
                h = h.lstrip("#")
                return tuple(int(h[j:j+2], 16) for j in (0, 2, 4))

            target_rgb = hex_to_rgb(target_color)

            # ---------- OPTIONAL PARAMS ----------
            while i < len(parts):
                p = parts[i].lower()

                if p == "tolerance":
                    tolerance = int(parts[i + 1])
                    i += 2

                elif p == "skip":
                    skip_lines = int(parts[i + 1])
                    i += 2

                else:
                    # assume time
                    timeout = parse_time_to_ms(p) / 1000
                    i += 1

            # ---------- WAIT LOOP ----------
            start_time = time.time()
            found = False

            while running and (time.time() - start_time < timeout):
                current = pyautogui.pixel(x, y)

                if all(abs(current[j] - target_rgb[j]) <= tolerance for j in range(3)):
                    found = True
                    break

                time.sleep(0.05)

            # ---------- RESULT ----------
            if found:
                log(f"Color matched at ({x},{y})", "success")

                if skip_lines > 0:
                    return ("skip", skip_lines)

            else:
                log(f"Color not found within {timeout}s", "error")

        elif cmd_type == "wait":
            if len(parts) < 2:
                log("Syntax error. Missing wait value", "error")
                return

            # ---------- RANDOM WAIT ----------
            if parts[1].lower() == "random":
                if len(parts) < 4:
                    log("Syntax error. random wait needs 2 values", "error")
                    return

                start = parse_time_to_ms(parts[2])
                end = parse_time_to_ms(parts[3])

                if end < start:
                    start, end = end, start

                delay = random.randint(start, end)
                smart_sleep(delay)

            # ---------- NORMAL WAIT ----------
            else:
                delay = parse_time_to_ms(parts[1])
                smart_sleep(delay)

        else:
            log("Syntax error.","error")

    except Exception as e:
        log(f"Engine Error: {e}", "error")


# ---------- TIME HANDLING ----------

def parse_time_to_ms(value):
    try:
        value = value.lower().strip()

        if value.endswith("ms"):
            return int(value[:-2])

        elif value.endswith("s"):
            return int(float(value[:-1]) * 1000)

        elif value.endswith("m"):
            return int(float(value[:-1]) * 60 * 1000)

        elif "m" in value or "s" in value:
            total_ms = 0
            num = ""
            for ch in value:
                if ch.isdigit() or ch == ".":
                    num += ch
                else:
                    if ch == "m":
                        total_ms += float(num) * 60 * 1000
                    elif ch == "s":
                        total_ms += float(num) * 1000
                    num = ""
            return int(total_ms)

        else:
            return int(value)

    except:
        raise ValueError(f"Invalid time format: {value}")


# ---------- SMART SLEEP ----------

def smart_sleep(ms):
    global running

    remaining = ms / 1000
    while remaining > 0 and running:
        time.sleep(min(0.05, remaining))
        remaining -= 0.05


# ---------- SAFETY ----------

def release_all_safe(log):
    global active_keys, active_mouse

    for btn in list(active_mouse):
        pyautogui.mouseUp(button=btn)

    for key in list(active_keys):
        pyautogui.keyUp(key)

    active_keys.clear()
    active_mouse.clear()

    log("Safety: All inputs released.", "neutral")


# ---------- SCRIPT RUNNER ----------

def run_script(commands, log, on_finish):
    global running

    loop_count = 1
    clean_cmds = []

    for c in commands:
        if c.startswith("loop"):
            try:
                loop_count = int(c.split()[1])
            except:
                pass
        else:
            clean_cmds.append(c)

    def run_once():
        i = 0
        while i < len(clean_cmds):
            if not running:
                return

            cmd = clean_cmds[i].strip()

            # 🚫 skip comment lines
            if cmd.startswith("//") and cmd.endswith("//"):
                i += 1
                continue

            result = execute_command(clean_cmds[i], log)

            if isinstance(result, tuple) and result[0] == "skip":
                skip_n = result[1]
                skipped = 0

                while skipped < skip_n and i + 1 < len(clean_cmds):
                    i += 1
                    if clean_cmds[i].strip() and not clean_cmds[i].strip().startswith("//"):
                        skipped += 1
            i += 1

    if loop_count == -1:
        while running:
            run_once()
    else:
        for _ in range(loop_count):
            if not running:
                break
            run_once()

    on_finish()