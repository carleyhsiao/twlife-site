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
    "Referer": "https://www.moneydj.com/",
}

def fetch_md(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("big5", errors="replace")

def parse_nav(html):
    for pat in [
        r"(\d{4}/\d{2}/\d{2})</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>",
        r"(\d{4}/\d{2}/\d{2})\s*</td>\s*<td[^>]*>\s*([\d.]+)",
    ]:
        m = re.search(pat, html)
        if m:
            nav = float(m.group(2))
            if nav > 0:
                return {"date": m.group(1), "nav": nav}
    return None

def parse_div(html):
    # 配息頁格式：配息基準日 | 除息日 | 發放日 | 類型 | 每單位配息
    # 抓兩個連續日期（基準日 + 除息日），再往後找配息金額
    m = re.search(
        r"(\d{4}/\d{2}/\d{2})</td>\s*<td[^>]*>\d{4}/\d{2}/\d{2}</td>"
        r"[\s\S]{0,300}?<td[^>]*>\s*([\d.]+)\s*</td>",
        html,
    )
    if m:
        div = float(m.group(2))
        if 0.001 < div < 100:
            return {"divDate": m.group(1), "div": div}
    # 備用
    m = re.search(
        r"(\d{4}/\d{2}/\d{2})</td>[\s\S]{0,400}?<td[^>]*>\s*([\d.]+)\s*</td>",
        html,
    )
    if m:
        div = float(m.group(2))
        if 0.001 < div < 100:
            return {"divDate": m.group(1), "div": div}
    return None

def update_el(html, el_id, new_text):
    pattern = rf'(id="{re.escape(el_id)}"[^>]*>)[^<]*'
    result, n = re.subn(pattern, rf'\g<1>{new_text}', html)
    if n == 0:
        print(f"  ⚠️  找不到 id={el_id}")
    else:
        print(f"  ✓ {el_id} → {new_text}")
    return result

def main():
    tw_now = datetime.now(timezone(timedelta(hours=8)))
    print(f"🕗 執行時間（台灣）：{tw_now.strftime('%Y/%m/%d %H:%M')}")
    print("=" * 50)

    with open("baofu.html", encoding="utf-8") as f:
        html = f.read()

    all_ok = True
    for code, cfg in FUNDS.items():
        print(f"\n📊 {code} {cfg['name']}")
        try:
            nav_html = fetch_md(f"https://www.moneydj.com/funddj/ya/yp010001.djhtm?a={cfg['mdNav']}")
            div_html = fetch_md(f"https://www.moneydj.com/funddj/yp/wb05.djhtm?a={cfg['mdDiv']}")

            nav_data = parse_nav(nav_html)
            div_data = parse_div(div_html)

            if not nav_data:
                raise ValueError("淨值解析失敗")

            nav      = nav_data["nav"]
            nav_date = nav_data["date"]
            div      = div_data["div"]     if div_data else cfg["div"]
            div_date = div_data["divDate"] if div_data else "查詢中"
            rate     = round((div * 12) / nav * 100, 2)

            print(f"  淨值：{nav}（{nav_date}）  配息基準日：{div_date}  配息：{div}  年化率：{rate}%")

            html = update_el(html, f"nav-{code}",     f"USD {nav:.4f}")
            html = update_el(html, f"date-{code}",    nav_date)
            html = update_el(html, f"rate-{code}",    f"{rate}%")
            html = update_el(html, f"divdate-{code}", div_date)
            cfg["div"] = div

        except Exception as e:
            print(f"  ❌ 失敗：{e}")
            all_ok = False

    ts = tw_now.strftime("%Y/%m/%d %H:%M 更新")
    html = re.sub(r'id="lastUpdate"[^>]*>[^<]*', f'id="lastUpdate">{ts}', html)
    print(f"\n⏰ 更新時間：{ts}")

    with open("baofu.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("=" * 50)
    print(f"{'✅ 全部完成' if all_ok else '⚠️ 部分失敗'}")

if __name__ == "__main__":
    main()
