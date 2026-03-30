/**
 * 摄像头控制模块
 */

const Camera = {
    stream: null,
    videoElement: null,
    canvasElement: null,

    init() {
        this.videoElement = document.getElementById('camera-preview');
        this.canvasElement = document.getElementById('camera-canvas');
    },

    /**
     * 打开后置摄像头
     */
    async open() {
        this.init();

        try {
            // 优先使用后置摄像头
            const constraints = {
                video: {
                    facingMode: { ideal: 'environment' },
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.stream;
            return true;
        } catch (e) {
            console.error('摄像头打开失败:', e);

            // 退而求其次用任意摄像头
            try {
                const fallback = {
                    video: { width: { ideal: 1920 }, height: { ideal: 1080 } },
                    audio: false
                };
                this.stream = await navigator.mediaDevices.getUserMedia(fallback);
                this.videoElement.srcObject = this.stream;
                return true;
            } catch (e2) {
                console.error('摄像头不可用:', e2);
                return false;
            }
        }
    },

    /**
     * 拍照
     * @returns {string} Base64 图片数据
     */
    capture() {
        const video = this.videoElement;
        const canvas = this.canvasElement;

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        // 压缩到最大 1920px
        const maxSize = 1920;
        let { width, height } = canvas;

        if (width > maxSize || height > maxSize) {
            const ratio = Math.min(maxSize / width, maxSize / height);
            width = Math.round(width * ratio);
            height = Math.round(height * ratio);
        }

        // 创建临时 canvas 进行压缩
        const tmpCanvas = document.createElement('canvas');
        tmpCanvas.width = width;
        tmpCanvas.height = height;
        const tmpCtx = tmpCanvas.getContext('2d');
        tmpCtx.drawImage(canvas, 0, 0, width, height);

        return tmpCanvas.toDataURL('image/jpeg', 0.85);
    },

    /**
     * 关闭摄像头
     */
    close() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
    },

    /**
     * 将 Base64 转换为 Blob
     */
    dataURLtoBlob(dataURL) {
        const parts = dataURL.split(',');
        const mime = parts[0].match(/:(.*?);/)[1];
        const bstr = atob(parts[1]);
        let n = bstr.length;
        const u8arr = new Uint8Array(n);
        while (n--) {
            u8arr[n] = bstr.charCodeAt(n);
        }
        return new Blob([u8arr], { type: mime });
    }
};
