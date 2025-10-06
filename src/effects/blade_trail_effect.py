"""
刀刃拖痕特效系统
实现刀刃旋转时产生的白色刀光拖痕效果
"""

import pygame
import math
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass
from src.utils.logger import game_logger


@dataclass
class TrailSegment:
    """拖痕段数据类"""
    x: float
    y: float
    alpha: float
    timestamp: float
    angle: float  # 该段对应的角度


class BladeTrailEffect:
    """刀刃拖痕特效类"""

    def __init__(self, center_x: float, center_y: float, radius: float,
                 duration: float = 0.8, rotation_speed: float = 1.5):
        """
        初始化刀刃拖痕特效

        Args:
            center_x: 旋转中心X坐标
            center_y: 旋转中心Y坐标
            radius: 旋转半径
            duration: 特效持续时间（秒）
            rotation_speed: 旋转速度倍数（1.0 = 一圈，1.25 = 一圈多一点）
        """
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
        self.duration = duration
        self.rotation_speed = rotation_speed

        self.start_time = time.time()
        self.trail_segments: List[TrailSegment] = []
        self.is_active = True

        # 拖痕参数
        self.max_segments = 30  # 最大拖痕段数（减少以缩小显示效果）
        self.segment_lifetime = 0.2  # 每个拖痕段的生命周期（秒）（缩短以缩小显示效果）
        self.alpha_decay_rate = 0.03  # 透明度衰减率（加快衰减）
        self.line_width = 2  # 拖痕线条宽度（减小以缩小显示效果）

        # 颜色设置
        self.color = (255, 255, 255)  # 白色刀光
        self.glow_color = (255, 255, 200)  # 发光边缘颜色

        game_logger.info(
            f"🗡️ 刀刃拖痕特效创建 - 中心:({center_x:.1f},{center_y:.1f}), 半径:{radius:.1f}")

    def update(self, delta_time: float) -> bool:
        """
        更新拖痕特效

        Args:
            delta_time: 时间增量（秒）

        Returns:
            bool: 特效是否仍然活跃
        """
        if not self.is_active:
            return False

        current_time = time.time()
        elapsed = current_time - self.start_time

        # 检查特效是否结束
        if elapsed >= self.duration:
            self.is_active = False
            return False

        # 计算当前旋转角度（一圈多一点）
        total_rotation = 2 * math.pi * self.rotation_speed
        current_angle = (elapsed / self.duration) * total_rotation

        # 计算当前刀刃位置
        blade_x = self.center_x + math.cos(current_angle) * self.radius
        blade_y = self.center_y + math.sin(current_angle) * self.radius

        # 添加新的拖痕段
        new_segment = TrailSegment(
            x=blade_x,
            y=blade_y,
            alpha=1.0,
            timestamp=current_time,
            angle=current_angle
        )
        self.trail_segments.append(new_segment)

        # 更新现有拖痕段的透明度
        for segment in self.trail_segments:
            age = current_time - segment.timestamp
            segment.alpha = max(0.0, 1.0 - (age / self.segment_lifetime))

        # 移除过期的拖痕段
        self.trail_segments = [
            segment for segment in self.trail_segments
            if segment.alpha > 0.0
        ]

        # 限制拖痕段数量
        if len(self.trail_segments) > self.max_segments:
            self.trail_segments = self.trail_segments[-self.max_segments:]

        return True

    def render(self, screen: pygame.Surface, ui_scale: float = 1.0,
               camera_x: float = 0, camera_y: float = 0):
        """
        渲染拖痕特效

        Args:
            screen: 渲染表面
            ui_scale: UI缩放倍数
            camera_x: 相机X坐标
            camera_y: 相机Y坐标
        """
        if not self.trail_segments:
            return

        # 将世界坐标转换为屏幕坐标
        def world_to_screen(wx: float, wy: float) -> Tuple[int, int]:
            return (
                int((wx - camera_x) * ui_scale),
                int((wy - camera_y) * ui_scale)
            )

        # 按时间顺序排序拖痕段
        sorted_segments = sorted(
            self.trail_segments, key=lambda s: s.timestamp)

        if len(sorted_segments) < 2:
            return

        # 绘制拖痕线条
        points = []
        for segment in sorted_segments:
            screen_x, screen_y = world_to_screen(segment.x, segment.y)
            points.append((screen_x, screen_y, segment.alpha))

        # 绘制连续的拖痕线条
        for i in range(len(points) - 1):
            x1, y1, alpha1 = points[i]
            x2, y2, alpha2 = points[i + 1]

            # 计算平均透明度
            avg_alpha = (alpha1 + alpha2) / 2
            if avg_alpha <= 0:
                continue

            # 创建带透明度的颜色
            color_with_alpha = (*self.color, int(255 * avg_alpha))
            glow_color_with_alpha = (
                *self.glow_color, int(255 * avg_alpha * 0.5))

            # 绘制发光边缘（更粗的线条）
            line_width = int(self.line_width * ui_scale)
            glow_width = line_width + 2

            # 绘制发光边缘
            pygame.draw.line(screen, glow_color_with_alpha,
                             (x1, y1), (x2, y2), glow_width)

            # 绘制主线条
            pygame.draw.line(screen, color_with_alpha,
                             (x1, y1), (x2, y2), line_width)

        # 绘制当前刀刃位置的高亮点
        if sorted_segments:
            current_segment = sorted_segments[-1]
            screen_x, screen_y = world_to_screen(
                current_segment.x, current_segment.y)

            # 绘制刀刃高亮点
            highlight_radius = int(4 * ui_scale)
            pygame.draw.circle(screen, self.color,
                               (screen_x, screen_y), highlight_radius)
            pygame.draw.circle(screen, self.glow_color,
                               (screen_x, screen_y), highlight_radius + 2, 2)

    def get_center_position(self) -> Tuple[float, float]:
        """获取特效中心位置"""
        return (self.center_x, self.center_y)

    def get_radius(self) -> float:
        """获取特效半径"""
        return self.radius

    def is_effect_active(self) -> bool:
        """检查特效是否活跃"""
        return self.is_active


class WhirlwindSlashEffect:
    """旋风斩特效管理器"""

    def __init__(self):
        self.active_effects: List[BladeTrailEffect] = []
        self.max_concurrent_effects = 3  # 最大同时存在的特效数量

    def create_whirlwind_effect(self, center_x: float, center_y: float,
                                radius: float = 80.0, duration: float = 1.2) -> BladeTrailEffect:
        """
        创建旋风斩特效

        Args:
            center_x: 旋转中心X坐标
            center_y: 旋转中心Y坐标
            radius: 旋转半径
            duration: 特效持续时间

        Returns:
            BladeTrailEffect: 创建的拖痕特效对象
        """
        # 限制同时存在的特效数量
        if len(self.active_effects) >= self.max_concurrent_effects:
            # 移除最老的特效
            oldest_effect = min(self.active_effects,
                                key=lambda e: e.start_time)
            self.active_effects.remove(oldest_effect)

        effect = BladeTrailEffect(center_x, center_y, radius, duration)
        self.active_effects.append(effect)

        game_logger.info(
            f"🌪️ 旋风斩特效创建 - 位置:({center_x:.1f},{center_y:.1f}), 半径:{radius:.1f}")
        return effect

    def update_all(self, delta_time: float):
        """更新所有活跃的特效"""
        # 更新特效并移除已结束的特效
        self.active_effects = [
            effect for effect in self.active_effects
            if effect.update(delta_time)
        ]

    def render_all(self, screen: pygame.Surface, ui_scale: float = 1.0,
                   camera_x: float = 0, camera_y: float = 0):
        """渲染所有活跃的特效"""
        for effect in self.active_effects:
            effect.render(screen, ui_scale, camera_x, camera_y)

    def clear_all(self):
        """清空所有特效"""
        self.active_effects.clear()
        game_logger.info("🗡️ 刀刃拖痕特效系统已清空")

    def get_active_count(self) -> int:
        """获取当前活跃特效数量"""
        return len(self.active_effects)

    def get_performance_stats(self) -> dict:
        """获取性能统计"""
        return {
            "active_effects": len(self.active_effects),
            "total_segments": sum(len(effect.trail_segments) for effect in self.active_effects)
        }
