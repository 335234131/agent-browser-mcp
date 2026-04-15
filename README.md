# agent-browser-mcp

Real-browser MCP server for Chrome, built from the GenericAgent browser stack and packaged for reuse with Hermes and other MCP clients.

It exposes:
- Real Chrome tab/session discovery and switching
- Simplified page scanning (`scan_page`)
- Arbitrary page JS execution (`execute_js`)
- Raw CDP single-command and batch execution
- Cookies access
- Page screenshots via CDP
- Desktop screenshots
- Physical mouse/keyboard input via `pyautogui`

This project is designed for cases where you want an LLM agent to operate on your real logged-in browser session instead of a headless sandbox browser.

## What this package contains

- A standalone MCP server
- The TMWebDriver bridge runtime
- The DOM simplification/page scanning logic
- An unpacked Chrome extension (`chrome_extension/`) that must be loaded manually
- A CLI for setup and diagnostics

## Important safety notes

This package can control your real browser and your real desktop.

That means:
- mouse movement is real
- clicks are real
- typed text is real
- hotkeys are real
- actions happen in your active Chrome/user session

Use it only with agents and MCP clients you trust.

## Architecture

The runtime has three layers:

1. Chrome extension
   - Injects into real pages
   - Uses Chrome APIs for tabs, cookies, and debugger/CDP
   - Connects to the local TMWebDriver bridge

2. TMWebDriver bridge
   - Hosts a local WebSocket server on `127.0.0.1:18765`
   - Hosts an HTTP sidecar on `127.0.0.1:18766`
   - Tracks connected tabs and forwards browser actions/results

3. MCP server
   - Exposes browser operations as MCP tools
   - Lets Hermes / Claude Desktop / Cursor call the bridge as standard MCP tools

## Features

### Browser/session tools
- `get_setup_status`
- `list_tabs`
- `switch_tab`
- `open_url`
- `open_new_tab`
- `extension_path`
- `list_extensions`

### Page interaction tools
- `scan_page`
- `execute_js`

### CDP tools
- `cdp_command`
- `cdp_batch`
- `get_cookies`
- `capture_page_screenshot`

### Desktop/physical input tools
- `capture_desktop_screenshot`
- `mouse_move`
- `mouse_click`
- `mouse_drag`
- `type_text`
- `hotkey`
- `pointer_info`

## Requirements

Recommended:
- macOS or Windows
- Python 3.10+
- Google Chrome
- An MCP client such as Hermes Agent, Claude Desktop, or Cursor

This package is most thoroughly validated on macOS with Chrome.

## Installation

### From a local checkout

```bash
cd agent-browser-mcp
pip install -e .
```

### Build and install wheel locally

```bash
python -m pip install --upgrade build
python -m build
pip install dist/agent_browser_mcp-0.1.0-py3-none-any.whl
```

### From GitHub later

Once you publish the repo, users can install with:

```bash
pip install git+https://github.com/YOUR_NAME/agent-browser-mcp.git
```

## CLI

After installation, these commands are available:

### Start the MCP server

```bash
agent-browser-mcp
```

This runs the MCP server over stdio for MCP clients.

### Print the unpacked Chrome extension path

```bash
agent-browser-mcp extension-path
```

### Print a ready-to-paste Hermes config snippet

```bash
agent-browser-mcp print-hermes-config
```

### Run diagnostics

```bash
agent-browser-mcp doctor
```

This prints JSON including:
- extension path
- generated `config.js` path
- bridge ports
- whether ports are open
- connected tabs
- suggested next steps

## Chrome extension setup

This package includes a Chrome extension that must be loaded manually.

### 1. Get the extension path

```bash
agent-browser-mcp extension-path
```

Example output:

```text
/Users/you/.../site-packages/agent_browser_mcp/chrome_extension
```

### 2. Load it in Chrome

Open:

```text
chrome://extensions
```

Then:
- enable Developer Mode
- click "Load unpacked"
- select the extension directory printed by the CLI

### 3. Open a normal page

Important:
- do not stay on `about:blank`
- open a normal `http://` or `https://` page in Chrome

Examples:
- `https://www.baidu.com`
- `https://www.xiaohongshu.com`

## Hermes setup

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  agent_browser:
    command: agent-browser-mcp
    timeout: 120
    connect_timeout: 60
```

A copy is also included at:
- `examples/hermes-config.yaml`

Then restart Hermes or reload MCP servers.

Verify:

```bash
hermes mcp list
hermes mcp test agent_browser
```

If successful, Hermes should discover the browser MCP tools.

## Claude Desktop setup

Use the example file:
- `examples/claude-desktop-config.json`

Typical config shape:

```json
{
  "mcpServers": {
    "agent_browser": {
      "command": "agent-browser-mcp",
      "args": []
    }
  }
}
```

## Cursor setup

Use the example file:
- `examples/cursor-mcp.json`

## Typical usage flow

1. Install package
2. Load unpacked extension in Chrome
3. Open a real web page in Chrome
4. Start/reload your MCP client
5. Call browser tools from the client

Example agent tasks:
- open Xiaohongshu homepage in the real browser
- scan visible recommendation cards
- execute CDP screenshot capture
- click/type on the real desktop when JS/CDP is insufficient

## Development notes

### Local editable install

```bash
pip install -e .
```

### Run the CLI directly

```bash
python -m agent_browser_mcp.cli doctor
```

### Build distributions

```bash
python -m pip install --upgrade build
python -m build
```

Build outputs go to:
- `dist/`

### Test package metadata/build

```bash
python -m py_compile src/agent_browser_mcp/*.py
python -m build
```

## Repository layout

```text
agent-browser-mcp/
├── pyproject.toml
├── MANIFEST.in
├── README.md
├── LICENSE
├── .gitignore
├── examples/
│   ├── hermes-config.yaml
│   ├── claude-desktop-config.json
│   └── cursor-mcp.json
└── src/
    └── agent_browser_mcp/
        ├── __init__.py
        ├── cli.py
        ├── server.py
        ├── tmwebdriver.py
        ├── simphtml.py
        └── chrome_extension/
            ├── manifest.json
            ├── background.js
            ├── content.js
            ├── disable_dialogs.js
            ├── popup.html
            └── popup.js
```

## Publishing to GitHub

### 1. Create a new GitHub repo

Example:
- `agent-browser-mcp`

### 2. Initialize git locally

```bash
cd /Users/zhea/Documents/agent-browser-mcp
git init
git add .
git commit -m "feat: initial publishable package for agent-browser-mcp"
```

### 3. Add remote and push

```bash
git remote add origin git@github.com:YOUR_NAME/agent-browser-mcp.git
git branch -M main
git push -u origin main
```

Or with HTTPS:

```bash
git remote add origin https://github.com/YOUR_NAME/agent-browser-mcp.git
git branch -M main
git push -u origin main
```

## Publishing to PyPI later

When ready:

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine upload dist/*
```

Before uploading, update in `pyproject.toml`:
- `version`
- `project.urls`
- `authors`
- classifiers if needed

## Known limitations

- Chrome extension installation is manual unless you later publish via Chrome Web Store
- Physical input uses the real active desktop and may be affected by OS permissions
- Some sites may still require CDP or physical input due to `isTrusted` constraints
- macOS accessibility/screen recording permissions may be required for full physical-input behavior

## Troubleshooting

### Hermes sees the MCP server but no tabs connect

Check all of these:
- extension is loaded in `chrome://extensions`
- a normal `http/https` page is open
- you are using Chrome, not only a background browser process
- run:

```bash
agent-browser-mcp doctor
```

### `connected_tabs` is 0

Usually means one of:
- extension not loaded
- only `about:blank` is open
- Chrome page needs refresh after extension reload

Try:
- refresh the current tab
- open a fresh normal URL
- rerun diagnostics

### Physical input does not work on macOS

Grant the terminal / MCP client app the needed permissions in macOS:
- Accessibility
- Screen Recording (for screenshots)

### `hermes mcp test agent_browser` fails

Check:
- package installed successfully
- `agent-browser-mcp` is on PATH
- Hermes config references `agent-browser-mcp`
- run `agent-browser-mcp doctor`

## Attribution

This package is derived from and packages the browser automation approach extracted from the GenericAgent project:
- `TMWebDriver.py`
- `simphtml.py`
- the `tmwd_cdp_bridge` extension assets

If you publish this publicly, you should keep attribution and verify license compatibility for redistributed components.

## License

MIT
