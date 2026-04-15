# agent-browser-mcp

一个面向真实 Chrome 浏览器的 MCP 服务。

它不是控制一个沙盒浏览器，也不是无状态网页抓取器，而是直接连接你自己正在使用的 Chrome，会保留：
- 登录状态
- Cookies
- 已打开标签页
- 真实页面上下文

如果你希望让 Hermes、Claude Desktop、Cursor 等 MCP 客户端直接操作你本机真实浏览器，这个项目就是为这个场景准备的。

## 这个 MCP 能做什么

这个项目把真实浏览器自动化能力包装成了标准 MCP 工具，重点能力包括：

### 1. 浏览器标签页与导航
- 查看当前已连接的真实标签页
- 切换到指定标签页
- 在当前标签页打开 URL
- 新建标签页

### 2. 页面读取
- 扫描当前页面内容
- 提取简化后的 HTML / 文本
- 适合读取信息流、帖子列表、搜索结果页

### 3. 页面执行与 CDP 控制
- 在页面中执行任意 JavaScript
- 直接调用 Chrome DevTools Protocol（CDP）
- 支持单条命令和批量命令
- 可用于截图、DOM 查询、点击、文件上传等更复杂操作

### 4. 截图能力
- 页面截图（通过 CDP）
- 桌面截图（用于辅助真实桌面操作）

### 5. 真实物理输入
- 鼠标移动
- 鼠标点击
- 鼠标拖拽
- 键盘输入
- 热键发送

这类能力很适合处理：
- 必须保留登录态的网站
- 普通浏览器自动化工具容易被风控的网站
- 必须使用真实点击 / 真实键盘输入的场景
- 需要读取复杂页面结构的场景

## 适合哪些场景

例如：
- 用 Hermes 读取你当前小红书首页推荐流
- 在真实浏览器里打开后台页面并抓取信息
- 调用 CDP 截图页面
- 在页面 JS 不够用时，回退到真实鼠标/键盘操作
- 让 Agent 直接操作你已登录的网站，而不是重新登录一个无状态浏览器

## 工作原理

项目由三层组成：

1. Chrome 扩展
- 注入到真实网页
- 通过 Chrome API 访问 tabs / cookies / debugger / management
- 与本地桥接服务通信

2. TMWebDriver 本地桥接
- 默认监听：
  - WebSocket: `127.0.0.1:18765`
  - HTTP: `127.0.0.1:18766`
- 负责连接扩展、维护会话、转发执行结果

3. MCP 服务
- 把浏览器能力暴露为 MCP tools
- 供 Hermes、Claude Desktop、Cursor 等客户端直接调用

## 主要工具

当前暴露的主要 MCP 工具包括：

### 浏览器/标签页
- `get_setup_status`
- `list_tabs`
- `switch_tab`
- `open_url`
- `open_new_tab`
- `extension_path`
- `list_extensions`

### 页面读取/执行
- `scan_page`
- `execute_js`

### CDP 与截图
- `cdp_command`
- `cdp_batch`
- `get_cookies`
- `capture_page_screenshot`
- `capture_desktop_screenshot`

### 物理输入
- `mouse_move`
- `mouse_click`
- `mouse_drag`
- `type_text`
- `hotkey`
- `pointer_info`

## 安装要求

推荐环境：
- macOS 或 Windows
- Python 3.10+
- Google Chrome
- 任意支持 MCP 的客户端，例如：
  - Hermes Agent
  - Claude Desktop
  - Cursor

## 安装

在本地克隆后执行：

```bash
cd agent-browser-mcp
pip install -e .
```

如果你想先构建 wheel 再安装：

```bash
python -m pip install --upgrade build
python -m build
pip install dist/agent_browser_mcp-0.1.0-py3-none-any.whl
```

## 命令行工具

安装后会提供一个 CLI：

```bash
agent-browser-mcp
```

它有几个常用子命令：

### 输出 Chrome 扩展目录

```bash
agent-browser-mcp extension-path
```

### 输出 Hermes 配置片段

```bash
agent-browser-mcp print-hermes-config
```

### 环境诊断

```bash
agent-browser-mcp doctor
```

这个命令会输出 JSON，帮助你检查：
- 扩展目录位置
- `config.js` 是否生成
- 端口状态
- 当前连接到的标签页数量
- 下一步建议

## Chrome 扩展安装

这个项目包含一个 unpacked Chrome 扩展，需要手动加载一次。

### 第一步：获取扩展目录

```bash
agent-browser-mcp extension-path
```

### 第二步：在 Chrome 中加载

打开：

```text
chrome://extensions
```

然后：
- 打开“开发者模式”
- 点击“加载已解压的扩展程序”
- 选择上一步输出的目录

### 第三步：打开正常网页

注意不要停留在 `about:blank`。

请在 Chrome 中打开一个正常网页，例如：
- `https://www.baidu.com`
- `https://www.xiaohongshu.com`

否则不会建立有效会话。

## Hermes 配置

把下面这段加到 `~/.hermes/config.yaml`：

```yaml
mcp_servers:
  agent_browser:
    command: agent-browser-mcp
    timeout: 120
    connect_timeout: 60
```

项目里也附带了示例文件：
- `examples/hermes-config.yaml`

配置后，重启 Hermes 或重新加载 MCP。

可用下面的命令验证：

```bash
hermes mcp list
hermes mcp test agent_browser
```

如果测试成功，Hermes 就能发现并调用这些浏览器工具。

## Claude Desktop / Cursor 配置

仓库中也放了示例：
- `examples/claude-desktop-config.json`
- `examples/cursor-mcp.json`

配置结构都很简单，核心就是：

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

## 典型使用流程

1. 安装 Python 包
2. 在 Chrome 中加载扩展
3. 打开一个真实网页
4. 在 MCP 客户端中接入这个服务
5. 开始调用浏览器工具

例如，Agent 可以做：
- 打开小红书首页
- 读取推荐流
- 扫描帖子列表
- 对页面进行 CDP 截图
- 在必要时执行真实鼠标/键盘操作

## 安全提醒

这个项目操作的是你的真实浏览器和真实桌面。

这意味着：
- 鼠标移动是真的
- 点击是真的
- 输入是真的
- 热键是真的
- 浏览器里的登录态也是真的

请只在你信任的 MCP 客户端和 Agent 环境中使用。

## 常见问题

### 1. Hermes 能看到 MCP 服务，但没有连接到任何标签页

请检查：
- 扩展是否已经在 `chrome://extensions` 中加载
- Chrome 里是否打开了正常网页
- 是否只是停留在 `about:blank`

你也可以运行：

```bash
agent-browser-mcp doctor
```

### 2. `connected_tabs` 为 0

通常是以下原因之一：
- 扩展没有加载成功
- 当前没有正常网页
- 扩展刚重载，页面还没刷新

建议：
- 刷新当前网页
- 新开一个正常 URL
- 再运行一次 `doctor`

### 3. 物理输入在 macOS 上不生效

请给终端 / MCP 客户端授予系统权限：
- 辅助功能（Accessibility）
- 屏幕录制（如果你需要桌面截图）

### 4. `hermes mcp test agent_browser` 失败

请检查：
- 包是否安装成功
- `agent-browser-mcp` 是否在 PATH 中
- Hermes 配置是否正确
- 运行 `agent-browser-mcp doctor` 看诊断输出

## 致谢

这个项目的浏览器自动化能力，是从 GenericAgent 的浏览器栈中提取并重新封装成 MCP 服务的。

特别感谢 GenericAgent 项目及其作者提供的原始实现思路与核心能力来源。

原项目地址：
- https://github.com/lsdefine/GenericAgent

本项目中以下部分来自或改编自 GenericAgent：
- `TMWebDriver.py`
- `simphtml.py`
- `tmwd_cdp_bridge` Chrome 扩展资源

如果你基于本项目继续二次开发或发布，也建议保留对 GenericAgent 的致谢与来源说明。

## 许可证

MIT
