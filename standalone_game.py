#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
War for the Overworld - 独立Python版本
基于index.html的逻辑，不依赖浏览器运行
"""

import pygame
import sys
import math
import random
import time
import os
import locale
from typing import List, Dict, Optional, Tuple, Any

# 导入重构后的模块
from src.core.constants import GameConstants, GameBalance
from src.core.enums import TileType, BuildMode
from src.core.game_state import Tile, GameState
from src.core import emoji_constants
from src.entities.configs import CreatureConfig, HeroConfig
from src.entities.creature import Creature
from src.entities.goblin_worker import GoblinWorker
from src.entities.goblin_engineer import Engineer, EngineerType
from src.entities.hero import Hero
from src.managers.movement_system import MovementSystem
from src.managers.font_manager import UnifiedFontManager
from src.managers.tile_manager import tile_manager
from src.ui.game_ui import GameUI
from src.ui.monster_selection import MonsterSelectionUI
from src.ui.logistics_selection import LogisticsSelectionUI

# 设置控制台编码，解决Windows中文和emoji显示问题
if sys.platform.startswith('win'):
    try:
        # 强制设置控制台为UTF-8编码
        os.system('chcp 65001 > nul 2>&1')
        # 设置环境变量，确保Python使用UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '1'  # 强制UTF-8输出
        # 设置locale
        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
        print("✅ Windows编码设置完成")
    except Exception as e:
        try:
            # 如果UTF-8失败，尝试GBK编码
            locale.setlocale(locale.LC_ALL, 'zh_CN.GBK')
            print("⚠️ 使用GBK编码")
        except:
            print("⚠️ 编码设置失败，使用系统默认")
            pass  # 如果都失败，继续运行
else:
    # 非Windows系统的编码设置
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except:
            pass

# 导入角色图鉴系统
try:
    from src.ui.character_bestiary import CharacterBestiary
    from src.entities.character_data import character_db
    BESTIARY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 角色图鉴系统不可用: {e}")
    BESTIARY_AVAILABLE = False


# 创建全局统一字体管理器实例
font_manager = UnifiedFontManager()

# 为了向后兼容，创建emoji_manager别名，使用emoji常量模块
emoji_manager = emoji_constants

# 导入状态指示器系统
try:
    from src.ui.status_indicator import StatusIndicator
    STATUS_INDICATOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 状态指示器系统不可用: {e}")
    STATUS_INDICATOR_AVAILABLE = False

# 导入建筑系统
try:
    from src.managers.building_manager import BuildingManager
    from src.ui.building_ui import BuildingUI
    from src.entities.building import BuildingType, BuildingRegistry
    from src.entities.goblin_engineer import EngineerType, EngineerRegistry
    BUILDING_SYSTEM_AVAILABLE = True
    print("🏗️ 建筑系统已加载")
except ImportError as e:
    print(f"⚠️ 建筑系统不可用: {e}")
    BUILDING_SYSTEM_AVAILABLE = False

# 初始化pygame
pygame.init()

# 设置输入法兼容性
pygame.key.set_repeat(500, 50)  # 设置按键重复延迟，有助于输入法兼容


class WarForTheOverworldGame:
    def __init__(self):
        """初始化游戏"""
        print(f"{emoji_manager.ROCKET} War for the Overworld - Python独立版本")
        print("=" * 60)

        # 初始化pygame
        self.screen = pygame.display.set_mode(
            (GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT))
        pygame.display.set_caption("War for the Overworld - 地下城争夺战")
        self.clock = pygame.time.Clock()

        # 游戏状态
        self.game_state = GameState()

        # 资源累积器 - 用于处理小的增量
        self.gold_accumulator = 0.0
        self.mana_accumulator = 0.0

        # 重新渲染标志
        self._pending_rerender = False

        # 游戏实体和位置（在地图初始化之前）
        self.creatures: List[Creature] = []
        self.heroes: List[Hero] = []
        self.dungeon_heart_pos = (0, 0)
        self.hero_bases = []

        # 特效系统 - 使用可视化版本提供真正的视觉效果
        try:
            from src.effects.visual_effect_manager import VisualEffectManager
            # 使用2倍速度初始化，斩击类特效会额外加速1倍（总共2倍速度）
            self.effect_manager = VisualEffectManager(speed_multiplier=2.0)
            print(f"{emoji_manager.SPARKLES} 可视化特效系统初始化成功 (速度: 2.0x，斩击特效: 2.0x)")
        except ImportError as e:
            print(f"⚠️ 可视化特效系统导入失败，使用简化版本: {e}")
            try:
                from src.effects.simple_effect_manager import SimpleEffectManager
                self.effect_manager = SimpleEffectManager()
                print(f"{emoji_manager.SPARKLES} 简化特效系统初始化成功")
            except ImportError as e2:
                print(f"❌ 特效系统导入失败: {e2}")
                self.effect_manager = None

        # 物理系统 - 提供碰撞检测和击退效果
        try:
            from src.systems.physics_system import PhysicsSystem
            from src.systems.knockback_animation import KnockbackAnimation

            # 初始化物理系统
            world_bounds = (0, 0,
                            GameConstants.MAP_WIDTH * GameConstants.TILE_SIZE,
                            GameConstants.MAP_HEIGHT * GameConstants.TILE_SIZE)
            self.physics_system = PhysicsSystem(
                world_bounds, GameConstants.TILE_SIZE)

            # 初始化击退动画系统
            self.knockback_animation = KnockbackAnimation()

            # 连接物理系统和动画系统
            self.physics_system.set_animation_manager(self.knockback_animation)

            print(
                f"⚡ 物理系统初始化成功 (世界边界: {world_bounds}, 瓦片大小: {GameConstants.TILE_SIZE})")
        except ImportError as e:
            print(f"❌ 物理系统导入失败: {e}")
            self.physics_system = None
            self.knockback_animation = None

        # 地图系统
        self.map_width = GameConstants.MAP_WIDTH
        self.map_height = GameConstants.MAP_HEIGHT
        self.tile_size = GameConstants.TILE_SIZE
        self.game_map = self._initialize_map()

        # 初始化统一寻路系统
        try:
            from src.managers.movement_system import MovementSystem
            from src.systems.unified_pathfinding import PathfindingConfig

            # 初始化统一寻路系统
            unified_success = MovementSystem.initialize_unified_pathfinding(
                PathfindingConfig(
                    max_iterations=1000,
                    cache_timeout=5.0,
                    dynamic_threshold=0.1,
                    enable_caching=True,
                    enable_dynamic_adjustment=True
                )
            )
            if unified_success:
                print("🚀 统一寻路系统初始化成功")

            # 初始化高级寻路系统（NavMesh）作为备用
            navmesh_success = MovementSystem.initialize_advanced_pathfinding(
                self.game_map, self.map_width, self.map_height)
            if navmesh_success:
                print("🧭 高级寻路系统（NavMesh）初始化成功")
            else:
                print("⚠️ 高级寻路系统初始化失败，将使用统一寻路系统")
        except ImportError as e:
            print(f"⚠️ 寻路系统不可用: {e}")

        # 相机系统 - 居中到地牢之心
        heart_pixel_x = self.dungeon_heart_pos[0] * self.tile_size
        heart_pixel_y = self.dungeon_heart_pos[1] * self.tile_size
        self.camera_x = heart_pixel_x - GameConstants.WINDOW_WIDTH // 2
        self.camera_y = heart_pixel_y - GameConstants.WINDOW_HEIGHT // 2
        print(f"{emoji_manager.CAMERA} 相机居中到地牢之心: ({self.camera_x}, {self.camera_y})")

        # 输入系统
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_world_x = -1
        self.mouse_world_y = -1
        self.build_mode = BuildMode.NONE
        self.selected_monster_type = None

        # 时间系统
        self.last_time = time.time()
        self.running = True

        # 调试模式
        self.debug_mode = False

        # 字体管理器 - 使用统一的字体管理器
        self.font_manager = font_manager

        # 手动初始化字体（确保pygame已初始化）
        self.font_manager._ensure_fonts_initialized()

        # 初始化表情符号图片映射器
        self.emoji_mapper = self.font_manager.emoji_mapper
        self.font = self.font_manager.get_font(24)
        self.small_font = self.font_manager.get_font(18)

        # 角色图鉴系统
        if BESTIARY_AVAILABLE:
            self.bestiary = CharacterBestiary(
                GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager)
            print("📚 角色图鉴系统已加载")

        # 状态指示器系统
        if STATUS_INDICATOR_AVAILABLE:
            self.status_indicator = StatusIndicator()
        else:
            self.status_indicator = None

        # 美化UI渲染器
        self.game_ui = GameUI(self.screen, self.font_manager)
        print("🎨 美化UI系统已加载")

        # 怪物选择UI系统
        self.monster_selection_ui = MonsterSelectionUI(
            GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager)
        # 设置emoji_mapper引用（向后兼容）
        self.monster_selection_ui.emoji_mapper = self.emoji_mapper

        # 后勤召唤UI系统
        self.logistics_selection_ui = LogisticsSelectionUI(
            GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager)

        # 建筑系统
        if BUILDING_SYSTEM_AVAILABLE:
            self.building_manager = BuildingManager()
            self.building_manager.game_instance = self  # 设置游戏实例引用
            self.building_ui = BuildingUI(
                GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager)
            print("🏗️ 建筑系统已初始化")
        else:
            self.building_manager = None
            self.building_ui = None

        print(f"{emoji_manager.CHECK} 游戏初始化完成")

        # 游戏初始化完成后，启用接壤金矿脉日志输出
        from src.systems.reachability_system import get_reachability_system
        reachability_system = get_reachability_system()
        reachability_system.enable_adjacent_vein_logging()

    def _update_world_mouse_position(self):
        """更新鼠标在世界坐标中的位置"""
        self.mouse_world_x = int(
            (self.mouse_x + self.camera_x) // self.tile_size)
        self.mouse_world_y = int(
            (self.mouse_y + self.camera_y) // self.tile_size)

    def _handle_click(self, mouse_pos: Tuple[int, int]):
        """处理鼠标点击"""
        self.mouse_x, self.mouse_y = mouse_pos
        self._update_world_mouse_position()

        if (self.mouse_world_x < 0 or self.mouse_world_x >= self.map_width or
                self.mouse_world_y < 0 or self.mouse_world_y >= self.map_height):
            return

        tile = self.game_map[self.mouse_world_y][self.mouse_world_x]

        if self.build_mode == BuildMode.DIG:
            self._dig_tile(self.mouse_world_x, self.mouse_world_y)
        elif self.build_mode == BuildMode.SUMMON:
            if self.selected_monster_type:
                self._summon_creature(
                    self.mouse_world_x, self.mouse_world_y, self.selected_monster_type)
        elif self.build_mode == BuildMode.SUMMON_LOGISTICS:
            if hasattr(self, 'selected_logistics_type'):
                self._summon_creature(self.mouse_world_x,
                                      self.mouse_world_y, self.selected_logistics_type)
        elif self.build_mode == BuildMode.BUILD_SPECIFIC:
            self._build_selected_building(
                self.mouse_world_x, self.mouse_world_y)

    def _dig_tile(self, x: int, y: int):
        """挖掘瓦片 - 使用瓦块管理器"""
        tile = self.game_map[y][x]

        # 挖掘前启用接壤金矿脉日志
        from src.systems.reachability_system import get_reachability_system
        reachability_system = get_reachability_system()
        reachability_system.enable_adjacent_vein_logging()

        # 使用瓦块管理器的统一挖掘方法
        result = tile_manager.dig_tile(
            tile, x, y, cost=10, game_state=self.game_state)

        if result['success']:
            if result['gold_discovered'] > 0:
                # 发现金矿脉
                print(f"{emoji_manager.MONEY} {result['message']}")
                # 根据文档要求，发现时会有特殊的金色特效和提示音
                self._show_gold_discovery_effect(x, y)
            else:
                # 普通挖掘
                print(f"{emoji_manager.PICKAXE} {result['message']}")

            # 挖掘成功后，强制更新可达性以检测新的可到达金矿脉
            reachability_system.update_reachability(
                self.game_map, force_update=True)
        else:
            # 挖掘失败
            print(f"❌ 挖掘失败: {result['message']}")

        # 挖掘后禁用接壤金矿脉日志，避免频繁输出
        reachability_system.disable_adjacent_vein_logging()

    def _summon_creature(self, x: int, y: int, creature_type: str):
        """召唤生物 - 只能在已挖掘区域召唤"""
        tile = self.game_map[y][x]

        # 获取生物成本
        cost = 80  # 默认成本
        creature_name = creature_type
        if BESTIARY_AVAILABLE:
            character_data = character_db.get_character(creature_type)
            if character_data:
                cost = character_data.cost if character_data.cost else 80
                creature_name = character_data.name
        else:
            # 如果图鉴系统不可用，使用硬编码的成本
            if creature_type == 'goblin_worker':
                cost = 80  # 哥布林苦工成本80金币
                creature_name = '哥布林苦工'

        # 自动转换原始黄金为金币
        if self.game_state.raw_gold > 0 and self.game_state.gold < cost:
            needed_gold = cost - self.game_state.gold
            converted_gold = min(self.game_state.raw_gold, needed_gold)
            if converted_gold > 0:
                self.game_state.raw_gold -= converted_gold
                self.game_state.gold += converted_gold
                print(
                    f"{emoji_manager.MONEY} 转换了 {converted_gold} 原始黄金为金币 (当前金币: {self.game_state.gold})")

        # 检查召唤位置是否被占用
        summon_position_occupied = self._check_summon_position_occupied(
            x, y, creature_type, verbose=True)

        # 使用瓦块管理器检查地形
        if (tile_manager.check_tile_passable(tile) and
            len(self.creatures) < GameBalance.max_creatures and
            self.game_state.gold >= cost and
                not summon_position_occupied):

            # 根据生物类型创建不同的实例 - 使用瓦块管理器获取中心坐标
            creature_x, creature_y = tile_manager.get_tile_center_pixel(x, y)

            if creature_type == 'goblin_worker':
                # 创建哥布林苦工专用类
                creature = GoblinWorker(creature_x, creature_y)
            elif creature_type == 'goblin_engineer':
                # 创建地精工程师专用类
                from src.entities.goblin_engineer import EngineerRegistry
                config = EngineerRegistry.get_config(EngineerType.BASIC)
                creature = Engineer(creature_x, creature_y,
                                    EngineerType.BASIC, config)
                # 在建筑管理器中注册工程师
                if self.building_manager:
                    self.building_manager.engineers.append(creature)
                    print(f"🔨 {creature_name} 已注册为工程师")
            else:
                # 其他生物使用基础类
                creature = Creature(creature_x, creature_y, creature_type)

            # 设置游戏实例引用，用于资源更新
            creature.game_instance = self
            self.creatures.append(creature)
            self.game_state.gold -= cost
            print(f"{emoji_manager.MONSTER} 召唤了{creature_name} ({x}, {y})")
        else:
            # 失败原因分析
            if not tile_manager.check_tile_passable(tile):
                print(f"❌ 召唤失败: 位置({x},{y})不是可通行区域")
            elif len(self.creatures) >= GameBalance.max_creatures:
                print(f"❌ 召唤失败: 生物数量已达上限({GameBalance.max_creatures})")
            elif self.game_state.gold < cost:
                print(f"❌ 召唤失败: 金币不足(需要{cost}金，当前{self.game_state.gold}金)")
            elif summon_position_occupied:
                print(f"❌ 召唤失败: 位置({x},{y})已被其他单位占用")

    def _check_summon_position_occupied(self, tile_x: int, tile_y: int, creature_type: str, verbose: bool = False) -> bool:
        """
        检查召唤位置是否被其他单位占用

        Args:
            tile_x, tile_y: 瓦片坐标
            creature_type: 要召唤的生物类型
            verbose: 是否打印详细信息

        Returns:
            bool: 位置是否被占用
        """
        # 计算召唤位置的世界坐标 - 使用瓦块管理器
        summon_x, summon_y = tile_manager.get_tile_center_pixel(tile_x, tile_y)

        # 获取要召唤生物的大小（用于碰撞检测）
        creature_size = 15  # 默认大小
        if BESTIARY_AVAILABLE:
            character_data = character_db.get_character(creature_type)
            if character_data:
                creature_size = character_data.size

        # 计算召唤生物的碰撞半径
        summon_radius = creature_size * 0.6  # 使用物理系统的碰撞半径计算方式
        summon_radius = max(5, min(summon_radius, 25))  # 限制范围

        # 检查与现有生物的碰撞
        for existing_creature in self.creatures:
            # 计算距离
            dx = existing_creature.x - summon_x
            dy = existing_creature.y - summon_y
            distance = math.sqrt(dx * dx + dy * dy)

            # 获取现有生物的碰撞半径
            existing_radius = getattr(
                existing_creature, 'collision_radius', None)
            if existing_radius is None:
                existing_size = getattr(existing_creature, 'size', 15)
                existing_radius = existing_size * 0.6
                existing_radius = max(5, min(existing_radius, 25))

            # 检查是否会发生碰撞
            required_distance = summon_radius + existing_radius
            if distance < required_distance:
                if verbose:
                    print(
                        f"   🚫 位置被 {existing_creature.type} 占用 (距离: {distance:.1f}, 需要: {required_distance:.1f})")
                return True

        # 检查与英雄的碰撞
        for hero in self.heroes:
            # 计算距离
            dx = hero.x - summon_x
            dy = hero.y - summon_y
            distance = math.sqrt(dx * dx + dy * dy)

            # 获取英雄的碰撞半径
            hero_radius = getattr(hero, 'collision_radius', None)
            if hero_radius is None:
                hero_size = getattr(hero, 'size', 20)
                hero_radius = hero_size * 0.6
                hero_radius = max(5, min(hero_radius, 25))

            # 检查是否会发生碰撞
            required_distance = summon_radius + hero_radius
            if distance < required_distance:
                if verbose:
                    print(
                        f"   🚫 位置被 {hero.type} 占用 (距离: {distance:.1f}, 需要: {required_distance:.1f})")
                return True

        return False

    def _safe_render_text(self, font, text, color, use_emoji_fallback=True):
        """安全渲染文本，使用UnifiedFontManager的safe_render方法"""
        return self.font_manager.safe_render(font, text, color, use_emoji_fallback)

    def _initialize_map(self) -> List[List[Tile]]:
        """初始化地图"""
        game_map = []
        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                # 随机生成金矿 - 根据文档要求8%概率，每个矿脉500单位原始黄金
                is_gold = random.random() < 0.08
                gold_amount = 500 if is_gold else 0
                tile = Tile(
                    TileType.ROCK,
                    is_gold_vein=is_gold,
                    gold_amount=gold_amount
                )
                row.append(tile)
            game_map.append(row)

        # 创建起始区域 - 在地图中央挖掘一个8x8的区域
        center_x = self.map_width // 2
        center_y = self.map_height // 2

        print(f"{emoji_manager.BUILD} 创建起始区域，中心位置: ({center_x}, {center_y})")

        # 挖掘起始区域（8x8）
        for dy in range(-4, 4):
            for dx in range(-4, 4):
                x = center_x + dx
                y = center_y + dy
                if 0 <= x < self.map_width and 0 <= y < self.map_height:
                    game_map[y][x].type = TileType.GROUND
                    game_map[y][x].is_dug = True
                    # 清除起始区域的金矿，避免阻挡
                    game_map[y][x].is_gold_vein = False
                    game_map[y][x].gold_amount = 0

        # 在8x8空间的中心放置地牢之心（主基地）- 2x2瓦片
        # 8x8空间范围：-4到3，中心位置为(-0.5, -0.5)
        # 2x2地牢之心最佳位置：(-1, -1)到(0, 0)
        heart_x = center_x - 1  # 向左偏移1格
        heart_y = center_y - 1  # 向上偏移1格
        if 0 <= heart_x < self.map_width - 1 and 0 <= heart_y < self.map_height - 1:
            # 设置2x2瓦片区域为地牢之心
            for dy in range(2):
                for dx in range(2):
                    tile_x = heart_x + dx
                    tile_y = heart_y + dy
                    if 0 <= tile_x < self.map_width and 0 <= tile_y < self.map_height:
                        game_map[tile_y][tile_x].type = TileType.ROOM
                        game_map[tile_y][tile_x].room_type = 'dungeon_heart'
                        # 标记为地牢之心的一部分
                        game_map[tile_y][tile_x].is_dungeon_heart_part = True
                        game_map[tile_y][tile_x].dungeon_heart_center = (
                            heart_x, heart_y)

            # 创建地牢之心建筑对象（使用中心坐标）
            from src.entities.building import BuildingRegistry, BuildingType
            dungeon_heart = BuildingRegistry.create_building(
                BuildingType.DUNGEON_HEART, heart_x, heart_y)

            # 将建筑对象添加到建筑管理器
            if hasattr(self, 'building_manager'):
                self.building_manager.buildings.append(dungeon_heart)

            # 将血量信息传递到所有2x2瓦片
            for dy in range(2):
                for dx in range(2):
                    tile_x = heart_x + dx
                    tile_y = heart_y + dy
                    if 0 <= tile_x < self.map_width and 0 <= tile_y < self.map_height:
                        game_map[tile_y][tile_x].health = dungeon_heart.health
                        game_map[tile_y][tile_x].max_health = dungeon_heart.max_health
                        # 保存建筑对象引用
                        game_map[tile_y][tile_x].dungeon_heart_building = dungeon_heart

            print(
                f"{emoji_manager.HEART} 地牢之心建造在 ({heart_x}, {heart_y}) - 2x2瓦片区域，位于8x8空间中心")

        # 记录地牢之心位置
        self.dungeon_heart_pos = (heart_x, heart_y)

        # 初始化可达性系统
        from src.systems.reachability_system import get_reachability_system
        reachability_system = get_reachability_system()
        reachability_system.set_base_position(heart_x, heart_y)

        # 创建英雄基地
        self._create_hero_bases(game_map)

        return game_map

    def _create_hero_bases(self, game_map: List[List[Tile]]):
        """在地图边缘创建1-3个英雄基地"""
        import random

        # 随机决定创建1-3个基地
        num_bases = random.randint(1, 3)
        print(f"{emoji_manager.CASTLE} 创建 {num_bases} 个英雄基地")

        # 定义可能的基地位置（地图边缘）
        possible_positions = []

        # 上边缘
        for x in range(5, self.map_width - 5):
            possible_positions.append((x, 2, "north"))

        # 下边缘
        for x in range(5, self.map_width - 5):
            possible_positions.append((x, self.map_height - 3, "south"))

        # 左边缘
        for y in range(5, self.map_height - 5):
            possible_positions.append((2, y, "west"))

        # 右边缘
        for y in range(5, self.map_height - 5):
            possible_positions.append((self.map_width - 3, y, "east"))

        # 随机选择基地位置，确保它们之间有足够距离
        selected_bases = []
        for _ in range(num_bases):
            if not possible_positions:
                break

            # 随机选择一个位置
            base_pos = random.choice(possible_positions)
            selected_bases.append(base_pos)

            # 移除附近的位置，确保基地之间有足够距离
            base_x, base_y, direction = base_pos
            possible_positions = [pos for pos in possible_positions
                                  if abs(pos[0] - base_x) > 8 or abs(pos[1] - base_y) > 8]

        # 创建每个基地
        for i, (base_x, base_y, direction) in enumerate(selected_bases):
            self._build_hero_base(game_map, base_x, base_y, direction, i + 1)
            self.hero_bases.append((base_x, base_y, direction))

    def _build_hero_base(self, game_map: List[List[Tile]], base_x: int, base_y: int, direction: str, base_id: int):
        """建造单个英雄基地和周围的挖掘区域"""
        print(
            f"{emoji_manager.CASTLE} 建造英雄基地 {base_id} 在 ({base_x}, {base_y}) 方向: {direction}")

        # 创建基地周围的挖掘区域（5x5）
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                x = base_x + dx
                y = base_y + dy
                if 0 <= x < self.map_width and 0 <= y < self.map_height:
                    game_map[y][x].type = TileType.GROUND
                    game_map[y][x].is_dug = True
                    # 清除金矿，确保区域畅通
                    game_map[y][x].is_gold_vein = False
                    game_map[y][x].gold_amount = 0

        # 在基地中心放置英雄基地标识
        if 0 <= base_x < self.map_width and 0 <= base_y < self.map_height:
            game_map[base_y][base_x].type = TileType.ROOM
            game_map[base_y][base_x].room_type = f'hero_base_{base_id}'

        # 自动生成守卫：两个骑士和一个弓箭手
        self._spawn_hero_base_defenders(base_x, base_y, direction, game_map)

    def _spawn_hero_base_defenders(self, base_x: int, base_y: int, direction: str, game_map: List[List[Tile]]):
        """在英雄基地附近生成守卫：两个骑士和一个弓箭手"""
        import random

        # 定义守卫配置：两个骑士和一个弓箭手
        defenders = [
            {'type': 'knight', 'name': '骑士'},
            {'type': 'knight', 'name': '骑士'},
            {'type': 'archer', 'name': '弓箭手'}
        ]

        # 根据基地方向确定守卫位置
        spawn_positions = []

        if direction == "north":
            # 基地在上方，守卫在基地下方
            spawn_positions = [
                (base_x - 1, base_y + 2),  # 左骑士
                (base_x + 1, base_y + 2),  # 右骑士
                (base_x, base_y + 1)       # 弓箭手在基地后方
            ]
        elif direction == "south":
            # 基地在下方，守卫在基地上方
            spawn_positions = [
                (base_x - 1, base_y - 2),  # 左骑士
                (base_x + 1, base_y - 2),  # 右骑士
                (base_x, base_y - 1)       # 弓箭手在基地后方
            ]
        elif direction == "west":
            # 基地在左方，守卫在基地右方
            spawn_positions = [
                (base_x + 2, base_y - 1),  # 上骑士
                (base_x + 2, base_y + 1),  # 下骑士
                (base_x + 1, base_y)       # 弓箭手在基地后方
            ]
        elif direction == "east":
            # 基地在右方，守卫在基地左方
            spawn_positions = [
                (base_x - 2, base_y - 1),  # 上骑士
                (base_x - 2, base_y + 1),  # 下骑士
                (base_x - 1, base_y)       # 弓箭手在基地后方
            ]

        # 生成守卫
        for i, defender in enumerate(defenders):
            if i < len(spawn_positions):
                spawn_x, spawn_y = spawn_positions[i]

                # 检查位置是否在地图范围内且是可通行区域
                if (0 <= spawn_x < self.map_width and
                    0 <= spawn_y < self.map_height and
                    (game_map[spawn_y][spawn_x].type == TileType.GROUND or
                     game_map[spawn_y][spawn_x].is_dug)):

                    # 创建守卫英雄
                    hero_x = spawn_x * self.tile_size + self.tile_size // 2
                    hero_y = spawn_y * self.tile_size + self.tile_size // 2

                    hero = Hero(hero_x, hero_y, defender['type'])
                    self.heroes.append(hero)

                    print(
                        f"🛡️ {defender['name']}守卫在 ({spawn_x}, {spawn_y}) 保卫基地")
                else:
                    # 如果指定位置不可用，在基地附近寻找替代位置
                    alternative_positions = []
                    for dy in range(-3, 4):
                        for dx in range(-3, 4):
                            alt_x = base_x + dx
                            alt_y = base_y + dy
                            if (0 <= alt_x < self.map_width and
                                0 <= alt_y < self.map_height and
                                (game_map[alt_y][alt_x].type == TileType.GROUND or
                                 game_map[alt_y][alt_x].is_dug) and
                                not any(h.x // self.tile_size == alt_x and h.y // self.tile_size == alt_y
                                        for h in self.heroes)):
                                alternative_positions.append((alt_x, alt_y))

                    if alternative_positions:
                        alt_x, alt_y = random.choice(alternative_positions)
                        hero_x = alt_x * self.tile_size + self.tile_size // 2
                        hero_y = alt_y * self.tile_size + self.tile_size // 2

                        hero = Hero(hero_x, hero_y, defender['type'])
                        self.heroes.append(hero)

                        print(
                            f"🛡️ {defender['name']}守卫在备用位置 ({alt_x}, {alt_y}) 保卫基地")

    def _is_key_pressed(self, event, key_chars):
        """增强的按键检测，支持输入法兼容性"""
        # 检查物理按键
        for char in key_chars:
            if char.lower() == 'w' and event.key == pygame.K_w:
                return True
            elif char.lower() == 'a' and event.key == pygame.K_a:
                return True
            elif char.lower() == 's' and event.key == pygame.K_s:
                return True
            elif char.lower() == 'd' and event.key == pygame.K_d:
                return True
            elif char.lower() == 'b' and event.key == pygame.K_b:
                return True

        # 检查unicode字符（输入法兼容）
        if event.unicode and event.unicode.lower() in [c.lower() for c in key_chars]:
            return True

        return False

    def _show_gold_discovery_effect(self, x: int, y: int):
        """显示黄金发现特效"""
        # 这里可以添加粒子特效或高亮效果
        # 由于当前没有特效系统，我们通过控制台消息来模拟
        print(f"✨ 金色光芒从 ({x}, {y}) 闪烁！黄金矿脉被发现！")

    def _build_room(self, x: int, y: int, room_type: str, cost: int):
        """建造房间"""
        tile = self.game_map[y][x]
        if tile.type == TileType.GROUND and not tile.room and self.game_state.gold >= cost:
            tile.type = TileType.ROOM
            tile.room = room_type
            self.game_state.gold -= cost
            print(f"{emoji_manager.BUILD} 建造了{room_type} ({x}, {y})")

    def _execute_attack_with_rules(self, attacker, target, delta_time, current_time, attacker_type):
        """执行攻击，应用新的攻击规则 - 三步骤攻击流程"""
        # 步骤1: 攻击发起检查
        attack_initiated = self._initiate_attack(
            attacker, target, current_time)
        if not attack_initiated:
            return False

        # 步骤2: 特效生成
        effect_created = self._create_attack_effect(attacker, target)
        if not effect_created:
            return False

        # 步骤3: 伤害判定
        damage_dealt = self._apply_damage(attacker, target)
        if damage_dealt == 0:
            return False

        # 更新攻击时间
        attacker.last_attack = current_time

        # 简化日志输出 - 只显示关键信息
        print(
            f"⚔️ {attacker.type} 攻击 {target.type} 造成 {damage_dealt} 点伤害 (目标剩余: {target.health})")
        return True

    def _initiate_attack(self, attacker, target, current_time):
        """步骤1: 攻击发起检查"""
        # 检查攻击类型
        is_melee = attacker._is_melee_attack()

        if is_melee:
            # 近战攻击：检查目标是否已被其他近战攻击者攻击
            if target.melee_target is not None and target.melee_target != attacker:
                return False

            # 设置近战攻击目标
            target.melee_target = attacker
            attacker.melee_target = target

        return True

    def _create_attack_effect(self, attacker, target):
        """步骤2: 特效生成"""
        try:
            # 获取攻击特效类型
            effect_type = self._get_attack_effect_type(attacker)
            if not effect_type:
                return False

            # 计算攻击方向
            dx = target.x - attacker.x
            dy = target.y - attacker.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > 0:
                # 归一化方向向量
                dx /= distance
                dy /= distance

                # 将世界坐标转换为屏幕坐标
                screen_x = attacker.x - self.camera_x
                screen_y = attacker.y - self.camera_y
                target_screen_x = target.x - self.camera_x
                target_screen_y = target.y - self.camera_y

                # 创建特效
                success = self.effect_manager.create_effect(
                    effect_type=effect_type,
                    x=screen_x,
                    y=screen_y,
                    target_x=target_screen_x,
                    target_y=target_screen_y,
                    damage=attacker.attack
                )

                return success
            else:
                return False

        except Exception as e:
            return False

    def _apply_damage(self, attacker, target):
        """步骤3: 伤害判定"""
        try:
            # 计算伤害
            damage = attacker.attack

            # 应用护甲减免
            if hasattr(target, 'armor') and target.armor > 0:
                damage_reduction = target.armor * 0.1  # 每点护甲减少10%伤害
                damage = max(1, int(damage * (1 - damage_reduction)))

            # 造成伤害
            target.health -= damage
            target.health = max(0, target.health)  # 确保生命值不为负数

            # 应用物理击退效果（仅近战攻击）
            if self.physics_system and attacker._is_melee_attack():
                # 获取攻击类型
                attack_type = self._get_attack_type(attacker)

                # 执行击退
                knockback_success = self.physics_system.execute_melee_attack_with_knockback(
                    attacker, target, damage, attack_type
                )

                if knockback_success:
                    # 创建击退动画效果
                    if self.knockback_animation and target.knockback_state:
                        direction = target.knockback_state.target_x - target.knockback_state.start_x, \
                            target.knockback_state.target_y - target.knockback_state.start_y
                        distance = (direction[0]**2 + direction[1]**2)**0.5
                        if distance > 0:
                            normalized_direction = (
                                direction[0]/distance, direction[1]/distance)
                            self.knockback_animation.create_knockback_effect(
                                target, normalized_direction, distance
                            )

            return damage

        except Exception as e:
            return 0

    def _get_attack_effect_type(self, attacker):
        """获取攻击特效类型"""
        effect_mapping = {
            # 英雄特效映射
            'knight': 'melee_slash',
            'archer': 'arrow_shot',
            'wizard': 'fireball',
            'paladin': 'divine_strike',
            'assassin': 'shadow_slash',
            'ranger': 'tracking_arrow',
            'archmage': 'chain_lightning',
            'druid': 'nature_arrow',
            'dragon_knight': 'fire_breath',
            'shadow_blade': 'shadow_slash',
            'berserker': 'melee_heavy',
            'priest': 'healing_aura',
            'thief': 'shadow_slash',
            'engineer': 'arrow_shot',

            # 怪物特效映射
            'imp': 'melee_slash',
            'goblin_worker': 'melee_slash',
            'gargoyle': 'melee_heavy',
            'fire_salamander': 'fire_splash',
            'shadow_mage': 'shadow_penetration',
            'tree_guardian': 'vine_entangle',
            'shadow_lord': 'shadow_slash',
            'bone_dragon': 'spine_storm',
            'hellhound': 'fire_breath',
            'stone_golem': 'melee_heavy',
            'succubus': 'charm_effect',
            'orc': 'melee_heavy'
        }
        return effect_mapping.get(attacker.type, 'melee_slash')

    def _close_all_ui_windows(self):
        """关闭所有UI窗口"""
        # 关闭建筑UI
        if self.building_ui:
            self.building_ui.show_building_panel = False
            self.building_ui.show_statistics_panel = False
            self.building_ui.selected_building_category = None
            self.building_ui.selected_building_type = None

        # 关闭怪物选择UI
        if self.monster_selection_ui:
            self.monster_selection_ui.hide()

        # 关闭后勤召唤UI
        if self.logistics_selection_ui:
            self.logistics_selection_ui.hide()

        # 关闭角色图鉴
        if self.bestiary:
            self.bestiary.hide()

    def _open_ui_window(self, window_type: str):
        """打开指定的UI窗口，关闭其他窗口"""
        # 先关闭所有窗口
        self._close_all_ui_windows()

        # 打开指定窗口
        if window_type == "building":
            if self.building_ui:
                self.building_ui.show_building_panel = True
        elif window_type == "monster_selection":
            if self.monster_selection_ui:
                self.monster_selection_ui.show()
        elif window_type == "logistics_selection":
            if self.logistics_selection_ui:
                self.logistics_selection_ui.show()
        elif window_type == "bestiary":
            if self.bestiary:
                self.bestiary.show()

    def _get_building_color(self, building_type: str) -> tuple:
        """根据建筑类型获取颜色"""
        building_colors = {
            'treasury': GameConstants.COLORS['treasury'],  # 金库 - 金色
            'lair': GameConstants.COLORS['lair'],          # 巢穴 - 棕色
            'training_room': (112, 128, 144),              # 训练室 - 灰蓝色
            'library': (25, 25, 112),                      # 图书馆 - 深蓝色
            'workshop': (139, 69, 19),                     # 工坊 - 棕色
            'prison': (105, 105, 105),                     # 监狱 - 深灰色
            'torture_chamber': (139, 0, 0),               # 刑房 - 深红色
            'arrow_tower': (211, 211, 211),               # 箭塔 - 浅灰色
            'defense_fortification': (169, 169, 169),     # 防御工事 - 灰色
            'magic_altar': (138, 43, 226),                # 魔法祭坛 - 紫色
            'shadow_temple': (72, 61, 139),               # 暗影神殿 - 暗紫色
            'magic_research_institute': (65, 105, 225),   # 魔法研究院 - 蓝色
            'advanced_gold_mine': (255, 215, 0),          # 高级金矿 - 金黄色
        }

        # 默认颜色
        return building_colors.get(building_type, GameConstants.COLORS['lair'])

    def _get_attack_type(self, attacker):
        """获取攻击类型用于击退计算"""
        # 根据单位类型返回攻击类型
        heavy_attackers = {'gargoyle', 'stone_golem',
                           'dragon_knight', 'paladin'}
        area_attackers = {'fire_salamander', 'archmage'}
        magic_attackers = {'shadow_mage', 'wizard', 'archmage', 'druid'}

        if attacker.type in heavy_attackers:
            return "heavy"
        elif attacker.type in area_attackers:
            return "area"
        elif attacker.type in magic_attackers:
            return "magic"
        else:
            return "normal"

    def _handle_combat(self, delta_time: float):
        """处理战斗系统 - 优化版本"""
        current_time = time.time()

        # 检测生物与英雄的战斗（只处理战斗单位）
        for creature in self.creatures[:]:
            # 跳过非战斗单位
            if hasattr(creature, 'is_combat_unit') and not creature.is_combat_unit:
                continue

            for hero in self.heroes[:]:
                # 优化：使用平方距离避免开方运算
                dx = creature.x - hero.x
                dy = creature.y - hero.y
                distance_squared = dx * dx + dy * dy
                distance = math.sqrt(distance_squared)  # 只在需要精确距离时计算

                # 根据角色类型动态计算攻击距离
                creature_attack_range = creature.attack_range if hasattr(
                    creature, 'attack_range') else 30
                hero_attack_range = hero.attack_range if hasattr(
                    hero, 'attack_range') else 30

                # 计算追击范围 - 根据攻击类型区分
                # 远程单位：追击范围 = 攻击范围
                # 近战单位：追击范围 = 攻击范围 * 2.5
                creature_is_melee = hasattr(
                    creature, '_is_melee_attack') and creature._is_melee_attack()
                hero_is_melee = hasattr(
                    hero, '_is_melee_attack') and hero._is_melee_attack()

                creature_pursuit_range = creature_attack_range * \
                    (2.5 if creature_is_melee else 1.0)
                hero_pursuit_range = hero_attack_range * \
                    (2.5 if hero_is_melee else 1.0)
                max_pursuit_range = max(
                    creature_pursuit_range, hero_pursuit_range)
                max_pursuit_range_squared = max_pursuit_range * max_pursuit_range

                # 检查是否在追击范围内（用于进入和维持战斗状态）
                if distance_squared <= max_pursuit_range_squared:
                    # 设置战斗状态
                    creature.in_combat = True
                    creature.last_combat_time = current_time
                    creature.state = 'fighting'
                    hero.in_combat = True
                    hero.last_combat_time = current_time
                    hero.state = 'fighting'

                    # 检查攻击冷却时间
                    creature_can_attack = current_time - \
                        creature.last_attack >= creature.attack_cooldown
                    hero_can_attack = current_time - hero.last_attack >= hero.attack_cooldown

                    # 执行攻击（只有在实际攻击范围内才能攻击）
                    attack_occurred = False
                    creature_attack_range_squared = creature_attack_range * creature_attack_range
                    hero_attack_range_squared = hero_attack_range * hero_attack_range

                    if creature_can_attack and distance_squared <= creature_attack_range_squared:
                        if self._execute_attack_with_rules(creature, hero, delta_time, current_time, "creature"):
                            attack_occurred = True

                    if hero_can_attack and distance_squared <= hero_attack_range_squared:
                        if self._execute_attack_with_rules(hero, creature, delta_time, current_time, "hero"):
                            attack_occurred = True

                    # 如果不在攻击范围内但在追击范围内，主动追击
                    max_attack_range_squared = max(
                        creature_attack_range_squared, hero_attack_range_squared)
                    if distance_squared > max_attack_range_squared:
                        self._handle_combat_pursuit(
                            creature, hero, delta_time, distance)
                else:
                    # 超出追击范围，检查是否脱离战斗
                    self._handle_combat_exit(creature, hero, distance)

        # 处理英雄攻击建筑物
        self._handle_hero_attack_buildings(current_time)

        # 处理英雄攻击功能性怪物
        self._handle_hero_attack_functional_creatures(current_time)

        # 处理回血系统
        self._handle_health_regeneration(current_time)

    def _handle_combat_pursuit(self, creature, hero, delta_time, distance):
        """处理战斗追击 - 当单位在追击范围内但不在攻击范围内时主动追击"""
        # 跳过非战斗单位
        if hasattr(creature, 'is_combat_unit') and not creature.is_combat_unit:
            return

        # 计算各自的攻击范围
        creature_attack_range = creature.attack_range if hasattr(
            creature, 'attack_range') else 30
        hero_attack_range = hero.attack_range if hasattr(
            hero, 'attack_range') else 30

        # 检查目标是否死亡
        if hero.health <= 0:
            creature.in_combat = False
            creature.state = 'wandering'
            return

        if creature.health <= 0:
            hero.in_combat = False
            hero.state = 'exploring'
            return

        # 如果生物不在攻击范围内，主动追击英雄
        if distance > creature_attack_range and creature.in_combat:
            creature.state = 'moving'
            # 使用移动系统追击目标
            from src.managers.movement_system import MovementSystem
            MovementSystem.target_seeking_movement(
                creature, (hero.x, hero.y), delta_time, self.game_map, speed_multiplier=1.2)

        # 如果英雄不在攻击范围内，主动追击生物
        if distance > hero_attack_range and hero.in_combat:
            hero.state = 'moving'
            # 使用移动系统追击目标
            from src.managers.movement_system import MovementSystem
            MovementSystem.target_seeking_movement(
                hero, (creature.x, creature.y), delta_time, self.game_map, speed_multiplier=1.2)

    def _handle_combat_exit(self, creature, hero, distance):
        """处理战斗脱离 - 只有目标死亡或离开追击范围才脱离战斗"""
        # 跳过非战斗单位
        if hasattr(creature, 'is_combat_unit') and not creature.is_combat_unit:
            return

        # 计算追击范围 - 根据攻击类型区分
        creature_attack_range = creature.attack_range if hasattr(
            creature, 'attack_range') else 30
        hero_attack_range = hero.attack_range if hasattr(
            hero, 'attack_range') else 30

        # 远程单位：追击范围 = 攻击范围
        # 近战单位：追击范围 = 攻击范围 * 2.5
        creature_is_melee = hasattr(
            creature, '_is_melee_attack') and creature._is_melee_attack()
        hero_is_melee = hasattr(
            hero, '_is_melee_attack') and hero._is_melee_attack()

        creature_pursuit_range = creature_attack_range * \
            (2.5 if creature_is_melee else 1.0)
        hero_pursuit_range = hero_attack_range * \
            (2.5 if hero_is_melee else 1.0)
        max_pursuit_range = max(
            creature_pursuit_range, hero_pursuit_range)
        max_pursuit_range_squared = max_pursuit_range * max_pursuit_range

        # 计算当前距离的平方
        dx = creature.x - hero.x
        dy = creature.y - hero.y
        distance_squared = dx * dx + dy * dy

        # 检查目标是否死亡
        if hero.health <= 0:
            if creature.in_combat:
                creature.in_combat = False
                self._cleanup_melee_target(creature)
                if creature.type == 'goblin_worker':
                    creature.state = 'wandering'
                else:
                    creature.state = 'wandering'
                print(f"🛡️ {creature.type} 脱离战斗")

        if creature.health <= 0:
            if hero.in_combat:
                hero.in_combat = False
                self._cleanup_melee_target(hero)
                hero.state = 'exploring'
                print(f"🛡️ {hero.type} 脱离战斗")

        # 检查是否超出追击范围
        if distance_squared > max_pursuit_range_squared:
            if creature.in_combat:
                creature.in_combat = False
                self._cleanup_melee_target(creature)
                if creature.type == 'goblin_worker':
                    creature.state = 'wandering'
                else:
                    creature.state = 'wandering'
                print(f"🛡️ {creature.type} 脱离战斗")

            if hero.in_combat:
                hero.in_combat = False
                self._cleanup_melee_target(hero)
                hero.state = 'exploring'
                print(f"🛡️ {hero.type} 脱离战斗")

    def _cleanup_melee_target(self, unit):
        """清理近战目标追踪"""
        if unit.melee_target is not None:
            if unit.melee_target.melee_target == unit:
                unit.melee_target.melee_target = None
            unit.melee_target = None

    def _handle_hero_attack_buildings(self, current_time: float):
        """处理英雄攻击建筑物"""
        if not self.building_manager or not self.building_manager.buildings:
            return

        for hero in self.heroes[:]:
            if not hasattr(hero, 'attack_range') or not hasattr(hero, 'attack_cooldown'):
                continue

            hero_attack_range = hero.attack_range
            hero_can_attack = current_time - hero.last_attack >= hero.attack_cooldown

            if not hero_can_attack:
                continue

            # 寻找攻击范围内的建筑物
            for building in self.building_manager.buildings[:]:
                if not building.is_active:
                    continue

                # 计算建筑物位置（瓦片中心）
                building_x = building.x * self.tile_size + self.tile_size // 2
                building_y = building.y * self.tile_size + self.tile_size // 2

                # 计算距离
                dx = building_x - hero.x
                dy = building_y - hero.y
                distance_squared = dx * dx + dy * dy
                distance = math.sqrt(distance_squared)

                # 检查是否在攻击范围内
                if distance <= hero_attack_range:
                    # 执行攻击
                    if self._execute_hero_attack_building(hero, building, current_time):
                        print(
                            f"⚔️ {hero.type} 攻击建筑物 {building.building_type.value} (距离: {distance:.1f})")
                        break  # 一次只能攻击一个目标

    def _handle_hero_attack_functional_creatures(self, current_time: float):
        """处理英雄攻击功能性怪物"""
        for hero in self.heroes[:]:
            if not hasattr(hero, 'attack_range') or not hasattr(hero, 'attack_cooldown'):
                continue

            hero_attack_range = hero.attack_range
            hero_can_attack = current_time - hero.last_attack >= hero.attack_cooldown

            if not hero_can_attack:
                continue

            # 寻找攻击范围内的功能性怪物
            for creature in self.creatures[:]:
                # 跳过战斗单位（已经在主战斗循环中处理）
                if hasattr(creature, 'is_combat_unit') and creature.is_combat_unit:
                    continue

                # 只攻击功能性怪物（如哥布林苦工、地精工程师等）
                if creature.type in ['goblin_worker', 'goblin_engineer']:
                    # 计算距离
                    dx = creature.x - hero.x
                    dy = creature.y - hero.y
                    distance_squared = dx * dx + dy * dy
                    distance = math.sqrt(distance_squared)

                    # 检查是否在攻击范围内
                    if distance <= hero_attack_range:
                        # 执行攻击
                        if self._execute_hero_attack_creature(hero, creature, current_time):
                            print(
                                f"⚔️ {hero.type} 攻击功能性怪物 {creature.type} (距离: {distance:.1f})")
                            break  # 一次只能攻击一个目标

    def _execute_hero_attack_building(self, hero, building, current_time: float) -> bool:
        """执行英雄攻击建筑物"""
        try:
            # 计算伤害
            damage = hero.attack

            # 检查建筑物是否有护甲
            if hasattr(building, 'armor'):
                # 护甲减伤：每点护甲减少1点伤害，最少造成1点伤害
                damage = max(1, damage - building.armor)

            # 应用伤害
            if hasattr(building, 'take_damage'):
                building.take_damage(damage)
            elif hasattr(building, 'health'):
                building.health -= damage
                if building.health < 0:
                    building.health = 0

            # 更新攻击冷却
            hero.last_attack = current_time

            # 创建攻击特效
            if self.effect_manager:
                effect_type = hero._get_attack_effect_type()
                # 将世界坐标转换为屏幕坐标
                screen_x = hero.x - self.camera_x
                screen_y = hero.y - self.camera_y
                target_screen_x = (building.x * self.tile_size +
                                   self.tile_size // 2) - self.camera_x
                target_screen_y = (building.y * self.tile_size +
                                   self.tile_size // 2) - self.camera_y

                self.effect_manager.create_effect(
                    effect_type,
                    screen_x, screen_y,
                    target_screen_x, target_screen_y,
                    damage=damage
                )

            # 输出攻击日志
            building_health = getattr(building, 'health', 0)
            print(
                f"🏹 {hero.type} 攻击 {building.building_type.value} 造成 {damage} 点伤害 (建筑剩余: {building_health})")

            return True

        except Exception as e:
            print(f"❌ 英雄攻击建筑物出错: {e}")
            return False

    def _execute_hero_attack_creature(self, hero, creature, current_time: float) -> bool:
        """执行英雄攻击功能性怪物"""
        try:
            # 计算伤害
            damage = hero.attack

            # 检查怪物是否有护甲
            if hasattr(creature, 'armor'):
                # 护甲减伤：每点护甲减少1点伤害，最少造成1点伤害
                damage = max(1, damage - creature.armor)

            # 应用伤害
            creature.health -= damage
            if creature.health < 0:
                creature.health = 0

            # 更新攻击冷却
            hero.last_attack = current_time

            # 创建攻击特效
            if self.effect_manager:
                effect_type = hero._get_attack_effect_type()
                # 将世界坐标转换为屏幕坐标
                screen_x = hero.x - self.camera_x
                screen_y = hero.y - self.camera_y
                target_screen_x = creature.x - self.camera_x
                target_screen_y = creature.y - self.camera_y

                self.effect_manager.create_effect(
                    effect_type,
                    screen_x, screen_y,
                    target_screen_x, target_screen_y,
                    damage=damage
                )

            # 输出攻击日志
            print(
                f"🏹 {hero.type} 攻击 {creature.type} 造成 {damage} 点伤害 (怪物剩余: {creature.health})")

            return True

        except Exception as e:
            print(f"❌ 英雄攻击功能性怪物出错: {e}")
            return False

    def _handle_health_regeneration(self, current_time: float):
        """处理回血系统"""
        # 处理生物的回血
        for creature in self.creatures:
            if not creature.in_combat and creature.health < creature.max_health:
                # 检查是否脱离战斗足够长时间
                time_since_combat = current_time - creature.last_combat_time
                if time_since_combat >= creature.regeneration_delay:
                    # 开始回血
                    creature._regenerate_health(current_time)

        # 处理英雄的回血
        for hero in self.heroes:
            if not hero.in_combat and hero.health < hero.max_health:
                # 检查是否脱离战斗足够长时间
                time_since_combat = current_time - hero.last_combat_time
                if time_since_combat >= hero.regeneration_delay:
                    # 开始回血
                    hero._regenerate_health(current_time)

    def _cleanup_dead_units(self):
        """清理死亡的单位"""
        # 清理死亡的生物
        dead_creatures = [c for c in self.creatures if c.health <= 0]
        for creature in dead_creatures:
            # 清理近战目标追踪
            if creature.melee_target is not None:
                if creature.melee_target.melee_target == creature:
                    creature.melee_target.melee_target = None
                creature.melee_target = None
            # 清理挖掘分配
            if creature.type == 'goblin_worker':
                creature._cleanup_mining_assignment(self.game_map)
            self.creatures.remove(creature)
            print(f"💀 {creature.type} 死亡并被移除")

        # 清理死亡的英雄
        dead_heroes = [h for h in self.heroes if h.health <= 0]
        for hero in dead_heroes:
            # 清理近战目标追踪
            if hero.melee_target is not None:
                if hero.melee_target.melee_target == hero:
                    hero.melee_target.melee_target = None
                hero.melee_target = None
            self.heroes.remove(hero)
            print(f"💀 {hero.type} 死亡并被移除")

    def _spawn_hero(self):
        """生成英雄 - 在英雄基地附近刷新"""
        if random.random() < GameBalance.hero_spawn_rate:
            if not self.hero_bases:
                print("❌ 没有英雄基地，无法生成英雄")
                return

            # 随机选择一个英雄基地
            base_x, base_y, direction = random.choice(self.hero_bases)

            # 在基地附近的已挖掘区域生成英雄
            spawn_positions = []
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    x = base_x + dx
                    y = base_y + dy
                    if (0 <= x < self.map_width and 0 <= y < self.map_height):
                        tile = self.game_map[y][x]
                        if tile.type == TileType.GROUND or tile.is_dug:
                            spawn_positions.append((x, y))

            if spawn_positions:
                # 随机选择一个生成位置
                spawn_x, spawn_y = random.choice(spawn_positions)

                # 随机选择英雄类型
                if BESTIARY_AVAILABLE:
                    available_heroes = list(
                        character_db.get_all_heroes().keys())
                    hero_type = random.choice(available_heroes)
                    hero_data = character_db.get_character(hero_type)
                    hero_name = hero_data.name if hero_data else hero_type
                else:
                    hero_type = 'knight'
                    hero_name = '骑士'

                hero = Hero(spawn_x * self.tile_size + self.tile_size // 2,
                            spawn_y * self.tile_size + self.tile_size // 2, hero_type)
                self.heroes.append(hero)
                print(
                    f"{emoji_manager.COMBAT} {hero_name}从基地 ({base_x}, {base_y}) 入侵！")
            else:
                print("❌ 英雄基地附近没有可用的生成位置")

    def update(self, delta_time: float):
        """更新游戏逻辑"""
        # 更新生物
        for creature in self.creatures[:]:
            creature.update(delta_time, self.game_map,
                            self.creatures, self.heroes, self.effect_manager, self.building_manager)

        # 更新英雄
        for hero in self.heroes[:]:
            hero.update(delta_time, self.creatures,
                        self.game_map, self.effect_manager)

        # 更新特效系统
        if self.effect_manager:
            all_targets = self.creatures + self.heroes
            self.effect_manager.update(delta_time, all_targets)

        # 更新物理系统
        if self.physics_system:
            # 将毫秒转换为秒
            delta_seconds = delta_time / 1000.0
            all_units = self.creatures + self.heroes

            # 只更新击退效果，不处理单位间碰撞（避免召唤时的弹开效果）
            self.physics_system.update_knockbacks(delta_seconds, self.game_map)

        # 更新击退动画
        if self.knockback_animation:
            delta_seconds = delta_time / 1000.0
            self.knockback_animation.update(delta_seconds)

        # 更新建筑系统
        if self.building_manager:
            building_result = self.building_manager.update(
                delta_time, self.game_state, self.game_map)

            # 处理建筑系统事件
            for event in building_result.get('events', []):
                print(f"🏗️ {event}")

            # 检查是否有建筑完成，需要立即重新渲染
            if building_result.get('needs_rerender'):
                self._pending_rerender = True

        # 处理箭塔攻击
        self._handle_arrow_tower_attacks(delta_time)

        # 处理战斗
        self._handle_combat(delta_time)

        # 清理死亡的单位
        self._cleanup_dead_units()

        # 生成英雄
        self._spawn_hero()

        # 资源生成 - 使用累积器确保整数
        treasury_count = sum(1 for row in self.game_map for tile in row
                             if tile.room == 'treasury')

        # 黄金累积
        self.gold_accumulator += treasury_count * \
            GameBalance.gold_per_second_per_treasury * delta_time * 0.001
        if self.gold_accumulator >= 1.0:
            gold_to_add = int(self.gold_accumulator)
            self.game_state.gold += gold_to_add
            self.gold_accumulator -= gold_to_add
            # 确保金币始终为整数
            self.game_state.gold = int(self.game_state.gold)

        # 法力累积
        self.mana_accumulator += GameBalance.mana_regen_per_second * delta_time * 0.001
        if self.mana_accumulator >= 1.0:
            mana_to_add = int(self.mana_accumulator)
            self.game_state.mana = min(
                self.game_state.mana + mana_to_add, 200)  # 法力上限
            self.mana_accumulator -= mana_to_add

    def render(self):
        """渲染游戏"""
        # 清空屏幕
        self.screen.fill(GameConstants.COLORS['background'])

        # 处理待重新渲染的建筑
        if self._pending_rerender:
            self._force_rerender_buildings()
            self._pending_rerender = False

        # 渲染地图
        self._render_map()

        # 渲染目标连线（功能性怪物的目标可视化）
        from src.managers.movement_system import MovementSystem
        MovementSystem.render_target_lines(
            self.screen, self.camera_x, self.camera_y)

        # 渲染生物
        self._render_creatures()

        # 渲染英雄
        self._render_heroes()

        # 工程师状态指示器现在由统一的生物状态指示器系统处理

        # 渲染特效系统
        if self.effect_manager:
            self.screen = self.effect_manager.render(self.screen)

        # 渲染击退动画
        if self.knockback_animation:
            self.knockback_animation.render(
                self.screen, self.camera_x, self.camera_y)

        # 渲染鼠标高亮
        self._render_mouse_cursor()

        # 渲染UI
        self._render_ui()

        # 渲染怪物选择UI
        self.monster_selection_ui.render(
            self.screen, self.font, self.small_font)

        # 渲染后勤召唤UI
        self.logistics_selection_ui.render(
            self.screen, self.font, self.small_font)

        # 渲染角色图鉴
        if self.bestiary:
            self.bestiary.render(self.screen)

        # 渲染建筑系统UI
        if self.building_ui:
            # 更新地精工程师计数 - 从生物列表中统计
            goblin_engineer_count = sum(1 for creature in self.creatures
                                        if creature.type == 'goblin_engineer')
            self.building_ui.set_goblin_engineer_count(goblin_engineer_count)
            self.building_ui.render(
                self.screen, self.building_manager, self.game_state)

        # 渲染调试信息
        if self.debug_mode:
            self._render_debug_info()

        # 更新显示
        pygame.display.flip()

    def _render_map(self):
        """渲染地图"""
        for y in range(self.map_height):
            for x in range(self.map_width):
                tile = self.game_map[y][x]
                screen_x = x * self.tile_size - self.camera_x
                screen_y = y * self.tile_size - self.camera_y

                # 只渲染屏幕内的瓦片
                if (screen_x + self.tile_size < 0 or screen_x > GameConstants.WINDOW_WIDTH or
                        screen_y + self.tile_size < 0 or screen_y > GameConstants.WINDOW_HEIGHT):
                    continue

                # 绘制特殊标识和状态（优先处理特殊建筑）
                elif tile.room_type and tile.room_type.startswith('hero_base_'):
                    # 绘制英雄基地 - 正义风格的金蓝色设计
                    # 背景：渐变蓝色
                    base_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                               self.tile_size - 2, self.tile_size - 2)
                    pygame.draw.rect(self.screen, (25, 25, 112),
                                     base_bg_rect)  # 深蓝色背景

                    # 边框：双层边框效果
                    outer_border = pygame.Rect(
                        screen_x, screen_y, self.tile_size, self.tile_size)
                    inner_border = pygame.Rect(
                        screen_x + 2, screen_y + 2, self.tile_size - 4, self.tile_size - 4)
                    pygame.draw.rect(self.screen, (100, 149, 237),
                                     outer_border, 2)  # 外边框：天蓝色
                    pygame.draw.rect(self.screen, (255, 215, 0),
                                     inner_border, 1)  # 内边框：金色

                    # 中心装饰：城堡符号
                    base_text = self._safe_render_text(
                        self.font, emoji_manager.CASTLE, (255, 255, 255))  # 白色城堡
                    base_rect = base_text.get_rect(center=(
                        screen_x + self.tile_size // 2,
                        screen_y + self.tile_size // 2))
                    self.screen.blit(base_text, base_rect)

                    # 正义光环：十字装饰
                    center_x = screen_x + self.tile_size // 2
                    center_y = screen_y + self.tile_size // 2
                    # 垂直十字
                    pygame.draw.rect(self.screen, (255, 215, 0),
                                     (center_x - 1, center_y - 4, 2, 8))
                    # 水平十字
                    pygame.draw.rect(self.screen, (255, 215, 0),
                                     (center_x - 4, center_y - 1, 8, 2))

                    # 四个角的装饰：小星星
                    corner_size = 2
                    corners = [
                        (screen_x + 1, screen_y + 1),  # 左上
                        (screen_x + self.tile_size - 3, screen_y + 1),  # 右上
                        (screen_x + 1, screen_y + self.tile_size - 3),  # 左下
                        (screen_x + self.tile_size - 3,
                         screen_y + self.tile_size - 3)  # 右下
                    ]
                    for cx, cy in corners:
                        pygame.draw.rect(self.screen, (255, 215, 0),
                                         (cx, cy, corner_size, corner_size))

                    # 英雄基地渲染完成，跳过后续处理
                    continue
                elif tile.type == TileType.ROOM:
                    # 检查是否刚刚重新渲染过
                    if hasattr(tile, 'just_rerendered') and tile.just_rerendered:
                        # 清除重新渲染标记，跳过本次渲染
                        tile.just_rerendered = False
                        continue

                    # 渲染建筑瓦片
                    if tile.room_type and self.building_ui:
                        self._render_building_tile(
                            tile, screen_x, screen_y, x, y)
                        continue  # 跳过后续的普通渲染
                    else:
                        # 没有BuildingUI或room_type，使用默认颜色
                        color = self._get_building_color(
                            tile.room_type or tile.room)
                else:
                    # 选择普通瓦片颜色
                    color = self._get_tile_color(tile)

                # 绘制瓦片
                pygame.draw.rect(self.screen, color, (screen_x,
                                 screen_y, self.tile_size, self.tile_size))

                # 绘制边框
                pygame.draw.rect(self.screen, (50, 50, 50), (screen_x,
                                 screen_y, self.tile_size, self.tile_size), 1)

                # 绘制金矿和其他特殊瓦片
                if tile.is_gold_vein and tile.gold_amount > 0:
                    self._render_gold_mine_ui(screen_x, screen_y, tile)
                elif tile.is_gold_vein and tile.gold_amount <= 0:
                    self._render_depleted_mine_ui(screen_x, screen_y)

    def _render_building_tile(self, tile, screen_x: int, screen_y: int, x: int, y: int):
        """渲染建筑瓦片 - 统一处理完成和未完成建筑"""

        # 特殊处理2x2地牢之心：只在中心瓦片渲染完整外观
        if (hasattr(tile, 'is_dungeon_heart_part') and tile.is_dungeon_heart_part and
                hasattr(tile, 'dungeon_heart_center')):
            center_x, center_y = tile.dungeon_heart_center

            # 只在中心瓦片渲染完整的2x2地牢之心
            if x == center_x and y == center_y:
                # 计算2x2地牢之心的起始渲染坐标（左上角）
                start_screen_x = screen_x
                start_screen_y = screen_y

                self.building_ui._render_2x2_dungeon_heart(
                    self.screen, start_screen_x, start_screen_y, self.tile_size, tile)

                # 获取建筑对象并渲染生命条
                building = self._get_building_at_position(x, y)
                if building:
                    self.building_ui.render_building_health_bar(
                        self.screen, start_screen_x, start_screen_y, self.tile_size, tile, building)

                # 渲染建筑状态高亮
                self._render_building_status_overlay(
                    tile, screen_x, screen_y, x, y)
            else:
                # 非中心瓦片，只渲染背景色，不渲染任何内容
                # 这样中心瓦片的2x2渲染会覆盖这些区域
                pass
            return

        if tile.is_incomplete:
            # 未完成建筑 - 创建半透明表面
            building_surface = pygame.Surface((self.tile_size, self.tile_size))
            building_surface.set_alpha(128)  # 50%透明度

            # 获取建筑对象并同步生命值
            building = self._get_building_at_position(x, y)
            self._sync_building_construction_health(building, tile)

            # 使用建筑对象自己的渲染方法
            if building:
                building.render(building_surface, 0, 0, self.tile_size,
                                self.font_manager, self.building_ui)
                # 将半透明表面绘制到主屏幕
                self.screen.blit(building_surface, (screen_x, screen_y))
                # 渲染生命条
                building.render_health_bar(
                    self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui)
            else:
                # 回退到简单渲染
                pygame.draw.rect(building_surface, (100, 100, 100),
                                 (0, 0, self.tile_size, self.tile_size))
                self.screen.blit(building_surface, (screen_x, screen_y))

            # 渲染建筑状态高亮（包括血量条）
            self._render_building_status_overlay(
                tile, screen_x, screen_y, x, y)

        else:
            # 完成的建筑 - 正常渲染
            building = self._get_building_at_position(x, y)
            if building:
                # 使用建筑对象自己的渲染方法
                building.render(self.screen, screen_x, screen_y,
                                self.tile_size, self.font_manager, self.building_ui)
                # 渲染生命条
                building.render_health_bar(
                    self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui)
            else:
                # 回退到简单渲染
                pygame.draw.rect(self.screen, (100, 100, 100),
                                 (screen_x, screen_y, self.tile_size, self.tile_size))

            # 渲染建筑状态高亮
            self._render_building_status_overlay(
                tile, screen_x, screen_y, x, y)

    def _get_tile_color(self, tile):
        """获取瓦片颜色"""
        if tile.type == TileType.ROCK:
            return GameConstants.COLORS['gold_vein'] if tile.is_gold_vein else GameConstants.COLORS['rock']
        elif tile.type == TileType.GROUND:
            return GameConstants.COLORS['ground']
        elif tile.type == TileType.GOLD_VEIN:
            return GameConstants.COLORS['gold_vein']
        else:
            return GameConstants.COLORS['rock']

    def _force_rerender_buildings(self):
        """强制重新渲染所有标记为需要重新渲染的建筑瓦片"""
        for y in range(self.map_height):
            for x in range(self.map_width):
                tile = self.game_map[y][x]
                if hasattr(tile, 'needs_rerender') and tile.needs_rerender:
                    # 清除重新渲染标记
                    tile.needs_rerender = False

                    # 计算屏幕坐标
                    screen_x = x * self.tile_size - self.camera_x
                    screen_y = y * self.tile_size - self.camera_y

                    # 只重新渲染屏幕内的瓦片
                    if (screen_x + self.tile_size < 0 or screen_x > GameConstants.WINDOW_WIDTH or
                            screen_y + self.tile_size < 0 or screen_y > GameConstants.WINDOW_HEIGHT):
                        continue

                    # 重新渲染建筑瓦片
                    if tile.type == TileType.ROOM and tile.room_type and self.building_ui:
                        self._render_building_tile(
                            tile, screen_x, screen_y, x, y)
                        # 标记为已重新渲染，避免被_render_map覆盖
                        tile.just_rerendered = True

    def _render_building_status_overlay(self, tile, screen_x: int, screen_y: int, x: int, y: int):
        """渲染建筑状态高亮覆盖层 - 在最后绘制，确保不被覆盖"""
        if not self.status_indicator:
            return

        # 获取建筑对象
        building = self._get_building_at_position(x, y)
        if not building:
            return

        # 特殊处理地牢之心的血量条显示
        if hasattr(building, 'building_type') and building.building_type.value == 'dungeon_heart':
            self._render_dungeon_heart_health_bar(building, screen_x, screen_y)

        # 根据建筑状态渲染高亮
        if building.status.value == 'destroyed':
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, self.tile_size, 'destroyed')
        elif building.status.value == 'damaged' or (hasattr(building, 'health') and building.health < building.max_health):
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, self.tile_size, 'damaged')
        elif building.status.value == 'completed':
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, self.tile_size, 'completed')
        elif tile.is_incomplete:
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, self.tile_size, 'incomplete')

    def _render_dungeon_heart_health_bar(self, building, screen_x: int, screen_y: int):
        """渲染地牢之心的血量条（2x2建筑）"""
        if not hasattr(building, 'health') or not hasattr(building, 'max_health'):
            return

        # 计算血量百分比
        health_percentage = building.health / \
            building.max_health if building.max_health > 0 else 0.0

        # 2x2地牢之心的血量条尺寸和位置
        total_width = self.tile_size * 2  # 2x2建筑的总宽度
        bar_width = total_width - 16  # 更宽的血量条
        bar_height = 8  # 更高的血量条
        bar_x = screen_x + 8  # 血量条X位置（居中）
        bar_y = screen_y - 15  # 血量条Y位置（建筑上方）

        # 绘制血量条背景（深红色）
        background_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, (100, 0, 0), background_rect)  # 深红色背景
        pygame.draw.rect(self.screen, (150, 0, 0), background_rect, 1)  # 深红色边框

        # 绘制当前血量（绿色到红色的渐变）
        if health_percentage > 0:
            current_width = int(bar_width * health_percentage)
            health_rect = pygame.Rect(bar_x, bar_y, current_width, bar_height)

            # 根据血量百分比选择颜色
            if health_percentage > 0.6:
                health_color = (0, 255, 0)  # 绿色（健康）
            elif health_percentage > 0.3:
                health_color = (255, 255, 0)  # 黄色（警告）
            else:
                health_color = (255, 0, 0)  # 红色（危险）

            pygame.draw.rect(self.screen, health_color, health_rect)

        # 绘制血量文字
        health_text = f"{building.health}/{building.max_health}"
        health_surface = self._safe_render_text(
            self.font, health_text, (255, 255, 255))
        text_rect = health_surface.get_rect(
            center=(screen_x + self.tile_size // 2, bar_y - 8))
        self.screen.blit(health_surface, text_rect)

        # 如果正在受到攻击，添加闪烁效果
        if hasattr(building, 'is_under_attack') and building.is_under_attack():
            # 添加红色闪烁边框
            flash_rect = pygame.Rect(
                screen_x - 2, screen_y - 2, self.tile_size + 4, self.tile_size + 4)
            pygame.draw.rect(self.screen, (255, 0, 0), flash_rect, 2)

    def _render_building_status_highlight(self, building, screen_x: int, screen_y: int):
        """渲染建筑状态高亮（已废弃，使用_render_building_status_overlay代替）"""
        if building.status.value == 'destroyed':
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, self.tile_size, 'destroyed')
        elif building.status.value == 'damaged' or (hasattr(building, 'health') and building.health < building.max_health):
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, self.tile_size, 'damaged')
        elif building.status.value == 'completed':
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, self.tile_size, 'completed')

    def _render_gold_mine_ui(self, screen_x: int, screen_y: int, tile):
        """渲染金矿UI - 现代化设计"""
        # 计算储量百分比
        max_gold = 100  # 假设最大储量为100
        gold_percentage = min(tile.gold_amount / max_gold, 1.0)

        # 根据储量选择颜色
        if gold_percentage > 0.7:
            # 高储量：亮金色
            base_color = (255, 215, 0)      # 金色
            border_color = (184, 134, 11)   # 深金色
            glow_color = (255, 255, 150)    # 发光效果
        elif gold_percentage > 0.3:
            # 中储量：中等金色
            base_color = (255, 193, 7)      # 琥珀色
            border_color = (205, 127, 50)   # 铜色
            glow_color = (255, 255, 100)    # 淡发光
        else:
            # 低储量：暗金色
            base_color = (218, 165, 32)     # 金棒色
            border_color = (139, 69, 19)    # 马鞍棕色
            glow_color = (255, 255, 80)     # 微弱发光

        # 绘制主背景
        main_rect = pygame.Rect(
            screen_x + 1, screen_y + 1, self.tile_size - 2, self.tile_size - 2)
        pygame.draw.rect(self.screen, base_color, main_rect)

        # 绘制发光效果
        glow_rect = pygame.Rect(
            screen_x + 3, screen_y + 3, self.tile_size - 6, self.tile_size - 6)
        pygame.draw.rect(self.screen, glow_color, glow_rect, 1)

        # 绘制边框
        pygame.draw.rect(self.screen, border_color, main_rect, 2)

        # 绘制金矿图标 - 使用更现代的符号
        center_x = screen_x + self.tile_size // 2
        center_y = screen_y + self.tile_size // 2

        # 绘制钻石形状的金矿图标
        diamond_points = [
            (center_x, center_y - 6),      # 上
            (center_x + 6, center_y),      # 右
            (center_x, center_y + 6),      # 下
            (center_x - 6, center_y)       # 左
        ]
        pygame.draw.polygon(self.screen, (255, 255, 255), diamond_points)
        pygame.draw.polygon(self.screen, (200, 200, 200), diamond_points, 1)

        # 绘制储量条
        bar_width = self.tile_size - 8
        bar_height = 3
        bar_x = screen_x + 4
        bar_y = screen_y + self.tile_size - 8

        # 背景条
        bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, (100, 100, 100), bar_bg_rect)

        # 储量条
        bar_fill_width = int(bar_width * gold_percentage)
        if bar_fill_width > 0:
            bar_fill_rect = pygame.Rect(
                bar_x, bar_y, bar_fill_width, bar_height)
            pygame.draw.rect(self.screen, (255, 255, 0), bar_fill_rect)

        # 挖掘状态指示
        if tile.being_mined or tile.miners_count > 0:
            if self.status_indicator:
                self.status_indicator.render_mining_highlight(
                    self.screen, screen_x, screen_y, self.tile_size, tile.miners_count)
            else:
                self._render_mining_status(screen_x, screen_y, tile)

    def _render_depleted_mine_ui(self, screen_x: int, screen_y: int):
        """渲染枯竭矿脉UI"""
        # 绘制灰色背景表示枯竭
        main_rect = pygame.Rect(
            screen_x + 2, screen_y + 2, self.tile_size - 4, self.tile_size - 4)
        pygame.draw.rect(self.screen, (139, 69, 19), main_rect)  # 马鞍棕色
        pygame.draw.rect(self.screen, (101, 67, 33), main_rect, 2)  # 深棕色边框

        # 绘制X符号表示枯竭
        center_x = screen_x + self.tile_size // 2
        center_y = screen_y + self.tile_size // 2

        # 绘制X
        pygame.draw.line(self.screen, (100, 100, 100),
                         (center_x - 4, center_y - 4), (center_x + 4, center_y + 4), 2)
        pygame.draw.line(self.screen, (100, 100, 100),
                         (center_x + 4, center_y - 4), (center_x - 4, center_y + 4), 2)

    def _render_mining_status(self, screen_x: int, screen_y: int, tile):
        """渲染挖掘状态指示"""
        # 根据挖掘者数量选择边框颜色和样式
        if tile.miners_count >= 3:
            # 满员：红色脉冲边框
            border_color = (255, 100, 100)
            border_width = 3
        elif tile.miners_count >= 2:
            # 较多：黄色边框
            border_color = (255, 255, 0)
            border_width = 2
        else:
            # 正常：绿色边框
            border_color = (0, 255, 0)
            border_width = 2

        # 绘制挖掘状态边框
        pygame.draw.rect(self.screen, border_color,
                         (screen_x, screen_y, self.tile_size, self.tile_size), border_width)

        # 显示挖掘者数量
        if tile.miners_count > 0:
            # 直接使用pygame.font.render，设置透明背景
            count_text = self.small_font.render(
                str(tile.miners_count), True, (255, 255, 255), None)
            # 在右上角显示数量
            count_x = screen_x + self.tile_size - 12
            count_y = screen_y + 2
            self.screen.blit(count_text, (count_x, count_y))

    def _render_creatures(self):
        """渲染生物"""
        for creature in self.creatures:
            screen_x = creature.x - self.camera_x
            screen_y = creature.y - self.camera_y

            # 绘制生物
            pygame.draw.circle(self.screen, creature.color,
                               (int(screen_x), int(screen_y)), creature.size // 2)

            # 绘制状态指示器
            self._render_creature_status_indicator(
                creature, screen_x, screen_y)

            # 为哥布林苦工绘制特殊标识和携带金币信息
            if creature.type == 'goblin_worker':
                self._render_goblin_worker_special(
                    creature, screen_x, screen_y)

            # 绘制血条
            if creature.health < creature.max_health:
                bar_width = creature.size
                bar_height = 3
                health_ratio = creature.health / creature.max_health

                # 红色背景
                pygame.draw.rect(self.screen, (255, 0, 0),
                                 (screen_x - bar_width//2, screen_y - 25, bar_width, bar_height))
                # 绿色血量
                pygame.draw.rect(self.screen, (0, 255, 0),
                                 (screen_x - bar_width//2, screen_y - 25, bar_width * health_ratio, bar_height))

    def _render_heroes(self):
        """渲染英雄"""
        for hero in self.heroes:
            screen_x = hero.x - self.camera_x
            screen_y = hero.y - self.camera_y

            # 绘制英雄
            pygame.draw.rect(self.screen, hero.color,
                             (screen_x - hero.size//2, screen_y - hero.size//2, hero.size, hero.size))

            # 移除了所有英雄状态图标显示

            # 绘制血条
            if hero.health < hero.max_health:
                bar_width = hero.size
                bar_height = 3
                health_ratio = hero.health / hero.max_health

                pygame.draw.rect(self.screen, (255, 0, 0),
                                 (screen_x - bar_width//2, screen_y - 25, bar_width, bar_height))
                pygame.draw.rect(self.screen, (0, 255, 0),
                                 (screen_x - bar_width//2, screen_y - 25, bar_width * health_ratio, bar_height))

    def _render_creature_status_indicator(self, creature, screen_x, screen_y):
        """渲染生物状态指示器"""
        # 使用新的状态指示器系统
        if self.status_indicator:
            self.status_indicator.render(
                self.screen, screen_x, screen_y, creature.size, creature.state)
        else:
            # 回退到旧的颜色系统
            status_colors = {
                'fighting': (255, 0, 0),      # 红色 - 战斗中
                'moving': (0, 255, 0),        # 绿色 - 移动中
                'moving_to_mine': (0, 255, 0),  # 绿色 - 移动到挖掘点
                'mining': (255, 215, 0),      # 金色 - 挖掘中
                'fleeing': (64, 64, 64),      # 深灰色 - 逃跑中
                'returning_to_base': (0, 255, 255),  # 青色 - 返回基地
                'wandering': (255, 165, 0),   # 橙色 - 游荡中
                'idle': (255, 255, 255),      # 白色 - 空闲

                # 工程师专用状态
                'moving_to_site': (0, 255, 0),    # 绿色 - 前往工地
                'constructing': (255, 165, 0),    # 橙色 - 建造中
                'repairing': (255, 215, 0),       # 黄色 - 修理中
                'upgrading': (138, 43, 226),      # 紫色 - 升级中
                'returning': (0, 255, 255)        # 青色 - 返回中
            }

            if creature.state in status_colors:
                color = status_colors[creature.state]
                # 在生物右上角绘制竖向空心长方形指示器
                indicator_width = 4
                indicator_height = 8
                indicator_x = screen_x + creature.size//2 - indicator_width//2
                indicator_y = screen_y - creature.size//2 - indicator_height - 2
                pygame.draw.rect(self.screen, color,
                                 (indicator_x, indicator_y,
                                  indicator_width, indicator_height), 1)

    def _render_goblin_worker_special(self, creature, screen_x, screen_y):
        """渲染哥布林苦工特殊效果"""
        # 已取消金币显示，保持方法为空以备用
        pass

    def _render_mouse_cursor(self):
        """渲染鼠标光标高亮"""
        if (self.build_mode != BuildMode.NONE and
            self.mouse_world_x >= 0 and self.mouse_world_y >= 0 and
                self.mouse_world_x < self.map_width and self.mouse_world_y < self.map_height):

            screen_x = self.mouse_world_x * self.tile_size - self.camera_x
            screen_y = self.mouse_world_y * self.tile_size - self.camera_y

            tile = self.game_map[self.mouse_world_y][self.mouse_world_x]

            # 检查是否可以建造
            can_build = False
            highlight_color = GameConstants.COLORS['highlight_red']

            if self.build_mode == BuildMode.DIG:
                can_build = tile.type == TileType.ROCK
                highlight_color = GameConstants.COLORS[
                    'highlight_green'] if can_build else GameConstants.COLORS['highlight_red']
                if can_build and tile.is_gold_vein:
                    highlight_color = GameConstants.COLORS['highlight_gold']
            elif self.build_mode in [BuildMode.SUMMON, BuildMode.SUMMON_LOGISTICS]:
                # 检查基础地形条件
                terrain_ok = tile.type in [TileType.GROUND, TileType.ROOM]

                # 检查位置是否被占用
                position_occupied = False
                if terrain_ok:
                    if self.build_mode == BuildMode.SUMMON:
                        creature_type = self.selected_monster_type
                    elif self.build_mode == BuildMode.SUMMON_LOGISTICS:
                        creature_type = getattr(
                            self, 'selected_logistics_type', 'goblin_worker')

                    position_occupied = self._check_summon_position_occupied(
                        self.mouse_world_x, self.mouse_world_y, creature_type)

                # 综合判断是否可以建造
                can_build = terrain_ok and not position_occupied

                # 设置高亮颜色
                if not terrain_ok:
                    # 红色：地形不合适
                    highlight_color = GameConstants.COLORS['highlight_red']
                elif position_occupied:
                    highlight_color = (255, 165, 0)  # 橙色：位置被占用
                else:
                    highlight_color = (0, 255, 255)  # 青色：可以召唤

            # 绘制高亮
            pygame.draw.rect(self.screen, highlight_color,
                             (screen_x, screen_y, self.tile_size, self.tile_size), 3)

            # 绘制半透明覆盖
            overlay = pygame.Surface((self.tile_size, self.tile_size))
            overlay.set_alpha(80)
            overlay.fill(highlight_color)
            self.screen.blit(overlay, (screen_x, screen_y))

    def _render_ui(self):
        """渲染用户界面"""
        # 使用美化的UI渲染器
        self.game_ui.render_resource_panel(self.game_state, len(
            self.creatures), GameBalance.max_creatures, self.building_manager)
        self.game_ui.render_build_panel(self.build_mode, self.game_state)
        self.game_ui.render_status_panel(
            self.mouse_world_x, self.mouse_world_y,
            self.camera_x, self.camera_y,
            self.build_mode, self.debug_mode
        )
        self.game_ui.render_game_info_panel(self.game_state.wave_number)

    def _render_resource_panel(self):
        """渲染资源面板"""
        panel_x, panel_y = 10, 10
        panel_width, panel_height = 200, 180

        # 绘制面板背景
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.set_alpha(200)
        panel_surface.fill((0, 0, 0))
        self.screen.blit(panel_surface, (panel_x, panel_y))

        # 绘制边框
        pygame.draw.rect(self.screen, GameConstants.COLORS['ui_border'],
                         (panel_x, panel_y, panel_width, panel_height), 2)

        # 绘制标题 - 分别渲染emoji和中文
        emoji_surface = self.font_manager.safe_render(
            self.font, emoji_manager.CHART, (255, 102, 0))
        text_surface = self.font_manager.safe_render(
            self.font, " 资源状况", (255, 102, 0))

        # 渲染emoji
        self.screen.blit(emoji_surface, (panel_x + 10, panel_y + 10))
        # 渲染中文
        self.screen.blit(text_surface, (panel_x + 10 +
                         emoji_surface.get_width(), panel_y + 10))

        # 绘制资源信息 - 分离emoji和中文渲染
        resources = [
            ('gold', (emoji_manager.MONEY,
             f"黄金: {int(self.game_state.gold)}"), (255, 255, 255)),
            ('mana',
             ("🔮", f"法力: {int(self.game_state.mana)}"), (100, 149, 237)),
            ('food', ("🍖", f"食物: {int(self.game_state.food)}"), (255, 165, 0)),
            ('raw_gold',
             ("⚡", f"原始黄金: {int(self.game_state.raw_gold)}"), (255, 215, 0)),
            ('creatures', (emoji_manager.MONSTER,
             f"怪物: {len(self.creatures)}/{GameBalance.max_creatures}"), (255, 107, 107)),
            ('score',
             ("🏆", f"分数: {int(self.game_state.score)}"), (255, 255, 255)),
            ('wave',
             ("🌊", f"波次: {self.game_state.wave_number}"), (135, 206, 235))
        ]

        for i, (resource_id, (emoji, text), color) in enumerate(resources):
            # 分别渲染emoji和中文文本
            emoji_surface = self.font_manager.safe_render(
                self.small_font, emoji, color)
            text_surface = self.font_manager.safe_render(
                self.small_font, text, color)

            # 计算位置并渲染
            x_offset = panel_x + 10
            y_offset = panel_y + 40 + i * 20

            # 渲染emoji
            self.screen.blit(emoji_surface, (x_offset, y_offset))
            x_offset += emoji_surface.get_width() + 5

            # 渲染中文
            self.screen.blit(text_surface, (x_offset, y_offset))

    def _render_build_panel(self):
        """渲染建造面板"""
        panel_x = GameConstants.WINDOW_WIDTH - 180
        panel_y = 10
        panel_width, panel_height = 170, 200

        # 绘制面板背景
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.set_alpha(200)
        panel_surface.fill((0, 0, 0))
        self.screen.blit(panel_surface, (panel_x, panel_y))

        # 绘制边框
        pygame.draw.rect(self.screen, GameConstants.COLORS['ui_border'],
                         (panel_x, panel_y, panel_width, panel_height), 2)

        # 绘制标题 - 分别渲染emoji和中文
        emoji_surface = self.font_manager.safe_render(
            self.font, emoji_manager.HAMMER, (255, 102, 0))
        text_surface = self.font_manager.safe_render(
            self.font, " 建造选项", (255, 102, 0))

        # 渲染emoji
        self.screen.blit(emoji_surface, (panel_x + 10, panel_y + 10))
        # 渲染中文
        self.screen.blit(text_surface, (panel_x + 10 +
                         emoji_surface.get_width(), panel_y + 10))

        # 建造选项 - 使用统一字体管理器
        build_options = [
            ('dig', ("1.", emoji_manager.PICKAXE, "挖掘 (10金)"), BuildMode.DIG),
            ('building_panel', ("2.", emoji_manager.BUILD, "建筑面板"), None),
            ('summon_selection', ("4.", emoji_manager.MONSTER, "召唤怪物"),
             BuildMode.SUMMON_SELECTION),
        ]

        for i, (option_id, (number, emoji, text), mode) in enumerate(build_options):
            # 特殊处理建筑面板选项
            if option_id == 'building_panel':
                color = (0, 255, 0) if (
                    self.building_ui and self.building_ui.show_building_panel) else (255, 255, 255)
            else:
                color = (0, 255, 0) if self.build_mode == mode else (
                    255, 255, 255)

            # 分别渲染数字、emoji和中文文本
            number_surface = self.font_manager.safe_render(
                self.small_font, number, color)
            emoji_surface = self.font_manager.safe_render(
                self.small_font, emoji, color)
            text_surface = self.font_manager.safe_render(
                self.small_font, text, color)

            # 计算位置并渲染
            x_offset = panel_x + 10
            y_offset = panel_y + 40 + i * 25

            # 渲染数字
            self.screen.blit(number_surface, (x_offset, y_offset))
            x_offset += number_surface.get_width() + 5

            # 渲染emoji
            self.screen.blit(emoji_surface, (x_offset, y_offset))
            x_offset += emoji_surface.get_width() + 5

            # 渲染中文
            self.screen.blit(text_surface, (x_offset, y_offset))

    def _render_status_panel(self):
        """渲染状态面板"""
        panel_x = 10
        panel_y = GameConstants.WINDOW_HEIGHT - 120
        panel_width, panel_height = 300, 110

        # 绘制面板背景
        panel_surface = pygame.Surface((panel_width, panel_height))
        panel_surface.set_alpha(200)
        panel_surface.fill((0, 0, 0))
        self.screen.blit(panel_surface, (panel_x, panel_y))

        # 绘制边框
        pygame.draw.rect(self.screen, GameConstants.COLORS['ui_border'],
                         (panel_x, panel_y, panel_width, panel_height), 2)

        # 绘制标题
        # 分别渲染emoji和中文
        emoji_surface = self._safe_render_text(
            self.font, emoji_manager.CHART, (255, 102, 0))
        text_surface = self._safe_render_text(
            self.font, " 游戏状态", (255, 102, 0))

        # 渲染emoji
        self.screen.blit(emoji_surface, (panel_x + 10, panel_y + 10))
        # 渲染中文
        self.screen.blit(text_surface, (panel_x + 10 +
                         emoji_surface.get_width(), panel_y + 10))

        # 状态信息
        build_mode_text = self.build_mode.value if self.build_mode != BuildMode.NONE else "无"
        status_info = [
            f"建造模式: {build_mode_text}",
            f"鼠标位置: ({self.mouse_x}, {self.mouse_y})",
            f"世界坐标: ({self.mouse_world_x}, {self.mouse_world_y})",
            f"相机位置: ({int(self.camera_x)}, {int(self.camera_y)})"
        ]

        for i, text in enumerate(status_info):
            rendered_text = self._safe_render_text(
                self.small_font, text, (200, 200, 200))
            self.screen.blit(
                rendered_text, (panel_x + 10, panel_y + 40 + i * 18))

    def _render_debug_info(self):
        """渲染调试信息"""
        debug_x = 10
        debug_y = 200

        # 创建调试面板背景
        debug_width = 300
        debug_height = 200
        debug_surface = pygame.Surface((debug_width, debug_height))
        debug_surface.set_alpha(200)
        debug_surface.fill((0, 0, 0))
        self.screen.blit(debug_surface, (debug_x, debug_y))

        # 绘制边框
        pygame.draw.rect(self.screen, (255, 255, 0),
                         (debug_x, debug_y, debug_width, debug_height), 2)

        # 调试标题 - 分别渲染emoji和中文
        emoji_surface = self._safe_render_text(
            self.small_font, "🐛", (255, 255, 0))
        text_surface = self._safe_render_text(
            self.small_font, " 挖掘系统调试", (255, 255, 0))

        # 渲染emoji
        self.screen.blit(emoji_surface, (debug_x + 10, debug_y + 10))
        # 渲染中文
        self.screen.blit(text_surface, (debug_x + 10 +
                         emoji_surface.get_width(), debug_y + 10))

        # 统计信息
        goblin_workers = [
            c for c in self.creatures if c.type == 'goblin_worker']
        active_miners = sum(1 for g in goblin_workers if g.state == 'mining')
        total_gold_veins = sum(
            1 for row in self.game_map for tile in row if tile.is_gold_vein and tile.gold_amount > 0)
        depleted_veins = sum(
            1 for row in self.game_map for tile in row if tile.is_gold_vein and tile.gold_amount <= 0)

        debug_info = [
            f"哥布林苦工总数: {len(goblin_workers)}",
            f"正在挖掘: {active_miners}",
            f"活跃金矿: {total_gold_veins}",
            f"枯竭金矿: {depleted_veins}",
            f"原始黄金储量: {int(self.game_state.raw_gold)}",
            f"金币储量: {int(self.game_state.gold)}",
            f"平均携带量: {int(sum(g.carried_gold for g in goblin_workers) / max(1, len(goblin_workers)))}"
        ]

        # 添加物理系统调试信息
        if self.physics_system:
            physics_stats = self.physics_system.get_performance_stats()
            debug_info.extend([
                f"",  # 空行
                f"=== 物理系统 ===",
                f"碰撞检测次数: {physics_stats['collision_checks']}",
                f"击退计算次数: {physics_stats['knockback_calculations']}",
                f"活跃击退: {physics_stats['active_knockbacks']}",
                f"空间哈希格子: {physics_stats['spatial_hash_cells']}",
                f"撞墙次数: {physics_stats['wall_collisions']}"
            ])

        if self.knockback_animation:
            effect_stats = self.knockback_animation.get_effect_count()
            debug_info.extend([
                f"粒子效果: {effect_stats['particles']}",
                f"闪烁效果: {effect_stats['flash_effects']}",
                f"屏幕震动: {'是' if effect_stats['screen_shake_active'] else '否'}"
            ])

        for i, info in enumerate(debug_info):
            text = self._safe_render_text(
                self.small_font, info, (255, 255, 255))
            self.screen.blit(text, (debug_x + 10, debug_y + 35 + i * 18))

        # 绘制哥布林苦工状态
        if goblin_workers:
            worker_info_y = debug_y + 35 + len(debug_info) * 18 + 10
            status_text = self._safe_render_text(
                self.small_font, "苦工状态:", (255, 255, 0))
            self.screen.blit(status_text, (debug_x + 10, worker_info_y))

            for i, worker in enumerate(goblin_workers[:5]):  # 只显示前5个
                state_color = {
                    'mining': (255, 215, 0),
                    'moving_to_mine': (0, 255, 0),
                    'fleeing': (255, 255, 0),
                    'returning_to_base': (0, 255, 255),
                    'wandering': (255, 165, 0),
                    'idle': (128, 128, 128)
                }.get(worker.state, (255, 255, 255))

                worker_text = f"苦工{i+1}: {worker.state} ({worker.carried_gold:.1f}金)"
                text = self._safe_render_text(
                    self.small_font, worker_text, state_color)
                self.screen.blit(
                    text, (debug_x + 10, worker_info_y + 20 + i * 15))

    def handle_events(self):
        """处理事件"""
        for event in pygame.event.get():
            # 让建筑UI先处理事件
            if self.building_ui and self.building_ui.handle_event(event, self.building_manager):
                # 检查是否有选中的建筑类型
                selected_building = self.building_ui.get_selected_building_type()

                if selected_building:
                    self.build_mode = BuildMode.BUILD_SPECIFIC
                    self.selected_building_type = selected_building
                    print(f"🏗️ 选择了建筑: {selected_building.value}")
                continue  # 事件已被建筑UI处理

            # 让怪物选择UI先处理事件
            if self.monster_selection_ui.handle_event(event, character_db if BESTIARY_AVAILABLE else None):
                # 检查是否有选中的怪物
                if self.monster_selection_ui.selected_monster:
                    self.build_mode = BuildMode.SUMMON
                    self.selected_monster_type = self.monster_selection_ui.selected_monster
                    # 清空UI中的选择，避免重复处理
                    self.monster_selection_ui.selected_monster = None
                    print(f"🎯 选择了怪物: {self.selected_monster_type}，进入召唤模式")
                continue  # 事件已被怪物选择UI处理

            # 让后勤召唤UI处理事件
            if self.logistics_selection_ui.handle_event(event, character_db if BESTIARY_AVAILABLE else None):
                # 检查是否有选中的后勤单位
                selected_logistics = self.logistics_selection_ui.get_selected_logistics()
                if selected_logistics:
                    self.build_mode = BuildMode.SUMMON_LOGISTICS
                    self.selected_logistics_type = selected_logistics
                    print(f"🎒 选择了后勤单位: {selected_logistics}")
                continue  # 事件已被后勤UI处理

            # 让角色图鉴系统处理事件
            if self.bestiary and self.bestiary.handle_event(event):
                continue  # 事件已被图鉴处理

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    self._handle_click(event.pos)
                elif event.button == 3:  # 右键
                    self.build_mode = BuildMode.NONE

            elif event.type == pygame.MOUSEMOTION:
                self.mouse_x, self.mouse_y = event.pos
                self._update_world_mouse_position()

            elif event.type == pygame.KEYDOWN:
                # 数字键选择建造模式
                if event.key == pygame.K_1:
                    self.build_mode = BuildMode.DIG
                elif event.key == pygame.K_2:
                    # 显示建筑面板 - 使用互斥窗口管理
                    if self.building_ui and self.building_ui.show_building_panel:
                        self._close_all_ui_windows()  # 如果已打开则关闭
                    else:
                        self._open_ui_window("building")  # 否则打开建筑面板
                elif event.key == pygame.K_4:
                    # 显示怪物选择UI - 使用互斥窗口管理
                    self._open_ui_window("monster_selection")
                elif event.key == pygame.K_5:
                    # 显示后勤召唤UI - 使用互斥窗口管理
                    self._open_ui_window("logistics_selection")
                elif event.key == pygame.K_ESCAPE:
                    # ESC键关闭所有UI窗口并取消建造模式
                    self._close_all_ui_windows()
                    self.build_mode = BuildMode.NONE
                elif self._is_key_pressed(event, ['b', 'B']):
                    # B键打开角色图鉴 - 使用互斥窗口管理
                    if BESTIARY_AVAILABLE:
                        self._open_ui_window("bestiary")
                elif event.key == pygame.K_p:
                    # 切换调试模式
                    self.debug_mode = not self.debug_mode
                    print(f"🐛 调试模式: {'开启' if self.debug_mode else '关闭'}")

                # WASD相机控制 - 增强的输入法兼容性检测
                elif self._is_key_pressed(event, ['w', 'W']):
                    self.camera_y -= 50
                    print(f"🎯 W键: 相机Y = {self.camera_y}")
                elif self._is_key_pressed(event, ['s', 'S']):
                    self.camera_y += 50
                    print(f"🎯 S键: 相机Y = {self.camera_y}")
                elif self._is_key_pressed(event, ['a', 'A']):
                    self.camera_x -= 50
                    print(f"🎯 A键: 相机X = {self.camera_x}")
                elif self._is_key_pressed(event, ['d', 'D']):
                    self.camera_x += 50
                    print(f"🎯 D键: 相机X = {self.camera_x}")

    def run(self):
        """运行游戏主循环"""
        print(f"{emoji_manager.GAME} 游戏开始运行...")
        print(f"{emoji_manager.TARGET} 控制说明:")
        print("  - 1键: 挖掘")
        print("  - 2键: 建筑面板 (建造各种建筑)")
        print("  - 4键: 召唤怪物 (弹出选择界面)")
        print("  - 5键: 后勤召唤 (地精工程师/哥布林苦工)")
        print("  - 鼠标左键: 执行建造")
        print("  - 鼠标右键: 取消建造模式")
        print("  - WASD: 移动相机")
        print("  - ESC: 取消建造模式")
        if BESTIARY_AVAILABLE:
            print("  - B键: 打开/关闭角色图鉴")
        if BUILDING_SYSTEM_AVAILABLE:
            print("  - TAB键: 统计面板 (查看详细统计)")
        print("  - 关闭窗口: 退出游戏")
        print()

        while self.running:
            current_time = time.time()
            delta_time = (current_time - self.last_time) * 1000  # 转换为毫秒
            self.last_time = current_time

            # 处理事件
            self.handle_events()

            # 更新游戏逻辑
            self.update(delta_time)

            # 渲染游戏
            self.render()

            # 控制帧率
            self.clock.tick(GameConstants.FPS_TARGET)

        print("🛑 游戏结束")
        pygame.quit()

    def _sync_building_construction_health(self, building, tile):
        """
        同步建筑建造进度和生命值

        Args:
            building: 建筑对象
            tile: 瓦片对象
        """
        if not building:
            return

        # 同步建造进度到tile对象
        tile.construction_progress = building.construction_progress

        # 根据建造进度同步生命值
        if hasattr(building, 'max_health') and hasattr(building, 'health'):
            # 计算建造进度对应的生命值
            progress = building.construction_progress
            target_health = int(building.max_health * progress)

            # 更新建筑和tile的生命值
            building.health = target_health
            tile.health = target_health
            tile.max_health = building.max_health

    def _get_building_at_position(self, x: int, y: int):
        """
        获取指定位置的建筑对象

        Args:
            x, y: 瓦片坐标

        Returns:
            Building对象或None
        """
        if not self.building_manager:
            return None

        for building in self.building_manager.buildings:
            # 处理2x2地牢之心
            if (hasattr(building, 'building_type') and
                building.building_type.value == 'dungeon_heart' and
                    hasattr(building, 'size') and building.size == (2, 2)):
                # 检查是否在2x2范围内
                if (building.x <= x < building.x + 2 and
                        building.y <= y < building.y + 2):
                    return building
            else:
                # 普通建筑：精确匹配坐标
                if building.x == x and building.y == y:
                    return building

        return None

    def _handle_arrow_tower_attacks(self, delta_time: float):
        """处理箭塔攻击 - 根据BUILDING_SYSTEM.md的攻击功能"""
        if not self.building_manager:
            return

        # 获取所有箭塔
        arrow_towers = [building for building in self.building_manager.buildings
                        if hasattr(building, 'building_type') and
                        building.building_type.value == 'arrow_tower' and
                        building.is_active]

        if not arrow_towers or not self.heroes:
            return

        # 为每个箭塔处理攻击
        for tower in arrow_towers:
            # 寻找最佳目标
            best_target = tower.find_best_target(self.heroes)

            if best_target:
                # 更新当前目标
                tower.current_target = best_target

                # 检查是否可以攻击
                if tower.can_attack_target(best_target) and tower.attack_cooldown <= 0:
                    # 先创建攻击特效，再执行攻击（与弓箭手逻辑保持一致）
                    if self.effect_manager:
                        # 根据是否为暴击选择不同的特效
                        is_critical = random.random() < tower.critical_chance
                        if is_critical:
                            effect_type = 'tower_critical_arrow'
                        else:
                            effect_type = 'tower_arrow_shot'

                        # 计算箭塔的精确像素位置（瓦片中心）
                        tower_pixel_x = tower.x * self.tile_size + self.tile_size // 2
                        tower_pixel_y = tower.y * self.tile_size + self.tile_size // 2

                        # 将世界坐标转换为屏幕坐标
                        tower_screen_x = tower_pixel_x - self.camera_x
                        tower_screen_y = tower_pixel_y - self.camera_y
                        target_screen_x = best_target.x - self.camera_x
                        target_screen_y = best_target.y - self.camera_y

                        # 创建攻击特效
                        self.effect_manager.create_effect(
                            effect_type,
                            tower_screen_x,
                            tower_screen_y,
                            target_screen_x,
                            target_screen_y,
                            damage=tower.attack_damage
                        )

                    # 执行攻击
                    attack_result = tower.attack_target(best_target)

                    if attack_result['attacked']:
                        # 创建命中特效
                        if self.effect_manager:
                            impact_screen_x = best_target.x - self.camera_x
                            impact_screen_y = best_target.y - self.camera_y

                            self.effect_manager.create_effect(
                                'tower_arrow_impact',
                                impact_screen_x,
                                impact_screen_y,
                                None, None,
                                damage=attack_result['damage']
                            )

                        # 输出攻击日志
                        critical_text = " (暴击!)" if attack_result['is_critical'] else ""
                        print(
                            f"🏹 箭塔攻击 {getattr(best_target, 'name', '敌人')} 造成 {attack_result['damage']} 点伤害{critical_text} (目标剩余: {attack_result['target_health']})")
            else:
                # 没有目标，清除当前目标
                tower.current_target = None

    def _build_selected_building(self, x: int, y: int):
        """建造选中的建筑"""
        if not self.building_manager or not hasattr(self, 'selected_building_type'):
            return

        building_type = self.selected_building_type

        # 检查是否可以建造
        can_build_result = self.building_manager.can_build(
            building_type, x, y, self.game_state, self.game_map
        )

        if can_build_result['can_build']:
            # 开始建造
            build_result = self.building_manager.start_construction(
                building_type, x, y, self.game_state, self.game_map
            )

            if build_result['started']:
                print(f"🏗️ 开始建造 {build_result['building'].name} 在 ({x}, {y})")
                # 清空选择
                self.selected_building_type = None
                self.build_mode = BuildMode.NONE
                if self.building_ui:
                    self.building_ui.clear_selections()
            else:
                print(f"❌ 建造失败: {build_result['message']}")
        else:
            print(f"❌ 无法建造: {can_build_result['message']}")


def main():
    """主函数"""
    try:
        # 检查pygame是否可用
        print(f"{emoji_manager.SEARCH} 检查pygame依赖...")
        pygame.mixer.quit()  # 测试pygame
        print(f"{emoji_manager.CHECK} pygame可用")

        # 创建并运行游戏
        game = WarForTheOverworldGame()
        game.run()

    except ImportError:
        print("❌ 缺少pygame库")
        print("🔧 安装方法:")
        print("   pip install pygame")
        print()
        input("按Enter键退出...")

    except Exception as e:
        print(f"❌ 游戏运行失败: {e}")
        input("按Enter键退出...")


if __name__ == "__main__":
    main()
