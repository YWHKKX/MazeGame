#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一放置系统
整合建造、怪物召唤、后勤召唤的API功能
"""

from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass

from src.core.enums import TileType, BuildMode
from src.entities.building import BuildingType, BuildingRegistry
from src.entities.creature import Creature
from src.entities.monster.goblin_worker import GoblinWorker
from src.entities.monster.goblin_engineer import Engineer, EngineerType, EngineerRegistry
from src.entities.monster.orc_warrior import OrcWarrior
from src.managers.tile_manager import tile_manager
from src.managers.resource_consumption_manager import get_resource_consumption_manager
from src.utils.logger import game_logger


class PlacementType(Enum):
    """放置类型枚举"""
    BUILDING = "building"
    CREATURE = "creature"
    LOGISTICS = "logistics"


@dataclass
class PlacementResult:
    """放置结果数据类"""
    success: bool
    message: str
    entity: Optional[Any] = None
    cost: int = 0
    position: Optional[Tuple[int, int]] = None


@dataclass
class PlacementConfig:
    """放置配置数据类"""
    placement_type: PlacementType
    entity_type: str
    cost: int
    requires_dug: bool = True
    requires_passable: bool = True
    check_occupancy: bool = True
    max_count: Optional[int] = None
    size: int = 15
    resource_type: str = 'gold'  # 'gold' 或 'mana'


class PlacementSystem:
    """统一放置系统"""

    def __init__(self, game_instance):
        """
        初始化放置系统

        Args:
            game_instance: 游戏实例引用
        """
        self.game_instance = game_instance

        # 放置配置映射
        self.placement_configs = self._initialize_placement_configs()

        # UI缩放倍数（从游戏实例获取）
        self.ui_scale = getattr(game_instance, 'ui_scale', 1.0)

    def update_ui_scale(self, new_scale: float):
        """
        更新UI缩放倍数

        Args:
            new_scale: 新的UI缩放倍数
        """
        self.ui_scale = new_scale

    def _initialize_placement_configs(self) -> Dict[str, PlacementConfig]:
        """初始化放置配置"""
        configs = {}

        # 建筑配置 - 需要从BuildingRegistry获取配置信息
        try:
            for building_type in BuildingType:
                building_config = BuildingRegistry.get_config(building_type)
                if building_config:
                    configs[f"building_{building_type.value}"] = PlacementConfig(
                        placement_type=PlacementType.BUILDING,
                        entity_type=building_type.value,
                        cost=building_config.cost_gold,
                        requires_dug=True,
                        requires_passable=True,
                        check_occupancy=True,
                        max_count=None,
                        size=32
                    )
        except ImportError:
            # 如果BuildingRegistry不可用，使用默认配置
            for building_type in BuildingType:
                configs[f"building_{building_type.value}"] = PlacementConfig(
                    placement_type=PlacementType.BUILDING,
                    entity_type=building_type.value,
                    cost=100,  # 默认成本
                    requires_dug=True,
                    requires_passable=True,
                    check_occupancy=True,
                    max_count=None,
                    size=32
                )

        # 怪物配置 - 现在消耗魔力而不是金币
        monster_configs = {
            'imp': PlacementConfig(PlacementType.CREATURE, 'imp', 100, True, True, True, 50, 15, 'mana'),
            'gargoyle': PlacementConfig(PlacementType.CREATURE, 'gargoyle', 200, True, True, True, 30, 20, 'mana'),
            'hellhound': PlacementConfig(PlacementType.CREATURE, 'hellhound', 250, True, True, True, 25, 18, 'mana'),
            'fire_salamander': PlacementConfig(PlacementType.CREATURE, 'fire_salamander', 300, True, True, True, 20, 22, 'mana'),
            'succubus': PlacementConfig(PlacementType.CREATURE, 'succubus', 450, True, True, True, 15, 25, 'mana'),
            'shadow_mage': PlacementConfig(PlacementType.CREATURE, 'shadow_mage', 400, True, True, True, 18, 20, 'mana'),
            'tree_guardian': PlacementConfig(PlacementType.CREATURE, 'tree_guardian', 350, True, True, True, 12, 30, 'mana'),
            'stone_golem': PlacementConfig(PlacementType.CREATURE, 'stone_golem', 600, True, True, True, 8, 35, 'mana'),
            'shadow_lord': PlacementConfig(PlacementType.CREATURE, 'shadow_lord', 800, True, True, True, 5, 40, 'mana'),
            'bone_dragon': PlacementConfig(PlacementType.CREATURE, 'bone_dragon', 1000, True, True, True, 3, 50, 'mana'),
            'orc_warrior': PlacementConfig(PlacementType.CREATURE, 'orc_warrior', 120, True, True, True, 20, 18, 'mana'),
        }

        # 后勤单位配置 - 消耗金币
        logistics_configs = {
            'goblin_worker': PlacementConfig(PlacementType.LOGISTICS, 'goblin_worker', 50, True, True, True, 100, 12, 'gold'),
            'goblin_engineer': PlacementConfig(PlacementType.LOGISTICS, 'goblin_engineer', 100, True, True, True, 50, 15, 'gold'),
        }

        # 英雄配置
        hero_configs = {
            'knight': PlacementConfig(PlacementType.CREATURE, 'knight', 200, True, True, True, 10, 20),
            'archer': PlacementConfig(PlacementType.CREATURE, 'archer', 150, True, True, True, 15, 18),
            'mage': PlacementConfig(PlacementType.CREATURE, 'mage', 180, True, True, True, 12, 16),
        }

        configs.update(monster_configs)
        configs.update(logistics_configs)
        configs.update(hero_configs)

        return configs

    def can_place(self, entity_id: str, x: int, y: int) -> Tuple[bool, str]:
        """
        检查是否可以放置实体

        Args:
            entity_id: 实体ID (如 "building_treasury", "imp", "goblin_worker")
            x, y: 瓦片坐标

        Returns:
            Tuple[bool, str]: (是否可以放置, 原因消息)
        """
        # 获取配置
        config = self.placement_configs.get(entity_id)
        if not config:
            return False, f"未知的实体类型: {entity_id}"

        # 检查地图边界
        if not self._is_within_map_bounds(x, y):
            return False, f"位置({x}, {y})超出地图边界"

        # 获取瓦片
        tile = self.game_instance.game_map[y][x]

        # 检查地形条件
        if config.requires_dug and not tile.is_dug:
            return False, f"位置({x}, {y})需要先挖掘"

        if config.requires_passable and not tile_manager.check_tile_passable(tile):
            return False, f"位置({x}, {y})不是可通行区域"

        # 检查资源（使用资源消耗管理器）
        resource_manager = get_resource_consumption_manager(self.game_instance)

        gold_cost = config.cost if config.resource_type == 'gold' else 0
        mana_cost = config.cost if config.resource_type == 'mana' else 0

        can_afford, reason = resource_manager.can_afford(gold_cost, mana_cost)
        if not can_afford:
            return False, reason

        # 检查数量限制
        if config.max_count and not self._check_count_limit(config):
            return False, f"数量已达上限({config.max_count})"

        # 检查位置占用
        if config.check_occupancy and self._is_position_occupied(x, y, config):
            return False, f"位置({x}, {y})已被其他单位占用"

        return True, "可以放置"

    def place_entity(self, entity_id: str, x: int, y: int) -> PlacementResult:
        """
        放置实体

        Args:
            entity_id: 实体ID
            x, y: 瓦片坐标

        Returns:
            PlacementResult: 放置结果
        """
        # 检查是否可以放置
        can_place, message = self.can_place(entity_id, x, y)
        if not can_place:
            return PlacementResult(success=False, message=message)

        # 获取配置
        config = self.placement_configs[entity_id]

        try:
            # 根据类型执行放置
            if config.placement_type == PlacementType.BUILDING:
                return self._place_building(entity_id, x, y, config)
            elif config.placement_type == PlacementType.CREATURE:
                return self._place_creature(entity_id, x, y, config)
            elif config.placement_type == PlacementType.LOGISTICS:
                return self._place_logistics(entity_id, x, y, config)
            else:
                return PlacementResult(success=False, message=f"不支持的放置类型: {config.placement_type}")

        except Exception as e:
            return PlacementResult(success=False, message=f"放置失败: {str(e)}")

    def _place_building(self, entity_id: str, x: int, y: int, config: PlacementConfig) -> PlacementResult:
        """放置建筑"""
        # 从entity_id中提取建筑类型
        building_type_str = entity_id.replace("building_", "")
        building_type = BuildingType(building_type_str)

        # 使用建筑管理器检查并建造
        can_build_result = self.game_instance.building_manager.can_build(
            building_type, x, y, self.game_instance.game_state, self.game_instance.game_map
        )

        if not can_build_result['can_build']:
            return PlacementResult(success=False, message=can_build_result['message'])

        # 开始建造
        build_result = self.game_instance.building_manager.start_construction(
            building_type, x, y, self.game_instance.game_state, self.game_instance.game_map
        )

        if build_result['started']:
            # 新机制：放置阶段不扣除资源，工程师建造期间提供金币
            return PlacementResult(
                success=True,
                message=f"开始建造 {build_result['building'].name} 在 ({x}, {y})，等待工程师建造（成本：{config.cost}金币）",
                entity=build_result['building'],
                cost=config.cost,
                position=(x, y)
            )
        else:
            return PlacementResult(success=False, message=build_result['message'])

    def _place_creature(self, entity_id: str, x: int, y: int, config: PlacementConfig) -> PlacementResult:
        """放置怪物"""
        # 获取中心像素坐标（不使用UI缩放，因为实体坐标是基础坐标）
        base_x, base_y = tile_manager.get_tile_center_pixel(x, y)
        creature_x = base_x
        creature_y = base_y

        # 创建怪物实例
        if hasattr(self.game_instance, 'character_db') and self.game_instance.character_db:
            from src.utils.logger import game_logger
            game_logger.info(
                f"🏗️ PlacementSystem 调用 character_db.create_character: {entity_id}")
            creature = self.game_instance.character_db.create_character(
                entity_id, creature_x, creature_y)
            game_logger.info(
                f"🏗️ PlacementSystem 创建结果: {type(creature).__name__}")
        else:
            # 回退到简单创建
            from src.utils.logger import game_logger
            game_logger.info(f"🏗️ PlacementSystem 回退到 Creature: {entity_id}")
            creature = Creature(creature_x, creature_y, entity_id)

        # 设置游戏实例引用
        creature.game_instance = self.game_instance

        # 添加到游戏世界
        self.game_instance.monsters.append(creature)

        # 使用资源消耗管理器扣除资源
        resource_manager = get_resource_consumption_manager(self.game_instance)

        gold_cost = config.cost if config.resource_type == 'gold' else 0
        mana_cost = config.cost if config.resource_type == 'mana' else 0

        consumption_result = resource_manager.consume_resources(
            gold_cost, mana_cost)
        if not consumption_result.success:
            # 如果资源消耗失败，移除已创建的生物
            self.game_instance.monsters.remove(creature)
            return PlacementResult(success=False, message=consumption_result.message)

        return PlacementResult(
            success=True,
            message=f"召唤了{entity_id}在 ({x}, {y})",
            entity=creature,
            cost=config.cost,
            position=(x, y)
        )

    def _place_logistics(self, entity_id: str, x: int, y: int, config: PlacementConfig) -> PlacementResult:
        """放置后勤单位"""
        # 获取中心像素坐标（不使用UI缩放，因为实体坐标是基础坐标）
        base_x, base_y = tile_manager.get_tile_center_pixel(x, y)
        unit_x = base_x
        unit_y = base_y

        # 创建后勤单位实例
        if entity_id == 'goblin_worker':
            unit = GoblinWorker(unit_x, unit_y)
            # 设置游戏实例引用
            unit.game_instance = self.game_instance
            self.game_instance.monsters.append(unit)
        elif entity_id == 'goblin_engineer':
            # 创建基础工程师
            config = EngineerRegistry.get_config(EngineerType.BASIC)
            unit = Engineer(unit_x, unit_y, EngineerType.BASIC, config)
            # 设置游戏实例引用
            unit.game_instance = self.game_instance
            self.game_instance.monsters.append(unit)
            # 在建筑管理器中注册工程师
            if hasattr(self.game_instance, 'building_manager') and self.game_instance.building_manager:
                self.game_instance.building_manager.engineers.append(unit)
                game_logger.info(f"🔨 {entity_id} 已注册为工程师")
        else:
            return PlacementResult(success=False, message=f"未知的后勤单位类型: {entity_id}")

        # 使用资源消耗管理器扣除资源
        resource_manager = get_resource_consumption_manager(self.game_instance)

        gold_cost = config.cost if config.resource_type == 'gold' else 0
        mana_cost = config.cost if config.resource_type == 'mana' else 0

        consumption_result = resource_manager.consume_resources(
            gold_cost, mana_cost)
        if not consumption_result.success:
            # 如果资源消耗失败，移除已创建的单位
            if hasattr(self.game_instance, 'monsters') and unit in self.game_instance.monsters:
                self.game_instance.monsters.remove(unit)
            if hasattr(self.game_instance, 'building_manager') and hasattr(self.game_instance.building_manager, 'engineers') and unit in self.game_instance.building_manager.engineers:
                self.game_instance.building_manager.engineers.remove(unit)
            return PlacementResult(success=False, message=consumption_result.message)

        return PlacementResult(
            success=True,
            message=f"召唤了{entity_id}在 ({x}, {y})",
            entity=unit,
            cost=config.cost,
            position=(x, y)
        )

    def _is_within_map_bounds(self, x: int, y: int) -> bool:
        """检查是否在地图边界内"""
        return (0 <= x < self.game_instance.map_width and
                0 <= y < self.game_instance.map_height)

    def _check_count_limit(self, config: PlacementConfig) -> bool:
        """检查数量限制"""
        if config.placement_type == PlacementType.CREATURE:
            return len(self.game_instance.monsters) < config.max_count
        elif config.placement_type == PlacementType.LOGISTICS:
            if config.entity_type == 'goblin_worker':
                # 统计哥布林苦工数量
                worker_count = sum(
                    1 for c in self.game_instance.monsters if c.type == 'goblin_worker')
                return worker_count < config.max_count
            elif config.entity_type == 'goblin_engineer':
                # 统计地精工程师数量
                engineer_count = sum(
                    1 for c in self.game_instance.monsters if c.type == 'goblin_engineer')
                return engineer_count < config.max_count
        return True

    def _is_position_occupied(self, x: int, y: int, config: PlacementConfig) -> bool:
        """检查位置是否被占用"""
        # 获取中心像素坐标（不使用UI缩放，因为实体坐标是基础坐标）
        base_x, base_y = tile_manager.get_tile_center_pixel(x, y)
        center_x = base_x
        center_y = base_y

        # 计算碰撞半径（不使用UI缩放，因为碰撞检测基于基础坐标）
        collision_radius = config.size * 0.6
        collision_radius = max(5, min(collision_radius, 25))

        # 检查所有单位
        all_units = (self.game_instance.monsters +
                     self.game_instance.heroes)

        for unit in all_units:
            distance = ((unit.x - center_x) ** 2 +
                        (unit.y - center_y) ** 2) ** 0.5
            if distance < collision_radius * 2:  # 两个半径的距离
                return True

        return False

    def get_placement_info(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        获取放置信息

        Args:
            entity_id: 实体ID

        Returns:
            Dict: 放置信息
        """
        config = self.placement_configs.get(entity_id)
        if not config:
            return None

        return {
            'entity_id': entity_id,
            'placement_type': config.placement_type.value,
            'entity_type': config.entity_type,
            'cost': config.cost,
            'resource_type': config.resource_type,
            'requires_dug': config.requires_dug,
            'requires_passable': config.requires_passable,
            'max_count': config.max_count,
            'size': config.size
        }

    def list_available_entities(self, placement_type: Optional[PlacementType] = None) -> List[str]:
        """
        列出可用的实体ID

        Args:
            placement_type: 放置类型过滤

        Returns:
            List[str]: 实体ID列表
        """
        if placement_type:
            return [entity_id for entity_id, config in self.placement_configs.items()
                    if config.placement_type == placement_type]
        else:
            return list(self.placement_configs.keys())
