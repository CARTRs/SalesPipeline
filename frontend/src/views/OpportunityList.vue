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
          <el-option label="紧急" :value="1" />
          <el-option label="高" :value="2" />
          <el-option label="中" :value="3" />
          <el-option label="低" :value="4" />
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

  <!-- 表格（Jira 风格） -->
  <el-card shadow="never" class="table-card">
    <el-table
      :data="list"
      v-loading="loading"
      stripe
      style="width:100%"
      @row-click="goDetail"
      row-class-name="jira-row"
    >
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="priority_level" label="优先级" width="80" align="center">
        <template #default="{ row }">
          <el-tag :class="'tag-priority-' + row.priority_level" size="small" effect="dark">
            {{ { 1: '紧急', 2: '高', 3: '中', 4: '低' }[row.priority_level] }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="opportunity_name" label="商机名称" min-width="200">
        <template #default="{ row }">
          <a class="link-name">{{ row.opportunity_name }}</a>
        </template>
      </el-table-column>
      <el-table-column prop="customer_name" label="客户名称" width="160" />
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
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Search, Aim } from '@element-plus/icons-vue'
import http from '../api/http'
import { opportunityApi } from '../api'
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

async function handleAiAnalyzeAll() {
  aiAnalyzing.value = true
  try {
    const res = await http.post('/ai/analyze-all', null, { timeout: 300000 })
    const data = res.data
    if (data.failed > 0) {
      ElMessage.warning(`AI分析完成：成功 ${data.analyzed} 条，失败 ${data.failed} 条`)
    } else {
      ElMessage.success(`AI分析完成，共分析 ${data.analyzed} 条商机`)
    }
    loadData()
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    if (err.code === 'ECONNABORTED' || detail?.includes('timeout')) {
      ElMessage.warning('AI 分析请求超时，商机数量较多或 DeepSeek API 响应较慢，请稍后分批分析')
    } else if (detail?.includes('key') || detail?.includes('配置')) {
      ElMessage.warning('AI 分析失败：DeepSeek API Key 未配置，请在系统设置中配置')
    } else {
      ElMessage.error(`AI分析请求失败：${detail}`)
    }
  } finally {
    aiAnalyzing.value = false
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
</style>

<style>
.jira-row { cursor: pointer; }
</style>
