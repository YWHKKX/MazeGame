#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特效渲染器模块
"""

import pygame
from typing import List, Tuple, Optional
from .particle_system import ParticleSystem
from .projectile_system import ProjectileSystem
from .area_effect_system import AreaEffectSystem
from src.utils.logger import game_logger


class EffectRenderer:
    """特效渲染器"""

    def __init__(self):
        self.render_layers = {
            "background": 0,    # 背景特效
            "projectiles": 1,   # 投射物
            "characters": 2,    # 角色和生物
            "melee_effects": 3,  # 近战特效
            "ui_effects": 4     # UI特效
        }
        self.effects_by_layer = {
            layer: [] for layer in self.render_layers.values()
        }

    def add_effect(self, effect, layer: str = "melee_effects"):
        """添加特效到指定层级"""
        layer_id = self.render_layers.get(layer, 3)
        self.effects_by_layer[layer_id].append(effect)

    def remove_effect(self, effect):
        """移除特效"""
        for layer_effects in self.effects_by_layer.values():
            if effect in layer_effects:
                layer_effects.remove(effect)

    def render_layer(self, screen: pygame.Surface, layer: str):
        """渲染指定层级"""
        layer_id = self.render_layers.get(layer, 3)
        effects = self.effects_by_layer[layer_id]

        for effect in effects:
            if hasattr(effect, 'render'):
                effect.render(screen)

    def render_all(self, screen: pygame.Surface, ui_scale: float = 1.0):
        """按层级顺序渲染所有特效"""
        if screen is None:
            return screen

        # 按层级ID排序渲染
        for layer_id in sorted(self.effects_by_layer.keys()):
            effects = self.effects_by_layer[layer_id]
            for effect in effects:
                if hasattr(effect, 'render') and not getattr(effect, 'finished', False):
                    # 检查effect的render方法是否支持ui_scale参数
                    if 'ui_scale' in effect.render.__code__.co_varnames:
                        effect.render(screen, ui_scale)
                    else:
                        effect.render(screen)

        return screen

    def clear_layer(self, layer: str):
        """清空指定层级"""
        layer_id = self.render_layers.get(layer, 3)
        self.effects_by_layer[layer_id].clear()

    def clear_all(self):
        """清空所有特效"""
        for layer_effects in self.effects_by_layer.values():
            layer_effects.clear()

    def get_layer_count(self, layer: str) -> int:
        """获取指定层级的特效数量"""
        layer_id = self.render_layers.get(layer, 3)
        return len(self.effects_by_layer[layer_id])

    def get_total_count(self) -> int:
        """获取总特效数量"""
        return sum(len(effects) for effects in self.effects_by_layer.values())

    def cleanup_finished_effects(self):
        """清理已完成的特效"""
        for layer_effects in self.effects_by_layer.values():
            layer_effects[:] = [effect for effect in layer_effects
                                if not getattr(effect, 'finished', False)]


class ScreenShake:
    """屏幕震动效果"""

    def __init__(self):
        self.intensity = 0.0
        self.duration = 0.0
        self.current_time = 0.0
        self.active = False
        self.offset_x = 0
        self.offset_y = 0

    def start_shake(self, intensity: float, duration: float):
        """开始屏幕震动"""
        self.intensity = intensity
        self.duration = duration
        self.current_time = 0.0
        self.active = True

    def update(self, delta_time: float):
        """更新震动效果"""
        if not self.active:
            return

        self.current_time += delta_time

        if self.current_time >= self.duration:
            self.active = False
            self.offset_x = 0
            self.offset_y = 0
            return

        # 计算震动强度（随时间衰减）
        progress = self.current_time / self.duration
        current_intensity = self.intensity * (1 - progress)

        # 生成随机偏移
        import random
        self.offset_x = random.uniform(-current_intensity, current_intensity)
        self.offset_y = random.uniform(-current_intensity, current_intensity)

    def apply_to_surface(self, surface: pygame.Surface) -> pygame.Surface:
        """将震动效果应用到表面"""
        if not self.active or surface is None:
            return surface

        try:
            # 创建带偏移的新表面
            offset_surface = pygame.Surface(
                surface.get_size(), pygame.SRCALPHA)
            if offset_surface is None:
                game_logger.info("❌ 创建震动Surface失败")
                return surface

            offset_surface.blit(surface, (self.offset_x, self.offset_y))
            return offset_surface
        except Exception as e:
            game_logger.info(f"❌ 应用屏幕震动失败: {e}")
            return surface


class DamageNumberRenderer:
    """伤害数字渲染器"""

    def __init__(self):
        self.damage_numbers = []
        self.font = None
        self.try_load_font()

    def try_load_font(self):
        """尝试加载字体"""
        try:
            self.font = pygame.font.Font(None, 24)
        except:
            try:
                self.font = pygame.font.SysFont("Arial", 24)
            except:
                # 如果字体系统未初始化，设置为None
                self.font = None

    def add_damage_number(self, x: float, y: float, damage: int,
                          damage_type: str = "normal"):
        """添加伤害数字"""
        damage_info = {
            "x": x,
            "y": y,
            "damage": damage,
            "type": damage_type,
            "life": 2000,  # 2秒
            "max_life": 2000,
            "velocity_y": -50,  # 向上飘浮
            "alpha": 255
        }
        self.damage_numbers.append(damage_info)

    def update(self, delta_time: float):
        """更新伤害数字"""
        for damage_info in self.damage_numbers[:]:
            damage_info["life"] -= delta_time
            damage_info["y"] += damage_info["velocity_y"] * delta_time * 0.001
            damage_info["velocity_y"] += 20 * delta_time * 0.001  # 重力

            # 计算透明度
            progress = 1 - (damage_info["life"] / damage_info["max_life"])
            damage_info["alpha"] = int(255 * (1 - progress))

            if damage_info["life"] <= 0:
                self.damage_numbers.remove(damage_info)

    def render(self, screen: pygame.Surface, ui_scale: float = 1.0):
        """渲染伤害数字"""
        if not self.font or not pygame.font.get_init():
            return

        for damage_info in self.damage_numbers:
            if damage_info["alpha"] <= 0:
                continue

            # 根据伤害类型选择颜色
            if damage_info["type"] == "critical":
                color = (255, 215, 0)  # 金色
            elif damage_info["type"] == "heal":
                color = (0, 255, 0)    # 绿色
            elif damage_info["type"] == "magic":
                color = (138, 43, 226)  # 紫色
            else:
                color = (255, 255, 255)  # 白色

            # 应用UI缩放
            scaled_x = int(damage_info["x"] * ui_scale)
            scaled_y = int(damage_info["y"] * ui_scale)
            scaled_font_size = max(12, int(24 * ui_scale))

            # 创建缩放后的字体
            try:
                scaled_font = pygame.font.Font(None, scaled_font_size)
            except:
                scaled_font = self.font

            # 渲染文字
            text = scaled_font.render(str(damage_info["damage"]), True, color)

            # 应用透明度
            if damage_info["alpha"] < 255:
                text.set_alpha(damage_info["alpha"])

            # 绘制到屏幕
            screen.blit(text, (scaled_x, scaled_y))

    def clear(self):
        """清空所有伤害数字"""
        self.damage_numbers.clear()


class EffectRendererManager:
    """特效渲染管理器"""

    def __init__(self):
        self.renderer = EffectRenderer()
        self.screen_shake = ScreenShake()
        self.damage_renderer = DamageNumberRenderer()

    def render_all(self, screen: pygame.Surface, ui_scale: float = 1.0):
        """渲染所有特效"""
        if screen is None:
            game_logger.info(
                "❌ EffectRendererManager.render_all() 收到 None screen，跳过渲染")
            return screen

        # 渲染特效层级
        self.renderer.render_all(screen, ui_scale)

        # 渲染伤害数字
        self.damage_renderer.render(screen, ui_scale)

        # 应用屏幕震动
        if self.screen_shake.active:
            try:
                screen = self.screen_shake.apply_to_surface(screen)
                if screen is None:
                    game_logger.info(
                        "❌ ScreenShake.apply_to_surface() 返回 None")
                    return screen
            except Exception as e:
                game_logger.info(f"❌ 屏幕震动应用失败: {e}")
                return screen

        return screen

    def update(self, delta_time: float):
        """更新所有渲染效果"""
        self.screen_shake.update(delta_time)
        self.damage_renderer.update(delta_time)
        self.renderer.cleanup_finished_effects()

    def trigger_screen_shake(self, intensity: float, duration: float):
        """触发屏幕震动"""
        self.screen_shake.start_shake(intensity, duration)

    def show_damage_number(self, x: float, y: float, damage: int, damage_type: str = "normal"):
        """显示伤害数字 - 已禁用"""
        pass

    def clear_all(self):
        """清空所有特效"""
        self.renderer.clear_all()
        self.damage_renderer.clear()
        self.screen_shake.active = False
