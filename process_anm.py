"""
process_anm.py
自動處理 .anm 檔案：呼叫 thanm -l，解析 Sprite 座標，合併遮罩，裁切輸出。

用法：
    python process_anm.py <folder>        # 掃描資料夾下所有 .anm
    python process_anm.py <file.anm>      # 處理單一檔案
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from PIL import Image

THANM = os.environ.get("THANM_PATH", "thanm")


# ── 1. 執行 thanm -l 並取得輸出 ─────────────────────────────────────────────

def run_thanm_list(anm_path: Path, output_dir: Path) -> str:
    """執行 thanm -l <anm_path>，回傳標準輸出字串。"""
    result = subprocess.run(
        [THANM, "-l", str(anm_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[error] thanm 執行失敗：\n{result.stderr.strip()}", file=sys.stderr)
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    txt_path = output_dir / anm_path.with_suffix(".txt").name
    txt_path.write_text(result.stdout, encoding="utf-8")
    print(f"[info]  thanm 輸出已存至 {txt_path}")
    return result.stdout


def process_one(anm_path: Path, output_base: Path) -> bool:
    """處理單一 .anm 檔案，回傳是否成功。"""
    output_dir = output_base / anm_path.stem

    print(f"\n{'='*50}")
    print(f"[info]  處理：{anm_path.name}")
    print(f"[info]  輸出至：{output_dir}/")

    raw_text = run_thanm_list(anm_path, output_dir)
    if raw_text is None:
        return False

    name, name2, virtual_width = parse_entry_names(raw_text)
    if not name:
        print("[error] ANM 未包含 Name 欄位，略過", file=sys.stderr)
        return False
    print(f"[info]  Name: {name}" + (f"  Name2: {name2}" if name2 else "") + (f"  VirtualWidth: {virtual_width}" if virtual_width else ""))

    base_path = anm_path.parent / name
    if not base_path.exists():
        print(f"[error] 找不到主圖：{name}，略過", file=sys.stderr)
        return False

    sprites = parse_sprites(raw_text)
    if not sprites:
        print("[warn]  未找到任何 Sprite，請確認 thanm 輸出格式")
        return False
    print(f"[info]  找到 {len(sprites)} 個 Sprite")

    sheet = load_sheet(anm_path.parent, name, name2, output_dir)
    skipped = cut_and_save(sheet, sprites, output_dir, virtual_width)
    print(f"完成，共輸出 {len(sprites) - skipped} / {len(sprites)} 個 Sprite 至 {output_dir}/")
    return skipped == 0


# ── 2. 解析 ANM 資訊 ─────────────────────────────────────────────────────────

SPRITE_RE = re.compile(
    r"^\s*Sprite:\s*(\d+)\s+(\d+)\*(\d+)\+(\d+)\+(\d+)",
    re.MULTILINE,
)
NAME_RE  = re.compile(r"^Name:\s*(.+)$",   re.MULTILINE)
NAME2_RE = re.compile(r"^Name2:\s*(.+)$",  re.MULTILINE)
WIDTH_RE = re.compile(r"^Width:\s*(\d+)$", re.MULTILINE)

SpriteInfo = tuple[int, int, int, int, int]  # (index, w, h, x, y)


def parse_sprites(text: str) -> list[SpriteInfo]:
    """從 thanm 輸出文字解析所有 Sprite 資訊。"""
    sprites = []
    for m in SPRITE_RE.finditer(text):
        idx, w, h, x, y = (int(v) for v in m.groups())
        sprites.append((idx, w, h, x, y))
    return sprites


def parse_entry_names(text: str) -> tuple[str | None, str | None, int | None]:
    """從第一個 ENTRY 解析 Name、Name2、Width，回傳 (name, name2, virtual_width)。"""
    m1 = NAME_RE.search(text)
    m2 = NAME2_RE.search(text)
    mw = WIDTH_RE.search(text)
    name  = Path(m1.group(1).strip()).name if m1 else None
    name2 = Path(m2.group(1).strip()).name if m2 else None
    virtual_width = int(mw.group(1)) if mw else None
    return name, name2, virtual_width


# ── 3. 載入並合併遮罩 ─────────────────────────────────────────────────────────

def load_sheet(folder: Path, name: str, name2: str | None, output_dir: Path) -> Image.Image:
    """
    依 ANM 內的 Name/Name2 在 folder 下找圖片。
    若 Name2 存在則合併為 alpha channel，並將結果存到 output_dir。
    """
    base_path = folder / name
    base = Image.open(base_path).convert("RGBA")

    if name2:
        mask_path = folder / name2
        if mask_path.exists():
            mask = Image.open(mask_path).convert("L")
            if base.size != mask.size:
                print(
                    f"[warn]  主圖與遮罩尺寸不符 {base.size} vs {mask.size}，略過遮罩",
                    file=sys.stderr,
                )
            else:
                r, g, b, _ = base.split()
                base = Image.merge("RGBA", (r, g, b, mask))
                stem = Path(name).stem
                merged_path = output_dir / f"{stem}_merged.png"
                base.save(merged_path, "PNG")
                print(f"[info]  已合併遮罩 {name2}，存至 {merged_path}")
        else:
            print(f"[warn]  找不到遮罩：{name2}，直接使用主圖", file=sys.stderr)
    else:
        print(f"[info]  ANM 無 Name2，直接使用主圖")

    return base


# ── 4. 裁切並儲存每個 Sprite ──────────────────────────────────────────────────

def cut_and_save(
    sheet: Image.Image,
    sprites: list[SpriteInfo],
    output_dir: Path,
    virtual_width: int | None = None,
) -> int:
    """回傳超出範圍而略過的 Sprite 數量。"""
    sw, sh = sheet.size
    vw = virtual_width if virtual_width else sw
    output_dir.mkdir(parents=True, exist_ok=True)

    skipped = []
    for idx, w, h, x, y in sprites:
        filename = f"sprite_{idx}.png"
        dest = output_dir / filename

        actual_x = x % vw
        actual_y = y

        if actual_x < 0 or actual_y < 0 or actual_x + w > sw or actual_y + h > sh:
            msg = f"sprite_{idx}: 座標超出範圍 ({x},{y}) → 換算後 ({actual_x},{actual_y}) {w}x{h} / sheet {sw}x{sh}"
            print(f"[warn]  {msg}，略過")
            skipped.append(msg)
            continue

        crop = sheet.crop((actual_x, actual_y, actual_x + w, actual_y + h))
        crop.save(dest, "PNG")
        print(f"已處理 {filename}")

    if skipped:
        error_path = output_dir / "error.txt"
        error_path.write_text("\n".join(skipped), encoding="utf-8")
        print(f"[info]  已將 {len(skipped)} 筆超出範圍記錄至 error.txt")

    return len(skipped)


# ── 5. 收集無對應 .anm 的圖片 ────────────────────────────────────────────────

def collect_no_anm(folder: Path, anm_stems: set[str], output_base: Path) -> None:
    """
    找出資料夾中沒有對應 .anm 的 PNG/JPG，複製到 output_base/no_anm/。
    `_a.png` 遮罩若其主檔有對應 .anm 則一同略過。
    """
    no_anm_dir = output_base / "no_anm"
    collected = []

    image_files = sorted(
        f for ext in ("*.png", "*.jpg", "*.jpeg")
        for f in folder.glob(ext)
    )
    for img in image_files:
        stem = img.stem
        # 主圖：stem 直接對應 anm
        if stem in anm_stems:
            continue
        # 遮罩：stem 為 xxx_a，且 xxx 有對應 anm
        if stem.endswith("_a") and stem[:-2] in anm_stems:
            continue
        collected.append(img)

    if not collected:
        print("[info]  所有 PNG 都有對應的 .anm，無需建立 no_anm/")
        return

    no_anm_dir.mkdir(exist_ok=True)
    print(f"\n[info]  發現 {len(collected)} 個無對應 .anm 的圖片，複製至 no_anm/")
    for img in collected:
        shutil.copy2(img, no_anm_dir / img.name)
        print(f"  → {img.name}")


# ── 主程式 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="處理資料夾下所有 .anm 並輸出裁切後的 Sprite PNG")
    parser.add_argument("target", type=Path, help="資料夾路徑，或單一 .anm 檔案路徑")
    parser.add_argument("--thanm", type=str, help="thanm.exe 的完整路徑（預設從環境變數 THANM_PATH 或 PATH 尋找）")
    args = parser.parse_args()

    global THANM
    if args.thanm:
        THANM = args.thanm

    target: Path = args.target.resolve()

    if target.is_file():
        if target.suffix.lower() != ".anm":
            parser.error(f"指定的檔案不是 .anm：{target}")
        anm_files = [target]
        output_base = target.parent.parent / (target.parent.name + "_output")
    elif target.is_dir():
        anm_files = sorted(target.glob("*.anm"))
        if not anm_files:
            print(f"[warn]  在 {target} 中找不到任何 .anm 檔案")
            sys.exit(0)
        print(f"[info]  找到 {len(anm_files)} 個 .anm 檔案")
        anm_stems = {f.stem for f in anm_files}
        output_base = target.parent / (target.name + "_output")
    else:
        parser.error(f"路徑不存在：{target}")

    print(f"[info]  輸出根目錄：{output_base}/")

    success, failed = 0, 0
    for anm_path in anm_files:
        if process_one(anm_path, output_base):
            success += 1
        else:
            failed += 1

    if target.is_dir():
        collect_no_anm(target, anm_stems, output_base)

    print(f"\n{'='*50}")
    print(f"全部完成：{success} 成功 / {failed} 失敗")


if __name__ == "__main__":
    main()
