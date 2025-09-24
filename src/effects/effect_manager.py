#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特效管理器模块
"""

import math
import random
from typing import List, Dict, Any, Optional, Tuple
from .particle_system import ParticleSystem
from .projectile_system import ProjectileSystem
from .area_effect_system import AreaEffectSystem
from .effect_renderer import EffectRendererManager
from .effect_pool import EffectPool
from .effect_renderer import EffectRenderer


class EffectManager:
    """特效管理器 - 统一管理所有攻击特效"""

    def __init__(self):
        # 核心系统
        self.particle_system = ParticleSystem()
        self.projectile_system = ProjectileSystem()
        self.area_effect_system = AreaEffectSystem()
        self.renderer_manager = EffectRenderer()
        self.effect_pool = EffectPool()

        # 特效配置
        self.effect_configs = self._load_effect_configs()

        # 性能设置 - 大幅降低限制以避免卡死
        self.max_particles = 50  # 从500降低到50
        self.max_projectiles = 10  # 从100降低到10
        self.max_area_effects = 5  # 从50降低到5
        self.performance_mode = "low"  # 改为low模式

        # 特效冷却机制
        self.effect_cooldowns = {}  # 存储特效冷却时间
        self.effect_cooldown_time = 100  # 100毫秒冷却时间

    def _load_effect_configs(self) -> Dict[str, Dict]:
        """加载特效配置"""
        return {
            # 近战攻击特效 - 根据COMBAT_SYSTEM.md文档更新伤害值
            "melee_slash": {
                "type": "particle",
                "particles": {"sparks": 2, "color": (255, 215, 0), "velocity_range": (50, 100), "size_range": (2, 4)},
                "sound": "slash_1.wav",
                "screen_shake": {"intensity": 0.1, "duration": 0.1}
            },
            "melee_heavy": {
                "type": "particle",
                "particles": {"sparks": 3, "debris": 2, "color": (255, 69, 0), "velocity_range": (80, 150), "size_range": (3, 6)},
                "sound": "heavy_strike.wav",
                "screen_shake": {"intensity": 0.3, "duration": 0.2}
            },
            "shadow_slash": {
                "type": "particle",
                "particles": {"shadow_orbs": 2, "color": (74, 74, 74), "velocity_range": (30, 60)},
                "sound": "shadow_hit.wav",
                "screen_shake": {"intensity": 0.2, "duration": 0.15}
            },
            "divine_strike": {
                "type": "particle",
                "particles": {"light_orbs": 3, "color": (255, 215, 0), "velocity_range": (40, 80)},
                "sound": "divine_strike.wav",
                "screen_shake": {"intensity": 0.25, "duration": 0.2}
            },

            # 远程攻击特效 - 根据COMBAT_SYSTEM.md文档更新伤害值
            "arrow_shot": {
                "type": "projectile",
                "projectile_type": "arrow",
                "speed": 400,
                "damage": 16,  # 弓箭手攻击力
                "color": (139, 69, 19),
                "sound": "arrow_whiz.wav"
            },
            "precise_arrow": {
                "type": "projectile",
                "projectile_type": "arrow",
                "speed": 500,
                "damage": 25,  # 游侠攻击力
                "color": (255, 215, 0),
                "sound": "precise_shot.wav"
            },
            "tracking_arrow": {
                "type": "projectile",
                "projectile_type": "arrow",
                "speed": 350,
                "damage": 25,  # 游侠攻击力
                "color": (50, 205, 50),
                "tracking": True,
                "sound": "tracking_arrow.wav"
            },

            # 箭塔攻击特效 - 与文档保持一致
            "tower_arrow_shot": {
                "type": "projectile",
                "projectile_type": "tower_arrow",
                "speed": 500,
                "damage": 30,  # 更新为文档中的30点物理伤害
                "color": (200, 200, 200),
                "trail_effect": True,
                "sound": "tower_arrow.wav",
                "screen_shake": {"intensity": 0.05, "duration": 0.05}
            },
            "tower_critical_arrow": {
                "type": "projectile",
                "projectile_type": "tower_arrow",
                "speed": 600,
                "damage": 60,  # 更新为文档中的双倍伤害（30*2=60）
                "color": (255, 215, 0),
                "trail_effect": True,
                "glow_effect": True,
                "sound": "tower_critical.wav",
                "screen_shake": {"intensity": 0.1, "duration": 0.1}
            },
            "tower_arrow_impact": {
                "type": "particle",
                "particles": {"sparks": 8, "color": (255, 255, 255), "velocity_range": (80, 150), "size_range": (3, 6)},
                "sound": "arrow_impact.wav",
                "screen_shake": {"intensity": 0.08, "duration": 0.08}
            },

            # 魔法攻击特效 - 根据COMBAT_SYSTEM.md文档更新伤害值
            "fireball": {
                "type": "projectile",
                "projectile_type": "fireball",
                "speed": 300,
                "damage": 22,  # 法师攻击力
                "color": (255, 69, 0),
                "explosion_radius": 50,
                "sound": "fireball_explosion.wav",
                "screen_shake": {"intensity": 0.2, "duration": 0.15}
            },
            "chain_lightning": {
                "type": "projectile",
                "projectile_type": "lightning",
                "speed": 500,
                "damage": 35,  # 大法师攻击力
                "color": (0, 191, 255),
                "max_jumps": 5,
                "sound": "lightning_crack.wav"
            },

            # 怪物特殊攻击特效 - 根据COMBAT_SYSTEM.md文档更新伤害值
            "fire_breath": {
                "type": "area",
                "area_type": "fire",
                "radius": 80,
                "duration": 3000,
                "damage_per_second": 30,  # 地狱犬攻击力
                "color": (255, 69, 0),
                "sound": "fire_breath.wav"
            },
            "fire_splash": {
                "type": "area",
                "area_type": "fire",
                "radius": 40,
                "duration": 4000,
                "damage_per_second": 28,  # 火蜥蜴攻击力
                "color": (255, 69, 0),
                "sound": "fire_splash.wav"
            },
            "spine_storm": {
                "type": "area",
                "area_type": "explosion",
                "radius": 60,
                "duration": 2000,
                "damage_per_second": 60,  # 骨龙攻击力
                "color": (248, 249, 250),
                "sound": "spine_storm.wav",
                "screen_shake": {"intensity": 0.4, "duration": 0.3}
            },
            "acid_spray": {
                "type": "projectile",
                "projectile_type": "acid",
                "speed": 250,
                "damage": 22,  # 暗影法师攻击力
                "color": (50, 205, 50),
                "bounces": 2,
                "sound": "acid_hiss.wav"
            },
            "charm_effect": {
                "type": "projectile",
                "projectile_type": "charm",
                "speed": 200,
                "damage": 32,  # 魅魔攻击力
                "color": (255, 20, 147),
                "homing": True,
                "sound": "charm.wav"
            }
        }

    def create_effect(self, effect_type: str, x: float, y: float,
                      target_x: float = None, target_y: float = None,
                      damage: int = 0, **kwargs) -> bool:
        """创建特效"""
        if effect_type not in self.effect_configs:
            print(f"警告: 未知的特效类型: {effect_type}")
            return False

        # 激进性能保护 - 如果特效数量过多，直接跳过
        stats = self.get_performance_stats()
        if stats['particles'] > self.max_particles * 0.5:  # 50%阈值就跳过
            return False

        # 冷却机制 - 防止同一位置的特效创建过于频繁
        import time
        current_time = time.time() * 1000  # 转换为毫秒
        effect_key = f"{effect_type}_{int(x//10)}_{int(y//10)}"  # 按10像素网格分组

        if effect_key in self.effect_cooldowns:
            if current_time - self.effect_cooldowns[effect_key] < self.effect_cooldown_time:
                return False  # 冷却中，跳过创建

        self.effect_cooldowns[effect_key] = current_time

        config = self.effect_configs[effect_type]

        # 根据特效类型创建相应特效
        if config["type"] == "particle":
            return self._create_particle_effect(effect_type, x, y, config, damage, **kwargs)
        elif config["type"] == "projectile":
            return self._create_projectile_effect(effect_type, x, y, target_x, target_y, config, damage, **kwargs)
        elif config["type"] == "area":
            return self._create_area_effect(effect_type, x, y, config, damage, **kwargs)

        return False

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

    def _create_particle_effect_reduced(self, effect_type: str, x: float, y: float,
                                        config: Dict, damage: int, **kwargs) -> bool:
        """创建减少粒子数量的特效"""
        particles_config = config.get("particles", {})

        # 减少粒子数量到原来的1/3
        if effect_type == "melee_slash":
            reduced_sparks = max(1, particles_config.get("sparks", 8) // 3)
            self.particle_system.create_spark_effect(x, y, reduced_sparks,
                                                     particles_config.get("color", (255, 215, 0)))
        elif effect_type == "melee_heavy":
            reduced_sparks = max(1, particles_config.get("sparks", 15) // 3)
            self.particle_system.create_spark_effect(x, y, reduced_sparks,
                                                     particles_config.get("color", (255, 69, 0)))
        elif effect_type == "shadow_slash":
            reduced_orbs = max(1, particles_config.get("shadow_orbs", 5) // 3)
            self.particle_system.create_particle_burst(x, y, reduced_orbs,
                                                       particles_config.get(
                                                           "color", (74, 74, 74)),
                                                       (2, 4), (30, 60), 400, -0.5)
        elif effect_type == "divine_strike":
            reduced_orbs = max(1, particles_config.get("light_orbs", 12) // 3)
            self.particle_system.create_particle_burst(x, y, reduced_orbs,
                                                       particles_config.get(
                                                           "color", (255, 215, 0)),
                                                       (3, 6), (40, 80), 600, 0.2)

        # 伤害数字现在显示在目标位置，不在特效创建位置显示
        return True

    def _create_projectile_effect(self, effect_type: str, x: float, y: float,
                                  target_x: float, target_y: float, config: Dict,
                                  damage: int, **kwargs) -> bool:
        """创建投射物特效"""
        if target_x is None or target_y is None:
            return False

        # 创建投射物
        if config["projectile_type"] == "arrow":
            if effect_type == "tracking_arrow":
                projectile = self.projectile_system.create_tracking_arrow(x, y, target_x, target_y,
                                                                          config["speed"], damage)
            elif effect_type == "precise_arrow":
                projectile = self.projectile_system.create_arrow(x, y, target_x, target_y,
                                                                 config["speed"], damage)
                projectile.color = config["color"]  # 金色精准箭
            else:
                projectile = self.projectile_system.create_arrow(x, y, target_x, target_y,
                                                                 config["speed"], damage)

        elif config["projectile_type"] == "tower_arrow":
            # 检查是否为暴击箭矢
            is_critical = effect_type == "tower_critical_arrow"
            projectile = self.projectile_system.create_tower_arrow(x, y, target_x, target_y,
                                                                   config["speed"], damage, is_critical)

        elif config["projectile_type"] == "fireball":
            projectile = self.projectile_system.create_fireball(x, y, target_x, target_y,
                                                                config["speed"], damage)
            # 设置爆炸效果
            if "explosion_radius" in config:
                projectile.explosion_radius = config["explosion_radius"]

        elif config["projectile_type"] == "lightning":
            projectile = self.projectile_system.create_lightning_bolt(x, y, target_x, target_y,
                                                                      config["speed"], damage)

        elif config["projectile_type"] == "acid":
            projectile = self.projectile_system._get_or_create_projectile(
                x, y, target_x, target_y, config["speed"], damage,
                config["color"], 4, "acid", 4000
            )
            projectile.bounces = config.get("bounces", 0)
            projectile.max_bounces = projectile.bounces

        elif config["projectile_type"] == "charm":
            projectile = self.projectile_system._get_or_create_projectile(
                x, y, target_x, target_y, config["speed"], damage,
                config["color"], 3, "charm", 3000
            )
            projectile.tracking = True

        # 触发屏幕震动（如果支持）
        screen_shake = config.get("screen_shake")
        if screen_shake and hasattr(self.renderer_manager, 'trigger_screen_shake'):
            self.renderer_manager.trigger_screen_shake(
                screen_shake["intensity"], screen_shake["duration"]
            )

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

            # 创建命中特效
            self.particle_system.create_blood_effect(target.x, target.y, 6)

            # 如果是火球，创建爆炸效果
            if projectile.projectile_type == "fireball" and hasattr(projectile, 'explosion_radius'):
                self.area_effect_system.create_explosion(
                    target.x, target.y, projectile.explosion_radius, 1500)

            print(
                f"🎯 {projectile.projectile_type} 命中 {target.type}，造成 {projectile.damage} 点伤害")

    def _check_area_damage(self, targets: List, camera_x: float = 0, camera_y: float = 0):
        """检查区域伤害"""
        damage_events = self.area_effect_system.check_damage(targets)
        for effect, target in damage_events:
            target._take_damage(effect.damage_per_second)
            # 伤害数字显示已移除

    def render(self, screen):
        """渲染所有特效"""
        # 渲染各系统
        self.particle_system.render(screen)
        self.projectile_system.render(screen)
        self.area_effect_system.render(screen)

        # 渲染管理器处理屏幕震动和伤害数字
        return self.renderer_manager.render_all(screen)

    def clear_all(self):
        """清空所有特效"""
        self.particle_system.clear()
        self.projectile_system.clear()
        self.area_effect_system.clear()
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
