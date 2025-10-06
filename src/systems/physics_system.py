#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
物理系统 - 基于PHYSICS_SYSTEM.md设计
提供碰撞检测、击退效果和体型物理的完整物理交互框架
"""

import math
import random
import time
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class AttackType(Enum):
    """攻击类型枚举"""
    NORMAL = "normal"      # 普通攻击
    HEAVY = "heavy"        # 重击攻击
    AREA = "area"          # 范围攻击
    MAGIC = "magic"        # 魔法攻击
    PIERCING = "piercing"  # 穿透攻击


@dataclass
class KnockbackResult:
    """击退结果数据类"""
    distance: float = 0.0
    duration: float = 0.0
    direction: Tuple[float, float] = (0.0, 0.0)

    def reset(self):
        """重置击退结果"""
        self.distance = 0.0
        self.duration = 0.0
        self.direction = (0.0, 0.0)


@dataclass
class KnockbackState:
    """击退状态数据类"""
    is_knocked_back: bool = False
    start_x: float = 0.0
    start_y: float = 0.0
    target_x: float = 0.0
    target_y: float = 0.0
    duration: float = 0.0
    elapsed_time: float = 0.0


class PhysicsConstants:
    """物理系统常量"""
    # 碰撞系统参数
    COLLISION_RADIUS_MULTIPLIER = 0.6
    MIN_COLLISION_RADIUS = 5
    MAX_COLLISION_RADIUS = 25
    COLLISION_PRECISION = 2  # 像素精度

    # 击退系统参数
    BASE_KNOCKBACK_DISTANCE = 15
    MIN_KNOCKBACK_DISTANCE = 5
    MAX_KNOCKBACK_DISTANCE = 50
    KNOCKBACK_DURATION = 0.3
    KNOCKBACK_SPEED = 50  # 像素/秒

    # 体型物理参数
    MAX_SIZE_RATIO = 2.0
    SIZE_RESISTANCE_MULTIPLIER = 1.0

    # 环境碰撞参数
    WALL_COLLISION_DAMAGE_RATIO = 0.15  # 撞墙伤害为击退距离的15%
    MIN_WALL_DAMAGE = 2  # 最小撞墙伤害
    MAX_WALL_DAMAGE = 15  # 最大撞墙伤害
    WALL_BOUNCE_RATIO = 0.6  # 撞墙反弹距离比例
    MIN_BOUNCE_DISTANCE = 8  # 最小反弹距离

    # 性能参数
    SPATIAL_HASH_CELL_SIZE = 50
    MAX_UNITS_PER_CELL = 20
    UPDATE_FREQUENCY = 60


class SpatialHash:
    """空间哈希表，用于优化碰撞检测"""

    def __init__(self, cell_size: int = PhysicsConstants.SPATIAL_HASH_CELL_SIZE):
        self.cell_size = cell_size
        self.grid: Dict[Tuple[int, int], List[Any]] = {}

    def clear(self):
        """清空空间哈希表"""
        self.grid.clear()

    def get_cell_key(self, x: float, y: float) -> Tuple[int, int]:
        """获取单元格键值"""
        return (int(x // self.cell_size), int(y // self.cell_size))

    def add_unit(self, unit: Any):
        """添加单位到空间哈希表"""
        key = self.get_cell_key(unit.x, unit.y)
        if key not in self.grid:
            self.grid[key] = []
        self.grid[key].append(unit)

    def get_nearby_units(self, x: float, y: float, radius: float) -> List[Any]:
        """获取附近的单位"""
        nearby_units = []
        cell_radius = int(radius // self.cell_size) + 1
        center_key = self.get_cell_key(x, y)

        for dx in range(-cell_radius, cell_radius + 1):
            for dy in range(-cell_radius, cell_radius + 1):
                key = (center_key[0] + dx, center_key[1] + dy)
                if key in self.grid:
                    nearby_units.extend(self.grid[key])

        return nearby_units


class CollisionDetector:
    """碰撞检测器"""

    @staticmethod
    def get_collision_radius(unit: Any) -> float:
        """获取单位的碰撞半径"""
        if hasattr(unit, 'collision_radius') and unit.collision_radius is not None:
            return unit.collision_radius

        # 根据单位大小计算碰撞半径
        size = getattr(unit, 'size', 15)
        radius = size * PhysicsConstants.COLLISION_RADIUS_MULTIPLIER

        # 限制半径范围
        radius = max(PhysicsConstants.MIN_COLLISION_RADIUS,
                     min(radius, PhysicsConstants.MAX_COLLISION_RADIUS))

        # 缓存结果
        unit.collision_radius = radius
        return radius

    @staticmethod
    def check_collision(unit1: Any, unit2: Any) -> bool:
        """检测两个单位是否发生碰撞"""
        # 快速距离检查（避免开方运算）
        dx = unit1.x - unit2.x
        dy = unit1.y - unit2.y
        distance_squared = dx * dx + dy * dy

        # 碰撞半径之和的平方
        radius1 = CollisionDetector.get_collision_radius(unit1)
        radius2 = CollisionDetector.get_collision_radius(unit2)
        radius_sum_squared = (radius1 + radius2) ** 2

        return distance_squared < radius_sum_squared

    @staticmethod
    def get_collision_distance(unit1: Any, unit2: Any) -> float:
        """获取两个单位的碰撞距离"""
        dx = unit1.x - unit2.x
        dy = unit1.y - unit2.y
        return math.sqrt(dx * dx + dy * dy)


class KnockbackCalculator:
    """击退计算器"""

    @staticmethod
    def get_size_resistance(size: float) -> float:
        """根据体型获取击退抗性"""
        if size <= 12:
            return 0.5  # 超小型
        elif size <= 17:
            return 0.7  # 小型
        elif size <= 25:
            return 1.0  # 中型
        else:
            return 1.5  # 大型

    @staticmethod
    def get_attack_type_modifier(attack_type: str) -> float:
        """根据攻击类型获取击退修正"""
        modifiers = {
            AttackType.NORMAL.value: 1.0,
            AttackType.HEAVY.value: 1.5,    # 重击
            AttackType.AREA.value: 0.8,     # 范围攻击
            AttackType.MAGIC.value: 0.6,    # 魔法攻击
            AttackType.PIERCING.value: 0.7  # 穿透攻击
        }
        return modifiers.get(attack_type, 1.0)

    @staticmethod
    def calculate_knockback_direction(attacker_pos: Tuple[float, float],
                                      target_pos: Tuple[float, float]) -> Tuple[float, float]:
        """计算击退方向向量"""
        dx = target_pos[0] - attacker_pos[0]
        dy = target_pos[1] - attacker_pos[1]

        # 计算距离
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            # 如果距离为0，随机选择一个方向
            angle = random.uniform(0, 2 * math.pi)
            return (math.cos(angle), math.sin(angle))

        # 标准化方向向量
        return (dx / distance, dy / distance)

    @staticmethod
    def calculate_knockback(attacker: Any, target: Any, attack_damage: float,
                            attack_type: str = AttackType.NORMAL.value) -> KnockbackResult:
        """
        计算击退效果

        Args:
            attacker: 攻击者单位
            target: 目标单位
            attack_damage: 攻击伤害
            attack_type: 攻击类型

        Returns:
            KnockbackResult: 击退结果对象
        """
        # 1. 基础击退距离
        base_knockback = PhysicsConstants.BASE_KNOCKBACK_DISTANCE

        # 2. 体型差系数
        attacker_size = getattr(attacker, 'size', 15)
        target_size = getattr(target, 'size', 15)
        size_ratio = attacker_size / target_size
        size_modifier = min(size_ratio, PhysicsConstants.MAX_SIZE_RATIO)

        # 3. 目标击退抗性
        target_resistance = KnockbackCalculator.get_size_resistance(
            target_size)

        # 4. 攻击类型修正
        attack_modifier = KnockbackCalculator.get_attack_type_modifier(
            attack_type)

        # 5. 伤害修正
        damage_modifier = min(attack_damage / 20.0, 1.5)

        # 6. 最终击退距离
        final_distance = (base_knockback *
                          size_modifier *
                          attack_modifier *
                          damage_modifier /
                          target_resistance)

        # 7. 限制击退距离
        final_distance = max(PhysicsConstants.MIN_KNOCKBACK_DISTANCE,
                             min(final_distance, PhysicsConstants.MAX_KNOCKBACK_DISTANCE))

        # 8. 计算击退方向
        direction = KnockbackCalculator.calculate_knockback_direction(
            (attacker.x, attacker.y), (target.x, target.y)
        )

        return KnockbackResult(
            distance=final_distance,
            duration=PhysicsConstants.KNOCKBACK_DURATION,
            direction=direction
        )


class KnockbackApplier:
    """击退应用器"""

    def __init__(self, world_bounds: Tuple[float, float, float, float] = None):
        """
        初始化击退应用器

        Args:
            world_bounds: 世界边界 (min_x, min_y, max_x, max_y)
        """
        self.world_bounds = world_bounds or (0, 0, 1000, 1000)
        self.event_manager = None  # 可以设置事件管理器

    def set_world_bounds(self, bounds: Tuple[float, float, float, float]):
        """设置世界边界"""
        self.world_bounds = bounds

    def can_be_knocked_back(self, unit: Any) -> bool:
        """检查单位是否可以被击退"""
        # 1. 建筑物不能被击退
        if hasattr(unit, 'building_type') or hasattr(unit, 'is_building'):
            return False

        # 2. 死亡单位不能被击退
        if hasattr(unit, 'health') and unit.health <= 0:
            return False

        # 3. 特殊状态免疫击退
        if hasattr(unit, 'immunities') and 'knockback' in unit.immunities:
            return False

        # 4. 扎根状态免疫击退 (树人守护者)
        if hasattr(unit, 'is_rooted') and unit.is_rooted:
            return False

        # 5. 护盾状态减少击退
        if hasattr(unit, 'has_shield') and unit.has_shield:
            return "reduced"  # 击退效果减半

        return True

    def check_boundaries(self, x: float, y: float) -> Tuple[float, float]:
        """检查边界，防止击退出界"""
        min_x, min_y, max_x, max_y = self.world_bounds

        x = max(min_x, min(x, max_x))
        y = max(min_y, min(y, max_y))

        return x, y

    def apply_knockback(self, unit: Any, knockback_result: KnockbackResult) -> bool:
        """
        应用击退效果到单位

        Args:
            unit: 目标单位
            knockback_result: 击退结果

        Returns:
            bool: 是否成功应用击退
        """
        # 检查是否可以被击退
        can_knockback = self.can_be_knocked_back(unit)
        if can_knockback is False:
            return False

        # 如果是减少击退效果
        if can_knockback == "reduced":
            knockback_result.distance *= 0.5

        # 计算目标位置
        target_x = unit.x + \
            knockback_result.direction[0] * knockback_result.distance
        target_y = unit.y + \
            knockback_result.direction[1] * knockback_result.distance

        # 边界检查
        target_x, target_y = self.check_boundaries(target_x, target_y)

        # 设置击退状态
        unit.knockback_state = KnockbackState(
            is_knocked_back=True,
            start_x=unit.x,
            start_y=unit.y,
            target_x=target_x,
            target_y=target_y,
            duration=knockback_result.duration,
            elapsed_time=0.0
        )

        # 禁用单位控制
        if hasattr(unit, 'can_move'):
            unit.can_move = False
        if hasattr(unit, 'can_attack'):
            unit.can_attack = False

        # 触发击退事件
        if self.event_manager:
            self.event_manager.trigger_knockback_start(unit, knockback_result)

        return True


class EnvironmentCollisionDetector:
    """环境碰撞检测器 - 检测单位与墙面、建筑的碰撞"""

    def __init__(self, tile_size: int = 32):
        self.tile_size = tile_size

    def is_solid_tile(self, tile_type, tile_data=None) -> bool:
        """判断瓦片是否为固体（不可通过）"""
        # 导入TileType枚举
        try:
            from src.core.enums import TileType
            # 岩石和房间是固体
            if tile_type == TileType.ROCK:
                return True
            elif tile_type == TileType.ROOM:
                return True
            # 地面和金矿是可通过的
            elif tile_type in [TileType.GROUND, TileType.GOLD_VEIN, TileType.DEPLETED_VEIN]:
                return False
            else:
                return True  # 默认未知类型为固体
        except ImportError:
            # 如果无法导入，使用数字判断
            return tile_type in [0, 2]  # ROCK=0, ROOM=2

    def check_environment_collision(self, x: float, y: float, radius: float,
                                    game_map: List[List[Any]]) -> Optional[Tuple[str, Tuple[int, int]]]:
        """
        检测单位与环境的碰撞

        Args:
            x, y: 单位位置
            radius: 单位碰撞半径
            game_map: 游戏地图

        Returns:
            Optional[Tuple[str, Tuple[int, int]]]: 碰撞类型和瓦片位置，None表示无碰撞
        """
        if not game_map:
            return None

        # 计算单位占用的瓦片范围
        left = int((x - radius) // self.tile_size)
        right = int((x + radius) // self.tile_size)
        top = int((y - radius) // self.tile_size)
        bottom = int((y + radius) // self.tile_size)

        # 检查地图边界
        map_height = len(game_map)
        map_width = len(game_map[0]) if map_height > 0 else 0

        # 检查是否超出地图边界
        if left < 0 or right >= map_width or top < 0 or bottom >= map_height:
            # 计算最近的边界瓦片
            boundary_x = max(0, min(right, map_width - 1))
            boundary_y = max(0, min(bottom, map_height - 1))
            return ("boundary", (boundary_x, boundary_y))

        # 检查与固体瓦片的碰撞
        for tile_y in range(top, bottom + 1):
            for tile_x in range(left, right + 1):
                if 0 <= tile_x < map_width and 0 <= tile_y < map_height:
                    tile = game_map[tile_y][tile_x]
                    tile_type = getattr(tile, 'type', None)

                    if self.is_solid_tile(tile_type, tile):
                        # 检查圆形碰撞
                        if self._check_circle_tile_collision(x, y, radius, tile_x, tile_y):
                            # 判断碰撞类型
                            collision_type = self._get_collision_type(
                                tile_type, tile)
                            return (collision_type, (tile_x, tile_y))

        return None

    def _check_circle_tile_collision(self, circle_x: float, circle_y: float,
                                     radius: float, tile_x: int, tile_y: int) -> bool:
        """检查圆形与瓦片的碰撞"""
        # 瓦片的边界
        tile_left = tile_x * self.tile_size
        tile_right = (tile_x + 1) * self.tile_size
        tile_top = tile_y * self.tile_size
        tile_bottom = (tile_y + 1) * self.tile_size

        # 找到瓦片上距离圆心最近的点
        closest_x = max(tile_left, min(circle_x, tile_right))
        closest_y = max(tile_top, min(circle_y, tile_bottom))

        # 计算距离
        dx = circle_x - closest_x
        dy = circle_y - closest_y
        distance_squared = dx * dx + dy * dy

        return distance_squared <= radius * radius

    def _get_collision_type(self, tile_type, tile_data) -> str:
        """获取碰撞类型"""
        try:
            from src.core.enums import TileType
            if tile_type == TileType.ROCK:
                return "wall"
            elif tile_type == TileType.ROOM:
                # 根据房间类型细分
                room_type = getattr(tile_data, 'room_type', None)
                if room_type == 'dungeon_heart':
                    return "dungeon_heart"
                elif room_type and room_type.startswith('hero_base_'):
                    return "hero_base"
                else:
                    return "building"
            else:
                return "wall"
        except ImportError:
            return "wall"

    def calculate_bounce_direction(self, unit_x: float, unit_y: float,
                                   collision_tile_x: int, collision_tile_y: int,
                                   original_direction: Tuple[float, float]) -> Tuple[float, float]:
        """
        计算反弹方向

        Args:
            unit_x, unit_y: 单位位置
            collision_tile_x, collision_tile_y: 碰撞的瓦片位置
            original_direction: 原始移动方向

        Returns:
            新的反弹方向
        """
        # 瓦片中心
        tile_center_x = collision_tile_x * self.tile_size + self.tile_size / 2
        tile_center_y = collision_tile_y * self.tile_size + self.tile_size / 2

        # 计算从瓦片中心到单位的方向（法线方向）
        dx = unit_x - tile_center_x
        dy = unit_y - tile_center_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            # 如果重叠，使用原始方向的反向
            return (-original_direction[0], -original_direction[1])

        # 标准化法线
        normal_x = dx / distance
        normal_y = dy / distance

        # 计算反射向量：R = D - 2(D·N)N
        # D是入射方向，N是法线
        dot_product = original_direction[0] * \
            normal_x + original_direction[1] * normal_y
        reflect_x = original_direction[0] - 2 * dot_product * normal_x
        reflect_y = original_direction[1] - 2 * dot_product * normal_y

        # 标准化反射向量
        reflect_distance = math.sqrt(
            reflect_x * reflect_x + reflect_y * reflect_y)
        if reflect_distance > 0:
            reflect_x /= reflect_distance
            reflect_y /= reflect_distance

        return (reflect_x, reflect_y)


class PhysicsSystem:
    """物理系统主类"""

    def __init__(self, world_bounds: Tuple[float, float, float, float] = None, tile_size: int = 32):
        """
        初始化物理系统

        Args:
            world_bounds: 世界边界 (min_x, min_y, max_x, max_y)
            tile_size: 瓦片大小
        """
        self.collision_detector = CollisionDetector()
        self.knockback_calculator = KnockbackCalculator()
        self.knockback_applier = KnockbackApplier(world_bounds)
        self.spatial_hash = SpatialHash()
        self.environment_detector = EnvironmentCollisionDetector(tile_size)

        # 对象池，用于内存优化
        self.knockback_result_pool: List[KnockbackResult] = []

        # 活跃击退单位列表
        self.active_knockbacks: List[Any] = []

        # 性能统计
        self.collision_checks_count = 0
        self.knockback_calculations_count = 0
        self.wall_collision_count = 0

    def set_world_bounds(self, bounds: Tuple[float, float, float, float]):
        """设置世界边界"""
        self.knockback_applier.set_world_bounds(bounds)

    def set_animation_manager(self, animation_manager):
        """设置动画管理器"""
        self.animation_manager = animation_manager

    def get_knockback_result(self) -> KnockbackResult:
        """从对象池获取击退结果对象"""
        if self.knockback_result_pool:
            return self.knockback_result_pool.pop()
        return KnockbackResult()

    def return_knockback_result(self, result: KnockbackResult):
        """归还击退结果对象到对象池"""
        result.reset()
        self.knockback_result_pool.append(result)

    def check_collision(self, unit1: Any, unit2: Any) -> bool:
        """检测两个单位是否发生碰撞"""
        self.collision_checks_count += 1
        return self.collision_detector.check_collision(unit1, unit2)

    def calculate_knockback(self, attacker: Any, target: Any, attack_damage: float,
                            attack_type: str = AttackType.NORMAL.value) -> KnockbackResult:
        """计算击退效果"""
        self.knockback_calculations_count += 1
        return self.knockback_calculator.calculate_knockback(
            attacker, target, attack_damage, attack_type
        )

    def apply_knockback(self, unit: Any, knockback_result: KnockbackResult) -> bool:
        """应用击退效果"""
        success = self.knockback_applier.apply_knockback(
            unit, knockback_result)
        if success and unit not in self.active_knockbacks:
            self.active_knockbacks.append(unit)
        return success

    def execute_melee_attack_with_knockback(self, attacker: Any, target: Any,
                                            attack_damage: float,
                                            attack_type: str = AttackType.NORMAL.value) -> bool:
        """
        执行近战攻击并应用击退效果

        Args:
            attacker: 攻击者
            target: 目标
            attack_damage: 攻击伤害
            attack_type: 攻击类型

        Returns:
            bool: 是否成功执行攻击和击退
        """
        # 检查攻击者是否为近战
        if not self._is_melee_attack(attacker):
            return False

        # 计算击退效果
        knockback_result = self.calculate_knockback(
            attacker, target, attack_damage, attack_type)

        # 应用击退
        return self.apply_knockback(target, knockback_result)

    def _is_melee_attack(self, unit: Any) -> bool:
        """判断是否为近战攻击"""
        if hasattr(unit, '_is_melee_attack'):
            return unit._is_melee_attack()

        # 默认判断逻辑：攻击范围小于等于50像素认为是近战
        attack_range = getattr(unit, 'attack_range', 30)
        return attack_range <= 50

    def update_knockbacks(self, delta_time: float, game_map: List[List[Any]] = None):
        """更新所有击退效果"""
        units_to_remove = []

        for unit in self.active_knockbacks:
            if not hasattr(unit, 'knockback_state') or not unit.knockback_state:
                units_to_remove.append(unit)
                continue

            if not unit.knockback_state.is_knocked_back:
                units_to_remove.append(unit)
                continue

            # 更新击退状态
            if self._update_single_knockback(unit, delta_time, game_map):
                units_to_remove.append(unit)

        # 移除已完成击退的单位
        for unit in units_to_remove:
            if unit in self.active_knockbacks:
                self.active_knockbacks.remove(unit)

    def _update_single_knockback(self, unit: Any, delta_time: float, game_map: List[List[Any]] = None) -> bool:
        """
        更新单个单位的击退状态

        Args:
            unit: 单位对象
            delta_time: 时间增量（秒）
            game_map: 游戏地图（用于环境碰撞检测）

        Returns:
            bool: 击退是否完成
        """
        if not unit.knockback_state or not unit.knockback_state.is_knocked_back:
            return True

        # 更新击退时间
        unit.knockback_state.elapsed_time += delta_time

        # 计算击退进度 (使用缓动函数)
        progress = unit.knockback_state.elapsed_time / unit.knockback_state.duration
        progress = min(progress, 1.0)

        # 应用缓动函数 (ease-out)
        eased_progress = 1.0 - (1.0 - progress) ** 3

        # 插值计算新位置
        start_x = unit.knockback_state.start_x
        start_y = unit.knockback_state.start_y
        target_x = unit.knockback_state.target_x
        target_y = unit.knockback_state.target_y

        new_x = start_x + (target_x - start_x) * eased_progress
        new_y = start_y + (target_y - start_y) * eased_progress

        # 检查环境碰撞
        if game_map:
            collision_radius = self.collision_detector.get_collision_radius(
                unit)
            collision_result = self.environment_detector.check_environment_collision(
                new_x, new_y, collision_radius, game_map
            )

            if collision_result:
                collision_type, collision_tile = collision_result
                # 处理撞墙
                self._handle_wall_collision(
                    unit, collision_type, collision_tile, game_map)
                return True  # 击退因撞墙而结束

        # 更新位置
        unit.x = new_x
        unit.y = new_y

        # 检查击退是否完成
        if progress >= 1.0:
            # 击退完成
            unit.knockback_state.is_knocked_back = False
            if hasattr(unit, 'can_move'):
                unit.can_move = True
            if hasattr(unit, 'can_attack'):
                unit.can_attack = True
            unit.knockback_state = None

            # 触发击退完成事件
            if self.knockback_applier.event_manager:
                self.knockback_applier.event_manager.trigger_knockback_end(
                    unit)

            return True

        return False

    def _handle_wall_collision(self, unit: Any, collision_type: str,
                               collision_tile: Tuple[int, int], game_map: List[List[Any]]):
        """
        处理单位撞墙

        Args:
            unit: 撞墙的单位
            collision_type: 碰撞类型
            collision_tile: 碰撞的瓦片位置
            game_map: 游戏地图
        """
        self.wall_collision_count += 1

        print(f"💥 {unit.type} 撞到了 {collision_type}！位置: {collision_tile}")

        # 计算撞墙伤害
        original_knockback_distance = 0
        if unit.knockback_state:
            # 计算原始击退距离
            dx = unit.knockback_state.target_x - unit.knockback_state.start_x
            dy = unit.knockback_state.target_y - unit.knockback_state.start_y
            original_knockback_distance = math.sqrt(dx * dx + dy * dy)

        wall_damage = self._calculate_wall_damage(
            original_knockback_distance, collision_type)

        # 应用撞墙伤害
        if wall_damage > 0:
            old_health = unit.health
            unit.health -= wall_damage
            unit.health = max(0, unit.health)
            print(
                f"   💔 撞墙伤害: {wall_damage}, 剩余生命值: {unit.health}/{unit.max_health}")

        # 触发撞墙视觉效果
        if hasattr(self, 'animation_manager') and self.animation_manager:
            self.animation_manager.create_wall_collision_effect(
                unit, collision_type, wall_damage, collision_tile
            )

        # 计算反弹
        if unit.knockback_state and unit.health > 0:
            # 计算原始击退方向
            original_direction = self._get_knockback_direction(
                unit.knockback_state)

            # 计算反弹方向
            bounce_direction = self.environment_detector.calculate_bounce_direction(
                unit.x, unit.y, collision_tile[0], collision_tile[1], original_direction
            )

            # 计算反弹距离
            bounce_distance = max(
                PhysicsConstants.MIN_BOUNCE_DISTANCE,
                original_knockback_distance * PhysicsConstants.WALL_BOUNCE_RATIO
            )

            # 应用反弹
            self._apply_bounce(unit, bounce_direction,
                               bounce_distance, collision_tile, game_map)
        else:
            # 停止击退
            self._stop_knockback(unit)

    def _calculate_wall_damage(self, knockback_distance: float, collision_type: str) -> int:
        """计算撞墙伤害"""
        if knockback_distance <= 0:
            return 0

        # 基础伤害 = 击退距离 * 伤害比例
        base_damage = knockback_distance * PhysicsConstants.WALL_COLLISION_DAMAGE_RATIO

        # 根据碰撞类型调整伤害
        damage_multiplier = {
            "wall": 1.0,          # 普通墙面
            "building": 0.8,      # 建筑物稍软
            "dungeon_heart": 0.5,  # 地牢之心有保护
            "hero_base": 1.2,     # 英雄基地更坚硬
            "boundary": 1.5       # 地图边界最硬
        }.get(collision_type, 1.0)

        final_damage = int(base_damage * damage_multiplier)

        # 限制伤害范围
        return max(PhysicsConstants.MIN_WALL_DAMAGE,
                   min(final_damage, PhysicsConstants.MAX_WALL_DAMAGE))

    def _get_knockback_direction(self, knockback_state) -> Tuple[float, float]:
        """获取击退方向"""
        dx = knockback_state.target_x - knockback_state.start_x
        dy = knockback_state.target_y - knockback_state.start_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            return (dx / distance, dy / distance)
        return (1.0, 0.0)  # 默认方向

    def _apply_bounce(self, unit: Any, bounce_direction: Tuple[float, float],
                      bounce_distance: float, collision_tile: Tuple[int, int],
                      game_map: List[List[Any]]):
        """应用反弹效果"""
        # 计算反弹目标位置
        bounce_target_x = unit.x + bounce_direction[0] * bounce_distance
        bounce_target_y = unit.y + bounce_direction[1] * bounce_distance

        # 边界检查
        bounce_target_x, bounce_target_y = self.knockback_applier.check_boundaries(
            bounce_target_x, bounce_target_y
        )

        # 检查反弹路径是否会再次撞墙
        collision_radius = self.collision_detector.get_collision_radius(unit)
        bounce_collision = self.environment_detector.check_environment_collision(
            bounce_target_x, bounce_target_y, collision_radius, game_map
        )

        if bounce_collision:
            # 反弹路径也会撞墙，减少反弹距离
            bounce_distance *= 0.5
            bounce_target_x = unit.x + bounce_direction[0] * bounce_distance
            bounce_target_y = unit.y + bounce_direction[1] * bounce_distance
            bounce_target_x, bounce_target_y = self.knockback_applier.check_boundaries(
                bounce_target_x, bounce_target_y
            )

        # 更新击退状态为反弹
        unit.knockback_state.start_x = unit.x
        unit.knockback_state.start_y = unit.y
        unit.knockback_state.target_x = bounce_target_x
        unit.knockback_state.target_y = bounce_target_y
        unit.knockback_state.duration = PhysicsConstants.KNOCKBACK_DURATION * 0.6  # 反弹时间较短
        unit.knockback_state.elapsed_time = 0.0

        print(
            f"   ↩️ 反弹距离: {bounce_distance:.1f}, 方向: ({bounce_direction[0]:.2f}, {bounce_direction[1]:.2f})")

    def _stop_knockback(self, unit: Any):
        """停止击退"""
        unit.knockback_state.is_knocked_back = False
        if hasattr(unit, 'can_move'):
            unit.can_move = True
        if hasattr(unit, 'can_attack'):
            unit.can_attack = True
        unit.knockback_state = None
        print(f"   🛑 击退停止")

    def update_spatial_hash(self, units: List[Any]):
        """更新空间哈希表"""
        self.spatial_hash.clear()
        for unit in units:
            self.spatial_hash.add_unit(unit)

    def get_nearby_units(self, x: float, y: float, radius: float) -> List[Any]:
        """获取附近的单位"""
        return self.spatial_hash.get_nearby_units(x, y, radius)

    def detect_collisions(self, units: List[Any]) -> List[Tuple[Any, Any]]:
        """
        检测所有单位间的碰撞

        Args:
            units: 单位列表

        Returns:
            List[Tuple[Any, Any]]: 碰撞对列表
        """
        collisions = []

        # 更新空间哈希表
        self.update_spatial_hash(units)

        # 检测碰撞
        checked_pairs = set()

        for unit in units:
            # 获取附近的单位
            nearby_units = self.get_nearby_units(
                unit.x, unit.y,
                self.collision_detector.get_collision_radius(unit) * 2
            )

            for other_unit in nearby_units:
                if unit == other_unit:
                    continue

                # 避免重复检测
                pair = tuple(sorted([id(unit), id(other_unit)]))
                if pair in checked_pairs:
                    continue
                checked_pairs.add(pair)

                # 检测碰撞
                if self.check_collision(unit, other_unit):
                    collisions.append((unit, other_unit))

        return collisions

    def resolve_collision(self, unit1: Any, unit2: Any):
        """
        解决碰撞 - 将单位推开到不重叠的位置

        Args:
            unit1: 单位1
            unit2: 单位2
        """
        # 计算距离和方向
        dx = unit2.x - unit1.x
        dy = unit2.y - unit1.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance == 0:
            # 如果完全重叠，随机选择一个方向
            angle = random.uniform(0, 2 * math.pi)
            dx = math.cos(angle)
            dy = math.sin(angle)
            distance = 1.0

        # 标准化方向向量
        dx /= distance
        dy /= distance

        # 计算需要的分离距离
        radius1 = self.collision_detector.get_collision_radius(unit1)
        radius2 = self.collision_detector.get_collision_radius(unit2)
        required_distance = radius1 + radius2

        # 计算需要移动的距离
        separation_distance = (required_distance - distance) / 2

        # 移动单位
        unit1.x -= dx * separation_distance
        unit1.y -= dy * separation_distance
        unit2.x += dx * separation_distance
        unit2.y += dy * separation_distance

        # 边界检查
        unit1.x, unit1.y = self.knockback_applier.check_boundaries(
            unit1.x, unit1.y)
        unit2.x, unit2.y = self.knockback_applier.check_boundaries(
            unit2.x, unit2.y)

    def update(self, delta_time: float, units: List[Any] = None, game_map: List[List[Any]] = None):
        """
        更新物理系统

        Args:
            delta_time: 时间增量（秒）
            units: 单位列表（可选，用于碰撞检测）
            game_map: 游戏地图（可选，用于环境碰撞检测）
        """
        # 更新击退效果（包含环境碰撞检测）
        self.update_knockbacks(delta_time, game_map)

        # 如果提供了单位列表，检测和解决碰撞
        if units:
            collisions = self.detect_collisions(units)
            for unit1, unit2 in collisions:
                self.resolve_collision(unit1, unit2)

    def get_performance_stats(self) -> Dict[str, int]:
        """获取性能统计信息"""
        return {
            'collision_checks': self.collision_checks_count,
            'knockback_calculations': self.knockback_calculations_count,
            'active_knockbacks': len(self.active_knockbacks),
            'spatial_hash_cells': len(self.spatial_hash.grid),
            'wall_collisions': self.wall_collision_count
        }

    def reset_performance_stats(self):
        """重置性能统计"""
        self.collision_checks_count = 0
        self.knockback_calculations_count = 0
        self.wall_collision_count = 0
