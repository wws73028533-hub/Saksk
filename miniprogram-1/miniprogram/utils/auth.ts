import { api } from './api';

// 微信登录
export function wechatLogin(): Promise<'success' | 'need_bind'> {
  return new Promise((resolve, reject) => {
    wx.login({
      success: (res) => {
        if (res.code) {
          // 直接使用 code 登录，不强制获取用户信息
          // 首次未绑定时：由后端返回 need_bind，让用户选择创建/绑定
          console.log('开始调用登录API，code:', res.code);
              api.wechatLogin(res.code, undefined, false)
                .then((data: any) => {
              console.log('登录API返回数据:', data);
              if (data && data.need_bind && data.wechat_temp_token) {
                wx.setStorageSync('wechatTempToken', data.wechat_temp_token);
                resolve('need_bind');
                return;
              }
              if (!data || !data.token) {
                console.error('登录返回数据无效:', data);
                reject(new Error('登录失败：服务器返回数据异常'));
                return;
              }
              wx.setStorageSync('token', data.token);
              if (data.user_info) wx.setStorageSync('userInfo', data.user_info);
              console.log('登录成功，token已保存');
              resolve('success');
                })
            .catch((err) => {
              console.error('登录API调用失败:', err);
              reject(err);
          });
        } else {
          console.error('获取微信登录code失败:', res);
          reject(new Error('获取微信登录code失败'));
        }
      },
      fail: (err) => {
        console.error('wx.login调用失败:', err);
        reject(new Error('微信登录失败，请稍后重试'));
      }
    });
  });
}

// 检查登录状态
export function checkLogin(): boolean {
  const token = wx.getStorageSync('token');
  return !!token;
}

// 退出登录
export function logout(): void {
  wx.removeStorageSync('token');
  wx.removeStorageSync('userInfo');
}
