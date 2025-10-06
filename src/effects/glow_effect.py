#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发光效果API模块
提供统一的发光效果渲染功能
"""

import pygame
import math
from typing import Tuple, List, Optional, Union
from dataclasses import dataclass


@dataclass
class GlowConfig:
    """发光效果配置"""
    intensity: float = 1.0  # 发光强度 (0.0-2.0)
    size_multiplier: float = 1.2  # 发光大小倍数
    color_boost: Tuple[int, int, int] = (50, 50, 50)  # 颜色增强值
    alpha: int = 200  # 发光透明度
    layers: int = 2  # 发光层数


class GlowEffectRenderer:
    """发光效果渲染器"""

    def __init__(self):
        self.default_config = GlowConfig()

    def create_glow_color(self, base_color: Tuple[int, int, int],
                          config: Optional[GlowConfig] = None) -> Tuple[int, int, int]:
        """
        创建发光颜色

        Args:
            base_color: 基础颜色 (R, G, B)
            config: 发光配置，如果为None则使用默认配置

        Returns:
            发光颜色 (R, G, B)
        """
        if config is None:
            config = self.default_config

        glow_color = (
            min(255, max(
                0, base_color[0] + int(config.color_boost[0] * config.intensity))),
            min(255, max(
                0, base_color[1] + int(config.color_boost[1] * config.intensity))),
            min(255, max(
                0, base_color[2] + int(config.color_boost[2] * config.intensity)))
        )
        return glow_color

    def render_circle_glow(self, screen: pygame.Surface,
                           center: Tuple[int, int],
                           base_radius: int,
                           base_color: Tuple[int, int, int],
                           config: Optional[GlowConfig] = None,
                           ui_scale: float = 1.0,
                           camera_x: float = 0,
                           camera_y: float = 0) -> None:
        """
        渲染圆形发光效果

        Args:
            screen: 渲染表面
            center: 中心点坐标 (x, y)
            base_radius: 基础半径
            base_color: 基础颜色
            config: 发光配置
            ui_scale: UI缩放比例
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
        """
        if config is None:
            config = self.default_config

        # 世界坐标转屏幕坐标
        x, y = center
        screen_x = int((x - camera_x) * ui_scale)
        screen_y = int((y - camera_y) * ui_scale)

        glow_color = self.create_glow_color(base_color, config)

        # 渲染多层发光效果
        for layer in range(config.layers):
            layer_intensity = config.intensity * (1.0 - layer * 0.3)
            layer_radius = int(
                base_radius * config.size_multiplier * (1.0 + layer * 0.3) * ui_scale)
            layer_alpha = int(config.alpha * layer_intensity)

            # 创建半透明表面
            glow_surface = pygame.Surface(
                (layer_radius * 2, layer_radius * 2), pygame.SRCALPHA)
            glow_surface.set_alpha(layer_alpha)

            # 绘制发光圆形
            pygame.draw.circle(glow_surface, glow_color,
                               (layer_radius, layer_radius), layer_radius)

            # 渲染到主表面
            screen.blit(glow_surface, (screen_x -
                        layer_radius, screen_y - layer_radius))

    def render_line_glow(self, screen: pygame.Surface,
                         start: Tuple[int, int],
                         end: Tuple[int, int],
                         base_color: Tuple[int, int, int],
                         base_width: int,
                         config: Optional[GlowConfig] = None,
                         ui_scale: float = 1.0,
                         camera_x: float = 0,
                         camera_y: float = 0) -> None:
        """
        渲染线条发光效果

        Args:
            screen: 渲染表面
            start: 起点坐标 (x, y)
            end: 终点坐标 (x, y)
            base_color: 基础颜色
            base_width: 基础线条宽度
            config: 发光配置
            ui_scale: UI缩放比例
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
        """
        if config is None:
            config = self.default_config

        # 世界坐标转屏幕坐标
        start_x, start_y = start
        end_x, end_y = end
        screen_start = (int((start_x - camera_x) * ui_scale),
                        int((start_y - camera_y) * ui_scale))
        screen_end = (int((end_x - camera_x) * ui_scale),
                      int((end_y - camera_y) * ui_scale))

        glow_color = self.create_glow_color(base_color, config)

        # 渲染多层发光线条
        for layer in range(config.layers):
            layer_intensity = config.intensity * (1.0 - layer * 0.2)
            layer_width = max(
                1, int(base_width * config.size_multiplier * (1.0 + layer * 0.5) * ui_scale))
            layer_alpha = int(config.alpha * layer_intensity)

            # 创建半透明表面
            glow_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            glow_surface.set_alpha(layer_alpha)

            # 绘制发光线条
            pygame.draw.line(glow_surface, glow_color,
                             screen_start, screen_end, layer_width)

            # 渲染到主表面
            screen.blit(glow_surface, (0, 0))

    def render_particle_glow(self, screen: pygame.Surface,
                             position: Tuple[int, int],
                             base_size: int,
                             base_color: Tuple[int, int, int],
                             config: Optional[GlowConfig] = None,
                             ui_scale: float = 1.0,
                             camera_x: float = 0,
                             camera_y: float = 0) -> None:
        """
        渲染粒子发光效果

        Args:
            screen: 渲染表面
            position: 粒子位置 (x, y)
            base_size: 基础粒子大小
            base_color: 基础颜色
            config: 发光配置
            ui_scale: UI缩放比例
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
        """
        if config is None:
            config = self.default_config

        # 世界坐标转屏幕坐标
        x, y = position
        screen_x = int((x - camera_x) * ui_scale)
        screen_y = int((y - camera_y) * ui_scale)

        glow_color = self.create_glow_color(base_color, config)

        # 渲染发光粒子
        # base_size 是原始世界坐标大小，需要应用size_multiplier和ui_scale
        glow_size = max(1, int(base_size * config.size_multiplier * ui_scale))
        glow_alpha = int(config.alpha * config.intensity)

        # 创建半透明表面
        glow_surface = pygame.Surface(
            (glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        glow_surface.set_alpha(glow_alpha)

        # 绘制发光粒子
        pygame.draw.circle(glow_surface, glow_color,
                           (glow_size, glow_size), glow_size)

        # 渲染到主表面
        screen.blit(glow_surface, (screen_x - glow_size, screen_y - glow_size))

    def render_arc_glow(self, screen: pygame.Surface,
                        center: Tuple[int, int],
                        radius: int,
                        start_angle: float,
                        end_angle: float,
                        base_color: Tuple[int, int, int],
                        base_width: int,
                        config: Optional[GlowConfig] = None,
                        ui_scale: float = 1.0,
                        camera_x: float = 0,
                        camera_y: float = 0) -> None:
        """
        渲染弧形发光效果

        Args:
            screen: 渲染表面
            center: 中心点坐标 (x, y)
            radius: 弧形半径
            start_angle: 起始角度（弧度）
            end_angle: 结束角度（弧度）
            base_color: 基础颜色
            base_width: 基础线条宽度
            config: 发光配置
            ui_scale: UI缩放比例
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
        """
        if config is None:
            config = self.default_config

        # 世界坐标转屏幕坐标
        x, y = center
        screen_center = (int((x - camera_x) * ui_scale),
                         int((y - camera_y) * ui_scale))
        glow_color = self.create_glow_color(base_color, config)

        # 渲染多层发光弧形
        for layer in range(config.layers):
            layer_intensity = config.intensity * (1.0 - layer * 0.3)
            layer_radius = int(radius * config.size_multiplier *
                               (1.0 + layer * 0.2) * ui_scale)
            layer_width = max(
                1, int(base_width * config.size_multiplier * (1.0 + layer * 0.3) * ui_scale))
            layer_alpha = int(config.alpha * layer_intensity)

            # 创建半透明表面
            glow_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            glow_surface.set_alpha(layer_alpha)

            # 绘制发光弧形
            self._draw_arc(glow_surface, glow_color, screen_center, layer_radius,
                           start_angle, end_angle, layer_width)

            # 渲染到主表面
            screen.blit(glow_surface, (0, 0))

    def _draw_arc(self, surface: pygame.Surface,
                  color: Tuple[int, int, int],
                  center: Tuple[int, int],
                  radius: int,
                  start_angle: float,
                  end_angle: float,
                  width: int) -> None:
        """绘制弧形线条"""
        x, y = center

        # 计算弧形段数
        angle_range = end_angle - start_angle
        segments = max(8, int(abs(angle_range) * radius / 10))

        points = []
        for i in range(segments + 1):
            t = i / segments
            angle = start_angle + t * angle_range
            point_x = x + math.cos(angle) * radius
            point_y = y + math.sin(angle) * radius
            points.append((int(point_x), int(point_y)))

        # 绘制弧形线条
        for i in range(len(points) - 1):
            pygame.draw.line(surface, color, points[i], points[i + 1], width)


class GlowEffectManager:
    """发光效果管理器"""

    def __init__(self):
        self.renderer = GlowEffectRenderer()
        self.presets = self._create_presets()

    def _create_presets(self) -> dict:
        """创建预设发光效果配置"""
        return {
            'subtle': GlowConfig(
                intensity=0.5,
                size_multiplier=1.1,
                color_boost=(20, 20, 20),
                alpha=100,
                layers=1
            ),
            'normal': GlowConfig(
                intensity=1.0,
                size_multiplier=1.2,
                color_boost=(50, 50, 50),
                alpha=200,
                layers=2
            ),
            'intense': GlowConfig(
                intensity=1.5,
                size_multiplier=1.5,
                color_boost=(80, 80, 80),
                alpha=255,
                layers=3
            ),
            'critical': GlowConfig(
                intensity=2.0,
                size_multiplier=2.0,
                color_boost=(100, 100, 100),
                alpha=255,
                layers=4
            ),
            'magic': GlowConfig(
                intensity=1.2,
                size_multiplier=1.3,
                color_boost=(30, 30, 80),
                alpha=180,
                layers=2
            ),
            'fire': GlowConfig(
                intensity=1.3,
                size_multiplier=1.4,
                color_boost=(80, 30, 0),
                alpha=220,
                layers=3
            )
        }

    def get_preset(self, preset_name: str) -> GlowConfig:
        """获取预设发光配置"""
        return self.presets.get(preset_name, self.presets['normal'])

    def create_custom_config(self, intensity: float = 1.0,
                             size_multiplier: float = 1.2,
                             color_boost: Tuple[int, int, int] = (50, 50, 50),
                             alpha: int = 200,
                             layers: int = 2) -> GlowConfig:
        """创建自定义发光配置"""
        return GlowConfig(
            intensity=intensity,
            size_multiplier=size_multiplier,
            color_boost=color_boost,
            alpha=alpha,
            layers=layers
        )

    def render_effect_glow(self, screen: pygame.Surface,
                           effect_type: str,
                           position: Tuple[int, int],
                           base_color: Tuple[int, int, int],
                           ui_scale: float = 1.0,
                           camera_x: float = 0,
                           camera_y: float = 0,
                           **kwargs) -> None:
        """
        根据特效类型渲染相应的发光效果

        Args:
            screen: 渲染表面
            effect_type: 特效类型
            position: 位置坐标
            base_color: 基础颜色
            ui_scale: UI缩放比例
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
            **kwargs: 其他参数
        """
        # 根据特效类型选择预设配置
        preset_map = {
            'arrow_shot': 'normal',
            'tower_critical_arrow': 'critical',
            'tower_magic_impact': 'magic',
            'fire_breath': 'fire',
            'fire_splash': 'fire',
            'melee_slash': 'normal',
            'melee_heavy': 'intense',
            'magic_explosion': 'magic',
            'lightning_bolt': 'intense'
        }

        preset_name = preset_map.get(effect_type, 'normal')
        config = self.get_preset(preset_name)

        # 根据特效类型调用相应的渲染方法
        if 'radius' in kwargs:
            # 圆形发光
            self.renderer.render_circle_glow(
                screen, position, kwargs['radius'], base_color, config,
                ui_scale, camera_x, camera_y
            )
        elif 'end' in kwargs:
            # 线条发光
            self.renderer.render_line_glow(
                screen, position, kwargs['end'], base_color,
                kwargs.get('width', 3), config, ui_scale, camera_x, camera_y
            )
        elif 'size' in kwargs:
            # 粒子发光
            self.renderer.render_particle_glow(
                screen, position, kwargs['size'], base_color, config,
                ui_scale, camera_x, camera_y
            )
        elif 'start_angle' in kwargs and 'end_angle' in kwargs:
            # 弧形发光
            self.renderer.render_arc_glow(
                screen, position, kwargs['radius'], kwargs['start_angle'],
                kwargs['end_angle'], base_color, kwargs.get('width', 3),
                config, ui_scale, camera_x, camera_y
            )


# 全局发光效果管理器实例
_glow_manager = None


def get_glow_manager() -> GlowEffectManager:
    """获取全局发光效果管理器实例"""
    global _glow_manager
    if _glow_manager is None:
        _glow_manager = GlowEffectManager()
    return _glow_manager


def render_glow_effect(screen: pygame.Surface, effect_type: str,
                       position: Tuple[int, int], base_color: Tuple[int, int, int],
                       ui_scale: float = 1.0,
                       camera_x: float = 0,
                       camera_y: float = 0,
                       **kwargs) -> None:
    """
    便捷函数：渲染发光效果

    Args:
        screen: 渲染表面
        effect_type: 特效类型
        position: 位置坐标
        base_color: 基础颜色
        ui_scale: UI缩放比例
        camera_x: 相机X偏移
        camera_y: 相机Y偏移
        **kwargs: 其他参数
    """
    manager = get_glow_manager()
    manager.render_effect_glow(
        screen, effect_type, position, base_color, ui_scale, camera_x, camera_y, **kwargs)
