// bank-detail.ts - 个人题库详情/刷题设置页
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    bankId: 0,
    bankInfo: {
      name: '',
      description: '',
      question_count: 0,
      is_public: false,
      owner_username: ''
    },
    myStats: {
      total_answered: 0,
      correct_count: 0,
      wrong_count: 0,
      favorite_count: 0,
      accuracy: 0
    },
    loading: false
  },

  onLoad(options: any) {
    const bankId = Number(options.id || 0);
    if (!bankId) {
      wx.showToast({ title: '题库参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }

    this.setData({ bankId });
    wx.showShareMenu({ withShareTicket: true });
    this.loadBankInfo();
  },

  onShow() {
    // 从刷题页返回后刷新统计
    if (this.data.bankId) {
      this.loadBankInfo();
    }
  },

  async loadBankInfo() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    this.setData({ loading: true });
    try {
      const results: any[] = await Promise.all([
        api.getBankDetail(this.data.bankId),
        api.getBankMyStats(this.data.bankId),
        api.getBankUserCounts(this.data.bankId, {})
      ]);

      // 处理详情数据 - 兼容 {data: {...}} 和直接返回对象两种格式
      const detailRes = results[0];
      const statsRes = results[1];
      const countsRes = results[2];
      const bankData = detailRes.data || detailRes || {};
      const statsData = statsRes.data || statsRes || {};
      const countsData = countsRes.data || countsRes || {};

      this.setData({
        bankInfo: {
          name: bankData.name || '未知题库',
          description: bankData.description || '',
          question_count: bankData.question_count || 0,
          is_public: !!bankData.is_public,
          owner_username: bankData.owner_username || ''
        },
        myStats: {
          total_answered: statsData.total_answered || 0,
          correct_count: statsData.correct_count || 0,
          wrong_count: statsData.wrong_count || countsData.mistakes || 0,
          favorite_count: countsData.favorites || 0,
          accuracy: statsData.accuracy || 0
        },
        loading: false
      });
    } catch (err: any) {
      console.error('加载题库信息失败:', err);
      const errorMsg = (err && err.message) || '加载失败';

      if (errorMsg.includes('401') || errorMsg.includes('登录') || errorMsg.includes('过期')) {
        wx.removeStorageSync('token');
        wx.removeStorageSync('userInfo');
        wx.reLaunch({ url: '/pages/login/login' });
        return;
      }

      wx.showToast({ title: errorMsg, icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onButtonTap(e: any) {
    const action = e.currentTarget.dataset.action;
    const bankId = this.data.bankId;
    const bankInfo = this.data.bankInfo;

    if (!bankId) {
      wx.showToast({ title: '题库信息缺失', icon: 'none' });
      return;
    }

    if (action === 'practice') {
      // 刷题 - 跳转到刷题设置页
      if (bankInfo.question_count <= 0) {
        wx.showToast({ title: '该题库暂无题目', icon: 'none' });
        return;
      }
      wx.navigateTo({
        url: `/pages/practice-setup/practice-setup?bank_id=${bankId}`
      });
      return;
    }

    if (action === 'exam') {
      // 考试 - 跳转到考试设置页
      if (bankInfo.question_count <= 0) {
        wx.showToast({ title: '该题库暂无题目', icon: 'none' });
        return;
      }
      wx.navigateTo({
        url: `/pages/bank-exam-setup/bank-exam-setup?bank_id=${bankId}`
      });
      return;
    }

    if (action === 'search') {
      // 搜索 - 跳转到题库搜索页
      wx.navigateTo({
        url: `/pages/search/search?bank_id=${bankId}`
      });
      return;
    }

    if (action === 'mistakes') {
      // 错题模式
      if (this.data.myStats.wrong_count <= 0) {
        wx.showToast({ title: '暂无错题', icon: 'none' });
        return;
      }
      wx.navigateTo({
        url: `/pages/quiz/quiz?bank_id=${bankId}&source=mistakes`
      });
      return;
    }

    if (action === 'stats') {
      // 统计 - 跳转到统计页
      wx.navigateTo({
        url: `/pages/subject-stats/subject-stats?bank_id=${bankId}`
      });
      return;
    }

    if (action === 'favorites') {
      // 收藏模式
      if (this.data.myStats.favorite_count <= 0) {
        wx.showToast({ title: '暂无收藏', icon: 'none' });
        return;
      }
      wx.navigateTo({
        url: `/pages/quiz/quiz?bank_id=${bankId}&source=favorites`
      });
      return;
    }

    if (action === 'share') {
      // 分享设置 - 跳转到分享设置页
      wx.navigateTo({
        url: `/pages/bank-share/bank-share?bank_id=${bankId}`
      });
      return;
    }

    if (action === 'update') {
      // 刷新数据
      this.onRefreshTap();
      return;
    }

    wx.showToast({ title: '功能开发中', icon: 'none' });
  },

  onRefreshTap() {
    if (this.data.loading) return;
    wx.showLoading({ title: '刷新中...' });
    this.loadBankInfo().finally(() => {
      wx.hideLoading();
      wx.showToast({ title: '已刷新', icon: 'success' });
    });
  },

  onShareAppMessage() {
    const bankInfo = this.data.bankInfo;
    const name = bankInfo ? bankInfo.name : '题库';
    return {
      title: `一起刷题：${name}`,
      path: `/pages/bank-detail/bank-detail?id=${this.data.bankId}`
    };
  }
});
