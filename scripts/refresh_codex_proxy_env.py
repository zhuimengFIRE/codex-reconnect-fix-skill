#!/usr/bin/env python3
"""检测本地代理端口，并写入 Codex .env 代理变量。"""

from __future__ import annotations

import csv
import os
import platform
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Iterable


NO_PROXY_VALUE = "localhost,127.0.0.1,::1"
PROXY_KEYS = {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "::", "0.0.0.0", "*"}
PROXY_PROCESS_WORDS = (
    "clash",
    "mihomo",
    "verge",
    "sing-box",
    "v2ray",
    "xray",
    "surge",
    "loon",
    "quantumult",
    "shadow",
    "trojan",
    "privoxy",
    "mitmproxy",
    "charles",
    "proxyman",
)
CONFIG_FILE_NAMES = (
    "config.yaml",
    "clash-verge.yaml",
    "verge.yaml",
)
CONFIG_PORT_KEYS = (
    "mixed-port",
    "mixed_port",
    "verge_mixed_port",
    "port",
    "verge_port",
    "socks-port",
    "socks_port",
    "verge_socks_port",
    "redir-port",
    "redir_port",
    "verge_redir_port",
    "tproxy-port",
    "tproxy_port",
)


class Candidate:
    def __init__(self, port: int, source: str) -> None:
        self.port = port
        self.source = source


def run_command(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            check=False,
            text=True,
            capture_output=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0 and not result.stdout:
        return ""
    return result.stdout


def is_local_host(value: str | None) -> bool:
    if not value:
        return True
    return value.strip().strip("[]").lower() in LOCAL_HOSTS


def valid_port(value: str | int | None) -> int | None:
    try:
        port = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if 1 <= port <= 65535:
        return port
    return None


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def looks_like_http_proxy(port: int) -> bool:
    request = (
        b"CONNECT example.com:443 HTTP/1.1\r\n"
        b"Host: example.com:443\r\n"
        b"Proxy-Connection: Keep-Alive\r\n\r\n"
    )
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5) as sock:
            sock.settimeout(1.5)
            sock.sendall(request)
            data = sock.recv(128)
    except OSError:
        return False
    return data.startswith(b"HTTP/")


def parse_host_port(value: str) -> tuple[str, int] | None:
    value = value.strip().strip('"').strip("'")
    if not value:
        return None
    url_match = re.match(r"^(?:https?|socks5?h?)://(?:[^@/]+@)?([^:/\]]+|\[[^\]]+\]):(\d+)", value, re.I)
    if url_match:
        port = valid_port(url_match.group(2))
        return (url_match.group(1).strip("[]"), port) if port else None
    if value.startswith("["):
        bracket_match = re.match(r"^\[([^\]]+)\]:(\d+)$", value)
        if not bracket_match:
            return None
        port = valid_port(bracket_match.group(2))
        return (bracket_match.group(1), port) if port else None
    host, separator, raw_port = value.rpartition(":")
    if not separator:
        return None
    port = valid_port(raw_port)
    return (host, port) if port else None


def env_candidates() -> Iterable[Candidate]:
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        parsed = parse_host_port(os.environ.get(key, ""))
        if not parsed:
            continue
        host, port = parsed
        if is_local_host(host):
            yield Candidate(port, f"环境变量:{key}")


def scutil_candidates() -> Iterable[Candidate]:
    output = run_command(["scutil", "--proxy"])
    if not output:
        return
    values: dict[str, str] = {}
    for line in output.splitlines():
        match = re.match(r"\s*([A-Za-z]+(?:Enable|Port|Proxy))\s*:\s*(.+?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2)
    checks = (
        ("HTTPEnable", "HTTPProxy", "HTTPPort"),
        ("HTTPSEnable", "HTTPSProxy", "HTTPSPort"),
        ("SOCKSEnable", "SOCKSProxy", "SOCKSPort"),
    )
    for enable_key, host_key, port_key in checks:
        if values.get(enable_key) != "1" or not is_local_host(values.get(host_key)):
            continue
        port = valid_port(values.get(port_key))
        if port:
            yield Candidate(port, f"系统代理:{port_key}")


def windows_proxy_server_candidates(proxy_server: str) -> Iterable[Candidate]:
    for segment in proxy_server.split(";"):
        segment = segment.strip()
        if not segment:
            continue
        protocol = "ProxyServer"
        if "=" in segment:
            protocol, segment = segment.split("=", 1)
            segment = segment.strip()
        parsed = parse_host_port(segment)
        if not parsed:
            continue
        host, port = parsed
        if is_local_host(host):
            yield Candidate(port, f"Windows系统代理:{protocol.strip()}")


def windows_system_proxy_candidates() -> Iterable[Candidate]:
    if platform.system() != "Windows":
        return
    try:
        import winreg
    except ImportError:
        return
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if int(proxy_enable) != 1:
                return
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except (FileNotFoundError, OSError, ValueError):
        return
    yield from windows_proxy_server_candidates(str(proxy_server))


def system_proxy_candidates() -> Iterable[Candidate]:
    if platform.system() == "Windows":
        yield from windows_system_proxy_candidates()
    else:
        yield from scutil_candidates()


def unique_paths(paths: Iterable[Path]) -> Iterable[Path]:
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        yield path


def config_directories() -> Iterable[Path]:
    if platform.system() == "Windows":
        app_dir_names = (
            "io.github.clash-verge-rev.clash-verge-rev",
            "clash-verge",
            "Clash Verge",
            "Clash Verge Rev",
            "Clash for Windows",
            "mihomo",
            "clash",
        )
        for env_key in ("APPDATA", "LOCALAPPDATA"):
            base = os.environ.get(env_key)
            if not base:
                continue
            for app_dir_name in app_dir_names:
                yield Path(base) / app_dir_name
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            yield Path(user_profile) / ".config" / "mihomo"
            yield Path(user_profile) / ".config" / "clash"
    else:
        yield Path("~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev").expanduser()
        yield Path("~/.config/mihomo").expanduser()
        yield Path("~/.config/clash").expanduser()


def config_paths() -> Iterable[Path]:
    for directory in unique_paths(config_directories()):
        for file_name in CONFIG_FILE_NAMES:
            yield directory / file_name
        profiles_dir = directory / "profiles"
        if profiles_dir.exists() and profiles_dir.is_dir():
            yield from sorted(profiles_dir.glob("*.yaml"))
            yield from sorted(profiles_dir.glob("*.yml"))
        yield directory / "profiles.yaml"
        yield directory / "Merge.yaml"


def config_candidates() -> Iterable[Candidate]:
    for path in unique_paths(config_paths()):
        if not path.exists() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        found: dict[str, int] = {}
        for line in text.splitlines():
            match = re.match(
                r"^\s*([A-Za-z_-]+)\s*:\s*['\"]?(\d{2,5})['\"]?\s*(?:#.*)?$",
                line,
            )
            if not match:
                continue
            key = match.group(1)
            if key in CONFIG_PORT_KEYS:
                port = valid_port(match.group(2))
                if port:
                    found[key] = port
        for key in CONFIG_PORT_KEYS:
            if key in found:
                yield Candidate(found[key], f"配置文件:{path.name}:{key}")


def macos_listening_candidates() -> Iterable[Candidate]:
    output = run_command(["netstat", "-anv", "-p", "tcp"])
    if not output:
        return
    for line in output.splitlines():
        lower = line.lower()
        if "listen" not in lower:
            continue
        if not any(word in lower for word in PROXY_PROCESS_WORDS):
            continue
        match = re.search(r"(?:127\.0\.0\.1|localhost|\*)\.(\d{2,5})\s+", line)
        if not match:
            continue
        port = valid_port(match.group(1))
        if port:
            yield Candidate(port, "监听进程")


def windows_proxy_process_pids() -> set[str]:
    output = run_command(["tasklist", "/FO", "CSV", "/NH"])
    pids: set[str] = set()
    if not output:
        return pids
    for row in csv.reader(output.splitlines()):
        if len(row) < 2:
            continue
        process_name = row[0].strip().lower()
        if any(word in process_name for word in PROXY_PROCESS_WORDS):
            pids.add(row[1].strip())
    return pids


def windows_listening_candidates() -> Iterable[Candidate]:
    proxy_pids = windows_proxy_process_pids()
    if not proxy_pids:
        return
    output = run_command(["netstat", "-ano", "-p", "tcp"])
    if not output:
        return
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].lower() != "tcp":
            continue
        local_address = parts[1]
        state = parts[3].lower()
        pid = parts[-1]
        if state != "listening" or pid not in proxy_pids:
            continue
        parsed = parse_host_port(local_address)
        if not parsed:
            continue
        host, port = parsed
        if is_local_host(host):
            yield Candidate(port, "Windows监听进程")


def listening_candidates() -> Iterable[Candidate]:
    if platform.system() == "Windows":
        yield from windows_listening_candidates()
    else:
        yield from macos_listening_candidates()


def unique_candidates(candidates: Iterable[Candidate]) -> list[Candidate]:
    seen: set[int] = set()
    unique: list[Candidate] = []
    for candidate in candidates:
        if candidate.port in seen:
            continue
        seen.add(candidate.port)
        unique.append(candidate)
    return unique


def detect_port(forced_port: int | None = None) -> Candidate:
    if forced_port is not None:
        if not port_is_open(forced_port):
            raise RuntimeError(f"端口 {forced_port} 未在 127.0.0.1 上开放")
        return Candidate(forced_port, "手动指定")

    candidates = unique_candidates(
        [
            *env_candidates(),
            *system_proxy_candidates(),
            *config_candidates(),
            *listening_candidates(),
        ]
    )
    open_candidates = [candidate for candidate in candidates if port_is_open(candidate.port)]
    for candidate in open_candidates:
        if looks_like_http_proxy(candidate.port):
            return candidate
    if open_candidates:
        return open_candidates[0]
    raise RuntimeError("未检测到开放的本地代理端口")


def update_env_file(env_path: Path, port: int) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    preserved: list[str] = []
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
            if match and match.group(1) in PROXY_KEYS:
                continue
            preserved.append(line)
    if preserved and preserved[-1].strip():
        preserved.append("")
    preserved.extend(
        [
            f'HTTP_PROXY="http://127.0.0.1:{port}"',
            f'HTTPS_PROXY="http://127.0.0.1:{port}"',
            f'ALL_PROXY="socks5h://127.0.0.1:{port}"',
            f'NO_PROXY="{NO_PROXY_VALUE}"',
        ]
    )
    env_path.write_text("\n".join(preserved).rstrip() + "\n", encoding="utf-8")


def print_help(default_root: str) -> None:
    print(
        "\n".join(
            [
                "用法：refresh_codex_proxy_env.py [--codex-root 路径] [--port 端口]",
                "",
                "检测本地代理端口，并写入 Codex .env 代理变量。",
                "",
                "选项：",
                "  -h, --help            显示帮助信息并退出",
                f"  --codex-root 路径     Codex 根目录，默认：{default_root}",
                "  --port 端口           使用已知的本地代理端口",
            ]
        )
    )


def parse_args() -> tuple[str, int | None]:
    default_root = os.environ.get("CODEX_HOME") or str(Path.home() / ".codex")
    codex_root = default_root
    port: int | None = None
    args = sys.argv[1:]
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("-h", "--help"):
            print_help(default_root)
            raise SystemExit(0)
        if arg == "--codex-root":
            index += 1
            if index >= len(args):
                raise RuntimeError("缺少 --codex-root 的路径")
            codex_root = args[index]
        elif arg.startswith("--codex-root="):
            codex_root = arg.split("=", 1)[1]
            if not codex_root:
                raise RuntimeError("缺少 --codex-root 的路径")
        elif arg == "--port":
            index += 1
            if index >= len(args):
                raise RuntimeError("缺少 --port 的端口")
            port = valid_port(args[index])
            if port is None:
                raise RuntimeError(f"端口无效：{args[index]}")
        elif arg.startswith("--port="):
            raw_port = arg.split("=", 1)[1]
            port = valid_port(raw_port)
            if port is None:
                raise RuntimeError(f"端口无效：{raw_port}")
        else:
            raise RuntimeError(f"未知参数：{arg}")
        index += 1
    return codex_root, port


def main() -> int:
    try:
        codex_root_arg, port = parse_args()
        candidate = detect_port(port)
        codex_root = Path(codex_root_arg).expanduser()
        env_path = codex_root / ".env"
        update_env_file(env_path, candidate.port)
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(f"Codex 根目录：{codex_root}")
    print(f"代理端口：{candidate.port}（{candidate.source}）")
    print(f"已更新：{env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
