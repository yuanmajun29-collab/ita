/**
 * API 请求封装
 */

const API = {
    BASE_URL: '',

    async checkHealth() {
        try {
            const resp = await fetch(`${this.BASE_URL}/api/health`);
            return resp.ok;
        } catch (e) {
            return false;
        }
    },

    async analyzeImage(imageFile, lat, lon) {
        const formData = new FormData();
        formData.append('file', imageFile, 'photo.jpg');

        let url = `${this.BASE_URL}/api/analyze`;
        const params = [];
        if (lat) params.push(`lat=${lat}`);
        if (lon) params.push(`lon=${lon}`);
        if (params.length) url += '?' + params.join('&');

        try {
            const resp = await fetch(url, { method: 'POST', body: formData });
            return await resp.json();
        } catch (e) {
            return { success: false, message: `网络错误: ${e.message}` };
        }
    },

    async getHistory(limit = 20) {
        try {
            const resp = await fetch(`${this.BASE_URL}/api/history?limit=${limit}`);
            return await resp.json();
        } catch (e) {
            return { success: false, message: '网络错误' };
        }
    },

    async getTrend(days = 30) {
        try {
            const resp = await fetch(`${this.BASE_URL}/api/trend?days=${days}`);
            return await resp.json();
        } catch (e) {
            return { success: false, message: '网络错误' };
        }
    },

    async getUvAdvice(ita, fitzpatrick, uvIndex, lat, lon, month, hour, exposureTime) {
        const params = new URLSearchParams({
            ita, fitzpatrick
        });
        if (uvIndex !== undefined) params.append('uv_index', uvIndex);
        if (lat) params.append('lat', lat);
        if (lon) params.append('lon', lon);
        if (month) params.append('month', month);
        if (hour) params.append('hour', hour);
        if (exposureTime) params.append('exposure_time', exposureTime);

        try {
            const resp = await fetch(`${this.BASE_URL}/api/uv-advice?${params}`);
            return await resp.json();
        } catch (e) {
            return { success: false, message: '网络错误' };
        }
    }
};
