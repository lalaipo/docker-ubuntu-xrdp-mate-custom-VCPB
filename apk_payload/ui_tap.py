import re
import subprocess
import time
import xml.etree.ElementTree as ET


def dump_ui(remote_path="/sdcard/window_dump.xml", local_path="./window_dump.xml"):
    subprocess.run(["adb", "shell", "uiautomator", "dump", remote_path], check=False)
    subprocess.run(["adb", "pull", remote_path, local_path], check=False)
    try:
        with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print("dump_ui read error:", e)
        return ""


def parse_nodes(xml_text):
    nodes = []
    if not xml_text:
        return nodes
    try:
        root = ET.fromstring(xml_text)
        for node in root.iter("node"):
            text = node.attrib.get("text", "").strip()
            desc = node.attrib.get("content-desc", "").strip()
            cls = node.attrib.get("class", "")
            bounds = node.attrib.get("bounds", "")
            clickable = node.attrib.get("clickable", "false") == "true"
            checked = node.attrib.get("checked", "false") == "true"
            nodes.append({
                "text": text,
                "desc": desc,
                "class": cls,
                "bounds": bounds,
                "clickable": clickable,
                "checked": checked
            })
    except Exception as e:
        print("parse error:", e)
    return nodes


def center_of(bounds):
    nums = list(map(int, re.findall(r"-?\d+", bounds)))
    if len(nums) == 4:
        x1, y1, x2, y2 = nums
        return (x1 + x2) // 2, (y1 + y2) // 2
    return 540, 960


def switch_coords(bounds):
    nums = list(map(int, re.findall(r"-?\d+", bounds)))
    if len(nums) == 4:
        x1, y1, x2, y2 = nums
        # Switch thumb is on right side
        return x2 - 90, (y1 + y2) // 2
    return 950, 500


def tap(x, y):
    print(f"--> [TAP] at ({x}, {y})")
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=False)


def swipe_up():
    print("--> [SWIPE UP] (scroll down)")
    subprocess.run(["adb", "shell", "input", "swipe", "540", "1500", "540", "500", "400"], check=False)
    time.sleep(1.5)


def take_screen(remote="/sdcard/screen.png", local="./screen.png"):
    subprocess.run(["adb", "shell", "screencap", "-p", remote], check=False)
    subprocess.run(["adb", "pull", remote, local], check=False)


def main():
    print("=== TEST START: WAITING 3S FOR LAUNCH ===")
    time.sleep(3)

    # 1. Capture BEFORE screen
    print("\n=== STEP 1: CAPTURE INITIAL SCREEN (BEFORE TOGGLE) ===")
    take_screen("/sdcard/screen_before_toggle.png", "./screen_before_toggle.png")
    xml1 = dump_ui("/sdcard/ui_before.xml", "./ui_before.xml")
    nodes1 = parse_nodes(xml1)
    texts1 = [n["text"] for n in nodes1 if n["text"]]
    print("Initial visible texts:", texts1)

    target_kws = ["virtual", "gpu", "compilation", "wifi", "boost", "speed", "hardware", "battery"]
    target_node = None

    # Search for target toggle
    for attempt in range(4):
        print(f"\n--- Checking viewport {attempt} ---")
        for n in nodes1:
            combined = (n["text"] + " " + n["desc"]).lower()
            for kw in target_kws:
                if kw in combined:
                    print(f"Found match: text={repr(n['text'])}, desc={repr(n['desc'])}, bounds={n['bounds']}")
                    target_node = n
                    break
            if target_node:
                break
        if target_node:
            break
        print("Target not found in current view, scrolling...")
        swipe_up()
        xml1 = dump_ui(f"/sdcard/ui_scroll_{attempt}.xml", f"./ui_scroll_{attempt}.xml")
        nodes1 = parse_nodes(xml1)
        print("New texts:", [n["text"] for n in nodes1 if n["text"]])

    if not target_node:
        print("No keyword match found, finding first clickable row...")
        for n in nodes1:
            if n["clickable"] and n["text"]:
                target_node = n
                break

    if target_node:
        print(f"\nTarget element selected: {target_node}")
        sx, sy = switch_coords(target_node["bounds"])
        cx, cy = center_of(target_node["bounds"])
        print(f"Row center: ({cx}, {cy}), Switch target: ({sx}, {sy})")

        # 2. Tap toggle to turn ON
        print("\n=== STEP 2: TAP TOGGLE (TURNING ON) ===")
        tap(sx, sy)
        time.sleep(2)

        # 3. Capture AFTER screen
        print("\n=== STEP 3: CAPTURE SCREEN AFTER TOGGLE ===")
        take_screen("/sdcard/screen_after_toggle.png", "./screen_after_toggle.png")
        xml2 = dump_ui("/sdcard/ui_after.xml", "./ui_after.xml")
        nodes2 = parse_nodes(xml2)
        print("Post-toggle texts:", [n["text"] for n in nodes2 if n["text"]])

        # 4. Tap toggle again to turn OFF
        print("\n=== STEP 4: TAP TOGGLE AGAIN (TURNING OFF) ===")
        tap(sx, sy)
        time.sleep(2)
        take_screen("/sdcard/screen_toggle_off.png", "./screen_toggle_off.png")
    else:
        print("ERROR: No interactive element found!")

    # 5. Logcat summary
    print("\n=== STEP 5: LOGCAT SYSOPT_DBG SUMMARY ===")
    out = subprocess.run(["adb", "logcat", "-d"], capture_output=True, text=True, errors="ignore").stdout
    dbg = [l for l in out.splitlines() if "SYSOPT_DBG" in l]
    print(f"Total SYSOPT_DBG lines: {len(dbg)}")
    for l in dbg[-25:]:
        print(l)


if __name__ == "__main__":
    main()
