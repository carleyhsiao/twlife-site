#!/usr/bin/env python3
"""
update_nav.py - 每天台灣時間 08:00 由 GitHub Actions 自動執行
從 MoneyDJ 抓取 DB001-DB005 最新淨值及配息資料，更新 baofu.html
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
    # 找所有日期，取第一個日期後面緊接的數字作為淨值
    dates = re.findall(r'(\d{4}/\d{2}/\d{2})', html)
    for date in dates[:3]:
        idx = html.find(date)
        chunk = html[idx:idx+300]
        nums = re.findall(r'[\s>](\d+\.\d{2,4})[\s<]', chunk)
        for n in nums:
            v = float(n)
            if v > 0.5:
                return {"date": date, "nav": v}
    return None

def parse_div(html):
    """
    MoneyDJ 配息頁真實格式（已驗證）：
    <td>2026/03/13</td><td>2026/03/16</td><td>2026/03/18</td><td>配息</td><td>0.055</td><td>7.97</td>
    
    策略：找第一個日期，確認其後還有另一個日期（除息日），
    然後找後面第一個介於 0.01~10 的小數作為配息金額
    """
    # 找所有日期位置
    date_matches = list(re.finditer(r'(\d{4}/\d{2}/\d{2})', html))
    
    for i, dm in enumerate(date_matches[:-1]):
        # 確認這個日期後面不遠處還有另一個日期（確認是配息表格行）
        gap = date_matches[i+1].start() - dm.end()
        if gap < 100:  # 兩個日期很接近 = 同一行
            div_date = dm.group(1)
            # 從第一個日期之後，找第一個合理的配息金額
            after = html[dm.start():dm.start()+500]
            # 找所有小數
            nums = re.findall(r'[\s>](\d+\.\d+)[\s<]', after)
            print(f"  [debug] date={div_date}, nums found: {nums[:8]}")
            for n in nums:
                v = float(n)
                if 0.01 <= v <= 10:
                    return {"divDate": div_date, "div": v}
    return None

def update_el(html, el_id, new_text):
    pattern = rf'(id="{re.escape(el_id)}"[^>]*>)[^<]*'
    result, n = re.subn(pattern, rf'\g<1>{new_text}', html)
    if n == 0:
        print(f"  WARNING: id={el_id} not found")
    else:
        print(f"  OK {el_id} -> {new_text}")
    return result

def main():
    tw_now = datetime.now(timezone(timedelta(hours=8)))
    print(f"Time (TW): {tw_now.strftime('%Y/%m/%d %H:%M')}")
    print("=" * 50)

    with open("baofu.html", encoding="utf-8") as f:
        html = f.read()

    all_ok = True
    for code, cfg in FUNDS.items():
        print(f"\n--- {code} {cfg['name']} ---")
        try:
            nav_html = fetch_md(
                f"https://www.moneydj.com/funddj/ya/yp010001.djhtm?a={cfg['mdNav']}"
            )
            div_html = fetch_md(
                f"https://www.moneydj.com/funddj/yp/wb05.djhtm?a={cfg['mdDiv']}"
            )

            # Debug：印出配息頁前500字元看結構
            print(f"  [div_html sample] {repr(div_html[1000:1300])}")

            nav_data = parse_nav(nav_html)
            div_data = parse_div(div_html)

            if not nav_data:
                raise ValueError("NAV parse failed")

            nav      = nav_data["nav"]
            nav_date = nav_data["date"]
            div      = div_data["div"]     if div_data else cfg["div"]
            div_date = div_data["divDate"] if div_data else None
            rate     = round((div * 12) / nav * 100, 2)

            print(f"  NAV: {nav} ({nav_date})")
            print(f"  DIV: date={div_date}, amount={div}, rate={rate}%")

            html = update_el(html, f"nav-{code}",  f"USD {nav:.4f}")
            html = update_el(html, f"date-{code}", nav_date)
            html = update_el(html, f"rate-{code}", f"{rate}%")
            if div_date:
                html = update_el(html, f"divdate-{code}", div_date)
            else:
                print(f"  SKIP divdate-{code} (no date found, keeping existing)")
            cfg["div"] = div

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            all_ok = False

    ts = tw_now.strftime("%Y/%m/%d %H:%M updated")
    html = re.sub(r'id="lastUpdate"[^>]*>[^<]*', f'id="lastUpdate">{ts}', html)
    print(f"\nTimestamp: {ts}")

    with open("baofu.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("=" * 50)
    print("ALL OK" if all_ok else "SOME FAILED")

if __name__ == "__main__":
    main()
