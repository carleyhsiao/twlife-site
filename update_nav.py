#!/usr/bin/env python3
"""
update_nav.py
每次執行時從 MoneyDJ 抓取 DB001–DB005 最新淨值及配息資料，
並更新 baofu.html 內對應的 HTML 元素內容。

GitHub Actions 每天台灣時間 08:00 自動執行。
"""

import re
import urllib.request
from datetime import datetime, timezone, timedelta

# ── 基金設定 ──────────────────────────────────────────────
FUNDS = {
    "DB001": {"mdNav": "TLZ64", "mdDiv": "TLZ64", "div": 0.055, "name": "安聯AM穩定月收"},
    "DB002": {"mdNav": "ALBG6", "mdDiv": "ALBG6", "div": 0.063, "name": "聯博AD月配"},
    "DB003": {"mdNav": "PYZW5", "mdDiv": "PYZW5", "div": 0.617, "name": "施羅德環球多元"},
    "DB004": {"mdNav": "JFZK2", "mdDiv": "JFZK2", "div": 0.052, "name": "摩根JPM多重收益"},
    "DB005": {"mdNav": "FTZU8", "mdDiv": "FTZU8", "div": 0.049, "name": "富達全球多重資產"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9",
}

# ── 抓 MoneyDJ 頁面（Big5 解碼）─────────────────────────
def fetch_md(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode("big5", errors="replace")

# ── 解析淨值頁：取第一筆日期 + 淨值 ─────────────────────
def parse_nav(html: str):
    m = re.search(r"(\d{4}/\d{2}/\d{2})</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>", html)
    if not m:
        return None
    return {"date": m.group(1), "nav": float(m.group(2))}

# ── 解析配息頁：取第一筆基準日 + 配息金額 ───────────────
def parse_div(html: str):
    m = re.search(
        r"(\d{4}/\d{2}/\d{2})</td>[\s\S]{0,300}?<td[^>]*>\s*([\d.]+)\s*</td>",
        html,
    )
    if not m:
        return None
    return {"divDate": m.group(1), "div": float(m.group(2))}

# ── 更新 HTML 元素內容 ───────────────────────────────────
def update_el(html: str, el_id: str, new_text: str) -> str:
    pattern = rf'(id="{el_id}"[^>]*>)[^<]*'
    replacement = rf'\g<1>{new_text}'
    result, n = re.subn(pattern, replacement, html)
    if n == 0:
        print(f"  ⚠️  找不到 id={el_id}")
    return result

# ── 主程式 ───────────────────────────────────────────────
def main():
    tw_now = datetime.now(timezone(timedelta(hours=8)))
    print(f"🕗 執行時間（台灣）：{tw_now.strftime('%Y/%m/%d %H:%M')}")

    with open("baofu.html", encoding="utf-8") as f:
        html = f.read()

    all_ok = True
    for code, cfg in FUNDS.items():
        print(f"\n📊 處理 {code} {cfg['name']}")
        try:
            nav_html = fetch_md(
                f"https://www.moneydj.com/funddj/ya/yp010001.djhtm?a={cfg['mdNav']}"
            )
            div_html = fetch_md(
                f"https://www.moneydj.com/funddj/yp/wb05.djhtm?a={cfg['mdDiv']}"
            )

            nav_data = parse_nav(nav_html)
            div_data = parse_div(div_html)

            if not nav_data:
                raise ValueError("淨值解析失敗")

            nav   = nav_data["nav"]
            date  = nav_data["date"]
            div   = div_data["div"]    if div_data else cfg["div"]
            dddate= div_data["divDate"] if div_data else "—"
            rate  = round((div * 12) / nav * 100, 2)

            print(f"  淨值日：{date}  淨值：{nav}  配息：{div}  年化率：{rate}%  基準日：{dddate}")

            html = update_el(html, f"nav-{code}",     f"USD {nav:.4f}")
            html = update_el(html, f"date-{code}",    date)
            html = update_el(html, f"rate-{code}",    f"{rate}%")
            html = update_el(html, f"divdate-{code}", dddate)

        except Exception as e:
            print(f"  ❌ 失敗：{e}")
            all_ok = False

    # 更新最後更新時間
    ts = tw_now.strftime("%Y/%m/%d %H:%M 更新")
    html = re.sub(
        r'id="lastUpdate"[^>]*>[^<]*',
        f'id="lastUpdate">{ts}',
        html,
    )

    with open("baofu.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{'✅ 全部完成' if all_ok else '⚠️ 部分失敗'}，已寫入 baofu.html")

if __name__ == "__main__":
    main()
