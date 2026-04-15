#!/usr/bin/env python3
"""
update_nav.py - 每天台灣時間 08:00 由 GitHub Actions 自動執行
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
    找配息基準日：
    - 找兩個相鄰日期（gap < 150）
    - 第一個日期必須是「月中」（每月配息通常在 5~31 日）
    - 且後面跟著配息金額 <td>小數</td>
    """
    tw_now = datetime.now(timezone(timedelta(hours=8)))
    today_str = tw_now.strftime("%Y/%m/%d")

    all_dates = list(re.finditer(r'\d{4}/\d{2}/\d{2}', html))
    print(f"  [div] 共 {len(all_dates)} 個日期，今天={today_str}")

    for i in range(len(all_dates) - 1):
        d1 = all_dates[i]
        d2 = all_dates[i + 1]
        gap = d2.start() - d1.end()

        if gap < 150:
            div_date = d1.group()
            ex_date  = d2.group()

            # 排除今天或近期導覽日期（配息基準日通常比今天早至少 5 天）
            from datetime import date
            try:
                div_dt = date(int(div_date[:4]), int(div_date[5:7]), int(div_date[8:]))
                today  = tw_now.date()
                if (today - div_dt).days < 5:
                    print(f"  [div] 跳過近期日期 {div_date} (太新)")
                    continue
            except:
                continue

            print(f"  [div] 找到相鄰日期: {div_date} / {ex_date} (gap={gap})")

            # 在這個位置往後找配息金額 <td>小數</td>
            after = html[d1.start():d1.start() + 600]
            nums = re.findall(r'<td[^>]*>\s*([\d]+\.[\d]+)\s*</td>', after)
            print(f"  [div] 數字候選: {nums[:8]}")

            for n in nums:
                v = float(n)
                if 0.001 < v < 100:
                    return {"divDate": div_date, "div": v}

            # 備用：找任何小數（不限 <td> 格式）
            all_nums = re.findall(r'[\s>](\d+\.\d+)[\s<\r\n]', after)
            print(f"  [div] 備用數字: {all_nums[:8]}")
            for n in all_nums:
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

    with open("baofu.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("=" * 50)
    print("ALL OK" if all_ok else "SOME FAILED")

if __name__ == "__main__":
    main()
