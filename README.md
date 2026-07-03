# codex-reconnect-fix-skill

通过自动检测本地代理端口并刷新 Codex .env 代理配置解决Codex一直重新连接的问题，支持 macOS 和 Windows。

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

### 方式一：通过 Codex 安装

在 Codex 中输入：

```text
请安装 GitHub 仓库 zhuimengFIRE/codex-reconnect-fix-skill 中的 Skill
```

或直接使用仓库地址：

```text
请从 https://github.com/zhuimengFIRE/codex-reconnect-fix-skill 安装 Skill
```

### 方式二：手动复制安装

把整个目录复制到 Codex 的 skills 目录：

```bash
cp -R codex-reconnect-fix-skill ~/.codex/skills/
```

安装后新开一个 Codex 会话，使用：

```text
用 $codex-reconnect-fix-skill 修复代理
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

通过自动检测本地代理端口并刷新 Codex .env 代理配置解决Codex一直重新连接的问题，支持 macOS 和 Windows。
