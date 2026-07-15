<template>
  <div class="page-head">
    <h2>{{ isEdit ? '编辑商机' : '新建商机' }}</h2>
  </div>
  <el-card shadow="never">
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      class="jira-form"
    >
      <el-row :gutter="24">
        <el-col :span="12">
          <el-form-item label="商机名称" prop="opportunity_name">
            <el-input v-model="form.opportunity_name" placeholder="请输入商机名称" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="客户名称" prop="customer_name">
            <el-input v-model="form.customer_name" placeholder="请输入客户名称" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="24">
        <el-col :span="8">
          <el-form-item label="客户类型">
            <el-select v-model="form.customer_type" placeholder="请选择" clearable style="width:100%">
              <el-option label="企业" value="企业" />
              <el-option label="政府" value="政府" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="预测金额(万元)">
            <el-input-number v-model="form.predicted_amount" :min="0" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="支局">
            <el-input v-model="form.branch_office" placeholder="输入支局名称" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="24">
        <el-col :span="8">
          <el-form-item label="产品类别">
            <el-input v-model="form.product_category" placeholder="如：算力租赁" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="预计签约日期">
            <el-date-picker v-model="form.estimated_sign_date" type="date" style="width:100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="商机状态">
            <el-select v-model="form.opportunity_status" placeholder="请选择" clearable style="width:100%">
              <el-option label="正常推进" value="正常推进" />
              <el-option label="需推进" value="需推进" />
              <el-option label="已签约" value="已签约" />
              <el-option label="长期跟踪" value="长期跟踪" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>
      <el-form-item label="客户需求详情">
        <el-input v-model="form.requirement_detail" type="textarea" :rows="4" placeholder="输入客户需求" />
      </el-form-item>

      <el-divider content-position="left">三角色人员（必填）</el-divider>
      <el-row :gutter="24">
        <el-col :span="8">
          <el-form-item label="项目经理" prop="division_member_id">
            <el-select v-model="form.division_member_id" placeholder="请选择项目经理" clearable filterable style="width:100%">
              <el-option v-for="u in divisionMembers" :key="u.id" :label="u.real_name + ' (' + (u.email||u.username) + ')'" :value="u.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="客户经理" prop="account_manager_id">
            <el-select v-model="form.account_manager_id" placeholder="请选择客户经理" clearable filterable style="width:100%">
              <el-option v-for="u in accountManagers" :key="u.id" :label="u.real_name + ' (' + (u.email||u.username) + ')'" :value="u.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="责任支局长" prop="branch_director_id">
            <el-select v-model="form.branch_director_id" placeholder="请选择责任支局长" clearable filterable style="width:100%">
              <el-option v-for="u in branchDirectors" :key="u.id" :label="u.real_name + ' (' + (u.email||u.username) + ')'" :value="u.id" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <div class="form-actions">
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </div>
    </el-form>
  </el-card>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { opportunityApi } from '../api'
import http from '../api/http'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const saving = ref(false)
const isEdit = computed(() => !!route.params.id)
const divisionMembers = ref([])
const accountManagers = ref([])
const branchDirectors = ref([])

const form = reactive({
  opportunity_name: '',
  customer_name: '',
  customer_type: '',
  predicted_amount: undefined,
  branch_office: '',
  product_category: '',
  estimated_sign_date: null,
  opportunity_status: '',
  requirement_detail: '',
  division_member_id: undefined,
  account_manager_id: undefined,
  branch_director_id: undefined,
})

const rules = {
  opportunity_name: [{ required: true, message: '请输入商机名称', trigger: 'blur' }],
  customer_name: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
  division_member_id: [{ required: true, message: '请选择项目经理', trigger: 'change' }],
  account_manager_id: [{ required: true, message: '请选择客户经理', trigger: 'change' }],
  branch_director_id: [{ required: true, message: '请选择责任支局长', trigger: 'change' }],
}

onMounted(async () => {
  // Load users for role selection
  try {
    const userRes = await http.get('/users', { params: { page_size: 100 } })
    const allUsers = userRes.data.items || []
    divisionMembers.value = allUsers.filter(u => u.role === '项目经理')
    accountManagers.value = allUsers.filter(u => u.role === '客户经理')
    branchDirectors.value = allUsers.filter(u => u.role === '责任支局长')
  } catch { /* ignore user load errors */ }

  if (isEdit.value) {
    const res = await opportunityApi.get(route.params.id)
    Object.assign(form, res.data)
  }
})

function formatDate(d) {
  if (!d) return null
  if (typeof d === 'string') return d
  const dt = d instanceof Date ? d : new Date(d)
  return dt.toISOString().slice(0, 10)
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const payload = { ...form, estimated_sign_date: formatDate(form.estimated_sign_date) }
    if (isEdit.value) {
      await opportunityApi.update(route.params.id, payload)
      ElMessage.success('更新成功，AI 分析中...')
      router.push(`/opportunities/${route.params.id}`)
    } else {
      await opportunityApi.create(payload)
      ElMessage.success('创建成功')
      router.push('/opportunities')
    }
  } catch (e) {
    // error message already shown by http interceptor
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.jira-form { max-width: 960px; }
.form-actions { margin-top: 24px; display: flex; gap: 8px; }
</style>
