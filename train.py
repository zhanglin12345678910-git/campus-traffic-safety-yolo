import warnings, os
# os.environ["CUDA_VISIBLE_DEVICES"]="-1"
# os.environ["CUDA_VISIBLE_DEVICES"]="0"

warnings.filterwarnings('ignore')
from ultralytics import YOLO



if __name__ == '__main__':
    model = YOLO(r"<PROJECT_ROOT>\PMSFA_Ablation_Study_20260524\MultiScale_Module_Comparison\yolo11n-C2f-ASPP.yaml")
    # model.load('yolo11n.pt') # loading pretrain weights
    model.train(data=r"%USERPROFILE%\Desktop\AI-Reaserch\CCTSDB 2021\TEST-EXAM\cctsdb.yaml",
                cache=False,
                imgsz=640,
                epochs=200,
                batch=16,
                close_mosaic=10, # 最后多少个epoch关闭mosaic数据增强，设置0代表全程开启mosaic训练
                workers=0, # Windows下出现莫名其妙卡主的情况可以尝试把workers设置为0
                # device='0,1',
                optimizer='SGD', # using SGD
                # patience=0, # set 0 to close earlystop.
                # resume=True, # 断点续训,YOLO初始化时选择last.pt
                # amp=False, # close amp | loss出现nan可以关闭amp我LINGE2#
                # fraction=0.2,
                project='runs/train',
                name='ASPP-pssm-cctsdb-200e',
                )
    