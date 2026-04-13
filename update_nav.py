#!/usr/bin/env python3
"""
update_nav.py
每天台灣時間 08:00 由 GitHub Actions 自動執行。
直接從 MoneyDJ 抓取 DB001–DB005 最新淨值及配息資料，更新 baofu.html。
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
        raw = r.read()
        return raw.decode("big5", errors="replace")

def parse_nav(html):
    """
    MoneyDJ 淨值頁表格：日期 | 最新淨值 | 漲跌 | 年最高 | 年最低
    抓第一筆：日期 + 淨值
    """
    m = re.search(
        r"(\d{4}/\d{2}/\d{2})</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>",
        html
    )
    if m:
        nav = float(m.group(2))
        if nav > 0:
            return {"date": m.group(1), "nav": nav}
    return None

def parse_div(html):
    """
    MoneyDJ 配息頁表格：
    配息基準日 | 除息日 | 發放日 | 類型 | 每單位配息 | 年化配息率% | 備註 | 附件
    
    直接用 markdown 轉換後的格式解析（已由 web_fetch 確認）：
    | 2026/03/13 | 2026/03/16 | 2026/03/18 | 配息 | 0.055 | 7.97 | ... |
    """
    # 找第一列配息資料：基準日 + 除息日（兩個連續日期）+ 往後找配息金額
    # MoneyDJ 格式確認：三個日期欄 + 類型 + 配息金額
    m = re.search(
        r"(\d{4}/\d{2}/\d{2})</td>\s*"   # 配息基準日
        r"<td[^>]*>\d{4}/\d{2}/\d{2}</td>\s*"  # 除息日
        r"<td[^>]*>.*?</td>\s*"           # 發放日（可能是日期或--）
        r"<td[^>]*>[^<]*</td>\s*"         # 類型（配息）
        r"<td[^>]*>\s*([\d.]+)\s*</td>",  # 每單位配息金額
        html,
        re.DOTALL
    )
    if m:
        div = float(m.group(2))
        if 0.001 < div < 100:
            return {"divDate": m.group(1), "div": div}

    # 備用1：發放日可能是 -- 格式（摩根等）
    m = re.search(
        r"(\d{4}/\d{2}/\d{2})</td>\s*"
        r"<td[^>]*>\d{4}/\d{2}/\d{2}</td>\s*"
        r"<td[^>]*>--</td>\s*"
        r"<td[^>]*>[^<]*</td>\s*"
        r"<td[^>]*>\s*([\d.]+)\s*</td>",
        html,
        re.DOTALL
    )
    if m:
        div = float(m.group(2))
        if 0.001 < div < 100:
            return {"divDate": m.group(1), "div": div}

    # 備用2：更寬鬆 - 找第一個日期 + 往後1500字元內找合理配息金額
    dates = re.findall(r"(\d{4}/\d{2}/\d{2})</td>", html)
    if dates:
        div_date = dates[0]
        after = html[html.find(div_date + "</td>"):]
        nums = re.findall(r"<td[^>]*>\s*([\d]+\.[\d]+)\s*</td>", after[:2000])
        for s in nums:
            v = float(s)
            if 0.01 <= v <= 10:   # 配息金額通常在此範圍
                return {"divDate": div_date, "div": v}

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
            nav_html = fetch_md(
                f"https://www.moneydj.com/funddj/ya/yp010001.djhtm?a={cfg['mdNav']}"
            )
            div_html = fetch_md(
                f"https://www.moneydj.com/funddj/yp/wb05.djhtm?a={cfg['mdDiv']}"
            )

            nav_data = parse_nav(nav_html)
            div_data = parse_div(div_html)

            if not nav_data:
                raise ValueError("淨值解析失敗，請檢查 MoneyDJ 頁面")

            nav      = nav_data["nav"]
            nav_date = nav_data["date"]
            div      = div_data["div"]     if div_data else cfg["div"]
            div_date = div_data["divDate"] if div_data else "—"
            rate     = round((div * 12) / nav * 100, 2)

            print(f"  淨值：{nav}（{nav_date}）")
            print(f"  配息基準日：{div_date}  配息：{div}  年化率：{rate}%")

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
    print(f"\n⏰ 時間戳記：{ts}")

    with open("baofu.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("=" * 50)
    print(f"{'✅ 全部完成' if all_ok else '⚠️ 部分失敗'}")

if __name__ == "__main__":
    main()
