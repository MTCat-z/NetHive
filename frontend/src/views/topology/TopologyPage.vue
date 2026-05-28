<template>
  <div class="topology-page">
    <!-- 工具栏 -->
    <el-card shadow="never" style="margin-bottom:12px">
      <el-row :gutter="12" align="middle">
        <el-col :span="8">
          <el-input v-model="discoverSubnet" placeholder="扫描子网 如 192.168.1.0/24" style="width:220px" />
          <el-button type="primary" style="margin-left:8px" :loading="discovering" @click="startDiscover">自动发现</el-button>
        </el-col>
        <el-col :span="8">
          <el-button @click="addManualNode">添加节点</el-button>
          <el-button @click="addManualEdge">添加连线</el-button>
          <el-select v-model="layoutType" style="width:120px;margin-left:8px" @change="relayout">
            <el-option label="层次布局" value="dagre" /><el-option label="力导向" value="force" /><el-option label="环形" value="circular" />
          </el-select>
        </el-col>
        <el-col :span="8" style="text-align:right">
          <el-button size="small" @click="loadGraph">刷新</el-button>
          <el-tag v-if="nodes.length" style="margin-left:8px">节点: {{ nodes.length }}</el-tag>
          <el-tag v-if="edges.length" style="margin-left:4px">连线: {{ edges.length }}</el-tag>
        </el-col>
      </el-row>
    </el-card>
    <!-- 主区域 -->
    <el-row :gutter="12">
      <!-- 画布 -->
      <el-col :span="18">
        <el-card shadow="never" body-style="padding:0">
          <div ref="graphDom" class="graph-container"></div>
        </el-card>
      </el-col>
      <!-- 右侧面板 -->
      <el-col :span="6">
        <!-- 发现任务状态 -->
        <el-card shadow="never" style="margin-bottom:12px">
          <template #header><span style="font-weight:600">发现任务</span></template>
          <div v-if="!tasks.length" style="color:#999;font-size:13px">暂无任务</div>
          <div v-for="t in tasks" :key="t.id" style="margin-bottom:8px;padding:8px;background:#fafafa;border-radius:4px">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:13px">{{ t.target_subnet }}</span>
              <el-button size="small" type="danger" link @click="deleteTask(t)" :disabled="t.status==='running'">删除</el-button>
            </div>
            <el-progress :percentage="t.progress" :status="t.status==='completed'?'success':t.status==='failed'?'exception':''" :stroke-width="6" style="margin:4px 0" />
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:12px;color:#999">节点: {{ t.nodes_discovered }} | 连线: {{ t.edges_inferred }}</span>
              <el-tag v-if="t.status==='failed'" size="small" type="danger" style="font-size:11px" :title="t.error_message">失败</el-tag>
              <el-tag v-else-if="t.status==='running'" size="small" type="warning" style="font-size:11px">运行中</el-tag>
              <el-tag v-else-if="t.status==='completed'" size="small" type="success" style="font-size:11px">完成</el-tag>
              <el-tag v-else size="small" style="font-size:11px">{{ t.status }}</el-tag>
            </div>
            <div v-if="t.status==='failed' && t.error_message" style="font-size:11px;color:#f56c6c;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" :title="t.error_message">{{ t.error_message }}</div>
          </div>
        </el-card>
        <!-- 节点详情 -->
        <el-card shadow="never" v-if="selectedNode">
          <template #header><span style="font-weight:600">节点详情</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="名称">{{ selectedNode.name }}</el-descriptions-item>
            <el-descriptions-item label="IP">{{ selectedNode.ip_address || '-' }}</el-descriptions-item>
            <el-descriptions-item label="MAC">{{ selectedNode.mac_address || '-' }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ selectedNode.device_type }}</el-descriptions-item>
            <el-descriptions-item label="厂商">{{ selectedNode.vendor || '-' }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ selectedNode.is_manual ? '手动' : '自动发现' }}</el-descriptions-item>
          </el-descriptions>
          <div style="margin-top:12px;display:flex;gap:8px">
            <el-button size="small" type="primary" @click="importNode(selectedNode)" v-if="!selectedNode.asset_id">导入资产</el-button>
            <el-button size="small" type="danger" @click="deleteNode(selectedNode)">删除</el-button>
          </div>
        </el-card>
        <!-- 边详情 -->
        <el-card shadow="never" v-if="selectedEdge" style="margin-top:12px">
          <template #header><span style="font-weight:600">连线详情</span></template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="类型">{{ selectedEdge.link_type }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ selectedEdge.is_manual ? '手动' : '自动推断' }}</el-descriptions-item>
          </el-descriptions>
          <el-button size="small" type="danger" style="margin-top:8px" @click="deleteEdge(selectedEdge)">删除连线</el-button>
        </el-card>
      </el-col>
    </el-row>
    <!-- 添加节点对话框 -->
    <el-dialog v-model="nodeDlg" title="添加节点" width="440px">
      <el-form :model="nodeForm" label-width="80px">
        <el-form-item label="名称"><el-input v-model="nodeForm.name" /></el-form-item>
        <el-form-item label="IP"><el-input v-model="nodeForm.ip_address" placeholder="可选" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="nodeForm.device_type" style="width:100%"><el-option v-for="t in ['router','switch','server','firewall','ap','endpoint','unknown']" :key="t" :label="t" :value="t" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="nodeDlg=false">取消</el-button><el-button type="primary" @click="submitNode">确定</el-button></template>
    </el-dialog>
    <!-- 添加连线对话框 -->
    <el-dialog v-model="edgeDlg" title="添加连线" width="440px">
      <el-form :model="edgeForm" label-width="80px">
        <el-form-item label="起始节点"><el-select v-model="edgeForm.source_node_id" style="width:100%"><el-option v-for="n in nodes" :key="n.id" :label="`${n.name} (${n.ip_address||''})` " :value="n.id" /></el-select></el-form-item>
        <el-form-item label="目标节点"><el-select v-model="edgeForm.target_node_id" style="width:100%"><el-option v-for="n in nodes" :key="n.id" :label="`${n.name} (${n.ip_address||''})` " :value="n.id" /></el-select></el-form-item>
        <el-form-item label="连线类型"><el-select v-model="edgeForm.link_type" style="width:100%"><el-option v-for="t in ['ethernet','wifi','fiber','uplink','logical']" :key="t" :label="t" :value="t" /></el-select></el-form-item>
      </el-form>
      <template #footer><el-button @click="edgeDlg=false">取消</el-button><el-button type="primary" @click="submitEdge">确定</el-button></template>
    </el-dialog>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { topologyApi } from '@/api'

const graphDom = ref(null)
const nodes = ref([])
const edges = ref([])
const tasks = ref([])
const discovering = ref(false)
const discoverSubnet = ref('')
const layoutType = ref('dagre')
const selectedNode = ref(null)
const selectedEdge = ref(null)
const nodeDlg = ref(false)
const edgeDlg = ref(false)
const nodeForm = reactive({ name: '', ip_address: '', device_type: 'server' })
const edgeForm = reactive({ source_node_id: null, target_node_id: null, link_type: 'ethernet' })

let graph = null
let pollTimer = null

// 节点图标映射
const iconMap = { router: 'diamond', switch: 'rect', server: 'circle', firewall: 'triangle', ap: 'circle', endpoint: 'circle', unknown: 'circle' }
const colorMap = { router: '#f56c6c', switch: '#e6a23c', server: '#409eff', firewall: '#909399', ap: '#67c23a', endpoint: '#909399', unknown: '#c0c4cc' }

function nodeToG6(n) {
  const color = colorMap[n.device_type] || '#c0c4cc'
  const style = {
    labelText: `${n.name}\n${n.ip_address || ''}`.trim(),
    labelFill: '#333',
    labelFontSize: 11,
    labelPlacement: 'bottom',
    labelOffsetY: 8,
    fill: color,
    stroke: '#333',
    lineWidth: 1,
    size: 36,
  }
  // 仅在有有效非零坐标时设置，让布局引擎自动计算其余情况
  if (n.position_x && n.position_x !== 0) style.x = n.position_x
  if (n.position_y && n.position_y !== 0) style.y = n.position_y
  return {
    id: `node-${n.id}`,
    data: { _raw: n },
    style,
    type: 'circle',
  }
}
function edgeToG6(e) {
  return {
    id: `edge-${e.id}`,
    source: `node-${e.source_node_id}`,
    target: `node-${e.target_node_id}`,
    data: { _raw: e },
    style: {
      stroke: e.style === 'dashed' ? '#aaa' : '#666',
      lineDash: e.style === 'dashed' ? [5, 3] : undefined,
      lineWidth: 1.5,
    },
  }
}

async function loadGraph() {
  try {
    const data = await topologyApi.getGraph({})
    nodes.value = data.nodes || []
    edges.value = data.edges || []
    await nextTick()
    renderGraph()
  } catch (e) {
    console.error('加载拓扑图失败', e)
  }
}

async function renderGraph() {
  if (!graphDom.value) return

  // 容器尺寸校验
  const w = graphDom.value.clientWidth
  const h = graphDom.value.clientHeight || 540
  if (w <= 0) {
    console.warn('拓扑图容器宽度为 0，跳过渲染')
    return
  }

  // 动态导入 G6
  let G6
  try {
    G6 = await import('@antv/g6')
  } catch (e) {
    console.error('G6 加载失败', e)
    graphDom.value.innerHTML = '<div style="padding:40px;text-align:center;color:#999">请安装 @antv/g6 依赖: <code>npm install @antv/g6</code></div>'
    return
  }

  if (graph) { graph.destroy(); graph = null }

  const g6Nodes = nodes.value.map(nodeToG6)
  const g6Edges = edges.value.map(edgeToG6)

  // 无数据时显示空状态提示
  if (!g6Nodes.length) {
    graphDom.value.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;font-size:14px">暂无拓扑数据，请添加节点或执行自动发现</div>'
    return
  }

  try {
    // G6 v5 API
    const layoutConfig = layoutType.value === 'dagre'
      ? { type: 'dagre', rankdir: 'TB', nodesep: 40, ranksep: 60 }
      : layoutType.value === 'force'
      ? { type: 'd3-force', linkDistance: 120, nodeSize: 40 }
      : { type: 'circular', radius: 200 }

    graph = new G6.Graph({
      container: graphDom.value,
      width: w,
      height: Math.max(500, h),
      autoFit: 'view',
      padding: 40,
      data: { nodes: g6Nodes, edges: g6Edges },
      layout: layoutConfig,
      behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element', 'click-select'],
      animation: false,
    })

    await graph.render()

    // 事件绑定
    graph.on('node:click', (evt) => {
      const id = evt.target?.id
      if (!id) return
      const nodeData = graph.getNodeData(id)
      selectedNode.value = nodeData?.data?._raw || null
      selectedEdge.value = null
    })
    graph.on('edge:click', (evt) => {
      const id = evt.target?.id
      if (!id) return
      const edgeData = graph.getEdgeData(id)
      selectedEdge.value = edgeData?.data?._raw || null
      selectedNode.value = null
    })
    graph.on('canvas:click', () => {
      selectedNode.value = null
      selectedEdge.value = null
    })
    graph.on('node:dragend', async (evt) => {
      const id = evt.target?.id
      if (!id) return
      const nodeData = graph.getNodeData(id)
      if (nodeData?.data?._raw) {
        const pos = graph.getNodePosition(id)
        try {
          await topologyApi.updateNodePosition(nodeData.data._raw.id, { position_x: pos[0], position_y: pos[1] })
        } catch (err) { /* ignore */ }
      }
    })
  } catch (e) {
    console.error('G6 渲染失败', e)
    graphDom.value.innerHTML = `<div style="padding:40px;text-align:center;color:#f56c6c">拓扑图渲染失败: ${e.message || e}</div>`
  }
}

function relayout() { loadGraph() }

async function startDiscover() {
  if (!discoverSubnet.value) return ElMessage.warning('请输入子网')
  discovering.value = true
  try {
    const task = await topologyApi.discover({ target_subnet: discoverSubnet.value })
    ElMessage.success('发现任务已提交')
    tasks.value.unshift(task)
    pollTasks()
  } finally { discovering.value = false }
}

function pollTasks() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    let allDone = true
    for (let i = 0; i < tasks.value.length; i++) {
      if (tasks.value[i].status === 'pending' || tasks.value[i].status === 'running') {
        try {
          const t = await topologyApi.getDiscoveryTask(tasks.value[i].id)
          tasks.value[i] = t
        } catch (e) { /* ignore */ }
        allDone = false
      }
    }
    if (allDone) {
      clearInterval(pollTimer); pollTimer = null
      loadGraph()
    }
  }, 3000)
}

function addManualNode() { Object.assign(nodeForm, { name: '', ip_address: '', device_type: 'server' }); nodeDlg.value = true }
async function submitNode() {
  if (!nodeForm.name) return ElMessage.warning('请输入名称')
  await topologyApi.addNode({ ...nodeForm, position_x: 200 + Math.random() * 400, position_y: 200 + Math.random() * 300 })
  ElMessage.success('节点已添加'); nodeDlg.value = false; loadGraph()
}

function addManualEdge() { Object.assign(edgeForm, { source_node_id: null, target_node_id: null, link_type: 'ethernet' }); edgeDlg.value = true }
async function submitEdge() {
  if (!edgeForm.source_node_id || !edgeForm.target_node_id) return ElMessage.warning('请选择节点')
  await topologyApi.addEdge(edgeForm)
  ElMessage.success('连线已添加'); edgeDlg.value = false; loadGraph()
}

async function deleteNode(node) {
  await ElMessageBox.confirm('确定删除该节点及其连线?', '确认', { type: 'warning' })
  await topologyApi.deleteNode(node.id)
  ElMessage.success('已删除'); selectedNode.value = null; loadGraph()
}
async function deleteEdge(edge) {
  await topologyApi.deleteEdge(edge.id)
  ElMessage.success('已删除'); selectedEdge.value = null; loadGraph()
}
async function deleteTask(task) {
  try {
    await ElMessageBox.confirm(`确定删除该发现任务及其发现的节点和连线？`, '确认', { type: 'warning' })
    await topologyApi.deleteDiscoveryTask(task.id)
    ElMessage.success('任务已删除')
    tasks.value = tasks.value.filter(t => t.id !== task.id)
    loadGraph()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
async function importNode(node) {
  await topologyApi.importNode(node.id, { name: node.name, device_type: node.device_type })
  ElMessage.success('已导入资产管理'); loadGraph()
}

// 从后端加载历史发现任务
async function loadTasks() {
  try {
    const r = await topologyApi.listDiscoveryTasks({ size: 20 })
    tasks.value = r.items || []
    // 如果有进行中的任务，启动轮询
    if (tasks.value.some(t => t.status === 'pending' || t.status === 'running')) {
      pollTasks()
    }
  } catch (e) {
    console.error('加载发现任务列表失败', e)
  }
}

function handleResize() {
  if (graph) {
    try {
      graph.resize(graphDom.value?.clientWidth, Math.max(500, graphDom.value?.clientHeight || 540))
    } catch (e) { /* ignore */ }
  }
}

onMounted(() => {
  loadGraph()
  loadTasks()
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  if (graph) { graph.destroy(); graph = null }
  window.removeEventListener('resize', handleResize)
})
</script>
<style scoped>
.topology-page { height: 100%; }
.graph-container { width: 100%; height: 540px; background: #fafafa; border-radius: 4px; position: relative; overflow: hidden; }
</style>
