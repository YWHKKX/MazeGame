#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
区域特效系统模块
"""

import math
import random
import pygame
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from .particle_system import ParticleSystem


@dataclass
class AreaEffect:
    """区域特效类"""
    x: float
    y: float
    radius: float
    duration: float
    effect_type: str
    damage_per_second: int = 0
    color: Tuple[int, int, int] = (255, 255, 255)
    opacity: float = 0.5

    # 动画属性
    pulse_speed: float = 1.0
    growth_rate: float = 0.0
    max_radius: float = 0.0

    # 状态
    current_time: float = 0.0
    finished: bool = False

    # 特殊效果
    particles: Optional[ParticleSystem] = None
    damage_tick: float = 0.0

    def __post_init__(self):
        """初始化后处理"""
        if self.max_radius == 0:
            self.max_radius = self.radius

        # 移除粒子系统创建，避免性能问题
        # 区域特效不需要复杂的粒子系统
        self.particles = None

    def _create_particles(self):
        """创建特效粒子"""
        if not self.particles:
            return

        if self.effect_type == "fire":
            self.particles.create_fire_particles(self.x, self.y, 15)
        elif self.effect_type == "explosion":
            self.particles.create_particle_burst(
                self.x, self.y, 20, (255, 215, 0), (3, 8), (100, 300), 800
            )
        elif self.effect_type == "lightning":
            self.particles.create_lightning_particles(self.x, self.y, 15)
        elif self.effect_type == "acid":
            self.particles.create_particle_burst(
                self.x, self.y, 12, (50, 205, 50), (2, 5), (50, 150), 1000
            )

    def update(self, delta_time: float):
        """更新区域特效"""
        if self.finished:
            return

        self.current_time += delta_time

        # 检查是否结束
        if self.current_time >= self.duration:
            self.finished = True
            return

        # 更新半径（生长效果）
        if self.growth_rate > 0:
            growth_factor = self.current_time / self.duration
            self.radius = self.max_radius * growth_factor

        # 更新粒子
        if self.particles:
            self.particles.update(delta_time)

        # 更新伤害计时
        self.damage_tick += delta_time

    def should_damage(self, target) -> bool:
        """检查是否应该对目标造成伤害"""
        if self.damage_per_second <= 0 or not target:
            return False

        # 检查距离
        distance = math.sqrt((target.x - self.x) ** 2 +
                             (target.y - self.y) ** 2)
        if distance > self.radius:
            return False

        # 检查伤害间隔（每秒一次）
        if self.damage_tick >= 1000:  # 1秒 = 1000毫秒
            self.damage_tick = 0
            return True

        return False

    def render(self, screen: pygame.Surface):
        """渲染区域特效"""
        if self.finished:
            return

        # 计算透明度
        alpha = int(255 * self.opacity *
                    (1 - self.current_time / self.duration))

        # 创建带透明度的表面
        effect_surface = pygame.Surface(
            (int(self.radius * 2), int(self.radius * 2)), pygame.SRCALPHA)

        if self.effect_type == "fire":
            self._render_fire_effect(effect_surface, alpha)
        elif self.effect_type == "explosion":
            self._render_explosion_effect(effect_surface, alpha)
        elif self.effect_type == "lightning":
            self._render_lightning_effect(effect_surface, alpha)
        elif self.effect_type == "acid":
            self._render_acid_effect(effect_surface, alpha)
        else:
            self._render_default_effect(effect_surface, alpha)

        # 绘制到主屏幕
        screen.blit(effect_surface, (int(self.x - self.radius),
                    int(self.y - self.radius)))

        # 渲染粒子
        if self.particles:
            self.particles.render(screen)

    def _render_fire_effect(self, surface: pygame.Surface, alpha: int):
        """渲染火焰效果"""
        # 绘制火焰圆形
        fire_color = (*self.color, alpha)
        pygame.draw.circle(surface, fire_color,
                           (int(self.radius), int(self.radius)), int(self.radius))

        # 添加火焰纹理
        for _ in range(5):
            flame_x = self.radius + \
                random.uniform(-self.radius * 0.5, self.radius * 0.5)
            flame_y = self.radius + \
                random.uniform(-self.radius * 0.5, self.radius * 0.5)
            flame_size = random.uniform(self.radius * 0.3, self.radius * 0.7)
            pygame.draw.circle(surface, fire_color, (int(
                flame_x), int(flame_y)), int(flame_size))

    def _render_explosion_effect(self, surface: pygame.Surface, alpha: int):
        """渲染爆炸效果"""
        # 绘制爆炸圆形
        explosion_color = (*self.color, alpha)
        pygame.draw.circle(surface, explosion_color,
                           (int(self.radius), int(self.radius)), int(self.radius))

        # 添加冲击波效果
        for i in range(3):
            wave_radius = self.radius * (0.3 + i * 0.2)
            wave_alpha = int(alpha * (1 - i * 0.3))
            wave_color = (*self.color, wave_alpha)
            pygame.draw.circle(surface, wave_color,
                               (int(self.radius), int(self.radius)), int(wave_radius), 3)

    def _render_lightning_effect(self, surface: pygame.Surface, alpha: int):
        """渲染闪电效果"""
        # 绘制闪电圆形
        lightning_color = (*self.color, alpha)
        pygame.draw.circle(surface, lightning_color,
                           (int(self.radius), int(self.radius)), int(self.radius))

        # 添加闪电分支
        for _ in range(8):
            start_x = self.radius
            start_y = self.radius
            end_x = self.radius + random.uniform(-self.radius, self.radius)
            end_y = self.radius + random.uniform(-self.radius, self.radius)
            pygame.draw.line(surface, lightning_color,
                             (int(start_x), int(start_y)), (int(end_x), int(end_y)), 2)

    def _render_acid_effect(self, surface: pygame.Surface, alpha: int):
        """渲染酸液效果"""
        # 绘制酸液圆形
        acid_color = (*self.color, alpha)
        pygame.draw.circle(surface, acid_color,
                           (int(self.radius), int(self.radius)), int(self.radius))

        # 添加腐蚀气泡效果
        for _ in range(6):
            bubble_x = self.radius + \
                random.uniform(-self.radius * 0.6, self.radius * 0.6)
            bubble_y = self.radius + \
                random.uniform(-self.radius * 0.6, self.radius * 0.6)
            bubble_size = random.uniform(self.radius * 0.1, self.radius * 0.3)
            pygame.draw.circle(surface, acid_color, (int(
                bubble_x), int(bubble_y)), int(bubble_size))

    def _render_default_effect(self, surface: pygame.Surface, alpha: int):
        """渲染默认效果"""
        effect_color = (*self.color, alpha)
        pygame.draw.circle(surface, effect_color,
                           (int(self.radius), int(self.radius)), int(self.radius))


class AreaEffectSystem:
    """区域特效系统管理器"""

    def __init__(self):
        self.effects: List[AreaEffect] = []
        self.effect_pool: List[AreaEffect] = []

    def create_fire_area(self, x: float, y: float, radius: float = 40,
                         duration: float = 4000, damage_per_second: int = 8) -> AreaEffect:
        """创建火焰区域"""
        return self._create_area_effect(
            x, y, radius, duration, "fire", damage_per_second,
            (255, 69, 0), 0.6  # 橙红色
        )

    def create_explosion(self, x: float, y: float, radius: float = 50,
                         duration: float = 1500) -> AreaEffect:
        """创建爆炸效果"""
        return self._create_area_effect(
            x, y, radius, duration, "explosion", 0,
            (255, 215, 0), 0.8  # 金黄色
        )

    def create_lightning_field(self, x: float, y: float, radius: float = 60,
                               duration: float = 2000) -> AreaEffect:
        """创建闪电领域"""
        return self._create_area_effect(
            x, y, radius, duration, "lightning", 0,
            (0, 191, 255), 0.7  # 天蓝色
        )

    def create_acid_pool(self, x: float, y: float, radius: float = 15,
                         duration: float = 5000, damage_per_second: int = 5) -> AreaEffect:
        """创建酸液池"""
        return self._create_area_effect(
            x, y, radius, duration, "acid", damage_per_second,
            (50, 205, 50), 0.6  # 酸绿色
        )

    def create_healing_aura(self, x: float, y: float, radius: float = 80,
                            duration: float = 6000) -> AreaEffect:
        """创建治疗光环"""
        return self._create_area_effect(
            x, y, radius, duration, "healing", 0,
            (0, 255, 0), 0.3  # 绿色
        )

    def _create_area_effect(self, x: float, y: float, radius: float, duration: float,
                            effect_type: str, damage_per_second: int,
                            color: Tuple[int, int, int], opacity: float) -> AreaEffect:
        """创建区域特效"""
        # 尝试从对象池获取
        if self.effect_pool:
            effect = self.effect_pool.pop()
            effect.x = x
            effect.y = y
            effect.radius = radius
            effect.duration = duration
            effect.effect_type = effect_type
            effect.damage_per_second = damage_per_second
            effect.color = color
            effect.opacity = opacity
            effect.current_time = 0.0
            effect.finished = False
            effect.damage_tick = 0.0
            effect.particles = None
            effect.__post_init__()
        else:
            effect = AreaEffect(x, y, radius, duration,
                                effect_type, damage_per_second, color, opacity)

        self.effects.append(effect)
        return effect

    def update(self, delta_time: float):
        """更新所有区域特效"""
        for effect in self.effects[:]:
            effect.update(delta_time)
            if effect.finished:
                self.effects.remove(effect)
                # 将特效返回对象池
                if len(self.effect_pool) < 20:  # 限制对象池大小
                    self.effect_pool.append(effect)

    def check_damage(self, targets: List) -> List[Tuple[AreaEffect, Any]]:
        """检查区域特效对目标的伤害"""
        damage_events = []
        for effect in self.effects:
            for target in targets:
                if effect.should_damage(target):
                    damage_events.append((effect, target))
        return damage_events

    def render(self, screen: pygame.Surface):
        """渲染所有区域特效"""
        for effect in self.effects:
            effect.render(screen)

    def clear(self):
        """清空所有区域特效"""
        self.effects.clear()
        self.effect_pool.clear()
