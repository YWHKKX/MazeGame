#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
粒子系统模块
"""

import math
import random
import pygame
import time
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from .glow_effect import get_glow_manager
from .projectile_system import Projectile
from src.utils.logger import game_logger


class TimeManager:
    """独立的时间管理器，统一处理时间单位转换"""

    @staticmethod
    def delta_to_seconds(delta_time: float) -> float:
        """将毫秒转换为秒"""
        return delta_time * 0.001

    @staticmethod
    def seconds_to_delta(seconds: float) -> float:
        """将秒转换为毫秒"""
        return seconds * 1000.0

    @staticmethod
    def normalize_time_units(delta_time: float) -> Dict[str, float]:
        """标准化时间单位，返回秒和毫秒两种格式"""
        return {
            'delta_ms': delta_time,
            'delta_seconds': TimeManager.delta_to_seconds(delta_time)
        }


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


@dataclass
class ManaParticle(Projectile):
    """魔力粒子类，继承自Projectile"""
    # 魔力粒子特有属性
    angle: float = 0.0
    radius: float = 0.0
    alpha: int = 255
    angular_speed: float = 0.0
    radius_speed: float = 0.0
    fade_factor: float = 1.0
    center_x: float = 0.0
    center_y: float = 0.0
    created_time: float = 0.0  # 粒子创建时间（秒）

    def __post_init__(self):
        """初始化后处理"""
        # 调用父类初始化
        super().__post_init__()
        # 魔力粒子不需要目标，设置为自己
        self.target_x = self.x
        self.target_y = self.y
        # 设置魔力粒子类型
        self.projectile_type = "mana_particle"
        # 设置伤害为0（魔力粒子不造成伤害）
        self.damage = 0

    def update(self, delta_time: float, center_x: float = 0, center_y: float = 0):
        """更新魔力粒子状态"""
        if self.finished:
            return

        # 使用时间管理器统一处理时间单位
        time_units = TimeManager.normalize_time_units(delta_time)
        delta_seconds = time_units['delta_seconds']
        delta_ms = time_units['delta_ms']

        # 更新中心位置
        self.center_x = center_x
        self.center_y = center_y

        # 更新角度和半径（使用秒单位）
        self.angle += self.angular_speed * delta_seconds
        self.radius += self.radius_speed * delta_seconds

        # 计算位置（围绕中心旋转）
        self.x = center_x + math.cos(self.angle) * self.radius
        self.y = center_y + math.sin(self.angle) * self.radius

        # 更新生命值（使用毫秒单位，保持与创建时一致）
        self.life -= delta_ms
        if self.life <= 0:
            # 记录魔力粒子真实消失时间
            current_time = time.time()
            actual_lifetime = current_time - self.created_time
            expected_lifetime = self.max_life / 1000.0  # 转换为秒
            game_logger.info(
                f"魔力粒子消失 - 位置({self.x:.1f}, {self.y:.1f}), 颜色{self.color}, 预期生命周期: {expected_lifetime:.3f}s, 实际生命周期: {actual_lifetime:.3f}s, 差异: {abs(actual_lifetime - expected_lifetime):.3f}s")
            self.finished = True
            return

        # 更新透明度（渐变效果）
        life_ratio = self.life / self.max_life
        self.alpha = int(255 * life_ratio * self.fade_factor)

    def render(self, screen: pygame.Surface, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0, glow_config=None):
        """渲染魔力粒子"""
        if self.finished:
            return

        # 计算屏幕坐标（考虑相机偏移和UI缩放）
        screen_x = int((self.x - camera_x) * ui_scale)
        screen_y = int((self.y - camera_y) * ui_scale)

        # 绘制粒子
        particle_size = max(1, int(1 * ui_scale))
        pygame.draw.circle(screen, self.color,
                           (screen_x, screen_y), particle_size)

        # 添加发光效果
        if self.alpha > 50 and glow_config:  # 只在粒子足够可见且有发光配置时添加发光效果
            glow_manager = get_glow_manager()
            # 发光效果需要原始的世界坐标大小，发光系统会自己处理UI缩放
            base_particle_size = 1  # 原始粒子大小，不包含UI缩放
            glow_manager.render_effect_glow(
                screen, 'magic', (self.x, self.y), self.color,
                ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y,
                radius=base_particle_size
            )


@dataclass
class RegularParticle:
    """普通粒子类（重命名原来的Particle）"""
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
    created_time: float = 0.0  # 粒子创建时间（秒）

    def update(self, delta_time: float):
        """更新粒子状态"""
        # 使用时间管理器统一处理时间单位
        time_units = TimeManager.normalize_time_units(delta_time)
        delta_seconds = time_units['delta_seconds']
        delta_ms = time_units['delta_ms']

        # 更新位置（使用毫秒单位，因为速度是像素/毫秒）
        self.x += self.vx * delta_ms
        self.y += self.vy * delta_ms
        self.vy += self.gravity * delta_ms

        # 更新生命值（使用毫秒单位，保持与创建时一致）
        self.life -= delta_ms

        if self.life <= 0:
            # 记录粒子真实消失时间
            current_time = time.time()
            actual_lifetime = current_time - self.created_time
            expected_lifetime = self.max_life / 1000.0  # 转换为秒
            game_logger.info(
                f"粒子消失 - 位置({self.x:.1f}, {self.y:.1f}), 颜色{self.color}, 预期生命周期: {expected_lifetime:.3f}s, 实际生命周期: {actual_lifetime:.3f}s, 差异: {abs(actual_lifetime - expected_lifetime):.3f}s")
            self.finished = True

    def render(self, screen: pygame.Surface, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """渲染粒子"""
        if self.finished:
            return

        alpha = 255
        if self.fade:
            alpha = int(255 * (self.life / self.max_life))

        # 创建带透明度的颜色
        color_with_alpha = (*self.color, alpha)

        # 世界坐标转屏幕坐标并应用UI缩放
        scaled_x = int((self.x - camera_x) * ui_scale)
        scaled_y = int((self.y - camera_y) * ui_scale)
        scaled_size = max(1, int(self.size * ui_scale))

        # 绘制粒子
        pygame.draw.circle(screen, self.color,
                           (scaled_x, scaled_y), scaled_size)

    def reset(self):
        """重置粒子状态"""
        self.finished = False
        self.life = self.max_life


class ParticleSystem:
    """统一粒子系统管理器"""

    def __init__(self):
        self.particles: List[RegularParticle] = []
        self.particle_pool: List[RegularParticle] = []
        self.mana_particles: List[ManaParticle] = []
        self.mana_particle_pool: List[ManaParticle] = []

        # 获取发光效果管理器
        self.glow_manager = get_glow_manager()

        # 创建魔力粒子专用的发光配置
        self.inner_glow_config = self.glow_manager.create_custom_config(
            intensity=1.2,           # 内层粒子发光强度
            size_multiplier=1.5,     # 发光大小倍数
            color_boost=(40, 0, 40),  # 紫色增强
            alpha=150,               # 透明度
            layers=2                 # 发光层数
        )

        self.outer_glow_config = self.glow_manager.create_custom_config(
            intensity=0.8,           # 外层粒子发光强度
            size_multiplier=1.3,     # 发光大小倍数
            color_boost=(0, 0, 30),  # 蓝色增强
            alpha=100,               # 透明度
            layers=1                 # 发光层数
        )

    def create_particle(self, x: float, y: float, vx: float, vy: float,
                        color: Tuple[int, int, int], size: float,
                        life: float, gravity: float = 0.0, fade: bool = True) -> RegularParticle:
        """创建普通粒子"""
        current_time = time.time()

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
            particle.created_time = current_time
            particle.reset()
        else:
            particle = RegularParticle(x, y, vx, vy, color, size,
                                       life, life, gravity, fade, False, current_time)

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

    def create_splash_particles(self, x: float, y: float, color: tuple = (255, 255, 255), count: int = 8):
        """创建溅射粒子 - 用于攻击命中效果

        Args:
            x: 粒子生成X坐标
            y: 粒子生成Y坐标  
            color: 粒子颜色 (R, G, B)
            count: 粒子数量
        """
        for _ in range(count):
            # 随机方向，向外溅射
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 120)  # 溅射速度
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            # 可配置颜色的粒子，小尺寸，短生命周期
            size = random.uniform(1, 3)
            life = random.uniform(300, 600)  # 0.3-0.6秒生命周期

            # 创建指定颜色的粒子
            self.create_particle(x, y, vx, vy, color, size,
                                 life, gravity=0.0, fade=True)

    def create_mana_particle(self, center_x: float, center_y: float, max_range: float = 100.0) -> ManaParticle:
        """创建魔力粒子"""
        current_time = time.time()  # 记录创建时间
        # 随机选择内层（紫色）或外层（深蓝色）
        is_inner = random.random() < 0.6  # 60%概率为内层粒子

        if is_inner:
            # 内层粒子：紫色居多，顺时针旋转
            radius = random.uniform(10, 20)  # 缩小内层半径
            color = (200, 0, 200)  # 更亮的紫色
            life_seconds = random.uniform(3.0, 6.0)  # 3-6秒生命周期，延长粒子存在时间
            life = TimeManager.seconds_to_delta(life_seconds)  # 转换为毫秒
            fade_factor = random.uniform(0.8, 1.0)  # 更高透明度
        else:
            # 外层粒子：深蓝色居多，逆时针旋转
            radius = random.uniform(25, max_range * 0.6)  # 外层半径，限制在最大范围内
            color = (0, 100, 200)  # 更亮的蓝色
            life_seconds = random.uniform(3.0, 6.0)  # 3-6秒生命周期，延长粒子存在时间
            life = TimeManager.seconds_to_delta(life_seconds)  # 转换为毫秒
            fade_factor = random.uniform(0.6, 0.9)  # 更高透明度

        # 根据半径动态计算旋转速度：越靠近中心速度越快
        base_speed = random.uniform(0.4 * math.pi, math.pi)
        max_radius = max_range * 0.6
        speed_multiplier = max_radius / max(radius, 5)  # 最小半径为5，避免除零
        angular_speed = base_speed * speed_multiplier

        # 外层粒子使用逆时针旋转
        if not is_inner:
            angular_speed = -angular_speed

        # 随机角度
        angle = random.uniform(0, 2 * math.pi)

        # 计算初始位置
        x = center_x + math.cos(angle) * radius
        y = center_y + math.sin(angle) * radius

        # 尝试从对象池获取粒子
        if self.mana_particle_pool:
            particle = self.mana_particle_pool.pop()
            # 设置Projectile基类属性
            particle.x = x
            particle.y = y
            particle.target_x = x  # 魔力粒子不需要目标
            particle.target_y = y
            particle.speed = 0  # 魔力粒子不移动
            particle.damage = 0  # 魔力粒子不造成伤害
            particle.color = color
            particle.size = 1.0
            particle.projectile_type = "mana_particle"
            particle.life = life
            particle.max_life = life
            particle.finished = False
            # 设置魔力粒子特有属性
            particle.angle = angle
            particle.radius = radius
            particle.alpha = int(255 * fade_factor)
            particle.angular_speed = angular_speed
            particle.radius_speed = random.uniform(-0.5, 0.5)
            particle.fade_factor = fade_factor
            particle.center_x = center_x
            particle.center_y = center_y
            particle.created_time = current_time
        else:
            particle = ManaParticle(
                # Projectile基类属性
                x=x,
                y=y,
                target_x=x,  # 魔力粒子不需要目标
                target_y=y,
                speed=0,  # 魔力粒子不移动
                damage=0,  # 魔力粒子不造成伤害
                color=color,
                size=1.0,
                projectile_type="mana_particle",
                life=life,
                max_life=life,
                # 魔力粒子特有属性
                angle=angle,
                radius=radius,
                alpha=int(255 * fade_factor),
                angular_speed=angular_speed,
                radius_speed=random.uniform(-0.5, 0.5),
                fade_factor=fade_factor,
                center_x=center_x,
                center_y=center_y,
                created_time=current_time
            )

        self.mana_particles.append(particle)
        return particle

    def update(self, delta_time: float, center_x: float = 0, center_y: float = 0):
        """更新所有粒子"""

        # 添加粒子系统更新日志（每10次更新输出一次，减少日志频率）
        if not hasattr(self, '_update_counter'):
            self._update_counter = 0
        self._update_counter += 1

        if self._update_counter % 10 == 0:  # 每10次更新输出一次
            total_particles = len(self.particles) + len(self.mana_particles)
            game_logger.info(
                f"粒子系统更新 - 当前粒子数量: {total_particles}, delta_time: {delta_time:.3f}ms")

        # 更新普通粒子
        for particle in self.particles[:]:
            particle.update(delta_time)
            if particle.finished:
                self.particles.remove(particle)
                # 将粒子返回对象池
                if len(self.particle_pool) < 100:  # 限制对象池大小
                    self.particle_pool.append(particle)

        # 更新魔力粒子
        for particle in self.mana_particles[:]:
            particle.update(delta_time, center_x, center_y)
            if particle.finished:
                self.mana_particles.remove(particle)
                # 将粒子返回对象池
                if len(self.mana_particle_pool) < 100:  # 限制对象池大小
                    self.mana_particle_pool.append(particle)

    def render(self, screen: pygame.Surface, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """渲染所有粒子"""
        # 渲染普通粒子
        for particle in self.particles:
            particle.render(screen, ui_scale, camera_x, camera_y)

        # 渲染魔力粒子
        for particle in self.mana_particles:
            # 根据粒子颜色选择发光配置
            if particle.color[0] > 100:  # 紫色粒子（内层）
                glow_config = self.inner_glow_config
            else:  # 蓝色粒子（外层）
                glow_config = self.outer_glow_config

            particle.render(screen, ui_scale, camera_x, camera_y, glow_config)

    def clear(self):
        """清空所有粒子"""
        self.particles.clear()
        self.particle_pool.clear()
        self.mana_particles.clear()
        self.mana_particle_pool.clear()

    def clear_mana_particles(self):
        """清空魔力粒子"""
        # 将粒子回收到对象池
        for particle in self.mana_particles:
            if len(self.mana_particle_pool) < 100:
                self.mana_particle_pool.append(particle)
        self.mana_particles.clear()

    def get_mana_particle_count(self) -> int:
        """获取当前魔力粒子数量"""
        return len(self.mana_particles)

    def is_mana_active(self) -> bool:
        """检查是否有活跃的魔力粒子"""
        return len(self.mana_particles) > 0
