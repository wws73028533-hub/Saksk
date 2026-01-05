// API基础配置
// TODO: 请修改为实际的后端API地址
// 开发环境示例: 'http://localhost:5000/api' 或 'http://192.168.31.74:5000/api'（微信小程序需要使用IP地址）
// 生产环境示例: 'https://your-actual-domain.com/api'
const API_BASE_URL = 'http://192.168.31.74:5000/api';  // 后端API地址，微信小程序需要使用本机IP而非localhost
const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '');

export function getApiOrigin(): string {
  return API_ORIGIN;
}

// 将后端存储的相对路径（如 question_images/xxx.png）转换为可访问的完整 URL
export function resolveUploadUrl(input: any): string {
  if (input == null) return '';
  const raw = String(input).trim();
  if (!raw || raw === '[]') return '';
  if (/^https?:\/\//i.test(raw)) return raw;

  if (raw.startsWith('/uploads/')) return `${API_ORIGIN}${raw}`;
  if (raw.startsWith('uploads/')) return `${API_ORIGIN}/${raw}`;
  if (raw.startsWith('/')) return `${API_ORIGIN}${raw}`;

  // 默认认为存放在 /uploads 下（如 question_images/...）
  return `${API_ORIGIN}/uploads/${raw}`;
}

// 兼容 image_path 可能为：单路径字符串、JSON 数组字符串、数组
export function normalizeImageUrls(imagePath: any): string[] {
  if (imagePath == null) return [];

  if (Array.isArray(imagePath)) {
    return imagePath
      .map((p) => resolveUploadUrl(p))
      .filter((p) => typeof p === 'string' && p.length > 0);
  }

  const raw = String(imagePath).trim();
  if (!raw || raw === '[]') return [];

  if (raw.startsWith('[')) {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed
          .map((p) => resolveUploadUrl(p))
          .filter((p) => typeof p === 'string' && p.length > 0);
      }
      if (typeof parsed === 'string') {
        const url = resolveUploadUrl(parsed);
        return url ? [url] : [];
      }
    } catch (e) {
      // 忽略 JSON 解析失败，走单路径兜底
    }
  }

  const url = resolveUploadUrl(raw);
  return url ? [url] : [];
}

// 请求封装
function request<T = any>(
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  data?: any
): Promise<T> {
  return new Promise((resolve, reject) => {
    // 获取token
    const token = wx.getStorageSync('token') || '';
    // 记录本次请求使用的 token，避免“旧请求的 401 把新 token 清掉”导致登录循环
    const tokenAtRequest = token;
    
    // 调试日志
    if (url.includes('/quiz/subjects')) {
      console.log('API请求token状态:', token ? `有token(${token.substring(0, 20)}...)` : '无token');
    }
    
    // GET请求将data作为query参数（微信小程序会自动处理，但为了明确性我们也可以手动处理）
    wx.request({
      url: `${API_BASE_URL}${url}`,
      method,
      data,
      header: {
        'Content-Type': 'application/json',
        'Authorization': tokenAtRequest ? `Bearer ${tokenAtRequest}` : ''
      },
      success: (res) => {
        console.log(`API请求 ${method} ${url}:`, res.statusCode, res.data);
        if (res.statusCode === 200) {
          const result = res.data as { status: string; data?: T; message?: string; [key: string]: any };
          if (result.status === 'success') {
            // 如果有data字段，返回data；否则返回整个result（除了status字段）
            if (result.data !== undefined) {
              resolve(result.data as T);
            } else {
              // 返回除了status之外的所有字段
              const rest: any = Object.assign({}, result);
              delete rest.status;
              resolve(rest as T);
            }
          } else {
            console.error('API返回错误状态:', result);
            reject(new Error(result.message || '请求失败'));
          }
        } else if (res.statusCode === 401) {
          const errorData = res.data as { message?: string; error?: string; [key: string]: any };
          const errorMsg = (errorData && (errorData.message || errorData.error)) || '登录已过期';

          // 如果本次请求使用的是旧 token，而当前 storage 里已经是新 token，则认为是“旧请求 401”
          // 此时不要清 token / 不要跳转，避免把新 token 清掉导致“始终登录不上”
          const latestToken = wx.getStorageSync('token') || '';
          if (latestToken && latestToken !== tokenAtRequest) {
            console.warn('401来自旧请求，忽略登出:', url);
            const err: any = new Error(errorMsg);
            err.statusCode = 401;
            err.response = res.data;
            reject(err);
            return;
          }

          // 先检查当前页面，避免循环跳转
          const pages = getCurrentPages();
          const currentPage = pages[pages.length - 1];
          const currentRoute = currentPage ? currentPage.route : '';

          // 清理本地登录态（token 已经无效）
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');

          // 如果不在登录页，跳转到登录页
          if (!currentRoute.includes('login')) {
            console.log('401错误，清除token并跳转到登录页');
            wx.reLaunch({ url: '/pages/login/login' });
          }

          const err: any = new Error(errorMsg);
          err.statusCode = 401;
          err.response = res.data;
          reject(err);
        } else if (res.statusCode === 429) {
          // 请求过于频繁
          const errorMsg = '请求过于频繁，请稍后再试';
          console.error('API请求限流:', res.statusCode);
          reject(new Error(errorMsg));
        } else {
          // 尝试获取错误信息
          const errorData = res.data as { message?: string; error?: string };
          const errorMsg =
            (errorData && (errorData.message || errorData.error)) || `请求失败: ${res.statusCode}`;
          console.error('API请求失败:', res.statusCode, errorMsg);
          reject(new Error(errorMsg));
        }
      },
      fail: (err) => {
        console.error('网络请求失败:', err);
        // 处理网络错误
        const errorMsg = err.errMsg || err.message || '网络请求失败，请检查网络连接';
        reject(new Error(errorMsg));
      }
    });
  });
}

// 导出API方法
export const api = {
  // 微信登录
  wechatLogin: (code: string, userInfo?: any, allowCreate: boolean = true) =>
    request('/wechat/login', 'POST', { code, user_info: userInfo, allow_create: allowCreate }),

  // 微信：未绑定时创建新账号
  wechatCreate: (wechatTempToken: string) =>
    request('/wechat/create', 'POST', { wechat_temp_token: wechatTempToken }),

  // 微信：绑定已有账号（邮箱验证码）
  wechatBindSendCode: (wechatTempToken: string, email: string) =>
    request('/wechat/bind/send_code', 'POST', { wechat_temp_token: wechatTempToken, email }),

  wechatBindPassword: (wechatTempToken: string, account: string, password: string) =>
    request('/wechat/bind', 'POST', {
      wechat_temp_token: wechatTempToken,
      bind_mode: 'password',
      account,
      password
    }),

  wechatBindEmailCode: (wechatTempToken: string, email: string, code: string) =>
    request('/wechat/bind', 'POST', {
      wechat_temp_token: wechatTempToken,
      bind_mode: 'email_code',
      email,
      code
    }),

  // Web 扫码登录：小程序确认
  webLoginConfirm: (sid: string, nonce: string) =>
    request('/web_login/confirm', 'POST', { sid, nonce }),

  // Web 账号管理：绑定微信（小程序确认，使用 wx.login code）
  webWechatBindConfirm: (sid: string, nonce: string, code: string) =>
    request('/wechat/bind_confirm', 'POST', { sid, nonce, code }),

  // === 小程序：账号登录（JWT） ===
  miniPasswordLogin: (username: string, password: string) =>
    request('/mini/login', 'POST', { username, password }),

  miniSendEmailLoginCode: (email: string) =>
    request('/mini/email/send-login-code', 'POST', { email }),

  miniEmailLogin: (email: string, code: string) =>
    request('/mini/email/login', 'POST', { email, code }),
  
  // 获取科目列表
  getSubjects: () => request('/quiz/subjects', 'GET'),
  
  // 获取题目列表
  getQuestions: (params: {
    subject?: string;
    q_type?: string;
    mode?: string;
    source?: string;
    shuffle_questions?: string | number;
    shuffle_options?: string | number;
    page?: number;
    per_page?: number;
  }) => request('/quiz/questions', 'GET', params),
  
  // 获取题目详情
  getQuestionDetail: (id: number) => request(`/quiz/questions/${id}`, 'GET'),

  // 搜索题目（用于小程序搜索页）
  searchQuestions: (params: {
    keyword: string;
    subject?: string;
    q_type?: string;
    type?: string; // 兼容字段
    page?: number;
    per_page?: number;
  }) => request('/quiz/search', 'GET', params),
  
  // 记录答题结果
  recordResult: (questionId: number, isCorrect: boolean) =>
    request('/quiz/record_result', 'POST', {
      question_id: questionId,
      is_correct: isCorrect
    }),
  
  // 切换收藏
  toggleFavorite: (questionId: number) =>
    request('/quiz/favorite', 'POST', { question_id: questionId }),
  
  // 获取科目详情信息
  getSubjectInfo: (subject: string) =>
    request(`/quiz/subjects/${encodeURIComponent(subject)}/info`, 'GET'),
  
  // 获取题目数量统计（支持范围和题型筛选）
  getQuestionsCount: (params?: {
    subject?: string;
    type?: string;
    source?: string;
  }) => request('/quiz/questions/count', 'GET', params || {}),
  
  // 获取用户收藏和错题数量（支持题型筛选）
  getUserCounts: (params: {
    subject?: string;
    type?: string;
  }) => request('/quiz/questions/user_counts', 'GET', params),

  // 获取云端进度（与 Web 端 /api/progress 互通）
  getProgress: (key: string) => request('/progress', 'GET', { key }),

  // 保存云端进度（与 Web 端 /api/progress 互通）
  saveProgress: (key: string, data: any) => request('/progress', 'POST', { key, data }),

  // 删除云端进度（与 Web 端 /api/progress 互通）
  deleteProgress: (key: string) => request(`/progress?key=${encodeURIComponent(key)}`, 'DELETE'),

  // === 模拟考试（与 Web /api/exams 互通） ===
  createExam: (data: {
    subject: string;
    duration: number;
    types: Record<string, number>;
    scores?: Record<string, number>;
  }) => request('/exams/create', 'POST', data),

  getExam: (examId: number) => request(`/exams/${examId}`, 'GET'),

  saveExamDraft: (examId: number, answers: Array<{ question_id: number; user_answer: string }>) =>
    request('/exams/save_draft', 'POST', { exam_id: examId, answers }),

  submitExam: (examId: number, answers: Array<{ question_id: number; user_answer: string }>) =>
    request('/exams/submit', 'POST', { exam_id: examId, answers }),

  examToMistakes: (examId: number) => request(`/exams/${examId}/mistakes`, 'POST', {})
};
