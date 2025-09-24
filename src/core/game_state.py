#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏状态和数据结构
"""

from dataclasses import dataclass
from typing import Optional
from .enums import TileType
from .constants import GameBalance

# 为了保持向后兼容性，创建一个Tile类作为GameTile的包装


class Tile:
    """地图瓦片数据 - 兼容性包装类，现在基于GameTile"""

    def __init__(self, type: TileType, **kwargs):
        # 延迟导入避免循环导入
        from ..entities.tile import GameTile

        # 创建GameTile实例
        self._game_tile = GameTile(
            x=kwargs.get('x', 0),
            y=kwargs.get('y', 0),
            tile_type=type,
            **kwargs
        )

        # 设置坐标
        self._game_tile.x = kwargs.get('x', 0)
        self._game_tile.y = kwargs.get('y', 0)

    def __getattr__(self, name):
        """代理所有属性访问到GameTile"""
        return getattr(self._game_tile, name)

    def __setattr__(self, name, value):
        """代理所有属性设置到GameTile"""
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            setattr(self._game_tile, name, value)


@dataclass
class GameState:
    """游戏状态数据"""
    gold: int = GameBalance.starting_gold
    mana: int = GameBalance.starting_mana
    food: int = GameBalance.starting_food
    raw_gold: int = 0
    level: int = 1
    score: int = 0
    wave_number: int = 0
    reputation: int = 0
    research: int = 0

    # 建筑系统新增资源
    crystal: int = 0

    def get_total_gold(self, building_manager=None) -> int:
        """获取总金币数量（包括金库中存储的金币）"""
        total_gold = self.gold

        if building_manager:
            # 计算所有金库中存储的金币
            for building in building_manager.buildings:
                if (hasattr(building, 'building_type') and
                    building.building_type.value == 'treasury' and
                        hasattr(building, 'stored_gold')):
                    total_gold += building.stored_gold

        return total_gold

    # 建筑系统统计
    buildings_built: int = 0            # 已建造建筑数量
    engineers_summoned: int = 0         # 已召唤工程师数量
    total_construction_time: float = 0.0  # 总建造时间

    # 金币存储系统
    max_gold_capacity: int = 2000       # 主基地最大金币存储容量
    treasury_gold: int = 0              # 金库中存储的金币
