from __future__ import annotations

import base64
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any, Optional

os.environ.setdefault("PYAUTO_GUI_NO_FAILSAFE", "1")

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from .tmwebdriver import TMWebDriver  # noqa: E402
from . import simphtml  # noqa: E402

mcp = FastMCP(
    name="agent-browser",
    instructions=(
        "Browser automation tools for the user's real Chrome session via TMWebDriver/CDP bridge. "
        "Supports page scanning, JS execution, CDP commands, screenshots, cookies, and desktop physical input."
    ),
)

_driver: Optional[TMWebDriver] = None
_DRIVER_PORT = int(os.environ.get("AGENT_BROWSER_TMWD_PORT", "18765"))
_DRIVER_HOST = os.environ.get("AGENT_BROWSER_TMWD_HOST", "127.0.0.1")


def chrome_extension_dir() -> Path:
    return ROOT / "chrome_extension"


def ensure_config_js() -> Path:
    path = chrome_extension_dir() / "config.js"
    if not path.exists():
        path.write_text(
            f"const TID = '__ljq_{hex(random.randint(0, 99999999))[2:8]}';",
            encoding="utf-8",
        )
    return path


def get_driver() -> TMWebDriver:
    global _driver
    ensure_config_js()
    if _driver is None:
        _driver = TMWebDriver(host=_DRIVER_HOST, port=_DRIVER_PORT)
    return _driver


def require_driver() -> TMWebDriver:
    driver = get_driver()
    return driver


def active_sessions() -> list[dict[str, Any]]:
    return require_driver().get_all_sessions()


def ensure_sessions() -> list[dict[str, Any]]:
    sessions = active_sessions()
    if not sessions:
        raise RuntimeError(
            "No connected browser tabs. Load the unpacked extension from the reported extension path, "
            "keep this MCP server running via Hermes, and open a normal http/https page in Chrome."
        )
    return sessions


def normalize_session_id(session_id: Optional[str]) -> Optional[str]:
    if session_id is None:
        return None
    return str(session_id)


def switch_session(session_id: Optional[str] = None, url_pattern: Optional[str] = None) -> str:
    driver = require_driver()
    if session_id is not None:
        sid = str(session_id)
        found = next((s for s in active_sessions() if str(s.get("id")) == sid), None)
        if not found:
            raise RuntimeError(f"Session {sid} not found")
        driver.default_session_id = sid
        return sid
    if url_pattern:
        sid = driver.set_session(url_pattern)
        if not sid:
            raise RuntimeError(f"No session matching url pattern: {url_pattern}")
        return str(sid)
    if driver.default_session_id:
        return str(driver.default_session_id)
    sessions = ensure_sessions()
    driver.default_session_id = str(sessions[0]["id"])
    return str(driver.default_session_id)


def exec_js(script: str, session_id: Optional[str] = None, timeout: float = 15.0) -> dict[str, Any]:
    driver = require_driver()
    if session_id is not None:
        driver.default_session_id = str(session_id)
    return driver.execute_js(script, timeout=timeout)


def compact_tabs() -> list[dict[str, Any]]:
    tabs = []
    for sess in active_sessions():
        item = dict(sess)
        item.pop("connected_at", None)
        item.pop("type", None)
        tabs.append(item)
    return tabs


@mcp.tool(description="Return extension path, bridge ports, and connection status for setup/diagnostics.")
def get_setup_status() -> dict[str, Any]:
    driver = get_driver()
    sessions = compact_tabs()
    return {
        "extension_name": "TMWD CDP Bridge",
        "extension_path": str(chrome_extension_dir()),
        "config_js": str(ensure_config_js()),
        "tmwebdriver_host": _DRIVER_HOST,
        "tmwebdriver_ws_port": _DRIVER_PORT,
        "tmwebdriver_http_port": _DRIVER_PORT + 1,
        "remote_mode": driver.is_remote,
        "connected_tabs": len(sessions),
        "default_session_id": driver.default_session_id,
        "tabs": sessions,
        "notes": [
            "Load the unpacked extension from extension_path in chrome://extensions with Developer Mode enabled.",
            "Keep a normal http/https page open in Chrome; about:blank is not enough.",
            "This MCP server hosts TMWebDriver itself unless another compatible bridge is already listening.",
        ],
    }


@mcp.tool(description="List currently connected browser tabs/sessions.")
def list_tabs() -> dict[str, Any]:
    sessions = compact_tabs()
    return {
        "default_session_id": require_driver().default_session_id,
        "tabs": sessions,
    }


@mcp.tool(description="Set the active browser tab by session id or URL substring.")
def switch_tab(session_id: Optional[str] = None, url_pattern: Optional[str] = None) -> dict[str, Any]:
    sid = switch_session(session_id=session_id, url_pattern=url_pattern)
    return {"active_session_id": sid, "tabs": compact_tabs()}


@mcp.tool(description="Navigate the current tab to a URL using real-browser JS navigation.")
def open_url(url: str, session_id: Optional[str] = None, timeout: float = 15.0) -> dict[str, Any]:
    if session_id is not None:
        switch_session(session_id=session_id)
    driver = require_driver()
    driver.jump(url, timeout=timeout)
    return {
        "status": "ok",
        "active_session_id": driver.default_session_id,
        "url": url,
    }


@mcp.tool(description="Open a new browser tab with the given URL.")
def open_new_tab(url: str) -> dict[str, Any]:
    driver = require_driver()
    result = driver.newtab(url)
    return {"status": "ok", "result": result, "tabs": compact_tabs()}


@mcp.tool(description="Get absolute path to the unpacked Chrome extension directory for manual installation.")
def extension_path() -> dict[str, Any]:
    return {
        "extension_path": str(chrome_extension_dir()),
        "config_js": str(ensure_config_js()),
    }


@mcp.tool(description="List Chrome extensions visible to the CDP bridge extension itself.")
def list_extensions(session_id: Optional[str] = None) -> dict[str, Any]:
    if session_id is not None:
        switch_session(session_id=session_id)
    return exec_js(json.dumps({"cmd": "management", "method": "list"}), timeout=20.0)


@mcp.tool(description="Read the current page as simplified HTML/text, preserving login state from the real browser.")
def scan_page(
    session_id: Optional[str] = None,
    text_only: bool = False,
    cutlist: bool = True,
    maxchars: int = 35000,
    instruction: str = "",
    extra_js: str = "",
) -> dict[str, Any]:
    driver = require_driver()
    if session_id is not None:
        switch_session(session_id=session_id)
    ensure_sessions()
    content = simphtml.get_html(
        driver,
        cutlist=cutlist,
        maxchars=maxchars,
        instruction=instruction,
        extra_js=extra_js,
        text_only=text_only,
    )
    return {
        "status": "success",
        "active_session_id": driver.default_session_id,
        "tabs": compact_tabs(),
        "content": content,
    }


@mcp.tool(description="Execute arbitrary JS in the current page context or send JSON CDP bridge commands through the page bridge.")
def execute_js(
    script: str,
    session_id: Optional[str] = None,
    no_monitor: bool = False,
) -> dict[str, Any]:
    driver = require_driver()
    if session_id is not None:
        switch_session(session_id=session_id)
    ensure_sessions()
    return simphtml.execute_js_rich(script, driver, no_monitor=no_monitor)


@mcp.tool(description="Call a single Chrome DevTools Protocol command on the current or specified tab.")
def cdp_command(
    method: str,
    params_json: str = "{}",
    session_id: Optional[str] = None,
    tab_id: Optional[int] = None,
) -> dict[str, Any]:
    if session_id is not None:
        switch_session(session_id=session_id)
    params = json.loads(params_json or "{}")
    payload: dict[str, Any] = {"cmd": "cdp", "method": method, "params": params}
    if tab_id is not None:
        payload["tabId"] = tab_id
    return exec_js(json.dumps(payload), timeout=20.0)


@mcp.tool(description="Run a CDP bridge batch command; pass the full JSON command object as text.")
def cdp_batch(batch_json: str, session_id: Optional[str] = None) -> dict[str, Any]:
    if session_id is not None:
        switch_session(session_id=session_id)
    payload = json.loads(batch_json)
    if payload.get("cmd") != "batch":
        raise RuntimeError("batch_json must be a JSON object with cmd='batch'")
    return exec_js(json.dumps(payload), timeout=30.0)


@mcp.tool(description="Get cookies for the current page or specified tab via the Chrome extension bridge.")
def get_cookies(session_id: Optional[str] = None, tab_id: Optional[int] = None) -> dict[str, Any]:
    if session_id is not None:
        switch_session(session_id=session_id)
    payload: dict[str, Any] = {"cmd": "cookies"}
    if tab_id is not None:
        payload["tabId"] = tab_id
    return exec_js(json.dumps(payload), timeout=15.0)


@mcp.tool(description="Capture a screenshot of the current page/tab via CDP and optionally save it to a file path.")
def capture_page_screenshot(
    session_id: Optional[str] = None,
    tab_id: Optional[int] = None,
    format: str = "png",
    save_path: str = "",
) -> dict[str, Any]:
    if session_id is not None:
        switch_session(session_id=session_id)
    payload: dict[str, Any] = {
        "cmd": "cdp",
        "method": "Page.captureScreenshot",
        "params": {"format": format},
    }
    if tab_id is not None:
        payload["tabId"] = tab_id
    result = exec_js(json.dumps(payload), timeout=20.0)
    data = result.get("data")
    if isinstance(data, dict) and "data" in data:
        b64 = data["data"]
    else:
        b64 = data
    out: dict[str, Any] = {"format": format, "base64": b64}
    if save_path:
        path = Path(save_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(b64))
        out["saved_to"] = str(path)
    return out


@mcp.tool(description="Take a desktop screenshot of the whole screen using mss; useful for physical-input verification.")
def capture_desktop_screenshot(save_path: str = "") -> dict[str, Any]:
    import mss
    from PIL import Image

    path = Path(save_path).expanduser().resolve() if save_path else (ROOT / "temp_desktop.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        img.save(path)
    return {"saved_to": str(path), "size": path.stat().st_size}


@mcp.tool(description="Move the real mouse cursor to screen coordinates.")
def mouse_move(x: int, y: int, duration: float = 0.0) -> dict[str, Any]:
    import pyautogui

    pyautogui.moveTo(x, y, duration=duration)
    return {"status": "ok", "x": x, "y": y}


@mcp.tool(description="Click on the real desktop at screen coordinates.")
def mouse_click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.1,
) -> dict[str, Any]:
    import pyautogui

    if x is not None and y is not None:
        pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
    else:
        pyautogui.click(clicks=clicks, interval=interval, button=button)
    return {"status": "ok", "x": x, "y": y, "button": button, "clicks": clicks}


@mcp.tool(description="Drag the real mouse from one point to another.")
def mouse_drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.3, button: str = "left") -> dict[str, Any]:
    import pyautogui

    pyautogui.moveTo(x1, y1)
    pyautogui.dragTo(x2, y2, duration=duration, button=button)
    return {"status": "ok", "from": [x1, y1], "to": [x2, y2], "button": button}


@mcp.tool(description="Type text via the real keyboard, optionally after clicking a field.")
def type_text(text: str, interval: float = 0.01, click_x: Optional[int] = None, click_y: Optional[int] = None) -> dict[str, Any]:
    import pyautogui

    if click_x is not None and click_y is not None:
        pyautogui.click(click_x, click_y)
        time.sleep(0.1)
    pyautogui.write(text, interval=interval)
    return {"status": "ok", "typed_chars": len(text)}


@mcp.tool(description="Send a hotkey chord like 'command,l' or 'ctrl,shift,p' via the real keyboard.")
def hotkey(keys_csv: str) -> dict[str, Any]:
    import pyautogui

    keys = [k.strip() for k in keys_csv.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("keys_csv must contain at least one key")
    pyautogui.hotkey(*keys)
    return {"status": "ok", "keys": keys}


@mcp.tool(description="Report the current desktop mouse position and primary screen size.")
def pointer_info() -> dict[str, Any]:
    import pyautogui

    x, y = pyautogui.position()
    w, h = pyautogui.size()
    return {"x": x, "y": y, "screen_width": w, "screen_height": h}


if __name__ == "__main__":
    ensure_config_js()
    get_driver()
    mcp.run(transport="stdio")
