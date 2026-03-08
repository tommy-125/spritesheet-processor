"""
cutter.py
依座標定義切割 spritesheet，輸出個別 PNG 檔。

座標 JSON 格式（兩種皆支援）：

格式 A — 物件（有名稱）：
{
  "hero_idle": [0, 0, 64, 64],
  "hero_run":  [64, 0, 64, 64]
}

格式 B — 陣列（自動編號）：
[
  [0, 0, 64, 64],
  [64, 0, 64, 64]
]

每個 sprite 的值為 [x, y, width, height]。
"""

import argparse
import json
from pathlib import Path
from PIL import Image


SpriteEntry = tuple[str, tuple[int, int, int, int]]  # (name, (x, y, w, h))


def load_coords(coords_path: Path) -> list[SpriteEntry]:
    """從 JSON 檔讀取座標，回傳 [(name, (x, y, w, h)), ...] 列表。"""
    with open(coords_path, encoding="utf-8") as f:
        data = json.load(f)

    entries: list[SpriteEntry] = []

    if isinstance(data, dict):
        for name, rect in data.items():
            entries.append((name, tuple(rect)))
    elif isinstance(data, list):
        pad = len(str(len(data)))
        for i, rect in enumerate(data):
            entries.append((f"sprite_{i:0{pad}d}", tuple(rect)))
    else:
        raise ValueError("JSON 格式錯誤：根層級必須是物件或陣列")

    return entries


def cut_sprites(
    sheet_path: Path,
    entries: list[SpriteEntry],
    output_dir: Path,
    prefix: str = "",
    overwrite: bool = False,
) -> list[Path]:
    """
    切割 spritesheet 並儲存每個 sprite。
    回傳所有輸出檔案路徑。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.open(sheet_path)
    sw, sh = sheet.size
    outputs = []

    for name, (x, y, w, h) in entries:
        # 邊界檢查
        if x < 0 or y < 0 or x + w > sw or y + h > sh:
            print(f"[warn] '{name}' 座標超出圖片範圍 ({x},{y},{w},{h}) / sheet {sw}x{sh}，略過")
            continue

        filename = f"{prefix}{name}.png" if prefix else f"{name}.png"
        dest = output_dir / filename

        if dest.exists() and not overwrite:
            print(f"[skip] {filename} 已存在（使用 --overwrite 強制覆蓋）")
            continue

        sprite = sheet.crop((x, y, x + w, y + h))
        sprite.save(dest, "PNG")
        print(f"[ok]   {filename}  ({x},{y}) {w}x{h}")
        outputs.append(dest)

    return outputs


def cut_from_json(
    sheet_path: Path,
    coords_path: Path,
    output_dir: Path,
    prefix: str = "",
    overwrite: bool = False,
) -> list[Path]:
    """便利函式：從 JSON 讀座標後切割。"""
    entries = load_coords(coords_path)
    return cut_sprites(sheet_path, entries, output_dir, prefix, overwrite)


def main():
    parser = argparse.ArgumentParser(description="依座標切割 spritesheet")
    parser.add_argument("sheet", type=Path, help="spritesheet 圖片路徑")
    parser.add_argument("coords", type=Path, help="座標 JSON 檔路徑")
    parser.add_argument("-o", "--output", type=Path, default=None, help="輸出資料夾（預設：sheet 同層的 output/）")
    parser.add_argument("--prefix", default="", help="輸出檔名前綴")
    parser.add_argument("--overwrite", action="store_true", help="允許覆蓋已存在的輸出檔")
    args = parser.parse_args()

    if not args.sheet.is_file():
        parser.error(f"找不到 sheet：{args.sheet}")
    if not args.coords.is_file():
        parser.error(f"找不到座標檔：{args.coords}")

    output_dir = args.output or (args.sheet.parent / "output")
    cut_from_json(args.sheet, args.coords, output_dir, args.prefix, args.overwrite)


if __name__ == "__main__":
    main()
