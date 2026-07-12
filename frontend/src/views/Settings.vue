<template>
  <div class="page-head"><h2>系统设置</h2></div>
  <el-tabs v-model="activeTab">
    <!-- === 用户管理 === -->
    <el-tab-pane label="用户管理" name="users">
      <el-card shadow="never">
        <div style="margin-bottom:16px">
          <el-button type="primary" size="small" :icon="Plus" @click="openCreateUser">新增用户</el-button>
        </div>
        <el-table :data="users" stripe style="width:100%">
          <el-table-column prop="username" label="账号" width="120" />
          <el-table-column prop="real_name" label="姓名" width="120" />
          <el-table-column prop="email" label="邮箱" width="200" />
          <el-table-column prop="role" label="角色" width="130" />
          <el-table-column prop="department" label="部门" width="130" />
          <el-table-column prop="is_active" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link size="small" type="primary" @click="editUser(row)">编辑</el-button>
              <el-popconfirm title="确定删除？" @confirm="deleteUser(row.id)">
                <template #reference><el-button link size="small" type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </el-tab-pane>

    <!-- === AI 配置 === -->
    <el-tab-pane label="AI 配置" name="ai">
      <el-card shadow="never">
        <el-form label-position="top" style="max-width:600px">
          <el-form-item label="API Key">
            <el-input v-model="aiCfg.api_key" type="password" show-password placeholder="sk-..." />
          </el-form-item>
          <el-form-item label="API 地址">
            <el-input v-model="aiCfg.api_url" placeholder="https://api.deepseek.com/chat/completions" />
            <div style="font-size:12px;color:var(--ds-text-subtle);margin-top:4px">兼容 OpenAI 格式，支持 DeepSeek / 通义千问 / 智谱 GLM 等</div>
          </el-form-item>
          <el-form-item label="模型">
            <el-input v-model="aiCfg.model" placeholder="deepseek-chat" />
          </el-form-item>
          <el-button type="primary" @click="saveAiConfig" :loading="savingAi">保存 AI 配置</el-button>
        </el-form>
      </el-card>
    </el-tab-pane>

    <!-- === 邮件配置 === -->
    <el-tab-pane label="邮件配置" name="email">
      <el-card shadow="never">
        <el-form label-position="top" style="max-width:600px">
          <h3 style="margin:0 0 16px;font-size:15px">SMTP 服务器</h3>
          <el-form-item label="SMTP 服务器">
            <el-input v-model="emailCfg.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="端口">
            <el-input-number v-model="emailCfg.smtp_port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="SMTP 用户名">
            <el-input v-model="emailCfg.smtp_user" placeholder="邮箱账号或用户名" />
          </el-form-item>
          <el-form-item label="SMTP 密码">
            <el-input v-model="emailCfg.smtp_pass" type="password" show-password placeholder="邮箱密码或授权码" />
          </el-form-item>
          <el-form-item label="发件人地址">
            <el-input v-model="emailCfg.sender" placeholder="noreply@example.com" />
          </el-form-item>

          <h3 style="margin:24px 0 16px;font-size:15px">预警规则</h3>
          <el-form-item label="招标临近预警(天)">
            <el-input-number v-model="emailCfg.bid_approach_days" :min="1" :max="90" />
          </el-form-item>
          <el-form-item label="未推进超期预警(天)">
            <el-input-number v-model="emailCfg.no_push_warn_days" :min="1" :max="90" />
          </el-form-item>
          <el-form-item label="AI自动升级优先级">
            <el-switch v-model="emailCfg.priority_auto_upgrade" />
          </el-form-item>

          <el-button type="primary" @click="saveEmailConfig" :loading="savingEmail">保存邮件配置</el-button>
        </el-form>
      </el-card>
    </el-tab-pane>

    <!-- === 邮件模板 === -->
    <el-tab-pane label="邮件模板" name="templates">
      <el-card shadow="never">
        <div style="margin-bottom:16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
          <el-select v-model="selectedTemplateKey" placeholder="选择模板" style="width:200px" @change="loadTemplate">
            <el-option v-for="(tpl, key) in emailTemplates" :key="key" :label="templateLabels[key] || key" :value="key" />
          </el-select>
          <el-button type="primary" @click="saveCurrentTemplate" :loading="savingTpl">保存模板</el-button>
          <el-button @click="resetCurrentTemplate">恢复默认</el-button>
          <span style="font-size:12px;color:var(--ds-text-subtle);margin-left:8px">
            使用 <a href="https://jinja.palletsprojects.com/" target="_blank" style="color:var(--ds-text-link)">Jinja2</a> 模板语法，变量用 <code>{<!-- -->{ variable }}</code>
          </span>
        </div>
        <el-form label-position="top">
          <el-form-item label="邮件主题">
            <el-input v-model="currentTemplate.subject" placeholder="邮件主题模板（支持 Jinja2 变量）" />
          </el-form-item>
          <!-- 动态字段：根据蓝图渲染表单 -->
          <template v-if="currentBlueprint">
            <el-form-item v-for="(field, fkey) in currentBlueprint.fields" :key="fkey" :label="field.label">
              <el-input
                v-if="field.type === 'text'"
                v-model="currentFields[fkey]"
                :placeholder="field.default"
              />
              <el-color-picker
                v-else-if="field.type === 'color'"
                v-model="currentFields[fkey]"
              />
              <el-input
                v-else
                v-model="currentFields[fkey]"
                type="textarea"
                :rows="4"
                :placeholder="field.default"
              />
            </el-form-item>
          </template>
          <div v-else style="color:var(--ds-text-subtle);padding:12px 0">请先选择一个模板</div>
        </el-form>
      </el-card>
    </el-tab-pane>

    <!-- === Scheduler 状态 === -->
    <el-tab-pane label="Scheduler 状态" name="scheduler">
      <el-card shadow="never">
        <pre v-if="schedulerStatus" style="font-size:13px;line-height:1.8;">{{ JSON.stringify(schedulerStatus, null, 2) }}</pre>
        <div v-else class="text-subtle">加载中...</div>
      </el-card>
    </el-tab-pane>
  </el-tabs>

  <!-- User dialog -->
  <el-dialog v-model="showUserForm" :title="editingUser ? '编辑用户' : '新增用户'" width="450px">
    <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-position="top">
      <el-form-item label="账号" prop="username">
        <el-input v-model="userForm.username" :disabled="!!editingUser" />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input v-model="userForm.password" type="password" show-password :placeholder="editingUser ? '留空则不修改' : '请输入密码'" />
      </el-form-item>
      <el-form-item label="姓名" prop="real_name">
        <el-input v-model="userForm.real_name" />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input v-model="userForm.email" placeholder="必填，用于接收邮件通知" />
      </el-form-item>
      <el-form-item label="角色" prop="role">
        <el-select v-model="userForm.role" style="width:100%">
          <el-option label="项目经理" value="项目经理" />
          <el-option label="客户经理" value="客户经理" />
          <el-option label="责任支局长" value="责任支局长" />
          <el-option label="管理员" value="管理员" />
        </el-select>
      </el-form-item>
      <el-form-item label="部门">
        <el-input v-model="userForm.department" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showUserForm = false">取消</el-button>
      <el-button type="primary" @click="saveUser" :loading="savingUser">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import http from '../api/http'
import { userApi } from '../api'

const activeTab = ref('users')
const users = ref([])
const showUserForm = ref(false)
const editingUser = ref(null)
const savingUser = ref(false)
const savingAi = ref(false)
const savingEmail = ref(false)
const savingTpl = ref(false)
const schedulerStatus = ref(null)
const userFormRef = ref(null)
const userForm = reactive({})

/* ============ AI 配置 ============ */
const aiCfg = reactive({
  api_key: '',
  api_url: 'https://api.deepseek.com/chat/completions',
  model: 'deepseek-chat',
})

async function loadAiConfig() {
  try {
    const res = await http.get('/configs')
    const data = res.data
    if (data.deepseek_api_key !== undefined) aiCfg.api_key = data.deepseek_api_key || ''
    if (data.deepseek_api_url !== undefined) aiCfg.api_url = data.deepseek_api_url || 'https://api.deepseek.com/chat/completions'
    if (data.deepseek_model !== undefined) aiCfg.model = data.deepseek_model || 'deepseek-chat'
  } catch { /* use defaults */ }
}

async function saveAiConfig() {
  savingAi.value = true
  try {
    const configs = [
      { config_key: 'deepseek_api_key', config_value: aiCfg.api_key },
      { config_key: 'deepseek_api_url', config_value: aiCfg.api_url },
      { config_key: 'deepseek_model', config_value: aiCfg.model },
    ]
    await http.put('/configs', { configs })
    ElMessage.success('AI 配置已保存')
  } finally {
    savingAi.value = false
  }
}

/* ============ 邮件配置 ============ */
const emailCfg = reactive({
  smtp_host: '',
  smtp_port: 465,
  smtp_user: '',
  smtp_pass: '',
  sender: '',
  bid_approach_days: 7,
  no_push_warn_days: 7,
  priority_auto_upgrade: true,
})

async function loadEmailConfig() {
  try {
    const res = await http.get('/configs')
    const data = res.data
    if (data.email_smtp_host !== undefined) emailCfg.smtp_host = data.email_smtp_host || ''
    if (data.email_smtp_port !== undefined) emailCfg.smtp_port = parseInt(data.email_smtp_port) || 465
    if (data.email_smtp_user !== undefined) emailCfg.smtp_user = data.email_smtp_user || ''
    if (data.email_smtp_pass !== undefined) emailCfg.smtp_pass = data.email_smtp_pass || ''
    if (data.email_sender !== undefined) emailCfg.sender = data.email_sender || ''
    if (data.bid_approach_days !== undefined) emailCfg.bid_approach_days = parseInt(data.bid_approach_days) || 7
    if (data.no_push_warn_days !== undefined) emailCfg.no_push_warn_days = parseInt(data.no_push_warn_days) || 7
    if (data.priority_auto_upgrade !== undefined) emailCfg.priority_auto_upgrade = data.priority_auto_upgrade === 'true'
  } catch { /* use defaults */ }
}

async function saveEmailConfig() {
  savingEmail.value = true
  try {
    const configs = [
      { config_key: 'email_smtp_host', config_value: emailCfg.smtp_host },
      { config_key: 'email_smtp_port', config_value: String(emailCfg.smtp_port) },
      { config_key: 'email_smtp_user', config_value: emailCfg.smtp_user },
      { config_key: 'email_smtp_pass', config_value: emailCfg.smtp_pass },
      { config_key: 'email_sender', config_value: emailCfg.sender },
      { config_key: 'bid_approach_days', config_value: String(emailCfg.bid_approach_days) },
      { config_key: 'no_push_warn_days', config_value: String(emailCfg.no_push_warn_days) },
      { config_key: 'priority_auto_upgrade', config_value: emailCfg.priority_auto_upgrade ? 'true' : 'false' },
    ]
    await http.put('/configs', { configs })
    ElMessage.success('邮件配置已保存')
  } finally {
    savingEmail.value = false
  }
}

/* ============ 邮件模板 ============ */
const templateLabels = {
  weekly_remind: '周度提醒',
  ai_alert: 'AI 风险预警',
  priority_change: '优先级变更',
  bid_approach: '招标临近提醒',
  no_push_warn: '未推进超期预警',
  progress_update: '进度更新通知',
}

const emailTemplates = ref({})
const templateBlueprints = ref({})
const selectedTemplateKey = ref('')
const currentTemplate = reactive({ subject: '', fields: {} })
const currentFields = reactive({})
const currentBlueprint = computed(() => {
  if (!selectedTemplateKey.value) return null
  return templateBlueprints.value[selectedTemplateKey.value] || null
})

async function loadEmailTemplates() {
  try {
    const [tplRes, bpRes] = await Promise.all([
      http.get('/configs/email-templates'),
      http.get('/configs/email-template-blueprints'),
    ])
    emailTemplates.value = tplRes.data.templates
    templateBlueprints.value = bpRes.data.blueprints
    if (!selectedTemplateKey.value) {
      const keys = Object.keys(emailTemplates.value)
      if (keys.length > 0) selectedTemplateKey.value = keys[0]
    }
    loadTemplate(selectedTemplateKey.value)
  } catch { /* use defaults */ }
}

function loadTemplate(key) {
  if (!key || !emailTemplates.value[key]) return
  const tpl = emailTemplates.value[key]
  currentTemplate.subject = tpl.subject || ''
  // Reset fields and populate from template
  Object.keys(currentFields).forEach(k => delete currentFields[k])
  const fields = tpl.fields || {}
  const bp = templateBlueprints.value[key]
  if (bp) {
    for (const [fkey, fdef] of Object.entries(bp.fields)) {
      currentFields[fkey] = fields[fkey] !== undefined ? fields[fkey] : fdef.default
    }
  }
}

async function saveCurrentTemplate() {
  if (!selectedTemplateKey.value) return
  savingTpl.value = true
  try {
    // Build the fields object from currentFields (only keys defined in blueprint)
    const fields = {}
    const bp = templateBlueprints.value[selectedTemplateKey.value]
    if (bp) {
      for (const fkey of Object.keys(bp.fields)) {
        fields[fkey] = currentFields[fkey] !== undefined ? currentFields[fkey] : ''
      }
    }
    emailTemplates.value[selectedTemplateKey.value] = {
      subject: currentTemplate.subject,
      fields: fields,
    }
    await http.put('/configs/email-templates', { templates: emailTemplates.value })
    ElMessage.success('邮件模板已保存')
  } catch (err) {
    ElMessage.error('保存失败：' + (err.response?.data?.detail || err.message))
  } finally {
    savingTpl.value = false
  }
}

async function resetCurrentTemplate() {
  if (!selectedTemplateKey.value) return
  try {
    await ElMessageBox.confirm('确定恢复默认模板？自定义内容将丢失。', '确认', { type: 'warning' })
    const res = await http.get('/configs/email-templates')
    const defaults = res.data.templates
    if (defaults[selectedTemplateKey.value]) {
      currentTemplate.subject = defaults[selectedTemplateKey.value].subject
      const fields = defaults[selectedTemplateKey.value].fields || {}
      const bp = templateBlueprints.value[selectedTemplateKey.value]
      if (bp) {
        Object.keys(currentFields).forEach(k => delete currentFields[k])
        for (const [fkey, fdef] of Object.entries(bp.fields)) {
          currentFields[fkey] = fields[fkey] !== undefined ? fields[fkey] : fdef.default
        }
      }
      emailTemplates.value[selectedTemplateKey.value] = { ...defaults[selectedTemplateKey.value] }
      ElMessage.success('已恢复默认模板，点击「保存模板」生效')
    }
  } catch { /* cancelled */ }
}

/* ============ 用户管理 ============ */
const userRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [
    {
      validator: (rule, value, callback) => {
        if (!editingUser.value && !value) {
          callback(new Error('请输入密码'))
        } else if (value && value.length < 6) {
          callback(new Error('密码至少6位'))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

async function loadUsers() {
  const res = await userApi.list({ page: 1, page_size: 100 })
  users.value = res.data.items
}

function openCreateUser() {
  editingUser.value = null
  for (const k of Object.keys(userForm)) delete userForm[k]
  userForm.password = ''
  showUserForm.value = true
}

function editUser(row) {
  editingUser.value = row
  Object.assign(userForm, { ...row })
  showUserForm.value = true
}

async function saveUser() {
  const valid = await userFormRef.value.validate().catch(() => false)
  if (!valid) return
  savingUser.value = true
  try {
    if (editingUser.value) {
      await userApi.update(editingUser.value.id, userForm)
      ElMessage.success('更新成功')
    } else {
      await userApi.create(userForm)
      ElMessage.success('创建成功')
    }
    showUserForm.value = false
    loadUsers()
  } catch {
    // Error message already displayed by http interceptor
  } finally {
    savingUser.value = false
  }
}

async function deleteUser(id) {
  await http.delete(`/users/${id}`)
  ElMessage.success('已删除')
  loadUsers()
}

/* ============ Scheduler ============ */
async function loadScheduler() {
  try {
    const res = await http.get('/scheduler/status')
    schedulerStatus.value = res.data
  } catch { /* ignore */ }
}

onMounted(() => {
  loadUsers()
  loadAiConfig()
  loadEmailConfig()
  loadEmailTemplates()
  loadScheduler()
})
</script>

<style scoped>
.page-head { margin-bottom:20px; }
.page-head h2 { font-size:20px; font-weight:600; color:var(--ds-text); margin:0; }
.text-subtle { color:var(--ds-text-subtle); padding:20px; }
</style>
