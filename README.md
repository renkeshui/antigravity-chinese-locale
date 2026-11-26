# Antigravity Chinese Locale (Chinesizing)

Google Antigravity 桌面客户端简体中文汉化包与工程规范（支持 Agent Skill 与独立 Python 脚本两种方式）。

[中文说明](#中文说明) | [English](#english)

---

<a name="中文说明"></a>

## 中文说明

### 核心特性
- **全面覆盖（823+ 词条）**：覆盖常规/应用/外观/快捷键/通知/模型配额/浏览器设置、权限预设下拉框与原生窗口/托盘菜单；约定俗成的专有名词、按键与数值保持英文。
- **全生命周期守卫**：主进程挂载 `web-contents-created` 与 `browser-window-created`，覆写 `second-instance` / `activate`，避免刷新、跳转或托盘唤醒后回退英文，且对 `utils.js` 零修改。
- **零卡死与受控组件自愈**：`MutationObserver` 禁用 `characterData` 监听并配互斥锁，采用纯值比对（禁用 `WeakSet`）；通过 `Map.prototype` 双向映射桥保证 Base UI 下拉框与弹窗正常交互。
- **升级防坑与一键还原**：自动识别官方新版本并刷新 `app.asar.bak`，支持 `--restore` 一键恢复官方英文原版。

### 环境要求
- Google Antigravity 客户端（Windows / macOS / Linux）
- Node.js v18+（含 `npx` 或全局 `asar`）
- Python 3.8+（仅使用标准库，无需额外 `pip` 依赖）

### 快速开始

#### 方式一：作为 Antigravity Skill（推荐）
1. 将 [`skills/Chinesizing`](skills/Chinesizing) 复制到 Antigravity 全局技能目录：
   - **Windows**：`%USERPROFILE%\.gemini\config\skills\Chinesizing\`
   - **macOS / Linux**：`~/.gemini/config/skills/Chinesizing/`
2. 在对话中输入 `/Chinesizing` 让智能体执行汉化部署或增量补词。

#### 方式二：独立 Python 脚本
```bash
git clone https://github.com/renkeshui/antigravity-chinese-locale.git
cd antigravity-chinese-locale

# 部署汉化（运行前请先从系统托盘完全退出 Antigravity）
python scripts/deploy_chinese.py

# 如需还原官方英文原版
python scripts/deploy_chinese.py --restore
```

> **生效方式**：部署完成后，若客户端仍在后台运行，请在右下角系统托盘右键**退出**并重新打开 Antigravity 即可生效。

### 增量词条维护
官方客户端更新后若出现新英文界面，可运行离线提取脚本扫描 Chromium 缓存中的前端词条进行补充：
```bash
python scripts/extract_ui_strings.py
```

---

<a name="english"></a>

## English

Simplified Chinese localization package and engineering skill for the Google Antigravity desktop client.

### Highlights
- **823+ Entries**: Localizes Settings, Shortcuts, Notifications, Model Quotas, Browser preferences, dropdown presets, and native menus while preserving conventional English technical terms and numbers.
- **Lifecycle & Crash Guards**: Hooks `web-contents-created` and `browser-window-created` without touching `utils.js`. Disables `characterData` observation, avoids `WeakSet`, and proxies `Map.prototype` so Base UI controlled components work smoothly.
- **Safe Upgrades & Rollback**: Automatically refreshes `app.asar.bak` on official client updates and supports `--restore` to revert to the original English build.

### Usage
```bash
# Quit Antigravity from the system tray first, then run:
python scripts/deploy_chinese.py

# Restore original English version:
python scripts/deploy_chinese.py --restore
```

## License
[MIT](LICENSE) © 2026 renkeshui
