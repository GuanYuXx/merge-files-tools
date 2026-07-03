# 檔案合併工具 (Merge Files Tool)

> 把任意檔案（影像 / PDF / Office）統一轉換、調整、合併輸出成 **PNG / JPG / PDF** 的 Web 工具。
> 部署在實驗室 NAS 或個人電腦，瀏覽器開網址即可多人同時使用，使用者不需要安裝任何東西。

**目錄**
[功能](#功能) · [一鍵啟動](#一鍵啟動windows-桌面捷徑) · [快速部署](#快速部署) · [服務管理](#服務管理) · [設定說明](#設定說明-env) · [使用流程](#使用流程) · [常見問題](#常見問題) · [專案架構](#專案架構)

---

## 功能

| 功能 | 說明 |
|---|---|
| 多格式輸入 | PNG / JPG / BMP / WebP / TIFF / GIF / PDF / DOCX / XLSX / PPTX / DOC / XLS / PPT |
| 統一輸出 | PDF（單一合併檔）/ PNG / JPG（ZIP 壓縮包） |
| 拖曳排序 | 卡片式列表，滑鼠拖曳直接調整 PDF 合併順序 |
| 單頁旋轉 | 每個檔案可獨立旋轉 90° / 180° / 270° |
| 尺寸調整 | 最大值 / 最小值 / 手動輸入像素 / 不調整，縮放保持長寬比 |
| 縮放演算法 | Lanczos（預設）/ Bicubic / Bilinear / Nearest |
| 多人隔離 | UUID Session，各使用者資料完全隔離 |
| 共用密碼驗證 | 進入時輸入密碼，密碼存在環境變數，不寫死於程式碼 |

---

## 一鍵啟動（Windows 桌面捷徑）

設定好之後，日常使用**不需要打任何指令**。桌面捷徑點兩下就會：

1. 檢查服務是否活著 → 活著就直接開視窗（約 1 秒）
2. 容器停了 → 自動 `docker start` 救回（約 10 秒）
3. 容器不存在 → 自動跑完整 `docker compose up -d --build`（第一次會 build，需幾分鐘）
4. 連 Docker Desktop 都沒開 → 自動把它拉起來再繼續
5. 最後用 Edge `--app` 模式開出**獨立視窗**（無網址列、有自己的工作列圖示，看起來就是桌面 App）

### 從 clone 到一鍵啟動的完整流程（新電腦）

```powershell
# ① 裝好 Docker Desktop，然後 clone（Windows 路徑或 WSL 路徑都可以）
git clone https://github.com/GuanYuXx/merge-files-tools.git
cd merge-files-tools

# ② 建立設定檔（密碼、port）
copy .env.example .env.local
notepad .env.local        # 改 APP_PASSWORD；port 被佔用時改 PORT

# ③ 存下面的啟動腳本、改前三個變數 → 建捷徑 → 之後都點捷徑
```

> 不需要手動 `docker compose up` — 腳本第一次執行會自己 build + 啟動。

### 建立方式

**① 存一支啟動腳本**（例如 `MergeFiles-Launcher.ps1`，放哪都可以）：

```powershell
# Adjust these four lines for your machine
$port = 8010                                   # must match PORT in your env file
$url  = "http://localhost:$port"
$projectDir = "C:\path\to\merge-files-tools"   # or \\wsl.localhost\Ubuntu\home\<user>\merge_files
$envFile    = "$projectDir\.env.local"

function Test-AppUp {
    try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 | Out-Null; return $true }
    catch { return $false }
}

if (-not (Test-AppUp)) {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
        for ($i = 0; $i -lt 60; $i++) {
            docker info 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { break }
            Start-Sleep -Seconds 2
        }
    }
    $name = docker ps -a --filter "name=merge" --format "{{.Names}}" | Select-Object -First 1
    if ($name) { docker start $name | Out-Null }
    else { docker compose --project-directory $projectDir --env-file $envFile up -d --build }
    for ($i = 0; $i -lt 90; $i++) { if (Test-AppUp) { break }; Start-Sleep -Seconds 1 }
}

$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) { $edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe" }
if (Test-Path $edge) { Start-Process $edge "--app=$url" } else { Start-Process $url }
```

> ⚠️ 腳本註解請用英文 — Windows PowerShell 5.1 讀無 BOM 的 UTF-8 中文會解析錯誤。

**② 建桌面捷徑**，目標填：

```
powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "<腳本完整路徑>"
```

捷徑內容 → 執行方式選「最小化」，就不會閃出黑視窗。

### 平常幾乎是秒開

`docker-compose.yml` 設了 `restart: unless-stopped`，加上 Docker Desktop 開機自啟，**容器平常會一直活著** — 大多數時候點捷徑就是直接開視窗。

---

## 快速部署

### 情境 A — 個人電腦 / 本機測試

**需求：** Docker + Docker Compose

```bash
git clone https://github.com/GuanYuXx/merge-files-tools.git
cd merge-files-tools

cp .env.example .env
# 編輯 .env，至少把 APP_PASSWORD 改掉；port 被佔用時順便改 PORT
nano .env

docker compose up -d
```

開啟瀏覽器：`http://localhost:8000`（或你設定的 PORT）

> **Windows + WSL2 使用者：** 專案 clone 在 WSL 內部路徑（如 `~/merge_files`）。
> 若 Ubuntu 內 `docker` 指令不可用（WSL integration 未啟用），可以直接從 Windows 端跑：
> ```powershell
> docker compose --project-directory "\\wsl.localhost\Ubuntu\home\<帳號>\merge_files" `
>                --env-file "\\wsl.localhost\Ubuntu\home\<帳號>\merge_files\.env.local" up -d --build
> ```

### 情境 B — NAS 長期運作（Synology DS423+ 推薦）

```bash
docker compose --env-file .env.nas up -d
```

**`.env.nas` 關鍵設定：**

```dotenv
APP_PASSWORD=你的密碼
PORT=8080                          # 避開 Synology 5000/5001
MAX_FILE_SIZE_MB=100               # 2GB RAM 建議 100；升 6GB 可到 200
MAX_PARALLEL_OFFICE=2              # 2GB RAM 用 2；升 6GB 可到 5
SESSIONS_VOLUME=/volume1/docker/merge_files/sessions
```

開啟瀏覽器：`http://<NAS-IP>:8080`

### 情境 C — 本機 conda（開發 / 不用 Docker）

**需求：** conda、LibreOffice（[下載](https://www.libreoffice.org/download/download/)）

```bash
conda env create -f environment.yml
conda activate merge_files
cp .env.example .env  # 設定 APP_PASSWORD
python -m backend.main
```

### 情境 D — WSL2 直跑（Windows 11 + WSL）

```bash
sudo apt install libreoffice
pip install -r requirements.txt
cp .env.example .env
APP_PASSWORD=你的密碼 python -m backend.main
```

> **Note:** 部署在 WSL 時，volume 請掛 WSL 內部路徑（如 `/home/user/merge_files/sessions`），
> 不要掛 `D:\` 之類的 Windows 路徑，避免 I/O 效能損耗。

---

## 服務管理

| 動作 | 指令 |
|---|---|
| 查看狀態 | `docker ps --filter name=merge_files` |
| 停止服務（關閉 port） | `docker stop merge_files-app-1` |
| 重新啟動 | `docker start merge_files-app-1` |
| 看即時 log | `docker logs -f merge_files-app-1` |
| 更新到最新版 | `git pull && docker compose --env-file .env.local up -d --build` |
| 完全移除 | `docker compose down`（加 `-v` 連 session 資料一起刪） |

> 容器名稱格式是 `<專案資料夾名>-app-1`，clone 下來若資料夾叫 `merge-files-tools`，
> 容器就是 `merge-files-tools-app-1`。不確定時用 `docker ps` 查。

---

## 設定說明 (`.env`)

```dotenv
APP_PASSWORD=changeme          # 必填，部署前請改！

PORT=8000                      # 對外 port（被其他服務佔用時請改）
HOST=0.0.0.0

MAX_FILE_SIZE_MB=200           # 單檔大小上限
MAX_TOTAL_SIZE_MB=1024         # 單次上傳總量上限

SESSION_TTL_MINUTES=60         # Session 閒置過期時間
MAX_PARALLEL_OFFICE=2          # LibreOffice 同時轉檔數

SESSIONS_VOLUME=./sessions     # Session 資料 volume 路徑

ALLOWED_ORIGINS=               # 留空 = 僅同源；跨域時填入 http://example.com
```

**雙環境快速切換：** 同一份 code，不同機器只換 env 檔。

```bash
docker compose --env-file .env.local up -d   # 本機（高規格）
docker compose --env-file .env.nas   up -d   # NAS（低資源）
```

---

## 使用流程

```
1. 瀏覽器開網址 → 輸入密碼
2. 拖曳或選擇檔案上傳（支援多選）
3. 拖曳卡片調整合併順序
4. 需要時點旋轉按鈕（↻90° / ↻180° / ↺90°）
5. 設定輸出格式、尺寸模式、縮放演算法
6. 按「轉換」→ 等待處理完成
7. 點「下載」取得 PDF 或 ZIP
```

---

## 常見問題

**Q：關掉視窗，服務會跟著關掉嗎？port 還開著嗎？**
不會關。視窗只是「畫面」，真正的服務是背景的 Docker 容器 — 關掉視窗後容器繼續跑、port 繼續開著，其他人連進來也不受影響。這是刻意設計：服務常駐，下次點捷徑秒開。真的要停掉服務請用 `docker stop merge_files-app-1`。

**Q：忘記密碼了？**
密碼就在你部署時用的 env 檔裡：`grep APP_PASSWORD .env.local`（或 `.env` / `.env.nas`）。

**Q：port 被別的程式佔用（`bind: address already in use`）？**
改 env 檔的 `PORT=` 換一個沒被佔用的（例如 8010），再 `docker compose up -d` 重建。

**Q：電腦重開機後還要重新啟動嗎?**
不用。`restart: unless-stopped` + Docker Desktop 開機自啟 = 容器開機自動回來。只有你手動 `docker stop` 過，它才會保持停止。

**Q：Office 檔轉出來中文變方塊？**
Docker 版已內建 CJK 字型不會發生；conda / WSL 直跑版請安裝 `fonts-noto-cjk`。

---

## 專案架構

```
merge-files-tools/
├── backend/
│   ├── main.py       # FastAPI 進入點 + lifespan
│   ├── api.py        # REST 端點
│   ├── session.py    # UUID session 隔離 + 背景清理
│   ├── loader.py     # 檔案 → PIL Image 列表
│   ├── office.py     # LibreOffice headless 封裝（Semaphore 限流）
│   ├── resize.py     # 縮放邏輯（Lanczos 等）
│   ├── exporter.py   # 輸出 PNG/JPG ZIP / PDF
│   └── config.py     # 所有設定從環境變數讀取
├── frontend/
│   ├── index.html
│   ├── app.js        # 上傳 / 排序 / 旋轉 / 轉換
│   └── style.css
├── Dockerfile        # Python + LibreOffice + CJK 字型
├── docker-compose.yml
├── .env.example      # 設定範本（無真實值）
├── .env.local        # 本機高規格設定（gitignored）
├── .env.nas          # NAS 低資源設定（gitignored）
├── environment.yml   # conda 環境
└── requirements.txt
```

---

## 技術棧

| 層級 | 技術 |
|---|---|
| 後端框架 | FastAPI + Uvicorn |
| 影像處理 | Pillow |
| PDF 讀取 | PyMuPDF (fitz) |
| PDF 輸出 | img2pdf（不重壓縮，品質最佳） |
| Office 轉檔 | LibreOffice headless |
| 前端拖曳 | SortableJS |
| 容器化 | Docker + docker-compose |

---

## 安全說明

- **密碼存在 `.env`**，不寫死於程式碼，`.env` 已加入 `.gitignore` 不會被 push
- **`APP_PASSWORD` 預設值為 `changeme`，部署前請務必修改**
- Session UUID 隔離，使用者之間無法互相存取檔案
- Session 閒置 60 分鐘後自動清除，不永久儲存使用者資料

---

## License

MIT
