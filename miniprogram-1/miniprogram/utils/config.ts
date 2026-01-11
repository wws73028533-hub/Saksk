// 配置文件
// 可以根据环境变量或构建配置来切换不同的API地址

// 生产环境（需要替换为实际域名）
const PROD_API_BASE_URL = 'https://your-actual-domain.com/api';

// 后端服务端口
const DEV_PORT = 5000;

/**
 * 自动获取开发环境 API 地址
 * 在微信开发者工具中，通过获取本机 IP 来构建 API 地址
 */
function getDevApiBaseUrl(): string {
  // 默认使用 localhost（适用于大多数开发场景）
  let host = '127.0.0.1';

  try {
    // 尝试获取系统信息中的网络信息
    const systemInfo = wx.getSystemInfoSync();

    // 在开发者工具中，可以通过 wx.getLocalIPAddress 获取本机 IP（需要真机调试）
    // 这里使用备用方案：从 URL 参数或本地存储读取
    const savedHost = wx.getStorageSync('dev_api_host');
    if (savedHost) {
      host = savedHost;
    }
  } catch (e) {
    console.warn('获取系统信息失败，使用默认地址', e);
  }

  return `http://${host}:${DEV_PORT}/api`;
}

/**
 * 检测当前是否为开发环境
 */
function isDev(): boolean {
  try {
    const accountInfo = wx.getAccountInfoSync();
    // miniProgram.envVersion: 'develop' | 'trial' | 'release'
    return accountInfo.miniProgram.envVersion === 'develop';
  } catch (e) {
    // 获取失败时默认为开发环境
    return true;
  }
}

// 根据环境选择 API 地址
export const API_BASE_URL = isDev() ? getDevApiBaseUrl() : PROD_API_BASE_URL;

// 导出配置
export const config = {
  apiBaseUrl: API_BASE_URL,
  devPort: DEV_PORT,
  isDev: isDev(),

  /**
   * 动态设置开发环境的 API Host（保存到本地存储）
   * 使用方法：在小程序控制台执行 config.setDevHost('192.168.1.100')
   */
  setDevHost(host: string): void {
    wx.setStorageSync('dev_api_host', host);
    console.log(`已设置开发环境 API 地址为: http://${host}:${DEV_PORT}/api`);
    console.log('请重启小程序以生效');
  },

  /**
   * 获取当前配置的 API 地址
   */
  getApiUrl(): string {
    return isDev() ? getDevApiBaseUrl() : PROD_API_BASE_URL;
  }
};

