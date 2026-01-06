import { api } from '../../utils/api';

function parseQuery(raw: string): Record<string, string> {
  const out: Record<string, string> = {};
  if (!raw) return out;
  const parts = raw.split('&');
  for (const part of parts) {
    const [k, v] = part.split('=');
    if (!k) continue;
    out[decodeURIComponent(k)] = decodeURIComponent(v || '');
  }
  return out;
}

Page({
  data: {
    sid: '',
    nonce: '',
    loading: false,
    error: ''
  },

  onLoad(options: Record<string, string>) {
    let sid = (options.sid || '').trim();
    let nonce = (options.nonce || options.n || '').trim();

    const scene = (options.scene || '').trim();
    if ((!sid || !nonce) && scene) {
      const decoded = decodeURIComponent(scene);
      const q = parseQuery(decoded);
      sid = (q.sid || '').trim();
      nonce = (q.n || q.nonce || '').trim();
    }

    this.setData({ sid, nonce });
  },

  onShow() {
    const token = wx.getStorageSync('token');
    if (!token && this.data.sid && this.data.nonce) {
      wx.setStorageSync('pendingWebLogin', { sid: this.data.sid, nonce: this.data.nonce, ts: Date.now() });
      wx.reLaunch({ url: '/pages/login/login' });
      return;
    }
  },

  async onConfirm() {
    if (this.data.loading) return;
    this.setData({ loading: true, error: '' });

    try {
      if (!this.data.sid || !this.data.nonce) {
        this.setData({ error: '参数缺失，请重新扫码' });
        return;
      }
      await api.webLoginConfirm(this.data.sid, this.data.nonce);
      wx.removeStorageSync('pendingWebLogin');
      wx.showToast({ title: '已确认', icon: 'success' });
      setTimeout(() => {
        wx.reLaunch({ url: '/pages/index/index' });
      }, 600);
    } catch (e: any) {
      const msg = (e && (e.message || e.errMsg)) || '确认失败';
      this.setData({ error: msg });
    } finally {
      this.setData({ loading: false });
    }
  },

  onCancel() {
    wx.removeStorageSync('pendingWebLogin');
    wx.reLaunch({ url: '/pages/index/index' });
  }
});

