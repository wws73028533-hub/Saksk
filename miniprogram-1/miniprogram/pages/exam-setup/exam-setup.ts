// exam-setup.ts - 考试设置
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

type TypeItem = {
  name: string;
  available: number;
  enabled: boolean;
  count: number;
  score: number;
};

Page({
  data: {
    subject: '',
    duration: 60,
    total: 50,
    types: [] as TypeItem[],
    computedTotal: 0,
    computedScoreText: '0',
    loading: false,
    creating: false,
    warnText: ''
  },

  onLoad(options: any) {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }

    let subject = options.subject || '';
    if (!subject) {
      wx.showToast({ title: '科目参数缺失', icon: 'none' });
      setTimeout(() => wx.navigateBack(), 1200);
      return;
    }
    try {
      subject = decodeURIComponent(subject);
    } catch (e) {}

    this.setData({ subject });
    this.loadTypeCounts();
  },

  onDurationInput(e: any) {
    const v = Number(e.detail.value);
    const duration = isFinite(v) ? Math.max(1, Math.min(24 * 60, v)) : 60;
    this.setData({ duration });
  },

  onTotalInput(e: any) {
    const v = Number(e.detail.value);
    const total = isFinite(v) ? Math.max(1, Math.min(500, v)) : 50;
    this.setData({ total }, () => {
      this.refreshSummary();
    });
  },

  async loadTypeCounts() {
    if (this.data.loading) return;
    this.setData({ loading: true, warnText: '' });

    const baseTypes = ['选择题', '多选题', '判断题', '填空题', '问答题', '简答题', '计算题'];
    try {
      const subject = this.data.subject;
      const counts = await Promise.all(
        baseTypes.map(async (t) => {
          try {
            const res: any = await api.getQuestionsCount({ subject, type: t });
            return { name: t, available: Number(res.count || 0) };
          } catch (e) {
            return { name: t, available: 0 };
          }
        })
      );

      const types: TypeItem[] = counts
        .filter((x) => x.available > 0)
        .map((x, idx) => ({
          name: x.name,
          available: x.available,
          enabled: idx < 2,
          count: 0,
          score: 1
        }));

      // 初始给默认开启的题型分配题数（不覆盖后续用户自定义）
      const enabled = types.filter((t) => t.enabled);
      const defaultCounts = this.distributeCounts(this.data.total, enabled);
      const seeded = types.map((t) => {
        if (!t.enabled) return t;
        const c = Number(defaultCounts[t.name] || 0);
        const count = Math.max(0, Math.min(t.available, isFinite(c) ? c : 0));
        return Object.assign({}, t, { count, score: 1 });
      });

      this.setData({ types: seeded, loading: false }, () => {
        this.refreshSummary();
      });
    } catch (err) {
      console.error('加载题型失败:', err);
      this.setData({ types: [], loading: false, computedTotal: 0, computedScoreText: '0' });
    }
  },

  onToggleTypeSwitch(e: any) {
    const name = e.currentTarget.dataset.name;
    const value = !!(e && e.detail && e.detail.value);
    this.setTypeEnabled(name, value);
  },

  setTypeEnabled(name: string, enabled: boolean) {
    const next = (this.data.types || []).map((t) => {
      if (t.name !== name) return t;
      if (!enabled) {
        return Object.assign({}, t, { enabled: false, count: 0 });
      }
      // 启用：默认至少 1 题（若可用）
      const count = t.count > 0 ? t.count : Math.min(1, t.available);
      const scoreRaw = Number(t.score);
      const score = isFinite(scoreRaw) ? Math.max(0, Math.min(1000, scoreRaw)) : 1;
      return Object.assign({}, t, { enabled: true, count, score });
    });
    this.setData({ types: next }, () => {
      this.refreshSummary();
    });
  },

  onTypeConfigInput(e: any) {
    const name = e.currentTarget.dataset.name;
    const field = e.currentTarget.dataset.field;
    if (!name || !field) return;

    const next = (this.data.types || []).map((t) => {
      if (t.name !== name) return t;

      if (field === 'count') {
        const raw = Number(e.detail.value);
        const v = isFinite(raw) ? Math.max(0, Math.floor(raw)) : 0;
        const count = Math.min(v, t.available);
        return Object.assign({}, t, { count });
      }

      if (field === 'score') {
        const raw = Number(e.detail.value);
        const v = isFinite(raw) ? Math.max(0, Math.min(1000, raw)) : 0;
        return Object.assign({}, t, { score: v });
      }

      return t;
    });

    this.setData({ types: next }, () => {
      this.refreshSummary();
    });
  },

  refreshSummary() {
    const types = this.data.types || [];
    let total = 0;
    let score = 0;

    for (const t of types) {
      if (!t.enabled) continue;
      const c = Math.max(0, Math.min(t.available, Math.floor(Number(t.count) || 0)));
      const s = Math.max(0, Math.min(1000, Number(t.score) || 0));
      if (c <= 0) continue;
      total += c;
      score += c * s;
    }

    const scoreText = this.formatScore(score);

    let warnText = '';
    if (types.length > 0 && total > 0 && total !== this.data.total) {
      warnText = `当前已设置 ${total} 题，与目标 ${this.data.total} 题不一致`;
    }

    this.setData({ computedTotal: total, computedScoreText: scoreText, warnText });
  },

  formatScore(v: number): string {
    const n = Number(v) || 0;
    if (Math.abs(n - Math.round(n)) < 1e-6) {
      return String(Math.round(n));
    }
    return n.toFixed(1).replace(/\.0$/, '');
  },

  stopPropagation() {},

  async onStartExam() {
    if (this.data.creating || this.data.loading) return;

    const enabledTypes = (this.data.types || []).filter((t) => t.enabled);
    if (enabledTypes.length === 0) {
      wx.showToast({ title: '请选择题型', icon: 'none' });
      return;
    }

    const duration = this.data.duration;

    const { typesConfig, scoresConfig, actualTotal } = this.buildExamConfig(enabledTypes);
    if (actualTotal <= 0) {
      wx.showToast({ title: '题目不足，无法组卷', icon: 'none' });
      return;
    }

    const mismatch = actualTotal !== this.data.total;
    if (mismatch) {
      const ok = await this.confirmModal(
        '题目数量不一致',
        `当前题型题数合计为 ${actualTotal} 题，与目标 ${this.data.total} 题不一致，将按 ${actualTotal} 题组卷，是否继续？`
      );
      if (!ok) return;
    }

    this.setData({ creating: true });
    wx.showLoading({ title: '创建考试...' });
    try {
      const res: any = await api.createExam({
        subject: this.data.subject,
        duration,
        types: typesConfig,
        scores: scoresConfig
      });

      const examId = Number(res.exam_id);
      if (!isFinite(examId) || examId <= 0) {
        throw new Error('创建考试失败');
      }

      wx.hideLoading();
      this.setData({ creating: false });

      wx.navigateTo({ url: `/pages/exam-run/exam-run?exam_id=${examId}` });
    } catch (err: any) {
      console.error('创建考试失败:', err);
      wx.hideLoading();
      this.setData({ creating: false });
      wx.showToast({ title: (err && err.message) || '创建失败', icon: 'none' });
    }
  },

  buildExamConfig(enabledTypes: TypeItem[]): {
    typesConfig: Record<string, number>;
    scoresConfig: Record<string, number>;
    actualTotal: number;
  } {
    const typesConfig: Record<string, number> = {};
    const scoresConfig: Record<string, number> = {};

    enabledTypes.forEach((t) => {
      const c = Math.max(0, Math.min(t.available, Math.floor(Number(t.count) || 0)));
      const s = Math.max(0, Math.min(1000, Number(t.score) || 0));
      if (c > 0) {
        typesConfig[t.name] = c;
        scoresConfig[t.name] = s;
      }
    });

    const assignedTotal = Object.values(typesConfig).reduce((sum, v) => sum + (Number(v) || 0), 0);
    return { typesConfig, scoresConfig, actualTotal: assignedTotal };
  },

  distributeCounts(total: number, enabledTypes: TypeItem[]): Record<string, number> {
    const cfg: Record<string, number> = {};
    const n = enabledTypes.length;
    if (n <= 0) return cfg;

    const target = Math.max(1, Math.min(500, Math.floor(Number(total) || 0)));
    const base = Math.floor(target / n);
    let rem = target % n;

    enabledTypes.forEach((t) => {
      const want = base + (rem > 0 ? 1 : 0);
      if (rem > 0) rem -= 1;
      cfg[t.name] = Math.min(want, t.available);
    });

    // 尝试补齐剩余
    let assignedTotal = Object.values(cfg).reduce((s, v) => s + (Number(v) || 0), 0);
    let remaining = target - assignedTotal;
    let safety = 5000;
    while (remaining > 0 && safety-- > 0) {
      let progressed = false;
      for (const t of enabledTypes) {
        if (remaining <= 0) break;
        const cap = t.available - (cfg[t.name] || 0);
        if (cap > 0) {
          cfg[t.name] = (cfg[t.name] || 0) + 1;
          remaining -= 1;
          progressed = true;
        }
      }
      if (!progressed) break;
    }

    assignedTotal = Object.values(cfg).reduce((s, v) => s + (Number(v) || 0), 0);
    if (assignedTotal <= 0) {
      enabledTypes.forEach((t) => {
        cfg[t.name] = Math.min(1, t.available);
      });
    }

    return cfg;
  },

  confirmModal(title: string, content: string): Promise<boolean> {
    return new Promise((resolve) => {
      wx.showModal({
        title,
        content,
        confirmText: '继续',
        cancelText: '取消',
        success: (res) => resolve(!!res.confirm),
        fail: () => resolve(false)
      });
    });
  }
});
