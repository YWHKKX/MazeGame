#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
瓦块管理器 - 统一管理瓦块相关操作
"""

from typing import List, Tuple, Optional, Dict, Any
from ..core.enums import TileType
from ..core.game_state import Tile, GameState
from ..entities.tile import GameTile
from ..utils.tile_converter import TileConverter


class TileManager:
    """瓦块管理器 - 统一处理瓦块相关操作"""

    def __init__(self, tile_size: int = 20):
        """
        初始化瓦块管理器

        Args:
            tile_size: 瓦块大小（像素）
        """
        self.tile_size = tile_size

    def create_tile(self, x: int, y: int, tile_type: TileType,
                    is_gold_vein: bool = False, gold_amount: int = 0) -> Tile:
        """
        创建瓦块

        Args:
            x, y: 瓦块坐标
            tile_type: 瓦块类型
            is_gold_vein: 是否为金矿脉
            gold_amount: 金矿储量

        Returns:
            Tile对象
        """
        return Tile(
            type=tile_type,
            is_gold_vein=is_gold_vein,
            gold_amount=gold_amount
        )

    def dig_tile(self, tile: Tile, x: int, y: int, cost: int = 0,
                 game_state: Optional[GameState] = None) -> Dict[str, Any]:
        """
        挖掘瓦块 - 统一挖掘接口

        Args:
            tile: 要挖掘的瓦块
            x, y: 瓦块坐标
            cost: 挖掘成本
            game_state: 游戏状态

        Returns:
            挖掘结果字典
        """
        # 直接调用瓦块的dig方法，传入坐标参数
        return tile.dig(cost=cost, game_state=game_state, x=x, y=y)

    def check_tile_passable(self, tile: Tile) -> bool:
        """
        检查瓦块是否可通行

        Args:
            tile: 瓦块对象

        Returns:
            是否可通行
        """
        return tile.type in [TileType.GROUND, TileType.ROOM] or tile.is_dug

    def check_tile_has_gold(self, tile: Tile) -> bool:
        """
        检查瓦块是否有金矿

        Args:
            tile: 瓦块对象

        Returns:
            是否有金矿
        """
        return tile.is_gold_vein and tile.gold_amount > 0

    def get_tile_center_pixel(self, x: int, y: int) -> Tuple[int, int]:
        """
        获取瓦块中心像素坐标

        Args:
            x, y: 瓦块坐标

        Returns:
            中心像素坐标
        """
        center_x = x * self.tile_size + self.tile_size // 2
        center_y = y * self.tile_size + self.tile_size // 2
        return (center_x, center_y)

    def get_tile_screen_position(self, x: int, y: int, camera_x: int, camera_y: int) -> Tuple[int, int]:
        """
        获取瓦块在屏幕上的位置

        Args:
            x, y: 瓦块坐标
            camera_x, camera_y: 相机位置

        Returns:
            屏幕坐标
        """
        world_x = x * self.tile_size
        world_y = y * self.tile_size
        screen_x = world_x - camera_x
        screen_y = world_y - camera_y
        return (screen_x, screen_y)

    def convert_to_game_tile(self, tile: Tile, x: int, y: int) -> GameTile:
        """
        将Tile转换为GameTile

        Args:
            tile: 原始Tile对象
            x, y: 瓦块坐标

        Returns:
            GameTile对象
        """
        return TileConverter.tile_to_game_tile(tile, x, y, self.tile_size)

    def convert_to_tile(self, game_tile: GameTile) -> Tile:
        """
        将GameTile转换为Tile

        Args:
            game_tile: GameTile对象

        Returns:
            Tile对象
        """
        return TileConverter.game_tile_to_tile(game_tile)

    def get_tile_info(self, tile: Tile, x: int, y: int) -> Dict[str, Any]:
        """
        获取瓦块信息

        Args:
            tile: 瓦块对象
            x, y: 瓦块坐标

        Returns:
            瓦块信息字典
        """
        return {
            'position': (x, y),
            'type': tile.type,
            'is_dug': tile.is_dug,
            'is_gold_vein': tile.is_gold_vein,
            'gold_amount': tile.gold_amount,
            'miners_count': tile.miners_count,
            'is_passable': self.check_tile_passable(tile),
            'has_gold': self.check_tile_has_gold(tile),
            'center_pixel': self.get_tile_center_pixel(x, y),
            'room_type': tile.room_type,
            'is_incomplete': tile.is_incomplete,
            'needs_rerender': tile.needs_rerender
        }

    def update_tile_render_state(self, tile: Tile, needs_rerender: bool = True):
        """
        更新瓦块渲染状态

        Args:
            tile: 瓦块对象
            needs_rerender: 是否需要重新渲染
        """
        tile.needs_rerender = needs_rerender

    def is_tile_in_screen_bounds(self, x: int, y: int, camera_x: int, camera_y: int,
                                 screen_width: int, screen_height: int) -> bool:
        """
        检查瓦块是否在屏幕范围内

        Args:
            x, y: 瓦块坐标
            camera_x, camera_y: 相机位置
            screen_width, screen_height: 屏幕尺寸

        Returns:
            是否在屏幕范围内
        """
        screen_x, screen_y = self.get_tile_screen_position(
            x, y, camera_x, camera_y)
        return (screen_x + self.tile_size >= 0 and screen_x <= screen_width and
                screen_y + self.tile_size >= 0 and screen_y <= screen_height)


# 创建全局瓦块管理器实例
tile_manager = TileManager()
