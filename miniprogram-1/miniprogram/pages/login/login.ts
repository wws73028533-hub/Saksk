// 登录页面
import { wechatLogin } from '../../utils/auth';
import { api } from '../../utils/api';

Page({
  data: {
    mode: 'wechat' as 'wechat' | 'password' | 'email',
    loading: false,
    username: '',
    password: '',
    email: '',
    code: '',
    codeSending: false,
    countdown: 60
  },

  async onLoad() {
    // 避免“旧 token 已失效，但仍在 storage 导致一直跳首页又被 401 踢回”的循环：先轻量校验 token
    const token = wx.getStorageSync('token');
    if (!token) return;

    try {
      await api.getSubjects();
      wx.reLaunch({ url: '/pages/index/index' });
    } catch (err: any) {
      // 401：token 无效，清理后留在登录页
      if (err && err.statusCode === 401) {
        wx.removeStorageSync('token');
        wx.removeStorageSync('userInfo');
        return;
      }
      // 其它错误：不阻塞用户（可能是网络波动），仍按“已登录”处理
      wx.reLaunch({ url: '/pages/index/index' });
    }
  },

  // 微信登录
  async handleLogin() {
    if (this.data.loading) return;
    
    this.setData({ loading: true });
    try {
      const result = await wechatLogin();
      if (result === 'need_bind') {
        wx.reLaunch({ url: '/pages/wechat-bind/wechat-bind' });
        return;
      }

      wx.showToast({ title: '登录成功', icon: 'success' });

      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(() => {
          wx.reLaunch({
            url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
          });
        }, 600);
        return;
      }

      // 跳转到首页，使用reLaunch确保页面重新加载
      setTimeout(() => {
        wx.reLaunch({ url: '/pages/index/index' });
      }, 600);
    } catch (err: any) {
      console.error('登录失败:', err);
      const errorMsg = (err && (err.message || err.errMsg)) || '登录失败，请稍后重试';
      wx.showToast({ 
        title: errorMsg, 
        icon: 'none',
        duration: 3000
      });
      this.setData({ loading: false });
    }
  },

  // 手动登录按钮
  onLoginTap() {
    this.handleLogin();
  },

  onSwitchMode(e: any) {
    const mode = e.currentTarget.dataset.mode;
    if (mode !== 'wechat' && mode !== 'password' && mode !== 'email') return;
    this.setData({ mode });
  },

  onUsernameInput(e: any) {
    this.setData({ username: e.detail.value || '' });
  },

  onPasswordInput(e: any) {
    this.setData({ password: e.detail.value || '' });
  },

  onEmailInput(e: any) {
    this.setData({ email: e.detail.value || '' });
  },

  onCodeInput(e: any) {
    this.setData({ code: e.detail.value || '' });
  },

  async onPasswordLoginTap() {
    if (this.data.loading) return;
    const username = (this.data.username || '').trim();
    const password = this.data.password || '';
    if (!username || !password) {
      wx.showToast({ title: '请输入账号和密码', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    try {
      const data: any = await api.miniPasswordLogin(username, password);
      if (!data || !data.token) throw new Error('登录返回异常');
      wx.setStorageSync('token', data.token);
      if (data.user_info) wx.setStorageSync('userInfo', data.user_info);

      wx.showToast({ title: '登录成功', icon: 'success' });
      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(() => {
          wx.reLaunch({
            url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
          });
        }, 600);
        return;
      }
      setTimeout(() => wx.reLaunch({ url: '/pages/index/index' }), 600);
    } catch (e: any) {
      wx.showToast({ title: (e && (e.message || e.errMsg)) || '登录失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  async onSendCodeTap() {
    if (this.data.codeSending || this.data.loading) return;
    const email = (this.data.email || '').trim();
    if (!email) {
      wx.showToast({ title: '请输入邮箱', icon: 'none' });
      return;
    }
    try {
      await api.miniSendEmailLoginCode(email);
      wx.showToast({ title: '已发送', icon: 'success' });
      this.startCountdown();
    } catch (e: any) {
      wx.showToast({ title: (e && (e.message || e.errMsg)) || '发送失败', icon: 'none' });
    }
  },

  startCountdown() {
    this.setData({ codeSending: true, countdown: 60 });
    const timer = setInterval(() => {
      const next = (this.data.countdown || 0) - 1;
      if (next <= 0) {
        clearInterval(timer);
        this.setData({ codeSending: false, countdown: 60 });
        return;
      }
      this.setData({ countdown: next });
    }, 1000);
  },

  async onEmailLoginTap() {
    if (this.data.loading) return;
    const email = (this.data.email || '').trim();
    const code = (this.data.code || '').trim();
    if (!email || !code) {
      wx.showToast({ title: '请输入邮箱和验证码', icon: 'none' });
      return;
    }

    this.setData({ loading: true });
    try {
      const data: any = await api.miniEmailLogin(email, code);
      if (!data || !data.token) throw new Error('登录返回异常');
      wx.setStorageSync('token', data.token);
      if (data.user_info) wx.setStorageSync('userInfo', data.user_info);

      wx.showToast({ title: '登录成功', icon: 'success' });
      const pending = wx.getStorageSync('pendingWebLogin');
      if (pending && pending.sid && pending.nonce) {
        setTimeout(() => {
          wx.reLaunch({
            url: `/pages/web-login/web-login?sid=${encodeURIComponent(pending.sid)}&nonce=${encodeURIComponent(pending.nonce)}`
          });
        }, 600);
        return;
      }
      setTimeout(() => wx.reLaunch({ url: '/pages/index/index' }), 600);
    } catch (e: any) {
      wx.showToast({ title: (e && (e.message || e.errMsg)) || '登录失败', icon: 'none' });
      this.setData({ loading: false });
    }
  }
});
