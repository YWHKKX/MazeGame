#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源管理器 - 统一管理游戏中的资源获取和消耗
替代 GameState 中的 gold 和 mana 属性，从各个建筑中获取资源
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from src.utils.logger import game_logger


@dataclass
class ResourceInfo:
    """资源信息"""
    total: int
    available: int
    capacity: int
    sources: List[Dict[str, Any]]  # 资源来源列表


class ResourceManager:
    """资源管理器 - 统一管理游戏资源"""

    def __init__(self, game_instance):
        """
        初始化资源管理器

        Args:
            game_instance: 游戏实例，用于访问建筑和游戏状态
        """
        self.game_instance = game_instance

        # 维护两个专门的建筑列表
        self.gold_buildings = []  # 存储金币的建筑列表（地牢之心、金库）
        self.mana_buildings = []  # 存储魔力的建筑列表（地牢之心、魔法祭坛）

    def add_gold_building(self, building):
        """
        添加存储金币的建筑到列表

        Args:
            building: 建筑对象
        """
        if building not in self.gold_buildings:
            self.gold_buildings.append(building)
            game_logger.info(f"已添加金币建筑: {building.name}")

    def add_mana_building(self, building):
        """
        添加存储魔力的建筑到列表

        Args:
            building: 建筑对象
        """
        if building not in self.mana_buildings:
            self.mana_buildings.append(building)
            game_logger.info(f"已添加魔力建筑: {building.name}")

    def remove_gold_building(self, building):
        """
        从金币建筑列表中移除建筑

        Args:
            building: 建筑对象
        """
        if building in self.gold_buildings:
            self.gold_buildings.remove(building)
            game_logger.info(f"已移除金币建筑: {building.name}")

    def remove_mana_building(self, building):
        """
        从魔力建筑列表中移除建筑

        Args:
            building: 建筑对象
        """
        if building in self.mana_buildings:
            self.mana_buildings.remove(building)
            game_logger.info(f"已移除魔力建筑: {building.name}")

    def register_dungeon_heart(self, dungeon_heart):
        """
        注册地牢之心到两个建筑列表

        Args:
            dungeon_heart: 地牢之心建筑对象
        """
        self.add_gold_building(dungeon_heart)
        self.add_mana_building(dungeon_heart)
        game_logger.info(f"地牢之心已注册到资源管理器")

    def register_treasury(self, treasury):
        """
        注册金库到金币建筑列表

        Args:
            treasury: 金库建筑对象
        """
        self.add_gold_building(treasury)

    def register_magic_altar(self, magic_altar):
        """
        注册魔法祭坛到魔力建筑列表

        Args:
            magic_altar: 魔法祭坛建筑对象
        """
        self.add_mana_building(magic_altar)

    def get_total_gold(self) -> ResourceInfo:
        """
        获取总金币数量（从金币建筑列表中汇总）

        Returns:
            ResourceInfo: 包含总金币、可用金币、容量和来源信息
        """
        sources = []
        total_gold = 0
        total_capacity = 0

        # 从金币建筑列表中获取金币
        for building in self.gold_buildings:
            if hasattr(building, 'stored_gold'):
                building_name = getattr(building, 'name', '未知建筑')
                building_type = getattr(building, 'building_type', None)
                building_type_name = building_type.value if building_type else 'unknown'

                # 获取位置信息
                position = ""
                if hasattr(building, 'tile_x') and hasattr(building, 'tile_y'):
                    position = f"({building.tile_x},{building.tile_y})"

                sources.append({
                    'building': building_type_name,
                    'name': f'{building_name}{position}',
                    'amount': building.stored_gold,
                    'capacity': getattr(building, 'gold_storage_capacity', 0),
                    'available': building.stored_gold
                })
                total_gold += building.stored_gold
                total_capacity += getattr(building, 'gold_storage_capacity', 0)

        return ResourceInfo(
            total=total_gold,
            available=total_gold,  # 所有存储的金币都是可用的
            capacity=total_capacity,
            sources=sources
        )

    def get_total_mana(self) -> ResourceInfo:
        """
        获取总魔力数量（从魔力建筑列表中汇总）

        Returns:
            ResourceInfo: 包含总魔力、可用魔力、容量和来源信息
        """
        sources = []
        total_mana = 0
        total_capacity = 0

        # 从魔力建筑列表中获取魔力
        for building in self.mana_buildings:
            if hasattr(building, 'stored_mana'):
                building_name = getattr(building, 'name', '未知建筑')
                building_type = getattr(building, 'building_type', None)
                building_type_name = building_type.value if building_type else 'unknown'

                # 获取位置信息
                position = ""
                if hasattr(building, 'tile_x') and hasattr(building, 'tile_y'):
                    position = f"({building.tile_x},{building.tile_y})"

                sources.append({
                    'building': building_type_name,
                    'name': f'{building_name}{position}',
                    'amount': building.stored_mana,
                    'capacity': getattr(building, 'mana_storage_capacity', 0),
                    'available': building.stored_mana
                })
                total_mana += building.stored_mana
                total_capacity += getattr(building, 'mana_storage_capacity', 0)

        return ResourceInfo(
            total=total_mana,
            available=total_mana,  # 所有存储的魔力都是可用的
            capacity=total_capacity,
            sources=sources
        )

    def can_afford(self, gold_cost: int = 0, mana_cost: int = 0) -> bool:
        """
        检查是否有足够的资源

        Args:
            gold_cost: 需要的金币数量
            mana_cost: 需要的魔力数量

        Returns:
            bool: 是否有足够资源
        """
        gold_info = self.get_total_gold()
        mana_info = self.get_total_mana()

        return gold_info.available >= gold_cost and mana_info.available >= mana_cost

    def consume_gold(self, amount: int, priority_sources: List[str] = None) -> Dict[str, Any]:
        """
        消耗金币（按优先级从金币建筑列表中消耗）

        Args:
            amount: 要消耗的金币数量
            priority_sources: 优先级来源列表，如 ['dungeon_heart', 'treasury']

        Returns:
            Dict[str, Any]: 消耗结果
        """
        if priority_sources is None:
            priority_sources = ['dungeon_heart', 'treasury']

        remaining_amount = amount
        consumed_sources = []

        # 按优先级消耗金币
        for source_type in priority_sources:
            if remaining_amount <= 0:
                break

            for building in self.gold_buildings:
                if remaining_amount <= 0:
                    break

                # 检查建筑类型是否匹配优先级
                building_type = getattr(building, 'building_type', None)
                if building_type and hasattr(building_type, 'value') and building_type.value == source_type:
                    if hasattr(building, 'stored_gold') and building.stored_gold > 0:
                        available = building.stored_gold
                        consume_amount = min(remaining_amount, available)

                        if consume_amount > 0:
                            building.stored_gold -= consume_amount
                            remaining_amount -= consume_amount

                            # 获取位置信息
                            position = ""
                            if hasattr(building, 'tile_x') and hasattr(building, 'tile_y'):
                                position = f"({building.tile_x},{building.tile_y})"

                            consumed_sources.append({
                                'source': f'{source_type}{position}',
                                'amount': consume_amount,
                                'remaining': building.stored_gold
                            })

        return {
            'success': remaining_amount == 0,
            'requested': amount,
            'consumed': amount - remaining_amount,
            'remaining_needed': remaining_amount,
            'sources': consumed_sources
        }

    def consume_mana(self, amount: int, priority_sources: List[str] = None) -> Dict[str, Any]:
        """
        消耗魔力（按优先级从魔力建筑列表中消耗）

        Args:
            amount: 要消耗的魔力数量
            priority_sources: 优先级来源列表，如 ['dungeon_heart', 'magic_altar']

        Returns:
            Dict[str, Any]: 消耗结果
        """
        if priority_sources is None:
            priority_sources = ['dungeon_heart', 'magic_altar']

        remaining_amount = amount
        consumed_sources = []

        # 按优先级消耗魔力
        for source_type in priority_sources:
            if remaining_amount <= 0:
                break

            for building in self.mana_buildings:
                if remaining_amount <= 0:
                    break

                # 检查建筑类型是否匹配优先级
                building_type = getattr(building, 'building_type', None)
                if building_type and hasattr(building_type, 'value') and building_type.value == source_type:
                    if hasattr(building, 'stored_mana') and building.stored_mana > 0:
                        available = building.stored_mana
                        consume_amount = min(remaining_amount, available)

                        if consume_amount > 0:
                            building.stored_mana -= consume_amount
                            remaining_amount -= consume_amount

                            # 获取位置信息
                            position = ""
                            if hasattr(building, 'tile_x') and hasattr(building, 'tile_y'):
                                position = f"({building.tile_x},{building.tile_y})"

                            consumed_sources.append({
                                'source': f'{source_type}{position}',
                                'amount': consume_amount,
                                'remaining': building.stored_mana
                            })

        return {
            'success': remaining_amount == 0,
            'requested': amount,
            'consumed': amount - remaining_amount,
            'remaining_needed': remaining_amount,
            'sources': consumed_sources
        }

    def add_gold(self, amount: int, target_building=None) -> Dict[str, Any]:
        """
        添加金币到指定建筑

        Args:
            amount: 要添加的金币数量
            target_building: 目标建筑对象，如果为None则添加到地牢之心

        Returns:
            Dict[str, Any]: 添加结果
        """
        # 如果没有指定目标建筑，默认添加到地牢之心
        if target_building is None:
            for building in self.gold_buildings:
                building_type = getattr(building, 'building_type', None)
                if building_type and building_type.value == 'dungeon_heart':
                    target_building = building
                    break

        if target_building and hasattr(target_building, 'stored_gold'):
            old_amount = target_building.stored_gold
            target_building.stored_gold += amount

            building_name = getattr(target_building, 'name', '未知建筑')
            return {
                'success': True,
                'amount': amount,
                'old_amount': old_amount,
                'new_amount': target_building.stored_gold,
                'target': building_name
            }

        return {
            'success': False,
            'amount': 0,
            'message': f'无法添加金币到指定建筑'
        }

    def add_mana(self, amount: int, target_building=None) -> Dict[str, Any]:
        """
        添加魔力到指定建筑

        Args:
            amount: 要添加的魔力数量
            target_building: 目标建筑对象，如果为None则添加到地牢之心

        Returns:
            Dict[str, Any]: 添加结果
        """
        # 如果没有指定目标建筑，默认添加到地牢之心
        if target_building is None:
            for building in self.mana_buildings:
                building_type = getattr(building, 'building_type', None)
                if building_type and building_type.value == 'dungeon_heart':
                    target_building = building
                    break

        if target_building and hasattr(target_building, 'stored_mana'):
            old_amount = target_building.stored_mana
            target_building.stored_mana += amount

            building_name = getattr(target_building, 'name', '未知建筑')
            return {
                'success': True,
                'amount': amount,
                'old_amount': old_amount,
                'new_amount': target_building.stored_mana,
                'target': building_name
            }

        return {
            'success': False,
            'amount': 0,
            'message': f'无法添加魔力到指定建筑'
        }

    def get_resource_summary(self) -> Dict[str, Any]:
        """
        获取资源汇总信息

        Returns:
            Dict[str, Any]: 包含金币和魔力的详细信息
        """
        gold_info = self.get_total_gold()
        mana_info = self.get_total_mana()

        return {
            'gold': {
                'total': gold_info.total,
                'available': gold_info.available,
                'capacity': gold_info.capacity,
                'sources': gold_info.sources
            },
            'mana': {
                'total': mana_info.total,
                'available': mana_info.available,
                'capacity': mana_info.capacity,
                'sources': mana_info.sources
            }
        }


# 全局资源管理器实例
_resource_manager = None


def get_resource_manager(game_instance=None) -> ResourceManager:
    """
    获取资源管理器实例（单例模式）

    Args:
        game_instance: 游戏实例，如果为None则返回现有实例

    Returns:
        ResourceManager: 资源管理器实例
    """
    global _resource_manager

    if _resource_manager is None and game_instance is not None:
        _resource_manager = ResourceManager(game_instance)
    elif _resource_manager is not None and game_instance is not None:
        # 更新游戏实例引用
        _resource_manager.game_instance = game_instance

    return _resource_manager


def reset_resource_manager():
    """重置资源管理器（用于测试或重新开始游戏）"""
    global _resource_manager
    _resource_manager = None
