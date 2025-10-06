#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特效管理器模块
"""

import math
import random
import time
import pygame
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from .particle_system import ParticleSystem
from .projectile_system import ProjectileSystem
from .area_effect_system import AreaEffectSystem
from .blade_trail_effect import WhirlwindSlashEffect
from src.utils.logger import game_logger
from .effect_pool import EffectPool
from .effect_renderer import EffectRenderer
from .glow_effect import get_glow_manager


@dataclass
class VisualEffect:
    """可视化特效数据类"""
    effect_type: str
    x: float
    y: float
    target_x: float = None
    target_y: float = None
    damage: int = 0
    start_time: float = 0
    duration: float = 1.0
    color: Tuple[int, int, int] = (255, 255, 255)
    size: int = 5
    range: float = None  # 特效范围参数


class EffectManager:
    """特效管理器 - 统一管理所有攻击特效"""

    def __init__(self, speed_multiplier: float = 1.0):
        # 核心系统
        self.particle_system = ParticleSystem()
        self.projectile_system = ProjectileSystem()
        self.area_effect_system = AreaEffectSystem()
        self.whirlwind_effect_manager = WhirlwindSlashEffect()
        self.renderer_manager = EffectRenderer()
        self.effect_pool = EffectPool()

        # 可视化特效系统 - 整合自VisualEffectManager
        self.visual_effects: List[VisualEffect] = []
        self.speed_multiplier = speed_multiplier
        self.font = None

        # 特效配置 - 缓存配置避免重复加载
        self.visual_effect_configs = self._load_visual_effect_configs()

        # 性能设置 - 大幅降低限制以避免卡死
        self.max_particles = 50  # 从500降低到50
        self.max_projectiles = 10  # 从100降低到10
        self.max_area_effects = 5  # 从50降低到5
        self.performance_mode = "low"  # 改为low模式

        # 特效冷却机制
        self.effect_cooldowns = {}  # 存储特效冷却时间
        self.effect_cooldown_time = 100  # 100毫秒冷却时间

    def _create_particle_effect(self, effect_type: str, x: float, y: float,
                                config: Dict, damage: int, **kwargs) -> bool:
        """创建粒子特效"""
        particles_config = config.get("particles", {})

        # 根据特效类型创建不同粒子效果
        if effect_type == "melee_slash":
            self.particle_system.create_spark_effect(x, y, particles_config.get("sparks", 8),
                                                     particles_config.get("color", (255, 215, 0)))
        elif effect_type == "melee_heavy":
            self.particle_system.create_spark_effect(x, y, particles_config.get("sparks", 15),
                                                     particles_config.get("color", (255, 69, 0)))
            # 添加碎片效果
            self.particle_system.create_particle_burst(x, y, particles_config.get("debris", 6),
                                                       (139, 69, 19), (3, 6), (60, 120), 500, 0.8)
        elif effect_type == "shadow_slash":
            self.particle_system.create_particle_burst(x, y, particles_config.get("shadow_orbs", 5),
                                                       particles_config.get(
                                                           "color", (74, 74, 74)),
                                                       (2, 4), (30, 60), 400, -0.5)
        elif effect_type == "divine_strike":
            self.particle_system.create_particle_burst(x, y, particles_config.get("light_orbs", 12),
                                                       particles_config.get(
                                                           "color", (255, 215, 0)),
                                                       (3, 6), (40, 80), 600, 0.2)

        # 触发屏幕震动（如果支持）
        screen_shake = config.get("screen_shake")
        if screen_shake and hasattr(self.renderer_manager, 'trigger_screen_shake'):
            self.renderer_manager.trigger_screen_shake(
                screen_shake["intensity"], screen_shake["duration"]
            )

        # 伤害数字现在显示在目标位置，不在特效创建位置显示
        return True

    def _create_area_effect(self, effect_type: str, x: float, y: float,
                            config: Dict, damage: int, **kwargs) -> bool:
        """创建区域特效"""
        area_type = config["area_type"]

        if area_type == "fire":
            if effect_type == "fire_breath":
                effect = self.area_effect_system.create_fire_area(x, y, config["radius"],
                                                                  config["duration"], config["damage_per_second"])
            elif effect_type == "fire_splash":
                effect = self.area_effect_system.create_fire_area(x, y, config["radius"],
                                                                  config["duration"], config["damage_per_second"])

        elif area_type == "explosion":
            if effect_type == "spine_storm":
                effect = self.area_effect_system.create_explosion(
                    x, y, config["radius"], config["duration"])
                effect.damage_per_second = config["damage_per_second"]

        elif area_type == "vine":
            if effect_type == "vine_entangle":
                # 使用酸液池作为藤蔓缠绕的基础效果
                effect = self.area_effect_system.create_acid_pool(
                    x, y, config["radius"], config["duration"], config["damage_per_second"])
                effect.effect_type = "vine"

        elif area_type == "healing":
            if effect_type == "healing_aura":
                effect = self.area_effect_system.create_healing_aura(
                    x, y, config["radius"], config["duration"])
                effect.effect_type = "healing"

        # 触发屏幕震动（如果支持）
        screen_shake = config.get("screen_shake")
        if screen_shake and hasattr(self.renderer_manager, 'trigger_screen_shake'):
            self.renderer_manager.trigger_screen_shake(
                screen_shake["intensity"], screen_shake["duration"]
            )

        return True

    def update(self, delta_time: float, targets: List = None, camera_x: float = 0, camera_y: float = 0):
        """更新所有特效系统"""
        # 性能检查 - 如果特效数量过多，跳过某些更新
        stats = self.get_performance_stats()
        if stats['particles'] > self.max_particles:
            # 如果粒子过多，降低更新频率
            if hasattr(self, '_update_counter'):
                self._update_counter += 1
                if self._update_counter % 2 != 0:  # 每两帧更新一次
                    return
            else:
                self._update_counter = 0

        # 更新各系统
        self.particle_system.update(delta_time)
        self.projectile_system.update(delta_time, targets)
        self.area_effect_system.update(delta_time)
        self.whirlwind_effect_manager.update_all(delta_time)

        # 更新可视化特效
        self.update_visual_effects(delta_time, targets)

        if hasattr(self.renderer_manager, 'update'):
            self.renderer_manager.update(delta_time)

        # 检查碰撞
        if targets:
            self._check_projectile_collisions(targets, camera_x, camera_y)
            self._check_area_damage(targets, camera_x, camera_y)

        # 清理过期的冷却记录
        self._cleanup_effect_cooldowns()

    def _check_projectile_collisions(self, targets: List, camera_x: float = 0, camera_y: float = 0):
        """检查投射物碰撞"""
        collisions = self.projectile_system.check_collisions(targets)
        for projectile, target in collisions:
            # 造成伤害
            target._take_damage(projectile.damage)

            # 伤害数字显示已移除

            # 命中特效已移除

            # 如果是火球，创建爆炸效果
            if projectile.projectile_type == "fireball" and hasattr(projectile, 'explosion_radius'):
                self.area_effect_system.create_explosion(
                    target.x, target.y, projectile.explosion_radius, 1500)

            game_logger.info(
                f"🎯 {projectile.projectile_type} 命中 {target.type}，造成 {projectile.damage} 点伤害")

    def _check_area_damage(self, targets: List, camera_x: float = 0, camera_y: float = 0):
        """检查区域伤害"""
        damage_events = self.area_effect_system.check_damage(targets)
        for effect, target in damage_events:
            target._take_damage(effect.damage_per_second)
            # 伤害数字显示已移除

    def render(self, screen, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """渲染所有特效"""
        if screen is None:
            game_logger.info("❌ EffectManager.render() 收到 None screen，跳过渲染")
            return screen

        # 渲染各系统，传递UI放大倍数和相机参数
        self.particle_system.render(screen, ui_scale, camera_x, camera_y)
        self.projectile_system.render(screen, ui_scale, camera_x, camera_y)
        self.area_effect_system.render(screen, ui_scale, camera_x, camera_y)
        self.whirlwind_effect_manager.render_all(
            screen, ui_scale, camera_x, camera_y)

        # 渲染可视化特效
        self.render_visual_effects(screen, ui_scale, camera_x, camera_y)

        # 渲染管理器处理屏幕震动和伤害数字
        result = self.renderer_manager.render_all(screen, ui_scale)

        # 确保返回有效的Surface
        if result is None:
            game_logger.info(
                "❌ EffectRendererManager.render_all() 返回 None，返回原始screen")
            return screen

        return result

    def clear_all(self):
        """清空所有特效"""
        self.particle_system.clear()
        self.projectile_system.clear()
        self.area_effect_system.clear()
        self.whirlwind_effect_manager.clear_all()
        self.renderer_manager.clear_all()

    def set_performance_mode(self, mode: str):
        """设置性能模式"""
        self.performance_mode = mode
        if mode == "low":
            self.max_particles = 200
            self.max_projectiles = 50
            self.max_area_effects = 25
        elif mode == "medium":
            self.max_particles = 350
            self.max_projectiles = 75
            self.max_area_effects = 35
        else:  # high
            self.max_particles = 500
            self.max_projectiles = 100
            self.max_area_effects = 50

    def get_performance_stats(self) -> Dict[str, int]:
        """获取性能统计"""
        stats = {
            "particles": len(self.particle_system.particles),
            "projectiles": len(self.projectile_system.projectiles),
            "area_effects": len(self.area_effect_system.effects)
        }

        # 安全地获取伤害数字统计
        if hasattr(self.renderer_manager, 'damage_renderer') and hasattr(self.renderer_manager.damage_renderer, 'damage_numbers'):
            stats["damage_numbers"] = len(
                self.renderer_manager.damage_renderer.damage_numbers)
        else:
            stats["damage_numbers"] = 0

        return stats

    def _cleanup_effect_cooldowns(self):
        """清理过期的特效冷却记录"""
        import time
        current_time = time.time() * 1000

        # 清理5秒前的冷却记录
        expired_keys = []
        for key, timestamp in self.effect_cooldowns.items():
            if current_time - timestamp > 5000:  # 5秒
                expired_keys.append(key)

        for key in expired_keys:
            del self.effect_cooldowns[key]

    # ==================== 可视化特效系统方法 - 整合自VisualEffectManager ====================

    def create_visual_effect(self, effect_type: str, x: float, y: float,
                             target_x: float = None, target_y: float = None,
                             damage: int = 0, attacker_name: str = None, **kwargs) -> VisualEffect:
        """创建可视化特效"""
        # 输出攻击特效日志（单行格式）
        if attacker_name and damage > 0:
            game_logger.info(
                f"🎆 {attacker_name} 攻击特效 {effect_type} 位置({x:.1f},{y:.1f}) 伤害{damage}")
        elif attacker_name:
            game_logger.info(
                f"🎆 {attacker_name} 特效 {effect_type} 位置({x:.1f},{y:.1f})")

        # 根据特效类型获取配置
        config = self.visual_effect_configs.get(effect_type, {})
        if not config:
            game_logger.info(f"⚠️ 未找到特效配置: {effect_type}")
            return None

        # 创建普通可视化特效
        color, base_duration, effect_speed_multiplier = self._get_visual_effect_properties(
            effect_type)

        # 应用速度倍数 - 使用配置中的速度倍数
        total_speed_multiplier = self.speed_multiplier * effect_speed_multiplier
        duration = base_duration / total_speed_multiplier

        # 创建特效对象
        effect = VisualEffect(
            effect_type=effect_type,
            x=x,
            y=y,
            target_x=target_x,
            target_y=target_y,
            damage=damage,
            start_time=time.time(),
            duration=duration,
            color=color,
            size=self._get_visual_effect_size(effect_type),
            range=kwargs.get('range', None)  # 传递范围参数
        )

        self.visual_effects.append(effect)
        return effect

    def set_speed_multiplier(self, multiplier: float):
        """设置特效播放速度倍数"""
        self.speed_multiplier = max(0.1, multiplier)  # 限制最小速度为0.1倍
        game_logger.info(f"⚡ 特效播放速度设置为: {self.speed_multiplier}x")

    def get_speed_multiplier(self) -> float:
        """获取当前特效播放速度倍数"""
        return self.speed_multiplier

    def _load_visual_effect_configs(self) -> Dict[str, Dict[str, Any]]:
        """加载可视化特效配置，包含颜色、持续时间和速度倍数，按8大类分类"""
        return {
            # ==================== 1. 斩击类 - 半月形圆弧 ====================
            'melee_slash': {
                'type': 'slash',             # 斩击类
                'color': (255, 255, 255),    # 白色半圆弧
                'duration': 0.6,            # 基础持续时间0.6秒
                'speed_multiplier': 1.0,     # 斩击类特效正常速度
                'size': 5,
                'range': 5                  # 斩击范围5像素
            },
            'melee_heavy': {
                'type': 'slash',             # 斩击类
                'color': (255, 0, 0),        # 红色粗重半圆弧
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 斩击类特效正常速度
                'size': 8,
                'range': 10                  # 重击范围10像素
            },
            'shadow_slash': {
                'type': 'slash',             # 斩击类
                'color': (100, 0, 255),      # 紫色暗影
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 斩击类特效正常速度
                'size': 5,
                'range': 8                  # 暗影斩击范围8像素
            },
            'divine_strike': {
                'type': 'slash',             # 斩击类
                'color': (255, 215, 0),      # 金色明亮弧线
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 斩击类特效正常速度
                'size': 6,
                'range': 8                  # 神圣斩击范围8像素
            },
            'whirlwind_slash': {
                'type': 'slash',             # 斩击类
                'color': (255, 255, 255),    # 白色刀光
                'duration': 1.2,             # 基础持续时间1.2秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 12,                  # 刀光大小
                'range': 80                  # 旋风范围80像素
            },

            # ==================== 2. 射击类 - 适当长度的短线条 ====================
            'arrow_shot': {
                'type': 'projectile',        # 射击类
                'projectile_type': 'arrow',  # 箭矢类型
                'color': (255, 255, 255),    # 白色箭矢
                'duration': 0.3,             # 基础持续时间0.3秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5,
                'range': 80,                 # 箭矢射程80像素
                'speed': 400                 # 箭矢速度400像素/秒
            },
            'precise_arrow': {
                'type': 'projectile',        # 射击类
                'projectile_type': 'arrow',  # 箭矢类型
                'color': (255, 255, 0),      # 黄色精准
                'duration': 0.4,             # 基础持续时间0.4秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5,
                'range': 100,                # 精准箭矢射程100像素
                'speed': 400                 # 箭矢速度400像素/秒
            },
            'tracking_arrow': {
                'type': 'projectile',        # 射击类
                'projectile_type': 'arrow',  # 箭矢类型
                'color': (0, 255, 0),        # 绿色追踪
                'duration': 0.5,             # 基础持续时间0.5秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5,
                'range': 120,                # 追踪箭矢射程120像素
                'speed': 400                 # 箭矢速度400像素/秒
            },
            'nature_arrow': {
                'type': 'projectile',        # 射击类
                'projectile_type': 'arrow',  # 箭矢类型
                'color': (100, 255, 100),    # 绿色自然
                'duration': 0.6,             # 基础持续时间0.6秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5,
                'range': 90,                 # 自然箭矢射程90像素
                'speed': 400                 # 箭矢速度400像素/秒
            },
            'tower_arrow_shot': {
                'type': 'projectile',        # 射击类
                'projectile_type': 'tower_arrow',  # 箭塔箭矢类型
                'color': (255, 255, 255),    # 白色箭矢
                'duration': 0.8,             # 箭矢飞行时间0.8秒（包含穿透效果）
                'speed_multiplier': 1.0,     # 基础速度倍数
                'size': 6,
                'range': 120,                # 保持射程120像素
                'speed': 400,                # 箭矢飞行速度400像素/秒
                'penetration': True,         # 启用穿透效果
                'penetration_distance': 20.0,  # 穿透距离20像素
                'splash_particles': True,    # 启用溅射粒子
                'splash_color': (255, 255, 255),  # 白色溅射粒子
                'splash_count': 8            # 溅射粒子数量
            },
            'tower_critical_arrow': {
                'type': 'projectile',        # 射击类
                'projectile_type': 'tower_arrow',  # 箭塔箭矢类型
                'color': (255, 215, 0),      # 金色暴击箭矢
                'duration': 0.25,            # 暴击箭矢飞行时间0.25秒（基于120像素距离和480像素/秒速度）
                'speed_multiplier': 1.0,     # 基础速度倍数
                'size': 8,
                'range': 120,                # 保持射程120像素
                'speed': 480                 # 暴击箭矢飞行速度480像素/秒
            },
            'tower_arrow_impact': {
                'type': 'projectile',        # 射击类
                'color': (255, 255, 255),    # 白色箭矢
                'duration': 0.4,             # 基础持续时间0.4秒
                'speed_multiplier': 1.2,     # 稍快速度
                'size': 4,
                'range': 120                 # 箭矢冲击射程120像素
            },

            # ==================== 3. 魔法类 - 直接作用于目标，圆形爆炸 ====================
            'fireball': {
                'type': 'magic',             # 魔法类
                'color': (255, 0, 0),        # 红色火球
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 6,
                'range': 30                  # 火球爆炸范围30像素
            },
            'magic_explosion': {
                'type': 'magic',             # 魔法类
                'color': (255, 0, 255),      # 紫色魔法爆炸
                'duration': 0.6,             # 基础持续时间0.6秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 8,
                'range': 30                  # 魔法爆炸范围30像素
            },
            'arcane_blast': {
                'type': 'magic',             # 魔法类
                'color': (0, 255, 255),      # 青色奥术
                'duration': 0.7,             # 基础持续时间0.7秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 10,
                'range': 40                  # 奥术爆炸范围40像素
            },
            'charm_effect': {
                'type': 'magic',             # 魔法类
                'color': (255, 0, 255),      # 紫色魅惑
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5,
                'range': 20                  # 魅惑效果范围20像素
            },
            'healing_aura': {
                'type': 'magic',             # 魔法类
                'color': (0, 255, 255),      # 青色治疗
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 20,
                'range': 40                  # 治疗光环范围40像素
            },
            'tower_magic_impact': {
                'type': 'magic',             # 魔法类
                'color': (25, 25, 112),      # 深蓝色魔法冲击
                'duration': 1.2,             # 基础持续时间1.2秒
                'speed_multiplier': 0.6,     # 正常速度
                'size': 4,
                'range': 30                  # 魔法冲击范围30像素
            },

            # ==================== 4. 火焰类 - 前方扇形区域，需要生成粒子特效 ====================
            'fire_breath': {
                'type': 'flame',             # 火焰类
                'color': (255, 50, 0),       # 橙红色火焰
                'duration': 1.2,             # 基础持续时间1.2秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 10,
                'range': 80                  # 火焰呼吸范围80像素
            },
            'fire_splash': {
                'type': 'flame',             # 火焰类
                'color': (255, 100, 0),      # 橙色溅射
                'duration': 0.6,             # 基础持续时间0.6秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5,
                'range': 40                  # 火焰溅射范围40像素
            },
            'flame_wave': {
                'type': 'flame',             # 火焰类
                'color': (220, 20, 20),      # 赤红色火焰波
                'duration': 1.6,             # 基础持续时间1.6秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 6,
                'range': 40                 # 火焰波浪范围40像素
            },
            'acid_spray': {
                'type': 'flame',             # 火焰类（扇形区域）
                'color': (0, 255, 0),        # 绿色酸液
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5,
                'range': 60                  # 酸液喷射范围60像素
            },

            # ==================== 5. 冲击类 - 以自身为中心扩展冲击波 ====================
            'spine_storm': {
                'type': 'impact',            # 冲击类
                'color': (150, 150, 150),    # 灰色骨刺
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 15,
                'range': 100                 # 骨刺风暴范围100像素
            },
            'shockwave': {
                'type': 'impact',            # 冲击类
                'color': (255, 255, 0),      # 黄色冲击波
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 20,
                'range': 80                  # 冲击波范围80像素
            },
            'earthquake': {
                'type': 'impact',            # 冲击类
                'color': (139, 69, 19),      # 棕色地震
                'duration': 1.5,             # 基础持续时间1.5秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 25,
                'range': 120                 # 地震范围120像素
            },

            # ==================== 6. 闪电类 - 连接目标与自身的一道类似电流的折线 ====================
            'chain_lightning': {
                'type': 'lightning',         # 闪电类
                'color': (0, 255, 255),      # 青色闪电
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 12,
                'range': 120                 # 连锁闪电范围120像素
            },
            'lightning_bolt': {
                'type': 'lightning',         # 闪电类
                'color': (255, 255, 255),    # 白色闪电
                'duration': 0.4,             # 基础持续时间0.4秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 8,
                'range': 100                 # 闪电范围100像素
            },
            'electric_chain': {
                'type': 'lightning',         # 闪电类
                'color': (255, 255, 0),      # 黄色电流
                'duration': 0.6,             # 基础持续时间0.6秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 6,
                'range': 80                  # 电流链范围80像素
            },

            # ==================== 7. 爪击类 - 使用3条直线爪痕来模拟爪击 ====================
            'claw_attack': {
                'type': 'claw',              # 爪击类
                'color': (255, 140, 0),      # 橙色爪击
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 6,
                'range': 5                   # 爪击范围5像素
            },
            'beast_claw': {
                'type': 'claw',              # 爪击类
                'color': (160, 82, 45),      # 棕色野兽爪
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 8,
                'range': 10                  # 野兽爪击范围10像素
            },
            'shadow_claw': {
                'type': 'claw',              # 爪击类
                'color': (75, 0, 130),       # 紫色暗影爪
                'duration': 0.8,            # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 7,
                'range': 8                   # 暗影爪击范围8像素
            },

            # ==================== 8. 缠绕类 - 直接作用于目标，缠绕样式的弧形线条 ====================
            'vine_entangle': {
                'type': 'entangle',          # 缠绕类
                'color': (0, 150, 0),        # 深绿藤蔓
                'duration': 1.5,             # 基础持续时间1.5秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 8,
                'range': 50                  # 藤蔓缠绕范围50像素
            },
            'thorn_whip': {
                'type': 'entangle',          # 缠绕类
                'color': (0, 100, 0),        # 深绿色荆棘
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 6,
                'range': 40                  # 荆棘鞭打范围40像素
            },
            'shadow_bind': {
                'type': 'entangle',          # 缠绕类
                'color': (50, 0, 50),        # 深紫色暗影束缚
                'duration': 1.2,             # 基础持续时间1.2秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 10,
                'range': 60                  # 暗影束缚范围60像素
            }
        }

    def _get_visual_effect_properties(self, effect_type: str) -> Tuple[Tuple[int, int, int], float, float]:
        """根据特效类型获取颜色、持续时间和速度倍数"""
        config = self.visual_effect_configs.get(effect_type, {
            'type': 'magic',
            'color': (255, 255, 255),
            'duration': 1.0,
            'speed_multiplier': 1.0
        })
        return config['color'], config['duration'], config['speed_multiplier']

    def _get_visual_effect_size(self, effect_type: str) -> int:
        """根据特效类型获取大小"""
        config = self.visual_effect_configs.get(effect_type, {'size': 5})
        return config['size']

    def _get_visual_effect_range(self, effect_type: str) -> int:
        """根据特效类型获取范围"""
        config = self.visual_effect_configs.get(effect_type, {'range': 50})
        return config['range']

    def _get_visual_effect_type(self, effect_type: str) -> str:
        """根据特效类型获取特效分类"""
        config = self.visual_effect_configs.get(effect_type, {'type': 'magic'})
        return config['type']

    def _world_to_screen(self, world_x: float, world_y: float, camera_x: float, camera_y: float, ui_scale: float) -> Tuple[int, int]:
        """世界坐标转屏幕坐标"""
        return int((world_x - camera_x) * ui_scale), int((world_y - camera_y) * ui_scale)

    def update_visual_effects(self, delta_time: float, targets: List = None):
        """更新可视化特效"""
        current_time = time.time()

        # 移除过期的特效
        self.visual_effects = [
            effect for effect in self.visual_effects
            if current_time - effect.start_time < effect.duration
        ]

    def render_visual_effects(self, screen: pygame.Surface, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """渲染可视化特效"""
        current_time = time.time()

        for effect in self.visual_effects:
            # 计算特效的生命周期进度 (0.0 到 1.0)
            elapsed = current_time - effect.start_time
            progress = min(elapsed / effect.duration, 1.0)

            # 根据进度计算透明度
            alpha = int(255 * (1.0 - progress))

            # 根据特效类型渲染不同的效果
            self._render_visual_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        return screen

    def _render_visual_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """渲染单个可视化特效 - 按8大类分类渲染"""
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)
        effect_class = self._get_visual_effect_type(effect.effect_type)

        # 根据特效分类进行渲染
        if effect_class == 'slash':
            # 1. 斩击类 - 半月形圆弧
            self._render_slash_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        elif effect_class == 'projectile':
            # 2. 射击类 - 适当长度的短线条
            self._render_projectile_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        elif effect_class == 'magic':
            # 3. 魔法类 - 直接作用于目标，圆形爆炸
            self._render_magic_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        elif effect_class == 'flame':
            # 4. 火焰类 - 前方扇形区域，需要生成粒子特效
            self._render_flame_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        elif effect_class == 'impact':
            # 5. 冲击类 - 以自身为中心扩展冲击波
            self._render_impact_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        elif effect_class == 'lightning':
            # 6. 闪电类 - 连接目标与自身的一道类似电流的折线
            self._render_lightning_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        elif effect_class == 'claw':
            # 7. 爪击类 - 使用3条细曲线来模拟爪击
            self._render_claw_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        elif effect_class == 'entangle':
            # 8. 缠绕类 - 直接作用于目标，缠绕样式的弧形线条
            self._render_entangle_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

        else:
            # 默认效果：简单圆圈
            size = int(effect.size * (1.0 + progress) * ui_scale)
            pygame.draw.circle(screen, effect.color, (x, y), size)

    def _render_slash_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """1. 斩击类 - 渲染半月形圆弧斩击效果"""
        # 特殊处理旋风斩 - 使用刀刃拖痕特效系统
        if effect.effect_type == "whirlwind_slash":
            self._render_whirlwind_slash_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)
            return

        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 计算斩击角度和方向
        if effect.target_x is not None and effect.target_y is not None:
            # 如果有目标，朝目标方向斩击
            target_x, target_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)
            angle = math.atan2(target_y - y, target_x - x)
        else:
            # 如果没有目标，默认向右下方斩击
            angle = math.pi / 4

        # 使用特效配置中的范围参数
        effect_range = self._get_visual_effect_range(effect.effect_type)
        radius = int(effect_range * (1.0 + progress * 2) * ui_scale)
        angle_range = math.pi  # 180度范围，形成半月形圆弧

        # 绘制斩击弧线
        start_angle = angle - angle_range / 2
        end_angle = angle + angle_range / 2

        # 使用更多线段模拟更平滑的弧线
        segments = 16  # 增加段数使弧线更平滑
        for i in range(segments):
            t = i / (segments - 1)
            current_angle = start_angle + t * angle_range
            next_angle = start_angle + (i + 1) / (segments - 1) * angle_range

            # 计算当前点和下一个点
            x1 = x + math.cos(current_angle) * radius
            y1 = y + math.sin(current_angle) * radius
            x2 = x + math.cos(next_angle) * radius
            y2 = y + math.sin(next_angle) * radius

            # 绘制线段，使用半透明效果
            line_width = max(1, int(3 * ui_scale))
            # 创建半透明颜色
            color_with_alpha = (*effect.color, alpha)
            pygame.draw.line(screen, effect.color, (int(
                x1), int(y1)), (int(x2), int(y2)), line_width)

    def _render_tower_arrow_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """
        箭塔箭矢特效渲染 - 统一的箭塔攻击视觉效果

        渲染逻辑：
        - 根据箭矢类型（普通/暴击）选择不同的视觉效果
        - 绘制箭矢飞行轨迹
        - 添加粒子特效和发光效果
        - 支持UI缩放和相机移动
        """
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        if effect.target_x is not None and effect.target_y is not None:
            target_x, target_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)

            # 计算方向
            dx = target_x - x
            dy = target_y - y
            distance = math.sqrt(dx*dx + dy*dy)

            if distance > 0:
                # 归一化方向
                dx /= distance
                dy /= distance

                # 获取箭矢配置
                config = self.visual_effect_configs.get(effect.effect_type, {})
                speed = config.get('speed', 400)  # 默认400像素/秒

                # 根据实际距离和速度计算飞行时间
                actual_duration = distance / speed  # 实际飞行时间（秒）

                # 使用实际飞行时间计算进度
                effect_duration = effect.duration  # 配置的duration
                actual_progress = min(
                    progress * (effect_duration / actual_duration), 1.0)

                # 计算当前进度下的位置
                current_distance = distance * actual_progress
                current_x = x + dx * current_distance
                current_y = y + dy * current_distance

                # 根据箭矢类型选择颜色和样式
                is_critical = effect.effect_type == 'tower_critical_arrow'
                if is_critical:
                    # 暴击箭矢：金色，更粗的线条
                    arrow_color = (255, 215, 0)  # 金色
                    line_width = max(2, int(4 * ui_scale))
                else:
                    # 普通箭矢：白色，标准线条
                    arrow_color = (255, 255, 255)  # 白色
                    line_width = max(1, int(3 * ui_scale))

                # 计算穿透效果
                penetration_distance = 40.0 * ui_scale  # 40像素穿透距离，考虑UI缩放

                # 如果箭矢已经到达目标位置，继续向前穿透
                if actual_progress >= 1.0:
                    # 箭矢已经到达目标，继续向前穿透40px
                    penetration_end_x = target_x + dx * penetration_distance
                    penetration_end_y = target_y + dy * penetration_distance

                    # 绘制从起点到穿透终点的完整箭矢
                    pygame.draw.line(screen, arrow_color, (x, y),
                                     (int(penetration_end_x), int(penetration_end_y)), line_width)

                    # 在穿透终点创建溅射粒子
                    self._create_arrow_impact_particles(
                        penetration_end_x, penetration_end_y, x, y, is_critical, ui_scale)
                else:
                    # 箭矢还在飞行中，绘制到当前位置
                    pygame.draw.line(screen, arrow_color, (x, y),
                                     (int(current_x), int(current_y)), line_width)

                # 添加箭矢头部（三角形）
                if actual_progress > 0.1:  # 箭矢飞行10%后显示头部
                    head_size = max(3, int(6 * ui_scale))
                    head_angle = math.atan2(dy, dx)

                    # 计算箭头位置 - 根据是否穿透来决定头部位置
                    if actual_progress >= 1.0:
                        # 穿透状态：头部在穿透终点
                        head_x = int(target_x + dx * penetration_distance)
                        head_y = int(target_y + dy * penetration_distance)
                    else:
                        # 飞行状态：头部在当前进度位置
                        head_x = int(current_x)
                        head_y = int(current_y)

                    # 箭头左侧点
                    left_angle = head_angle + math.pi * 0.8
                    left_x = head_x + int(math.cos(left_angle) * head_size)
                    left_y = head_y + int(math.sin(left_angle) * head_size)

                    # 箭头右侧点
                    right_angle = head_angle - math.pi * 0.8
                    right_x = head_x + int(math.cos(right_angle) * head_size)
                    right_y = head_y + int(math.sin(right_angle) * head_size)

                    # 绘制箭头三角形
                    pygame.draw.polygon(screen, arrow_color,
                                        [(head_x, head_y), (left_x, left_y), (right_x, right_y)])

                # 添加发光效果
                if is_critical:
                    glow_manager = get_glow_manager()
                    # 将屏幕坐标转换回世界坐标，因为glow_manager期望世界坐标
                    world_start_x = effect.x
                    world_start_y = effect.y

                    # 发光效果的穿透距离设置为30px（世界坐标）
                    glow_penetration_distance = 30.0

                    if actual_progress >= 1.0:
                        # 穿透状态：发光到穿透终点（世界坐标）
                        world_end_x = effect.target_x + dx * glow_penetration_distance
                        world_end_y = effect.target_y + dy * glow_penetration_distance
                    else:
                        # 飞行状态：发光到当前位置（世界坐标）
                        world_end_x = effect.x + dx * current_distance / ui_scale
                        world_end_y = effect.y + dy * current_distance / ui_scale

                    glow_manager.render_effect_glow(
                        screen, 'tower_critical_arrow', (
                            world_start_x, world_start_y), arrow_color,
                        end=(world_end_x, world_end_y), width=3, ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y
                    )

                # 粒子特效现在在穿透终点创建（见上面的代码）

    def _create_arrow_impact_particles(self, target_x: float, target_y: float,
                                       tower_x: float, tower_y: float,
                                       is_critical: bool, ui_scale: float = 1.0):
        """创建箭矢命中粒子特效 - 溅射效果"""
        # 将屏幕坐标转换回世界坐标
        world_target_x = target_x / ui_scale
        world_target_y = target_y / ui_scale

        game_logger.info(
            f"🎯 创建穿透终点溅射粒子 - 位置: ({world_target_x:.1f}, {world_target_y:.1f}), 类型: {'暴击' if is_critical else '普通'}")

        # 根据箭矢类型选择粒子颜色
        if is_critical:
            # 暴击箭矢：金色粒子
            particle_color = (255, 215, 0)  # 金色
            particle_count = 12  # 暴击粒子更多
        else:
            # 普通箭矢：白色粒子
            particle_color = (255, 255, 255)  # 白色
            particle_count = 8

        # 创建指定颜色的溅射粒子
        self.particle_system.create_splash_particles(
            world_target_x, world_target_y, color=particle_color, count=particle_count
        )

        # 暴击效果已通过新的粒子API实现，无需额外粒子

    def _render_projectile_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """
        2. 射击类 - 从自身开始发射到目标结束

        渲染逻辑：
        - 根据特效类型选择相应的渲染方法
        - 箭塔箭矢使用专门的渲染函数
        - 其他投射物使用通用渲染逻辑
        """
        # 检查是否为箭塔箭矢特效
        if effect.effect_type in ['tower_arrow_shot', 'tower_critical_arrow', 'tower_arrow_impact']:
            self._render_tower_arrow_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)
            return

        # 通用投射物渲染逻辑
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        if effect.target_x is not None and effect.target_y is not None:
            target_x, target_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)

            # 计算方向
            dx = target_x - x
            dy = target_y - y
            distance = math.sqrt(dx*dx + dy*dy)

            if distance > 0:
                # 归一化方向
                dx /= distance
                dy /= distance

                # 获取箭矢配置
                config = self.visual_effect_configs.get(effect.effect_type, {})
                speed = config.get('speed', 400)  # 默认400像素/秒

                # 根据实际距离和速度计算飞行时间
                actual_duration = distance / speed  # 实际飞行时间（秒）

                # 使用实际飞行时间计算进度，而不是固定的duration
                # progress是基于effect.duration计算的，需要转换为基于actual_duration的进度
                effect_duration = effect.duration  # 配置的duration
                actual_progress = min(
                    progress * (effect_duration / actual_duration), 1.0)

                # 计算当前进度下的位置（从自身开始，向目标移动）
                current_distance = distance * actual_progress
                current_x = x + dx * current_distance
                current_y = y + dy * current_distance

                # 绘制从自身到当前位置的线条
                line_width = max(1, int(3 * ui_scale))
                pygame.draw.line(screen, effect.color, (x, y),
                                 (int(current_x), int(current_y)), line_width)

                # 如果是暴击箭矢，添加发光效果
                if effect.effect_type == 'tower_critical_arrow':
                    glow_manager = get_glow_manager()
                    glow_manager.render_effect_glow(
                        screen, 'tower_critical_arrow', (x, y), effect.color,
                        end=(int(current_x), int(current_y)), width=3, ui_scale=ui_scale
                    )
            else:
                # 如果没有方向，绘制一个短线条
                effect_range = self._get_visual_effect_range(
                    effect.effect_type)
                line_length = effect_range * ui_scale
                line_width = max(1, int(3 * ui_scale))
                pygame.draw.line(screen, effect.color, (x, y),
                                 (x + line_length, y), line_width)

    def _render_magic_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """3. 魔法类 - 直接作用于目标，圆形爆炸"""
        # 处理 tower_magic_impact 的特殊逻辑
        if effect.effect_type == 'tower_magic_impact':
            self._render_particle_tower_magic(
                screen, effect, progress, ui_scale, camera_x, camera_y
            )
            return

        # 其他魔法类特效直接作用于目标位置
        if effect.target_x is not None and effect.target_y is not None:
            x, y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)
        else:
            x, y = self._world_to_screen(
                effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 其他魔法类特效的通用处理
        # 使用特效配置中的范围参数
        effect_range = self._get_visual_effect_range(effect.effect_type)
        size = int(effect_range * (1.0 + progress * 2))  # 爆炸会扩大，使用世界坐标大小

        # 将屏幕坐标转换回世界坐标用于发光API
        world_x = (x / ui_scale) + camera_x
        world_y = (y / ui_scale) + camera_y

        # 使用统一的发光API渲染圆形爆炸效果
        glow_manager = get_glow_manager()
        glow_manager.render_effect_glow(
            screen, effect.effect_type, (world_x, world_y), effect.color,
            radius=size, ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y
        )

        # 添加爆炸波纹效果
        if progress > 0.3:
            outer_size = int(size * 1.5)
            glow_manager.render_effect_glow(
                screen, effect.effect_type, (world_x,
                                             world_y), effect.color,
                radius=outer_size, ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y
            )

        # 添加内层爆炸效果
        if progress > 0.6:
            inner_size = int(size * 0.5)
            inner_color = (min(255, effect.color[0] + 50),
                           min(255, effect.color[1] + 50),
                           min(255, effect.color[2] + 50))
            glow_manager.render_effect_glow(
                screen, effect.effect_type, (world_x,
                                             world_y), inner_color,
                radius=inner_size, ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y
            )

    def _render_flame_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """
        4. 火焰类 - 根据特效类型渲染不同的火焰效果

        渲染逻辑：
        - acid_spray, flame_wave: 大范围圆形颜色渲染
        - fire_breath, fire_splash: 粒子效果渲染
        - 使用伪随机数确保同一帧内粒子位置一致
        - 支持多层火焰效果和颜色渐变
        """
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 根据特效类型选择不同的渲染方式
        if effect.effect_type in ['acid_spray', 'flame_wave']:
            # 大范围圆形颜色渲染
            self._render_circular_flame_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)
        elif effect.effect_type in ['fire_breath', 'fire_splash']:
            # 粒子效果
            self._render_particle_flame_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)
        else:
            # 默认粒子效果
            self._render_particle_flame_effect(
                screen, effect, progress, alpha, ui_scale, camera_x, camera_y)

    def _render_circular_flame_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """大范围圆形颜色渲染 - 用于 acid_spray 和 flame_wave"""
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 计算火焰方向
        flame_angle = 0  # 默认向右
        if effect.target_x is not None and effect.target_y is not None:
            target_x, target_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)
            flame_angle = math.atan2(target_y - y, target_x - x)

        # 使用特效配置中的范围参数
        effect_range = self._get_visual_effect_range(effect.effect_type)
        flame_spread = math.pi / 2  # 90度，更大的扇形
        flame_length = effect_range * ui_scale  # 使用配置的范围作为火焰长度

        # 生成多层圆形渲染
        layers = 4
        for layer in range(layers):
            layer_progress = progress + (layer * 0.05)  # 每层稍微延迟

            # 计算当前层的半径
            radius_progress = min(1.0, layer_progress * 1.2)
            current_radius = flame_length * \
                radius_progress * (0.3 + layer * 0.2)

            # 在扇形范围内生成圆形
            circles_per_layer = 6 + layer * 2
            for i in range(circles_per_layer):
                # 计算圆形在扇形中的位置
                t = i / (circles_per_layer -
                         1) if circles_per_layer > 1 else 0.5
                circle_angle = flame_angle + (t - 0.5) * flame_spread

                # 使用基于特效ID的伪随机数
                circle_seed = hash(
                    (id(effect), layer, i, int(progress * 100))) % 1000
                pseudo_random = circle_seed / 1000.0

                # 添加随机性
                angle_noise = (pseudo_random - 0.5) * 0.2
                circle_angle += angle_noise

                # 计算圆形位置
                circle_distance = current_radius * (0.3 + pseudo_random * 0.7)
                circle_x = x + math.cos(circle_angle) * circle_distance
                circle_y = y + math.sin(circle_angle) * circle_distance

                # 圆形大小
                circle_size = max(
                    2, int((effect.size * (1.0 - layer * 0.2)) * ui_scale))

                # 颜色渐变
                if effect.effect_type == 'acid_spray':
                    # 酸液颜色：绿色系
                    base_color = effect.color
                    intensity = 1.0 - layer * 0.2
                    circle_color = (
                        int(base_color[0] * intensity),
                        int(base_color[1] * intensity),
                        int(base_color[2] * intensity)
                    )
                else:  # flame_wave
                    # 火焰颜色：赤红色系
                    base_color = effect.color
                    intensity = 1.0 - layer * 0.2
                    circle_color = (
                        int(base_color[0] * intensity),
                        int(base_color[1] * intensity * 0.8),
                        int(base_color[2] * intensity * 0.6)
                    )

                # 绘制圆形
                pygame.draw.circle(screen, circle_color,
                                   (int(circle_x), int(circle_y)), circle_size)

    def _render_particle_flame_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """粒子效果 - 用于 fire_breath 和 fire_splash"""
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 计算火焰方向
        flame_angle = 0  # 默认向右
        if effect.target_x is not None and effect.target_y is not None:
            target_x, target_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)
            flame_angle = math.atan2(target_y - y, target_x - x)

        # 使用特效配置中的范围参数
        effect_range = self._get_visual_effect_range(effect.effect_type)
        flame_spread = math.pi / 3  # 60度
        flame_length = effect_range * ui_scale  # 使用配置的范围作为火焰长度

        # 生成多层火焰粒子
        layers = 3
        for layer in range(layers):
            layer_progress = progress + (layer * 0.1)  # 每层稍微延迟

            # 每层的粒子数量
            particles_per_layer = 8 + layer * 4

            for i in range(particles_per_layer):
                # 计算粒子在扇形中的位置
                t = i / (particles_per_layer -
                         1) if particles_per_layer > 1 else 0.5
                particle_angle = flame_angle + (t - 0.5) * flame_spread

                # 使用基于特效ID的伪随机数，确保同一帧内粒子位置一致
                particle_seed = hash(
                    (id(effect), layer, i, int(progress * 100))) % 1000
                pseudo_random = particle_seed / 1000.0

                # 添加随机性模拟火焰抖动
                angle_noise = (pseudo_random - 0.5) * 0.3
                particle_angle += angle_noise

                # 计算粒子距离（火焰长度随进度变化）
                distance_progress = min(1.0, layer_progress * 1.5)
                # 使用另一个伪随机数
                distance_random = hash(
                    (id(effect), layer, i, int(progress * 100), 1)) % 1000 / 1000.0
                particle_distance = flame_length * \
                    distance_progress * (0.5 + distance_random * 0.5)

                # 计算粒子位置
                particle_x = x + math.cos(particle_angle) * particle_distance
                particle_y = y + math.sin(particle_angle) * particle_distance

                # 直接使用原始粒子位置
                final_x, final_y = particle_x, particle_y

                # 火焰颜色渐变（从中心到边缘：红->橙->黄）
                # 使用基于粒子索引的颜色随机数
                color_seed1 = hash((id(effect), layer, i, int(
                    progress * 100), 2)) % 1000 / 1000.0
                color_seed2 = hash((id(effect), layer, i, int(
                    progress * 100), 3)) % 1000 / 1000.0

                if layer == 0:  # 内层：红色
                    particle_color = (
                        255, 50 + int(color_seed1 * 50), int(color_seed2 * 30))
                elif layer == 1:  # 中层：橙色
                    particle_color = (
                        255, 100 + int(color_seed1 * 50), int(color_seed2 * 50))
                else:  # 外层：黄色
                    particle_color = (
                        255, 200 + int(color_seed1 * 55), int(color_seed2 * 100))

                # 粒子大小随距离和进度变化
                particle_size = max(
                    1, int((3 - layer) * (1.0 - distance_progress) * ui_scale))

                # 绘制火焰粒子
                pygame.draw.circle(screen, particle_color,
                                   (int(final_x), int(final_y)), particle_size)

                # 为外层粒子添加发光效果
                if layer == 2:
                    glow_manager = get_glow_manager()
                    glow_manager.render_effect_glow(
                        screen, 'fire_breath', (int(final_x), int(
                            final_y)), particle_color,
                        size=particle_size + 2, ui_scale=ui_scale
                    )

        # 移除火焰底部效果（火源）

    def _render_impact_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """5. 冲击类 - 渲染以自身为中心扩展冲击波"""
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 其他冲击效果：同心圆扩展
        for i in range(3):
            # 修正：effect.size已经是世界坐标大小，不应该再乘以ui_scale
            size = int(effect.size * (1.0 + progress * (i + 1)) * ui_scale)
            pygame.draw.circle(screen, effect.color,
                               (x, y), size, max(1, int(2 * ui_scale)))

    def _render_lightning_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """6. 闪电类 - 渲染连接目标与自身的一道类似电流的折线"""
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        if effect.target_x is not None and effect.target_y is not None:
            target_x, target_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)

            # 创建闪电折线效果
            segments = 5
            points = [(x, y)]

            for i in range(1, segments):
                t = i / segments
                # 添加随机偏移模拟闪电效果
                offset_x = random.randint(-10, 10) * ui_scale
                offset_y = random.randint(-10, 10) * ui_scale
                point_x = x + (target_x - x) * t + offset_x
                point_y = y + (target_y - y) * t + offset_y
                points.append((int(point_x), int(point_y)))

            points.append((target_x, target_y))

            # 绘制折线
            line_width = max(1, int(3 * ui_scale))
            for i in range(len(points) - 1):
                pygame.draw.line(screen, effect.color,
                                 points[i], points[i + 1], line_width)

    def _render_claw_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """
        7. 爪击类 - 渲染多条直线爪痕来模拟爪击

        爪击特效设计：
        - claw_attack: 3条直线爪痕，从攻击者位置向目标方向延伸
        - beast_claw/shadow_claw: 5条直线爪痕，从攻击者位置向目标方向延伸
        - 每条爪痕有轻微的角度偏移，模拟真实的爪击轨迹
        - 爪痕长度随进度变化，从短到长
        - 使用较细的线条，区别于斩击的粗弧线
        - 颜色通常为橙色或棕色，体现野兽爪击的特点
        - 应用5倍视觉放大倍数，让爪痕更明显和具有冲击力
        """
        # 将世界坐标转换为屏幕坐标
        x, y = self._world_to_screen(
            effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 计算爪击角度和方向
        if effect.target_x is not None and effect.target_y is not None:
            # 如果有目标，朝目标方向爪击
            target_x, target_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)
            base_angle = math.atan2(target_y - y, target_x - x)
        else:
            # 如果没有目标，默认向右下方爪击
            base_angle = math.pi / 4

        # 使用特效配置中的范围参数，并应用视觉放大倍数
        effect_range = self._get_visual_effect_range(effect.effect_type)
        # 爪击类特效视觉放大倍数：基础范围 * 5倍，让爪痕更明显
        visual_multiplier = 5.0
        # 修正：移除ui_scale的直接应用，因为坐标已经是屏幕坐标
        claw_length = int(effect_range * visual_multiplier * progress)

        # 根据特效类型决定爪痕数量
        if effect.effect_type == 'claw_attack':
            claw_count = 3  # claw_attack 使用3条抓痕
        else:
            claw_count = 5  # beast_claw 和 shadow_claw 使用5条抓痕

        # 绘制爪痕
        for claw in range(claw_count):
            # 计算角度偏移，确保爪痕均匀分布
            if claw_count == 3:
                # 3条爪痕：-15度、0度、+15度
                angle_offset = (claw - 1) * (math.pi / 12)  # 15度偏移
            else:
                # 5条爪痕：-30度、-15度、0度、+15度、+30度
                angle_offset = (claw - 2) * (math.pi / 12)  # 15度偏移
            claw_angle = base_angle + angle_offset

            # 计算爪痕的起点和终点
            start_x = x
            start_y = y
            end_x = x + math.cos(claw_angle) * claw_length
            end_y = y + math.sin(claw_angle) * claw_length

            # 绘制爪痕线条
            line_width = max(1, int(2 * ui_scale))  # 较细的线条

            # 根据进度调整透明度
            claw_alpha = int(alpha * (1.0 - progress * 0.3))  # 随进度逐渐变淡

            # 创建带透明度的颜色
            claw_color = (*effect.color, claw_alpha)

            # 绘制主爪痕
            pygame.draw.line(screen, effect.color,
                             (start_x, start_y), (end_x, end_y), line_width)

            # 为每条爪痕添加轻微的发光效果
            if progress > 0.3:  # 在特效后期添加发光
                glow_manager = get_glow_manager()
                # 修正：传递世界坐标给发光管理器，让它内部处理UI缩放
                world_start_x = effect.x
                world_start_y = effect.y
                world_end_x = effect.x + \
                    math.cos(claw_angle) * (claw_length / ui_scale)
                world_end_y = effect.y + \
                    math.sin(claw_angle) * (claw_length / ui_scale)

                glow_manager.render_effect_glow(
                    screen, 'claw_attack', (world_start_x,
                                            world_start_y), effect.color,
                    end=(world_end_x, world_end_y), width=1, ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y
                )

    def _render_entangle_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """8. 缠绕类 - 直接作用于目标，缠绕样式的弧形线条"""
        # 缠绕类特效应该直接作用于目标位置
        if effect.target_x is not None and effect.target_y is not None:
            center_x, center_y = self._world_to_screen(
                effect.target_x, effect.target_y, camera_x, camera_y, ui_scale)
        else:
            center_x, center_y = self._world_to_screen(
                effect.x, effect.y, camera_x, camera_y, ui_scale)

        # 绘制缠绕样式的弧形线条
        radius = int(effect.size * (1.0 + progress * 1.5) * ui_scale)

        # 绘制多条缠绕线
        for i in range(3):
            # 每条缠绕线的起始角度
            start_angle = (2 * math.pi * i) / 3

            # 绘制缠绕弧线
            segments = 12
            points = []
            for j in range(segments):
                t = j / (segments - 1)
                # 螺旋缠绕效果
                current_angle = start_angle + t * 4 * math.pi  # 缠绕2圈
                current_radius = radius * (1.0 - t * 0.4)  # 半径逐渐减小

                point_x = center_x + math.cos(current_angle) * current_radius
                point_y = center_y + math.sin(current_angle) * current_radius
                points.append((int(point_x), int(point_y)))

            # 绘制缠绕线
            line_width = max(1, int(2 * ui_scale))
            for k in range(len(points) - 1):
                pygame.draw.line(screen, effect.color,
                                 points[k], points[k + 1], line_width)

    def _render_particle_tower_magic(self, screen: pygame.Surface, effect: VisualEffect, progress: float, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """
        渲染奥术塔魔法特效的完整效果
        包含：前30%时间的魔法弹道 + 后70%时间的火花四溅效果

        Args:
            screen: 渲染表面
            effect: 特效对象
            progress: 特效进度 (0.0-1.0)
            ui_scale: UI缩放倍数
            camera_x: 相机X坐标
            camera_y: 相机Y坐标
        """
        # 获取攻击者和目标位置的世界坐标
        attacker_x, attacker_y = effect.x, effect.y
        if effect.target_x is not None and effect.target_y is not None:
            target_x, target_y = effect.target_x, effect.target_y
        else:
            target_x, target_y = attacker_x, attacker_y

        # 前30%时间：显示魔法弹道从攻击者到目标
        if progress < 0.3:
            # 将世界坐标转换为屏幕坐标
            x, y = self._world_to_screen(
                attacker_x, attacker_y, camera_x, camera_y, ui_scale)
            target_screen_x, target_screen_y = self._world_to_screen(
                target_x, target_y, camera_x, camera_y, ui_scale)

            # 计算方向
            dx = target_screen_x - x
            dy = target_screen_y - y
            distance = math.sqrt(dx*dx + dy*dy)

            if distance > 0:
                # 归一化方向
                dx /= distance
                dy /= distance

                # 计算当前进度下的位置（从自身开始，向目标移动）
                current_distance = distance * (progress / 0.3)  # 在0.3时间内完成
                current_x = x + dx * current_distance
                current_y = y + dy * current_distance

                # 绘制魔法弹道线条
                line_width = max(1, int(3 * ui_scale))
                pygame.draw.line(screen, effect.color, (x, y),
                                 (int(current_x), int(current_y)), line_width)

                # 添加发光效果 - 使用世界坐标
                glow_manager = get_glow_manager()
                # 将屏幕坐标转换回世界坐标
                world_start_x = (x / ui_scale) + camera_x
                world_start_y = (y / ui_scale) + camera_y
                world_end_x = (current_x / ui_scale) + camera_x
                world_end_y = (current_y / ui_scale) + camera_y

                glow_manager.render_effect_glow(
                    screen, 'tower_magic_impact', (world_start_x,
                                                   world_start_y), effect.color,
                    end=(world_end_x, world_end_y), width=3, ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y
                )
        else:
            # 后70%时间：在目标位置显示火花四溅效果

            # 在目标位置创建深紫色粒子特效（只调用一次）
            if not hasattr(effect, '_particle_effect_created'):
                self._render_particle_tower_magic_impact(
                    screen, target_x, target_y, id(
                        effect), camera_x, camera_y, ui_scale
                )
                effect._particle_effect_created = True

            # 渲染火花四溅效果
            spark_count = 8  # 固定火花数量，不随UI缩放变化
            glow_manager = get_glow_manager()  # 获取发光管理器
            for i in range(spark_count):
                angle = (2 * math.pi * i) / spark_count
                # 火花距离使用世界坐标，不预先应用UI缩放
                distance = effect.size * (1.0 + (progress - 0.3) * 2)
                spark_x = target_x + math.cos(angle) * distance
                spark_y = target_y + math.sin(angle) * distance
                # 火花大小使用世界坐标，不预先应用UI缩放
                spark_size = 2

                # 使用统一的发光API渲染火花效果，让它自己处理UI缩放
                glow_manager.render_effect_glow(
                    screen, 'tower_magic_impact', (spark_x,
                                                   spark_y), effect.color,
                    size=spark_size, ui_scale=ui_scale, camera_x=camera_x, camera_y=camera_y
                )

    def _render_particle_tower_magic_impact(self, screen: pygame.Surface, target_x: float, target_y: float, target_id: int, camera_x: float = 0, camera_y: float = 0, ui_scale: float = 1.0):
        """
        创建魔法塔冲击深紫色粒子特效（散射效果）
        参考 _render_particle_flame_effect 的多层粒子系统设计

        Args:
            screen: 渲染表面
            target_x: 目标X坐标（世界坐标）
            target_y: 目标Y坐标（世界坐标）
            target_id: 目标ID，用于伪随机数生成
            camera_x: 相机X坐标
            camera_y: 相机Y坐标
            ui_scale: UI缩放倍数
        """
        import time
        current_time = time.time()

        # 使用世界坐标，让粒子系统自己处理坐标转换
        x, y = target_x, target_y

        # 生成多层散射粒子效果 - 参考火焰特效的多层设计
        layers = 3  # 增加到3层粒子，从内到外
        for layer in range(layers):
            # 每层的粒子数量，内层少，外层多，增加粒子数量
            particles_per_layer = 6 + layer * 4  # 6, 10, 14个粒子（增加粒子数量）

            for i in range(particles_per_layer):
                # 计算散射角度 - 360度均匀分布
                base_angle = (2 * math.pi * i) / particles_per_layer

                # 使用基于目标ID、层、时间和粒子索引的伪随机数，增加随机性
                particle_seed = hash(
                    (target_id, layer, i, current_time)) % 1000
                pseudo_random = particle_seed / 1000.0

                # 添加角度随机性 - 内层散射范围小，外层散射范围大
                angle_noise_range = 0.5 + layer * 0.3  # 0.5, 0.8, 1.1 (增加随机性)
                angle_noise = (pseudo_random - 0.5) * angle_noise_range
                particle_angle = base_angle + angle_noise

                # 添加飞溅效果 - 参考火焰特效的飞溅实现
                # 飞溅方向随机性 - 让粒子向不同方向飞溅
                splash_direction_random = hash(
                    (target_id, layer, i, current_time, 2)) % 1000 / 1000.0
                splash_angle_offset = (
                    splash_direction_random - 0.5) * math.pi / 4  # ±22.5度
                particle_angle += splash_angle_offset

                # 深紫色粒子，带颜色渐变 - 增加颜色随机性
                color_seed1 = hash(
                    (target_id, layer, i, current_time, 2)) % 1000 / 1000.0
                color_seed2 = hash(
                    (target_id, layer, i, current_time, 3)) % 1000 / 1000.0
                color_seed3 = hash(
                    (target_id, layer, i, current_time, 4)) % 1000 / 1000.0

                if layer == 0:  # 内层：深紫色
                    particle_color = (
                        # 确保在0-255范围内
                        min(255, max(0, 75 + int(color_seed1 * 40))),
                        # 确保在0-255范围内
                        min(255, max(0, int(color_seed2 * 50))),
                        # 确保在0-255范围内
                        min(255, max(0, 130 + int(color_seed3 * 50)))
                    )
                elif layer == 1:  # 中层：中紫色
                    particle_color = (
                        min(255, max(0, 128 + int(color_seed1 * 40))),
                        min(255, max(0, int(color_seed2 * 50))),
                        min(255, max(0, 128 + int(color_seed3 * 50)))
                    )
                else:  # 外层：浅紫色
                    particle_color = (
                        min(255, max(0, 186 + int(color_seed1 * 40))),
                        min(255, max(0, 85 + int(color_seed2 * 50))),
                        min(255, max(0, 211 + int(color_seed3 * 50)))
                    )

                # 计算散射速度 - 超快速飞溅效果
                speed_random = hash(
                    (target_id, layer, i, current_time, 5)) % 1000 / 1000.0
                # 超快速基础速度：15.0, 12.0, 9.0 像素/秒（转换为像素/毫秒）
                base_speed = (15.0 - layer * 3.0) / \
                    1000.0  # 0.015, 0.012, 0.009 像素/毫秒
                particle_speed = base_speed + speed_random * 0.005  # 增加速度随机性

                # 添加飞溅速度变化 - 让粒子速度更随机，创造更明显的扩散效果
                splash_speed_random = hash(
                    (target_id, layer, i, current_time, 4)) % 1000 / 1000.0
                splash_speed_multiplier = 0.8 + splash_speed_random * 1.4  # 0.8-2.2倍速度
                particle_speed *= splash_speed_multiplier

                # 粒子大小 - 内层大，外层小，增加大小随机性（世界坐标）
                size_random = hash(
                    (target_id, layer, i, current_time, 6)) % 1000 / 1000.0
                # 2.0, 1.5, 1.0（适中的粒子大小），世界坐标
                base_size = 2.0 - layer * 0.5
                particle_size = base_size + size_random * 0.5  # 增加大小随机性

                # 生命周期 - 中等生命周期，0.5-1秒
                lifetime_random = hash(
                    (target_id, layer, i, current_time, 7)) % 1000 / 1000.0
                # 500, 750毫秒基础时间，实际范围：层0(500-1000ms=0.5-1.0s), 层1(750-1250ms=0.75-1.25s)
                base_lifetime = 500 + layer * 250
                lifetime = base_lifetime + lifetime_random * 500  # 增加生命周期随机性

                # 无重力，粒子保持直线运动
                gravity = 0.0

                # 创建粒子 - 散射效果，高速移动，渐弱消失
                self.particle_system.create_particle(
                    x, y,  # 从中心开始
                    math.cos(particle_angle) * particle_speed,  # 高速散射
                    math.sin(particle_angle) * particle_speed,
                    particle_color,
                    particle_size,  # 动态粒子大小
                    lifetime,  # 动态生命周期
                    gravity,  # 动态重力
                    True  # 淡出
                )

        # 添加额外的随机飞溅粒子 - 创造更丰富的飞溅效果
        extra_splash_particles = 8  # 增加额外的飞溅粒子数量
        for i in range(extra_splash_particles):
            # 完全随机的飞溅方向
            splash_angle = (2 * math.pi * i) / extra_splash_particles + \
                (hash((target_id, i, current_time, 9)) %
                 1000 / 1000.0) * 2 * math.pi

            # 随机飞溅速度 - 超快速扩散
            splash_speed_random = hash(
                (target_id, i, current_time, 11)) % 1000 / 1000.0
            splash_speed = (12.0 + splash_speed_random * 8.0) / \
                1000.0  # 0.012-0.02像素/毫秒随机速度

            # 随机飞溅粒子颜色（浅紫色系）
            color_random = hash(
                (target_id, i, current_time, 12)) % 1000 / 1000.0
            splash_color = (
                min(255, max(0, 150 + int(color_random * 50))),
                min(255, max(0, 50 + int(color_random * 50))),
                min(255, max(0, 200 + int(color_random * 55)))
            )

            # 随机飞溅粒子大小
            size_random = hash(
                (target_id, i, current_time, 13)) % 1000 / 1000.0
            splash_size = 1.0 + size_random * 1.0  # 1.0-2.0随机大小

            # 随机飞溅粒子生命周期 - 中等生命周期
            lifetime_random = hash(
                (target_id, i, current_time, 14)) % 1000 / 1000.0
            splash_lifetime = 500 + lifetime_random * 500  # 500-1000毫秒随机生命周期，实际范围0.5-1.0秒

            # 创建飞溅粒子
            self.particle_system.create_particle(
                x, y,  # 从中心开始
                math.cos(splash_angle) * splash_speed,
                math.sin(splash_angle) * splash_speed,
                splash_color,
                splash_size,
                splash_lifetime,
                0.0,  # 无重力
                True  # 淡出
            )

    # 魔力粒子系统管理方法
    def create_mana_particle(self, center_x: float, center_y: float, max_range: float = 100.0):
        """创建魔力粒子"""
        return self.particle_system.create_mana_particle(center_x, center_y, max_range)

    def clear_mana_particles(self):
        """清空魔力粒子"""
        self.particle_system.clear_mana_particles()

    def get_mana_particle_count(self) -> int:
        """获取当前魔力粒子数量"""
        return self.particle_system.get_mana_particle_count()

    def is_mana_active(self) -> bool:
        """检查是否有活跃的魔力粒子"""
        return self.particle_system.is_mana_active()

    def _render_whirlwind_slash_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """旋风斩特效 - 使用刀刃拖痕特效系统渲染"""
        # 优先使用传入的范围参数，如果没有则使用配置
        damage_radius = getattr(effect, 'range', None)
        if damage_radius is None:
            config = self.visual_effect_configs.get(effect.effect_type, {})
            damage_radius = config.get("range", 80)

        # 显示范围为伤害范围的0.8倍
        visual_radius = damage_radius * 0.8
        duration = 0.8  # 加快播放速度，从1.2秒减少到0.8秒

        # 创建刀刃拖痕特效（如果还没有创建）
        if not hasattr(effect, '_blade_trail_created'):
            # 使用世界坐标创建特效
            world_x = effect.x
            world_y = effect.y
            self.whirlwind_effect_manager.create_whirlwind_effect(
                world_x, world_y, visual_radius, duration)
            effect._blade_trail_created = True
            game_logger.info(
                f"🗡️ 旋风斩特效创建 - 中心:({world_x:.1f},{world_y:.1f}), 显示半径:{visual_radius:.1f}, 伤害半径:{damage_radius:.1f}")

        # 刀刃拖痕特效由独立的系统管理，这里不需要额外渲染
        # 只需要确保特效被创建即可
