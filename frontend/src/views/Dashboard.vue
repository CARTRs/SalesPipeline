<template>
  <div v-loading="loading">
    <div class="page-head"><h2>数据看板</h2></div>

    <!-- 统计卡片（Plane 风格：顶部分色条 + 悬浮上移） -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="(s, idx) in statsCards" :key="s.label">
        <el-card shadow="never" class="stat-card anim-fade-in-up" :class="'delay-' + (idx + 1)">
          <div class="stat-accent" :style="{background: s.color}"></div>
          <div class="stat-value">{{ s.value }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 优先级分布 -->
      <el-col :span="8">
        <el-card shadow="never" class="chart-card">
          <template #header>优先级分布</template>
          <div ref="priorityChartRef" style="height:260px" />
        </el-card>
      </el-col>
      <!-- 状态分布 -->
      <el-col :span="8">
        <el-card shadow="never" class="chart-card">
          <template #header>商机状态分布</template>
          <div ref="statusChartRef" style="height:260px" />
        </el-card>
      </el-col>
      <!-- AI风险等级 -->
      <el-col :span="8">
        <el-card shadow="never" class="chart-card">
          <template #header>AI 风险等级</template>
          <div ref="riskChartRef" style="height:260px" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top:16px">
      <!-- 支局统计 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>支局商机统计</template>
          <div ref="branchChartRef" style="height:280px" />
        </el-card>
      </el-col>
      <!-- 近期活动 -->
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>近期进度更新</template>
          <div v-if="recentItems.length === 0" class="chart-empty">暂无数据</div>
          <div v-else class="recent-list">
            <div v-for="item in recentItems" :key="item.id" class="recent-item">
              <div class="recent-opp">{{ item.opportunity_name }}</div>
              <div class="recent-meta">{{ item.updater_role }} - {{ item.updater_name }} · {{ item.created_at?.slice(0,10) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 紧急概览 -->
    <el-card shadow="never" class="chart-card" style="margin-top:16px">
      <template #header>需关注商机</template>
      <el-row :gutter="16">
        <el-col :span="8" v-for="g in urgentGroups" :key="g.title">
          <div class="urgent-group">
            <div class="urgent-title">
              <el-tag :type="g.type" size="small" round>{{ g.count }}</el-tag>
              <span>{{ g.title }}</span>
            </div>
            <div v-if="g.items?.length" class="urgent-list">
              <div v-for="item in g.items.slice(0,5)" :key="item.id" class="urgent-item" @click="$router.push(`/opportunities/${item.id}`)">
                {{ item.opportunity_name || item.name }}
              </div>
            </div>
            <div v-else class="chart-empty">暂无</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'

const router = useRouter()
const loading = ref(true)
const statsCards = ref([])
const recentItems = ref([])
const urgentGroups = ref([])

const priorityChartRef = ref(null)
const statusChartRef = ref(null)
const riskChartRef = ref(null)
const branchChartRef = ref(null)

async function load() {
  try {
    const [statsRes, priorityRes, statusRes, riskRes, recentRes, urgentRes, branchRes] = await Promise.all([
      http.get('/dashboard/stats'),
      http.get('/dashboard/priority-distribution'),
      http.get('/dashboard/status-distribution'),
      http.get('/dashboard/risk-overview'),
      http.get('/dashboard/recent-activity', { params: { limit: 10 } }),
      http.get('/dashboard/urgent-overview'),
      http.get('/dashboard/branch-stats'),
    ])
    const stats = statsRes.data
    statsCards.value = [
      { label: '总商机数', value: stats.total_opportunities || 0, color: '#0052CC' },
      { label: '待签约金额(万)', value: stats.pending_amount != null ? Number(stats.pending_amount).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '—', color: '#36B37E' },
      { label: '关闭商机', value: stats.closed_opportunities || 0, color: '#FFAB00' },
      { label: '未推进超期', value: stats.no_push_count || 0, color: '#DE350B' },
    ]
    recentItems.value = recentRes.data.items || []
    urgentGroups.value = [
      { title: '未推进超期', type: 'danger', count: stats.no_push_count || 0, items: urgentRes.data?.no_push_opportunities || [] },
      { title: '招标临近', type: 'warning', count: stats.bid_approaching_count || 0, items: urgentRes.data?.bid_approaching_opportunities || [] },
      { title: '检测到竞争对手', type: 'danger', count: stats.competitor_detected_count || 0, items: urgentRes.data?.competitor_detected_opportunities || [] },
    ]

    await nextTick()
    renderCharts(priorityRes.data, statusRes.data, riskRes.data, branchRes.data)
  } finally {
    loading.value = false
  }
}

function renderCharts(priorityData, statusData, riskData, branchData) {
  if (typeof window !== 'undefined' && window.echarts) {
    const e = window.echarts
    const colors = ['#DE350B', '#00B8D9', '#FFAB00', '#403294']

    // Priority
    if (priorityChartRef.value) {
      const p = e.init(priorityChartRef.value)
      p.setOption({
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie', radius: ['40%', '70%'],
          data: (priorityData?.items || []).map((d, i) => ({
            name: { 1: '紧急', 2: '高', 3: '中', 4: '低' }[d.priority_level] || d.priority_level,
            value: d.count,
            itemStyle: { color: colors[i] || '#C1C7D0' },
          })),
          label: { show: true, formatter: '{b}: {c}' },
        }],
      })
    }

    // Status
    if (statusChartRef.value) {
      const s = e.init(statusChartRef.value)
      s.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: (statusData?.items || []).map(d => d.opportunity_status || '未知') },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: (statusData?.items || []).map(d => d.count), itemStyle: { color: '#0052CC' } }],
      })
    }

    // Risk
    if (riskChartRef.value) {
      const r = e.init(riskChartRef.value)
      r.setOption({
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie',
          data: (riskData?.items || []).map(d => ({
            name: d.risk_level || '未知',
            value: d.count,
            itemStyle: {
              color: { critical: '#DE350B', high: '#FF8B00', medium: '#FFAB00', low: '#36B37E' }[d.risk_level] || '#C1C7D0',
            },
          })),
          label: { show: true, formatter: '{b}: {c}' },
        }],
      })
    }

    // Branch bar chart
    if (branchChartRef.value) {
      const b = e.init(branchChartRef.value)
      const items = (branchData?.items || []).slice(0, 10)
      b.setOption({
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: items.map(d => d.branch_office || '未知'), axisLabel: { rotate: 30 } },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: items.map(d => d.opportunity_count || 0), itemStyle: { color: '#00B8D9' } }],
      })
    }
  }
}

onMounted(load)
</script>

<style scoped>
.page-head { margin-bottom:20px; }
.page-head h2 { font-size:20px; font-weight:600; color:var(--ds-text); margin:0; }
.stats-row { margin-bottom:16px; }

/* Plane 风格：悬浮上移 + 阴影效果 */
.stat-card {
  text-align: center;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  border-top: none !important;
}
.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(9,30,66,0.2), 0 0 1px rgba(9,30,66,0.3);
}
.stat-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  border-radius: 0;
}
.stat-value { font-size:28px; font-weight:600; color:var(--ds-text); padding-top: 8px; }
.stat-label { font-size:13px; color:var(--ds-text-subtle); margin-top:4px; }

/* Chart cards with subtle hover lift */
.chart-card {
  margin-bottom:0;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.chart-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(9,30,66,0.18), 0 0 1px rgba(9,30,66,0.3);
}
.chart-empty { text-align:center; padding:40px; color:var(--ds-text-subtle); font-size:13px; }
.recent-list { max-height:280px; overflow-y:auto; }
.recent-item {
  padding:10px 12px;
  border-bottom:1px solid var(--ds-border);
  cursor:pointer;
  border-radius: 3px;
  transition: background 0.15s ease;
}
.recent-item:hover { background: #EBECF0; }
.recent-item:last-child { border-bottom:none; }
.recent-opp { font-size:14px; font-weight:500; color:var(--ds-text); }
.recent-meta { font-size:12px; color:var(--ds-text-subtle); margin-top:2px; }
.urgent-group { padding:8px; }
.urgent-title { display:flex; align-items:center; gap:8px; margin-bottom:8px; font-weight:600; font-size:14px; }
.urgent-list { max-height:200px; overflow-y:auto; }
.urgent-item {
  padding:6px 8px;
  font-size:13px;
  cursor:pointer;
  border-radius:3px;
  color:var(--ds-text-link);
  transition: background 0.15s ease;
}
.urgent-item:hover { background:#DEEBFF; }
</style>
