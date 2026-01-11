// bank-exam-setup.ts - 个人题库考试设置
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    bankId: 0,
    bankName: '',
    totalQuestions: 0,
    duration: 60,           // 考试时长（分钟）
    questionCount: 20,      // 题目数量
    scorePerQuestion: 5,    // 每题分值
    totalScore: 100,        // 总分
    shuffleQuestions: true, // 随机抽题
    loading: false,
    creating: false,
    warnText: ''
  },

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const bankId = Number(options.bank_id || 0);
    if (!bankId) {
      wx.showToast({ title: '题库参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }

    this.setData({ bankId });
    this.loadBankInfo();
  },

  async loadBankInfo() {
    this.setData({ loading: true });
    try {
      const res: any = await api.getBankDetail(this.data.bankId);
      const bankData = res.data || res || {};

      const totalQuestions = bankData.question_count || 0;
      const questionCount = Math.min(20, totalQuestions);

      this.setData({
        bankName: bankData.name || '题库',
        totalQuestions,
        questionCount,
        loading: false
      });

      this.updateTotalScore();
    } catch (err: any) {
      console.error('加载题库信息失败:', err);
      if (err.message?.includes('401') || err.message?.includes('登录')) {
        wx.reLaunch({ url: '/pages/login/login' });
        return;
      }
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  onDurationInput(e: any) {
    const v = Number(e.detail.value);
    const duration = isFinite(v) ? Math.max(1, Math.min(240, v)) : 60;
    this.setData({ duration });
  },

  onQuestionCountInput(e: any) {
    const v = Number(e.detail.value);
    const max = this.data.totalQuestions;
    const questionCount = isFinite(v) ? Math.max(1, Math.min(max, v)) : 20;
    this.setData({ questionCount }, () => {
      this.updateTotalScore();
      this.checkWarn();
    });
  },

  onScoreInput(e: any) {
    const v = Number(e.detail.value);
    const scorePerQuestion = isFinite(v) ? Math.max(0.5, Math.min(100, v)) : 5;
    this.setData({ scorePerQuestion }, () => {
      this.updateTotalScore();
    });
  },

  onShuffleChange(e: any) {
    this.setData({ shuffleQuestions: !!e.detail.value });
  },

  updateTotalScore() {
    const total = this.data.questionCount * this.data.scorePerQuestion;
    this.setData({ totalScore: Math.round(total * 10) / 10 });
  },

  checkWarn() {
    const { questionCount, totalQuestions } = this.data;
    if (questionCount > totalQuestions) {
      this.setData({ warnText: `题目数量超过可用题目数（${totalQuestions}）` });
    } else {
      this.setData({ warnText: '' });
    }
  },

  async onStartExam() {
    const { bankId, questionCount, duration, scorePerQuestion, shuffleQuestions, totalQuestions } = this.data;

    if (questionCount > totalQuestions) {
      wx.showToast({ title: '题目数量超过可用数量', icon: 'none' });
      return;
    }

    if (questionCount <= 0) {
      wx.showToast({ title: '请设置题目数量', icon: 'none' });
      return;
    }

    this.setData({ creating: true });

    try {
      // 跳转到考试页面，传递参数
      const params = [
        `bank_id=${bankId}`,
        `count=${questionCount}`,
        `duration=${duration}`,
        `score=${scorePerQuestion}`,
        `shuffle=${shuffleQuestions ? 1 : 0}`
      ];

      wx.navigateTo({
        url: `/pages/bank-exam/bank-exam?${params.join('&')}`,
        fail: (err) => {
          console.error('跳转失败:', err);
          // 如果bank-exam页面不存在，使用bank-quiz作为替代
          wx.navigateTo({
            url: `/pages/bank-quiz/bank-quiz?bank_id=${bankId}&mode=random&limit=${questionCount}`,
            fail: () => {
              wx.showToast({ title: '考试功能开发中', icon: 'none' });
            }
          });
        }
      });

      this.setData({ creating: false });
    } catch (err: any) {
      console.error('创建考试失败:', err);
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
      this.setData({ creating: false });
    }
  }
});
