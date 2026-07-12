<template>
  <div v-loading="loading">
    <template v-if="opp">
      <div class="detail-head">
        <div class="detail-head-left">
          <el-tag :class="'tag-priority-' + opp.priority_level" size="small" effect="dark" round>
            {{ { 1: '紧急', 2: '高', 3: '中', 4: '低' }[opp.priority_level] }}
          </el-tag>
          <h1 class="detail-title">{{ opp.opportunity_name }}</h1>
          <el-tag v-if="opp.opportunity_status" size="small" effect="plain" :type="statusType">
            {{ opp.opportunity_status }}
          </el-tag>
        </div>
        <div class="detail-head-actions">
          <el-button size="small" @click="$router.push(`/opportunities/${opp.id}/edit`)">编辑</el-button>
          <el-button size="small" type="primary" @click="triggerAiAnalysis" :loading="aiLoading">AI分析</el-button>
        </div>
      </div>

      <el-alert
        v-if="opp && (!opp.division_member || !opp.account_manager || !opp.branch_director)"
        title="此商机缺少三角色人员，请在编辑页面补充完整的项目经理、客户经理和责任支局长"
        type="warning"
        show-icon
        :closable="false"
        style="margin-bottom:16px"
      />

      <el-row :gutter="24">
        <!-- 左侧主内容 -->
        <el-col :span="16">
          <el-card shadow="never" class="detail-section">
            <template #header>基本信息</template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="客户名称">{{ opp.customer_name }}</el-descriptions-item>
              <el-descriptions-item label="商机状态">{{ opp.opportunity_status || '-' }}</el-descriptions-item>
              <el-descriptions-item label="预测金额">{{ opp.predicted_amount ? `${Number(opp.predicted_amount).toLocaleString()} 万元` : '-' }}</el-descriptions-item>
              <el-descriptions-item label="支局">{{ opp.branch_office || '-' }}</el-descriptions-item>
              <el-descriptions-item label="产品类别">{{ opp.product_category || '-' }}</el-descriptions-item>
              <el-descriptions-item label="预计签约">{{ opp.estimated_sign_date || '-' }}</el-descriptions-item>
              <el-descriptions-item label="未推进天数"><span :style="{color: opp.no_push_days > 7 ? '#DE350B' : '#5E6C84', fontWeight: 600}">{{ opp.no_push_days || 0 }} 天</span></el-descriptions-item>
              <el-descriptions-item label="是否清单客户">{{ opp.is_list_customer ? '是' : '否' }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 进度时间线 Tab -->
          <el-card shadow="never" class="detail-section">
            <template #header>
              <div style="display:flex;align-items:center;justify-content:space-between">
                <span>进度时间线</span>
                <el-button type="primary" size="small" @click="showProgressForm = true">+ 填写进度</el-button>
              </div>
            </template>

            <!-- 进度填写表单 -->
            <el-collapse-transition>
              <div v-if="showProgressForm" class="progress-form-box">
                <el-form :model="progressForm" label-position="top">
                  <el-form-item label="进度内容">
                    <el-input
                      v-model="progressForm.progress_content"
                      type="textarea"
                      :rows="4"
                      placeholder="请描述本周商机推进情况..."
                    />
                  </el-form-item>
                  <el-form-item label="进度日期">
                    <el-date-picker v-model="progressForm.progress_date" type="date" style="width:200px" />
                  </el-form-item>
                  <div style="text-align:right;margin-top:8px">
                    <el-button @click="showProgressForm = false">取消</el-button>
                    <el-button type="primary" @click="submitProgress" :loading="submitting">提交</el-button>
                  </div>
                </el-form>
              </div>
            </el-collapse-transition>

            <!-- 时间线列表 -->
            <div v-if="progressList.length === 0" class="empty-timeline">
              暂无进度记录，点击上方「填写进度」开始
            </div>
            <div v-else class="timeline">
              <div v-for="(item, idx) in progressList" :key="item.id" class="timeline-item">
                <div class="timeline-dot" :class="roleColor(item.updater_role)" />
                <div v-if="idx > 0" class="timeline-line" />
                <div class="timeline-content">
                  <div class="timeline-header">
                    <span class="timeline-role-tag" :class="roleColor(item.updater_role)">{{ item.updater_role }}</span>
                    <span class="timeline-author">{{ item.updater_name || '用户' }}</span>
                    <span class="timeline-time">{{ item.progress_date }}</span>
                  </div>
                  <div class="timeline-body">{{ item.progress_content }}</div>
                </div>
              </div>
            </div>
          </el-card>

          <!-- AI分析面板 -->
          <el-card shadow="never" class="detail-section">
            <template #header>AI 分析</template>
            <div v-if="opp.ai_analysis_summary" class="ai-panel">
              <div class="ai-summary">{{ opp.ai_analysis_summary }}</div>
              <div v-if="opp.next_action_required" class="ai-actions">
                <strong>建议行动：</strong>{{ opp.next_action_required }}
              </div>
              <div v-if="opp.competitor_detected || opp.bid_date_approaching" class="ai-signals">
                <el-tag v-if="opp.competitor_detected" type="danger" size="small" effect="dark" round>检测到竞争对手</el-tag>
                <el-tag v-if="opp.bid_date_approaching" type="warning" size="small" effect="dark" round>招标临近</el-tag>
              </div>
            </div>
            <div v-else class="text-subtle">暂无 AI 分析数据。提交进度后将自动触发 AI 分析，或点击右上角「AI分析」按钮手动触发。</div>
          </el-card>
        </el-col>

        <!-- 右侧面板 -->
        <el-col :span="8">
          <el-card shadow="never" class="detail-section">
            <template #header>三角色</template>
            <div class="roles-container">
              <div class="role-card" :class="{ 'role-missing': !opp.division_member }">
                <div class="role-label">项目经理</div>
                <div v-if="opp.division_member" class="role-info">
                  <div class="role-name">{{ opp.division_member.real_name }}</div>
                  <div class="role-email">{{ opp.division_member.email }}</div>
                </div>
                <div v-else class="role-missing-text">未分配</div>
              </div>
              <div class="role-card" :class="{ 'role-missing': !opp.account_manager }">
                <div class="role-label">客户经理</div>
                <div v-if="opp.account_manager" class="role-info">
                  <div class="role-name">{{ opp.account_manager.real_name }}</div>
                  <div class="role-email">{{ opp.account_manager.email }}</div>
                </div>
                <div v-else class="role-missing-text">未分配</div>
              </div>
              <div class="role-card" :class="{ 'role-missing': !opp.branch_director }">
                <div class="role-label">责任支局长</div>
                <div v-if="opp.branch_director" class="role-info">
                  <div class="role-name">{{ opp.branch_director.real_name }}</div>
                  <div class="role-email">{{ opp.branch_director.email }}</div>
                </div>
                <div v-else class="role-missing-text">未分配</div>
              </div>
            </div>
          </el-card>

          <el-card shadow="never" class="detail-section">
            <template #header>风险状态</template>
            <div class="risk-item">
              <span class="risk-label">AI风险等级</span>
              <el-tag :type="riskType" size="small">{{ opp.ai_risk_level || '未评估' }}</el-tag>
            </div>
            <div class="risk-item">
              <span class="risk-label">竞争对手</span>
              <el-tag :type="opp.competitor_detected ? 'danger' : 'info'" size="small">{{ opp.competitor_detected ? '已检测' : '未发现' }}</el-tag>
            </div>
            <div class="risk-item">
              <span class="risk-label">招标临近</span>
              <el-tag :type="opp.bid_date_approaching ? 'warning' : 'info'" size="small">{{ opp.bid_date_approaching ? '是' : '否' }}</el-tag>
            </div>
            <div class="risk-item">
              <span class="risk-label">邮件通知</span>
              <el-tag :type="emailStatus.has_sent ? 'success' : 'info'" size="small">{{ emailStatus.has_sent ? '已发送' : '未发送' }}</el-tag>
            </div>
            <div v-if="emailStatus.last_sent_at" class="risk-item">
              <span class="risk-label">最近发送</span>
              <span style="font-size:12px;color:var(--ds-text-subtle)">{{ formatTime(emailStatus.last_sent_at) }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'
import { opportunityApi } from '../api'

const route = useRoute()
const opp = ref(null)
const loading = ref(true)
const showProgressForm = ref(false)
const submitting = ref(false)
const aiLoading = ref(false)
const progressList = ref([])
const emailStatus = ref({ has_sent: false, last_sent_at: null })
let pollTimer = null

const progressForm = ref({
  progress_content: '',
  progress_date: new Date().toISOString().slice(0, 10),
})

const statusType = computed(() => {
  const map = { '已签约': 'success', '正常推进': 'primary', '需推进': 'warning', '长期跟踪': 'info' }
  return map[opp.value?.opportunity_status] || 'info'
})

const riskType = computed(() => {
  const map = { critical: 'danger', high: 'warning', medium: 'info', low: 'success' }
  return map[opp.value?.ai_risk_level] || 'info'
})

function roleColor(role) {
  const map = { '项目经理': 'role-member', '客户经理': 'role-manager', '责任支局长': 'role-director', '管理员': 'role-admin' }
  return map[role] || ''
}

async function loadDetail() {
  loading.value = true
  try {
    const res = await opportunityApi.get(route.params.id)
    opp.value = res.data
  } finally {
    loading.value = false
  }
}

async function loadProgress() {
  try {
    const res = await http.get(`/opportunities/${route.params.id}/progress`, { params: { page: 1, page_size: 50 } })
    progressList.value = res.data.items
  } catch { /* ignore */ }
}

async function loadEmailStatus() {
  try {
    const res = await http.get(`/email-logs/by-opportunity/${route.params.id}`)
    emailStatus.value = {
      has_sent: res.data.has_sent || false,
      last_sent_at: res.data.last_sent_at || null,
    }
  } catch { /* ignore */ }
}

function formatTime(t) {
  if (!t) return '-'
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function submitProgress() {
  if (!progressForm.value.progress_content?.trim()) {
    ElMessage.warning('请输入进度内容')
    return
  }
  submitting.value = true
  try {
    const payload = {
      progress_content: progressForm.value.progress_content,
      progress_date: progressForm.value.progress_date || new Date().toISOString().slice(0, 10),
    }
    const res = await http.post(`/opportunities/${route.params.id}/progress`, payload)
    ElMessage.success('进度提交成功，AI 分析和邮件发送中...')
    showProgressForm.value = false
    progressForm.value.progress_content = ''
    // Reload progress + opp detail
    await loadProgress()
    await loadDetail()
    // 启动轮询，等待 AI 分析和邮件发送完成
    startPolling()
  } finally {
    submitting.value = false
  }
}

function startPolling() {
  stopPolling()
  let count = 0
  pollTimer = setInterval(async () => {
    count++
    await Promise.all([
      loadEmailStatus(),
      loadDetail(),
    ])
    // 检查是否已完成（邮件已发送或达到最大轮询次数）
    if (emailStatus.value.has_sent || count >= 10) {
      stopPolling()
      if (emailStatus.value.has_sent) {
        ElMessage.success('邮件已发送')
      }
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function triggerAiAnalysis() {
  aiLoading.value = true
  try {
    await http.post(`/opportunities/${route.params.id}/analyze`, null, { timeout: 120000 })
    ElMessage.success('AI 分析完成')
    await loadDetail()
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    if (detail?.includes('key') || detail?.includes('配置')) {
      ElMessage.warning('AI 分析服务暂未配置，请在系统设置中配置 API Key')
    } else if (err.code === 'ECONNABORTED' || detail?.includes('timeout')) {
      ElMessage.warning('AI 分析请求超时，DeepSeek API 响应较慢，请稍后重试')
    } else {
      ElMessage.warning(`AI 分析失败：${detail}`)
    }
  } finally {
    aiLoading.value = false
  }
}

onMounted(() => {
  loadDetail()
  loadProgress()
  loadEmailStatus()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.detail-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; gap:12px; flex-wrap:wrap; }
.detail-head-left { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.detail-title { font-size:22px; font-weight:600; color:var(--ds-text); margin:0; }
.detail-section { margin-bottom:16px; }
.progress-form-box { padding:16px; background:#FAFBFC; border:1px solid var(--ds-border); border-radius:3px; margin-bottom:16px; }

/* Timeline */
.timeline { position:relative; padding-left:28px; }
.timeline-item { position:relative; padding-bottom:20px; }
.timeline-dot {
  position:absolute; left:-28px; top:4px;
  width:12px; height:12px; border-radius:50%;
  background:#C1C7D0; border:2px solid #fff; z-index:1;
}
.timeline-dot.role-member { background:#0052CC; }
.timeline-dot.role-manager { background:#00B8D9; }
.timeline-dot.role-director { background:#36B37E; }
.timeline-line {
  position:absolute; left:-23px; top:16px; bottom:0; width:2px;
  background:#EBECF0;
}
.timeline-content { background:#fff; border:1px solid var(--ds-border); border-radius:3px; padding:12px; }
.timeline-header { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.timeline-role-tag {
  display:inline-block; padding:1px 6px; border-radius:3px; font-size:11px; font-weight:600;
}
.timeline-role-tag.role-member { background:#DEEBFF; color:#0052CC; }
.timeline-role-tag.role-manager { background:#E6FCFF; color:#00B8D9; }
.timeline-role-tag.role-director { background:#E3FCEF; color:#36B37E; }
.timeline-author { font-size:13px; font-weight:600; color:var(--ds-text); }
.timeline-time { font-size:12px; color:var(--ds-text-subtle); margin-left:auto; }
.timeline-body { font-size:14px; line-height:1.6; color:var(--ds-text); white-space:pre-wrap; }
.empty-timeline { text-align:center; padding:48px; color:var(--ds-text-subtle); }

/* AI panel */
.ai-panel { font-size:14px; }
.ai-summary { margin-bottom:12px; line-height:1.6; }
.ai-actions { margin-bottom:12px; padding:8px 12px; background:#DEEBFF; border-radius:3px; }
.ai-signals { display:flex; gap:6px; }

/* Right panel */
.roles-container { display:flex; gap:12px; }
.role-card { flex:1; border:1px solid var(--ds-border); border-radius:3px; padding:12px; }
.role-card.role-missing { border-color: var(--ds-warning); background: var(--ds-warning-bg); }
.role-label { font-size:12px; color:var(--ds-text-subtle); margin-bottom:4px; }
.role-name { font-size:14px; font-weight:600; color:var(--ds-text); }
.role-email { font-size:12px; color:var(--ds-primary); }
.role-missing-text { font-size:13px; color:#DE350B; font-weight:500; }
.risk-item { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--ds-border); }
.risk-item:last-child { border-bottom:none; }
.risk-label { font-size:13px; color:var(--ds-text); }
.text-subtle { color:var(--ds-text-subtle); font-size:13px; padding:8px 0; }
</style>
