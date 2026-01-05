// subjects.ts - 科目页
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    subjects: [] as string[],
    filteredSubjects: [] as string[],
    keyword: '',
    loading: false
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    this.loadSubjects();
  },

  async loadSubjects() {
    if (this.data.loading) return;
    this.setData({ loading: true });
    try {
      const res: any = await api.getSubjects();
      const list = (res && res.subjects) ? res.subjects : [];
      const subjects = Array.isArray(list) ? list.filter((x: any) => typeof x === 'string' && x.trim()) : [];
      this.setData({ subjects }, () => {
        this.applyFilter();
      });
    } catch (err: any) {
      console.error('加载科目失败:', err);
      wx.showToast({ title: (err && err.message) || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  onKeywordInput(e: any) {
    const keyword = (e && e.detail && e.detail.value) ? String(e.detail.value) : '';
    this.setData({ keyword }, () => this.applyFilter());
  },

  onClearKeyword() {
    this.setData({ keyword: '' }, () => this.applyFilter());
  },

  applyFilter() {
    const kw = (this.data.keyword || '').trim().toLowerCase();
    const list = this.data.subjects || [];
    const filteredSubjects = kw
      ? list.filter((s) => String(s).toLowerCase().includes(kw))
      : list.slice();
    this.setData({ filteredSubjects });
  },

  onSubjectTap(e: any) {
    const subject = e.currentTarget.dataset.subject;
    if (!subject) return;
    wx.navigateTo({ url: `/pages/subject-detail/subject-detail?subject=${encodeURIComponent(subject)}` });
  },

  onPullDownRefresh() {
    this.loadSubjects().finally(() => wx.stopPullDownRefresh());
  }
});

