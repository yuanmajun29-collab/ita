/**
 * 摄像头控制模块
 */

const Camera = {
    stream: null,
    facingMode: 'environment', // 默认后置摄像头
    videoEl: null,
    placeholderEl: null,

    /**
     * 初始化摄像头
     */
    async init() {
        this.videoEl = document.getElementById('camera-preview');
        this.placeholderEl = document.getElementById('camera-placeholder');

        try {
            await this.start();
        } catch (e) {
            console.error('摄像头启动失败:', e);
            this.placeholderEl.innerHTML = '<p>📷</p><p>无法访问摄像头</p><p style="font-size:12px;color:#999;">请使用"相册"按钮选择图片</p>';
            this._enableGalleryOnly();
        }
    },

    /**
     * 启动摄像头
     */
    async start() {
        // 先停止已有的流
        this.stop();

        const constraints = {
            video: {
                facingMode: this.facingMode,
                width: { ideal: 1920 },
                height: { ideal: 1080 }
            }
        };

        this.stream = await navigator.mediaDevices.getUserMedia(constraints);
        this.videoEl.srcObject = this.stream;
        this.videoEl.style.display = 'block';
        this.placeholderEl.style.display = 'none';

        document.getElementById('btn-capture').disabled = false;
    },

    /**
     * 停止摄像头
     */
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    },

    /**
     * 切换前后摄像头
     */
    async switchCamera() {
        this.facingMode = this.facingMode === 'environment' ? 'user' : 'environment';
        try {
            await this.start();
        } catch (e) {
            // 该设备可能只有一个摄像头
            this.facingMode = this.facingMode === 'environment' ? 'user' : 'environment';
            showToast('该设备不支持切换摄像头');
        }
    },

    /**
     * 拍照
     */
    capture() {
        const canvas = document.getElementById('photo-canvas');
        const ctx = canvas.getContext('2d');

        // 使用视频的实际分辨率
        canvas.width = this.videoEl.videoWidth || 1280;
        canvas.height = this.videoEl.videoHeight || 720;

        ctx.drawImage(this.videoEl, 0, 0, canvas.width, canvas.height);

        // 压缩到最大 1920px
        return this._compressCanvas(canvas, 1920);
    },

    /**
     * 从相册选择
     */
    pick() {
        document.getElementById('gallery-input').click();
    },

    /**
     * 压缩图片
     */
    _compressCanvas(canvas, maxSize) {
        return new Promise((resolve) => {
            let { width, height } = canvas;

            if (width > maxSize || height > maxSize) {
                if (width > height) {
                    height = Math.round(height * maxSize / width);
                    width = maxSize;
                } else {
                    width = Math.round(width * maxSize / height);
                    height = maxSize;
                }
            }

            const out = document.createElement('canvas');
            out.width = width;
            out.height = height;
            out.getContext('2d').drawImage(canvas, 0, 0, width, height);

            out.toBlob((blob) => {
                resolve({ blob, dataUrl: out.toDataURL('image/jpeg', 0.85) });
            }, 'image/jpeg', 0.85);
        });
    },

    /**
     * 从文件压缩
     */
    compressFile(file, maxSize = 1920) {
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    let w = img.width, h = img.height;

                    if (w > maxSize || h > maxSize) {
                        if (w > h) {
                            h = Math.round(h * maxSize / w);
                            w = maxSize;
                        } else {
                            w = Math.round(w * maxSize / h);
                            h = maxSize;
                        }
                    }

                    canvas.width = w;
                    canvas.height = h;
                    canvas.getContext('2d').drawImage(img, 0, 0, w, h);

                    canvas.toBlob((blob) => {
                        resolve({ blob, dataUrl: canvas.toDataURL('image/jpeg', 0.85) });
                    }, 'image/jpeg', 0.85);
                };
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
        });
    },

    /**
     * 仅相册模式（摄像头不可用）
     */
    _enableGalleryOnly() {
        document.getElementById('btn-capture').disabled = true;
    }
};
