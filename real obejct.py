import cv2, numpy as np
from pathlib import Path
from tqdm import tqdm

IMG_DIR   = Path(r"%USERPROFILE%\Desktop\CCTSDB 2021\实验\images\test")
LABEL_DIR = Path(r"%USERPROFILE%\Desktop\CCTSDB 2021\实验\labels\test")
SAVE_DIR  = Path(r"runs\gt_drawn_all")
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# 0-蓝 1-红 2-黄；其余自动绿色
CLS_COLOR = {0:(255,0,0), 1:(0,0,255), 2:(0,255,255)}

def imread_u(p):
    data = np.fromfile(str(p), np.uint8)
    return cv2.imdecode(data, 1) if data.size else None

def imwrite_u(p, img):
    buf = cv2.imencode(".jpg", img)[1]
    buf.tofile(str(p))

seen_cls = set()
bad_img  = []

for img_path in tqdm(IMG_DIR.glob("*.*"), desc="GT draw"):
    img = imread_u(img_path)
    if img is None:
        bad_img.append(img_path.name)
        continue

    h, w = img.shape[:2]
    txt = LABEL_DIR / f"{img_path.stem}.txt"
    if txt.exists():
        for line in txt.read_text().strip().splitlines():
            cls, xc, yc, bw, bh = map(float, line.split())
            cls_id = int(round(cls))
            seen_cls.add(cls_id)

            color = CLS_COLOR.get(cls_id, (0,255,0))
            color = tuple(int(c) for c in color)      # ← 关键

            x1, y1 = int((xc-bw/2)*w), int((yc-bh/2)*h)
            x2, y2 = int((xc+bw/2)*w), int((yc+bh/2)*h)
            try:
                cv2.rectangle(img, (x1,y1), (x2,y2), color, 2)
            except Exception as e:
                print(f"[Err] {img_path.name}  cls={cls_id}  {e}")

    imwrite_u(SAVE_DIR / img_path.name, img)

print("完成！文件输出到：", SAVE_DIR.resolve())
print("出现过的类别：", sorted(seen_cls))
if bad_img:
    print("无法读取图片：", bad_img[:10], "...")
