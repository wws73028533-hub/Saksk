/**
 * theme.ts - 主题管理工具
 *
 * 支持三种模式：
 * - 'light': 浅色模式
 * - 'dark': 深色模式
 * - 'system': 跟随系统设置
 */

const THEME_STORAGE_KEY = 'app_theme_v1';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeInfo {
  mode: ThemeMode;        // 用户选择的模式
  isDark: boolean;        // 当前是否为深色
  systemIsDark: boolean;  // 系统是否为深色
}

// 全局主题状态
let currentThemeInfo: ThemeInfo = {
  mode: 'system',
  isDark: false,
  systemIsDark: false
};

// 主题变更回调列表
const themeChangeCallbacks: Array<(isDark: boolean) => void> = [];

/**
 * 获取系统主题偏好
 */
function getSystemTheme(): boolean {
  try {
    const systemInfo = wx.getAppBaseInfo();
    return systemInfo.theme === 'dark';
  } catch (e) {
    // 兼容旧版本API
    try {
      const systemInfo = wx.getSystemInfoSync();
      return (systemInfo as any).theme === 'dark';
    } catch (e2) {
      return false;
    }
  }
}

/**
 * 从本地存储获取保存的主题模式
 */
function getStoredThemeMode(): ThemeMode {
  try {
    const stored = wx.getStorageSync(THEME_STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
  } catch (e) {
    console.warn('读取主题设置失败:', e);
  }
  return 'system'; // 默认跟随系统
}

/**
 * 保存主题模式到本地存储
 */
function saveThemeMode(mode: ThemeMode): void {
  try {
    wx.setStorageSync(THEME_STORAGE_KEY, mode);
  } catch (e) {
    console.warn('保存主题设置失败:', e);
  }
}

/**
 * 计算当前是否应该使用深色模式
 */
function calculateIsDark(mode: ThemeMode, systemIsDark: boolean): boolean {
  if (mode === 'system') {
    return systemIsDark;
  }
  return mode === 'dark';
}

function getThemeClass(mode: ThemeMode): string {
  if (mode === 'dark') return 'theme-dark';
  if (mode === 'light') return 'theme-light';
  return '';
}

function applyTabBarStyle(isDark: boolean): void {
  if (typeof wx.setTabBarStyle !== 'function') return;
  try {
    wx.setTabBarStyle({
      color: isDark ? '#8E8E93' : '#7A7E83',
      selectedColor: '#007AFF',
      backgroundColor: isDark ? '#1C1C1E' : '#FFFFFF',
      borderStyle: isDark ? 'white' : 'black',
      fail: () => {}
    });
  } catch (e) {
    // 忽略 setTabBarStyle 异常
  }
}

/**
 * 通知所有页面主题变更
 */
function notifyThemeChange(): void {
  const isDark = currentThemeInfo.isDark;
  const mode = currentThemeInfo.mode;
  const themeClass = getThemeClass(mode);

  // 调用所有注册的回调
  themeChangeCallbacks.forEach(callback => {
    try {
      callback(isDark);
    } catch (e) {
      console.error('主题变更回调执行失败:', e);
    }
  });

  // 获取所有页面并尝试更新
  const pages = getCurrentPages();
  pages.forEach(page => {
    if (page && typeof (page as any).onThemeChange === 'function') {
      try {
        (page as any).onThemeChange(isDark);
      } catch (e) {
        console.error('页面主题变更处理失败:', e);
      }
    }
    // 更新页面主题数据
    if (page && page.setData) {
      try {
        page.setData({ isDarkMode: isDark, themeMode: mode, themeClass });
      } catch (e) {
        // 忽略setData失败
      }
    }
  });

  applyTabBarStyle(isDark);
}

/**
 * 主题管理器
 */
export const themeManager = {
  /**
   * 初始化主题系统（应在 app.ts onLaunch 中调用）
   */
  init(): ThemeInfo {
    const systemIsDark = getSystemTheme();
    const mode = getStoredThemeMode();
    const isDark = calculateIsDark(mode, systemIsDark);

    currentThemeInfo = {
      mode,
      isDark,
      systemIsDark
    };

    // 监听系统主题变化
    wx.onThemeChange((result) => {
      const newSystemIsDark = result.theme === 'dark';
      currentThemeInfo.systemIsDark = newSystemIsDark;

      // 如果是跟随系统模式，需要更新当前主题
      if (currentThemeInfo.mode === 'system') {
        const newIsDark = calculateIsDark('system', newSystemIsDark);
        if (newIsDark !== currentThemeInfo.isDark) {
          currentThemeInfo.isDark = newIsDark;
          notifyThemeChange();
        }
      }
    });

    return currentThemeInfo;
  },

  /**
   * 获取当前主题信息
   */
  getThemeInfo(): ThemeInfo {
    return { ...currentThemeInfo };
  },

  /**
   * 获取当前是否为深色模式
   */
  isDarkMode(): boolean {
    return currentThemeInfo.isDark;
  },

  /**
   * 获取当前主题模式设置
   */
  getMode(): ThemeMode {
    return currentThemeInfo.mode;
  },

  /**
   * 设置主题模式
   */
  setMode(mode: ThemeMode): void {
    if (mode !== 'light' && mode !== 'dark' && mode !== 'system') {
      console.warn('无效的主题模式:', mode);
      return;
    }

    const prevMode = currentThemeInfo.mode;
    const prevIsDark = currentThemeInfo.isDark;

    currentThemeInfo.mode = mode;
    saveThemeMode(mode);

    const newIsDark = calculateIsDark(mode, currentThemeInfo.systemIsDark);
    currentThemeInfo.isDark = newIsDark;

    if (prevMode !== mode || prevIsDark !== newIsDark) {
      notifyThemeChange();
    }
  },

  /**
   * 切换主题（在浅色和深色之间切换）
   * 返回切换后的状态
   */
  toggle(): boolean {
    const newMode: ThemeMode = currentThemeInfo.isDark ? 'light' : 'dark';
    this.setMode(newMode);
    return currentThemeInfo.isDark;
  },

  /**
   * 在三种模式之间循环切换
   * light -> dark -> system -> light
   */
  cycleMode(): ThemeMode {
    const modeOrder: ThemeMode[] = ['light', 'dark', 'system'];
    const currentIndex = modeOrder.indexOf(currentThemeInfo.mode);
    const nextIndex = (currentIndex + 1) % modeOrder.length;
    const newMode = modeOrder[nextIndex];
    this.setMode(newMode);
    return newMode;
  },

  /**
   * 注册主题变更回调
   */
  onThemeChange(callback: (isDark: boolean) => void): () => void {
    themeChangeCallbacks.push(callback);
    // 返回取消注册的函数
    return () => {
      const index = themeChangeCallbacks.indexOf(callback);
      if (index > -1) {
        themeChangeCallbacks.splice(index, 1);
      }
    };
  },

  /**
   * 获取用于页面的主题相关数据
   * 可在页面 onLoad/onShow 中调用并 setData
   */
  getPageData(): { isDarkMode: boolean; themeMode: ThemeMode; themeClass: string } {
    return {
      isDarkMode: currentThemeInfo.isDark,
      themeMode: currentThemeInfo.mode,
      themeClass: getThemeClass(currentThemeInfo.mode)
    };
  },

  /**
   * 应用主题到系统 UI（如 tabBar）
   */
  applySystemUI(): void {
    applyTabBarStyle(currentThemeInfo.isDark);
  },

  /**
   * 获取主题相关的导航栏配置
   */
  getNavBarStyle(): { background: string; color: 'black' | 'white' } {
    return {
      background: currentThemeInfo.isDark ? '#1C1C1E' : '#FFFFFF',
      color: currentThemeInfo.isDark ? 'white' : 'black'
    };
  },

  /**
   * 获取主题图标（用于UI显示）
   */
  getThemeIcon(): string {
    switch (currentThemeInfo.mode) {
      case 'light':
        return '☀';
      case 'dark':
        return '🌙';
      case 'system':
        return '⚙';
      default:
        return currentThemeInfo.isDark ? '☀' : '🌙';
    }
  },

  /**
   * 获取主题模式的显示名称
   */
  getModeName(): string {
    switch (currentThemeInfo.mode) {
      case 'light':
        return '浅色';
      case 'dark':
        return '深色';
      case 'system':
        return '跟随系统';
      default:
        return '未知';
    }
  }
};

export default themeManager;
