# 台壽商品快查站

## 網站結構
```
📁 github-site/
├── index.html           首頁（商品入口）
├── baofu.html           保富人生（淨值每日自動更新）
├── xinxin.html          信鑫滿滿
├── vip.html             星享 VIP
├── vip-line.html        星享 VIP 加好友
├── renewal-tool.html    續期保費查詢工具
├── update_nav.py        淨值更新腳本（GitHub Actions 執行）
└── .github/
    └── workflows/
        └── update-nav.yml   每日自動更新排程
```

## 淨值自動更新原理
每天台灣時間 08:00，GitHub Actions 自動執行 `update_nav.py`：
1. 從 MoneyDJ 抓取 DB001–DB005 最新淨值及配息基準日
2. 更新 `baofu.html` 內對應欄位
3. 自動 commit 並推回 GitHub
4. GitHub Pages 立即反映最新資料

## 上傳到 GitHub 步驟

### 第一次設定
1. 到 github.com 建立新 repository（名稱例如 `twlife-site`），選 **Public**
2. 把這個資料夾的所有檔案上傳（拖曳到 GitHub 網頁）
3. 進入 Settings → Pages → Source 選 `main` branch → Save
4. 網址：`https://你的名字.github.io/twlife-site/`

### 之後新增商品
1. 把新的 HTML 放進 repository
2. 在 index.html 複製一張卡片，改名稱、說明與連結

## 手動觸發更新
到 GitHub → Actions → 「每日自動更新基金淨值」→ Run workflow
