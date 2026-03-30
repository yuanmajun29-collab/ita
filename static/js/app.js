/**
 * ITA 肤色分析 - 主逻辑
 */

let capturedImageData = null;  // 拍照后的图片数据
let isDemoMode = false;        // 演示模式标志

// ===== 页面导航 =====
function goToPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById(pageId);
    if (page) page.classList.add('active');

    // 离开相机页面时关闭摄像头
    if (pageId !== 'page-camera') {
        Camera.close();
    }
}

// ===== 拍照流程 =====

/**
 * 打开摄像头拍照
 */
async function openCamera() {
    const success = await Camera.open();
    if (success) {
        goToPage('page-camera');
    } else {
        // 摄像头不可用，使用文件上传
        alert('无法访问摄像头，请从相册选择照片');
        uploadFromAlbum();
    }
}

/**
 * 拍照
 */
function capturePhoto() {
    capturedImageData = Camera.capture();
    document.getElementById('preview-image').src = capturedImageData;
    Camera.close();
    goToPage('page-preview');
}

/**
 * 从相册选择
 */
function uploadFromAlbum() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/jpeg,image/png,image/webp';
    input.capture = false;

    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // 压缩图片
        const reader = new FileReader();
        reader.onload = (ev) => {
            const img = new Image();
            img.onload = () => {
                const maxSize = 1920;
                let { width, height } = img;
                if (width > maxSize || height > maxSize) {
                    const ratio = Math.min(maxSize / width, maxSize / height);
                    width = Math.round(width * ratio);
                    height = Math.round(height * ratio);
                }
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                capturedImageData = canvas.toDataURL('image/jpeg', 0.85);
                document.getElementById('preview-image').src = capturedImageData;
                goToPage('page-preview');
            };
            img.src = ev.target.result;
        };
        reader.readAsDataURL(file);
    };

    input.click();
}

/**
 * 重拍
 */
function retakePhoto() {
    capturedImageData = null;
    goToPage('page-guide');
}

// ===== 分析流程 =====

/**
 * 提交分析
 */
async function submitAnalysis() {
    if (!capturedImageData) {
        showError('提交失败', '没有可分析的照片');
        return;
    }

    goToPage('page-loading');

    // 尝试调用后端
    const isBackendOk = await API.checkHealth();

    if (isBackendOk) {
        // 真实分析
        const blob = Camera.dataURLtoBlob(capturedImageData);
        const result = await API.analyzeImage(blob);

        if (result.success) {
            showResult(result.result);
        } else {
            showError('分析失败', result.message || '请检查照片是否符合要求');
        }
    } else {
        // 演示模式
        showDemoResult();
    }
}

// ===== 结果展示 =====

/**
 * 显示真实分析结果
 */
function showResult(result) {
    document.getElementById('ita-value').textContent = result.ita.toFixed(1);
    document.getElementById('category-name').textContent = result.category;
    document.getElementById('category-desc').textContent = result.description;
    document.getElementById('fitzpatrick').textContent = `Fitzpatrick: ${result.fitzpatrick}`;
    document.getElementById('color-bar').style.background = result.color_hex;

    document.getElementById('lab-L').textContent = result.lab.L.toFixed(1);
    document.getElementById('lab-a').textContent = result.lab.a.toFixed(1);
    document.getElementById('lab-b').textContent = result.lab.b.toFixed(1);
    document.getElementById('confidence').textContent = (result.confidence * 100).toFixed(0) + '%';

    // 分类分数条
    if (result.all_scores) {
        renderScoreBar(result.all_scores);
    }

    goToPage('page-result');
}

/**
 * 显示演示结果
 */
function showDemoResult() {
    const demoData = {
        ita: 35.2,
        category: '中等色',
        description: '白皙到橄榄色，偶尔晒伤但能晒黑',
        fitzpatrick: 'II-III',
        color_hex: '#F5CBA7',
        confidence: 0.85,
        lab: { L: 65.3, a: 12.1, b: 18.5 },
        all_scores: {
            '浅色': 0.12,
            '中等色': 0.85,
            '晒黑色': 0.28,
            '棕色': 0.05,
            '深色': 0.01
        }
    };

    showResult(demoData);
}

/**
 * 渲染分类分数条
 */
function renderScoreBar(scores) {
    const container = document.getElementById('score-bar');
    const colors = {
        '浅色': '#FDEBD0',
        '中等色': '#F5CBA7',
        '晒黑色': '#E59866',
        '棕色': '#BA4A00',
        '深色': '#6E2C00'
    };

    let html = '';
    for (const [name, score] of Object.entries(scores)) {
        const pct = (score * 100).toFixed(0);
        html += `
            <div class="score-row">
                <span class="score-label">${name}</span>
                <div class="score-track">
                    <div class="score-fill" style="width: ${pct}%; background: ${colors[name] || '#00BFA5'}"></div>
                </div>
                <span class="score-pct">${pct}%</span>
            </div>
        `;
    }
    container.innerHTML = html;
}

/**
 * 显示错误
 */
function showError(title, message) {
    document.getElementById('error-title').textContent = title;
    document.getElementById('error-message').textContent = message;
    goToPage('page-error');
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', async () => {
    // 检查后端状态
    const isBackendOk = await API.checkHealth();
    if (!isBackendOk) {
        isDemoMode = true;
        document.getElementById('demo-notice').style.display = 'block';
    }
});
