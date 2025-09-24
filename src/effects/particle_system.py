#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
粒子系统模块
"""

import math
import random
import pygame
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Particle:
    """粒子类"""
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    size: float
    life: float
    max_life: float
    gravity: float = 0.0
    fade: bool = True
    finished: bool = False

    def update(self, delta_time: float):
        """更新粒子状态"""
        self.x += self.vx * delta_time * 0.001
        self.y += self.vy * delta_time * 0.001
        self.vy += self.gravity * delta_time

        self.life -= delta_time

        if self.life <= 0:
            self.finished = True

    def render(self, screen: pygame.Surface):
        """渲染粒子"""
        if self.finished:
            return

        alpha = 255
        if self.fade:
            alpha = int(255 * (self.life / self.max_life))

        # 创建带透明度的颜色
        color_with_alpha = (*self.color, alpha)

        # 绘制粒子
        pygame.draw.circle(screen, self.color, (int(
            self.x), int(self.y)), int(self.size))

    def reset(self):
        """重置粒子状态"""
        self.finished = False
        self.life = self.max_life


class ParticleSystem:
    """粒子系统管理器"""

    def __init__(self):
        self.particles: List[Particle] = []
        self.particle_pool: List[Particle] = []

    def create_particle(self, x: float, y: float, vx: float, vy: float,
                        color: Tuple[int, int, int], size: float,
                        life: float, gravity: float = 0.0, fade: bool = True) -> Particle:
        """创建粒子"""
        # 尝试从对象池获取粒子
        if self.particle_pool:
            particle = self.particle_pool.pop()
            particle.x = x
            particle.y = y
            particle.vx = vx
            particle.vy = vy
            particle.color = color
            particle.size = size
            particle.life = life
            particle.max_life = life
            particle.gravity = gravity
            particle.fade = fade
            particle.reset()
        else:
            particle = Particle(x, y, vx, vy, color, size,
                                life, life, gravity, fade)

        self.particles.append(particle)
        return particle

    def create_particle_burst(self, x: float, y: float, count: int,
                              color: Tuple[int, int, int], size_range: Tuple[float, float],
                              velocity_range: Tuple[float, float], life: float,
                              gravity: float = 0.0):
        """创建粒子爆发"""
        for _ in range(count):
            # 随机方向
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(velocity_range[0], velocity_range[1])
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            # 随机大小
            size = random.uniform(size_range[0], size_range[1])

            self.create_particle(x, y, vx, vy, color, size, life, gravity)

    def create_spark_effect(self, x: float, y: float, count: int = 8,
                            color: Tuple[int, int, int] = (255, 215, 0)):
        """创建火花特效"""
        self.create_particle_burst(
            x, y, count, color, (2, 4), (50, 100), 300, 0.5
        )

    def create_blood_effect(self, x: float, y: float, count: int = 6):
        """创建血液特效"""
        self.create_particle_burst(
            x, y, count, (139, 0, 0), (3, 6), (60, 120), 500, 0.8
        )

    def create_fire_particles(self, x: float, y: float, count: int = 10):
        """创建火焰粒子"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 50  # 向上飘浮

            # 火焰颜色渐变
            colors = [(255, 0, 0), (255, 69, 0), (255, 215, 0)]
            color = random.choice(colors)

            self.create_particle(x, y, vx, vy, color,
                                 random.uniform(4, 8), 800, -0.3)

    def create_smoke_particles(self, x: float, y: float, count: int = 8):
        """创建烟雾粒子"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 30  # 向上飘浮

            self.create_particle(x, y, vx, vy, (105, 105, 105),
                                 random.uniform(6, 12), 1200, -0.2)

    def create_lightning_particles(self, x: float, y: float, count: int = 12):
        """创建闪电粒子"""
        self.create_particle_burst(
            x, y, count, (255, 255, 255), (2, 5), (80, 150), 200, 0.0
        )

    def update(self, delta_time: float):
        """更新所有粒子"""
        for particle in self.particles[:]:
            particle.update(delta_time)
            if particle.finished:
                self.particles.remove(particle)
                # 将粒子返回对象池
                if len(self.particle_pool) < 100:  # 限制对象池大小
                    self.particle_pool.append(particle)

    def render(self, screen: pygame.Surface):
        """渲染所有粒子"""
        for particle in self.particles:
            particle.render(screen)

    def clear(self):
        """清空所有粒子"""
        self.particles.clear()
        self.particle_pool.clear()
