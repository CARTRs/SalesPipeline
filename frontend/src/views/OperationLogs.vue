<template>
  <div class="page-head">
    <h2>操作日志</h2>
  </div>

  <!-- 筛选栏 -->
  <el-card shadow="never" class="filter-card">
    <el-form :model="filters" inline>
      <el-form-item label="操作类型">
        <el-select v-model="filters.action" placeholder="全部" clearable style="width:160px">
          <el-option label="导入" value="import" />
          <el-option label="导出" value="export" />
          <el-option label="创建商机" value="create_opportunity" />
          <el-option label="编辑商机" value="update_opportunity" />
          <el-option label="删除商机" value="delete_opportunity" />
          <el-option label="提交进度" value="create_progress" />
          <el-option label="AI分析" value="ai_analyze" />
          <el-option label="登录" value="login" />
        </el-select>
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="filters.status" placeholder="全部" clearable style="width:120px">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="fail" />
          <el-option label="部分成功" value="partial" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button @click="loadLogs" type="primary">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <!-- 日志表格 -->
  <el-card shadow="never">
    <el-table :data="logs" v-loading="loading" stripe style="width:100%" max-height="600px">
      <el-table-column prop="id" label="#" width="60" />
      <el-table-column prop="created_at" label="时间" width="160">
        <template #default="{ row }">{{ row.created_at?.slice(0, 19) || '-' }}</template>
      </el-table-column>
      <el-table-column prop="user_name" label="操作人" width="100" />
      <el-table-column prop="action" label="操作" width="120">
        <template #default="{ row }">
          <el-tag :type="actionType(row.action)" size="small">{{ actionLabel(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="resource_type" label="资源" width="100" />
      <el-table-column prop="resource_id" label="资源ID" width="70" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'success' ? 'success' : row.status === 'fail' ? 'danger' : 'warning'" size="small">
            {{ { success: '成功', fail: '失败', partial: '部分' }[row.status] || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="detail" label="详情" min-width="300">
        <template #default="{ row }">
          <div class="log-detail" v-if="row.detail">{{ row.detail }}</div>
          <div class="log-error" v-if="row.error_message">{{ row.error_message }}</div>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadLogs"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import http from '../api/http'

const logs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)

const filters = reactive({
  action: '',
  status: '',
})

const actionMap = {
  import: { label: '导入', type: '' },
  export: { label: '导出', type: 'success' },
  create_opportunity: { label: '创建商机', type: '' },
  update_opportunity: { label: '编辑商机', type: 'warning' },
  delete_opportunity: { label: '删除商机', type: 'danger' },
  create_progress: { label: '提交进度', type: '' },
  ai_analyze: { label: 'AI分析', type: 'info' },
  login: { label: '登录', type: 'info' },
}

function actionLabel(action) {
  return actionMap[action]?.label || action
}
function actionType(action) {
  return actionMap[action]?.type || ''
}

async function loadLogs() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.action) params.action = filters.action
    if (filters.status) params.status = filters.status
    const res = await http.get('/logs', { params })
    logs.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.action = ''
  filters.status = ''
  page.value = 1
  loadLogs()
}

onMounted(loadLogs)
</script>

<style scoped>
.page-head { margin-bottom:20px; }
.page-head h2 { font-size:20px; font-weight:600; color:var(--ds-text); margin:0; }
.filter-card { margin-bottom:16px; }
.log-detail { font-size:12px; color:var(--ds-text-subtle); max-height:48px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.log-error { font-size:12px; color:#DE350B; margin-top:2px; }
.pagination-wrap { display:flex; justify-content:flex-end; margin-top:16px; }
</style>
