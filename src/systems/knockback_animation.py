#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
击退动画系统 - 提供击退效果的视觉反馈
"""

import math
import random
import pygame
from typing import List, Tuple, Optional, Any
from dataclasses import dataclass
from src.utils.logger import game_logger


@dataclass
class Particle:
    """粒子数据类"""
    x: float
    y: float
    velocity_x: float
    velocity_y: float
    color: Tuple[int, int, int]
    life_time: float
    max_life_time: float
    size: float = 2.0

    def update(self, delta_time: float) -> bool:
        """
        更新粒子

        Args:
            delta_time: 时间增量（秒）

        Returns:
            bool: 粒子是否还活着
        """
        self.x += self.velocity_x * delta_time
        self.y += self.velocity_y * delta_time
        self.life_time -= delta_time

        # 应用重力和阻力
        self.velocity_y += 100 * delta_time  # 重力
        self.velocity_x *= 0.98  # 阻力
        self.velocity_y *= 0.98

        return self.life_time > 0

    def get_alpha(self) -> int:
        """获取透明度"""
        if self.max_life_time <= 0:
            return 255
        alpha_ratio = self.life_time / self.max_life_time
        return int(255 * alpha_ratio)


@dataclass
class FlashEffect:
    """闪烁效果数据类"""
    duration: float
    elapsed_time: float = 0.0
    color: Tuple[int, int, int] = (255, 255, 255)
    intensity: float = 1.0

    def update(self, delta_time: float) -> bool:
        """
        更新闪烁效果

        Args:
            delta_time: 时间增量（秒）

        Returns:
            bool: 效果是否还活着
        """
        self.elapsed_time += delta_time

        # 计算闪烁强度（淡出）
        if self.duration > 0:
            progress = self.elapsed_time / self.duration
            self.intensity = max(0, 1.0 - progress)

        return self.elapsed_time < self.duration

    def get_alpha(self) -> int:
        """获取透明度"""
        return int(255 * self.intensity)


class ScreenShakeManager:
    """屏幕震动管理器"""

    def __init__(self):
        self.shake_intensity = 0.0
        self.shake_duration = 0.0
        self.shake_elapsed = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

    def shake(self, intensity: float, duration: float):
        """
        开始屏幕震动

        Args:
            intensity: 震动强度（0-1）
            duration: 震动持续时间（秒）
        """
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_duration = max(self.shake_duration, duration)
        self.shake_elapsed = 0.0

    def update(self, delta_time: float):
        """更新屏幕震动"""
        if self.shake_duration <= 0:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0
            return

        self.shake_elapsed += delta_time

        if self.shake_elapsed >= self.shake_duration:
            # 震动结束
            self.shake_intensity = 0.0
            self.shake_duration = 0.0
            self.shake_elapsed = 0.0
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0
        else:
            # 计算当前震动强度（衰减）
            progress = self.shake_elapsed / self.shake_duration
            current_intensity = self.shake_intensity * (1.0 - progress)

            # 生成随机震动偏移
            max_offset = current_intensity * 10  # 最大震动10像素
            self.shake_offset_x = random.uniform(-max_offset, max_offset)
            self.shake_offset_y = random.uniform(-max_offset, max_offset)

    def get_offset(self) -> Tuple[float, float]:
        """获取当前震动偏移"""
        return self.shake_offset_x, self.shake_offset_y


class KnockbackAnimation:
    """击退动画系统"""

    def __init__(self):
        self.particle_effects: List[Particle] = []
        # (unit, effect)
        self.flash_effects: List[Tuple[Any, FlashEffect]] = []
        self.screen_shake = ScreenShakeManager()

        # 音效管理器（可选）
        self.sound_manager = None

    def set_sound_manager(self, sound_manager):
        """设置音效管理器"""
        self.sound_manager = sound_manager

    def create_knockback_effect(self, unit: Any, direction: Tuple[float, float], distance: float):
        """
        创建击退视觉效果

        Args:
            unit: 被击退的单位
            direction: 击退方向
            distance: 击退距离
        """
        # 类型检查：确保distance是数值类型
        if isinstance(distance, (tuple, list)):
            game_logger.info(
                f"❌ 击退动画错误: distance类型错误 {type(distance)}, 值: {distance}")
            distance = 0.0 if not distance else float(distance[0])

        try:
            # 1. 创建击退粒子效果
            self.create_impact_particles(unit.x, unit.y, direction, distance)

            # 2. 屏幕震动效果
            shake_intensity = min(distance / 30.0, 1.0)  # 根据击退距离调整震动强度
            self.screen_shake.shake(shake_intensity, 0.2)

            # 3. 单位闪烁效果
            flash_effect = FlashEffect(duration=0.3, color=(255, 255, 255))
            self.flash_effects.append((unit, flash_effect))

            # 4. 播放音效
            if self.sound_manager:
                self.play_knockback_sound(unit, distance)
        except Exception as e:
            game_logger.info(
                f"❌ 击退动画内部错误: {e}, distance类型: {type(distance)}, 值: {distance}")

    def create_wall_collision_effect(self, unit: Any, collision_type: str, damage: int,
                                     collision_pos: Tuple[int, int]):
        """
        创建撞墙效果

        Args:
            unit: 撞墙的单位
            collision_type: 碰撞类型
            damage: 撞墙伤害
            collision_pos: 碰撞位置（瓦片坐标）
        """
        # 1. 创建撞墙粒子效果
        self.create_wall_impact_particles(
            unit.x, unit.y, collision_type, damage)

        # 2. 强烈的屏幕震动
        shake_intensity = min(damage / 10.0, 1.0)
        self.screen_shake.shake(shake_intensity, 0.4)

        # 3. 撞墙闪烁效果（红色）
        flash_color = self._get_collision_flash_color(collision_type)
        flash_effect = FlashEffect(duration=0.5, color=flash_color)
        self.flash_effects.append((unit, flash_effect))

        # 4. 播放撞墙音效
        if self.sound_manager:
            self.play_wall_collision_sound(collision_type, damage)

    def create_wall_impact_particles(self, x: float, y: float, collision_type: str, damage: int):
        """创建撞墙冲击粒子效果"""
        particle_count = min(int(damage * 2), 20)  # 根据伤害决定粒子数量

        # 根据碰撞类型选择粒子颜色
        color = self._get_collision_particle_color(collision_type)

        for i in range(particle_count):
            # 随机散射方向
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(40, 80)  # 撞墙粒子速度更快
            life_time = random.uniform(0.5, 1.2)  # 撞墙粒子持续更久

            particle = Particle(
                x=x + random.uniform(-8, 8),  # 更大的起始位置偏移
                y=y + random.uniform(-8, 8),
                velocity_x=math.cos(angle) * speed,
                velocity_y=math.sin(angle) * speed,
                color=color,
                life_time=life_time,
                max_life_time=life_time,
                size=random.uniform(2.0, 4.0)  # 撞墙粒子更大
            )

            self.particle_effects.append(particle)

    def _get_collision_flash_color(self, collision_type: str) -> Tuple[int, int, int]:
        """获取碰撞闪烁颜色"""
        colors = {
            "wall": (255, 100, 100),        # 红色 - 普通墙面
            "building": (255, 150, 100),    # 橙红色 - 建筑物
            "dungeon_heart": (150, 100, 255),  # 紫色 - 地牢之心
            "hero_base": (100, 150, 255),   # 蓝色 - 英雄基地
            "boundary": (255, 50, 50)       # 深红色 - 地图边界
        }
        return colors.get(collision_type, (255, 100, 100))

    def _get_collision_particle_color(self, collision_type: str) -> Tuple[int, int, int]:
        """获取碰撞粒子颜色"""
        colors = {
            "wall": (200, 200, 200),        # 灰色 - 石墙碎片
            "building": (139, 69, 19),      # 棕色 - 建筑材料
            "dungeon_heart": (128, 0, 128),  # 紫色 - 魔法能量
            "hero_base": (65, 105, 225),    # 蓝色 - 神圣能量
            "boundary": (255, 0, 0)         # 红色 - 边界能量
        }
        return colors.get(collision_type, (200, 200, 200))

    def play_wall_collision_sound(self, collision_type: str, damage: int):
        """
        播放撞墙音效

        Args:
            collision_type: 碰撞类型
            damage: 撞墙伤害
        """
        if not self.sound_manager:
            return

        # 根据碰撞类型选择音效
        sound_map = {
            "wall": "wall_impact.wav",
            "building": "building_impact.wav",
            "dungeon_heart": "magic_impact.wav",
            "hero_base": "holy_impact.wav",
            "boundary": "boundary_impact.wav"
        }

        sound = sound_map.get(collision_type, "wall_impact.wav")

        # 根据伤害调整音量
        volume = min(damage / 15.0, 1.0)

        try:
            self.sound_manager.play_sound(sound, volume=volume)
        except Exception as e:
            game_logger.info(f"播放撞墙音效失败: {e}")

    def create_impact_particles(self, x: float, y: float, direction: Tuple[float, float], distance: float):
        """创建冲击粒子效果"""
        particle_count = min(int(distance / 3), 12)  # 根据击退距离决定粒子数量

        for i in range(particle_count):
            # 在击退方向的基础上添加随机偏移
            base_angle = math.atan2(direction[1], direction[0])
            angle = base_angle + random.uniform(-0.8, 0.8)  # ±45度随机偏移

            speed = random.uniform(30, 60)  # 粒子速度
            life_time = random.uniform(0.3, 0.8)  # 粒子生命时间

            # 根据击退距离选择粒子颜色
            if distance > 30:
                color = (255, 100, 100)  # 强击退：红色
            elif distance > 20:
                color = (255, 200, 100)  # 中等击退：橙色
            else:
                color = (255, 255, 200)  # 轻微击退：黄色

            particle = Particle(
                x=x + random.uniform(-5, 5),  # 起始位置随机偏移
                y=y + random.uniform(-5, 5),
                velocity_x=math.cos(angle) * speed,
                velocity_y=math.sin(angle) * speed,
                color=color,
                life_time=life_time,
                max_life_time=life_time,
                size=random.uniform(1.5, 3.0)
            )

            self.particle_effects.append(particle)

    def play_knockback_sound(self, unit: Any, distance: float):
        """
        播放击退音效

        Args:
            unit: 被击退的单位
            distance: 击退距离
        """
        if not self.sound_manager:
            return

        # 根据单位体型和击退距离选择音效
        unit_size = getattr(unit, 'size', 15)
        # 类型检查：确保unit_size是数值类型
        if isinstance(unit_size, (tuple, list)):
            game_logger.info(
                f"❌ 击退音效错误: unit_size类型错误 {type(unit_size)}, 值: {unit_size}")
            unit_size = 15

        # 选择音效类型
        if distance >= 25:
            sound = "knockback_heavy.wav"  # 重击退
        elif distance >= 15:
            sound = "knockback_medium.wav"  # 中等击退
        else:
            sound = "knockback_light.wav"  # 轻击退

        # 根据击退距离调整音量
        volume = min(distance / 40.0, 1.0)

        try:
            self.sound_manager.play_sound(sound, volume=volume)
        except Exception as e:
            game_logger.info(f"播放击退音效失败: {e}")

    def update(self, delta_time: float):
        """更新所有动画效果"""
        # 更新粒子效果
        self.particle_effects = [
            p for p in self.particle_effects if p.update(delta_time)]

        # 更新闪烁效果
        active_flash_effects = []
        for unit, effect in self.flash_effects:
            if effect.update(delta_time):
                active_flash_effects.append((unit, effect))
        self.flash_effects = active_flash_effects

        # 更新屏幕震动
        self.screen_shake.update(delta_time)

    def render_particles(self, screen: pygame.Surface, camera_x: float = 0, camera_y: float = 0, ui_scale: float = 1.0):
        """
        渲染粒子效果

        Args:
            screen: pygame屏幕对象
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
            ui_scale: UI缩放倍数
        """
        for particle in self.particle_effects:
            # 应用UI缩放和相机偏移
            screen_x = int((particle.x - camera_x) * ui_scale)
            screen_y = int((particle.y - camera_y) * ui_scale)

            # 只渲染屏幕内的粒子
            if (0 <= screen_x <= screen.get_width() and
                    0 <= screen_y <= screen.get_height()):

                # 创建带透明度的颜色
                alpha = particle.get_alpha()
                if alpha > 0:
                    # 应用UI缩放到粒子大小
                    scaled_size = int(particle.size * ui_scale)
                    # 创建临时表面用于透明度渲染
                    temp_surface = pygame.Surface(
                        (scaled_size * 2, scaled_size * 2))
                    temp_surface.set_alpha(alpha)
                    temp_surface.fill(particle.color)

                    # 绘制粒子
                    screen.blit(temp_surface,
                                (screen_x - scaled_size, screen_y - scaled_size))

    def render_flash_effects(self, screen: pygame.Surface, camera_x: float = 0, camera_y: float = 0, ui_scale: float = 1.0):
        """
        渲染闪烁效果

        Args:
            screen: pygame屏幕对象
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
            ui_scale: UI缩放倍数
        """
        for unit, effect in self.flash_effects:
            if not hasattr(unit, 'x') or not hasattr(unit, 'y'):
                continue

            # 应用UI缩放和相机偏移
            screen_x = int((unit.x - camera_x) * ui_scale)
            screen_y = int((unit.y - camera_y) * ui_scale)

            # 只渲染屏幕内的效果
            if (0 <= screen_x <= screen.get_width() and
                    0 <= screen_y <= screen.get_height()):

                alpha = effect.get_alpha()
                if alpha > 0:
                    # 获取单位大小并应用UI缩放
                    unit_size = getattr(unit, 'size', 15)
                    # 类型检查：确保unit_size是数值类型
                    if isinstance(unit_size, (tuple, list)):
                        game_logger.info(
                            f"❌ 击退闪烁效果错误: unit_size类型错误 {type(unit_size)}, 值: {unit_size}")
                        unit_size = 15
                    scaled_unit_size = int(unit_size * ui_scale)

                    # 创建圆形闪烁效果
                    flash_radius = int(scaled_unit_size * 0.75)  # 圆形半径，比单位稍大

                    # 创建带透明度的圆形闪烁效果
                    # 使用临时表面来实现透明度
                    temp_surface = pygame.Surface(
                        (flash_radius * 2, flash_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(
                        temp_surface, (*effect.color, alpha), (flash_radius, flash_radius), flash_radius)

                    # 绘制圆形闪烁效果
                    screen.blit(temp_surface, (screen_x -
                                flash_radius, screen_y - flash_radius))

    def render(self, screen: pygame.Surface, camera_x: float = 0, camera_y: float = 0, ui_scale: float = 1.0):
        """
        渲染所有击退动画效果

        Args:
            screen: pygame屏幕对象
            camera_x: 相机X偏移
            camera_y: 相机Y偏移
            ui_scale: UI缩放倍数
        """
        # 应用屏幕震动（修改相机位置）
        shake_x, shake_y = self.screen_shake.get_offset()
        adjusted_camera_x = camera_x + shake_x
        adjusted_camera_y = camera_y + shake_y

        # 渲染粒子效果
        self.render_particles(screen, adjusted_camera_x,
                              adjusted_camera_y, ui_scale)

        # 渲染闪烁效果
        self.render_flash_effects(
            screen, adjusted_camera_x, adjusted_camera_y, ui_scale)

    def clear_all_effects(self):
        """清除所有动画效果"""
        self.particle_effects.clear()
        self.flash_effects.clear()
        self.screen_shake.shake_intensity = 0.0
        self.screen_shake.shake_duration = 0.0

    def get_effect_count(self) -> dict:
        """获取当前效果数量统计"""
        return {
            'particles': len(self.particle_effects),
            'flash_effects': len(self.flash_effects),
            'screen_shake_active': self.screen_shake.shake_duration > 0
        }


class KnockbackSoundManager:
    """击退音效管理器"""

    def __init__(self):
        self.sound_enabled = True
        self.volume = 1.0

        # 预加载音效（如果pygame.mixer可用）
        self.sounds = {}
        try:
            import pygame.mixer
            if pygame.mixer.get_init():
                self._load_sounds()
        except:
            game_logger.info("音效系统不可用，将跳过音效播放")

    def _load_sounds(self):
        """预加载音效文件"""
        sound_files = {
            "knockback_heavy.wav": "sounds/knockback_heavy.wav",
            "knockback_medium.wav": "sounds/knockback_medium.wav",
            "knockback_light.wav": "sounds/knockback_light.wav"
        }

        for sound_name, file_path in sound_files.items():
            try:
                import pygame.mixer
                self.sounds[sound_name] = pygame.mixer.Sound(file_path)
            except:
                # 如果音效文件不存在，创建空的占位符
                self.sounds[sound_name] = None

    def play_sound(self, sound_name: str, volume: float = 1.0):
        """
        播放音效

        Args:
            sound_name: 音效名称
            volume: 音量（0-1）
        """
        if not self.sound_enabled:
            return

        if sound_name in self.sounds and self.sounds[sound_name]:
            try:
                sound = self.sounds[sound_name]
                sound.set_volume(volume * self.volume)
                sound.play()
            except Exception as e:
                game_logger.info(f"播放音效 {sound_name} 失败: {e}")

    def set_volume(self, volume: float):
        """设置总音量"""
        self.volume = max(0.0, min(1.0, volume))

    def enable_sound(self, enabled: bool):
        """启用/禁用音效"""
        self.sound_enabled = enabled
