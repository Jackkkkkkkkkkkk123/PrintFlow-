# 工作流程步骤权限系统实现文档

## 📋 项目概述

本项目实现了一个细粒度的工作流程步骤权限控制系统，取代原有的粗粒度权限控制，实现了对每个工作流程步骤的精确权限管理。

## 🎯 解决的问题

### 原有权限系统问题：
- ❌ **粗粒度权限**：操作员拥有权限后可以操作所有工作流程
- ❌ **无步骤区分**：不能控制具体能操作哪些步骤
- ❌ **无工艺类型限制**：同一权限可以操作封面印刷和内文印刷

### 新权限系统优势：
- ✅ **细粒度控制**：精确控制到每个步骤的每种操作类型
- ✅ **工艺类型区分**：可以分别控制封面印刷、内文印刷权限
- ✅ **步骤级权限**：可以指定具体能操作哪些步骤
- ✅ **操作类型控制**：可以分别控制开始、完成、跳过、查看、编辑、审批权限
- ✅ **时间限制**：支持工作时间限制
- ✅ **完整审计**：记录所有权限检查和操作日志

## 🏗️ 系统架构

### 核心模型设计

```python
# 权限类型
WorkflowStepPermissionType
├── start (开始步骤)
├── complete (完成步骤) 
├── skip (跳过步骤)
├── view (查看步骤)
├── edit_note (编辑备注)
└── approve (审批步骤)

# 步骤权限
WorkflowStepPermission
├── print_type (工艺类型: cover/content/all)
├── allowed_steps (允许的步骤列表)
├── permission_types (允许的操作类型)
├── time_restriction (时间限制)
└── max_concurrent_operations (并发限制)

# 操作日志
WorkflowStepOperationLog
├── order_no (订单号)
├── step_name (步骤名称)
├── operation_type (操作类型)
├── user (操作员)
├── permission_check_result (权限检查结果)
└── timestamp (操作时间)
```

### 权限控制维度

#### 1. 工艺类型控制
- **封面印刷 (cover)**: 印刷 → 覆膜 → 烫金 → 压痕 → 压纹 → 模切 → 击凸 → 过油 → 外调
- **内文印刷 (content)**: 调图 → CTP → 切纸 → 印刷 → 折页 → 锁线 → 胶包 → 马订 → 勒口 → 夹卡片 → 配本(塑封) → 打包 → 送货
- **混合/所有 (all)**: 可以操作两种工艺类型

#### 2. 步骤名称控制
- 可以指定具体允许操作的步骤列表
- 空列表表示允许操作所有步骤

#### 3. 操作类型控制
- **start**: 开始步骤
- **complete**: 完成步骤
- **skip**: 跳过步骤
- **view**: 查看步骤
- **edit_note**: 编辑备注
- **approve**: 审批步骤

#### 4. 时间限制
- **无限制**: 24小时可操作
- **仅工作时间**: 只能在工作时间操作
- **指定时间段**: 自定义时间段

#### 5. 并发限制
- 控制用户最多同时操作的步骤数量

## 🔧 技术实现

### 1. 数据库模型

```python
# rbac/models.py
class WorkflowStepPermissionType(models.Model):
    """步骤权限类型（开始、完成、跳过等）"""
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200)

class WorkflowStepPermission(models.Model):
    """工作流程步骤权限"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    print_type = models.CharField(max_length=20, choices=PRINT_TYPE_CHOICES)
    allowed_steps = models.TextField(default='[]')  # JSON格式
    permission_types = models.ManyToManyField(WorkflowStepPermissionType)
    time_restriction = models.CharField(max_length=50, default='none')
    max_concurrent_operations = models.IntegerField(default=5)

class WorkflowStepOperationLog(models.Model):
    """步骤操作日志"""
    order_no = models.CharField(max_length=50)
    step_name = models.CharField(max_length=100)
    print_type = models.CharField(max_length=20)
    operation_type = models.CharField(max_length=20)
    user = models.ForeignKey(UserInfo, on_delete=models.CASCADE)
    permission_used = models.CharField(max_length=200)
    permission_check_result = models.BooleanField(default=True)
    success = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)
```

### 2. 权限检查装饰器

```python
# rbac/decorators.py
@require_step_permission('start')
def post(self, request, step_id):
    # 自动进行权限检查
    # 检查通过才会执行实际的视图逻辑
    pass

def check_step_permission(user, step, operation_type):
    """权限检查核心函数"""
    # 1. 获取用户的所有角色
    # 2. 获取角色的所有步骤权限
    # 3. 检查工艺类型匹配
    # 4. 检查步骤名称匹配
    # 5. 检查操作类型匹配
    # 6. 检查时间限制
    # 7. 检查并发限制
    # 8. 记录权限检查日志
    pass
```

### 3. 管理界面

```python
# rbac/views/step_permissions.py
class StepPermissionListView(View):
    """步骤权限列表页面"""
    
class StepPermissionCreateView(View):
    """创建步骤权限"""
    
class RoleStepPermissionView(View):
    """角色权限分配"""
    
class StepPermissionLogView(View):
    """操作日志查看"""
```

## 📦 预配置权限

### 权限类型
- **start**: 开始步骤
- **complete**: 完成步骤
- **skip**: 跳过步骤
- **view**: 查看步骤
- **edit_note**: 编辑备注
- **approve**: 审批步骤

### 预定义权限

| 权限名称 | 工艺类型 | 允许步骤 | 允许操作 |
|---------|---------|---------|---------|
| 全权限 | 所有 | 所有步骤 | 所有操作 |
| 印刷专员权限 | 所有 | 印刷 | 开始、完成、查看、编辑备注 |
| 封面印刷权限 | 封面印刷 | 所有步骤 | 开始、完成、跳过、查看、编辑备注 |
| 封面后处理权限 | 封面印刷 | 覆膜、烫金、压痕、压纹、模切、击凸、过油 | 开始、完成、跳过、查看、编辑备注 |
| 内文印刷权限 | 内文印刷 | 所有步骤 | 开始、完成、跳过、查看、编辑备注 |
| 内文装订权限 | 内文印刷 | 折页、锁线、胶包、马订、勒口、夹卡片 | 开始、完成、查看、编辑备注 |
| 配送权限 | 所有 | 配本(塑封)、打包、送货、外调 | 开始、完成、查看、编辑备注 |
| 质检权限 | 所有 | 所有步骤 | 查看、审批 |
| 主管权限 | 所有 | 所有步骤 | 所有操作 |

### 角色权限映射
- **系统管理员** → 全权限
- **主管** → 主管权限  
- **印刷员** → 印刷专员权限
- **质检员** → 质检权限
- **配送员** → 配送权限

## 🚀 部署和使用

### 1. 数据库迁移

```bash
# 创建迁移文件
python manage.py makemigrations rbac

# 执行迁移
python manage.py migrate rbac
```

### 2. 初始化权限数据

```bash
# 初始化步骤权限系统基础数据
python manage.py init_step_permissions

# 强制重新初始化（删除现有数据）
python manage.py init_step_permissions --force
```

### 3. 权限管理界面

访问以下URL进行权限管理：

- **步骤权限列表**: `/rbac/step-permission/`
- **创建步骤权限**: `/rbac/step-permission/create/`
- **角色权限分配**: `/rbac/role-step-permission/`
- **操作日志查看**: `/rbac/step-permission/logs/`

### 4. 在视图中使用权限检查

```python
from rbac.decorators import require_step_permission

class StartProgressStepView(View):
    @method_decorator(require_step_permission('start'))
    def post(self, request, step_id):
        # 自动进行权限检查，通过后执行步骤开始逻辑
        pass

class CompleteProgressStepView(View):
    @method_decorator(require_step_permission('complete'))
    def post(self, request, step_id):
        # 自动进行权限检查，通过后执行步骤完成逻辑
        pass
```

## 🧪 测试验证

### 运行测试脚本

```bash
# 运行权限系统测试
python test_step_permissions.py
```

测试内容包括：
- ✅ 印刷员只能操作印刷步骤
- ✅ 封面后处理员不能操作印刷步骤
- ✅ 多角色权限继承测试
- ✅ 时间限制权限测试
- ✅ 操作日志记录测试

### 测试用例

```python
# 测试1：印刷员权限控制
print_user = 印刷员用户
step1 = 印刷步骤
step2 = 覆膜步骤

# 印刷员应该可以操作印刷步骤
can_start_print = check_step_permission(print_user, step1, 'start')
assert can_start_print == True

# 印刷员不应该能操作覆膜步骤  
can_start_cover = check_step_permission(print_user, step2, 'start')
assert can_start_cover == False
```

## 📊 功能特性

### ✅ 已实现功能

1. **细粒度权限控制**
   - 工艺类型区分（封面印刷/内文印刷/混合）
   - 步骤名称控制（具体步骤列表）
   - 操作类型控制（开始/完成/跳过/查看/编辑/审批）

2. **时间限制功能**
   - 无限制、仅工作时间、指定时间段

3. **并发控制**
   - 限制用户最大同时操作步骤数

4. **完整审计日志**
   - 记录所有权限检查过程
   - 记录操作成功/失败状态
   - 支持按条件查询日志

5. **权限管理界面**
   - 权限列表查看
   - 权限创建/编辑
   - 角色权限分配
   - 操作日志查看

6. **角色权限继承**
   - 支持用户拥有多个角色
   - 权限取并集（任一角色有权限即可操作）

7. **装饰器权限检查**
   - 自动权限检查装饰器
   - 简化视图代码

### 🔄 权限检查流程

```
用户操作步骤
     ↓
获取用户所有角色
     ↓
获取角色的所有步骤权限
     ↓
检查工艺类型是否匹配
     ↓
检查步骤名称是否允许
     ↓
检查操作类型是否允许
     ↓
检查时间限制
     ↓
检查并发限制
     ↓
记录权限检查日志
     ↓
返回检查结果
```

## 🎉 实施效果

### 权限控制精度提升
- **之前**: 一个权限可以操作所有流程
- **现在**: 精确控制到每个步骤的每种操作

### 安全性增强
- 完整的操作审计日志
- 权限检查过程透明化
- 支持时间和并发限制

### 管理效率提升
- 可视化权限配置界面
- 预配置常用权限模板
- 灵活的角色权限分配

### 系统扩展性
- 模块化设计，易于扩展
- 支持新的操作类型
- 支持复杂的权限规则

## 🔧 维护指南

### 添加新的操作类型

1. 在 `WorkflowStepPermissionType` 中添加新类型
2. 更新装饰器支持新操作类型
3. 在管理界面中配置相关权限

### 添加新的工艺类型

1. 更新 `PRINT_TYPE_CHOICES`
2. 在初始化脚本中添加相关权限配置
3. 更新权限检查逻辑

### 性能优化

1. 权限检查结果缓存
2. 数据库查询优化
3. 批量权限检查接口

## 📞 支持和反馈

如果您在使用过程中遇到问题或有改进建议，请：

1. 检查操作日志排查权限问题
2. 运行测试脚本验证系统功能
3. 查阅本文档的相关章节

---

**🎯 通过实施这个细粒度权限控制系统，您的打印订单管理系统现在拥有了企业级的权限管理能力，可以精确控制每个操作员对每个工作流程步骤的操作权限，大大提升了系统的安全性和管理效率。** 