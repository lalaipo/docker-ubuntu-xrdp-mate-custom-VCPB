import re
import subprocess
import time
import xml.etree.ElementTree as ET


def dump_ui(path="/sdcard/window_dump.xml", local="./window_dump.xml"):
    subprocess.run(["adb", "shell", "uiautomator", "dump", path], check=False)
    subprocess.run(["adb", "pull", path, local], check=False)
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
            text = node.attrib.get("text", "")
            desc = node.attrib.get("content-desc", "")
            cls = node.attrib.get("class", "")
            bounds = node.attrib.get("bounds", "")
            clickable = node.attrib.get("clickable", "false") == "true"
            nodes.append({
                "text": text,
                "desc": desc,
                "class": cls,
                "bounds": bounds,
                "clickable": clickable
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


def tap(x, y):
    print(f"--> TAP at ({x}, {y})")
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=False)


def take_screen(remote="/sdcard/screen.png", local="./screen.png"):
    subprocess.run(["adb", "shell", "screencap", "-p", remote], check=False)
    subprocess.run(["adb", "pull", remote, local], check=False)


def main():
    print("=== STEP 1: INITIAL UI ===")
    xml1 = dump_ui("/sdcard/ui_initial.xml", "./ui_initial.xml")
    nodes1 = parse_nodes(xml1)
    texts1 = [n["text"] for n in nodes1 if n["text"]]
    descs1 = [n["desc"] for n in nodes1 if n["desc"]]
    print("Initial texts:", texts1)
    print("Initial descs:", descs1)

    # 1. Test clicking "Game Enhance"
    print("\n=== STEP 2: TAP 'Game Enhance' ===")
    game_enhance = next((n for n in nodes1 if "game enhance" in n["text"].lower()), None)
    if game_enhance:
        x, y = center_of(game_enhance["bounds"])
        print(f"Found 'Game Enhance' at {x}, {y}. Tapping...")
        tap(x, y)
    else:
        print("Fallback tap at (288, 367)")
        tap(288, 367)

    time.sleep(2)
    take_screen("/sdcard/screen_after_ge.png", "./screen_after_ge.png")

    xml2 = dump_ui("/sdcard/ui_after_ge.xml", "./ui_after_ge.xml")
    nodes2 = parse_nodes(xml2)
    texts2 = [n["text"] for n in nodes2 if n["text"]]
    descs2 = [n["desc"] for n in nodes2 if n["desc"]]
    print("Texts after 'Game Enhance':", texts2)
    print("Descs after 'Game Enhance':", descs2)

    # Check if a dialog or new screen appeared
    for n in nodes2:
        if n["text"] and n["text"] not in texts1:
            print(f"NEW ELEMENT: {n}")
        if any(kw in (n["text"] + " " + n["desc"]).lower() for kw in ["confirm", "apply", "ok", "enable", "start", "opt"]):
            x, y = center_of(n["bounds"])
            print(f"Action button found: {n}. Tapping...")
            tap(x, y)
            time.sleep(1)

    # 2. Test clicking "One-Click Restore"
    print("\n=== STEP 3: TAP 'One-Click Restore' ===")
    restore = next((n for n in nodes1 if "restore" in n["text"].lower()), None)
    if restore:
        x, y = center_of(restore["bounds"])
        print(f"Found 'Restore' at {x}, {y}. Tapping...")
        tap(x, y)
        time.sleep(2)
        take_screen("/sdcard/screen_after_restore.png", "./screen_after_restore.png")
        xml3 = dump_ui("/sdcard/ui_after_restore.xml", "./ui_after_restore.xml")
        nodes3 = parse_nodes(xml3)
        print("Texts after 'Restore':", [n["text"] for n in nodes3 if n["text"]])

    # 3. Dump logcat SYSOPT_DBG
    print("\n=== STEP 4: LOGCAT INSPECTION ===")
    out = subprocess.run(["adb", "logcat", "-d"], capture_output=True, text=True, errors="ignore").stdout
    dbg_lines = [l for l in out.splitlines() if "SYSOPT_DBG" in l]
    print(f"Found {len(dbg_lines)} SYSOPT_DBG lines:")
    for l in dbg_lines[-30:]:
        print(l)


if __name__ == "__main__":
    main()
