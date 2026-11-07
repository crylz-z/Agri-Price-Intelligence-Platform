"""Screenshot dashboard pages at 1440 and 375 px from a fresh server and browser.

    uv run --no-project --with playwright python scripts/screenshot.py [path?query ...]

e.g. `scripts/screenshot.py "" "?region=Central+Luzon" ulam`. It starts its own
server on a free port, so it always runs the current code, then opens a new
browser per width: a cold font cache is what exposes clipped chart labels. It
opens every expander and prints exceptions and console errors. PNGs go to
$SHOT_DIR (default: the system temp folder). Set $CHROME to use a local Chromium,
$SCHEME=dark to shoot the dark theme, and $APP to run another entry script (e.g.
one that serves the test fixtures when R2 is slow).
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

WIDTHS = (1440, 375)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return int(s.getsockname()[1])


def wait_healthy(base: str, server: subprocess.Popen[bytes]) -> None:
    for _ in range(120):
        if server.poll() is not None:
            sys.exit("streamlit exited before it was healthy")
        try:
            urllib.request.urlopen(f"{base}/_stcore/health", timeout=2)
            return
        except OSError:
            time.sleep(1)
    sys.exit("streamlit not healthy after 120 s")


def settle(page: Any) -> None:
    """Wait until the script stopped running and the page held still for 3 s."""
    count = "document.querySelectorAll('[data-testid=\"stElementContainer\"]').length"
    busy = "!!document.querySelector('[data-testid=\"stStatusWidget\"]')"
    last, still = -1, 0
    for _ in range(300):
        now = page.evaluate(count)
        still = still + 1 if now == last and now > 0 and not page.evaluate(busy) else 0
        if still == 3:
            return
        last = now
        time.sleep(1)
    print("  page still changing after 300 s")


def shoot(base: str, target: str, out: Path, exe: str | None) -> None:
    slug = target.replace("?", "_").replace("=", "-").replace("+", "-").strip("_")
    name = f"{os.getenv('SCHEME', 'light')}_{slug or 'home'}"
    with sync_playwright() as p:
        for width in WIDTHS:
            browser = p.chromium.launch(executable_path=exe)
            page = browser.new_page(
                viewport={"width": width, "height": 900},
                color_scheme=os.getenv("SCHEME", "light"),  # type: ignore[arg-type]
            )
            page.on(
                "console",
                lambda m: m.type == "error" and print("  console:", m.text[:300]),
            )
            page.goto(f"{base}/{target}")
            settle(page)
            for summary in page.locator("[data-testid='stExpander'] summary").all():
                summary.click()
            time.sleep(3)  # charts draw after the script finishes
            for exc in page.locator("[data-testid='stException']").all():
                print("  exception:", exc.inner_text()[-800:])
            # Streamlit scrolls inside its main container, so size to its height.
            height = page.evaluate(
                "Math.max(...[...document.querySelectorAll('*')].map(e => e.scrollHeight))"
            )
            scroll = page.evaluate("document.documentElement.scrollWidth")
            page.set_viewport_size({"width": width, "height": height})
            time.sleep(1)
            path = out / f"{name}_{width}.png"
            page.screenshot(path=str(path))
            flag = "  HORIZONTAL SCROLL" if scroll > width else ""
            print(f"{path} ({height} px tall){flag}")
            browser.close()


def main() -> None:
    targets = sys.argv[1:] or [""]
    out = Path(os.getenv("SHOT_DIR", tempfile.gettempdir()))
    port = free_port()
    base = f"http://localhost:{port}"
    server = subprocess.Popen(
        ["uv", "run", "python", "-m", "streamlit", "run", os.getenv("APP", "src/dashboard/app.py"),
         "--server.port", str(port), "--server.headless", "true"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )  # fmt: skip
    try:
        wait_healthy(base, server)
        for target in targets:
            shoot(base, target, out, os.getenv("CHROME"))
    finally:
        server.terminate()


if __name__ == "__main__":
    main()
