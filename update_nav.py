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

def extract_td_values(html):
    """抓出所有 <td>...</td> 的內容，移除內部 HTML tag"""
    tds = re.findall(r'<td[^>]*>(.*?)</td>', html, re.DOTALL | re.IGNORECASE)
    return [re.sub(r'<[^>]+>', '', td).strip() for td in tds]

def parse_nav(html):
    """
    MoneyDJ 淨值頁：日期 | 淨值 | 漲跌 | 年最高 | 年最低
    找第一個日期格式的 td，下一個 td 就是淨值
    """
    tds = extract_td_values(html)
    date_re = re.compile(r'^\d{4}/\d{2}/\d{2}$')
    for i, td in enumerate(tds):
        if date_re.match(td) and i + 1 < len(tds):
            try:
                nav = float(tds[i + 1])
                if nav > 0.5:
                    return {"date": td, "nav": nav}
            except ValueError:
                continue
    return None

def parse_div(html):
    """
    MoneyDJ 配息頁：配息基準日 | 除息日 | 發放日 | 類型 | 每單位配息 | 年化率 | 備註 | 附件
    找連續兩個日期格式的 td（基準日 + 除息日），
    再往後第 3 個 td 就是配息金額（跳過發放日和類型）
    """
    tds = extract_td_values(html)
    date_re = re.compile(r'^\d{4}/\d{2}/\d{2}$')
    for i, td in enumerate(tds):
        if date_re.match(td) and i + 1 < len(tds) and date_re.match(tds[i + 1]):
            # tds[i]   = 配息基準日
            # tds[i+1] = 除息日
            # tds[i+2] = 發放日（可能是日期或--）
            # tds[i+3] = 類型（配息）
            # tds[i+4] = 每單位配息金額  ← 目標
            if i + 4 < len(tds):
                try:
                    div = float(tds[i + 4])
                    if 0.001 < div < 100:
                        print(f"  [div found] date={td}, tds[i:i+6]={tds[i:i+6]}")
                        return {"divDate": td, "div": div}
                except ValueError:
                    pass
            # 備用：往後找第一個合理的小數
            for j in range(i + 2, min(i + 8, len(tds))):
                try:
                    v = float(tds[j])
                    if 0.001 < v < 100:
                        print(f"  [div fallback] date={td}, value={v}, pos={j-i}")
                        return {"divDate": td, "div": v}
                except ValueError:
                    continue
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

            # debug：印出前20個 td 看結構
            tds = extract_td_values(div_html)
            print(f"  [div tds sample] {tds[:10]}")

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
