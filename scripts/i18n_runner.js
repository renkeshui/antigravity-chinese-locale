(function () {
    var data = window.__ANTIGRAVITY_I18N_DATA__ || {};
    var EXACT = data.exact || {};
    var REVERSE_MAP = data.reverse_map || {};
    var REGEX_RULES = [];
    if (Array.isArray(data.regex_rules)) {
        for (var i = 0; i < data.regex_rules.length; i++) {
            try {
                REGEX_RULES.push({
                    re: new RegExp(data.regex_rules[i].pattern),
                    rep: data.regex_rules[i].replacement
                });
            } catch (e) {}
        }
    }
    var EXEMPTIONS = data.exemptions || [];

    // Always update global store on new data injection
    window.__ANTIGRAVITY_EXACT__ = Object.assign(window.__ANTIGRAVITY_EXACT__ || {}, EXACT);
    window.__ANTIGRAVITY_REVERSE_MAP__ = Object.assign(window.__ANTIGRAVITY_REVERSE_MAP__ || {}, REVERSE_MAP);
    window.__ANTIGRAVITY_REGEX_RULES__ = REGEX_RULES;
    window.__ANTIGRAVITY_EXEMPTIONS__ = EXEMPTIONS;

    if (window.__antigravity_i18n_runner_active) {
        if (typeof window.__antigravity_translateWholePage === 'function') {
            window.__antigravity_translateWholePage();
        }
        return;
    }
    window.__antigravity_i18n_runner_active = true;

    // 1. Controlled Component Reverse Map Hook (Protects Base UI / Radix Select states)
    if (!window.__antigravity_map_hooked) {
        window.__antigravity_map_hooked = true;
        var origHas = Map.prototype.has;
        var origGet = Map.prototype.get;

        Map.prototype.has = function (key) {
            if (origHas.call(this, key)) return true;
            var rev = window.__ANTIGRAVITY_REVERSE_MAP__ || REVERSE_MAP;
            if (typeof key === "string" && rev[key]) {
                return origHas.call(this, rev[key]);
            }
            return false;
        };

        Map.prototype.get = function (key) {
            var val = origGet.call(this, key);
            if (val !== undefined) return val;
            var rev = window.__ANTIGRAVITY_REVERSE_MAP__ || REVERSE_MAP;
            if (typeof key === "string" && rev[key]) {
                return origGet.call(this, rev[key]);
            }
            return undefined;
        };
    }

    // 2. Isolation & Exemption Checks
    var EXCLUDED_TAGS = {
        "SCRIPT": true,
        "STYLE": true,
        "PRE": true,
        "CODE": true,
        "TEXTAREA": true
    };

    function isInsideExcluded(node) {
        var curr = node;
        while (curr && curr !== document.body && curr !== document.documentElement) {
            if (curr.nodeType === 1) {
                var tag = curr.tagName;
                if (EXCLUDED_TAGS[tag]) return true;
                if (curr.isContentEditable) return true;
                var cls = curr.className;
                if (typeof cls === "string" && (
                    cls.indexOf("monaco-editor") !== -1 ||
                    cls.indexOf("token") !== -1 ||
                    cls.indexOf("syntax") !== -1
                )) {
                    return true;
                }
            }
            curr = curr.parentNode;
        }
        return false;
    }

    function isExempt(text) {
        var exemptions = window.__ANTIGRAVITY_EXEMPTIONS__ || EXEMPTIONS;
        for (var i = 0; i < exemptions.length; i++) {
            if (text.indexOf(exemptions[i]) !== -1) {
                return true;
            }
        }
        return false;
    }

    function getTranslatedText(original) {
        var trimmed = original.trim();
        if (!trimmed) return null;
        if (isExempt(original)) return null;

        var exactMap = window.__ANTIGRAVITY_EXACT__ || EXACT;
        var regexList = window.__ANTIGRAVITY_REGEX_RULES__ || REGEX_RULES;

        // Exact match
        if (exactMap[trimmed]) {
            var target = exactMap[trimmed];
            var leading = original.match(/^\s*/)[0];
            var trailing = original.match(/\s*$/)[0];
            return leading + target + trailing;
        }

        // Regex dynamic rules
        for (var i = 0; i < regexList.length; i++) {
            if (regexList[i].re.test(trimmed)) {
                var replaced = trimmed.replace(regexList[i].re, regexList[i].rep);
                var lead = original.match(/^\s*/)[0];
                var trail = original.match(/\s*$/)[0];
                return lead + replaced + trail;
            }
        }

        return null;
    }

    // 3. Node Translation Engine (Pure value matching, no harmful WeakSet blocking)
    function translateTextNode(textNode) {
        if (!textNode || textNode.nodeType !== 3) return;
        var val = textNode.nodeValue;
        if (!val || !val.trim()) return;

        if (isInsideExcluded(textNode)) return;

        var translated = getTranslatedText(val);
        if (translated !== null && translated !== val) {
            textNode.nodeValue = translated;
        }
    }

    function translateElementAttributes(el) {
        if (!el || el.nodeType !== 1) return;
        if (EXCLUDED_TAGS[el.tagName]) return;

        // placeholder
        if (el.hasAttribute("placeholder")) {
            var ph = el.getAttribute("placeholder");
            var tPh = getTranslatedText(ph);
            if (tPh !== null && tPh !== ph) el.setAttribute("placeholder", tPh);
        }
        // title
        if (el.hasAttribute("title")) {
            var tit = el.getAttribute("title");
            var tTit = getTranslatedText(tit);
            if (tTit !== null && tTit !== tit) el.setAttribute("title", tTit);
        }
        // aria-label
        if (el.hasAttribute("aria-label")) {
            var al = el.getAttribute("aria-label");
            var tAl = getTranslatedText(al);
            if (tAl !== null && tAl !== al) el.setAttribute("aria-label", tAl);
        }
    }

    function translateSubtree(root) {
        if (!root) return;
        if (root.nodeType === 3) {
            translateTextNode(root);
            return;
        }
        if (root.nodeType === 1) {
            if (isInsideExcluded(root)) return;
            translateElementAttributes(root);
            var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while ((node = walker.nextNode())) {
                translateTextNode(node);
            }
            var elementsWithAttrs = root.querySelectorAll("[placeholder], [title], [aria-label]");
            for (var i = 0; i < elementsWithAttrs.length; i++) {
                translateElementAttributes(elementsWithAttrs[i]);
            }
        }
    }

    // 4. Initial Full Page Translation & Lifecycle Hooks
    function translateWholePage() {
        var target = document.body || document.documentElement;
        if (target) {
            translateSubtree(target);
        }
    }
    window.__antigravity_translateWholePage = translateWholePage;

    translateWholePage();

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", translateWholePage);
    }
    window.addEventListener("load", translateWholePage);

    // SPA client-side routing triggers
    window.addEventListener("popstate", function() { setTimeout(translateWholePage, 50); });
    window.addEventListener("hashchange", function() { setTimeout(translateWholePage, 50); });

    // Multi-turn progressive scans for React initial async rendering
    var scanDelays = [100, 250, 500, 1000, 1800, 3000, 5000];
    for (var k = 0; k < scanDelays.length; k++) {
        setTimeout(translateWholePage, scanDelays[k]);
    }

    // 5. High-Performance MutationObserver (observes childList on documentElement)
    var isTranslating = false;
    var observer = new MutationObserver(function (mutations) {
        if (isTranslating) return;
        isTranslating = true;
        try {
            for (var i = 0; i < mutations.length; i++) {
                var m = mutations[i];
                if (m.type === "childList") {
                    for (var j = 0; j < m.addedNodes.length; j++) {
                        translateSubtree(m.addedNodes[j]);
                    }
                }
            }
        } finally {
            isTranslating = false;
        }
    });

    function startObserving() {
        var root = document.documentElement || document.body;
        if (root) {
            observer.observe(root, {
                childList: true,
                subtree: true
            });
        } else {
            setTimeout(startObserving, 30);
        }
    }
    startObserving();

    console.log("[Antigravity i18n] Localization runner successfully initialized and active.");
})();
