# Spritesheet Processor

自動將東方 Project `.anm` 檔案的 Spritesheet 裁切成獨立的 Sprite PNG。

---

## 環境需求

- Python 3.10+
- [thtk](https://github.com/thpatch/thtk/releases)（包含 `thanm.exe`）
- 相依套件：

```bash
pip install Pillow python-dotenv
```

---

## 設定

在 `.env` 填入 `thanm.exe` 的實際路徑：

```
THANM_PATH=C:\path\to\thtk-bin\thanm.exe
```

---

## 使用方式

### 處理整個資料夾

```bash
python process_anm.py <資料夾路徑>
```

掃描資料夾內所有 `.anm` 檔案並逐一處理。

### 處理單一檔案

```bash
python process_anm.py <檔案.anm>
```

---

## 輸入檔案結構

在 `.anm` 同一資料夾尋找對應的圖片：

```
th06c_TL/
  eff00.anm      ← 動畫定義（Sprite 座標）
  eff00.png      ← RGB 主圖
  eff00_a.png    ← 灰階遮罩（選用，作為 Alpha channel）
  extra.jpg      ← 無對應 .anm 的圖片
```

---

## 輸出結構

輸出會放在與輸入資料夾同級、名稱加上 `_output` 的新資料夾：

```
th06c/
  th06c_TL/               ← 輸入（原始檔案不動）
  th06c_TL_output/        ← 輸出根目錄
    eff00/
      eff00.txt           ← thanm 反編譯的原始文字
      eff00_merged.png    ← 合併遮罩後的完整 Spritesheet
      sprite_0.png
      sprite_1.png
      ...
      error.txt           ← 座標超出範圍的 Sprite 記錄（有問題時才產生）
    no_anm/
      extra.jpg           ← 沒有對應 .anm 的圖片
```

**備註：**
- 若無 `_a.png` 遮罩，`_merged.png` 不會產生，直接以主圖裁切
- `error.txt` 只在有 Sprite 座標超出圖片範圍時才會產生
- `no_anm/` 只在有無對應 `.anm` 的圖片時才會產生，`_a.png` 遮罩不會被列入
