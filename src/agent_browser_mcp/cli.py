from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

from .server import ROOT, ensure_config_js, get_driver, chrome_extension_dir, mcp


def cmd_extension_path() -> int:
    path = chrome_extension_dir()
    ensure_config_js()
    print(path)
    return 0


def cmd_print_hermes_config() -> int:
    print(
        "mcp_servers:\n"
        "  agent_browser:\n"
        "    command: agent-browser-mcp\n"
        "    timeout: 120\n"
        "    connect_timeout: 60"
    )
    return 0


def _port_open(host: str, port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(1)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def cmd_doctor() -> int:
    ensure_config_js()
    driver = get_driver()
    ws_port = getattr(driver, "port", 18765)
    http_port = ws_port + 1
    sessions = []
    err = None
    try:
        sessions = driver.get_all_sessions()
    except Exception as e:
        err = str(e)
    payload = {
        "extension_path": str(chrome_extension_dir()),
        "config_js": str((chrome_extension_dir() / 'config.js').resolve()),
        "remote_mode": getattr(driver, "is_remote", False),
        "tmwebdriver_host": getattr(driver, "host", "127.0.0.1"),
        "tmwebdriver_ws_port": ws_port,
        "tmwebdriver_http_port": http_port,
        "ws_port_open": _port_open(getattr(driver, "host", "127.0.0.1"), ws_port),
        "http_port_open": _port_open(getattr(driver, "host", "127.0.0.1"), http_port),
        "connected_tabs": len(sessions),
        "tabs": sessions,
        "error": err,
        "next_steps": [
            "Load the unpacked extension in chrome://extensions from extension_path.",
            "Open a normal http/https page in Chrome.",
            "Run `hermes mcp test agent_browser` after adding the MCP config.",
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-browser-mcp",
        description="Real-browser MCP server with TMWebDriver/CDP bridge, screenshots, and physical input.",
    )
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("extension-path", help="Print the unpacked Chrome extension path")
    sub.add_parser("doctor", help="Run local diagnostics and print JSON status")
    sub.add_parser("print-hermes-config", help="Print a ready-to-paste Hermes MCP config snippet")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extension-path":
        return cmd_extension_path()
    if args.command == "doctor":
        return cmd_doctor()
    if args.command == "print-hermes-config":
        return cmd_print_hermes_config()

    ensure_config_js()
    get_driver()
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
