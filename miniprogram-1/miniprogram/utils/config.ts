// 配置文件
// 可以根据环境变量或构建配置来切换不同的API地址

// 开发环境
// 微信小程序需要使用本机IP地址而非localhost
const DEV_API_BASE_URL = 'http://192.168.31.74:5000/api';

// 生产环境（需要替换为实际域名）
const PROD_API_BASE_URL = 'https://your-actual-domain.com/api';

// 根据环境选择API地址
// 在小程序中可以通过 __wxConfig 或 process.env 来判断环境
// 这里先使用开发环境，实际部署时需要修改
export const API_BASE_URL = DEV_API_BASE_URL;

// 导出配置
export const config = {
  apiBaseUrl: API_BASE_URL
};

