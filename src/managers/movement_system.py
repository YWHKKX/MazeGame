#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一移动系统模块 - 整合所有寻路算法的智能移动系统

核心特性:
1. 统一寻路接口 - 整合B*、A*、DFS、NavMesh等算法
2. 智能算法选择 - 根据场景自动选择最佳算法
3. 性能优化 - 缓存、预计算、增量更新
4. 路径可视化 - 支持多种路径显示模式
5. 动态调整 - 实时适应环境变化
6. 多种移动模式 - 战斗、探索、游荡等
"""

import math
import random
import heapq
import time
import pygame
from typing import List, Tuple, Optional, Set, Dict, Any, Union
from src.utils.logger import game_logger
from dataclasses import dataclass, field
from enum import Enum

from ..core.constants import GameConstants
from ..core.enums import TileType
from ..systems.advanced_pathfinding import AdvancedPathfindingSystem, PathfindingStrategy
from ..systems.unified_pathfinding import (
    UnifiedPathfindingSystem, PathfindingStrategy as UnifiedPathfindingStrategy,
    PathfindingResult, PathfindingConfig
)
from ..utils.tile_converter import TileConverter
from ..systems.bstar_pathfinding import BStarPathfinding


class MovementMode(Enum):
    """移动模式枚举"""
    IDLE = "idle"                    # 空闲
    MOVING = "moving"                # 移动中
    WANDERING = "wandering"          # 游荡
    FLEEING = "fleeing"              # 逃跑
    PURSUING = "pursuing"            # 追击
    MINING = "mining"                # 挖掘
    BUILDING = "building"            # 建造
    RETURNING = "returning"          # 返回


class PathfindingPhase(Enum):
    """寻路阶段枚举"""
    IDLE = "idle"                    # 空闲
    PATHFINDING = "pathfinding"      # 寻路中
    PATH_FOUND = "path_found"        # 路径已找到
    PATH_NOT_FOUND = "path_not_found"  # 路径未找到
    ALL_TARGETS_FAILED = "all_targets_failed"  # 所有目标都不可达


class UnitMovementState(Enum):
    """单位移动状态枚举"""
    IDLE = "idle"                    # 空闲
    PATHFINDING = "pathfinding"      # 寻路阶段
    MOVING = "moving"                # 移动阶段
    WANDERING = "wandering"          # 游荡阶段
    STUCK = "stuck"                  # 卡住状态


@dataclass
class MovementState:
    """移动状态"""
    mode: MovementMode = MovementMode.IDLE
    target: Optional[Tuple[float, float]] = None
    current_path: List[Tuple[float, float]] = field(default_factory=list)
    path_index: int = 0
    last_position: Tuple[float, float] = (0, 0)
    stuck_counter: int = 0
    last_path_update: float = 0.0
    path_valid: bool = True


@dataclass
class PathfindingState:
    """寻路状态"""
    phase: PathfindingPhase = PathfindingPhase.IDLE
    current_target: Optional[Tuple[float, float]] = None
    failed_targets: Set[Tuple[float, float]] = field(default_factory=set)
    pathfinding_start_time: float = 0.0
    max_pathfinding_time: float = 2.0  # 最大寻路时间（秒）
    path: Optional[List[Tuple[int, int]]] = None
    pixel_path: Optional[List[Tuple[int, int]]] = None


@dataclass
class UnitState:
    """单位状态"""
    movement_state: UnitMovementState = UnitMovementState.IDLE
    pathfinding_state: PathfindingState = field(
        default_factory=PathfindingState)
    movement_state_data: MovementState = field(default_factory=MovementState)
    last_update_time: float = 0.0
    target_queue: List[Tuple[float, float]] = field(default_factory=list)
    wandering_target: Optional[Tuple[float, float]] = None
    wandering_wait_time: float = 0.0

    def __getattr__(self, name):
        """向后兼容的属性访问"""
        if name == 'current_path':
            return self.movement_state_data.current_path
        elif name == 'path_index':
            return self.movement_state_data.path_index
        elif name == 'path_target':
            return self.movement_state_data.target
        elif name == 'path_valid':
            return self.movement_state_data.path_valid
        elif name == 'last_position':
            return self.movement_state_data.last_position
        elif name == 'stuck_counter':
            return self.movement_state_data.stuck_counter
        else:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        """向后兼容的属性设置"""
        if name in ['current_path', 'path_index', 'path_target', 'path_valid', 'last_position', 'stuck_counter']:
            if not hasattr(self, 'movement_state_data'):
                super().__setattr__('movement_state_data', MovementState())
            if name == 'current_path':
                self.movement_state_data.current_path = value
            elif name == 'path_index':
                self.movement_state_data.path_index = value
            elif name == 'path_target':
                self.movement_state_data.target = value
            elif name == 'path_valid':
                self.movement_state_data.path_valid = value
            elif name == 'last_position':
                self.movement_state_data.last_position = value
            elif name == 'stuck_counter':
                self.movement_state_data.stuck_counter = value
        else:
            super().__setattr__(name, value)


class PathfindingNode:
    """B*寻路算法节点"""

    def __init__(self, x: int, y: int, g: float = 0, h: float = 0, parent=None):
        self.x = x
        self.y = y
        self.g = g  # 从起点到当前节点的实际代价
        self.h = h  # 从当前节点到终点的启发式代价
        self.f = g + h  # 总代价
        self.parent = parent

    def __lt__(self, other):
        return self.f < other.f

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


class PathVisualizer:
    """路径可视化器"""

    def __init__(self):
        self.path_markers: List[Dict[str, Any]] = []
        self.visualization_enabled = True

    def add_path_marker(self, path: List[Tuple[float, float]], unit_name: str,
                        color: Tuple[int, int, int] = (200, 200, 200),
                        duration: float = 5.0, style: str = "dashed"):
        """添加路径标记"""
        if not self.visualization_enabled or not path:
            return

        marker = {
            'path': path,
            'unit_name': unit_name,
            'color': color,
            'style': style,
            'created_time': time.time(),
            'duration': duration,
            'visible': True
        }
        self.path_markers.append(marker)

    def render(self, screen: pygame.Surface, camera_x: int = 0, camera_y: int = 0):
        """渲染路径标记"""
        if not self.visualization_enabled:
            return

        current_time = time.time()

        for marker in self.path_markers[:]:
            if not marker['visible']:
                continue

            # 检查是否过期
            if current_time - marker['created_time'] > marker['duration']:
                marker['visible'] = False
                continue

            # 渲染路径
            self._render_path(screen, marker, camera_x, camera_y)

    def _render_path(self, screen: pygame.Surface, marker: Dict[str, Any],
                     camera_x: int, camera_y: int):
        """渲染单条路径"""
        path = marker['path']
        if len(path) < 2:
            return

        color = marker['color']
        style = marker['style']

        # 转换坐标（考虑相机偏移）
        screen_points = []
        for point in path:
            screen_x = int(point[0] - camera_x)
            screen_y = int(point[1] - camera_y)
            screen_points.append((screen_x, screen_y))

        # 根据样式渲染
        if style == "dashed":
            self._draw_dashed_line(screen, color, screen_points)
        elif style == "solid":
            pygame.draw.lines(screen, color, False, screen_points, 2)
        elif style == "dots":
            for point in screen_points:
                pygame.draw.circle(screen, color, point, 3)

    def _draw_dashed_line(self, screen: pygame.Surface, color: Tuple[int, int, int],
                          points: List[Tuple[int, int]]):
        """绘制虚线"""
        if len(points) < 2:
            return

        dash_length = 8
        gap_length = 4

        for i in range(len(points) - 1):
            start = points[i]
            end = points[i + 1]

            # 计算线段长度和方向
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            distance = math.sqrt(dx * dx + dy * dy)

            if distance == 0:
                continue

            # 单位方向向量
            unit_x = dx / distance
            unit_y = dy / distance

            # 绘制虚线
            current_distance = 0
            while current_distance < distance:
                # 计算当前段的起点和终点
                segment_start_x = int(start[0] + unit_x * current_distance)
                segment_start_y = int(start[1] + unit_y * current_distance)

                current_distance += dash_length
                if current_distance > distance:
                    current_distance = distance

                segment_end_x = int(start[0] + unit_x * current_distance)
                segment_end_y = int(start[1] + unit_y * current_distance)

                # 绘制线段
                pygame.draw.line(screen, color,
                                 (segment_start_x, segment_start_y),
                                 (segment_end_x, segment_end_y), 2)

                # 跳过间隙
                current_distance += gap_length

    def clear_markers(self):
        """清空所有路径标记"""
        self.path_markers.clear()

    def set_visibility(self, enabled: bool):
        """设置可视化开关"""
        self.visualization_enabled = enabled


class TargetVisualizer:
    """高性能实时目标可视化器 - 用于显示功能性怪物的目标连线"""

    def __init__(self):
        self.target_lines: List[Dict[str, Any]] = []
        self.visualization_enabled = True

        # 性能优化相关
        self._last_camera_pos = (0, 0)  # 上次相机位置
        self._camera_moved = False  # 相机是否移动
        self._needs_redraw = True  # 是否需要重绘

        # LOD设置
        self.lod_distances = [100, 200, 400]  # 距离阈值
        self.lod_dash_lengths = [8, 6, 4]  # 对应距离的虚线长度
        self.lod_gap_lengths = [4, 3, 2]  # 对应距离的间隙长度

        # 性能统计
        self._render_stats = {
            'lines_rendered': 0,
            'last_render_time': 0
        }

    def add_target_line(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                        unit_name: str, color: Tuple[int, int, int] = (128, 128, 128),
                        duration: float = 2.0, style: str = "dashed"):
        """添加目标连线"""
        if not self.visualization_enabled:
            return

        line = {
            'start_pos': start_pos,
            'end_pos': end_pos,
            'unit_name': unit_name,
            'color': color,
            'style': style,
            'created_time': time.time(),
            'duration': duration,
            'visible': True
        }
        self.target_lines.append(line)
        self._needs_redraw = True  # 添加新连线时需要重绘

    def render(self, screen: pygame.Surface, camera_x: int = 0, camera_y: int = 0, ui_scale: float = 1.0):
        """高性能实时渲染目标连线"""
        if not self.visualization_enabled:
            return

        if not self.target_lines:
            return

        start_time = time.time()

        # 检查相机是否移动
        current_camera_pos = (camera_x, camera_y)
        if current_camera_pos != self._last_camera_pos:
            self._camera_moved = True
            self._last_camera_pos = current_camera_pos
            self._needs_redraw = True
        else:
            self._camera_moved = False

        # 清理过期连线并收集脏矩形
        self._cleanup_expired_lines()

        # 如果不需要重绘且相机未移动，跳过渲染
        if not self._needs_redraw and not self._camera_moved:
            return

        # 批处理渲染
        self._batch_render_lines(screen, camera_x, camera_y, ui_scale)

        # 更新性能统计
        render_time = time.time() - start_time
        self._render_stats['last_render_time'] = render_time
        self._needs_redraw = False

    def _render_target_line(self, screen: pygame.Surface, line: Dict[str, Any],
                            camera_x: int, camera_y: int):
        """渲染单条目标连线"""
        start_pos = line['start_pos']
        end_pos = line['end_pos']
        color = line['color']
        style = line['style']

        # 转换坐标（考虑相机偏移）
        start_screen_x = int(start_pos[0] - camera_x)
        start_screen_y = int(start_pos[1] - camera_y)
        end_screen_x = int(end_pos[0] - camera_x)
        end_screen_y = int(end_pos[1] - camera_y)

        screen_points = [(start_screen_x, start_screen_y),
                         (end_screen_x, end_screen_y)]

        # 根据样式渲染
        if style == "dashed":
            self._draw_dashed_line(screen, color, screen_points)
        elif style == "solid":
            pygame.draw.line(screen, color, (start_screen_x, start_screen_y),
                             (end_screen_x, end_screen_y), 2)

    def _draw_dashed_line(self, screen: pygame.Surface, color: Tuple[int, int, int],
                          points: List[Tuple[int, int]]):
        """绘制虚线"""
        if len(points) < 2:
            return

        dash_length = 6
        gap_length = 3

        start = points[0]
        end = points[1]

        # 计算线段长度和方向
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return

        # 单位方向向量
        unit_x = dx / distance
        unit_y = dy / distance

        # 绘制虚线
        current_distance = 0
        while current_distance < distance:
            # 计算当前段的起点和终点
            segment_start_x = int(start[0] + unit_x * current_distance)
            segment_start_y = int(start[1] + unit_y * current_distance)

            current_distance += dash_length
            if current_distance > distance:
                current_distance = distance

            segment_end_x = int(start[0] + unit_x * current_distance)
            segment_end_y = int(start[1] + unit_y * current_distance)

            # 绘制线段
            pygame.draw.line(screen, color,
                             (segment_start_x, segment_start_y),
                             (segment_end_x, segment_end_y), 2)

            # 跳过间隙
            current_distance += gap_length

    def clear_lines(self):
        """清空所有目标连线"""
        self.target_lines.clear()

    def clear_unit_lines(self, unit_name: str):
        """清空指定单位的目标连线"""
        self.target_lines = [
            line for line in self.target_lines if line['unit_name'] != unit_name]

    def update_target_line(self, start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                           unit_name: str, color: Tuple[int, int, int] = (128, 128, 128),
                           duration: float = 2.0, style: str = "dashed"):
        """更新目标连线（先删除旧的，再添加新的）"""
        # 先删除该单位的旧连线
        self.clear_unit_lines(unit_name)
        # 再添加新连线
        self.add_target_line(start_pos, end_pos, unit_name,
                             color, duration, style)
        self._needs_redraw = True  # 更新连线时需要重绘

    def _cleanup_expired_lines(self):
        """清理过期连线"""
        current_time = time.time()
        lines_to_remove = []

        for i, line in enumerate(self.target_lines):
            if not line['visible']:
                lines_to_remove.append(i)
                continue

            # 检查是否过期
            if current_time - line['created_time'] > line['duration']:
                line['visible'] = False
                lines_to_remove.append(i)

        # 从后往前删除，避免索引问题
        for i in reversed(lines_to_remove):
            del self.target_lines[i]

    def _batch_render_lines(self, screen: pygame.Surface, camera_x: int, camera_y: int, ui_scale: float = 1.0):
        """批处理渲染所有连线"""
        if not self.target_lines:
            return

        # 按LOD分组渲染
        lod_groups = {0: [], 1: [], 2: []}  # 三个LOD级别

        for line in self.target_lines:
            if not line['visible']:
                continue

            # 计算距离以确定LOD级别
            start_pos = line['start_pos']
            end_pos = line['end_pos']
            distance = math.sqrt(
                (end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)

            # 确定LOD级别
            lod_level = 0
            for i, threshold in enumerate(self.lod_distances):
                if distance > threshold:
                    lod_level = i + 1
                else:
                    break

            # 限制LOD级别
            lod_level = min(lod_level, 2)
            lod_groups[lod_level].append(line)

        # 按LOD级别渲染
        for lod_level, lines in lod_groups.items():
            if lines:
                self._render_lod_group(
                    screen, lines, lod_level, camera_x, camera_y, ui_scale)

    def _render_lod_group(self, screen: pygame.Surface, lines: List[Dict], lod_level: int,
                          camera_x: int, camera_y: int, ui_scale: float = 1.0):
        """渲染指定LOD级别的连线组"""
        if not lines:
            return

        # 获取LOD参数，根据UI缩放倍数调整
        dash_length = int(self.lod_dash_lengths[lod_level] * ui_scale)
        gap_length = int(self.lod_gap_lengths[lod_level] * ui_scale)

        # 批处理渲染
        for line in lines:
            self._render_target_line_optimized(screen, line, camera_x, camera_y,
                                               dash_length, gap_length, ui_scale)
            self._render_stats['lines_rendered'] += 1

    def _render_target_line_optimized(self, screen: pygame.Surface, line: Dict[str, Any],
                                      camera_x: int, camera_y: int, dash_length: int, gap_length: int, ui_scale: float = 1.0):
        """优化的目标连线渲染"""
        start_pos = line['start_pos']
        end_pos = line['end_pos']
        color = line['color']
        style = line['style']

        # 转换坐标（考虑相机偏移和UI缩放）
        start_screen_x = int((start_pos[0] - camera_x) * ui_scale)
        start_screen_y = int((start_pos[1] - camera_y) * ui_scale)
        end_screen_x = int((end_pos[0] - camera_x) * ui_scale)
        end_screen_y = int((end_pos[1] - camera_y) * ui_scale)

        # 检查是否在屏幕范围内
        screen_rect = screen.get_rect()
        if not self._is_line_in_screen(start_screen_x, start_screen_y,
                                       end_screen_x, end_screen_y, screen_rect):
            return

        screen_points = [(start_screen_x, start_screen_y),
                         (end_screen_x, end_screen_y)]

        # 根据样式渲染
        if style == "dashed":
            self._draw_dashed_line_optimized(
                screen, color, screen_points, dash_length, gap_length)
        elif style == "solid":
            # 根据UI缩放调整线条宽度
            line_width = max(1, int(2 * ui_scale))
            pygame.draw.line(screen, color, (start_screen_x, start_screen_y),
                             (end_screen_x, end_screen_y), line_width)

    def _is_line_in_screen(self, x1: int, y1: int, x2: int, y2: int, screen_rect: pygame.Rect) -> bool:
        """检查连线是否在屏幕范围内"""
        # 简单的边界检查
        return not (x1 < screen_rect.left - 100 and x2 < screen_rect.left - 100 or
                    x1 > screen_rect.right + 100 and x2 > screen_rect.right + 100 or
                    y1 < screen_rect.top - 100 and y2 < screen_rect.top - 100 or
                    y1 > screen_rect.bottom + 100 and y2 > screen_rect.bottom + 100)

    def _draw_dashed_line_optimized(self, screen: pygame.Surface, color: Tuple[int, int, int],
                                    points: List[Tuple[int, int]], dash_length: int, gap_length: int):
        """优化的虚线绘制"""
        if len(points) < 2:
            return

        start = points[0]
        end = points[1]

        # 计算线段长度和方向
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            return

        # 单位方向向量
        unit_x = dx / distance
        unit_y = dy / distance

        # 预计算所有线段点
        segments = []
        current_distance = 0
        while current_distance < distance:
            segment_start_x = int(start[0] + unit_x * current_distance)
            segment_start_y = int(start[1] + unit_y * current_distance)

            current_distance += dash_length
            if current_distance > distance:
                current_distance = distance

            segment_end_x = int(start[0] + unit_x * current_distance)
            segment_end_y = int(start[1] + unit_y * current_distance)

            segments.append(((segment_start_x, segment_start_y),
                            (segment_end_x, segment_end_y)))
            current_distance += gap_length

        # 批量绘制所有线段
        for segment_start, segment_end in segments:
            pygame.draw.line(screen, color, segment_start, segment_end, 2)

    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return {
            **self._render_stats,
            'active_lines': len([line for line in self.target_lines if line['visible']]),
            'total_lines': len(self.target_lines)
        }

    def set_visibility(self, enabled: bool):
        """设置可视化开关"""
        self.visualization_enabled = enabled


class PathMarker:
    """路径标记类 - 用于可视化DFS寻路结果（向后兼容）"""

    def __init__(self, path: List[Tuple[int, int]], unit_name: str, color: Tuple[int, int, int] = (0, 255, 0), pixel_path: Optional[List[Tuple[int, int]]] = None):
        self.path = path  # 瓦块路径
        self.pixel_path = pixel_path  # 像素中心点路径
        self.unit_name = unit_name
        self.color = color
        self.visible = True
        self.creation_time = 0  # 创建时间，用于自动消失
        self.duration = 5.0  # 显示持续时间（秒）

    def is_expired(self, current_time: float) -> bool:
        """检查路径标记是否已过期"""
        return current_time - self.creation_time > self.duration

    def render(self, screen, camera_x: int, camera_y: int, tile_size: int):
        """渲染路径标记"""
        if not self.visible or not self.path or len(self.path) < 2:
            return

        # 优先使用像素中心点路径，如果没有则计算瓦块中心点
        points = []
        if self.pixel_path and len(self.pixel_path) > 0:
            # 使用预计算的像素中心点路径，按顺序连接
            for pixel_point in self.pixel_path:
                screen_x = pixel_point[0] - camera_x
                screen_y = pixel_point[1] - camera_y
                points.append((screen_x, screen_y))
        else:
            # 计算瓦块中心点路径，按顺序连接
            for tile in self.path:
                center_x, center_y = TileConverter.get_screen_center_pixel(
                    tile[0], tile[1], tile_size, camera_x, camera_y)
                points.append((center_x, center_y))

        # 绘制连接路径点的虚线
        for i in range(len(points) - 1):
            start_point = points[i]
            end_point = points[i + 1]
            self._draw_dashed_line(
                screen, self.color, start_point, end_point, 2)

    def _draw_dashed_line(self, screen, color, start_pos, end_pos, width):
        """绘制虚线"""

        x1, y1 = start_pos
        x2, y2 = end_pos

        # 计算距离和方向
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if distance == 0:
            return

        # 虚线参数
        dash_length = 8
        gap_length = 4

        # 计算单位方向向量
        dx = (x2 - x1) / distance
        dy = (y2 - y1) / distance

        # 绘制虚线
        current_distance = 0
        while current_distance < distance:
            # 计算当前段的起点和终点
            start_x = x1 + current_distance * dx
            start_y = y1 + current_distance * dy

            end_distance = min(current_distance + dash_length, distance)
            end_x = x1 + end_distance * dx
            end_y = y1 + end_distance * dy

            # 绘制线段
            pygame.draw.line(screen, color, (int(start_x), int(
                start_y)), (int(end_x), int(end_y)), width)

            # 移动到下一个虚线段的起点
            current_distance += dash_length + gap_length


class MovementSystem:
    """
    统一移动系统 - 整合所有寻路算法的智能移动系统

    主要功能:
    1. 统一寻路接口 - 整合B*、A*、DFS、NavMesh等算法
    2. 智能算法选择 - 根据场景自动选择最佳算法
    3. 性能优化 - 缓存、预计算、增量更新
    4. 路径可视化 - 支持多种路径显示模式
    5. 动态调整 - 实时适应环境变化
    6. 多种移动模式 - 战斗、探索、游荡等
    7. 向后兼容 - 保持原有API接口
    """

    # 类变量：存储所有路径标记（向后兼容）
    _path_markers: List[PathMarker] = []

    # 高级寻路系统（向后兼容）
    _advanced_pathfinding: Optional[AdvancedPathfindingSystem] = None

    # 统一寻路系统
    _unified_pathfinding: Optional[UnifiedPathfindingSystem] = None

    # 路径可视化器
    _path_visualizer: Optional[PathVisualizer] = None

    # 目标可视化器
    _target_visualizer: Optional[TargetVisualizer] = None

    # 单位状态管理
    _unit_states: Dict[Any, UnitState] = {}
    _old_unit_states: Dict[Any, MovementState] = {}  # 向后兼容

    # 移动参数
    _stuck_threshold = GameConstants.STUCK_THRESHOLD  # 卡住检测阈值（帧数）
    _path_update_interval = GameConstants.PATH_UPDATE_INTERVAL  # 路径更新间隔（秒）
    _min_distance_threshold = GameConstants.MIN_DISTANCE_THRESHOLD  # 最小距离阈值（像素）
    _pathfinding_timeout = GameConstants.PATHFINDING_TIMEOUT  # 寻路超时时间（秒）

    # ==================== 统一寻路系统 ====================

    @staticmethod
    def initialize_unified_pathfinding(config: PathfindingConfig = None) -> bool:
        """初始化统一寻路系统"""
        if MovementSystem._unified_pathfinding is None:
            if config is None:
                config = PathfindingConfig(
                    max_iterations=1000,
                    cache_timeout=5.0,
                    dynamic_threshold=0.1,
                    enable_caching=True,
                    enable_dynamic_adjustment=True
                )
            MovementSystem._unified_pathfinding = UnifiedPathfindingSystem(
                config)

        if MovementSystem._path_visualizer is None:
            MovementSystem._path_visualizer = PathVisualizer()

        if MovementSystem._target_visualizer is None:
            MovementSystem._target_visualizer = TargetVisualizer()

        return True

    @staticmethod
    def initialize_advanced_pathfinding(game_map: List[List], map_width: int, map_height: int) -> bool:
        """初始化高级寻路系统（向后兼容）"""
        if MovementSystem._advanced_pathfinding is None:
            MovementSystem._advanced_pathfinding = AdvancedPathfindingSystem()

        return MovementSystem._advanced_pathfinding.initialize(game_map, map_width, map_height)

    @staticmethod
    def find_path_unified(start_pos: Tuple[float, float], target_pos: Tuple[float, float],
                          game_map: List[List], strategy: UnifiedPathfindingStrategy = UnifiedPathfindingStrategy.HYBRID) -> Optional[List[Tuple[float, float]]]:
        """使用统一寻路系统寻找路径"""
        if MovementSystem._unified_pathfinding is None:
            MovementSystem.initialize_unified_pathfinding()

        result = MovementSystem._unified_pathfinding.find_path(
            start_pos, target_pos, game_map, strategy)
        return result.path if result.success else None

    @staticmethod
    def find_path_with_algorithm_selection(start_pos: Tuple[float, float], target_pos: Tuple[float, float],
                                           game_map: List[List], algorithm: str = "A_STAR") -> Optional[List[Tuple[float, float]]]:
        """
        使用算法选择接口寻找路径

        Args:
            start_pos: 起始位置
            target_pos: 目标位置
            game_map: 游戏地图
            algorithm: 算法选择 ("A_STAR", "B_STAR", "DFS", "NAVMESH", "HYBRID")

        Returns:
            路径点列表，如果找不到路径返回None
        """
        # 转换像素坐标为瓦片坐标
        start_tile = (int(start_pos[0] // GameConstants.TILE_SIZE),
                      int(start_pos[1] // GameConstants.TILE_SIZE))
        target_tile = (int(target_pos[0] // GameConstants.TILE_SIZE),
                       int(target_pos[1] // GameConstants.TILE_SIZE))

        # 检查起点和终点是否有效
        if not MovementSystem._is_valid_position(start_tile, game_map, 1):
            return None
        if not MovementSystem._is_valid_position(target_tile, game_map, 1):
            return None

        # 如果起点和终点相同，直接返回
        if start_tile == target_tile:
            pixel_center = (target_tile[0] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                            target_tile[1] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)
            return [pixel_center]

        # 根据算法选择执行相应的寻路
        if algorithm == "A_STAR":
            return MovementSystem._find_path_astar(start_tile, target_tile, game_map)
        elif algorithm == "B_STAR":
            return MovementSystem._find_path_bstar(start_tile, target_tile, game_map)
        elif algorithm == "DFS":
            return MovementSystem._find_path_dfs(start_tile, target_tile, game_map)
        elif algorithm == "NAVMESH":
            # 使用统一寻路系统的NavMesh
            if MovementSystem._unified_pathfinding is not None:
                result = MovementSystem._unified_pathfinding.find_path(
                    start_pos, target_pos, game_map, UnifiedPathfindingStrategy.NAVMESH)
                return result.path if result.success else None
            else:
                # 回退到A*
                return MovementSystem._find_path_astar(start_tile, target_tile, game_map)
        elif algorithm == "HYBRID":
            # 使用统一寻路系统的混合策略
            if MovementSystem._unified_pathfinding is not None:
                result = MovementSystem._unified_pathfinding.find_path(
                    start_pos, target_pos, game_map, UnifiedPathfindingStrategy.HYBRID)
                return result.path if result.success else None
            else:
                # 回退到A*
                return MovementSystem._find_path_astar(start_tile, target_tile, game_map)
        else:
            # 默认使用A*
            return MovementSystem._find_path_astar(start_tile, target_tile, game_map)

    @staticmethod
    def find_path_advanced(start_pos: Tuple[float, float], target_pos: Tuple[float, float],
                           game_map: List[List], strategy: PathfindingStrategy = PathfindingStrategy.HYBRID) -> Optional[List[Tuple[float, float]]]:
        """使用高级寻路系统寻找路径（向后兼容）"""
        if MovementSystem._advanced_pathfinding is None:
            # 如果高级寻路系统未初始化，使用统一寻路系统
            return MovementSystem.find_path_unified(start_pos, target_pos, game_map)

        result = MovementSystem._advanced_pathfinding.find_path(
            start_pos, target_pos, game_map, strategy)
        return result.path if result.success else None

    @staticmethod
    def get_pathfinding_stats() -> dict:
        """获取寻路统计信息"""
        if MovementSystem._unified_pathfinding is not None:
            return MovementSystem._unified_pathfinding.get_performance_stats()
        elif MovementSystem._advanced_pathfinding is not None:
            return MovementSystem._advanced_pathfinding.get_performance_stats()
        else:
            return {"status": "寻路系统未初始化"}

    @staticmethod
    def update_advanced_pathfinding(changed_tiles: List[Tuple[int, int]], game_map: List[List]):
        """更新高级寻路系统（向后兼容）"""
        if MovementSystem._advanced_pathfinding is not None:
            MovementSystem._advanced_pathfinding.update_map(
                changed_tiles, game_map)

    # ==================== 分离的寻路+移动系统 ====================

    @staticmethod
    def generate_path(unit: Any, target: Tuple[float, float], game_map: List[List],
                      algorithm: str = "A_STAR") -> bool:
        """
        生成路径（寻路阶段）

        Args:
            unit: 单位对象
            target: 目标位置
            game_map: 游戏地图
            algorithm: 寻路算法 ("A_STAR", "B_STAR", "DFS", "NAVMESH", "HYBRID")

        Returns:
            bool: 是否成功生成路径
        """
        # 初始化单位状态
        MovementSystem.initialize_unit(unit)
        unit_state = MovementSystem.get_unit_state(unit)

        # 检查目标是否已经失败过
        if MovementSystem.is_target_failed(unit, target):
            game_logger.info(f"❌ 目标 {target} 已失败过，跳过寻路")
            return False

        # 设置寻路状态
        unit_state.pathfinding_state.phase = PathfindingPhase.PATHFINDING
        unit_state.pathfinding_state.current_target = target
        unit_state.pathfinding_state.pathfinding_start_time = time.time()
        unit_state.movement_state = UnitMovementState.PATHFINDING

        # 执行寻路算法
        path = MovementSystem.find_path_with_algorithm_selection(
            (unit.x, unit.y), target, game_map, algorithm)

        if path:
            # 寻路成功
            unit_state.pathfinding_state.phase = PathfindingPhase.PATH_FOUND
            unit_state.pathfinding_state.path = path
            unit_state.pathfinding_state.pixel_path = path

            # 设置移动状态数据
            unit_state.movement_state_data.current_path = path
            unit_state.movement_state_data.target = target
            unit_state.movement_state_data.path_valid = True
            unit_state.movement_state_data.path_index = 0

            # 如果路径包含起始点，从第二个点开始移动
            if len(path) > 1 and path[0] == (unit.x, unit.y):
                unit_state.movement_state_data.path_index = 1

            # 寻路成功
            game_logger.info(f"✅ 寻路成功: 路径长度 {len(path)}")

            # 标记路径已生成
            unit.path_generated = True
            unit.current_target = target

            return True
        else:
            # 寻路失败
            unit_state.pathfinding_state.phase = PathfindingPhase.PATH_NOT_FOUND
            MovementSystem.mark_target_failed(unit, target)
            game_logger.info(f"❌ 寻路失败: 目标 {target} 不可达")
            return False

    @staticmethod
    def execute_movement(unit: Any, delta_time: float, game_map: List[List],
                         speed_multiplier: float = 1.0) -> bool:
        """
        执行移动（移动阶段）

        Args:
            unit: 单位对象
            delta_time: 时间增量
            game_map: 游戏地图
            speed_multiplier: 速度倍数

        Returns:
            bool: 是否成功移动
        """
        unit_state = MovementSystem.get_unit_state(unit)

        # 检查是否有有效路径
        if not unit_state.movement_state_data.path_valid or not unit_state.movement_state_data.current_path:
            game_logger.info(f"❌ 单位 {getattr(unit, 'name', 'Unknown')} 没有有效路径")
            return False

        # 检查路径索引是否超出范围
        if unit_state.movement_state_data.path_index >= len(unit_state.movement_state_data.current_path):
            game_logger.info(f"✅ 单位 {getattr(unit, 'name', 'Unknown')} 已到达目标")
            # 清除路径
            unit_state.movement_state_data.path_valid = False
            unit_state.movement_state_data.current_path = []
            unit_state.movement_state = UnitMovementState.IDLE
            if hasattr(unit, 'path_generated'):
                unit.path_generated = False
            return False

        # 获取当前目标点
        target_point = unit_state.movement_state_data.current_path[
            unit_state.movement_state_data.path_index]

        # 计算移动方向
        dx = target_point[0] - unit.x
        dy = target_point[1] - unit.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 计算移动距离
            move_distance = unit.speed * delta_time * speed_multiplier

            # 计算新位置
            new_x = unit.x + dx * move_distance
            new_y = unit.y + dy * move_distance

            # 尝试移动
            if MovementSystem._try_move(unit, new_x, new_y, game_map):
                # 更新位置
                unit.x = new_x
                unit.y = new_y
                unit_state.movement_state = UnitMovementState.MOVING

                # 检查是否到达当前目标点
                if distance <= GameConstants.ARRIVAL_DISTANCE:  # 到达距离范围内算到达
                    unit_state.movement_state_data.path_index += 1
                    unit_state.movement_state_data.stuck_counter = 0
                    game_logger.info(
                        f"🚶 单位 {getattr(unit, 'name', 'Unknown')} 到达路径点 {unit_state.movement_state_data.path_index}/{len(unit_state.movement_state_data.current_path)}")
                else:
                    # 检查是否卡住
                    MovementSystem._check_stuck(unit)

                return True
            else:
                # 移动失败，可能被阻挡
                unit_state.movement_state_data.stuck_counter += 1
                if unit_state.movement_state_data.stuck_counter > MovementSystem._stuck_threshold:
                    # 重新计算路径
                    unit_state.movement_state_data.path_valid = False
                    if hasattr(unit, 'path_generated'):
                        unit.path_generated = False
                    game_logger.info(
                        f"⚠️ 单位 {getattr(unit, 'name', 'Unknown')} 被阻挡，需要重新寻路")

                return False

        return False

    @staticmethod
    def pathfind_and_move(unit: Any, target: Tuple[float, float], delta_time: float,
                          game_map: List[List], algorithm: str = "A_STAR",
                          speed_multiplier: float = 1.0) -> bool:
        """
        统一的寻路+移动API

        Args:
            unit: 单位对象
            target: 目标位置
            delta_time: 时间增量
            game_map: 游戏地图
            algorithm: 寻路算法
            speed_multiplier: 速度倍数

        Returns:
            bool: 是否成功执行（寻路成功或移动成功）
        """
        # 检查击退状态 - 击退期间禁止移动
        if hasattr(unit, 'knockback_state') and unit.knockback_state and unit.knockback_state.is_knocked_back:
            return False

        # 检查是否需要重新寻路
        if (not hasattr(unit, 'path_generated') or not unit.path_generated or
                not hasattr(unit, 'current_target') or unit.current_target != target):
            # 需要寻路
            return MovementSystem.generate_path(unit, target, game_map, algorithm)
        else:
            # 路径已生成，执行移动
            return MovementSystem.execute_movement(unit, delta_time, game_map, speed_multiplier)

    @staticmethod
    def clear_path(unit: Any):
        """清除单位的路径"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.movement_state_data.path_valid = False
        unit_state.movement_state_data.current_path = []
        unit_state.movement_state_data.path_index = 0
        unit_state.movement_state = UnitMovementState.IDLE

        if hasattr(unit, 'path_generated'):
            unit.path_generated = False
        if hasattr(unit, 'current_target'):
            unit.current_target = None

        game_logger.info(f"🧹 单位 {getattr(unit, 'name', 'Unknown')} 路径已清除")

    @staticmethod
    def is_pathfinding(unit: Any) -> bool:
        """检查单位是否在寻路"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.pathfinding_state.phase == PathfindingPhase.PATHFINDING

    @staticmethod
    def is_moving(unit: Any) -> bool:
        """检查单位是否在移动"""
        unit_state = MovementSystem.get_unit_state(unit)
        return (unit_state.movement_state == UnitMovementState.MOVING and
                unit_state.movement_state_data.path_valid)

    @staticmethod
    def has_path(unit: Any) -> bool:
        """检查单位是否有有效路径"""
        unit_state = MovementSystem.get_unit_state(unit)
        return (unit_state.movement_state_data.path_valid and
                len(unit_state.movement_state_data.current_path) > 0)

    @staticmethod
    def get_path_progress(unit: Any) -> Tuple[int, int]:
        """获取路径进度 (当前步骤, 总步骤)"""
        unit_state = MovementSystem.get_unit_state(unit)
        if not unit_state.movement_state_data.path_valid:
            return (0, 0)
        return (unit_state.movement_state_data.path_index,
                len(unit_state.movement_state_data.current_path))

    # ==================== 新的分离式架构 ====================

    @staticmethod
    def initialize_unit(unit: Any):
        """初始化单位状态"""
        if unit not in MovementSystem._unit_states:
            MovementSystem._unit_states[unit] = UnitState()
        # 向后兼容
        if unit not in MovementSystem._old_unit_states:
            MovementSystem._old_unit_states[unit] = MovementState()

    @staticmethod
    def get_unit_state(unit: Any) -> UnitState:
        """获取单位状态"""
        MovementSystem.initialize_unit(unit)
        return MovementSystem._unit_states[unit]

    @staticmethod
    def set_unit_state(unit: Any, state: UnitMovementState):
        """设置单位状态"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.movement_state = state
        unit_state.last_update_time = time.time()

    @staticmethod
    def add_target_to_queue(unit: Any, target: Tuple[float, float]):
        """添加目标到队列"""
        unit_state = MovementSystem.get_unit_state(unit)
        if target not in unit_state.target_queue:
            unit_state.target_queue.append(target)

    @staticmethod
    def get_next_target(unit: Any) -> Optional[Tuple[float, float]]:
        """获取下一个目标"""
        unit_state = MovementSystem.get_unit_state(unit)
        if unit_state.target_queue:
            return unit_state.target_queue.pop(0)
        return None

    @staticmethod
    def mark_target_failed(unit: Any, target: Tuple[float, float]):
        """标记目标失败"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.pathfinding_state.failed_targets.add(target)

    @staticmethod
    def is_target_failed(unit: Any, target: Tuple[float, float]) -> bool:
        """检查目标是否已失败"""
        unit_state = MovementSystem.get_unit_state(unit)
        return target in unit_state.pathfinding_state.failed_targets

    @staticmethod
    def clear_failed_targets(unit: Any):
        """清除失败目标列表"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.pathfinding_state.failed_targets.clear()

    # ==================== 寻路阶段 ====================

    @staticmethod
    def start_pathfinding_phase(unit: Any, target: Tuple[float, float], game_map: List[List]) -> bool:
        """开始寻路阶段"""
        unit_state = MovementSystem.get_unit_state(unit)

        # 检查目标是否已经失败过
        if MovementSystem.is_target_failed(unit, target):
            return False

        # 设置寻路状态
        unit_state.pathfinding_state.phase = PathfindingPhase.PATHFINDING
        unit_state.pathfinding_state.current_target = target
        unit_state.pathfinding_state.pathfinding_start_time = time.time()
        unit_state.movement_state = UnitMovementState.PATHFINDING

        # 执行寻路
        path_result = MovementSystem._execute_pathfinding(
            unit, target, game_map)

        if path_result:
            unit_state.pathfinding_state.phase = PathfindingPhase.PATH_FOUND
            unit_state.movement_state = UnitMovementState.MOVING
            return True
        else:
            unit_state.pathfinding_state.phase = PathfindingPhase.PATH_NOT_FOUND
            MovementSystem.mark_target_failed(unit, target)
            return False

    @staticmethod
    def _execute_pathfinding(unit: Any, target: Tuple[float, float], game_map: List[List]) -> bool:
        """执行寻路算法"""
        # 使用新的算法选择接口，默认使用A*算法
        path = MovementSystem.find_path_with_algorithm_selection(
            (unit.x, unit.y), target, game_map, "A_STAR")

        if path:
            unit_state = MovementSystem.get_unit_state(unit)
            unit_state.pathfinding_state.path = path

            # 路径已经是像素坐标，直接使用
            unit_state.pathfinding_state.pixel_path = path

            # 设置移动状态
            unit_state.movement_state_data.current_path = path
            # 如果路径包含起始点，从第二个点开始移动
            if len(path) > 1 and path[0] == (unit.x, unit.y):
                unit_state.movement_state_data.path_index = 1
            else:
                unit_state.movement_state_data.path_index = 0
            unit_state.movement_state_data.target = target
            unit_state.movement_state_data.path_valid = True

            return True

        return False

    # ==================== 移动阶段 ====================

    @staticmethod
    def execute_movement_phase(unit: Any, delta_time: float, game_map: List[List], speed_multiplier: float = 1.0) -> bool:
        """执行移动阶段"""
        unit_state = MovementSystem.get_unit_state(unit)

        if unit_state.movement_state != UnitMovementState.MOVING:
            return False

        # 检查是否有有效路径
        if not unit_state.movement_state_data.path_valid or not unit_state.movement_state_data.current_path:
            return False

        # 执行移动
        return MovementSystem._execute_movement_unified(unit, delta_time, game_map, speed_multiplier)

    # ==================== 游荡阶段 ====================

    @staticmethod
    def start_wandering_phase(unit: Any, game_map: List[List]) -> bool:
        """开始游荡阶段"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.movement_state = UnitMovementState.WANDERING

        # 寻找随机游荡目标
        wander_target = MovementSystem._find_random_nearby_position(
            unit, game_map)
        if wander_target:
            unit_state.wandering_target = wander_target
            unit_state.wandering_wait_time = 0.0
            return True

        return False

    @staticmethod
    def execute_wandering_phase(unit: Any, delta_time: float, game_map: List[List], speed_multiplier: float = 0.5) -> bool:
        """执行游荡阶段"""
        unit_state = MovementSystem.get_unit_state(unit)

        if unit_state.movement_state != UnitMovementState.WANDERING:
            return False

        # 检查是否有游荡目标
        if not unit_state.wandering_target:
            return MovementSystem.start_wandering_phase(unit, game_map)

        # 移动到游荡目标
        target = unit_state.wandering_target
        dx = target[0] - unit.x
        dy = target[1] - unit.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 10:
            # 移动到目标
            move_speed = unit.speed * delta_time * speed_multiplier
            new_x = unit.x + (dx / distance) * move_speed
            new_y = unit.y + (dy / distance) * move_speed

            if unit._safe_move(new_x, new_y, game_map):
                return True
        else:
            # 到达目标，开始等待
            unit_state.wandering_wait_time += delta_time

            # 等待2-3秒后选择新目标
            if unit_state.wandering_wait_time >= random.uniform(2.0, 3.0):
                unit_state.wandering_target = None
                unit_state.wandering_wait_time = 0.0

        return True

    # ==================== 主控制函数 ====================

    @staticmethod
    def update_unit_movement(unit: Any, delta_time: float, game_map: List[List], speed_multiplier: float = 1.0) -> bool:
        """更新单位移动 - 主控制函数"""
        unit_state = MovementSystem.get_unit_state(unit)
        current_time = time.time()

        # 检查寻路超时
        if (unit_state.pathfinding_state.phase == PathfindingPhase.PATHFINDING and
                current_time - unit_state.pathfinding_state.pathfinding_start_time > MovementSystem._pathfinding_timeout):
            unit_state.pathfinding_state.phase = PathfindingPhase.PATH_NOT_FOUND
            if unit_state.pathfinding_state.current_target:
                MovementSystem.mark_target_failed(
                    unit, unit_state.pathfinding_state.current_target)
            # 寻路失败，转换到游荡状态
            unit_state.movement_state = UnitMovementState.WANDERING

        # 根据当前状态执行相应逻辑
        if unit_state.movement_state == UnitMovementState.IDLE:
            # 空闲状态，尝试获取新目标
            target = MovementSystem.get_next_target(unit)
            if target:
                return MovementSystem.start_pathfinding_phase(unit, target, game_map)
            else:
                # 没有目标，进入游荡
                return MovementSystem.start_wandering_phase(unit, game_map)

        elif unit_state.movement_state == UnitMovementState.PATHFINDING:
            # 寻路中，检查寻路结果
            if unit_state.pathfinding_state.phase == PathfindingPhase.PATH_FOUND:
                # 寻路成功，转换到移动状态
                unit_state.movement_state = UnitMovementState.MOVING
                return False
            elif unit_state.pathfinding_state.phase == PathfindingPhase.PATH_NOT_FOUND:
                # 寻路失败，转换到游荡状态
                unit_state.movement_state = UnitMovementState.WANDERING
                return False
            else:
                # 寻路中，等待寻路完成
                return False

        elif unit_state.movement_state == UnitMovementState.MOVING:
            # 移动中，执行移动
            return MovementSystem.execute_movement_phase(unit, delta_time, game_map, speed_multiplier)

        elif unit_state.movement_state == UnitMovementState.WANDERING:
            # 游荡中，执行游荡
            return MovementSystem.execute_wandering_phase(unit, delta_time, game_map, speed_multiplier)

        return False

    # ==================== 向后兼容的旧系统 ====================

    @staticmethod
    def initialize_unit_old(unit: Any):
        """初始化单位移动状态（向后兼容）"""
        if unit not in MovementSystem._old_unit_states:
            MovementSystem._old_unit_states[unit] = MovementState()

    @staticmethod
    def update_movement_unified(unit: Any, target: Optional[Tuple[float, float]],
                                delta_time: float, game_map: List[List],
                                speed_multiplier: float = 1.0) -> bool:
        """使用统一寻路系统更新单位移动（向后兼容）"""
        # 使用新的分离式架构
        if target:
            MovementSystem.add_target_to_queue(unit, target)
        return MovementSystem.update_unit_movement(unit, delta_time, game_map, speed_multiplier)

    @staticmethod
    def set_target(unit: Any, target: Tuple[float, float]):
        """设置单位目标（新API）"""
        MovementSystem.add_target_to_queue(unit, target)

    @staticmethod
    def clear_targets(unit: Any):
        """清除单位所有目标（新API）"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.target_queue.clear()
        unit_state.movement_state = UnitMovementState.IDLE

    @staticmethod
    def get_current_state(unit: Any) -> UnitMovementState:
        """获取单位当前状态（新API）"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.movement_state

    @staticmethod
    def is_moving(unit: Any) -> bool:
        """检查单位是否在移动（新API）"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.movement_state == UnitMovementState.MOVING

    @staticmethod
    def is_pathfinding(unit: Any) -> bool:
        """检查单位是否在寻路（新API）"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.movement_state == UnitMovementState.PATHFINDING

    @staticmethod
    def is_wandering(unit: Any) -> bool:
        """检查单位是否在游荡（新API）"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.movement_state == UnitMovementState.WANDERING

    # ==================== 向后兼容属性访问 ====================

    @staticmethod
    def get_current_path(unit: Any) -> List[Tuple[float, float]]:
        """获取当前路径（向后兼容）"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.movement_state_data.current_path

    @staticmethod
    def set_current_path(unit: Any, path: List[Tuple[float, float]]):
        """设置当前路径（向后兼容）"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.movement_state_data.current_path = path

    @staticmethod
    def get_path_index(unit: Any) -> int:
        """获取路径索引（向后兼容）"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.movement_state_data.path_index

    @staticmethod
    def set_path_index(unit: Any, index: int):
        """设置路径索引（向后兼容）"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.movement_state_data.path_index = index

    @staticmethod
    def get_path_target(unit: Any) -> Optional[Tuple[float, float]]:
        """获取路径目标（向后兼容）"""
        unit_state = MovementSystem.get_unit_state(unit)
        return unit_state.movement_state_data.target

    @staticmethod
    def set_path_target(unit: Any, target: Tuple[float, float]):
        """设置路径目标（向后兼容）"""
        unit_state = MovementSystem.get_unit_state(unit)
        unit_state.movement_state_data.target = target

    @staticmethod
    def _update_path_unified(unit: Any, target: Tuple[float, float], game_map: List[List]):
        """使用统一寻路系统更新路径"""
        state = MovementSystem._unit_states[unit]
        start_pos = (unit.x, unit.y)

        # 使用新的算法选择接口，默认使用A*算法
        result = MovementSystem.find_path_with_algorithm_selection(
            start_pos, target, game_map, "A_STAR")

        if result:
            state.current_path = result
            # 如果路径包含起始点，从第二个点开始移动
            if len(result) > 1 and result[0] == (unit.x, unit.y):
                state.path_index = 1
            else:
                state.path_index = 0
            state.path_valid = True
            state.target = target

            # 路径可视化已禁用
        else:
            state.path_valid = False
            state.current_path = []
            state.path_index = 0

    @staticmethod
    def _select_pathfinding_strategy(unit: Any, target: Tuple[float, float]) -> UnifiedPathfindingStrategy:
        """选择寻路策略"""
        # 根据单位类型和距离选择策略
        distance = math.sqrt((target[0] - unit.x)**2 + (target[1] - unit.y)**2)

        if hasattr(unit, 'creature_type'):
            if unit.creature_type == 'goblin_worker':
                # 苦工使用A*算法，更稳定可靠
                return UnifiedPathfindingStrategy.A_STAR
            elif unit.creature_type == 'hero':
                # 英雄使用NavMesh，适合复杂地形
                return UnifiedPathfindingStrategy.NAVMESH
            else:
                # 其他单位使用混合策略
                return UnifiedPathfindingStrategy.HYBRID
        else:
            # 默认策略
            if distance < 100:
                return UnifiedPathfindingStrategy.DFS
            else:
                return UnifiedPathfindingStrategy.A_STAR

    @staticmethod
    def _execute_movement_unified(unit: Any, delta_time: float, game_map: List[List],
                                  speed_multiplier: float) -> bool:
        """执行移动"""
        unit_state = MovementSystem.get_unit_state(unit)
        state = unit_state.movement_state_data

        if not state.current_path or state.path_index >= len(state.current_path):
            return False

        # 获取当前目标点（已经是像素坐标）
        target_point = state.current_path[state.path_index]

        # 计算移动方向
        dx = target_point[0] - unit.x
        dy = target_point[1] - unit.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 计算移动距离
            move_distance = unit.speed * delta_time * speed_multiplier

            # 计算新位置
            new_x = unit.x + dx * move_distance
            new_y = unit.y + dy * move_distance

            # 尝试移动
            if MovementSystem._try_move(unit, new_x, new_y, game_map):
                # 更新位置
                unit.x = new_x
                unit.y = new_y
                state.mode = MovementMode.MOVING

                # 检查是否到达当前目标点
                if distance <= GameConstants.ARRIVAL_DISTANCE:  # 到达距离范围内算到达
                    state.path_index += 1
                    state.stuck_counter = 0
                else:
                    # 检查是否卡住
                    MovementSystem._check_stuck(unit)

                return True
            else:
                # 移动失败，可能被阻挡
                state.stuck_counter += 1
                if state.stuck_counter > MovementSystem._stuck_threshold:
                    # 重新计算路径
                    state.path_valid = False

                return False

        return False

    @staticmethod
    def _try_move(unit: Any, new_x: float, new_y: float, game_map: List[List]) -> bool:
        """尝试移动单位"""
        # 检查边界
        if (new_x < 0 or new_x >= len(game_map[0]) * GameConstants.TILE_SIZE or
                new_y < 0 or new_y >= len(game_map) * GameConstants.TILE_SIZE):
            return False

        # 检查地形碰撞
        tile_x = int(new_x // GameConstants.TILE_SIZE)
        tile_y = int(new_y // GameConstants.TILE_SIZE)

        if (tile_x < 0 or tile_x >= len(game_map[0]) or
                tile_y < 0 or tile_y >= len(game_map)):
            return False

        tile = game_map[tile_y][tile_x]

        # 检查瓦片类型是否可通行
        # 如果game_map是整数数组，直接检查值
        if isinstance(tile, int):
            if tile == 1:  # 1表示不可通行
                return False
        else:
            # 如果game_map是Tile对象数组，检查tile类型
            if tile.type == TileType.ROCK:
                return False

        return True

    @staticmethod
    def _check_stuck(unit: Any):
        """检查单位是否卡住"""
        state = MovementSystem._unit_states[unit]
        current_pos = (unit.x, unit.y)

        if hasattr(state, 'last_position'):
            distance_moved = math.sqrt(
                (current_pos[0] - state.last_position[0])**2 +
                (current_pos[1] - state.last_position[1])**2
            )

            if distance_moved < 0.5:  # 移动距离很小
                state.stuck_counter += 1
            else:
                state.stuck_counter = 0

        state.last_position = current_pos

    @staticmethod
    def _get_path_color(unit: Any) -> Tuple[int, int, int]:
        """获取路径颜色"""
        if hasattr(unit, 'creature_type'):
            if unit.creature_type == 'goblin_worker':
                return (200, 200, 100)  # 黄色
            elif unit.creature_type == 'hero':
                return (100, 200, 200)  # 青色
            else:
                return (200, 200, 200)  # 灰色
        return (200, 200, 200)

    @staticmethod
    def set_movement_mode(unit: Any, mode: MovementMode):
        """设置移动模式（向后兼容）"""
        MovementSystem.initialize_unit_old(unit)
        MovementSystem._old_unit_states[unit].mode = mode

    @staticmethod
    def get_movement_state(unit: Any) -> Optional[MovementState]:
        """获取移动状态（向后兼容）"""
        return MovementSystem._old_unit_states.get(unit)

    @staticmethod
    def clear_unit_state(unit: Any):
        """清除单位状态"""
        if unit in MovementSystem._unit_states:
            del MovementSystem._unit_states[unit]
        if unit in MovementSystem._old_unit_states:
            del MovementSystem._old_unit_states[unit]

    @staticmethod
    def render_paths_unified(screen: pygame.Surface, camera_x: int = 0, camera_y: int = 0):
        """渲染路径（统一系统）"""
        if MovementSystem._path_visualizer:
            MovementSystem._path_visualizer.render(screen, camera_x, camera_y)

    @staticmethod
    def render_target_lines(screen: pygame.Surface, camera_x: int = 0, camera_y: int = 0, ui_scale: float = 1.0):
        """渲染目标连线"""
        if MovementSystem._target_visualizer:
            MovementSystem._target_visualizer.render(
                screen, camera_x, camera_y, ui_scale)

    @staticmethod
    def add_target_line(start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                        unit_name: str, color: Tuple[int, int, int] = (128, 128, 128)):
        """添加目标连线"""
        if MovementSystem._target_visualizer:
            MovementSystem._target_visualizer.add_target_line(
                start_pos, end_pos, unit_name, color, 10.0, "dashed"  # 增加到10秒
            )
            game_logger.info(
                f"🎯 添加目标连线: {unit_name} 从 ({start_pos[0]:.1f}, {start_pos[1]:.1f}) 到 ({end_pos[0]:.1f}, {end_pos[1]:.1f})")

    @staticmethod
    def update_target_line(start_pos: Tuple[float, float], end_pos: Tuple[float, float],
                           unit_name: str, color: Tuple[int, int, int] = (128, 128, 128)):
        """更新目标连线（先删除旧的，再添加新的）"""
        if MovementSystem._target_visualizer:
            MovementSystem._target_visualizer.update_target_line(
                start_pos, end_pos, unit_name, color, 10.0, "dashed"  # 增加到10秒
            )
            game_logger.info(
                f"🔄 更新目标连线: {unit_name} 从 ({start_pos[0]:.1f}, {start_pos[1]:.1f}) 到 ({end_pos[0]:.1f}, {end_pos[1]:.1f})")

    @staticmethod
    def clear_unit_target_lines(unit_name: str):
        """清空指定单位的目标连线"""
        if MovementSystem._target_visualizer:
            MovementSystem._target_visualizer.clear_unit_lines(unit_name)

    @staticmethod
    def get_target_visualizer_stats() -> Dict[str, Any]:
        """获取目标可视化器性能统计"""
        if MovementSystem._target_visualizer:
            return MovementSystem._target_visualizer.get_performance_stats()
        return {}

    @staticmethod
    def clear_cache_unified():
        """清空缓存（统一系统）"""
        if MovementSystem._unified_pathfinding:
            MovementSystem._unified_pathfinding.clear_cache()
        if MovementSystem._path_visualizer:
            MovementSystem._path_visualizer.clear_markers()

    # ==================== 核心寻路算法 ====================

    @staticmethod
    def find_path(start_pos: Tuple[float, float], target_pos: Tuple[float, float],
                  game_map: List[List], unit_size: int = 1) -> Optional[List[Tuple[int, int]]]:
        """
        A*寻路算法 - 寻找从起点到终点的最优路径

        Args:
            start_pos: 起点坐标 (像素坐标)
            target_pos: 终点坐标 (像素坐标)
            game_map: 游戏地图
            unit_size: 单位大小（瓦片数）

        Returns:
            路径点列表（像素坐标），如果找不到路径返回None
        """
        # 转换像素坐标为瓦片坐标
        start_tile = (int(start_pos[0] // GameConstants.TILE_SIZE),
                      int(start_pos[1] // GameConstants.TILE_SIZE))
        target_tile = (int(target_pos[0] // GameConstants.TILE_SIZE),
                       int(target_pos[1] // GameConstants.TILE_SIZE))

        # 检查起点和终点是否有效
        if not MovementSystem._is_valid_position(start_tile, game_map, unit_size):
            return None
        if not MovementSystem._is_valid_position(target_tile, game_map, unit_size):
            return None

        # 如果起点和终点相同，直接返回
        if start_tile == target_tile:
            return [start_tile]

        # 初始化A*算法
        open_list = []
        closed_set: Set[Tuple[int, int]] = set()

        start_node = PathfindingNode(start_tile[0], start_tile[1], 0,
                                     MovementSystem._heuristic(start_tile, target_tile))
        heapq.heappush(open_list, start_node)

        # 8方向移动（包括对角线）
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        while open_list:
            current_node = heapq.heappop(open_list)

            # 检查是否到达目标
            if current_node.x == target_tile[0] and current_node.y == target_tile[1]:
                return MovementSystem._reconstruct_path(current_node)

            # 将当前节点加入关闭列表
            closed_set.add((current_node.x, current_node.y))

            # 检查所有相邻节点
            for dx, dy in directions:
                neighbor_x = current_node.x + dx
                neighbor_y = current_node.y + dy
                neighbor_pos = (neighbor_x, neighbor_y)

                # 跳过无效位置或已访问的位置
                if (neighbor_pos in closed_set or
                        not MovementSystem._is_valid_position(neighbor_pos, game_map, unit_size)):
                    continue

                # 计算移动代价（对角线移动代价更高）
                move_cost = 1.414 if abs(dx) + abs(dy) == 2 else 1.0
                tentative_g = current_node.g + move_cost

                # 检查是否已在开放列表中
                existing_node = None
                for node in open_list:
                    if node.x == neighbor_x and node.y == neighbor_y:
                        existing_node = node
                        break

                if existing_node is None:
                    # 新节点，添加到开放列表
                    neighbor_node = PathfindingNode(
                        neighbor_x, neighbor_y, tentative_g,
                        MovementSystem._heuristic(neighbor_pos, target_tile),
                        current_node
                    )
                    heapq.heappush(open_list, neighbor_node)
                elif tentative_g < existing_node.g:
                    # 找到更好的路径，更新节点
                    existing_node.g = tentative_g
                    existing_node.f = existing_node.g + existing_node.h
                    existing_node.parent = current_node
                    heapq.heapify(open_list)  # 重新排序堆

        # 没有找到路径
        return None

    @staticmethod
    def _is_valid_position(pos: Tuple[int, int], game_map: List[List], unit_size: int = 1) -> bool:
        """检查位置是否可通行"""
        x, y = pos

        # 检查边界
        if (x < 0 or x >= len(game_map[0]) or
                y < 0 or y >= len(game_map)):
            return False

        # 检查单位大小范围内的所有瓦片
        for dx in range(unit_size):
            for dy in range(unit_size):
                check_x = x + dx
                check_y = y + dy

                if (check_x >= len(game_map[0]) or check_y >= len(game_map)):
                    return False

                tile = game_map[check_y][check_x]

                # 检查瓦片类型是否可通行
                # 如果game_map是整数数组，直接检查值
                if isinstance(tile, int):
                    if tile == 1:  # 1表示不可通行
                        return False
                else:
                    # 如果game_map是Tile对象数组，检查tile类型
                    if tile.type == TileType.ROCK:
                        # 如果是金矿脉，允许寻路（单位可以挖掘）
                        if hasattr(tile, 'is_gold_vein') and tile.is_gold_vein:
                            continue  # 金矿脉可以寻路
                        else:
                            return False  # 普通岩石不可通行

        return True

    @staticmethod
    def _heuristic(pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """启发式函数 - 使用对角线距离"""
        dx = abs(pos1[0] - pos2[0])
        dy = abs(pos1[1] - pos2[1])
        return max(dx, dy) + (1.414 - 1) * min(dx, dy)

    @staticmethod
    def _reconstruct_path(node: PathfindingNode) -> List[Tuple[float, float]]:
        """重构路径（返回像素坐标）"""
        path = []
        current = node
        while current:
            # 将瓦片坐标转换为像素坐标（瓦片中心）
            pixel_x = current.x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            pixel_y = current.y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            path.append((pixel_x, pixel_y))
            current = current.parent
        return path[::-1]  # 反转路径

    # ==================== 智能移动系统 ====================

    @staticmethod
    def smart_target_seeking_movement(unit, target_pos, delta_time, game_map, speed_multiplier=1.0):
        """智能目标导向移动 - 使用新的分离式架构（向后兼容）"""
        if not target_pos:
            return False

        # 使用新的分离式架构
        MovementSystem.add_target_to_queue(unit, target_pos)
        return MovementSystem.update_unit_movement(unit, delta_time, game_map, speed_multiplier)

    # ==================== 基础移动模式 ====================

    @staticmethod
    def target_seeking_movement(unit, target_pos, delta_time, game_map, speed_multiplier=1.0):
        """目标导向移动 - 向指定目标移动，处理单位碰撞"""
        if not target_pos:
            return False

        dx = target_pos[0] - unit.x
        dy = target_pos[1] - unit.y
        distance = math.sqrt(dx * dx + dy * dy)

        # 添加调试信息
        if hasattr(unit, 'name') and hasattr(unit, '_move_debug_counter'):
            if unit._move_debug_counter % 60 == 1:
                game_logger.info(
                    f"📐 {unit.name} 移动计算: 当前({unit.x:.1f}, {unit.y:.1f}) 目标{target_pos} 距离:{distance:.1f}")

        if distance > GameConstants.MIN_DISTANCE_THRESHOLD:  # 增加到达距离阈值
            move_speed = unit.speed * delta_time * speed_multiplier
            new_x = unit.x + (dx / distance) * move_speed
            new_y = unit.y + (dy / distance) * move_speed

            # 尝试移动
            move_result = unit._safe_move(new_x, new_y, game_map)

            # 如果移动失败，尝试小幅度的侧向移动来绕过其他单位
            if not move_result and distance > GameConstants.MIN_DISTANCE_THRESHOLD * 1.5:  # 只有在距离较远时才尝试绕行
                # 尝试左右侧移
                side_moves = [
                    (new_x + move_speed * GameConstants.SIDE_MOVE_DISTANCE, new_y),  # 右移
                    (new_x - move_speed * GameConstants.SIDE_MOVE_DISTANCE, new_y),  # 左移
                    (new_x, new_y + move_speed *
                     GameConstants.SIDE_MOVE_DISTANCE),  # 下移
                    (new_x, new_y - move_speed *
                     GameConstants.SIDE_MOVE_DISTANCE),  # 上移
                ]

                for side_x, side_y in side_moves:
                    if unit._safe_move(side_x, side_y, game_map):
                        move_result = True
                        break

            if hasattr(unit, 'name') and hasattr(unit, '_move_debug_counter'):
                if unit._move_debug_counter % 60 == 1:
                    game_logger.info(
                        f"🚶 {unit.name} 移动结果: {move_result} 新位置:({unit.x:.1f}, {unit.y:.1f})px")
            return move_result  # 返回实际的移动结果

        return True

    @staticmethod
    def flee_movement(unit, threat_pos, delta_time, game_map, speed_multiplier=1.2):
        """逃离移动 - 远离威胁目标"""
        # 检查击退状态 - 击退期间禁止移动
        if hasattr(unit, 'knockback_state') and unit.knockback_state and unit.knockback_state.is_knocked_back:
            return False

        if not threat_pos:
            return False

        # 计算逃离方向
        escape_dx = unit.x - threat_pos[0]
        escape_dy = unit.y - threat_pos[1]
        escape_length = math.sqrt(
            escape_dx * escape_dx + escape_dy * escape_dy)

        if escape_length > 0:
            escape_dx /= escape_length
            escape_dy /= escape_length

            # 向逃离方向移动
            move_speed = unit.speed * delta_time * speed_multiplier
            new_x = unit.x + escape_dx * move_speed
            new_y = unit.y + escape_dy * move_speed

            return unit._safe_move(new_x, new_y, game_map)
        return False

    @staticmethod
    def wandering_movement(unit, delta_time, game_map, speed_multiplier=0.5, interrupt_check=None):
        """
        随机游荡移动 - 随机移动+等待，支持中断机制

        Args:
            unit: 移动单位
            delta_time: 时间增量
            game_map: 游戏地图
            speed_multiplier: 速度倍数
            interrupt_check: 中断检查函数，如果返回True则中断游荡

        Returns:
            bool: 是否完成了一个游荡周期
        """
        # 检查击退状态 - 击退期间禁止移动
        if hasattr(unit, 'knockback_state') and unit.knockback_state and unit.knockback_state.is_knocked_back:
            return False

        # 检查是否有游荡目标
        if not hasattr(unit, 'wander_target') or not unit.wander_target:
            unit.wander_target = MovementSystem._find_random_nearby_position(
                unit, game_map)
            unit.wander_wait_time = 0

        if unit.wander_target:
            dx = unit.wander_target[0] - unit.x
            dy = unit.wander_target[1] - unit.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > 10:
                # 移动到目标
                move_speed = unit.speed * delta_time * speed_multiplier
                new_x = unit.x + (dx / distance) * move_speed
                new_y = unit.y + (dy / distance) * move_speed

                unit._safe_move(new_x, new_y, game_map)

                # 在移动过程中检查中断条件
                if interrupt_check and interrupt_check():
                    unit.wander_target = None  # 清除游荡目标
                    unit.wander_wait_time = 0
                    return True  # 表示游荡被中断

            else:
                # 到达目标，开始等待
                if not hasattr(unit, 'wander_wait_time'):
                    unit.wander_wait_time = 0
                unit.wander_wait_time += delta_time

                # 等待期间也检查中断条件
                if interrupt_check and interrupt_check():
                    unit.wander_target = None
                    unit.wander_wait_time = 0
                    return True  # 表示游荡被中断

                # 等待2-3秒后选择新目标
                if unit.wander_wait_time >= random.uniform(2.0, 3.0):
                    unit.wander_target = None
                    unit.wander_wait_time = 0
                    return True  # 表示完成了一个游荡周期

        return False  # 游荡仍在进行中

    @staticmethod
    def _find_random_nearby_position(unit, game_map):
        """寻找附近的随机位置"""
        current_tile_x = int(unit.x // GameConstants.TILE_SIZE)
        current_tile_y = int(unit.y // GameConstants.TILE_SIZE)

        # 在附近范围内寻找可移动位置
        for attempt in range(GameConstants.WANDER_ATTEMPT_COUNT):  # 尝试次数
            dx = random.randint(-GameConstants.WANDER_RANGE,
                                GameConstants.WANDER_RANGE)
            dy = random.randint(-GameConstants.WANDER_RANGE,
                                GameConstants.WANDER_RANGE)

            target_x = current_tile_x + dx
            target_y = current_tile_y + dy

            if (0 <= target_x < len(game_map[0]) and
                    0 <= target_y < len(game_map)):
                tile = game_map[target_y][target_x]
                if tile.type == TileType.GROUND or tile.is_dug:
                    pixel_x = target_x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
                    pixel_y = target_y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
                    return (pixel_x, pixel_y)

        return None

    @staticmethod
    def construction_movement(engineer, target_building, delta_time, game_map):
        """建造移动 - 工程师移动到建筑位置进行建造"""
        if not target_building:
            return False

        # 计算建筑的世界坐标
        building_x = target_building.x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        building_y = target_building.y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        target_pos = (building_x, building_y)

        # 使用智能寻路移动，建造移动使用1.0倍速（基础速度）
        return MovementSystem.smart_target_seeking_movement(engineer, target_pos, delta_time, game_map, 1.0)

    @staticmethod
    def work_site_positioning(engineer, building, work_type="construction"):
        """工作位置定位 - 为工程师找到合适的工作位置"""
        # 基础实现：返回建筑位置
        building_x = building.x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        building_y = building.y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        # 根据工作类型调整位置
        if work_type == "repair":
            # 修理时稍微远离建筑中心
            building_x += 10
        elif work_type == "upgrade":
            # 升级时位于建筑旁边
            building_y += 10

        return (building_x, building_y)

    @staticmethod
    def clear_path_cache(unit):
        """清除单位的路径缓存，强制重新计算路径"""
        if hasattr(unit, 'current_path'):
            unit.current_path = None
        if hasattr(unit, 'pixel_path'):
            unit.pixel_path = None
        if hasattr(unit, 'path_target'):
            unit.path_target = None
        if hasattr(unit, 'path_index'):
            unit.path_index = 0
        if hasattr(unit, 'path_simulation_failed'):
            unit.path_simulation_failed = False
        if hasattr(unit, 'path_stuck_counter'):
            unit.path_stuck_counter = 0
        if hasattr(unit, 'consecutive_failures'):
            unit.consecutive_failures = 0
        if hasattr(unit, '_path_debug_counter'):
            unit._path_debug_counter = 0

    @staticmethod
    def is_path_valid(unit, target_pos) -> bool:
        """检查当前路径是否仍然有效"""
        unit_state = MovementSystem.get_unit_state(unit)
        current_path = unit_state.movement_state_data.current_path

        if not current_path:
            return False

        if unit_state.movement_state_data.target != target_pos:
            return False

        # 检查路径是否已经执行完毕
        if unit_state.movement_state_data.path_index >= len(current_path):
            return False

        return True

    @staticmethod
    def reset_path_for_new_target(unit, new_target_pos):
        """为目标更换重置路径状态"""
        unit_name = getattr(unit, 'name', 'Unknown')
        game_logger.info(f"🔄 单位 {unit_name} 更换目标，重置路径状态")
        MovementSystem.clear_path_cache(unit)
        unit.path_target = new_target_pos

    @staticmethod
    def add_path_marker(path: List[Tuple[int, int]], unit_name: str, color: Tuple[int, int, int] = (0, 255, 0), pixel_path: Optional[List[Tuple[int, int]]] = None):
        """添加路径标记（已禁用可视化）"""
        # 路径可视化已禁用，此方法保留用于向后兼容
        pass

    @staticmethod
    def clear_path_markers():
        """清除所有路径标记"""
        MovementSystem._path_markers.clear()

    @staticmethod
    def render_path_markers(screen, camera_x: int, camera_y: int, tile_size: int):
        """渲染所有路径标记（统一系统）"""
        # 优先使用统一寻路系统的可视化
        if MovementSystem._path_visualizer:
            MovementSystem.render_paths_unified(screen, camera_x, camera_y)

        # 向后兼容：渲染旧系统的路径标记
        current_time = time.time()

        # 移除过期的路径标记
        MovementSystem._path_markers = [
            marker for marker in MovementSystem._path_markers
            if not marker.is_expired(current_time)
        ]

        # 渲染所有有效的路径标记
        for marker in MovementSystem._path_markers:
            marker.render(screen, camera_x, camera_y, tile_size)

    @staticmethod
    def get_path_debug_info(unit) -> str:
        """获取路径调试信息"""
        unit_state = MovementSystem.get_unit_state(unit)
        current_path = unit_state.movement_state_data.current_path

        if not current_path:
            return "无路径"

        total_steps = len(current_path)
        current_step = unit_state.movement_state_data.path_index

        if current_step >= total_steps:
            return f"路径完成 ({total_steps}步)"

        return f"路径进度: {current_step}/{total_steps} 步"

    # ==================== 路径优化算法 ====================

    @staticmethod
    def optimize_path_for_units(units: List, game_map: List[List]) -> None:
        """为多个单位优化路径，避免路径冲突"""
        # 简单的路径优化：为每个单位分配不同的路径点
        occupied_tiles = set()

        for unit in units:
            unit_state = MovementSystem.get_unit_state(unit)
            current_path = unit_state.movement_state_data.current_path

            if current_path:
                # 检查当前路径是否被其他单位占用
                for i, tile in enumerate(current_path):
                    if tile in occupied_tiles and i > 0:  # 跳过起点
                        # 重新计算路径
                        MovementSystem.clear_path_cache(unit)
                        break

                # 标记路径点
                for tile in current_path:
                    occupied_tiles.add(tile)

    @staticmethod
    def smooth_path(path: List[Tuple[int, int]], game_map: List[List]) -> List[Tuple[int, int]]:
        """路径平滑 - 移除不必要的中间点"""
        if len(path) <= 2:
            return path

        smoothed = [path[0]]  # 起点
        i = 0

        while i < len(path) - 1:
            # 寻找最远的可见点
            j = len(path) - 1
            while j > i + 1:
                if MovementSystem._has_line_of_sight(path[i], path[j], game_map):
                    smoothed.append(path[j])
                    i = j
                    break
                j -= 1
            else:
                # 没有找到可见点，添加下一个点
                smoothed.append(path[i + 1])
                i += 1

        return smoothed

    @staticmethod
    def _has_line_of_sight(start: Tuple[int, int], end: Tuple[int, int], game_map: List[List]) -> bool:
        """检查两点之间是否有直线视野（无障碍物）"""
        x0, y0 = start
        x1, y1 = end

        # 使用Bresenham算法检查直线路径
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x_step = 1 if x0 < x1 else -1
        y_step = 1 if y0 < y1 else -1

        error = dx - dy
        x, y = x0, y0

        while True:
            # 检查当前点是否可通行
            if not MovementSystem._is_valid_position((x, y), game_map, 1):
                return False

            if x == x1 and y == y1:
                break

            e2 = 2 * error
            if e2 > -dy:
                error -= dy
                x += x_step
            if e2 < dx:
                error += dx
                y += y_step

        return True

    @staticmethod
    def find_alternative_path(start_pos: Tuple[float, float], target_pos: Tuple[float, float],
                              game_map: List[List], blocked_tiles: Set[Tuple[int, int]]) -> Optional[List[Tuple[int, int]]]:
        """寻找替代路径 - 避开被阻塞的瓦片"""
        # 临时标记被阻塞的瓦片
        original_tiles = {}
        for tile in blocked_tiles:
            x, y = tile
            if 0 <= x < len(game_map[0]) and 0 <= y < len(game_map):
                original_tiles[tile] = game_map[y][x]
                # 临时设置为不可通行
                game_map[y][x] = Tile(type=TileType.ROCK,
                                      is_gold_vein=False, gold_amount=0,
                                      miners_count=0, being_mined=False)

        try:
            # 寻找路径
            path = MovementSystem.find_path(start_pos, target_pos, game_map, 1)
            return path
        finally:
            # 恢复原始瓦片状态
            for tile, original_tile in original_tiles.items():
                x, y = tile
                if 0 <= x < len(game_map[0]) and 0 <= y < len(game_map):
                    game_map[y][x] = original_tile

    @staticmethod
    def _get_blocked_tiles_around(unit, game_map: List[List], radius: int = 3) -> Set[Tuple[int, int]]:
        """获取单位周围的阻塞瓦片"""
        blocked_tiles = set()
        unit_tile_x = int(unit.x // GameConstants.TILE_SIZE)
        unit_tile_y = int(unit.y // GameConstants.TILE_SIZE)

        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                check_x = unit_tile_x + dx
                check_y = unit_tile_y + dy

                if (0 <= check_x < len(game_map[0]) and
                        0 <= check_y < len(game_map)):

                    tile = game_map[check_y][check_x]
                    if not MovementSystem._is_valid_position((check_x, check_y), game_map, 1):
                        blocked_tiles.add((check_x, check_y))

        return blocked_tiles

    @staticmethod
    def optimize_rectangular_path(path: List[Tuple[int, int]], game_map: List[List]) -> List[Tuple[int, int]]:
        """矩形路径优化 - 针对矩形地图的路径优化算法"""
        if len(path) <= 2:
            return path

        optimized = [path[0]]  # 起点
        i = 0

        while i < len(path) - 1:
            # 寻找最远的可直线到达的点
            j = len(path) - 1
            best_j = i + 1

            while j > i + 1:
                # 检查是否可以直线到达
                if MovementSystem._can_move_directly(path[i], path[j], game_map):
                    best_j = j
                    break
                j -= 1

            # 添加最佳路径点
            optimized.append(path[best_j])
            i = best_j

        return optimized

    @staticmethod
    def _can_move_directly(start: Tuple[int, int], end: Tuple[int, int], game_map: List[List]) -> bool:
        """检查两点之间是否可以直线移动（考虑矩形路径）"""
        x0, y0 = start
        x1, y1 = end

        # 使用Bresenham算法检查直线路径
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x_step = 1 if x0 < x1 else -1
        y_step = 1 if y0 < y1 else -1

        error = dx - dy
        x, y = x0, y0

        while True:
            # 检查当前点是否可通行
            if not MovementSystem._is_valid_position((x, y), game_map, 1):
                return False

            if x == x1 and y == y1:
                break

            e2 = 2 * error
            if e2 > -dy:
                error -= dy
                x += x_step
            if e2 < dx:
                error += dx
                y += y_step

        return True

    @staticmethod
    def _is_path_blocked(unit, target_pos: Tuple[float, float], game_map: List[List]) -> bool:
        """检查单位到目标位置的路径是否被阻塞"""
        unit_tile_x = int(unit.x // GameConstants.TILE_SIZE)
        unit_tile_y = int(unit.y // GameConstants.TILE_SIZE)
        target_tile_x = int(target_pos[0] // GameConstants.TILE_SIZE)
        target_tile_y = int(target_pos[1] // GameConstants.TILE_SIZE)

        # 检查直线路径上的瓦片
        return not MovementSystem._can_move_directly(
            (unit_tile_x, unit_tile_y), (target_tile_x, target_tile_y), game_map)

    # ==================== 瓦块路径算法 ====================

    @staticmethod
    def find_rectangular_path(start_pos: Tuple[float, float], target_pos: Tuple[float, float],
                              game_map: List[List]) -> Optional[List[Tuple[int, int]]]:
        """寻找矩形路径 - 优先考虑水平和垂直移动"""
        start_tile = (
            int(start_pos[0] // GameConstants.TILE_SIZE),
            int(start_pos[1] // GameConstants.TILE_SIZE)
        )
        target_tile = (
            int(target_pos[0] // GameConstants.TILE_SIZE),
            int(target_pos[1] // GameConstants.TILE_SIZE)
        )

        # 确保坐标在地图范围内
        if (start_tile[0] < 0 or start_tile[0] >= len(game_map[0]) or
            start_tile[1] < 0 or start_tile[1] >= len(game_map) or
            target_tile[0] < 0 or target_tile[0] >= len(game_map[0]) or
                target_tile[1] < 0 or target_tile[1] >= len(game_map)):
            game_logger.info(
                f"🔍 坐标超出地图范围: 起始({start_tile[0]}, {start_tile[1]}) 目标({target_tile[0]}, {target_tile[1]}) 地图大小({len(game_map[0])}, {len(game_map)})")
            return None

        # 尝试L形路径（先水平后垂直，或先垂直后水平）
        paths = []

        # 路径1: 先水平后垂直
        path1 = MovementSystem._build_l_path(
            start_tile, target_tile, game_map, horizontal_first=True)
        if path1:
            paths.append(path1)
        # 路径2: 先垂直后水平
        path2 = MovementSystem._build_l_path(
            start_tile, target_tile, game_map, horizontal_first=False)
        if path2:
            paths.append(path2)

        # 选择最短路径
        if paths:
            return min(paths, key=len)

        # 如果L形路径都失败，使用基于瓦块的A*算法
        return MovementSystem._find_tile_path(start_tile, target_tile, game_map)

    @staticmethod
    def _build_l_path(start: Tuple[int, int], target: Tuple[int, int],
                      game_map: List[List], horizontal_first: bool = True) -> Optional[List[Tuple[int, int]]]:
        """构建L形路径"""
        x0, y0 = start
        x1, y1 = target

        # 检查起点和终点是否有效
        if not MovementSystem._is_valid_position(start, game_map, 1) or not MovementSystem._is_valid_position(target, game_map, 1):
            return None

        path = [start]

        if horizontal_first:
            # 先水平移动
            current_x = x0
            while current_x != x1:
                current_x += 1 if x1 > x0 else -1
                if not MovementSystem._is_valid_position((current_x, y0), game_map, 1):
                    return None
                path.append((current_x, y0))

            # 再垂直移动
            current_y = y0
            while current_y != y1:
                current_y += 1 if y1 > y0 else -1
                if not MovementSystem._is_valid_position((x1, current_y), game_map, 1):
                    return None
                path.append((x1, current_y))
        else:
            # 先垂直移动
            current_y = y0
            while current_y != y1:
                current_y += 1 if y1 > y0 else -1
                if not MovementSystem._is_valid_position((x0, current_y), game_map, 1):
                    return None
                path.append((x0, current_y))

            # 再水平移动
            current_x = x0
            while current_x != x1:
                current_x += 1 if x1 > x0 else -1
                if not MovementSystem._is_valid_position((current_x, y1), game_map, 1):
                    return None
                path.append((current_x, y1))

        return path

    @staticmethod
    def _find_tile_path(start_tile: Tuple[int, int], target_tile: Tuple[int, int],
                        game_map: List[List]) -> Optional[List[Tuple[int, int]]]:
        """基于瓦块的A*寻路算法"""
        # 如果起点和终点相同，直接返回
        if start_tile == target_tile:
            return [start_tile]

        # 初始化A*算法
        open_list = []
        closed_set: Set[Tuple[int, int]] = set()

        start_node = PathfindingNode(start_tile[0], start_tile[1], 0,
                                     MovementSystem._heuristic(start_tile, target_tile))
        heapq.heappush(open_list, start_node)

        # 8方向移动（包括对角线）
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        while open_list:
            current_node = heapq.heappop(open_list)

            # 检查是否到达目标
            if current_node.x == target_tile[0] and current_node.y == target_tile[1]:
                return MovementSystem._reconstruct_path(current_node)

            # 将当前节点加入关闭列表
            closed_set.add((current_node.x, current_node.y))

            # 检查所有相邻节点
            for dx, dy in directions:
                neighbor_x = current_node.x + dx
                neighbor_y = current_node.y + dy
                neighbor_pos = (neighbor_x, neighbor_y)

                # 跳过无效位置或已访问的位置
                if (neighbor_pos in closed_set or
                        not MovementSystem._is_valid_position(neighbor_pos, game_map, 1)):
                    continue

                # 计算移动代价（对角线移动代价更高）
                move_cost = 1.414 if abs(dx) + abs(dy) == 2 else 1.0
                tentative_g = current_node.g + move_cost

                # 检查是否已在开放列表中
                existing_node = None
                for node in open_list:
                    if node.x == neighbor_x and node.y == neighbor_y:
                        existing_node = node
                        break

                if existing_node is None:
                    # 新节点，添加到开放列表
                    neighbor_node = PathfindingNode(
                        neighbor_x, neighbor_y, tentative_g,
                        MovementSystem._heuristic(neighbor_pos, target_tile),
                        current_node
                    )
                    heapq.heappush(open_list, neighbor_node)
                elif tentative_g < existing_node.g:
                    # 找到更好的路径，更新节点
                    existing_node.g = tentative_g
                    existing_node.f = existing_node.g + existing_node.h
                    existing_node.parent = current_node
                    heapq.heapify(open_list)  # 重新排序堆

        # 没有找到路径
        return None

    @staticmethod
    def _find_simple_tile_path(start_tile: Tuple[int, int], target_tile: Tuple[int, int],
                               game_map: List[List]) -> Optional[List[Tuple[int, int]]]:
        """简单的瓦块路径 - 直线路径作为备选"""
        x0, y0 = start_tile
        x1, y1 = target_tile

        path = [start_tile]

        # 先水平移动
        current_x = x0
        while current_x != x1:
            current_x += 1 if x1 > x0 else -1
            if not MovementSystem._is_valid_position((current_x, y0), game_map, 1):
                return None
            path.append((current_x, y0))

        # 再垂直移动
        current_y = y0
        while current_y != y1:
            current_y += 1 if y1 > y0 else -1
            if not MovementSystem._is_valid_position((x1, current_y), game_map, 1):
                return None
            path.append((x1, current_y))

        return path

    # ==================== 深度优先搜索系统 ====================

    @staticmethod
    def simulate_path_execution(unit, target_pos: Tuple[float, float], game_map: List[List],
                                max_steps: int = 100) -> Tuple[bool, str, Optional[List[Tuple[int, int]]]]:
        """
        模拟路径执行 - 使用深度优先搜索判断目标是否可达

        Args:
            unit: 移动单位
            target_pos: 目标位置
            game_map: 游戏地图
            max_steps: 最大模拟步数

        Returns:
            (is_feasible, reason, path): 是否可行, 原因, 路径
        """
        # 1. 确定起始和目标瓦块
        start_tile = (
            int(unit.x // GameConstants.TILE_SIZE),
            int(unit.y // GameConstants.TILE_SIZE)
        )
        target_tile = (
            int(target_pos[0] // GameConstants.TILE_SIZE),
            int(target_pos[1] // GameConstants.TILE_SIZE)
        )

        # 2. 检查边界
        if (start_tile[0] < 0 or start_tile[0] >= len(game_map[0]) or
            start_tile[1] < 0 or start_tile[1] >= len(game_map) or
            target_tile[0] < 0 or target_tile[0] >= len(game_map[0]) or
                target_tile[1] < 0 or target_tile[1] >= len(game_map)):
            return False, "目标超出地图范围", None

        # 3. 使用带GameTile的深度优先搜索判断是否可达
        is_reachable, tile_path, pixel_path = MovementSystem._dfs_path_find_with_gametile(
            start_tile, target_tile, game_map, max_steps, GameConstants.TILE_SIZE)

        # 为了向后兼容，使用tile_path作为path
        path = tile_path

        # 生成深度优先搜索日志
        unit_name = getattr(unit, 'name', '单位')
        distance = abs(start_tile[0] - target_tile[0]) + \
            abs(start_tile[1] - target_tile[1])

        if is_reachable:
            game_logger.info(
                f"✅ {unit_name} DFS寻路成功: 起始({start_tile[0]}, {start_tile[1]}) -> 目标({target_tile[0]}, {target_tile[1]}) 距离:{distance} 路径长度:{len(path) if path else 0}")
        else:
            game_logger.info(
                f"❌ {unit_name} DFS寻路失败: 起始({start_tile[0]}, {start_tile[1]}) -> 目标({target_tile[0]}, {target_tile[1]}) 距离:{distance} 深度限制:{max_steps}")

            # 添加调试信息：显示DFS搜索的路径
            # 检查起点周围
            game_logger.info(f"   起点({start_tile[0]},{start_tile[1]})周围:")
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    check_x, check_y = start_tile[0] + dx, start_tile[1] + dy
                    if 0 <= check_x < len(game_map[0]) and 0 <= check_y < len(game_map):
                        tile = game_map[check_y][check_x]
                        is_valid = MovementSystem._is_valid_position(
                            (check_x, check_y), game_map, 1)
                        game_logger.info(
                            f"     瓦片({check_x},{check_y}): 类型={tile.type.name} 可通行={is_valid}")

            # 检查终点周围
            game_logger.info(f"   终点({target_tile[0]},{target_tile[1]})周围:")
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    check_x, check_y = target_tile[0] + dx, target_tile[1] + dy
                    if 0 <= check_x < len(game_map[0]) and 0 <= check_y < len(game_map):
                        tile = game_map[check_y][check_x]
                        is_valid = MovementSystem._is_valid_position(
                            (check_x, check_y), game_map, 1)
                        game_logger.info(
                            f"     瓦片({check_x},{check_y}): 类型={tile.type.name} 可通行={is_valid}")

            # 标记单位路径模拟失败，防止重复尝试
            unit.path_simulation_failed = True

        if not is_reachable:
            return False, "目标不可达", None

        return True, "路径可行", path

    @staticmethod
    def _find_path_astar(start_tile: Tuple[int, int], target_tile: Tuple[int, int], game_map: List[List]) -> Optional[List[Tuple[float, float]]]:
        """
        A*寻路算法实现

        Args:
            start_tile: 起始瓦片坐标
            target_tile: 目标瓦片坐标
            game_map: 游戏地图

        Returns:
            像素坐标路径，如果找不到路径返回None
        """
        # 如果起点和终点相同，直接返回
        if start_tile == target_tile:
            pixel_center = (target_tile[0] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                            target_tile[1] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)
            return [pixel_center]

        # 初始化A*算法
        open_list = []
        closed_set: Set[Tuple[int, int]] = set()

        start_node = PathfindingNode(start_tile[0], start_tile[1], 0,
                                     MovementSystem._heuristic(start_tile, target_tile))
        heapq.heappush(open_list, start_node)

        # 8方向移动（包括对角线）
        directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                      (0, 1), (1, -1), (1, 0), (1, 1)]

        while open_list:
            current_node = heapq.heappop(open_list)

            # 检查是否到达目标
            if current_node.x == target_tile[0] and current_node.y == target_tile[1]:
                # 重构路径（已经是像素坐标）
                return MovementSystem._reconstruct_path(current_node)

            # 将当前节点加入关闭列表
            closed_set.add((current_node.x, current_node.y))

            # 检查所有相邻节点
            for dx, dy in directions:
                neighbor_x = current_node.x + dx
                neighbor_y = current_node.y + dy
                neighbor_pos = (neighbor_x, neighbor_y)

                # 跳过无效位置或已访问的位置
                if (neighbor_pos in closed_set or
                        not MovementSystem._is_valid_position(neighbor_pos, game_map, 1)):
                    continue

                # 计算移动代价（对角线移动代价更高）
                move_cost = 1.414 if abs(dx) + abs(dy) == 2 else 1.0
                tentative_g = current_node.g + move_cost

                # 检查是否已在开放列表中
                existing_node = None
                for node in open_list:
                    if node.x == neighbor_x and node.y == neighbor_y:
                        existing_node = node
                        break

                if existing_node is None:
                    # 新节点，添加到开放列表
                    neighbor_node = PathfindingNode(
                        neighbor_x, neighbor_y, tentative_g,
                        MovementSystem._heuristic(neighbor_pos, target_tile),
                        current_node
                    )
                    heapq.heappush(open_list, neighbor_node)
                elif tentative_g < existing_node.g:
                    # 找到更好的路径，更新节点
                    existing_node.g = tentative_g
                    existing_node.f = existing_node.g + existing_node.h
                    existing_node.parent = current_node
                    heapq.heapify(open_list)  # 重新排序堆

        # 没有找到路径
        return None

    @staticmethod
    def _find_path_bstar(start_tile: Tuple[int, int], target_tile: Tuple[int, int], game_map: List[List]) -> Optional[List[Tuple[float, float]]]:
        """
        B*寻路算法实现（简化版）

        Args:
            start_tile: 起始瓦片坐标
            target_tile: 目标瓦片坐标
            game_map: 游戏地图

        Returns:
            像素坐标路径，如果找不到路径返回None
        """
        # 如果起点和终点相同，直接返回
        if start_tile == target_tile:
            pixel_center = (target_tile[0] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                            target_tile[1] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)
            return [pixel_center]

        # 简化的B*实现：使用A*作为基础，添加动态调整
        # 这里先回退到A*算法，因为B*算法比较复杂
        return MovementSystem._find_path_astar(start_tile, target_tile, game_map)

    @staticmethod
    def _find_path_dfs(start_tile: Tuple[int, int], target_tile: Tuple[int, int], game_map: List[List]) -> Optional[List[Tuple[float, float]]]:
        """
        DFS寻路算法实现

        Args:
            start_tile: 起始瓦片坐标
            target_tile: 目标瓦片坐标
            game_map: 游戏地图

        Returns:
            像素坐标路径，如果找不到路径返回None
        """
        # 如果起点和终点相同，直接返回
        if start_tile == target_tile:
            pixel_center = (target_tile[0] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                            target_tile[1] * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)
            return [pixel_center]

        # 使用DFS搜索
        is_reachable, tile_path, pixel_path = MovementSystem._dfs_path_find_with_gametile(
            start_tile, target_tile, game_map, max_depth=100, tile_size=GameConstants.TILE_SIZE)

        return pixel_path if is_reachable else None

    @staticmethod
    def _dfs_path_find(start_tile: Tuple[int, int], target_tile: Tuple[int, int],
                       game_map: List[List], max_depth: int) -> Tuple[bool, Optional[List[Tuple[int, int]]]]:
        """
        使用深度优先搜索判断目标是否可达，按照顺序返回所经过的瓦块

        Args:
            start_tile: 起始瓦块坐标
            target_tile: 目标瓦块坐标
            game_map: 游戏地图
            max_depth: 最大搜索深度

        Returns:
            (is_reachable, path): 是否可达, 路径
        """
        visited = set()
        search_count = 0  # 搜索计数器
        best_path = None  # 记录找到的最佳路径

        def dfs(current_tile: Tuple[int, int], depth: int, current_path: List[Tuple[int, int]]) -> Tuple[bool, List[Tuple[int, int]]]:
            nonlocal search_count, best_path
            search_count += 1

            # 检查深度限制
            if depth > max_depth:
                return False, current_path

            # 检查是否到达目标
            if current_tile == target_tile:
                # 找到目标，返回完整路径（包括目标瓦块）
                final_path = current_path + [current_tile]
                best_path = final_path  # 记录最佳路径
                return True, final_path

            # 检查是否已访问
            if current_tile in visited:
                return False, current_path

            # 检查位置是否有效
            if not MovementSystem._is_valid_position(current_tile, game_map, 1):
                return False, current_path

            # 标记为已访问（只有在位置有效时才标记）
            visited.add(current_tile)
            # 将当前瓦块添加到路径中
            new_path = current_path + [current_tile]

            # 优化搜索顺序：优先搜索朝向目标的方向
            dx_to_target = target_tile[0] - current_tile[0]
            dy_to_target = target_tile[1] - current_tile[1]

            # 根据目标方向排序搜索方向
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

            # 如果所有方向都失败，返回False
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

    @staticmethod
    def _dfs_path_find_with_gametile(start_tile: Tuple[int, int], target_tile: Tuple[int, int],
                                     game_map: List[List], max_depth: int, tile_size: int = 20) -> Tuple[bool, Optional[List[Tuple[int, int]]], Optional[List[Tuple[int, int]]]]:
        """
        使用深度优先搜索判断目标是否可达，并基于GameTile生成像素中心点路径

        Args:
            start_tile: 起始瓦块坐标
            target_tile: 目标瓦块坐标
            game_map: 游戏地图
            max_depth: 最大搜索深度
            tile_size: 瓦块大小

        Returns:
            (is_reachable, tile_path, pixel_path): 是否可达, 瓦块路径, 像素中心点路径
        """

        visited = set()
        tile_path = []
        pixel_path = []
        search_count = 0  # 搜索计数器

        def dfs(current_tile: Tuple[int, int], depth: int, current_path: List[Tuple[int, int]]) -> Tuple[bool, List[Tuple[int, int]]]:
            nonlocal search_count
            search_count += 1

            # 检查深度限制
            if depth > max_depth:
                return False, current_path

            # 检查是否到达目标
            if current_tile == target_tile:
                # 找到目标，返回完整路径（包括目标瓦块）
                final_path = current_path + [current_tile]
                return True, final_path

            # 检查是否已访问
            if current_tile in visited:
                return False, current_path

            # 检查位置是否有效
            if not MovementSystem._is_valid_position(current_tile, game_map, 1):
                return False, current_path

            # 标记为已访问（只有在位置有效时才标记）
            visited.add(current_tile)
            # 将当前瓦块添加到路径中
            new_path = current_path + [current_tile]

            # 优化搜索顺序：优先搜索朝向目标的方向
            dx_to_target = target_tile[0] - current_tile[0]
            dy_to_target = target_tile[1] - current_tile[1]

            # 根据目标方向排序搜索方向
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

            # 如果所有方向都失败，返回False
            return False, current_path

        # 开始搜索
        found, tile_path = dfs(start_tile, 0, [])

        if found and tile_path:
            # 生成像素中心点路径
            pixel_path = []
            for tile in tile_path:
                pixel_center = TileConverter.get_tile_center_pixel(
                    tile[0], tile[1], tile_size)
                pixel_path.append(pixel_center)
            return True, tile_path, pixel_path
        else:
            # 添加调试信息：显示DFS搜索统计
            if len(visited) > 0:
                game_logger.info(
                    f"   访问的瓦片: {list(visited)[:10]}{'...' if len(visited) > 10 else ''}")
            return False, None, None


# ==================== 使用示例和文档 ====================

"""
新的分离式移动系统使用指南
========================

## 核心概念

新的移动系统将寻路和移动分离为两个独立的阶段：

1. **寻路阶段 (Pathfinding Phase)**: 
   - 判断目标是否可达
   - 如果可达，生成路径并进入移动阶段
   - 如果不可达，标记目标失败并尝试下一个目标
   - 如果所有目标都失败，进入游荡阶段

2. **移动阶段 (Movement Phase)**:
   - 执行已确认的路径
   - 处理移动中的碰撞和卡住检测
   - 到达目标后进入空闲状态

3. **游荡阶段 (Wandering Phase)**:
   - 当所有目标都不可达时自动进入
   - 随机移动直到有新目标

## 基本用法

### 新API (推荐)

```python
# 1. 设置目标
MovementSystem.set_target(unit, (x, y))

# 2. 更新移动 (每帧调用)
MovementSystem.update_unit_movement(unit, delta_time, game_map, speed_multiplier)

# 3. 检查状态
if MovementSystem.is_moving(unit):
    game_logger.info("单位正在移动")
elif MovementSystem.is_pathfinding(unit):
    game_logger.info("单位正在寻路")
elif MovementSystem.is_wandering(unit):
    game_logger.info("单位正在游荡")

# 4. 清除所有目标
MovementSystem.clear_targets(unit)
```

### 向后兼容API

```python
# 旧的方式仍然可以工作
MovementSystem.smart_target_seeking_movement(unit, target_pos, delta_time, game_map, speed_multiplier)
MovementSystem.update_movement_unified(unit, target_pos, delta_time, game_map, speed_multiplier)
```

## 状态管理

### 单位状态 (UnitMovementState)
- `IDLE`: 空闲状态，等待新目标
- `PATHFINDING`: 寻路中，正在计算路径
- `MOVING`: 移动中，执行已确认的路径
- `WANDERING`: 游荡中，随机移动
- `STUCK`: 卡住状态（暂未实现）

### 寻路阶段 (PathfindingPhase)
- `IDLE`: 空闲
- `PATHFINDING`: 寻路中
- `PATH_FOUND`: 路径已找到
- `PATH_NOT_FOUND`: 路径未找到
- `ALL_TARGETS_FAILED`: 所有目标都不可达

## 目标管理

系统会自动跟踪失败的目标，避免重复寻路计算：

```python
# 添加多个目标
MovementSystem.add_target_to_queue(unit, target1)
MovementSystem.add_target_to_queue(unit, target2)
MovementSystem.add_target_to_queue(unit, target3)

# 系统会按顺序尝试每个目标
# 如果目标1不可达，会自动尝试目标2
# 如果所有目标都不可达，会进入游荡状态
```

## 性能优化

1. **避免重复寻路**: 系统会记录失败的目标，避免重复计算
2. **寻路超时**: 每个寻路操作有2秒超时限制
3. **状态缓存**: 单位状态被缓存，减少重复计算
4. **智能游荡**: 当所有目标都失败时，自动进入游荡状态

## 调试信息

系统会输出详细的调试信息：

```
🔍 单位 哥布林苦工 开始寻路: 目标 (100, 200)
✅ 单位 哥布林苦工 NavMesh寻路成功: 路径长度 15
🚶 单位 哥布林苦工 继续执行路径: 5/15
🎯 单位 哥布林苦工 到达目标，清除路径缓存
```

## 迁移指南

从旧系统迁移到新系统：

1. 将 `smart_target_seeking_movement` 调用替换为 `update_unit_movement`
2. 使用 `set_target` 设置目标，而不是直接传递参数
3. 使用新的状态检查函数替代旧的属性检查
4. 利用目标队列功能管理多个目标

## 注意事项

1. 新系统完全向后兼容，现有代码无需修改
2. 建议逐步迁移到新API以获得更好的性能
3. 新系统会自动处理寻路失败和游荡逻辑
4. 目标队列按FIFO顺序处理
5. 失败的目标会被记录，避免重复寻路
"""
