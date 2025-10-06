# 技能系统设计文档

## 概述

技能系统是一个独立的模块，为游戏中的英雄和怪物提供主动技能和被动技能支持。系统设计遵循面向对象原则，具有良好的扩展性和可维护性。

## 系统架构

### 核心组件

1. **技能基类 (Skill)**: 所有技能的抽象基类
2. **主动技能 (ActiveSkill)**: 需要玩家操作或AI触发的技能
3. **被动技能 (PassiveSkill)**: 自动触发的技能
4. **技能管理器 (SkillManager)**: 管理所有技能实例和单位技能分配

### 技能类型

#### 主动技能
- **旋风斩 (WhirlwindSlash)**: 骑士和兽人战士的圆形范围攻击
- **多重射击 (MultiShot)**: 弓箭手的连续射击技能

#### 被动技能
- **烈焰自爆 (FlameExplosion)**: 小恶魔死亡时的扇形范围攻击

## 技能设计

### 旋风斩 (WhirlwindSlash)
- **伤害**: 80点基础伤害
- **范围**: 60像素半径的圆形区域
- **冷却**: 8秒
- **法力消耗**: 30点
- **特效**: 金色旋风特效
- **适用单位**: 骑士、兽人战士

### 多重射击 (MultiShot)
- **伤害**: 40点基础伤害
- **射程**: 120像素
- **射击次数**: 4次
- **射击间隔**: 0.2秒
- **冷却**: 6秒
- **法力消耗**: 25点
- **特效**: 蓝色箭矢特效（arrow_shot）
- **适用单位**: 弓箭手、工程师
- **特殊机制**: 目标记忆系统，确保完整射击序列

### 烈焰自爆 (FlameExplosion)
- **伤害**: 60点基础伤害
- **范围**: 80像素半径
- **攻击次数**: 3次扇形攻击
- **触发条件**: 单位死亡时
- **特效**: 橙红色火焰特效
- **适用单位**: 小恶魔

## API设计

### 技能基类API

```python
class Skill:
    def can_use(self, caster) -> bool:
        """检查技能是否可以使用"""
        
    def use_skill(self, caster, target=None, **kwargs) -> bool:
        """使用技能"""
        
    def execute_skill(self, caster, target=None, **kwargs) -> bool:
        """执行技能效果 - 子类必须实现"""
```

### 主动技能API

```python
class ActiveSkill(Skill):
    def __init__(self, skill_id, name, damage, range, direction, cooldown, mana_cost, description):
        # 初始化主动技能参数
```

### 被动技能API

```python
class PassiveSkill(Skill):
    def __init__(self, skill_id, name, description):
        # 初始化被动技能参数
```

### 技能管理器API

```python
class SkillManager:
    def register_skill(self, skill: Skill):
        """注册技能"""
        
    def assign_skill_to_unit(self, unit, skill_id: str):
        """为单位分配技能"""
        
    def get_unit_skills(self, unit) -> List[Skill]:
        """获取单位的技能列表"""
        
    def use_skill(self, unit, skill_id: str, target=None, **kwargs) -> bool:
        """使用技能"""
        
    def get_available_skills(self, unit) -> List[Skill]:
        """获取单位可用的技能"""
```

## 集成方式

### 英雄类集成

```python
class Hero(Creature):
    def __init__(self, x, y, hero_type):
        # 技能系统初始化
        self.skills = []
        self.mana = 100
        self.max_mana = 100
        self.mana_regen_rate = 2
        self._assign_hero_skills(hero_type)
    
    def use_skill(self, skill_id: str, target=None, **kwargs) -> bool:
        """使用技能"""
        
    def update_skills(self, delta_time: float, game_instance=None):
        """更新技能状态"""
```

### 怪物类集成

```python
class Monster(Creature):
    def __init__(self, x, y, monster_type):
        # 技能系统初始化
        self.skills = []
        self.mana = 50
        self.max_mana = 50
        self.mana_regen_rate = 1
        self._assign_monster_skills(monster_type)
    
    def _on_death(self):
        """怪物死亡时触发被动技能"""
```

### 战斗系统集成

```python
class CombatSystem:
    def _execute_attack_sequence(self, attacker, target, delta_time, current_time, distance):
        """执行攻击序列：技能判定 -> 生成特效 -> 造成伤害"""
        # 检查是否可以使用主动技能
        skill_used = self._try_use_active_skill(attacker, target, current_time)
        
        # 如果没有使用技能，执行普通攻击
        if not skill_used:
            # 普通攻击逻辑
```

## 技能分配

### 英雄技能分配

| 英雄类型                | 技能列表 |
| ----------------------- | -------- |
| 骑士 (knight)           | 旋风斩   |
| 弓箭手 (archer)         | 多重射击 |
| 圣骑士 (paladin)        | 旋风斩   |
| 刺客 (assassin)         | 无       |
| 游侠 (ranger)           | 多重射击 |
| 法师 (wizard)           | 无       |
| 大法师 (archmage)       | 无       |
| 德鲁伊 (druid)          | 无       |
| 龙骑士 (dragon_knight)  | 旋风斩   |
| 暗影剑圣 (shadow_blade) | 无       |
| 狂战士 (berserker)      | 旋风斩   |
| 牧师 (priest)           | 无       |
| 盗贼 (thief)            | 无       |
| 工程师 (engineer)       | 多重射击 |

### 怪物技能分配

| 怪物类型                     | 技能列表 |
| ---------------------------- | -------- |
| 小恶魔 (imp)                 | 烈焰自爆 |
| 兽人战士 (orc_warrior)       | 旋风斩   |
| 哥布林苦工 (goblin_worker)   | 无       |
| 地精工程师 (goblin_engineer) | 无       |
| 石像鬼 (gargoyle)            | 无       |
| 火蜥蜴 (fire_salamander)     | 无       |
| 暗影法师 (shadow_mage)       | 无       |
| 树人守护者 (tree_guardian)   | 无       |
| 暗影领主 (shadow_lord)       | 无       |
| 骨龙 (bone_dragon)           | 无       |
| 地狱犬 (hellhound)           | 无       |
| 石魔像 (stone_golem)         | 无       |
| 魅魔 (succubus)              | 无       |

## 特效系统集成

技能系统与现有的特效系统完全集成，每个技能都有对应的特效类型：

- **旋风斩**: `whirlwind_slash` - 金色旋风特效
- **多重射击**: `arrow_shot` - 蓝色箭矢特效
- **烈焰自爆**: `fire_breath` - 橙红色火焰扇形特效

## 测试验证

系统包含完整的测试套件 (`tests/skill_system_test.py`)，验证：

1. 技能注册和分配
2. 主动技能使用和冷却
3. 被动技能触发
4. 法力值消耗和恢复
5. 特效生成
6. 伤害计算

## 扩展性

系统设计具有良好的扩展性：

1. **添加新技能**: 继承 `ActiveSkill` 或 `PassiveSkill` 基类
2. **修改技能参数**: 通过构造函数参数调整
3. **添加新特效**: 在技能实现中指定特效类型
4. **调整技能分配**: 修改 `_assign_hero_skills` 和 `_assign_monster_skills` 方法

## 性能考虑

1. **技能冷却检查**: 使用时间戳避免频繁计算
2. **目标搜索优化**: 使用距离计算和范围检查
3. **特效管理**: 与现有特效系统集成，避免重复创建
4. **内存管理**: 技能实例复用，避免频繁创建销毁

## 总结

技能系统成功实现了：

1. ✅ 独立的技能系统架构
2. ✅ 主动技能和被动技能支持
3. ✅ 完整的API设计
4. ✅ 英雄和怪物技能集成
5. ✅ 战斗系统集成
6. ✅ 特效系统集成
7. ✅ 完整的测试验证

系统已经可以投入使用，为游戏增加了丰富的技能战斗体验。
