// logs.ts
// const util = require('../../utils/util.js')
import { formatTime } from '../../utils/util'

Page({
  data: {
    logs: [] as Array<{ date: string; timeStamp: string }>
  },

  onLoad() {
    this.loadLogs();
  },

  onShow() {
    this.loadLogs();
  },

  loadLogs() {
    const logs = (wx.getStorageSync('logs') || []).map((log: string) => {
      return {
        date: formatTime(new Date(log)),
        timeStamp: log
      };
    });
    this.setData({ logs });
  }
});
