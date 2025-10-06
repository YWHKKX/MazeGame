#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏环境模拟器
提供完整的游戏环境模拟，包括地图、建筑、角色、管理器等
用于测试各种游戏逻辑
"""

from src.core.constants import GameConstants
from src.managers.movement_system import MovementSystem
from src.managers.tile_manager import TileManager
from src.managers.building_manager import BuildingManager
from src.utils.logger import game_logger
# 移除时间管理器依赖，统一使用绝对时间
from src.core.constants import GameBalance
from src.entities.creature import Creature
from src.entities.monsters import Monster
from src.entities.hero import Hero
from src.entities.monster.goblin_worker import GoblinWorker
from src.entities.monster.goblin_engineer import Engineer, EngineerType, EngineerConfig
from src.entities.building_types import ArrowTower, DungeonHeart, Treasury
from src.entities.building import Building, BuildingType, BuildingConfig, BuildingStatus, BuildingCategory, BuildingRegistry
from src.entities.gold_mine import GoldMine, GoldMineStatus
from src.core.enums import TileType
from src.core.game_state import GameState, Tile
from src.ui.building_ui import BuildingUI
from src.systems.physics_system import PhysicsSystem
from src.systems.knockback_animation import KnockbackAnimation
from src.systems.combat_system import CombatSystem
from src.effects.effect_manager import EffectManager
from src.managers.resource_manager import get_resource_manager
from src.effects.glow_effect import get_glow_manager
from src.managers.font_manager import UnifiedFontManager
from src.ui.character_bestiary import CharacterBestiary
from src.ui.monster_selection import MonsterSelectionUI
from src.ui.logistics_selection import LogisticsSelectionUI
from src.entities.building_types import MagicAltar, ArcaneTower
from src.entities.character_data import CharacterDatabase
from src.systems.knockback_animation import Particle
import sys
import os
import time
import pygame
import math
import random
from typing import List, Dict, Any, Optional, Tuple

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class IdleStateManager:
    """全局空闲状态管理器 - 统一管理所有生物的空闲到游荡状态转换"""

    def __init__(self):
        """初始化空闲状态管理器"""
        self.idle_units = {}  # {unit_id: {'start_time': timestamp, 'unit': unit}}
        self.idle_timeout = 1.0  # 空闲超时时间（秒）

    def register_idle_unit(self, unit):
        """注册进入空闲状态的单位"""
        unit_id = id(unit)
        current_time = time.time()

        # 如果单位已经在空闲列表中，更新开始时间
        if unit_id in self.idle_units:
            self.idle_units[unit_id]['start_time'] = current_time
        else:
            # 新单位进入空闲状态
            self.idle_units[unit_id] = {
                'start_time': current_time,
                'unit': unit
            }
            game_logger.debug(
                f"⏰ 单位进入空闲状态: {getattr(unit, 'name', 'Unknown')} (ID: {unit_id})")

    def unregister_idle_unit(self, unit):
        """取消注册空闲状态的单位"""
        unit_id = id(unit)
        if unit_id in self.idle_units:
            del self.idle_units[unit_id]
            game_logger.debug(
                f"⏰ 单位离开空闲状态: {getattr(unit, 'name', 'Unknown')} (ID: {unit_id})")

    def update_idle_units(self, delta_seconds: float):
        """更新所有空闲状态的单位"""
        current_time = time.time()
        units_to_remove = []

        for unit_id, unit_data in self.idle_units.items():
            unit = unit_data['unit']
            start_time = unit_data['start_time']
            idle_duration = current_time - start_time

            # 检查单位是否仍然存在且处于空闲状态
            if not self._is_unit_still_idle(unit):
                units_to_remove.append(unit_id)
                continue

            # 检查是否超时
            if idle_duration >= self.idle_timeout:
                self._transition_to_wandering(unit)
                units_to_remove.append(unit_id)

        # 清理已处理的单位
        for unit_id in units_to_remove:
            if unit_id in self.idle_units:
                del self.idle_units[unit_id]

    def _is_unit_still_idle(self, unit):
        """检查单位是否仍然处于空闲状态"""
        try:
            # 检查单位是否仍然存在
            if not hasattr(unit, 'state') and not hasattr(unit, 'status'):
                return False

            # 检查各种空闲状态 - 使用状态枚举
            if hasattr(unit, 'state'):
                from src.entities.creature import CreatureStatus
                if unit.state == CreatureStatus.IDLE.value:
                    return True

            if hasattr(unit, 'status'):
                # 工程师状态 - 使用工程师状态枚举
                from src.entities.monster.goblin_engineer import EngineerStatus
                if hasattr(unit.status, 'value') and unit.status.value == EngineerStatus.IDLE.value:
                    return True
                # 其他状态枚举
                if str(unit.status) == EngineerStatus.IDLE.value:
                    return True

            return False
        except Exception as e:
            game_logger.warning(f"⚠️ 检查单位空闲状态时出错: {e}")
            return False

    def _transition_to_wandering(self, unit):
        """将单位从空闲状态转换为游荡状态"""
        try:
            unit_name = getattr(unit, 'name', 'Unknown')
            unit_type = getattr(unit, 'type', 'Unknown')

            # 根据单位类型进行不同的状态转换
            if hasattr(unit, 'state'):
                # 通用生物状态转换 - 使用状态枚举
                from src.entities.creature import CreatureStatus
                unit.state = CreatureStatus.WANDERING.value
                game_logger.info(f"🎲 {unit_name} ({unit_type}) 从空闲状态转换为游荡状态")

            elif hasattr(unit, 'status'):
                # 工程师状态转换 - 使用工程师状态枚举
                from src.entities.monster.goblin_engineer import EngineerStatus
                if hasattr(EngineerStatus, 'WANDERING'):
                    unit.status = EngineerStatus.WANDERING
                    game_logger.info(
                        f"🎲 {unit_name} ({unit_type}) 从空闲状态转换为游荡状态")
                else:
                    # 回退到通用状态 - 使用状态枚举
                    from src.entities.creature import CreatureStatus
                    unit.state = CreatureStatus.WANDERING.value
                    game_logger.info(
                        f"🎲 {unit_name} ({unit_type}) 从空闲状态转换为游荡状态")

        except Exception as e:
            game_logger.error(f"❌ 转换单位到游荡状态时出错: {e}")

    def get_idle_unit_count(self):
        """获取当前空闲单位数量"""
        return len(self.idle_units)

    def get_idle_units_info(self):
        """获取空闲单位信息（用于调试）"""
        info = []
        for unit_id, unit_data in self.idle_units.items():
            unit = unit_data['unit']
            start_time = unit_data['start_time']
            idle_duration = time.time() - start_time

            unit_name = getattr(unit, 'name', 'Unknown')
            unit_type = getattr(unit, 'type', 'Unknown')

            info.append({
                'id': unit_id,
                'name': unit_name,
                'type': unit_type,
                'idle_duration': idle_duration
            })

        return info


class GameEnvironmentSimulator:
    """游戏环境模拟器 - 提供完整的游戏环境"""

    def __init__(self, screen_width: int = 1200, screen_height: int = 800, tile_size: int = 20, ui_scale: int = 1, map_width: int = None, map_height: int = None):
        """
        初始化游戏环境模拟器

        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            tile_size: 瓦片大小
            ui_scale: UI放大倍数，用于方便观察细节，默认值为1.0
            map_width: 地图宽度（瓦片数量），如果为None则根据屏幕大小自动计算
            map_height: 地图高度（瓦片数量），如果为None则根据屏幕大小自动计算
        """
        # 基础设置 - 与真实游戏保持一致
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.tile_size = tile_size  # 瓦片大小（原始大小）
        self.ui_scale = ui_scale  # UI放大倍数

        # 地图大小设置：优先使用传入的参数，否则根据屏幕大小自动计算
        if map_width is not None and map_height is not None:
            # 使用指定的地图大小
            self.map_width = map_width
            self.map_height = map_height
        else:
            # 根据屏幕大小自动计算地图大小（保持原有逻辑）
            scaled_tile_size = int(tile_size * ui_scale)
            self.map_width = screen_width // scaled_tile_size
            self.map_height = screen_height // scaled_tile_size

        # 相机设置（用于CombatSystem兼容性）
        self.camera_x = 0
        self.camera_y = 0
        self.camera_speed = 50  # 相机移动速度（像素/次）

        # 初始化Pygame - 与真实游戏保持一致
        pygame.init()  # 确保pygame完全初始化
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("War for the Overworld - 模拟器")
        self.clock = pygame.time.Clock()
        self.font = None
        self.small_font = None

        # 游戏状态
        self.game_state = GameState()

        # 管理器 - 与真实游戏保持一致
        self.building_manager = BuildingManager()
        self.building_manager.game_instance = self  # 设置游戏实例引用，与真实游戏一致
        # 使用全局 tile_manager 和 MovementSystem
        from src.managers.tile_manager import tile_manager
        from src.managers.movement_system import MovementSystem
        self.tile_manager = tile_manager  # 使用全局实例
        self.movement_system = MovementSystem  # 使用全局类

        # 初始化资源管理器 - 与真实游戏保持一致
        self.resource_manager = get_resource_manager(self)

        # 字体管理器（延迟初始化）
        self.font_manager = None

        # UI 系统组件（延迟初始化）
        self.character_bestiary = None
        self.monster_selection = None
        self.logistics_selection = None

        # 物理和特效系统 - 与真实游戏保持一致
        world_bounds = (0, 0, screen_width, screen_height)
        self.physics_system = PhysicsSystem(world_bounds, tile_size)
        self.knockback_animation = KnockbackAnimation()
        # 使用EffectManager作为主要的effect_manager，与真实游戏保持一致
        self.effect_manager = EffectManager(speed_multiplier=2.0)

        # 初始化最新的特效系统
        self.glow_manager = get_glow_manager()

        # 战斗系统 - 与真实游戏保持一致
        self.combat_system = CombatSystem()
        self.combat_system.set_game_instance(self)  # 设置游戏实例引用

        # 高级范围攻击系统 - 与真实游戏保持一致
        try:
            from src.systems.advanced_area_damage import get_advanced_area_damage_system
            self.advanced_area_damage_system = get_advanced_area_damage_system(
                self)
            game_logger.info("🎯 高级范围攻击系统初始化成功")
        except ImportError:
            self.advanced_area_damage_system = None
            game_logger.warning("⚠️ 高级范围攻击系统不可用，箭塔攻击可能失败")

        # 状态指示器系统 - 与真实游戏保持一致
        try:
            from src.ui.status_indicator import StatusIndicator
            self.status_indicator = StatusIndicator()
            self.cached_texts = {}  # 缓存文本渲染结果
            game_logger.info("🎨 状态指示器系统初始化成功")
        except ImportError:
            self.status_indicator = None
            self.cached_texts = {}
            game_logger.warning("⚠️ 状态指示器系统不可用")

        # 优化挖掘系统 - 与真实游戏保持一致
        try:
            from src.managers.optimized_mining_system import OptimizedMiningSystem
            self.optimized_mining_system = OptimizedMiningSystem()
            game_logger.info("⛏️ 优化挖掘系统初始化成功")
        except ImportError:
            self.optimized_mining_system = None
            game_logger.warning("⚠️ 优化挖掘系统不可用")

        # 全局空闲状态管理器
        self.idle_state_manager = IdleStateManager()
        game_logger.info("⏰ 全局空闲状态管理器初始化成功")

        # UI管理器 - 与真实游戏保持一致
        self.building_ui = None  # 延迟初始化

        # 性能优化缓存
        self._cached_ui_texts = {}  # 缓存UI文本
        self._last_ui_values = {}   # 上次UI值
        self._needs_ui_redraw = True  # 是否需要重绘UI

        # 地图数据
        self.game_map = self._create_map()

        # 游戏对象 - 与真实游戏保持一致，通过 building_manager 管理
        self.heroes = []     # 所有英雄
        self.monsters = []  # 所有怪物
        self.gold_mines = []  # 所有金矿

        # 特殊建筑引用
        self.dungeon_heart = None
        self.treasury = None

        # 主基地位置（用于工程师寻找）
        self.dungeon_heart_pos = None

        # 模拟状态
        self.simulation_time = 0.0
        self.is_paused = False

        # 怪物数量限制
        self.max_monsters = 0  # 最大怪物数量，由建筑决定

        # 使用安全的打印方法
        self._safe_log("🎮 游戏环境模拟器初始化完成")
        self._safe_log(
            f"   🗺️ 地图大小: {self.map_width}x{self.map_height}")
        self._safe_log(f"   📐 瓦片大小: {self.tile_size}像素")
        self._safe_log(f"   🔍 UI放大倍数: {self.ui_scale}x")

    def calculate_max_monsters(self) -> int:
        """计算最大怪物数量上限"""
        max_monsters = 0

        # 统计地牢之心数量（每个提供20个上限）
        dungeon_heart_count = 0
        for building in self.building_manager.buildings:
            if (hasattr(building, 'building_type') and
                building.building_type.value == 'dungeon_heart' and
                    building.is_active and not building.is_destroyed):
                dungeon_heart_count += 1

        # 统计兽人巢穴数量（每个提供5个上限）
        orc_lair_count = 0
        for building in self.building_manager.buildings:
            if (hasattr(building, 'building_type') and
                building.building_type.value == 'orc_lair' and
                    building.is_active and not building.is_destroyed):
                orc_lair_count += 1

        # 计算总上限
        max_monsters = dungeon_heart_count * 20 + orc_lair_count * 5

        # 更新最大怪物数量
        self.max_monsters = max_monsters

        return max_monsters

    def can_create_monster(self) -> bool:
        """检查是否可以创建新怪物"""
        current_monster_count = len(self.monsters)
        return current_monster_count < self.max_monsters

    def get_monster_capacity_info(self) -> Dict[str, Any]:
        """获取怪物容量信息"""
        current_count = len(self.monsters)
        max_count = self.calculate_max_monsters()

        return {
            'current': current_count,
            'max': max_count,
            'available': max(0, max_count - current_count),
            'can_create': current_count < max_count
        }

    def init_pygame(self):
        """初始化Pygame（用于可视化测试） - 现在Pygame已在初始化时设置"""
        # Pygame 已经在 __init__ 中初始化，这里只需要初始化UI组件
        if not self.font_manager:
            # 确保字体系统已初始化
            pygame.font.init()
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)

            self.font_manager = UnifiedFontManager()
            self.building_ui = BuildingUI(
                self.screen_width, self.screen_height, self.font_manager, game_instance=self)

            # 初始化完整的 UI 系统
            self.character_bestiary = CharacterBestiary(
                self.screen_width, self.screen_height, self.font_manager)
            self.monster_selection = MonsterSelectionUI(
                self.screen_width, self.screen_height, self.font_manager)
            self.logistics_selection = LogisticsSelectionUI(
                self.screen_width, self.screen_height, self.font_manager)

            game_logger.info("🎨 UI组件初始化完成")

    def _create_map(self) -> List[List[Tile]]:
        """创建游戏地图"""
        game_map = []

        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                # 创建基础地面瓦片
                tile = self.tile_manager.create_tile(
                    x=x, y=y,
                    tile_type=TileType.GROUND,
                    is_gold_vein=False,
                    gold_amount=0
                )
                row.append(tile)
            game_map.append(row)

        # 使用安全的打印方法处理表情符号
        if hasattr(self, 'font_manager') and self.font_manager:
            self.font_manager.safe_log_with_emoji(
                f"🗺️ 创建地图: {self.map_width}x{self.map_height}")
        else:
            # 回退到文本替代
            game_logger.info(f"[地图] 创建地图: {self.map_width}x{self.map_height}")
        return game_map

    def get_map_as_array(self) -> List[List[int]]:
        """获取地图作为2D数组，用于路径查找"""
        map_array = []
        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                tile = self.game_map[y][x]
                # 0 = 可通行, 1 = 不可通行
                # 只有ROCK类型不可通行，其他都可通行
                if tile.tile_type == TileType.ROCK:
                    row.append(1)
                else:
                    row.append(0)
            map_array.append(row)
        return map_array

    # ==================== 地图生成和管理 ====================

    def generate_blank_map(self, width: int = None, height: int = None) -> List[List[Tile]]:
        """
        生成空白网格地面地图

        Args:
            width: 地图宽度（瓦片数）
            height: 地图高度（瓦片数）

        Returns:
            List[List[Tile]]: 空白地图
        """
        if width is None:
            width = self.map_width
        if height is None:
            height = self.map_height

        game_map = []
        for y in range(height):
            row = []
            for x in range(width):
                tile = self.tile_manager.create_tile(
                    x=x, y=y,
                    tile_type=TileType.GROUND,
                    is_gold_vein=False,
                    gold_amount=0
                )
                row.append(tile)
            game_map.append(row)

        game_logger.info(f"🗺️ 生成空白地图: {width}x{height}")
        return game_map

    def add_gold_mine(self, x: int, y: int, gold_amount: int = 100) -> GoldMine:
        """
        在地图上添加金矿

        Args:
            x: 瓦片X坐标
            y: 瓦片Y坐标
            gold_amount: 金矿储量

        Returns:
            GoldMine: 金矿对象
        """
        if not (0 <= x < self.map_width and 0 <= y < self.map_height):
            game_logger.info(f"❌ 金矿位置超出地图范围: ({x}, {y})")
            return None

        # 创建金矿对象
        gold_mine = GoldMine(x, y, gold_amount)

        # 更新地图瓦片
        tile = self.game_map[y][x]
        tile.tile_type = TileType.GOLD_VEIN
        tile.is_gold_vein = True
        tile.gold_amount = gold_amount
        tile.gold_mine = gold_mine

        self.gold_mines.append(gold_mine)

        # 注册到金矿管理器
        if hasattr(self, 'optimized_mining_system') and self.optimized_mining_system:
            self.optimized_mining_system.gold_mine_manager.register_gold_mine_object(
                x, y, gold_mine)
            game_logger.info(f"✅ 金矿对象已注册到管理器: 位置=({x}, {y})")
        else:
            game_logger.warning(f"⚠️ 无法注册金矿对象: optimized_mining_system 不可用")

        game_logger.info(f"⛏️ 添加金矿: 位置({x}, {y}), 储量({gold_amount})")
        return gold_mine

    def add_rock_tile(self, x: int, y: int) -> bool:
        """
        在地图上添加岩石瓦片

        Args:
            x: 瓦片X坐标
            y: 瓦片Y坐标

        Returns:
            bool: 是否成功添加
        """
        if not (0 <= x < self.map_width and 0 <= y < self.map_height):
            game_logger.info(f"❌ 岩石位置超出地图范围: ({x}, {y})")
            return False

        # 更新地图瓦片
        tile = self.game_map[y][x]
        tile.tile_type = TileType.ROCK

        game_logger.info(f"🪨 添加岩石瓦片: 位置({x}, {y})")
        return True

    def add_wall_tile(self, x: int, y: int) -> bool:
        """
        在地图上添加墙壁瓦片（使用ROCK类型）

        Args:
            x: 瓦片X坐标
            y: 瓦片Y坐标

        Returns:
            bool: 是否成功添加
        """
        if not (0 <= x < self.map_width and 0 <= y < self.map_height):
            game_logger.info(f"❌ 墙壁位置超出地图范围: ({x}, {y})")
            return False

        # 更新地图瓦片（使用ROCK类型作为墙壁）
        tile = self.game_map[y][x]
        tile.tile_type = TileType.ROCK

        game_logger.info(f"🧱 添加墙壁瓦片: 位置({x}, {y})")
        return True

    def generate_random_map(self, gold_mine_count: int = 10, rock_count: int = 20, wall_count: int = 15) -> List[List[Tile]]:
        """
        生成随机地图

        Args:
            gold_mine_count: 金矿数量
            rock_count: 岩石数量
            wall_count: 墙壁数量

        Returns:
            List[List[Tile]]: 随机生成的地图
        """
        # 重置地图为空白
        self.game_map = self.generate_blank_map()

        # 添加随机金矿
        for _ in range(gold_mine_count):
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            gold_amount = random.randint(50, 200)
            self.add_gold_mine(x, y, gold_amount)

        # 添加随机岩石
        for _ in range(rock_count):
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            # 确保不是金矿位置
            if self.game_map[y][x].tile_type == TileType.GROUND:
                self.add_rock_tile(x, y)

        # 添加随机墙壁
        for _ in range(wall_count):
            x = random.randint(0, self.map_width - 1)
            y = random.randint(0, self.map_height - 1)
            # 确保不是金矿或岩石位置
            if self.game_map[y][x].tile_type == TileType.GROUND:
                self.add_wall_tile(x, y)

        game_logger.info(
            f"🎲 生成随机地图: {gold_mine_count}个金矿, {rock_count}个岩石, {wall_count}个墙壁")
        return self.game_map

    def clear_map(self):
        """清空地图，重置为空白地面"""
        self.game_map = self.generate_blank_map()
        self.gold_mines.clear()
        game_logger.info("🧹 清空地图")

    # ==================== 建筑管理 ====================

    def create_dungeon_heart(self, x: int, y: int, gold: int = 500, completed: bool = True) -> DungeonHeart:
        """创建地牢之心（主基地）"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.DUNGEON_HEART]

        # 地牢之心是免费建筑，不需要检查资源
        # gold 参数只是设置初始存储的金币数量

        dungeon_heart = DungeonHeart(x, y, BuildingType.DUNGEON_HEART, config)
        dungeon_heart.stored_gold = gold  # 使用 stored_gold 而不是 gold

        if completed:
            dungeon_heart.status = BuildingStatus.COMPLETED
            dungeon_heart.is_active = True
        else:
            dungeon_heart.status = BuildingStatus.UNDER_CONSTRUCTION
            dungeon_heart.is_active = False

        self.building_manager.buildings.append(dungeon_heart)
        self.dungeon_heart = dungeon_heart

        # 设置主基地位置（用于工程师寻找）
        self.dungeon_heart_pos = (x, y)

        # 注册地牢之心到ResourceManager
        if self.resource_manager:
            self.resource_manager.register_dungeon_heart(dungeon_heart)
            game_logger.info(f"🏰 地牢之心已注册到资源管理器")

        game_logger.info(
            f"🏰 创建地牢之心: 位置({x}, {y}), 金币({dungeon_heart.stored_gold}), 魔力({dungeon_heart.stored_mana}), 状态({'已完成' if completed else '建造中'})")
        return dungeon_heart

    def create_arrow_tower(self, x: int, y: int, ammunition: int = 60, completed: bool = True) -> ArrowTower:
        """创建箭塔"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.ARROW_TOWER]

        arrow_tower = ArrowTower(x, y, BuildingType.ARROW_TOWER, config)

        # 设置弹药量
        arrow_tower.current_ammunition = ammunition

        # 设置状态
        if completed:
            arrow_tower.status = BuildingStatus.COMPLETED
            arrow_tower.is_active = True
        else:
            arrow_tower.status = BuildingStatus.UNDER_CONSTRUCTION
            arrow_tower.is_active = False

        self.building_manager.buildings.append(arrow_tower)

        game_logger.info(
            f"🏹 创建箭塔: 位置({x}, {y}), 弹药({arrow_tower.current_ammunition}/{arrow_tower.max_ammunition}), 状态({'已完成' if completed else '建造中'})")
        return arrow_tower

    def create_arcane_tower(self, x: int, y: int, completed: bool = True):
        """创建奥术塔"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.ARCANE_TOWER]

        arcane_tower = ArcaneTower(x, y, BuildingType.ARCANE_TOWER, config)

        # 设置游戏实例引用（用于资源管理器访问）
        arcane_tower.game_instance = self

        # 设置状态
        if completed:
            arcane_tower.status = BuildingStatus.COMPLETED
            arcane_tower.is_active = True
        else:
            arcane_tower.status = BuildingStatus.UNDER_CONSTRUCTION
            arcane_tower.is_active = False

        self.building_manager.buildings.append(arcane_tower)

        game_logger.info(
            f"🔮 创建奥术塔: 位置({x}, {y}), 状态({'已完成' if completed else '建造中'})")
        return arcane_tower

    def create_treasury(self, x: int, y: int, stored_gold: int = 0, completed: bool = True) -> Treasury:
        """创建金库"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.TREASURY]

        treasury = Treasury(x, y, BuildingType.TREASURY, config)
        treasury.stored_gold = stored_gold

        if completed:
            treasury.status = BuildingStatus.COMPLETED
            treasury.is_active = True
        else:
            treasury.status = BuildingStatus.UNDER_CONSTRUCTION
            treasury.is_active = False

        self.building_manager.buildings.append(treasury)
        self.treasury = treasury

        # 注册金库到ResourceManager
        if self.resource_manager and completed:
            self.resource_manager.register_treasury(treasury)
            game_logger.info(f"💰 金库已注册到资源管理器")

        game_logger.info(
            f"💰 创建金库: 位置({x}, {y}), 存储金币({stored_gold}), 状态({'已完成' if completed else '建造中'})")
        return treasury

    def create_magic_altar(self, x: int, y: int, stored_gold: int = 0, stored_mana: int = 0, completed: bool = True) -> Building:
        """
        创建魔法祭坛建筑

        Args:
            x: 瓦片X坐标
            y: 瓦片Y坐标
            stored_gold: 存储的金币数量
            stored_mana: 存储的魔力数量
            completed: 是否已完成建造

        Returns:
            MagicAltar: 魔法祭坛建筑对象
        """
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.MAGIC_ALTAR]
        building = MagicAltar(x, y, BuildingType.MAGIC_ALTAR, config)

        if completed:
            building.status = BuildingStatus.COMPLETED
            building.is_active = True
            building.construction_progress = 1.0
        else:
            building.status = BuildingStatus.UNDER_CONSTRUCTION
            building.is_active = False
            building.construction_progress = 0.0

        # 设置存储资源
        if stored_gold > 0:
            building.temp_gold = min(
                stored_gold, building.max_temp_gold)
        if stored_mana > 0:
            building.stored_mana = min(
                stored_mana, building.mana_storage_capacity)

        # 添加到建筑管理器
        self.building_manager.buildings.append(building)

        # 注册魔法祭坛到ResourceManager
        if self.resource_manager and completed:
            self.resource_manager.register_magic_altar(building)
            game_logger.info(f"🔮 魔法祭坛已注册到资源管理器")

        game_logger.info(
            f"🔮 创建魔法祭坛: 位置({x}, {y}), 魔力({building.stored_mana}/{building.mana_storage_capacity}), 状态({'已完成' if completed else '建造中'})")
        return building

    def create_training_room(self, x: int, y: int, completed: bool = True) -> Building:
        """创建训练室"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.TRAINING_ROOM]

        training_room = Building(x, y, BuildingType.TRAINING_ROOM, config)

        if completed:
            training_room.status = BuildingStatus.COMPLETED
            training_room.is_active = True
        else:
            training_room.status = BuildingStatus.UNDER_CONSTRUCTION
            training_room.is_active = False

        self.building_manager.buildings.append(training_room)

        game_logger.info(
            f"🏋️ 创建训练室: 位置({x}, {y}), 状态({'已完成' if completed else '建造中'})")
        return training_room

    def create_library(self, x: int, y: int, completed: bool = True) -> Building:
        """创建图书馆"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.LIBRARY]

        library = Building(x, y, BuildingType.LIBRARY, config)

        if completed:
            library.status = BuildingStatus.COMPLETED
            library.is_active = True
        else:
            library.status = BuildingStatus.UNDER_CONSTRUCTION
            library.is_active = False

        self.building_manager.buildings.append(library)

        game_logger.info(
            f"📚 创建图书馆: 位置({x}, {y}), 状态({'已完成' if completed else '建造中'})")
        return library

    def create_prison(self, x: int, y: int, completed: bool = True) -> Building:
        """创建监狱"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.PRISON]

        prison = Building(x, y, BuildingType.PRISON, config)

        if completed:
            prison.status = BuildingStatus.COMPLETED
            prison.is_active = True
        else:
            prison.status = BuildingStatus.UNDER_CONSTRUCTION
            prison.is_active = False

        self.building_manager.buildings.append(prison)

        game_logger.info(
            f"🔒 创建监狱: 位置({x}, {y}), 状态({'已完成' if completed else '建造中'})")
        return prison

    def create_defense_fortification(self, x: int, y: int, completed: bool = True) -> Building:
        """创建防御工事"""
        # 直接引用真实游戏的建筑配置
        config = BuildingRegistry.BUILDING_CONFIGS[BuildingType.DEFENSE_FORTIFICATION]

        fortification = Building(
            x, y, BuildingType.DEFENSE_FORTIFICATION, config)

        if completed:
            fortification.status = BuildingStatus.COMPLETED
            fortification.is_active = True
        else:
            fortification.status = BuildingStatus.UNDER_CONSTRUCTION
            fortification.is_active = False

        self.building_manager.buildings.append(fortification)

        game_logger.info(
            f"🛡️ 创建防御工事: 位置({x}, {y}), 状态({'已完成' if completed else '建造中'})")
        return fortification

    def create_building(self, x: int, y: int, building_type: BuildingType, completed: bool = True, **kwargs) -> Building:
        """
        通用建筑创建方法 - 支持所有建筑类型

        Args:
            x: 瓦片X坐标
            y: 瓦片Y坐标
            building_type: 建筑类型
            completed: 是否已完成建造
            **kwargs: 建筑特定参数

        Returns:
            Building: 创建的建筑对象
        """
        # 使用BuildingRegistry创建正确的建筑子类
        config = BuildingRegistry.get_config(building_type)

        if not config:
            game_logger.info(f"❌ 未找到建筑配置: {building_type}")
            return None

        # 只有在建筑完成时才消耗资源（规划阶段不消耗资源）
        if completed and (config.cost_gold > 0 or config.cost_crystal > 0):
            # 检查金币是否足够
            if config.cost_gold > 0:
                gold_info = self.resource_manager.get_total_gold()
                if gold_info.available < config.cost_gold:
                    game_logger.info(
                        f"❌ 金币不足，无法创建 {config.name}（需要 {config.cost_gold} 金币，可用 {gold_info.available}）")
                    return None

            # 检查魔力是否足够
            if config.cost_crystal > 0:
                mana_info = self.resource_manager.get_total_mana()
                if mana_info.available < config.cost_crystal:
                    game_logger.info(
                        f"❌ 魔力不足，无法创建 {config.name}（需要 {config.cost_crystal} 魔力，可用 {mana_info.available}）")
                    return None

            # 消耗资源
            if config.cost_gold > 0:
                # 传递优先级源列表而不是单个对象
                priority_sources = [
                    BuildingType.DUNGEON_HEART.value] if self.dungeon_heart else []
                gold_result = self.resource_manager.consume_gold(
                    config.cost_gold, priority_sources)
                if not gold_result['success']:
                    game_logger.info(f"❌ 金币消耗失败，无法创建 {config.name}")
                    return None

            if config.cost_crystal > 0:
                # 传递优先级源列表而不是单个对象
                priority_sources = [
                    BuildingType.DUNGEON_HEART.value] if self.dungeon_heart else []
                mana_result = self.resource_manager.consume_mana(
                    config.cost_crystal, priority_sources)
                if not mana_result['success']:
                    game_logger.info(f"❌ 魔力消耗失败，无法创建 {config.name}")
                    return None

        # 使用BuildingRegistry创建正确的建筑子类
        building = BuildingRegistry.create_building(building_type, x, y)
        if not building:
            game_logger.info(f"❌ 建筑创建失败: {building_type}")
            return None

        # 设置游戏实例引用（用于资源管理器访问）
        building.game_instance = self

        # 应用建筑特定参数
        self._apply_building_specific_params(building, building_type, **kwargs)

        # 设置状态
        if completed:
            building.status = BuildingStatus.COMPLETED
            building.is_active = True
            building.construction_progress = 1.0
        else:
            building.status = BuildingStatus.UNDER_CONSTRUCTION
            building.is_active = False
            building.construction_progress = 0.0

        # 添加到建筑列表
        self.building_manager.buildings.append(building)

        # 注册到资源管理器（如果适用）
        self._register_building_to_resource_manager(
            building, building_type, completed)

        game_logger.info(
            f"🏗️ 创建{building.name}: 位置({x}, {y}), 状态({'已完成' if completed else '建造中'})")
        return building

    def _apply_building_specific_params(self, building, building_type: BuildingType, **kwargs):
        """应用建筑特定参数"""
        # 地牢之心参数
        if building_type == BuildingType.DUNGEON_HEART:
            if 'stored_gold' in kwargs:
                building.stored_gold = kwargs['stored_gold']
            if 'stored_mana' in kwargs:
                building.stored_mana = kwargs['stored_mana']
            # 设置主基地位置引用
            self.dungeon_heart = building
            self.dungeon_heart_pos = (building.tile_x, building.tile_y)

        # 箭塔参数
        elif building_type == BuildingType.ARROW_TOWER:
            if 'ammunition' in kwargs:
                building.current_ammunition = min(
                    kwargs['ammunition'], building.max_ammunition)

        # 金库参数
        elif building_type == BuildingType.TREASURY:
            if 'stored_gold' in kwargs:
                building.stored_gold = kwargs['stored_gold']
            self.treasury = building

        # 魔法祭坛参数
        elif building_type == BuildingType.MAGIC_ALTAR:
            if 'stored_gold' in kwargs:
                building.temp_gold = min(
                    kwargs['stored_gold'], building.max_temp_gold)
            if 'stored_mana' in kwargs:
                building.stored_mana = min(
                    kwargs['stored_mana'], building.mana_storage_capacity)

        # 训练室参数
        elif building_type == BuildingType.TRAINING_ROOM:
            if 'training_queue' in kwargs:
                building.training_queue = kwargs['training_queue']

        # 图书馆参数
        elif building_type == BuildingType.LIBRARY:
            if 'research_queue' in kwargs:
                building.research_queue = kwargs['research_queue']

        # 监狱参数
        elif building_type == BuildingType.PRISON:
            if 'prisoner_capacity' in kwargs:
                building.prisoner_capacity = kwargs['prisoner_capacity']

        # 防御工事参数
        elif building_type == BuildingType.DEFENSE_FORTIFICATION:
            if 'defense_bonus' in kwargs:
                building.defense_bonus = kwargs['defense_bonus']

        # 兽人巢穴参数
        elif building_type == BuildingType.ORC_LAIR:
            if 'stored_gold' in kwargs:
                building.temp_gold = min(
                    kwargs['stored_gold'], building.max_temp_gold)

        # 恶魔巢穴参数
        elif building_type == BuildingType.DEMON_LAIR:
            if 'stored_gold' in kwargs:
                building.temp_gold = min(
                    kwargs['stored_gold'], building.max_temp_gold)

    def _register_building_to_resource_manager(self, building, building_type: BuildingType, completed: bool):
        """将建筑注册到资源管理器"""
        if not self.resource_manager or not completed:
            return

        if building_type == BuildingType.DUNGEON_HEART:
            self.resource_manager.register_dungeon_heart(building)
            game_logger.info(f"🏰 地牢之心已注册到资源管理器")
        elif building_type == BuildingType.TREASURY:
            self.resource_manager.register_treasury(building)
            game_logger.info(f"💰 金库已注册到资源管理器")
        elif building_type == BuildingType.MAGIC_ALTAR:
            self.resource_manager.register_magic_altar(building)
            game_logger.info(f"🔮 魔法祭坛已注册到资源管理器")

    # ==================== 便捷建筑创建方法 ====================

    def create_orc_lair(self, x: int, y: int, stored_gold: int = 0, completed: bool = True) -> Building:
        """创建兽人巢穴"""
        return self.create_building(x, y, BuildingType.ORC_LAIR, completed, stored_gold=stored_gold)

    def create_demon_lair(self, x: int, y: int, stored_gold: int = 0, completed: bool = True) -> Building:
        """创建恶魔巢穴"""
        return self.create_building(x, y, BuildingType.DEMON_LAIR, completed, stored_gold=stored_gold)

    def create_workshop(self, x: int, y: int, completed: bool = True) -> Building:
        """创建工坊"""
        return self.create_building(x, y, BuildingType.WORKSHOP, completed)

    def create_barracks(self, x: int, y: int, completed: bool = True) -> Building:
        """创建兵营"""
        return self.create_building(x, y, BuildingType.BARRACKS, completed)

    def create_temple(self, x: int, y: int, completed: bool = True) -> Building:
        """创建神庙"""
        return self.create_building(x, y, BuildingType.TEMPLE, completed)

    def create_guard_room(self, x: int, y: int, completed: bool = True) -> Building:
        """创建警卫室"""
        return self.create_building(x, y, BuildingType.GUARD_ROOM, completed)

    def create_torture_chamber(self, x: int, y: int, completed: bool = True) -> Building:
        """创建刑讯室"""
        return self.create_building(x, y, BuildingType.TORTURE_CHAMBER, completed)

    def create_graveyard(self, x: int, y: int, completed: bool = True) -> Building:
        """创建墓地"""
        return self.create_building(x, y, BuildingType.GRAVEYARD, completed)

    def create_scavenger_room(self, x: int, y: int, completed: bool = True) -> Building:
        """创建清道夫室"""
        return self.create_building(x, y, BuildingType.SCAVENGER_ROOM, completed)

    def create_hatchery(self, x: int, y: int, completed: bool = True) -> Building:
        """创建孵化室"""
        return self.create_building(x, y, BuildingType.HATCHERY, completed)

    def create_lair(self, x: int, y: int, completed: bool = True) -> Building:
        """创建巢穴"""
        return self.create_building(x, y, BuildingType.LAIR, completed)

    def create_bridge(self, x: int, y: int, completed: bool = True) -> Building:
        """创建桥梁"""
        return self.create_building(x, y, BuildingType.BRIDGE, completed)

    def create_doors(self, x: int, y: int, completed: bool = True) -> Building:
        """创建门"""
        return self.create_building(x, y, BuildingType.DOORS, completed)

    def create_guard_post(self, x: int, y: int, completed: bool = True) -> Building:
        """创建岗哨"""
        return self.create_building(x, y, BuildingType.GUARD_POST, completed)

    def create_arcane_tower(self, x: int, y: int, completed: bool = True) -> Building:
        """创建奥术塔"""
        return self.create_building(x, y, BuildingType.ARCANE_TOWER, completed)

    def create_lightning_tower(self, x: int, y: int, completed: bool = True) -> Building:
        """创建闪电塔"""
        return self.create_building(x, y, BuildingType.LIGHTNING_TOWER, completed)

    def create_teleport(self, x: int, y: int, completed: bool = True) -> Building:
        """创建传送门"""
        return self.create_building(x, y, BuildingType.TELEPORT, completed)

    def create_hero_gate(self, x: int, y: int, completed: bool = True) -> Building:
        """创建英雄门"""
        return self.create_building(x, y, BuildingType.HERO_GATE, completed)

    def create_heart_of_darkness(self, x: int, y: int, completed: bool = True) -> Building:
        """创建黑暗之心"""
        return self.create_building(x, y, BuildingType.HEART_OF_DARKNESS, completed)

    def create_imp_stone(self, x: int, y: int, completed: bool = True) -> Building:
        """创建小鬼石"""
        return self.create_building(x, y, BuildingType.IMP_STONE, completed)

    def create_claim_ground(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领地面"""
        return self.create_building(x, y, BuildingType.CLAIM_GROUND, completed)

    def create_claim_wall(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领墙壁"""
        return self.create_building(x, y, BuildingType.CLAIM_WALL, completed)

    def create_claim_floor(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领地板"""
        return self.create_building(x, y, BuildingType.CLAIM_FLOOR, completed)

    def create_claim_gold(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领金矿"""
        return self.create_building(x, y, BuildingType.CLAIM_GOLD, completed)

    def create_claim_rock(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领岩石"""
        return self.create_building(x, y, BuildingType.CLAIM_ROCK, completed)

    def create_claim_water(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领水域"""
        return self.create_building(x, y, BuildingType.CLAIM_WATER, completed)

    def create_claim_lava(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领熔岩"""
        return self.create_building(x, y, BuildingType.CLAIM_LAVA, completed)

    def create_claim_hero_gate(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领英雄门"""
        return self.create_building(x, y, BuildingType.CLAIM_HERO_GATE, completed)

    def create_claim_portal(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领传送门"""
        return self.create_building(x, y, BuildingType.CLAIM_PORTAL, completed)

    def create_claim_heart(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领心脏"""
        return self.create_building(x, y, BuildingType.CLAIM_HEART, completed)

    def create_claim_imp_stone(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领小鬼石"""
        return self.create_building(x, y, BuildingType.CLAIM_IMP_STONE, completed)

    def create_claim_lightning_tower(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领闪电塔"""
        return self.create_building(x, y, BuildingType.CLAIM_LIGHTNING_TOWER, completed)

    def create_claim_arcane_tower(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领奥术塔"""
        return self.create_building(x, y, BuildingType.CLAIM_ARCANE_TOWER, completed)

    def create_claim_arrow_tower(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领箭塔"""
        return self.create_building(x, y, BuildingType.CLAIM_ARROW_TOWER, completed)

    def create_claim_teleport(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领传送门"""
        return self.create_building(x, y, BuildingType.CLAIM_TELEPORT, completed)

    def create_claim_guard_post(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领岗哨"""
        return self.create_building(x, y, BuildingType.CLAIM_GUARD_POST, completed)

    def create_claim_doors(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领门"""
        return self.create_building(x, y, BuildingType.CLAIM_DOORS, completed)

    def create_claim_bridge(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领桥梁"""
        return self.create_building(x, y, BuildingType.CLAIM_BRIDGE, completed)

    def create_claim_lair(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领巢穴"""
        return self.create_building(x, y, BuildingType.CLAIM_LAIR, completed)

    def create_claim_hatchery(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领孵化室"""
        return self.create_building(x, y, BuildingType.CLAIM_HATCHERY, completed)

    def create_claim_scavenger_room(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领清道夫室"""
        return self.create_building(x, y, BuildingType.CLAIM_SCAVENGER_ROOM, completed)

    def create_claim_graveyard(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领墓地"""
        return self.create_building(x, y, BuildingType.CLAIM_GRAVEYARD, completed)

    def create_claim_torture_chamber(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领刑讯室"""
        return self.create_building(x, y, BuildingType.CLAIM_TORTURE_CHAMBER, completed)

    def create_claim_guard_room(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领警卫室"""
        return self.create_building(x, y, BuildingType.CLAIM_GUARD_ROOM, completed)

    def create_claim_temple(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领神庙"""
        return self.create_building(x, y, BuildingType.CLAIM_TEMPLE, completed)

    def create_claim_barracks(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领兵营"""
        return self.create_building(x, y, BuildingType.CLAIM_BARRACKS, completed)

    def create_claim_workshop(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领工坊"""
        return self.create_building(x, y, BuildingType.CLAIM_WORKSHOP, completed)

    def create_claim_prison(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领监狱"""
        return self.create_building(x, y, BuildingType.CLAIM_PRISON, completed)

    def create_claim_library(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领图书馆"""
        return self.create_building(x, y, BuildingType.CLAIM_LIBRARY, completed)

    def create_claim_training_room(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领训练室"""
        return self.create_building(x, y, BuildingType.CLAIM_TRAINING_ROOM, completed)

    def create_claim_defense_fortification(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领防御工事"""
        return self.create_building(x, y, BuildingType.CLAIM_DEFENSE_FORTIFICATION, completed)

    def create_claim_treasury(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领金库"""
        return self.create_building(x, y, BuildingType.CLAIM_TREASURY, completed)

    def create_claim_magic_altar(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领魔法祭坛"""
        return self.create_building(x, y, BuildingType.CLAIM_MAGIC_ALTAR, completed)

    def create_claim_demon_lair(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领恶魔巢穴"""
        return self.create_building(x, y, BuildingType.CLAIM_DEMON_LAIR, completed)

    def create_claim_orc_lair(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领兽人巢穴"""
        return self.create_building(x, y, BuildingType.CLAIM_ORC_LAIR, completed)

    def create_claim_dungeon_heart(self, x: int, y: int, completed: bool = True) -> Building:
        """创建占领地牢之心"""

        return self.create_building(x, y, BuildingType.CLAIM_DUNGEON_HEART, completed)

    # ==================== 物理系统集成 ====================

    def apply_knockback(self, attacker, target, attack_damage: float, attack_type: str = "normal") -> bool:
        """
        应用击退效果

        Args:
            attacker: 攻击者
            target: 目标
            attack_damage: 攻击伤害
            attack_type: 攻击类型

        Returns:
            bool: 是否成功应用击退
        """
        # 计算击退效果
        knockback_result = self.physics_system.calculate_knockback(
            attacker, target, attack_damage, attack_type
        )

        # 应用击退
        success = self.physics_system.apply_knockback(target, knockback_result)

        if success and target.knockback_state:
            # 创建击退视觉效果 - 与真实游戏保持一致
            # 计算击退方向向量
            dx = target.knockback_state.target_x - target.knockback_state.start_x
            dy = target.knockback_state.target_y - target.knockback_state.start_y
            distance = (dx**2 + dy**2)**0.5
            if distance > 0:
                normalized_direction = (dx/distance, dy/distance)
            self.knockback_animation.create_knockback_effect(
                target, normalized_direction, distance
            )

        return success

    def handle_unit_attacked_response(self, attacker, target, damage: float):
        """
        处理单位被攻击时的响应逻辑

        Args:
            attacker: 攻击者
            target: 被攻击的目标
            damage: 受到的伤害
        """
        if not target or target.health <= 0:
            return

        # 委托给战斗系统处理
        self.combat_system.handle_unit_attacked_response(
            attacker, target, damage)

    def check_collision(self, unit1, unit2) -> bool:
        """检查两个单位是否发生碰撞"""
        return self.physics_system.check_collision(unit1, unit2)

    def resolve_collision(self, unit1, unit2):
        """解决碰撞，将单位推开"""
        self.physics_system.resolve_collision(unit1, unit2)

    def detect_all_collisions(self) -> List[Tuple[Any, Any]]:
        """检测所有单位间的碰撞"""
        all_units = self.monsters + self.heroes + self.building_manager.engineers
        return self.physics_system.detect_collisions(all_units)

    # ==================== 特效系统集成 ====================
    # 注意：特效创建现在统一由combat_system处理，这里只保留必要的接口

    def create_particle_effect(self, x: float, y: float, particle_count: int = 10,
                               color: Tuple[int, int, int] = (255, 255, 255)) -> None:
        """
        创建粒子特效 - 使用击退动画系统

        Args:
            x, y: 粒子位置
            particle_count: 粒子数量
            color: 粒子颜色
        """
        # 使用击退动画系统创建粒子效果
        for _ in range(particle_count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 60)
            life_time = random.uniform(0.5, 1.5)

            # 创建粒子对象
            particle = Particle(
                x=x + random.uniform(-5, 5),
                y=y + random.uniform(-5, 5),
                velocity_x=math.cos(angle) * speed,
                velocity_y=math.sin(angle) * speed,
                color=color,
                life_time=life_time,
                max_life_time=life_time,
                size=random.uniform(1.0, 3.0)
            )

            # 添加到击退动画系统
            self.knockback_animation.particle_effects.append(particle)

    # ==================== 状态指示器集成 ====================

    def render_status_indicator(self, unit, screen_x: float, screen_y: float) -> None:
        """
        渲染单位状态指示器

        Args:
            unit: 单位对象
            screen_x, screen_y: 屏幕坐标
        """
        # 注意：status_indicator 在模拟器中未配置，跳过状态渲染
        if hasattr(unit, 'get_status_for_indicator'):
            status = unit.get_status_for_indicator()
            # self.status_indicator.render(
            #     self.screen, screen_x, screen_y, unit.size, status
            # )

    def get_status_description(self, status: str) -> str:
        """获取状态描述"""
        # 注意：status_indicator 在模拟器中未配置，返回默认描述
        return f"状态: {status}"

    # ==================== 角色管理 ====================

    def create_engineer(self, x: float, y: float, engineer_type: EngineerType = EngineerType.BASIC) -> Engineer:
        """创建工程师"""
        config = EngineerConfig(
            name="工程师",
            engineer_type=engineer_type,
            cost=50,
            health=100,
            speed=30,
            build_efficiency=1.0,
            color=(100, 100, 255),
            size=15,
            level=1,
            max_concurrent_projects=1,
            repair_efficiency=1.0,
            upgrade_capability=False,
            special_abilities=[],
            description="基础工程师"
        )

        engineer = Engineer(x, y, engineer_type, config)
        engineer.carried_gold = 0

        # 设置游戏实例引用，让工程师能找到主基地和触发攻击响应
        engineer.game_instance = self

        # 工程师只由 building_manager 管理，不添加到 monsters 列表
        # 这样工程师的更新完全由 building_manager 的工程师分配器控制
        self.building_manager.engineers.append(engineer)

        game_logger.info(f"🔧 创建工程师: 位置({x}, {y}), 类型({engineer_type.value})")
        return engineer

    def create_worker(self, x: float, y: float) -> GoblinWorker:
        """创建工人"""
        worker = GoblinWorker(x, y)

        # 设置游戏实例引用，用于触发攻击响应
        worker.game_instance = self

        # 将苦工添加到monsters列表中，这样它会被正常更新
        self.monsters.append(worker)
        # 通过 building_manager 管理工人
        self.building_manager.workers.append(worker)

        game_logger.info(f"⛏️ 创建工人: 位置({x}, {y})")
        return worker

    def create_hero(self, x: float, y: float, hero_type: str = 'knight') -> Hero:
        """创建英雄"""

        # 使用最新的角色配置系统
        character_db = CharacterDatabase()
        character_data = character_db.get_character(hero_type)
        if not character_data:
            game_logger.info(f"❌ 未知英雄类型: {hero_type}")
            return None

        hero = Hero(x, y, hero_type)

        # 应用最新的配置
        hero.name = character_data.name
        hero.health = character_data.hp
        hero.max_health = character_data.hp
        hero.attack = character_data.attack
        hero.speed = character_data.speed
        hero.color = character_data.color
        hero.size = character_data.size
        hero.armor = character_data.armor
        hero.attack_range = character_data.attack_range
        hero.attack_cooldown = character_data.attack_cooldown

        # 设置游戏实例引用，用于触发攻击响应
        hero.game_instance = self

        self.heroes.append(hero)

        game_logger.info(
            f"🛡️ 创建英雄: 位置({x}, {y}), 类型({hero_type}), 名称({hero.name})")
        return hero

    def create_creature(self, x: float, y: float, creature_type: str = 'imp') -> Creature:
        """创建怪物"""
        # 检查怪物数量限制
        if not self.can_create_monster():
            capacity_info = self.get_monster_capacity_info()
            game_logger.info(
                f"❌ 无法创建怪物，已达到数量上限: {capacity_info['current']}/{capacity_info['max']}")
            return None

        # 使用最新的角色配置系统
        character_db = CharacterDatabase()
        character_data = character_db.get_character(creature_type)
        if not character_data:
            game_logger.info(f"❌ 未知角色类型: {creature_type}")
            return None

        creature = Creature(x, y, creature_type)

        # 应用最新的配置
        creature.name = character_data.name
        creature.health = character_data.hp
        creature.max_health = character_data.hp
        creature.attack = character_data.attack
        creature.speed = character_data.speed
        creature.color = character_data.color
        creature.size = character_data.size
        creature.armor = character_data.armor
        creature.attack_range = character_data.attack_range
        creature.attack_cooldown = character_data.attack_cooldown

        # 设置游戏实例引用，用于触发攻击响应
        creature.game_instance = self

        self.monsters.append(creature)

        # 更新怪物数量限制
        self.calculate_max_monsters()

        game_logger.info(
            f"👹 创建怪物: 位置({x}, {y}), 类型({creature_type}), 名称({creature.name})")
        return creature

    # ==================== 游戏逻辑更新 ====================

    def _spawn_hero(self):
        """生成英雄 - 在英雄基地附近刷新"""
        if random.random() < GameBalance.hero_spawn_rate:
            if not hasattr(self, 'hero_bases') or not self.hero_bases:
                # 模拟器模式下不生成英雄，避免干扰测试
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
                hero_type = 'knight'
                hero_name = '骑士'

                hero = Hero(spawn_x * self.tile_size + self.tile_size // 2,
                            spawn_y * self.tile_size + self.tile_size // 2, hero_type)
                # 设置游戏实例引用，用于触发攻击响应
                hero.game_instance = self
                self.heroes.append(hero)
                game_logger.info(
                    f"👹 {hero_name}从基地 ({base_x}, {base_y}) 入侵！")
            else:
                game_logger.info("❌ 英雄基地附近没有可用的生成位置")

    def update(self, delta_time: float):
        """
        更新游戏逻辑

        Args:
            delta_time: 时间增量（毫秒）- 与pygame.clock.tick()一致
        """
        # 将毫秒转换为秒，供需要秒为单位的子系统使用
        delta_seconds = delta_time / 1000.0

        # 更新怪物（期望秒）- 排除工程师，工程师由building_manager管理
        for creature in self.monsters[:]:
            creature.update(delta_seconds, self.game_map,
                            self.monsters, self.heroes, self.effect_manager, self.building_manager, self)

        # 更新英雄（期望秒）
        for hero in self.heroes[:]:
            hero.update(delta_seconds, self.monsters,
                        self.game_map, self.effect_manager)

        # 更新特效系统（期望毫秒）
        if self.effect_manager:
            all_targets = self.monsters + self.heroes
            self.effect_manager.update(delta_time, all_targets)

        # 更新物理系统
        if self.physics_system:
            # 将毫秒转换为秒
            delta_seconds = delta_time / 1000.0
            all_units = self.monsters + self.heroes

            # 只更新击退效果，不处理单位间碰撞（避免召唤时的弹开效果）
            self.physics_system.update_knockbacks(delta_seconds, self.game_map)

        # 更新击退动画
        if self.knockback_animation:
            delta_seconds = delta_time / 1000.0
            self.knockback_animation.update(delta_seconds)

        # 更新全局空闲状态管理器
        if self.idle_state_manager:
            self.idle_state_manager.update_idle_units(delta_seconds)

        # 更新建筑系统 - 与真实游戏保持一致
        if self.building_manager:
            # 获取所有活着的苦工作为workers参数
            living_workers = [creature for creature in self.monsters
                              if hasattr(creature, 'type') and creature.type == 'goblin_worker'
                              and creature.health > 0]

            # 建筑管理器期望秒，需要转换时间单位
            building_result = self.building_manager.update(
                delta_seconds, self.game_state, self.game_map, living_workers)

            # 处理建筑系统事件
            for event in building_result.get('events', []):
                game_logger.info(f"🏗️ {event}")

            # 检查是否有建筑完成，需要立即重新渲染
            if building_result.get('needs_rerender'):
                self._pending_rerender = True

        # 更新战斗系统
        if self.combat_system:
            delta_seconds = delta_time / 1000.0

            # 处理战斗逻辑
            self.combat_system.handle_combat(
                delta_seconds, self.monsters, self.heroes, self.building_manager)

            # 处理防御塔攻击
            self.combat_system.handle_defense_tower_attacks(
                delta_time, self.building_manager, self.heroes)

        # 清理死亡的单位
        self._cleanup_dead_units()

    # ==================== 测试场景预设 ====================

    def setup_repair_test_scenario(self):
        """设置建筑修复测试场景"""
        # 创建主基地
        self.create_dungeon_heart(10, 10, 500)

        # 创建半血箭塔
        damaged_tower = self.create_arrow_tower(25, 15, 30)  # 30弹药
        self.building_manager.repair_queue.append(damaged_tower)

        # 创建工程师
        self.create_engineer(12, 12)

        game_logger.info("🔧 建筑修复测试场景设置完成")

    def setup_combat_test_scenario(self):
        """设置战斗测试场景"""
        # 创建箭塔
        self.create_arrow_tower(15, 10)

        # 创建英雄骑士
        knight = self.create_hero(200, 200, 'knight')
        knight.health = 120
        knight.max_health = 120
        knight.attack = 22
        knight.speed = 25

        game_logger.info("⚔️ 战斗测试场景设置完成")

    def setup_economy_test_scenario(self):
        """设置经济测试场景"""
        # 创建主基地
        self.create_dungeon_heart(10, 10, 1000)

        # 创建金库
        self.create_treasury(15, 10, 0)

        # 创建工人
        self.create_worker(12, 12)

        game_logger.info("💰 经济测试场景设置完成")

    # ==================== 渲染系统 ====================

    def render(self):
        """渲染游戏画面"""
        if not self.screen:
            return

        self.screen.fill((50, 50, 50))  # 深灰色背景

        # 绘制地图
        self._render_map()

        # 绘制建筑
        self._render_buildings()

        # 绘制角色
        self._render_characters()

        # 绘制特效
        self._render_effects()

        # 绘制UI
        self._render_ui()

        # 绘制游戏UI（资源面板等）
        # 注意：game_ui 在模拟器中未配置，跳过UI渲染
        # if self.game_ui:
        #     # 渲染资源面板
        #     self.game_ui.render_resource_panel(
        #         self.game_state,
        #         len(self.monsters),
        #         100,  # max_monsters
        #         self.building_manager,
        #         self.ui_scale
        #     )

        pygame.display.flip()

    def _render_map(self):
        """渲染地图瓦片"""
        for y in range(self.map_height):
            for x in range(self.map_width):
                tile = self.game_map[y][x]
                # 计算瓦片在屏幕上的位置和大小，应用UI放大参数和相机偏移
                screen_x = int(
                    (x * self.tile_size - self.camera_x) * self.ui_scale)
                screen_y = int(
                    (y * self.tile_size - self.camera_y) * self.ui_scale)
                scaled_tile_size = int(self.tile_size * self.ui_scale)

                # 根据瓦片类型选择颜色
                if tile.tile_type == TileType.GROUND:
                    color = (100, 150, 100)  # 绿色地面
                elif tile.tile_type == TileType.ROCK:
                    color = (120, 100, 80)   # 棕色岩石/墙壁
                elif tile.tile_type == TileType.GOLD_VEIN:
                    color = (255, 215, 0)    # 金色金矿
                elif tile.tile_type == TileType.ROOM:
                    color = (80, 80, 80)     # 灰色房间
                elif tile.tile_type == TileType.DEPLETED_VEIN:
                    color = (150, 150, 150)  # 灰色枯竭矿脉
                else:
                    color = (120, 120, 120)  # 默认颜色

                pygame.draw.rect(self.screen, color,
                                 (screen_x, screen_y, scaled_tile_size, scaled_tile_size))
                pygame.draw.rect(self.screen, (60, 60, 60),
                                 (screen_x, screen_y, scaled_tile_size, scaled_tile_size), 1)

                # 渲染金矿UI
                if tile.tile_type == TileType.GOLD_VEIN and hasattr(tile, 'gold_mine'):
                    self._render_gold_mine_ui(screen_x, screen_y, tile)

                    # 渲染金矿挖掘状态高亮
                    self._render_mining_status_overlay(
                        tile, screen_x, screen_y)
                elif tile.tile_type == TileType.GOLD_VEIN:
                    pass  # 金矿瓦片，但没有gold_mine对象

    def _render_buildings(self):
        """渲染建筑 - 使用真实游戏的渲染逻辑"""
        for building in self.building_manager.buildings:
            # 使用瓦片坐标计算屏幕位置，与地图渲染保持一致，应用相机偏移
            screen_x = int((building.tile_x * self.tile_size -
                           self.camera_x) * self.ui_scale)
            screen_y = int((building.tile_y * self.tile_size -
                           self.camera_y) * self.ui_scale)
            # 传递放大后的瓦片大小给Building.render
            scaled_tile_size = int(self.tile_size * self.ui_scale)

            # 使用建筑对象自己的渲染方法，传递building_ui
            building.render(self.screen, screen_x, screen_y,
                            self.tile_size, self.font_manager, self.building_ui, self.ui_scale)

            # 使用真实游戏的生命条渲染逻辑
            self._render_building_health_bar_real_game(
                building, screen_x, screen_y)

            # 渲染状态条
            building.render_status_bar(
                self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui, self.ui_scale)

            # 渲染建筑状态高亮覆盖层
            self._render_building_status_overlay(building, screen_x, screen_y)

            # 渲染魔法祭坛的魔力生成粒子特效
            if (hasattr(building, 'building_type') and
                building.building_type.value == 'magic_altar' and
                    hasattr(building, 'render_mana_particles')):
                building.render_mana_particles(
                    self.screen, self.effect_manager, self.ui_scale, self.camera_x, self.camera_y)

    def _render_characters(self):
        """渲染角色 - 使用真实游戏的渲染逻辑"""
        # 使用真实游戏的渲染方法
        self._render_characters_real_game()

    def _render_characters_real_game(self):
        """使用真实游戏的角色渲染逻辑"""
        # 渲染工程师 - 与真实游戏保持一致，作为goblin_engineer类型渲染
        for engineer in self.building_manager.engineers:
            screen_x = int((engineer.x - self.camera_x) * self.ui_scale)
            screen_y = int((engineer.y - self.camera_y) * self.ui_scale)

            # 使用真实游戏中工程师的大小和颜色，应用UI放大参数
            engineer_size = int(getattr(engineer, 'size', 15) * self.ui_scale)
            engineer_color = getattr(engineer, 'color', (100, 100, 255))

            # 工程师使用圆形渲染，与怪物相同（与真实游戏一致）
            pygame.draw.circle(self.screen, engineer_color,
                               (screen_x, screen_y), engineer_size // 2)

            # 绘制状态指示器（与真实游戏一致）
            self._render_creature_status_indicator(
                engineer, screen_x, screen_y)

            # 为工程师绘制携带金币信息（使用真实游戏的方法）
            self._render_engineer_gold(engineer, screen_x, screen_y)

            # 绘制血条（与真实游戏一致）
            if engineer.health < engineer.max_health:
                bar_width = engineer_size
                bar_height = max(1, int(3 * self.ui_scale))
                health_ratio = engineer.health / engineer.max_health
                bar_offset = int(25 * self.ui_scale)

                # 背景条
                bg_rect = pygame.Rect(
                    screen_x - bar_width//2, screen_y - bar_offset, bar_width, bar_height)
                pygame.draw.rect(self.screen, (100, 0, 0), bg_rect)

                # 生命条
                health_rect = pygame.Rect(screen_x - bar_width//2, screen_y - bar_offset,
                                          int(bar_width * health_ratio), bar_height)
                pygame.draw.rect(self.screen, (0, 255, 0), health_rect)

        # 渲染工人 - 使用圆形（与怪物相同）
        for worker in self.monsters:
            # 检查是否为苦工（通过worker_type或类名判断）
            is_worker = (hasattr(worker, 'worker_type') and worker.worker_type == 'goblin_worker') or \
                (hasattr(worker, '__class__')
                 and worker.__class__.__name__ == 'GoblinWorker')

            if is_worker:
                screen_x = int((worker.x - self.camera_x) * self.ui_scale)
                screen_y = int((worker.y - self.camera_y) * self.ui_scale)

                # 使用真实游戏中工人的大小和颜色，应用UI放大参数
                worker_size = int(getattr(worker, 'size', 12) * self.ui_scale)
                worker_color = getattr(worker, 'color', (0, 255, 0))
                # 工人使用圆形渲染，与怪物相同
                pygame.draw.circle(self.screen, worker_color,
                                   (screen_x, screen_y), worker_size // 2)

                # 渲染苦工携带的金币数 - 总是调用，包括金币为0的情况
                self._render_character_gold_display(
                    worker, screen_x, screen_y, worker_size)

                # 绘制工人状态指示器
                self._render_character_status_indicator(
                    worker, screen_x, screen_y)

        # 渲染英雄 - 使用正方形（与真实游戏完全一致）
        for hero in self.heroes:
            screen_x = int((hero.x - self.camera_x) * self.ui_scale)
            screen_y = int((hero.y - self.camera_y) * self.ui_scale)

            # 使用真实游戏中英雄的大小和颜色，应用UI放大参数
            hero_size = int(getattr(hero, 'size', 18) * self.ui_scale)
            hero_color = getattr(hero, 'color', (77, 171, 247))
            # 英雄使用正方形渲染，与真实游戏完全一致
            pygame.draw.rect(self.screen, hero_color,
                             (screen_x - hero_size//2, screen_y - hero_size//2, hero_size, hero_size))

            # 使用真实游戏的生命条渲染逻辑
            self._render_character_health_bar_real_game(
                hero, screen_x, screen_y, hero_size)

            # 绘制英雄状态指示器
            self._render_character_status_indicator(hero, screen_x, screen_y)

        # 渲染怪物 - 使用圆形
        for creature in self.monsters:
            screen_x = int((creature.x - self.camera_x) * self.ui_scale)
            screen_y = int((creature.y - self.camera_y) * self.ui_scale)

            # 使用真实游戏中怪物的大小和颜色，应用UI放大参数
            creature_size = int(getattr(creature, 'size', 12) * self.ui_scale)
            creature_color = getattr(creature, 'color', (255, 100, 100))
            # 怪物使用圆形渲染
            pygame.draw.circle(self.screen, creature_color,
                               (screen_x, screen_y), creature_size // 2)

            # 使用真实游戏的生命条渲染逻辑（与英雄一致）
            self._render_character_health_bar_real_game(
                creature, screen_x, screen_y, creature_size)

            # 绘制怪物状态指示器
            self._render_character_status_indicator(
                creature, screen_x, screen_y)

    def _render_gold_mine_ui(self, screen_x: int, screen_y: int, tile):
        """渲染金矿UI"""
        if not hasattr(tile, 'gold_mine') or not tile.gold_mine:
            return

        gold_mine = tile.gold_mine
        scaled_tile_size = int(self.tile_size * self.ui_scale)

        # 绘制钻石图标
        diamond_size = int(8 * self.ui_scale)
        diamond_x = screen_x + scaled_tile_size // 2 - diamond_size // 2
        diamond_y = screen_y + scaled_tile_size // 2 - diamond_size // 2

        # 根据储量选择颜色
        if gold_mine.gold_amount > 100:
            color = (255, 255, 0)  # 亮金色
        elif gold_mine.gold_amount > 50:
            color = (255, 215, 0)  # 金色
        else:
            color = (184, 134, 11)  # 暗金色

        # 绘制钻石形状
        points = [
            (diamond_x + diamond_size // 2, diamond_y),
            (diamond_x + diamond_size, diamond_y + diamond_size // 2),
            (diamond_x + diamond_size // 2, diamond_y + diamond_size),
            (diamond_x, diamond_y + diamond_size // 2)
        ]
        pygame.draw.polygon(self.screen, color, points)

        # 绘制储量条
        if gold_mine.gold_amount < gold_mine.max_gold_amount:
            bar_width = scaled_tile_size - int(4 * self.ui_scale)
            bar_height = int(3 * self.ui_scale)
            bar_x = screen_x + int(2 * self.ui_scale)
            bar_y = screen_y + scaled_tile_size - int(5 * self.ui_scale)

            # 背景
            pygame.draw.rect(self.screen, (100, 100, 100),
                             (bar_x, bar_y, bar_width, bar_height))

            # 储量条
            ratio = gold_mine.gold_amount / gold_mine.max_gold_amount
            fill_width = int(bar_width * ratio)
            pygame.draw.rect(self.screen, color,
                             (bar_x, bar_y, fill_width, bar_height))

    def _render_effects(self):
        """渲染特效"""
        # 渲染击退动画
        self.knockback_animation.render(
            self.screen, self.camera_x, self.camera_y, self.ui_scale)

        # 渲染攻击特效 - 与真实游戏保持一致，传递UI放大倍数和相机参数
        if self.effect_manager:
            self.screen = self.effect_manager.render(
                self.screen, self.ui_scale, self.camera_x, self.camera_y)

    def _render_ui(self):
        """渲染UI信息 - 性能优化版本"""
        # 检查是否需要重绘UI
        current_values = {
            'simulation_time': round(self.simulation_time, 1),
            'buildings_count': len(self.building_manager.buildings),
            'engineers_count': len(self.building_manager.engineers),
            'workers_count': len([w for w in self.monsters if hasattr(w, 'worker_type') and w.worker_type == 'goblin_worker']),
            'heroes_count': len(self.heroes),
            'dungeon_heart_gold': self.dungeon_heart.stored_gold if self.dungeon_heart else 0,
            'ui_scale': self.ui_scale,
            'camera_x': int(self.camera_x),
            'camera_y': int(self.camera_y)
        }

        # 如果值没有变化且不需要强制重绘，跳过渲染
        if not self._needs_ui_redraw and current_values == self._last_ui_values:
            return

        # 更新缓存的值
        self._last_ui_values = current_values.copy()

        y_offset = 10

        # 模拟时间 - 使用缓存
        time_key = f"time_{current_values['simulation_time']}"
        if time_key not in self._cached_ui_texts:
            self._cached_ui_texts[time_key] = self.font.render(
                f"模拟时间: {current_values['simulation_time']:.1f}s", True, (255, 255, 255))
        self.screen.blit(self._cached_ui_texts[time_key], (10, y_offset))
        y_offset += 30

        # 建筑数量 - 使用缓存
        buildings_key = f"buildings_{current_values['buildings_count']}"
        if buildings_key not in self._cached_ui_texts:
            self._cached_ui_texts[buildings_key] = self.font.render(
                f"建筑数量: {current_values['buildings_count']}", True, (255, 255, 255))
        self.screen.blit(self._cached_ui_texts[buildings_key], (10, y_offset))
        y_offset += 25

        # 角色数量 - 使用缓存
        characters_key = f"characters_{current_values['engineers_count']}_{current_values['workers_count']}_{current_values['heroes_count']}"
        if characters_key not in self._cached_ui_texts:
            self._cached_ui_texts[characters_key] = self.font.render(
                f"工程师: {current_values['engineers_count']}, 工人: {current_values['workers_count']}, 英雄: {current_values['heroes_count']}", True, (255, 255, 255))
        self.screen.blit(self._cached_ui_texts[characters_key], (10, y_offset))
        y_offset += 25

        # 工程师详细统计 - 与真实游戏一致
        if self.building_manager and self.building_manager.engineers:
            engineer_stats = self.building_manager.get_engineer_statistics()

            # 工程师类型统计
            engineer_types_text = f"工程师类型: 基础({engineer_stats['by_type'].get('basic', 0)}) 专业({engineer_stats['by_type'].get('specialist', 0)}) 大师({engineer_stats['by_type'].get('master', 0)})"
            if engineer_types_text not in self._cached_ui_texts:
                self._cached_ui_texts[engineer_types_text] = self.font.render(
                    engineer_types_text, True, (255, 255, 255))
            self.screen.blit(
                self._cached_ui_texts[engineer_types_text], (10, y_offset))
            y_offset += 20

            # 工程师状态统计
            engineer_status_text = f"工程师状态: 空闲({engineer_stats['by_status'].get('idle', 0)}) 工作中({engineer_stats['by_status'].get('constructing', 0)}) 移动中({engineer_stats['by_status'].get('moving_to_site', 0)})"
            if engineer_status_text not in self._cached_ui_texts:
                self._cached_ui_texts[engineer_status_text] = self.font.render(
                    engineer_status_text, True, (255, 255, 255))
            self.screen.blit(
                self._cached_ui_texts[engineer_status_text], (10, y_offset))
            y_offset += 20

            # 工程师效率统计
            efficiency_text = f"平均效率: {engineer_stats['efficiency_stats']['average_efficiency']:.1f}x 总项目: {engineer_stats['efficiency_stats']['total_projects']}"
            if efficiency_text not in self._cached_ui_texts:
                self._cached_ui_texts[efficiency_text] = self.font.render(
                    efficiency_text, True, (255, 255, 255))
            self.screen.blit(
                self._cached_ui_texts[efficiency_text], (10, y_offset))
            y_offset += 25

        # 主基地信息 - 使用缓存
        if self.dungeon_heart:
            heart_key = f"heart_{current_values['dungeon_heart_gold']}"
            if heart_key not in self._cached_ui_texts:
                self._cached_ui_texts[heart_key] = self.font.render(
                    f"主基地金币: {current_values['dungeon_heart_gold']}", True, (255, 255, 255))
            self.screen.blit(self._cached_ui_texts[heart_key], (10, y_offset))
            y_offset += 25

        # UI放大倍数信息 - 使用缓存
        ui_scale_key = f"ui_scale_{current_values['ui_scale']}"
        if ui_scale_key not in self._cached_ui_texts:
            self._cached_ui_texts[ui_scale_key] = self.font.render(
                f"UI放大倍数: {current_values['ui_scale']}x (按+/-调整, 0重置)", True, (255, 255, 255))
        self.screen.blit(self._cached_ui_texts[ui_scale_key], (10, y_offset))
        y_offset += 25

        # 相机位置信息 - 使用缓存
        camera_key = f"camera_{current_values['camera_x']}_{current_values['camera_y']}"
        if camera_key not in self._cached_ui_texts:
            self._cached_ui_texts[camera_key] = self.font.render(
                f"相机位置: ({current_values['camera_x']}, {current_values['camera_y']}) (WASD移动)", True, (255, 255, 255))
        self.screen.blit(self._cached_ui_texts[camera_key], (10, y_offset))
        y_offset += 25

        # 清理旧的缓存（保留最近50个）
        if len(self._cached_ui_texts) > 50:
            keys_to_remove = list(self._cached_ui_texts.keys())[:-50]
            for key in keys_to_remove:
                del self._cached_ui_texts[key]

        self._needs_ui_redraw = False

    def force_ui_redraw(self):
        """强制重绘UI"""
        self._needs_ui_redraw = True

    def set_ui_scale(self, scale: float):
        """
        设置UI放大倍数

        Args:
            scale: 放大倍数，1.0为原始大小，2.0为放大2倍
        """
        if scale <= 0:
            game_logger.info("❌ UI放大倍数必须大于0")
            return False

        old_scale = self.ui_scale
        self.ui_scale = scale
        game_logger.info(f"🔍 UI放大倍数已更新: {old_scale}x -> {scale}x")

        # 强制重绘UI
        self.force_ui_redraw()
        return True

    def get_ui_scale(self) -> float:
        """获取当前UI放大倍数"""
        return self.ui_scale

    # ==================== 统一API接口 ====================

    def move_camera(self, dx: float, dy: float) -> bool:
        """
        移动相机 - 统一API接口

        Args:
            dx: X方向移动量（像素）
            dy: Y方向移动量（像素）

        Returns:
            bool: 是否成功移动
        """
        self.camera_x += dx
        self.camera_y += dy
        game_logger.info(
            f"🎯 模拟器相机移动: ({dx}, {dy}) -> 新位置: ({self.camera_x}, {self.camera_y})")
        return True

    def set_camera_position(self, x: float, y: float) -> bool:
        """
        设置相机位置 - 统一API接口

        Args:
            x: 相机X坐标（像素）
            y: 相机Y坐标（像素）

        Returns:
            bool: 是否成功设置
        """
        self.camera_x = x
        self.camera_y = y
        game_logger.info(f"🎯 模拟器相机位置设置为: ({x}, {y})")
        return True

    def get_camera_position(self) -> Tuple[float, float]:
        """
        获取相机位置 - 统一API接口

        Returns:
            Tuple[float, float]: 相机位置 (x, y)
        """
        return (self.camera_x, self.camera_y)

    def center_camera_on_position(self, world_x: float, world_y: float) -> bool:
        """
        将相机居中到指定世界坐标 - 统一API接口

        Args:
            world_x: 世界X坐标（像素）
            world_y: 世界Y坐标（像素）

        Returns:
            bool: 是否成功居中
        """
        self.camera_x = world_x - self.screen_width // 2
        self.camera_y = world_y - self.screen_height // 2
        game_logger.info(
            f"🎯 模拟器相机居中到世界坐标: ({world_x}, {world_y}) -> 相机位置: ({self.camera_x}, {self.camera_y})")
        return True

    def center_camera_on_tile(self, tile_x: int, tile_y: int) -> bool:
        """
        将相机居中到指定瓦片坐标 - 统一API接口

        Args:
            tile_x: 瓦片X坐标
            tile_y: 瓦片Y坐标

        Returns:
            bool: 是否成功居中
        """
        world_x = tile_x * self.tile_size + self.tile_size // 2
        world_y = tile_y * self.tile_size + self.tile_size // 2
        return self.center_camera_on_position(world_x, world_y)

    def handle_camera_input(self, event) -> bool:
        """
        处理相机输入 - 统一API接口

        Args:
            event: pygame事件

        Returns:
            bool: 是否处理了输入
        """
        if event.type == pygame.KEYDOWN:
            # WASD相机控制
            if event.key == pygame.K_w:
                self.move_camera(0, -self.camera_speed)
                return True
            elif event.key == pygame.K_s:
                self.move_camera(0, self.camera_speed)
                return True
            elif event.key == pygame.K_a:
                self.move_camera(-self.camera_speed, 0)
                return True
            elif event.key == pygame.K_d:
                self.move_camera(self.camera_speed, 0)
                return True
        return False

    def handle_ui_scale_input(self, event) -> bool:
        """
        处理UI缩放输入 - 统一API接口

        Args:
            event: pygame事件

        Returns:
            bool: 是否处理了输入
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                # 放大UI (按+或=键)
                new_scale = min(self.ui_scale + 0.5, 5.0)  # 最大5倍
                return self.set_ui_scale(new_scale)
            elif event.key == pygame.K_MINUS:
                # 缩小UI (按-键)
                new_scale = max(self.ui_scale - 0.5, 0.5)  # 最小0.5倍
                return self.set_ui_scale(new_scale)
            elif event.key == pygame.K_0:
                # 重置UI放大倍数 (按0键)
                return self.set_ui_scale(1.0)
        return False

    # ==================== 工具方法 ====================

    def get_building_at(self, x: int, y: int) -> Optional[Building]:
        """获取指定位置的建筑"""
        for building in self.building_manager.buildings:
            if building.x == x and building.y == y:
                return building
        return None

    def get_engineer_at(self, x: float, y: float, tolerance: float = 1.0) -> Optional[Engineer]:
        """获取指定位置的工程师"""
        for engineer in self.building_manager.engineers:
            if abs(engineer.x - x) <= tolerance and abs(engineer.y - y) <= tolerance:
                return engineer
        return None

    def pause(self):
        """暂停模拟"""
        self.is_paused = True
        game_logger.info("⏸️ 模拟已暂停")

    def resume(self):
        """恢复模拟"""
        self.is_paused = False
        game_logger.info("▶️ 模拟已恢复")

    def reset(self):
        """重置模拟环境"""
        self.simulation_time = 0.0
        self.is_paused = False

        # 清空所有对象
        self.building_manager.buildings.clear()
        self.building_manager.engineers.clear()
        # Workers are managed in monsters list, no need to clear separately
        self.heroes.clear()
        self.monsters.clear()

        # 重置管理器
        self.building_manager = BuildingManager()

        # 重置特殊引用
        self.dungeon_heart = None
        self.treasury = None

        game_logger.info("🔄 模拟环境已重置")

    def get_statistics(self) -> Dict[str, Any]:
        """获取模拟统计信息"""
        return {
            'simulation_time': self.simulation_time / 1000,
            'buildings_count': len(self.building_manager.buildings),
            'creatures_count': len(self.heroes) + len(self.monsters),
            'engineers_count': len(self.building_manager.engineers),
            'workers_count': len([w for w in self.monsters if hasattr(w, 'worker_type') and w.worker_type == 'goblin_worker']),
            'heroes_count': len(self.heroes),
            'monsters_count': len(self.monsters),
            'dungeon_heart_gold': self.dungeon_heart.stored_gold if self.dungeon_heart else 0,
            'treasury_gold': self.treasury.stored_gold if self.treasury else 0,
            'total_gold': self.resource_manager.get_total_gold().total
        }

    # ==================== 事件处理 ====================

    def handle_events(self):
        """处理Pygame事件"""
        if not self.screen:
            return True  # 在模拟器中，即使没有屏幕也继续运行

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.is_paused = not self.is_paused
                    game_logger.info(
                        "⏸️ 模拟已暂停" if self.is_paused else "▶️ 模拟已恢复")
                elif event.key == pygame.K_r:
                    self.reset()
                    game_logger.info("🔄 模拟环境已重置")
                # 处理相机输入
                elif self.handle_camera_input(event):
                    pass  # 相机输入已处理
                # 处理UI缩放输入
                elif self.handle_ui_scale_input(event):
                    pass  # UI缩放输入已处理
        return True

    # ==================== 运行循环 ====================

    def run_simulation(self, max_duration: float = 60.0, enable_visualization: bool = True):
        """运行模拟"""
        if enable_visualization:
            self.init_pygame()
            game_logger.info("🎮 开始可视化模拟")
        else:
            game_logger.info("🎮 开始无头模拟")

        start_time = time.time()
        running = True

        while running and (time.time() - start_time) < max_duration:
            if enable_visualization:
                running = self.handle_events()
                if not running:
                    break

            # 更新游戏逻辑
            # 统一使用毫秒单位，与真实游戏保持一致
            delta_time = 100 if not enable_visualization else self.clock.tick(
                60)
            self.update(delta_time)

            # 渲染（仅可视化模式）
            if enable_visualization:
                self.render()

        if enable_visualization:
            pygame.quit()

        game_logger.info(f"🏁 模拟结束，运行时间: {time.time() - start_time:.1f}秒")
        return self.get_statistics()

    # ==================== 测试辅助方法 ====================

    def wait_for_condition(self, condition_func, timeout: float = 10.0, check_interval: float = 0.1) -> bool:
        """等待某个条件满足"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(check_interval)
        return False

    def get_engineer_by_name(self, name: str) -> Optional[Engineer]:
        """根据名称获取工程师"""
        for engineer in self.building_manager.engineers:
            if engineer.name == name:
                return engineer
        return None

    def get_building_by_name(self, name: str) -> Optional[Building]:
        """根据名称获取建筑"""
        for building in self.building_manager.buildings:
            if building.name == name:
                return building
        return None

    def get_hero_by_name(self, name: str) -> Optional[Hero]:
        """根据名称获取英雄"""
        for hero in self.heroes:
            if hero.name == name:
                return hero
        return None

    def add_gold_to_dungeon_heart(self, amount: int):
        """向主基地添加金币"""
        if self.dungeon_heart:
            self.dungeon_heart.stored_gold += amount
            game_logger.info(
                f"💰 向主基地添加 {amount} 金币，当前金币: {self.dungeon_heart.stored_gold}")

    def damage_building(self, building: Building, damage: int):
        """对建筑造成伤害"""
        if building:
            old_health = building.health
            building.health = max(0, building.health - damage)
            game_logger.info(
                f"💥 {building.name} 受到 {damage} 点伤害: {old_health} -> {building.health}")

            if building.health <= 0:
                building.status = BuildingStatus.DESTROYED
                building.is_active = False
                game_logger.info(f"💀 {building.name} 被摧毁！")

    def heal_building(self, building: Building, heal_amount: int):
        """治疗建筑"""
        if building:
            old_health = building.health
            building.health = min(building.max_health,
                                  building.health + heal_amount)
            game_logger.info(
                f"💚 {building.name} 恢复 {heal_amount} 点生命值: {old_health} -> {building.health}")

            if building.health >= building.max_health * 0.5:
                building.status = BuildingStatus.COMPLETED
                building.is_active = True
                game_logger.info(f"✅ {building.name} 已修复！")

    def move_character_to(self, character, target_x: float, target_y: float, speed: float = 30.0):
        """移动角色到指定位置（单帧移动）"""
        if not character:
            return

        # 计算移动方向
        dx = target_x - character.x
        dy = target_y - character.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 移动角色
            move_distance = speed * 0.1  # 假设每帧0.1秒
            character.x += dx * move_distance
            character.y += dy * move_distance

    def set_character_movement_target(self, character, target_x: float, target_y: float, speed: float = 30.0, tolerance: float = 5.0):
        """
        设置角色的持续移动目标

        Args:
            character: 要移动的角色
            target_x, target_y: 目标位置
            speed: 移动速度
            tolerance: 到达目标的容错距离

        Returns:
            bool: 是否成功设置目标
        """
        if not character:
            game_logger.info("❌ [设置目标] 角色对象为空")
            return False

        character_name = getattr(
            character, 'name', getattr(character, 'type', '未知角色'))

        # 为角色添加移动目标属性
        character.movement_target_x = target_x
        character.movement_target_y = target_y
        character.movement_speed = speed
        character.movement_tolerance = tolerance
        character.has_movement_target = True

        # 重置调试日志标记
        if hasattr(character, '_movement_debug_logged'):
            delattr(character, '_movement_debug_logged')
        if hasattr(character, '_movement_start_logged'):
            delattr(character, '_movement_start_logged')

        game_logger.info(
            f"🎯 为 {character_name} 设置移动目标: ({target_x:.1f}, {target_y:.1f}), 速度: {speed}")
        return True

    def update_character_movement(self, character):
        """
        更新角色的持续移动 - 使用MovementSystem API

        Args:
            character: 要更新的角色

        Returns:
            bool: 是否到达目标位置
        """
        if not character:
            return False

        has_target = getattr(character, 'has_movement_target', False)
        character_name = getattr(
            character, 'name', getattr(character, 'type', '未知角色'))

        if not has_target:
            return False

        # 获取移动目标
        target_x = character.movement_target_x
        target_y = character.movement_target_y
        speed = character.movement_speed
        tolerance = character.movement_tolerance

        # 计算到目标的距离
        dx = target_x - character.x
        dy = target_y - character.y
        distance = math.sqrt(dx * dx + dy * dy)

        # 检查是否已经到达目标
        if distance <= tolerance:
            # 清除移动目标
            character.has_movement_target = False
            delattr(character, 'movement_target_x')
            delattr(character, 'movement_target_y')
            delattr(character, 'movement_speed')
            delattr(character, 'movement_tolerance')

            game_logger.info(
                f"✅ {character_name} 已到达目标位置: ({character.x:.1f}, {character.y:.1f})")
            return True

        # 使用MovementSystem进行移动
        MovementSystem.target_seeking_movement(
            character, (target_x, target_y), 0.1, self.game_map,
            speed_multiplier=speed / 30.0)  # 将速度转换为倍数

        # 只在移动开始时输出一次日志
        if not hasattr(character, '_movement_start_logged'):
            game_logger.info(
                f"🚶 {character_name} 开始移动: 目标({target_x:.1f}, {target_y:.1f}), 速度: {speed}")
            character._movement_start_logged = True

        return False

    def set_character_position(self, character, x: float, y: float):
        """设置角色位置"""
        if character:
            character.x = x
            character.y = y
            game_logger.info(
                f"📍 {character.name if hasattr(character, 'name') else '角色'} 移动到 ({x}, {y})")

    # ==================== 日志和调试 ====================

    def log_event(self, message: str):
        """记录事件日志"""
        timestamp = f"[{self.simulation_time:.1f}s]"
        game_logger.info(f"{timestamp} {message}")

    def get_debug_info(self) -> Dict[str, Any]:
        """获取调试信息"""
        debug_info = {
            'simulation_time': self.simulation_time,
            'is_paused': self.is_paused,
            'pygame_available': self.screen is not None,
            'map_size': f"{self.map_width}x{self.map_height}",
            'tile_size': self.tile_size
        }

        # 建筑信息
        debug_info['buildings'] = []
        for building in self.building_manager.buildings:
            debug_info['buildings'].append({
                'name': building.name,
                'type': building.building_type.value,
                'position': (building.x, building.y),
                'health': f"{building.health}/{building.max_health}",
                'status': building.status.value,
                'is_active': building.is_active
            })

        # 工程师信息
        debug_info['engineers'] = []
        for engineer in self.building_manager.engineers:
            debug_info['engineers'].append({
                'name': engineer.name,
                'position': (engineer.x, engineer.y),
                'carried_gold': engineer.carried_gold,
                'status': engineer.status.value if hasattr(engineer, 'status') else 'unknown'
            })

        return debug_info

    def _log_debug_info(self):
        """打印调试信息"""
        debug_info = self.get_debug_info()
        game_logger.info("\n" + "=" * 50)
        game_logger.info("🐛 调试信息")
        game_logger.info("=" * 50)

        for key, value in debug_info.items():
            if key not in ['buildings', 'engineers']:
                game_logger.info(f"{key}: {value}")

        game_logger.info(f"\n建筑列表 ({len(debug_info['buildings'])}):")
        for building in debug_info['buildings']:
            game_logger.info(
                f"  - {building['name']} ({building['type']}) at {building['position']} - {building['health']} HP")

        game_logger.info(f"\n工程师列表 ({len(debug_info['engineers'])}):")
        for engineer in debug_info['engineers']:
            game_logger.info(
                f"  - {engineer['name']} at {engineer['position']} - ${engineer['carried_gold']} gold")

        game_logger.info("=" * 50)

    # ==================== 预设测试场景扩展 ====================

    def setup_complex_test_scenario(self):
        """设置复杂测试场景"""
        # 创建主基地
        self.create_dungeon_heart(5, 5, 1000)

        # 创建金库
        self.create_treasury(8, 5, 0)

        # 创建多个箭塔（不同状态）
        self.create_arrow_tower(15, 10)  # 完整箭塔
        self.create_arrow_tower(20, 15, 18)  # 18弹药
        self.create_arrow_tower(25, 20, 42)  # 42弹药

        # 创建巢穴 - 已删除，使用新的兽人巢穴和恶魔巢穴

        # 创建多个工程师
        self.create_engineer(6, 6)  # 靠近主基地
        self.create_engineer(10, 10)  # 中间位置

        # 创建工人
        self.create_worker(7, 7)

        # 创建英雄
        knight = self.create_hero(200, 200, 'knight')
        knight.health = 100
        knight.max_health = 100

        game_logger.info("🏗️ 复杂测试场景设置完成")

    def setup_stress_test_scenario(self):
        """设置压力测试场景"""
        # 创建大量建筑
        for i in range(10):
            for j in range(10):
                if (i + j) % 3 == 0:  # 每3个位置创建一个建筑
                    self.create_arrow_tower(
                        i * 3, j * 3, random.randint(0, 60))

        # 创建主基地
        self.create_dungeon_heart(15, 15, 5000)

        # 创建大量工程师
        for i in range(20):
            self.create_engineer(random.uniform(0, 30), random.uniform(0, 30))

        game_logger.info("⚡ 压力测试场景设置完成")

    def setup_physics_test_scenario(self):
        """设置物理系统测试场景"""
        # 创建主基地
        self.create_dungeon_heart(10, 10, 1000)

        # 创建多个单位用于测试碰撞和击退
        for i in range(5):
            x = random.uniform(100, 300)
            y = random.uniform(100, 300)
            self.create_creature(x, y, 'goblin')

        # 创建英雄用于测试击退
        knight = self.create_hero(200, 200, 'knight')
        knight.health = 100
        knight.max_health = 100

        game_logger.info("⚔️ 物理系统测试场景设置完成")

    def setup_effects_test_scenario(self):
        """设置特效系统测试场景 - 现在使用combat_system统一处理特效"""
        # 创建主基地
        self.create_dungeon_heart(10, 10, 1000)

        # 创建箭塔用于测试攻击特效
        self.create_arrow_tower(15, 10)

        # 创建英雄用于测试战斗特效
        knight = self.create_hero(200, 200, 'knight')
        knight.health = 100
        knight.max_health = 100

        game_logger.info("✨ 特效系统测试场景设置完成 - 使用combat_system统一处理")

    def setup_comprehensive_test_scenario(self):
        """设置综合测试场景"""
        # 生成随机地图
        self.generate_random_map(
            gold_mine_count=8, rock_count=15, wall_count=10)

        # 创建主基地
        self.create_dungeon_heart(5, 5, 2000)

        # 创建各种建筑
        self.create_treasury(8, 5, 0)
        self.create_arrow_tower(15, 10)
        self.create_training_room(20, 15)
        self.create_library(25, 20)
        self.create_prison(30, 25)
        self.create_defense_fortification(35, 30)

        # 创建角色
        for i in range(3):
            x = random.uniform(50, 200)
            y = random.uniform(50, 200)
            self.create_engineer(x, y)

        for i in range(2):
            x = random.uniform(50, 200)
            y = random.uniform(50, 200)
            self.create_worker(x, y)

        # 创建英雄
        knight = self.create_hero(300, 300, 'knight')
        knight.health = 120
        knight.max_health = 120

        game_logger.info("🎯 综合测试场景设置完成")

    # ==================== 工具方法扩展 ====================

    def simulate_attack(self, attacker, target, damage: float = 20.0) -> bool:
        """
        模拟攻击并应用击退效果 - 委托给战斗系统处理

        Args:
            attacker: 攻击者
            target: 目标
            damage: 攻击伤害

        Returns:
            bool: 是否成功攻击
        """
        if not attacker or not target:
            return False

        # 委托给战斗系统处理攻击逻辑
        # 应用伤害
        if hasattr(target, 'health'):
            target.health -= damage
            target.health = max(0, target.health)

        # 应用击退效果
        success = self.apply_knockback(attacker, target, damage, "normal")

        # 创建攻击特效 - 使用粒子效果
        self.create_particle_effect(target.x, target.y, 8, (255, 100, 100))

        return success

    def get_physics_stats(self) -> Dict[str, Any]:
        """获取物理系统统计信息"""
        return self.physics_system.get_performance_stats()

    def get_effects_stats(self) -> Dict[str, Any]:
        """获取特效系统统计信息"""
        return {
            'knockback_effects': self.knockback_animation.get_effect_count(),
            'visual_effects': len(self.effect_manager.visual_effects) if hasattr(self.effect_manager, 'visual_effects') else 0,
            'particle_effects': len(self.effect_manager.particle_system.particles) if hasattr(self.effect_manager, 'particle_system') else 0
        }

    def _render_building_health_bar_real_game(self, building, screen_x: int, screen_y: int):
        """使用真实游戏的建筑生命条渲染逻辑"""
        # 检查是否是地牢之心（2x2建筑）
        if (hasattr(building, 'building_type') and
                building.building_type.value == 'dungeon_heart'):
            # 使用真实游戏的地牢之心专用生命条渲染
            self._render_dungeon_heart_health_bar_real_game(
                building, screen_x, screen_y)
        else:
            # 使用BuildingUI的通用建筑生命条渲染
            if self.building_ui:
                self.building_ui.render_building_health_bar(
                    self.screen, screen_x, screen_y, self.tile_size, None, building, self.ui_scale)

    def _render_dungeon_heart_health_bar_real_game(self, building, screen_x: int, screen_y: int):
        """使用真实游戏的地牢之心生命条渲染逻辑"""
        if not hasattr(building, 'health') or not hasattr(building, 'max_health'):
            return

        # 计算血量百分比
        health_percentage = building.health / \
            building.max_health if building.max_health > 0 else 0.0

        # 2x2地牢之心的血量条尺寸和位置，应用UI缩放
        scaled_tile_size = int(self.tile_size * self.ui_scale)
        total_width = scaled_tile_size * 2  # 2x2建筑的总宽度
        bar_width = total_width - int(16 * self.ui_scale)  # 更宽的血量条
        bar_height = max(1, int(8 * self.ui_scale))  # 更高的血量条
        bar_x = screen_x + int(8 * self.ui_scale)  # 血量条X位置（居中）
        bar_y = screen_y - int(15 * self.ui_scale)  # 血量条Y位置（建筑上方）

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

    def _render_character_health_bar_real_game(self, character, screen_x: int, screen_y: int, character_size: int):
        """使用真实游戏的角色生命条渲染逻辑"""
        # 使用真实游戏的角色生命条渲染逻辑
        if hasattr(character, 'max_health') and character.max_health > 0 and character.health < character.max_health:
            bar_width = character_size
            bar_height = int(3 * self.ui_scale)
            health_ratio = character.health / character.max_health
            bar_offset = int(25 * self.ui_scale)

            # 红色背景
            pygame.draw.rect(self.screen, (255, 0, 0),
                             (screen_x - bar_width//2, screen_y - bar_offset, bar_width, bar_height))
            # 绿色血量
            pygame.draw.rect(self.screen, (0, 255, 0),
                             (screen_x - bar_width//2, screen_y - bar_offset, bar_width * health_ratio, bar_height))

    def _safe_render_text(self, font, text, color, use_emoji_fallback=True):
        """安全渲染文本，使用UnifiedFontManager的safe_render方法"""
        if self.font_manager:
            return self.font_manager.safe_render(font, text, color, use_emoji_fallback, self.ui_scale)
        else:
            # 回退到简单渲染
            return font.render(str(text), True, color)

    def _render_character_status_indicator(self, character, screen_x: int, screen_y: int):
        """渲染角色状态指示器 - 使用真实游戏的API"""
        if self.status_indicator:
            # 获取角色状态 - 支持工程师和通用生物
            character_state = 'idle'
            if hasattr(character, 'state'):
                # 通用生物状态
                character_state = character.state
            elif hasattr(character, 'status'):
                # 工程师状态
                character_state = character.status.value if hasattr(
                    character.status, 'value') else str(character.status)

            character_size = getattr(character, 'size', 15)

            # 使用真实游戏的状态指示器API
            self.status_indicator.render(
                self.screen, screen_x, screen_y, character_size, character_state, self.ui_scale)
        else:
            # StatusIndicator系统不可用，记录错误日志
            game_logger.error("❌ StatusIndicator系统不可用，无法渲染角色状态指示器")

    def _render_character_gold_display(self, character, screen_x: int, screen_y: int, character_size: int):
        """渲染角色携带的金币数显示"""
        carried_gold = getattr(character, 'carried_gold', 0)

        # 如果金币数为0，不渲染
        if carried_gold <= 0:
            return

        # 如果状态指示器可用，使用它来渲染
        if self.status_indicator:
            try:
                self.status_indicator.render_carried_gold(
                    self.screen, screen_x, screen_y, character_size, carried_gold,
                    self.ui_scale, self.font_manager.get_font(16),
                    getattr(self, 'cached_texts', {}), self.font_manager)
                return
            except Exception as e:
                game_logger.warning(f"⚠️ 状态指示器渲染金币失败: {e}")

    def _render_building_status_overlay(self, building, screen_x: int, screen_y: int):
        """渲染建筑状态高亮覆盖层 - 使用真实游戏的API"""
        if not self.status_indicator:
            return

        # 根据建筑类型确定状态指示器尺寸
        if (hasattr(building, 'building_type') and
            building.building_type.value == 'dungeon_heart' and
                hasattr(building, 'building_size') and building.building_size == (2, 2)):
            # 2x2地牢之心：使用2倍瓦片大小
            status_indicator_size = self.tile_size * 2
        else:
            # 普通1x1建筑：使用标准瓦片大小
            status_indicator_size = self.tile_size

        # 使用建筑的 get_status_for_indicator 方法获取状态
        if hasattr(building, 'get_status_for_indicator'):
            status = building.get_status_for_indicator()
            self.status_indicator.render_building_highlight(
                self.screen, screen_x, screen_y, status_indicator_size, status, self.ui_scale)
        else:
            # 回退到旧的状态判断逻辑
            if building.status.value == 'destroyed':
                self.status_indicator.render_building_highlight(
                    self.screen, screen_x, screen_y, status_indicator_size, 'destroyed', self.ui_scale)
            elif hasattr(building, 'health') and building.health < building.max_health:
                self.status_indicator.render_building_highlight(
                    self.screen, screen_x, screen_y, status_indicator_size, 'needs_repair', self.ui_scale)
            elif building.status.value == 'completed':
                self.status_indicator.render_building_highlight(
                    self.screen, screen_x, screen_y, status_indicator_size, 'completed', self.ui_scale)
            elif building.status.value in ['planning', 'under_construction']:
                self.status_indicator.render_building_highlight(
                    self.screen, screen_x, screen_y, status_indicator_size, 'incomplete', self.ui_scale)

    def _render_mining_status_overlay(self, tile, screen_x: int, screen_y: int):
        """渲染金矿挖掘状态高亮覆盖层 - 使用真实游戏的API"""
        if not self.status_indicator:
            game_logger.warning("⚠️ StatusIndicator不可用，跳过金矿状态渲染")
            return

        # 获取挖掘者数量 - 优先从 gold_mine 对象获取
        miners_count = 0
        being_mined = False

        if hasattr(tile, 'gold_mine') and tile.gold_mine:
            # 从 GoldMine 对象获取挖掘状态
            gold_mine = tile.gold_mine
            miners_count = len(
                [a for a in gold_mine.mining_assignments if a.is_active])
            being_mined = gold_mine.status == GoldMineStatus.BEING_MINED

        else:
            # 回退到 tile 属性
            miners_count = getattr(tile, 'miners_count', 0)
            being_mined = getattr(tile, 'being_mined', False)
            game_logger.warning(
                f"⚠️ 金矿瓦片缺少gold_mine对象: 位置=({tile.x}, {tile.y})")

        # 如果有挖掘者或正在被挖掘，显示挖掘状态高亮
        if miners_count > 0 or being_mined:
            game_logger.info(
                f"🎨 渲染金矿状态高亮: 位置=({tile.x}, {tile.y}), 挖掘者={miners_count}")
            self.status_indicator.render_mining_highlight(
                self.screen, screen_x, screen_y, self.tile_size, miners_count, self.ui_scale)

    def _cleanup_dead_units(self):
        """清理死亡的单位 - 与真实游戏保持一致"""
        # 清理死亡的怪物
        dead_monsters = [c for c in self.monsters if c.health <= 0]
        for creature in dead_monsters:
            # 清理近战目标追踪
            if creature.melee_target is not None:
                if creature.melee_target.melee_target == creature:
                    creature.melee_target.melee_target = None
                creature.melee_target = None
            # 清理挖掘分配
            if creature.type == 'goblin_worker':
                creature._cleanup_mining_assignment(self.game_map)
            # 通知绑定的巢穴（如果有）- 统一处理兽人战士和小恶魔
            if hasattr(creature, 'bound_lair') and creature.bound_lair:
                creature.bound_lair.on_bound_monster_died()
                game_logger.info(f"🔓 通知巢穴：{creature.type} 已死亡，解除绑定")

            # 从monsters列表中移除
            self.monsters.remove(creature)
            game_logger.info(f"💀 {creature.type} 死亡并被移除")

        # 清理死亡的工程师
        dead_engineers = [
            e for e in self.building_manager.engineers if e.health <= 0]
        for engineer in dead_engineers:
            # 清理工程师的任务分配
            if hasattr(engineer, 'target_building') and engineer.target_building:
                engineer.target_building = None

            # 从building_manager.engineers列表中移除
            self.building_manager.engineers.remove(engineer)
            game_logger.info(f"💀 工程师 {engineer.name} 死亡并被移除")

        # 清理死亡的英雄
        dead_heroes = [h for h in self.heroes if h.health <= 0]
        for hero in dead_heroes:
            # 清理近战目标追踪
            if hero.melee_target is not None:
                if hero.melee_target.melee_target == hero:
                    hero.melee_target.melee_target = None
                hero.melee_target = None
            self.heroes.remove(hero)
            game_logger.info(f"💀 {hero.type} 死亡并被移除")

    def clear_all_effects(self):
        """清除所有特效"""
        self.knockback_animation.clear_all_effects()
        if hasattr(self.effect_manager, 'clear_all'):
            self.effect_manager.clear_all()
        game_logger.info("🧹 清除所有特效")

    def _safe_log(self, text, fallback_prefix=""):
        """
        安全的打印方法，自动处理表情符号兼容性

        Args:
            text: 要打印的文本
            fallback_prefix: 回退文本的前缀
        """
        # 如果字体管理器已初始化，使用其安全打印方法
        if hasattr(self, 'font_manager') and self.font_manager:
            self.font_manager.safe_log_with_emoji(
                text, fallback_prefix)
        else:
            # 回退到简单的文本替代
            try:
                game_logger.info(text)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 如果编码错误，使用简单的文本替代
                safe_text = text
                # 简单的表情符号替代
                emoji_replacements = {
                    '🗺️': '[地图]', '🎮': '[游戏]', '📐': '[尺寸]', '🔍': '[放大]',
                    '🎯': '[目标]', '⚔️': '[战斗]', '👹': '[怪物]', '💰': '[金币]',
                    '⛏️': '[挖掘]', '🏰': '[城堡]', '💖': '[心形]', '🔨': '[锤子]',
                    '🛑': '[停止]', '📚': '[书籍]', '🔍': '[搜索]', '✅': '[确认]',
                    '⚠️': '[警告]', '❌': '[错误]', '🏗️': '[建造]', '📝': '[笔记]',
                    '📤': '[发送]', '🎒': '[背包]', '💀': '[骷髅]', '🗡️': '[剑]',
                    '🛡️': '[盾牌]', '💚': '[绿心]', '🔤': '[字母]', '📊': '[图表]',
                    '📷': '[相机]', '🚀': '[火箭]', '🧙': '[法师]', '🌿': '[植物]',
                    '🗿': '[石头]', '👑': '[王冠]', '🐲': '[龙]', '🔥': '[火焰]',
                    '🦅': '[鹰]', '🦎': '[蜥蜴]', '🛠️': '[工具]', '🧙‍♂️': '[男法师]'
                }

                for emoji, replacement in emoji_replacements.items():
                    safe_text = safe_text.replace(emoji, replacement)

                game_logger.info(f"{fallback_prefix}{safe_text}")

    def get_assignment_status(self) -> Dict[str, Any]:
        """获取自动分配器状态信息"""
        result = {
            'engineer_assigner': {
                'available': False,
                'strategy': None,
                'active_tasks': 0,
                'assigned_engineers': 0
            },
            'worker_assigner': {
                'available': False,
                'strategy': None,
                'active_tasks': 0,
                'assigned_workers': 0
            }
        }

        try:
            # 获取工程师分配器状态
            if hasattr(self.building_manager, 'engineer_assigner') and self.building_manager.engineer_assigner:
                engineer_stats = self.building_manager.engineer_assigner.get_statistics()
                # 工程师现在只由building_manager管理
                engineers = self.building_manager.engineers
                result['engineer_assigner'] = {
                    'available': True,
                    'strategy': engineer_stats.get('strategy', 'unknown'),
                    'active_tasks': engineer_stats.get('assigned_tasks', 0),
                    'assigned_engineers': len([eng for eng in engineers if hasattr(eng, 'target_building') and eng.target_building])
                }

            # 获取苦工分配器状态
            if hasattr(self.building_manager, 'worker_assigner') and self.building_manager.worker_assigner:
                worker_stats = self.building_manager.worker_assigner.get_statistics()
                # 从monsters列表中筛选苦工
                workers = [m for m in self.monsters if hasattr(
                    m, 'creature_type') and m.creature_type == 'goblin_worker']
                result['worker_assigner'] = {
                    'available': True,
                    'strategy': worker_stats.get('strategy', 'unknown'),
                    'active_tasks': worker_stats.get('assigned_tasks', 0),
                    'assigned_workers': len([worker for worker in workers if hasattr(worker, 'target_building') and worker.target_building])
                }

        except Exception as e:
            game_logger.warning(f"获取分配器状态时出错: {e}")

        return result

    def _render_engineer_gold(self, creature, screen_x, screen_y):
        """渲染工程师携带金币信息（与真实游戏一致）"""
        # 渲染工程师携带的金币数 - 使用统一API和字体管理器
        if hasattr(creature, 'carried_gold') and creature.carried_gold > 0:
            if self.status_indicator:
                self.status_indicator.render_carried_gold(
                    self.screen, screen_x, screen_y,
                    int(creature.size * self.ui_scale),
                    creature.carried_gold, self.ui_scale,
                    self.font_manager.get_font(16), self._cached_ui_texts, self.font_manager)
            else:
                # 回退到简单渲染
                gold_text = f"${creature.carried_gold}"
                gold_surface = self.font_manager.safe_render(
                    self.font_manager.get_font(12), gold_text, (255, 255, 0), self.ui_scale)
                text_rect = gold_surface.get_rect(
                    center=(screen_x, screen_y - int(creature.size * self.ui_scale)))
                self.screen.blit(gold_surface, text_rect)

    def _render_creature_status_indicator(self, creature, screen_x, screen_y):
        """渲染生物状态指示器（与真实游戏一致）"""
        if self.status_indicator:
            # 获取生物状态
            creature_state = 'idle'
            if hasattr(creature, 'state'):
                creature_state = creature.state
            elif hasattr(creature, 'get_status_for_indicator'):
                creature_state = creature.get_status_for_indicator()

            # 渲染状态指示器
            self.status_indicator.render(
                self.screen, screen_x, screen_y, int(creature.size * self.ui_scale), creature_state, self.ui_scale)
        else:
            # StatusIndicator系统不可用，记录错误日志
            game_logger.error("❌ StatusIndicator系统不可用，无法渲染生物状态指示器")

    def __del__(self):
        """析构函数"""
        if hasattr(self, 'screen') and self.screen:
            pygame.quit()
