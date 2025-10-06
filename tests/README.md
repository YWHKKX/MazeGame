# 游戏环境模拟器快速学习指南

这是一个关键测试目录，包含用于验证游戏各种逻辑的测试文件。

## ⚠️ 重要说明

**这个tests目录里的测试为关键测试，只有在我特地说明的情况下才可以将测试移动到这个文件中，而且这里的测试不能被删除。**

## 🎯 核心设计原则

### 完全自动化原则
**所有测试必须完全自动化运行，禁止任何手动操作逻辑。**

- ✅ **允许**：自动检测、自动更新、自动渲染、自动统计
- ❌ **禁止**：键盘输入检测、手动触发方法、手动调试输出、手动控制逻辑
- 🎯 **目标**：测试应该能够独立运行，展示完整的游戏系统交互，无需任何人工干预

### 测试设计标准
1. **自动化运行**：测试完全自主运行指定时间
2. **真实API调用**：使用与真实游戏完全一致的API调用链
3. **系统集成完整**：所有相关系统（移动、战斗、建筑、资源等）自动运行
4. **数据统计准确**：自动收集详细的测试数据和结果
5. **代码简洁高效**：移除所有手动控制逻辑，保持代码简洁
6. **导入规范统一**：所有import语句必须统一放在文件顶部，禁止内联导入

## 🚀 快速开始

### 0. 字符编码设置（Windows用户必看）
```cmd
# 在运行任何测试前，先设置UTF-8编码
chcp 65001
```

### 1. 基础设置
```python
# 所有导入语句必须统一放在文件顶部
import sys
import os
import time
import math
import random
import pygame
import traceback

# 重要：必须先设置Python路径，再导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.core.constants import GameConstants
from src.utils.logger import game_logger

# 创建模拟器（推荐配置）
simulator = GameEnvironmentSimulator(
    screen_width=1200,
    screen_height=800,
    tile_size=GameConstants.TILE_SIZE,
    ui_scale=2.0  # 2倍放大，方便观察
)

# 初始化Pygame（可视化模式）
simulator.init_pygame()
```

### 2. 运行测试
```python
# 可视化模式（推荐）
simulator.run_simulation(max_duration=60.0, enable_visualization=True)

# 无头模式（性能测试）
simulator.run_simulation(max_duration=60.0, enable_visualization=False)
```

## 🏗️ 建筑系统API

### 通用建筑创建方法（推荐）
```python
# 使用通用建筑创建API - 支持所有建筑类型
building = simulator.create_building(x, y, building_type, completed=True, **kwargs)

# 示例：
# 地牢之心
dungeon_heart = simulator.create_building(10, 10, BuildingType.DUNGEON_HEART, stored_gold=500, stored_mana=100)

# 箭塔
arrow_tower = simulator.create_building(15, 10, BuildingType.ARROW_TOWER, ammunition=60)

# 魔法祭坛
magic_altar = simulator.create_building(20, 10, BuildingType.MAGIC_ALTAR, stored_gold=30, stored_mana=50)

# 兽人巢穴
orc_lair = simulator.create_building(25, 10, BuildingType.ORC_LAIR, stored_gold=40)

# 恶魔巢穴
demon_lair = simulator.create_building(30, 10, BuildingType.DEMON_LAIR, stored_gold=35)
```

### 便捷建筑创建方法
```python
# 主基地（地牢之心）
dungeon_heart = simulator.create_dungeon_heart(x=10, y=10, gold=500, completed=True)

# 箭塔
arrow_tower = simulator.create_arrow_tower(x=15, y=10, ammunition=60, completed=True)

# 奥术塔
arcane_tower = simulator.create_arcane_tower(x=20, y=10, completed=True)

# 金库
treasury = simulator.create_treasury(x=25, y=10, stored_gold=0, completed=True)

# 兽人巢穴
orc_lair = simulator.create_orc_lair(x=30, y=10, stored_gold=0, completed=True)

# 恶魔巢穴
demon_lair = simulator.create_demon_lair(x=35, y=10, stored_gold=0, completed=True)

# 魔法祭坛
magic_altar = simulator.create_magic_altar(x=40, y=10, stored_gold=0, stored_mana=0, completed=True)

# 其他建筑
training_room = simulator.create_training_room(x=45, y=10, completed=True)
library = simulator.create_library(x=50, y=10, completed=True)
prison = simulator.create_prison(x=55, y=10, completed=True)
fortification = simulator.create_defense_fortification(x=60, y=10, completed=True)
```

### 建筑特定参数支持
```python
# 地牢之心参数
dungeon_heart = simulator.create_building(10, 10, BuildingType.DUNGEON_HEART, 
                                        stored_gold=500, stored_mana=100)

# 箭塔参数
arrow_tower = simulator.create_building(15, 10, BuildingType.ARROW_TOWER, 
                                      ammunition=60)

# 金库参数
treasury = simulator.create_building(20, 10, BuildingType.TREASURY, 
                                   stored_gold=200)

# 魔法祭坛参数
magic_altar = simulator.create_building(25, 10, BuildingType.MAGIC_ALTAR, 
                                      stored_gold=30, stored_mana=50)

# 兽人巢穴/恶魔巢穴参数
orc_lair = simulator.create_building(30, 10, BuildingType.ORC_LAIR, 
                                   stored_gold=40)
demon_lair = simulator.create_building(35, 10, BuildingType.DEMON_LAIR, 
                                     stored_gold=35)
```

### 建筑操作
```python
# 对建筑造成伤害
simulator.damage_building(building, damage=50)

# 治疗建筑
simulator.heal_building(building, heal_amount=30)

# 获取建筑
building = simulator.get_building_at(x=15, y=10)
building = simulator.get_building_by_name("箭塔")
```

## 👥 角色系统API

### 创建角色
```python
# 工程师
engineer = simulator.create_engineer(x=12.0, y=12.0, engineer_type=EngineerType.BASIC)

# 工人
worker = simulator.create_worker(x=15.0, y=15.0)

# 英雄
knight = simulator.create_hero(x=200.0, y=200.0, hero_type='knight')

# 生物
goblin = simulator.create_creature(x=100.0, y=100.0, creature_type='goblin')
```

### 角色移动
```python
# 设置角色位置
simulator.set_character_position(character, x=20.0, y=20.0)

# 设置持续移动目标（推荐使用）
simulator.set_character_movement_target(
    character, 
    target_x=30.0, 
    target_y=30.0, 
    speed=50.0, 
    tolerance=5.0
)

# 单帧移动
simulator.move_character_to(character, target_x=40.0, target_y=40.0, speed=30.0)
```

### 角色查找
```python
# 按位置查找
engineer = simulator.get_engineer_at(x=12.0, y=12.0, tolerance=1.0)

# 按名称查找
engineer = simulator.get_engineer_by_name("工程师")
hero = simulator.get_hero_by_name("骑士")
building = simulator.get_building_by_name("箭塔")
```

## 🗺️ 地图系统API

### 地图操作
```python
# 生成空白地图
simulator.generate_blank_map(width=30, height=20)

# 生成随机地图
simulator.generate_random_map(gold_mine_count=10, rock_count=20, wall_count=15)

# 添加金矿
gold_mine = simulator.add_gold_mine(x=5, y=5, gold_amount=100)

# 添加岩石/墙壁
simulator.add_rock_tile(x=10, y=10)
simulator.add_wall_tile(x=15, y=15)

# 清空地图
simulator.clear_map()
```

### 🎯 地图生成与相机控制技巧

#### **默认地牢之心位置**
```python
# 计算地图中心瓦片坐标
map_width = 30
map_height = 20
map_center_x = map_width // 2  # 15
map_center_y = map_height // 2  # 10

# 创建地牢之心在地图中心
dungeon_heart = simulator.create_dungeon_heart(
    x=map_center_x, 
    y=map_center_y, 
    gold=1000, 
    completed=True
)
```

#### **地图尺寸选择**
- **小地图**：`20x15` - 适合快速测试
- **中地图**：`30x20` - 平衡性能和视野
- **大地图**：`50x30` - 完整游戏体验

#### **相机控制核心公式**
```python
# 屏幕中心计算（考虑UI缩放）
screen_center_x = screen_width // 2 // ui_scale
screen_center_y = screen_height // 2 // ui_scale

# 地牢之心像素坐标
dungeon_heart_pixel_x = map_center_x * TILE_SIZE + TILE_SIZE // 2
dungeon_heart_pixel_y = map_center_y * TILE_SIZE + TILE_SIZE // 2

# 相机位置 = 地牢之心位置 - 屏幕中心位置
camera_x = dungeon_heart_pixel_x - screen_center_x
camera_y = dungeon_heart_pixel_y - screen_center_y

# 设置相机位置
simulator.set_camera_position(x=camera_x, y=camera_y)
```

#### **常用屏幕尺寸的相机位置**
```python
# 1200x800, UI缩放2.0x
screen_center_x = 300
screen_center_y = 200

# 1600x900, UI缩放2.0x  
screen_center_x = 400
screen_center_y = 225

# 1920x1080, UI缩放2.0x
screen_center_x = 480
screen_center_y = 270
```

#### **建筑和单位布局技巧**
```python
# 地牢之心周围建筑布局
dungeon_heart_x = 15
dungeon_heart_y = 10

# 建筑间隔距离（瓦片单位）
BUILDING_SPACING = 3

# 创建建筑
buildings = [
    (dungeon_heart_x + BUILDING_SPACING, dungeon_heart_y),      # 右侧
    (dungeon_heart_x - BUILDING_SPACING, dungeon_heart_y),      # 左侧
    (dungeon_heart_x, dungeon_heart_y + BUILDING_SPACING),      # 下方
    (dungeon_heart_x, dungeon_heart_y - BUILDING_SPACING),      # 上方
]

for x, y in buildings:
    simulator.create_building(x=x, y=y, building_type="treasury")
```

#### **单位创建坐标转换**
```python
# 瓦片坐标转像素坐标
def tile_to_pixel(tile_x, tile_y, offset_x=0, offset_y=0):
    """瓦片坐标转像素坐标，支持偏移"""
    pixel_x = tile_x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2 + offset_x
    pixel_y = tile_y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2 + offset_y
    return pixel_x, pixel_y

# 创建单位示例
engineer_pixel_x, engineer_pixel_y = tile_to_pixel(15, 10, offset_x=20, offset_y=20)
engineer = simulator.create_engineer(
    x=engineer_pixel_x, 
    y=engineer_pixel_y
)
```

#### **完整的地图生成模板**
```python
class MapGenerator:
    def __init__(self, simulator, ui_scale=2.0):
        self.simulator = simulator
        self.ui_scale = ui_scale
        self.screen_width = 1200
        self.screen_height = 800
        
    def generate_centered_map(self, width=30, height=20):
        """生成以地牢之心为中心的地图"""
        # 1. 生成空白地图
        self.simulator.generate_blank_map(width=width, height=height)
        
        # 2. 计算地图中心
        map_center_x = width // 2
        map_center_y = height // 2
        
        # 3. 创建地牢之心
        dungeon_heart = self.simulator.create_dungeon_heart(
            x=map_center_x, 
            y=map_center_y, 
            gold=1000, 
            completed=True
        )
        
        # 4. 设置相机位置
        self._center_camera_on_dungeon_heart(map_center_x, map_center_y)
        
        return dungeon_heart, map_center_x, map_center_y
    
    def _center_camera_on_dungeon_heart(self, map_center_x, map_center_y):
        """将相机居中到地牢之心"""
        # 计算屏幕中心（考虑UI缩放）
        screen_center_x = self.screen_width // 2 // self.ui_scale
        screen_center_y = self.screen_height // 2 // self.ui_scale
        
        # 计算地牢之心像素坐标
        dungeon_heart_pixel_x = map_center_x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        dungeon_heart_pixel_y = map_center_y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        
        # 计算相机位置
        camera_x = dungeon_heart_pixel_x - screen_center_x
        camera_y = dungeon_heart_pixel_y - screen_center_y
        
        # 设置相机位置
        self.simulator.set_camera_position(x=camera_x, y=camera_y)
    
    def create_building_around_dungeon_heart(self, map_center_x, map_center_y, 
                                           building_type, spacing=3):
        """在地牢之心周围创建建筑"""
        positions = [
            (map_center_x + spacing, map_center_y),      # 右
            (map_center_x - spacing, map_center_y),      # 左
            (map_center_x, map_center_y + spacing),      # 下
            (map_center_x, map_center_y - spacing),      # 上
        ]
        
        buildings = []
        for x, y in positions:
            building = self.simulator.create_building(
                x=x, y=y, building_type=building_type
            )
            buildings.append(building)
        
        return buildings
    
    def create_units_around_dungeon_heart(self, map_center_x, map_center_y, 
                                        unit_type, count=1, spacing=2):
        """在地牢之心周围创建单位"""
        units = []
        for i in range(count):
            # 计算单位位置（像素坐标）
            angle = (i * 360 / count) * math.pi / 180
            offset_x = math.cos(angle) * spacing * GameConstants.TILE_SIZE
            offset_y = math.sin(angle) * spacing * GameConstants.TILE_SIZE
            
            pixel_x = map_center_x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2 + offset_x
            pixel_y = map_center_y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2 + offset_y
            
            # 创建单位
            unit = self.simulator.create_unit(
                x=pixel_x, y=pixel_y, unit_type=unit_type
            )
            units.append(unit)
        
        return units
```

#### **关键注意事项**
- **坐标系统**：瓦片坐标用于建筑创建（整数），像素坐标用于单位创建（浮点）
- **转换公式**：`像素坐标 = 瓦片坐标 * TILE_SIZE + TILE_SIZE // 2`
- **UI缩放影响**：相机位置计算必须考虑UI缩放，屏幕中心 = `屏幕尺寸 / 2 / UI缩放`
- **布局最佳实践**：建筑间隔至少3个瓦片，单位间隔至少2个瓦片，地牢之心周围留出足够空间

## 🎮 相机系统API

### 相机控制
```python
# 移动相机
simulator.move_camera(dx=50, dy=0)

# 设置相机位置
simulator.set_camera_position(x=100, y=100)

# 获取相机位置
camera_x, camera_y = simulator.get_camera_position()

# 相机居中
simulator.center_camera_on_position(world_x=200, world_y=200)
simulator.center_camera_on_tile(tile_x=10, tile_y=10)
```

### UI缩放
```python
# 设置UI缩放
simulator.set_ui_scale(scale=2.0)

# 获取UI缩放
scale = simulator.get_ui_scale()

# 强制重绘UI
simulator.force_ui_redraw()
```

## ⚔️ 战斗系统API

### 攻击模拟
```python
# 模拟攻击
success = simulator.simulate_attack(attacker, target, damage=20.0, attack_type="normal")

# 应用击退效果（新固定距离机制）
success = simulator.apply_knockback(attacker, target, attack_damage=20.0, attack_type="normal")

# 处理单位被攻击响应
simulator.handle_unit_attacked_response(attacker, target, damage=20.0)
```

### 击退系统API（新固定距离机制）

#### 击退类型配置
```python
from src.core.enums import KnockbackType

# 设置单位击退类型
unit.knockback_type = KnockbackType.STRONG    # 强击退
unit.knockback_type = KnockbackType.NORMAL    # 普通击退
unit.knockback_type = KnockbackType.WEAK      # 弱击退
unit.knockback_type = KnockbackType.NONE      # 无击退
```

#### 箭塔击退配置
```python
# 创建箭塔
arrow_tower = simulator.create_arrow_tower(x=15, y=10, ammunition=60)

# 设置击退类型
arrow_tower.set_knockback_type(KnockbackType.STRONG)  # 强制强击退
arrow_tower.set_knockback_type(KnockbackType.NORMAL)  # 强制普通击退

# 获取击退信息
info = arrow_tower.get_knockback_info()
print(f"可用击退类型: {info['available_types']}")
print(f"击退距离: {info['distances']}")
```

#### 击退距离常量
```python
from src.core.constants import GameConstants

# 固定击退距离
weak_distance = GameConstants.KNOCKBACK_DISTANCE_WEAK      # 8像素
normal_distance = GameConstants.KNOCKBACK_DISTANCE_NORMAL  # 15像素
strong_distance = GameConstants.KNOCKBACK_DISTANCE_STRONG  # 30像素
```

### 碰撞检测
```python
# 检查碰撞
collision = simulator.check_collision(unit1, unit2)

# 解决碰撞
simulator.resolve_collision(unit1, unit2)

# 检测所有碰撞
collisions = simulator.detect_all_collisions()
```

## 🎨 特效系统API

### 粒子特效
```python
# 创建粒子特效
simulator.create_particle_effect(
    x=100.0, y=100.0, 
    particle_count=10, 
    color=(255, 255, 255)
)

# 清除所有特效
simulator.clear_all_effects()
```

## 📊 测试辅助API

### 等待条件
```python
# 等待条件满足
def check_repair_complete():
    return damaged_tower.health >= damaged_tower.max_health

success = simulator.wait_for_condition(check_repair_complete, timeout=30.0)
```

### 统计信息
```python
# 获取统计信息
stats = simulator.get_statistics()
game_logger.info(f"建筑数量: {stats['buildings_count']}")
game_logger.info(f"工程师数量: {stats['engineers_count']}")

# 获取调试信息
debug_info = simulator.get_debug_info()
```

### 日志记录
```python
# 记录事件
simulator.log_event("测试事件发生")

# 使用统一日志系统
from src.utils.logger import game_logger

# 不同级别的日志
game_logger.info("信息日志")
game_logger.warning("警告日志")
game_logger.error("错误日志")
game_logger.debug("调试日志")  # 在DEBUG模式下会显示函数名
```

## 🎯 预设测试场景

### 快速场景设置
```python
# 建筑修复测试场景
simulator.setup_repair_test_scenario()

# 战斗测试场景
simulator.setup_combat_test_scenario()

# 经济测试场景
simulator.setup_economy_test_scenario()

# 复杂测试场景
simulator.setup_complex_test_scenario()

# 压力测试场景
simulator.setup_stress_test_scenario()

# 物理系统测试场景
simulator.setup_physics_test_scenario()

# 特效系统测试场景
simulator.setup_effects_test_scenario()

# 综合测试场景
simulator.setup_comprehensive_test_scenario()
```

## 🎮 事件处理API

### 键盘控制
```python
# 处理相机输入（WASD移动）
simulator.handle_camera_input(event)

# 处理UI缩放输入（+/-调整，0重置）
simulator.handle_ui_scale_input(event)

# 处理所有事件
should_continue = simulator.handle_events()
```

### 模拟控制
```python
# 暂停/恢复
simulator.pause()
simulator.resume()

# 重置模拟
simulator.reset()
```

## 🔧 高级功能

### 自定义更新逻辑
```python
# 自定义更新（在run_simulation之前）
def custom_update(delta_time):
    # 自定义逻辑
    simulator.update(delta_time)

# 运行自定义模拟
simulator.run_simulation(max_duration=60.0, enable_visualization=True)
```

### 性能监控
```python
# 获取物理系统统计
physics_stats = simulator.get_physics_stats()

# 获取特效系统统计
effects_stats = simulator.get_effects_stats()
```

## 📝 常用测试模式

### 1. 基础功能测试（完全自动化）
```python
# 所有导入语句统一放在文件顶部
import sys
import os
import time
import pygame
import traceback

# 重要：必须先设置Python路径，再导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.utils.logger import game_logger

def test_basic_functionality():
    simulator = GameEnvironmentSimulator()
    simulator.init_pygame()
    
    # 创建测试对象
    dungeon_heart = simulator.create_dungeon_heart(10, 10, 500)
    engineer = simulator.create_engineer(12, 12)
    
    # 完全自动化运行 - 无手动控制
    simulator.run_simulation(max_duration=30.0, enable_visualization=True)
```

### 2. 战斗测试（完全自动化）
```python
# 所有导入语句统一放在文件顶部
import sys
import os
import time
import pygame
import traceback

# 重要：必须先设置Python路径，再导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.utils.logger import game_logger

def test_combat():
    simulator = GameEnvironmentSimulator()
    simulator.init_pygame()
    
    # 设置战斗场景
    simulator.setup_combat_test_scenario()
    
    # 完全自动化运行 - 系统自动处理战斗逻辑
    simulator.run_simulation(max_duration=20.0, enable_visualization=True)
```

### 3. 建筑修复测试（完全自动化）
```python
# 所有导入语句统一放在文件顶部
import sys
import os
import time
import pygame
import traceback

# 重要：必须先设置Python路径，再导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.utils.logger import game_logger

def test_repair():
    simulator = GameEnvironmentSimulator()
    simulator.init_pygame()
    
    # 设置修复场景
    simulator.setup_repair_test_scenario()
    
    # 完全自动化运行 - 工程师自动修复建筑
    simulator.run_simulation(max_duration=30.0, enable_visualization=True)
```

## 🎨 可视化说明

### 颜色编码
- **红色建筑**：主基地（地牢之心）
- **黄色/红色建筑**：损坏的建筑（根据血量显示颜色）
- **蓝色圆圈**：工程师
- **绿色圆圈**：工人
- **灰色圆圈**：英雄
- **绿色/红色血条**：建筑血量指示器
- **黄色文字**：工程师携带的金币数量

### 控制键
- **WASD**：相机移动
- **+/-**：UI缩放调整
- **0**：重置UI缩放
- **空格**：暂停/恢复
- **R**：重置模拟
- **ESC**：退出

## 📝 统一日志系统

### 日志系统概述
项目使用统一的日志系统，所有模块都通过 `game_logger` 进行日志记录，确保日志格式一致性和可维护性。

### 基本使用
```python
# 所有导入语句统一放在文件顶部
import sys
import os
import time
import pygame
import traceback

from src.utils.logger import game_logger

# 不同级别的日志
game_logger.info("普通信息")           # 显示时间戳和消息
game_logger.warning("警告信息")        # 显示时间戳和警告标识
game_logger.error("错误信息")          # 显示时间戳和错误标识
game_logger.debug("调试信息")          # 在DEBUG模式下显示函数名和类名
```

### 日志级别
- **INFO**: 一般信息，如系统状态、操作结果
- **WARNING**: 警告信息，如配置问题、性能警告
- **ERROR**: 错误信息，如异常、失败操作
- **DEBUG**: 调试信息，包含调用函数名和类名（仅在DEBUG模式）

### 日志格式
```
[时间戳] [级别] [模块名] 消息内容
[14:06:25.395] [INFO] [MazeMaster] ✅ Windows编码设置完成
[14:06:25.415] [WARNING] [MazeMaster] ⚠️ 建筑系统不可用
[14:06:25.423] [ERROR] [MazeMaster] ❌ 游戏运行失败
[14:06:25.430] [DEBUG] [MazeMaster] [函数名] 调试信息
```

### 在测试中使用
```python
# 所有导入语句统一放在文件顶部
import sys
import os
import time
import pygame
import traceback

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.utils.logger import game_logger

# 测试开始时记录
game_logger.info("🚀 开始新建造功能测试")

# 测试过程中记录状态
game_logger.info(f"📊 测试进度: {progress}%")

# 测试结果记录
game_logger.info("✅ 测试通过" if success else "❌ 测试失败")

# 调试信息（仅在需要时）
game_logger.debug("详细调试信息")
```

### 注意事项
1. **统一使用**: 所有模块必须使用 `game_logger`，不要使用 `print()`
2. **级别选择**: 根据信息重要性选择合适的日志级别
3. **消息格式**: 使用emoji和清晰的中文描述，便于阅读
4. **性能考虑**: DEBUG日志仅在调试时启用，避免影响性能
5. **导入方式**: 使用 `from src.utils.logger import game_logger`
6. **导入规范**: 所有import语句必须统一放在文件顶部，禁止内联导入

## 🔤 字符编码问题解决方案

### 问题描述
在Windows环境下运行测试时，可能会遇到Unicode字符（特别是emoji）显示问题：
```
UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f680' in position 40: illegal multibyte sequence
```

### 解决方案

#### **方案1：设置代码页（推荐）**
```cmd
chcp 65001
python tests/your_test.py
```

#### **方案2：环境变量设置**
```bash
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1
chcp 65001
python tests/your_test.py
```

#### **方案3：创建批处理文件**
```batch
@echo off
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=1
chcp 65001
python tests/your_test.py
pause
```

#### **方案4：测试代码优化**
```python
# 避免使用emoji，使用ASCII字符替代
game_logger.info("[START] 启动测试")  # 而不是 🚀
game_logger.info("[SUCCESS] 测试完成")  # 而不是 ✅
```

### 为什么 `chcp 65001` 后出现乱码

**根本原因**：
1. **时机问题**：`chcp 65001` 只影响新启动的控制台窗口
2. **Python进程**：`sys.stdout.encoding` 在 Python 启动时已确定
3. **字体冲突**：UTF-8 控制台与某些中文字体渲染不兼容

### 效果对比
| 设置前                     | 设置后                       |
| -------------------------- | ---------------------------- |
| `sys.stdout.encoding: gbk` | `sys.stdout.encoding: utf-8` |
| emoji显示为 `???`          | emoji正常显示 `🚀`            |
| 日志输出报错               | 日志正常输出                 |
| 测试无法运行               | 测试正常运行                 |

### 最佳实践
1. **运行测试前先设置代码页**：`chcp 65001`
2. **为每个测试创建批处理文件**，自动设置编码
3. **在IDE中配置终端编码为UTF-8**
4. **测试代码使用ASCII字符**，避免emoji编码问题

## ⚠️ 注意事项

1. **完全自动化原则**：所有测试必须完全自动化，禁止任何手动操作逻辑
2. **统一日志系统**：所有日志必须使用 `game_logger`，禁止使用 `print()`
3. **导入规范统一**：所有import语句必须统一放在文件顶部，禁止内联导入
4. **容错机制（推荐）**：使用 try-except 处理导入错误，提供自动修复功能
5. **字符编码设置**：Windows环境下运行测试前请先执行 `chcp 65001` 设置UTF-8编码
6. **路径设置**：确保正确设置Python路径，推荐使用容错机制
7. **依赖项**：需要安装pygame用于可视化功能
8. **性能**：压力测试场景可能消耗较多资源
9. **线程安全**：模拟器不是线程安全的，避免多线程使用
10. **内存管理**：长时间运行后建议调用`reset()`清理资源
11. **建筑状态**：确保测试中的建筑状态设置正确，避免优先级冲突

## 🔧 导入规范详解

**核心原则：必须先设置Python路径，再导入项目模块**

这是避免 `ModuleNotFoundError: No module named 'src'` 错误的关键原则。Python解释器在导入模块时会按照 `sys.path` 中的路径顺序查找模块，因此必须在导入项目模块之前将项目根目录添加到 `sys.path` 中。

### 🛡️ 容错机制：使用 try-except 解决导入问题

**推荐方案**：使用 try-except 机制处理导入错误，提供自动修复功能：

```python
# 设置Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 使用try-except处理导入错误（推荐）
try:
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
    from src.core.constants import GameConstants
    from src.utils.logger import game_logger
except ImportError as e:
    print(f"导入错误: {e}")
    print("正在尝试修复路径问题...")
    # 重新设置路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # 再次尝试导入
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
    from src.core.constants import GameConstants
    from src.utils.logger import game_logger
```

**优势**：
- ✅ **健壮性**：即使路径设置有问题，也能自动修复
- ✅ **用户友好**：提供清晰的错误信息和修复过程
- ✅ **向后兼容**：不影响正常情况下的导入
- ✅ **调试友好**：帮助开发者快速定位和解决问题

### 常见导入错误

#### **错误示例**：
```python
# ❌ 错误：先导入项目模块，后设置路径
from src.managers.game_environment_simulator import GameEnvironmentSimulator
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
```

#### **正确示例**：
```python
# ✅ 正确：先设置路径，再导入项目模块
import sys
import os
import time
import math
import random
import pygame
import traceback

# 重要：必须先设置Python路径，再导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.core.constants import GameConstants
from src.utils.logger import game_logger
```

### 快速导入模板

#### **完整测试文件模板（推荐 - 带容错机制）**：
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件描述
"""

# 所有导入语句统一放在文件顶部
import sys
import os
import time
import math
import random
import pygame
import traceback

# 设置Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 使用try-except处理导入错误（推荐）
try:
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
    from src.core.constants import GameConstants
    from src.utils.logger import game_logger
except ImportError as e:
    print(f"导入错误: {e}")
    print("正在尝试修复路径问题...")
    # 重新设置路径
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # 再次尝试导入
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
    from src.core.constants import GameConstants
    from src.utils.logger import game_logger

def main():
    """主测试函数"""
    # 创建模拟器
    simulator = GameEnvironmentSimulator(
        screen_width=1200,
        screen_height=800,
        tile_size=GameConstants.TILE_SIZE,
        ui_scale=2.0
    )
    
    # 初始化Pygame
    simulator.init_pygame()
    
    # 运行测试
    simulator.run_simulation(max_duration=60.0, enable_visualization=True)

if __name__ == "__main__":
    main()
```

#### **简化测试文件模板（基础版本）**：
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文件描述
"""

# 所有导入语句统一放在文件顶部
import sys
import os
import time
import math
import random
import pygame
import traceback

# 重要：必须先设置Python路径，再导入项目模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.core.constants import GameConstants
from src.utils.logger import game_logger

def main():
    """主测试函数"""
    # 创建模拟器
    simulator = GameEnvironmentSimulator(
        screen_width=1200,
        screen_height=800,
        tile_size=GameConstants.TILE_SIZE,
        ui_scale=2.0
    )
    
    # 初始化Pygame
    simulator.init_pygame()
    
    # 运行测试
    simulator.run_simulation(max_duration=60.0, enable_visualization=True)

if __name__ == "__main__":
    main()
```

### 导入规范要点

1. **标准库导入**：`sys`, `os`, `time`, `math`, `random`, `pygame`, `traceback`
2. **路径设置**：`sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))`
3. **项目模块导入**：`from src.xxx import xxx`
4. **顺序要求**：标准库 → 路径设置 → 项目模块
5. **禁止内联导入**：不要在函数内部使用 import 语句

## 🔍 调试技巧

### 1. 启用详细日志（自动化调试）
```python
# 在创建模拟器后添加
simulator.debug_mode = True
```

### 2. 监控特定对象（自动化监控）
```python
# 所有导入语句统一放在文件顶部
import sys
import os
import time
import pygame
import traceback

from src.managers.game_environment_simulator import GameEnvironmentSimulator
from src.utils.logger import game_logger

# 定期检查对象状态 - 自动执行，无需手动触发
if frame_count % 60 == 0:  # 每秒检查一次
    game_logger.info(f"工程师状态: {engineer.status}")
    game_logger.info(f"建筑血量: {building.health}/{building.max_health}")
    
# 使用统一日志系统记录调试信息
game_logger.debug(f"详细状态: {detailed_info}")  # 仅在DEBUG模式显示
```

### 3. 使用预设场景（完全自动化）
```python
# 使用预设场景可以快速开始测试 - 所有逻辑自动运行
simulator.setup_repair_test_scenario()  # 包含所有必要的测试对象
```

### 4. 自动化测试最佳实践
- **避免手动控制**：不要添加键盘输入检测或手动触发方法
- **使用真实API**：直接调用游戏系统的真实API，不要绕过
- **自动数据收集**：让系统自动收集测试数据，不要手动统计
- **完整系统集成**：确保所有相关系统都能自动运行
- **统一日志记录**：使用 `game_logger` 记录所有测试信息，不要使用 `print()`
- **导入规范统一**：所有import语句统一放在文件顶部，禁止在函数内部使用import
- **路径设置优先**：必须先设置Python路径，再导入项目模块，避免 `ModuleNotFoundError`

## 📚 扩展阅读

- `src/managers/game_environment_simulator.py` - 模拟器主文件
- `src/utils/logger.py` - 统一日志系统实现
- `tests/arcane_tower_attack_simulator.py` - 奥术塔攻击测试示例
- `tests/arrow_tower_attack_simulator.py` - 箭塔攻击测试示例
- `tests/repair_test_with_simulator.py` - 建筑修复测试示例

---

## 🆕 最新API更新说明

### 击退系统重构（固定距离机制）

**新击退系统特点**：
- ✅ **固定距离机制**: 使用预定义的击退距离（弱8px/普通15px/强30px）
- ✅ **击退类型选择**: 单位可以选择不同的击退强度
- ✅ **简化计算**: 移除复杂的动态计算，提高性能
- ✅ **箭塔集成**: 箭塔支持动态击退类型选择

**击退类型枚举**：
```python
from src.core.enums import KnockbackType

KnockbackType.NORMAL  # 普通击退 (15像素)
KnockbackType.STRONG  # 强击退 (30像素)
KnockbackType.WEAK    # 弱击退 (8像素)
KnockbackType.NONE    # 无击退 (0像素)
```

**箭塔击退配置**：
```python
# 设置击退类型
arrow_tower.set_knockback_type(KnockbackType.STRONG)

# 获取击退信息
info = arrow_tower.get_knockback_info()
```

### 建筑创建API变化

**新增通用建筑创建方法**：
```python
# 新的推荐方式 - 支持所有建筑类型
building = simulator.create_building(x, y, building_type, completed=True, **kwargs)
```

**新增便捷建筑创建方法**：
```python
# 兽人巢穴
orc_lair = simulator.create_orc_lair(x, y, stored_gold=0, completed=True)

# 恶魔巢穴
demon_lair = simulator.create_demon_lair(x, y, stored_gold=0, completed=True)

# 魔法祭坛
magic_altar = simulator.create_magic_altar(x, y, stored_gold=0, stored_mana=0, completed=True)
```

**建筑特定参数支持**：
- `stored_gold`: 地牢之心、金库、魔法祭坛、兽人巢穴、恶魔巢穴
- `stored_mana`: 地牢之心、魔法祭坛
- `ammunition`: 箭塔
- `training_queue`: 训练室
- `research_queue`: 图书馆
- `prisoner_capacity`: 监狱
- `defense_bonus`: 防御工事

**自动资源管理**：
- 自动检查资源是否足够
- 自动消耗建筑成本
- 自动注册到资源管理器
- 自动设置特殊建筑引用

### 测试文件更新

所有测试文件已更新为使用最新的建筑创建API：
- `building_showcase_simulator.py` - 使用通用建筑创建API
- `new_buildings_test_simulator.py` - 使用便捷建筑创建方法
- `repair_test_with_simulator.py` - 保持现有API（向后兼容）
- `arrow_tower_attack_simulator.py` - 保持现有API（向后兼容）

## 🎯 核心原则总结

**完全自动化，不要手动生成逻辑**

- ✅ **自动化运行**：测试完全自主运行，展示完整系统交互
- ✅ **真实API调用**：使用与真实游戏一致的API调用链
- ✅ **系统集成完整**：所有相关系统自动运行
- ✅ **统一日志系统**：使用 `game_logger` 记录所有信息，确保日志一致性
- ✅ **导入规范统一**：所有import语句统一放在文件顶部，禁止内联导入
- ✅ **路径设置优先**：必须先设置Python路径，再导入项目模块（避免ModuleNotFoundError）
- ✅ **容错机制**：使用 try-except 处理导入错误，提供自动修复功能
- ✅ **最新API使用**：优先使用新的通用建筑创建API
- ❌ **禁止手动控制**：键盘输入、手动触发、手动调试等
- ❌ **禁止绕过系统**：不要绕过游戏的真实逻辑
- ❌ **禁止使用print**：不要使用 `print()` 输出信息，必须使用 `game_logger`
- ❌ **禁止内联导入**：不要在函数内部使用import语句
- ❌ **禁止错误导入顺序**：不要先导入项目模块，后设置路径

**记住**：这个README是快速学习指南，每次创建新测试时都应该先阅读这个文件，了解可用的API和最佳实践。**最重要的是遵循完全自动化原则、统一日志系统和导入规范统一，确保测试能够独立运行，无需任何人工干预。**

### 导入规范检查清单

在创建新测试文件时，请确保：

1. ✅ **标准库导入在前**：`import sys`, `import os`, `import time` 等
2. ✅ **路径设置优先**：`sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))`（必须在项目模块导入之前）
3. ✅ **项目模块导入在后**：`from src.xxx import xxx`
4. ✅ **所有导入在文件顶部**：不要在函数内部使用 import
5. ✅ **使用完整测试模板**：复制上面的完整测试文件模板（推荐带容错机制版本）
6. ✅ **避免ModuleNotFoundError**：确保路径设置在项目模块导入之前，这是避免 `ModuleNotFoundError: No module named 'src'` 的关键
7. ✅ **容错机制（推荐）**：使用 try-except 处理导入错误，提供自动修复功能
8. ✅ **错误处理**：在 except 块中重新设置路径并再次尝试导入