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

function parseCompactScene(scene: string): { sid: string; nonce: string } | null {
  const s = (scene || '').trim();
  // B + sid(16 hex) + nonce(8 hex)
  if (!/^B[0-9a-fA-F]{24}$/.test(s)) return null;
  const sid = s.slice(1, 17);
  const nonce = s.slice(17, 25);
  return { sid, nonce };
}

Page({
  data: {
    sid: '',
    nonce: '',
    loading: false,
    done: false,
    error: ''
  },

  onLoad(options: Record<string, string>) {
    let sid = (options.sid || '').trim();
    let nonce = (options.nonce || options.n || '').trim();

    const scene = (options.scene || '').trim();
    if ((!sid || !nonce) && scene) {
      const decoded = decodeURIComponent(scene);
      const compact = parseCompactScene(decoded);
      if (compact) {
        sid = compact.sid;
        nonce = compact.nonce;
      } else {
        const q = parseQuery(decoded);
        sid = (q.sid || '').trim();
        nonce = (q.n || q.nonce || '').trim();
      }
    }

    this.setData({ sid, nonce });
  },

  async onConfirm() {
    if (this.data.loading || this.data.done) return;
    this.setData({ loading: true, error: '' });
    try {
      if (!this.data.sid || !this.data.nonce) {
        this.setData({ error: '参数缺失，请重新扫码' });
        return;
      }

      const code = await new Promise<string>((resolve, reject) => {
        wx.login({
          success: (res) => (res.code ? resolve(res.code) : reject(new Error('获取微信code失败'))),
          fail: () => reject(new Error('获取微信code失败'))
        });
      });

      await api.webWechatBindConfirm(this.data.sid, this.data.nonce, code);
      this.setData({ done: true });
      wx.showToast({ title: '绑定成功', icon: 'success' });
      setTimeout(() => wx.reLaunch({ url: '/pages/index/index' }), 800);
    } catch (e: any) {
      const msg = (e && (e.message || e.errMsg)) || '绑定失败';
      this.setData({ error: msg });
    } finally {
      this.setData({ loading: false });
    }
  },

  onCancel() {
    wx.reLaunch({ url: '/pages/index/index' });
  }
});

