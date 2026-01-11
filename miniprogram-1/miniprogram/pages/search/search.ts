// search.ts - 题目搜索
// 支持公有题库（subject参数）和个人题库（bank_id参数）双数据源
import { checkLogin } from '../../utils/auth';
import { createSourceFromOptions, IQuizSource } from '../../utils/quiz-source';

// 数据源实例（页面级别）
let quizSource: IQuizSource | null = null;

Page({
  data: {
    // 数据源信息
    sourceType: '' as 'public' | 'bank' | '',
    sourceId: '' as string | number,
    displayName: '',
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

    // 使用工厂函数创建数据源
    quizSource = createSourceFromOptions(options);

    if (!quizSource) {
      console.error('数据源参数缺失（需要 subject 或 bank_id）');
      wx.showToast({ title: '参数缺失', icon: 'none' });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
      return;
    }

    console.log('搜索页面数据源类型:', quizSource.sourceType, '标识:', quizSource.sourceId);

    this.setData({
      sourceType: quizSource.sourceType,
      sourceId: quizSource.sourceId,
      displayName: quizSource.displayName || String(quizSource.sourceId)
    });
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
    if (this.data.loading || !quizSource) return;

    const keyword = (this.data.keyword || '').trim();
    if (!keyword) return;

    const page = reset ? 1 : this.data.page;
    this.setData({ loading: true });

    try {
      // 使用数据源适配器搜索题目
      const result = await quizSource.searchQuestions({
        keyword,
        type: this.data.selectedType !== 'all' ? this.data.selectedType : undefined,
        page,
        per_page: this.data.per_page
      });

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

    const { sourceType, sourceId } = this.data;
    const type = this.data.selectedType;

    // 获取保存的设置
    const storageKey = sourceType === 'bank'
      ? `bank_practice_settings_${sourceId}`
      : `practice_settings_${sourceId}`;
    const saved = wx.getStorageSync(storageKey) || {};
    const shuffleQuestions = !!saved.shuffleQuestions;
    const shuffleOptions = !!saved.shuffleOptions;

    // 构建跳转参数
    const params: string[] = [];

    // 根据数据源类型添加不同的标识参数
    if (sourceType === 'bank') {
      params.push(`bank_id=${sourceId}`);
    } else {
      params.push(`subject=${encodeURIComponent(String(sourceId))}`);
    }

    params.push('mode=quiz');
    if (type && type !== 'all') params.push(`type=${encodeURIComponent(type)}`);
    params.push(`start_id=${id}`);
    if (shuffleQuestions) params.push('shuffle_questions=1');
    if (shuffleOptions) params.push('shuffle_options=1');

    wx.navigateTo({ url: `/pages/quiz/quiz?${params.join('&')}` });
  }
});
