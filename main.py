"""
main.py — spritesheet-processor 統一 CLI 入口

子指令：
  merge   合併資料夾內的 xxx.png + xxx_a.png（遮罩）
  cut     依座標 JSON 切割 spritesheet
"""

import argparse
from pathlib import Path

from merger import process_folder
from cutter import cut_from_json


def cmd_merge(args):
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[error] 找不到資料夾：{folder}")
        return
    output = Path(args.output) if args.output else None
    process_folder(folder, output, args.overwrite)


def cmd_cut(args):
    sheet = Path(args.sheet)
    coords = Path(args.coords)
    if not sheet.is_file():
        print(f"[error] 找不到 sheet：{sheet}")
        return
    if not coords.is_file():
        print(f"[error] 找不到座標檔：{coords}")
        return
    output = Path(args.output) if args.output else sheet.parent / "output"
    cut_from_json(sheet, coords, output, args.prefix, args.overwrite)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spritesheet-processor",
        description="Spritesheet 處理工具",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- merge ---
    p_merge = sub.add_parser("merge", help="合併 PNG 與遮罩（_a.png）")
    p_merge.add_argument("folder", help="包含圖片的資料夾")
    p_merge.add_argument("-o", "--output", default=None, help="輸出資料夾（預設覆蓋原檔）")
    p_merge.add_argument("--overwrite", action="store_true", help="允許覆蓋已存在的輸出檔")
    p_merge.set_defaults(func=cmd_merge)

    # --- cut ---
    p_cut = sub.add_parser("cut", help="依座標切割 spritesheet")
    p_cut.add_argument("sheet", help="spritesheet 圖片路徑")
    p_cut.add_argument("coords", help="座標 JSON 檔路徑")
    p_cut.add_argument("-o", "--output", default=None, help="輸出資料夾（預設：sheet 同層的 output/）")
    p_cut.add_argument("--prefix", default="", help="輸出檔名前綴")
    p_cut.add_argument("--overwrite", action="store_true", help="允許覆蓋已存在的輸出檔")
    p_cut.set_defaults(func=cmd_cut)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
