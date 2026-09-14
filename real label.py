import os
import cv2
import numpy as np

# 图像目录和标注目录
image_dir = r'%USERPROFILE%\Desktop\CCTSDB 2021\实验\images\test'
label_dir = r'%USERPROFILE%\Desktop\CCTSDB 2021\实验\labels\test'

# 获取图像文件列表
image_files = [f for f in os.listdir(image_dir) if f.endswith('.jpg')]

# 遍历每张图像
for image_file in image_files:
    # 读取图像
    image_path = os.path.join(image_dir, image_file)
    img = cv2.imread(image_path)
    if img is None:
        continue

    # 对应的标注文件路径
    label_file = os.path.splitext(image_file)[0] + '.txt'
    label_path = os.path.join(label_dir, label_file)

    # 如果标注文件存在
    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            lines = f.readlines()

        # 遍历每个标注
        for line in lines:
            data = line.split()
            if len(data) < 5:
                continue

            # 解析标注：class_id, center_x, center_y, width, height (归一化)
            class_id = int(data[0])
            center_x = float(data[1])
            center_y = float(data[2])
            width = float(data[3])
            height = float(data[4])

            # 转换为绝对坐标
            img_height, img_width = img.shape[:2]
            x_center = center_x * img_width
            y_center = center_y * img_height
            w = width * img_width
            h = height * img_height

            # 计算左上角坐标
            x1 = int(x_center - w / 2)
            y1 = int(y_center - h / 2)
            x2 = int(x_center + w / 2)
            y2 = int(y_center + h / 2)

            # 在图像上绘制真实框（绿色）
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, f'Class {class_id}', (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

        # 保存或显示图像
        output_path = os.path.join('output', image_file)  # 确保output目录存在
        cv2.imwrite(output_path, img)
        # 或者显示
        # cv2.imshow('Ground Truth', img)
        # cv2.waitKey(0)

# cv2.destroyAllWindows()