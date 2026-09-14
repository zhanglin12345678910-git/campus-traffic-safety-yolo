// ==================== 全局变量 ====================
let currentSection = 'home';
let currentFile = null;
let currentPage = 1;
let isDetecting = false;
let cameraActive = false;
let cameraInterval = null;
let cameraAbortController = null;  // 用于中断摄像头请求
let cameraRequestInProgress = false;  // 防止请求堆积
let videoProcessing = false;
let videoInterval = null;

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    checkHealth();
});

function initializeApp() {
    // 设置默认显示的部分
    switchSection('home');
    
    // 加载统计数据
    loadStats();
    
    // 加载历史记录
    loadHistory();

    // 加载模型列表
    loadModels();
}

// ==================== 模型管理 ====================
// 模型显示名称映射（用于更友好的展示）
const MODEL_DISPLAY_NAMES = {
    'PSSM-YOLO': '🏆 PSSM-YOLO (自研改进)',
    'YOLOv11n': '⚡ YOLOv11n (超轻量)',
    'YOLOv10n': '🎯 YOLOv10n (实时检测)',
    'YOLOv9t': '🚀 YOLOv9t (高精度)',
    'YOLOv8n': '💎 YOLOv8n (经典)',
    'YOLOv7-tiny': '⚙️ YOLOv7-tiny (紧凑)',
    'YOLOv5n': '🔧 YOLOv5n (稳定)',
    'YOLO-NAS-s': '🤖 YOLO-NAS-s (神经架构搜索)',
    'RT-DETR': '🎪 RT-DETR (实时检测器)',
    'YOLO-FastestV2': '💨 YOLO-FastestV2 (极速)',
    'PP-YOLOE+': '🐼 PP-YOLOE+ (PaddlePaddle)'
};

// 模型详细描述
const MODEL_DESCRIPTIONS = {
    'PSSM-YOLO': '基于YOLOv11改进的自研模型，采用PMSFA注意力机制和CSP结构，在交通标志检测上达到最佳平衡',
    'YOLOv11n': 'Ultralytics最新YOLO版本的纳米模型，速度与精度平衡优秀，支持分类/检测/分割/姿态多任务',
    'YOLOv10n': '清华大学2024年发布，首个端到端YOLO，消除NMS需求，推理效率大幅提升',
    'YOLOv9t': '台湾中研院2024年力作，引入PGI和GELAN架构，训练效率和检测精度显著提升',
    'YOLOv8n': 'Ultralytics 2023年旗舰作品，工业部署首选，模型轻量、精度高、生态完善',
    'YOLOv7-tiny': '2022年COCO冠军YOLOv7的轻量版，E-ELAN架构，训练策略先进，性能卓越',
    'YOLOv5n': 'Glenn Jocher 2020年经典之作，成熟稳定，社区庞大，是学习和部署的最佳入门选择',
    'YOLO-NAS-s': 'Deci AI基于AutoNAC技术自动搜索的架构，量化友好，在边缘设备上性能优异',
    'RT-DETR': '百度2023年提出的实时DETR检测器，首个实用化Transformer检测器，精度速度俱佳',
    'YOLO-FastestV2': '国内开源超轻量模型，模型仅0.25MB，专为MCU和移动端设计，适合嵌入式场景',
    'PP-YOLOE+': '百度飞桨2022年发布，融合多种SOTA技术，无Anchor设计，工业部署性能出色'
};

// 全局变量：防止重复绑定事件
let modelSelectHandlerBound = false;

async function loadModels() {
    try {
        const response = await fetch('/api/models');
        const data = await response.json();

        if (data.success) {
            let select = document.getElementById('modelSelect');
            if (!select) return;

            // 先移除旧的事件监听器（如果存在）
            if (modelSelectHandlerBound) {
                const newSelect = select.cloneNode(false);
                select.parentNode.replaceChild(newSelect, select);
                select = newSelect;
                modelSelectHandlerBound = false; // 重置标志
            }

            select.innerHTML = '';

            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.model_id;
                
                // 使用友好的显示名称
                const displayName = MODEL_DISPLAY_NAMES[model.model_id] || model.model_id;
                const statusBadge = model.is_active ? ' ✓ 当前使用' : '';
                const existsBadge = !model.exists ? ' ⚠️ 文件缺失' : '';
                
                option.textContent = `${displayName}${statusBadge}${existsBadge}`;
                
                if (model.is_active) {
                    option.selected = true;
                    // 显示当前模型信息
                    showModelInfo(model.model_id);
                }
                
                // 如果文件不存在，禁用该选项
                if (!model.exists) {
                    option.disabled = true;
                    option.style.color = '#999';
                }
                
                select.appendChild(option);
            });

            // 只绑定一次事件监听器
            if (!modelSelectHandlerBound) {
                const modelSelectHandler = async (e) => {
                    const modelId = e.target.value;
                    
                    // 显示模型信息
                    showModelInfo(modelId);
                    
                    try {
                        showNotification('切换中', `正在切换到模型: ${MODEL_DISPLAY_NAMES[modelId] || modelId}...`, 'info');
                        
                        // 通知后端切换默认模型
                        const response = await fetch('/api/models/active', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ model_id: modelId })
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            console.log('模型已切换为:', modelId);
                            showNotification('成功', `已切换到: ${MODEL_DISPLAY_NAMES[modelId] || modelId}`, 'success');
                            // 不再重新加载模型列表，避免递归绑定
                        } else {
                            throw new Error(result.error || '切换失败');
                        }
                    } catch (error) {
                        console.error('切换模型失败:', error);
                        showNotification('错误', `模型切换失败: ${error.message}`, 'error');
                    }
                };
                
                document.getElementById('modelSelect').addEventListener('change', modelSelectHandler);
                modelSelectHandlerBound = true;
            }
        }
    } catch (error) {
        console.error('加载模型列表失败:', error);
        showNotification('错误', '无法加载模型列表', 'error');
    }
}

// 显示模型信息
function showModelInfo(modelId) {
    const infoPanel = document.getElementById('modelInfo');
    const infoText = document.getElementById('modelInfoText');
    
    if (infoPanel && infoText) {
        const description = MODEL_DESCRIPTIONS[modelId] || '暂无模型描述';
        infoText.textContent = description;
        infoPanel.style.display = 'block';
    }
}

// ==================== 事件监听器 ====================
function setupEventListeners() {
    // 导航链接
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.getAttribute('data-section');
            switchSection(section);
        });
    });
    
    // 文件上传
    const fileInput = document.getElementById('fileInput');
    const uploadArea = document.getElementById('uploadArea');
    
    fileInput.addEventListener('change', handleFileSelect);
    
    // 拖拽上传
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
    
    // 点击上传区域 - 修复重复弹窗问题
    uploadArea.addEventListener('click', (e) => {
        // 防止事件冒泡和重复触发
        if (e.target === fileInput || isDetecting) {
            return;
        }
        fileInput.click();
    });
}

// ==================== 导航功能 ====================
function switchSection(sectionName) {
    // 隐藏所有部分
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // 显示目标部分
    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
    }
    
    // 更新导航链接状态
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.querySelector(`[data-section="${sectionName}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
    
    currentSection = sectionName;
    
    // 根据不同部分执行特定操作
    switch(sectionName) {
        case 'history':
            loadHistory();
            break;
        case 'stats':
            loadStats();
            break;
    }
}

// ==================== 健康检查 ====================
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();
        
        if (data.status === 'ok') {
            // 多模型系统使用懒加载，不需要在启动时检查模型是否已加载
            // 只在没有可用模型配置时才警告
            if (!data.available_models || data.available_models.length === 0) {
                showNotification('警告', '未配置任何检测模型', 'warning');
            }
        } else {
            showNotification('错误', '服务器连接失败', 'error');
        }
    } catch (error) {
        console.error('健康检查失败:', error);
        showNotification('错误', '无法连接到服务器', 'error');
    }
}

// ==================== 文件处理 ====================
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        handleFile(file);
    }
}

function handleFile(file) {
    // 检查文件类型
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 
                         'video/mp4', 'video/avi', 'video/mov', 'video/mkv'];
    
    if (!allowedTypes.includes(file.type)) {
        showNotification('错误', '不支持的文件格式', 'error');
        return;
    }
    
    // 取消文件大小限制 - 根据用户要求
    // 只保留合理性检查，防止过小的无效文件
    if (file.size < 1024) {  // 小于1KB的文件可能无效
        showNotification('错误', '文件太小，请选择有效的图片或视频文件', 'error');
        return;
    }
    
    currentFile = file;
    showFilePreview(file);
}

function showFilePreview(file) {
    const preview = document.getElementById('filePreview');
    const previewImage = document.getElementById('previewImage');
    const previewVideo = document.getElementById('previewVideo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    
    // 显示文件信息
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    
    // 创建文件URL
    const fileURL = URL.createObjectURL(file);
    
    // 根据文件类型显示预览
    if (file.type.startsWith('image/')) {
        previewImage.src = fileURL;
        previewImage.style.display = 'block';
        previewVideo.style.display = 'none';
    } else if (file.type.startsWith('video/')) {
        previewVideo.src = fileURL;
        previewVideo.style.display = 'block';
        previewImage.style.display = 'none';
    }
    
    // 显示预览区域
    preview.style.display = 'block';
    
    // 滚动到预览区域
    preview.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function clearPreview() {
    const preview = document.getElementById('filePreview');
    const previewImage = document.getElementById('previewImage');
    const previewVideo = document.getElementById('previewVideo');
    
    preview.style.display = 'none';
    previewImage.src = '';
    previewVideo.src = '';
    currentFile = null;
    
    // 清空文件输入
    document.getElementById('fileInput').value = '';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ==================== 检测功能 ====================
async function startDetection() {
    if (!currentFile) {
        showNotification('错误', '请先选择文件', 'error');
        return;
    }
    
    if (isDetecting) {
        showNotification('提示', '检测正在进行中，请稍候', 'warning');
        return;
    }
    
    isDetecting = true;
    showLoadingState();
    
    try {
        const formData = new FormData();
        formData.append('file', currentFile);
        
        // 添加选中的模型ID
        const modelSelect = document.getElementById('modelSelect');
        if (modelSelect && modelSelect.value) {
            formData.append('model_id', modelSelect.value);
        }

        // 根据文件类型选择API端点
        const fileType = getFileTypeFromFile(currentFile);
        const endpoint = fileType === 'video' ? '/api/detect/video' : '/api/detect/image';
        
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (fileType === 'video') {
                startVideoPlayback(data);
            } else {
                showDetectionResult(data);
            }
            showNotification('成功', '检测完成！', 'success');
            
            // 总是刷新历史记录 - 确保数据同步
            console.log('🔄 检测完成，刷新历史记录...');
            setTimeout(() => {
                loadHistory();
            }, 500); // 延迟500ms确保数据库已保存
        } else {
            throw new Error(data.error || '检测失败');
        }
    } catch (error) {
        console.error('检测失败:', error);
        showNotification('错误', error.message || '检测失败，请重试', 'error');
        hideLoadingState();
    } finally {
        isDetecting = false;
    }
}

function getFileTypeFromFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (['mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv'].includes(ext)) {
        return 'video';
    }
    return 'image';
}

function startVideoPlayback(data) {
    // 启动视频实时播放和检测显示
    hideLoadingState();
    
    console.log('🎬 启动视频实时播放:', data);
    
    // 显示视频基本信息
    const videoInfo = `视频: ${data.video_info.filename} | 时长: ${data.video_info.duration.toFixed(1)}s | 帧率: ${data.video_info.fps.toFixed(1)}fps`;
    showNotification('信息', videoInfo, 'info');
    
    // 设置视频处理状态
    videoProcessing = true;
    
    // 显示结果区域
    document.getElementById('resultImage').style.display = 'block';
    document.getElementById('resultInfo').style.display = 'block';
    
    // 添加停止视频按钮 - 平滑添加防止跳动
    const resultActions = document.querySelector('.result-actions');
    if (resultActions && !document.getElementById('stopVideoBtn')) {
        const stopBtn = document.createElement('button');
        stopBtn.id = 'stopVideoBtn';
        stopBtn.className = 'btn btn-danger';
        stopBtn.innerHTML = '<i class="fas fa-stop"></i> 停止视频';
        stopBtn.onclick = stopVideoPlayback;
        stopBtn.style.opacity = '0';
        stopBtn.style.transform = 'scale(0.8)';
        resultActions.insertBefore(stopBtn, resultActions.firstChild);
        
        // 平滑显示动画
        setTimeout(() => {
            stopBtn.style.transition = 'all 0.3s ease';
            stopBtn.style.opacity = '1';
            stopBtn.style.transform = 'scale(1)';
        }, 10);
    }
    
    // 开始获取视频帧
    startVideoFrameLoop();
    
    // 滚动到结果区域
    document.getElementById('resultInfo').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function startVideoFrameLoop() {
    // 视频帧获取循环
    let frameCount = 0;
    
    videoInterval = setInterval(async () => {
        if (!videoProcessing) {
            clearInterval(videoInterval);
            return;
        }
        
        try {
            const response = await fetch('/api/video/frame');
            const data = await response.json();
            
            if (data.success && data.result_image) {
                frameCount++;
                
                // 更新视频画面
                const resultImg = document.getElementById('detectionResult');
                resultImg.src = 'data:image/jpeg;base64,' + data.result_image;
                document.getElementById('resultImage').style.display = 'block';
                
                // 更新检测信息 - 显示坐标
                updateVideoDetectionInfo(data);
                
                console.log(`🎬 视频帧 ${data.frame_number}: ${data.results.object_count} 个目标`);
            } else if (data.message) {
                console.log('⏳ 等待视频帧...');
            }
        } catch (error) {
            console.error('获取视频帧失败:', error);
        }
    }, 100); // 每100ms获取一帧
}

function updateVideoDetectionInfo(data) {
    // 更新视频检测信息显示
    // 更新检测信息
    document.getElementById('detectionTime').textContent = data.detection_time + ' ms';
    document.getElementById('objectCount').textContent = data.results.object_count;
    document.getElementById('mainClass').textContent = data.results.main_class || '-';
    
    // 更新置信度
    const confidence = data.results.confidence || 0;
    const confidencePercent = Math.round(confidence * 100);
    document.getElementById('confidenceFill').style.width = confidencePercent + '%';
    document.getElementById('confidenceText').textContent = confidencePercent + '%';
    
    // 显示边界框坐标（始终显示区域，未检测到时显示"-"）
    if (data.results.bbox) {
        document.getElementById('bboxX1').textContent = data.results.bbox.x1;
        document.getElementById('bboxY1').textContent = data.results.bbox.y1;
        document.getElementById('bboxX2').textContent = data.results.bbox.x2;
        document.getElementById('bboxY2').textContent = data.results.bbox.y2;
    } else {
        document.getElementById('bboxX1').textContent = '-';
        document.getElementById('bboxY1').textContent = '-';
        document.getElementById('bboxX2').textContent = '-';
        document.getElementById('bboxY2').textContent = '-';
    }
    document.getElementById('bboxInfo').style.display = 'block';
}

function stopVideoPlayback() {
    // 停止视频播放
    try {
        console.log('🛑 停止视频播放...');
        
        // 停止前端轮询
        videoProcessing = false;
        if (videoInterval) {
            clearInterval(videoInterval);
            videoInterval = null;
        }
        
        // 调用后端停止API
        fetch('/api/video/stop', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('✅ 视频处理已停止');
                    showNotification('成功', '视频处理已停止', 'success');
                    
                    // 🎯 视频停止后刷新历史记录（延迟确保数据库已保存）
                    console.log('🔄 视频停止，刷新历史记录...');
                    setTimeout(() => {
                        loadHistory();
                    }, 500);
                }
            })
            .catch(error => {
                console.error('停止视频失败:', error);
            });
        
        // 平滑移除停止按钮
        const stopBtn = document.getElementById('stopVideoBtn');
        if (stopBtn) {
            stopBtn.style.transition = 'all 0.3s ease';
            stopBtn.style.opacity = '0';
            stopBtn.style.transform = 'scale(0.8)';
            setTimeout(() => {
                if (stopBtn.parentNode) {
                    stopBtn.remove();
                }
            }, 300);
        }
        
        // 清理显示
        document.getElementById('resultImage').style.display = 'none';
        document.getElementById('resultInfo').style.display = 'none';
        
    } catch (error) {
        console.error('停止视频播放失败:', error);
    }
}

function showVideoDetectionResult(data) {
    // 保留原有的简单视频结果显示作为备用
    hideLoadingState();
    
    // 显示视频检测结果摘要
    document.getElementById('detectionTime').textContent = data.detection_summary?.total_detection_time?.toFixed(1) + ' ms' || '0 ms';
    document.getElementById('objectCount').textContent = data.detection_summary?.frames_with_objects || 0;
    document.getElementById('mainClass').textContent = data.results?.length > 0 ? data.results[0].main_class : '-';
    
    // 更新置信度
    const confidence = data.results?.length > 0 ? data.results[0].confidence : 0;
    const confidencePercent = Math.round(confidence * 100);
    document.getElementById('confidenceFill').style.width = confidencePercent + '%';
    document.getElementById('confidenceText').textContent = confidencePercent + '%';
    
    // 显示视频信息
    const videoInfo = `视频时长: ${data.video_info?.duration?.toFixed(1) || 0}s, 帧率: ${data.video_info?.fps?.toFixed(1) || 0}fps`;
    document.getElementById('detectionTime').textContent += ` (${videoInfo})`;
    
    // 隐藏边界框信息（视频检测显示摘要）
    document.getElementById('bboxInfo').style.display = 'none';
    
    document.getElementById('resultInfo').style.display = 'block';
    
    // 滚动到结果区域
    document.getElementById('resultInfo').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ==================== 摄像头检测功能 ====================
async function startCamera() {
    if (cameraActive) {
        showNotification('提示', '摄像头已在运行中', 'warning');
        return;
    }
    
    try {
        // 获取选中的模型ID
        const modelSelect = document.getElementById('modelSelect');
        let url = '/api/camera/start';
        if (modelSelect && modelSelect.value) {
            url += `?model_id=${encodeURIComponent(modelSelect.value)}`;
        }

        const response = await fetch(url, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            cameraActive = true;
            document.getElementById('startCameraBtn').style.display = 'none';
            document.getElementById('stopCameraBtn').style.display = 'inline-flex';
            document.getElementById('cameraPreview').style.display = 'block';
            
            // 开始获取摄像头帧
            startCameraLoop();
            showNotification('成功', '摄像头已启动', 'success');
        } else {
            throw new Error(data.error || '启动摄像头失败');
        }
    } catch (error) {
        console.error('启动摄像头失败:', error);
        showNotification('错误', error.message || '启动摄像头失败', 'error');
    }
}

async function stopCamera() {
    try {
        console.log('🛑 正在停止摄像头...');
        
        // 第一步：立即停止前端轮询（防止新请求）
        cameraActive = false;
        console.log('🚩 摄像头活动标志已设置为 false');
        
        // 第二步：清除定时器
        if (cameraInterval) {
            clearInterval(cameraInterval);
            cameraInterval = null;
            console.log('⏹️ 前端轮询已停止');
        }
        
        // 第三步：中断所有飞行中的请求
        if (cameraAbortController) {
            cameraAbortController.abort();
            cameraAbortController = null;
            console.log('🚫 已中断飞行中的请求');
        }
        
        // 重置请求锁
        cameraRequestInProgress = false;
        
        // 第四步：等待一小段时间，确保中断生效
        await new Promise(resolve => setTimeout(resolve, 100));
        console.log('⏱️ 等待请求中断完成');
        
        // 第四步：调用后端停止API
        const response = await fetch('/api/camera/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 第五步：更新UI
            document.getElementById('startCameraBtn').style.display = 'inline-flex';
            document.getElementById('stopCameraBtn').style.display = 'none';
            document.getElementById('cameraPreview').style.display = 'none';
            
            // 清空摄像头画面
            const cameraImage = document.getElementById('cameraImage');
            if (cameraImage) {
                cameraImage.src = '';
            }
            
            // 清空检测信息（可选）
            document.getElementById('resultInfo').style.display = 'none';
            
            console.log('✅ 摄像头已完全停止');
            showNotification('成功', '摄像头已停止', 'success');
        } else {
            throw new Error(data.error || '停止摄像头失败');
        }
    } catch (error) {
        console.error('❌ 停止摄像头失败:', error);
        
        // 即使出错也要强制重置UI和所有状态
        cameraActive = false;
        cameraRequestInProgress = false;
        if (cameraAbortController) {
            cameraAbortController.abort();
            cameraAbortController = null;
        }
        if (cameraInterval) {
            clearInterval(cameraInterval);
            cameraInterval = null;
        }
        document.getElementById('startCameraBtn').style.display = 'inline-flex';
        document.getElementById('stopCameraBtn').style.display = 'none';
        
        showNotification('错误', '停止摄像头失败，但已重置状态', 'warning');
    }
}

function startCameraLoop() {
    let frameCount = 0;
    let startTime = Date.now();
    let lastUpdateTime = 0;
    
    // 创建新的AbortController
    cameraAbortController = new AbortController();
    
    cameraInterval = setInterval(async () => {
        // 双重检查：如果摄像头已停止，立即退出
        if (!cameraActive) {
            clearInterval(cameraInterval);
            cameraInterval = null;
            return;
        }
        
        // 防止请求堆积：如果上一个请求还在进行中，跳过本次
        if (cameraRequestInProgress) {
            return;
        }
        
        try {
            cameraRequestInProgress = true;
            
            // 再次检查，防止在等待期间摄像头被关闭
            if (!cameraActive) {
                cameraRequestInProgress = false;
                return;
            }
            
            const response = await fetch('/api/camera/frame', {
                signal: cameraAbortController ? cameraAbortController.signal : undefined
            });
            
            // 请求完成后再次检查
            if (!cameraActive) {
                cameraRequestInProgress = false;
                return;
            }
            
            const data = await response.json();
            
            if (data.success && data.result_image) {
                const currentTime = Date.now();
                
                // 性能拉满模式 - 60FPS更新
                if (currentTime - lastUpdateTime < 16) {  // 16ms间隔 = 60FPS
                    return;
                }
                lastUpdateTime = currentTime;
                
                // 更新摄像头画面
                const cameraImage = document.getElementById('cameraImage');
                const newSrc = 'data:image/jpeg;base64,' + data.result_image;
                
                // 平滑更新图像
                if (cameraImage.src !== newSrc) {
                    cameraImage.src = newSrc;
                }
                
                // 更新检测结果
                updateCameraDetectionInfo(data);
                
                // 取消FPS显示 - 根据用户要求
            } else {
                // 如果摄像头已停止，不打印错误
                if (cameraActive) {
                    console.error('获取摄像头画面失败:', data.error || '无图像数据');
                }
            }
        } catch (error) {
            // 忽略因中断导致的错误
            if (error.name === 'AbortError') {
                console.log('📡 请求已被中断');
            } else if (cameraActive) {
                // 只在摄像头仍在运行时打印错误
                console.error('摄像头检测错误:', error);
            }
        } finally {
            cameraRequestInProgress = false;
        }
    }, 50); // 每50ms获取一帧，20FPS (更稳定，减少请求堆积)
}

function updateCameraDetectionInfo(data) {
    // 更新右侧检测信息面板
    document.getElementById('detectionTime').textContent = data.detection_time + ' ms';
    document.getElementById('objectCount').textContent = data.results.object_count;
    document.getElementById('mainClass').textContent = data.results.main_class || '-';
    
    // 更新置信度
    const confidence = data.results.confidence || 0;
    const confidencePercent = Math.round(confidence * 100);
    document.getElementById('confidenceFill').style.width = confidencePercent + '%';
    document.getElementById('confidenceText').textContent = confidencePercent + '%';
    
    // 显示边界框信息（始终显示区域，未检测到时显示"-"）
    if (data.results.bbox) {
        document.getElementById('bboxX1').textContent = data.results.bbox.x1;
        document.getElementById('bboxY1').textContent = data.results.bbox.y1;
        document.getElementById('bboxX2').textContent = data.results.bbox.x2;
        document.getElementById('bboxY2').textContent = data.results.bbox.y2;
    } else {
        document.getElementById('bboxX1').textContent = '-';
        document.getElementById('bboxY1').textContent = '-';
        document.getElementById('bboxX2').textContent = '-';
        document.getElementById('bboxY2').textContent = '-';
    }
    document.getElementById('bboxInfo').style.display = 'block';
    
    document.getElementById('resultInfo').style.display = 'block';
}

function showLoadingState() {
    document.getElementById('loadingState').style.display = 'block';
    document.getElementById('resultImage').style.display = 'none';
    document.getElementById('resultInfo').style.display = 'none';
}

function hideLoadingState() {
    document.getElementById('loadingState').style.display = 'none';
}

function showDetectionResult(data) {
    hideLoadingState();
    
    // 显示结果图片
    if (data.result_image) {
        const resultImg = document.getElementById('detectionResult');
        resultImg.src = 'data:image/jpeg;base64,' + data.result_image;
        document.getElementById('resultImage').style.display = 'block';
        document.getElementById('downloadBtn').style.display = 'inline-flex';
    }
    
    // 显示检测信息
    document.getElementById('detectionTime').textContent = data.detection_time + ' ms';
    document.getElementById('objectCount').textContent = data.results.object_count;
    document.getElementById('mainClass').textContent = data.results.main_class || '-';
    
    // 更新置信度
    const confidence = data.results.confidence || 0;
    const confidencePercent = Math.round(confidence * 100);
    document.getElementById('confidenceFill').style.width = confidencePercent + '%';
    document.getElementById('confidenceText').textContent = confidencePercent + '%';
    
    // 显示边界框信息（始终显示区域，未检测到时显示"-"）
    if (data.results.bbox) {
        document.getElementById('bboxX1').textContent = data.results.bbox.x1;
        document.getElementById('bboxY1').textContent = data.results.bbox.y1;
        document.getElementById('bboxX2').textContent = data.results.bbox.x2;
        document.getElementById('bboxY2').textContent = data.results.bbox.y2;
    } else {
        document.getElementById('bboxX1').textContent = '-';
        document.getElementById('bboxY1').textContent = '-';
        document.getElementById('bboxX2').textContent = '-';
        document.getElementById('bboxY2').textContent = '-';
    }
    document.getElementById('bboxInfo').style.display = 'block';
    
    document.getElementById('resultInfo').style.display = 'block';
    
    // 滚动到结果区域
    document.getElementById('resultInfo').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // 刷新历史记录
    if (currentSection === 'history') {
        loadHistory();
    }
}

function downloadResult() {
    const resultImg = document.getElementById('detectionResult');
    if (resultImg.src) {
        const link = document.createElement('a');
        link.download = 'detection_result_' + Date.now() + '.jpg';
        link.href = resultImg.src;
        link.click();
    }
}

function clearResult() {
    // 停止视频播放
    if (videoProcessing) {
        stopVideoPlayback();
    }
    
    document.getElementById('resultImage').style.display = 'none';
    document.getElementById('resultInfo').style.display = 'none';
    document.getElementById('downloadBtn').style.display = 'none';
    hideLoadingState();
    
    // 平滑移除视频停止按钮
    const stopBtn = document.getElementById('stopVideoBtn');
    if (stopBtn) {
        stopBtn.style.transition = 'all 0.3s ease';
        stopBtn.style.opacity = '0';
        stopBtn.style.transform = 'scale(0.8)';
        setTimeout(() => {
            if (stopBtn.parentNode) {
                stopBtn.remove();
            }
        }, 300);
    }
}

// ==================== 历史记录 ====================
async function loadHistory(page = 1) {
    const historyLoading = document.getElementById('historyLoading');
    const historyList = document.getElementById('historyList');
    
    if (historyLoading) {
        historyLoading.style.display = 'block';
    }
    if (historyList) {
        historyList.innerHTML = '';
    }
    
    try {
        console.log(`📋 加载历史记录 - 页面 ${page}`);
        const response = await fetch(`/api/history?page=${page}&per_page=10`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('📋 历史记录数据:', data);
        
        if (data.success) {
            displayHistory(data.data);
            setupPagination(data.pagination);
            console.log(`✅ 历史记录加载成功: ${data.data.length} 条记录`);
        } else {
            throw new Error(data.error || '加载历史记录失败');
        }
    } catch (error) {
        console.error('❌ 加载历史记录失败:', error);
        if (historyList) {
            historyList.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--gray-400);">
                    <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>加载历史记录失败: ${error.message}</p>
                    <button onclick="loadHistory()" style="margin-top: 1rem; padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer;">重试</button>
                </div>
            `;
        }
    } finally {
        if (historyLoading) {
            historyLoading.style.display = 'none';
        }
    }
}

function displayHistory(records) {
    const historyList = document.getElementById('historyList');
    
    if (records.length === 0) {
        historyList.innerHTML = `
            <div style="text-align: center; padding: 3rem; color: var(--gray-400);">
                <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <h3>暂无检测记录</h3>
                <p>开始您的第一次检测吧！</p>
            </div>
        `;
        return;
    }
    
    historyList.innerHTML = records.map(record => `
        <div class="history-item">
            <div class="history-item-header">
                <div class="history-item-info">
                    <h4>${record.original_filename}</h4>
                    <div class="history-item-meta">
                        <span><i class="fas fa-calendar"></i> ${formatDate(record.created_at)}</span>
                        <span><i class="fas fa-file"></i> ${record.file_type}</span>
                        <span><i class="fas fa-hdd"></i> ${formatFileSize(record.file_size)}</span>
                    </div>
                </div>
            </div>
            <div class="history-item-results">
                <div class="history-result-item">
                    <label>检测用时</label>
                    <span>${record.detection_time.toFixed(1)} ms</span>
                </div>
                <div class="history-result-item">
                    <label>目标数量</label>
                    <span>${record.object_count}</span>
                </div>
                <div class="history-result-item">
                    <label>主要类别</label>
                    <span>${record.main_class || '-'}</span>
                </div>
                <div class="history-result-item">
                    <label>置信度</label>
                    <span>${record.confidence ? (record.confidence * 100).toFixed(1) + '%' : '-'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

function setupPagination(pagination) {
    const paginationContainer = document.getElementById('pagination');
    
    if (pagination.pages <= 1) {
        paginationContainer.style.display = 'none';
        return;
    }
    
    paginationContainer.style.display = 'flex';
    
    let paginationHTML = '';
    
    // 上一页按钮
    if (pagination.page > 1) {
        paginationHTML += `<button onclick="loadHistory(${pagination.page - 1})">上一页</button>`;
    }
    
    // 页码按钮
    const startPage = Math.max(1, pagination.page - 2);
    const endPage = Math.min(pagination.pages, pagination.page + 2);
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === pagination.page ? 'active' : '';
        paginationHTML += `<button class="${activeClass}" onclick="loadHistory(${i})">${i}</button>`;
    }
    
    // 下一页按钮
    if (pagination.page < pagination.pages) {
        paginationHTML += `<button onclick="loadHistory(${pagination.page + 1})">下一页</button>`;
    }
    
    paginationContainer.innerHTML = paginationHTML;
}

function refreshHistory() {
    loadHistory(currentPage);
}

// ==================== 统计功能 ====================
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
        // 显示默认值
        resetStatsDisplay();
    }
}

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

function displayStats(stats) {
    // ========== 核心指标 ==========
    document.getElementById('totalDetections').textContent = stats.total_detections || 0;
    document.getElementById('todayDetections').textContent = stats.today_detections || 0;
    document.getElementById('recentDetections').textContent = stats.recent_detections || 0;
    document.getElementById('successRate').textContent = stats.success_rate || 0;
    
    // ========== 类型分布 ==========
    document.getElementById('imageDetections').textContent = stats.image_detections || 0;
    document.getElementById('videoDetections').textContent = stats.video_detections || 0;
    document.getElementById('cameraDetections').textContent = stats.camera_detections || 0;
    
    // ========== 性能指标 ==========
    document.getElementById('successDetections').textContent = stats.success_detections || 0;
    document.getElementById('highestConfidence').textContent = stats.highest_confidence?.confidence || 0;
    
    // ========== 热门类别 ==========
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
    
    // ========== 趋势图 ==========
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

function getColorByRank(index) {
    const colors = ['#ffd700', '#c0c0c0', '#cd7f32', '#3b82f6', '#10b981'];
    return colors[index] || '#64748b';
}

// 显示趋势图
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
    
    // 找出最大值用于计算比例
    const maxCount = Math.max(...trendData.map(d => d.count), 1);
    
    // 生成柱状图
    chartContainer.innerHTML = `
        <div class="chart-bars">
            ${trendData.map(item => {
                const height = (item.count / maxCount) * 100;
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

// ==================== 通知系统 ====================
function showNotification(title, message, type = 'info') {
    const container = document.getElementById('notifications');
    const notification = document.createElement('div');
    
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };
    
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
    
    container.appendChild(notification);
    
    // 自动移除通知
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
    
    // 点击移除通知
    notification.addEventListener('click', () => {
        notification.style.animation = 'slideOutRight 0.3s ease forwards';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    });
}

// ==================== 工具函数 ====================
function formatDate(dateString) {
    if (!dateString) return '-';
    
    // 后端已使用本地时间，直接解析即可（不要添加Z后缀）
    const date = new Date(dateString);
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
        return dateString; // 如果解析失败，返回原始字符串
    }
    
    const now = new Date();
    const diff = now - date;
    
    // 小于1分钟
    if (diff < 60000 && diff >= 0) {
        return '刚刚';
    }
    
    // 小于1小时
    if (diff < 3600000 && diff >= 0) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}分钟前`;
    }
    
    // 小于24小时
    if (diff < 86400000 && diff >= 0) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}小时前`;
    }
    
    // 小于7天
    if (diff < 604800000 && diff >= 0) {
        const days = Math.floor(diff / 86400000);
        return `${days}天前`;
    }
    
    // 超过7天或未来时间，显示具体日期时间
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    const today = new Date();
    const isToday = date.getDate() === today.getDate() && 
                    date.getMonth() === today.getMonth() && 
                    date.getFullYear() === today.getFullYear();
    
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const isYesterday = date.getDate() === yesterday.getDate() && 
                        date.getMonth() === yesterday.getMonth() && 
                        date.getFullYear() === yesterday.getFullYear();
    
    if (isToday) {
        return `今天 ${hours}:${minutes}`;
    } else if (isYesterday) {
        return `昨天 ${hours}:${minutes}`;
    } else if (year === today.getFullYear()) {
        return `${month}-${day} ${hours}:${minutes}`;
    } else {
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    }
}

// 添加滑出动画
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
