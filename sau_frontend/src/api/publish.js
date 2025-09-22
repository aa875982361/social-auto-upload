import { http } from '@/utils/request'

// 发布相关API
export const publishApi = {
  // 发布视频到社交媒体平台
  publishVideo: (publishData) => {
    return http.post('/api/postVideo', publishData)
  },
  
  // 获取发布历史记录
  getPublishHistory: (params) => {
    return http.get('/api/publishHistory', { params })
  },
  
  // 获取发布状态
  getPublishStatus: (taskId) => {
    return http.get(`/api/publishStatus/${taskId}`)
  },
  
  // 取消发布任务
  cancelPublish: (taskId) => {
    return http.post(`/api/cancelPublish/${taskId}`)
  },
  
  // 重新发布
  republish: (taskId) => {
    return http.post(`/api/republish/${taskId}`)
  },
  
  // 删除发布历史记录
  deletePublishHistory: (historyId) => {
    return http.delete(`/api/deletePublishHistory/${historyId}`)
  }
}
