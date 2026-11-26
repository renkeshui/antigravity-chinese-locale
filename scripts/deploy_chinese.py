#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity Chinese Locale Installer & Manager
Google Antigravity 桌面客户端汉化部署与还原工具（零第三方依赖）
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile


def find_antigravity_resources():
    candidates = []
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidates.append(os.path.join(local_app_data, "Programs", "antigravity", "resources"))
    candidates.extend([
        "/Applications/Antigravity.app/Contents/Resources",
        "/opt/Antigravity/resources",
    ])
    for p in candidates:
        if os.path.exists(os.path.join(p, "app.asar")):
            return p
    return None


def get_asar_cmd():
    asar_bin = shutil.which("asar")
    if asar_bin:
        return [asar_bin]
    npx_bin = shutil.which("npx")
    if npx_bin:
        return [npx_bin, "--yes", "@electron/asar"]
    return None


def run_cmd(cmd, **kwargs):
    use_shell = os.name == "nt" and cmd[0].lower().endswith((".cmd", ".bat"))
    return subprocess.run(cmd, shell=use_shell, **kwargs)


def check_file_unlocked(path):
    if not os.path.exists(path):
        return True
    try:
        with open(path, "r+b"):
            return True
    except PermissionError:
        return False
    except OSError:
        return True


def has_i18n_marker(asar_path):
    """Quick binary scan to detect whether app.asar is already patched."""
    try:
        with open(asar_path, "rb") as f:
            head = f.read(1024 * 1024)
        return b"i18n_inject.js" in head
    except Exception:
        return False


def gatekeeper_check(i18n_data_path, i18n_runner_path, js_files):
    with open(i18n_data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    exact = data.get("exact", {})
    if not exact or any(not k or not v for k, v in exact.items()):
        raise ValueError("i18n_data.json exact 字典为空或存在空键值")

    with open(i18n_runner_path, "r", encoding="utf-8") as f:
        runner_code = f.read()
    if re.search(r"characterData\s*:\s*true", runner_code):
        raise ValueError("红线拦截：i18n_runner.js 严禁开启 characterData: true")
    if "new WeakSet" in runner_code:
        raise ValueError("红线拦截：i18n_runner.js 严禁使用 WeakSet 阻断标记")

    for fp in js_files:
        if os.path.exists(fp):
            chk = subprocess.run(["node", "--check", fp], capture_output=True, text=True)
            if chk.returncode != 0:
                raise RuntimeError(f"语法门禁失败 {fp}:\n{chk.stderr}")


def patch_main_js(main_js):
    with open(main_js, "r", encoding="utf-8") as f:
        content = f.read()

    if "i18n_inject" in content:
        return

    hook_code = (
        "\n// --- Antigravity i18n Full Lifecycle Hook ---\n"
        "try {\n"
        "    const { setupI18nLifecycle } = require('./i18n_inject');\n"
        "    setupI18nLifecycle(electron_1.app);\n"
        "} catch (e) {\n"
        "    console.error('[Antigravity i18n] Setup lifecycle failed:', e);\n"
        "}\n"
    )
    anchor = re.search(r"const electron_1 = require\([\"']electron[\"']\);", content)
    if not anchor:
        raise RuntimeError("未在 main.js 中找到 electron 模块引入锚点，已中止打包")

    pos = anchor.end()
    content = content[:pos] + hook_code + content[pos:]
    with open(main_js, "w", encoding="utf-8") as f:
        f.write(content)


def patch_menu_and_tray(dist_dir):
    menu_js = os.path.join(dist_dir, "menu.js")
    if os.path.exists(menu_js):
        with open(menu_js, "r", encoding="utf-8") as f:
            mc = f.read()
        replacements = [
            ("label: 'Zoom In',", "label: '放大',"),
            ("label: 'New Window',", "label: '新建窗口',"),
            ("label: 'Docs',", "label: '官方文档',"),
            ("label: 'Connect to WSL'", "label: '连接到 WSL'"),
            ("label: 'Reopen Locally'", "label: '在本地重新打开'"),
        ]
        for old, new in replacements:
            mc = mc.replace(old, new)
        with open(menu_js, "w", encoding="utf-8") as f:
            f.write(mc)

    tray_js = os.path.join(dist_dir, "tray.js")
    if os.path.exists(tray_js):
        with open(tray_js, "r", encoding="utf-8") as f:
            tc = f.read()
        pattern = re.compile(
            r"countItem\.label\s*=\s*\(count\s*>\s*0\s*\?\s*`\$\{count\}`\s*:\s*'No'\)\s*\+\s*' agent'\s*\+\s*\(count\s*===\s*1\s*\?\s*''\s*:\s*'s'\)\s*\+\s*' running';",
            re.MULTILINE,
        )
        tc = pattern.sub(
            "countItem.label = (count > 0 ? `${count} 个智能体运行中` : '暂无运行中的智能体');",
            tc,
        )
        with open(tray_js, "w", encoding="utf-8") as f:
            f.write(tc)


def restore_backup(resources_dir):
    target_asar = os.path.join(resources_dir, "app.asar")
    backup_asar = os.path.join(resources_dir, "app.asar.bak")
    if not os.path.exists(backup_asar):
        print("[Error] 未找到官方备份 app.asar.bak，无法还原。")
        sys.exit(1)
    if not check_file_unlocked(target_asar):
        print("[Error] app.asar 正在被占用。请先在系统托盘右键完全退出 Antigravity 后重试。")
        sys.exit(1)
    shutil.copy2(backup_asar, target_asar)
    print("[OK] 已从 app.asar.bak 还原官方原版。重启 Antigravity 即可生效。")


def main():
    parser = argparse.ArgumentParser(description="Antigravity 客户端汉化部署与还原工具")
    parser.add_argument("--restore", action="store_true", help="使用 app.asar.bak 还原为官方英文原版")
    parser.add_argument("--resources", help="手动指定 Antigravity resources 目录路径")
    args = parser.parse_args()

    resources_dir = args.resources or find_antigravity_resources()
    if not resources_dir or not os.path.exists(os.path.join(resources_dir, "app.asar")):
        print("[Error] 未检测到 Antigravity 安装目录，请使用 --resources 指定路径。")
        sys.exit(1)

    if args.restore:
        restore_backup(resources_dir)
        return

    if not shutil.which("node"):
        print("[Error] 未找到 Node.js，请先安装 Node.js (v18+)。")
        sys.exit(1)
    asar_cmd = get_asar_cmd()
    if not asar_cmd:
        print("[Error] 未找到 asar 或 npx，请确认 Node.js / npm 环境正常。")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    required_files = ["i18n_runner.js", "i18n_data.json", "i18n_inject.js"]
    for name in required_files:
        if not os.path.exists(os.path.join(script_dir, name)):
            print(f"[Error] 缺少必要文件: {name}")
            sys.exit(1)

    target_asar = os.path.join(resources_dir, "app.asar")
    backup_asar = os.path.join(resources_dir, "app.asar.bak")

    if not check_file_unlocked(target_asar):
        print("[Error] app.asar 正在被客户端占用，请先从系统托盘完全退出 Antigravity 后再运行。")
        sys.exit(1)

    # 智能备份：若当前 app.asar 未打过补丁（刚安装或刚更新），刷新备份；否则以 .bak 为纯净基准
    if not has_i18n_marker(target_asar):
        print("[*] 检测到官方原版 app.asar，正在更新纯净备份 app.asar.bak ...")
        shutil.copy2(target_asar, backup_asar)
        source_asar = target_asar
    elif os.path.exists(backup_asar):
        print("[*] 检测到已汉化状态，将基于纯净备份 app.asar.bak 重新构建 ...")
        source_asar = backup_asar
    else:
        source_asar = target_asar

    work_dir = tempfile.mkdtemp(prefix="antigravity_i18n_")
    try:
        print("[1/4] 解包应用资源 ...")
        run_cmd(asar_cmd + ["extract", source_asar, work_dir], check=True)

        dist_dir = os.path.join(work_dir, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        for name in required_files:
            shutil.copy2(os.path.join(script_dir, name), os.path.join(dist_dir, name))

        print("[2/4] 注入生命周期守卫与静态汉化 ...")
        main_js = os.path.join(dist_dir, "main.js")
        patch_main_js(main_js)
        patch_menu_and_tray(dist_dir)

        print("[3/4] 执行语法与红线门禁校验 ...")
        gatekeeper_check(
            os.path.join(dist_dir, "i18n_data.json"),
            os.path.join(dist_dir, "i18n_runner.js"),
            [
                main_js,
                os.path.join(dist_dir, "menu.js"),
                os.path.join(dist_dir, "tray.js"),
                os.path.join(dist_dir, "i18n_inject.js"),
                os.path.join(dist_dir, "i18n_runner.js"),
            ],
        )

        print("[4/4] 打包并校验产物 ...")
        temp_pack = os.path.join(tempfile.gettempdir(), "antigravity_new.asar")
        temp_unpacked = temp_pack + ".unpacked"
        if os.path.exists(temp_pack):
            os.remove(temp_pack)
        if os.path.exists(temp_unpacked):
            shutil.rmtree(temp_unpacked)

        run_cmd(
            asar_cmd + ["pack", work_dir, temp_pack, "--unpack-dir", "node_modules/chrome-devtools-mcp"],
            check=True,
        )
        if not has_i18n_marker(temp_pack):
            raise RuntimeError("打包产物完整性校验失败：未检测到注入模块")

        target_unpacked = target_asar + ".unpacked"
        if os.path.exists(temp_unpacked):
            if os.path.exists(target_unpacked):
                shutil.rmtree(target_unpacked)
            shutil.copytree(temp_unpacked, target_unpacked)
        shutil.copy2(temp_pack, target_asar)

        print("[OK] 汉化部署完成！请从系统托盘完全退出 Antigravity 并重新打开以生效。")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
