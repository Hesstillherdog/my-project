# Django 后端优化方案

from django.core.paginator import Paginator
from django.db import connection, transaction, OperationalError
from django.http import JsonResponse
from django.utils.functional import cached_property
from django.db.models import Q
import json

class FastPaginator(Paginator):
    """
    优化的分页器 - 限制 COUNT 查询时间
    如果超时则返回估算值
    """
    @cached_property
    def count(self):
        try:
            with transaction.atomic(), connection.cursor() as cursor:
                # 限制 COUNT 查询最多 200ms
                cursor.execute('SET LOCAL statement_timeout TO 200;')
                return super().count
        except OperationalError:
            # 如果超时，返回估算值
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    "SELECT reltuples FROM pg_class WHERE relname = %s",
                    [self.object_list.query.model._meta.db_table]
                )
                estimate = int(cursor.fetchone()[0])
                return estimate

def get_auditdata_optimized(request):
    """优化的数据获取接口"""
    
    # 获取分页参数
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 100))
    
    # 获取筛选参数
    filters = {}
    search = request.GET.get('search', '')
    
    # 构建基础查询
    queryset = AuditResult.objects.all()
    
    # 只选择必要的字段，避免大字段
    queryset = queryset.values(
        'id', 'task_id', 'audittype', 'network_code', 'network_options',
        'responsibleDeptId', 'dept', 'account', 'opt_resource', 'opt_name',
        'opt_start_time', 'ifBlack', 'opt_resource_num', 'ifViolation', 
        'assignmentStatus', 'proofer', 'approvaler'
        # 移除大字段如 detail_info, proofInfo 等，按需获取
    )
    
    # 全局搜索优化
    if search:
        search_q = Q(task_id__icontains=search) | \
                  Q(account__icontains=search) | \
                  Q(network_code__icontains=search)
        queryset = queryset.filter(search_q)
    
    # 高级筛选
    for field in ['audittype', 'responsibleDeptId', 'dept', 'ifViolation', 'assignmentStatus']:
        value = request.GET.get(field)
        if value and value != '':
            filters[field] = value
    
    if filters:
        queryset = queryset.filter(**filters)
    
    # 时间范围筛选
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')
    if start_time and end_time:
        queryset = queryset.filter(
            opt_start_time__range=[start_time, end_time]
        )
    
    # 排序优化 - 使用索引字段
    order_by = request.GET.get('order_by', 'id')
    order_direction = request.GET.get('order_direction', 'desc')
    if order_direction == 'desc':
        order_by = f'-{order_by}'
    
    queryset = queryset.order_by(order_by)
    
    # 使用优化的分页器
    paginator = FastPaginator(queryset, page_size)
    
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    # 返回分页数据
    return JsonResponse({
        'data': list(page_obj.object_list),
        'pagination': {
            'current_page': page,
            'total_pages': paginator.num_pages if paginator.count < 10000000 else None,
            'page_size': page_size,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
    })

def get_filter_options(request):
    """获取筛选选项 - 异步加载"""
    field = request.GET.get('field')
    search = request.GET.get('search', '')
    
    if field not in ['audittype', 'responsibleDeptId', 'dept', 'ifViolation', 'assignmentStatus']:
        return JsonResponse({'error': 'Invalid field'}, status=400)
    
    # 使用 distinct 和 limit 优化
    queryset = AuditResult.objects.values_list(field, flat=True).distinct()
    
    if search:
        queryset = queryset.filter(**{f"{field}__icontains": search})
    
    options = list(queryset[:100])  # 限制返回数量
    
    return JsonResponse({'options': options})

# 数据库迁移 - 添加必要索引
"""
在 Django 模型中添加索引：

class AuditResult(models.Model):
    # ... 其他字段 ...
    
    class Meta:
        app_label = 'auditapp'
        verbose_name = "稽查结果"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['task_id']),
            models.Index(fields=['audittype']),
            models.Index(fields=['responsibleDeptId']),
            models.Index(fields=['dept']),
            models.Index(fields=['account']),
            models.Index(fields=['opt_start_time']),
            models.Index(fields=['ifViolation']),
            models.Index(fields=['assignmentStatus']),
            models.Index(fields=['network_code']),
            # 复合索引用于常见查询组合
            models.Index(fields=['assignmentStatus', 'opt_start_time']),
            models.Index(fields=['ifViolation', 'opt_start_time']),
        ]
"""