# 🎮 游戏环境模拟器 - 完整功能文档

## 📚 概述

游戏环境模拟器 (`GameEnvironmentSimulator`) 是一个强大的测试工具，提供了完整的游戏环境模拟功能，包括地图生成、建筑管理、物理系统、特效系统、状态指示器和统一的移动系统等。它集成了最新的 MovementSystem API，确保所有角色移动都使用统一的路径查找和智能移动逻辑。

### ⏰ 时间单位统一
模拟器现在使用秒作为统一的时间单位，与真实游戏保持一致：
- **delta_time**: 秒单位，与真实游戏一致
- **时间转换**: 所有时间相关的API都使用秒单位
- **API一致性**: 确保时间单位在整个系统中的一致性

## 🚀 新增功能

### 🗺️ 地图生成和管理

#### 基础地图生成
```python
# 生成空白网格地面
simulator.generate_blank_map(width=40, height=30)

# 清空地图
simulator.clear_map()
```

#### 地图元素添加
```python
# 添加金矿
gold_mine = simulator.add_gold_mine(x=5, y=5, gold_amount=100)

# 添加岩石瓦片
simulator.add_rock_tile(x=3, y=3)

# 添加墙壁瓦片
simulator.add_wall_tile(x=12, y=12)
```

#### 随机地图生成
```python
# 生成随机地图
simulator.generate_random_map(
    gold_mine_count=10,  # 金矿数量
    rock_count=20,       # 岩石数量
    wall_count=15        # 墙壁数量
)
```

### 🏗️ 建筑API扩展

#### 基础设施建筑
```python
# 地牢之心（主基地）
dungeon_heart = simulator.create_dungeon_heart(x=5, y=5, gold=1000)

# 金库（支持存储回退机制）
treasury = simulator.create_treasury(x=8, y=5, stored_gold=0)

# 巢穴
lair = simulator.create_lair(x=12, y=8)
```

#### 军事建筑
```python
# 箭塔（支持弹药量设置）
arrow_tower = simulator.create_arrow_tower(x=15, y=10, ammunition=60)

# 创建无弹药的箭塔
empty_tower = simulator.create_arrow_tower(x=20, y=15, ammunition=0)

# 监狱
prison = simulator.create_prison(x=20, y=15)

# 防御工事
fortification = simulator.create_defense_fortification(x=25, y=20)
```

#### 功能建筑
```python
# 训练室
training_room = simulator.create_training_room(x=30, y=25)

# 图书馆
library = simulator.create_library(x=35, y=30)
```

### ⚔️ 物理系统集成

#### 碰撞检测
```python
# 检查两个单位是否碰撞
collision = simulator.check_collision(unit1, unit2)

# 检测所有单位间的碰撞
collisions = simulator.detect_all_collisions()

# 解决碰撞（推开单位）
simulator.resolve_collision(unit1, unit2)
```

#### 击退效果
```python
# 应用击退效果
success = simulator.apply_knockback(
    attacker=hero,
    target=creature,
    attack_damage=25.0,
    attack_type="heavy"
)

# 箭塔击退效果（自动触发）
# 箭塔攻击时会自动计算和应用击退效果
# 击退距离 = 基础击退距离 × 1.8 × 伤害系数 × 暴击系数
# 伤害系数 = 1.0 + (伤害 / 150.0)
# 暴击系数 = 1.3（如果暴击）
```

#### 攻击模拟
```python
# 模拟攻击（包含伤害和击退）
success = simulator.simulate_attack(
    attacker=hero,
    target=creature,
    damage=30.0
)
```

### ✨ 特效系统集成

#### 粒子特效
```python
# 创建粒子特效
simulator.create_particle_effect(
    x=100, y=100,
    particle_count=15,
    color=(255, 255, 0)
)
```

#### 视觉特效
```python
# 创建视觉特效
effect = simulator.create_visual_effect(
    effect_type="explosion",
    x=200, y=200,
    intensity=1.5
)

# 创建通用特效
effect = simulator.create_effect(
    effect_type="magic_aura",
    x=250, y=250,
    color=(100, 100, 255)
)
```

### 📊 状态指示器集成

#### 状态渲染
```python
# 渲染单位状态指示器
simulator.render_status_indicator(unit, screen_x, screen_y)

# 获取状态描述
description = simulator.get_status_description("constructing")
```

### 🚶 移动系统集成

#### 角色移动管理
```python
# 设置角色持续移动目标（使用MovementSystem API）
simulator.set_character_movement_target(
    character=engineer,
    target_x=100.0,
    target_y=100.0,
    speed=50.0,        # 移动速度
    tolerance=5.0      # 到达目标的容错距离
)

# 单帧移动角色到指定位置
simulator.move_character_to(character, 50.0, 50.0, speed=30.0)

# 设置角色位置
simulator.set_character_position(character, 25.0, 25.0)
```

#### 移动系统特性
- **统一API**: 所有角色移动都使用 MovementSystem API
- **路径查找**: 自动进行路径规划和障碍物避让
- **智能移动**: 支持目标寻找和持续移动
- **性能优化**: 使用空间哈希和路径缓存优化性能

### 🎯 测试场景预设

#### 基础测试场景
```python
# 建筑修复测试
simulator.setup_repair_test_scenario()

# 战斗测试
simulator.setup_combat_test_scenario()

# 经济测试
simulator.setup_economy_test_scenario()
```

#### 高级测试场景
```python
# 物理系统测试
simulator.setup_physics_test_scenario()

# 特效系统测试
simulator.setup_effects_test_scenario()

# 工程师修复测试
simulator.setup_repair_test_scenario()

# 综合测试场景
simulator.setup_comprehensive_test_scenario()
```

## 🎮 使用示例

### 基础使用
```python
from src.managers.game_environment_simulator import GameEnvironmentSimulator

# 创建模拟器
simulator = GameEnvironmentSimulator(
    screen_width=1200,
    screen_height=800,
    tile_size=20
)

# 生成随机地图
simulator.generate_random_map(gold_mine_count=8, rock_count=15, wall_count=10)

# 创建主基地
simulator.create_dungeon_heart(5, 5, 1000)

# 创建角色
engineer = simulator.create_engineer(100, 100)
hero = simulator.create_hero(200, 200, 'knight')

# 运行模拟（时间单位：秒）
simulator.run_simulation(max_duration=60.0, enable_visualization=True)  # 60秒
```

### 高级使用
```python
# 设置综合测试场景
simulator.setup_comprehensive_test_scenario()

# 使用MovementSystem API进行角色移动
simulator.set_character_movement_target(
    engineer, 100.0, 100.0, speed=50.0, tolerance=5.0
)

# 模拟攻击
simulator.simulate_attack(hero, engineer, 25.0)

# 获取统计信息
stats = simulator.get_statistics()
physics_stats = simulator.get_physics_stats()
effects_stats = simulator.get_effects_stats()

# 清除特效
simulator.clear_all_effects()
```

### MovementSystem API 使用示例
```python
# 创建角色
engineer = simulator.create_engineer(50, 50)
hero = simulator.create_hero(200, 200, 'knight')

# 设置持续移动目标
simulator.set_character_movement_target(
    character=engineer,
    target_x=150.0,
    target_y=150.0,
    speed=60.0,        # 移动速度
    tolerance=10.0     # 到达目标的容错距离
)

# 在游戏循环中，移动会自动更新
# 角色会使用MovementSystem进行路径查找和智能移动

# 检查是否到达目标
if not hasattr(engineer, 'has_movement_target'):
    game_logger.info("工程师已到达目标位置")

# 单帧移动（不持续）
simulator.move_character_to(hero, 100.0, 100.0, speed=40.0)

# 直接设置位置
simulator.set_character_position(engineer, 200.0, 200.0)

# 使用秒时间单位更新移动
delta_time = 0.016  # 约16毫秒（约60FPS）
simulator.update(delta_time)  # 直接使用秒单位
```

### 工程师修复功能使用示例
```python
# 创建地牢之心（主基地，500金币）
dungeon_heart = simulator.create_dungeon_heart(5, 5, 500)

# 创建损坏的箭塔（生命值200/400）
damaged_tower = simulator.create_arrow_tower(20, 15)
damaged_tower.health = 200  # 设置为半血状态

# 创建工程师
engineer = simulator.create_engineer(150, 150, EngineerType.BASIC)

# 工程师会自动：
# 1. 检测到损坏的箭塔
# 2. 前往主基地获取金币
# 3. 移动到箭塔位置
# 4. 开始修复（每1秒投入4金币，修复20点生命值）
# 5. 完成修复后转为空闲状态

# 修复计算：
# - 修复费用：0.2金币/HP
# - 每次投入：4金币
# - 每次修复：4 ÷ 0.2 = 20 HP
# - 总需要修复：200 HP
# - 修复次数：200 ÷ 20 = 10次
# - 总费用：10 × 4 = 40金币
# - 修复时间：约10秒
```

### 自动分配器状态查询API
```python
# 获取自动分配器状态信息
assignment_status = simulator.get_assignment_status()

# 工程师分配器状态
if assignment_status['engineer_assigner']['available']:
    engineer_info = assignment_status['engineer_assigner']
    print(f"工程师分配器策略: {engineer_info['strategy']}")
    print(f"活跃任务: {engineer_info['active_tasks']}")
    print(f"已分配工程师: {engineer_info['assigned_engineers']}")

# 苦工分配器状态
if assignment_status['worker_assigner']['available']:
    worker_info = assignment_status['worker_assigner']
    print(f"苦工分配器策略: {worker_info['strategy']}")
    print(f"活跃任务: {worker_info['active_tasks']}")
    print(f"已分配苦工: {worker_info['assigned_workers']}")
```

### 苦工训练任务API
```python
# 创建训练室
training_room = simulator.create_training_room(x=30, y=25)

# 创建苦工
worker = simulator.create_worker(x=100, y=100)

# WorkerAssigner会自动：
# 1. 检测训练室需要训练任务
# 2. 分配训练任务给苦工
# 3. 苦工前往训练室
# 4. 开始训练（训练时间30秒）
# 5. 训练完成后转为空闲状态

# 苦工优先级顺序：
# 1. WorkerAssigner任务（训练任务等）
# 2. 逃离敌人（60像素检测范围）
# 3. 存储金币（携带满时）
# 4. 挖掘金矿（主要工作）
# 5. 游荡（空闲状态）
```

## 🔧 系统集成

### 移动系统
- **MovementSystem集成**: 所有角色移动都使用统一的 MovementSystem API
- **路径查找**: 支持A*和B*路径查找算法，自动避障
- **智能移动**: 支持目标寻找、持续移动和路径优化
- **性能优化**: 使用空间哈希和路径缓存机制提升性能
- **坐标系统**: 统一使用像素坐标，避免瓦片坐标混淆

### 物理系统
- **碰撞检测**: 基于空间哈希的高效碰撞检测
- **击退效果**: 支持不同攻击类型的击退计算
- **环境碰撞**: 检测与墙面、建筑的碰撞
- **反弹效果**: 撞墙后的反弹和伤害计算

### 特效系统
- **粒子系统**: 支持粒子特效的创建和渲染
- **击退动画**: 击退效果的视觉反馈
- **屏幕震动**: 攻击和碰撞的屏幕震动效果
- **闪烁效果**: 单位受到攻击时的闪烁反馈

### 状态指示器
- **统一设计**: 所有单位使用统一的状态指示器
- **颜色编码**: 不同状态使用不同颜色表示
- **状态描述**: 提供状态的中文描述文本
- **动态更新**: 状态变化时自动更新显示

### 移动系统
- **MovementSystem集成**: 使用统一的移动系统API
- **路径查找**: 支持A*和B*路径查找算法
- **智能移动**: 自动避障和目标寻找
- **性能优化**: 空间哈希和路径缓存机制

## 📊 性能统计

### 物理系统统计
```python
physics_stats = simulator.get_physics_stats()
game_logger.info(f"碰撞检测次数: {physics_stats['collision_checks']}")
game_logger.info(f"击退计算次数: {physics_stats['knockback_calculations']}")
game_logger.info(f"活跃击退数量: {physics_stats['active_knockbacks']}")
game_logger.info(f"撞墙次数: {physics_stats['wall_collisions']}")
```

### 特效系统统计
```python
effects_stats = simulator.get_effects_stats()
game_logger.info(f"击退特效数量: {effects_stats['knockback_effects']}")
game_logger.info(f"视觉特效数量: {effects_stats['visual_effects']}")
game_logger.info(f"粒子特效数量: {effects_stats['particle_effects']}")
```

## 🎯 测试场景说明

### 1. 地图生成测试
- 测试空白地图生成
- 测试各种地图元素的添加
- 测试随机地图生成

### 2. 建筑API测试
- 测试各种建筑的创建
- 测试建筑状态管理
- 测试建筑功能

### 3. 物理系统测试
- 测试碰撞检测
- 测试击退效果
- 测试环境碰撞

### 4. 特效系统测试
- 测试粒子特效
- 测试视觉特效
- 测试动画效果

### 5. 移动系统测试
- 测试角色移动和路径查找
- 测试持续移动目标设置
- 测试移动性能优化

### 6. 工程师修复测试
- 测试工程师修复建筑功能
- 测试修复费用计算
- 测试修复进度显示
- 测试修复完成检测

### 7. 综合测试
- 测试所有系统的集成
- 测试性能表现
- 测试稳定性

## 🚀 快速开始

1. **运行演示脚本**:
```bash
python examples/game_environment_simulator_demo.py
```

2. **创建自定义测试**:
```python
from src.managers.game_environment_simulator import GameEnvironmentSimulator

simulator = GameEnvironmentSimulator()
simulator.setup_comprehensive_test_scenario()
simulator.run_simulation(max_duration=30.0, enable_visualization=True)
```

3. **查看统计信息**:
```python
stats = simulator.get_statistics()
game_logger.info(f"模拟时间: {stats['simulation_time']:.1f}秒")
game_logger.info(f"建筑数量: {stats['buildings_count']}")
game_logger.info(f"总金币: {stats['total_gold']}")
```

## 🔍 调试功能

### 调试信息输出
```python
# 打印调试信息
simulator.game_logger.info_debug_info()

# 获取调试信息
debug_info = simulator.get_debug_info()
```

### 事件日志
```python
# 记录事件日志
simulator.log_event("单位攻击了目标")

# 获取模拟统计
stats = simulator.get_statistics()
```

## 🎨 渲染系统

### 地图渲染
- 支持不同瓦片类型的颜色渲染
- 金矿UI显示（钻石图标 + 储量条）
- 瓦片边框显示

### 建筑渲染
- 建筑状态高亮显示
- 生命条显示
- 状态指示器

### 特效渲染
- 粒子特效渲染
- 击退动画渲染
- 屏幕震动效果

## 📝 注意事项

1. **内存管理**: 长时间运行时注意清理特效和对象
2. **性能优化**: 大量单位时考虑使用空间哈希优化
3. **错误处理**: 注意检查API调用的返回值
4. **资源清理**: 使用完毕后调用相应的清理方法
5. **时间单位**: 所有时间相关API都使用秒单位，与真实游戏保持一致
6. **箭塔击退**: 箭塔攻击会自动触发击退效果，无需手动调用
7. **弹药系统**: 箭塔需要弹药才能攻击，工程师会自动装填
8. **存储系统**: 苦工现在支持存储回退机制，找不到金库时会自动回退到主基地存储
9. **修复系统**: 工程师支持建筑修复功能，修复费用为每点生命值0.2金币，每1秒执行一次修复
10. **自动分配器**: 支持工程师和苦工的智能任务分配，包括建造、修理、装填和训练任务
11. **任务优先级**: 任务按CRITICAL(10.0)、HIGH(7.0)、NORMAL(4.0)、LOW(1.0)四个等级分配
12. **苦工训练**: WorkerAssigner支持为苦工分配训练任务，训练时间为30秒
13. **状态查询**: 提供get_assignment_status()API查询自动分配器的工作状态

## 🔮 未来扩展

- [ ] 更多地图元素类型
- [ ] 更复杂的物理效果
- [ ] 更多视觉特效
- [ ] 音效系统集成
- [ ] 网络多人测试支持

---

*游戏环境模拟器为游戏开发提供了强大的测试和调试工具，帮助开发者快速验证游戏逻辑和系统集成。*

