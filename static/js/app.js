/**
 * ITA 肤色分析 - 主逻辑
 */

let capturedImageData = null;
let isDemoMode = false;
let lastAnalysisResult = null;  // 保存最近一次分析结果

// ===== 底部导航 =====
function switchTab(btn) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    const pageId = btn.dataset.page;
    goToPage(pageId);
    if (pageId === 'page-history-list') loadHistory();
}

// ===== 页面导航 =====
function goToPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = document.getElementById(pageId);
    if (page) page.classList.add('active');
    if (pageId !== 'page-camera') Camera.close();
}

// ===== 拍照流程 =====
async function openCamera() {
    const success = await Camera.open();
    if (success) {
        goToPage('page-camera');
    } else {
        alert('无法访问摄像头，请从相册选择照片');
        uploadFromAlbum();
    }
}

function capturePhoto() {
    capturedImageData = Camera.capture();
    document.getElementById('preview-image').src = capturedImageData;
    Camera.close();
    goToPage('page-preview');
}

function uploadFromAlbum() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/jpeg,image/png,image/webp';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
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
                canvas.width = width; canvas.height = height;
                canvas.getContext('2d').drawImage(img, 0, 0, width, height);
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

function retakePhoto() {
    capturedImageData = null;
    goToPage('page-guide');
}

// ===== 分析 =====
async function submitAnalysis() {
    if (!capturedImageData) { showError('提交失败', '没有可分析的照片'); return; }
    goToPage('page-loading');

    const isBackendOk = await API.checkHealth();
    if (isBackendOk) {
        const blob = Camera.dataURLtoBlob(capturedImageData);
        const result = await API.analyzeImage(blob);
        if (result.success) {
            showResult(result.result);
        } else {
            showError('分析失败', result.message || '请检查照片是否符合要求');
        }
    } else {
        showDemoResult();
    }
}

// ===== 结果展示 =====
function showResult(result) {
    lastAnalysisResult = result;

    document.getElementById('ita-value').textContent = result.ita.toFixed(1);
    document.getElementById('category-name').textContent = result.category;
    document.getElementById('category-desc').textContent = result.description;
    document.getElementById('fitzpatrick').textContent = `Fitzpatrick: ${result.fitzpatrick}`;
    document.getElementById('color-bar').style.background = result.color_hex;
    document.getElementById('lab-L').textContent = result.lab.L.toFixed(1);
    document.getElementById('lab-a').textContent = result.lab.a.toFixed(1);
    document.getElementById('lab-b').textContent = result.lab.b.toFixed(1);
    document.getElementById('confidence').textContent = (result.confidence * 100).toFixed(0) + '%';

    if (result.all_scores) renderScoreBar(result.all_scores);

    // UV 建议
    const uvSection = document.getElementById('uv-section');
    if (result.uv && result.vitd_advice) {
        uvSection.style.display = 'block';
        renderUvAdvice(result.uv, result.vitd_advice);
    } else {
        uvSection.style.display = 'none';
    }

    goToPage('page-result');
}

function showDemoResult() {
    const demoData = {
        ita: 35.2,
        category: '中等色',
        description: '白皙到橄榄色，偶尔晒伤但能晒黑',
        fitzpatrick: 'II-III',
        color_hex: '#F5CBA7',
        confidence: 0.85,
        lab: { L: 65.3, a: 12.1, b: 18.5 },
        all_scores: { '浅色': 0.12, '中等色': 0.85, '晒黑色': 0.28, '棕色': 0.05, '深色': 0.01 },
        uv: { uv_index: 5.2, level: '中等', color: '#FFC107', danger: '注意', advice: '建议使用防晒霜' },
        vitd_advice: {
            uv: { uv_index: 5.2, level: '中等', danger: '注意' },
            fitzpatrick_type: 'II', fitzpatrick_name: '白皙',
            spf_recommended: 'SPF 50',
            vitd: {
                optimal_time_range: '6-11 分钟',
                optimal_min_minutes: 6, optimal_max_minutes: 11,
                safe_max_minutes: 15,
                estimated_iu_range: '520-950 IU',
                daily_target_iu: 1000, achieving_pct: 95,
            },
            recommendations: [
                '🌤️ 当前紫外线适中，是适当的日照时间',
                '🧴 建议使用 SPF 50 防晒霜',
                '⏱️ 建议日照时间：6-11 分钟（暴露前臂/面部）',
                '✅ 此照射时间可满足大部分每日维D需求',
                '🍞 建议在上午 10 点前或下午 3 点后进行日照',
            ]
        }
    };
    showResult(demoData);
}

function renderScoreBar(scores) {
    const container = document.getElementById('score-bar');
    const colors = { '浅色': '#FDEBD0', '中等色': '#F5CBA7', '晒黑色': '#E59866', '棕色': '#BA4A00', '深色': '#6E2C00' };
    let html = '';
    for (const [name, score] of Object.entries(scores)) {
        const pct = (score * 100).toFixed(0);
        html += `<div class="score-row">
            <span class="score-label">${name}</span>
            <div class="score-track"><div class="score-fill" style="width:${pct}%;background:${colors[name]||'#00BFA5'}"></div></div>
            <span class="score-pct">${pct}%</span>
        </div>`;
    }
    container.innerHTML = html;
}

function renderUvAdvice(uv, advice) {
    // UV 显示
    document.getElementById('uv-display').innerHTML = `
        <div class="uv-badge" style="background:${uv.color}">
            <span class="uv-number">${uv.uv_index}</span>
            <span class="uv-label">UV 指数</span>
            <span class="uv-level">${uv.level}</span>
        </div>
        <p class="uv-danger">${uv.danger}：${uv.advice}</p>
    `;

    // 维D 摘要
    const vitd = advice.vitd;
    document.getElementById('vitd-summary').innerHTML = `
        <div class="vitd-grid">
            <div class="vitd-item">
                <div class="vitd-label">建议日照</div>
                <div class="vitd-value">${vitd.optimal_time_range}</div>
            </div>
            <div class="vitd-item">
                <div class="vitd-label">安全上限</div>
                <div class="vitd-value">${vitd.safe_max_minutes} 分钟</div>
            </div>
            <div class="vitd-item">
                <div class="vitd-label">预估维D</div>
                <div class="vitd-value">${vitd.estimated_iu_range}</div>
            </div>
            <div class="vitd-item">
                <div class="vitd-label">日需满足</div>
                <div class="vitd-value">${vitd.achieving_pct}%</div>
            </div>
        </div>
        <p class="spf-tip">🧴 建议 ${advice.spf_recommended}</p>
    `;

    // 建议
    const recs = advice.recommendations || [];
    document.getElementById('recommendations').innerHTML =
        recs.map(r => `<div class="rec-item">${r}</div>`).join('');
}

function showError(title, message) {
    document.getElementById('error-title').textContent = title;
    document.getElementById('error-message').textContent = message;
    goToPage('page-error');
}

// ===== 历史记录 =====
async function loadHistory() {
    const list = document.getElementById('history-list');
    list.innerHTML = '<p class="empty-text">加载中...</p>';

    const result = await API.getHistory();
    if (!result.success || !result.result || !result.result.records || result.result.records.length === 0) {
        list.innerHTML = '<p class="empty-text">暂无分析记录，快去拍照分析吧 📸</p>';
        return;
    }

    const records = result.result.records;
    list.innerHTML = records.map(r => {
        const date = new Date(r.created_at || Date.now());
        const dateStr = date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        return `<div class="history-item">
            <div class="history-ita">${(r.ita || 0).toFixed(1)}°</div>
            <div class="history-info">
                <div class="history-category" style="color:${r.color_hex || '#333'}">${r.category || '--'}</div>
                <div class="history-date">${dateStr}</div>
            </div>
            <div class="history-fitz">${r.fitzpatrick || ''}</div>
        </div>`;
    }).join('');
}

// ===== UV 建议工具 =====
async function requestUvAdvice() {
    const ita = parseFloat(document.getElementById('uv-ita').value);
    const fitz = document.getElementById('uv-fitz').value;
    const uvIndex = parseFloat(document.getElementById('uv-index').value) || undefined;
    const month = parseInt(document.getElementById('uv-month').value);
    const now = new Date();
    const hour = now.getHours();

    if (isNaN(ita)) {
        alert('请输入 ITA° 值');
        return;
    }

    const resultDiv = document.getElementById('uv-tool-result');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div class="loading-spinner" style="width:30px;height:30px;margin:20px auto;"></div>';

    const result = await API.getUvAdvice(ita, fitz, uvIndex, null, null, month, hour);

    if (result.success && result.result) {
        const advice = result.result;
        const uv = advice.uv || { uv_index: 0, level: '--', color: '#ccc', danger: '--' };
        resultDiv.innerHTML = `
            <div class="uv-badge" style="background:${uv.color}">
                <span class="uv-number">${uv.uv_index}</span>
                <span class="uv-label">UV 指数</span>
                <span class="uv-level">${uv.level}</span>
            </div>
            <div class="vitd-grid" style="margin-top:16px;">
                <div class="vitd-item"><div class="vitd-label">建议日照</div><div class="vitd-value">${advice.vitd?.optimal_time_range || '--'}</div></div>
                <div class="vitd-item"><div class="vitd-label">安全上限</div><div class="vitd-value">${advice.vitd?.safe_max_minutes || '--'} 分钟</div></div>
                <div class="vitd-item"><div class="vitd-label">预估维D</div><div class="vitd-value">${advice.vitd?.estimated_iu_range || '--'}</div></div>
                <div class="vitd-item"><div class="vitd-label">日需满足</div><div class="vitd-value">${advice.vitd?.achieving_pct || 0}%</div></div>
            </div>
            <p class="spf-tip" style="margin-top:12px;">🧴 建议 ${advice.spf_recommended || '--'}</p>
            ${(advice.recommendations || []).map(r => `<div class="rec-item" style="margin-top:8px;">${r}</div>`).join('')}
        `;
    } else {
        resultDiv.innerHTML = '<p class="empty-text">获取建议失败，请重试</p>';
    }
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', async () => {
    const isBackendOk = await API.checkHealth();
    if (!isBackendOk) {
        isDemoMode = true;
        document.getElementById('demo-notice').style.display = 'block';
    }
    // 设置当前月份
    const monthSelect = document.getElementById('uv-month');
    if (monthSelect) monthSelect.value = new Date().getMonth() + 1;
});
