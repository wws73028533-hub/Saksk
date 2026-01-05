import { api } from '../../utils/api';

Page({
  data: {
    step: 'choice' as 'choice' | 'bind',
    mode: 'password' as 'password' | 'email_code',
    wechatTempToken: '',

    account: '',
    password: '',

    email: '',
    code: '',

    loadingCreate: false,
    loadingBind: false,
    codeSending: false,
    loadingAny: false,
    actionDisabled: false,
    sendCodeDisabled: false,
    countdown: 60,
    error: ''
  },

  setLoading(partial: Partial<any>) {
    const next = { ...this.data, ...partial };
    const loadingAny = !!(next.loadingCreate || next.loadingBind || next.codeSending);
    const actionDisabled = !!(next.loadingCreate || next.loadingBind);
    const sendCodeDisabled = !!(next.loadingBind || next.codeSending);
    this.setData({ ...partial, loadingAny, actionDisabled, sendCodeDisabled });
  },

  onLoad() {
    const token = wx.getStorageSync('wechatTempToken') || '';
    if (!token) {
      this.setData({ error: '缺少临时票据，请重新登录' });
      return;
    }
    this.setData({ wechatTempToken: token });
  },

  setMode(e: any) {
    const mode = e.currentTarget.dataset.mode;
    if (mode !== 'password' && mode !== 'email_code') return;
    this.setData({ mode, error: '' });
  },

  onGoBind() {
    this.setData({ step: 'bind', error: '' });
  },

  onBack() {
    this.setData({ step: 'choice', error: '' });
  },

  onAccount(e: any) {
    this.setData({ account: e.detail.value || '' });
  },

  onPassword(e: any) {
    this.setData({ password: e.detail.value || '' });
  },

  onEmail(e: any) {
    this.setData({ email: e.detail.value || '' });
  },

  onCode(e: any) {
    this.setData({ code: e.detail.value || '' });
  },

  async onCreate() {
    if (this.data.loadingCreate) return;
    this.setLoading({ loadingCreate: true, error: '' });
    try {
      const res: any = await api.wechatCreate(this.data.wechatTempToken);
      if (!res || !res.token) throw new Error('返回数据异常');
      wx.setStorageSync('token', res.token);
      if (res.user_info) wx.setStorageSync('userInfo', res.user_info);
      wx.removeStorageSync('wechatTempToken');
      wx.showToast({ title: '已创建', icon: 'success' });
      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(
          () =>
            wx.reLaunch({
              url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
            }),
          600
        );
      } else {
        setTimeout(() => wx.reLaunch({ url: '/pages/index/index' }), 600);
      }
    } catch (e: any) {
      const msg = (e && (e.message || e.errMsg)) || '创建失败';
      this.setData({ error: msg });
    } finally {
      this.setLoading({ loadingCreate: false });
    }
  },

  async onSendCode() {
    if (this.data.codeSending || this.data.loadingBind) return;
    if (!this.data.email) {
      this.setData({ error: '请输入邮箱' });
      return;
    }
    this.setData({ error: '' });
    try {
      await api.wechatBindSendCode(this.data.wechatTempToken, this.data.email);
      wx.showToast({ title: '已发送', icon: 'success' });
      this.startCountdown();
    } catch (e: any) {
      const msg = (e && (e.message || e.errMsg)) || '发送失败';
      this.setData({ error: msg });
    }
  },

  startCountdown() {
    this.setLoading({ codeSending: true, countdown: 60 });
    const timer = setInterval(() => {
      const next = (this.data.countdown || 0) - 1;
      if (next <= 0) {
        clearInterval(timer);
        this.setLoading({ codeSending: false, countdown: 60 });
        return;
      }
      this.setData({ countdown: next });
    }, 1000);
  },

  async onBind() {
    if (this.data.loadingBind) return;
    // 先校验，避免校验失败后按钮被锁死
    if (this.data.mode === 'password') {
      if (!this.data.account || !this.data.password) {
        this.setData({ error: '请输入账号和密码' });
        return;
      }
    } else {
      if (!this.data.email || !this.data.code) {
        this.setData({ error: '请输入邮箱和验证码' });
        return;
      }
    }

    this.setLoading({ loadingBind: true, error: '' });
    try {
      let res: any;
      if (this.data.mode === 'password') {
        res = await api.wechatBindPassword(this.data.wechatTempToken, this.data.account, this.data.password);
      } else {
        res = await api.wechatBindEmailCode(this.data.wechatTempToken, this.data.email, this.data.code);
      }

      if (!res || !res.token) throw new Error('返回数据异常');
      wx.setStorageSync('token', res.token);
      if (res.user_info) wx.setStorageSync('userInfo', res.user_info);
      wx.removeStorageSync('wechatTempToken');
      wx.showToast({ title: '已绑定', icon: 'success' });
      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(
          () =>
            wx.reLaunch({
              url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
            }),
          600
        );
      } else {
        setTimeout(() => wx.reLaunch({ url: '/pages/index/index' }), 600);
      }
    } catch (e: any) {
      const msg = (e && (e.message || e.errMsg)) || '绑定失败';
      this.setData({ error: msg });
    } finally {
      this.setLoading({ loadingBind: false });
    }
  }
});
