// search.ts - 题目搜索
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    subject: '',
    keyword: '',
    selectedType: 'all',

    questions: [] as any[],
    page: 1,
    per_page: 20,
    total: 0,
    hasMore: true,
    loading: false,
    searched: false
  },

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    let subject = options.subject || '';
    try {
      subject = subject ? decodeURIComponent(subject) : '';
    } catch (e) {}

    this.setData({ subject });
  },

  onKeywordInput(e: any) {
    this.setData({ keyword: e.detail.value || '' });
  },

  onTypeTap(e: any) {
    const type = e.currentTarget.dataset.type || 'all';
    this.setData({ selectedType: type });
  },

  onSearch() {
    const kw = (this.data.keyword || '').trim();
    if (!kw) {
      wx.showToast({ title: '请输入关键词', icon: 'none' });
      return;
    }
    this.loadResults(true);
  },

  async loadResults(reset = false) {
    if (this.data.loading) return;

    const keyword = (this.data.keyword || '').trim();
    if (!keyword) return;

    const page = reset ? 1 : this.data.page;
    this.setData({ loading: true });

    try {
      const params: any = {
        keyword,
        page,
        per_page: this.data.per_page
      };
      if (this.data.subject) {
        params.subject = this.data.subject;
      }
      if (this.data.selectedType !== 'all') {
        params.q_type = this.data.selectedType;
      }

      const result: any = await api.searchQuestions(params);
      const list = (result.questions || []) as any[];
      const next = reset ? list : this.data.questions.concat(list);

      this.setData({
        questions: next,
        total: result.total || 0,
        page: page + 1,
        hasMore: list.length === this.data.per_page,
        loading: false,
        searched: true
      });
    } catch (err: any) {
      console.error('搜索失败:', err);
      const msg = (err && err.message) || '搜索失败';
      wx.showToast({ title: msg, icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onPullDownRefresh() {
    this.loadResults(true).finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadResults(false);
    }
  },

  onResultTap(e: any) {
    const id = Number(e.currentTarget.dataset.id);
    if (!isFinite(id) || id <= 0) return;

    const subject = this.data.subject || '';
    const type = this.data.selectedType;

    const saved = wx.getStorageSync(`practice_settings_${subject}`) || {};
    const shuffleQuestions = !!saved.shuffleQuestions;
    const shuffleOptions = !!saved.shuffleOptions;

    const params: string[] = [];
    if (subject) params.push(`subject=${encodeURIComponent(subject)}`);
    params.push('mode=quiz');
    if (type && type !== 'all') params.push(`type=${encodeURIComponent(type)}`);
    params.push(`start_id=${id}`);
    if (shuffleQuestions) params.push('shuffle_questions=1');
    if (shuffleOptions) params.push('shuffle_options=1');

    wx.navigateTo({ url: `/pages/quiz/quiz?${params.join('&')}` });
  }
});

