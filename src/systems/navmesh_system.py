#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导航网格系统 - 基于凸多边形的寻路系统

主要功能:
1. 导航网格生成 - 将可行走区域划分为凸多边形
2. 路径查找 - 在导航网格上寻找最优路径
3. 路径平滑 - 生成自然的移动路径
4. 动态更新 - 支持地图变化时的网格更新
"""

import math
import pygame
from typing import List, Tuple, Optional, Set, Dict, Any
from dataclasses import dataclass
from src.utils.logger import game_logger
from enum import Enum
import heapq
from .bstar_pathfinding import BStarPathfinding


class NavMeshNodeType(Enum):
    """导航网格节点类型"""
    WALKABLE = "walkable"
    OBSTACLE = "obstacle"
    BOUNDARY = "boundary"


@dataclass
class NavMeshNode:
    """导航网格节点"""
    id: int
    center: Tuple[float, float]  # 节点中心点
    vertices: List[Tuple[float, float]]  # 多边形顶点
    neighbors: List[int]  # 相邻节点ID列表
    node_type: NavMeshNodeType
    area: float = 0.0  # 节点面积
    is_connected: bool = True  # 是否与主网络连通

    def __post_init__(self):
        """计算节点面积"""
        if len(self.vertices) >= 3:
            self.area = self._calculate_polygon_area()

    def _calculate_polygon_area(self) -> float:
        """计算多边形面积（使用鞋带公式）"""
        n = len(self.vertices)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self.vertices[i][0] * self.vertices[j][1]
            area -= self.vertices[j][0] * self.vertices[i][1]
        return abs(area) / 2.0

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """检查点是否在多边形内"""
        x, y = point
        n = len(self.vertices)
        inside = False

        p1x, p1y = self.vertices[0]
        for i in range(1, n + 1):
            p2x, p2y = self.vertices[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / \
                                (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def get_center(self) -> Tuple[float, float]:
        """获取多边形中心点"""
        if not self.vertices:
            return self.center

        x_sum = sum(v[0] for v in self.vertices)
        y_sum = sum(v[1] for v in self.vertices)
        return (x_sum / len(self.vertices), y_sum / len(self.vertices))


@dataclass
class NavMeshEdge:
    """导航网格边"""
    start_node: int
    end_node: int
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    length: float
    is_boundary: bool = False

    def __post_init__(self):
        """计算边长"""
        dx = self.end_point[0] - self.start_point[0]
        dy = self.end_point[1] - self.start_point[1]
        self.length = math.sqrt(dx * dx + dy * dy)


class NavMeshSystem:
    """导航网格系统"""

    def __init__(self, tile_size: int = 20):
        self.tile_size = tile_size
        self.nodes: Dict[int, NavMeshNode] = {}
        self.edges: List[NavMeshEdge] = []
        self.node_id_counter = 0
        self.spatial_hash: Dict[Tuple[int, int], List[int]] = {}
        self.hash_cell_size = tile_size * 2

    def generate_navmesh(self, game_map: List[List], map_width: int, map_height: int) -> bool:
        """
        生成导航网格

        Args:
            game_map: 游戏地图
            map_width: 地图宽度
            map_height: 地图高度

        Returns:
            bool: 是否成功生成
        """
        game_logger.info("🏗️ 开始生成导航网格...")

        # 清空现有数据
        self.nodes.clear()
        self.edges.clear()
        self.spatial_hash.clear()
        self.node_id_counter = 0

        # 1. 识别可行走区域
        walkable_regions = self._identify_walkable_regions(
            game_map, map_width, map_height)
        game_logger.info(f"   发现 {len(walkable_regions)} 个可行走区域")

        # 2. 为每个区域生成凸多边形
        for region in walkable_regions:
            self._create_polygon_for_region(region, game_map)

        # 3. 连接相邻的多边形
        self._connect_adjacent_polygons()

        # 4. 构建空间哈希表
        self._build_spatial_hash()

        game_logger.info(
            f"✅ 导航网格生成完成: {len(self.nodes)} 个节点, {len(self.edges)} 条边")
        return True

    def _identify_walkable_regions(self, game_map: List[List], map_width: int, map_height: int) -> List[List[Tuple[int, int]]]:
        """识别可行走区域"""
        regions = []
        visited = set()

        for y in range(map_height):
            for x in range(map_width):
                if (x, y) not in visited and self._is_walkable_tile(x, y, game_map):
                    region = self._flood_fill_region(x, y, game_map, visited)
                    if len(region) > 1:  # 只保留足够大的区域
                        regions.append(region)

        return regions

    def _is_walkable_tile(self, x: int, y: int, game_map: List[List]) -> bool:
        """检查瓦片是否可行走"""
        if not (0 <= x < len(game_map[0]) and 0 <= y < len(game_map)):
            return False

        tile = game_map[y][x]
        return tile.type.name in ['GROUND', 'ROOM'] or tile.is_dug

    def _flood_fill_region(self, start_x: int, start_y: int, game_map: List[List], visited: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """使用洪水填充算法识别连通区域"""
        region = []
        stack = [(start_x, start_y)]

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue

            if not self._is_walkable_tile(x, y, game_map):
                continue

            visited.add((x, y))
            region.append((x, y))

            # 检查4个相邻方向
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in visited:
                    stack.append((nx, ny))

        return region

    def _create_polygon_for_region(self, region: List[Tuple[int, int]], game_map: List[List]):
        """为区域创建凸多边形"""
        if len(region) < 3:
            return

        # 将大区域分割成更小的子区域
        sub_regions = self._split_region_into_subregions(region)

        for sub_region in sub_regions:
            if len(sub_region) < 3:
                continue

            # 计算子区域的边界框
            min_x = min(pos[0] for pos in sub_region) * self.tile_size
            max_x = (max(pos[0] for pos in sub_region) + 1) * self.tile_size
            min_y = min(pos[1] for pos in sub_region) * self.tile_size
            max_y = (max(pos[1] for pos in sub_region) + 1) * self.tile_size

            # 创建矩形多边形
            vertices = [
                (min_x, min_y),
                (max_x, min_y),
                (max_x, max_y),
                (min_x, max_y)
            ]

            # 创建导航网格节点
            node_id = self.node_id_counter
            self.node_id_counter += 1

            center = ((min_x + max_x) / 2, (min_y + max_y) / 2)

            node = NavMeshNode(
                id=node_id,
                center=center,
                vertices=vertices,
                neighbors=[],
                node_type=NavMeshNodeType.WALKABLE
            )

            self.nodes[node_id] = node

    def _split_region_into_subregions(self, region: List[Tuple[int, int]], max_size: int = 5) -> List[List[Tuple[int, int]]]:
        """将大区域分割成更小的子区域"""
        if len(region) <= max_size:
            return [region]

        # 计算区域的边界
        min_x = min(pos[0] for pos in region)
        max_x = max(pos[0] for pos in region)
        min_y = min(pos[1] for pos in region)
        max_y = max(pos[1] for pos in region)

        # 计算分割点
        mid_x = (min_x + max_x) // 2
        mid_y = (min_y + max_y) // 2

        # 分割成4个子区域
        sub_regions = []

        # 左上
        top_left = [pos for pos in region if pos[0]
                    <= mid_x and pos[1] <= mid_y]
        if top_left:
            sub_regions.extend(
                self._split_region_into_subregions(top_left, max_size))

        # 右上
        top_right = [pos for pos in region if pos[0]
                     > mid_x and pos[1] <= mid_y]
        if top_right:
            sub_regions.extend(
                self._split_region_into_subregions(top_right, max_size))

        # 左下
        bottom_left = [pos for pos in region if pos[0]
                       <= mid_x and pos[1] > mid_y]
        if bottom_left:
            sub_regions.extend(
                self._split_region_into_subregions(bottom_left, max_size))

        # 右下
        bottom_right = [pos for pos in region if pos[0]
                        > mid_x and pos[1] > mid_y]
        if bottom_right:
            sub_regions.extend(
                self._split_region_into_subregions(bottom_right, max_size))

        return sub_regions

    def _connect_adjacent_polygons(self):
        """连接相邻的多边形"""
        node_list = list(self.nodes.values())

        for i, node1 in enumerate(node_list):
            for j, node2 in enumerate(node_list[i+1:], i+1):
                if self._are_polygons_adjacent(node1, node2):
                    # 添加双向连接
                    node1.neighbors.append(node2.id)
                    node2.neighbors.append(node1.id)

                    # 创建边
                    edge = NavMeshEdge(
                        start_node=node1.id,
                        end_node=node2.id,
                        start_point=node1.center,
                        end_point=node2.center,
                        length=self._calculate_distance(
                            node1.center, node2.center)
                    )
                    self.edges.append(edge)
                    game_logger.info(
                        f"   连接节点 {node1.id} 和 {node2.id}, 距离: {edge.length:.1f}")

    def _are_polygons_adjacent(self, node1: NavMeshNode, node2: NavMeshNode) -> bool:
        """检查两个多边形是否相邻"""
        # 首先检查两个多边形是否重叠或相邻
        if self._polygons_overlap_or_adjacent(node1, node2):
            return True

        # 如果边检查失败，使用距离检查作为备用
        distance = self._calculate_distance(node1.center, node2.center)
        max_distance = self.tile_size * 3  # 增加最大距离

        return distance <= max_distance

    def _polygons_overlap_or_adjacent(self, node1: NavMeshNode, node2: NavMeshNode) -> bool:
        """检查两个多边形是否重叠或相邻"""
        # 检查边界框是否相交或相邻
        min1_x = min(v[0] for v in node1.vertices)
        max1_x = max(v[0] for v in node1.vertices)
        min1_y = min(v[1] for v in node1.vertices)
        max1_y = max(v[1] for v in node1.vertices)

        min2_x = min(v[0] for v in node2.vertices)
        max2_x = max(v[0] for v in node2.vertices)
        min2_y = min(v[1] for v in node2.vertices)
        max2_y = max(v[1] for v in node2.vertices)

        # 检查是否相交
        if (min1_x <= max2_x and max1_x >= min2_x and
                min1_y <= max2_y and max1_y >= min2_y):
            return True

        # 检查是否相邻（边界框之间有小的间隙）
        gap_x = max(0, min1_x - max2_x) + max(0, min2_x - max1_x)
        gap_y = max(0, min1_y - max2_y) + max(0, min2_y - max1_y)

        return gap_x <= self.tile_size and gap_y <= self.tile_size

    def _points_are_close(self, p1: Tuple[float, float], p2: Tuple[float, float],
                          tolerance: float = 1.0) -> bool:
        """检查两个点是否足够接近"""
        dx = abs(p1[0] - p2[0])
        dy = abs(p1[1] - p2[1])
        return dx <= tolerance and dy <= tolerance

    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """计算两点间距离"""
        dx = pos2[0] - pos1[0]
        dy = pos2[1] - pos1[1]
        return math.sqrt(dx * dx + dy * dy)

    def _build_spatial_hash(self):
        """构建空间哈希表"""
        for node in self.nodes.values():
            center = node.center
            hash_x = int(center[0] // self.hash_cell_size)
            hash_y = int(center[1] // self.hash_cell_size)

            key = (hash_x, hash_y)
            if key not in self.spatial_hash:
                self.spatial_hash[key] = []
            self.spatial_hash[key].append(node.id)

    def find_path(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float]) -> Optional[List[Tuple[float, float]]]:
        """
        在导航网格中寻找路径

        Args:
            start_pos: 起始位置
            end_pos: 目标位置

        Returns:
            Optional[List[Tuple[float, float]]]: 路径点列表，如果找不到路径返回None
        """
        # 1. 找到起始和结束位置所在的节点
        start_node = self._find_node_containing_point(start_pos)
        end_node = self._find_node_containing_point(end_pos)

        if not start_node or not end_node:
            return None

        if start_node.id == end_node.id:
            # 在同一节点内，直接返回直线路径
            return [start_pos, end_pos]

        # 2. 使用B*算法在导航网格中寻路
        path_nodes = self._bstar_search(start_node, end_node)
        if not path_nodes:
            return None

        # 3. 生成路径点
        path_points = [start_pos]
        for node in path_nodes[1:-1]:  # 跳过起始和结束节点
            path_points.append(node.center)
        path_points.append(end_pos)

        # 4. 路径平滑
        smoothed_path = self._smooth_path(path_points)

        return smoothed_path

    def _find_node_containing_point(self, point: Tuple[float, float]) -> Optional[NavMeshNode]:
        """找到包含指定点的节点"""
        # 首先尝试使用空间哈希表快速查找
        hash_x = int(point[0] // self.hash_cell_size)
        hash_y = int(point[1] // self.hash_cell_size)

        # 检查周围的哈希格子
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                key = (hash_x + dx, hash_y + dy)
                if key in self.spatial_hash:
                    for node_id in self.spatial_hash[key]:
                        node = self.nodes[node_id]
                        if node.contains_point(point):
                            return node

        # 如果空间哈希表失败，遍历所有节点
        for node in self.nodes.values():
            if node.contains_point(point):
                return node

        # 如果仍然找不到，返回最近的节点
        closest_node = None
        min_distance = float('inf')

        for node in self.nodes.values():
            distance = self._calculate_distance(point, node.center)
            if distance < min_distance:
                min_distance = distance
                closest_node = node

        return closest_node

    def _bstar_search(self, start_node: NavMeshNode, end_node: NavMeshNode) -> Optional[List[NavMeshNode]]:
        """使用B*算法在导航网格中搜索路径"""

        # 创建B*寻路实例
        bstar = BStarPathfinding(max_iterations=1000, dynamic_threshold=0.1)

        # 将NavMesh节点转换为瓦片坐标进行B*搜索
        start_tile = (int(start_node.center[0] // self.tile_size),
                      int(start_node.center[1] // self.tile_size))
        end_tile = (int(end_node.center[0] // self.tile_size),
                    int(end_node.center[1] // self.tile_size))

        # 创建简化的地图用于B*搜索
        simplified_map = self._create_simplified_map()

        # 使用B*算法搜索路径
        tile_path = bstar.find_path(start_tile, end_tile, simplified_map,
                                    dynamic_adjustments=True)

        if not tile_path:
            return None

        # 将瓦片路径转换回NavMesh节点
        return self._convert_tile_path_to_navmesh_nodes(tile_path)

    def _create_simplified_map(self) -> List[List]:
        """创建简化的地图用于B*搜索"""
        # 这里创建一个简化的地图表示
        # 在实际实现中，可以根据NavMesh节点创建更精确的地图
        max_x = max(node.center[0]
                    for node in self.nodes.values()) // self.tile_size + 1
        max_y = max(node.center[1]
                    for node in self.nodes.values()) // self.tile_size + 1

        simplified_map = []
        for y in range(int(max_y)):
            row = []
            for x in range(int(max_x)):
                # 检查是否有NavMesh节点覆盖这个瓦片
                pixel_x = x * self.tile_size + self.tile_size // 2
                pixel_y = y * self.tile_size + self.tile_size // 2

                # 查找包含此点的节点
                has_node = False
                for node in self.nodes.values():
                    if node.contains_point((pixel_x, pixel_y)):
                        has_node = True
                        break

                # 创建简化的瓦片对象
                tile = type('Tile', (), {
                    'type': 1 if has_node else 0,  # 1=可通行, 0=不可通行
                    'is_gold_vein': False,
                    'gold_amount': 0
                })()
                row.append(tile)
            simplified_map.append(row)

        return simplified_map

    def _convert_tile_path_to_navmesh_nodes(self, tile_path: List[Tuple[int, int]]) -> List[NavMeshNode]:
        """将瓦片路径转换为NavMesh节点路径"""
        navmesh_path = []

        for tile_x, tile_y in tile_path:
            pixel_x = tile_x * self.tile_size + self.tile_size // 2
            pixel_y = tile_y * self.tile_size + self.tile_size // 2

            # 查找包含此点的NavMesh节点
            for node in self.nodes.values():
                if node.contains_point((pixel_x, pixel_y)):
                    navmesh_path.append(node)
                    break

        return navmesh_path

    def _smooth_path(self, path_points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """路径平滑处理"""
        if len(path_points) <= 2:
            return path_points

        smoothed = [path_points[0]]

        for i in range(1, len(path_points) - 1):
            # 简单的线性插值平滑
            prev_point = path_points[i - 1]
            curr_point = path_points[i]
            next_point = path_points[i + 1]

            # 计算平滑点
            smooth_x = (prev_point[0] + curr_point[0] + next_point[0]) / 3
            smooth_y = (prev_point[1] + curr_point[1] + next_point[1]) / 3
            smoothed.append((smooth_x, smooth_y))

        smoothed.append(path_points[-1])
        return smoothed

    def get_nearby_nodes(self, position: Tuple[float, float], radius: float) -> List[NavMeshNode]:
        """获取指定位置附近的节点"""
        nearby_nodes = []
        hash_x = int(position[0] // self.hash_cell_size)
        hash_y = int(position[1] // self.hash_cell_size)

        # 检查周围的哈希格子
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                key = (hash_x + dx, hash_y + dy)
                if key in self.spatial_hash:
                    for node_id in self.spatial_hash[key]:
                        node = self.nodes[node_id]
                        distance = self._calculate_distance(
                            position, node.center)
                        if distance <= radius:
                            nearby_nodes.append(node)

        return nearby_nodes

    def update_navmesh(self, changed_tiles: List[Tuple[int, int]], game_map: List[List]):
        """更新导航网格（当地图发生变化时）"""
        game_logger.info("🔄 更新导航网格...")

        # 简化的更新策略：重新生成整个网格
        # 在实际应用中，可以实现增量更新
        map_width = len(game_map[0]) if game_map else 0
        map_height = len(game_map) if game_map else 0

        if map_width > 0 and map_height > 0:
            self.generate_navmesh(game_map, map_width, map_height)

    def render_debug(self, screen, camera_x: int, camera_y: int):
        """渲染调试信息"""

        # 渲染节点
        for node in self.nodes.values():
            if node.node_type == NavMeshNodeType.WALKABLE:
                # 渲染多边形
                screen_points = []
                for vertex in node.vertices:
                    screen_x = int(vertex[0] - camera_x)
                    screen_y = int(vertex[1] - camera_y)
                    screen_points.append((screen_x, screen_y))

                if len(screen_points) >= 3:
                    pygame.draw.polygon(
                        screen, (100, 255, 100, 50), screen_points)
                    pygame.draw.polygon(screen, (0, 255, 0), screen_points, 2)

                # 渲染中心点
                center_x = int(node.center[0] - camera_x)
                center_y = int(node.center[1] - camera_y)
                pygame.draw.circle(screen, (255, 0, 0),
                                   (center_x, center_y), 3)

        # 渲染边
        for edge in self.edges:
            start_x = int(edge.start_point[0] - camera_x)
            start_y = int(edge.start_point[1] - camera_y)
            end_x = int(edge.end_point[0] - camera_x)
            end_y = int(edge.end_point[1] - camera_y)
            pygame.draw.line(screen, (255, 255, 0),
                             (start_x, start_y), (end_x, end_y), 2)
