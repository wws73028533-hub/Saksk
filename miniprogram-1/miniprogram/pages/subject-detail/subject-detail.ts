// subject-detail.ts
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    subject: '',
    subjectInfo: {
      totalCount: 0,
      author: '',
      doneCount: 0,
      wrongCount: 0,
      favoriteCount: 0,
      noteCount: 0,
      lastActivity: ''
    },
    loading: false
  },

  onLoad(options: any) {
    let subject = options.subject || '';
    if (!subject) {
      wx.showToast({ title: '科目参数缺失', icon: 'none' });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
      return;
    }
    
    // 显式解码URL参数（微信小程序会自动解码，但显式解码更安全）
    try {
      subject = decodeURIComponent(subject);
    } catch (e) {
      // 如果解码失败，使用原始值
      console.warn('URL参数解码失败，使用原始值:', e);
    }
    
    this.setData({ subject });
    wx.showShareMenu({ withShareTicket: true });
    this.loadSubjectInfo();
  },

  onShow() {
    // 从刷题/收藏/错题等页面返回后刷新统计
    if (this.data.subject) {
      this.loadSubjectInfo();
    }
  },

  async loadSubjectInfo() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    this.setData({ loading: true });
    try {
      const data: any = await api.getSubjectInfo(this.data.subject);
      // utils/api.ts 已经把 {status,data} 解包为 data，这里兼容两种返回结构
      const subjectInfo = (data && (data as any).data) ? (data as any).data : (data || {});
      const userStats = subjectInfo.user_stats || {};
      
      this.setData({
        subjectInfo: {
          totalCount: subjectInfo.total_count || 0,
          author: subjectInfo.author || '',
          doneCount: userStats.done_count || 0,
          wrongCount: userStats.wrong_count || 0,
          favoriteCount: userStats.favorite_count || 0,
          noteCount: userStats.note_count || 0,
          lastActivity: this.formatDateTime(userStats.last_activity || '')
        },
        loading: false
      });
    } catch (err: any) {
      console.error('加载科目信息失败:', err);
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
  },

  onStartPracticeTap() {
    const subject = this.data.subject;
    console.log('准备跳转到练习设置页面:', subject);
    
    if (!subject) {
      wx.showToast({ title: '科目信息缺失', icon: 'none' });
      return;
    }
    
    const url = `/pages/practice-setup/practice-setup?subject=${encodeURIComponent(subject)}`;
    console.log('跳转URL:', url);
    
    wx.navigateTo({
      url: url,
      success: () => {
        console.log('跳转成功');
      },
      fail: (err) => {
        console.error('跳转失败:', err);
        wx.showToast({ title: '跳转失败: ' + (err.errMsg || '未知错误'), icon: 'none', duration: 3000 });
      }
    });
  },

  onButtonTap(e: any) {
    const action = e.currentTarget.dataset.action;
    console.log('按钮点击，action:', action);
    
    if (action === 'practice') {
      console.log('跳转到练习页面，subject:', this.data.subject);
      this.onStartPracticeTap();
      return;
    }

    if (action === 'exam') {
      wx.navigateTo({
        url: `/pages/exam-setup/exam-setup?subject=${encodeURIComponent(this.data.subject)}`
      });
      return;
    }

    if (action === 'search') {
      wx.navigateTo({
        url: `/pages/search/search?subject=${encodeURIComponent(this.data.subject)}`
      });
      return;
    }

    if (action === 'update') {
      this.onUpdateQuestionsTap();
      return;
    }

    if (action === 'favorites') {
      this.goToQuestionBank('favorites');
      return;
    }

    if (action === 'mistakes') {
      this.goToQuestionBank('mistakes');
      return;
    }

    if (action === 'stats') {
      wx.navigateTo({
        url: `/pages/subject-stats/subject-stats?subject=${encodeURIComponent(this.data.subject)}`
      });
      return;
    }

    wx.showToast({ title: '功能开发中', icon: 'none' });
  },

  async onUpdateQuestionsTap() {
    if (this.data.loading) return;
    wx.showLoading({ title: '同步中...' });
    try {
      await this.loadSubjectInfo();
      wx.hideLoading();
      wx.showToast({ title: '已同步', icon: 'success' });
    } catch (e) {
      wx.hideLoading();
    }
  },

  goToQuestionBank(source: 'favorites' | 'mistakes') {
    const subject = this.data.subject;
    if (!subject) return;

    const saved = wx.getStorageSync(`practice_settings_${subject}`) || {};
    const shuffleQuestions = !!saved.shuffleQuestions;
    const shuffleOptions = !!saved.shuffleOptions;

    const params: string[] = [];
    params.push(`subject=${encodeURIComponent(subject)}`);
    params.push('mode=quiz');
    params.push(`source=${source}`);
    if (shuffleQuestions) params.push('shuffle_questions=1');
    if (shuffleOptions) params.push('shuffle_options=1');

    wx.navigateTo({ url: `/pages/quiz/quiz?${params.join('&')}` });
  },

  onShareAppMessage() {
    const subject = this.data.subject || '科目';
    return {
      title: `一起刷题：${subject}`,
      path: `/pages/subject-detail/subject-detail?subject=${encodeURIComponent(subject)}`
    };
  },

  onShareTimeline() {
    const subject = this.data.subject || '科目';
    return {
      title: `一起刷题：${subject}`,
      query: `subject=${encodeURIComponent(subject)}`
    };
  }
});
