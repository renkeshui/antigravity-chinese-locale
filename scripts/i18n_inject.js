'use strict';

const fs = require('fs');
const path = require('path');
const electron = require('electron');

function injectAntigravityI18n(target) {
    try {
        const wc = target && target.webContents ? target.webContents : target;
        if (!wc || typeof wc.executeJavaScript !== 'function' || (typeof wc.isDestroyed === 'function' && wc.isDestroyed())) {
            return;
        }
        const runnerPath = path.join(__dirname, 'i18n_runner.js');
        const dataPath = path.join(__dirname, 'i18n_data.json');
        if (fs.existsSync(runnerPath) && fs.existsSync(dataPath)) {
            const dataStr = fs.readFileSync(dataPath, 'utf-8');
            const runnerCode = fs.readFileSync(runnerPath, 'utf-8');
            const script = `
                (function(){
                    try {
                        window.__ANTIGRAVITY_I18N_DATA__ = ${JSON.stringify(JSON.parse(dataStr))};
                        ${runnerCode}
                    } catch(e) {
                        console.error('[Antigravity i18n] Error executing i18n runner:', e);
                    }
                })();
            `;
            wc.executeJavaScript(script).catch(() => {});
        }
    } catch (e) {
        console.error('[Antigravity i18n] Injection error:', e);
    }
}

function setupI18nLifecycle(app) {
    if (!app || typeof app.on !== 'function') return;

    // 1. 全局 WebContents 监听（常规页面、新Tab、子窗口与重载）
    app.on('web-contents-created', (_event, wc) => {
        if (!wc) return;
        wc.on('dom-ready', () => injectAntigravityI18n(wc));
        wc.on('did-finish-load', () => injectAntigravityI18n(wc));
        wc.on('did-navigate-in-page', () => injectAntigravityI18n(wc));
    });

    // 2. 全局 BrowserWindow 监听（窗口创建即保）
    app.on('browser-window-created', (_event, win) => {
        if (win && win.webContents) {
            win.webContents.on('dom-ready', () => injectAntigravityI18n(win.webContents));
            win.webContents.on('did-finish-load', () => injectAntigravityI18n(win.webContents));
        }
    });

    // 3. 多实例与托盘唤醒补偿
    app.on('second-instance', () => {
        setTimeout(() => {
            if (electron.BrowserWindow && typeof electron.BrowserWindow.getAllWindows === 'function') {
                electron.BrowserWindow.getAllWindows().forEach(win => injectAntigravityI18n(win));
            }
        }, 150);
    });

    app.on('activate', () => {
        if (electron.BrowserWindow && typeof electron.BrowserWindow.getAllWindows === 'function') {
            electron.BrowserWindow.getAllWindows().forEach(win => injectAntigravityI18n(win));
        }
    });
}

module.exports = {
    injectAntigravityI18n,
    setupI18nLifecycle
};
