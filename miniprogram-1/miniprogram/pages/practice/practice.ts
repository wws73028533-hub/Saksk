// practice.ts - 练习页面（入口页）
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

Page({
  data: {
    subject: '',              // 科目名称
    selectedSource: 'all',    // 选中的刷题范围（all/favorites/mistakes）
    selectedType: 'all',      // 选中的题型（all/选择题/多选题/判断题/填空题）
    
    // 统计信息
    stats: {
      total: 0,              // 总题数（当前范围和题型）
      favorites: 0,          // 收藏数（当前题型）
      mistakes: 0            // 错题数（当前题型）
    },
    
    // 设置选项
    settings: {
      shuffleQuestions: false,  // 打乱题目
      shuffleOptions: false     // 打乱选项
    },
    
    loading: false,              // 加载状态
    debounceTimer: null as any   // 防抖定时器
  },

  onLoad(options: any) {
    console.log('练习页面 onLoad，参数:', options);
    
    let subject = options.subject || '';
    if (!subject) {
      // 作为 tabBar 页面进入时没有 subject 参数，给出引导
      wx.showToast({ title: '请先选择科目', icon: 'none' });
      setTimeout(() => {
        wx.switchTab({ url: '/pages/index/index' });
      }, 800);
      return;
    }
    
    // 显式解码URL参数
    try {
      subject = decodeURIComponent(subject);
    } catch (e) {
      console.warn('URL参数解码失败，使用原始值:', e);
    }

    console.log('科目名称:', subject);
    
    // 从路由参数或本地存储获取设置
    const savedSettings = wx.getStorageSync(`practice_settings_${subject}`) || {};
    let selectedType = options.type || 'all';
    try {
      selectedType = decodeURIComponent(selectedType);
    } catch (e) {
      console.warn('题型参数解码失败，使用原始值:', e);
    }
    
    this.setData({
      subject,
      selectedSource: options.source || 'all',
      selectedType,
      settings: {
        shuffleQuestions: savedSettings.shuffleQuestions || false,
        shuffleOptions: savedSettings.shuffleOptions || false
      }
    });
    
    this.loadStats();
  },

  // 加载统计信息
  async loadStats() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    this.setData({ loading: true });
    try {
      const { subject, selectedSource, selectedType } = this.data;
      
      // 获取总题数（基于当前范围和题型）
      const countParams: any = { subject };
      if (selectedType !== 'all') {
        countParams.type = selectedType;
      }
      if (selectedSource !== 'all') {
        countParams.source = selectedSource;
      }
      
      const totalCount = await api.getQuestionsCount(countParams);
      
      // 获取用户收藏和错题数量（基于当前题型）
      const userCounts = await api.getUserCounts({
        subject,
        type: selectedType !== 'all' ? selectedType : undefined
      });
      
      this.setData({
        stats: {
          total: totalCount.count || 0,
          favorites: userCounts.favorites || 0,
          mistakes: userCounts.mistakes || 0
        },
        loading: false
      });
    } catch (err: any) {
      console.error('加载统计信息失败:', err);
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

  // 防抖加载统计信息
  debouncedLoadStats() {
    if (this.data.debounceTimer) {
      clearTimeout(this.data.debounceTimer);
    }
    
    this.data.debounceTimer = setTimeout(() => {
      this.loadStats();
    }, 300);
  },

  // 选择刷题范围
  onSourceTap(e: any) {
    const source = e.currentTarget.dataset.source;
    this.setData({ selectedSource: source });
    this.debouncedLoadStats();
  },

  // 选择题型
  onTypeTap(e: any) {
    const type = e.currentTarget.dataset.type;
    this.setData({ selectedType: type });
    this.debouncedLoadStats();
  },

  // 切换设置选项
  onSettingChange(e: any) {
    const setting = e.currentTarget.dataset.setting;
    const value = e.detail.value;
    
    const newSettings: any = Object.assign({}, this.data.settings);
    newSettings[setting] = value;
    
    this.setData({ settings: newSettings });
    
    // 保存用户偏好到本地存储
    try {
      wx.setStorageSync(`practice_settings_${this.data.subject}`, newSettings);
    } catch (e) {
      console.warn('保存设置失败:', e);
    }
  },

  // 操作按钮点击（刷题/背题）
  onActionButtonTap(e: any) {
    console.log('操作按钮点击，event:', e);
    
    const mode = e.currentTarget.dataset.mode; // quiz/memo
    console.log('模式:', mode);
    
    const { subject, selectedSource, selectedType, settings } = this.data;
    console.log('当前数据:', { subject, selectedSource, selectedType, settings });
    
    if (!subject) {
      wx.showToast({ title: '科目信息缺失', icon: 'none' });
      return;
    }

    if (this.data.loading) {
      wx.showToast({ title: '加载中，请稍候', icon: 'none' });
      return;
    }

    const total = (this.data.stats && this.data.stats.total) || 0;
    if (total <= 0) {
      wx.showToast({ title: '当前筛选暂无题目', icon: 'none' });
      return;
    }
    
    // 构建参数
    const params: string[] = [];
    params.push(`subject=${encodeURIComponent(subject)}`);
    
    // 题型参数
    if (selectedType !== 'all') {
      params.push(`type=${encodeURIComponent(selectedType)}`);
    }
    
    // 模式参数
    params.push(`mode=${mode}`);
    
    // 来源参数
    if (selectedSource !== 'all') {
      params.push(`source=${selectedSource}`);
    }
    
    // 设置参数
    if (settings.shuffleQuestions) {
      params.push('shuffle_questions=1');
    }
    if (settings.shuffleOptions) {
      params.push('shuffle_options=1');
    }
    
    // 直接进入答题页（支持题型/来源筛选与打乱选项/题目）
    const url = `/pages/quiz/quiz?${params.join('&')}`;
    console.log('跳转URL:', url);
    
    wx.navigateTo({
      url: url,
      success: () => {
        console.log('跳转到刷题页面成功');
      },
      fail: (err) => {
        console.error('跳转失败:', err);
        wx.showToast({ title: '跳转失败: ' + (err.errMsg || '未知错误'), icon: 'none', duration: 3000 });
      }
    });
  },

  buildProgressKey(mode: 'quiz' | 'memo'): string {
    const userInfo = wx.getStorageSync('userInfo') || {};
    const uid = (userInfo && (userInfo.id || userInfo.user_id)) ? String(userInfo.id || userInfo.user_id) : 'guest';

    const subject = (this.data.subject || 'all').toString();
    const type = (this.data.selectedType || 'all').toString();

    const sourceParam = (this.data.selectedSource || '').toString();
    const dataScope = (sourceParam === 'favorites' || sourceParam === 'mistakes') ? sourceParam : 'all';

    const shuffleQ = this.data.settings.shuffleQuestions ? '1' : '0';
    const shuffleO = this.data.settings.shuffleOptions ? '1' : '0';

    return `quiz_progress_${uid}_${mode}_${subject}_${type}_${dataScope}_q${shuffleQ}_o${shuffleO}`;
  },

  onClearProgressTap() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    if (this.data.loading) {
      wx.showToast({ title: '加载中，请稍候', icon: 'none' });
      return;
    }

    wx.showActionSheet({
      itemList: ['清除刷题进度', '清除背题进度'],
      success: (res) => {
        const mode: 'quiz' | 'memo' = res.tapIndex === 1 ? 'memo' : 'quiz';
        const modeText = mode === 'quiz' ? '刷题' : '背题';

        const sourceMap: any = {
          all: '全部',
          favorites: '收藏',
          mistakes: '错题'
        };
        const sourceText = sourceMap[this.data.selectedSource] || '全部';
        const typeText = this.data.selectedType === 'all' ? '全部题型' : this.data.selectedType;

        const key = this.buildProgressKey(mode);

        wx.showModal({
          title: '确认清除',
          content: `将清除【${this.data.subject}】${modeText}（${sourceText} / ${typeText}）的进度记录，不影响其他筛选。是否继续？`,
          confirmText: '清除',
          confirmColor: '#FF3B30',
          success: async (r) => {
            if (!r.confirm) return;
            try {
              await api.deleteProgress(key);
            } catch (err: any) {
              console.warn('删除云端进度失败（将继续清除本地）:', err);
            }

            try {
              wx.removeStorageSync(key);
            } catch (e) {}

            wx.showToast({ title: '已清除', icon: 'none' });
          }
        });
      }
    });
  },

  onUnload() {
    // 清除防抖定时器
    if (this.data.debounceTimer) {
      clearTimeout(this.data.debounceTimer);
    }
  }
});
