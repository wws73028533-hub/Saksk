// index.ts
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';
import { themeManager } from '../../utils/theme';

function parseQuery(raw: string): Record<string, string> {
  const out: Record<string, string> = {};
  if (!raw) return out;
  const parts = raw.split('&');
  for (const part of parts) {
    const kv = part.split('=');
    const k = kv[0];
    const v = kv[1];
    if (!k) continue;
    out[decodeURIComponent(k)] = decodeURIComponent(v || '');
  }
  return out;
}

function parseCompactBindScene(scene: string): { sid: string; nonce: string } | null {
  const s = (scene || '').trim();
  // B + sid(16 hex) + nonce(8 hex)
  if (!/^B[0-9a-fA-F]{24}$/.test(s)) return null;
  const sid = s.slice(1, 17);
  const nonce = s.slice(17, 25);
  return { sid, nonce };
}

Page({
  data: {
    stats: {
      total: 0,
      favorites: 0,
      mistakes: 0
    },
    lastSession: null as any,
    loading: false,
    userInfo: null as any
  },

  onLoad(options: Record<string, any>) {
    // 兼容后端生成二维码使用 index 作为落地页（避免 41030 invalid page）
    let sid = (options && options.sid ? String(options.sid) : '').trim();
    let nonce = (options && (options.nonce || options.n) ? String(options.nonce || options.n) : '').trim();
    const scene = (options && options.scene ? String(options.scene) : '').trim();
    if ((!sid || !nonce) && scene) {
      const decoded = decodeURIComponent(scene);
      const compactBind = parseCompactBindScene(decoded);
      if (compactBind) {
        wx.navigateTo({
          url: `/pages/web-bind/web-bind?sid=${encodeURIComponent(compactBind.sid)}&nonce=${encodeURIComponent(compactBind.nonce)}`
        });
        return;
      }
      const q = parseQuery(decoded);
      sid = (q.sid || '').trim();
      nonce = (q.n || q.nonce || '').trim();
    }

    if (sid && nonce) {
      wx.setStorageSync('pendingWebLogin', { sid, nonce, ts: Date.now() });
      const token = wx.getStorageSync('token');
      if (token) {
        wx.navigateTo({ url: `/pages/web-login/web-login?sid=${encodeURIComponent(sid)}&nonce=${encodeURIComponent(nonce)}` });
      } else {
        wx.redirectTo({ url: '/pages/login/login' });
      }
      return;
    }
  },

  onShow() {
    // 统一走鉴权&加载，避免 onLoad/onShow 重复触发导致并发请求
    this.checkAuthAndLoad();
  },

  // 检查认证并加载数据
  async checkAuthAndLoad() {
    if (!checkLogin()) {
      // 未登录，跳转到登录页（不在首页自动登录，让用户手动登录）
      console.log('未登录，跳转到登录页');
        wx.redirectTo({
          url: '/pages/login/login'
        });
        return;
    } else {
      const userInfo = wx.getStorageSync('userInfo');
      this.setData({ userInfo });
      this.loadHome();
    }
  },

  // 加载首页数据（统计 + 上次练习）
  async loadHome() {
    // 再次检查token，确保token存在
    if (!checkLogin()) {
      console.log('loadData: token不存在，跳转到登录页');
      wx.redirectTo({
        url: '/pages/login/login'
      });
      return;
    }
    
    this.setData({ loading: true });
    try {
      const results = await Promise.all([
        api.getQuestionsCount({ subject: 'all' }),
        api.getUserCounts({ subject: 'all' })
      ]);

      const countData = results[0];
      const userCounts = results[1];

      const total = (countData && (countData as any).count) ? (countData as any).count : 0;
      const favorites = (userCounts && (userCounts as any).favorites) ? (userCounts as any).favorites : 0;
      const mistakes = (userCounts && (userCounts as any).mistakes) ? (userCounts as any).mistakes : 0;

      // 上次练习（云端优先，本地兜底）
      const remote = await this.safeGetProgress('last_practice_session');
      const local = this.safeParseStorage(wx.getStorageSync('last_practice_session'));
      const merged = this.pickLatestSession(local, remote);
      const lastSession = this.normalizeSession(merged);
      
      this.setData({
        stats: { total, favorites, mistakes },
        lastSession,
        loading: false
      });
    } catch (err: any) {
      console.error('加载数据失败:', err);
      const errorMsg = (err && err.message) || '加载失败';
      // 如果是401错误，清除token并跳转到登录页（但不要立即重新登录，避免循环）
      if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期') || errorMsg.includes('unauthorized')) {
        console.log('401错误，清除token并跳转到登录页');
        wx.removeStorageSync('token');
        wx.removeStorageSync('userInfo');
        // 使用reLaunch避免返回时再次触发
        wx.reLaunch({
          url: '/pages/login/login'
        });
        return;
      }
      wx.showToast({ title: errorMsg, icon: 'none' });
      this.setData({ loading: false });
    }
  },

  async safeGetProgress(key: string): Promise<any | null> {
    if (!key) return null;
    try {
      return await api.getProgress(key);
    } catch (e) {
      return null;
    }
  },

  safeParseStorage(val: any): any | null {
    if (!val) return null;
    if (typeof val === 'string') {
      try {
        return JSON.parse(val);
      } catch (e) {
        return null;
      }
    }
    if (typeof val === 'object') return val;
    return null;
  },

  pickLatestSession(a: any, b: any): any | null {
    if (!a && !b) return null;
    if (a && !b) return a;
    if (!a && b) return b;
    const ta = Number(a && a.timestamp) || 0;
    const tb = Number(b && b.timestamp) || 0;
    return tb >= ta ? b : a;
  },

  normalizeSession(raw: any): any | null {
    if (!raw || typeof raw !== 'object') return null;
    const subject = (raw.subject || '').toString().trim();
    if (!subject) return null;

    const mode = (raw.mode || 'quiz').toString();
    const type = (raw.type || 'all').toString();
    const source = (raw.source || 'all').toString();
    const shuffleQuestions = raw.shuffle_questions === 1 || raw.shuffle_questions === '1' || raw.shuffle_questions === true;
    const shuffleOptions = raw.shuffle_options === 1 || raw.shuffle_options === '1' || raw.shuffle_options === true;
    const timestamp = Number(raw.timestamp) || 0;

    const modeText = mode === 'memo' ? '背题' : '刷题';
    const sourceText = source === 'favorites' ? '收藏' : source === 'mistakes' ? '错题' : '全部';
    const typeText = type === 'all' ? '全部题型' : type;
    const metaText = `${modeText} · ${sourceText} · ${typeText}`;

    return {
      subject,
      mode,
      type,
      source,
      shuffleQuestions,
      shuffleOptions,
      timestamp,
      timeText: this.formatTimestamp(timestamp),
      metaText
    };
  },

  formatTimestamp(ts: number): string {
    const t = Number(ts) || 0;
    if (!t) return '';
    try {
      const d = new Date(t);
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const hh = String(d.getHours()).padStart(2, '0');
      const mi = String(d.getMinutes()).padStart(2, '0');
      return `${mm}-${dd} ${hh}:${mi}`;
    } catch (e) {
      return '';
    }
  },

  onContinueTap() {
    const s = this.data.lastSession;
    if (!s || !s.subject) {
      wx.showToast({ title: '暂无上次练习记录', icon: 'none' });
      return;
    }

    const params: string[] = [];
    params.push(`subject=${encodeURIComponent(s.subject)}`);
    params.push(`mode=${encodeURIComponent(s.mode || 'quiz')}`);
    if (s.type && s.type !== 'all') params.push(`type=${encodeURIComponent(s.type)}`);
    if (s.source && s.source !== 'all') params.push(`source=${s.source}`);
    if (s.shuffleQuestions) params.push('shuffle_questions=1');
    if (s.shuffleOptions) params.push('shuffle_options=1');

    wx.navigateTo({ url: `/pages/quiz/quiz?${params.join('&')}` });
  },

  onGoSubjectsTap() {
    wx.switchTab({ url: '/pages/subjects/subjects' });
  },

  onToggleThemeTap() {
    themeManager.cycleMode();
    wx.showToast({ title: `主题：${themeManager.getModeName()}`, icon: 'none' });
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadHome().finally(() => wx.stopPullDownRefresh());
  }
});
