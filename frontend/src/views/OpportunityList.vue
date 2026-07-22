<template>
  <div class="page-head">
    <div class="page-head-title">
      <h2>商机列表</h2>
      <span class="page-head-count">共 {{ total }} 条</span>
    </div>
    <div class="page-head-actions">
      <el-button type="primary" :icon="Plus" @click="$router.push('/opportunities/create')">
        新建商机
      </el-button>
      <el-button :icon="Aim" :loading="aiAnalyzing" @click="handleAiAnalyzeAll">
        AI分析
      </el-button>
      <el-button :icon="Upload" @click="importDialogRef?.open()">导入</el-button>
      <el-button :icon="Download" :loading="exporting" @click="handleExport">导出</el-button>
    </div>
  </div>

  <!-- 筛选栏（Jira 风格） -->
  <el-card class="filter-card" shadow="never">
    <el-form :model="filters" inline class="filter-form">
      <el-form-item label="状态">
        <el-select v-model="filters.status" placeholder="全部" clearable style="width:140px">
          <el-option label="正常推进" value="正常推进" />
          <el-option label="需推进" value="需推进" />
          <el-option label="已签约" value="已签约" />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级">
        <el-select v-model="filters.priority" placeholder="全部" clearable style="width:120px">
          <el-option label="高" :value="1" />
          <el-option label="中" :value="2" />
          <el-option label="低" :value="3" />
        </el-select>
      </el-form-item>
      <el-form-item label="支局">
        <el-input v-model="filters.branch_office" placeholder="输入支局名称" clearable style="width:150px" />
      </el-form-item>
      <el-form-item label="搜索">
        <el-input
          v-model="filters.keyword"
          placeholder="商机名称 / 客户名称"
          clearable
          style="width:200px"
          :prefix-icon="Search"
          @keyup.enter="loadData"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="loadData">筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <!-- 统计卡片（带入场动画） -->
  <el-row :gutter="16" class="stats-row">
    <el-col :span="6" v-for="(stat, idx) in stats" :key="stat.label">
      <el-card shadow="never" class="stat-card anim-fade-in-up" :class="'delay-' + (idx + 1)">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
      </el-card>
    </el-col>
  </el-row>

  <!-- 人员缺失提示 -->
  <el-alert
    v-if="memberWarnings.length > 0"
    :title="'部分商机缺少三角色人员：' + memberWarnings.join('；')"
    type="warning"
    show-icon
    :closable="false"
    style="margin-bottom:16px"
  />

  <!-- 导入对话框 -->
  <ImportDialog ref="importDialogRef" @imported="loadData" />

  <!-- 批量操作栏 -->
  <div v-if="selectedRows.length > 0" class="batch-bar">
    <span class="batch-count">已选择 {{ selectedRows.length }} 条商机</span>
    <el-button type="primary" size="small" @click="showBatchBindDialog">
      <el-icon><User /></el-icon> 批量绑定
    </el-button>
    <el-button type="danger" size="small" @click="handleBatchDelete">
      <el-icon><Delete /></el-icon> 批量删除
    </el-button>
    <el-button size="small" @click="clearSelection">取消选择</el-button>
  </div>

  <!-- 表格（Jira 风格） -->
  <el-card shadow="never" class="table-card">
    <el-table
      :data="list"
      v-loading="loading"
      stripe
      style="width:100%"
      @row-click="goDetail"
      row-class-name="jira-row"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="priority_level" label="优先级" width="80" align="center">
        <template #default="{ row }">
          <el-tag :class="'tag-priority-' + row.priority_level" size="small" effect="dark">
            {{ { 1: '高', 2: '中', 3: '低' }[row.priority_level] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="opportunity_name" label="商机名称" min-width="200">
        <template #default="{ row }">
          <a class="link-name">{{ row.opportunity_name }}</a>
        </template>
      </el-table-column>
      <el-table-column prop="customer_name" label="客户名称" width="160" />
      <el-table-column prop="branch_office" label="支局" width="100">
        <template #default="{ row }">
          {{ row.branch_office || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="predicted_amount" label="预测金额(万)" width="120" align="right">
        <template #default="{ row }">
          {{ row.predicted_amount ? Number(row.predicted_amount).toLocaleString() : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="opportunity_status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :class="getStatusClass(row)" size="small" effect="plain">
            {{ row.opportunity_status || '-' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="no_push_days" label="未推进(天)" width="100" align="center">
        <template #default="{ row }">
          <span :style="{ color: row.no_push_days > 7 ? '#DE350B' : '#5E6C84' }">
            {{ row.no_push_days || 0 }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click.stop="$router.push(`/opportunities/${row.id}`)">
            详情
          </el-button>
          <el-button link type="primary" size="small" @click.stop="$router.push(`/opportunities/${row.id}/edit`)">
            编辑
          </el-button>
          <el-popconfirm title="确定删除此商机？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button link type="danger" size="small" @click.stop>删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </div>
  </el-card>

  <!-- 批量绑定对话框 -->
  <el-dialog v-model="batchBindVisible" title="批量绑定商机" width="420px">
    <el-form label-width="100px">
      <el-form-item label="绑定角色">
        <el-select v-model="batchBindRole" placeholder="选择角色" style="width:100%">
          <el-option label="项目经理" value="division_member_id" />
          <el-option label="客户经理" value="account_manager_id" />
          <el-option label="责任支局长" value="branch_director_id" />
        </el-select>
      </el-form-item>
      <el-form-item label="选择人员">
        <el-select
          v-model="batchBindUserId"
          placeholder="搜索用户姓名"
          filterable
          style="width:100%"
        >
          <el-option
            v-for="user in userList"
            :key="user.id"
            :label="user.real_name"
            :value="user.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="batchBindVisible = false">取消</el-button>
      <el-button type="primary" :loading="batchBinding" @click="handleBatchBind">
        确定绑定 ({{ selectedRows.length }} 条)
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Search, Aim, User, Delete } from '@element-plus/icons-vue'
import http from '../api/http'
import { opportunityApi, userApi } from '../api'
import ImportDialog from '../components/ImportDialog.vue'

const router = useRouter()
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const importDialogRef = ref()

const memberWarnings = ref([])
const exporting = ref(false)
const aiAnalyzing = ref(false)

// 多选相关
const selectedRows = ref([])

// 批量绑定相关
const batchBindVisible = ref(false)
const batchBindRole = ref('division_member_id')
const batchBindUserId = ref(null)
const batchBinding = ref(false)
const userList = ref([])

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function clearSelection() {
  selectedRows.value = []
}

async function showBatchBindDialog() {
  batchBindRole.value = 'division_member_id'
  batchBindUserId.value = null
  batchBindVisible.value = true
  // 加载用户列表
  if (userList.value.length === 0) {
    try {
      const res = await userApi.list({ page_size: 200 })
      userList.value = res.data.items || []
    } catch (e) {
      console.error('加载用户列表失败', e)
    }
  }
}

async function handleBatchBind() {
  if (!batchBindUserId.value) {
    ElMessage.warning('请选择绑定人员')
    return
  }
  batchBinding.value = true
  try {
    const ids = selectedRows.value.map(r => r.id)
    await opportunityApi.batchBind(ids, batchBindRole.value, batchBindUserId.value)
    const roleName = { division_member_id: '项目经理', account_manager_id: '客户经理', branch_director_id: '责任支局长' }[batchBindRole.value]
    const userName = userList.value.find(u => u.id === batchBindUserId.value)?.real_name || ''
    ElMessage.success(`已将 ${ids.length} 条商机绑定给 ${userName}（${roleName}）`)
    batchBindVisible.value = false
    selectedRows.value = []
    loadData()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '绑定失败')
  } finally {
    batchBinding.value = false
  }
}

async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selectedRows.value.length} 条商机？`, '批量删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    const ids = selectedRows.value.map(r => r.id)
    await opportunityApi.batchDelete(ids)
    ElMessage.success(`已删除 ${ids.length} 条商机`)
    selectedRows.value = []
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const res = await http.get('/opportunities/export', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '商机列表.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } finally {
    exporting.value = false
  }
}

let aiPollTimer = null

async function handleAiAnalyzeAll() {
  aiAnalyzing.value = true
  try {
    const res = await http.post('/ai/analyze-all', null, { timeout: 10000 })
    const data = res.data
    const taskId = data.task_id
    if (!taskId) {
      ElMessage.info('没有需要分析的商机')
      aiAnalyzing.value = false
      return
    }
    ElMessage.success(`AI 分析已启动，共 ${data.total} 条商机正在后台分析...`)
    // 轮询进度
    startAiPolling(taskId, data.total)
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    if (detail?.includes('key') || detail?.includes('配置')) {
      ElMessage.warning('AI 分析失败：DeepSeek API Key 未配置，请在系统设置中配置')
    } else {
      ElMessage.error(`AI分析请求失败：${detail}`)
    }
    aiAnalyzing.value = false
  }
}

function startAiPolling(taskId, total) {
  stopAiPolling()
  let lastAnalyzed = 0
  aiPollTimer = setInterval(async () => {
    try {
      const res = await http.get(`/ai/analyze-all/${taskId}`)
      const task = res.data
      if (task.is_completed) {
        stopAiPolling()
        aiAnalyzing.value = false
        loadData()
        if (task.failed > 0) {
          ElMessage.warning(`AI分析完成：成功 ${task.analyzed} 条，失败 ${task.failed} 条`)
        } else {
          ElMessage.success(`AI分析完成，共分析 ${task.analyzed} 条商机`)
        }
      } else if (task.analyzed > lastAnalyzed) {
        lastAnalyzed = task.analyzed
        ElMessage.info(`AI分析进行中：${task.analyzed}/${total}（失败 ${task.failed}）`)
      }
    } catch {
      // 轮询出错时不中断，下次重试
    }
  }, 5000)
}

function stopAiPolling() {
  if (aiPollTimer) {
    clearInterval(aiPollTimer)
    aiPollTimer = null
  }
}

const filters = reactive({
  status: '',
  priority: '',
  branch_office: '',
  keyword: '',
})

const stats = reactive([
  { label: '总商机数', value: '-' },
  { label: '本月新增', value: '-' },
  { label: '待签约金额', value: '-' },
  { label: '漏单率', value: '-' },
])

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (filters.status) params.status = filters.status
    if (filters.priority) params.priority = filters.priority
    if (filters.branch_office) params.branch_office = filters.branch_office
    if (filters.keyword) params.keyword = filters.keyword

    const res = await opportunityApi.list(params)
    list.value = res.data.items
    total.value = res.data.total
    stats[0].value = res.data.total

    const missingDivision = list.value.filter(o => !o.division_member_id).length
    const missingManager = list.value.filter(o => !o.account_manager_id).length
    const missingDirector = list.value.filter(o => !o.branch_director_id).length
    const warnings = []
    if (missingDivision > 0) warnings.push(`${missingDivision}条缺少项目经理`)
    if (missingManager > 0) warnings.push(`${missingManager}条缺少客户经理`)
    if (missingDirector > 0) warnings.push(`${missingDirector}条缺少责任支局长`)
    memberWarnings.value = warnings
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.status = ''
  filters.priority = ''
  filters.branch_office = ''
  filters.keyword = ''
  page.value = 1
  loadData()
}

function goDetail(row) {
  router.push(`/opportunities/${row.id}`)
}

async function handleDelete(id) {
  await opportunityApi.delete(id)
  loadData()
}

function getStatusClass(row) {
  if (!row.opportunity_status) return ''
  if (row.opportunity_status === '已签约') return 'tag-status-normal'
  return 'tag-status-warning'
}

onMounted(loadData)

onUnmounted(() => {
  stopAiPolling()
})
</script>

<style scoped>
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-head-title { display: flex; align-items: baseline; gap: 12px; }
.page-head-title h2 { font-size: 20px; font-weight: 600; color: var(--ds-text); margin: 0; }
.page-head-count { font-size: 13px; color: var(--ds-text-subtle); }
.page-head-actions { display: flex; gap: 8px; }
.filter-card { margin-bottom: 16px; }
.filter-form { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; cursor: pointer; transition: box-shadow 0.2s; }
.stat-card:hover { box-shadow: 0 2px 4px rgba(9,30,66,0.25); }
.stat-value { font-size: 28px; font-weight: 600; color: var(--ds-text); }
.stat-label { font-size: 13px; color: var(--ds-text-subtle); margin-top: 4px; }
.table-card { border-top: none; }
.link-name { color: var(--ds-text-link); text-decoration: none; }
.link-name:hover { text-decoration: underline; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }

.batch-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 12px;
  background: #E3FCEF;
  border: 1px solid #36B37E;
  border-radius: 4px;
}
.batch-count {
  font-size: 14px;
  font-weight: 500;
  color: #006644;
  margin-right: 8px;
}
</style>

<style>
.jira-row { cursor: pointer; }
</style>
