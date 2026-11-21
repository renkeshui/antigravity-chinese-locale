---
name: Chinesizing
description: Electron 桌面端软件深度汉化、解包逆向、防崩溃与防卡死全流程工程规范。用于对 Electron / React 桌面应用进行界面国际化、安全打包部署、DOM 监听死循环规避、UI 组件键值反向透传与自动化门禁自检。
---

# Electron 桌面端软件深度汉化与工程规范

针对 Electron 架构客户端（React、Base UI、Monaco Editor 等现代复杂桌面应用），规范解包逆向、动态 DOM 汉化、防主进程崩溃、防渲染层死循环与受控组件键值透传全流程工程标准。

## 五大核心架构原则

1. **数据与逻辑解耦**：翻译词典独立为 `i18n_data.json`，严禁在执行逻辑中以 ES6 模板字符串字面量硬编码；
2. **全生命周期守卫**：通过 `app.on('web-contents-created')` 建立拦截网，100% 覆盖新建窗口、子窗口、F5 刷新与页面重载；
3. **严格门禁（Gatekeeper）**：任何改动写入封包前，必须 100% 通过 `node --check` 静态语法校验及沙箱模拟解包测试；
4. **受控组件双向一致**：拦截底层 Map/事件回调，保障组件库（Base UI、Radix UI）内部状态机与中文展示无缝映射；
5. **值比对渐进自愈**：依靠实时文本值比对实现 SPA 异步渲染自愈，严禁使用永久阻断型引用标记。

## 渲染层与主进程核心防御规范

### 1. 规避模板字符串反引号嵌套崩溃
- **红线**：严禁在注入脚本拼接中嵌套未转义的 ES6 反引号，防止模板内部插值提前闭合导致 SyntaxError 崩溃；
- **规范**：字符串拼接退回安全的 ES5 单/双引号加号拼接，发布前强制执行 `node --check`。

### 2. MutationObserver 监听锁定与防重入锁
- **红线**：**绝对严禁全文档开启 `characterData: true`**（修改 `nodeValue` 会抛出新的微任务引发无限递归卡死）；
- **规范**：监听配置严格锁定为 `{ childList: true, subtree: true }`，并配备原子防重入锁：
  ```javascript
  var isTranslating = false;
  var obs = new MutationObserver(function (mutations) {
      if (isTranslating) return;
      isTranslating = true;
      try {
          for (var i = 0; i < mutations.length; i++) {
              if (mutations[i].type === "childList") {
                  for (var j = 0; j < mutations[i].addedNodes.length; j++) {
                      translateSubtree(mutations[i].addedNodes[j]);
                  }
              }
          }
      } finally {
          isTranslating = false;
      }
  });
  ```

### 3. SPA 纯值比对自愈（禁用阻断性 WeakSet）
- **红线**：严禁使用 `new WeakSet()` 记录已汉化 DOM 节点（会导致异步加载与路由复用时永久回退为英文）；
- **规范**：采用纯值比对法，仅在匹配且值不相同时赋值；已汉化节点二次匹配为 `null`，无重复触发风险：
  ```javascript
  function translateTextNode(node) {
      if (!node || node.nodeType !== 3) return;
      var val = node.nodeValue;
      if (!val || !val.trim() || isInsideExcluded(node)) return;
      var translated = getTranslatedText(val);
      if (translated !== null && translated !== val) {
          node.nodeValue = translated;
      }
  }
  ```

### 4. 受控组件双向映射桥（解决选项卡死）
- **红线**：Base UI 等受控组件在内部通过原生英文 Map 校验值，DOM 改为中文后回调回传中文会导致事件被静默拒绝、弹窗无法关闭；
- **规范**：维护 `reverse_map`（中文 ➔ 英文），全局拦截 `Map.prototype.has` 与 `get`：
  ```javascript
  (function () {
      var origHas = Map.prototype.has, origGet = Map.prototype.get;
      Map.prototype.has = function (k) {
          if (origHas.call(this, k)) return true;
          var rev = window.__ANTIGRAVITY_REVERSE_MAP__ || {};
          return typeof k === "string" && rev[k] ? origHas.call(this, rev[k]) : false;
      };
      Map.prototype.get = function (k) {
          var val = origGet.call(this, k);
          if (val !== undefined) return val;
          var rev = window.__ANTIGRAVITY_REVERSE_MAP__ || {};
          return typeof k === "string" && rev[k] ? origGet.call(this, rev[k]) : undefined;
      };
  })();
  ```

### 5. 主进程全生命周期与后台驻留释放
- **全生命周期绑定**：
  ```javascript
  app.on('web-contents-created', (_event, wc) => {
      wc.on('dom-ready', () => injectI18n(wc));
      wc.on('did-finish-load', () => injectI18n(wc));
      wc.on('did-navigate-in-page', () => injectI18n(wc));
  });
  ```
- **彻底释放驻留进程**：针对托盘常驻应用，替换 `app.asar` 前必须通过 `taskkill /f /im App.exe` 彻底结束后台进程，或配套交付重启批处理（`进程强杀 ➔ 延迟1秒释放句柄 ➔ 重新拉起`）；
- **内联标签切片文本**：对被 `<a>` / `<span>` 切割的句子，按前后独立 TextNode 分离配对翻译；
- **热重载支持**：词典挂载至 `window.__ANTIGRAVITY_EXACT__`，重注时触发全量页面增量重译；
- **`.unpacked` 依赖原子替换**：打包声明 `--unpack-dir`，部署时与 `app.asar` 同步成对替换。

### 6. 严禁特征锚点失效时追加至模块顶层（防 win is not defined 崩溃）
- **红线**：部署脚本使用字符串特征码（如 `"win.webContents.setWindowOpenHandler"`）查找注入位置时，一旦因客户端版本升级、代码混淆或二次修改未命中，**绝对严禁在 `else` 中兜底追加到文件末尾**！局部变量 `win` 泄露至 CJS 模块顶层会在应用启动 `require` 阶段立即引发 `ReferenceError: win is not defined` 崩溃；
- **规范**：
  1. 锚点查找失败必须明确报错并中断打包，绝不带病生成损坏包；
  2. 优先采用 Electron 原生生命周期事件（如 `app.on('browser-window-created', (event, win) => ...)`），直接使用运行时注入的 `win` 参数，从根本上摆脱对具体函数名和内部局部变量名的脆弱依赖。

## 自动化巡检与 SOP 标准作业程序

1. **资产备份**：复制官方原包为 `app.asar.bak`；
2. **字典构建**：产出标准 `i18n_data.json` 并配套受控组件 `reverse_map`；
3. **编写执行器**：实现 `childList` 单向监听、值比对自愈与 Map 原型链拦截；
4. **语法门禁**：对脚本执行 `node --check` 必须 0 报错；
5. **沙箱闭环测试**：打包测试 ASAR ➔ 解包至临时目录 ➔ 二次 `node --check`；
6. **成对原子部署**：同时替换 `app.asar` 与 `app.asar.unpacked`；
7. **CDP 巡检**：连接 Chrome 调试端口，遍历各 Tab，通过 TreeWalker 探测未汉化可见文本（排查 `[placeholder]`, `[title]`, `[aria-label]`）；
8. **释放驻留进程**：终止后台旧主进程，拉起新实例验证生效。
