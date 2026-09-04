(function () {
    var data = window.__antigravity_i18n_data;
    if (!data) return;

    var I18N_MAP = data.map || {};
    var PHRASES = data.phrases || [];
    var REVERSE_MAP = data.reverse_map || {};

    // 1. 全局拦截 Map.prototype.has 和 get，实现 Base UI / React 下拉选项反向透传
    if (!window.__antigravity_map_hooked) {
        window.__antigravity_map_hooked = true;
        var origHas = Map.prototype.has;
        var origGet = Map.prototype.get;

        Map.prototype.has = function (key) {
            if (origHas.call(this, key)) return true;
            if (typeof key === "string" && REVERSE_MAP[key]) {
                return origHas.call(this, REVERSE_MAP[key]);
            }
            return false;
        };

        Map.prototype.get = function (key) {
            var val = origGet.call(this, key);
            if (val !== undefined) return val;
            if (typeof key === "string" && REVERSE_MAP[key]) {
                return origGet.call(this, REVERSE_MAP[key]);
            }
            return undefined;
        };
    }

    var translatedNodes = new WeakSet();

    function translateNode(node) {
        if (!node || translatedNodes.has(node)) return;

        if (node.nodeType === 3) {
            var text = node.nodeValue;
            if (!text) return;
            var trimmed = text.trim();
            if (!trimmed) return;

            // 动态配额倒计时小字：保持原始英文，绝不翻译
            if (trimmed.indexOf("it will fully refresh in") !== -1 || trimmed.indexOf("limit, it will") !== -1) {
                return;
            }

            // 自定义扩展 Token 剩余百分比动态匹配
            if (trimmed.indexOf("of the customization budget is available.") !== -1) {
                node.nodeValue = text.replace("of the customization budget is available.", "的自定义扩展配额可用。");
                translatedNodes.add(node);
                return;
            }

            // 自定义扩展 Show X breakdown(s) 动态匹配
            if (/^Show \d+ breakdown(s?)$/.test(trimmed)) {
                var num = trimmed.match(/\d+/)[0];
                node.nodeValue = text.replace(trimmed, "查看 " + num + " 项明细");
                translatedNodes.add(node);
                return;
            }
            if (/^Hide breakdown(s?)$/.test(trimmed)) {
                node.nodeValue = text.replace(trimmed, "收起明细");
                translatedNodes.add(node);
                return;
            }

            // 字典精准匹配
            if (I18N_MAP[trimmed]) {
                node.nodeValue = text.replace(trimmed, I18N_MAP[trimmed]);
                translatedNodes.add(node);
                return;
            }

            // 复合短句替换
            var replaced = text;
            for (var i = 0; i < PHRASES.length; i++) {
                var en = PHRASES[i][0];
                var zh = PHRASES[i][1];
                if (replaced.indexOf(en) !== -1) {
                    replaced = replaced.split(en).join(zh);
                }
            }
            if (replaced !== text) {
                node.nodeValue = replaced;
                translatedNodes.add(node);
            }
        } else if (node.nodeType === 1) {
            var tag = node.tagName ? node.tagName.toLowerCase() : "";
            if (tag === "code" || tag === "pre" || tag === "style" || tag === "script") return;
            if (node.closest && node.closest(".monaco-editor, pre, code")) return;

            if (node.placeholder && I18N_MAP[node.placeholder.trim()]) {
                node.placeholder = I18N_MAP[node.placeholder.trim()];
            }
            if (node.title && I18N_MAP[node.title.trim()]) {
                node.title = I18N_MAP[node.title.trim()];
            }
            var aria = node.getAttribute && node.getAttribute("aria-label");
            if (aria && I18N_MAP[aria.trim()]) {
                node.setAttribute("aria-label", I18N_MAP[aria.trim()]);
            }

            for (var c = node.firstChild; c; c = c.nextSibling) {
                translateNode(c);
            }
        }
    }

    // 初次遍历
    translateNode(document.body);

    // 重新连接并单例保护
    if (window.__antigravity_i18n_observer_instance) {
        window.__antigravity_i18n_observer_instance.disconnect();
    }

    var isTranslating = false;
    var obs = new MutationObserver(function (mutations) {
        if (isTranslating) return;
        isTranslating = true;
        try {
            for (var i = 0; i < mutations.length; i++) {
                var m = mutations[i];
                if (m.type === "childList") {
                    for (var j = 0; j < m.addedNodes.length; j++) {
                        translateNode(m.addedNodes[j]);
                    }
                }
            }
        } finally {
            isTranslating = false;
        }
    });

    // 严禁监听 characterData，彻底阻绝任何输入与下拉点击死循环
    obs.observe(document.body, { childList: true, subtree: true });
    window.__antigravity_i18n_observer_instance = obs;
})();