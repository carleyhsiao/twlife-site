#!/usr/bin/env python3
# update_nav.py
# GitHub Actions runs this daily at 08:00 Taiwan time (UTC 00:00)
# Fetches NAV and dividend data from MoneyDJ, updates baofu.html

import re
import urllib.request
from datetime import datetime, timezone, timedelta

FUNDS = {
    "DB001": {"mdNav": "TLZ64", "mdDiv": "TLZ64", "div": 0.055, "name": "Allianz AM"},
    "DB002": {"mdNav": "ALBG6", "mdDiv": "ALBG6", "div": 0.063, "name": "AB AD"},
    "DB003": {"mdNav": "PYZW5", "mdDiv": "PYZW5", "div": 0.617, "name": "Schroders"},
    "DB004": {"mdNav": "JFZK2", "mdDiv": "JFZK2", "div": 0.052, "name": "JPMorgan"},
    "DB005": {"mdNav": "FTZU8", "mdDiv": "FTZU8", "div": 0.049, "name": "Fidelity"},
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
    # NAV page format: date | nav | change | high | low
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
    # Dividend page format: record_date | ex_date | pay_date | type | amount | annual_rate
    # Method 1: record_date + ex_date (two consecutive dates) + amount
    m = re.search(
        r"(\d{4}/\d{2}/\d{2})</td>\s*"
        r"<td[^>]*>\d{4}/\d{2}/\d{2}</td>\s*"
        r"<td[^>]*>.*?</td>\s*"
        r"<td[^>]*>[^<]*</td>\s*"
        r"<td[^>]*>\s*([\d.]+)\s*</td>",
        html,
        re.DOTALL
    )
    if m:
        div = float(m.group(2))
        if 0.001 < div < 100:
            return {"divDate": m.group(1), "div": div}

    # Method 2: pay_date is '--'
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

    # Method 3: fallback - first date + first decimal in range 0.01~10
    dates = re.findall(r"(\d{4}/\d{2}/\d{2})</td>", html)
    if dates:
        div_date = dates[0]
        after = html[html.find(div_date + "</td>"):]
        nums = re.findall(r"<td[^>]*>\s*([\d]+\.[\d]+)\s*</td>", after[:2000])
        for s in nums:
            v = float(s)
            if 0.01 <= v <= 10:
                return {"divDate": div_date, "div": v}

    return None

def update_el(html, el_id, new_text):
    pattern = rf'(id="{re.escape(el_id)}"[^>]*>)[^<]*'
    result, n = re.subn(pattern, rf'\g<1>{new_text}', html)
    if n == 0:
        print(f"  WARNING: id={el_id} not found")
    else:
        print(f"  OK: {el_id} -> {new_text}")
    return result

def main():
    tw_now = datetime.now(timezone(timedelta(hours=8)))
    print(f"Time (Taiwan): {tw_now.strftime('%Y/%m/%d %H:%M')}")
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
            div_date = div_data["divDate"] if div_data else None  # None = 抓不到時保留原值
            rate     = round((div * 12) / nav * 100, 2)

            print(f"  NAV: {nav} ({nav_date})")
            print(f"  Div date: {div_date or '(保留原值)'}  Div: {div}  Rate: {rate}%")

            html = update_el(html, f"nav-{code}",     f"USD {nav:.4f}")
            html = update_el(html, f"date-{code}",    nav_date)
            html = update_el(html, f"rate-{code}",    f"{rate}%")
            if div_date:  # 只有成功抓到日期才更新，否則保留原本的值
                html = update_el(html, f"divdate-{code}", div_date)
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
