<template>
  <div class="dashboard" v-loading="loading">
    <!-- 顶部标题栏 -->
    <div class="dashboard-header">
      <div class="header-content">
        <h1>{{ dashboardTitle }}</h1>
        <div class="header-date">数据更新日期：{{ currentDate }}</div>
      </div>
    </div>

    <div class="dashboard-container">
      <!-- 总览卡片 -->
      <div class="overview">
        <div class="card card-red">
          <div class="icon">商</div>
          <div class="label">商机总数</div>
          <div class="value">{{ stats.total_opportunities || 0 }}</div>
          <div class="unit">个</div>
        </div>
        <div class="card card-orange">
          <div class="icon">金</div>
          <div class="label">预测总金额</div>
          <div class="value">{{ formatAmount(stats.pending_amount) }}</div>
          <div class="unit">万元</div>
        </div>
        <div class="card card-green">
          <div class="icon">签</div>
          <div class="label">已签约商机</div>
          <div class="value">{{ stats.closed_opportunities || 0 }}</div>
          <div class="unit">个</div>
        </div>
        <div class="card card-blue">
          <div class="icon">推</div>
          <div class="label">本周推进商机数</div>
          <div class="value">{{ stats.weekly_progress_count || 0 }}</div>
          <div class="unit">个</div>
        </div>
        <div class="card card-dark">
          <div class="icon">滞</div>
          <div class="label">周未推进商机数</div>
          <div class="value">{{ stats.no_push_opportunity_count || 0 }}</div>
          <div class="unit">个</div>
        </div>
      </div>

      <!-- 第一行：状态+优先级 -->
      <div class="charts-row row-2">
        <div class="chart-box">
          <h3>商机状态分布</h3>
          <div ref="statusChartRef" class="chart-container"></div>
        </div>
        <div class="chart-box">
          <h3>优先级分布</h3>
          <div ref="priorityChartRef" class="chart-container"></div>
        </div>
      </div>

      <!-- 第二行：支局 -->
      <div class="charts-row row-1">
        <div class="chart-box">
          <h3>支局商机响应等级占比</h3>
          <div ref="branchChartRef" class="chart-container" style="height:360px;"></div>
        </div>
      </div>

      <!-- 预警表格 -->
      <div class="charts-row row-2">
        <div class="table-box">
          <h3>300万以上大单跟踪 (TOP15)</h3>
          <div class="scroll-wrapper" ref="scrollWrapperRef" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
            <table>
              <thead>
                <tr>
                  <th>商机名称</th>
                  <th>金额(万)</th>
                  <th>状态</th>
                  <th>支局</th>
                </tr>
              </thead>
              <tbody ref="scrollBodyRef">
                <tr v-for="(item, index) in largeAmountList" :key="item.id" :data-index="index">
                  <td>{{ item.opportunity_name }}</td>
                  <td>{{ item.predicted_amount }}</td>
                  <td><span :class="getStatusBadgeClass(item.opportunity_status)">{{ item.opportunity_status || '-' }}</span></td>
                  <td>{{ item.branch_office || '-' }}</td>
                </tr>
                <tr v-if="largeAmountList.length === 0">
                  <td colspan="4" class="empty-row">暂无数据</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="table-box">
          <h3>未推进超30天预警 (TOP10)</h3>
          <table>
            <thead>
              <tr>
                <th>商机名称</th>
                <th>未推进天数</th>
                <th>支局</th>
                <th>状态</th>
                <th>金额(万)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in noPushWarningList" :key="item.id" class="warn-row">
                <td>{{ item.opportunity_name }}</td>
                <td><span class="badge badge-red">{{ item.no_push_days }}天</span></td>
                <td>{{ item.branch_office || '-' }}</td>
                <td><span :class="getStatusBadgeClass(item.opportunity_status)">{{ item.opportunity_status || '-' }}</span></td>
                <td>{{ item.predicted_amount || '-' }}</td>
              </tr>
              <tr v-if="noPushWarningList.length === 0">
                <td colspan="5" class="empty-row">暂无预警数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import http from '../api/http'

const loading = ref(true)
const stats = ref({})
const statusData = ref([])
const priorityData = ref([])
const branchData = ref([])
const noPushWarningList = ref([])
const largeAmountList = ref([])

const statusChartRef = ref(null)
const priorityChartRef = ref(null)
const branchChartRef = ref(null)
const scrollWrapperRef = ref(null)
const scrollBodyRef = ref(null)

let scrollTimer = null
let scrollPaused = false

const currentDate = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
})

const dashboardTitle = computed(() => {
  const role = localStorage.getItem('user_role')
  const userName = localStorage.getItem('user_name')
  if (role === '管理员') return '余杭分公司产数大单商机看板'
  if (userName === '政务') return '余杭政务支局-产数大单商机看板'
  return '大单商机数据看板'
})

function formatAmount(amount) {
  if (!amount) return '0'
  return Number(amount).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 1 })
}

const STATUS_COLOR_MAP = [
  { category: '需求挖掘',       statuses: ['需求挖掘'],       color: '#9C27B0', badge: 'badge-purple' },
  { category: '解决方案',       statuses: ['解决方案'],       color: '#2196F3', badge: 'badge-blue' },
  { category: '商务谈判/招投标', statuses: ['商务谈判/招投标'], color: '#FF9800', badge: 'badge-orange' },
  { category: '签约',           statuses: ['签约'],           color: '#4CAF50', badge: 'badge-green' },
]

function getStatusColor(status) {
  if (!status) return '#7F8C8D'
  const entry = STATUS_COLOR_MAP.find(e => e.statuses.includes(status))
  return entry ? entry.color : '#7F8C8D'
}

function getStatusBadgeClass(status) {
  if (!status) return 'badge badge-gray'
  const entry = STATUS_COLOR_MAP.find(e => e.statuses.includes(status))
  return entry ? `badge ${entry.badge}` : 'badge badge-gray'
}

async function loadData() {
  loading.value = true
  try {
    const [statsRes, statusRes, priorityRes, branchRes] = await Promise.all([
      http.get('/dashboard/stats'),
      http.get('/dashboard/status-distribution'),
      http.get('/dashboard/priority-distribution'),
      http.get('/dashboard/branch-stats'),
    ])

    stats.value = statsRes.data
    statusData.value = statusRes.data?.items || []
    priorityData.value = priorityRes.data?.items || []
    branchData.value = branchRes.data?.items || []

    // 加载大单和预警数据
    await loadLargeAmountData()
    await loadNoPushWarningData()

    await nextTick()
    renderCharts()
    startAutoScroll()
  } finally {
    loading.value = false
  }
}

function startAutoScroll() {
  stopAutoScroll()
  const wrapper = scrollWrapperRef.value
  const body = scrollBodyRef.value
  if (!wrapper || !body || largeAmountList.value.length <= 8) return

  const rowHeight = 40
  const visibleRows = 8
  const totalHeight = largeAmountList.value.length * rowHeight
  let scrollTop = 0

  scrollTimer = setInterval(() => {
    if (scrollPaused) return
    scrollTop += rowHeight
    if (scrollTop >= totalHeight - visibleRows * rowHeight) {
      scrollTop = 0
    }
    wrapper.scrollTop = scrollTop
  }, 2000)
}

function stopAutoScroll() {
  if (scrollTimer) {
    clearInterval(scrollTimer)
    scrollTimer = null
  }
}

function onMouseEnter() {
  scrollPaused = true
}

function onMouseLeave() {
  scrollPaused = false
}

async function loadLargeAmountData() {
  try {
    const res = await http.get('/opportunities', {
      params: { page: 1, page_size: 15, sort_by: 'predicted_amount', sort_order: 'desc' }
    })
    largeAmountList.value = (res.data.items || []).filter(item => item.predicted_amount >= 300)
  } catch (e) {
    console.error('加载大单数据失败', e)
  }
}

async function loadNoPushWarningData() {
  try {
    const res = await http.get('/opportunities', {
      params: { page: 1, page_size: 10, sort_by: 'no_push_days', sort_order: 'desc' }
    })
    noPushWarningList.value = (res.data.items || []).filter(item => item.no_push_days >= 30)
  } catch (e) {
    console.error('加载预警数据失败', e)
  }
}

function renderCharts() {
  if (typeof window === 'undefined' || !window.echarts) return
  const e = window.echarts
  // 商机状态饼图
  if (statusChartRef.value) {
    const chart = e.init(statusChartRef.value)
    const statusChartData = statusData.value.map(d => ({
      name: d.opportunity_status || '未知',
      value: d.count,
      itemStyle: { color: getStatusColor(d.opportunity_status) }
    }))
    chart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}个 ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 12 } },
      series: [{
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '45%'],
        label: { formatter: '{b}\n{d}%', fontSize: 11 },
        data: statusChartData,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 }
      }]
    })
  }

  // 优先级分布
  if (priorityChartRef.value) {
    const chart = e.init(priorityChartRef.value)
    chart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c}个 ({d}%)' },
      legend: { bottom: 0, textStyle: { fontSize: 12 } },
      series: [{
        type: 'pie',
        radius: ['35%', '65%'],
        center: ['50%', '45%'],
        label: { formatter: '{b}\n{c}个', fontSize: 12 },
        data: priorityData.value.map(d => ({
          name: { 1: '高', 2: '中', 3: '低' }[d.priority_level] || '未知',
          value: d.count
        })),
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        color: ['#E67E22', '#2980B9', '#27AE60']
      }]
    })
  }

  // 支局分布堆叠柱状图
  if (branchChartRef.value) {
    const chart = e.init(branchChartRef.value)
    const items = branchData.value.slice(0, 15)
    const reversed = items.slice().reverse()

    // 根据数据量动态调整柱子宽度，避免单条时过宽
    const barWidthVal = reversed.length <= 3 ? '25%' : '65%'

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function(params) {
          let result = params[0].axisValue + '<br/>'
          let total = 0
          params.forEach(p => {
            total += p.value
          })
          params.forEach(p => {
            const pct = total > 0 ? ((p.value / total) * 100).toFixed(1) : 0
            result += `${p.marker} ${p.seriesName}: ${p.value}个 (${pct}%)<br/>`
          })
          result += `<strong>合计: ${total}个</strong>`
          return result
        }
      },
      legend: {
        data: ['高', '中', '低'],
        top: 0,
        textStyle: { fontSize: 11 }
      },
      grid: { left: 100, right: 30, bottom: 30, top: 40 },
      xAxis: { type: 'value' },
      yAxis: {
        type: 'category',
        data: reversed.map(d => d.branch_office || '未知'),
        axisLabel: { fontSize: 11 }
      },
      series: [
        {
          name: '高',
          type: 'bar',
          stack: 'total',
          data: reversed.map(d => d.high_count || 0),
          itemStyle: { color: '#E67E22' },
          barWidth: barWidthVal
        },
        {
          name: '中',
          type: 'bar',
          stack: 'total',
          data: reversed.map(d => d.medium_count || 0),
          itemStyle: { color: '#2980B9' },
          barWidth: barWidthVal
        },
        {
          name: '低',
          type: 'bar',
          stack: 'total',
          data: reversed.map(d => d.low_count || 0),
          itemStyle: { color: '#27AE60' },
          barWidth: barWidthVal
        }
      ]
    })
  }
}

onMounted(loadData)

onUnmounted(() => {
  stopAutoScroll()
})

// 响应式
window.addEventListener('resize', () => {
  const charts = [statusChartRef, priorityChartRef, branchChartRef]
  charts.forEach(ref => {
    if (ref.value) {
      const chart = window.echarts?.getInstanceByDom(ref.value)
      chart?.resize()
    }
  })
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f0f2f5;
}

/* 顶部标题栏 */
.dashboard-header {
  background: linear-gradient(135deg, #C00000 0%, #8B0000 100%);
  color: white;
  padding: 20px 32px;
  text-align: center;
  box-shadow: 0 2px 12px rgba(0,0,0,0.15);
  border-radius: 10px;
  margin: 16px 16px 0 16px;
}
.header-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.dashboard-header h1 {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 2px;
  margin: 0;
}
.header-date {
  font-size: 14px;
  opacity: 0.85;
}

.dashboard-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px;
}

/* 总览卡片 */
.overview {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.card {
  background: white;
  border-radius: 10px;
  padding: 20px 16px;
  text-align: center;
  box-shadow: 0 1px 6px rgba(0,0,0,0.08);
  transition: transform 0.2s;
  position: relative;
  overflow: hidden;
}
.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.card .icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 10px;
  font-size: 18px;
  color: white;
}
.card .label {
  font-size: 13px;
  color: #888;
  margin-bottom: 6px;
}
.card .value {
  font-size: 28px;
  font-weight: 700;
}
.card .unit {
  font-size: 13px;
  color: #888;
  margin-top: 2px;
}
.card-red .value { color: #C00000; }
.card-orange .value { color: #E67E22; }
.card-green .value { color: #27AE60; }
.card-blue .value { color: #2980B9; }
.card-purple .value { color: #8E44AD; }
.card-dark .value { color: #2C3E50; }
.card-red .icon { background: #C00000; }
.card-orange .icon { background: #E67E22; }
.card-green .icon { background: #27AE60; }
.card-blue .icon { background: #2980B9; }
.card-purple .icon { background: #8E44AD; }
.card-dark .icon { background: #2C3E50; }

/* 图表网格 */
.charts-row {
  display: grid;
  gap: 16px;
  margin-bottom: 20px;
}
.row-2 { grid-template-columns: 1fr 1fr; }
.row-3 { grid-template-columns: 1fr 1fr 1fr; }
.row-1 { grid-template-columns: 1fr; }
.chart-box {
  background: white;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.08);
}
.chart-box h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2C3E50;
  margin-bottom: 8px;
  padding-left: 10px;
  border-left: 3px solid #C00000;
}
.chart-container {
  width: 100%;
  height: 320px;
}

/* 预警/表格 */
.table-box {
  background: white;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.08);
  margin-bottom: 20px;
}
.table-box h3 {
  font-size: 15px;
  font-weight: 600;
  color: #2C3E50;
  margin-bottom: 12px;
  padding-left: 10px;
  border-left: 3px solid #C00000;
}
.table-box table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table-box th {
  background: #F8F9FA;
  color: #555;
  font-weight: 600;
  padding: 10px 12px;
  text-align: left;
  border-bottom: 2px solid #e8e8e8;
}
.table-box td {
  padding: 9px 12px;
  border-bottom: 1px solid #f0f0f0;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.table-box tr:hover {
  background: #FFF5F5;
}
.warn-row {
  background: #FFF8F0 !important;
}
.empty-row {
  text-align: center;
  color: #999;
  padding: 20px !important;
}

.scroll-wrapper {
  max-height: 360px;
  overflow-y: auto;
  scrollbar-width: thin;
}
.scroll-wrapper table {
  width: 100%;
}
.scroll-wrapper thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #F8F9FA;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}
.badge-red { background: #FDEDEC; color: #C00000; }
.badge-orange { background: #FEF5E7; color: #E67E22; }
.badge-green { background: #EAFAF1; color: #27AE60; }
.badge-blue { background: #EBF5FB; color: #2980B9; }
.badge-gray { background: #F2F3F4; color: #7F8C8D; }
.badge-purple { background: #F4ECF7; color: #8E44AD; }

@media (max-width: 1024px) {
  .overview { grid-template-columns: repeat(3, 1fr); }
  .row-2, .row-3 { grid-template-columns: 1fr; }
}
</style>
