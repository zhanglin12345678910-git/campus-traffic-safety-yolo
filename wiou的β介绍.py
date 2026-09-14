# 导入必要的库
import numpy as np  # 用于数值计算
import matplotlib.pyplot as plt  # 用于绘图

# 设置matplotlib的中文显示配置
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置为黑体，解决中文显示问题
plt.rcParams['axes.unicode_minus'] = False    # 正确显示负号，解决负号显示问题

# 设置参数
beta = np.linspace(0.1, 5.0, 500)  # 生成500个均匀分布的β值，范围从0.1到5.0
alpha = 1.7  # α参数，用于控制函数的形状
delta = 2.7  # δ参数，表示期望的β阈值

# 计算WIoU v3的聚焦函数r
# r = β / (δ * α^(β-δ))，这个函数用于根据锚框质量动态调整损失权重
r = beta / (delta * np.power(alpha, beta - delta))

# 创建图形并设置大小
plt.figure(figsize=(8, 5))  # 设置图形大小为8x5英寸

# 绘制主曲线
plt.plot(beta, r, label='r(β)', color='blue', linewidth=2)  # 绘制r(β)曲线，使用蓝色，线宽为2

# 添加参考线
plt.axvline(x=delta, linestyle='--', color='red', label='β = δ')  # 添加β=δ的垂直参考线

# 设置图形标题和轴标签
plt.title("WIoU v3 聚焦函数 r 与 锚框质量 β 的关系")  # 图形标题
plt.xlabel("β（离群度）")  # x轴标签
plt.ylabel("r（损失缩放因子）")  # y轴标签
plt.legend()  # 显示图例
plt.grid(True)  # 显示网格
plt.tight_layout()  # 自动调整子图参数，使之填充整个图像区域
plt.show()  # 显示图形
