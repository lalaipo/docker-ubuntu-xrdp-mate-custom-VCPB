import re
import subprocess
import time


def dump_ui(path="/sdcard/window_dump.xml", local="./window_dump.xml"):
    subprocess.run(["adb", "shell", "uiautomator", "dump", path], check=False)
    subprocess.run(["adb", "pull", path, local], check=False)
    with open(local, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def find_bounds(xml_text, keywords):
    results = []
    for m in re.finditer(r'<node[^>]*text="([^"]*)"[^>]*bounds="(\[[0-9,-]+\]\[[0-9,-]+\])"[^>]*/>', xml_text):
        text, bounds = m.group(1), m.group(2)
        for kw in keywords:
            if kw.lower() in text.lower():
                results.append((text, bounds))
    return results


def center_of(bounds):
    nums = list(map(int, re.findall(r'-?\d+', bounds)))
    x1, y1, x2, y2 = nums
    return (x1 + x2) // 2, (y1 + y2) // 2


def tap(x, y):
    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)], check=False)


def main():
    xml_text = dump_ui("/sdcard/window_dump1.xml", "./window_dump1.xml")
    print("=== first dump matches ===")
    keywords = ["Optimization", "Boost", "Protect", "Performance", "Advanced", "Tools"]
    matches = find_bounds(xml_text, keywords)
    print(matches)

    advanced_hits = [m for m in matches if "advanced" in m[0].lower() or "tools" in m[0].lower()]
    if advanced_hits:
        x, y = center_of(advanced_hits[0][1])
        print(f"Tapping nav entry: {advanced_hits[0]} at {x},{y}")
        tap(x, y)
        time.sleep(2)
        xml_text = dump_ui("/sdcard/window_dump2.xml", "./window_dump2.xml")
        matches = find_bounds(xml_text, ["Optimization", "Boost", "Protect", "Performance"])
        print("=== post-nav matches ===", matches)

    if matches:
        x, y = center_of(matches[0][1])
        print(f"Tapping toggle candidate: {matches[0]} at {x},{y}")
        tap(x, y)
        time.sleep(1)
        tap(x, y)
        time.sleep(1)
        tap(x, y)
        time.sleep(1)
    else:
        print("NO TOGGLE MATCH FOUND IN UI DUMP")


if __name__ == "__main__":
    main()
