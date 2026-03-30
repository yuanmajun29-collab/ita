/**
 * API 请求封装
 */

const API = {
    BASE_URL: '',

    // 检查后端是否可用
    async checkHealth() {
        try {
            const resp = await fetch(`${this.BASE_URL}/api/health`, {
                method: 'GET',
                timeout: 3000
            });
            return resp.ok;
        } catch (e) {
            return false;
        }
    },

    /**
     * 上传图片进行肤色分析
     * @param {File|Blob} imageFile - 图片文件
     * @returns {Promise<Object>} 分析结果
     */
    async analyzeImage(imageFile) {
        const formData = new FormData();
        formData.append('file', imageFile, 'photo.jpg');

        try {
            const resp = await fetch(`${this.BASE_URL}/api/analyze`, {
                method: 'POST',
                body: formData
            });

            const data = await resp.json();
            return data;
        } catch (e) {
            return {
                success: false,
                message: `网络错误: ${e.message}`
            };
        }
    },

    /**
     * 获取历史记录
     */
    async getHistory() {
        try {
            const resp = await fetch(`${this.BASE_URL}/api/history`);
            return await resp.json();
        } catch (e) {
            return { success: false, message: '网络错误' };
        }
    }
};
