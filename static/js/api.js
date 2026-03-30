/**
 * API 请求封装
 */

const API = {
    // 后端 API 基地址（同源）
    baseUrl: '/api',

    // Demo 模式（后端不可用时使用）
    demo: false,

    /**
     * 上传图片进行肤色分析
     */
    async analyzeImage(blob) {
        const formData = new FormData();
        formData.append('file', blob, 'photo.jpg');

        try {
            const response = await fetch(`${this.baseUrl}/analyze`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || `请求失败 (${response.status})`);
            }

            this.demo = false;
            return await response.json();
        } catch (e) {
            // 后端不可用，使用 demo 模式
            console.warn('后端不可用，使用 Demo 模式:', e.message);
            this.demo = true;
            return this.getDemoResult();
        }
    },

    /**
     * 获取所有分类
     */
    async getCategories() {
        try {
            const response = await fetch(`${this.baseUrl}/categories`);
            if (response.ok) {
                return await response.json();
            }
        } catch (e) {
            // ignore
        }
        return null;
    },

    /**
     * Demo 结果（后端不可用时展示）
     */
    getDemoResult() {
        const demoResults = [
            { ita: 62.5, category: '浅色', category_id: 'very_light', fitzpatrick: ['I', 'II'], confidence: 0.91, lab: { L: 72.3, a: 8.5, b: 12.1 } },
            { ita: 38.2, category: '中等色', category_id: 'medium', fitzpatrick: ['II', 'III'], confidence: 0.85, lab: { L: 63.1, a: 11.2, b: 18.5 } },
            { ita: 18.7, category: '晒黑色', category_id: 'tanned', fitzpatrick: ['III', 'IV'], confidence: 0.88, lab: { L: 54.2, a: 14.8, b: 22.3 } },
            { ita: -5.3, category: '棕色', category_id: 'brown', fitzpatrick: ['IV', 'V'], confidence: 0.82, lab: { L: 42.5, a: 16.1, b: 28.7 } },
        ];

        const demo = demoResults[Math.floor(Math.random() * demoResults.length)];
        return {
            success: true,
            ita: demo.ita,
            category: demo.category,
            category_id: demo.category_id,
            description: SKIN_CATEGORIES_DEMO[demo.category_id]?.description || '',
            fitzpatrick: demo.fitzpatrick,
            uv_advice: SKIN_CATEGORIES_DEMO[demo.category_id]?.uv_advice || '',
            confidence: demo.confidence,
            lab: demo.lab,
            calibrated: false,
            message: 'Demo 模式（后端未连接）',
            timestamp: new Date().toISOString()
        };
    },

    /**
     * 健康检查
     */
    async healthCheck() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }
};

// Demo 分类数据
const SKIN_CATEGORIES_DEMO = {
    very_light: {
        description: '非常白皙的肤色，容易晒伤',
        uv_advice: '皮肤对紫外线非常敏感，外出请做好充分防晒（SPF50+），限制日晒时间。'
    },
    medium: {
        description: '白皙到橄榄色，适度日晒会变棕',
        uv_advice: '皮肤对紫外线较敏感，建议使用 SPF30+ 防晒，可适度日光照射补充维D。'
    },
    tanned: {
        description: '日晒后偏棕，不易晒伤',
        uv_advice: '皮肤有一定耐受性，仍建议 SPF15+ 防晒，适合短时间日光浴。'
    },
    brown: {
        description: '天然棕褐色，不易晒伤',
        uv_advice: '皮肤对紫外线较耐受，日常防晒 SPF15 即可，自然光照可充分补充维D。'
    },
    dark: {
        description: '深棕色至黑色，极少晒伤',
        uv_advice: '皮肤对紫外线耐受性较强，但仍需适当防护。注意检查皮肤有无异常变化。'
    }
};
