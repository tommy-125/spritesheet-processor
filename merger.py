"""
merger.py
掃描資料夾，將 xxx.png 與 xxx_a.png（灰階遮罩）合併成帶 alpha 的 PNG。
遮罩規則：白色 = 不透明，黑色 = 透明。
"""

import argparse
import re
from pathlib import Path
from PIL import Image


def find_pairs(folder: Path) -> list[tuple[Path, Path]]:
    """找出所有 (base.png, base_a.png) 配對。"""
    mask_pattern = re.compile(r"^(.+)_a\.png$", re.IGNORECASE)
    masks: dict[str, Path] = {}

    for f in folder.iterdir():
        m = mask_pattern.match(f.name)
        if m:
            masks[m.group(1).lower()] = f

    pairs = []
    for f in folder.iterdir():
        if f.suffix.lower() != ".png":
            continue
        # 跳過本身就是 _a 結尾的檔案
        if re.search(r"_a$", f.stem, re.IGNORECASE):
            continue
        key = f.stem.lower()
        if key in masks:
            pairs.append((f, masks[key]))

    return sorted(pairs, key=lambda p: p[0].name)


def merge_with_mask(base_path: Path, mask_path: Path) -> Image.Image:
    """將遮罩套用為 base 圖的 alpha channel，回傳 RGBA 圖。"""
    base = Image.open(base_path).convert("RGBA")
    mask = Image.open(mask_path).convert("L")  # 轉灰階

    if base.size != mask.size:
        raise ValueError(
            f"尺寸不符：{base_path.name} {base.size} vs {mask_path.name} {mask.size}"
        )

    r, g, b, _ = base.split()
    merged = Image.merge("RGBA", (r, g, b, mask))
    return merged


def process_folder(
    folder: Path,
    output_dir: Path | None = None,
    overwrite: bool = False,
) -> list[Path]:
    """
    處理資料夾內所有配對，輸出合併後的 PNG。
    output_dir 為 None 時，輸出至同一資料夾（覆蓋 base 檔）。
    回傳所有輸出檔案路徑。
    """
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    pairs = find_pairs(folder)
    if not pairs:
        print(f"[!] 在 {folder} 中找不到任何 (png + mask) 配對")
        return []

    outputs = []
    for base_path, mask_path in pairs:
        dest = (output_dir or folder) / base_path.name
        if dest.exists() and not overwrite and dest != base_path:
            print(f"[skip] {dest.name} 已存在（使用 --overwrite 強制覆蓋）")
            continue

        try:
            img = merge_with_mask(base_path, mask_path)
            img.save(dest, "PNG")
            print(f"[ok]   {base_path.name} + {mask_path.name} -> {dest}")
            outputs.append(dest)
        except Exception as e:
            print(f"[err]  {base_path.name}: {e}")

    return outputs


def main():
    parser = argparse.ArgumentParser(description="合併 PNG 與遮罩（_a.png）")
    parser.add_argument("folder", type=Path, help="包含圖片的資料夾")
    parser.add_argument("-o", "--output", type=Path, default=None, help="輸出資料夾（預設覆蓋原檔）")
    parser.add_argument("--overwrite", action="store_true", help="允許覆蓋已存在的輸出檔")
    args = parser.parse_args()

    if not args.folder.is_dir():
        parser.error(f"找不到資料夾：{args.folder}")

    process_folder(args.folder, args.output, args.overwrite)


if __name__ == "__main__":
    main()
