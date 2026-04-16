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
let lastQualityReady = false;

/** 浏览器仅在 HTTPS 或 localhost 等安全上下文中允许 getUserMedia；http://公网IP 会被拒绝 */
function isCameraContextAllowed() {
    if (typeof window.isSecureContext === 'boolean') {
        return window.isSecureContext;
    }
    const h = window.location.hostname;
    return h === 'localhost' || h === '127.0.0.1' || h === '[::1]';
}

/**
 * 将用户选择的图片文件写入预览（与相册流程共用）
 */
function loadImageFileToPreview(file) {
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
            canvas.getContext('2d').drawImage(img, 0, 0, width, height);
            capturedImageData = canvas.toDataURL('image/jpeg', 0.85);
            document.getElementById('preview-image').src = capturedImageData;
            goToPage('page-preview');
        };
        img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
}

/**
 * HTTP / 公网 IP 等场景：不调用 getUserMedia，用系统相机或相册选图（多数手机仍可调起后置相机）
 */
function openCameraViaSystemCapture() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/jpeg,image/png,image/webp';
    input.setAttribute('capture', 'environment');
    input.onchange = (e) => {
        const file = e.target.files && e.target.files[0];
        if (file) loadImageFileToPreview(file);
    };
    input.click();
}

async function openCamera() {
    if (!isCameraContextAllowed()) {
        openCameraViaSystemCapture();
        return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        openCameraViaSystemCapture();
        return;
    }
    const success = await Camera.open();
    if (success) {
        goToPage('page-camera');
        lastQualityReady = false;
        Camera.startQualityCheck(onQualityUpdate, 500);
    } else {
        if (window.confirm('无法打开实时摄像头，是否改用手机系统相机 / 相册选择照片？')) {
            openCameraViaSystemCapture();
        }
    }
}

function onQualityUpdate(result) {
    const overlay = document.getElementById('quality-overlay');
    const captureBtn = document.getElementById('btn-capture');

    if (!overlay) return;

    lastQualityReady = result.ready;

    // 更新质量分数
    const scorePct = Math.round(result.score * 100);
    const scoreColor = result.ready ? '#4CAF50' : scorePct > 50 ? '#FFC107' : '#F44336';
    overlay.innerHTML = `
        <div class="quality-score" style="border-color:${scoreColor}">
            <span class="quality-num" style="color:${scoreColor}">${scorePct}</span>
            <span class="quality-label">质量分</span>
        </div>
        <div class="quality-tips">
            ${result.tips.map(t => `<div class="quality-tip ${t.startsWith('✅') ? 'tip-ok' : t.startsWith('📄') && t.includes('已') ? 'tip-ok' : t.startsWith('🦴') && t.includes('已') ? 'tip-ok' : ''}">${t}</div>`).join('')}
        </div>
    `;

    // 更新拍照按钮状态
    if (captureBtn) {
        if (result.ready) {
            captureBtn.classList.add('btn-ready');
            captureBtn.disabled = false;
            captureBtn.textContent = '✅ 拍照';
        } else {
            captureBtn.classList.remove('btn-ready');
            captureBtn.disabled = true;
            captureBtn.textContent = '📷 拍照';
        }
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
        const file = e.target.files && e.target.files[0];
        if (file) loadImageFileToPreview(file);
    };
    input.click();
}

function retakePhoto() {
    capturedImageData = null;
    const wrap = document.getElementById('result-photos-wrap');
    if (wrap) wrap.style.display = 'none';
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
function escapeHtml(text) {
    if (text == null || text === undefined) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

/**
 * 根据本次分析结果生成面向手机用户的通俗解读（拍照/相册上传后同显）
 */
function renderResultInterpretation(result) {
    const box = document.getElementById('result-interpretation');
    if (!box) return;

    const ita = typeof result.ita === 'number' ? result.ita : parseFloat(result.ita);
    const lab = result.lab || {};
    const L = typeof lab.L === 'number' ? lab.L : parseFloat(lab.L) || 0;
    const a = typeof lab.a === 'number' ? lab.a : parseFloat(lab.a) || 0;
    const b = typeof lab.b === 'number' ? lab.b : parseFloat(lab.b) || 0;
    const conf = typeof result.confidence === 'number' ? result.confidence : parseFloat(result.confidence) || 0;
    const category = escapeHtml(result.category || '—');
    const descRaw = result.description || '';
    const descPhrase = descRaw ? `「${escapeHtml(descRaw)}」` : '';
    const fitz = escapeHtml(result.fitzpatrick || '—');

    let itaLine = '';
    if (ita > 55) {
        itaLine = 'ITA° 数值较高，在本次算法中与<strong>偏浅肤色</strong>一致；会随光线、手臂部位变化，适合作为自我观察参考。';
    } else if (ita > 28) {
        itaLine = 'ITA° 处于<strong>中等偏浅</strong>区间，常见于白皙至橄榄色外观，日晒后可能略向深侧变化。';
    } else if (ita > 10) {
        itaLine = 'ITA° 处于<strong>晒黑至中等</strong>过渡区，可能与日晒或天然偏棕相符。';
    } else if (ita > -30) {
        itaLine = 'ITA° 偏低，与<strong>棕褐至深肤色侧</strong>相符；建议固定光线、同一条手臂多次对比更有参考价值。';
    } else {
        itaLine = 'ITA° 较低，在本次分类中接近<strong>深肤色</strong>区间；若与主观感受不符，请确认照片中白纸与光线是否合格。';
    }

    let confLine = '';
    if (conf >= 0.75) {
        confLine = '本次<strong>分类置信度较高</strong>，当前 ITA° 与所选类别较为匹配。';
    } else if (conf >= 0.45) {
        confLine = '置信度为<strong>中等</strong>，可能接近相邻类别分界，可在同样条件下再拍一张对比。';
    } else {
        confLine = '本次<strong>置信度偏低</strong>，可能靠近分类边界或受光线/白纸影响，建议按首页指引重拍。';
    }

    const labParts = [];
    if (L >= 65) labParts.push('整体<strong>偏亮</strong>');
    else if (L >= 45) labParts.push('明暗<strong>适中</strong>');
    else labParts.push('整体<strong>偏暗</strong>，注意阴影与曝光');
    if (a > 6) labParts.push('红调略明显');
    else if (a < -2) labParts.push('绿调略明显');
    else labParts.push('红绿倾向适中');
    if (b > 14) labParts.push('黄调较明显（常与日晒或底调有关）');
    else if (b < 4) labParts.push('黄调不突出');
    else labParts.push('黄蓝在常见范围');
    const labLine = `L*a*b* 中：${labParts.join('；')}。`;

    box.innerHTML = `
        <h3>📖 结果解读</h3>
        <div class="interpret-block">
            <span class="interpret-label">ITA° 说明</span>
            <p>${itaLine}</p>
        </div>
        <div class="interpret-block">
            <span class="interpret-label">本次分类（${category}）</span>
            <p>${descPhrase ? descPhrase + ' ' : ''}Fitzpatrick 映射为 <strong>${fitz}</strong>，可用于日常<strong>防晒强度</strong>等参考，并非医学诊断。</p>
        </div>
        <div class="interpret-block">
            <span class="interpret-label">置信度（${(conf * 100).toFixed(0)}%）</span>
            <p>${confLine}</p>
        </div>
        <div class="interpret-block">
            <span class="interpret-label">颜色数据（通俗）</span>
            <p>${labLine}</p>
        </div>
        <p class="interpret-disclaimer">以上内容由前臂照片 + 白纸校准自动估算，仅供护肤与防晒参考；拍照或从相册上传的分析逻辑相同。如有皮肤问题或医学需求请咨询专业医师。</p>
    `;
    box.style.display = 'block';
}

/** 演示模式无上传图时的占位，保证结果页双栏布局 */
const DEMO_RESULT_PLACEHOLDER_IMAGE =
    'data:image/svg+xml,' +
    encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">' +
            '<rect fill="#eceff1" width="400" height="300"/>' +
            '<text x="200" y="145" text-anchor="middle" fill="#78909c" font-size="16" font-family="sans-serif">演示示意</text>' +
            '<text x="200" y="172" text-anchor="middle" fill="#b0bec5" font-size="12" font-family="sans-serif">无实际上传图</text>' +
        '</svg>'
    );

const EFFECT_SCORE_COLORS = {
    浅色: '#FDEBD0',
    中等色: '#F5CBA7',
    晒黑色: '#E59866',
    棕色: '#BA4A00',
    深色: '#6E2C00',
};

const EFFECT_SCORE_ORDER = ['浅色', '中等色', '晒黑色', '棕色', '深色'];

/**
 * 在效果示意叠层内绘制五类 all_scores 微型条（与下方 score-bar 同源数据）
 */
function renderEffectScoresMini(scores, highlightCategory) {
    const el = document.getElementById('effect-scores-mini');
    if (!el) return;
    if (!scores || typeof scores !== 'object') {
        el.innerHTML = '';
        el.style.display = 'none';
        return;
    }

    let html = '<div class="effect-scores-mini-title">五类匹配</div>';
    for (const name of EFFECT_SCORE_ORDER) {
        const raw = scores[name];
        if (raw == null || raw === undefined) continue;
        const pct = Math.min(100, Math.round(Number(raw) * 100));
        const color = EFFECT_SCORE_COLORS[name] || '#00BFA5';
        const active = highlightCategory && name === highlightCategory ? ' effect-mini-row--active' : '';
        const title = `${name} ${pct}%`;
        html += `<div class="effect-mini-row${active}" title="${escapeHtml(title)}">` +
            `<span class="effect-mini-label">${escapeHtml(name)}</span>` +
            `<div class="effect-mini-track"><div class="effect-mini-fill" style="width:${pct}%;background:${color}"></div></div>` +
            `</div>`;
    }
    el.innerHTML = html;
    el.style.display = 'block';
}

function renderResultPhotos(result) {
    const wrap = document.getElementById('result-photos-wrap');
    const origImg = document.getElementById('result-photo-original');
    const effImg = document.getElementById('result-photo-effect');
    const effectBox = document.getElementById('result-photo-effect-box');
    const itaBadge = document.getElementById('effect-ita-badge');
    const catBadge = document.getElementById('effect-cat-badge');
    if (!wrap || !origImg || !effImg || !effectBox || !itaBadge || !catBadge) return;

    const src = capturedImageData || DEMO_RESULT_PLACEHOLDER_IMAGE;
    origImg.src = src;
    effImg.src = src;

    const hex = result.color_hex || '#00BFA5';
    effectBox.style.borderColor = hex;
    effectBox.style.boxShadow = `0 4px 16px ${hex}55`;

    itaBadge.textContent = `ITA° ${result.ita.toFixed(1)}`;
    catBadge.textContent = result.category || '—';

    renderEffectScoresMini(result.all_scores, result.category);

    wrap.style.display = 'grid';
}

function showResult(result) {
    lastAnalysisResult = result;

    renderResultPhotos(result);

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
        renderUvItaBridge(result);
    } else {
        uvSection.style.display = 'none';
        const bridge = document.getElementById('uv-ita-summary');
        if (bridge) {
            bridge.style.display = 'none';
            bridge.innerHTML = '';
        }
    }

    renderResultInterpretation(result);

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

/**
 * UV 区块下方：把本次 ITA° / 分类 与 vitd_advice、UV 指数串成一段可读摘要
 */
function renderUvItaBridge(result) {
    const host = document.getElementById('uv-ita-summary');
    if (!host || !result.vitd_advice) {
        if (host) {
            host.style.display = 'none';
            host.innerHTML = '';
        }
        return;
    }

    const adv = result.vitd_advice;
    const uv = result.uv || adv.uv || {};
    const vitd = adv.vitd || {};
    const ita = typeof result.ita === 'number' ? result.ita : parseFloat(result.ita);
    const category = escapeHtml(result.category || '—');
    const fitz = escapeHtml(result.fitzpatrick || '—');
    const spf = escapeHtml(adv.spf_recommended || '按需防晒');
    const uvIdx = uv.uv_index != null && uv.uv_index !== ''
        ? Number(uv.uv_index).toFixed(1)
        : '—';
    const uvLevel = escapeHtml(uv.level || '—');
    const optimal = vitd.optimal_time_range
        ? escapeHtml(String(vitd.optimal_time_range))
        : '见上文';
    const safeMax = vitd.safe_max_minutes != null ? String(vitd.safe_max_minutes) : '—';

    host.innerHTML = `
        <div class="uv-ita-bridge">
            <h4>🧴 结合本次肤色的防晒提示</h4>
            <p>您本次测得 <strong>ITA° ${ita.toFixed(1)}°</strong>（${category}，Fitzpatrick ${fitz}）。在估算的 <strong>UV 指数 ${uvIdx}</strong>（${uvLevel}）下，建议优先使用 <strong>${spf}</strong>；日晒时长可参考上方「建议日照」<strong>${optimal}</strong>，单日无防护暴露不宜超过约 <strong>${safeMax} 分钟</strong>。维D与日照为模型估算，请结合自身与医嘱调整。</p>
        </div>
    `;
    host.style.display = 'block';
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
    const insecureNotice = document.getElementById('insecure-camera-notice');
    const btnCam = document.getElementById('btn-camera');
    if (insecureNotice && !isCameraContextAllowed()) {
        insecureNotice.style.display = 'block';
        if (btnCam) {
            btnCam.title = '将调起系统相机或相册（无网页内实时预览与质量条）';
        }
    } else if (btnCam) {
        btnCam.title = '网页内实时预览，支持质量检测（需 HTTPS 或本机访问）';
    }
    const isBackendOk = await API.checkHealth();
    if (!isBackendOk) {
        isDemoMode = true;
        document.getElementById('demo-notice').style.display = 'block';
    }
    // 设置当前月份
    const monthSelect = document.getElementById('uv-month');
    if (monthSelect) monthSelect.value = new Date().getMonth() + 1;
});
