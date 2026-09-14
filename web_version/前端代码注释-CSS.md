# 📘 前端CSS样式详细注释 - style.css

> 文件位置：`web_version/static/css/style.css`  
> 作者：project_user  
> 功能：实现专业的UI设计、动画效果、响应式布局

---

## 📋 目录

1. [CSS变量定义](#1-css变量定义)
2. [全局样式重置](#2-全局样式重置)
3. [导航栏样式](#3-导航栏样式)
4. [首页样式](#4-首页样式)
5. [检测页面样式](#5-检测页面样式)
6. [历史记录样式](#6-历史记录样式)
7. [统计分析样式](#7-统计分析样式)
8. [通知系统样式](#8-通知系统样式)
9. [响应式设计](#9-响应式设计)
10. [动画效果](#10-动画效果)

---

## 1. CSS变量定义

```css
/**
 * CSS自定义属性（变量）
 * 用途：统一管理颜色、间距、阴影等设计元素
 * 优点：便于维护、快速切换主题
 */
:root {
    /* ========== 颜色系统 ========== */
    
    /* 主题色 - 蓝色系 */
    --primary-color: #3b82f6;      /* 主要蓝色 */
    --primary-dark: #1e40af;       /* 深蓝色（悬停） */
    --primary-light: #60a5fa;      /* 浅蓝色（高亮） */
    
    /* 成功色 - 绿色系 */
    --success-color: #10b981;      /* 成功绿 */
    --success-dark: #059669;       /* 深绿 */
    
    /* 警告色 - 橙色系 */
    --warning-color: #f59e0b;      /* 警告橙 */
    --warning-dark: #d97706;       /* 深橙 */
    
    /* 危险色 - 红色系 */
    --danger-color: #ef4444;       /* 危险红 */
    --danger-dark: #dc2626;        /* 深红 */
    
    /* 信息色 - 紫色系 */
    --info-color: #8b5cf6;         /* 信息紫 */
    --info-dark: #7c3aed;          /* 深紫 */
    
    /* 灰度色 - 从浅到深 */
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-400: #9ca3af;
    --gray-500: #6b7280;
    --gray-600: #4b5563;
    --gray-700: #374151;
    --gray-800: #1f2937;
    --gray-900: #111827;
    
    /* ========== 背景与文本 ========== */
    
    /* 深色背景（主题风格） */
    --bg-dark: #0a0e1a;            /* 页面主背景 */
    --bg-section: #0f1729;         /* section背景 */
    --bg-card: #1a2332;            /* 卡片背景 */
    
    /* 渐变背景 */
    --card-gradient: linear-gradient(
        135deg,
        rgba(15, 23, 42, 0.8),     /* 深蓝透明 */
        rgba(30, 41, 59, 0.6)      /* 中蓝透明 */
    );
    
    /* ========== 间距系统 ========== */
    --spacing-xs: 0.5rem;          /* 8px */
    --spacing-sm: 1rem;            /* 16px */
    --spacing-md: 1.5rem;          /* 24px */
    --spacing-lg: 2rem;            /* 32px */
    --spacing-xl: 3rem;            /* 48px */
    
    /* ========== 阴影效果 ========== */
    --shadow-sm: 0 2px 4px rgba(0, 0, 0, 0.1);
    --shadow-md: 0 4px 8px rgba(0, 0, 0, 0.2);
    --shadow-lg: 0 8px 16px rgba(0, 0, 0, 0.3);
    --shadow-xl: 0 20px 40px rgba(0, 0, 0, 0.4);
    
    /* 发光阴影（主题色） */
    --shadow-glow: 0 0 20px rgba(59, 130, 246, 0.3);
    
    /* ========== 过渡动画 ========== */
    --transition: all 0.3s ease;   /* 通用过渡 */
    --transition-fast: all 0.15s ease;  /* 快速过渡 */
    --transition-slow: all 0.5s ease;   /* 慢速过渡 */
    
    /* ========== 边框圆角 ========== */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
}
```

---

## 2. 全局样式重置

```css
/**
 * 全局样式重置
 * 用途：统一浏览器默认样式差异
 */
* {
    margin: 0;                     /* 清除默认margin */
    padding: 0;                    /* 清除默认padding */
    box-sizing: border-box;        /* 盒模型：border-box */
}

/**
 * body样式
 * 功能：设置全局字体、颜色、背景
 */
body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg-dark);    /* 深色背景 */
    color: var(--gray-100);        /* 浅色文字 */
    line-height: 1.6;              /* 行高1.6倍 */
    overflow-x: hidden;            /* 隐藏横向滚动条 */
}

/**
 * 平滑滚动
 * 功能：页面内锚点跳转时平滑过渡
 */
html {
    scroll-behavior: smooth;
}

/**
 * 链接样式重置
 */
a {
    text-decoration: none;         /* 去除下划线 */
    color: inherit;                /* 继承父元素颜色 */
    transition: var(--transition); /* 添加过渡效果 */
}

a:hover {
    color: var(--primary-color);   /* 悬停变蓝 */
}

/**
 * 按钮样式重置
 */
button {
    border: none;                  /* 去除默认边框 */
    background: none;              /* 去除默认背景 */
    cursor: pointer;               /* 鼠标指针 */
    font-family: inherit;          /* 继承字体 */
}
```

---

## 3. 导航栏样式

```css
/**
 * 导航栏容器
 * 布局：固定顶部，毛玻璃效果
 */
.navbar {
    position: fixed;               /* 固定定位 */
    top: 0;                        /* 顶部对齐 */
    left: 0;
    right: 0;
    z-index: 1000;                 /* 最高层级 */
    background: rgba(10, 14, 26, 0.9);  /* 半透明背景 */
    backdrop-filter: blur(10px);   /* 毛玻璃效果 */
    border-bottom: 1px solid rgba(59, 130, 246, 0.2);  /* 蓝色底边 */
    padding: 1rem 2rem;            /* 内边距 */
    box-shadow: var(--shadow-md);  /* 阴影 */
}

/**
 * 导航栏内容容器
 * 布局：Flexbox，左右分布
 */
.nav-container {
    max-width: 1400px;             /* 最大宽度 */
    margin: 0 auto;                /* 居中 */
    display: flex;                 /* Flex布局 */
    justify-content: space-between;  /* 两端对齐 */
    align-items: center;           /* 垂直居中 */
}

/**
 * Logo区域
 */
.nav-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;                  /* 图标与文字间距 */
    font-size: 1.5rem;             /* 字体大小 */
    font-weight: 700;              /* 粗体 */
    color: var(--gray-100);        /* 浅色文字 */
}

.nav-brand i {
    color: var(--primary-color);   /* 图标蓝色 */
    font-size: 1.75rem;            /* 图标更大 */
}

/**
 * 导航链接容器
 */
.nav-links {
    display: flex;
    gap: 2rem;                     /* 链接间距 */
}

/**
 * 单个导航链接
 * 功能：悬停效果、激活状态
 */
.nav-link {
    padding: 0.5rem 1rem;          /* 内边距 */
    border-radius: var(--radius-md);  /* 圆角 */
    transition: var(--transition);  /* 过渡动画 */
    color: var(--gray-400);        /* 默认灰色 */
}

.nav-link:hover {
    background: rgba(59, 130, 246, 0.1);  /* 浅蓝背景 */
    color: var(--primary-color);   /* 蓝色文字 */
    transform: translateY(-2px);   /* 上浮2px */
}

/**
 * 激活状态的导航链接
 */
.nav-link.active {
    background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
    color: white;                  /* 白色文字 */
    box-shadow: var(--shadow-glow);  /* 发光效果 */
}
```

---

## 4. 首页样式

```css
/**
 * Hero区域
 * 布局：Flex居中，水平方向
 */
.hero-section {
    display: flex;
    flex-direction: column;        /* 垂直排列 */
    align-items: center;           /* 水平居中 */
    justify-content: center;       /* 垂直居中 */
    min-height: 100vh;             /* 至少占满视口高度 */
    padding: 0rem 0;               /* 垂直内边距 */
    gap: 0rem;                     /* 元素间距 */
    text-align: center;            /* 文字居中 */
}

/**
 * Hero标题
 * 样式：渐变色、大字号
 */
.hero-title {
    font-size: 3.5rem;             /* 56px */
    font-weight: 800;              /* 超粗体 */
    margin-bottom: 1rem;
    
    /* 渐变文字效果 */
    background: linear-gradient(135deg, var(--primary-color), var(--info-color));
    -webkit-background-clip: text;  /* WebKit内核 */
    -webkit-text-fill-color: transparent;  /* 文字透明 */
    background-clip: text;
}

/**
 * Hero描述文字
 */
.hero-description {
    font-size: 1.25rem;            /* 20px */
    color: var(--gray-400);        /* 灰色 */
    margin-bottom: 2rem;
    max-width: 600px;              /* 最大宽度 */
    line-height: 1.8;              /* 行高 */
}

/**
 * 功能按钮组
 */
.hero-buttons {
    display: flex;
    gap: 1rem;                     /* 按钮间距 */
    justify-content: center;       /* 居中 */
    margin-bottom: 2rem;
}

/**
 * 特性卡片容器
 * 布局：Flexbox，居中
 */
.hero-image {
    display: flex;
    gap: 0.5rem;                   /* 卡片间距：0.5rem = 很近 */
    justify-content: flex-start;   /* 左对齐 */
    flex-wrap: wrap;               /* 允许换行 */
    max-width: 800px;
}

/**
 * 浮动卡片
 * 效果：悬停上浮、阴影增强
 */
.floating-card {
    background: var(--card-gradient);  /* 渐变背景 */
    padding: 1.25rem;              /* 内边距 */
    border-radius: var(--radius-lg);  /* 大圆角 */
    border: 1px solid rgba(59, 130, 246, 0.2);  /* 蓝色边框 */
    text-align: center;
    transition: var(--transition);
    flex: 1;                       /* 自适应宽度 */
    min-width: 160px;              /* 最小宽度 */
    backdrop-filter: blur(10px);   /* 毛玻璃 */
}

.floating-card:hover {
    transform: translateY(-10px);  /* 上浮10px */
    box-shadow: var(--shadow-xl);  /* 增强阴影 */
    border-color: var(--primary-color);  /* 边框变蓝 */
}

/**
 * 卡片图标
 * 样式：圆形背景、渐变色
 */
.card-icon {
    width: 50px;                   /* 宽度 */
    height: 50px;                  /* 高度 */
    background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
    border-radius: 50%;            /* 圆形 */
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 0.75rem;        /* 居中，底部间距 */
    font-size: 1.25rem;            /* 图标大小 */
    color: white;
}

/**
 * 卡片标题
 */
.floating-card h3 {
    font-size: 1rem;               /* 字体大小 */
    font-weight: 600;
    color: var(--gray-100);
    margin-bottom: 0.25rem;
}

/**
 * 卡片描述
 */
.floating-card p {
    font-size: 0.8125rem;          /* 13px */
    color: var(--gray-400);
    margin: 0;
}
```

---

## 5. 检测页面样式

```css
/**
 * 检测内容区域
 * 布局：Grid，2:1比例（左2右1）
 */
.detect-content {
    display: grid;
    grid-template-columns: 2fr 1fr;  /* 左侧2份，右侧1份 */
    gap: 2rem;                     /* 间距 */
    height: calc(100vh - 140px);   /* 高度：视口高度 - 导航栏 - 标题 */
}

/**
 * 上传区域
 * 样式：深色背景、圆角、边框
 */
.upload-section {
    background: var(--card-gradient);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: var(--radius-lg);
    padding: 2rem;
    display: flex;
    flex-direction: column;        /* 垂直排列 */
    gap: 1.5rem;
    height: 100%;                  /* 占满父容器 */
    overflow-y: auto;              /* 纵向滚动 */
}

/**
 * 文件预览区域
 * 功能：显示占位符或预览内容
 */
.file-preview {
    background: rgba(15, 23, 42, 0.6);
    border: 2px dashed rgba(59, 130, 246, 0.3);  /* 虚线边框 */
    border-radius: var(--radius-md);
    padding: 3rem;
    text-align: center;
    transition: var(--transition);
    min-height: 300px;             /* 最小高度 */
    max-height: 600px;             /* 最大高度 */
    display: flex;
    align-items: center;
    justify-content: center;
}

/**
 * 文件预览悬停效果
 */
.file-preview:hover {
    border-color: var(--primary-color);  /* 边框变蓝 */
    background: rgba(59, 130, 246, 0.05);  /* 浅蓝背景 */
}

/**
 * 预览占位符
 * 样式：大图标、提示文字
 */
.preview-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
}

.preview-placeholder i {
    font-size: 4rem;               /* 64px大图标 */
    color: var(--primary-color);
    opacity: 0.5;
}

.preview-placeholder h3 {
    font-size: 1.5rem;
    color: var(--gray-200);
}

.preview-placeholder p {
    font-size: 0.9375rem;          /* 15px */
    color: var(--gray-400);
}

/**
 * 预览内容容器
 * 功能：显示图片/视频预览
 */
.preview-content {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #0a0e1a;           /* 深色背景 */
    border-radius: var(--radius-md);
    padding: 1rem;
}

/**
 * 预览图片/视频样式
 * 关键：object-fit: contain（保持比例）
 */
.preview-content img,
.preview-content video {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    object-fit: contain;           /* 等比例缩放，不裁剪 */
    border-radius: var(--radius-md);
}

/**
 * 结果图片容器
 * 布局：inline-flex（适应内容大小）
 */
.result-image {
    flex: 1;                       /* 自适应高度 */
    margin: 0;
    padding: 0;
    background: transparent;       /* 透明背景 */
    display: inline-flex;          /* 容器适应内容 */
    align-items: center;
    justify-content: center;
    min-height: 300px;             /* 最小高度 */
}

/**
 * 结果图片样式
 * 特点：边框直接加在图片上，不是容器上
 */
.result-image img {
    max-width: 100%;
    max-height: calc(100vh - 250px);  /* 限制最大高度 */
    width: auto;
    height: auto;
    object-fit: contain;           /* 保持比例 */
    display: block;
    border-radius: 12px;
    border: 2px solid rgba(59, 130, 246, 0.4);  /* 蓝色边框 */
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);  /* 阴影 */
}

/**
 * 摄像头预览容器
 * 样式：与结果图片类似
 */
.camera-preview {
    flex: 1;
    background: transparent;
    display: inline-flex;          /* 容器适应内容 */
    align-items: center;
    justify-content: center;
    min-height: 300px;
    padding: 0;
    margin-top: 1rem;
}

.camera-preview img {
    max-width: 100%;
    max-height: calc(100vh - 400px);
    width: auto;
    height: auto;
    object-fit: contain;
    display: block;
    border-radius: 12px;
    border: 2px solid rgba(59, 130, 246, 0.4);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}
```

---

## 6. 按钮样式

```css
/**
 * 通用按钮基础样式
 * 特点：圆角、过渡、固定最小尺寸
 */
.btn {
    padding: 0.75rem 1.5rem;       /* 内边距 */
    border-radius: var(--radius-md);  /* 圆角 */
    font-size: 1rem;
    font-weight: 600;
    transition: var(--transition);
    cursor: pointer;
    display: inline-flex;          /* Flex布局 */
    align-items: center;
    gap: 0.5rem;                   /* 图标与文字间距 */
    border: none;
    min-width: 120px;              /* 最小宽度 */
    height: 44px;                  /* 固定高度 */
    justify-content: center;
}

/**
 * 主要按钮（蓝色渐变）
 */
.btn-primary {
    background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
    color: white;
    box-shadow: var(--shadow-md);
}

.btn-primary:hover {
    transform: translateY(-2px);   /* 上浮 */
    box-shadow: var(--shadow-glow);  /* 发光 */
}

/**
 * 次要按钮（灰色）
 */
.btn-secondary {
    background: rgba(71, 85, 105, 0.3);  /* 半透明灰 */
    color: var(--gray-200);
    border: 1px solid var(--gray-700);
}

.btn-secondary:hover {
    background: rgba(71, 85, 105, 0.5);
    border-color: var(--primary-color);
}

/**
 * 成功按钮（绿色）
 */
.btn-success {
    background: linear-gradient(135deg, var(--success-color), var(--success-dark));
    color: white;
}

/**
 * 信息按钮（紫色）
 */
.btn-info {
    background: linear-gradient(135deg, var(--info-color), var(--info-dark));
    color: white;
}

/**
 * 危险按钮（红色）
 */
.btn-danger {
    background: linear-gradient(135deg, var(--danger-color), var(--danger-dark));
    color: white;
}

/**
 * 禁用状态
 */
.btn:disabled {
    opacity: 0.5;                  /* 半透明 */
    cursor: not-allowed;           /* 禁用指针 */
    transform: none !important;    /* 禁用变换 */
}
```

---

## 7. 统计分析样式

```css
/**
 * 统计概览 - 大卡片布局
 * 布局：Grid 4列
 */
.stats-overview {
    display: grid;
    grid-template-columns: repeat(4, 1fr);  /* 4列等宽 */
    gap: 1.5rem;
    margin-bottom: 2rem;
}

/**
 * 大统计卡片
 * 特点：顶部彩色条、渐变背景、悬停上浮
 */
.stat-card-large {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.6));
    border: 2px solid rgba(59, 130, 246, 0.3);
    border-radius: 20px;
    padding: 2rem;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;              /* 隐藏溢出（用于顶部条） */
}

/**
 * 顶部彩色条（伪元素）
 */
.stat-card-large::before {
    content: '';                   /* 必需 */
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;                   /* 高度4px */
    background: linear-gradient(90deg, var(--primary-color), var(--primary-dark));
}

/**
 * 不同主题的顶部条颜色
 */
.stat-card-large.primary::before {
    background: linear-gradient(90deg, #3b82f6, #2563eb);  /* 蓝色 */
}

.stat-card-large.success::before {
    background: linear-gradient(90deg, #10b981, #059669);  /* 绿色 */
}

.stat-card-large.warning::before {
    background: linear-gradient(90deg, #f59e0b, #d97706);  /* 橙色 */
}

.stat-card-large.info::before {
    background: linear-gradient(90deg, #8b5cf6, #7c3aed);  /* 紫色 */
}

/**
 * 卡片悬停效果
 */
.stat-card-large:hover {
    transform: translateY(-5px);   /* 上浮5px */
    border-color: var(--primary-color);
    box-shadow: 0 20px 40px rgba(59, 130, 246, 0.2);  /* 蓝色阴影 */
}

/**
 * 卡片头部（图标+标题）
 */
.stat-card-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    font-size: 0.875rem;           /* 小字号 */
    color: var(--gray-400);
    text-transform: uppercase;     /* 大写 */
    letter-spacing: 0.05em;        /* 字母间距 */
}

.stat-card-header i {
    font-size: 1.25rem;
    color: var(--primary-color);
}

/**
 * 卡片数值（超大字号）
 */
.stat-card-value {
    font-size: 3rem;               /* 48px */
    font-weight: 700;
    color: var(--gray-100);
    margin: 1rem 0;
    line-height: 1;                /* 行高1（紧凑） */
}

/**
 * 卡片底部说明
 */
.stat-card-footer {
    font-size: 0.875rem;
    color: var(--gray-500);
}

/**
 * 小统计卡片
 * 用途：类型分布、性能指标
 */
.mini-stat-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-radius: 12px;
    padding: 1.25rem;
    transition: all 0.3s ease;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
}

/**
 * 小卡片悬停效果
 */
.mini-stat-card:hover {
    border-color: var(--primary-color);
    transform: scale(1.05);        /* 缩放1.05倍 */
    background: rgba(59, 130, 246, 0.1);  /* 浅蓝背景 */
}

/**
 * 小图标（彩色背景）
 */
.mini-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
}

/**
 * 不同类型的图标颜色
 */
.mini-icon.image-icon {
    background: linear-gradient(135deg, #3b82f6, #2563eb);  /* 蓝色 */
    color: white;
}

.mini-icon.video-icon {
    background: linear-gradient(135deg, #8b5cf6, #7c3aed);  /* 紫色 */
    color: white;
}

.mini-icon.camera-icon {
    background: linear-gradient(135deg, #10b981, #059669);  /* 绿色 */
    color: white;
}

.mini-icon.success-icon {
    background: linear-gradient(135deg, #10b981, #059669);
    color: white;
}

.mini-icon.star-icon {
    background: linear-gradient(135deg, #f59e0b, #d97706);  /* 橙色 */
    color: white;
}

.mini-icon.trophy-icon {
    background: linear-gradient(135deg, #fbbf24, #f59e0b);  /* 金色 */
    color: white;
}
```

---

## 8. 趋势图样式

```css
/**
 * 趋势图容器
 */
.chart-container {
    min-height: 250px;
    position: relative;
}

/**
 * 柱状图容器
 * 布局：Flexbox，底部对齐
 */
.chart-bars {
    display: flex;
    align-items: flex-end;         /* 底部对齐 */
    justify-content: space-around;  /* 均匀分布 */
    height: 220px;                 /* 固定高度 */
    gap: 0.75rem;
    padding: 1rem 0.5rem;
}

/**
 * 单个柱子包装器
 */
.chart-bar-wrapper {
    flex: 1;                       /* 自适应宽度 */
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}

/**
 * 柱子容器
 */
.chart-bar-container {
    width: 100%;
    height: 160px;                 /* 柱子区域高度 */
    display: flex;
    align-items: flex-end;         /* 底部对齐 */
    justify-content: center;
}

/**
 * 柱子本体
 * 特点：渐变色、圆角顶部、动态高度、阴影
 */
.chart-bar {
    width: 100%;
    min-height: 30px;              /* 最小高度（即使数据为0） */
    background: linear-gradient(180deg, #3b82f6, #1e40af);  /* 蓝色渐变 */
    border-radius: 8px 8px 0 0;    /* 仅顶部圆角 */
    position: relative;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);  /* 缓动函数 */
    display: flex;
    align-items: flex-start;       /* 顶部对齐 */
    justify-content: center;
    padding-top: 0.5rem;
    box-shadow: 0 -2px 10px rgba(59, 130, 246, 0.3);  /* 上方阴影（发光） */
}

/**
 * 柱子悬停效果
 * 效果：放大、增强发光
 */
.chart-bar:hover {
    filter: brightness(1.3);       /* 亮度增加30% */
    transform: scaleY(1.08) scaleX(1.05);  /* Y轴放大8%，X轴放大5% */
    box-shadow: 0 -4px 20px rgba(59, 130, 246, 0.5);  /* 增强阴影 */
}

/**
 * 柱子数值标签
 */
.bar-value {
    color: white;
    font-weight: 700;
    font-size: 0.875rem;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);  /* 文字阴影 */
}

/**
 * 日期标签
 */
.chart-label {
    color: var(--gray-400);
    font-size: 0.8125rem;          /* 13px */
    text-align: center;
    font-weight: 500;
}
```

---

## 9. 排行榜样式

```css
/**
 * 排行榜列表
 */
.class-list {
    display: grid;
    gap: 0.75rem;
}

/**
 * 排行榜单项
 * 特点：左侧彩色边框、悬停右移
 */
.class-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem;
    background: linear-gradient(90deg, rgba(15, 23, 42, 0.6), rgba(30, 41, 59, 0.4));
    border: 1px solid rgba(71, 85, 105, 0.3);
    border-left: 3px solid var(--primary-color);  /* 左侧彩色边框 */
    border-radius: 10px;
    transition: all 0.3s ease;
}

/**
 * 排行榜项悬停效果
 */
.class-item:hover {
    border-left-color: #10b981;    /* 边框变绿 */
    transform: translateX(5px);    /* 右移5px */
    background: linear-gradient(90deg, rgba(59, 130, 246, 0.1), rgba(30, 41, 59, 0.6));
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

/**
 * 类别名称
 */
.class-name {
    font-weight: 600;
    font-size: 0.9375rem;
    color: var(--gray-200);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/**
 * 计数徽章
 * 样式：圆角、渐变背景、阴影
 */
.class-count {
    background: linear-gradient(135deg, #3b82f6, #1e40af);
    color: white;
    padding: 0.375rem 0.875rem;
    border-radius: 20px;           /* 圆角胶囊形状 */
    font-size: 0.875rem;
    font-weight: 700;
    min-width: 40px;               /* 最小宽度 */
    text-align: center;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);  /* 阴影 */
}
```

---

## 10. 通知系统样式

```css
/**
 * 通知容器
 * 位置：固定右上角
 */
.notification-container {
    position: fixed;
    top: 100px;                    /* 距顶部100px（导航栏下方） */
    right: 20px;
    z-index: 9999;                 /* 最高层级 */
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

/**
 * 单个通知
 * 样式：卡片、阴影、过渡动画
 */
.notification {
    background: var(--card-gradient);
    border-radius: var(--radius-md);
    padding: 1rem 1.5rem;
    min-width: 300px;
    max-width: 400px;
    box-shadow: var(--shadow-xl);
    border-left: 4px solid;        /* 左侧彩色边框 */
    opacity: 0;                    /* 初始透明（淡入效果） */
    transform: translateX(20px);   /* 初始右移（滑入效果） */
    transition: all 0.3s ease;
}

/**
 * 不同类型的通知颜色
 */
.notification.success {
    border-left-color: var(--success-color);  /* 绿色 */
}

.notification.error {
    border-left-color: var(--danger-color);   /* 红色 */
}

.notification.warning {
    border-left-color: var(--warning-color);  /* 橙色 */
}

.notification.info {
    border-left-color: var(--info-color);     /* 紫色 */
}

/**
 * 通知内容布局
 */
.notification-content {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
}

/**
 * 通知图标
 */
.notification-icon {
    font-size: 1.5rem;
}

.notification.success .notification-icon {
    color: var(--success-color);
}

.notification.error .notification-icon {
    color: var(--danger-color);
}

/**
 * 通知文字
 */
.notification-text h4 {
    margin-bottom: 0.25rem;
    font-size: 1rem;
    font-weight: 600;
    color: var(--gray-100);
}

.notification-text p {
    font-size: 0.875rem;
    color: var(--gray-400);
}
```

---

## 11. 响应式设计

```css
/**
 * 平板设备（768px - 1024px）
 */
@media (max-width: 1024px) {
    /* 统计卡片改为2列 */
    .stats-overview {
        grid-template-columns: repeat(2, 1fr);
    }
    
    /* 检测区域改为单列 */
    .detect-content {
        grid-template-columns: 1fr;
    }
    
    /* 导航链接间距减小 */
    .nav-links {
        gap: 1rem;
    }
}

/**
 * 手机设备（<768px）
 */
@media (max-width: 768px) {
    /* Hero标题字号减小 */
    .hero-title {
        font-size: 2.5rem;
    }
    
    /* 统计卡片改为1列 */
    .stats-overview {
        grid-template-columns: 1fr;
    }
    
    /* 按钮改为竖向排列 */
    .hero-buttons {
        flex-direction: column;
        width: 100%;
    }
    
    /* 导航栏改为汉堡菜单（可选实现） */
    .nav-links {
        display: none;  /* 默认隐藏 */
    }
}
```

---

## 12. 动画效果

```css
/**
 * 淡入动画（用于section切换）
 */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.section.active {
    animation: fadeIn 0.5s ease;
}

/**
 * 脉冲动画（用于加载状态）
 */
@keyframes pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}

.loading {
    animation: pulse 1.5s infinite;
}

/**
 * 旋转动画（用于加载图标）
 */
@keyframes spin {
    from {
        transform: rotate(0deg);
    }
    to {
        transform: rotate(360deg);
    }
}

.fa-spinner {
    animation: spin 1s linear infinite;
}
```

---

**CSS文件总结**：
- **总行数**：约1400行
- **颜色变量**：30+
- **组件样式**：50+
- **动画效果**：10+
- **响应式断点**：2个
- **主题特色**：深色系、蓝色主调、毛玻璃效果、渐变色

这就是完整的CSS代码注释！所有关键样式都已详细说明。🎨✨

