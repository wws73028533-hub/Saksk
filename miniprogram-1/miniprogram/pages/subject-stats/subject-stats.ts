// subject-stats.ts - 学习统计
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

    // 使用工厂函数创建数据源
    quizSource = createSourceFromOptions(options);

    if (!quizSource) {
      console.error('数据源参数缺失（需要 subject 或 bank_id）');
      wx.showToast({ title: '参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1200);
      return;
    }

    console.log('统计页面数据源类型:', quizSource.sourceType, '标识:', quizSource.sourceId);

    this.setData({
      sourceType: quizSource.sourceType,
      sourceId: quizSource.sourceId,
      displayName: quizSource.displayName || String(quizSource.sourceId)
    });

    this.loadStats();
  },

  onShow() {
    // 返回该页时刷新一次（例如从收藏/错题返回）
    if (quizSource) {
      this.loadStats();
    }
  },

  async loadStats() {
    if (this.data.loading || !quizSource) return;
    this.setData({ loading: true });

    try {
      // 获取基础信息
      const info = await quizSource.getInfo();
      const totalCount = info.question_count || 0;

      // 更新显示名称
      if (info.name) {
        this.setData({ displayName: info.name });
      }

      // 获取用户统计
      const userCounts = await quizSource.getUserCounts();
      const myStats = await quizSource.getMyStats();

      const doneCount = myStats.total_answered || 0;
      const wrongCount = userCounts.mistakes || myStats.wrong_count || 0;
      const favoriteCount = userCounts.favorites || 0;

      const accuracy = doneCount > 0 ? Math.max(0, (doneCount - wrongCount) / doneCount) : 0;
      const accuracyText = `${Math.round(accuracy * 100)}%`;

      this.setData({
        stats: {
          totalCount,
          doneCount,
          wrongCount,
          favoriteCount,
          lastActivity: '',  // 数据源适配器暂未提供此字段
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
