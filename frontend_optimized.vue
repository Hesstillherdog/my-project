<template>
  <!-- 高级筛选面板 -->
  <div class="advanced-filter-panel" v-show="dialogVisible">
    <div class="advanced-filter-card">
      <div class="card-header">
        <h3 class="card-title">高级筛选</h3>
        <el-button type="text" @click="toggleFilterPanel" class="close-btn">
          <i class="el-icon-close"></i>
        </el-button>
      </div>
      
      <div class="card-content">
        <el-form :model="advancedFilters" label-position="top" class="filter-form">
          <el-row :gutter="35">
            <el-col :span="6" class="mb10" v-for="col in filterableColumns" :key="col.prop">
              <el-form-item :label="col.label" class="filter-item">
                <el-select
                  v-model="advancedFilters[col.prop]"
                  filterable
                  remote
                  :remote-method="(query) => loadFilterOptions(col.prop, query)"
                  :loading="filterOptionsLoading[col.prop]"
                  :placeholder="`请选择${col.label}`"
                  style="width: 180px;"
                  clearable
                >
                  <el-option
                    v-for="option in filterOptions[col.prop] || []"
                    :key="option"
                    :label="option || 'NULL'"
                    :value="option"
                  />
                </el-select>
              </el-form-item>
            </el-col>
            <el-form-item label="时间" class="filter-item">
              <el-date-picker
                v-model="advancedFilters.timeRange"
                type="datetimerange"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                start-placeholder="起始时间"
                end-placeholder="截止时间"
                style="width: 250px;"
                clearable
              />
            </el-form-item>
          </el-row>
        </el-form>
      </div>
      
      <div class="card-footer">
        <el-button @click="resetAdvancedFilter">重置</el-button>
        <el-button type="primary" @click="applyAdvancedFilter">确定</el-button>
      </div>
    </div>
  </div>

  <!-- 主界面 -->
  <div class="container">
    <div style="display: flex; gap: 10px; margin-bottom: 10px;">
      <el-input 
        v-model="searchKeyword" 
        placeholder="请输入关键词搜索" 
        :prefix-icon="Search" 
        style="width: 200px"
        @input="debounceSearch"
      />
      <el-button type="primary" @click="dialogVisible = !dialogVisible">高级筛选</el-button>
    </div>
    
    <div class="upload-container">
      <el-button plain type="primary" @click="batchProof" :disabled="selectedRows.length === 0">
        批量举证
      </el-button>
      <el-button plain type="warning" @click="batchApproval" :disabled="selectedRows.length === 0">
        批量审批
      </el-button>
    </div>
  </div>

  <!-- 虚拟表格 -->
  <div class="virtual-table-container" ref="tableContainer" @scroll="handleScroll">
    <!-- 表头 -->
    <div class="table-header" :style="{ width: tableWidth + 'px' }">
      <div class="table-row header-row">
        <div class="table-cell selection-cell">
          <el-checkbox v-model="selectAll" @change="handleSelectAll" />
        </div>
        <div 
          v-for="col in visibleColumns" 
          :key="col.prop" 
          class="table-cell"
          :style="{ width: col.width + 'px', minWidth: col.minWidth + 'px' }"
        >
          <div class="header-content">
            <span>{{ col.label }}</span>
            <div v-if="col.sortable" class="sort-icons" @click="toggleSort(col.prop)">
              <el-icon :class="{ active: sortBy === col.prop && sortOrder === 'asc' }">
                <CaretTop />
              </el-icon>
              <el-icon :class="{ active: sortBy === col.prop && sortOrder === 'desc' }">
                <CaretBottom />
              </el-icon>
            </div>
          </div>
        </div>
        <div class="table-cell action-cell" style="width: 120px;">操作</div>
      </div>
    </div>

    <!-- 虚拟表格主体 -->
    <div 
      class="table-body" 
      :style="{ 
        height: virtualHeight + 'px',
        width: tableWidth + 'px'
      }"
    >
      <!-- 占位空间 -->
      <div :style="{ height: offsetY + 'px' }"></div>
      
      <!-- 可见行 -->
      <div 
        v-for="(item, index) in visibleItems" 
        :key="item.id || startIndex + index"
        class="table-row data-row"
        :class="{ selected: selectedRows.includes(item.id) }"
        @click="toggleRowSelection(item)"
      >
        <div class="table-cell selection-cell">
          <el-checkbox 
            :model-value="selectedRows.includes(item.id)"
            @change="() => toggleRowSelection(item)"
          />
        </div>
        
        <div 
          v-for="col in visibleColumns" 
          :key="col.prop"
          class="table-cell"
          :style="{ width: col.width + 'px', minWidth: col.minWidth + 'px' }"
        >
          <!-- 状态标签 -->
          <el-tag 
            v-if="col.prop === 'ifViolation'" 
            :type="complianceType[item.ifViolation]" 
            effect="light"
          >
            {{ item.ifViolation }}
          </el-tag>
          <el-tag 
            v-else-if="col.prop === 'assignmentStatus'" 
            :type="statusType[item.assignmentStatus]" 
            effect="light"
          >
            {{ item.assignmentStatus }}
          </el-tag>
          <span v-else>{{ item[col.prop] || '-' }}</span>
        </div>
        
        <div class="table-cell action-cell" style="width: 120px;">
          <el-button link type="danger" size="small" @click.stop="addProof(item)">
            举证
          </el-button>
          <el-button link type="primary" size="small" @click.stop="addApproval(item)">
            审批
          </el-button>
        </div>
      </div>
      
      <!-- 底部占位空间 -->
      <div :style="{ height: (virtualHeight - offsetY - visibleItems.length * rowHeight) + 'px' }"></div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
  </div>

  <!-- 分页 -->
  <div class="demo-pagination-block">
    <el-pagination
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :page-sizes="[50, 100, 200, 500]"
      :total="totalCount"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="handleSizeChange"
      @current-change="handleCurrentChange"
      :hide-on-single-page="false"
    />
  </div>

  <!-- 对话框保持不变 -->
  <!-- ... 原有的对话框代码 ... -->
</template>

<script lang="ts" setup>
import axios from "@/utils/axios";
import { ref, computed, onMounted, reactive, nextTick, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { Search, CaretTop, CaretBottom, Loading } from '@element-plus/icons-vue';
import { debounce } from 'lodash-es';

// 基础配置
const props = defineProps({
  id: String
});

// 响应式数据
const loading = ref(false);
const tableData = ref([]);
const searchKeyword = ref("");
const currentPage = ref(1);
const pageSize = ref(100);
const totalCount = ref(0);
const hasNextPage = ref(false);
const hasPrevPage = ref(false);

// 虚拟滚动相关
const tableContainer = ref<HTMLElement>();
const rowHeight = 50; // 每行高度
const visibleCount = ref(20); // 可见行数
const startIndex = ref(0);
const scrollTop = ref(0);

// 筛选相关
const dialogVisible = ref(false);
const advancedFilters = reactive({
  audittype: '',
  responsibleDeptId: '',
  dept: '',
  ifViolation: '',
  assignmentStatus: '',
  timeRange: []
});

const filterOptions = ref({});
const filterOptionsLoading = ref({});

// 排序相关
const sortBy = ref('id');
const sortOrder = ref('desc');

// 选择相关
const selectedRows = ref([]);
const selectAll = ref(false);

// 列配置 - 简化版本，只显示核心字段
const columns = [
  { prop: 'task_id', label: '任务单号', width: 150, minWidth: 150, sortable: true, fixed: 'left' },
  { prop: 'audittype', label: '稽查场景', width: 150, minWidth: 150, filterable: true },
  { prop: 'network_code', label: 'NIS网络ID', width: 180, minWidth: 180, filterable: true },
  { prop: 'responsibleDeptId', label: '代表处', width: 150, minWidth: 150, filterable: true },
  { prop: 'dept', label: '部门', width: 150, minWidth: 150, filterable: true },
  { prop: 'account', label: '操作账户', width: 150, minWidth: 150 },
  { prop: 'opt_start_time', label: '操作时间', width: 180, minWidth: 180 },
  { prop: 'ifViolation', label: '是否违规', width: 120, minWidth: 120, filterable: true },
  { prop: 'assignmentStatus', label: '当前状态', width: 120, minWidth: 120, filterable: true }
];

// 计算属性
const visibleColumns = computed(() => columns);

const filterableColumns = computed(() => 
  columns.filter(col => col.filterable)
);

const tableWidth = computed(() => {
  return visibleColumns.value.reduce((total, col) => total + (col.width || 150), 0) + 55 + 120; // 55选择列 + 120操作列
});

const virtualHeight = computed(() => totalCount.value * rowHeight);

const offsetY = computed(() => startIndex.value * rowHeight);

const visibleItems = computed(() => {
  const start = startIndex.value;
  const end = Math.min(start + visibleCount.value, tableData.value.length);
  return tableData.value.slice(start, end);
});

// 状态映射
const statusType = {
  '已关闭': 'success',
  '待举证': 'danger',
  '待处理': 'info'
};

const complianceType = {
  'NO': 'success',
  'YES': 'danger'
};

// 防抖搜索
const debounceSearch = debounce(() => {
  currentPage.value = 1;
  fetchData();
}, 500);

// 数据获取
const fetchData = async () => {
  if (loading.value) return;
  
  loading.value = true;
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchKeyword.value,
      order_by: sortBy.value,
      order_direction: sortOrder.value,
      ...advancedFilters
    };

    // 处理时间范围
    if (advancedFilters.timeRange && advancedFilters.timeRange.length === 2) {
      params.start_time = advancedFilters.timeRange[0];
      params.end_time = advancedFilters.timeRange[1];
    }

    const response = await axios.get('/api/auditdata/', { params });
    
    tableData.value = response.data.data;
    totalCount.value = response.data.pagination.total_count;
    hasNextPage.value = response.data.pagination.has_next;
    hasPrevPage.value = response.data.pagination.has_previous;
    
    // 重置虚拟滚动位置
    startIndex.value = 0;
    if (tableContainer.value) {
      tableContainer.value.scrollTop = 0;
    }
    
  } catch (error) {
    console.error('数据获取失败:', error);
    ElMessage.error('数据加载失败');
  } finally {
    loading.value = false;
  }
};

// 虚拟滚动处理
const handleScroll = () => {
  if (!tableContainer.value) return;
  
  const { scrollTop: newScrollTop } = tableContainer.value;
  const containerHeight = tableContainer.value.clientHeight;
  
  scrollTop.value = newScrollTop;
  
  // 计算可见行数和起始索引
  visibleCount.value = Math.ceil(containerHeight / rowHeight) + 5; // 额外渲染5行作为缓冲
  startIndex.value = Math.max(0, Math.floor(newScrollTop / rowHeight) - 2); // 提前渲染2行
  
  // 确保不超出数据范围
  if (startIndex.value + visibleCount.value > tableData.value.length) {
    startIndex.value = Math.max(0, tableData.value.length - visibleCount.value);
  }
};

// 筛选选项加载
const loadFilterOptions = debounce(async (field: string, query: string = '') => {
  if (filterOptionsLoading.value[field]) return;
  
  filterOptionsLoading.value[field] = true;
  try {
    const response = await axios.get('/api/filter-options/', {
      params: { field, search: query }
    });
    filterOptions.value[field] = response.data.options;
  } catch (error) {
    console.error('筛选选项加载失败:', error);
  } finally {
    filterOptionsLoading.value[field] = false;
  }
}, 300);

// 排序处理
const toggleSort = (column: string) => {
  if (sortBy.value === column) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortBy.value = column;
    sortOrder.value = 'asc';
  }
  fetchData();
};

// 选择处理
const toggleRowSelection = (item: any) => {
  const index = selectedRows.value.indexOf(item.id);
  if (index > -1) {
    selectedRows.value.splice(index, 1);
  } else {
    selectedRows.value.push(item.id);
  }
  updateSelectAllState();
};

const handleSelectAll = () => {
  if (selectAll.value) {
    selectedRows.value = [...new Set([...selectedRows.value, ...visibleItems.value.map(item => item.id)])];
  } else {
    const visibleIds = visibleItems.value.map(item => item.id);
    selectedRows.value = selectedRows.value.filter(id => !visibleIds.includes(id));
  }
};

const updateSelectAllState = () => {
  const visibleIds = visibleItems.value.map(item => item.id);
  const selectedVisibleIds = selectedRows.value.filter(id => visibleIds.includes(id));
  selectAll.value = selectedVisibleIds.length === visibleIds.length && visibleIds.length > 0;
};

// 分页处理
const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchData();
};

const handleCurrentChange = (page: number) => {
  currentPage.value = page;
  fetchData();
};

// 筛选处理
const applyAdvancedFilter = () => {
  dialogVisible.value = false;
  currentPage.value = 1;
  fetchData();
};

const resetAdvancedFilter = () => {
  Object.keys(advancedFilters).forEach(key => {
    if (key === 'timeRange') {
      advancedFilters[key] = [];
    } else {
      advancedFilters[key] = '';
    }
  });
  fetchData();
};

const toggleFilterPanel = () => {
  dialogVisible.value = !dialogVisible.value;
};

// 批量操作
const batchProof = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请至少选择一条记录');
    return;
  }
  // 实现批量举证逻辑
};

const batchApproval = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请至少选择一条记录');
    return;
  }
  // 实现批量审批逻辑
};

// 单行操作
const addProof = (row: any) => {
  // 实现单行举证逻辑
};

const addApproval = (row: any) => {
  // 实现单行审批逻辑
};

// 生命周期
onMounted(() => {
  fetchData();
  
  // 初始化筛选选项
  filterableColumns.value.forEach(col => {
    loadFilterOptions(col.prop);
  });
});

onUnmounted(() => {
  // 清理防抖函数
  debounceSearch.cancel();
});
</script>

<style scoped>
.virtual-table-container {
  height: 600px;
  overflow: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  position: relative;
}

.table-header {
  position: sticky;
  top: 0;
  background: #f5f7fa;
  z-index: 10;
  border-bottom: 1px solid #ebeef5;
}

.table-body {
  position: relative;
}

.table-row {
  display: flex;
  align-items: center;
  height: 50px;
  border-bottom: 1px solid #ebeef5;
}

.header-row {
  background: #f5f7fa;
  font-weight: bold;
}

.data-row {
  background: #fff;
  transition: background-color 0.2s;
}

.data-row:hover {
  background: #f5f7fa;
}

.data-row.selected {
  background: #ecf5ff;
}

.table-cell {
  padding: 8px 12px;
  border-right: 1px solid #ebeef5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
}

.selection-cell {
  width: 55px;
  min-width: 55px;
  justify-content: center;
}

.action-cell {
  justify-content: center;
  gap: 8px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.sort-icons {
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.sort-icons .el-icon {
  font-size: 12px;
  color: #c0c4cc;
}

.sort-icons .el-icon.active {
  color: #409eff;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 100;
}

.demo-pagination-block {
  margin-top: 20px;
  text-align: center;
}

/* 原有样式保持不变 */
.advanced-filter-panel {
  width: 100%;
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.advanced-filter-card {
  display: flex;
  flex-direction: column;
}

.card-header {
  padding: 12px 20px;
  background-color: #f5f7fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content {
  padding: 15px 20px;
}

.card-footer {
  padding: 10px 20px;
  text-align: right;
  background-color: #f5f7fa;
}

.container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.upload-container {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>