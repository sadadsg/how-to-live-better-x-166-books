#!/usr/bin/env python3
"""tools/og_template.html → og.png (1280×640)。改文案改模板，重跑本脚本。"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL, OUT = ROOT / "tools" / "og_template.html", ROOT / "og.png"


def find_chrome():
    for name in ("Google Chrome", "Chromium", "Microsoft Edge"):
        p = Path("/Applications") / f"{name}.app" / "Contents" / "MacOS" / name
        if p.exists():
            return str(p)
    return shutil.which("google-chrome") or shutil.which("chromium")


chrome = find_chrome()
if not chrome:
    sys.exit("未找到 Chrome/Chromium，装一个或改 find_chrome()")
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                "--force-device-scale-factor=1", "--force-color-profile=srgb",
                f"--screenshot={OUT}", "--window-size=1280,640", TPL.as_uri()],
               check=True, capture_output=True)
print(f"OK {OUT} ({OUT.stat().st_size // 1024}KB)")
