<template>
  <div class="publish-history">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>发布历史</h2>
      <p class="page-description">查看所有账号的发布记录和状态</p>
    </div>

    <!-- 筛选和搜索区域 -->
    <div class="filter-section">
      <div class="filter-row">
        <div class="filter-item">
          <label>平台筛选：</label>
          <el-select v-model="filters.platformType" placeholder="选择平台" clearable>
            <el-option label="全部平台" value="" />
            <el-option label="小红书" :value="1" />
            <el-option label="视频号" :value="2" />
            <el-option label="抖音" :value="3" />
            <el-option label="快手" :value="4" />
          </el-select>
        </div>
        
        <div class="filter-item">
          <label>状态筛选：</label>
          <el-select v-model="filters.status" placeholder="选择状态" clearable>
            <el-option label="全部状态" value="" />
            <el-option label="发布中" value="pending" />
            <el-option label="发布成功" value="success" />
            <el-option label="发布失败" value="failed" />
          </el-select>
        </div>
        
        <div class="filter-item">
          <label>账号搜索：</label>
          <el-input
            v-model="filters.accountName"
            placeholder="输入账号名称"
            clearable
            style="width: 200px"
          />
        </div>
        
        <div class="filter-actions">
          <el-button type="primary" @click="loadHistory" :loading="loading">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilters">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </div>
      </div>
    </div>

    <!-- 发布历史列表 -->
    <div class="history-content">
      <el-table
        :data="historyList"
        v-loading="loading"
        stripe
        style="width: 100%"
        :default-sort="{ prop: 'created_time', order: 'descending' }"
      >
        <el-table-column prop="id" label="ID" width="80" />
        
        <el-table-column prop="platform_name" label="平台" width="100">
          <template #default="{ row }">
            <el-tag :type="getPlatformTagType(row.platform_type)">
              {{ row.platform_name }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="account_name" label="账号" width="150" />
        
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        
        <el-table-column prop="tags" label="话题" width="150">
          <template #default="{ row }">
            <div v-if="row.tags && row.tags.length > 0" class="tags-container">
              <el-tag
                v-for="(tag, index) in row.tags.slice(0, 2)"
                :key="index"
                size="small"
                class="tag-item"
              >
                #{{ tag }}
              </el-tag>
              <span v-if="row.tags.length > 2" class="more-tags">
                +{{ row.tags.length - 2 }}
              </span>
            </div>
            <span v-else class="no-tags">无话题</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="file_list" label="文件" width="120">
          <template #default="{ row }">
            <span>{{ row.file_list ? row.file_list.length : 0 }} 个文件</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="enable_timer" label="定时发布" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.enable_timer" type="warning" size="small">
              定时
            </el-tag>
            <span v-else class="no-timer">立即</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_time" label="创建时间" width="160" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.created_time) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="publish_time" label="发布时间" width="160">
          <template #default="{ row }">
            {{ row.publish_time ? formatDateTime(row.publish_time) : '-' }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="viewDetails(row)"
            >
              详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="deleteRecord(row)"
              :disabled="row.status === 'pending'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="发布详情"
      width="800px"
      class="detail-dialog"
    >
      <div v-if="selectedRecord" class="detail-content">
        <div class="detail-section">
          <h4>基本信息</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>任务ID：</label>
              <span>{{ selectedRecord.task_id }}</span>
            </div>
            <div class="detail-item">
              <label>平台：</label>
              <el-tag :type="getPlatformTagType(selectedRecord.platform_type)">
                {{ selectedRecord.platform_name }}
              </el-tag>
            </div>
            <div class="detail-item">
              <label>账号：</label>
              <span>{{ selectedRecord.account_name }}</span>
            </div>
            <div class="detail-item">
              <label>状态：</label>
              <el-tag :type="getStatusTagType(selectedRecord.status)">
                {{ getStatusText(selectedRecord.status) }}
              </el-tag>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>内容信息</h4>
          <div class="detail-item">
            <label>标题：</label>
            <p class="title-text">{{ selectedRecord.title }}</p>
          </div>
          <div class="detail-item" v-if="selectedRecord.tags && selectedRecord.tags.length > 0">
            <label>话题：</label>
            <div class="tags-container">
              <el-tag
                v-for="(tag, index) in selectedRecord.tags"
                :key="index"
                size="small"
                class="tag-item"
              >
                #{{ tag }}
              </el-tag>
            </div>
          </div>
          <div class="detail-item">
            <label>文件列表：</label>
            <div class="file-list">
              <div
                v-for="(file, index) in selectedRecord.file_list"
                :key="index"
                class="file-item"
              >
                {{ file }}
              </div>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="selectedRecord.enable_timer">
          <h4>定时发布设置</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>每天发布数量：</label>
              <span>{{ selectedRecord.videos_per_day }} 个</span>
            </div>
            <div class="detail-item">
              <label>发布时间：</label>
              <span>{{ selectedRecord.daily_times ? selectedRecord.daily_times.join(', ') : '-' }}</span>
            </div>
            <div class="detail-item">
              <label>开始天数：</label>
              <span>{{ selectedRecord.start_days === 0 ? '明天' : '后天' }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>时间信息</h4>
          <div class="detail-grid">
            <div class="detail-item">
              <label>创建时间：</label>
              <span>{{ formatDateTime(selectedRecord.created_time) }}</span>
            </div>
            <div class="detail-item">
              <label>发布时间：</label>
              <span>{{ selectedRecord.publish_time ? formatDateTime(selectedRecord.publish_time) : '-' }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="selectedRecord.error_message">
          <h4>错误信息</h4>
          <div class="error-message">
            {{ selectedRecord.error_message }}
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import { publishApi } from '@/api/publish'

// 响应式数据
const loading = ref(false)
const historyList = ref([])
const detailDialogVisible = ref(false)
const selectedRecord = ref(null)

// 筛选条件
const filters = reactive({
  platformType: '',
  status: '',
  accountName: ''
})

// 分页信息
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 获取平台标签类型
const getPlatformTagType = (platformType) => {
  const typeMap = {
    1: 'success',  // 小红书 - 绿色
    2: 'primary',  // 视频号 - 蓝色
    3: 'danger',   // 抖音 - 红色
    4: 'warning'   // 快手 - 橙色
  }
  return typeMap[platformType] || 'info'
}

// 获取状态标签类型
const getStatusTagType = (status) => {
  const typeMap = {
    'pending': 'warning',
    'success': 'success',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    'pending': '发布中',
    'success': '成功',
    'failed': '失败'
  }
  return textMap[status] || status
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 加载发布历史
const loadHistory = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      pageSize: pagination.pageSize,
      ...filters
    }
    
    const response = await publishApi.getPublishHistory(params)
    if (response.code === 200) {
      historyList.value = response.data.list
      pagination.total = response.data.total
    } else {
      ElMessage.error(response.msg || '获取发布历史失败')
    }
  } catch (error) {
    console.error('获取发布历史失败:', error)
    ElMessage.error('获取发布历史失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const resetFilters = () => {
  filters.platformType = ''
  filters.status = ''
  filters.accountName = ''
  pagination.page = 1
  loadHistory()
}

// 查看详情
const viewDetails = (record) => {
  selectedRecord.value = record
  detailDialogVisible.value = true
}

// 删除记录
const deleteRecord = async (record) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除这条发布记录吗？\n标题：${record.title}\n账号：${record.account_name}`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await publishApi.deletePublishHistory(record.id)
    if (response.code === 200) {
      ElMessage.success('删除成功')
      loadHistory()
    } else {
      ElMessage.error(response.msg || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除记录失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 分页大小改变
const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.page = 1
  loadHistory()
}

// 当前页改变
const handleCurrentChange = (page) => {
  pagination.page = page
  loadHistory()
}

// 页面挂载时加载数据
onMounted(() => {
  loadHistory()
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.publish-history {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: 100vh;

  .page-header {
    background-color: #fff;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

    h2 {
      margin: 0 0 8px 0;
      color: #303133;
      font-size: 24px;
      font-weight: 600;
    }

    .page-description {
      margin: 0;
      color: #909399;
      font-size: 14px;
    }
  }

  .filter-section {
    background-color: #fff;
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

    .filter-row {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;

      .filter-item {
        display: flex;
        align-items: center;
        gap: 8px;

        label {
          font-size: 14px;
          color: #606266;
          white-space: nowrap;
        }
      }

      .filter-actions {
        display: flex;
        gap: 10px;
        margin-left: auto;
      }
    }
  }

  .history-content {
    background-color: #fff;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);

    .tags-container {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      align-items: center;

      .tag-item {
        margin: 0;
      }

      .more-tags {
        font-size: 12px;
        color: #909399;
      }
    }

    .no-tags {
      color: #c0c4cc;
      font-size: 12px;
    }

    .no-timer {
      color: #909399;
      font-size: 12px;
    }

    .pagination-container {
      margin-top: 20px;
      display: flex;
      justify-content: center;
    }
  }

  .detail-dialog {
    .detail-content {
      .detail-section {
        margin-bottom: 24px;

        h4 {
          margin: 0 0 16px 0;
          color: #303133;
          font-size: 16px;
          font-weight: 600;
          border-bottom: 1px solid #ebeef5;
          padding-bottom: 8px;
        }

        .detail-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 16px;
        }

        .detail-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;

          label {
            font-weight: 500;
            color: #606266;
            min-width: 100px;
            flex-shrink: 0;
          }

          .title-text {
            margin: 0;
            color: #303133;
            line-height: 1.5;
          }

          .tags-container {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;

            .tag-item {
              margin: 0;
            }
          }

          .file-list {
            .file-item {
              padding: 4px 8px;
              background-color: #f5f7fa;
              border-radius: 4px;
              margin-bottom: 4px;
              font-size: 12px;
              color: #606266;
              word-break: break-all;
            }
          }
        }

        .error-message {
          padding: 12px;
          background-color: #fef0f0;
          border: 1px solid #fbc4c4;
          border-radius: 4px;
          color: #f56c6c;
          font-size: 14px;
          line-height: 1.5;
        }
      }
    }
  }
}

// 移动端适配
@media (max-width: $breakpoint-sm) {
  .publish-history {
    padding: 12px;

    .page-header {
      padding: 16px;
      margin-bottom: 12px;

      h2 {
        font-size: 20px;
      }
    }

    .filter-section {
      padding: 16px;
      margin-bottom: 12px;

      .filter-row {
        flex-direction: column;
        align-items: stretch;
        gap: 12px;

        .filter-item {
          flex-direction: column;
          align-items: stretch;
          gap: 4px;

          label {
            font-size: 12px;
          }
        }

        .filter-actions {
          margin-left: 0;
          justify-content: center;
        }
      }
    }

    .history-content {
      padding: 12px;
      overflow-x: auto;

      .pagination-container {
        margin-top: 16px;
      }
    }

    .detail-dialog {
      :deep(.el-dialog) {
        width: 95% !important;
        margin: 5vh auto !important;
      }

      .detail-content {
        .detail-section {
          margin-bottom: 20px;

          .detail-grid {
            grid-template-columns: 1fr;
            gap: 12px;
          }

          .detail-item {
            flex-direction: column;
            align-items: stretch;
            gap: 4px;

            label {
              min-width: auto;
              font-size: 12px;
            }
          }
        }
      }
    }
  }
}
</style>
