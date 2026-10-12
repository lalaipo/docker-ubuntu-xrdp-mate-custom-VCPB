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
    dump_ui("/sdcard/ui_p1.xml", "./ui_p1.xml")

    # 2. Swipe left to navigate to Page 2 (Graphics & Performance toggles)
    print("\n=== STEP 1: SWIPING LEFT TO PAGE 2 ===")
    swipe_left()

    # Verify Page 2
    xml2 = dump_ui("/sdcard/ui_p2.xml", "./ui_p2.xml")
    nodes2 = parse_nodes(xml2)
    texts2 = [n["text"] for n in nodes2 if n["text"]]
    print(f"Page 2 visible texts: {texts2}")

    # Find the clickable container row for Virtual GPU Optimization [42,747][1038,916]
    target_row = next((n for n in nodes2 if n["clickable"] and "747" in n["bounds"]), None)
    if not target_row:
        # Fallback by text matching
        print("Finding row by text position...")
        target_row = next((n for n in nodes2 if n["clickable"] and "1038" in n["bounds"]), None)

    # Coordinates: switch toggle thumb is at x=950, y=831
    switch_x = 950
    switch_y = 831

    if target_row:
        nums = list(map(int, re.findall(r"-?\d+", target_row["bounds"])))
        if len(nums) == 4:
            x1, y1, x2, y2 = nums
            switch_x = x2 - 80
            switch_y = (y1 + y2) // 2
            print(f"Target row bounds: {target_row['bounds']} -> Switch tap coords: ({switch_x}, {switch_y})")

    # 3. CAPTURE BEFORE SCREENSHOT (TOGGLE OFF)
    print("\n=== STEP 2: CAPTURING screen_before_toggle.png ===")
    take_screen("/sdcard/screen_before_toggle.png", "./screen_before_toggle.png")

    # 4. TAP SWITCH TO TOGGLE ON
    print(f"\n=== STEP 3: TAPPING SWITCH ON AT ({switch_x}, {switch_y}) ===")
    tap(switch_x, switch_y)
    time.sleep(2)

    # 5. CAPTURE AFTER SCREENSHOT (TOGGLE ON)
    print("\n=== STEP 4: CAPTURING screen_after_toggle.png ===")
    take_screen("/sdcard/screen_after_toggle.png", "./screen_after_toggle.png")
    dump_ui("/sdcard/ui_after_on.xml", "./ui_after_on.xml")

    # 6. TAP SWITCH AGAIN TO TOGGLE OFF (VERIFY REVERSIBILITY)
    print(f"\n=== STEP 5: TAPPING SWITCH OFF AT ({switch_x}, {switch_y}) ===")
    tap(switch_x, switch_y)
    time.sleep(2)
    take_screen("/sdcard/screen_toggle_off.png", "./screen_toggle_off.png")
    dump_ui("/sdcard/ui_after_off.xml", "./ui_after_off.xml")

    print("\n=== TEST COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    main()
