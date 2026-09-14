import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# 全局设置


# 数据准备
learning_rate = np.array([0.0001, 0.0002, 0.0004, 0.0008])
metrics = {
    'MAE': np.array([0.03780, 0.03801, 0.03943, 0.03949]),
    'RMSE': np.array([0.07879, 0.07991, 0.08236, 0.08451]),
    'R²': np.array([0.89844, 0.89072, 0.88903, 0.88317])
}

# 创建图形（增大整体宽度）
fig = plt.figure(figsize=(22, 6))  # 保持宽度22英寸

# 创建3个正方形子图（调整位置和边距）
axes = []
left_positions = [0.07, 0.39, 0.71]  # 调整水平间距
width = 0.22  # 稍微减小宽度
height = 0.7  # 保持高度

for i in range(3):
    ax = fig.add_axes([left_positions[i], 0.15, width, height])
    axes.append(ax)

# 颜色和标记样式
colors = ['#4169E1', '#3CB371', '#FF6347']
markers = ['o', 's', '^']

# 绘制每个子图
for ax, (metric, values), color, marker in zip(axes, metrics.items(), colors, markers):
    # 绘制曲线（确保标记完整显示）
    ax.plot(learning_rate, values, marker=marker, color=color, linestyle='-',
            markeredgecolor='black', markeredgewidth=1.2,
            markersize=10, clip_on=False)  # 关键参数：clip_on=False

    # 添加数据标签（显示原始值）
    for x, y in zip(learning_rate, values):
        ax.annotate(f'{y}', (x, y), xytext=(0, 8),
                    textcoords="offset points", ha='center',
                    fontsize=11, fontweight='bold')

    # 设置标签
    ax.set_xlabel('Learning Rate', fontsize=12, labelpad=12, fontweight='bold')
    ylabel = {'MAE': 'MAE Value', 'RMSE': 'RMSE Value', 'R²': 'R² Value'}[metric]
    ax.set_ylabel(ylabel, fontsize=12, labelpad=15, fontweight='bold')

    # 设置坐标范围（扩大范围确保标记完整显示）
    if metric == 'MAE':
        ax.set_xlim(0, 0.0009)  # 左侧扩展0.0001，右侧扩展0.0001
        ax.set_ylim(0.0375, 0.04)  # 细化纵坐标范围
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))  # 设置纵坐标为三位小数
        ax.yaxis.set_major_locator(ticker.LinearLocator(numticks=7))  # 设置七个刻度
        ax.xaxis.set_major_locator(ticker.MultipleLocator(0.0002))
        ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.4f'))
    elif metric == 'RMSE':
        ax.set_xlim(0, 0.0009)
        ax.set_ylim(min(values) - 0.001, max(values) + 0.001)  # 细化纵坐标范围
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))  # 设置纵坐标为三位小数
        ax.yaxis.set_major_locator(ticker.LinearLocator(numticks=6))  # 设置六个刻度
        ax.xaxis.set_major_locator(ticker.MultipleLocator(0.0002))
        ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.4f'))
    else:
        ax.set_xlim(0, 0.0009)
        ax.set_ylim(0.88, 0.91)  # 底部扩展0.002，顶部扩展0.002
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.3f'))  # 设置纵坐标为三位小数
        ax.yaxis.set_major_locator(ticker.MultipleLocator(0.01))
        ax.xaxis.set_major_locator(ticker.MultipleLocator(0.0002))
        ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.4f'))

    # 强制设置为正方形（考虑扩展后的范围）
    ax.set_aspect(1.0 / ax.get_data_ratio() * 0.95)  # 微调比例系数

    # 网格和边框
    ax.grid(True, linestyle=':', alpha=0.7)
    for spine in ax.spines.values():
        spine.set_linewidth(1.5)

    # 图例（调整位置到子图内的上方中间，字体小一号）
    legend = ax.legend([metric], fontsize=11, framealpha=0.9,
                       bbox_to_anchor=(0.5, 1.0), loc='upper center', ncol=1)
    for text in legend.get_texts():
        text.set_fontweight('bold')

    # 关键：加粗横坐标刻度
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
    # 纵坐标加粗
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')

# 保存图形
plt.savefig('adjusted_square_subplots.png', dpi=350, bbox_inches='tight')
plt.show()
