#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可达性检查系统 - 计算瓦块是否与主基地联通
"""

import time
import math
from typing import List, Tuple, Set, Optional
from collections import deque

from ..core.enums import TileType
from ..core.constants import GameConstants
from src.utils.logger import game_logger


class ReachabilitySystem:
    """可达性检查系统"""

    def __init__(self):
        self.last_update_time = 0.0
        self.update_interval = 2.0  # 每2秒更新一次
        self.base_position = None
        self.reachable_tiles: Set[Tuple[int, int]] = set()
        self.log_adjacent_veins = True  # 是否输出接壤金矿脉日志

        # 强制更新机制
        self.force_update_events = set()  # 需要强制更新的事件
        self.last_force_update_time = 0.0  # 上次强制更新时间
        self.force_update_cooldown = 0.5  # 强制更新冷却时间（秒）

    def set_base_position(self, base_x: int, base_y: int):
        """设置主基地位置"""
        self.base_position = (base_x, base_y)
        self.reachable_tiles.clear()  # 清除缓存

    def register_force_update_event(self, event_type: str, x: int, y: int):
        """注册需要强制更新的事件"""
        self.force_update_events.add((event_type, x, y))
        game_logger.info(f"🔔 注册强制更新事件: {event_type} at ({x}, {y})")

    def clear_force_update_events(self):
        """清除强制更新事件"""
        self.force_update_events.clear()

    def has_force_update_events(self) -> bool:
        """检查是否有强制更新事件"""
        return len(self.force_update_events) > 0

    def should_force_update(self) -> bool:
        """检查是否应该强制更新"""
        current_time = time.time()

        # 检查冷却时间
        if current_time - self.last_force_update_time < self.force_update_cooldown:
            return False

        # 检查是否有强制更新事件
        return self.has_force_update_events()

    def update_reachability(self, game_map: List[List], force_update: bool = False) -> bool:
        """更新所有瓦块的可达性"""
        current_time = time.time()

        # 检查是否需要更新
        if not force_update and (current_time - self.last_update_time) < self.update_interval:
            # 检查是否有强制更新事件
            if self.should_force_update():
                force_update = True
                game_logger.info(
                    f"🔄 触发强制更新，事件数量: {len(self.force_update_events)}")
            else:
                return False

        if not self.base_position:
            return False

        start_time = time.time()

        # 使用BFS算法计算可达性
        self._calculate_reachability_bfs(game_map)

        # 更新瓦块的可达性标记
        self._update_tile_reachability(game_map)

        self.last_update_time = current_time
        elapsed = time.time() - start_time

        # 如果是强制更新，记录时间并清除事件
        if force_update:
            self.last_force_update_time = current_time
            self.clear_force_update_events()

        # 统计金矿脉数量
        gold_veins = self.get_reachable_gold_veins(game_map)
        update_type = "强制更新" if force_update else "常规更新"
        game_logger.info(
            f"✅ 可达性{update_type}完成: {len(self.reachable_tiles)} 个瓦块可达，{len(gold_veins)} 个金矿脉可达，耗时 {elapsed:.3f}秒")

        return True

    def _calculate_reachability_bfs(self, game_map: List[List]):
        """使用BFS算法计算可达性"""
        if not self.base_position:
            game_logger.info("❌ 主基地位置未设置")
            return

        base_x, base_y = self.base_position
        self.reachable_tiles.clear()

        # 检查主基地位置是否有效
        if (base_x < 0 or base_x >= len(game_map[0]) or
                base_y < 0 or base_y >= len(game_map)):
            game_logger.info(f"❌ 主基地位置无效: ({base_x}, {base_y})")
            return

        # 检查主基地瓦块是否可通行
        base_tile = game_map[base_y][base_x]
        if not self._is_tile_passable(base_tile):
            game_logger.info(f"❌ 主基地瓦块不可通行: {base_tile}")
            return

        # BFS队列
        queue = deque([(base_x, base_y)])
        visited = set([(base_x, base_y)])

        # 4方向移动
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        while queue:
            x, y = queue.popleft()
            self.reachable_tiles.add((x, y))

            # 检查4个方向
            for dx, dy in directions:
                nx, ny = x + dx, y + dy

                # 检查边界
                if (nx < 0 or nx >= len(game_map[0]) or
                        ny < 0 or ny >= len(game_map)):
                    continue

                # 检查是否已访问
                if (nx, ny) in visited:
                    continue

                # 检查瓦块是否可通行
                tile = game_map[ny][nx]
                if self._is_tile_passable(tile):
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    def _is_tile_passable(self, tile) -> bool:
        """检查瓦块是否可通行"""
        # 检查瓦块类型
        if hasattr(tile, 'type'):
            # Tile类
            # 可通行的瓦片类型：地面、房间、金矿脉
            return tile.type in [TileType.GROUND, TileType.ROOM, TileType.GOLD_VEIN]
        elif hasattr(tile, 'tile_type'):
            # GameTile类
            return tile.tile_type in [TileType.GROUND, TileType.ROOM, TileType.GOLD_VEIN]
        else:
            # 兼容性检查
            return (getattr(tile, 'is_dug', False) or
                    getattr(tile, 'type', None) in [TileType.GROUND, TileType.GOLD_VEIN])

    def _update_tile_reachability(self, game_map: List[List]):
        """更新瓦块的可达性标记"""
        current_time = time.time()

        for y in range(len(game_map)):
            for x in range(len(game_map[0])):
                tile = game_map[y][x]
                is_reachable = (x, y) in self.reachable_tiles

                # 更新瓦块的可达性标记
                if hasattr(tile, 'is_reachable_from_base'):
                    tile.is_reachable_from_base = is_reachable
                    tile.reachability_checked = True
                    tile.last_reachability_check = current_time
                elif hasattr(tile, 'set_reachability'):
                    tile.set_reachability(is_reachable, current_time)

    def is_tile_reachable(self, x: int, y: int) -> bool:
        """检查指定瓦块是否可达"""
        return (x, y) in self.reachable_tiles

    def get_reachable_tiles(self) -> Set[Tuple[int, int]]:
        """获取所有可达瓦块的集合"""
        return self.reachable_tiles.copy()

    def get_reachable_gold_veins(self, game_map: List[List]) -> List[Tuple[int, int, int]]:
        """获取所有可达的金矿脉（有储量的金矿）"""
        reachable_veins = []

        # 首先检查已挖掘区域的金矿脉
        for x, y in self.reachable_tiles:
            tile = game_map[y][x]

            # 检查是否为金矿脉
            is_gold_vein = False
            gold_amount = 0
            miners_count = 0

            if hasattr(tile, 'is_gold_vein'):
                # Tile类
                is_gold_vein = tile.is_gold_vein
                gold_amount = tile.gold_amount
                miners_count = tile.miners_count
            elif hasattr(tile, 'resource'):
                # GameTile类
                is_gold_vein = tile.resource.is_gold_vein
                gold_amount = tile.resource.gold_amount
                miners_count = tile.resource.miners_count

            if is_gold_vein and gold_amount > 0:
                reachable_veins.append((x, y, gold_amount))

        # 检查与可到达区域接壤的有储量金矿脉
        adjacent_gold_veins = self._find_adjacent_gold_veins_with_stock(
            game_map)
        reachable_veins.extend(adjacent_gold_veins)

        return reachable_veins

    def _find_adjacent_gold_veins_with_stock(self, game_map: List[List]) -> List[Tuple[int, int, int]]:
        """查找与可到达区域接壤的有储量金矿脉"""
        adjacent_veins = []

        # 4方向移动
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        # 检查每个可到达瓦块周围的有储量金矿脉
        for reachable_x, reachable_y in self.reachable_tiles:
            for dx, dy in directions:
                check_x = reachable_x + dx
                check_y = reachable_y + dy

                # 检查边界
                if (check_x < 0 or check_x >= len(game_map[0]) or
                        check_y < 0 or check_y >= len(game_map)):
                    continue

                # 检查是否已经处理过
                if (check_x, check_y) in self.reachable_tiles:
                    continue

                tile = game_map[check_y][check_x]

                # 检查是否为有储量的金矿脉
                is_gold_vein_with_stock = False
                gold_amount = 0

                if hasattr(tile, 'is_gold_vein'):
                    # Tile类
                    is_gold_vein_with_stock = (tile.is_gold_vein and
                                               hasattr(tile, 'gold_amount') and
                                               tile.gold_amount > 0)
                    gold_amount = tile.gold_amount
                elif hasattr(tile, 'resource'):
                    # GameTile类
                    is_gold_vein_with_stock = (tile.resource.is_gold_vein and
                                               hasattr(tile, 'resource') and
                                               tile.resource.gold_amount > 0)
                    gold_amount = tile.resource.gold_amount

                if is_gold_vein_with_stock:
                    # 检查是否已经添加过
                    if not any(v[0] == check_x and v[1] == check_y for v in adjacent_veins):
                        adjacent_veins.append((check_x, check_y, gold_amount))
                        # 只在启用日志时输出
                        if self.log_adjacent_veins:
                            game_logger.info(
                                f"🔍 发现接壤的有储量金矿脉: ({check_x}, {check_y}) 储量: {gold_amount}")

        return adjacent_veins

    def invalidate_reachability(self):
        """使可达性缓存失效"""
        self.reachable_tiles.clear()
        self.last_update_time = 0.0

    def enable_adjacent_vein_logging(self):
        """启用接壤金矿脉日志输出"""
        self.log_adjacent_veins = True

    def disable_adjacent_vein_logging(self):
        """禁用接壤金矿脉日志输出"""
        self.log_adjacent_veins = False

    def get_stats(self) -> dict:
        """获取可达性统计信息"""
        return {
            'reachable_tiles_count': len(self.reachable_tiles),
            'last_update_time': self.last_update_time,
            'base_position': self.base_position,
            'needs_update': time.time() - self.last_update_time > self.update_interval
        }


# 全局可达性系统实例
_reachability_system = None


def get_reachability_system() -> ReachabilitySystem:
    """获取全局可达性系统实例"""
    global _reachability_system
    if _reachability_system is None:
        _reachability_system = ReachabilitySystem()
    return _reachability_system
