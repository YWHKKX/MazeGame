#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资源消耗管理器
统一管理金币和魔力的消耗逻辑，优先从金库和魔法祭坛消耗资源
现在使用 ResourceManager 来统一管理资源
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .resource_manager import get_resource_manager
from src.utils.logger import game_logger


@dataclass
class ResourceConsumptionResult:
    """资源消耗结果"""
    success: bool
    message: str
    gold_consumed: int = 0
    mana_consumed: int = 0
    gold_source: str = ""  # 'dungeon_heart', 'treasury', 'mixed'
    mana_source: str = ""  # 'dungeon_heart', 'magic_altar', 'mixed'


class ResourceConsumptionManager:
    """资源消耗管理器"""

    def __init__(self, game_instance):
        """
        初始化资源消耗管理器

        Args:
            game_instance: 游戏实例引用
        """
        self.game_instance = game_instance

    def consume_resources(self, gold_cost: int = 0, mana_cost: int = 0) -> ResourceConsumptionResult:
        """
        消耗资源（优先从建筑中消耗）

        Args:
            gold_cost: 需要消耗的金币数量
            mana_cost: 需要消耗的魔力数量

        Returns:
            ResourceConsumptionResult: 消耗结果
        """
        if gold_cost <= 0 and mana_cost <= 0:
            return ResourceConsumptionResult(
                success=True,
                message="无需消耗资源",
                gold_consumed=0,
                mana_consumed=0
            )

        # 使用 ResourceManager 检查资源
        resource_manager = get_resource_manager(self.game_instance)
        can_afford, reason = self.can_afford(gold_cost, mana_cost)
        if not can_afford:
            return ResourceConsumptionResult(
                success=False,
                message=reason,
                gold_consumed=0,
                mana_consumed=0
            )

        # 使用 ResourceManager 消耗资源
        gold_result = resource_manager.consume_gold(gold_cost) if gold_cost > 0 else {
            'success': True, 'consumed': 0, 'sources': []}
        mana_result = resource_manager.consume_mana(mana_cost) if mana_cost > 0 else {
            'success': True, 'consumed': 0, 'sources': []}

        return ResourceConsumptionResult(
            success=gold_result['success'] and mana_result['success'],
            message=f"成功消耗 {gold_result['consumed']} 金币和 {mana_result['consumed']} 魔力",
            gold_consumed=gold_result['consumed'],
            mana_consumed=mana_result['consumed'],
            gold_source=gold_result.get('sources', [{}])[0].get(
                'source', 'unknown') if gold_result['sources'] else 'none',
            mana_source=mana_result.get('sources', [{}])[0].get(
                'source', 'unknown') if mana_result['sources'] else 'none'
        )

    def _get_available_gold(self) -> int:
        """获取可用金币总数（包括金库存储）"""
        resource_manager = get_resource_manager(self.game_instance)
        return resource_manager.get_total_gold().available

    def _get_available_mana(self) -> int:
        """获取可用魔力总数（包括地牢之心和魔法祭坛存储）"""
        resource_manager = get_resource_manager(self.game_instance)
        return resource_manager.get_total_mana().available

    def _consume_gold(self, amount: int) -> Dict[str, Any]:
        """
        消耗金币（优先从金库消耗）

        Args:
            amount: 需要消耗的金币数量

        Returns:
            Dict: {'consumed': int, 'source': str}
        """
        if amount <= 0:
            return {'consumed': 0, 'source': ''}

        remaining_amount = amount
        consumed_from_treasury = 0
        consumed_from_dungeon_heart = 0

        # 优先从金库消耗
        if hasattr(self.game_instance, 'building_manager') and self.game_instance.building_manager:
            for building in self.game_instance.building_manager.buildings:
                if (hasattr(building, 'building_type') and
                    building.building_type.value == 'treasury' and
                    hasattr(building, 'stored_gold') and
                    building.stored_gold > 0 and
                        remaining_amount > 0):

                    # 从金库消耗金币
                    consume_from_treasury = min(
                        remaining_amount, building.stored_gold)
                    building.stored_gold -= consume_from_treasury
                    consumed_from_treasury += consume_from_treasury
                    remaining_amount -= consume_from_treasury

                    game_logger.info(
                        f"💰 从金库({building.name})消耗 {consume_from_treasury} 金币")

        # 如果金库不够，从地牢之心消耗
        if remaining_amount > 0:
            dungeon_heart = self._get_dungeon_heart()
            if dungeon_heart and hasattr(dungeon_heart, 'stored_gold'):
                available_dungeon_gold = dungeon_heart.stored_gold
                consume_from_dungeon = min(
                    remaining_amount, available_dungeon_gold)
                dungeon_heart.stored_gold -= consume_from_dungeon
                consumed_from_dungeon_heart += consume_from_dungeon
                remaining_amount -= consume_from_dungeon

                if consume_from_dungeon > 0:
                    game_logger.info(f"💖 从地牢之心消耗 {consume_from_dungeon} 金币")

        # 确定消耗来源
        if consumed_from_treasury > 0 and consumed_from_dungeon_heart > 0:
            source = 'mixed'
        elif consumed_from_treasury > 0:
            source = 'treasury'
        else:
            source = 'dungeon_heart'

        return {
            'consumed': consumed_from_treasury + consumed_from_dungeon_heart,
            'source': source
        }

    def _consume_mana(self, amount: int) -> Dict[str, Any]:
        """
        消耗魔力（优先从魔法祭坛消耗）

        Args:
            amount: 需要消耗的魔力数量

        Returns:
            Dict: {'consumed': int, 'source': str}
        """
        if amount <= 0:
            return {'consumed': 0, 'source': ''}

        remaining_amount = amount
        consumed_from_altar = 0
        consumed_from_dungeon_heart = 0

        # 优先从魔法祭坛消耗
        if hasattr(self.game_instance, 'building_manager') and self.game_instance.building_manager:
            for building in self.game_instance.building_manager.buildings:
                if (hasattr(building, 'building_type') and
                    building.building_type.value == 'magic_altar' and
                    hasattr(building, 'stored_mana') and
                    building.stored_mana > 0 and
                        remaining_amount > 0):

                    # 从魔法祭坛消耗魔力
                    consume_from_altar = min(
                        remaining_amount, building.stored_mana)
                    building.stored_mana -= consume_from_altar
                    consumed_from_altar += consume_from_altar
                    remaining_amount -= consume_from_altar

                    game_logger.info(
                        f"🔮 从魔法祭坛({building.name})消耗 {consume_from_altar} 魔力")

        # 如果魔法祭坛不够，从地牢之心消耗
        if remaining_amount > 0:
            # 从地牢之心的存储魔力中消耗
            dungeon_heart = self._get_dungeon_heart()
            if dungeon_heart and hasattr(dungeon_heart, 'stored_mana'):
                available_dungeon_mana = dungeon_heart.stored_mana
                consume_from_dungeon = min(
                    remaining_amount, available_dungeon_mana)
                dungeon_heart.stored_mana -= consume_from_dungeon
                consumed_from_dungeon_heart += consume_from_dungeon
                remaining_amount -= consume_from_dungeon

                if consume_from_dungeon > 0:
                    game_logger.info(f"💖 从地牢之心消耗 {consume_from_dungeon} 魔力")
            else:
                # 如果找不到地牢之心，无法消耗魔力
                game_logger.info(f"❌ 无法找到地牢之心，无法消耗剩余的 {remaining_amount} 魔力")

        # 确定消耗来源
        if consumed_from_altar > 0 and consumed_from_dungeon_heart > 0:
            source = 'mixed'
        elif consumed_from_altar > 0:
            source = 'magic_altar'
        else:
            source = 'dungeon_heart'

        return {
            'consumed': consumed_from_altar + consumed_from_dungeon_heart,
            'source': source
        }

    def can_afford(self, gold_cost: int = 0, mana_cost: int = 0) -> Tuple[bool, str]:
        """
        检查是否有足够的资源

        Args:
            gold_cost: 需要消耗的金币数量
            mana_cost: 需要消耗的魔力数量

        Returns:
            Tuple[bool, str]: (是否有足够资源, 原因消息)
        """
        resource_manager = get_resource_manager(self.game_instance)

        if not resource_manager.can_afford(gold_cost, mana_cost):
            gold_info = resource_manager.get_total_gold()
            mana_info = resource_manager.get_total_mana()

            if gold_cost > gold_info.available:
                return False, f"金币不足，需要 {gold_cost}，可用 {gold_info.available}"
            if mana_cost > mana_info.available:
                return False, f"魔力不足，需要 {mana_cost}，可用 {mana_info.available}"

        return True, "资源充足"

    def _get_dungeon_heart(self):
        """获取地牢之心建筑对象"""
        if hasattr(self.game_instance, 'building_manager') and self.game_instance.building_manager:
            for building in self.game_instance.building_manager.buildings:
                if (hasattr(building, 'building_type') and
                        building.building_type.value == 'dungeon_heart'):
                    return building
        return None


def get_resource_consumption_manager(game_instance) -> ResourceConsumptionManager:
    """
    获取资源消耗管理器实例（单例模式）

    Args:
        game_instance: 游戏实例

    Returns:
        ResourceConsumptionManager: 资源消耗管理器实例
    """
    if not hasattr(game_instance, '_resource_consumption_manager'):
        game_instance._resource_consumption_manager = ResourceConsumptionManager(
            game_instance)

    return game_instance._resource_consumption_manager
