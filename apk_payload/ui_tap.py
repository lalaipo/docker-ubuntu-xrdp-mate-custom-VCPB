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


def swipe_up():
    print("--> SWIPE UP (scroll down)")
    subprocess.run(["adb", "shell", "input", "swipe", "540", "1400", "540", "400", "400"], check=False)
    time.sleep(1.5)


def print_visible_texts(nodes):
    texts = [n["text"] for n in nodes if n["text"]]
    descs = [n["desc"] for n in nodes if n["desc"]]
    print("Visible texts:", texts)
    if descs:
        print("Visible descs:", descs)


def main():
    print("=== STEP 1: INITIAL UI ===")
    xml = dump_ui("/sdcard/ui_initial.xml", "./ui_initial.xml")
    nodes = parse_nodes(xml)
    print_visible_texts(nodes)

    # Let's scroll down up to 3 times looking for "Advanced Tools" or toggle keywords
    target_kws = ["virtual", "gpu", "wifi", "boost", "advanced", "protect", "speed", "turbo", "battery", "performance"]

    found_target = None
    for attempt in range(4):
        print(f"\n--- Search round {attempt} ---")
        for n in nodes:
            combined = (n["text"] + " " + n["desc"]).lower()
            for kw in target_kws:
                if kw in combined:
                    print(f"MATCH FOUND: text={repr(n['text'])} desc={repr(n['desc'])} bounds={n['bounds']} class={n['class']}")
                    if any(k in combined for k in ["virtual", "gpu", "engine", "wifi", "battery"]):
                        found_target = n
                        break
            if found_target:
                break

        if found_target:
            break

        print("Target not in current viewport, scrolling down...")
        swipe_up()
        xml = dump_ui(f"/sdcard/ui_scroll_{attempt}.xml", f"./ui_scroll_{attempt}.xml")
        nodes = parse_nodes(xml)
        print_visible_texts(nodes)

    if found_target:
        print(f"\nTarget to tap: {found_target}")
        x, y = center_of(found_target["bounds"])
        # If it's a row, the switch might be on the right side of the row!
        # So we tap center first, then right edge
        nums = list(map(int, re.findall(r"-?\d+", found_target["bounds"])))
        x1, y1, x2, y2 = nums
        right_x = x2 - 80
        center_y = (y1 + y2) // 2

        print(f"Tapping target row center ({x}, {y})")
        tap(x, y)
        time.sleep(1)
        print(f"Tapping target switch area on right ({right_x}, {center_y})")
        tap(right_x, center_y)
        time.sleep(1)
        tap(right_x, center_y)
        time.sleep(1)
    else:
        print("\nNo specific toggle found by keyword, dumping all clickable elements on current screen:")
        for n in nodes:
            if n["clickable"] or "button" in n["class"].lower() or "switch" in n["class"].lower():
                print(f"Clickable: {n}")
                x, y = center_of(n["bounds"])
                tap(x, y)
                time.sleep(1)


if __name__ == "__main__":
    main()
