#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地 Chromium Cache 离线提取 Antigravity 前端 bundle 中尚未汉化的设置与快捷键词条。
用法: python scripts/extract_ui_strings.py
"""

import json
import os
import re
import zlib


def find_cache_dirs():
    dirs = []
    if os.name == "nt":
        base = os.path.join(os.environ.get("APPDATA", ""), "Antigravity")
    elif os.uname().sysname == "Darwin":
        base = os.path.expanduser("~/Library/Application Support/Antigravity")
    else:
        base = os.path.expanduser("~/.config/Antigravity")

    main_cache = os.path.join(base, "Cache", "Cache_Data")
    if os.path.exists(main_cache):
        dirs.append(main_cache)
    return dirs


def extract_bundle_bytes(cache_dirs):
    for cd in cache_dirs:
        for fname in os.listdir(cd):
            if not fname.startswith("f_"):
                continue
            fpath = os.path.join(cd, fname)
            try:
                if not os.path.isfile(fpath) or os.path.getsize(fpath) < 100_000:
                    continue
                raw = open(fpath, "rb").read()
            except OSError:
                continue

            if b"Interface Layout" in raw or b"Move Conversation Up" in raw:
                return raw.decode("utf-8", errors="ignore")
            gz = raw.find(b"\x1f\x8b\x08")
            if gz != -1:
                try:
                    dec = zlib.decompress(raw[gz:], 16 + zlib.MAX_WBITS)
                    if b"Interface Layout" in dec or b"Move Conversation Up" in dec:
                        return dec.decode("utf-8", errors="ignore")
                except Exception:
                    pass
    return None


def main():
    cache_dirs = find_cache_dirs()
    bundle = extract_bundle_bytes(cache_dirs)
    if not bundle:
        print("[!] 未在 Chromium Cache 中找到前端 bundle，请先启动一次 Antigravity 并打开设置页面。")
        return

    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "i18n_data.json")
    exact = json.load(open(data_path, "r", encoding="utf-8")).get("exact", {})

    candidates = set()
    for m in re.finditer(r'(?:label|description|title|placeholder)\s*:\s*"([A-Za-z][^"\\]{1,220})"', bundle):
        val = m.group(1)
        if val in exact:
            continue
        if any(c in val for c in ("=>", "===", "var(--", "{", "}")):
            continue
        if " " in val or re.match(r"^[A-Z][a-zA-Z]+$", val):
            candidates.add(val)

    print(f"[OK] 共扫描到 {len(candidates)} 条候选未汉化字段（部分为代码内部字段，请按需筛选）：")
    for s in sorted(candidates)[:120]:
        print(" ", s)


if __name__ == "__main__":
    main()
