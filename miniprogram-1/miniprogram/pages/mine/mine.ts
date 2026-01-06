// mine.ts - 我的
import { api } from '../../utils/api';
import { checkLogin, logout } from '../../utils/auth';

Page({
  data: {
    userInfo: null as any,
    stats: {
      favorites: 0,
      mistakes: 0
    },
    loading: false
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    const userInfo = wx.getStorageSync('userInfo');
    this.setData({ userInfo });
    this.loadStats();
  },

  async loadStats() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const userCounts: any = await api.getUserCounts({ subject: 'all' });
      this.setData({
        stats: {
          favorites: userCounts.favorites || 0,
          mistakes: userCounts.mistakes || 0
        },
        loading: false
      });
    } catch (err: any) {
      console.error('加载用户统计失败:', err);
      wx.showToast({ title: (err && err.message) || '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onGoSubjectsTap() {
    wx.switchTab({ url: '/pages/subjects/subjects' });
  },

  onOpenLogsTap() {
    wx.navigateTo({ url: '/pages/logs/logs' });
  },

  onLogoutTap() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmText: '退出',
      confirmColor: '#FF3B30',
      success: (res) => {
        if (!res.confirm) return;
        logout();
        wx.reLaunch({ url: '/pages/login/login' });
      }
    });
  }
});

