// 题目列表页面
import { api } from '../../utils/api';

Page({
  data: {
    questions: [] as any[],
    subject: 'all',
    loading: false,
    page: 1,
    hasMore: true,
    total: 0
  },

  onLoad(options: any) {
    if (options.subject) {
      this.setData({ subject: decodeURIComponent(options.subject) });
    }
    this.loadQuestions(true);
  },

  // 加载题目列表
  async loadQuestions(reset = false) {
    if (this.data.loading) return;
    
    const page = reset ? 1 : this.data.page;
    this.setData({ loading: true });

    try {
      const result = await api.getQuestions({
        subject: this.data.subject === 'all' ? undefined : this.data.subject,
        page,
        per_page: 20
      });

      const resultQuestions = result.questions || [];
      const questions = reset ? resultQuestions : this.data.questions.concat(resultQuestions);
       
      this.setData({
        questions,
        total: result.total || 0,
        page: page + 1,
        hasMore: resultQuestions.length === 20,
        loading: false
      });
    } catch (err: any) {
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  // 下拉刷新
  onPullDownRefresh() {
    this.loadQuestions(true).then(() => {
      wx.stopPullDownRefresh();
    });
  },

  // 上拉加载
  onReachBottom() {
    if (this.data.hasMore && !this.data.loading) {
      this.loadQuestions();
    }
  },

  // 点击题目
  onQuestionTap(e: any) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({
      url: `/pages/practice/practice?id=${id}`
    });
  }
});

