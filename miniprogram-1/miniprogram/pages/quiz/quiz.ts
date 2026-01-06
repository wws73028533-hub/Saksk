// quiz.ts - 刷题/背题页面
import { api, normalizeImageUrls } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

type OptionItem = {
  key: string;
  value: string;
  answerValue: string;
};

type DisplayOption = OptionItem & {
  isSelected: boolean;
  isCorrect: boolean;
  isWrong: boolean;
  className: string;
};

type QuestionType = '选择题' | '多选题' | '判断题' | '填空题' | '问答题' | '简答题' | '计算题' | string;

Page({
  data: {
    mode: 'quiz',              // 模式：'quiz' 或 'memo'
    subject: '',               // 科目名称
    source: 'all',             // 数据范围：all/favorites/mistakes
    qType: 'all',              // 题型筛选（用于进度key）
    shuffleQuestions: false,   // 打乱题目（用于进度key）
    shuffleOptions: false,     // 打乱选项（用于进度key & 服务端确定性打乱）
    startId: 0,                // 从搜索等入口指定起始题目ID
    questions: [] as any[],    // 题目列表
    currentIndex: 0,           // 当前题目索引
    currentQuestion: null as any,  // 当前题目对象
    selectedAnswer: '',        // 选中的答案（刷题模式 - 单选题/判断题/填空题）
    selectedAnswers: [] as string[], // 多选题答案数组
    showAnswer: false,         // 是否显示答案（刷题模式）
    isFavorite: false,         // 是否收藏
    isCorrect: false,          // 回答是否正确（刷题模式）
    isJudgable: true,          // 是否可自动判分（主观题为 false）
    loading: false,            // 加载状态
    showQuestionList: false,   // 是否显示题目列表抽屉
    displayOptions: [] as DisplayOption[],
    blankAnswers: [] as string[],
    blankIndexes: [] as number[],
    blankCount: 0,
    showSubmitButton: false,
    submitDisabled: true,
    userAnswerText: '',

    // 刷题设置
    showSettings: false,
    practiceSettings: {
      autoNextOnCorrect: false,   // 答对自动切题（答错不切题）
      autoFavoriteOnWrong: false, // 做错自动收藏
      vibrationFeedback: false    // 答题震动反馈
    },

    // AI 解析
    showAIExplain: false,
    aiLoading: false,
    aiExplainText: '',
    aiExplainError: '',
    aiExplainQuestionId: 0,
    
    // 进度信息
    progress: {
      current: 0,              // 当前题号
      total: 0                 // 总题数
    },
    
    // 答题记录（用于题目列表显示状态）
    answerRecords: {} as Record<number, { answered: boolean; isCorrect: boolean }>
  },

  // === 进度同步（与 Web 端 /api/progress 互通）===
  progressKey: '' as any,
  progressStatusMap: {} as any,
  progressAnswerMap: {} as any,
  progressOrder: null as any,
  saveProgressTimer: null as any,
  syncPending: false as any,
  lastSavedPayload: null as any,
  practiceSettingsKey: 'quiz_practice_settings_v1' as any,

  onLoad(options: any) {
    console.log('刷题页面 onLoad，参数:', options);
    
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    
    // 解析参数
    let subject = options.subject || '';
    const mode = options.mode || 'quiz';
    let type = options.type || 'all';
    const source = options.source || 'all';
    const shuffleQuestions = options.shuffle_questions === '1';
    const shuffleOptions = options.shuffle_options === '1';
    const startId = Number(options.start_id || 0);
    
    if (!subject) {
      wx.showToast({ title: '科目参数缺失', icon: 'none' });
      setTimeout(() => {
        wx.navigateBack();
      }, 1500);
      return;
    }
    
    try {
      subject = decodeURIComponent(subject);
    } catch (e) {
      console.warn('URL参数解码失败:', e);
    }

    // 题型可能会被 encodeURIComponent（如“选择题”），需显式解码避免后端筛选不匹配
    try {
      type = decodeURIComponent(type);
    } catch (e) {
      console.warn('题型参数解码失败:', e);
    }
    
    this.setData({
      mode,
      subject,
      source,
      qType: type || 'all',
      shuffleQuestions,
      shuffleOptions,
      startId: isFinite(startId) && startId > 0 ? startId : 0,
      loading: true
    });

    this.initPracticeSettings();
    
    this.loadQuestions(type, source, shuffleQuestions, shuffleOptions);
  },

  initPracticeSettings() {
    try {
      const raw = wx.getStorageSync(this.practiceSettingsKey);
      if (raw && typeof raw === 'object') {
        const s: any = raw;
        const next = {
          autoNextOnCorrect: !!s.autoNextOnCorrect,
          autoFavoriteOnWrong: !!s.autoFavoriteOnWrong,
          vibrationFeedback: !!s.vibrationFeedback
        };
        this.setData({ practiceSettings: next });
      }
    } catch (e) {
      // 忽略本地存储异常
    }
  },

  savePracticeSettings() {
    try {
      wx.setStorageSync(this.practiceSettingsKey, this.data.practiceSettings);
    } catch (e) {
      // 忽略本地存储异常
    }
  },

  onOpenSettings() {
    this.setData({ showSettings: true });
  },

  onCloseSettings() {
    this.setData({ showSettings: false });
  },

  onSettingSwitchChange(e: any) {
    const key = e.currentTarget?.dataset?.key;
    const value = !!(e && e.detail && e.detail.value);
    if (!key) return;

    const next = Object.assign({}, this.data.practiceSettings);
    (next as any)[key] = value;
    this.setData({ practiceSettings: next }, () => this.savePracticeSettings());
  },

  // 加载题目列表
  async loadQuestions(type: string, source: string, shuffleQuestions: boolean, shuffleOptions: boolean) {
    try {
      const { subject, mode } = this.data;
      
      // 构建请求参数
      // 注意：如果source是favorites或mistakes，需要将其作为mode传递
      // 否则使用传入的mode参数
      const actualMode = (source === 'favorites' || source === 'mistakes') ? source : mode;
      
      const params: any = {
        subject,
        mode: actualMode,
        per_page: 1000  // 一次性加载所有题目
      };
      
      if (type !== 'all') {
        params.q_type = type;
      }
      if (shuffleOptions) {
        params.shuffle_options = '1';
      }
      
      console.log('加载题目列表，参数:', params);
      
      const result = await api.getQuestions(params);
      
      let questions = result.questions || [];
      const total = result.total || questions.length;

      // 统一 options 结构，避免不同历史数据格式导致前端无法渲染
      questions = questions.map((q: any) => {
        const normalizedOptions = this.normalizeOptions(q.options, q.q_type, q.answer);
        const imageUrls = normalizeImageUrls(q.image_path);
        const imagePath = imageUrls.length > 0 ? imageUrls[0] : '';
        return Object.assign({}, q, { options: normalizedOptions, image_urls: imageUrls, image_path: imagePath });
      });
      
      // 为每个题目生成预览内容
      let questionsWithPreview = questions.map((q: any) => {
        const content = q.content || '';
        const textContent = content.replace(/<[^>]+>/g, ''); // 移除HTML标签
        const preview = textContent.length > 40 ? textContent.substring(0, 40) + '...' : textContent;
        return Object.assign({}, q, { contentPreview: preview });
      });

      // 进度key（必须与 Web progressKey() 格式一致）
      const pKey = this.buildProgressKey();
      this.progressKey = pKey;

      // 先尝试恢复云端/本地进度（含题目顺序）
      const saved = await this.loadProgressState(pKey);
      const savedPayload = (saved && typeof saved === 'object') ? saved : null;

      // 初始化进度缓存
      this.progressStatusMap = (savedPayload && savedPayload.status && typeof savedPayload.status === 'object') ? savedPayload.status : {};
      this.progressAnswerMap = (savedPayload && savedPayload.answers && typeof savedPayload.answers === 'object') ? savedPayload.answers : {};
      this.progressOrder = (savedPayload && Array.isArray(savedPayload.order)) ? savedPayload.order : null;

      // 打乱题目顺序：优先使用已保存的 order；无 order 时再生成并同步到云端
      if (shuffleQuestions && questionsWithPreview.length > 0) {
        const hasHistory =
          !!(savedPayload && ((savedPayload.status && Object.keys(savedPayload.status).length) || (savedPayload.answers && Object.keys(savedPayload.answers).length)));

        if (this.progressOrder && Array.isArray(this.progressOrder)) {
          questionsWithPreview = this.applyQuestionOrder(questionsWithPreview, this.progressOrder);
        } else {
          // 如果已有历史答题痕迹但缺少order，兜底：把当前顺序作为order保存，避免索引错位
          if (hasHistory) {
            this.progressOrder = questionsWithPreview.map((q: any) => q.id);
          } else {
            questionsWithPreview = this.shuffleArray(questionsWithPreview.slice());
            this.progressOrder = questionsWithPreview.map((q: any) => q.id);
          }

          const nextPayload: any = Object.assign({}, savedPayload || {});
          if (typeof nextPayload.index !== 'number') nextPayload.index = 0;
          if (!nextPayload.status || typeof nextPayload.status !== 'object') nextPayload.status = this.progressStatusMap || {};
          if (!nextPayload.answers || typeof nextPayload.answers !== 'object') nextPayload.answers = this.progressAnswerMap || {};
          nextPayload.order = this.progressOrder;
          nextPayload.timestamp = Date.now();

          // 保存一次order（避免多端乱序不一致）
          this.saveProgressState(nextPayload, true);
        }
      }

      // 基于已保存的状态，恢复题目列表正确/错误标记
      const restoredRecords = this.buildAnswerRecordsFromStatus(questionsWithPreview, this.progressStatusMap);
      
      this.setData({
        questions: questionsWithPreview,
        loading: false,
        answerRecords: restoredRecords,
        progress: {
          current: 1,
          total: total
        }
      });
      
      // 加载第一题
      if (questionsWithPreview.length > 0) {
        let idx = savedPayload && typeof savedPayload.index === 'number' ? savedPayload.index : 0;
        const startId = this.data.startId;
        if (startId && startId > 0) {
          const found = questionsWithPreview.findIndex((q: any) => q && q.id === startId);
          if (found >= 0) {
            idx = found;
          }
        }
        const safeIndex = Math.max(0, Math.min(idx, questionsWithPreview.length - 1));
        this.loadQuestion(safeIndex);
      } else {
        wx.showToast({ title: '暂无题目', icon: 'none' });
        setTimeout(() => {
          wx.navigateBack();
        }, 1500);
      }
    } catch (err: any) {
      console.error('加载题目失败:', err);
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

  // 加载指定题目
  loadQuestion(index: number) {
    const { questions } = this.data;
    if (index < 0 || index >= questions.length) {
      return;
    }
    
    const question = questions[index];
    const qType: QuestionType = question.q_type || '';
    const rawContent = (question.content || '').toString();
    const rawAnswer = (question.answer || '').toString();

    let displayContent = this.formatContentForDisplay(rawContent);
    if (qType === '填空题') {
      // 填空题挖空：仅填空题替换，避免代码里的 __ 被误改
      displayContent = displayContent.replace(/__/g, '____');
    }

    const isCode = this.looksLikeCode(displayContent);
    if (isCode) {
      displayContent = this.preserveSpacesForCode(displayContent);
    }
    const displayAnswer = this.formatAnswerForDisplay(qType, rawAnswer);

    const rawExplanation = (question.explanation || '').toString();
    const explanationIsCode = this.looksLikeCode(rawExplanation);
    const displayExplanation = explanationIsCode ? this.preserveSpacesForCode(rawExplanation) : rawExplanation;

    const normalizedOptions = this.normalizeOptions(question.options, qType, rawAnswer);
    const blankState = this.initBlankState(qType, rawContent, rawAnswer);
    let blankCount = blankState.blankCount;
    const blankAnswers = blankState.blankAnswers;
    let blankIndexes = blankState.blankIndexes;

    // 恢复当前题目的已保存作答（未提交也会恢复“草稿”）
    const savedAnswer = this.getSavedAnswerForIndex(index);
    const savedStatus = this.getSavedStatusForIndex(index);

    let selectedAnswer = '';
    let selectedAnswers: string[] = [];
    let nextBlankAnswers = blankAnswers.slice();
    let showAnswer = false;
    let isCorrect = false;
    let userAnswerText = '';

    if (Array.isArray(savedAnswer)) {
      if (qType === '多选题') {
        selectedAnswers = savedAnswer.map((x) => String(x)).filter(Boolean);
        userAnswerText = selectedAnswers.slice().sort().join('');
      } else if (qType === '选择题' || qType === '判断题') {
        selectedAnswer = savedAnswer.length > 0 ? String(savedAnswer[0]) : '';
        userAnswerText = selectedAnswer;
      } else if (qType === '填空题') {
        const trimmed = savedAnswer.map((x) => (x == null ? '' : String(x))).map((x) => x.trim());
        // 适配空数变化
        const filledCount = Math.max(blankCount, trimmed.length);
        const filled = Array.from({ length: filledCount }, (_, i) => trimmed[i] || '');
        blankCount = filledCount;
        blankIndexes = Array.from({ length: filledCount }, (_, i) => i);
        nextBlankAnswers = filled.slice(0, filledCount);
        userAnswerText = nextBlankAnswers.filter(Boolean).join(' / ');
      }
    } else if (typeof savedAnswer === 'string') {
      if (qType === '填空题') {
        const parts = savedAnswer.split(';;').map((x) => x.trim()).filter((x) => x.length > 0);
        const filledCount = Math.max(blankCount, parts.length);
        const filled = Array.from({ length: filledCount }, (_, i) => parts[i] || '');
        blankCount = filledCount;
        blankIndexes = Array.from({ length: filledCount }, (_, i) => i);
        nextBlankAnswers = filled.slice(0, filledCount);
        userAnswerText = nextBlankAnswers.filter(Boolean).join(' / ');
      } else {
        selectedAnswer = savedAnswer;
        userAnswerText = savedAnswer;
      }
    }

    // 仅自动判分题型恢复“已批改”状态
    if ((qType === '选择题' || qType === '多选题' || qType === '判断题' || qType === '填空题') && (savedStatus === 'correct' || savedStatus === 'wrong')) {
      showAnswer = true;
      isCorrect = savedStatus === 'correct';
    }
    
    this.setData({
      currentIndex: index,
      currentQuestion: Object.assign({}, question, {
        displayContent,
        displayAnswer,
        options: normalizedOptions,
        isCode,
        explanationIsCode,
        displayExplanation
      }),
      selectedAnswer,
      selectedAnswers,
      blankCount,
      blankAnswers: nextBlankAnswers,
      blankIndexes,
      showAnswer,
      isJudgable: this.isAutoJudgable(qType),
      isCorrect,
      userAnswerText,
      isFavorite: question.is_fav === 1 || question.is_fav === true,
      showAIExplain: false,
      aiLoading: false,
      aiExplainText: '',
      aiExplainError: '',
      aiExplainQuestionId: question.id || 0,
      progress: {
        current: index + 1,
        total: this.data.progress.total
      }
    }, () => {
      this.refreshDisplayOptions();
      this.updateSubmitState();
      this.saveProgressIndex(false);
    });
  },

  // 选择答案（单选题/判断题）
  onSelectAnswer(e: any) {
    if (this.data.showAnswer || this.data.mode === 'memo') {
      return; // 已提交或背题模式不允许选择
    }
    
    const answer = (e.currentTarget.dataset.answer as string) || '';
    const { currentQuestion } = this.data;
    const qType: QuestionType = currentQuestion.q_type || '';
    
    // 多选题处理
    if (qType === '多选题') {
      const selectedAnswers = this.data.selectedAnswers.slice();
      const index = selectedAnswers.indexOf(answer);
      if (index > -1) {
        selectedAnswers.splice(index, 1); // 取消选择
      } else {
        selectedAnswers.push(answer); // 选择
      }
      this.setData({ selectedAnswers }, () => {
        this.refreshDisplayOptions();
        this.updateSubmitState();
        this.saveDraftAnswer();
      });
    } else {
      // 单选题/判断题
      this.setData({ selectedAnswer: answer }, () => {
        this.refreshDisplayOptions();
        this.updateSubmitState();

        // 选择题、判断题：点选即判
        if (this.data.mode === 'quiz' && !this.data.showAnswer && (qType === '选择题' || qType === '判断题')) {
          this.onSubmitAnswer();
        }
      });
    }
  },

  // 输入答案（主观题：问答/计算/简答）
  onInputAnswer(e: any) {
    if (this.data.showAnswer || this.data.mode === 'memo') {
      return;
    }
    const cq = this.data.currentQuestion;
    const qType: QuestionType = (cq && cq.q_type) || '';
    if (qType === '填空题') {
      return;
    }
    this.setData({ selectedAnswer: e.detail.value }, () => {
      this.updateSubmitState();
      this.saveDraftAnswer();
    });
  },

  // 输入答案（填空题：多空）
  onBlankInput(e: any) {
    if (this.data.showAnswer || this.data.mode === 'memo') {
      return;
    }
    const cq = this.data.currentQuestion;
    const qType: QuestionType = (cq && cq.q_type) || '';
    if (qType !== '填空题') {
      return;
    }
    const idx = Number(e.currentTarget.dataset.index);
    if (!isFinite(idx) || idx < 0) {
      return;
    }
    const next = this.data.blankAnswers.slice();
    next[idx] = e.detail.value;
    this.setData({ blankAnswers: next }, () => {
      this.updateSubmitState();
      this.saveDraftAnswer();
    });
  },

  // 提交答案（刷题模式）
  async onSubmitAnswer() {
    const { currentQuestion, selectedAnswer, selectedAnswers, mode, blankAnswers } = this.data;
    
    if (mode === 'memo') {
      return; // 背题模式不需要提交
    }
    
    if (!currentQuestion) {
      return;
    }
    
    const qType: QuestionType = currentQuestion.q_type || '';
    const isJudgable = this.isAutoJudgable(qType);

    // 检查是否已选择答案
    let userAnswer = '';
    let userAnswerText = '';

    if (qType === '多选题') {
      if (selectedAnswers.length === 0) {
        wx.showToast({ title: '请选择答案', icon: 'none' });
        return;
      }
      userAnswer = selectedAnswers.sort().join(''); // 排序后拼接
      userAnswerText = userAnswer;
    } else if (qType === '填空题') {
      const normalized = (blankAnswers || []).map((x) => (x || '').trim());
      if (normalized.length === 0 || normalized.some((x) => !x)) {
        wx.showToast({ title: '请填写所有空', icon: 'none' });
        return;
      }
      userAnswer = normalized.join(';;');
      userAnswerText = normalized.join(' / ');
    } else if (qType === '问答题' || qType === '简答题' || qType === '计算题') {
      const t = (selectedAnswer || '').trim();
      if (!t) {
        wx.showToast({ title: '请输入答案', icon: 'none' });
        return;
      }
      userAnswer = t;
      userAnswerText = t;
    } else {
      if (!selectedAnswer) {
        wx.showToast({ title: '请选择或输入答案', icon: 'none' });
        return;
      }
      userAnswer = selectedAnswer.trim();
      userAnswerText = userAnswer;
    }
    
    // 验证答案
    const correctAnswer = currentQuestion.answer || '';
    const isCorrect = isJudgable ? this.checkAnswer(userAnswer, correctAnswer, qType) : false;
    
    // 更新进度缓存（answers/status/order/index）
    this.setProgressAnswerForIndex(this.data.currentIndex, qType);
    if (isJudgable) {
      this.progressStatusMap = this.progressStatusMap || {};
      this.progressStatusMap[String(this.data.currentIndex)] = isCorrect ? 'correct' : 'wrong';
    }

    this.setData({
      showAnswer: true,
      isCorrect,
      isJudgable,
      userAnswerText
    }, () => {
      this.refreshDisplayOptions();
      this.updateSubmitState();
    });
    
    // 记录答题结果（主观题不自动判分，避免误记错题）
    if (isJudgable) {
      const nextRecords: any = Object.assign({}, this.data.answerRecords);
      nextRecords[currentQuestion.id] = {
        answered: true,
        isCorrect
      };
      this.setData({
        answerRecords: nextRecords
      });
    }

    // 更新 questions 列表里的错题标记（保证“错题本”筛选能即时生效）
    if (isJudgable) {
      const questions = this.data.questions.map((q: any) => {
        if (q.id !== currentQuestion.id) return q;
        return Object.assign({}, q, { is_mistake: isCorrect ? 0 : 1 });
      });
      this.setData({ questions });
    }

    // 重要操作：立即同步进度到云端
    this.saveProgressIndex(true);
    
    // 调用API记录答题结果
    try {
      if (isJudgable) {
        await api.recordResult(currentQuestion.id, isCorrect);
      }
    } catch (err: any) {
      console.error('记录答题结果失败:', err);
    }

    // 震动反馈（提交后）
    if (isJudgable && this.data.practiceSettings.vibrationFeedback) {
      try {
        const vibrateType = isCorrect ? 'medium' : 'heavy';
        // @ts-ignore - 部分基础库不支持 type 参数
        wx.vibrateShort({ type: vibrateType });
      } catch (e) {
        try {
          wx.vibrateShort();
        } catch (e2) {
          // ignore
        }
      }
    }

    // 做错自动收藏（仅在未收藏时触发）
    if (isJudgable && !isCorrect && this.data.practiceSettings.autoFavoriteOnWrong) {
      await this.autoFavoriteIfNeeded();
    }

    // 答对自动切题（给用户一点点反馈时间）
    if (isJudgable && isCorrect && this.data.practiceSettings.autoNextOnCorrect) {
      setTimeout(() => {
        // 仍在当前题且已展示答案时再切题
        if (this.data.showAnswer && this.data.currentQuestion && this.data.currentQuestion.id === currentQuestion.id) {
          this.onNextQuestion();
        }
      }, 650);
    }
  },

  async autoFavoriteIfNeeded() {
    const { currentQuestion, isFavorite } = this.data;
    if (!currentQuestion || isFavorite) return;

    try {
      await api.toggleFavorite(currentQuestion.id);
      this.setData({ isFavorite: true });
      const questions = this.data.questions.map((q: any) => {
        if (q.id === currentQuestion.id) return Object.assign({}, q, { is_fav: 1 });
        return q;
      });
      this.setData({ questions });
    } catch (err: any) {
      console.error('自动收藏失败:', err);
    }
  },

  onToggleAIExplain() {
    const next = !this.data.showAIExplain;
    this.setData({ showAIExplain: next }, () => {
      if (next) {
        this.loadAIExplain(false);
      }
    });
  },

  onRegenerateAIExplain() {
    this.loadAIExplain(true);
  },

  async loadAIExplain(force: boolean) {
    const cq = this.data.currentQuestion;
    if (!cq) return;

    const qid = Number(cq.id) || 0;
    if (!force && this.data.aiExplainText && this.data.aiExplainQuestionId === qid) {
      return;
    }

    const options = Array.isArray(cq.options)
      ? cq.options.map((x: any) => ({ key: x.key, value: x.value }))
      : undefined;

    this.setData({ aiLoading: true, aiExplainError: '', aiExplainText: '', aiExplainQuestionId: qid });
    try {
      const res: any = await api.aiExplain({
        question_id: qid || undefined,
        content: (cq.content || '').toString(),
        q_type: (cq.q_type || '').toString(),
        options
      });
      const text = (res && res.explain) ? String(res.explain) : '';
      this.setData({ aiExplainText: text || '暂无解析内容', aiLoading: false });
    } catch (err: any) {
      console.error('AI解析失败:', err);
      this.setData({ aiExplainError: err?.message || 'AI解析失败，请稍后重试', aiLoading: false });
    }
  },

  // 检查答案是否正确
  checkAnswer(userAnswer: string, correctAnswer: string, qType: string): boolean {
    if (qType === '多选题') {
      // 多选题：答案排序后比较
      const userAnswerSorted = userAnswer.split('').sort().join('');
      const correctAnswerSorted = correctAnswer.split('').sort().join('');
      return userAnswerSorted === correctAnswerSorted;
    } else if (qType === '填空题') {
      // 填空题：支持一题多空（;; 分隔），一空多答案（; 分隔）
      const userBlanks = userAnswer.split(';;').map((x) => x.trim());
      const normalizedCorrect = (correctAnswer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
      const correctBlanksRaw = normalizedCorrect.split(';;').map((x) => x.trim());
      const blankCount = Math.max(userBlanks.length, correctBlanksRaw.length, 1);

      for (let i = 0; i < blankCount; i++) {
        const userBlank = (userBlanks[i] || '').trim();
        const correctBlank = (correctBlanksRaw[i] || '').trim();
        if (!userBlank) {
          return false;
        }
        if (!correctBlank) {
          return false;
        }

        const correctAlternatives = correctBlank
          .split(';')
          .map((x) => x.trim())
          .filter(Boolean)
          .map((x) => x.toLowerCase());

        const u = userBlank.toLowerCase();
        if (correctAlternatives.length === 0) {
          if (u !== correctBlank.toLowerCase()) {
            return false;
          }
        } else {
          if (!correctAlternatives.includes(u)) {
            return false;
          }
        }
      }

      return true;
    } else {
      // 单选题/判断题/填空题：直接比较（忽略大小写和空格）
      const ua = userAnswer.trim().toLowerCase();
      const ca = (correctAnswer || '').toString().replace(/；/g, ';').trim().toLowerCase();

      // 支持单空多答案（; 分隔）
      if (ca.includes(';')) {
        const candidates = ca
          .split(';')
          .map((x) => x.trim())
          .filter(Boolean);
        return candidates.includes(ua);
      }

      return ua === ca;
    }
  },

  // 切换收藏
  async onToggleFavorite() {
    const { currentQuestion, isFavorite } = this.data;
    if (!currentQuestion) {
      return;
    }
    
    try {
      await api.toggleFavorite(currentQuestion.id);
      this.setData({
        isFavorite: !isFavorite
      });
      
      // 更新题目数据
      const questions = this.data.questions.map((q: any) => {
        if (q.id === currentQuestion.id) {
          return Object.assign({}, q, { is_fav: !isFavorite ? 1 : 0 });
        }
        return q;
      });
      
      this.setData({ questions });
      
      wx.showToast({
        title: !isFavorite ? '已收藏' : '已取消收藏',
        icon: 'none',
        duration: 1500
      });
    } catch (err: any) {
      console.error('切换收藏失败:', err);
      wx.showToast({ title: err.message || '操作失败', icon: 'none' });
    }
  },

  // 上一题
  onPrevQuestion() {
    const { currentIndex } = this.data;
    if (currentIndex > 0) {
      this.loadQuestion(currentIndex - 1);
    }
  },

  // 下一题
  onNextQuestion() {
    const { currentIndex, questions } = this.data;
    if (currentIndex < questions.length - 1) {
      this.loadQuestion(currentIndex + 1);
    } else {
      // 最后一题，显示完成提示
      wx.showModal({
        title: '提示',
        content: '已是最后一题，是否返回？',
        success: (res) => {
          if (res.confirm) {
            wx.navigateBack();
          }
        }
      });
    }
  },

  // 打开题目列表抽屉
  onOpenQuestionList() {
    this.setData({ showQuestionList: true });
  },

  // 关闭题目列表抽屉
  onCloseQuestionList() {
    this.setData({ showQuestionList: false });
  },

  // 点击题目列表项
  onQuestionListItemTap(e: any) {
    const index = e.currentTarget.dataset.index;
    this.loadQuestion(index);
    this.onCloseQuestionList();
  },

  // 工具函数：打乱数组
  shuffleArray<T>(array: T[]): T[] {
    const shuffled = array.slice();
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      const tmp = shuffled[i];
      shuffled[i] = shuffled[j];
      shuffled[j] = tmp;
    }
    return shuffled;
  },

  // 预览图片
  previewImage(e: any) {
    const idx = Number(e.currentTarget.dataset.index || 0);
    const urls = (this.data.currentQuestion && this.data.currentQuestion.image_urls) || [];
    if (!Array.isArray(urls) || urls.length === 0) return;
    const current = urls[Math.max(0, Math.min(idx, urls.length - 1))] || urls[0];
    wx.previewImage({ urls, current });
  },

  // 阻止事件冒泡（用于抽屉）
  stopPropagation() {
    // 空函数，用于阻止点击事件冒泡
  },

  normalizeOptions(rawOptions: any, qType: string, correctAnswer?: string): OptionItem[] {
    let optList: any = rawOptions;

    if (typeof optList === 'string') {
      const s = optList.trim();
      if (!s) {
        optList = [];
      } else {
        try {
          optList = JSON.parse(s);
        } catch (e) {
          console.warn('options JSON 解析失败，将按纯文本处理:', e);
          optList = [s];
        }
      }
    }

    if (!Array.isArray(optList)) {
      optList = [];
    }

    if (qType === '判断题') {
      const ans = (correctAnswer || '').toString().trim();
      // 如果答案是字母（少数历史格式），优先使用题目自带 options
      if (!/^[A-Za-z]$/.test(ans)) {
        const normalized = ans.toLowerCase();
        let trueText = '正确';
        let falseText = '错误';

        if (normalized === '对' || normalized === '错') {
          trueText = '对';
          falseText = '错';
        } else if (normalized === '是' || normalized === '否') {
          trueText = '是';
          falseText = '否';
        } else if (normalized === 'true' || normalized === 'false') {
          trueText = 'True';
          falseText = 'False';
        }

        return [
          { key: 'A', value: trueText, answerValue: trueText },
          { key: 'B', value: falseText, answerValue: falseText }
        ];
      }
    }

    const options: OptionItem[] = [];
    for (const item of optList) {
      if (item && typeof item === 'object') {
        const rawKey = (item as any).key;
        const rawValue = (item as any).value;
        const key = String(rawKey == null ? '' : rawKey).trim();
        const value = String(rawValue == null ? '' : rawValue).trim();
        if (key || value) {
          options.push({ key, value, answerValue: key || value });
        }
        continue;
      }

      const s = String(item == null ? '' : item).trim();
      if (!s) {
        continue;
      }

      // 解析 "A、xxx" / "A.xxx" / "A：xxx"
      const m = s.match(/^([A-Za-z0-9]{1,3})\s*[、.．:：]\s*(.+)$/);
      if (m) {
        const key = m[1].trim().slice(0, 1).toUpperCase();
        const value = m[2].trim();
        options.push({ key, value, answerValue: key });
        continue;
      }

      // 兜底：如果首字符像 A/B/C/D，尝试把它当 key
      const first = s.slice(0, 1).toUpperCase();
      if (first && 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.includes(first)) {
        const value = s.slice(1).replace(/^[\s:：.,、]+/, '').trim();
        options.push({ key: first, value, answerValue: first });
        continue;
      }

      options.push({ key: '', value: s, answerValue: s });
    }

    // 如果 key 全为空，补 A/B/C...（仅用于展示，答题用 answerValue 仍保持原始 value）
    if (options.length > 0 && options.every((x) => !(x.key || '').trim())) {
      const seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      options.forEach((x, i) => {
        x.key = seed[i] || String(i + 1);
      });
    }

    return options;
  },

  refreshDisplayOptions() {
    const { currentQuestion, selectedAnswer, selectedAnswers, showAnswer, mode } = this.data;
    if (!currentQuestion) {
      this.setData({ displayOptions: [] });
      return;
    }

    const qType: QuestionType = currentQuestion.q_type || '';
    const correctAnswer = (currentQuestion.answer || '').toString();
    const correctAnswerNormalized = correctAnswer.trim().toLowerCase();
    const shouldShowResult = showAnswer || mode === 'memo';

    const normalizedOptions = this.normalizeOptions(currentQuestion.options, qType, currentQuestion.answer);

    const displayOptions: DisplayOption[] = normalizedOptions.map((opt) => {
      const isSelected =
        qType === '多选题' ? selectedAnswers.indexOf(opt.answerValue) > -1 : selectedAnswer === opt.answerValue;

      const isCorrect = shouldShowResult
        ? correctAnswerNormalized.indexOf(opt.answerValue.toString().trim().toLowerCase()) > -1
        : false;
      const isWrong = showAnswer ? isSelected && !isCorrect : false;

      const classParts: string[] = [];
      if (isSelected) classParts.push('selected');
      if (isCorrect) classParts.push('correct');
      if (isWrong) classParts.push('wrong');

      return {
        key: opt.key,
        value: opt.value,
        answerValue: opt.answerValue,
        isSelected,
        isCorrect,
        isWrong,
        className: classParts.join(' ')
      };
    });

    this.setData({
      displayOptions,
      currentQuestion: Object.assign({}, currentQuestion, { options: normalizedOptions })
    });
  },

  isAutoJudgable(qType: QuestionType): boolean {
    return qType === '选择题' || qType === '多选题' || qType === '判断题' || qType === '填空题';
  },

  updateSubmitState() {
    const { currentQuestion, mode, showAnswer, selectedAnswers, selectedAnswer, blankAnswers } = this.data;
    if (!currentQuestion || mode !== 'quiz' || showAnswer) {
      this.setData({ showSubmitButton: false, submitDisabled: true });
      return;
    }

    const qType: QuestionType = currentQuestion.q_type || '';
    const showSubmit =
      qType === '多选题' || qType === '填空题' || qType === '问答题' || qType === '简答题' || qType === '计算题';

    let disabled = true;
    if (qType === '多选题') {
      disabled = selectedAnswers.length === 0;
    } else if (qType === '填空题') {
      disabled = !blankAnswers.length || blankAnswers.some((x) => !(x || '').trim());
    } else if (qType === '问答题' || qType === '简答题' || qType === '计算题') {
      disabled = !(selectedAnswer || '').trim();
    } else {
      disabled = true;
    }

    this.setData({ showSubmitButton: showSubmit, submitDisabled: showSubmit ? disabled : true });
  },

  initBlankState(
    qType: QuestionType,
    content: string,
    answer: string
  ): { blankCount: number; blankAnswers: string[]; blankIndexes: number[] } {
    if (qType !== '填空题') {
      return { blankCount: 0, blankAnswers: [], blankIndexes: [] };
    }

    const contentCount = (content.match(/__/g) || []).length;
    const normalizedAnswer = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
    const answerCount = normalizedAnswer.split(';;').length;
    const blankCount = Math.max(1, contentCount || 0, answerCount || 0);
    return {
      blankCount,
      blankAnswers: Array.from({ length: blankCount }, () => ''),
      blankIndexes: Array.from({ length: blankCount }, (_, i) => i)
    };
  },

  formatContentForDisplay(content: string): string {
    return (content || '').toString();
  },

  looksLikeCode(text: string): boolean {
    const s = (text || '').toString();
    if (!s.includes('\n')) return false;
    const hasIndent = /(^|\n)[ \t]{2,}\S/.test(s);
    const hasCodeTokens =
      /\b(for|while|if|else|elif|def|class|print|return|break|continue|import|from|int|float|public|private|static|void|main)\b/.test(
        s
      );
    const hasSymbols = /[{}();=<>]/.test(s);
    return hasIndent || hasCodeTokens || hasSymbols;
  },

  preserveSpacesForCode(text: string): string {
    const s = (text || '').toString().replace(/\t/g, '  ');
    // 小程序 <text> 会折叠连续空格；代码场景将空格替换为 NBSP 保留缩进/对齐
    return s
      .split('\n')
      .map((line) => line.replace(/ /g, '\u00A0'))
      .join('\n');
  },

  formatAnswerForDisplay(qType: QuestionType, answer: string): string {
    const a = (answer || '').toString().replace(/；；/g, ';;').replace(/；/g, ';');
    if (qType === '填空题') {
      return a.replace(/;;/g, ' / ').replace(/;/g, ' 或 ');
    }
    return a;
  },

  buildProgressKey(): string {
    const userInfo = wx.getStorageSync('userInfo') || {};
    const uid = (userInfo && (userInfo.id || userInfo.user_id)) ? String(userInfo.id || userInfo.user_id) : 'guest';

    const mode = (this.data.mode || 'quiz').toString();
    const subject = (this.data.subject || 'all').toString();
    const type = (this.data.qType || 'all').toString();

    const sourceParam = (this.data.source || '').toString();
    const dataScope = (sourceParam === 'favorites' || sourceParam === 'mistakes') ? sourceParam : 'all';

    const shuffleQ = this.data.shuffleQuestions ? '1' : '0';
    const shuffleO = this.data.shuffleOptions ? '1' : '0';

    return `quiz_progress_${uid}_${mode}_${subject}_${type}_${dataScope}_q${shuffleQ}_o${shuffleO}`;
  },

  async loadProgressState(key: string): Promise<any | null> {
    if (!key) return null;

    const local = this.safeParseStorage(wx.getStorageSync(key));
    let remote: any = null;
    try {
      remote = await api.getProgress(key);
    } catch (e) {
      remote = null;
    }

    const merged = this.pickLatestProgress(local, remote);
    if (merged) {
      try {
        wx.setStorageSync(key, merged);
      } catch (e) {}
    }
    return merged;
  },

  safeParseStorage(val: any): any | null {
    if (!val) return null;
    if (typeof val === 'string') {
      try {
        return JSON.parse(val);
      } catch (e) {
        return null;
      }
    }
    if (typeof val === 'object') return val;
    return null;
  },

  pickLatestProgress(a: any, b: any): any | null {
    if (!a && !b) return null;
    if (a && !b) return a;
    if (!a && b) return b;

    const ta = Number(a && a.timestamp) || 0;
    const tb = Number(b && b.timestamp) || 0;
    return tb >= ta ? b : a;
  },

  applyQuestionOrder(questions: any[], order: any[]): any[] {
    try {
      const map = new Map<number, any>();
      questions.forEach((q: any) => {
        if (q && typeof q.id === 'number') map.set(q.id, q);
      });

      const ordered: any[] = [];
      order.forEach((id: any) => {
        const qid = Number(id);
        if (!isFinite(qid)) return;
        const hit = map.get(qid);
        if (hit) {
          ordered.push(hit);
          map.delete(qid);
        }
      });

      if (map.size > 0) {
        ordered.push(...Array.from(map.values()));
      }
      return ordered;
    } catch (e) {
      return questions;
    }
  },

  buildAnswerRecordsFromStatus(questions: any[], status: any): Record<number, { answered: boolean; isCorrect: boolean }> {
    const records: Record<number, { answered: boolean; isCorrect: boolean }> = {};
    if (!status || typeof status !== 'object') return records;

    Object.keys(status).forEach((k) => {
      const idx = Number(k);
      if (!isFinite(idx) || idx < 0 || idx >= questions.length) return;
      const v = status[k];
      if (v !== 'correct' && v !== 'wrong') return;
      const q = questions[idx];
      if (!q || typeof q.id !== 'number') return;
      records[q.id] = { answered: true, isCorrect: v === 'correct' };
    });

    return records;
  },

  getSavedAnswerForIndex(index: number): any {
    const map = this.progressAnswerMap;
    if (!map || typeof map !== 'object') return null;
    return map[String(index)];
  },

  getSavedStatusForIndex(index: number): any {
    const map = this.progressStatusMap;
    if (!map || typeof map !== 'object') return null;
    return map[String(index)];
  },

  setProgressAnswerForIndex(index: number, qType: QuestionType) {
    if (!this.progressAnswerMap || typeof this.progressAnswerMap !== 'object') {
      this.progressAnswerMap = {};
    }

    if (qType === '多选题') {
      this.progressAnswerMap[String(index)] = (this.data.selectedAnswers || []).slice();
      return;
    }
    if (qType === '选择题' || qType === '判断题') {
      const a = (this.data.selectedAnswer || '').trim();
      this.progressAnswerMap[String(index)] = a ? [a] : [];
      return;
    }
    if (qType === '填空题') {
      this.progressAnswerMap[String(index)] = (this.data.blankAnswers || []).slice();
      return;
    }

    // 问答/简答/计算
    this.progressAnswerMap[String(index)] = (this.data.selectedAnswer || '').toString();
  },

  saveDraftAnswer() {
    if (this.data.mode !== 'quiz' || this.data.showAnswer) return;
    if (!this.data.currentQuestion) return;

    const qType: QuestionType = this.data.currentQuestion.q_type || '';
    this.setProgressAnswerForIndex(this.data.currentIndex, qType);
    this.saveProgressIndex(false);
  },

  saveProgressIndex(immediate: boolean) {
    const key = this.progressKey || this.buildProgressKey();
    if (!key) return;

    const payload: any = {
      index: this.data.currentIndex,
      status: this.progressStatusMap || {},
      answers: this.progressAnswerMap || {},
      timestamp: Date.now()
    };
    if (this.progressOrder) {
      payload.order = this.progressOrder;
    }

    this.saveProgressState(payload, immediate);
  },

  saveProgressState(payload: any, immediate: boolean) {
    const key = this.progressKey || this.buildProgressKey();
    if (!key) return;

    try {
      wx.setStorageSync(key, payload);
    } catch (e) {}

    this.lastSavedPayload = payload;
    this.syncPending = true;

    if (immediate) {
      if (this.saveProgressTimer) {
        clearTimeout(this.saveProgressTimer);
        this.saveProgressTimer = null;
      }
      this.syncToServer(payload);
      return;
    }

    if (this.saveProgressTimer) {
      clearTimeout(this.saveProgressTimer);
    }
    this.saveProgressTimer = setTimeout(() => {
      this.saveProgressTimer = null;
      this.syncToServer(payload);
    }, 200);
  },

  async syncToServer(payload: any) {
    if (!payload) return;
    const key = this.progressKey || this.buildProgressKey();
    if (!key) return;

    try {
      await api.saveProgress(key, payload);
      this.syncPending = false;
    } catch (e) {
      // 网络波动时保留本地进度即可
    }
  },

  // 保存“上次练习”指针（云端 + 本地），用于首页一键继续
  async saveLastSession(force = false) {
    const subject = (this.data.subject || '').toString().trim();
    if (!subject) return;

    const payload = {
      subject,
      mode: (this.data.mode || 'quiz').toString(),
      type: (this.data.qType || 'all').toString(),
      source: (this.data.source || 'all').toString(),
      shuffle_questions: this.data.shuffleQuestions ? 1 : 0,
      shuffle_options: this.data.shuffleOptions ? 1 : 0,
      progress_key: this.progressKey || this.buildProgressKey(),
      timestamp: Date.now()
    };

    const key = 'last_practice_session';
    try {
      wx.setStorageSync(key, payload);
    } catch (e) {}

    // 避免频繁写云端：仅在强制 flush 时写一次
    if (!force) return;
    try {
      await api.saveProgress(key, payload);
    } catch (e) {}
  },

  onHide() {
    if (this.syncPending && this.lastSavedPayload) {
      this.saveProgressState(this.lastSavedPayload, true);
    }
    this.saveLastSession(true);
  },

  onUnload() {
    if (this.syncPending && this.lastSavedPayload) {
      this.saveProgressState(this.lastSavedPayload, true);
    }
    if (this.saveProgressTimer) {
      clearTimeout(this.saveProgressTimer);
      this.saveProgressTimer = null;
    }
    this.saveLastSession(true);
  }
});
