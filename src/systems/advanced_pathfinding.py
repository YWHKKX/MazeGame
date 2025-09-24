#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级寻路系统 - 集成NavMesh和多种寻路算法

主要功能:
1. NavMesh寻路 - 基于导航网格的高效寻路
2. 混合寻路 - 结合网格和NavMesh的寻路策略
3. 路径优化 - 多种路径平滑和优化算法
4. 动态避障 - 实时避障和路径调整
"""

import math
import time
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .navmesh_system import NavMeshSystem, NavMeshNode
from ..core.constants import GameConstants


class PathfindingStrategy(Enum):
    """寻路策略"""
    NAVMESH = "navmesh"  # 导航网格寻路
    GRID_DFS = "grid_dfs"  # 网格DFS寻路
    HYBRID = "hybrid"  # 混合寻路
    FALLBACK = "fallback"  # 备用寻路


@dataclass
class PathfindingResult:
    """寻路结果"""
    success: bool
    path: Optional[List[Tuple[float, float]]]
    strategy_used: PathfindingStrategy
    execution_time: float
    path_length: int
    distance: float
    reason: str = ""


class AdvancedPathfindingSystem:
    """高级寻路系统"""

    def __init__(self, tile_size: int = GameConstants.TILE_SIZE):
        self.tile_size = tile_size
        self.navmesh_system = NavMeshSystem(tile_size)

        # 性能统计
        self.stats = {
            'navmesh_calls': 0,
            'grid_dfs_calls': 0,
            'hybrid_calls': 0,
            'fallback_calls': 0,
            'total_calls': 0,
            'successful_calls': 0,
            'average_time': 0.0
        }

        # 缓存
        self.path_cache: Dict[Tuple[Tuple[float, float],
                                    Tuple[float, float]], PathfindingResult] = {}
        self.cache_timeout = 5.0  # 缓存超时时间（秒）

    def initialize(self, game_map: List[List], map_width: int, map_height: int) -> bool:
        """初始化寻路系统"""
        print("🚀 初始化高级寻路系统...")

        # 生成导航网格
        success = self.navmesh_system.generate_navmesh(
            game_map, map_width, map_height)

        if success:
            print("✅ 高级寻路系统初始化完成")
        else:
            print("❌ 高级寻路系统初始化失败")

        return success

    def find_path(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                  game_map: List[List], strategy: PathfindingStrategy = PathfindingStrategy.HYBRID) -> PathfindingResult:
        """
        寻找路径

        Args:
            start_pos: 起始位置
            end_pos: 目标位置
            game_map: 游戏地图
            strategy: 寻路策略

        Returns:
            PathfindingResult: 寻路结果
        """
        start_time = time.time()
        self.stats['total_calls'] += 1

        # 检查缓存
        cache_key = (start_pos, end_pos)
        if cache_key in self.path_cache:
            cached_result = self.path_cache[cache_key]
            if time.time() - cached_result.execution_time < self.cache_timeout:
                return cached_result

        result = None

        # 根据策略选择寻路方法
        if strategy == PathfindingStrategy.NAVMESH:
            result = self._navmesh_pathfinding(start_pos, end_pos, game_map)
        elif strategy == PathfindingStrategy.GRID_DFS:
            result = self._grid_dfs_pathfinding(start_pos, end_pos, game_map)
        elif strategy == PathfindingStrategy.HYBRID:
            result = self._hybrid_pathfinding(start_pos, end_pos, game_map)
        elif strategy == PathfindingStrategy.FALLBACK:
            result = self._fallback_pathfinding(start_pos, end_pos, game_map)

        if result:
            execution_time = time.time() - start_time
            result.execution_time = execution_time

            # 更新统计
            self.stats[f'{result.strategy_used.value}_calls'] += 1
            if result.success:
                self.stats['successful_calls'] += 1

            # 更新平均时间
            total_time = self.stats['average_time'] * \
                (self.stats['total_calls'] - 1) + execution_time
            self.stats['average_time'] = total_time / self.stats['total_calls']

            # 缓存结果
            self.path_cache[cache_key] = result

            return result

        # 如果所有策略都失败
        return PathfindingResult(
            success=False,
            path=None,
            strategy_used=PathfindingStrategy.FALLBACK,
            execution_time=time.time() - start_time,
            path_length=0,
            distance=math.sqrt(
                (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2),
            reason="所有寻路策略都失败"
        )

    def _navmesh_pathfinding(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                             game_map: List[List]) -> PathfindingResult:
        """NavMesh寻路"""
        try:
            path = self.navmesh_system.find_path(start_pos, end_pos)

            if path:
                distance = self._calculate_path_distance(path)
                return PathfindingResult(
                    success=True,
                    path=path,
                    strategy_used=PathfindingStrategy.NAVMESH,
                    execution_time=0.0,  # 将在外部设置
                    path_length=len(path),
                    distance=distance,
                    reason="NavMesh寻路成功"
                )
            else:
                return PathfindingResult(
                    success=False,
                    path=None,
                    strategy_used=PathfindingStrategy.NAVMESH,
                    execution_time=0.0,
                    path_length=0,
                    distance=math.sqrt(
                        (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2),
                    reason="NavMesh未找到路径"
                )
        except Exception as e:
            return PathfindingResult(
                success=False,
                path=None,
                strategy_used=PathfindingStrategy.NAVMESH,
                execution_time=0.0,
                path_length=0,
                distance=math.sqrt(
                    (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2),
                reason=f"NavMesh寻路异常: {str(e)}"
            )

    def _grid_dfs_pathfinding(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                              game_map: List[List]) -> PathfindingResult:
        """网格DFS寻路"""
        try:
            # 转换为瓦片坐标
            start_tile = (
                int(start_pos[0] // self.tile_size), int(start_pos[1] // self.tile_size))
            end_tile = (int(end_pos[0] // self.tile_size),
                        int(end_pos[1] // self.tile_size))

            # 使用独立的DFS寻路
            is_reachable, path = self._dfs_path_find(
                start_tile, end_tile, game_map, 100)

            if is_reachable and path:
                # 转换为像素坐标路径
                pixel_path = []
                for tile in path:
                    pixel_x = tile[0] * self.tile_size + self.tile_size // 2
                    pixel_y = tile[1] * self.tile_size + self.tile_size // 2
                    pixel_path.append((pixel_x, pixel_y))

                distance = self._calculate_path_distance(pixel_path)
                return PathfindingResult(
                    success=True,
                    path=pixel_path,
                    strategy_used=PathfindingStrategy.GRID_DFS,
                    execution_time=0.0,
                    path_length=len(pixel_path),
                    distance=distance,
                    reason="网格DFS寻路成功"
                )
            else:
                return PathfindingResult(
                    success=False,
                    path=None,
                    strategy_used=PathfindingStrategy.GRID_DFS,
                    execution_time=0.0,
                    path_length=0,
                    distance=math.sqrt(
                        (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2),
                    reason="网格DFS未找到路径"
                )
        except Exception as e:
            return PathfindingResult(
                success=False,
                path=None,
                strategy_used=PathfindingStrategy.GRID_DFS,
                execution_time=0.0,
                path_length=0,
                distance=math.sqrt(
                    (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2),
                reason=f"网格DFS寻路异常: {str(e)}"
            )

    def _hybrid_pathfinding(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                            game_map: List[List]) -> PathfindingResult:
        """混合寻路策略"""
        # 首先尝试NavMesh寻路
        navmesh_result = self._navmesh_pathfinding(
            start_pos, end_pos, game_map)
        if navmesh_result.success:
            return navmesh_result

        # 如果NavMesh失败，尝试网格DFS
        grid_result = self._grid_dfs_pathfinding(start_pos, end_pos, game_map)
        if grid_result.success:
            return grid_result

        # 如果都失败，返回NavMesh的结果（包含错误信息）
        return navmesh_result

    def _fallback_pathfinding(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                              game_map: List[List]) -> PathfindingResult:
        """备用寻路策略"""
        # 简单的直线移动作为最后的备用方案
        distance = math.sqrt(
            (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)

        return PathfindingResult(
            success=True,
            path=[start_pos, end_pos],
            strategy_used=PathfindingStrategy.FALLBACK,
            execution_time=0.0,
            path_length=2,
            distance=distance,
            reason="使用直线移动作为备用方案"
        )

    def _dfs_path_find(self, start_tile: Tuple[int, int], target_tile: Tuple[int, int],
                       game_map: List[List], max_depth: int) -> Tuple[bool, Optional[List[Tuple[int, int]]]]:
        """独立的DFS寻路方法"""
        visited = set()
        search_count = 0
        best_path = None

        def dfs(current_tile: Tuple[int, int], depth: int, current_path: List[Tuple[int, int]]) -> Tuple[bool, List[Tuple[int, int]]]:
            nonlocal search_count, best_path
            search_count += 1

            # 检查深度限制
            if depth > max_depth:
                return False, current_path

            # 检查是否到达目标
            if current_tile == target_tile:
                final_path = current_path + [current_tile]
                best_path = final_path
                return True, final_path

            # 检查是否已访问
            if current_tile in visited:
                return False, current_path

            # 检查位置是否有效
            if not self._is_valid_position(current_tile, game_map):
                return False, current_path

            # 标记为已访问
            visited.add(current_tile)
            new_path = current_path + [current_tile]

            # 优化搜索顺序：优先搜索朝向目标的方向
            dx_to_target = target_tile[0] - current_tile[0]
            dy_to_target = target_tile[1] - current_tile[1]

            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if dx_to_target != 0:
                directions.sort(key=lambda d: abs(
                    d[0] - (1 if dx_to_target > 0 else -1)))
            if dy_to_target != 0:
                directions.sort(key=lambda d: abs(
                    d[1] - (1 if dy_to_target > 0 else -1)))

            for dx, dy in directions:
                next_tile = (current_tile[0] + dx, current_tile[1] + dy)
                found, result_path = dfs(next_tile, depth + 1, new_path)
                if found:
                    return True, result_path

            return False, current_path

        # 开始搜索
        found, path = dfs(start_tile, 0, [])

        if found and path:
            return True, path
        else:
            # 如果没找到路径，返回最佳路径（如果存在）
            if best_path:
                return True, best_path
            return False, None

    def _is_valid_position(self, pos: Tuple[int, int], game_map: List[List]) -> bool:
        """检查位置是否有效"""
        x, y = pos
        if not (0 <= x < len(game_map[0]) and 0 <= y < len(game_map)):
            return False

        tile = game_map[y][x]
        return tile.type.name in ['GROUND', 'ROOM'] or tile.is_dug

    def _calculate_path_distance(self, path: List[Tuple[float, float]]) -> float:
        """计算路径总距离"""
        if len(path) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(path) - 1):
            dx = path[i+1][0] - path[i][0]
            dy = path[i+1][1] - path[i][1]
            total_distance += math.sqrt(dx * dx + dy * dy)

        return total_distance

    def optimize_path(self, path: List[Tuple[float, float]], game_map: List[List]) -> List[Tuple[float, float]]:
        """路径优化"""
        if len(path) < 3:
            return path

        optimized = [path[0]]

        i = 0
        while i < len(path) - 1:
            # 寻找最远的可见点
            j = len(path) - 1
            while j > i + 1:
                if self._is_line_of_sight(path[i], path[j], game_map):
                    optimized.append(path[j])
                    i = j
                    break
                j -= 1
            else:
                # 如果没有找到可见点，移动到下一个点
                i += 1
                if i < len(path):
                    optimized.append(path[i])

        return optimized

    def _is_line_of_sight(self, start: Tuple[float, float], end: Tuple[float, float],
                          game_map: List[List]) -> bool:
        """检查两点间是否有视线（无障碍物）"""
        # 简化的视线检查：检查路径上的瓦片
        steps = int(max(abs(end[0] - start[0]),
                    abs(end[1] - start[1])) / self.tile_size) + 1

        for i in range(steps + 1):
            t = i / steps
            x = start[0] + t * (end[0] - start[0])
            y = start[1] + t * (end[1] - start[1])

            tile_x = int(x // self.tile_size)
            tile_y = int(y // self.tile_size)

            if not (0 <= tile_x < len(game_map[0]) and 0 <= tile_y < len(game_map)):
                return False

            tile = game_map[tile_y][tile_x]
            if tile.type.name == 'ROCK' and not tile.is_dug:
                return False

        return True

    def update_map(self, changed_tiles: List[Tuple[int, int]], game_map: List[List]):
        """更新地图变化"""
        if changed_tiles:
            self.navmesh_system.update_navmesh(changed_tiles, game_map)
            # 清除相关缓存
            self._clear_affected_cache(changed_tiles)

    def _clear_affected_cache(self, changed_tiles: List[Tuple[int, int]]):
        """清除受影响的缓存"""
        # 简化的缓存清理：清除所有缓存
        # 在实际应用中，可以实现更精确的缓存清理
        self.path_cache.clear()

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        success_rate = (self.stats['successful_calls'] / self.stats['total_calls']
                        * 100) if self.stats['total_calls'] > 0 else 0

        return {
            'total_calls': self.stats['total_calls'],
            'successful_calls': self.stats['successful_calls'],
            'success_rate': f"{success_rate:.1f}%",
            'average_time': f"{self.stats['average_time']*1000:.2f}ms",
            'navmesh_calls': self.stats['navmesh_calls'],
            'grid_dfs_calls': self.stats['grid_dfs_calls'],
            'hybrid_calls': self.stats['hybrid_calls'],
            'fallback_calls': self.stats['fallback_calls'],
            'cache_size': len(self.path_cache)
        }

    def render_debug(self, screen, camera_x: int, camera_y: int):
        """渲染调试信息"""
        self.navmesh_system.render_debug(screen, camera_x, camera_y)
