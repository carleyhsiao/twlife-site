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
        return r.read().decode("big5", errors="replace")

def parse_nav(html):
    """
    MoneyDJ 淨值頁：直接用正規表達式找「日期</td><td>數字」的模式
    """
    m = re.search(
        r'(\d{4}/\d{2}/\d{2})</td>\s*<td[^>]*>\s*([\d.]+)\s*</td>',
        html
    )
    if m:
        nav = float(m.group(2))
        if nav > 0:
            return {"date": m.group(1), "nav": nav}
    return None

def parse_div(html):
    """
    MoneyDJ 配息頁真實結構（從 log 確認）：
    前面有大量廣告 <td>，表頭也在 <td> 裡：
    '配息基準日', '除息日', '發放日', '狀態', '每單位分配金額', '年化配息率%'
    
    策略：直接在原始 HTML 找「日期</td>...<td>日期</td>」模式，
    然後從那個位置往後找配息金額
    """
    # 找第一組「兩個相鄰日期」在 HTML 中的位置
    # 兩個日期之間只隔一個 </td><td...> 或 </td>\n<td...>
    m = re.search(
        r'(\d{4}/\d{2}/\d{2})</td>\s*<td[^>]*>\s*(\d{4}/\d{2}/\d{2})</td>',
        html
    )
    if not m:
        print("  [div] 找不到連續兩個日期")
        return None

    div_date = m.group(1)
    print(f"  [div] 找到基準日={div_date}, 除息日={m.group(2)}")

    # 從這個位置往後，找第一個合理的配息金額
    after = html[m.start():]
    # 找所有 <td>數字</td> 格式
    nums = re.findall(r'<td[^>]*>\s*([\d]+\.[\d]+)\s*</td>', after[:800])
    print(f"  [div] 往後找到的數字: {nums[:8]}")

    for n in nums:
        v = float(n)
        if 0.001 < v < 100:
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
                print(f"  SKIP divdate-{code} (keeping existing)")
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
