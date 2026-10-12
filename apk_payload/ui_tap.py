import re
import subprocess
import time
import xml.etree.ElementTree as ET


def dump_ui(remote="/sdcard/window_dump.xml", local="./window_dump.xml"):
    subprocess.run(["adb", "shell", "uiautomator", "dump", remote], check=False)
    subprocess.run(["adb", "pull", remote, local], check=False)
    try:
        with open(local, "r", encoding="utf-8", errors="ignore") as f:
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
        return x2 - 90, (y1 + y2) // 2
    return 950, 500


def tap(x, y):
    print(f"--> [TAP] at ({x}, {y})")
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=False)


def swipe_up():
    print("--> [SWIPE UP] (scroll down)")
    subprocess.run(["adb", "shell", "input", "swipe", "540", "1400", "540", "500", "350"], check=False)
    time.sleep(1.5)


def take_screen(remote="/sdcard/screen.png", local="./screen.png"):
    subprocess.run(["adb", "shell", "screencap", "-p", remote], check=False)
    subprocess.run(["adb", "pull", remote, local], check=False)


def main():
    print("=== STEP 0: WAIT 3S FOR APP START ===")
    time.sleep(3)

    # 1. Advance through Onboarding / Guide if present
    for step in range(5):
        xml = dump_ui(f"/sdcard/step_{step}.xml", f"./step_{step}.xml")
        nodes = parse_nodes(xml)
        texts = [n["text"] for n in nodes if n["text"]]
        print(f"Step {step} texts: {texts}")

        # Check for Next / Agree / Start / Enter buttons
        next_btn = next((n for n in nodes if n["text"].lower() in ["next", "agree", "start", "enter", "finish", "continue", "get started"]), None)
        if next_btn:
            # Check if there is an agreement checkbox to check first!
            checkbox = next((n for n in nodes if "agree" in (n["text"] + " " + n["desc"]).lower() and not n["checked"] and n != next_btn), None)
            if checkbox:
                cx, cy = center_of(checkbox["bounds"])
                print(f"Checking agreement checkbox at ({cx}, {cy})")
                tap(cx, cy)
                time.sleep(1)

            cx, cy = center_of(next_btn["bounds"])
            print(f"Tapping '{next_btn['text']}' at ({cx}, {cy})")
            tap(cx, cy)
            time.sleep(2)
        else:
            # Also check if there is a big bottom clickable button
            big_btn = next((n for n in nodes if n["clickable"] and "1584" in n["bounds"]), None)
            if big_btn:
                cx, cy = center_of(big_btn["bounds"])
                print(f"Tapping bottom action button at ({cx}, {cy})")
                tap(cx, cy)
                time.sleep(2)
            else:
                print("No onboarding button detected, moving to main UI.")
                break

    # 2. Main screen loaded
    time.sleep(2)
    xml_main = dump_ui("/sdcard/ui_main.xml", "./ui_main.xml")
    nodes_main = parse_nodes(xml_main)
    texts_main = [n["text"] for n in nodes_main if n["text"]]
    descs_main = [n["desc"] for n in nodes_main if n["desc"]]
    print(f"Main screen texts: {texts_main}")
    print(f"Main screen descs: {descs_main}")

    # Check for bottom navigation tabs: Home, Tools, My
    tools_tab = next((n for n in nodes_main if any(kw in (n["text"] + " " + n["desc"]).lower() for kw in ["tool", "advanced", "setting", "opt"])), None)
    if tools_tab:
        cx, cy = center_of(tools_tab["bounds"])
        print(f"Switching to tools tab at ({cx}, {cy})")
        tap(cx, cy)
        time.sleep(2)

    # 3. Search for toggles
    target_kws = ["virtual", "gpu", "compilation", "wifi", "boost", "speed", "hardware", "battery", "performance"]
    target_node = None

    for attempt in range(4):
        xml_curr = dump_ui(f"/sdcard/ui_tools_{attempt}.xml", f"./ui_tools_{attempt}.xml")
        nodes_curr = parse_nodes(xml_curr)
        for n in nodes_curr:
            comb = (n["text"] + " " + n["desc"]).lower()
            for kw in target_kws:
                if kw in comb:
                    print(f"MATCH: {n['text']} / {n['desc']} at {n['bounds']}")
                    target_node = n
                    break
            if target_node:
                break
        if target_node:
            break
        print("Scrolling down to find toggles...")
        swipe_up()

    # Fallback to any clickable row if specific keyword not found
    xml_curr = dump_ui("/sdcard/ui_tools_final.xml", "./ui_tools_final.xml")
    nodes_curr = parse_nodes(xml_curr)
    if not target_node:
        for n in nodes_curr:
            if n["clickable"] and n["text"]:
                target_node = n
                break

    if target_node:
        print(f"\nTarget toggle found: {target_node}")
        sx, sy = switch_coords(target_node["bounds"])

        # Capture BEFORE screenshot
        print("\n=== CAPTURING screen_before_toggle.png ===")
        take_screen("/sdcard/screen_before_toggle.png", "./screen_before_toggle.png")

        # Tap the toggle
        print(f"\n=== TAPPING TOGGLE at ({sx}, {sy}) ===")
        tap(sx, sy)
        time.sleep(2)

        # Capture AFTER screenshot
        print("\n=== CAPTURING screen_after_toggle.png ===")
        take_screen("/sdcard/screen_after_toggle.png", "./screen_after_toggle.png")

        # Tap toggle again to verify OFF
        print(f"\n=== TAPPING TOGGLE OFF at ({sx}, {sy}) ===")
        tap(sx, sy)
        time.sleep(2)
        take_screen("/sdcard/screen_toggle_off.png", "./screen_toggle_off.png")
    else:
        print("ERROR: No toggle found!")
        take_screen("/sdcard/screen_before_toggle.png", "./screen_before_toggle.png")
        take_screen("/sdcard/screen_after_toggle.png", "./screen_after_toggle.png")


if __name__ == "__main__":
    main()
