// my-banks.ts - 我的题库页
import { api } from '../../utils/api';
import { checkLogin } from '../../utils/auth';

interface Bank {
  id: number;
  name: string;
  description?: string;
  question_count: number;
  is_public?: boolean;
  category_name?: string;
  permission?: string;
  access_type?: string;
  owner_nickname?: string;
}

Page({
  data: {
    activeTab: 'my' as 'my' | 'shared',
    myBanks: [] as Bank[],
    sharedBanks: [] as Bank[],
    loading: false,
    showJoinModal: false,
    shareCode: ''
  },

  onShow() {
    if (!checkLogin()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    this.loadBanks();
  },

  async loadBanks() {
    if (this.data.loading) return;
    this.setData({ loading: true });

    try {
      if (this.data.activeTab === 'my') {
        const res: any = await api.getMyBanks();
        const banks = res.banks || [];
        this.setData({ myBanks: banks });
      } else {
        const res: any = await api.getSharedBanks();
        const banks = res.banks || [];
        this.setData({ sharedBanks: banks });
      }
    } catch (err: any) {
      console.error('加载题库失败:', err);
      wx.showToast({ title: err.message || '加载失败', icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  onTabChange(e: any) {
    const tab = e.currentTarget.dataset.tab;
    if (tab === this.data.activeTab) return;
    this.setData({ activeTab: tab }, () => {
      this.loadBanks();
    });
  },

  onBankTap(e: any) {
    const bankId = e.currentTarget.dataset.id;
    if (!bankId) return;
    wx.navigateTo({
      url: `/pages/bank-detail/bank-detail?id=${bankId}`
    });
  },

  onJoinTap() {
    this.setData({ showJoinModal: true, shareCode: '' });
  },

  onCloseJoinModal() {
    this.setData({ showJoinModal: false, shareCode: '' });
  },

  onShareCodeInput(e: any) {
    this.setData({ shareCode: e.detail.value || '' });
  },

  async onConfirmJoin() {
    const code = this.data.shareCode.trim().toUpperCase();
    if (!code) {
      wx.showToast({ title: '请输入分享码', icon: 'none' });
      return;
    }

    try {
      wx.showLoading({ title: '加入中...' });
      const res: any = await api.joinBankByCode(code);
      wx.hideLoading();
      wx.showToast({ title: `已加入「${res.bank_name}」`, icon: 'success' });
      this.setData({ showJoinModal: false, shareCode: '', activeTab: 'shared' });
      this.loadBanks();
    } catch (err: any) {
      wx.hideLoading();
      wx.showToast({ title: err.message || '加入失败', icon: 'none' });
    }
  },

  onPullDownRefresh() {
    this.loadBanks().finally(() => wx.stopPullDownRefresh());
  }
});
