import warnings
warnings.filterwarnings('ignore')
from ultralytics import YOLO



if __name__ == '__main__':
    model = YOLO(r"<LOCAL_PATH>") # select your model.pt path
    results = model.predict(source=r'<LOCAL_PATH>',
                            imgsz=640,
                            project='runs/detect',
                            name='new-tt100k-3-predict',
                            device=0,
                            save=True,
                            # conf=0.2,
                            # iou=0.7,
                            # agnostic_nms=True,
                            # visualize=True, # visualize model features maps
                            # show_conf=False, # do not show prediction confidence
                            # show_labels=False, # do not show prediction labels
                            save_txt=True, # save results as .txt file
                            save_crop=False, # avoid saving many cropped images during large-batch prediction
                            save_conf=True,
                            line_width=2,
                            stream=True
                            )
    for _ in results:
        pass
