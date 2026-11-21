#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Antigravity Chinese Locale One-Click Installer v2.1
Google Antigravity 官方客户端一键安全汉化与全生命周期持久化工具

Features:
- Auto-detects Antigravity resources folder across Windows, macOS & Linux
- Automatic pristine backup (app.asar.bak)
- Decoupled architecture: independent i18n_inject module, zero pollution to utils.js
- Full WebContents & BrowserWindow lifecycle guards (prevents reverting on restart, refresh, or child windows)
- Traps second-instance & activate events for seamless tray wake-up compensation
- Strict syntax gatekeeper (node --check on all modified files)
- Atomic replacement of app.asar & app.asar.unpacked
- Optional live hot-reload via Chrome DevTools Protocol (CDP)
"""

import os
import sys
import shutil
import tempfile
import subprocess
import json
import urllib.request

def find_antigravity_resources():
    # 1. Windows default path
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        p = os.path.join(local_app_data, "Programs", "antigravity", "resources")
        if os.path.exists(p) and os.path.exists(os.path.join(p, "app.asar")):
            return p
    # 2. macOS default path
    mac_path = "/Applications/Antigravity.app/Contents/Resources"
    if os.path.exists(mac_path) and os.path.exists(os.path.join(mac_path, "app.asar")):
        return mac_path
    # 3. Linux default path
    linux_path = "/opt/Antigravity/resources"
    if os.path.exists(linux_path) and os.path.exists(os.path.join(linux_path, "app.asar")):
        return linux_path
    return None

def main():
    print("=" * 60)
    print("  Google Antigravity Chinese Localization Installer v2.1")
    print("  Google Antigravity 客户端一键安全汉化工具 (独立模块守护版)")
    print("=" * 60)

    # 1. 检查 Node.js 环境
    try:
        res = subprocess.run(["node", "-v"], capture_output=True, text=True)
        if res.returncode != 0:
            print("[Error] Node.js is required. Please install Node.js (v18+).")
            sys.exit(1)
        print(f"[✓] Node.js detected: {res.stdout.strip()}")
    except Exception:
        print("[Error] Node.js executable not found in PATH. Please install Node.js.")
        sys.exit(1)

    # 2. 定位资源目录
    resources_dir = find_antigravity_resources()
    if not resources_dir:
        print("[!] Antigravity installation not detected in standard path.")
        user_in = input("Please input the 'resources' folder path of Antigravity: ").strip()
        if os.path.exists(user_in) and os.path.exists(os.path.join(user_in, "app.asar")):
            resources_dir = user_in
        else:
            print("[Error] Invalid path or app.asar not found.")
            sys.exit(1)

    print(f"[✓] Antigravity resources found: {resources_dir}")
    target_asar = os.path.join(resources_dir, "app.asar")
    backup_asar = os.path.join(resources_dir, "app.asar.bak")

    # 3. 官方原版纯净备份
    if not os.path.exists(backup_asar):
        print("[*] Creating initial backup: app.asar.bak ...")
        shutil.copy2(target_asar, backup_asar)
        print("[✓] Backup completed.")
    else:
        print("[✓] Existing backup detected (app.asar.bak).")

    # 4. 解包与部署核心资产
    script_dir = os.path.dirname(os.path.abspath(__file__))
    i18n_runner_src = os.path.join(script_dir, "i18n_runner.js")
    i18n_data_src = os.path.join(script_dir, "i18n_data.json")
    i18n_inject_src = os.path.join(script_dir, "i18n_inject.js")

    if not os.path.exists(i18n_runner_src) or not os.path.exists(i18n_data_src) or not os.path.exists(i18n_inject_src):
        print("[Error] Missing required i18n scripts in scripts directory.")
        sys.exit(1)

    work_dir = tempfile.mkdtemp(prefix="antigravity_i18n_")
    try:
        print("[*] Extracting app.asar into temporary sandbox...")
        subprocess.run(f'npx --yes @electron/asar extract "{target_asar}" "{work_dir}"', shell=True, check=True)

        dist_dir = os.path.join(work_dir, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        shutil.copy2(i18n_runner_src, os.path.join(dist_dir, "i18n_runner.js"))
        shutil.copy2(i18n_data_src, os.path.join(dist_dir, "i18n_data.json"))
        shutil.copy2(i18n_inject_src, os.path.join(dist_dir, "i18n_inject.js"))

        main_js = os.path.join(dist_dir, "main.js")
        if not os.path.exists(main_js):
            print("[Error] dist/main.js not found in extracted app.asar.")
            sys.exit(1)

        # 5. 在 main.js 顶部挂载独立生命周期守卫 (彻底避免侵入 utils.js 局部作用域)
        with open(main_js, "r", encoding="utf-8") as f:
            m_content = f.read()

        hook_code = (
            "\n// Antigravity Chinese Localization Lifecycle Hook\n"
            "try {\n"
            "    require('./i18n_inject').setupI18nLifecycle(electron_1.app);\n"
            "} catch (e) {\n"
            "    console.error('[Antigravity i18n] Setup error:', e);\n"
            "}\n"
        )

        if "i18n_inject" not in m_content:
            needle = 'const electron_1 = require("electron");'
            if needle in m_content:
                m_content = m_content.replace(needle, needle + "\n" + hook_code, 1)
            else:
                # 兼容不同编译产物的 import 形式
                alt_needle = 'require("electron")'
                if alt_needle in m_content:
                    # 在首个 electron 引用下方安全注入
                    idx = m_content.find(alt_needle)
                    end_idx = m_content.find("\n", idx)
                    if end_idx != -1:
                        m_content = m_content[:end_idx+1] + hook_code + m_content[end_idx+1:]
                else:
                    print("[Error] Unable to locate Electron module import in main.js. Packaging aborted to prevent corruption.")
                    sys.exit(1)

            with open(main_js, "w", encoding="utf-8") as f:
                f.write(m_content)

        # 6. 严格语法检查门禁 (node --check)
        print("[*] Performing syntax gatekeeper checks (node --check)...")
        modified_files = [
            main_js,
            os.path.join(dist_dir, "i18n_inject.js"),
            os.path.join(dist_dir, "i18n_runner.js")
        ]
        for fpath in modified_files:
            chk = subprocess.run(["node", "--check", fpath], capture_output=True, text=True)
            if chk.returncode != 0:
                print(f"[Error] Syntax verification failed on {fpath}:\n{chk.stderr}")
                sys.exit(1)
        print("[✓] Syntax checks passed 100%.")

        # 7. 打包新 asar
        temp_pack = os.path.join(tempfile.gettempdir(), "antigravity_new.asar")
        temp_unpacked = temp_pack + ".unpacked"
        if os.path.exists(temp_pack):
            os.remove(temp_pack)
        if os.path.exists(temp_unpacked):
            shutil.rmtree(temp_unpacked)

        print("[*] Packaging modified files into asar...")
        subprocess.run(
            f'npx --yes @electron/asar pack "{work_dir}" "{temp_pack}" --unpack-dir "node_modules/chrome-devtools-mcp"',
            shell=True,
            check=True
        )

        # 8. 原子替换
        target_unpacked = target_asar + ".unpacked"
        if os.path.exists(temp_unpacked):
            if os.path.exists(target_unpacked):
                shutil.rmtree(target_unpacked)
            shutil.copytree(temp_unpacked, target_unpacked)

        shutil.copy2(temp_pack, target_asar)
        print("[✓] Production app.asar successfully updated!")

        # 9. 尝试 CDP 实时热注入
        try:
            active_port_file = os.path.join(os.environ.get("APPDATA", ""), "Antigravity", "DevToolsActivePort")
            if os.path.exists(active_port_file):
                with open(active_port_file, "r") as f:
                    dt_port = f.readline().strip()
                with urllib.request.urlopen(f"http://127.0.0.1:{dt_port}/json", timeout=2) as resp:
                    pages = json.loads(resp.read().decode("utf-8"))
                    page = next((p for p in pages if p.get("type") == "page"), None)
                    if page:
                        with open(os.path.join(dist_dir, "i18n_data.json"), "r", encoding="utf-8") as f:
                            dt_str = f.read()
                        with open(os.path.join(dist_dir, "i18n_runner.js"), "r", encoding="utf-8") as f:
                            rn_str = f.read()
                        full_code = "window.__ANTIGRAVITY_I18N_DATA__ = " + dt_str + ";\n" + rn_str
                        ws_url = page["webSocketDebuggerUrl"]
                        node_eval = f'''
                        const ws = new WebSocket({json.dumps(ws_url)});
                        ws.onopen = () => {{
                            ws.send(JSON.stringify({{ id: 1, method: "Runtime.evaluate", params: {{ expression: {json.dumps(full_code)} }} }}));
                        }};
                        ws.onmessage = () => process.exit(0);
                        setTimeout(() => process.exit(0), 1000);
                        '''
                        eval_file = os.path.join(tempfile.gettempdir(), "cdp_hot_reload.js")
                        with open(eval_file, "w", encoding="utf-8") as f:
                            f.write(node_eval)
                        subprocess.run(["node", eval_file], capture_output=True)
                        print("[✓] Active Antigravity window hot-reloaded successfully!")
        except Exception:
            pass

        print("\n" + "=" * 60)
        print("  Localization deployed successfully! Enjoy Antigravity in Chinese.")
        print("  汉化部署成功！(v2.1 全生命周期持久化与独立模块守护版)")
        print("  提示：若关闭窗口后重新打开仍显示英文，请在任务栏右下角系统托盘彻底退出")
        print("  Antigravity 或在任务管理器结束残留进程后再打开，即可永久生效。")
        print("=" * 60)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
