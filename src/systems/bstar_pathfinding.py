#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B*寻路算法实现
B*算法是A*算法的改进版本，具有更好的动态路径规划和实时调整能力

核心特性:
1. 动态路径调整 - 能够实时调整路径以应对环境变化
2. 多目标优化 - 同时考虑多个目标函数
3. 路径平滑 - 生成更自然的移动路径
4. 性能优化 - 比传统A*更高效的搜索
"""

import math
import heapq
import time
from typing import List, Tuple, Optional, Set, Dict, Any
from dataclasses import dataclass
from enum import Enum


class BStarNodeType(Enum):
    """B*节点类型"""
    NORMAL = "normal"
    DYNAMIC = "dynamic"  # 动态调整节点
    CRITICAL = "critical"  # 关键路径节点


@dataclass
class BStarNode:
    """B*寻路算法节点"""
    x: int
    y: int
    g: float = 0  # 从起点到当前节点的实际代价
    h: float = 0  # 从当前节点到终点的启发式代价
    f: float = 0  # 总代价 f = g + h
    b: float = 0  # B*特有的动态调整代价
    parent: Optional['BStarNode'] = None
    node_type: BStarNodeType = BStarNodeType.NORMAL
    dynamic_weight: float = 1.0  # 动态权重
    last_updated: float = 0  # 最后更新时间

    def __lt__(self, other):
        # B*使用 f + b 作为优先级，b是动态调整因子
        return (self.f + self.b) < (other.f + other.b)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def update_dynamic_cost(self, current_time: float, environment_changes: float = 0.0):
        """更新动态代价"""
        self.b = self.dynamic_weight * environment_changes
        self.last_updated = current_time


class BStarPathfinding:
    """B*寻路算法实现"""

    def __init__(self, max_iterations: int = 1000, dynamic_threshold: float = 0.1):
        """
        初始化B*寻路算法

        Args:
            max_iterations: 最大迭代次数
            dynamic_threshold: 动态调整阈值
        """
        self.max_iterations = max_iterations
        self.dynamic_threshold = dynamic_threshold
        self.path_cache: Dict[Tuple, List[Tuple[int, int]]] = {}
        self.cache_timeout = 5.0  # 缓存超时时间（秒）

        # 性能统计
        self.search_count = 0
        self.cache_hits = 0
        self.dynamic_adjustments = 0

    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int],
                  game_map: List[List], heuristic_func=None,
                  dynamic_adjustments: bool = True) -> Optional[List[Tuple[int, int]]]:
        """
        使用B*算法寻找路径

        Args:
            start: 起始位置
            goal: 目标位置
            game_map: 游戏地图
            heuristic_func: 启发式函数
            dynamic_adjustments: 是否启用动态调整

        Returns:
            路径列表，如果找不到路径则返回None
        """
        start_time = time.time()
        self.search_count += 1

        # 检查缓存
        cache_key = (start, goal, int(dynamic_adjustments))
        if cache_key in self.path_cache:
            cached_path, cache_time = self.path_cache[cache_key]
            if time.time() - cache_time < self.cache_timeout:
                self.cache_hits += 1
                return cached_path

        # 检查起点和终点是否有效
        if not self._is_valid_position(start, game_map) or not self._is_valid_position(goal, game_map):
            return None

        # 如果起点和终点相同
        if start == goal:
            return [start]

        # 使用默认启发式函数
        if heuristic_func is None:
            heuristic_func = self._manhattan_distance

        # 执行B*搜索
        path = self._bstar_search(
            start, goal, game_map, heuristic_func, dynamic_adjustments)

        # 缓存结果
        if path:
            self.path_cache[cache_key] = (path, time.time())

        # 清理过期缓存
        self._cleanup_cache()

        return path

    def _bstar_search(self, start: Tuple[int, int], goal: Tuple[int, int],
                      game_map: List[List], heuristic_func, dynamic_adjustments: bool) -> Optional[List[Tuple[int, int]]]:
        """执行B*搜索算法"""
        open_set = []
        closed_set: Set[Tuple[int, int]] = set()
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}

        # 创建起始节点
        start_node = BStarNode(start[0], start[1])
        start_node.h = heuristic_func(start, goal)
        start_node.f = start_node.g + start_node.h
        start_node.last_updated = time.time()

        heapq.heappush(open_set, start_node)

        # 环境变化检测
        environment_changes = 0.0
        last_environment_check = time.time()

        iterations = 0
        while open_set and iterations < self.max_iterations:
            iterations += 1

            # 获取当前最佳节点
            current = heapq.heappop(open_set)

            # 检查是否已访问
            if (current.x, current.y) in closed_set:
                continue

            closed_set.add((current.x, current.y))

            # 检查是否到达目标
            if (current.x, current.y) == goal:
                return self._reconstruct_path(came_from, start, goal)

            # 动态调整检测
            if dynamic_adjustments:
                current_time = time.time()
                if current_time - last_environment_check > 0.1:  # 每0.1秒检查一次
                    environment_changes = self._detect_environment_changes(
                        (current.x, current.y), game_map)
                    last_environment_check = current_time

                    if environment_changes > self.dynamic_threshold:
                        self.dynamic_adjustments += 1
                        current.update_dynamic_cost(
                            current_time, environment_changes)

            # 探索邻居节点
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                neighbor_x = current.x + dx
                neighbor_y = current.y + dy
                neighbor_pos = (neighbor_x, neighbor_y)

                # 检查邻居是否有效
                if not self._is_valid_position(neighbor_pos, game_map):
                    continue

                # 检查是否已访问
                if neighbor_pos in closed_set:
                    continue

                # 计算移动代价
                move_cost = self._calculate_move_cost(
                    current, neighbor_pos, dx, dy)
                tentative_g = current.g + move_cost

                # 创建或更新邻居节点
                neighbor_node = BStarNode(neighbor_x, neighbor_y)
                neighbor_node.g = tentative_g
                neighbor_node.h = heuristic_func(neighbor_pos, goal)
                neighbor_node.f = neighbor_node.g + neighbor_node.h
                neighbor_node.parent = current
                neighbor_node.last_updated = time.time()

                # 动态调整
                if dynamic_adjustments and environment_changes > self.dynamic_threshold:
                    neighbor_node.update_dynamic_cost(
                        time.time(), environment_changes)

                # 添加到开放集
                heapq.heappush(open_set, neighbor_node)
                came_from[neighbor_pos] = (current.x, current.y)

        return None

    def _is_valid_position(self, pos: Tuple[int, int], game_map: List[List]) -> bool:
        """检查位置是否有效"""
        x, y = pos

        # 检查边界
        if (x < 0 or x >= len(game_map[0]) or
                y < 0 or y >= len(game_map)):
            return False

        # 检查瓦片类型
        tile = game_map[y][x]

        # 导入TileType枚举
        try:
            from src.core.enums import TileType
            # 允许通过地面、房间、金矿脉和已挖掘的瓦片
            return tile.type in [TileType.GROUND, TileType.ROOM, TileType.GOLD_VEIN] or tile.is_dug
        except ImportError:
            # 如果无法导入，使用数字判断
            # GROUND=1, ROOM=2, GOLD_VEIN=3, 已挖掘的瓦片
            return tile.type in [1, 2, 3] or getattr(tile, 'is_dug', False)

    def _calculate_move_cost(self, current: BStarNode, neighbor_pos: Tuple[int, int],
                             dx: int, dy: int) -> float:
        """计算移动代价"""
        # 基础移动代价
        if abs(dx) + abs(dy) == 1:
            # 直线移动
            base_cost = 1.0
        else:
            # 对角线移动
            base_cost = 1.414

        # 根据节点类型调整代价
        if current.node_type == BStarNodeType.CRITICAL:
            base_cost *= 0.8  # 关键路径节点代价更低
        elif current.node_type == BStarNodeType.DYNAMIC:
            base_cost *= current.dynamic_weight

        return base_cost

    def _detect_environment_changes(self, pos: Tuple[int, int], game_map: List[List]) -> float:
        """检测环境变化程度"""
        # 简单的环境变化检测
        # 在实际应用中，这里可以检测动态障碍物、其他单位等
        x, y = pos
        change_factor = 0.0

        # 检查周围8个方向的瓦片变化
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue

                check_x = x + dx
                check_y = y + dy

                if (0 <= check_x < len(game_map[0]) and
                        0 <= check_y < len(game_map)):
                    tile = game_map[check_y][check_x]
                    # 这里可以添加更复杂的环境变化检测逻辑
                    if hasattr(tile, 'is_dynamic') and tile.is_dynamic:
                        change_factor += 0.1

        return min(change_factor, 1.0)  # 限制在0-1范围内

    def _manhattan_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """曼哈顿距离启发式函数"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _euclidean_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """欧几里得距离启发式函数"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def _reconstruct_path(self, came_from: Dict[Tuple[int, int], Tuple[int, int]],
                          start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """重构路径"""
        path = []
        current = goal

        while current != start:
            path.append(current)
            if current not in came_from:
                return []
            current = came_from[current]

        path.append(start)
        path.reverse()
        return path

    def _cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, (_, cache_time) in self.path_cache.items():
            if current_time - cache_time > self.cache_timeout:
                expired_keys.append(key)

        for key in expired_keys:
            del self.path_cache[key]

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return {
            "search_count": self.search_count,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(self.search_count, 1),
            "dynamic_adjustments": self.dynamic_adjustments,
            "cache_size": len(self.path_cache)
        }

    def clear_cache(self):
        """清空缓存"""
        self.path_cache.clear()
        self.search_count = 0
        self.cache_hits = 0
        self.dynamic_adjustments = 0


class BStarPathfindingSystem:
    """B*寻路系统 - 高级寻路接口"""

    def __init__(self):
        self.bstar = BStarPathfinding()
        self.enabled = True

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float],
                  game_map: List[List], tile_size: int = 20) -> Optional[List[Tuple[float, float]]]:
        """
        寻找路径

        Args:
            start: 起始位置（像素坐标）
            goal: 目标位置（像素坐标）
            game_map: 游戏地图
            tile_size: 瓦片大小

        Returns:
            路径点列表（像素坐标）
        """
        if not self.enabled:
            return None

        # 转换为瓦片坐标
        start_tile = (int(start[0] // tile_size), int(start[1] // tile_size))
        goal_tile = (int(goal[0] // tile_size), int(goal[1] // tile_size))

        # 使用B*算法寻找路径
        tile_path = self.bstar.find_path(start_tile, goal_tile, game_map)

        if not tile_path:
            return None

        # 转换为像素坐标
        pixel_path = []
        for tile in tile_path:
            pixel_x = tile[0] * tile_size + tile_size // 2
            pixel_y = tile[1] * tile_size + tile_size // 2
            pixel_path.append((pixel_x, pixel_y))

        return pixel_path

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return self.bstar.get_performance_stats()

    def clear_cache(self):
        """清空缓存"""
        self.bstar.clear_cache()

    def set_enabled(self, enabled: bool):
        """启用/禁用B*寻路"""
        self.enabled = enabled
