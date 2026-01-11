// bank-share.ts - 个人题库分享设置页面
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

interface ShareItem {
  id: number;
  share_code?: string;
  share_token?: string;
  permission: 'read' | 'copy';
  expires_at?: string;
  expires_at_display?: string;
  current_uses: number;
  max_uses?: number;
  is_active: boolean;
}

Page({
  data: {
    bankId: 0,
    bankInfo: {
      name: '',
      question_count: 0
    },
    shares: [] as ShareItem[],
    newShare: {
      permission: 'read' as 'read' | 'copy',
      expiresIn: 0  // 0表示永久，7、30表示天数
    },
    loading: false,
    showCodeModal: false,
    generatedCode: ''
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
    wx.showShareMenu({ withShareTicket: true });
    this.loadData();
  },

  async loadData() {
    this.setData({ loading: true });
    try {
      const results: any[] = await Promise.all([
        api.getBankDetail(this.data.bankId),
        api.getBankShares(this.data.bankId)
      ]);

      const detailRes = results[0];
      const sharesRes = results[1];
      const bankData = detailRes.data || detailRes || {};
      const sharesData = sharesRes.data || sharesRes || {};
      const shares = (sharesData.shares || []).map((s: any) => {
        return Object.assign({}, s, {
          expires_at_display: s.expires_at ? this.formatDate(s.expires_at) : ''
        });
      });

      this.setData({
        bankInfo: {
          name: bankData.name || '未知题库',
          question_count: bankData.question_count || 0
        },
        shares,
        loading: false
      });
    } catch (err: any) {
      console.error('加载数据失败:', err);
      if (err.message?.includes('401') || err.message?.includes('登录')) {
        wx.reLaunch({ url: '/pages/login/login' });
        return;
      }
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${month}-${day}`;
    } catch {
      return '';
    }
  },

  onPermissionTap(e: any) {
    const permission = e.currentTarget.dataset.permission as 'read' | 'copy';
    this.setData({ 'newShare.permission': permission });
  },

  onExpiresTap(e: any) {
    const expiresIn = Number(e.currentTarget.dataset.expires);
    this.setData({ 'newShare.expiresIn': expiresIn });
  },

  async onCreateShare(e: any) {
    const type = e.currentTarget.dataset.type; // 'code' or 'link'
    const { bankId, newShare } = this.data;

    wx.showLoading({ title: '创建中...' });
    try {
      const res: any = await api.createBankShare(bankId, {
        type: type,
        permission: newShare.permission,
        expires_in: newShare.expiresIn || null
      });

      wx.hideLoading();

      const shareData = res.data || res || {};
      if (shareData.share_code) {
        this.setData({
          showCodeModal: true,
          generatedCode: shareData.share_code
        });
      }

      // 刷新列表
      this.loadData();
    } catch (err: any) {
      wx.hideLoading();
      wx.showToast({ title: err.message || '创建失败', icon: 'none' });
    }
  },

  onCloseCodeModal() {
    this.setData({ showCodeModal: false });
  },

  onCopyGeneratedCode() {
    wx.setClipboardData({
      data: this.data.generatedCode,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
        this.setData({ showCodeModal: false });
      }
    });
  },

  onCopyCode(e: any) {
    const code = e.currentTarget.dataset.code;
    if (!code) {
      wx.showToast({ title: '暂无分享码', icon: 'none' });
      return;
    }
    wx.setClipboardData({
      data: code,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' });
      }
    });
  },

  onDeleteShare(e: any) {
    const shareId = e.currentTarget.dataset.id;
    wx.showModal({
      title: '确认撤销',
      content: '撤销后，使用此分享码加入的用户将无法继续访问',
      confirmColor: '#FF3B30',
      success: async (res) => {
        if (!res.confirm) return;

        wx.showLoading({ title: '撤销中...' });
        try {
          await api.deleteBankShare(this.data.bankId, shareId);
          wx.hideLoading();
          wx.showToast({ title: '已撤销', icon: 'success' });
          this.loadData();
        } catch (err: any) {
          wx.hideLoading();
          wx.showToast({ title: err.message || '撤销失败', icon: 'none' });
        }
      }
    });
  },

  onShareAppMessage() {
    const { bankId, bankInfo } = this.data;
    return {
      title: `邀请你加入题库：${bankInfo.name}`,
      path: `/pages/bank-detail/bank-detail?id=${bankId}`
    };
  }
});
