import { http } from '@/utils/request'

// 账号管理相关API
export const accountApi = {
  // 获取有效账号列表
  getValidAccounts(searchKeyword = '') {
    const params = searchKeyword ? { search: searchKeyword } : {}
    return http.get('/api/getValidAccounts', { params })
  },
  
  // 添加账号
  addAccount(data) {
    return http.post('/api/account', data)
  },
  
  // 更新账号
  updateAccount(data) {
    return http.post('/api/updateUserinfo', data)
  },
  
  // 删除账号
  deleteAccount(id) {
    return http.get(`/api/deleteAccount?id=${id}`)
  }
}