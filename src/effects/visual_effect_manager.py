#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可视化特效管理器 - 提供基本的视觉效果
"""

import pygame
import time
import math
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


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


class VisualEffectManager:
    """可视化特效管理器 - 提供基本的视觉特效显示"""

    def __init__(self, speed_multiplier: float = 1.0):
        self.effects: List[VisualEffect] = []
        self.font = None
        self.speed_multiplier = speed_multiplier  # 特效播放速度倍数
        self.try_load_font()

    def try_load_font(self):
        """尝试加载字体"""
        try:
            self.font = pygame.font.Font(None, 24)
        except:
            try:
                self.font = pygame.font.SysFont("Arial", 24)
            except:
                self.font = None

    def create_effect(self, effect_type: str, x: float, y: float,
                      target_x: float = None, target_y: float = None,
                      damage: int = 0, **kwargs) -> bool:
        """创建特效"""
        print(
            f"🎆 特效创建请求: 类型={effect_type}, 位置=({x:.1f}px, {y:.1f}px), 伤害={damage}")
        if target_x is not None and target_y is not None:
            print(f"   目标位置: ({target_x:.1f}px, {target_y:.1f}px)")

        # 根据特效类型获取配置
        color, base_duration, effect_speed_multiplier = self._get_effect_properties(
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
            size=self._get_effect_size(effect_type)
        )

        self.effects.append(effect)
        return True

    def set_speed_multiplier(self, multiplier: float):
        """设置特效播放速度倍数"""
        self.speed_multiplier = max(0.1, multiplier)  # 限制最小速度为0.1倍
        print(f"⚡ 特效播放速度设置为: {self.speed_multiplier}x")

    def get_speed_multiplier(self) -> float:
        """获取当前特效播放速度倍数"""
        return self.speed_multiplier

    def _load_effect_configs(self) -> Dict[str, Dict[str, Any]]:
        """加载特效配置，包含颜色、持续时间和速度倍数"""
        return {
            # 近战攻击特效 - 斩击类特效2倍速度播放
            'melee_slash': {
                'color': (255, 255, 255),    # 白色半圆弧
                'duration': 0.25,            # 基础持续时间0.25秒
                'speed_multiplier': 2.0,     # 斩击类特效2倍速度
                'size': 5
            },
            'melee_heavy': {
                'color': (255, 0, 0),        # 红色粗重半圆弧
                'duration': 0.4,             # 基础持续时间0.4秒
                'speed_multiplier': 2.0,     # 斩击类特效2倍速度
                'size': 8
            },
            'shadow_slash': {
                'color': (100, 0, 255),      # 紫色暗影
                'duration': 0.3,             # 基础持续时间0.3秒
                'speed_multiplier': 2.0,     # 斩击类特效2倍速度
                'size': 5
            },
            'divine_strike': {
                'color': (255, 215, 0),      # 金色明亮弧线
                'duration': 0.5,             # 基础持续时间0.5秒
                'speed_multiplier': 2.0,     # 斩击类特效2倍速度
                'size': 6
            },

            # 远程攻击特效 - 正常速度播放
            'arrow_shot': {
                'color': (200, 200, 200),    # 灰色箭矢
                'duration': 0.3,             # 基础持续时间0.3秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5
            },
            'precise_arrow': {
                'color': (255, 255, 0),      # 黄色精准
                'duration': 0.4,             # 基础持续时间0.4秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5
            },
            'tracking_arrow': {
                'color': (0, 255, 0),        # 绿色追踪
                'duration': 0.5,             # 基础持续时间0.5秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5
            },
            'fireball': {
                'color': (255, 0, 0),        # 红色火球
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 6
            },
            'chain_lightning': {
                'color': (0, 255, 255),      # 青色闪电
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 12
            },

            # 魔法攻击特效 - 正常速度播放
            'fire_breath': {
                'color': (255, 50, 0),       # 橙红色火焰
                'duration': 1.2,             # 基础持续时间1.2秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 10
            },
            'fire_splash': {
                'color': (255, 100, 0),      # 橙色溅射
                'duration': 0.6,             # 基础持续时间0.6秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5
            },
            'spine_storm': {
                'color': (150, 150, 150),    # 灰色骨刺
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 15
            },
            'acid_spray': {
                'color': (0, 255, 0),        # 绿色酸液
                'duration': 0.8,             # 基础持续时间0.8秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5
            },
            'charm_effect': {
                'color': (255, 0, 255),      # 紫色魅惑
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5
            },

            # 自然魔法特效 - 正常速度播放
            'nature_arrow': {
                'color': (100, 255, 100),    # 绿色自然
                'duration': 0.6,             # 基础持续时间0.6秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 5
            },
            'vine_entangle': {
                'color': (0, 150, 0),        # 深绿藤蔓
                'duration': 1.5,             # 基础持续时间1.5秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 8
            },

            # 其他特效 - 正常速度播放
            'healing_aura': {
                'color': (0, 255, 255),      # 青色治疗
                'duration': 1.0,             # 基础持续时间1.0秒
                'speed_multiplier': 1.0,     # 正常速度
                'size': 20
            }
        }

    def _get_effect_properties(self, effect_type: str) -> Tuple[Tuple[int, int, int], float, float]:
        """根据特效类型获取颜色、持续时间和速度倍数"""
        configs = self._load_effect_configs()
        config = configs.get(effect_type, {
            'color': (255, 255, 255),
            'duration': 1.0,
            'speed_multiplier': 1.0
        })
        return config['color'], config['duration'], config['speed_multiplier']

    def _get_effect_size(self, effect_type: str) -> int:
        """根据特效类型获取大小"""
        configs = self._load_effect_configs()
        config = configs.get(effect_type, {'size': 5})
        return config['size']

    def update(self, delta_time: float, targets: List = None):
        """更新特效"""
        current_time = time.time()

        # 移除过期的特效
        self.effects = [
            effect for effect in self.effects
            if current_time - effect.start_time < effect.duration
        ]

    def render(self, screen: pygame.Surface):
        """渲染特效"""
        current_time = time.time()

        for effect in self.effects:
            # 计算特效的生命周期进度 (0.0 到 1.0)
            elapsed = current_time - effect.start_time
            progress = min(elapsed / effect.duration, 1.0)

            # 根据进度计算透明度
            alpha = int(255 * (1.0 - progress))

            # 根据特效类型渲染不同的效果
            self._render_effect(screen, effect, progress, alpha)

        return screen

    def _render_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int):
        """渲染单个特效"""
        x, y = int(effect.x), int(effect.y)

        # 创建带透明度的颜色
        color_with_alpha = (*effect.color, alpha)

        if effect.effect_type in ['melee_slash', 'melee_heavy', 'shadow_slash', 'divine_strike']:
            # 近战攻击：斜劈曲线效果
            self._render_slash_effect(screen, effect, progress, alpha)

        elif effect.effect_type in ['arrow_shot', 'precise_arrow', 'tracking_arrow']:
            # 远程攻击：线条轨迹
            if effect.target_x is not None and effect.target_y is not None:
                target_x, target_y = int(effect.target_x), int(effect.target_y)
                # 绘制从起点到终点的线条
                pygame.draw.line(screen, effect.color, (x, y),
                                 (target_x, target_y), 3)

        elif effect.effect_type in ['fireball', 'chain_lightning']:
            # 魔法攻击：圆形效果
            size = int(effect.size * (1.0 + progress))
            pygame.draw.circle(screen, effect.color, (x, y), size)

        elif effect.effect_type in ['fire_breath', 'acid_spray']:
            # 范围攻击：扇形效果
            if effect.target_x is not None and effect.target_y is not None:
                target_x, target_y = int(effect.target_x), int(effect.target_y)
                # 绘制扇形区域
                angle = math.atan2(target_y - y, target_x - x)
                for i in range(5):
                    offset_angle = angle + (i - 2) * 0.2
                    end_x = x + math.cos(offset_angle) * 50
                    end_y = y + math.sin(offset_angle) * 50
                    pygame.draw.line(screen, effect.color,
                                     (x, y), (int(end_x), int(end_y)), 2)

        elif effect.effect_type == 'healing_aura':
            # 治疗光环：脉冲圆圈
            size = int(effect.size * (1.0 + math.sin(progress * 10) * 0.3))
            pygame.draw.circle(screen, effect.color, (x, y), size, 3)

        else:
            # 默认效果：简单圆圈
            size = int(effect.size * (1.0 + progress))
            pygame.draw.circle(screen, effect.color, (x, y), size)

        # 伤害数字显示已移除

    def _render_slash_effect(self, screen: pygame.Surface, effect: VisualEffect, progress: float, alpha: int):
        """渲染半圆弧斩击效果"""
        x, y = int(effect.x), int(effect.y)

        # 计算斩击角度和方向
        if effect.target_x is not None and effect.target_y is not None:
            # 如果有目标，朝目标方向斩击
            target_x, target_y = int(effect.target_x), int(effect.target_y)
            angle = math.atan2(target_y - y, target_x - x)
            # 使用特效自身的目标位置，避免全局变量冲突
            effect_target_x = target_x
            effect_target_y = target_y
        else:
            # 如果没有目标，默认向右下方斩击
            angle = math.pi / 4
            effect_target_x = x + 50
            effect_target_y = y + 50

        # 半圆弧的长度和宽度
        slash_length = int(effect.size * (1.5 + progress * 2.5))  # 长度随进度增长
        slash_width = max(3, int(effect.size * 0.4))  # 宽度

        # 计算半圆弧斩击轨迹的关键点
        points = self._calculate_slash_curve_points(
            x, y, angle, slash_length, slash_width, progress, effect_target_x, effect_target_y)

        # 根据特效类型选择不同的渲染方式
        if effect.effect_type == 'melee_slash':
            self._render_melee_slash(
                screen, points, effect.color, alpha, progress)
        elif effect.effect_type == 'melee_heavy':
            self._render_heavy_slash(
                screen, points, effect.color, alpha, progress)
        elif effect.effect_type == 'shadow_slash':
            self._render_shadow_slash(
                screen, points, effect.color, alpha, progress)
        elif effect.effect_type == 'divine_strike':
            self._render_divine_slash(
                screen, points, effect.color, alpha, progress)

    def _calculate_slash_curve_points(self, x: int, y: int, angle: float, length: int, width: int, progress: float, target_x: int, target_y: int) -> List[Tuple[int, int]]:
        """计算半圆弧斩击轨迹关键点"""
        points = []

        # 半圆弧斩击轨迹
        num_points = 12  # 增加点数以获得更平滑的弧线

        # 使用传入的目标位置确定斩击方向
        if target_x is not None and target_y is not None:
            # 计算斩击方向角度
            slash_angle = math.atan2(target_y - y, target_x - x)
        else:
            # 默认向右下方斩击
            slash_angle = math.pi / 4

        # 半圆弧的半径和起始角度
        radius = length
        start_angle = slash_angle - math.pi / 2  # 从左侧开始
        end_angle = slash_angle + math.pi / 2    # 到右侧结束

        for i in range(num_points + 1):
            t = i / num_points

            # 计算当前角度（半圆弧）
            current_angle = start_angle + t * (end_angle - start_angle)

            # 计算圆弧上的点
            arc_x = x + radius * math.cos(current_angle)
            arc_y = y + radius * math.sin(current_angle)

            # 添加动态效果 - 弧线随进度变化
            dynamic_factor = math.sin(progress * math.pi)  # 0到1再到0的变化

            # 弧线宽度随进度变化
            current_width = width * (1.0 + dynamic_factor * 0.5)

            # 添加垂直于弧线方向的偏移，形成剑刃宽度
            perp_angle = current_angle + math.pi / 2
            width_offset = (t - 0.5) * current_width  # 中心为0，两端有偏移

            offset_x = width_offset * math.cos(perp_angle)
            offset_y = width_offset * math.sin(perp_angle)

            # 添加轻微的随机抖动，让斩击更生动
            if i > 0 and i < num_points:
                jitter_strength = 2.0 * (1.0 - progress)  # 随进度减少抖动
                jitter_x = (math.sin(t * math.pi * 8 +
                            progress * 20) * jitter_strength)
                jitter_y = (math.cos(t * math.pi * 5 +
                            progress * 15) * jitter_strength)
                offset_x += jitter_x
                offset_y += jitter_y

            # 弧线长度随进度变化
            arc_progress = math.sin(progress * math.pi)  # 0到1再到0
            length_factor = 0.3 + 0.7 * arc_progress  # 30%到100%的长度变化

            final_x = int(arc_x + offset_x * length_factor)
            final_y = int(arc_y + offset_y * length_factor)

            points.append((final_x, final_y))

        return points

    def _render_melee_slash(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float):
        """渲染普通斩击效果 - 半圆弧轨迹"""
        if len(points) < 2:
            return

        # 绘制主剑刃轨迹 - 半圆弧
        for i in range(len(points) - 1):
            # 线条粗细从粗到细，中心最粗
            center_factor = 1.0 - abs(i / len(points) - 0.5) * 2  # 中心为1，两端为0
            thickness = max(1, int(6 * center_factor * (1.0 - progress * 0.3)))

            # 透明度渐变
            line_alpha = int(alpha * (1.0 - i / len(points)) * 0.8)

            if line_alpha > 0 and thickness > 0:
                pygame.draw.line(
                    screen, color, points[i], points[i + 1], thickness)

        # 添加半圆弧火花效果
        self._add_arc_spark_effects(
            screen, points, color, alpha, progress, num_sparks=4)

    def _render_heavy_slash(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float):
        """渲染重击效果 - 粗重的半圆弧"""
        if len(points) < 2:
            return

        # 绘制粗重的半圆弧剑刃轨迹
        for i in range(len(points) - 1):
            # 中心最粗，两端较细
            center_factor = 1.0 - abs(i / len(points) - 0.5) * 2
            thickness = max(
                2, int(12 * center_factor * (1.0 - progress * 0.2)))
            line_alpha = int(alpha * (1.0 - i / len(points)) * 0.9)

            if line_alpha > 0 and thickness > 0:
                pygame.draw.line(
                    screen, color, points[i], points[i + 1], thickness)

        # 添加重击火花和冲击波效果 - 更多火花
        self._add_arc_spark_effects(
            screen, points, color, alpha, progress, num_sparks=12)
        # 添加额外火花效果
        self._add_spark_effects(
            screen, points, color, alpha, progress, num_sparks=6)
        # 在半圆弧终点添加冲击波
        end_point = points[len(points) // 2]  # 使用弧线中点
        self._add_impact_wave(screen, end_point, color, alpha, progress)

    def _render_shadow_slash(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float):
        """渲染暗影斩击效果"""
        if len(points) < 2:
            return

        # 绘制暗影轨迹 - 多条平行线
        for offset in [-3, 0, 3]:
            shadow_points = []
            for x, y in points:
                shadow_points.append((x + offset, y + offset))

            for i in range(len(shadow_points) - 1):
                thickness = max(1, int(3 * (1.0 - i / len(shadow_points))))
                line_alpha = int(alpha * 0.6 * (1.0 - i / len(shadow_points)))

                if line_alpha > 0:
                    pygame.draw.line(
                        screen, color, shadow_points[i], shadow_points[i + 1], thickness)

        # 添加暗影粒子效果
        self._add_shadow_particles(screen, points, color, alpha, progress)

    def _render_divine_slash(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float):
        """渲染神圣斩击效果 - 金色明亮弧线"""
        if len(points) < 2:
            return

        # 绘制神圣轨迹 - 明亮的主线，中心最粗
        for i in range(len(points) - 1):
            # 中心最粗，两端较细
            center_factor = 1.0 - abs(i / len(points) - 0.5) * 2
            thickness = max(2, int(8 * center_factor * (1.0 - progress * 0.2)))
            line_alpha = int(alpha * (1.0 - i / len(points)) * 0.9)

            if line_alpha > 0 and thickness > 0:
                pygame.draw.line(
                    screen, color, points[i], points[i + 1], thickness)

        # 添加神圣光环效果
        self._add_divine_aura(screen, points, color, alpha, progress)
        # 添加金色粒子特效
        self._add_divine_particles(screen, points, color, alpha, progress)
        # 添加半圆弧火花效果
        self._add_arc_spark_effects(
            screen, points, color, alpha, progress, num_sparks=6)

    def _add_arc_spark_effects(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float, num_sparks: int = 3):
        """添加半圆弧火花效果"""
        import random

        for i in range(0, len(points), max(1, len(points) // num_sparks)):
            if i < len(points):
                x, y = points[i]

                # 计算该点在弧线上的切线方向
                if i > 0 and i < len(points) - 1:
                    # 使用前后点计算切线方向
                    dx = points[i + 1][0] - points[i - 1][0]
                    dy = points[i + 1][1] - points[i - 1][1]
                    length = math.sqrt(dx * dx + dy * dy)
                    if length > 0:
                        # 切线方向
                        tangent_x = dx / length
                        tangent_y = dy / length
                        # 垂直方向（向外）
                        perp_x = -tangent_y
                        perp_y = tangent_x
                    else:
                        perp_x, perp_y = 1, 0
                else:
                    perp_x, perp_y = 1, 0

                # 火花沿垂直方向散射
                for j in range(2):
                    spark_distance = random.randint(5, 15) * (1.0 - progress)
                    spark_x = x + perp_x * spark_distance + \
                        random.randint(-3, 3)
                    spark_y = y + perp_y * spark_distance + \
                        random.randint(-3, 3)
                    spark_alpha = int(alpha * 0.8 * (1.0 - progress))
                    if spark_alpha > 0:
                        pygame.draw.circle(
                            screen, color, (spark_x, spark_y), 1)

    def _add_spark_effects(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float, num_sparks: int = 3):
        """添加火花效果"""
        import random

        for i in range(0, len(points), max(1, len(points) // num_sparks)):
            if i < len(points):
                x, y = points[i]
                # 在轨迹点周围添加小火花
                for j in range(2):
                    spark_x = x + random.randint(-8, 8)
                    spark_y = y + random.randint(-8, 8)
                    spark_alpha = int(alpha * 0.7 * (1.0 - progress))
                    if spark_alpha > 0:
                        pygame.draw.circle(
                            screen, color, (spark_x, spark_y), 1)

    def _add_impact_wave(self, screen: pygame.Surface, center: Tuple[int, int], color: Tuple[int, int, int], alpha: int, progress: float):
        """添加冲击波效果"""
        x, y = center
        wave_radius = int(15 * progress)
        if wave_radius > 0:
            wave_alpha = int(alpha * 0.5 * (1.0 - progress))
            if wave_alpha > 0:
                pygame.draw.circle(screen, color, (x, y), wave_radius, 2)

    def _add_shadow_particles(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float):
        """添加暗影粒子效果"""
        import random

        for i in range(0, len(points), 2):
            if i < len(points):
                x, y = points[i]
                # 暗影粒子向上飘散
                for j in range(3):
                    particle_x = x + random.randint(-5, 5)
                    particle_y = y - int(progress * 20) + random.randint(-3, 3)
                    particle_alpha = int(alpha * 0.4 * (1.0 - progress))
                    if particle_alpha > 0:
                        pygame.draw.circle(
                            screen, color, (particle_x, particle_y), 1)

    def _add_divine_particles(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float):
        """添加金色粒子特效"""
        import random

        # 在弧线周围添加金色粒子
        for i in range(0, len(points), 2):
            if i < len(points):
                x, y = points[i]

                # 添加多个金色粒子
                for j in range(4):
                    # 粒子向各个方向飘散
                    angle = random.uniform(0, 2 * math.pi)
                    distance = random.randint(10, 25) * (1.0 - progress)

                    particle_x = x + math.cos(angle) * distance
                    particle_y = y + math.sin(angle) * distance

                    # 金色粒子大小和透明度
                    particle_size = random.randint(1, 3)
                    particle_alpha = int(alpha * 0.6 * (1.0 - progress))

                    if particle_alpha > 0:
                        # 绘制金色粒子
                        pygame.draw.circle(
                            screen, color,
                            (int(particle_x), int(particle_y)),
                            particle_size)

    def _add_divine_aura(self, screen: pygame.Surface, points: List[Tuple[int, int]], color: Tuple[int, int, int], alpha: int, progress: float):
        """添加神圣光环效果"""
        if len(points) > 0:
            # 在轨迹中点添加神圣光环
            mid_index = len(points) // 2
            x, y = points[mid_index]

            # 脉冲光环
            aura_radius = int(12 + math.sin(progress * 20) * 5)
            aura_alpha = int(alpha * 0.3 * (1.0 - progress))
            if aura_alpha > 0 and aura_radius > 0:
                pygame.draw.circle(screen, color, (x, y), aura_radius, 1)

    def get_performance_stats(self) -> Dict[str, int]:
        """获取性能统计"""
        return {
            "particles": len(self.effects),
            "projectiles": len([e for e in self.effects if 'arrow' in e.effect_type or 'fireball' in e.effect_type]),
            "area_effects": len([e for e in self.effects if e.effect_type in ['fire_breath', 'chain_lightning', 'healing_aura']]),
            "damage_numbers": len([e for e in self.effects if e.damage > 0])
        }

    def clear(self):
        """清空所有特效"""
        self.effects.clear()
