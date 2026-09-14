import warnings, os
# os.environ["CUDA_VISIBLE_DEVICES"]="-1"
# os.environ["CUDA_VISIBLE_DEVICES"]="0"

warnings.filterwarnings('ignore')
from ultralytics import YOLO



if __name__ == '__main__':
    # 使用v2版本（去掉P5层）
    model = YOLO(r'"<LOCAL_PATH>"')
    # model.load('yolo11n.pt') # loading pretrain weights
    model.train(data=r"<LOCAL_PATH>",
                cache=False,
                imgsz=640,
                epochs=200,
                batch=32,  # v2版本更轻量，可以尝试增大到 batch=48
                close_mosaic=10, # 最后多少个epoch关闭mosaic数据增强，设置0代表全程开启mosaic训练
                workers=4, # Windows下出现莫名其妙卡主的情况可以尝试把workers设置为0
                # device='0,1',
                optimizer='SGD', # using SGD
                # patience=0, # set 0 to close earlystop.
                # resume=True, # 断点续训,YOLO初始化时选择last.pt
                # amp=False, # close amp | loss出现nan可以关闭amp
                # fraction=0.2,
                project='runs/train',
                name='yolo11-CSP-PMSFA-v2-noP5-Detect_LSCD',  # v2版本命名
                )

