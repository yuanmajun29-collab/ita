/**
 * 摄像头控制 + 实时质量检测模块
 */

const Camera = {
    stream: null,
    videoElement: null,
    canvasElement: null,
    ws: null,                    // WebSocket 连接
    qualityInterval: null,       // 质量检测定时器
    qualityCallback: null,       // 质量结果回调
    qualityActive: false,        // 是否启用质量检测

    init() {
        this.videoElement = document.getElementById('camera-preview');
        this.canvasElement = document.getElementById('camera-canvas');
    },

    async open() {
        this.init();
        try {
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            };
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.stream;
            return true;
        } catch (e) {
            console.error('摄像头打开失败:', e);
            try {
                this.stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 1280 }, height: { ideal: 720 } },
                    audio: false
                });
                this.videoElement.srcObject = this.stream;
                return true;
            } catch (e2) {
                console.error('摄像头不可用:', e2);
                return false;
            }
        }
    },

    capture() {
        const video = this.videoElement;
        const canvas = this.canvasElement;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        const maxSize = 1920;
        let { width, height } = canvas;
        if (width > maxSize || height > maxSize) {
            const ratio = Math.min(maxSize / width, maxSize / height);
            width = Math.round(width * ratio);
            height = Math.round(height * ratio);
        }
        const tmpCanvas = document.createElement('canvas');
        tmpCanvas.width = width;
        tmpCanvas.height = height;
        tmpCanvas.getContext('2d').drawImage(canvas, 0, 0, width, height);
        return tmpCanvas.toDataURL('image/jpeg', 0.85);
    },

    close() {
        this.stopQualityCheck();
        this.disconnectWs();
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
    },

    /**
     * 启动实时质量检测
     * @param {Function} callback - 每次检测结果回调 (result) => void
     * @param {number} intervalMs - 检测间隔（毫秒），默认 500ms
     */
    startQualityCheck(callback, intervalMs = 500) {
        this.qualityCallback = callback;
        this.qualityActive = true;
        this.connectWs();
        this.qualityInterval = setInterval(() => {
            this._sendFrame();
        }, intervalMs);
    },

    stopQualityCheck() {
        this.qualityActive = false;
        if (this.qualityInterval) {
            clearInterval(this.qualityInterval);
            this.qualityInterval = null;
        }
    },

    connectWs() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/ws/quality`;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('质量检测 WebSocket 已连接');
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (this.qualityCallback) {
                        this.qualityCallback(data);
                    }
                } catch (e) {
                    console.error('解析质量数据失败:', e);
                }
            };

            this.ws.onerror = (e) => {
                console.warn('WebSocket 连接失败，使用本地质量检测');
                this._startLocalQualityCheck();
            };

            this.ws.onclose = () => {
                // 不自动重连，让定时器使用本地检测
            };
        } catch (e) {
            console.warn('WebSocket 不支持，使用本地质量检测');
            this._startLocalQualityCheck();
        }
    },

    disconnectWs() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    },

    _sendFrame() {
        if (!this.qualityActive || !this.videoElement || !this.videoElement.videoWidth) return;

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            // 使用小尺寸帧加速传输
            const canvas = document.createElement('canvas');
            const scale = 320 / Math.max(this.videoElement.videoWidth, this.videoElement.videoHeight);
            canvas.width = Math.round(this.videoElement.videoWidth * scale);
            canvas.height = Math.round(this.videoElement.videoHeight * scale);
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);
            const dataUrl = canvas.toDataURL('image/jpeg', 0.6);

            try {
                this.ws.send(JSON.stringify({ image: dataUrl }));
            } catch (e) {
                // 发送失败，切换到本地检测
                this._startLocalQualityCheck();
            }
        }
    },

    /**
     * 本地降级质量检测（无 WebSocket 时使用）
     * 使用 Canvas 像素分析做基础判断
     */
    _localQualityCallback: null,
    _localInterval: null,
    _startLocalQualityCheck() {
        if (this._localInterval) return; // 已在运行

        this._localInterval = setInterval(() => {
            if (!this.qualityActive || !this.videoElement || !this.videoElement.videoWidth) return;

            const canvas = document.createElement('canvas');
            const scale = 160 / Math.max(this.videoElement.videoWidth, this.videoElement.videoHeight);
            canvas.width = Math.round(this.videoElement.videoWidth * scale);
            canvas.height = Math.round(this.videoElement.videoHeight * scale);
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);

            try {
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const data = imageData.data;
                const pixelCount = data.length / 4;

                // 计算平均亮度
                let totalBrightness = 0;
                let brightPixels = 0;
                let darkPixels = 0;
                let veryBrightPixels = 0;

                for (let i = 0; i < data.length; i += 4) {
                    const brightness = (data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114);
                    totalBrightness += brightness;

                    if (brightness > 200) brightPixels++;
                    if (brightness < 50) darkPixels++;
                    if (brightness > 245) veryBrightPixels++;
                }

                const avgBrightness = totalBrightness / pixelCount;
                const brightRatio = brightPixels / pixelCount;
                const darkRatio = darkPixels / pixelCount;
                const glareRatio = veryBrightPixels / pixelCount;

                // 简单的本地评估
                const tips = [];
                let score = 0.5;
                let ready = false;

                // 亮度检查
                if (avgBrightness < 50) {
                    tips.push('💡 画面太暗');
                    score -= 0.2;
                } else if (avgBrightness > 210) {
                    tips.push('💡 画面太亮');
                    score -= 0.2;
                } else {
                    score += 0.15;
                }

                // 白纸检测（亮色区域 > 8%）
                if (brightRatio > 0.08) {
                    score += 0.2;
                    tips.push('📄 已检测到白纸');
                } else {
                    tips.push('📄 未检测到白纸');
                }

                // 反光
                if (glareRatio > 0.03) {
                    tips.push('✨ 检测到反光');
                    score -= 0.1;
                }

                // 皮肤区域（中间亮度像素占比）
                const normalPixels = pixelCount - brightPixels - darkPixels;
                const normalRatio = normalPixels / pixelCount;
                if (normalRatio > 0.15) {
                    score += 0.15;
                    tips.push('🦴 检测到皮肤区域');
                } else {
                    tips.push('🦴 未检测到足够皮肤区域');
                }

                score = Math.max(0, Math.min(1, score));
                ready = score >= 0.6 && brightRatio > 0.08 && normalRatio > 0.15;

                if (ready && tips.length > 0) {
                    tips[0] = '✅ 条件良好，可以拍照！';
                }

                const result = {
                    score: Math.round(score * 100) / 100,
                    ready: ready,
                    tips: tips,
                    checks: {
                        brightness: { level: avgBrightness < 50 ? 'too_dark' : avgBrightness > 210 ? 'too_bright' : 'good', mean: Math.round(avgBrightness) },
                        white_paper: { detected: brightRatio > 0.08, ratio: Math.round(brightRatio * 100) / 100 },
                        skin_coverage: { detected: normalRatio > 0.15, ratio: Math.round(normalRatio * 100) / 100 },
                        glare: { has_glare: glareRatio > 0.03, ratio: Math.round(glareRatio * 100) / 100 }
                    },
                    mode: 'local'
                };

                if (this.qualityCallback) {
                    this.qualityCallback(result);
                }
            } catch (e) {
                // Canvas tainted 等
            }
        }, 800);
    },

    dataURLtoBlob(dataURL) {
        const parts = dataURL.split(',');
        const mime = parts[0].match(/:(.*?);/)[1];
        const bstr = atob(parts[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) u8arr[n] = bstr.charCodeAt(n);
        return new Blob([u8arr], { type: mime });
    }
};
