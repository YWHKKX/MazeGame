#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一寻路系统 - 重构并优化所有寻路逻辑

核心特性:
1. 统一的寻路接口 - 整合所有寻路算法
2. 智能算法选择 - 根据场景自动选择最佳算法
3. 性能优化 - 缓存、预计算、增量更新
4. 动态调整 - 实时适应环境变化
5. 多策略支持 - B*、A*、DFS、NavMesh等
"""

import math
import time
import heapq
from typing import List, Tuple, Optional, Dict, Any, Union, Callable
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod

from ..core.constants import GameConstants
from ..core.enums import TileType


class PathfindingStrategy(Enum):
    """寻路策略枚举"""
    B_STAR = "b_star"           # B*算法 - 动态调整
    A_STAR = "a_star"           # A*算法 - 经典寻路
    DFS = "dfs"                 # 深度优先搜索 - 简单场景
    NAVMESH = "navmesh"         # 导航网格 - 复杂地形
    HYBRID = "hybrid"           # 混合策略 - 自动选择
    RECTANGULAR = "rectangular"  # 矩形路径 - 简单移动


class PathfindingResult:
    """寻路结果"""

    def __init__(self, success: bool, path: Optional[List[Tuple[float, float]]] = None,
                 algorithm: str = "", cost: float = 0.0, time_ms: float = 0.0):
        self.success = success
        self.path = path or []
        self.algorithm = algorithm
        self.cost = cost
        self.time_ms = time_ms
        self.timestamp = time.time()


@dataclass
class PathfindingConfig:
    """寻路配置"""
    max_iterations: int = 1000
    cache_timeout: float = 5.0
    dynamic_threshold: float = 0.1
    enable_caching: bool = True
    enable_dynamic_adjustment: bool = True
    fallback_strategies: List[PathfindingStrategy] = None

    def __post_init__(self):
        if self.fallback_strategies is None:
            self.fallback_strategies = [
                PathfindingStrategy.B_STAR,
                PathfindingStrategy.A_STAR,
                PathfindingStrategy.DFS
            ]


class PathfindingAlgorithm(ABC):
    """寻路算法基类"""

    def __init__(self, config: PathfindingConfig):
        self.config = config
        self.stats = {
            'calls': 0,
            'successes': 0,
            'total_time': 0.0,
            'cache_hits': 0
        }

    @abstractmethod
    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float],
                  game_map: List[List], **kwargs) -> PathfindingResult:
        """寻找路径"""
        pass

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self.stats,
            'success_rate': self.stats['successes'] / max(self.stats['calls'], 1),
            'avg_time': self.stats['total_time'] / max(self.stats['calls'], 1)
        }


class BStarAlgorithm(PathfindingAlgorithm):
    """B*算法实现"""

    def __init__(self, config: PathfindingConfig):
        super().__init__(config)
        self.cache: Dict[Tuple, Tuple[PathfindingResult, float]] = {}

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float],
                  game_map: List[List], **kwargs) -> PathfindingResult:
        """B*算法寻路"""
        start_time = time.time()
        self.stats['calls'] += 1

        # 检查缓存
        cache_key = (start, goal, int(kwargs.get('dynamic_adjustments', True)))
        if self.config.enable_caching and cache_key in self.cache:
            result, cache_time = self.cache[cache_key]
            if time.time() - cache_time < self.config.cache_timeout:
                self.stats['cache_hits'] += 1
                return result

        # 转换为瓦片坐标
        start_tile = (int(start[0] // GameConstants.TILE_SIZE),
                      int(start[1] // GameConstants.TILE_SIZE))
        goal_tile = (int(goal[0] // GameConstants.TILE_SIZE),
                     int(goal[1] // GameConstants.TILE_SIZE))

        # 执行B*搜索
        path = self._bstar_search(start_tile, goal_tile, game_map, **kwargs)

        # 转换为像素坐标
        pixel_path = None
        if path:
            pixel_path = []
            for tile in path:
                pixel_x = tile[0] * GameConstants.TILE_SIZE + \
                    GameConstants.TILE_SIZE // 2
                pixel_y = tile[1] * GameConstants.TILE_SIZE + \
                    GameConstants.TILE_SIZE // 2
                pixel_path.append((pixel_x, pixel_y))

        # 创建结果
        result = PathfindingResult(
            success=path is not None,
            path=pixel_path,
            algorithm="B*",
            time_ms=(time.time() - start_time) * 1000
        )

        if result.success:
            self.stats['successes'] += 1

        self.stats['total_time'] += result.time_ms

        # 缓存结果
        if self.config.enable_caching:
            self.cache[cache_key] = (result, time.time())

        return result

    def _bstar_search(self, start: Tuple[int, int], goal: Tuple[int, int],
                      game_map: List[List], **kwargs) -> Optional[List[Tuple[int, int]]]:
        """B*搜索核心算法"""
        from .bstar_pathfinding import BStarPathfinding

        bstar = BStarPathfinding(
            max_iterations=self.config.max_iterations,
            dynamic_threshold=self.config.dynamic_threshold
        )

        return bstar.find_path(
            start, goal, game_map,
            dynamic_adjustments=kwargs.get('dynamic_adjustments', True)
        )


class AStarAlgorithm(PathfindingAlgorithm):
    """A*算法实现"""

    def __init__(self, config: PathfindingConfig):
        super().__init__(config)
        self.cache: Dict[Tuple, Tuple[PathfindingResult, float]] = {}

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float],
                  game_map: List[List], **kwargs) -> PathfindingResult:
        """A*算法寻路"""
        start_time = time.time()
        self.stats['calls'] += 1

        # 检查缓存
        cache_key = (start, goal)
        if self.config.enable_caching and cache_key in self.cache:
            result, cache_time = self.cache[cache_key]
            if time.time() - cache_time < self.config.cache_timeout:
                self.stats['cache_hits'] += 1
                return result

        # 转换为瓦片坐标
        start_tile = (int(start[0] // GameConstants.TILE_SIZE),
                      int(start[1] // GameConstants.TILE_SIZE))
        goal_tile = (int(goal[0] // GameConstants.TILE_SIZE),
                     int(goal[1] // GameConstants.TILE_SIZE))

        # 执行A*搜索
        path = self._astar_search(start_tile, goal_tile, game_map)

        # 转换为像素坐标
        pixel_path = None
        if path:
            pixel_path = []
            for tile in path:
                pixel_x = tile[0] * GameConstants.TILE_SIZE + \
                    GameConstants.TILE_SIZE // 2
                pixel_y = tile[1] * GameConstants.TILE_SIZE + \
                    GameConstants.TILE_SIZE // 2
                pixel_path.append((pixel_x, pixel_y))

        # 创建结果
        result = PathfindingResult(
            success=path is not None,
            path=pixel_path,
            algorithm="A*",
            time_ms=(time.time() - start_time) * 1000
        )

        if result.success:
            self.stats['successes'] += 1

        self.stats['total_time'] += result.time_ms

        # 缓存结果
        if self.config.enable_caching:
            self.cache[cache_key] = (result, time.time())

        return result

    def _astar_search(self, start: Tuple[int, int], goal: Tuple[int, int],
                      game_map: List[List]) -> Optional[List[Tuple[int, int]]]:
        """A*搜索核心算法"""
        open_set = []
        closed_set = set()
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self._heuristic(start, goal)}

        heapq.heappush(open_set, (f_score[start], start))

        iterations = 0
        while open_set and iterations < self.config.max_iterations:
            iterations += 1
            current_f, current = heapq.heappop(open_set)

            if current in closed_set:
                continue

            closed_set.add(current)

            if current == goal:
                return self._reconstruct_path(came_from, start, goal)

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]:
                neighbor = (current[0] + dx, current[1] + dy)

                if not self._is_valid_position(neighbor, game_map):
                    continue

                if neighbor in closed_set:
                    continue

                tentative_g = g_score[current] + \
                    self._get_move_cost(current, neighbor)

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + \
                        self._heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None

    def _heuristic(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """启发式函数"""
        dx = abs(pos1[0] - pos2[0])
        dy = abs(pos1[1] - pos2[1])
        return max(dx, dy) + (1.414 - 1) * min(dx, dy)

    def _get_move_cost(self, current: Tuple[int, int], neighbor: Tuple[int, int]) -> float:
        """获取移动代价"""
        dx = abs(neighbor[0] - current[0])
        dy = abs(neighbor[1] - current[1])
        return 1.414 if dx == 1 and dy == 1 else 1.0

    def _is_valid_position(self, pos: Tuple[int, int], game_map: List[List]) -> bool:
        """检查位置是否有效"""
        x, y = pos
        if (x < 0 or x >= len(game_map[0]) or y < 0 or y >= len(game_map)):
            return False

        tile = game_map[y][x]

        # 检查瓦片类型是否可通行
        if tile.type not in [TileType.GROUND, TileType.ROOM, TileType.GOLD_VEIN] and not tile.is_dug:
            return False

        # 检查是否有建筑阻挡（建造中的建筑不阻挡）
        if hasattr(tile, 'building') and tile.building:
            building = tile.building
            # 只有已完成的建筑才阻挡寻路，建造中的建筑不阻挡
            from src.entities.building import BuildingStatus
            if building.status == BuildingStatus.COMPLETED:
                return False

        return True

    def _reconstruct_path(self, came_from: Dict, start: Tuple[int, int], goal: Tuple[int, int]) -> List[Tuple[int, int]]:
        """重构路径"""
        path = []
        current = goal
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        return path


class DFSAlgorithm(PathfindingAlgorithm):
    """DFS算法实现"""

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float],
                  game_map: List[List], **kwargs) -> PathfindingResult:
        """DFS算法寻路"""
        start_time = time.time()
        self.stats['calls'] += 1

        # 转换为瓦片坐标
        start_tile = (int(start[0] // GameConstants.TILE_SIZE),
                      int(start[1] // GameConstants.TILE_SIZE))
        goal_tile = (int(goal[0] // GameConstants.TILE_SIZE),
                     int(goal[1] // GameConstants.TILE_SIZE))

        # 执行DFS搜索
        path = self._dfs_search(start_tile, goal_tile, game_map)

        # 转换为像素坐标
        pixel_path = None
        if path:
            pixel_path = []
            for tile in path:
                pixel_x = tile[0] * GameConstants.TILE_SIZE + \
                    GameConstants.TILE_SIZE // 2
                pixel_y = tile[1] * GameConstants.TILE_SIZE + \
                    GameConstants.TILE_SIZE // 2
                pixel_path.append((pixel_x, pixel_y))

        # 创建结果
        result = PathfindingResult(
            success=path is not None,
            path=pixel_path,
            algorithm="DFS",
            time_ms=(time.time() - start_time) * 1000
        )

        if result.success:
            self.stats['successes'] += 1

        self.stats['total_time'] += result.time_ms

        return result

    def _dfs_search(self, start: Tuple[int, int], goal: Tuple[int, int],
                    game_map: List[List], max_depth: int = 100) -> Optional[List[Tuple[int, int]]]:
        """DFS搜索核心算法"""
        visited = set()

        def dfs(current: Tuple[int, int], depth: int, path: List[Tuple[int, int]]) -> Optional[List[Tuple[int, int]]]:
            if depth > max_depth:
                return None

            if current == goal:
                return path + [current]

            if current in visited:
                return None

            if not self._is_valid_position(current, game_map):
                return None

            visited.add(current)
            new_path = path + [current]

            # 优化搜索顺序：优先朝向目标
            dx_to_goal = goal[0] - current[0]
            dy_to_goal = goal[1] - current[1]

            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            if dx_to_goal != 0:
                directions.sort(key=lambda d: abs(
                    d[0] - (1 if dx_to_goal > 0 else -1)))
            if dy_to_goal != 0:
                directions.sort(key=lambda d: abs(
                    d[1] - (1 if dy_to_goal > 0 else -1)))

            for dx, dy in directions:
                neighbor = (current[0] + dx, current[1] + dy)
                result = dfs(neighbor, depth + 1, new_path)
                if result:
                    return result

            return None

        return dfs(start, 0, [])

    def _is_valid_position(self, pos: Tuple[int, int], game_map: List[List]) -> bool:
        """检查位置是否有效"""
        x, y = pos
        if (x < 0 or x >= len(game_map[0]) or y < 0 or y >= len(game_map)):
            return False

        tile = game_map[y][x]

        # 检查瓦片类型是否可通行
        if tile.type not in [TileType.GROUND, TileType.ROOM, TileType.GOLD_VEIN] and not tile.is_dug:
            return False

        # 检查是否有建筑阻挡（建造中的建筑不阻挡）
        if hasattr(tile, 'building') and tile.building:
            building = tile.building
            # 只有已完成的建筑才阻挡寻路，建造中的建筑不阻挡
            from src.entities.building import BuildingStatus
            if building.status == BuildingStatus.COMPLETED:
                return False

        return True


class NavMeshAlgorithm(PathfindingAlgorithm):
    """NavMesh算法实现"""

    def __init__(self, config: PathfindingConfig):
        super().__init__(config)
        self.navmesh_system = None

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float],
                  game_map: List[List], **kwargs) -> PathfindingResult:
        """NavMesh算法寻路"""
        start_time = time.time()
        self.stats['calls'] += 1

        # 初始化NavMesh系统
        if self.navmesh_system is None:
            from .navmesh_system import NavMeshSystem
            self.navmesh_system = NavMeshSystem(GameConstants.TILE_SIZE)
            self.navmesh_system.generate_navmesh(game_map)

        # 使用NavMesh寻路
        path = self.navmesh_system.find_path(start, goal)

        # 创建结果
        result = PathfindingResult(
            success=path is not None,
            path=path,
            algorithm="NavMesh",
            time_ms=(time.time() - start_time) * 1000
        )

        if result.success:
            self.stats['successes'] += 1

        self.stats['total_time'] += result.time_ms

        return result


class UnifiedPathfindingSystem:
    """统一寻路系统"""

    def __init__(self, config: PathfindingConfig = None):
        self.config = config or PathfindingConfig()
        self.algorithms = {
            PathfindingStrategy.B_STAR: BStarAlgorithm(self.config),
            PathfindingStrategy.A_STAR: AStarAlgorithm(self.config),
            PathfindingStrategy.DFS: DFSAlgorithm(self.config),
            PathfindingStrategy.NAVMESH: NavMeshAlgorithm(self.config)
        }
        self.global_stats = {
            'total_calls': 0,
            'total_successes': 0,
            'total_time': 0.0
        }

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float],
                  game_map: List[List], strategy: PathfindingStrategy = PathfindingStrategy.HYBRID,
                  **kwargs) -> PathfindingResult:
        """统一寻路接口"""
        start_time = time.time()
        self.global_stats['total_calls'] += 1

        # 选择算法
        if strategy == PathfindingStrategy.HYBRID:
            strategy = self._select_best_strategy(start, goal, game_map)

        # 执行寻路
        if strategy in self.algorithms:
            result = self.algorithms[strategy].find_path(
                start, goal, game_map, **kwargs)
        else:
            # 回退到默认策略
            result = self.algorithms[PathfindingStrategy.B_STAR].find_path(
                start, goal, game_map, **kwargs)

        # 如果失败，尝试回退策略
        if not result.success and strategy != PathfindingStrategy.DFS:
            for fallback_strategy in self.config.fallback_strategies:
                if fallback_strategy != strategy and fallback_strategy in self.algorithms:
                    fallback_result = self.algorithms[fallback_strategy].find_path(
                        start, goal, game_map, **kwargs)
                    if fallback_result.success:
                        result = fallback_result
                        result.algorithm += f" (fallback from {strategy.value})"
                        break

        # 更新全局统计
        if result.success:
            self.global_stats['total_successes'] += 1

        self.global_stats['total_time'] += (time.time() - start_time) * 1000

        return result

    def _select_best_strategy(self, start: Tuple[float, float], goal: Tuple[float, float],
                              game_map: List[List]) -> PathfindingStrategy:
        """选择最佳寻路策略"""
        # 计算距离
        distance = math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)

        # 根据距离和复杂度选择策略
        if distance < 100:  # 短距离
            return PathfindingStrategy.DFS
        elif distance < 500:  # 中等距离
            return PathfindingStrategy.B_STAR
        else:  # 长距离
            return PathfindingStrategy.NAVMESH

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        algorithm_stats = {}
        for strategy, algorithm in self.algorithms.items():
            algorithm_stats[strategy.value] = algorithm.get_performance_stats()

        return {
            'global': {
                **self.global_stats,
                'success_rate': self.global_stats['total_successes'] / max(self.global_stats['total_calls'], 1),
                'avg_time': self.global_stats['total_time'] / max(self.global_stats['total_calls'], 1)
            },
            'algorithms': algorithm_stats
        }

    def clear_cache(self):
        """清空所有缓存"""
        for algorithm in self.algorithms.values():
            if hasattr(algorithm, 'cache'):
                algorithm.cache.clear()

    def update_config(self, new_config: PathfindingConfig):
        """更新配置"""
        self.config = new_config
        for algorithm in self.algorithms.values():
            algorithm.config = new_config
