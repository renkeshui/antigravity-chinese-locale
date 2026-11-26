---
name: Chinesizing
description: Electron 桌面端软件深度汉化、解包逆向、防崩溃与防卡死全流程工程规范。用于对 Electron / React 桌面应用进行界面国际化、安全打包部署、DOM 监听死循环规避、UI 组件键值反向透传与自动化门禁自检。
---

# Electron 桌面端软件深度汉化工程规范

针对 Electron + React / Base UI / Monaco Editor 等现代桌面应用，规范逆向提取、动态 DOM 汉化、防崩溃与安全部署全流程。

## 一、词典构建与前端提取

1. **数据与逻辑解耦**：翻译词典独立为 `i18n_data.json`（含 `exact`、`reverse_map`、`regex_rules`、`exemptions`），严禁在注入逻辑中以 ES6 模板字符串字面量硬编码。
2. **前端 Bundle 离线提取**：当 `app.asar` 仅含主进程代码、UI 由本地服务动态下发时，扫描用户数据目录 `Cache/Cache_Data/f_*`（跳过被锁定的 `data_*` 索引），对明文或内嵌 gzip 流解压即可提取完整前端 JS bundle，系统性抽取设置项（`label`/`description`/`title`）、快捷键与组件文案。
3. **专有名词豁免与动态模板**：约定俗成的产品/技术专有名词、按键名、字体名、数值与色值（如 `Antigravity`、`VS Code`、`MCP`、`WSL`、`Turbo`、`Enter`、`14px`、`#FFFFFF`）保持英文/数字不译；带动态变量的文案（如 `Your plan: ...`、`Available AI credits: ...`）写入 `regex_rules`；被 `<a>`/`<span>` 切割的句子按独立 TextNode 分段匹配。
4. **受控枚举同步**：凡在 `exact` 中新增下拉框、分段开关等受控组件枚举项（如 `Request Review`/`Auto`/`Verbose`/`Strong`）时，必须同步补齐 `reverse_map`（中文 ➔ 英文）。

## 二、渲染层与主进程防御红线

### 1. 规避反引号嵌套崩溃
- **红线**：注入脚本拼接严禁嵌套未转义的 ES6 反引号，防止模板插值提前闭合引发 `SyntaxError`；
- **规范**：字符串拼接使用 ES5 单/双引号加号拼接，发布前强制执行 `node --check`。

### 2. MutationObserver 锁定与防重入锁
- **红线**：**严禁全文档开启 `characterData: true`**（修改 `nodeValue` 会触发微任务无限递归卡死）；
- **规范**：锁定 `{ childList: true, subtree: true }` 并配备互斥锁：
  ```javascript
  var isTranslating = false;
  var obs = new MutationObserver(function (mutations) {
      if (isTranslating) return;
      isTranslating = true;
      try {
          mutations.forEach(function (m) {
              if (m.type === "childList") {
                  m.addedNodes.forEach(translateSubtree);
              }
          });
      } finally {
          isTranslating = false;
      }
  });
  ```

### 3. SPA 纯值比对自愈（禁用 WeakSet）
- **红线**：严禁使用 `new WeakSet()` 标记已汉化节点（SPA 路由复用或异步重渲时会永久回退为英文）；
- **规范**：仅在译文非空且与当前值不同时赋值（二次匹配为 `null`，无死循环风险）：
  ```javascript
  function translateTextNode(node) {
      if (!node || node.nodeType !== 3) return;
      var val = node.nodeValue;
      if (!val || !val.trim() || isInsideExcluded(node)) return;
      var translated = getTranslatedText(val);
      if (translated !== null && translated !== val) node.nodeValue = translated;
  }
  ```

### 4. 受控组件双向映射桥（解决选项卡死）
- **红线**：Base UI / Radix UI 等组件内部通过原生英文 `Map` 校验值，DOM 改为中文后回调回传中文会导致事件静默失败或弹窗无法关闭；
- **规范**：全局拦截 `Map.prototype.has` / `get`，未命中时通过 `reverse_map` 回查英文原键，并挂载 `window.__ANTIGRAVITY_EXACT__` 支持热重载：
  ```javascript
  (function () {
      var origHas = Map.prototype.has, origGet = Map.prototype.get;
      function revKey(k) {
          var rev = window.__ANTIGRAVITY_REVERSE_MAP__ || {};
          return typeof k === "string" ? rev[k] : undefined;
      }
      Map.prototype.has = function (k) {
          if (origHas.call(this, k)) return true;
          var ek = revKey(k);
          return ek ? origHas.call(this, ek) : false;
      };
      Map.prototype.get = function (k) {
          var val = origGet.call(this, k);
          if (val !== undefined) return val;
          var ek = revKey(k);
          return ek ? origGet.call(this, ek) : undefined;
      };
  })();
  ```

### 5. 主进程生命周期注入（防 `win is not defined` 崩溃）
- **红线**：特征锚点（如 `"win.webContents.setWindowOpenHandler"`）未命中时，**严禁兜底追加到文件末尾**，否则局部变量 `win` 泄露至模块顶层会导致启动即报 `ReferenceError: win is not defined`；锚点失效必须报错并中断打包；
- **规范**：优先使用 Electron 原生生命周期事件直接接收参数，覆盖新建窗口、F5 刷新与热重载：
  ```javascript
  app.on('web-contents-created', (_e, wc) => {
      ['dom-ready', 'did-finish-load', 'did-navigate-in-page'].forEach(ev => {
          wc.on(ev, () => injectI18n(wc));
      });
  });
  ```

## 三、打包部署与交付 SOP

0. **仓库同步（上游更新）**：若基于仓库 `https://github.com/renkeshui/antigravity-chinese-locale.git` 安装或更新本技能，执行前先从 `main` 分支拉取（`git pull` 或重新下载）最新 `skills/Chinesizing/SKILL.md` 与 `scripts/`（`i18n_data.json`、`deploy_chinese.py` 等），并将 `SKILL.md` 同步至全局技能目录，确保词典与脚本为最新版本。
1. **资产备份**：复制官方原包为 `app.asar.bak`（若使用 `scripts/deploy_chinese.py`，会自动识别官方新版本并刷新备份）。
2. **门禁校验**：对所有修改与注入脚本执行 `node --check`（必须 0 报错），并运行自动化门禁测试。
3. **沙箱闭环**：`asar pack`（声明 `--unpack-dir`）生成测试包 ➔ 解包至临时目录 ➔ 二次 `node --check` 与词典完整性校验。
4. **成对原子部署**：将 `app.asar` 与 `app.asar.unpacked` 同步原子替换至生产目录。
5. **CDP 巡检（可选）**：连接调试端口遍历 Tab，通过 `TreeWalker` 探测遗漏可见文本及 `[placeholder]` / `[title]` / `[aria-label]`。
6. **无打扰自主重启交付**：助手运行于目标客户端宿主机进程内时，**严禁未经授权强杀客户端进程**（会瞬间中断当前会话）；完成原子部署后即止，提示用户随时从系统托盘完全退出旧进程并重新打开即可生效（仅在用户明确要求代为重启时再提供延迟脱离重启）。
