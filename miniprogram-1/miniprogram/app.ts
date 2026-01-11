// app.ts
import { themeManager } from './utils/theme';

function patchPageThemeOnce() {
  const g = globalThis as any;
  if (g.__appThemePagePatched) return;
  g.__appThemePagePatched = true;

  const originalPage = g.Page;
  if (typeof originalPage !== 'function') return;

  g.Page = (options: any) => {
    const originalOnLoad = options.onLoad;
    const originalOnShow = options.onShow;

    options.onLoad = function (...args: any[]) {
      try {
        this.setData(themeManager.getPageData());
      } catch (e) {
        // 忽略 setData 失败
      }
      return typeof originalOnLoad === 'function' ? originalOnLoad.apply(this, args) : undefined;
    };

    options.onShow = function (...args: any[]) {
      try {
        themeManager.applySystemUI();
      } catch (e) {
        // 忽略 applySystemUI 失败
      }
      try {
        this.setData(themeManager.getPageData());
      } catch (e) {
        // 忽略 setData 失败
      }
      return typeof originalOnShow === 'function' ? originalOnShow.apply(this, args) : undefined;
    };

    return originalPage(options);
  };
}

patchPageThemeOnce();

App<IAppOption>({
  globalData: {
    isDarkMode: false,
    themeMode: 'system' as 'light' | 'dark' | 'system'
  },
  onLaunch() {
    // 初始化主题系统
    const themeInfo = themeManager.init();
    this.globalData.isDarkMode = themeInfo.isDark;
    this.globalData.themeMode = themeInfo.mode;

    // 监听主题变化，更新全局数据
    themeManager.onThemeChange((isDark) => {
      this.globalData.isDarkMode = isDark;
      this.globalData.themeMode = themeManager.getMode();
    });

    // 展示本地存储能力
    const logs = wx.getStorageSync('logs') || [];
    logs.unshift(Date.now());
    wx.setStorageSync('logs', logs);

    // 登录
    wx.login({
      success: res => {
        console.log(res.code);
        // 发送 res.code 到后台换取 openId, sessionKey, unionId
      },
    });
  },
  onShow() {
    themeManager.applySystemUI();
  },
});
