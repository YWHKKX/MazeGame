# 游戏环境模拟器使用指南

## 概述

`GameEnvironmentSimulator` 是一个完整的游戏环境模拟器，提供了真实的游戏环境来测试各种游戏逻辑。它包含了地图、建筑、角色、管理器等所有必要的游戏组件。

## 文件结构

```
src/managers/game_environment_simulator.py  # 游戏环境模拟器主文件
tests/test_with_environment_simulator.py    # 使用示例
tests/repair_test_with_simulator.py         # 建筑修复测试
tests/combat_test_with_simulator.py         # 战斗逻辑测试
```

## 主要功能

### 1. 环境管理
- 自动创建游戏地图
- 管理所有游戏对象（建筑、角色等）
- 提供统一的更新和渲染接口

### 2. 建筑系统
- 创建各种建筑（地牢之心、箭塔、金库、巢穴等）
- 支持建筑状态管理（健康、损坏、完成等）
- 提供建筑伤害和治疗功能

### 3. 角色系统
- 创建工程师、工人、英雄、生物等角色
- 支持角色移动和位置管理
- 提供角色查找和管理功能

### 4. 测试场景预设
- `setup_repair_test_scenario()` - 建筑修复测试场景
- `setup_combat_test_scenario()` - 战斗测试场景
- `setup_economy_test_scenario()` - 经济测试场景
- `setup_complex_test_scenario()` - 复杂测试场景
- `setup_stress_test_scenario()` - 压力测试场景

## 使用方法

### 基本使用

```python
from src.managers.game_environment_simulator import GameEnvironmentSimulator

# 创建模拟器
simulator = GameEnvironmentSimulator(screen_width=1200, screen_height=800, tile_size=20)

# 设置测试场景
simulator.setup_repair_test_scenario()

# 运行模拟
stats = simulator.run_simulation(max_duration=60.0, enable_visualization=True)
```

### 创建自定义场景

```python
# 创建主基地
dungeon_heart = simulator.create_dungeon_heart(10, 10, 500)

# 创建损坏的箭塔
damaged_tower = simulator.create_arrow_tower(25, 15, 0.5)  # 50%血量

# 创建工程师
engineer = simulator.create_engineer(12, 12)

# 运行模拟
simulator.run_simulation(max_duration=30.0, enable_visualization=False)
```

### 测试辅助功能

```python
# 等待条件满足
def check_repair_complete():
    return damaged_tower.health >= damaged_tower.max_health

success = simulator.wait_for_condition(check_repair_complete, timeout=30.0)

# 获取特定对象
engineer = simulator.get_engineer_by_name("工程师")
tower = simulator.get_building_by_name("箭塔")

# 操作建筑
simulator.damage_building(tower, 50)  # 造成50点伤害
simulator.heal_building(tower, 30)    # 治疗30点生命值

# 移动角色
simulator.set_character_position(engineer, 15.0, 15.0)

# 获取调试信息
simulator.print_debug_info()
```

## 测试示例

### 1. 建筑修复测试

```python
def test_repair_logic():
    simulator = GameEnvironmentSimulator()
    simulator.setup_repair_test_scenario()
    
    # 获取测试对象
    damaged_tower = simulator.get_building_by_name("箭塔")
    engineer = simulator.engineers[0]
    
    # 运行模拟
    start_time = time.time()
    while time.time() - start_time < 30.0:
        simulator.update(0.1)
        
        if damaged_tower.health >= damaged_tower.max_health:
            print("✅ 箭塔修复完成！")
            break
    
    return damaged_tower.health >= damaged_tower.max_health
```

### 2. 战斗测试

```python
def test_combat_logic():
    simulator = GameEnvironmentSimulator()
    simulator.setup_combat_test_scenario()
    
    # 获取测试对象
    arrow_tower = simulator.get_building_by_name("箭塔")
    knight = simulator.heroes[0]
    
    # 运行模拟
    start_time = time.time()
    while time.time() - start_time < 20.0:
        simulator.update(0.1)
        
        # 移动骑士朝向箭塔
        simulator.move_character_to(knight, arrow_tower.x * 20, arrow_tower.y * 20)
        
        if knight.health <= 0:
            print("💀 骑士被击败！")
            break
    
    return knight.health <= 0
```

## 可视化功能

模拟器支持可视化模式，可以实时查看游戏状态：

```python
# 启用可视化
simulator.init_pygame()
simulator.run_simulation(max_duration=60.0, enable_visualization=True)

# 控制键：
# ESC - 退出模拟
# 空格 - 暂停/继续
# R - 重置模拟
```

## 调试功能

```python
# 获取统计信息
stats = simulator.get_statistics()
print(f"建筑数量: {stats['buildings_count']}")
print(f"工程师数量: {stats['engineers_count']}")

# 获取调试信息
debug_info = simulator.get_debug_info()
simulator.print_debug_info()

# 记录事件
simulator.log_event("测试事件发生")
```

## 预设测试场景

### 修复测试场景
- 主基地（500金币）
- 半血箭塔（需要修复）
- 工程师（自动修复）

### 战斗测试场景
- 完整箭塔
- 英雄骑士（120血量）
- 自动战斗逻辑

### 经济测试场景
- 主基地（1000金币）
- 金库（500存储）
- 工人（资源收集）

### 复杂测试场景
- 多个建筑（不同状态）
- 多个工程师
- 多个角色
- 完整的游戏环境

### 压力测试场景
- 大量建筑（100个）
- 大量工程师（20个）
- 性能测试

## 注意事项

1. **路径设置**: 确保正确设置Python路径
2. **依赖项**: 需要安装pygame用于可视化功能
3. **性能**: 压力测试场景可能消耗较多资源
4. **线程安全**: 模拟器不是线程安全的，避免多线程使用
5. **内存管理**: 长时间运行后建议调用`reset()`清理资源

## 扩展功能

可以通过继承`GameEnvironmentSimulator`类来添加自定义功能：

```python
class CustomSimulator(GameEnvironmentSimulator):
    def setup_custom_scenario(self):
        # 自定义测试场景
        pass
    
    def custom_update_logic(self, delta_time):
        # 自定义更新逻辑
        super().update(delta_time)
```

这个游戏环境模拟器为测试提供了完整的游戏环境，让测试更加真实和可靠。

