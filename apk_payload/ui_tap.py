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
        # In Android/Compose switch rows, the thumb sits 90px from the right edge
        return x2 - 90, (y1 + y2) // 2
    return 950, 500


def tap(x, y):
    print(f"--> [TAP] at ({x}, {y})")
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=False)


def swipe_left():
    print("--> [SWIPE LEFT] from Page 1 to Page 2")
    subprocess.run(["adb", "shell", "input", "swipe", "950", "900", "80", "900", "350"], check=False)
    time.sleep(2)


def take_screen(remote="/sdcard/screen.png", local="./screen.png"):
    subprocess.run(["adb", "shell", "screencap", "-p", remote], check=False)
    subprocess.run(["adb", "pull", remote, local], check=False)


def main():
    print("=== STEP 0: WAIT 4S FOR APP LAUNCH ===")
    time.sleep(4)

    # 1. Check Page 1
    xml1 = dump_ui("/sdcard/ui_p1.xml", "./ui_p1.xml")
    nodes1 = parse_nodes(xml1)
    texts1 = [n["text"] for n in nodes1 if n["text"]]
    print(f"Page 1 visible texts: {texts1}")

    # 2. Swipe left to navigate to Page 2 (Graphics & Performance toggles)
    print("\n=== STEP 1: SWIPING LEFT TO PAGE 2 ===")
    swipe_left()

    # Verify Page 2
    xml2 = dump_ui("/sdcard/ui_p2.xml", "./ui_p2.xml")
    nodes2 = parse_nodes(xml2)
    texts2 = [n["text"] for n in nodes2 if n["text"]]
    descs2 = [n["desc"] for n in nodes2 if n["desc"]]
    print(f"Page 2 visible texts: {texts2}")
    print(f"Page 2 visible descs: {descs2}")

    # 3. Locate target toggle
    target_kws = ["virtual gpu", "hardware composition", "vulkan", "superperformance", "compilation"]
    target_node = None

    for n in nodes2:
        combined = (n["text"] + " " + n["desc"]).lower()
        for kw in target_kws:
            if kw in combined:
                print(f"Found target toggle: text={repr(n['text'])}, desc={repr(n['desc'])}, bounds={n['bounds']}")
                target_node = n
                break
        if target_node:
            break

    if not target_node:
        print("Target keyword not found in current view. Trying to scroll down on Page 2...")
        subprocess.run(["adb", "shell", "input", "swipe", "540", "1200", "540", "600", "300"], check=False)
        time.sleep(1.5)
        xml2_scroll = dump_ui("/sdcard/ui_p2_scroll.xml", "./ui_p2_scroll.xml")
        nodes2 = parse_nodes(xml2_scroll)
        print("Page 2 scrolled texts:", [n["text"] for n in nodes2 if n["text"]])
        for n in nodes2:
            combined = (n["text"] + " " + n["desc"]).lower()
            for kw in target_kws:
                if kw in combined:
                    print(f"Found target toggle after scroll: text={repr(n['text'])}, bounds={n['bounds']}")
                    target_node = n
                    break
            if target_node:
                break

    if target_node:
        sx, sy = switch_coords(target_node["bounds"])
        print(f"\nTarget selected: {target_node['text']} at bounds {target_node['bounds']}")
        print(f"Switch coordinates to tap: ({sx}, {sy})")

        # 4. CAPTURE BEFORE SCREENSHOT
        print("\n=== STEP 2: CAPTURING screen_before_toggle.png ===")
        take_screen("/sdcard/screen_before_toggle.png", "./screen_before_toggle.png")

        # 5. TAP TOGGLE
        print(f"\n=== STEP 3: TAPPING SWITCH AT ({sx}, {sy}) ===")
        tap(sx, sy)
        time.sleep(2)

        # 6. CAPTURE AFTER SCREENSHOT
        print("\n=== STEP 4: CAPTURING screen_after_toggle.png ===")
        take_screen("/sdcard/screen_after_toggle.png", "./screen_after_toggle.png")

        # Dump post-tap UI
        dump_ui("/sdcard/ui_after_toggle.xml", "./ui_after_toggle.xml")
    else:
        print("WARNING: Could not find specific target toggle. Capturing fallback screenshots.")
        take_screen("/sdcard/screen_before_toggle.png", "./screen_before_toggle.png")
        # Tap switch area on right side of screen
        tap(950, 480)
        time.sleep(2)
        take_screen("/sdcard/screen_after_toggle.png", "./screen_after_toggle.png")

    # 7. Print Logcat summary
    print("\n=== STEP 5: LOGCAT SYSOPT_DBG ===")
    out = subprocess.run(["adb", "logcat", "-d"], capture_output=True, text=True, errors="ignore").stdout
    dbg = [l for l in out.splitlines() if "SYSOPT_DBG" in l]
    print(f"SYSOPT_DBG lines ({len(dbg)} total):")
    for l in dbg[-20:]:
        print(l)


if __name__ == "__main__":
    main()
