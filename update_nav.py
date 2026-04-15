#!/usr/bin/env python3
"""
update_nav.py - 每天台灣時間 08:00 由 GitHub Actions 自動執行
直接從 MoneyDJ 抓取 DB001-DB005 最新淨值及配息資料，更新 baofu.html
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

def get_td_values(html):
    """抓出 HTML 中所有 <td> 的文字內容，依序排列"""
    return re.findall(r'<td[^>]*>\s*(.*?)\s*</td>', html, re.DOTALL)

def clean(s):
    """移除 HTML 標籤和多餘空白"""
    return re.sub(r'<[^>]+>', '', s).strip()

def parse_nav(html):
    """
    MoneyDJ 淨值頁：找第一個符合「日期 + 數字」格式的 td 組合
    格式：日期 | 最新淨值 | 漲跌 | 年最高 | 年最低
    """
    tds = [clean(v) for v in get_td_values(html)]
    date_re = re.compile(r'^\d{4}/\d{2}/\d{2}$')
    for i, td in enumerate(tds):
        if date_re.match(td) and i + 1 < len(tds):
            try:
                nav = float(tds[i + 1])
                if nav > 0:
                    return {"date": td, "nav": nav}
            except ValueError:
                continue
    return None

def parse_div(html):
    """
    MoneyDJ 配息頁表格欄位（固定 8 欄）：
    [0] 配息基準日  [1] 除息日  [2] 發放日  [3] 類型
    [4] 每單位配息  [5] 年化配息率  [6] 備註  [7] 附件
    
    策略：找第一個日期，往後數到第 5 個 td，就是配息金額
    """
    tds = [clean(v) for v in get_td_values(html)]
    date_re = re.compile(r'^\d{4}/\d{2}/\d{2}$')
    
    for i, td in enumerate(tds):
        if date_re.match(td):
            # 確認第 2 欄也是日期（除息日），避免抓到淨值頁的日期
            if i + 1 < len(tds) and date_re.match(tds[i + 1]):
                # 第 5 欄（index i+4）是每單位配息
                if i + 4 < len(tds):
                    try:
                        div = float(tds[i + 4])
                        if 0.001 < div < 100:
                            return {"divDate": td, "div": div}
                    except ValueError:
                        pass
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
        print(f"\n{code} {cfg['name']}")
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
            print(f"  DIV date: {div_date or '(keep existing)'}  amount: {div}  rate: {rate}%")

            html = update_el(html, f"nav-{code}",     f"USD {nav:.4f}")
            html = update_el(html, f"date-{code}",    nav_date)
            html = update_el(html, f"rate-{code}",    f"{rate}%")
            if div_date:
                html = update_el(html, f"divdate-{code}", div_date)
            else:
                print(f"  SKIP divdate-{code} (keeping existing value)")

            cfg["div"] = div

        except Exception as e:
            print(f"  ERROR: {e}")
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
