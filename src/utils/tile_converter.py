#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
瓦块转换工具 - 在Tile和GameTile之间转换
"""

from typing import List, Tuple
from ..core.game_state import Tile
from ..core.enums import TileType
from ..entities.tile import GameTile


class TileConverter:
    """瓦块转换工具类"""

    @staticmethod
    def tile_to_game_tile(tile: Tile, x: int, y: int, tile_size: int = 20) -> GameTile:
        """
        将Tile转换为GameTile

        Args:
            tile: 原始Tile对象
            x, y: 瓦块坐标
            tile_size: 瓦块大小

        Returns:
            GameTile对象
        """
        game_tile = GameTile(x, y, tile.type, tile_size)

        # 复制基础属性
        game_tile.is_dug = tile.is_dug

        # 复制资源信息
        game_tile.resource.gold_amount = tile.gold_amount
        game_tile.resource.is_gold_vein = tile.is_gold_vein
        game_tile.resource.being_mined = tile.being_mined
        game_tile.resource.miners_count = tile.miners_count
        game_tile.resource.is_depleted = (tile.type == TileType.DEPLETED_VEIN)

        # 复制建筑信息
        game_tile.building.room = tile.room
        game_tile.building.room_type = tile.room_type
        game_tile.building.is_incomplete = tile.is_incomplete
        game_tile.building.needs_rerender = tile.needs_rerender
        game_tile.building.just_rerendered = tile.just_rerendered

        return game_tile

    @staticmethod
    def game_tile_to_tile(game_tile: GameTile) -> Tile:
        """
        将GameTile转换为Tile

        Args:
            game_tile: GameTile对象

        Returns:
            Tile对象
        """
        tile = Tile(
            type=game_tile.tile_type,
            room=game_tile.building.room,
            room_type=game_tile.building.room_type,
            gold_amount=game_tile.resource.gold_amount,
            is_gold_vein=game_tile.resource.is_gold_vein,
            being_mined=game_tile.resource.being_mined,
            is_dug=game_tile.is_dug,
            miners_count=game_tile.resource.miners_count,
            is_incomplete=game_tile.building.is_incomplete,
            needs_rerender=game_tile.building.needs_rerender,
            just_rerendered=game_tile.building.just_rerendered
        )
        return tile

    @staticmethod
    def convert_map_to_game_tiles(game_map: List[List[Tile]], tile_size: int = 20) -> List[List[GameTile]]:
        """
        将整个地图从Tile转换为GameTile

        Args:
            game_map: 原始地图（Tile二维数组）
            tile_size: 瓦块大小

        Returns:
            GameTile二维数组
        """
        new_map = []
        for y, row in enumerate(game_map):
            new_row = []
            for x, tile in enumerate(row):
                if tile:
                    game_tile = TileConverter.tile_to_game_tile(
                        tile, x, y, tile_size)
                    new_row.append(game_tile)
                else:
                    new_row.append(None)
            new_map.append(new_row)
        return new_map

    @staticmethod
    def convert_map_to_tiles(game_map: List[List[GameTile]]) -> List[List[Tile]]:
        """
        将整个地图从GameTile转换为Tile

        Args:
            game_map: GameTile二维数组

        Returns:
            Tile二维数组
        """
        new_map = []
        for row in game_map:
            new_row = []
            for game_tile in row:
                if game_tile:
                    tile = TileConverter.game_tile_to_tile(game_tile)
                    new_row.append(tile)
                else:
                    new_row.append(None)
            new_map.append(new_row)
        return new_map

    @staticmethod
    def get_tile_center_pixel(x: int, y: int, tile_size: int) -> Tuple[int, int]:
        """
        获取瓦块中心像素点坐标

        Args:
            x, y: 瓦块坐标
            tile_size: 瓦块大小

        Returns:
            (center_x, center_y) 中心像素点坐标
        """
        center_x = x * tile_size + tile_size // 2
        center_y = y * tile_size + tile_size // 2
        return (center_x, center_y)

    @staticmethod
    def get_screen_center_pixel(x: int, y: int, tile_size: int, camera_x: int, camera_y: int) -> Tuple[int, int]:
        """
        获取瓦块中心像素点在屏幕上的坐标

        Args:
            x, y: 瓦块坐标
            tile_size: 瓦块大小
            camera_x, camera_y: 相机位置

        Returns:
            (screen_x, screen_y) 屏幕坐标
        """
        center_x, center_y = TileConverter.get_tile_center_pixel(
            x, y, tile_size)
        screen_x = center_x - camera_x
        screen_y = center_y - camera_y
        return (screen_x, screen_y)
