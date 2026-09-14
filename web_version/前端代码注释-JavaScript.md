# 📘 前端JavaScript代码详细注释 - app.js

> 文件位置：`web_version/static/js/app.js`  
> 作者：project_user  
> 功能：实现前端交互逻辑、API调用、页面导航等

---

## 📋 目录

1. [全局变量](#1-全局变量)
2. [页面导航功能](#2-页面导航功能)
3. [文件上传与预览](#3-文件上传与预览)
4. [图片检测功能](#4-图片检测功能)
5. [视频检测功能](#5-视频检测功能)
6. [摄像头检测功能](#6-摄像头检测功能)
7. [历史记录功能](#7-历史记录功能)
8. [统计分析功能](#8-统计分析功能)
9. [通知系统](#9-通知系统)
10. [工具函数](#10-工具函数)

---

## 1. 全局变量

```javascript
// ==================== 全局变量定义 ====================

// 页面导航相关
let currentSection = 'home';  // 当前显示的页面section（home/detect/history/stats）

// 文件上传相关
let selectedFile = null;      // 用户选择的文件对象
let currentFileType = null;   // 当前文件类型（image/video）

// 摄像头相关
let cameraActive = false;     // 摄像头是否激活
let cameraInterval = null;    // 摄像头轮询定时器

// 视频检测相关
let videoProcessing = false;  // 视频是否正在处理
let videoInterval = null;     // 视频帧轮询定时器

// 历史记录分页
let currentPage = 1;          // 当前页码
let totalPages = 1;           // 总页数
```

---

## 2. 页面导航功能

```javascript
/**
 * 页面导航函数
 * 功能：切换不同的section页面（SPA单页应用）
 * 
 * @param {string} sectionId - 目标section的ID（home/detect/history/stats）
 * 
 * 流程：
 * 1. 隐藏所有section
 * 2. 移除所有导航链接的active类
 * 3. 显示目标section
 * 4. 高亮目标导航链接
 * 5. 更新全局状态
 * 6. 触发特定section的初始化逻辑
 */
function navigateToSection(sectionId) {
    // === 步骤1: 隐藏所有section ===
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // === 步骤2: 移除所有active类 ===
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // === 步骤3: 显示目标section ===
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // === 步骤4: 高亮导航链接 ===
    const targetLink = document.querySelector(`[href="#${sectionId}"]`);
    if (targetLink) {
        targetLink.classList.add('active');
    }
    
    // === 步骤5: 更新全局状态 ===
    currentSection = sectionId;
    
    // === 步骤6: section特定逻辑 ===
    if (sectionId === 'history') {
        // 进入历史记录页面时加载数据
        loadHistory();
    } else if (sectionId === 'stats') {
        // 进入统计页面时加载统计数据
        loadStats();
    }
}

// 导航链接点击事件监听
document.addEventListener('DOMContentLoaded', function() {
    /**
     * 为所有导航链接添加点击事件
     * 使用事件委托模式，在nav-links容器上监听
     */
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();  // 阻止默认的锚点跳转行为
            const sectionId = this.getAttribute('href').substring(1);  // 获取section ID（去掉#）
            navigateToSection(sectionId);
        });
    });
});
```

---

## 3. 文件上传与预览

```javascript
/**
 * 文件输入变化事件处理
 * 触发时机：用户通过文件选择器选择文件后
 * 
 * 功能：
 * 1. 获取选择的文件
 * 2. 验证文件大小（最小1KB）
 * 3. 判断文件类型（图片/视频）
 * 4. 预览文件
 * 5. 显示对应的检测按钮
 */
document.getElementById('fileInput').addEventListener('change', function(e) {
    const file = e.target.files[0];  // 获取第一个文件
    
    if (!file) {
        // 用户取消选择
        return;
    }
    
    // === 文件大小验证 ===
    if (file.size < 1024) {  // 小于1KB
        showNotification('错误', '文件太小，请选择有效的文件', 'error');
        return;
    }
    
    // === 保存文件引用 ===
    selectedFile = file;
    
    // === 判断文件类型 ===
    const fileType = file.type;
    if (fileType.startsWith('image/')) {
        currentFileType = 'image';
        previewImage(file);  // 预览图片
        showDetectButton('image');  // 显示图片检测按钮
    } else if (fileType.startsWith('video/')) {
        currentFileType = 'video';
        previewVideo(file);  // 预览视频
        showDetectButton('video');  // 显示视频检测按钮
    } else {
        showNotification('错误', '不支持的文件格式', 'error');
        selectedFile = null;
        currentFileType = null;
    }
});

/**
 * 图片预览函数
 * 
 * @param {File} file - 图片文件对象
 * 
 * 功能：
 * 1. 使用FileReader读取文件内容
 * 2. 创建预览元素
 * 3. 显示在预览区域
 */
function previewImage(file) {
    const reader = new FileReader();
    
    // 文件读取完成后的回调
    reader.onload = function(e) {
        const previewContainer = document.getElementById('filePreview');
        
        // 清空预览区域
        previewContainer.innerHTML = `
            <div class="preview-content">
                <div class="preview-header">
                    <h3><i class="fas fa-image"></i> 图片预览</h3>
                    <span class="file-info">${file.name} (${formatFileSize(file.size)})</span>
                </div>
                <img src="${e.target.result}" alt="预览图片">
            </div>
        `;
    };
    
    // 以DataURL格式读取文件（Base64编码）
    reader.readAsDataURL(file);
}

/**
 * 视频预览函数
 * 
 * @param {File} file - 视频文件对象
 * 
 * 功能：
 * 1. 使用URL.createObjectURL创建临时URL
 * 2. 创建video元素
 * 3. 显示在预览区域
 */
function previewVideo(file) {
    const videoUrl = URL.createObjectURL(file);  // 创建临时URL
    const previewContainer = document.getElementById('filePreview');
    
    previewContainer.innerHTML = `
        <div class="preview-content">
            <div class="preview-header">
                <h3><i class="fas fa-video"></i> 视频预览</h3>
                <span class="file-info">${file.name} (${formatFileSize(file.size)})</span>
            </div>
            <video controls>
                <source src="${videoUrl}" type="${file.type}">
                您的浏览器不支持视频播放。
            </video>
        </div>
    `;
}

/**
 * 显示检测按钮
 * 
 * @param {string} type - 文件类型（'image' 或 'video'）
 * 
 * 功能：
 * - 隐藏所有检测按钮
 * - 显示对应类型的检测按钮
 */
function showDetectButton(type) {
    // 隐藏所有检测按钮
    document.getElementById('detectImageBtn').style.display = 'none';
    document.getElementById('detectVideoBtn').style.display = 'none';
    
    // 显示对应按钮
    if (type === 'image') {
        document.getElementById('detectImageBtn').style.display = 'inline-flex';
    } else if (type === 'video') {
        document.getElementById('detectVideoBtn').style.display = 'inline-flex';
    }
}

/**
 * 文件大小格式化函数
 * 
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的文件大小（如：1.5 MB）
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}
```

---

## 4. 图片检测功能

```javascript
/**
 * 图片检测按钮点击事件
 * 
 * 功能：
 * 1. 验证文件选择
 * 2. 创建FormData
 * 3. 调用检测API
 * 4. 显示检测结果
 * 5. 保存到历史记录
 */
document.getElementById('detectImageBtn').addEventListener('click', async function() {
    // === 步骤1: 前置验证 ===
    if (!selectedFile) {
        showNotification('错误', '请先选择图片文件', 'error');
        return;
    }
    
    // === 步骤2: 显示加载状态 ===
    this.disabled = true;  // 禁用按钮防止重复点击
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 检测中...';
    
    try {
        // === 步骤3: 构建FormData ===
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        // === 步骤4: 调用检测API ===
        const response = await fetch('/api/detect/image', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // === 步骤5: 处理响应 ===
        if (data.success) {
            // 显示检测结果
            showDetectionResult(data);
            
            // 成功提示
            showNotification('成功', '图片检测完成', 'success');
            
            // 延迟刷新历史记录（等待数据库commit）
            setTimeout(loadHistory, 500);
        } else {
            // 错误提示
            showNotification('错误', data.error || '检测失败', 'error');
        }
    } catch (error) {
        // 网络或其他错误
        console.error('检测失败:', error);
        showNotification('错误', '网络请求失败，请重试', 'error');
    } finally {
        // === 步骤6: 恢复按钮状态 ===
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-camera"></i> 检测图片';
    }
});

/**
 * 显示检测结果函数
 * 
 * @param {Object} data - API返回的检测结果数据
 * @param {Object} data.results - 检测结果对象
 * @param {number} data.detection_time - 检测耗时
 * @param {string} data.result_image - Base64编码的结果图片
 * 
 * 功能：
 * 1. 更新检测信息面板
 * 2. 显示结果图片
 * 3. 显示边界框坐标
 */
function showDetectionResult(data) {
    const results = data.results;
    
    // === 更新检测信息卡片 ===
    document.getElementById('objectCount').textContent = results.object_count || 0;
    document.getElementById('mainClass').textContent = results.main_class || '-';
    document.getElementById('confidence').textContent = 
        results.confidence ? (results.confidence * 100).toFixed(1) + '%' : '0%';
    document.getElementById('detectionTime').textContent = 
        data.detection_time ? data.detection_time.toFixed(2) + ' ms' : '0 ms';
    
    // === 更新边界框坐标（始终显示，无数据时显示'-'）===
    if (results.bbox) {
        document.getElementById('bboxX1').textContent = results.bbox.x1;
        document.getElementById('bboxY1').textContent = results.bbox.y1;
        document.getElementById('bboxX2').textContent = results.bbox.x2;
        document.getElementById('bboxY2').textContent = results.bbox.y2;
    } else {
        // 无检测结果时显示占位符
        document.getElementById('bboxX1').textContent = '-';
        document.getElementById('bboxY1').textContent = '-';
        document.getElementById('bboxX2').textContent = '-';
        document.getElementById('bboxY2').textContent = '-';
    }
    
    // 确保边界框信息始终显示
    document.getElementById('bboxInfo').style.display = 'block';
    
    // === 显示结果图片 ===
    if (data.result_image) {
        const resultImage = document.getElementById('resultImage');
        const resultImg = document.getElementById('resultImg');
        
        // 设置图片源（Base64）
        resultImg.src = 'data:image/jpeg;base64,' + data.result_image;
        
        // 显示结果容器
        resultImage.style.display = 'block';
    }
}
```

---

## 5. 视频检测功能

```javascript
/**
 * 视频检测按钮点击事件
 * 
 * 功能：
 * 1. 上传视频文件
 * 2. 启动后台视频处理
 * 3. 开始轮询获取检测帧
 * 4. 实时显示检测结果
 */
document.getElementById('detectVideoBtn').addEventListener('click', async function() {
    // === 步骤1: 前置验证 ===
    if (!selectedFile) {
        showNotification('错误', '请先选择视频文件', 'error');
        return;
    }
    
    // === 步骤2: 显示加载状态 ===
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 启动中...';
    
    try {
        // === 步骤3: 上传视频文件 ===
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        const response = await fetch('/api/detect/video', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // === 步骤4: 启动视频播放 ===
            startVideoPlayback();
            
            showNotification('成功', '视频处理已启动', 'success');
        } else {
            showNotification('错误', data.error || '视频处理失败', 'error');
        }
    } catch (error) {
        console.error('视频检测失败:', error);
        showNotification('错误', '网络请求失败，请重试', 'error');
    } finally {
        // 恢复按钮状态
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-video"></i> 播放视频';
    }
});

/**
 * 启动视频播放和检测显示
 * 
 * 功能：
 * 1. 设置全局状态
 * 2. 显示结果区域
 * 3. 启动帧轮询
 * 4. 显示停止按钮
 */
function startVideoPlayback() {
    // === 步骤1: 设置全局状态 ===
    videoProcessing = true;
    
    // === 步骤2: 显示结果区域 ===
    const resultImage = document.getElementById('resultImage');
    resultImage.style.display = 'block';
    
    // === 步骤3: 启动帧轮询（每50ms获取一帧，20FPS）===
    startVideoFrameLoop();
    
    // === 步骤4: 显示停止按钮（带动画效果）===
    const stopBtn = document.getElementById('stopVideoBtn');
    if (!stopBtn) {
        // 动态创建停止按钮
        const buttonContainer = document.querySelector('.button-container');
        const btn = document.createElement('button');
        btn.id = 'stopVideoBtn';
        btn.className = 'btn btn-danger';
        btn.innerHTML = '<i class="fas fa-stop"></i> 停止视频';
        btn.onclick = stopVideoPlayback;
        buttonContainer.appendChild(btn);
        
        // 触发淡入动画
        setTimeout(() => btn.style.opacity = '1', 10);
    } else {
        stopBtn.style.display = 'inline-flex';
    }
}

/**
 * 视频帧轮询循环
 * 
 * 功能：
 * - 定时调用 /api/video/frame 获取最新帧
 * - 更新显示区域
 * - 自动循环直到视频结束或手动停止
 */
function startVideoFrameLoop() {
    // 清除之前的定时器
    if (videoInterval) {
        clearInterval(videoInterval);
    }
    
    // 设置新的轮询定时器（50ms间隔，20FPS）
    videoInterval = setInterval(async () => {
        if (!videoProcessing) {
            // 停止标志已设置，清除定时器
            clearInterval(videoInterval);
            return;
        }
        
        try {
            // 获取当前帧
            const response = await fetch('/api/video/frame');
            const data = await response.json();
            
            if (data.success && data.result_image) {
                // 更新图片显示
                const resultImg = document.getElementById('resultImg');
                resultImg.src = 'data:image/jpeg;base64,' + data.result_image;
                
                // 更新检测信息
                updateVideoDetectionInfo(data);
            }
        } catch (error) {
            console.error('获取视频帧失败:', error);
        }
    }, 50);  // 50ms = 20FPS
}

/**
 * 更新视频检测信息
 * 
 * @param {Object} data - 帧数据
 * 
 * 功能：与图片检测类似，更新检测信息面板
 */
function updateVideoDetectionInfo(data) {
    if (!data.results) return;
    
    const results = data.results;
    
    // 更新检测信息
    document.getElementById('objectCount').textContent = results.object_count || 0;
    document.getElementById('mainClass').textContent = results.main_class || '-';
    document.getElementById('confidence').textContent = 
        results.confidence ? (results.confidence * 100).toFixed(1) + '%' : '0%';
    document.getElementById('detectionTime').textContent = 
        data.detection_time ? data.detection_time.toFixed(2) + ' ms' : '0 ms';
    
    // 更新边界框坐标（始终显示）
    if (results.bbox) {
        document.getElementById('bboxX1').textContent = results.bbox.x1;
        document.getElementById('bboxY1').textContent = results.bbox.y1;
        document.getElementById('bboxX2').textContent = results.bbox.x2;
        document.getElementById('bboxY2').textContent = results.bbox.y2;
    } else {
        document.getElementById('bboxX1').textContent = '-';
        document.getElementById('bboxY1').textContent = '-';
        document.getElementById('bboxX2').textContent = '-';
        document.getElementById('bboxY2').textContent = '-';
    }
    
    document.getElementById('bboxInfo').style.display = 'block';
}

/**
 * 停止视频播放
 * 
 * 功能：
 * 1. 清除轮询定时器
 * 2. 调用停止API
 * 3. 重置UI状态
 */
async function stopVideoPlayback() {
    // === 步骤1: 设置停止标志 ===
    videoProcessing = false;
    
    // === 步骤2: 清除定时器 ===
    if (videoInterval) {
        clearInterval(videoInterval);
        videoInterval = null;
    }
    
    try {
        // === 步骤3: 调用停止API ===
        const response = await fetch('/api/video/stop', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('成功', '视频已停止', 'success');
        }
    } catch (error) {
        console.error('停止视频失败:', error);
    }
    
    // === 步骤4: 隐藏停止按钮 ===
    const stopBtn = document.getElementById('stopVideoBtn');
    if (stopBtn) {
        stopBtn.style.display = 'none';
    }
}
```

---

## 6. 摄像头检测功能

```javascript
/**
 * 启动摄像头按钮点击事件
 * 
 * 功能：
 * 1. 调用启动API
 * 2. 开始帧轮询
 * 3. 切换按钮状态
 */
document.getElementById('startCameraBtn').addEventListener('click', async function() {
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 启动中...';
    
    try {
        // === 调用启动API ===
        const response = await fetch('/api/camera/start', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // === 启动成功 ===
            cameraActive = true;
            
            // 显示摄像头区域
            document.getElementById('cameraSection').style.display = 'block';
            
            // 启动帧轮询（16ms = 60FPS）
            startCameraLoop();
            
            // 切换按钮
            this.style.display = 'none';
            document.getElementById('stopCameraBtn').style.display = 'inline-flex';
            
            showNotification('成功', '摄像头已启动', 'success');
        } else {
            showNotification('错误', data.error || '摄像头启动失败', 'error');
        }
    } catch (error) {
        console.error('启动摄像头失败:', error);
        showNotification('错误', '网络请求失败，请重试', 'error');
    } finally {
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-webcam"></i> 启动摄像头';
    }
});

/**
 * 摄像头帧轮询循环
 * 
 * 功能：
 * - 定时调用 /api/camera/frame
 * - 实时显示摄像头画面和检测结果
 * - 60FPS刷新率
 */
function startCameraLoop() {
    // 清除之前的定时器
    if (cameraInterval) {
        clearInterval(cameraInterval);
    }
    
    // 设置新的轮询定时器（16ms ≈ 60FPS）
    cameraInterval = setInterval(async () => {
        if (!cameraActive) {
            clearInterval(cameraInterval);
            return;
        }
        
        try {
            const response = await fetch('/api/camera/frame');
            const data = await response.json();
            
            if (data.success && data.result_image) {
                // 更新摄像头画面
                const cameraImg = document.getElementById('cameraImg');
                cameraImg.src = 'data:image/jpeg;base64,' + data.result_image;
                
                // 更新检测信息
                updateCameraDetectionInfo(data);
            } else if (data.error) {
                // 发生错误，停止摄像头
                console.error('摄像头错误:', data.error);
                stopCamera();
            }
        } catch (error) {
            console.error('获取摄像头画面失败:', error);
        }
    }, 16);  // 16ms ≈ 60FPS
}

/**
 * 更新摄像头检测信息
 * 
 * @param {Object} data - 帧数据
 * 
 * 功能：与图片/视频检测类似
 */
function updateCameraDetectionInfo(data) {
    if (!data.results) return;
    
    const results = data.results;
    
    document.getElementById('objectCount').textContent = results.object_count || 0;
    document.getElementById('mainClass').textContent = results.main_class || '-';
    document.getElementById('confidence').textContent = 
        results.confidence ? (results.confidence * 100).toFixed(1) + '%' : '0%';
    document.getElementById('detectionTime').textContent = 
        data.detection_time ? data.detection_time.toFixed(2) + ' ms' : '0 ms';
    
    // 边界框坐标（始终显示）
    if (results.bbox) {
        document.getElementById('bboxX1').textContent = results.bbox.x1;
        document.getElementById('bboxY1').textContent = results.bbox.y1;
        document.getElementById('bboxX2').textContent = results.bbox.x2;
        document.getElementById('bboxY2').textContent = results.bbox.y2;
    } else {
        document.getElementById('bboxX1').textContent = '-';
        document.getElementById('bboxY1').textContent = '-';
        document.getElementById('bboxX2').textContent = '-';
        document.getElementById('bboxY2').textContent = '-';
    }
    
    document.getElementById('bboxInfo').style.display = 'block';
}

/**
 * 停止摄像头按钮点击事件
 * 
 * 功能：
 * 1. 停止帧轮询
 * 2. 延迟200ms等待飞行中的请求
 * 3. 调用停止API
 * 4. 重置UI状态
 */
document.getElementById('stopCameraBtn').addEventListener('click', async function() {
    this.disabled = true;
    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 停止中...';
    
    // === 步骤1: 设置停止标志 ===
    cameraActive = false;
    
    // === 步骤2: 清除定时器 ===
    if (cameraInterval) {
        clearInterval(cameraInterval);
        cameraInterval = null;
    }
    
    // === 步骤3: 等待飞行中的请求完成 ===
    await new Promise(resolve => setTimeout(resolve, 200));
    
    try {
        // === 步骤4: 调用停止API ===
        const response = await fetch('/api/camera/stop', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('成功', '摄像头已停止', 'success');
            
            // 隐藏摄像头区域
            document.getElementById('cameraSection').style.display = 'none';
            
            // 切换按钮
            this.style.display = 'none';
            document.getElementById('startCameraBtn').style.display = 'inline-flex';
        } else {
            showNotification('错误', data.error || '停止失败', 'error');
        }
    } catch (error) {
        console.error('停止摄像头失败:', error);
        showNotification('错误', '网络请求失败', 'error');
    } finally {
        this.disabled = false;
        this.innerHTML = '<i class="fas fa-stop"></i> 停止摄像头';
        
        // 强制重置状态（错误恢复）
        cameraActive = false;
    }
});

/**
 * 停止摄像头函数（内部调用）
 * 
 * 功能：程序化停止摄像头（用于错误恢复）
 */
function stopCamera() {
    cameraActive = false;
    if (cameraInterval) {
        clearInterval(cameraInterval);
        cameraInterval = null;
    }
    
    // 重置UI
    document.getElementById('cameraSection').style.display = 'none';
    document.getElementById('stopCameraBtn').style.display = 'none';
    document.getElementById('startCameraBtn').style.display = 'inline-flex';
}
```

---

## 7. 历史记录功能

```javascript
/**
 * 加载历史记录
 * 
 * @param {number} page - 页码，默认为当前页
 * 
 * 功能：
 * 1. 调用历史记录API
 * 2. 渲染记录列表
 * 3. 更新分页控件
 */
async function loadHistory(page = currentPage) {
    try {
        // === 调用API ===
        const response = await fetch(`/api/history?page=${page}&per_page=10`);
        const data = await response.json();
        
        if (data.success) {
            // === 更新全局分页状态 ===
            currentPage = data.pagination.page;
            totalPages = data.pagination.pages;
            
            // === 渲染历史记录 ===
            displayHistory(data.data);
            
            // === 更新分页控件 ===
            updatePagination(data.pagination);
        } else {
            // API返回错误
            document.getElementById('historyList').innerHTML = `
                <div class="error-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>加载失败: ${data.error}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
        document.getElementById('historyList').innerHTML = `
            <div class="error-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>网络错误，请稍后重试</p>
            </div>
        `;
    }
}

/**
 * 显示历史记录列表
 * 
 * @param {Array} records - 历史记录数组
 * 
 * 功能：
 * - 动态生成历史记录卡片HTML
 * - 处理空状态
 */
function displayHistory(records) {
    const historyList = document.getElementById('historyList');
    
    // === 空状态处理 ===
    if (!records || records.length === 0) {
        historyList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-inbox"></i>
                <p>暂无检测记录</p>
                <p>开始您的第一次检测吧！</p>
            </div>
        `;
        document.getElementById('pagination').style.display = 'none';
        return;
    }
    
    // === 生成记录卡片 ===
    historyList.innerHTML = records.map(record => `
        <div class="history-item">
            <!-- 时间戳 -->
            <div class="history-time">
                <i class="fas fa-clock"></i>
                ${formatDateTime(record.created_at)}
            </div>
            
            <!-- 文件信息 -->
            <div class="history-info">
                <div class="history-icon">
                    <i class="fas fa-${record.file_type === 'image' ? 'image' : 'video'}"></i>
                </div>
                <div class="history-details">
                    <h4>${record.original_filename}</h4>
                    <p>
                        类型: ${record.file_type} | 
                        大小: ${formatFileSize(record.file_size)} | 
                        耗时: ${record.detection_time.toFixed(2)} ms
                    </p>
                </div>
            </div>
            
            <!-- 检测结果 -->
            <div class="history-results">
                <span class="result-badge">
                    <i class="fas fa-hashtag"></i> 
                    ${record.object_count} 个对象
                </span>
                ${record.main_class ? `
                    <span class="result-badge">
                        <i class="fas fa-tag"></i> 
                        ${record.main_class}
                    </span>
                ` : ''}
                ${record.confidence > 0 ? `
                    <span class="result-badge">
                        <i class="fas fa-percentage"></i> 
                        ${(record.confidence * 100).toFixed(1)}%
                    </span>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // 显示分页
    document.getElementById('pagination').style.display = 'flex';
}

/**
 * 更新分页控件
 * 
 * @param {Object} pagination - 分页信息
 * @param {number} pagination.page - 当前页
 * @param {number} pagination.pages - 总页数
 * 
 * 功能：
 * - 生成页码按钮
 * - 高亮当前页
 * - 处理上一页/下一页
 */
function updatePagination(pagination) {
    const paginationContainer = document.getElementById('pagination');
    
    if (pagination.pages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    
    let html = '';
    
    // === 上一页按钮 ===
    html += `
        <button class="btn btn-secondary" 
                onclick="loadHistory(${pagination.page - 1})"
                ${pagination.page === 1 ? 'disabled' : ''}>
            上一页
        </button>
    `;
    
    // === 页码按钮（最多显示5个）===
    const maxButtons = 5;
    let startPage = Math.max(1, pagination.page - 2);
    let endPage = Math.min(pagination.pages, startPage + maxButtons - 1);
    
    // 调整起始页
    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `
            <button class="btn ${i === pagination.page ? 'btn-primary' : 'btn-secondary'}"
                    onclick="loadHistory(${i})">
                ${i}
            </button>
        `;
    }
    
    // === 下一页按钮 ===
    html += `
        <button class="btn btn-secondary"
                onclick="loadHistory(${pagination.page + 1})"
                ${pagination.page === pagination.pages ? 'disabled' : ''}>
            下一页
        </button>
    `;
    
    paginationContainer.innerHTML = html;
}

/**
 * 刷新历史记录按钮
 * 
 * 功能：重新加载当前页
 */
function refreshHistory() {
    loadHistory(currentPage);
}
```

---

## 8. 统计分析功能

```javascript
/**
 * 加载统计数据
 * 
 * 功能：
 * 1. 调用统计API
 * 2. 显示各种统计指标
 * 3. 绘制趋势图
 * 4. 显示排行榜
 */
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            displayStats(data.stats);
        } else {
            throw new Error(data.error || '加载统计数据失败');
        }
    } catch (error) {
        console.error('加载统计数据失败:', error);
        resetStatsDisplay();  // 显示默认值
    }
}

/**
 * 重置统计显示（显示默认值）
 * 
 * 功能：在加载失败时显示占位符
 */
function resetStatsDisplay() {
    // 核心指标
    document.getElementById('totalDetections').textContent = '0';
    document.getElementById('todayDetections').textContent = '0';
    document.getElementById('recentDetections').textContent = '0';
    document.getElementById('successRate').textContent = '0';
    
    // 类型分布
    document.getElementById('imageDetections').textContent = '0';
    document.getElementById('videoDetections').textContent = '0';
    document.getElementById('cameraDetections').textContent = '0';
    
    // 性能指标
    document.getElementById('successDetections').textContent = '0';
    document.getElementById('highestConfidence').textContent = '0';
    document.getElementById('topClass').textContent = '-';
}

/**
 * 显示统计数据
 * 
 * @param {Object} stats - 统计数据对象
 * 
 * 功能：
 * - 更新所有统计卡片
 * - 绘制趋势图
 * - 显示排行榜
 */
function displayStats(stats) {
    // === 核心指标 ===
    document.getElementById('totalDetections').textContent = stats.total_detections || 0;
    document.getElementById('todayDetections').textContent = stats.today_detections || 0;
    document.getElementById('recentDetections').textContent = stats.recent_detections || 0;
    document.getElementById('successRate').textContent = stats.success_rate || 0;
    
    // === 类型分布 ===
    document.getElementById('imageDetections').textContent = stats.image_detections || 0;
    document.getElementById('videoDetections').textContent = stats.video_detections || 0;
    document.getElementById('cameraDetections').textContent = stats.camera_detections || 0;
    
    // === 性能指标 ===
    document.getElementById('successDetections').textContent = stats.success_detections || 0;
    document.getElementById('highestConfidence').textContent = stats.highest_confidence?.confidence || 0;
    
    // === 热门类别 ===
    if (stats.top_classes && stats.top_classes.length > 0) {
        document.getElementById('topClass').textContent = stats.top_classes[0].class;
        displayTopClasses(stats.top_classes);
    } else {
        document.getElementById('topClass').textContent = '-';
        document.getElementById('classList').innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--gray-400);">
                <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.3;"></i>
                <p>暂无数据</p>
            </div>
        `;
    }
    
    // === 趋势图 ===
    if (stats.daily_trend && stats.daily_trend.length > 0) {
        displayTrendChart(stats.daily_trend);
    } else {
        document.getElementById('trendChart').innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--gray-400);">
                <i class="fas fa-chart-line" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.3;"></i>
                <p>暂无趋势数据</p>
            </div>
        `;
    }
}

/**
 * 显示类别排行榜
 * 
 * @param {Array} classes - 类别数组 [{class: str, count: int}]
 * 
 * 功能：
 * - 生成排行榜HTML
 * - 金银铜牌图标
 * - 渐变数字徽章
 */
function displayTopClasses(classes) {
    const classList = document.getElementById('classList');
    
    classList.innerHTML = classes.map((item, index) => `
        <div class="class-item">
            <span class="class-name">
                <i class="fas fa-medal" style="color: ${getColorByRank(index)}; margin-right: 0.5rem;"></i>
                ${item.class}
            </span>
            <span class="class-count">${item.count}</span>
        </div>
    `).join('');
}

/**
 * 根据排名获取颜色
 * 
 * @param {number} index - 排名索引（0-based）
 * @returns {string} 颜色代码
 * 
 * 金银铜牌配色：
 * - 0: 金色
 * - 1: 银色
 * - 2: 铜色
 * - 其他: 蓝色/绿色
 */
function getColorByRank(index) {
    const colors = ['#ffd700', '#c0c0c0', '#cd7f32', '#3b82f6', '#10b981'];
    return colors[index] || '#64748b';
}

/**
 * 显示趋势图
 * 
 * @param {Array} trendData - 趋势数据 [{date: str, count: int}]
 * 
 * 功能：
 * - 绘制柱状图
 * - 动态高度计算
 * - 悬停效果
 */
function displayTrendChart(trendData) {
    const chartContainer = document.getElementById('trendChart');
    
    if (!trendData || trendData.length === 0) {
        chartContainer.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--gray-400);">
                <p>暂无数据</p>
            </div>
        `;
        return;
    }
    
    // === 计算最大值（用于比例）===
    const maxCount = Math.max(...trendData.map(d => d.count), 1);
    
    // === 生成柱状图HTML ===
    chartContainer.innerHTML = `
        <div class="chart-bars">
            ${trendData.map(item => {
                const height = (item.count / maxCount) * 100;  // 百分比高度
                return `
                    <div class="chart-bar-wrapper">
                        <div class="chart-bar-container">
                            <div class="chart-bar" style="height: ${height}%;">
                                <span class="bar-value">${item.count}</span>
                            </div>
                        </div>
                        <div class="chart-label">${item.date}</div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}
```

---

## 9. 通知系统

```javascript
/**
 * 显示通知
 * 
 * @param {string} title - 通知标题
 * @param {string} message - 通知内容
 * @param {string} type - 通知类型（success/error/warning/info）
 * 
 * 功能：
 * 1. 创建通知元素
 * 2. 显示动画
 * 3. 3秒后自动消失
 */
function showNotification(title, message, type = 'info') {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    
    // === 图标映射 ===
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    
    // === 生成HTML ===
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <div class="notification-icon">
                <i class="${icons[type] || icons.info}"></i>
            </div>
            <div class="notification-text">
                <h4>${title}</h4>
                <p>${message}</p>
            </div>
        </div>
    `;
    
    // === 添加到容器 ===
    container.appendChild(notification);
    
    // === 触发淡入动画 ===
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // === 3秒后自动移除 ===
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(20px)';
        
        // 等待动画结束后移除DOM
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}
```

---

## 10. 工具函数

```javascript
/**
 * 格式化日期时间
 * 
 * @param {string} isoString - ISO格式时间字符串
 * @returns {string} 格式化后的时间（YYYY-MM-DD HH:mm:ss）
 */
function formatDateTime(isoString) {
    const date = new Date(isoString);
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}
```

---

**总代码行数**：约1000行  
**核心功能模块**：10个  
**API调用**：12个接口  
**事件监听器**：15+  

这就是完整的JavaScript代码注释！🎉

