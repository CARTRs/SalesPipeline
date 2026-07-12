<template>
  <el-dialog
    v-model="visible"
    title="导入商机"
    width="520px"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <div class="import-body">
      <!-- 下载模板 -->
      <div class="template-section">
        <el-button type="primary" plain :icon="Download" @click="downloadTemplate">
          下载导入模板
        </el-button>
        <span class="template-hint">下载 Excel 模板，按模板格式填写后上传</span>
      </div>

      <el-divider />

      <!-- 拖拽上传区域 -->
      <div
        class="upload-zone"
        :class="{ 'upload-dragover': isDragover, 'upload-has-file': selectedFile }"
        @dragover.prevent="isDragover = true"
        @dragleave.prevent="isDragover = false"
        @drop.prevent="handleDrop"
        @click="triggerFileSelect"
      >
        <template v-if="!selectedFile">
          <el-icon class="upload-icon" :size="40"><UploadFilled /></el-icon>
          <p class="upload-text">将 Excel 文件拖到此处，或<em>点击选择文件</em></p>
          <p class="upload-hint">仅支持 .xlsx / .xls 格式</p>
        </template>
        <template v-else>
          <el-icon class="upload-icon" :size="40" color="#0052CC"><Document /></el-icon>
          <p class="upload-text file-name">{{ selectedFile.name }}</p>
          <p class="upload-hint file-size">{{ (selectedFile.size / 1024).toFixed(1) }} KB</p>
          <el-button size="small" type="danger" link @click.stop="selectedFile = null">重新选择</el-button>
        </template>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="importing" :disabled="!selectedFile" @click="handleImport">
        {{ importing ? '导入中...' : '开始导入' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, UploadFilled, Document } from '@element-plus/icons-vue'
import http from '../api/http'

const emit = defineEmits(['imported'])
const visible = ref(false)
const importing = ref(false)
const isDragover = ref(false)
const selectedFile = ref(null)

function open() {
  visible.value = true
}

function handleClosed() {
  selectedFile.value = null
  isDragover.value = false
}

async function downloadTemplate() {
  try {
    const res = await http.get('/opportunities/import-template', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '商机导入模板.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('模板已下载')
  } catch (err) {
    ElMessage.error('下载模板失败：' + (err.message || '网络错误'))
  }
}

function triggerFileSelect() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.xlsx,.xls'
  input.style.display = 'none'
  input.addEventListener('change', (e) => {
    const file = e.target?.files?.[0]
    if (file) selectedFile.value = file
    document.body.removeChild(input)
  })
  document.body.appendChild(input)
  input.click()
}

function handleDrop(e) {
  isDragover.value = false
  const file = e.dataTransfer?.files?.[0]
  if (!file) return
  const ext = file.name.split('.').pop().toLowerCase()
  if (ext !== 'xlsx' && ext !== 'xls') {
    ElMessage.warning('仅支持 .xlsx 或 .xls 格式')
    return
  }
  selectedFile.value = file
}

async function handleImport() {
  if (!selectedFile.value) return
  importing.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const res = await http.post('/opportunities/import', formData, { timeout: 60000 })
    const data = res.data
    if (data.errors?.length > 0) {
      const msg = data.message + '\n\n' + data.errors.slice(0, 10).join('\n')
      ElMessageBox.alert(msg, '导入结果', { type: 'warning', dangerouslyUseHTMLString: false })
    } else {
      ElMessage.success(data.message)
    }
    visible.value = false
    emit('imported')
  } catch (err) {
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) {
      ElMessage.error(detail.map(d => d.msg || d).join('; '))
    } else if (detail) {
      ElMessage.error(`导入失败：${detail}`)
    } else {
      ElMessage.error(`导入失败：${err.message || '网络错误'}`)
    }
  } finally {
    importing.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.import-body { padding: 8px 0; }
.template-section {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.template-hint {
  font-size: 13px;
  color: var(--ds-text-subtle);
}
.upload-zone {
  border: 2px dashed var(--ds-border);
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #FAFBFC;
}
.upload-zone:hover {
  border-color: var(--ds-primary);
  background: var(--ds-primary-subtle);
}
.upload-zone.upload-dragover {
  border-color: var(--ds-primary);
  background: var(--ds-primary-subtle);
  transform: scale(1.01);
}
.upload-zone.upload-has-file {
  border-style: solid;
  border-color: var(--ds-primary);
  background: #F0F5FF;
}
.upload-icon { margin-bottom: 12px; color: var(--ds-text-subtle); }
.upload-text { font-size: 14px; color: var(--ds-text); margin: 0 0 4px; }
.upload-text em { color: var(--ds-primary); font-style: normal; font-weight: 500; }
.upload-text.file-name { font-weight: 600; color: var(--ds-primary); }
.upload-hint { font-size: 12px; color: var(--ds-text-subtle); margin: 0; }
.upload-hint.file-size { color: var(--ds-text-subtle); }
</style>
