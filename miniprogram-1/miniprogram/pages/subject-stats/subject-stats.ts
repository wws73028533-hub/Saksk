// subject-stats.ts - 学习统计
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    subject: '',
    loading: false,
    stats: {
      totalCount: 0,
      doneCount: 0,
      wrongCount: 0,
      favoriteCount: 0,
      lastActivity: '',
      accuracyText: '0%'
    }
  },

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    let subject = options.subject || '';
    if (!subject) {
      wx.showToast({ title: '科目参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1200);
      return;
    }
    try {
      subject = decodeURIComponent(subject);
    } catch (e) {}
    this.setData({ subject });
    this.loadStats();
  },

  onShow() {
    // 返回该页时刷新一次（例如从收藏/错题返回）
    if (this.data.subject) {
      this.loadStats();
    }
  },

  async loadStats() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const res: any = await api.getSubjectInfo(this.data.subject);
      // utils/api.ts 已经把 {status,data} 解包为 data，这里兼容两种返回结构
      const data = (res && (res as any).data) ? (res as any).data : (res || {});
      const user = data.user_stats || {};

      const totalCount = data.total_count || 0;
      const doneCount = user.done_count || 0;
      const wrongCount = user.wrong_count || 0;
      const favoriteCount = user.favorite_count || 0;

      const accuracy = doneCount > 0 ? Math.max(0, (doneCount - wrongCount) / doneCount) : 0;
      const accuracyText = `${Math.round(accuracy * 100)}%`;

      this.setData({
        stats: {
          totalCount,
          doneCount,
          wrongCount,
          favoriteCount,
          lastActivity: this.formatDateTime(user.last_activity || ''),
          accuracyText
        },
        loading: false
      });
    } catch (err: any) {
      console.error('加载学习统计失败:', err);
      const msg = (err && err.message) || '加载失败';
      wx.showToast({ title: msg, icon: 'none' });
      this.setData({ loading: false });
    }
  },

  formatDateTime(dateTimeStr: string): string {
    if (!dateTimeStr) return '';
    try {
      const date = new Date(dateTimeStr);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      return `${month}-${day} ${hours}:${minutes}`;
    } catch (e) {
      return '';
    }
  }
});
