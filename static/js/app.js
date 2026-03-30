/**
 * ITA 肤色分析 - 主应用逻辑
 */

// ===== 页面路由 =====
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(pageId).classList.add('active');

    // 进入特定页面时的初始化
    if (pageId === 'page-camera') {
        Camera.init();
        document.getElementById('preview-area').style.display = 'none';
        document.getElementById('camera-controls').style.display = 'block';
    } else if (pageId === 'page-history') {
        renderHistory();
    }
}

// ===== 拍照流程 =====
let capturedBlob = null;

async function capturePhoto() {
    try {
        const { blob, dataUrl } = Camera.capture();
        capturedBlob = blob;
        showPreview(dataUrl);
    } catch (e) {
        showToast('拍照失败，请重试');
    }
}

function pickFromGallery() {
    Camera.pick();
}

function handleGallery(event) {
    const file = event.target.files[0];
    if (!file) return;

    Camera.compressFile(file).then(({ blob, dataUrl }) => {
        capturedBlob = blob;
        showPreview(dataUrl);
    });

    // 清空 input 以允许重复选择同一文件
    event.target.value = '';
}

function showPreview(dataUrl) {
    document.getElementById('preview-image').src = dataUrl;
    document.getElementById('camera-controls').style.display = 'none';
    document.getElementById('preview-area').style.display = 'block';
}

function retakePhoto() {
    capturedBlob = null;
    document.getElementById('preview-area').style.display = 'none';
    document.getElementById('camera-controls').style.display = 'block';
}

function switchCamera() {
    Camera.switchCamera();
}

// ===== 分析 =====
async function analyzePhoto() {
    if (!capturedBlob) {
        showToast('请先拍照或选择图片');
        return;
    }

    showPage('page-loading');

    try {
        const result = await API.analyzeImage(capturedBlob);

        if (!result.success) {
            showToast(result.message || '分析失败');
            showPage('page-camera');
            return;
        }

        // 保存到历史
        saveToHistory(result);

        // 显示结果
        displayResult(result);
        showPage('page-result');
    } catch (e) {
        showToast('分析出错: ' + e.message);
        showPage('page-camera');
    }
}

// ===== 显示结果 =====
function displayResult(result) {
    // ITA 值
    document.getElementById('result-ita').querySelector('.ita-value').textContent =
        result.ita !== null ? result.ita.toFixed(1) : '--';

    // 分类
    const badge = document.getElementById('result-category').querySelector('.category-badge');
    badge.textContent = result.category || '未知';

    // 分类颜色
    const colorMap = {
        'very_light': '#FFDFC4',
        'medium': '#F0C8A0',
        'tanned': '#D4A574',
        'brown': '#A0724A',
        'dark': '#6B4226'
    };
    badge.style.background = colorMap[result.category_id] || 'var(--primary)';

    // 置信度
    document.getElementById('result-confidence').textContent =
        result.confidence ? `置信度: ${Math.round(result.confidence * 100)}%` : '--';

    // 校准状态
    const calibEl = document.getElementById('result-calibrated');
    if (result.calibrated) {
        calibEl.textContent = '✅ 已使用白纸校准';
        calibEl.className = 'result-calibrated ok';
    } else {
        calibEl.textContent = '⚠️ 未检测到白纸，结果仅供参考';
        calibEl.className = 'result-calibrated warn';
    }

    // L*a*b* 值
    if (result.lab) {
        document.getElementById('result-L').textContent = result.lab.L?.toFixed(1) || '--';
        document.getElementById('result-a').textContent = result.lab.a?.toFixed(1) || '--';
        document.getElementById('result-b').textContent = result.lab.b?.toFixed(1) || '--';
    }

    // Fitzpatrick
    document.getElementById('result-fitz').textContent =
        result.fitzpatrick ? result.fitzpatrick.join(' / ') : '--';

    // 描述
    document.getElementById('result-description').textContent =
        result.description || '--';

    // UV 建议
    document.getElementById('result-advice-text').textContent =
        result.uv_advice || '--';
}

// ===== 历史记录 =====
const HISTORY_KEY = 'ita_history';
const MAX_HISTORY = 50;

function saveToHistory(result) {
    let history = getHistory();
    history.unshift({
        id: Date.now(),
        ita: result.ita,
        category: result.category,
        category_id: result.category_id,
        confidence: result.confidence,
        timestamp: result.timestamp || new Date().toISOString()
    });

    // 限制数量
    if (history.length > MAX_HISTORY) {
        history = history.slice(0, MAX_HISTORY);
    }

    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function getHistory() {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    } catch {
        return [];
    }
}

function renderHistory() {
    const container = document.getElementById('history-list');
    const history = getHistory();

    if (history.length === 0) {
        container.innerHTML = `
            <div class="history-empty">
                <p>📭</p>
                <p>暂无历史记录</p>
                <p class="text-muted">完成第一次肤色分析后，记录将显示在这里</p>
            </div>
        `;
        return;
    }

    const colorMap = {
        'very_light': '#FFDFC4',
        'medium': '#F0C8A0',
        'tanned': '#D4A574',
        'brown': '#A0724A',
        'dark': '#6B4226'
    };

    container.innerHTML = history.map(item => {
        const date = new Date(item.timestamp);
        const dateStr = `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
        const color = colorMap[item.category_id] || '#ccc';

        return `
            <div class="history-item">
                <div class="history-color" style="background:${color};"></div>
                <div class="history-info">
                    <div class="history-ita">${item.category} · ${item.ita?.toFixed(1)}°</div>
                    <div class="history-meta">${dateStr} · 置信度 ${Math.round((item.confidence || 0) * 100)}%</div>
                </div>
            </div>
        `;
    }).join('');
}

function clearHistory() {
    if (confirm('确定要清空所有历史记录吗？')) {
        localStorage.removeItem(HISTORY_KEY);
        renderHistory();
        showToast('历史记录已清空');
    }
}

// ===== 工具函数 =====
function resetToCamera() {
    capturedBlob = null;
    showPage('page-camera');
}

function stopCamera() {
    Camera.stop();
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 2500);
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', () => {
    // 检查后端状态
    API.healthCheck().then(ok => {
        if (!ok) {
            console.log('后端未连接，将使用 Demo 模式');
        }
    });

    // 更新历史按钮
    const history = getHistory();
    const historyBtn = document.getElementById('btn-history-home');
    if (historyBtn) {
        historyBtn.textContent = history.length > 0
            ? `📋 查看历史记录 (${history.length})`
            : '📋 查看历史记录';
    }
});
