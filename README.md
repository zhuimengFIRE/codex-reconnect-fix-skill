# codex-reconnect-fix-skill

一个用于修复 Codex 代理环境变量的本地 Skill。它会检测本地代理软件端口，并把 `HTTP_PROXY`、`HTTPS_PROXY`、`NO_PROXY` 写入 Codex 根目录的 `.env` 文件。

## 适用场景

- Codex 出现 reconnect、network、连接失败等问题。
- 本地代理端口变化后，需要重新写入 Codex 的 `.env`。
- 希望用一个 Skill 自动维护 Codex 代理配置。

## 功能

- 自动创建 Codex 根目录下的 `.env` 文件。
- 如果 `.env` 已存在，只更新代理三项并保留其他内容。
- 自动检测本地代理端口。
- 支持 macOS 和 Windows。
- 支持手动指定端口。

写入示例：

```dotenv
HTTP_PROXY="http://127.0.0.1:7897"
HTTPS_PROXY="http://127.0.0.1:7897"
NO_PROXY="localhost,127.0.0.1,::1"
```

## 安装

把整个目录复制到 Codex 的 skills 目录：

```bash
cp -R codex-reconnect-fix-skill ~/.codex/skills/
```

安装后新开一个 Codex 会话，使用：

```text
用 $codex-reconnect-fix-skill 修复代理
```

## 直接运行脚本

在 skill 目录内执行：

```bash
python3 scripts/refresh_codex_proxy_env.py
```

强制指定端口：

```bash
python3 scripts/refresh_codex_proxy_env.py --port 7897
```

使用临时 Codex 根目录测试：

```bash
python3 scripts/refresh_codex_proxy_env.py --codex-root /tmp/codex-root-test
```

## 端口检测逻辑

脚本会按顺序检查：

1. 手动传入的 `--port`。
2. 当前环境变量中的本地代理地址。
3. macOS `scutil --proxy` 或 Windows 注册表中的系统代理设置。
4. macOS 和 Windows 常见 Clash、Clash Verge、Mihomo 配置文件。
5. macOS 和 Windows 常见本地代理进程正在监听的 TCP 端口。

如果 Clash 兼容配置暴露多个端口，脚本会优先使用 `mixed-port`。

## 验证

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py .
python3 -m py_compile scripts/refresh_codex_proxy_env.py
```

## 仓库简介

Codex Skill：自动检测本地代理端口并刷新 Codex `.env` 代理配置，支持 macOS 和 Windows。
