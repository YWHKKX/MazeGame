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
    # 注意：gold、mana、food 已移除，现在从各个建筑中获取
    # 使用 ResourceManager 来统一管理资源
    level: int = 1
    score: int = 0
    wave_number: int = 0
    reputation: int = 0
    research: int = 0

    # 建筑系统统计
    buildings_built: int = 0            # 已建造建筑数量
    engineers_summoned: int = 0         # 已召唤工程师数量
    total_construction_time: float = 0.0  # 总建造时间

    # 注意：资源管理现在由 ResourceManager 处理
    # 不再在 GameState 中存储 gold、mana、food 等资源
