#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投射物系统模块
"""

import math
import random
import pygame
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Projectile:
    """投射物类"""
    x: float
    y: float
    target_x: float
    target_y: float
    speed: float
    damage: int
    color: Tuple[int, int, int]
    size: float
    projectile_type: str
    life: float
    max_life: float

    # 轨迹属性
    trail_points: List[Tuple[float, float]] = None
    max_trail_length: int = 15

    # 特殊效果
    rotation: float = 0.0
    rotation_speed: float = 0.0
    tracking: bool = False
    penetration: bool = False
    bounces: int = 0
    max_bounces: int = 0

    # 状态
    finished: bool = False
    hit_target: bool = False

    def __post_init__(self):
        """初始化后处理"""
        if self.trail_points is None:
            self.trail_points = [(self.x, self.y)]
        # 计算初始方向
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            self.vx = (dx / distance) * self.speed
            self.vy = (dy / distance) * self.speed
        else:
            self.vx = 0
            self.vy = 0

    def update(self, delta_time: float, targets: List = None):
        """更新投射物状态"""
        if self.finished:
            return

        # 更新旋转
        if self.rotation_speed != 0:
            self.rotation += self.rotation_speed * delta_time * 0.001

        # 追踪目标
        if self.tracking and targets:
            self._update_tracking(targets)

        # 更新位置
        self.x += self.vx * delta_time * 0.001
        self.y += self.vy * delta_time * 0.001

        # 更新轨迹
        self.trail_points.append((self.x, self.y))
        if len(self.trail_points) > self.max_trail_length:
            self.trail_points.pop(0)

        # 检查生命周期
        self.life -= delta_time
        if self.life <= 0:
            self.finished = True

    def _update_tracking(self, targets: List):
        """更新追踪逻辑"""
        if not targets:
            return

        # 找到最近的目标
        nearest_target = None
        nearest_distance = float('inf')

        for target in targets:
            distance = math.sqrt((target.x - self.x) **
                                 2 + (target.y - self.y) ** 2)
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_target = target

        if nearest_target and nearest_distance < 200:  # 追踪范围
            # 计算转向角度
            dx = nearest_target.x - self.x
            dy = nearest_target.y - self.y
            target_angle = math.atan2(dy, dx)

            current_angle = math.atan2(self.vy, self.vx)

            # 限制转向速度
            angle_diff = target_angle - current_angle
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi

            # 应用转向
            turn_rate = 180 * math.pi / 180  # 度转弧度
            max_turn = turn_rate * 0.016  # 假设60FPS

            if abs(angle_diff) > max_turn:
                angle_diff = max_turn if angle_diff > 0 else -max_turn

            new_angle = current_angle + angle_diff
            self.vx = math.cos(new_angle) * self.speed
            self.vy = math.sin(new_angle) * self.speed

    def check_collision(self, target) -> bool:
        """检查与目标的碰撞"""
        if not target or self.hit_target:
            return False

        distance = math.sqrt((target.x - self.x) ** 2 +
                             (target.y - self.y) ** 2)
        collision_distance = self.size + target.size

        if distance <= collision_distance:
            if not self.penetration:
                self.hit_target = True
                if self.bounces >= self.max_bounces:
                    self.finished = True
            return True

        return False

    def render(self, screen: pygame.Surface):
        """渲染投射物"""
        if self.finished:
            return

        # 渲染轨迹
        if len(self.trail_points) > 1:
            for i in range(1, len(self.trail_points)):
                alpha = int(255 * (i / len(self.trail_points)))
                trail_color = (*self.color, alpha)

                start_pos = (
                    int(self.trail_points[i-1][0]), int(self.trail_points[i-1][1]))
                end_pos = (int(self.trail_points[i][0]), int(
                    self.trail_points[i][1]))

                pygame.draw.line(screen, self.color, start_pos, end_pos, 2)

        # 渲染投射物本体
        if self.projectile_type == "arrow":
            self._render_arrow(screen)
        elif self.projectile_type == "tower_arrow":
            self._render_tower_arrow(screen)
        elif self.projectile_type == "fireball":
            self._render_fireball(screen)
        elif self.projectile_type == "lightning":
            self._render_lightning(screen)
        else:
            # 默认圆形投射物 - 添加调试信息
            print(
                f"🔍 投射物类型: {self.projectile_type}, 位置: ({self.x:.1f}, {self.y:.1f}), 大小: {self.size}")
            pygame.draw.circle(screen, self.color, (int(
                self.x), int(self.y)), int(self.size))

    def _render_arrow(self, screen: pygame.Surface):
        """渲染箭矢"""
        # 计算箭矢方向
        angle = math.atan2(self.vy, self.vx)

        # 箭矢顶点
        tip_x = self.x + math.cos(angle) * self.size
        tip_y = self.y + math.sin(angle) * self.size

        # 箭矢尾部
        tail_x = self.x - math.cos(angle) * self.size * 0.8
        tail_y = self.y - math.sin(angle) * self.size * 0.8

        # 箭矢两侧
        side_angle1 = angle + math.pi / 2
        side_angle2 = angle - math.pi / 2
        side_x1 = tail_x + math.cos(side_angle1) * self.size * 0.3
        side_y1 = tail_y + math.sin(side_angle1) * self.size * 0.3
        side_x2 = tail_x + math.cos(side_angle2) * self.size * 0.3
        side_y2 = tail_y + math.sin(side_angle2) * self.size * 0.3

        # 绘制箭矢
        points = [
            (int(tip_x), int(tip_y)),
            (int(side_x1), int(side_y1)),
            (int(side_x2), int(side_y2))
        ]
        pygame.draw.polygon(screen, self.color, points)

    def _render_tower_arrow(self, screen: pygame.Surface):
        """渲染箭塔箭矢 - 与弓箭手保持一致的直线设计"""
        print(
            f"🏹 渲染箭塔箭矢: 位置({self.x:.1f}, {self.y:.1f}), 速度({self.vx:.1f}, {self.vy:.1f}), 大小: {self.size}")
        # 计算箭矢方向
        angle = math.atan2(self.vy, self.vx)

        # 箭矢顶点
        tip_x = self.x + math.cos(angle) * self.size
        tip_y = self.y + math.sin(angle) * self.size

        # 箭矢尾部
        tail_x = self.x - math.cos(angle) * self.size * 0.8
        tail_y = self.y - math.sin(angle) * self.size * 0.8

        # 箭矢两侧
        side_angle1 = angle + math.pi / 2
        side_angle2 = angle - math.pi / 2
        side_x1 = tail_x + math.cos(side_angle1) * self.size * 0.3
        side_y1 = tail_y + math.sin(side_angle1) * self.size * 0.3
        side_x2 = tail_x + math.cos(side_angle2) * self.size * 0.3
        side_y2 = tail_y + math.sin(side_angle2) * self.size * 0.3

        # 绘制箭矢 - 与普通箭矢相同的三角形设计
        points = [
            (int(tip_x), int(tip_y)),
            (int(side_x1), int(side_y1)),
            (int(side_x2), int(side_y2))
        ]
        pygame.draw.polygon(screen, self.color, points)

        # 如果是暴击箭矢，添加发光效果
        if hasattr(self, 'glow_effect') and self.glow_effect:
            # 绘制发光光环
            glow_color = (255, 255, 0, 100)  # 半透明黄色
            glow_surface = pygame.Surface(
                (int(self.size * 6), int(self.size * 6)), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color,
                               (int(self.size * 3), int(self.size * 3)), int(self.size * 3))
            screen.blit(glow_surface, (int(self.x - self.size * 3),
                        int(self.y - self.size * 3)))

    def _render_fireball(self, screen: pygame.Surface):
        """渲染火球"""
        # 绘制火球主体
        pygame.draw.circle(screen, self.color, (int(
            self.x), int(self.y)), int(self.size))

        # 绘制火焰效果
        fire_colors = [(255, 0, 0), (255, 69, 0), (255, 215, 0)]
        for i, fire_color in enumerate(fire_colors):
            fire_size = self.size * (0.7 - i * 0.2)
            pygame.draw.circle(screen, fire_color, (int(
                self.x), int(self.y)), int(fire_size))

    def _render_lightning(self, screen: pygame.Surface):
        """渲染闪电"""
        # 绘制闪电主体
        pygame.draw.circle(screen, self.color, (int(
            self.x), int(self.y)), int(self.size))

        # 绘制闪电分支效果
        for _ in range(3):
            branch_angle = random.uniform(0, 2 * math.pi)
            branch_length = self.size * 0.5
            end_x = self.x + math.cos(branch_angle) * branch_length
            end_y = self.y + math.sin(branch_angle) * branch_length
            pygame.draw.line(screen, (255, 255, 255),
                             (int(self.x), int(self.y)),
                             (int(end_x), int(end_y)), 2)

    def reset(self):
        """重置投射物状态"""
        self.finished = False
        self.hit_target = False
        self.trail_points.clear()
        self.trail_points.append((self.x, self.y))
        # 注意：projectile_type 在 _get_or_create_projectile 中设置，这里不需要重置


class ProjectileSystem:
    """投射物系统管理器"""

    def __init__(self):
        self.projectiles: List[Projectile] = []
        self.projectile_pool: List[Projectile] = []

    def create_arrow(self, x: float, y: float, target_x: float, target_y: float,
                     speed: float = 400, damage: int = 20) -> Projectile:
        """创建箭矢"""
        arrow = self._get_or_create_projectile(
            x, y, target_x, target_y, speed, damage,
            (139, 69, 19), 4, "arrow", 3000  # 棕色，3秒生命周期
        )
        return arrow

    def create_fireball(self, x: float, y: float, target_x: float, target_y: float,
                        speed: float = 300, damage: int = 30) -> Projectile:
        """创建火球"""
        fireball = self._get_or_create_projectile(
            x, y, target_x, target_y, speed, damage,
            (255, 69, 0), 6, "fireball", 4000  # 橙红色，4秒生命周期
        )
        fireball.rotation_speed = 360  # 旋转效果
        return fireball

    def create_tracking_arrow(self, x: float, y: float, target_x: float, target_y: float,
                              speed: float = 350, damage: int = 25) -> Projectile:
        """创建追踪箭"""
        arrow = self._get_or_create_projectile(
            x, y, target_x, target_y, speed, damage,
            (50, 205, 50), 4, "arrow", 4000  # 绿色，4秒生命周期
        )
        arrow.tracking = True
        return arrow

    def create_lightning_bolt(self, x: float, y: float, target_x: float, target_y: float,
                              speed: float = 500, damage: int = 40) -> Projectile:
        """创建闪电球"""
        lightning = self._get_or_create_projectile(
            x, y, target_x, target_y, speed, damage,
            (0, 191, 255), 5, "lightning", 2000  # 天蓝色，2秒生命周期
        )
        return lightning

    def create_tower_arrow(self, x: float, y: float, target_x: float, target_y: float,
                           speed: float = 500, damage: int = 16, is_critical: bool = False) -> Projectile:
        """创建箭塔箭矢 - 与弓箭手保持一致"""
        if is_critical:
            # 暴击箭矢 - 金色，更大，更快
            arrow = self._get_or_create_projectile(
                x, y, target_x, target_y, speed, damage,
                (255, 215, 0), 6, "tower_arrow", 3000  # 金色，3秒生命周期
            )
            arrow.glow_effect = True
            arrow.trail_effect = True
        else:
            # 普通箭矢 - 灰色
            arrow = self._get_or_create_projectile(
                x, y, target_x, target_y, speed, damage,
                (200, 200, 200), 4, "tower_arrow", 3000  # 灰色，3秒生命周期
            )
            arrow.trail_effect = True

        return arrow

    def _get_or_create_projectile(self, x: float, y: float, target_x: float, target_y: float,
                                  speed: float, damage: int, color: Tuple[int, int, int],
                                  size: float, projectile_type: str, max_life: float) -> Projectile:
        """获取或创建投射物"""
        # 尝试从对象池获取
        if self.projectile_pool:
            projectile = self.projectile_pool.pop()
            projectile.x = x
            projectile.y = y
            projectile.target_x = target_x
            projectile.target_y = target_y
            projectile.speed = speed
            projectile.damage = damage
            projectile.color = color
            projectile.size = size
            projectile.projectile_type = projectile_type
            projectile.max_life = max_life
            projectile.life = max_life
            projectile.reset()
        else:
            projectile = Projectile(x, y, target_x, target_y, speed, damage, color, size,
                                    projectile_type, max_life, max_life)

        self.projectiles.append(projectile)
        return projectile

    def update(self, delta_time: float, targets: List = None):
        """更新所有投射物"""
        for projectile in self.projectiles[:]:
            projectile.update(delta_time, targets)
            if projectile.finished:
                self.projectiles.remove(projectile)
                # 将投射物返回对象池
                if len(self.projectile_pool) < 50:  # 限制对象池大小
                    self.projectile_pool.append(projectile)

    def check_collisions(self, targets: List) -> List[Tuple[Projectile, Any]]:
        """检查所有投射物的碰撞"""
        collisions = []
        for projectile in self.projectiles:
            for target in targets:
                if projectile.check_collision(target):
                    collisions.append((projectile, target))
                    break  # 每个投射物只碰撞一个目标
        return collisions

    def render(self, screen: pygame.Surface):
        """渲染所有投射物"""
        for projectile in self.projectiles:
            projectile.render(screen)

    def clear(self):
        """清空所有投射物"""
        self.projectiles.clear()
        self.projectile_pool.clear()
