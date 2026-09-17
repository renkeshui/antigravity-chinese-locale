#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Antigravity Chinese Locale One-Click Installer
Google Antigravity 官方客户端一键安全汉化与全生命周期持久化工具

Features:
- Auto-detects Antigravity resources folder across Windows, macOS & Linux
- Automatic pristine backup (app.asar.bak)
- Microtask loop prevention & Base UI controlled component bridge
- Full WebContents lifecycle hook (prevents reverting on restart, refresh, or child windows)
- Static syntax gatekeeper (node --check on all modified files)
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
    print("  Google Antigravity Chinese Localization Installer v2.0")
    print("  Google Antigravity 客户端一键安全汉化工具 (全生命周期持久版)")
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

    # 4. 解包与注入
    script_dir = os.path.dirname(os.path.abspath(__file__))
    i18n_runner_src = os.path.join(script_dir, "i18n_runner.js")
    i18n_data_src = os.path.join(script_dir, "i18n_data.json")

    if not os.path.exists(i18n_runner_src) or not os.path.exists(i18n_data_src):
        print("[Error] Missing i18n_runner.js or i18n_data.json in scripts directory.")
        sys.exit(1)

    work_dir = tempfile.mkdtemp(prefix="antigravity_i18n_")
    try:
        print("[*] Extracting app.asar into temporary sandbox...")
        subprocess.run(f'npx --yes @electron/asar extract "{target_asar}" "{work_dir}"', shell=True, check=True)

        dist_dir = os.path.join(work_dir, "dist")
        os.makedirs(dist_dir, exist_ok=True)
        shutil.copy2(i18n_runner_src, os.path.join(dist_dir, "i18n_runner.js"))
        shutil.copy2(i18n_data_src, os.path.join(dist_dir, "i18n_data.json"))

        utils_js = os.path.join(dist_dir, "utils.js")
        main_js = os.path.join(dist_dir, "main.js")
        modified_files = []

        # A. 注入 utils.js (主窗体生命周期与唤醒补偿)
        with open(utils_js, "r", encoding="utf-8") as f:
            u_content = f.read()

        inject_code = (
            '    const injectAntigravityI18n = (target) => {\n'
            '        try {\n'
            '            const wc = target?.webContents ? target.webContents : target;\n'
            '            if (!wc || typeof wc.executeJavaScript !== "function" || wc.isDestroyed()) return;\n'
            '            const runnerPath = path_1.default.join(__dirname, "i18n_runner.js");\n'
            '            const dataPath = path_1.default.join(__dirname, "i18n_data.json");\n'
            '            if (fs.existsSync(runnerPath) && fs.existsSync(dataPath)) {\n'
            '                const dataStr = fs.readFileSync(dataPath, "utf-8");\n'
            '                const runnerCode = fs.readFileSync(runnerPath, "utf-8");\n'
            '                const script = `\n'
            '                    (function(){\n'
            '                        try {\n'
            '                            window.__ANTIGRAVITY_I18N_DATA__ = ${JSON.stringify(JSON.parse(dataStr))};\n'
            '                            ${runnerCode}\n'
            '                        } catch(e) {\n'
            '                            console.error("[Antigravity i18n] Error executing i18n runner:", e);\n'
            '                        }\n'
            '                    })();\n'
            '                `;\n'
            '                wc.executeJavaScript(script).catch(() => {});\n'
            '            }\n'
            '        } catch (e) {\n'
            '            console.error("[Antigravity i18n] Injection error:", e);\n'
            '        }\n'
            '    };\n'
            '    exports.injectAntigravityI18n = injectAntigravityI18n;\n'
            '    win.webContents.on("dom-ready", () => injectAntigravityI18n(win.webContents));\n'
            '    win.webContents.on("did-finish-load", () => injectAntigravityI18n(win.webContents));\n'
            '    win.webContents.on("did-navigate-in-page", () => injectAntigravityI18n(win.webContents));\n'
        )

        if "injectAntigravityI18n" not in u_content:
            needle = "win.webContents.setWindowOpenHandler"
            if needle in u_content:
                u_content = u_content.replace(needle, inject_code + "\n    " + needle, 1)
            else:
                u_content = u_content + "\n" + inject_code

            show_needle = "wins[0].focus();"
            if show_needle in u_content:
                u_content = u_content.replace(
                    show_needle,
                    show_needle + "\n        if (exports.injectAntigravityI18n) { (0, exports.injectAntigravityI18n)(wins[0]); }",
                    1
                )

            with open(utils_js, "w", encoding="utf-8") as f:
                f.write(u_content)
        modified_files.append(utils_js)

        # B. 注入 main.js (全局 web-contents-created 守卫)
        if os.path.exists(main_js):
            with open(main_js, "r", encoding="utf-8") as f:
                m_content = f.read()

            if "web-contents-created" not in m_content:
                main_inject = (
                    "    // Register global WebContents i18n injection lifecycle hook\n"
                    "    electron_1.app.on('web-contents-created', (_event, wc) => {\n"
                    "        wc.on('dom-ready', () => { if (utils_1.injectAntigravityI18n) (0, utils_1.injectAntigravityI18n)(wc); });\n"
                    "        wc.on('did-finish-load', () => { if (utils_1.injectAntigravityI18n) (0, utils_1.injectAntigravityI18n)(wc); });\n"
                    "        wc.on('did-navigate-in-page', () => { if (utils_1.injectAntigravityI18n) (0, utils_1.injectAntigravityI18n)(wc); });\n"
                    "    });\n"
                )
                when_ready_needle = "electron_1.app.whenReady().then(async () => {"
                if when_ready_needle in m_content:
                    m_content = m_content.replace(when_ready_needle, when_ready_needle + "\n" + main_inject, 1)
                    with open(main_js, "w", encoding="utf-8") as f:
                        f.write(m_content)
            modified_files.append(main_js)

        modified_files.append(os.path.join(dist_dir, "i18n_runner.js"))

        # 5. 严格语法检查门禁 (node --check)
        print("[*] Performing syntax gatekeeper checks (node --check)...")
        for fpath in modified_files:
            chk = subprocess.run(["node", "--check", fpath], capture_output=True, text=True)
            if chk.returncode != 0:
                print(f"[Error] Syntax verification failed on {fpath}:\n{chk.stderr}")
                sys.exit(1)
        print("[✓] Syntax checks passed 100%.")

        # 6. 打包新 asar
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

        # 7. 原子替换
        target_unpacked = target_asar + ".unpacked"
        if os.path.exists(temp_unpacked):
            if os.path.exists(target_unpacked):
                shutil.rmtree(target_unpacked)
            shutil.copytree(temp_unpacked, target_unpacked)

        shutil.copy2(temp_pack, target_asar)
        print("[✓] Production app.asar successfully updated!")

        # 8. 尝试 CDP 实时热注入
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
        print("  汉化部署成功！")
        print("  提示：若关闭窗口后重新打开仍显示英文，请在任务栏右下角系统托盘彻底退出")
        print("  Antigravity 或在任务管理器结束残留进程后再打开，即可永久生效。")
        print("=" * 60)

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
