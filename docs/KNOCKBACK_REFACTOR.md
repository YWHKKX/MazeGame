# 击退系统重构文档

## 概述

本次重构将强击退逻辑从复杂的动态计算改为固定距离机制，让单位可以选择执行强击退或普通击退的其中一个。

## 重构内容

### 1. 新增击退类型枚举

**文件**: `src/core/enums.py`

```python
class KnockbackType(Enum):
    """击退类型 - 用于选择击退强度"""
    NORMAL = 'normal'      # 普通击退
    STRONG = 'strong'      # 强击退
    WEAK = 'weak'          # 弱击退
    NONE = 'none'          # 无击退
```

### 2. 更新击退常量配置

**文件**: `src/core/constants.py`

```python
# 击退系统常量 - 固定距离机制
KNOCKBACK_DISTANCE_WEAK = 8      # 弱击退距离
KNOCKBACK_DISTANCE_NORMAL = 15   # 普通击退距离
KNOCKBACK_DISTANCE_STRONG = 30   # 强击退距离
KNOCKBACK_DURATION = 0.3         # 击退持续时间
KNOCKBACK_SPEED = 50             # 击退速度
```

### 3. 重构击退计算逻辑

**文件**: `src/systems/physics_system.py`

#### 主要变化：

1. **固定距离机制**: 不再使用复杂的动态计算，而是基于击退类型使用固定距离
2. **击退类型确定**: 新增 `_determine_knockback_type()` 方法来确定击退类型
3. **简化计算**: 移除复杂的体型、攻击类型、伤害修正等计算

#### 新的计算流程：

```python
def calculate_knockback(attacker, target, attack_damage, attack_type):
    # 1. 确定击退类型
    knockback_type = _determine_knockback_type(attacker, attack_damage)
    
    # 2. 获取固定击退距离
    final_distance = _get_fixed_knockback_distance(knockback_type)
    
    # 3. 应用目标抗性修正（只影响强击退）
    if knockback_type == KnockbackType.STRONG:
        target_resistance = get_size_resistance(target.size)
        final_distance = int(final_distance / target_resistance)
    
    # 4. 计算击退方向
    direction = calculate_knockback_direction(attacker, target)
    
    return KnockbackResult(distance=final_distance, duration=duration, direction=direction)
```

### 4. 更新箭塔配置

**文件**: `src/entities/building_types.py`

#### 新增功能：

1. **击退类型设置**: `set_knockback_type(knockback_type)`
2. **击退信息查询**: `get_knockback_info()`
3. **动态击退选择**: 支持普通攻击使用普通击退，暴击攻击使用强击退

#### 箭塔击退行为：

- **普通攻击**: 使用普通击退（15像素）
- **暴击攻击**: 使用强击退（30像素，受目标抗性影响）
- **显式设置**: 可以强制设置特定的击退类型

## 击退类型确定逻辑

### 优先级顺序：

1. **显式设置**: 如果单位设置了 `knockback_type` 属性，直接使用
2. **强击退能力**: 如果具有强击退能力，根据是否暴击选择普通/强击退
3. **弱击退能力**: 如果设置了 `has_weak_knockback`，使用弱击退
4. **无击退能力**: 如果设置了 `has_no_knockback`，无击退
5. **默认**: 使用普通击退

### 箭塔击退逻辑：

```python
# 普通攻击
arrow_tower.is_critical_attack = False
# 结果: KnockbackType.NORMAL (15像素)

# 暴击攻击  
arrow_tower.is_critical_attack = True
# 结果: KnockbackType.STRONG (30像素，受抗性影响)

# 显式设置
arrow_tower.set_knockback_type(KnockbackType.WEAK)
# 结果: KnockbackType.WEAK (8像素)
```

## 测试验证

**测试文件**: `tests/knockback_system_test.py`

### 测试内容：

1. **击退类型确定逻辑**: 验证各种情况下的击退类型选择
2. **固定击退距离**: 验证各种击退类型的固定距离
3. **击退计算**: 验证完整的击退计算流程
4. **箭塔击退信息**: 验证箭塔的击退配置和信息查询

### 测试结果：

```
开始击退系统测试...
==================================================
测试击退类型确定逻辑...
  普通攻击击退类型: normal
  暴击攻击击退类型: strong
  显式设置弱击退: weak
击退类型确定逻辑测试通过

测试固定击退距离...
  弱击退距离: 8
  普通击退距离: 15
  强击退距离: 30
  无击退距离: 0.0
固定击退距离测试通过

测试击退计算...
  普通攻击击退距离: 15
  暴击攻击击退距离: 42
  显式弱击退距离: 8
击退计算测试通过

测试箭塔击退信息...
  击退信息: {'has_strong_knockback': True, 'knockback_type': 'dynamic', 'available_types': ['normal', 'strong'], 'distances': {'normal': 15, 'strong': 30}}
箭塔击退信息测试通过

==================================================
所有测试通过！新的固定距离击退系统工作正常
```

## 优势

### 1. 简化逻辑
- 移除复杂的动态计算
- 使用固定的击退距离
- 更容易理解和维护

### 2. 灵活配置
- 支持多种击退类型
- 单位可以显式设置击退类型
- 支持动态击退选择

### 3. 性能优化
- 减少计算复杂度
- 固定距离避免重复计算
- 更快的击退响应

### 4. 易于扩展
- 新增击退类型只需添加枚举值
- 击退距离配置集中管理
- 支持更多击退策略

## 兼容性

- 保持原有的击退接口不变
- 箭塔的击退行为向后兼容
- 现有的击退动画系统无需修改

## 使用示例

```python
# 创建箭塔
arrow_tower = ArrowTower(x, y, BuildingType.ARROW_TOWER, config)

# 查看击退信息
info = arrow_tower.get_knockback_info()
print(f"可用击退类型: {info['available_types']}")
print(f"击退距离: {info['distances']}")

# 设置特定击退类型
arrow_tower.set_knockback_type(KnockbackType.WEAK)

# 攻击目标（自动选择击退类型）
result = arrow_tower.attack_target(target)
```

## 总结

本次重构成功将复杂的动态击退计算简化为固定距离机制，提高了系统的可维护性和性能，同时保持了灵活性和扩展性。新的击退系统更加直观，易于理解和配置。
