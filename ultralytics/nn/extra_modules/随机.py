
import importlib.util
import sys

# 手动找并加载标准库的 ast
spec = importlib.util.find_spec('ast')  # 这会找标准库的
if spec is None:
    raise ImportError("Cannot find standard ast")
ast_module = importlib.util.module_from_spec(spec)
sys.modules['ast'] = ast_module
spec.loader.exec_module(ast_module)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# ==================== 1. 模拟数据（你需要替换成真实的 γ 值） ====================
# 假设你已经提取了所有 BN 层的 gamma 参数（可以是绝对值 |gamma|）
# 这里用随机数据模拟，实际中你从 model.state_dict() 收集

np.random.seed(42)

# 原始模型（base）：γ 分布较集中，很多值较大
base_gammas = np.concatenate([
    np.random.normal(1.2, 0.4, 800),   # 大部分重要通道
    np.random.normal(0.3, 0.15, 400),  # 一些小值
    np.random.uniform(0, 0.1, 200)     # 接近0的少量
])

# 稀疏训练后（prune）：很多 γ 被推向0
prune_gammas = np.concatenate([
    np.random.normal(1.0, 0.35, 500),   # 保留的重要通道
    np.random.normal(0.1, 0.08, 600),   # 被压小的通道
    np.random.uniform(0, 0.05, 500)     # 大量接近0
])

# 如果你想用绝对值（推荐，大部分论文这么做）
base_gammas = np.abs(base_gammas)
prune_gammas = np.abs(prune_gammas)

print(f"Base γ 数量: {len(base_gammas)},  Mean: {base_gammas.mean():.4f}")
print(f"Prune γ 数量: {len(prune_gammas)}, Mean: {prune_gammas.mean():.4f}")

# ==================== 2. 绘图设置（中英双语，学术风格） ====================
plt.style.use('seaborn-v0_8-whitegrid')  # 或 'ggplot' / 'default'
mpl.rcParams['font.family'] = 'SimHei'   # 支持中文（Windows常见）
# 如果 Mac/Linux 用不到中文字体，可注释上面一行，或换成 'DejaVu Sans'

plt.figure(figsize=(10, 6), dpi=150)

# bins 设置：建议 50~100，根据你的 γ 值范围调整
bins = np.linspace(0, max(max(base_gammas), max(prune_gammas)) * 1.05, 80)

# 绘制 base（绿色）
plt.hist(base_gammas, bins=bins, alpha=0.7, label='Base (before sparsity)', 
         color='forestgreen', edgecolor='black', linewidth=0.5)

# 绘制 prune（橙色），堆叠在上面看对比更明显
plt.hist(prune_gammas, bins=bins, alpha=0.7, label='After sparsity (pruned)', 
         color='orange', edgecolor='black', linewidth=0.5)

# ==================== 3. 美化与标签 ====================
plt.xlabel('BN 缩放因子 γ 的绝对值 |γ|', fontsize=14)
plt.ylabel('通道数量', fontsize=14)
plt.title('稀疏训练前后 BN 缩放因子 γ 分布对比\n'
          'Fig. 4.13 Comparison of BN γ Distributions Before and After Sparsity Training',
          fontsize=15, fontweight='bold', pad=15)

plt.legend(fontsize=12, loc='upper right')
plt.grid(True, linestyle='--', alpha=0.6)

# 可选：限制 x 轴范围（如果 γ 最大值很大，可避免图像太扁）
# plt.xlim(0, 2.5)

# 可选：添加稀疏率统计文本
sparsity_base = (base_gammas < 0.01).mean() * 100
sparsity_prune = (prune_gammas < 0.01).mean() * 100
plt.text(0.02, 0.95, f'Base |γ|<0.01 比例: {sparsity_base:.1f}%\n'
                     f'Prune |γ|<0.01 比例: {sparsity_prune:.1f}%',
         transform=plt.gca().transAxes, fontsize=11,
         bbox=dict(facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig('gamma_distribution_compare.png', dpi=300, bbox_inches='tight')
plt.show()