// exam-run.ts - 模拟考试
import { api, normalizeImageUrls } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

type OptionItem = {
  key: string;
  value: string;
  answerValue: string;
};

type DisplayOption = OptionItem & {
  isSelected: boolean;
  className: string;
};

type QuestionType = '选择题' | '多选题' | '判断题' | '填空题' | '问答题' | '简答题' | '计算题' | string;

Page({
  data: {
    examId: 0,
    loading: false,
    submitted: false,

    exam: null as any,
    questions: [] as any[],
    currentIndex: 0,
    currentQuestion: null as any,

    selectedAnswer: '',
    selectedAnswers: [] as string[],
    displayOptions: [] as DisplayOption[],
    blankAnswers: [] as string[],
    blankIndexes: [] as number[],
    blankCount: 0,

    answers: {} as Record<number, string>,

    showQuestionList: false,

    timeLeft: 0,
    timeText: '00:00'
  },

  draftTimer: null as any,
  tickTimer: null as any,

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    const examId = Number(options.exam_id);
    if (!isFinite(examId) || examId <= 0) {
      wx.showToast({ title: '考试参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1200);
      return;
    }

    this.setData({ examId });
    this.loadExam();
  },

  onHide() {
    this.flushDraft();
  },

  onUnload() {
    this.flushDraft();
    if (this.tickTimer) {
      clearInterval(this.tickTimer);
      this.tickTimer = null;
    }
    if (this.draftTimer) {
      clearTimeout(this.draftTimer);
      this.draftTimer = null;
    }
  },

  async loadExam() {
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      const res: any = await api.getExam(this.data.examId);
      const exam = res.exam || {};
      let questions = (res.questions || []) as any[];

      // 预览内容
      questions = questions.map((q: any) => {
        const content = q.content || '';
        const text = String(content).replace(/<[^>]+>/g, '').replace(/\n/g, ' ').trim();
        const preview = text.length > 40 ? text.slice(0, 40) + '...' : text;
        const imageUrls = normalizeImageUrls(q.image_path);
        const imagePath = imageUrls.length > 0 ? imageUrls[0] : '';
        return Object.assign({}, q, { contentPreview: preview, image_urls: imageUrls, image_path: imagePath });
      });

      // 初始化答案缓存（草稿）
      const answers: Record<number, string> = {};
      questions.forEach((q: any) => {
        const ua = (q.user_answer || '').toString();
        if (ua && q.id) {
          answers[q.id] = ua;
        }
      });

      const submitted = exam.status === 'submitted';

      // 计时器
      const durationMin = Number(exam.duration_minutes) || 60;
      const timeLeft = submitted ? 0 : this.computeRemainingSeconds(exam.started_at, durationMin);

      this.setData(
        {
          exam,
          questions,
          answers,
          submitted,
          timeLeft,
          timeText: this.formatTime(timeLeft),
          loading: false
        },
        () => {
          if (questions.length > 0) {
            this.loadQuestion(0);
          }
          if (!submitted) {
            this.startTimer();
          }
        }
      );
    } catch (err: any) {
      console.error('加载考试失败:', err);
      this.setData({ loading: false });
      wx.showToast({ title: (err && err.message) || '加载失败', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1200);
    }
  },

  computeRemainingSeconds(startedAt: string, durationMin: number): number {
    const total = Math.max(1, durationMin) * 60;
    if (!startedAt) return total;
    const iso = String(startedAt).replace(' ', 'T');
    const d = new Date(iso);
    if (isNaN(d.getTime())) return total;
    const elapsed = Math.floor((Date.now() - d.getTime()) / 1000);
    return Math.max(0, total - Math.max(0, elapsed));
  },

  startTimer() {
    if (this.tickTimer) {
      clearInterval(this.tickTimer);
    }
    this.tickTimer = setInterval(() => {
      const next = Math.max(0, (this.data.timeLeft || 0) - 1);
      this.setData({ timeLeft: next, timeText: this.formatTime(next) });
      if (next <= 0) {
        clearInterval(this.tickTimer);
        this.tickTimer = null;
        this.autoSubmitWhenTimeout();
      }
    }, 1000);
  },

  formatTime(sec: number): string {
    const s = Math.max(0, Number(sec) || 0);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`;
  },

  autoSubmitWhenTimeout() {
    if (this.data.submitted) return;
    wx.showToast({ title: '时间到，正在交卷', icon: 'none' });
    this.doSubmitExam(true);
  },

  loadQuestion(index: number) {
    const { questions } = this.data;
    if (index < 0 || index >= questions.length) return;

    const q = questions[index];
    const qType: QuestionType = q.q_type || '';
    const rawContent = (q.content || '').toString();
    const rawAnswer = (q.answer || '').toString();

    let displayContent = this.formatContentForDisplay(rawContent);
    if (qType === '填空题') {
      displayContent = displayContent.replace(/__/g, '____');
    }

    const isCode = this.looksLikeCode(displayContent);
    if (isCode) {
      displayContent = this.preserveSpacesForCode(displayContent);
    }
    const displayAnswer = this.formatAnswerForDisplay(qType, rawAnswer);

    const rawExplanation = (q.explanation || '').toString();
    const explanationIsCode = this.looksLikeCode(rawExplanation);
    const displayExplanation = explanationIsCode ? this.preserveSpacesForCode(rawExplanation) : rawExplanation;

    const normalizedOptions = this.normalizeOptions(q.options, qType, rawAnswer);
    const blankState = this.initBlankState(qType, rawContent, rawAnswer);

    // 恢复草稿答案
    const ua = (this.data.answers && q.id) ? (this.data.answers[q.id] || '') : '';

    let selectedAnswer = '';
    let selectedAnswers: string[] = [];
    let blankAnswers = blankState.blankAnswers.slice();
    let blankCount = blankState.blankCount;
    let blankIndexes = blankState.blankIndexes.slice();

    if (ua) {
      if (qType === '多选题') {
        selectedAnswers = ua.split('').filter(Boolean);
      } else if (qType === '选择题' || qType === '判断题') {
        selectedAnswer = ua;
      } else if (qType === '填空题') {
        const normalized = ua.replace(/；；/g, ';;').replace(/；/g, ';');
        // 多空：后端保存可能是 JSON 数组字符串
        try {
          const tmp = JSON.parse(normalized);
          if (Array.isArray(tmp)) {
            const filledCount = Math.max(blankCount, tmp.length);
            blankCount = filledCount;
            blankIndexes = Array.from({ length: filledCount }, (_, i) => i);
            blankAnswers = Array.from({ length: filledCount }, (_, i) => String(tmp[i] || ''));
          }
        } catch (e) {
          const parts = normalized.split(';;').map((x) => x.trim()).filter((x) => x.length > 0);
          if (parts.length > 0) {
            const filledCount = Math.max(blankCount, parts.length);
            blankCount = filledCount;
            blankIndexes = Array.from({ length: filledCount }, (_, i) => i);
            blankAnswers = Array.from({ length: filledCount }, (_, i) => parts[i] || '');
          }
        }
      } else if (qType === '问答题' || qType === '简答题' || qType === '计算题') {
        selectedAnswer = ua;
      }
    }

    this.setData(
      {
        currentIndex: index,
        currentQuestion: Object.assign({}, q, {
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
        blankAnswers,
        blankIndexes
      },
      () => {
        this.refreshDisplayOptions();
      }
    );
  },

  onSelectAnswer(e: any) {
    if (this.data.submitted) return;
    const answer = (e.currentTarget.dataset.answer as string) || '';
    const cq = this.data.currentQuestion;
    if (!cq) return;
    const qType: QuestionType = cq.q_type || '';

    if (qType === '多选题') {
      const next = (this.data.selectedAnswers || []).slice();
      const i = next.indexOf(answer);
      if (i > -1) next.splice(i, 1);
      else next.push(answer);
      this.setData({ selectedAnswers: next }, () => {
        this.refreshDisplayOptions();
        this.saveCurrentAnswerDraft();
      });
      return;
    }

    this.setData({ selectedAnswer: answer }, () => {
      this.refreshDisplayOptions();
      this.saveCurrentAnswerDraft();
    });
  },

  onInputAnswer(e: any) {
    if (this.data.submitted) return;
    this.setData({ selectedAnswer: e.detail.value || '' }, () => {
      this.saveCurrentAnswerDraft();
    });
  },

  onBlankInput(e: any) {
    if (this.data.submitted) return;
    const idx = Number(e.currentTarget.dataset.index);
    if (!isFinite(idx) || idx < 0) return;
    const next = (this.data.blankAnswers || []).slice();
    next[idx] = e.detail.value;
    this.setData({ blankAnswers: next }, () => {
      this.saveCurrentAnswerDraft();
    });
  },

  saveCurrentAnswerDraft() {
    const cq = this.data.currentQuestion;
    if (!cq || !cq.id) return;
    const qType: QuestionType = cq.q_type || '';
    const qid = cq.id as number;

    const ua = this.serializeCurrentAnswer(qType);
    const nextAnswers: any = Object.assign({}, this.data.answers);
    nextAnswers[qid] = ua;

    this.setData({ answers: nextAnswers }, () => {
      this.queueDraftSave(qid, ua);
    });
  },

  serializeCurrentAnswer(qType: QuestionType): string {
    if (qType === '多选题') {
      return (this.data.selectedAnswers || []).slice().sort().join('');
    }
    if (qType === '选择题' || qType === '判断题') {
      return (this.data.selectedAnswer || '').trim();
    }
    if (qType === '填空题') {
      const blanks = (this.data.blankAnswers || []).map((x) => (x || '').trim());
      if (blanks.length <= 1) {
        return (blanks[0] || '').trim();
      }
      return JSON.stringify(blanks);
    }
    // 主观题
    return (this.data.selectedAnswer || '').toString();
  },

  queueDraftSave(qid: number, ua: string) {
    if (this.draftTimer) {
      clearTimeout(this.draftTimer);
      this.draftTimer = null;
    }
    this.draftTimer = setTimeout(() => {
      this.draftTimer = null;
      this.flushDraftSingle(qid, ua);
    }, 250);
  },

  async flushDraftSingle(qid: number, ua: string) {
    if (this.data.submitted) return;
    try {
      await api.saveExamDraft(this.data.examId, [{ question_id: qid, user_answer: ua || '' }]);
    } catch (e) {
      // 网络波动忽略，草稿仍保留在本地 answers
    }
  },

  flushDraft() {
    // 简化处理：交由单题保存的防抖完成；卸载时不做批量提交，避免卡顿
    if (this.draftTimer) {
      clearTimeout(this.draftTimer);
      this.draftTimer = null;
    }
  },

  onPrevQuestion() {
    if (this.data.currentIndex > 0) this.loadQuestion(this.data.currentIndex - 1);
  },

  onNextQuestion() {
    const idx = this.data.currentIndex;
    if (idx < this.data.questions.length - 1) {
      this.loadQuestion(idx + 1);
    } else {
      wx.showToast({ title: '已是最后一题', icon: 'none' });
    }
  },

  onOpenQuestionList() {
    this.setData({ showQuestionList: true });
  },

  onCloseQuestionList() {
    this.setData({ showQuestionList: false });
  },

  onQuestionListItemTap(e: any) {
    const index = Number(e.currentTarget.dataset.index);
    if (!isFinite(index)) return;
    this.loadQuestion(index);
    this.onCloseQuestionList();
  },

  stopPropagation() {},

  onSubmitExam() {
    if (this.data.submitted) return;
    this.submitExam(false);
  },

  submitExam(silent: boolean) {
    if (this.data.submitted) return;
    if (silent) {
      this.doSubmitExam(true);
      return;
    }

    wx.showModal({
      title: '确认交卷',
      content: '交卷后将无法继续修改答案，是否继续？',
      confirmText: '交卷',
      confirmColor: '#FF3B30',
      success: (res) => {
        if (!res.confirm) return;
        this.doSubmitExam(false);
      }
    });
  },

  async doSubmitExam(silent: boolean) {
    if (this.data.submitted) return;
    wx.showLoading({ title: '提交中...' });

    try {
      const answers = this.data.questions.map((q: any) => ({
        question_id: q.id,
        user_answer: (this.data.answers && q.id) ? (this.data.answers[q.id] || '') : ''
      }));

      const res: any = await api.submitExam(this.data.examId, answers);

      wx.hideLoading();
      if (this.tickTimer) {
        clearInterval(this.tickTimer);
        this.tickTimer = null;
      }

      this.setData({ submitted: true, timeLeft: 0, timeText: '00:00' });

      if (!silent) {
        const total = res.total || 0;
        const correct = res.correct || 0;
        const score = res.total_score || 0;
        wx.showModal({
          title: '成绩',
          content: `总题数：${total}\n答对：${correct}\n得分：${score}`,
          showCancel: false
        });
      }
    } catch (err: any) {
      console.error('提交考试失败:', err);
      wx.hideLoading();
      wx.showToast({ title: (err && err.message) || '提交失败', icon: 'none' });
    }
  },

  // ====== 工具函数（复用 quiz 页） ======
  refreshDisplayOptions() {
    const { currentQuestion, selectedAnswer, selectedAnswers } = this.data;
    if (!currentQuestion) {
      this.setData({ displayOptions: [] });
      return;
    }
    const qType: QuestionType = currentQuestion.q_type || '';
    const normalizedOptions = this.normalizeOptions(currentQuestion.options, qType, currentQuestion.answer);
    const displayOptions: DisplayOption[] = normalizedOptions.map((opt) => {
      const isSelected =
        qType === '多选题' ? selectedAnswers.indexOf(opt.answerValue) > -1 : selectedAnswer === opt.answerValue;
      const className = isSelected ? 'selected' : '';
      return Object.assign({}, opt, { isSelected, className });
    });
    this.setData({ displayOptions, currentQuestion: Object.assign({}, currentQuestion, { options: normalizedOptions }) });
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
          optList = [s];
        }
      }
    }

    if (!Array.isArray(optList)) {
      optList = [];
    }

    if (qType === '判断题') {
      const ans = (correctAnswer || '').toString().trim();
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
      if (!s) continue;

      const m = s.match(/^([A-Za-z0-9]+)[、.．:：\s]+(.+)$/);
      if (m) {
        const key = m[1].trim().slice(0, 1).toUpperCase();
        const value = m[2].trim();
        options.push({ key, value, answerValue: key });
        continue;
      }

      const first = s.slice(0, 1).toUpperCase();
      if (first && 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.includes(first)) {
        const value = s.slice(1).replace(/^[\s:：.,、]+/, '').trim();
        options.push({ key: first, value, answerValue: first });
        continue;
      }

      options.push({ key: '', value: s, answerValue: s });
    }

    if (options.length > 0 && options.every((x) => !(x.key || '').trim())) {
      const seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
      options.forEach((x, i) => {
        x.key = seed[i] || String(i + 1);
      });
    }

    return options;
  },

  initBlankState(qType: QuestionType, content: string, answer: string): { blankCount: number; blankAnswers: string[]; blankIndexes: number[] } {
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

  previewImage(e: any) {
    const idx = Number(e.currentTarget.dataset.index || 0);
    const urls = (this.data.currentQuestion && this.data.currentQuestion.image_urls) || [];
    if (!Array.isArray(urls) || urls.length === 0) return;
    const current = urls[Math.max(0, Math.min(idx, urls.length - 1))] || urls[0];
    wx.previewImage({ urls, current });
  }
});
