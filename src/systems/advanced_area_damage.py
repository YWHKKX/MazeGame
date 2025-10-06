#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级范围攻击系统
支持扇形、圆形、长方形三种攻击区域类型
"""

import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from src.utils.logger import game_logger


class AreaAttackType(Enum):
    """范围攻击类型枚举"""
    CIRCLE = "circle"      # 圆形区域
    SECTOR = "sector"      # 扇形区域
    RECTANGLE = "rectangle"  # 长方形区域


@dataclass
class AreaAttackConfig:
    """范围攻击配置"""
    attack_type: AreaAttackType
    damage_ratio: float
    target_type: str  # 'enemy', 'ally', 'all'
    effect_type: str

    # 圆形区域参数
    radius: float = 50.0

    # 扇形区域参数
    angle: float = 60.0  # 扇形角度（度）
    direction: float = 0.0  # 扇形方向（度，0度为右方向）

    # 长方形区域参数
    width: float = 100.0
    height: float = 20.0
    length: float = 100.0  # 长方形长度（与width相同，为了语义清晰）


@dataclass
class AreaAttackResult:
    """范围攻击结果"""
    success: bool
    targets_hit: int
    total_damage: int
    message: str


class AdvancedAreaDamageSystem:
    """高级范围攻击系统"""

    def __init__(self, game_instance):
        """
        初始化高级范围攻击系统

        Args:
            game_instance: 游戏实例引用
        """
        self.game_instance = game_instance

    def apply_area_damage(self, attacker, primary_target, damage: float,
                          start_x: float, start_y: float, direction: float = 0.0,
                          area_config: Optional[AreaAttackConfig] = None) -> AreaAttackResult:
        """
        应用范围伤害（扩展版本）

        Args:
            attacker: 攻击者对象
            primary_target: 主要目标（已受到伤害的目标）
            damage: 基础伤害值
            start_x, start_y: 范围攻击起始位置
            direction: 攻击方向（度，0度为右方向）
            area_config: 范围攻击配置，如果为None则使用攻击者的area_damage配置

        Returns:
            AreaAttackResult: 范围攻击结果
        """
        if not self.game_instance:
            return AreaAttackResult(False, 0, 0, "游戏实例不可用")

        # 获取范围攻击配置
        if area_config is None:
            area_config = self._get_attacker_area_config(
                attacker, start_x, start_y, direction)

        if not area_config:
            return AreaAttackResult(False, 0, 0, "无效的范围攻击配置")

        # 计算范围伤害值
        area_damage = int(damage * area_config.damage_ratio)
        is_healing = area_damage < 0
        if is_healing:
            area_damage = abs(area_damage)

        # 根据攻击类型获取目标
        if area_config.attack_type == AreaAttackType.CIRCLE:
            targets = self._get_targets_in_circle(attacker, start_x, start_y,
                                                  area_config.radius, area_config.target_type)
        elif area_config.attack_type == AreaAttackType.SECTOR:
            targets = self._get_targets_in_sector(attacker, start_x, start_y,
                                                  area_config.radius, area_config.angle,
                                                  direction, area_config.target_type)
        elif area_config.attack_type == AreaAttackType.RECTANGLE:
            targets = self._get_targets_in_rectangle(attacker, start_x, start_y,
                                                     area_config.width, area_config.height,
                                                     direction, area_config.target_type)
        else:
            return AreaAttackResult(False, 0, 0, f"不支持的攻击类型: {area_config.attack_type}")

        # 对目标造成伤害
        targets_hit = 0
        total_damage = 0

        for target in targets:
            is_primary_target = (target == primary_target)

            # 计算伤害衰减
            damage_factor = self._calculate_damage_factor(
                target, start_x, start_y, area_config, direction)

            if damage_factor <= 0:
                continue

            final_damage = max(1, int(area_damage * damage_factor))

            # 应用护甲减免
            if hasattr(self.game_instance, 'combat_system'):
                final_damage = self.game_instance.combat_system._calculate_armor_reduction(
                    final_damage, target)

            # 造成伤害或治疗 - 所有目标都应该受到伤害
            if is_healing:
                # 治疗
                old_health = target.health
                target.health += final_damage
                if hasattr(target, 'max_health'):
                    target.health = min(target.health, target.max_health)
                actual_healing = target.health - old_health
                game_logger.info(
                    f"💚 {attacker.type} 的范围治疗对 {target.type} 治疗 {actual_healing} 点生命值")
            else:
                # 伤害 - 所有目标都受到伤害
                target.health -= final_damage
                target.health = max(0, target.health)
                if final_damage >= 5:
                    game_logger.info(
                        f"Range attack: {attacker.type} hits {target.type} for {final_damage} damage")

            # 触发伤害事件
            if hasattr(target, '_take_damage'):
                target._take_damage(final_damage, attacker)

            # 触发击退动画
            if (not is_healing and self.game_instance.physics_system and
                    self.game_instance.knockback_animation):
                attack_type = self._get_attack_type(attacker)
                self.game_instance.combat_system._execute_knockback_with_animation(
                    attacker, target, final_damage, attack_type)

            targets_hit += 1
            total_damage += final_damage

            # 创建特效（只有主目标创建攻击特效）
            if self.game_instance.effect_manager and is_primary_target:
                self._create_area_damage_effect(attacker, target, final_damage,
                                                area_config, is_primary_target)

        return AreaAttackResult(
            success=True,
            targets_hit=targets_hit,
            total_damage=total_damage,
            message=f"范围攻击命中 {targets_hit} 个目标，总伤害 {total_damage}"
        )

    def _get_attacker_area_config(self, attacker, start_x: float, start_y: float,
                                  direction: float) -> Optional[AreaAttackConfig]:
        """获取攻击者的范围攻击配置"""
        area_damage_config = getattr(attacker, 'area_damage', {})
        if not area_damage_config:
            return None

        # 确定攻击类型
        attack_type_str = area_damage_config.get('area_type', 'circle')
        if attack_type_str == 'sector':
            attack_type = AreaAttackType.SECTOR
        elif attack_type_str == 'rectangle':
            attack_type = AreaAttackType.RECTANGLE
        else:
            attack_type = AreaAttackType.CIRCLE

        return AreaAttackConfig(
            attack_type=attack_type,
            damage_ratio=area_damage_config.get('damage_ratio', 0.5),
            target_type=area_damage_config.get('type', 'enemy'),
            effect_type=area_damage_config.get(
                'effect_type', 'area_explosion'),
            radius=area_damage_config.get('radius', 50.0),
            angle=area_damage_config.get('angle', 60.0),
            direction=direction,
            width=area_damage_config.get('width', 100.0),
            height=area_damage_config.get('height', 20.0)
        )

    def _get_targets_in_circle(self, attacker, center_x: float, center_y: float,
                               radius: float, target_type: str) -> List[Any]:
        """获取圆形区域内的目标"""
        targets = []

        # 获取所有可能的目标
        all_units = self._get_all_units()

        for unit in all_units:
            if not unit or unit.health <= 0:
                continue

            # 计算距离
            distance = math.sqrt((unit.x - center_x) **
                                 2 + (unit.y - center_y) ** 2)
            if distance > radius:
                continue

            # 根据目标类型筛选
            if self._is_valid_target(attacker, unit, target_type):
                targets.append(unit)

        return targets

    def _get_targets_in_sector(self, attacker, center_x: float, center_y: float,
                               radius: float, angle: float, direction: float,
                               target_type: str) -> List[Any]:
        """获取扇形区域内的目标"""
        targets = []

        # 获取所有可能的目标
        all_units = self._get_all_units()

        # 将角度转换为弧度
        direction_rad = math.radians(direction)
        half_angle_rad = math.radians(angle / 2)

        for unit in all_units:
            if not unit or unit.health <= 0:
                continue

            # 计算距离
            distance = math.sqrt((unit.x - center_x) **
                                 2 + (unit.y - center_y) ** 2)
            if distance > radius:
                continue

            # 计算角度
            unit_angle = math.atan2(unit.y - center_y, unit.x - center_x)

            # 计算角度差
            angle_diff = abs(unit_angle - direction_rad)
            if angle_diff > math.pi:
                angle_diff = 2 * math.pi - angle_diff

            # 检查是否在扇形内
            if angle_diff <= half_angle_rad:
                if self._is_valid_target(attacker, unit, target_type):
                    targets.append(unit)

        return targets

    def _get_targets_in_rectangle(self, attacker, start_x: float, start_y: float,
                                  width: float, height: float, direction: float,
                                  target_type: str) -> List[Any]:
        """获取长方形区域内的目标"""
        targets = []

        # 获取所有可能的目标
        all_units = self._get_all_units()

        # 将方向转换为弧度
        direction_rad = math.radians(direction)
        cos_dir = math.cos(direction_rad)
        sin_dir = math.sin(direction_rad)

        # 计算长方形的四个角点
        half_width = width / 2
        half_height = height / 2

        # 旋转后的角点
        corners = [
            (start_x - half_width * cos_dir + half_height * sin_dir,
             start_y - half_width * sin_dir - half_height * cos_dir),
            (start_x + half_width * cos_dir + half_height * sin_dir,
             start_y + half_width * sin_dir - half_height * cos_dir),
            (start_x + half_width * cos_dir - half_height * sin_dir,
             start_y + half_width * sin_dir + half_height * cos_dir),
            (start_x - half_width * cos_dir - half_height * sin_dir,
             start_y - half_width * sin_dir + half_height * cos_dir)
        ]

        for unit in all_units:
            if not unit or unit.health <= 0:
                continue

            # 检查点是否在长方形内
            if self._point_in_rotated_rectangle(unit.x, unit.y, corners):
                if self._is_valid_target(attacker, unit, target_type):
                    targets.append(unit)

        return targets

    def _point_in_rotated_rectangle(self, x: float, y: float, corners: List[Tuple[float, float]]) -> bool:
        """检查点是否在旋转的长方形内"""
        # 使用射线法判断点是否在多边形内
        n = len(corners)
        inside = False

        p1x, p1y = corners[0]
        for i in range(1, n + 1):
            p2x, p2y = corners[i % n]
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

    def _get_all_units(self) -> List[Any]:
        """获取所有可能的单位"""
        all_units = []

        # 添加生物
        if hasattr(self.game_instance, 'monsters'):
            all_units.extend(self.game_instance.monsters)

        # 添加英雄
        if hasattr(self.game_instance, 'heroes'):
            all_units.extend(self.game_instance.heroes)

        # 添加建筑
        if hasattr(self.game_instance, 'building_manager') and self.game_instance.building_manager:
            buildings = self.game_instance.building_manager.buildings
            if buildings:
                all_units.extend(buildings)

        return all_units

    def _is_valid_target(self, attacker, target, target_type: str) -> bool:
        """检查目标是否有效"""
        if target == attacker:
            return False

        if target_type == 'enemy':
            return self._is_enemy_of(attacker, target)
        elif target_type == 'ally':
            return not self._is_enemy_of(attacker, target)
        elif target_type == 'all':
            return True

        return False

    def _is_enemy_of(self, attacker, target) -> bool:
        """检查是否为敌人关系"""
        # 简化的敌人关系判断
        if hasattr(attacker, 'is_enemy') and hasattr(target, 'is_enemy'):
            return attacker.is_enemy != target.is_enemy
        return True  # 默认认为是敌人

    def _calculate_damage_factor(self, target, start_x: float, start_y: float,
                                 area_config: AreaAttackConfig, direction: float) -> float:
        """计算伤害衰减因子"""
        distance = math.sqrt((target.x - start_x) ** 2 +
                             (target.y - start_y) ** 2)

        if area_config.attack_type == AreaAttackType.CIRCLE:
            # 圆形：距离衰减
            return max(0.1, 1.0 - (distance / area_config.radius))
        elif area_config.attack_type == AreaAttackType.SECTOR:
            # 扇形：距离衰减
            return max(0.1, 1.0 - (distance / area_config.radius))
        elif area_config.attack_type == AreaAttackType.RECTANGLE:
            # 长方形：基于到中心线的距离衰减
            center_distance = self._distance_to_rectangle_center_line(
                target.x, target.y, start_x, start_y, direction, area_config.width)
            return max(0.1, 1.0 - (center_distance / (area_config.width / 2)))

        return 1.0

    def _distance_to_rectangle_center_line(self, x: float, y: float, start_x: float,
                                           start_y: float, direction: float, width: float) -> float:
        """计算点到长方形中心线的距离"""
        # 将方向转换为弧度
        direction_rad = math.radians(direction)

        # 计算点到中心线的垂直距离
        dx = x - start_x
        dy = y - start_y

        # 旋转到长方形坐标系
        cos_dir = math.cos(-direction_rad)
        sin_dir = math.sin(-direction_rad)

        rotated_x = dx * cos_dir - dy * sin_dir
        rotated_y = dx * sin_dir + dy * cos_dir

        # 返回Y坐标的绝对值（到中心线的距离）
        return abs(rotated_y)

    def _get_attack_type(self, attacker) -> str:
        """获取攻击类型"""
        if hasattr(attacker, 'attack_type'):
            return attacker.attack_type

        # 委托给战斗系统获取攻击类型
        if hasattr(self.game_instance, 'combat_system'):
            return self.game_instance.combat_system._get_attack_type(attacker)

        # 备用方法：直接检查建筑类型
        if hasattr(attacker, 'building_type') and hasattr(attacker.building_type, 'value'):
            if attacker.building_type.value == 'arrow_tower':
                from src.core.enums import AttackType
                return AttackType.PIERCING.value
            elif attacker.building_type.value == 'arcane_tower':
                from src.core.enums import AttackType
                return AttackType.AREA.value

        from src.core.enums import AttackType
        return AttackType.NORMAL.value

    def _create_area_damage_effect(self, attacker, target, damage: int,
                                   area_config: AreaAttackConfig, is_primary_target: bool):
        """创建范围伤害特效"""
        if not self.game_instance.effect_manager:
            return

        try:
            effect_type = area_config.effect_type
            if effect_type == 'None':
                return

            # 根据攻击类型调整特效参数
            if area_config.attack_type == AreaAttackType.SECTOR:
                # 扇形特效
                effect = self.game_instance.effect_manager.create_visual_effect(
                    effect_type=effect_type,
                    x=attacker.x,
                    y=attacker.y,
                    target_x=target.x,
                    target_y=target.y,
                    damage=damage,
                    attacker_name=getattr(attacker, 'name', attacker.type),
                    duration=0.5 if is_primary_target else 0.3,
                    size=5 if is_primary_target else 3,
                    color=(255, 150, 0) if is_primary_target else (
                        255, 100, 0),
                    area_type='sector',
                    angle=area_config.angle,
                    direction=area_config.direction
                )
            elif area_config.attack_type == AreaAttackType.RECTANGLE:
                # 长方形特效
                effect = self.game_instance.effect_manager.create_visual_effect(
                    effect_type=effect_type,
                    x=attacker.x,
                    y=attacker.y,
                    target_x=target.x,
                    target_y=target.y,
                    damage=damage,
                    attacker_name=getattr(attacker, 'name', attacker.type),
                    duration=0.5 if is_primary_target else 0.3,
                    size=5 if is_primary_target else 3,
                    color=(255, 150, 0) if is_primary_target else (
                        255, 100, 0),
                    area_type='rectangle',
                    width=area_config.width,
                    height=area_config.height,
                    direction=area_config.direction
                )
            else:
                # 圆形特效
                effect = self.game_instance.effect_manager.create_visual_effect(
                    effect_type=effect_type,
                    x=attacker.x,
                    y=attacker.y,
                    target_x=target.x,
                    target_y=target.y,
                    damage=damage,
                    attacker_name=getattr(attacker, 'name', attacker.type),
                    duration=0.5 if is_primary_target else 0.3,
                    size=5 if is_primary_target else 3,
                    color=(255, 150, 0) if is_primary_target else (
                        255, 100, 0),
                    area_type='circle',
                    radius=area_config.radius
                )
        except Exception as e:
            game_logger.info(f"❌ 范围伤害特效创建错误: {e}")


def get_advanced_area_damage_system(game_instance) -> AdvancedAreaDamageSystem:
    """
    获取高级范围攻击系统实例（单例模式）

    Args:
        game_instance: 游戏实例

    Returns:
        AdvancedAreaDamageSystem: 高级范围攻击系统实例
    """
    if not hasattr(game_instance, '_advanced_area_damage_system'):
        game_instance._advanced_area_damage_system = AdvancedAreaDamageSystem(
            game_instance)

    return game_instance._advanced_area_damage_system
