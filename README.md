# 檔案合併工具 (Merge Files Tool)

> 把任意檔案（影像 / PDF / Office）統一轉換、調整、合併輸出成 **PNG / JPG / PDF** 的 Web 工具。  
> 部署在實驗室 NAS 或個人電腦，瀏覽器開網址即可多人同時使用，不需要任何安裝。

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

## 快速部署

### 情境 A — 個人電腦 / 本機測試

**需求：** Docker + Docker Compose

```bash
git clone https://github.com/GuanYuXx/merge-files-tools.git
cd merge-files-tools

cp .env.example .env
# 編輯 .env，至少把 APP_PASSWORD 改掉
nano .env

docker compose up -d
```

開啟瀏覽器：`http://localhost:8000`

---

### 情境 B — NAS 長期運作（Synology DS423+ 推薦）

```bash
# 在 NAS 上（或先在本機 build 再推）
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

---

### 情境 C — 本機 conda（開發 / 不用 Docker）

**需求：** conda、LibreOffice（[下載](https://www.libreoffice.org/download/download/)）

```bash
conda env create -f environment.yml
conda activate merge_files

cp .env.example .env  # 設定 APP_PASSWORD

python -m backend.main
```

---

### 情境 D — WSL2 直跑（Windows 11 + WSL）

```bash
sudo apt install libreoffice
pip install -r requirements.txt

cp .env.example .env
APP_PASSWORD=你的密碼 python -m backend.main
```

> **Note:** 若部署在 WSL，volume 請掛在 WSL 內部路徑（如 `/home/user/merge_files/sessions`），  
> 不要掛 `D:\` 之類的 Windows 路徑，避免 I/O 效能損耗。

---

## 設定說明 (`.env`)

```dotenv
APP_PASSWORD=changeme          # 必填，部署前請改！

PORT=8000                      # 對外 port
HOST=0.0.0.0

MAX_FILE_SIZE_MB=200           # 單檔大小上限
MAX_TOTAL_SIZE_MB=1024         # 單次上傳總量上限

SESSION_TTL_MINUTES=60         # Session 閒置過期時間
MAX_PARALLEL_OFFICE=2          # LibreOffice 同時轉檔數

SESSIONS_VOLUME=./sessions     # Session 資料 volume 路徑

ALLOWED_ORIGINS=               # 留空 = 僅同源；跨域時填入 http://example.com
```

**雙環境快速切換：**

```bash
# 本機（高規格）
docker compose --env-file .env.local up -d

# NAS（低資源）
docker compose --env-file .env.nas up -d
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
