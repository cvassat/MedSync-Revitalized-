#!/usr/bin/env python3
"""MedSync7 smoke driver.

Usage:
  python smoke.py screenshot          # login page screenshot
  python smoke.py screenshot-calc     # calculator screenshot (no auth needed)
  python smoke.py test                # AppTest unit verification (no browser)
  python smoke.py all                 # screenshot + test

Works from any working directory; the app path is resolved from this file.
Screenshots → /tmp/shots/
"""
from __future__ import annotations
import asyncio
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
APP = REPO_ROOT / "med_sync_app_final.py"
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
SHOTS = Path("/tmp/shots")
PORT = 8501
URL = f"http://localhost:{PORT}"


# ---------------------------------------------------------------------------
# Browser helpers (Playwright)
# ---------------------------------------------------------------------------

async def _browser_screenshot(url: str, wait_selector: str, out: Path) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=CHROMIUM,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_selector(wait_selector, timeout=20_000)
        SHOTS.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out), full_page=True)
        await browser.close()
    print(f"screenshot → {out}")


def _wait_for_server(url: str, timeout: int = 30) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"Server at {url} did not start within {timeout}s")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_screenshot() -> None:
    """Screenshot the live login page (server must already be running on 8501)."""
    _wait_for_server(URL, timeout=5)
    asyncio.run(_browser_screenshot(
        URL,
        "input[aria-label='Email']",
        SHOTS / "login.png",
    ))


def cmd_screenshot_calc() -> None:
    """Launch a patched (auth-bypassed) server on 8502 and screenshot the calculator."""
    import tempfile
    src = APP.read_text()
    bypass = "st.session_state.setdefault('user', True)\n"
    patched = src.replace("if 'user' not in st.session_state:", bypass + "if 'user' not in st.session_state:")
    tmp = Path(tempfile.mktemp(suffix=".py"))
    tmp.write_text(patched)
    proc = subprocess.Popen(
        ["streamlit", "run", str(tmp), "--server.port", "8502", "--server.headless", "true"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server("http://localhost:8502")
        asyncio.run(_browser_screenshot(
            "http://localhost:8502",
            "input[aria-label='Number of existing medications']",
            SHOTS / "calculator.png",
        ))
    finally:
        proc.terminate()
        tmp.unlink(missing_ok=True)


def cmd_test() -> None:
    """Run AppTest smoke: auth bypass → fill 1 med + 1 new → calculate → assert output."""
    from streamlit.testing.v1 import AppTest
    from datetime import date, timedelta

    at = AppTest.from_file(str(APP), default_timeout=30)
    at.session_state["user"] = True
    at.run()

    at.number_input[0].set_value(1)
    at.run()

    at.text_input(key="name_0").set_value("Metformin")
    at.number_input(key="dose_0").set_value(2)
    at.number_input(key="remaining_0").set_value(10)
    at.text_input(key="new_name").set_value("Lisinopril")
    at.number_input(key="new_dose").set_value(1)
    at.date_input[0].set_value(date.today() + timedelta(days=30))
    at.run()

    at.button[0].click()
    at.run()

    assert not at.error, f"Unexpected errors: {[e.value for e in at.error]}"
    subheaders = [e.value for e in at.subheader]
    assert "Sync Plan" in subheaders, f"Expected 'Sync Plan' subheader, got {subheaders}"

    lines = "\n".join(m.value for m in at.markdown)
    assert "Metformin" in lines, "Metformin missing from output"
    assert "Lisinopril (new)" in lines, "Lisinopril (new) missing from output"
    print("AppTest PASSED — Sync Plan rendered with both medications")


COMMANDS = {
    "screenshot": cmd_screenshot,
    "screenshot-calc": cmd_screenshot_calc,
    "test": cmd_test,
    "all": lambda: (cmd_screenshot_calc(), cmd_test()),
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}. Available: {', '.join(COMMANDS)}")
        sys.exit(1)
    COMMANDS[cmd]()
