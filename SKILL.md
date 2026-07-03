---
name: codex-reconnect-fix-skill
description: 通过检测本地代理端口并写入 Codex 根目录的 .env 文件，刷新 Codex 代理环境变量 HTTP_PROXY、HTTPS_PROXY 和 NO_PROXY。用于 Codex 出现 reconnect/network 问题、需要恢复代理配置，或用户要求根据本地代理软件更新 Codex .env 代理变量的场景。
---

# Codex 代理重连修复

## 执行流程

使用内置脚本检测本地代理端口，并更新 Codex 根目录下的 `.env` 文件。

```bash
python3 scripts/refresh_codex_proxy_env.py
```

脚本使用 `${CODEX_HOME:-$HOME/.codex}` 作为 Codex 根目录；如果目录不存在会自动创建，并写入或更新：

```dotenv
HTTP_PROXY="http://127.0.0.1:<检测到的端口>"
HTTPS_PROXY="http://127.0.0.1:<检测到的端口>"
NO_PROXY="localhost,127.0.0.1,::1"
```

脚本会保留 `.env` 中不相关的现有内容，只替换 `HTTP_PROXY`、`HTTPS_PROXY` 和 `NO_PROXY`。

## 端口检测

脚本会按顺序检查：

1. 手动传入的 `--port`。
2. 当前环境变量中的本地代理地址。
3. macOS `scutil --proxy` 或 Windows 注册表中的系统代理设置。
4. macOS 和 Windows 常见 Clash/Clash Verge/Mihomo 配置文件。
5. macOS 和 Windows 常见本地代理进程正在监听的 TCP 端口。

如果 Clash 兼容配置暴露了多个端口，优先使用 `mixed-port`。写入 `.env` 前，必须确认选中的端口在 `127.0.0.1` 上可连接。

Windows 下会额外检查 `%APPDATA%`、`%LOCALAPPDATA%`、`%USERPROFILE%\.config` 中常见的 Clash/Clash Verge/Mihomo 配置目录，并通过 `tasklist` 和 `netstat -ano` 识别代理进程监听端口。

## 常用命令

更新真实 Codex 根目录：

```bash
python3 scripts/refresh_codex_proxy_env.py
```

强制使用已知端口：

```bash
python3 scripts/refresh_codex_proxy_env.py --port 7897
```

使用临时 Codex 根目录测试：

```bash
python3 scripts/refresh_codex_proxy_env.py --codex-root /tmp/codex-root-test
```
