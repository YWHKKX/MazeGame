# 统一阵营系统设计文档

## 概述

本文档描述了游戏中的统一阵营系统，简化了原有的复杂敌我关系逻辑，使用统一的阵营属性来管理所有单位的敌我关系。

## 阵营类型

### 1. 怪物阵营 (`"monsters"`)
- **包含单位**：
  - 所有怪物类型（imp, orc_warrior, goblin_worker, goblin_engineer, 等）
  - 怪物巢穴建筑（orc_lair, demon_lair）
- **特点**：与英雄阵营互相敌对

### 2. 英雄阵营 (`"heroes"`)
- **包含单位**：
  - 所有英雄类型（knight, paladin, assassin, 等）
  - 所有建筑（dungeon_heart, treasury, arrow_tower, arcane_tower, 等）
- **特点**：与怪物阵营互相敌对

## 简化后的属性系统

### 移除的属性
- `is_monster` - 不再需要，由faction判断
- `is_enemy` - 不再需要，由faction判断  
- `is_hero` - 不再需要，由faction判断

### 保留的属性
- `faction` - 阵营属性，统一管理敌我关系
- `is_combat_unit` - 是否为战斗单位（用于技能系统等）

## 敌我关系判断

### 统一判断逻辑
```python
def _is_enemy_of(self, target) -> bool:
    """判断目标是否为敌人 - 统一使用faction判断"""
    # 检查阵营 - 不同阵营即为敌人
    if hasattr(self, 'faction') and hasattr(target, 'faction'):
        return self.faction != target.faction
    
    # 如果目标没有faction属性，默认为敌人（兼容性考虑）
    return True
```

### 判断规则
1. **不同阵营 = 敌人**：`monsters` vs `heroes` = 敌对
2. **相同阵营 = 友军**：`monsters` vs `monsters` = 友军
3. **无阵营属性 = 敌人**：兼容性考虑，默认为敌对

## 单位分类

### 战斗单位 (`is_combat_unit = True`)
- 所有英雄
- 所有怪物
- 防御塔（arrow_tower, arcane_tower）

### 非战斗单位 (`is_combat_unit = False`)
- 所有建筑（除防御塔外）
- 功能性单位（goblin_worker, goblin_engineer）

## 实现细节

### 1. Creature基类
```python
class Creature:
    def __init__(self, x: int, y: int, creature_type: str = 'imp'):
        # 战斗属性
        self.is_combat_unit = True  # 是否为战斗单位（默认是）
        
        # 阵营系统 - 统一使用faction属性
        self.faction = "monsters"  # 默认怪物阵营，子类可以重写
```

### 2. Monster类
```python
class Monster(Creature):
    def __init__(self, x: int, y: int, monster_type: str = 'imp'):
        super().__init__(x, y, monster_type)
        
        # 怪物特有属性 - 统一阵营系统
        self.faction = "monsters"  # 怪物阵营
```

### 3. Hero类
```python
class Hero(Creature):
    def __init__(self, x: int, y: int, hero_type: str = 'knight'):
        super().__init__(x, y, hero_type)
        
        # 英雄特有属性 - 统一阵营系统
        self.faction = "heroes"  # 英雄阵营
```

### 4. Building类
```python
class Building(GameTile):
    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        # 阵营系统 - 建筑默认属于英雄阵营
        self.faction = "heroes"  # 建筑属于英雄阵营
        self.is_combat_unit = False  # 建筑不是战斗单位（除了防御塔）
```

### 5. 防御塔特殊处理
```python
class ArrowTower(Building):
    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)
        
        # 战斗单位设置
        self.is_combat_unit = True  # 箭塔是战斗单位
```

## 优势

### 1. 简化逻辑
- 移除了复杂的多重判断条件
- 统一使用faction属性管理敌我关系
- 代码更易维护和理解

### 2. 性能优化
- 减少了属性检查次数
- 简化了敌我判断逻辑
- 提高了战斗系统性能

### 3. 易于扩展
- 新增单位只需设置正确的faction
- 新增阵营类型只需修改判断逻辑
- 支持更复杂的阵营关系（如中立阵营）

## 兼容性

### 向后兼容
- 保留了`is_combat_unit`属性用于技能系统
- 对于没有faction属性的单位，默认为敌人
- 渐进式迁移，不影响现有功能

### 迁移指南
1. 移除所有`is_monster`、`is_enemy`、`is_hero`属性引用
2. 使用`faction`属性进行敌我判断
3. 使用`is_combat_unit`属性进行战斗单位判断

## 测试建议

### 1. 阵营判断测试
- 验证不同阵营单位互相敌对
- 验证相同阵营单位互相友好
- 验证无阵营属性的兼容性

### 2. 技能系统测试
- 验证兽人战士旋风斩技能正常工作
- 验证技能只攻击敌对阵营
- 验证战斗单位判断正确

### 3. 战斗系统测试
- 验证攻击列表管理正确
- 验证目标选择逻辑正确
- 验证防御塔攻击逻辑正确

## 总结

统一阵营系统成功简化了游戏的敌我关系管理，提高了代码的可维护性和性能。通过使用单一的`faction`属性，我们实现了清晰、高效的阵营判断逻辑，为游戏的后续发展奠定了良好的基础。
