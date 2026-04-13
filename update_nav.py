name: 每日自動更新基金淨值

on:
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  update-nav:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: 取得程式碼
        uses: actions/checkout@v4

      - name: 設定 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: 執行淨值更新腳本
        run: python update_nav.py

      - name: 顯示更新結果（debug）
        run: |
          echo "=== 淨值欄位 ==="
          grep -o 'id="nav-DB[0-9]*">[^<]*' baofu.html
          echo "=== 配息基準日欄位 ==="
          grep -o 'id="divdate-DB[0-9]*">[^<]*' baofu.html
          echo "=== 最後更新時間 ==="
          grep -o 'id="lastUpdate">[^<]*' baofu.html
          echo "=== git diff ==="
          git diff baofu.html | head -50

      - name: 推回 GitHub
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add baofu.html
          git diff --cached --quiet && echo "無變更，跳過 commit" || git commit -m "⚡ 自動更新基金淨值 $(date +'%Y/%m/%d %H:%M')"
          git push
