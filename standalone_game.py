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

# 使用try语句处理导入错误，避免循环导入问题
try:
    from src.managers.building_manager import BuildingManager
    from src.entities.building import BuildingType, BuildingRegistry
    from src.entities.monster.goblin_engineer import EngineerType, EngineerRegistry
    from src.systems.combat_system import CombatSystem
    from src.systems.placement_system import PlacementSystem
    from src.effects.effect_manager import EffectManager
    from src.systems.physics_system import PhysicsSystem
    from src.systems.knockback_animation import KnockbackAnimation
    from src.systems.unified_pathfinding import PathfindingConfig
    from src.systems.reachability_system import get_reachability_system
    from src.managers.resource_manager import get_resource_manager
    from src.effects.glow_effect import get_glow_manager
    from src.ui.character_bestiary import CharacterBestiary
    from src.ui.status_indicator import StatusIndicator
    from src.ui.building_ui import BuildingUI
    from src.core.constants import GameConstants, GameBalance
    from src.core.enums import TileType, BuildMode
    from src.core.game_state import Tile, GameState
    from src.core import emoji_constants
    from src.entities.configs import CreatureConfig, HeroConfig
    from src.entities.character_data import character_db
    from src.entities.creature import Creature
    from src.entities.monsters import Monster
    from src.entities.monster.goblin_worker import GoblinWorker
    from src.entities.monster.goblin_engineer import Engineer, EngineerType
    from src.entities.heros import Hero
    from src.managers.movement_system import MovementSystem
    from src.managers.font_manager import UnifiedFontManager
    from src.managers.tile_manager import tile_manager
    from src.ui.game_ui import GameUI
    from src.ui.monster_selection import MonsterSelectionUI
    from src.ui.logistics_selection import LogisticsSelectionUI
    from src.entities.monster.goblin_engineer import EngineerRegistry
    from src.utils.logger import game_logger
except ImportError as e:
    from src.utils.logger import game_logger
    game_logger.error(f"❌ 系统导入失败: {e}")
    raise


# 初始化pygame
pygame.init()

# 创建全局统一字体管理器实例（在pygame初始化后）
font_manager = UnifiedFontManager()

# 为了向后兼容，创建emoji_manager别名，使用emoji常量模块
emoji_manager = emoji_constants

# 设置输入法兼容性
pygame.key.set_repeat(500, 50)  # 设置按键重复延迟，有助于输入法兼容


class IdleStateManager:
    """全局空闲状态管理器 - 统一管理所有生物的空闲到游荡状态转换"""

    def __init__(self):
        """初始化空闲状态管理器"""
        self.idle_units = {}  # {unit_id: {'start_time': timestamp, 'unit': unit}}
        self.idle_timeout = 0.1  # 空闲超时时间（秒）

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
                game_logger.debug(
                    f"⏰ 单位 {getattr(unit, 'name', 'Unknown')} 空闲超时: {idle_duration:.3f}秒 >= {self.idle_timeout}秒")
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
                if hasattr(unit.status, 'value'):
                    if unit.status.value == EngineerStatus.IDLE.value:
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
                    # 无论当前是IDLE还是WAITING，都转换为WANDERING
                    old_status = str(unit.status)
                    unit.status = EngineerStatus.WANDERING
                    game_logger.info(
                        f"🎲 {unit_name} ({unit_type}) 从{old_status}状态转换为游荡状态")
                else:
                    # 回退到通用状态 - 使用状态枚举
                    from src.entities.creature import CreatureStatus
                    unit.state = CreatureStatus.WANDERING.value
                    game_logger.info(
                        f"🎲 {unit_name} ({unit_type}) 从空闲状态转换为游荡状态")

        except Exception as e:
            game_logger.error(f"❌ 转换单位到游荡状态时出错: {e}")


class WarForTheOverworldGame:
    def __init__(self):
        """初始化游戏"""
        game_logger.info(
            f"{emoji_manager.ROCKET} War for the Overworld - Python独立版本")
        game_logger.info("=" * 60)

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
        self.monsters: List[Monster] = []
        self.heroes: List[Hero] = []
        self.dungeon_heart_pos = (0, 0)
        self.hero_bases = []

        # 特效系统 - 使用整合后的EffectManager
        # 使用2倍速度初始化，斩击类特效会额外加速1倍（总共2倍速度）
        self.effect_manager = EffectManager(speed_multiplier=2.0)
        game_logger.info(
            f"{emoji_manager.SPARKLES} 整合特效系统初始化成功 (速度: 2.0x，斩击特效: 2.0x)")

        # 物理系统 - 提供碰撞检测和击退效果
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

        game_logger.info(
            f"⚡ 物理系统初始化成功 (世界边界: {world_bounds}, 瓦片大小: {GameConstants.TILE_SIZE})")

        # 地图系统
        self.map_width = GameConstants.MAP_WIDTH
        self.map_height = GameConstants.MAP_HEIGHT
        self.tile_size = GameConstants.TILE_SIZE
        self.game_map = self._initialize_map()

        # 初始化统一寻路系统
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
            game_logger.info("🚀 统一寻路系统初始化成功")

        # 初始化高级寻路系统（NavMesh）作为备用
        navmesh_success = MovementSystem.initialize_advanced_pathfinding(
            self.game_map, self.map_width, self.map_height)
        if navmesh_success:
            game_logger.info("🧭 高级寻路系统（NavMesh）初始化成功")
        else:
            game_logger.info("⚠️ 高级寻路系统初始化失败，将使用统一寻路系统")

        # 相机系统 - 居中到地牢之心
        heart_pixel_x = self.dungeon_heart_pos[0] * self.tile_size
        heart_pixel_y = self.dungeon_heart_pos[1] * self.tile_size
        self.camera_x = heart_pixel_x - GameConstants.WINDOW_WIDTH // 2
        self.camera_y = heart_pixel_y - GameConstants.WINDOW_HEIGHT // 2
        game_logger.info(
            f"{emoji_manager.CAMERA} 相机居中到地牢之心: ({self.camera_x}, {self.camera_y})")

        # UI缩放系统
        self.ui_scale = 1.0  # 默认UI缩放倍数
        self.min_ui_scale = 0.5  # 最小UI缩放倍数
        self.max_ui_scale = 5.0  # 最大UI缩放倍数

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

        # 性能优化缓存
        self._cached_ui_texts = {}  # 缓存UI文本

        # 角色图鉴系统
        self.bestiary = CharacterBestiary(
            GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager)
        game_logger.info("📚 角色图鉴系统已加载")

        # 状态指示器系统
        self.status_indicator = StatusIndicator()

        # 美化UI渲染器
        self.game_ui = GameUI(self.screen, self.font_manager)
        game_logger.info("🎨 美化UI系统已加载")

        # 怪物选择UI系统
        self.monster_selection_ui = MonsterSelectionUI(
            GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager)
        # 设置emoji_mapper引用（向后兼容）
        self.monster_selection_ui.emoji_mapper = self.emoji_mapper

        # 后勤召唤UI系统
        self.logistics_selection_ui = LogisticsSelectionUI(
            GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager)

        # 建筑系统
        self.building_manager = BuildingManager()
        self.building_manager.game_instance = self  # 设置游戏实例引用
        self.building_ui = BuildingUI(
            GameConstants.WINDOW_WIDTH, GameConstants.WINDOW_HEIGHT, self.font_manager, game_instance=self)

        # 添加待处理的地牢之心到建筑管理器
        if hasattr(self, '_pending_dungeon_heart') and self._pending_dungeon_heart:
            self.dungeon_heart = self._pending_dungeon_heart  # 设置地牢之心引用
            self.building_manager.buildings.append(
                self._pending_dungeon_heart)
            game_logger.info(f"✅ 地牢之心已添加到建筑管理器")

            # 注册地牢之心到ResourceManager
            resource_manager = get_resource_manager(self)
            resource_manager.register_dungeon_heart(self.dungeon_heart)

            delattr(self, '_pending_dungeon_heart')  # 清理临时引用

        game_logger.info("🏗️ 建筑系统已初始化")

        # 战斗系统
        self.combat_system = CombatSystem()
        self.combat_system.set_game_instance(self)  # 设置游戏实例引用
        game_logger.info("⚔️ 战斗系统已初始化")

        # 角色数据库 - 设置到游戏实例
        self.character_db = character_db
        game_logger.info("📚 角色数据库已设置到游戏实例")

        # 统一放置系统
        self.placement_system = PlacementSystem(self)
        game_logger.info("🎯 统一放置系统已初始化")

        game_logger.info(f"{emoji_manager.CHECK} 游戏初始化完成")

        # 游戏初始化完成后，启用接壤金矿脉日志输出
        reachability_system = get_reachability_system()
        reachability_system.enable_adjacent_vein_logging()

    def _update_world_mouse_position(self):
        """更新鼠标在世界坐标中的位置"""
        # 考虑UI缩放：鼠标坐标需要除以缩放倍数
        scaled_mouse_x = self.mouse_x / self.ui_scale
        scaled_mouse_y = self.mouse_y / self.ui_scale

        self.mouse_world_x = int(
            (scaled_mouse_x + self.camera_x) // self.tile_size)
        self.mouse_world_y = int(
            (scaled_mouse_y + self.camera_y) // self.tile_size)

    def _handle_click(self, mouse_pos: Tuple[int, int]):
        """处理鼠标点击 - 使用统一放置系统"""
        self.mouse_x, self.mouse_y = mouse_pos
        self._update_world_mouse_position()

        if (self.mouse_world_x < 0 or self.mouse_world_x >= self.map_width or
                self.mouse_world_y < 0 or self.mouse_world_y >= self.map_height):
            return

        # 使用统一放置系统处理所有放置操作
        if self.placement_system:
            if self.build_mode == BuildMode.DIG:
                # 挖掘操作仍使用原有方法
                self._dig_tile(self.mouse_world_x, self.mouse_world_y)
            elif self.build_mode == BuildMode.SUMMON:
                if self.selected_monster_type:
                    result = self.placement_system.place_entity(
                        self.selected_monster_type,
                        self.mouse_world_x,
                        self.mouse_world_y
                    )
                    if result.success:
                        game_logger.info(f"✅ {result.message}")
                    else:
                        game_logger.info(f"❌ {result.message}")
            elif self.build_mode == BuildMode.SUMMON_LOGISTICS:
                if hasattr(self, 'selected_logistics_type'):
                    result = self.placement_system.place_entity(
                        self.selected_logistics_type,
                        self.mouse_world_x,
                        self.mouse_world_y
                    )
                    if result.success:
                        game_logger.info(f"✅ {result.message}")
                    else:
                        game_logger.info(f"❌ {result.message}")
            elif self.build_mode == BuildMode.BUILD_SPECIFIC:
                if hasattr(self, 'selected_building_type'):
                    entity_id = f"building_{self.selected_building_type.value}"
                    result = self.placement_system.place_entity(
                        entity_id,
                        self.mouse_world_x,
                        self.mouse_world_y
                    )
                    if result.success:
                        game_logger.info(f"✅ {result.message}")
                        # 清空选择
                        self.selected_building_type = None
                        self.build_mode = BuildMode.NONE
                        if self.building_ui:
                            self.building_ui.clear_selections()
                    else:
                        game_logger.info(f"❌ {result.message}")
        else:
            game_logger.error("❌ 统一放置系统不可用，无法处理点击事件")

    def _dig_tile(self, x: int, y: int):
        """挖掘瓦片 - 使用瓦块管理器"""
        tile = self.game_map[y][x]

        # 挖掘前启用接壤金矿脉日志
        reachability_system = get_reachability_system()
        reachability_system.enable_adjacent_vein_logging()

        # 使用瓦块管理器的统一挖掘方法
        result = tile_manager.dig_tile(
            tile, x, y, cost=10, game_state=self.game_state)

        if result['success']:
            if result['gold_discovered'] > 0:
                # 发现金矿脉
                game_logger.info(f"{emoji_manager.MONEY} {result['message']}")
                # 根据文档要求，发现时会有特殊的金色特效和提示音
                self._show_gold_discovery_effect(x, y)
            else:
                # 普通挖掘
                game_logger.info(
                    f"{emoji_manager.PICKAXE} {result['message']}")

            # 挖掘成功后，强制更新可达性以检测新的可到达金矿脉
            reachability_system.update_reachability(
                self.game_map, force_update=True)
        else:
            # 挖掘失败
            game_logger.info(f"❌ 挖掘失败: {result['message']}")

        # 挖掘后禁用接壤金矿脉日志，避免频繁输出
        reachability_system.disable_adjacent_vein_logging()

    def _summon_creature(self, x: int, y: int, creature_type: str):
        """
        召唤生物 - 只能在已挖掘区域召唤

        ⚠️ 已废弃：此函数已被统一放置系统替代
        请使用 self.placement_system.place_entity() 代替
        """
        tile = self.game_map[y][x]

        # 获取生物成本
        cost = 80  # 默认成本
        creature_name = creature_type
        character_data = character_db.get_character(creature_type)
        if character_data:
            cost = character_data.cost if character_data.cost else 80
            creature_name = character_data.name

        # 检查召唤位置是否被占用
        summon_position_occupied = self._check_summon_position_occupied(
            x, y, creature_type, verbose=True)

        # 使用瓦块管理器检查地形
        if (tile_manager.check_tile_passable(tile) and
            len(self.monsters) < GameBalance.max_creatures and
                not summon_position_occupied):

            # 使用ResourceManager检查资源
            resource_manager = get_resource_manager(self)
            if not resource_manager.can_afford(gold_cost=cost):
                gold_info = resource_manager.get_total_gold()
                game_logger.info(
                    f"❌ 召唤失败: 金币不足(需要{cost}金，当前{gold_info.available}金)")
                return

            # 根据生物类型创建不同的实例 - 使用瓦块管理器获取中心坐标
            creature_x, creature_y = tile_manager.get_tile_center_pixel(x, y)

            if creature_type == 'goblin_worker':
                # 创建哥布林苦工专用类
                creature = GoblinWorker(creature_x, creature_y)
                # 设置游戏实例引用，用于获取主基地位置
                creature.game_instance = self
            elif creature_type == 'goblin_engineer':
                # 创建地精工程师专用类
                config = EngineerRegistry.get_config(EngineerType.BASIC)
                creature = Engineer(creature_x, creature_y,
                                    EngineerType.BASIC, config)
                # 设置游戏实例引用，用于获取主基地位置
                creature.game_instance = self
                # 在建筑管理器中注册工程师
                if self.building_manager:
                    self.building_manager.engineers.append(creature)
                    game_logger.info(f"🔨 {creature_name} 已注册为工程师")
            else:
                # 其他生物使用基础类
                creature = Creature(creature_x, creature_y, creature_type)

            # 设置游戏实例引用，用于资源更新
            creature.game_instance = self
            self.monsters.append(creature)

            # 使用ResourceManager消耗资源
            gold_result = resource_manager.consume_gold(cost)
            if gold_result['success']:
                game_logger.info(
                    f"{emoji_manager.MONSTER} 召唤了{creature_name} ({x}, {y})")
            else:
                game_logger.info(f"❌ 资源消耗失败: {gold_result}")
                self.monsters.remove(creature)  # 移除已添加的生物
        else:
            # 失败原因分析
            if not tile_manager.check_tile_passable(tile):
                game_logger.info(f"❌ 召唤失败: 位置({x},{y})不是可通行区域")
            elif len(self.monsters) >= GameBalance.max_creatures:
                game_logger.info(
                    f"❌ 召唤失败: 生物数量已达上限({GameBalance.max_creatures})")
            # 资源检查已在上面处理
            elif summon_position_occupied:
                game_logger.info(f"❌ 召唤失败: 位置({x},{y})已被其他单位占用")

    def _check_summon_position_occupied(self, tile_x: int, tile_y: int, creature_type: str, verbose: bool = False) -> bool:
        """
        检查召唤位置是否被其他单位占用

        ⚠️ 已废弃：此函数已被统一放置系统替代
        请使用 self.placement_system.can_place() 代替

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
        character_data = character_db.get_character(creature_type)
        if character_data:
            creature_size = character_data.size

        # 计算召唤生物的碰撞半径
        summon_radius = creature_size * 0.6  # 使用物理系统的碰撞半径计算方式
        summon_radius = max(5, min(summon_radius, 25))  # 限制范围

        # 检查与现有生物的碰撞
        for existing_creature in self.monsters:
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
                    game_logger.info(
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
                    game_logger.info(
                        f"   🚫 位置被 {hero.type} 占用 (距离: {distance:.1f}, 需要: {required_distance:.1f})")
                return True

        return False

    def _safe_render_text(self, font, text, color, use_emoji_fallback=True):
        """安全渲染文本，使用UnifiedFontManager的safe_render方法"""
        return self.font_manager.safe_render(font, text, color, use_emoji_fallback, self.ui_scale)

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

        game_logger.info(
            f"{emoji_manager.BUILD} 创建起始区域，中心位置: ({center_x}, {center_y})")

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
            dungeon_heart = None
            try:
                dungeon_heart = BuildingRegistry.create_building(
                    BuildingType.DUNGEON_HEART, heart_x, heart_y)
                if dungeon_heart is None:
                    game_logger.error(
                        "❌ 地牢之心创建失败：BuildingRegistry.create_building 返回 None")
                else:
                    game_logger.info(f"✅ 地牢之心创建成功：{dungeon_heart.name}")
            except Exception as e:
                game_logger.error(f"❌ 地牢之心创建失败：{e}")
                dungeon_heart = None

            # 立即设置地牢之心引用，确保ResourceManager可以访问
            self.dungeon_heart = dungeon_heart

            # 将建筑对象添加到建筑管理器（稍后在building_manager初始化后添加）
            # 暂时保存地牢之心引用
            self._pending_dungeon_heart = dungeon_heart

        # 记录地牢之心位置
        self.dungeon_heart_pos = (heart_x, heart_y)
        game_logger.info(f"🏰 地牢之心位置设置为: {self.dungeon_heart_pos}")

        # 初始化可达性系统
        reachability_system = get_reachability_system()
        reachability_system.set_base_position(heart_x, heart_y)
        game_logger.info(f"🏰 可达性系统主基地位置设置为: {heart_x}, {heart_y}")

        # 验证主基地位置是否可通行
        if 0 <= heart_x < self.map_width and 0 <= heart_y < self.map_height:
            base_tile = game_map[heart_y][heart_x]
            is_passable = (hasattr(base_tile, 'type') and base_tile.type in [TileType.GROUND, TileType.ROOM, TileType.GOLD_VEIN]) or \
                (hasattr(base_tile, 'tile_type') and base_tile.tile_type in [TileType.GROUND, TileType.ROOM, TileType.GOLD_VEIN]) or \
                (getattr(base_tile, 'is_dug', False))
            game_logger.info(
                f"🏰 主基地瓦片类型检查: 可通行={is_passable}, 瓦片类型={getattr(base_tile, 'type', getattr(base_tile, 'tile_type', 'unknown'))}")
        else:
            game_logger.error(f"❌ 主基地位置超出地图范围: ({heart_x}, {heart_y})")

        # 创建英雄基地
        self._create_hero_bases(game_map)

        return game_map

    def _create_hero_bases(self, game_map: List[List[Tile]]):
        """在地图边缘创建1-3个英雄基地"""

        # 随机决定创建1-3个基地
        num_bases = random.randint(1, 3)
        game_logger.info(f"{emoji_manager.CASTLE} 创建 {num_bases} 个英雄基地")

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
        game_logger.info(
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
                    # 设置游戏实例引用，用于触发攻击响应
                    hero.game_instance = self
                    self.heroes.append(hero)

                    game_logger.info(
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
                        # 设置游戏实例引用，用于触发攻击响应
                        hero.game_instance = self
                        self.heroes.append(hero)

                        game_logger.info(
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
        game_logger.info(f"✨ 金色光芒从 ({x}, {y}) 闪烁！黄金矿脉被发现！")

    def _build_room(self, x: int, y: int, room_type: str, cost: int):
        """建造房间"""
        tile = self.game_map[y][x]
        if tile.type == TileType.GROUND and not tile.room:
            # 使用ResourceManager检查资源
            resource_manager = get_resource_manager(self)
            if resource_manager.can_afford(gold_cost=cost):
                tile.type = TileType.ROOM
                tile.room = room_type
                gold_result = resource_manager.consume_gold(cost)
                if gold_result['success']:
                    game_logger.info(
                        f"{emoji_manager.BUILD} 建造了{room_type} ({x}, {y})")
                else:
                    game_logger.info(f"❌ 资源消耗失败: {gold_result}")
            else:
                gold_info = resource_manager.get_total_gold()
                game_logger.info(
                    f"❌ 建造失败: 金币不足(需要{cost}金，当前{gold_info.available}金)")

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
        }

        # 默认颜色
        return building_colors.get(building_type, GameConstants.COLORS['background'])

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
        if self.combat_system:
            self.combat_system.handle_unit_attacked_response(
                attacker, target, damage)

    def _cleanup_dead_units(self):
        """清理死亡的单位"""
        # 清理死亡的生物
        dead_creatures = [c for c in self.monsters if c.health <= 0]
        for creature in dead_creatures:
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
            self.monsters.remove(creature)
            game_logger.info(f"💀 {creature.type} 死亡并被移除")

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

    def _spawn_hero(self):
        """生成英雄 - 在英雄基地附近刷新"""
        if random.random() < GameBalance.hero_spawn_rate:
            if not self.hero_bases:
                game_logger.info("❌ 没有英雄基地，无法生成英雄")
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
                available_heroes = list(
                    character_db.get_all_heroes().keys())
                hero_type = random.choice(available_heroes)
                hero_data = character_db.get_character(hero_type)
                hero_name = hero_data.name if hero_data else hero_type

                hero = Hero(spawn_x * self.tile_size + self.tile_size // 2,
                            spawn_y * self.tile_size + self.tile_size // 2, hero_type)
                # 设置游戏实例引用，用于触发攻击响应
                hero.game_instance = self
                self.heroes.append(hero)
                game_logger.info(
                    f"{emoji_manager.COMBAT} {hero_name}从基地 ({base_x}, {base_y}) 入侵！")
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

        # 更新生物（期望秒）
        for creature in self.monsters[:]:
            creature.update(delta_seconds, self.game_map,
                            self.monsters, self.heroes, self.effect_manager, self.building_manager)

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

        # 更新建筑系统
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

        # 生成英雄
        self._spawn_hero()

        # 资源生成 - 使用累积器确保整数
        treasury_count = sum(1 for row in self.game_map for tile in row
                             if tile.room == 'treasury')

        # 黄金累积 - 使用ResourceManager
        self.gold_accumulator += treasury_count * \
            GameBalance.gold_per_second_per_treasury * delta_time * 0.001
        if self.gold_accumulator >= 1.0:
            gold_to_add = int(self.gold_accumulator)
            resource_manager = get_resource_manager(self)
            resource_manager.add_gold(gold_to_add, self.dungeon_heart)
            self.gold_accumulator -= gold_to_add

        # 法力增长现在由地牢之心处理，不再在主循环中处理

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
        MovementSystem.render_target_lines(
            self.screen, self.camera_x, self.camera_y, self.ui_scale)

        # 渲染生物
        self._render_monsters()

        # 渲染英雄
        self._render_heroes()

        # 工程师状态指示器现在由统一的生物状态指示器系统处理

        # 渲染特效系统
        if self.effect_manager:
            self.screen = self.effect_manager.render(
                self.screen, self.ui_scale, self.camera_x, self.camera_y)

        # 渲染击退动画
        if self.knockback_animation:
            self.knockback_animation.render(
                self.screen, self.camera_x, self.camera_y, self.ui_scale)

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
            goblin_engineer_count = sum(1 for creature in self.monsters
                                        if creature.type == 'goblin_engineer')
            self.building_ui.set_goblin_engineer_count(goblin_engineer_count)
            self.building_ui.render(
                self.screen, self.building_manager, self.game_state, self.ui_scale)

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
                # 应用UI缩放
                scaled_tile_size = int(self.tile_size * self.ui_scale)
                screen_x = int(
                    (x * self.tile_size - self.camera_x) * self.ui_scale)
                screen_y = int(
                    (y * self.tile_size - self.camera_y) * self.ui_scale)

                # 只渲染屏幕内的瓦片
                if (screen_x + scaled_tile_size < 0 or screen_x > GameConstants.WINDOW_WIDTH or
                        screen_y + scaled_tile_size < 0 or screen_y > GameConstants.WINDOW_HEIGHT):
                    continue

                # 绘制特殊标识和状态（优先处理特殊建筑）
                elif tile.room_type and tile.room_type.startswith('hero_base_'):
                    # 绘制英雄基地 - 正义风格的金蓝色设计
                    # 背景：渐变蓝色
                    base_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                               scaled_tile_size - 2, scaled_tile_size - 2)
                    pygame.draw.rect(self.screen, (25, 25, 112),
                                     base_bg_rect)  # 深蓝色背景

                    # 边框：双层边框效果
                    outer_border = pygame.Rect(
                        screen_x, screen_y, scaled_tile_size, scaled_tile_size)
                    inner_border = pygame.Rect(
                        screen_x + 2, screen_y + 2, scaled_tile_size - 4, scaled_tile_size - 4)
                    pygame.draw.rect(self.screen, (100, 149, 237),
                                     outer_border, 2)  # 外边框：天蓝色
                    pygame.draw.rect(self.screen, (255, 215, 0),
                                     inner_border, 1)  # 内边框：金色

                    # 中心装饰：城堡符号
                    base_text = self._safe_render_text(
                        self.font, emoji_manager.CASTLE, (255, 255, 255))  # 白色城堡
                    base_rect = base_text.get_rect(center=(
                        screen_x + scaled_tile_size // 2,
                        screen_y + scaled_tile_size // 2))
                    self.screen.blit(base_text, base_rect)

                    # 正义光环：十字装饰
                    center_x = screen_x + scaled_tile_size // 2
                    center_y = screen_y + scaled_tile_size // 2
                    # 垂直十字
                    pygame.draw.rect(self.screen, (255, 215, 0),
                                     (center_x - 1, center_y - 4, 2, 8))
                    # 水平十字
                    pygame.draw.rect(self.screen, (255, 215, 0),
                                     (center_x - 4, center_y - 1, 8, 2))

                    # 四个角的装饰：小星星
                    corner_size = max(1, int(2 * self.ui_scale))
                    corners = [
                        (screen_x + 1, screen_y + 1),  # 左上
                        (screen_x + scaled_tile_size - 3, screen_y + 1),  # 右上
                        (screen_x + 1, screen_y + scaled_tile_size - 3),  # 左下
                        (screen_x + scaled_tile_size - 3,
                         screen_y + scaled_tile_size - 3)  # 右下
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
                                 screen_y, scaled_tile_size, scaled_tile_size))

                # 绘制边框
                pygame.draw.rect(self.screen, (50, 50, 50), (screen_x,
                                 screen_y, scaled_tile_size, scaled_tile_size), 1)

                # 绘制金矿和其他特殊瓦片
                if tile.is_gold_vein and tile.gold_amount > 0:
                    self._render_gold_mine_ui(
                        screen_x, screen_y, tile, scaled_tile_size)
                elif tile.is_gold_vein and tile.gold_amount <= 0:
                    # 枯竭金矿显示为灰色
                    pygame.draw.rect(self.screen, (100, 100, 100),
                                     (screen_x, screen_y, scaled_tile_size, scaled_tile_size))

    def _render_building_tile(self, tile, screen_x: int, screen_y: int, x: int, y: int):
        """渲染建筑瓦片 - 统一处理完成和未完成建筑"""

        # 计算缩放后的瓦片大小
        scaled_tile_size = int(self.tile_size * self.ui_scale)

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
                    self.screen, start_screen_x, start_screen_y, self.tile_size, tile, self.ui_scale)

                # 获取建筑对象并渲染状态条（血条已在_render_2x2_dungeon_heart内部渲染）
                building = self._get_building_at_position(x, y)
                if building:
                    # 渲染状态条
                    self.building_ui.render_building_status_bar(
                        self.screen, start_screen_x, start_screen_y, self.tile_size, tile, building, self.ui_scale)

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
            building_surface = pygame.Surface(
                (scaled_tile_size, scaled_tile_size))
            building_surface.set_alpha(128)  # 50%透明度

            # 获取建筑对象并同步生命值
            building = self._get_building_at_position(x, y)
            self._sync_building_construction_health(building, tile)

            # 使用建筑对象自己的渲染方法
            if building:
                building.render(building_surface, 0, 0, self.tile_size,
                                self.font_manager, self.building_ui, self.ui_scale)
                # 将半透明表面绘制到主屏幕
                self.screen.blit(building_surface, (screen_x, screen_y))
                # 渲染生命条
                building.render_health_bar(
                    self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui, self.ui_scale)

                # 渲染状态条
                building.render_status_bar(
                    self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui, self.ui_scale)
            else:
                game_logger.error("❌ 建筑对象不可用，无法渲染建筑")

            # 渲染建筑状态高亮（包括血量条）
            self._render_building_status_overlay(
                tile, screen_x, screen_y, x, y)

        else:
            # 完成的建筑 - 正常渲染
            building = self._get_building_at_position(x, y)
            if building:
                # 使用建筑对象自己的渲染方法
                building.render(self.screen, screen_x, screen_y,
                                self.tile_size, self.font_manager, self.building_ui, self.ui_scale)
                # 渲染生命条
                building.render_health_bar(
                    self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui, self.ui_scale)

                # 渲染状态条
                building.render_status_bar(
                    self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui, self.ui_scale)
            else:
                game_logger.error("❌ 建筑对象不可用，无法渲染建筑")

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

        # 地牢之心使用通用建筑血条，不需要特殊处理

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
            game_logger.error("❌ 建筑对象缺少get_status_for_indicator方法，无法渲染状态指示器")

    def _render_gold_mine_ui(self, screen_x: int, screen_y: int, tile, scaled_tile_size: int = None):
        """渲染金矿UI - 现代化设计"""
        if scaled_tile_size is None:
            scaled_tile_size = self.tile_size
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
            screen_x + 1, screen_y + 1, scaled_tile_size - 2, scaled_tile_size - 2)
        pygame.draw.rect(self.screen, base_color, main_rect)

        # 绘制发光效果
        glow_manager = get_glow_manager()
        glow_manager.render_effect_glow(
            self.screen, 'normal',
            (screen_x + scaled_tile_size // 2,
             screen_y + scaled_tile_size // 2),
            glow_color,
            radius=scaled_tile_size // 2 - 3, ui_scale=1.0
        )

        # 绘制边框
        pygame.draw.rect(self.screen, border_color, main_rect, 2)

        # 绘制金矿图标 - 使用更现代的符号
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2

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
        bar_width = scaled_tile_size - 8
        bar_height = max(1, int(3 * self.ui_scale))
        bar_x = screen_x + 4
        bar_y = screen_y + scaled_tile_size - 8

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
                    self.screen, screen_x, screen_y, self.tile_size, tile.miners_count, self.ui_scale)
            else:
                game_logger.error("❌ StatusIndicator系统不可用，无法渲染挖掘状态")

    def _render_monsters(self):
        """渲染生物"""
        for creature in self.monsters:
            screen_x = int((creature.x - self.camera_x) * self.ui_scale)
            screen_y = int((creature.y - self.camera_y) * self.ui_scale)

            # 绘制生物
            scaled_size = int(creature.size * self.ui_scale)
            pygame.draw.circle(self.screen, creature.color,
                               (screen_x, screen_y), scaled_size // 2)

            # 绘制状态指示器
            self._render_creature_status_indicator(
                creature, screen_x, screen_y)

            # 为哥布林苦工绘制特殊标识和携带金币信息
            if creature.type == 'goblin_worker':
                self._render_goblin_worker_special(
                    creature, screen_x, screen_y)

            # 为工程师绘制携带金币信息
            elif creature.type == 'goblin_engineer':
                self._render_engineer_gold(creature, screen_x, screen_y)

            # 绘制血条
            if creature.health < creature.max_health:
                bar_width = scaled_size
                bar_height = max(1, int(3 * self.ui_scale))
                health_ratio = creature.health / creature.max_health
                bar_offset = int(25 * self.ui_scale)

                # 红色背景
                pygame.draw.rect(self.screen, (255, 0, 0),
                                 (screen_x - bar_width//2, screen_y - bar_offset, bar_width, bar_height))
                # 绿色血量
                pygame.draw.rect(self.screen, (0, 255, 0),
                                 (screen_x - bar_width//2, screen_y - bar_offset, bar_width * health_ratio, bar_height))

    def _render_heroes(self):
        """渲染英雄"""
        for hero in self.heroes:
            screen_x = int((hero.x - self.camera_x) * self.ui_scale)
            screen_y = int((hero.y - self.camera_y) * self.ui_scale)

            # 绘制英雄
            scaled_size = int(hero.size * self.ui_scale)
            pygame.draw.rect(self.screen, hero.color,
                             (screen_x - scaled_size//2, screen_y - scaled_size//2, scaled_size, scaled_size))

            # 移除了所有英雄状态图标显示

            # 绘制血条
            if hero.health < hero.max_health:
                bar_width = scaled_size
                bar_height = max(1, int(3 * self.ui_scale))
                health_ratio = hero.health / hero.max_health
                bar_offset = int(25 * self.ui_scale)

                pygame.draw.rect(self.screen, (255, 0, 0),
                                 (screen_x - bar_width//2, screen_y - bar_offset, bar_width, bar_height))
                pygame.draw.rect(self.screen, (0, 255, 0),
                                 (screen_x - bar_width//2, screen_y - bar_offset, bar_width * health_ratio, bar_height))

    def _render_creature_status_indicator(self, creature, screen_x, screen_y):
        """渲染生物状态指示器"""
        # 使用统一的状态指示器系统
        if self.status_indicator:
            self.status_indicator.render(
                self.screen, screen_x, screen_y, creature.size, creature.state, self.ui_scale)
        else:
            # StatusIndicator系统不可用，记录错误日志
            game_logger.error("❌ StatusIndicator系统不可用，无法渲染生物状态指示器")

    def _render_goblin_worker_special(self, creature, screen_x, screen_y):
        """渲染哥布林苦工特殊效果"""
        # 渲染苦工携带的金币数 - 使用统一API和字体管理器
        if hasattr(creature, 'carried_gold') and creature.carried_gold > 0:
            self.status_indicator.render_carried_gold(
                self.screen, screen_x, screen_y,
                int(creature.size * self.ui_scale),
                creature.carried_gold, self.ui_scale,
                self.font_manager.get_font(16), self._cached_ui_texts, self.font_manager)

    def _render_engineer_gold(self, creature, screen_x, screen_y):
        """渲染工程师携带金币信息"""
        # 渲染工程师携带的金币数 - 使用统一API和字体管理器
        if hasattr(creature, 'carried_gold') and creature.carried_gold > 0:
            self.status_indicator.render_carried_gold(
                self.screen, screen_x, screen_y,
                int(creature.size * self.ui_scale),
                creature.carried_gold, self.ui_scale,
                self.font_manager.get_font(16), self._cached_ui_texts, self.font_manager)

    def _render_mouse_cursor(self):
        """渲染鼠标光标高亮 - 使用统一放置系统"""
        if (self.build_mode != BuildMode.NONE and
            self.mouse_world_x >= 0 and self.mouse_world_y >= 0 and
                self.mouse_world_x < self.map_width and self.mouse_world_y < self.map_height):

            screen_x = int(
                (self.mouse_world_x * self.tile_size - self.camera_x) * self.ui_scale)
            screen_y = int(
                (self.mouse_world_y * self.tile_size - self.camera_y) * self.ui_scale)

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
            elif self.placement_system:
                # 使用统一放置系统检查
                entity_id = None
                if self.build_mode == BuildMode.SUMMON and self.selected_monster_type:
                    entity_id = self.selected_monster_type
                elif self.build_mode == BuildMode.SUMMON_LOGISTICS and hasattr(self, 'selected_logistics_type'):
                    entity_id = self.selected_logistics_type
                elif self.build_mode == BuildMode.BUILD_SPECIFIC and hasattr(self, 'selected_building_type'):
                    entity_id = f"building_{self.selected_building_type.value}"

                if entity_id:
                    can_place, reason = self.placement_system.can_place(
                        entity_id, self.mouse_world_x, self.mouse_world_y
                    )
                    can_build = can_place

                    # 根据检查结果设置高亮颜色
                    if can_place:
                        highlight_color = (0, 255, 255)  # 青色：可以放置
                    else:
                        if "地形" in reason or "挖掘" in reason:
                            # 红色：地形问题
                            highlight_color = GameConstants.COLORS['highlight_red']
                        elif "占用" in reason:
                            highlight_color = (255, 165, 0)  # 橙色：位置被占用
                        elif "金币" in reason:
                            highlight_color = (255, 255, 0)  # 黄色：资源不足
                        else:
                            # 红色：其他问题
                            highlight_color = GameConstants.COLORS['highlight_red']
            else:
                game_logger.error("❌ 统一放置系统不可用，无法检查放置位置")
                can_build = False
                highlight_color = GameConstants.COLORS['highlight_red']

            # 绘制高亮
            scaled_tile_size = int(self.tile_size * self.ui_scale)
            pygame.draw.rect(self.screen, highlight_color,
                             (screen_x, screen_y, scaled_tile_size, scaled_tile_size), 3)

            # 绘制半透明覆盖
            overlay = pygame.Surface((scaled_tile_size, scaled_tile_size))
            overlay.set_alpha(80)
            overlay.fill(highlight_color)
            self.screen.blit(overlay, (screen_x, screen_y))

    def _render_ui(self):
        """渲染用户界面"""
        # 使用美化的UI渲染器
        self.game_ui.render_resource_panel(self.game_state, len(
            self.monsters), GameBalance.max_creatures, self.building_manager, self.ui_scale)
        self.game_ui.render_build_panel(
            self.build_mode, self.game_state, self.ui_scale)
        self.game_ui.render_status_panel(
            self.mouse_world_x, self.mouse_world_y,
            self.camera_x, self.camera_y,
            self.build_mode, self.debug_mode, self.ui_scale
        )
        self.game_ui.render_game_info_panel(
            self.game_state.wave_number, self.ui_scale)

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
            self.font, emoji_manager.HAMMER, (255, 102, 0), False, self.ui_scale)
        text_surface = self.font_manager.safe_render(
            self.font, " 建造选项", (255, 102, 0), False, self.ui_scale)

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
                self.small_font, number, color, False, self.ui_scale)
            emoji_surface = self.font_manager.safe_render(
                self.small_font, emoji, color, False, self.ui_scale)
            text_surface = self.font_manager.safe_render(
                self.small_font, text, color, False, self.ui_scale)

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
            f"相机位置: ({int(self.camera_x)}, {int(self.camera_y)})",
            f"UI放大倍数: {self.ui_scale}x"
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
            c for c in self.monsters if c.type == 'goblin_worker']
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
            f"金币储量: {int(self.dungeon_heart.stored_gold) if self.dungeon_heart else 0}",
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
                # 使用状态指示器系统获取颜色
                if self.status_indicator:
                    state_color = self.status_indicator.get_color(worker.state)
                else:
                    # StatusIndicator系统不可用，使用默认颜色
                    state_color = (255, 255, 255)  # 白色

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
                    game_logger.info(f"🏗️ 选择了建筑: {selected_building.value}")
                continue  # 事件已被建筑UI处理

            # 让怪物选择UI先处理事件
            if self.monster_selection_ui.handle_event(event, character_db):
                # 检查是否有选中的怪物
                if self.monster_selection_ui.selected_monster:
                    self.build_mode = BuildMode.SUMMON
                    self.selected_monster_type = self.monster_selection_ui.selected_monster
                    # 清空UI中的选择，避免重复处理
                    self.monster_selection_ui.selected_monster = None
                    game_logger.info(
                        f"🎯 选择了怪物: {self.selected_monster_type}，进入召唤模式")
                continue  # 事件已被怪物选择UI处理

            # 让后勤召唤UI处理事件
            if self.logistics_selection_ui.handle_event(event, character_db):
                # 检查是否有选中的后勤单位
                selected_logistics = self.logistics_selection_ui.get_selected_logistics()
                if selected_logistics:
                    self.build_mode = BuildMode.SUMMON_LOGISTICS
                    self.selected_logistics_type = selected_logistics
                    game_logger.info(f"🎒 选择了后勤单位: {selected_logistics}")
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
                    self._open_ui_window("bestiary")
                elif event.key == pygame.K_p:
                    # 切换调试模式
                    self.debug_mode = not self.debug_mode
                    game_logger.info(
                        f"🐛 调试模式: {'开启' if self.debug_mode else '关闭'}")

                # 处理相机输入
                elif self.handle_camera_input(event):
                    pass  # 相机输入已处理
                # 处理UI缩放输入
                elif self.handle_ui_scale_input(event):
                    pass  # UI缩放输入已处理

    def run(self):
        """运行游戏主循环"""
        game_logger.info(f"{emoji_manager.GAME} 游戏开始运行...")
        game_logger.info(f"{emoji_manager.TARGET} 控制说明:")
        game_logger.info("  - 1键: 挖掘")
        game_logger.info("  - 2键: 建筑面板 (建造各种建筑)")
        game_logger.info("  - 4键: 召唤怪物 (弹出选择界面)")
        game_logger.info("  - 5键: 后勤召唤 (地精工程师/哥布林苦工)")
        game_logger.info("  - 鼠标左键: 执行建造")
        game_logger.info("  - 鼠标右键: 取消建造模式")
        game_logger.info("  - WASD: 移动相机")
        game_logger.info("  - +/-: 调整UI放大倍数")
        game_logger.info("  - 0键: 重置UI放大倍数")
        game_logger.info("  - ESC: 取消建造模式")
        game_logger.info("  - B键: 打开/关闭角色图鉴")
        game_logger.info("  - TAB键: 统计面板 (查看详细统计)")
        game_logger.info("  - 关闭窗口: 退出游戏")
        game_logger.info("")

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

        game_logger.info("🛑 游戏结束")
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
                # 检查是否在2x2范围内（使用瓦片坐标）
                if (building.tile_x <= x < building.tile_x + 2 and
                        building.tile_y <= y < building.tile_y + 2):
                    return building
            else:
                # 普通建筑：精确匹配坐标（使用瓦片坐标）
                if building.tile_x == x and building.tile_y == y:
                    return building

        return None

    # ==================== 统一API接口 ====================

    def set_ui_scale(self, scale: float) -> bool:
        """
        设置UI放大倍数 - 统一API接口

        Args:
            scale: 放大倍数，1.0为原始大小，2.0为放大2倍

        Returns:
            bool: 是否成功设置
        """
        if scale <= 0:
            game_logger.info("❌ UI放大倍数必须大于0")
            return False

        # 限制在合理范围内
        scale = max(self.min_ui_scale, min(scale, self.max_ui_scale))

        old_scale = self.ui_scale
        self.ui_scale = scale

        # 更新放置系统的UI缩放倍数
        if self.placement_system:
            self.placement_system.update_ui_scale(scale)

        game_logger.info(f"🔍 UI放大倍数已更新: {old_scale}x -> {scale}x")
        return True

    def get_ui_scale(self) -> float:
        """
        获取当前UI放大倍数 - 统一API接口

        Returns:
            float: 当前UI放大倍数
        """
        return self.ui_scale

    def adjust_ui_scale(self, delta: float) -> bool:
        """
        调整UI放大倍数 - 统一API接口

        Args:
            delta: 调整量，正数为放大，负数为缩小

        Returns:
            bool: 是否成功调整
        """
        new_scale = self.ui_scale + delta
        return self.set_ui_scale(new_scale)

    def reset_ui_scale(self) -> bool:
        """
        重置UI放大倍数到默认值 - 统一API接口

        Returns:
            bool: 是否成功重置
        """
        return self.set_ui_scale(1.0)

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
            f"🎯 相机移动: ({dx}, {dy}) -> 新位置: ({self.camera_x}, {self.camera_y})")
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
        game_logger.info(f"🎯 相机位置设置为: ({x}, {y})")
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
        self.camera_x = world_x - GameConstants.WINDOW_WIDTH // 2
        self.camera_y = world_y - GameConstants.WINDOW_HEIGHT // 2
        game_logger.info(
            f"🎯 相机居中到世界坐标: ({world_x}, {world_y}) -> 相机位置: ({self.camera_x}, {self.camera_y})")
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
            # WASD相机控制 - 增强的输入法兼容性检测
            # 根据UI缩放倍数调整移动速度，保持视觉一致性
            base_speed = 50
            scaled_speed = base_speed / self.ui_scale  # 缩放倍数越大，移动速度越慢

            if self._is_key_pressed(event, ['w', 'W']):
                self.move_camera(0, -scaled_speed)
                return True
            elif self._is_key_pressed(event, ['s', 'S']):
                self.move_camera(0, scaled_speed)
                return True
            elif self._is_key_pressed(event, ['a', 'A']):
                self.move_camera(-scaled_speed, 0)
                return True
            elif self._is_key_pressed(event, ['d', 'D']):
                self.move_camera(scaled_speed, 0)
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
                self.adjust_ui_scale(0.5)
                return True
            elif event.key == pygame.K_MINUS:
                # 缩小UI (按-键)
                self.adjust_ui_scale(-0.5)
                return True
            elif event.key == pygame.K_0:
                # 重置UI放大倍数 (按0键)
                self.reset_ui_scale()
                return True
        return False


def main():
    """主函数"""

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
            game_logger.info("✅ Windows编码设置完成")
        except Exception as e:
            try:
                # 如果UTF-8失败，尝试GBK编码
                locale.setlocale(locale.LC_ALL, 'zh_CN.GBK')
                game_logger.info("⚠️ 使用GBK编码")
            except:
                game_logger.info("⚠️ 编码设置失败，使用系统默认")
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

    # 模块导入已在顶部处理
    game_logger.info("🏗️ 建筑系统已加载")
    game_logger.info("⚔️ 战斗系统已加载")
    game_logger.info("🎯 统一放置系统已加载")

    try:
        # 检查pygame是否可用
        game_logger.info(f"{emoji_manager.SEARCH} 检查pygame依赖...")
        pygame.mixer.quit()  # 测试pygame
        game_logger.info(f"{emoji_manager.CHECK} pygame可用")

    except ImportError as e:
        if 'pygame' in str(e).lower():
            game_logger.info("❌ 缺少pygame库")
            game_logger.info("🔧 安装方法:")
            game_logger.info("   pip install pygame")
            game_logger.info("")
            input("按Enter键退出...")
            return
        else:
            game_logger.info(f"❌ 导入错误: {e}")
            input("按Enter键退出...")
            return

    # 创建并运行游戏
    try:
        game = WarForTheOverworldGame()
        game.run()
    except Exception as e:
        game_logger.info(f"❌ 游戏运行失败: {e}")
        input("按Enter键退出...")


if __name__ == "__main__":
    main()
