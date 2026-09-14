# -*- coding: utf-8 -*-
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from ultralytics.utils.plotting import plot_results


# ======================== 使用说明 ========================
# 这个脚本的作用：
#   根据 Ultralytics YOLO 训练得到的 results.csv，重新生成训练曲线图 results.png。
#
# 你不需要在命令行输入参数，直接在下面三行填写路径，然后运行本文件即可。
#
# 需要修改的配置只有这 3 个：
#   1. INPUT_PATH   ：你的 csv 文件路径，或者存放 csv 的文件夹路径
#   2. OUTPUT_PATH  ：输出图片路径/输出文件夹路径；留空则默认保存到 csv 同目录
#   3. RECURSIVE    ：当 INPUT_PATH 是文件夹时，是否递归搜索子文件夹里的 csv
#
# ----------------------------------------------------------
# 用法 1：只有一个 results.csv，生成到 csv 同目录
# ----------------------------------------------------------
# INPUT_PATH = r"<LOCAL_PATH>"
# OUTPUT_PATH = r""
# RECURSIVE = False
#
# 运行后生成：
# <LOCAL_PATH>
#
# ----------------------------------------------------------
# 用法 2：只有一个 results.csv，但想指定输出图片名
# ----------------------------------------------------------
# INPUT_PATH = r"<LOCAL_PATH>"
# OUTPUT_PATH = r"<LOCAL_PATH>"
# RECURSIVE = False
#
# ----------------------------------------------------------
# 用法 3：一个文件夹里有多个 csv，批量生成图片
# ----------------------------------------------------------
# INPUT_PATH = r"<LOCAL_PATH>"
# OUTPUT_PATH = r"<LOCAL_PATH>"
# RECURSIVE = False
#
# ----------------------------------------------------------
# 用法 4：一个总文件夹里有很多子文件夹，每个子文件夹里有 csv
# ----------------------------------------------------------
# INPUT_PATH = r"<LOCAL_PATH>"
# OUTPUT_PATH = r"<LOCAL_PATH>"
# RECURSIVE = True
#
# 注意：
#   - 训练结果文件一般叫 results.csv。
#   - 如果你的 csv 文件不叫 results.csv，也可以用，本脚本会自动临时改名后绘图。
#   - 输出图片是 Ultralytics 原生 plot_results() 生成的 YOLO 风格 results.png。
# ==========================================================

# ======================== 路径配置区 ========================
# 输入路径：
#   - 如果只处理一个文件，就填 results.csv 的完整路径。
#   - 如果批量处理，就填存放 csv 的文件夹路径。
INPUT_PATH = r"<LOCAL_PATH>"

# 输出路径：
#   - 留空：图片保存到 csv 同目录，文件名为 results.png。
#   - 单个 csv：可以填完整 png 路径。
#   - 多个 csv：填写输出文件夹路径。
OUTPUT_PATH = r""

# 是否递归搜索子文件夹：
#   - False：只搜索 INPUT_PATH 当前文件夹。
#   - True ：搜索 INPUT_PATH 以及所有子文件夹。
RECURSIVE = False
# ==========================================================


def safe_name(text):
    """Make a Windows-safe file name from a path string."""
    text = str(text)
    for ch in '<>:"/\\|?*, ':
        text = text.replace(ch, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_") or "results"


def collect_csv_files(input_path, recursive=False):
    """Collect CSV files from a file or folder."""
    path = Path(input_path)
    if path.is_file():
        return [path]
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    pattern = "**/*.csv" if recursive else "*.csv"
    return sorted(path.glob(pattern))


def generate_one(csv_path, output_path=None):
    """
    Generate a YOLO-style results.png from any training CSV.

    Ultralytics plot_results() looks for results*.csv in the CSV directory,
    so this function copies the input CSV to a temporary results.csv first.
    """
    csv_path = Path(csv_path)
    if output_path is None:
        output_path = csv_path.with_name("results.png")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        tmp_csv = tmp_dir / "results.csv"
        shutil.copy2(csv_path, tmp_csv)

        plot_results(file=str(tmp_csv))

        tmp_png = tmp_dir / "results.png"
        if not tmp_png.exists():
            raise RuntimeError(f"Ultralytics did not generate results.png for: {csv_path}")
        shutil.copy2(tmp_png, output_path)

    return output_path


def main():
    if len(sys.argv) == 1:
        if not INPUT_PATH:
            raise ValueError(
                "Please fill INPUT_PATH at the top of this file, for example:\n"
                r'INPUT_PATH = r"<LOCAL_PATH>"'
            )
        args = argparse.Namespace(input=INPUT_PATH, out=OUTPUT_PATH, recursive=RECURSIVE)
    else:
        parser = argparse.ArgumentParser(
            description="Generate Ultralytics YOLO results.png from one CSV file or a folder of CSV files."
        )
        parser.add_argument(
            "--input",
            "-i",
            required=True,
            help="Path to a CSV file, or a folder containing CSV files.",
        )
        parser.add_argument(
            "--out",
            "-o",
            default="",
            help="Output png path for one CSV, or output folder for multiple CSV files. Default: same folder as CSV.",
        )
        parser.add_argument(
            "--recursive",
            "-r",
            action="store_true",
            help="Recursively search CSV files when input is a folder.",
        )
        args = parser.parse_args()

    csv_files = collect_csv_files(args.input, recursive=args.recursive)
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in: {args.input}")

    out_arg = Path(args.out) if args.out else None
    multiple = len(csv_files) > 1

    print(f"Found {len(csv_files)} CSV file(s).")
    for csv_path in csv_files:
        if out_arg:
            if multiple or out_arg.suffix.lower() != ".png":
                out_arg.mkdir(parents=True, exist_ok=True)
                png_name = f"{safe_name(csv_path.parent.name)}_{safe_name(csv_path.stem)}.png"
                output_path = out_arg / png_name
            else:
                output_path = out_arg
        else:
            output_path = csv_path.with_name("results.png")

        png_path = generate_one(csv_path, output_path)
        print(f"OK: {csv_path} -> {png_path}")


if __name__ == "__main__":
    main()
