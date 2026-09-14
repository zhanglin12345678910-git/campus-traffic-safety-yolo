"""最小测试：验证 cv2 和路径是否正常"""
import cv2
import numpy as np
from pathlib import Path

def imwrite_unicode(path, img):
    """cv2.imwrite 不支持中文路径，用 imencode + Python I/O 替代"""
    ret, buf = cv2.imencode(Path(path).suffix, img)
    if ret:
        Path(path).write_bytes(buf.tobytes())
    return ret

ROOT = Path(r"<LOCAL_PATH>")
IMG_DIR = ROOT / "images" / "train"
OUT = Path(__file__).parent / "test_output"
OUT.mkdir(exist_ok=True)

imgs = list(IMG_DIR.glob("*.jpg"))
print(f"找到 {len(imgs)} 张 jpg")

if imgs:
    p = imgs[0]
    print(f"测试读取: {p}")
    print(f"  文件存在: {p.exists()}")
    img = cv2.imread(str(p))
    print(f"  imread结果: {type(img)}, shape={img.shape if img is not None else 'NONE'}")

    if img is not None:
        out = OUT / f"test_{p.name}"
        ok = imwrite_unicode(out, img)
        print(f"  写入结果: {ok}")
        print(f"  输出文件: {out} (存在: {out.exists()})")
else:
    print("未找到 .jpg，尝试列出目录内容：")
    for f in IMG_DIR.iterdir():
        print(f"  {f.name}")
        if len(list(IMG_DIR.iterdir())) > 20:
            print("  ... (超过20个文件，停止列举)")
            break
