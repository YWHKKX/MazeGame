#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI组件基类
提供通用的UI绘制方法和样式支持
"""

import pygame
import time
from typing import Tuple, Optional, Dict, Any
from src.core.ui_design import (
    Colors, FontSizes, Spacing, BorderRadius, UIStyles, Animations,
    create_rounded_rect_surface, create_gradient_surface, draw_text_with_shadow
)
from src.managers.font_manager import UnifiedFontManager


class BaseUI:
    """UI组件基类"""

    def __init__(self, font_manager: UnifiedFontManager = None):
        self.font_manager = font_manager or UnifiedFontManager()
        self.animations = {}  # 存储动画状态

    def draw_panel(self, surface: pygame.Surface, rect: pygame.Rect,
                   style: Dict[str, Any] = None) -> pygame.Surface:
        """绘制面板"""
        if style is None:
            style = UIStyles.PANEL

        # 创建圆角矩形
        panel_surface = create_rounded_rect_surface(
            rect.width, rect.height,
            style.get('border_radius', BorderRadius.LG),
            style.get('bg_color', Colors.DARK_SURFACE)
        )

        # 绘制边框
        if style.get('border_width', 0) > 0:
            border_color = style.get('border_color', Colors.GRAY_600)
            border_width = style.get('border_width', 2)

            # 创建边框表面
            border_surface = create_rounded_rect_surface(
                rect.width, rect.height,
                style.get('border_radius', BorderRadius.LG),
                border_color
            )

            # 创建内部透明区域
            inner_surface = create_rounded_rect_surface(
                rect.width - border_width * 2,
                rect.height - border_width * 2,
                max(0, style.get('border_radius', BorderRadius.LG) - border_width),
                Colors.TRANSPARENT
            )

            # 合并边框
            border_surface.blit(inner_surface, (border_width, border_width))
            surface.blit(border_surface, rect.topleft)

        # 绘制主体
        surface.blit(panel_surface, rect.topleft)

        return panel_surface

    def draw_card(self, surface: pygame.Surface, rect: pygame.Rect,
                  style: Dict[str, Any] = None, hover: bool = False) -> pygame.Surface:
        """绘制卡片"""
        if style is None:
            style = UIStyles.CARD.copy()

        # 悬停效果
        if hover:
            style['bg_color'] = Colors.DARK_HOVER

        return self.draw_panel(surface, rect, style)

    def draw_button(self, surface: pygame.Surface, rect: pygame.Rect,
                    text: str, style: Dict[str, Any] = None,
                    hover: bool = False, pressed: bool = False) -> pygame.Rect:
        """绘制按钮"""
        if style is None:
            style = UIStyles.BUTTON_PRIMARY

        # 按钮状态颜色
        bg_color = style.get('bg_color', Colors.PRIMARY)
        if hover and not pressed:
            bg_color = style.get('bg_hover', Colors.PRIMARY_DARK)
        elif pressed:
            # 按下时稍微暗一些
            r, g, b = bg_color
            bg_color = (max(0, r-20), max(0, g-20), max(0, b-20))

        # 创建按钮表面
        button_style = style.copy()
        button_style['bg_color'] = bg_color

        button_surface = create_rounded_rect_surface(
            rect.width, rect.height,
            style.get('border_radius', BorderRadius.MD),
            bg_color
        )

        surface.blit(button_surface, rect.topleft)

        # 绘制文字 - 分离emoji和中文进行渲染
        font_size = style.get('font_size', FontSizes.NORMAL)
        text_color = style.get('text_color', Colors.WHITE)

        # 性能优化: 添加按钮文本渲染缓存
        if not hasattr(self, '_button_cache'):
            self._button_cache = {}

        cache_key = (text, font_size, text_color, pressed)

        if cache_key in self._button_cache:
            # 使用缓存的渲染结果
            cached_surface, cached_rect_offset = self._button_cache[cache_key]
            final_rect = cached_surface.get_rect(center=rect.center)
            if pressed:
                final_rect.y += 1
            surface.blit(cached_surface, final_rect)
            return final_rect

        # 分离emoji和文本
        emoji_part, text_part = self._separate_emoji_and_text(text)

        if emoji_part and text_part:
            # 有emoji和文本，需要分别渲染
            emoji_font = self.font_manager.get_emoji_font(font_size)
            text_font = self.font_manager.get_font(font_size)

            # 渲染emoji和文本
            emoji_surface = self.font_manager.safe_render(
                emoji_font, emoji_part, text_color)
            text_surface = self.font_manager.safe_render(
                text_font, text_part, text_color)

            # 计算总宽度和位置
            total_width = emoji_surface.get_width() + text_surface.get_width() + 4  # 4px间距
            start_x = rect.centerx - total_width // 2
            center_y = rect.centery

            # 按下时稍微向下移动
            if pressed:
                center_y += 1

            # 绘制emoji
            emoji_rect = emoji_surface.get_rect(
                left=start_x,
                centery=center_y
            )
            surface.blit(emoji_surface, emoji_rect)

            # 绘制文本（在emoji右侧）
            text_rect = text_surface.get_rect(
                left=start_x + emoji_surface.get_width() + 4,
                centery=center_y
            )
            surface.blit(text_surface, text_rect)

            # 返回整体区域
            return pygame.Rect(start_x, min(emoji_rect.top, text_rect.top),
                               total_width, max(emoji_rect.height, text_rect.height))
        else:
            # 只有文本或只有emoji，使用标准渲染
            font = self.font_manager.get_font(font_size)
            text_surface = self.font_manager.safe_render(
                font, text, text_color)
            text_rect = text_surface.get_rect(center=rect.center)

            # 按下时文字稍微向下移动
            if pressed:
                text_rect.y += 1

            surface.blit(text_surface, text_rect)

        return text_rect

    def _separate_emoji_and_text(self, text: str) -> tuple[str, str]:
        """分离emoji和普通文本

        Returns:
            tuple: (emoji_part, text_part)
        """
        import re

        # Unicode emoji范围（简化版本，涵盖常用emoji）
        emoji_pattern = re.compile(
            r'[\U0001F300-\U0001F9FF]|'  # 各种符号和象形文字
            r'[\U0001F600-\U0001F64F]|'  # 表情符号
            r'[\U0001F680-\U0001F6FF]|'  # 交通和地图符号
            r'[\U0001F1E0-\U0001F1FF]|'  # 地区指示符号
            r'[\U00002600-\U000027BF]|'  # 杂项符号
            r'[\U0000FE00-\U0000FE0F]|'  # 变体选择器
            r'[\U00002190-\U000021FF]|'  # 箭头
            r'[\U00002700-\U000027BF]|'  # 装饰符号
            r'[\U0001F900-\U0001F9FF]|'  # 补充符号和象形文字
            r'[⚔️⚡💖💰🏰🛡️👹🔧🎯💔↩️🎆📋📝📍✅❌💀🛑💚⛏️📤🎒⚠️💥🔊🎨🔍🧪🎉🎮🎯📚📊🔤✨🏗️💖🏰🛡️👹📷🔧🎮]'
        )

        # 找到所有emoji
        emojis = emoji_pattern.findall(text)
        emoji_part = ''.join(emojis)

        # 移除emoji，得到纯文本
        text_part = emoji_pattern.sub('', text).strip()

        return emoji_part, text_part

    def draw_input_field(self, surface: pygame.Surface, rect: pygame.Rect,
                         text: str, placeholder: str = "", focused: bool = False,
                         style: Dict[str, Any] = None) -> pygame.Rect:
        """绘制输入框"""
        if style is None:
            style = UIStyles.INPUT

        # 背景
        bg_surface = create_rounded_rect_surface(
            rect.width, rect.height,
            style.get('border_radius', BorderRadius.SM),
            style.get('bg_color', Colors.DARK_BG)
        )
        surface.blit(bg_surface, rect.topleft)

        # 边框
        border_color = style.get('border_focus', Colors.PRIMARY) if focused else style.get(
            'border_color', Colors.GRAY_600)
        border_width = style.get('border_width', 2)

        pygame.draw.rect(surface, border_color, rect, border_width,
                         style.get('border_radius', BorderRadius.SM))

        # 文字
        padding_x = style.get('padding_x', Spacing.MD)
        padding_y = style.get('padding_y', Spacing.SM)

        font = self.font_manager.get_font(FontSizes.NORMAL)

        if text:
            text_color = style.get('text_color', Colors.WHITE)
            text_surface = self.font_manager.safe_render(
                font, text, text_color)
        elif placeholder:
            text_color = style.get('placeholder_color', Colors.GRAY_400)
            text_surface = self.font_manager.safe_render(
                font, placeholder, text_color)
        else:
            text_surface = None

        if text_surface:
            text_rect = pygame.Rect(
                rect.x + padding_x, rect.y + padding_y,
                rect.width - padding_x * 2, rect.height - padding_y * 2
            )
            # 裁剪文字到输入框内
            text_pos = (text_rect.x, text_rect.centery -
                        text_surface.get_height() // 2)
            surface.blit(text_surface, text_pos,
                         (0, 0, min(text_surface.get_width(), text_rect.width), text_surface.get_height()))

        return rect

    def draw_progress_bar(self, surface: pygame.Surface, rect: pygame.Rect,
                          progress: float, style: Dict[str, Any] = None) -> pygame.Rect:
        """绘制进度条"""
        if style is None:
            style = {
                'bg_color': Colors.GRAY_700,
                'fill_color': Colors.PRIMARY,
                'border_radius': BorderRadius.SM
            }

        # 限制进度值
        progress = max(0.0, min(1.0, progress))

        # 背景
        bg_surface = create_rounded_rect_surface(
            rect.width, rect.height,
            style.get('border_radius', BorderRadius.SM),
            style.get('bg_color', Colors.GRAY_700)
        )
        surface.blit(bg_surface, rect.topleft)

        # 填充
        if progress > 0:
            fill_width = int(rect.width * progress)
            if fill_width > 0:
                fill_surface = create_rounded_rect_surface(
                    fill_width, rect.height,
                    style.get('border_radius', BorderRadius.SM),
                    style.get('fill_color', Colors.PRIMARY)
                )
                surface.blit(fill_surface, rect.topleft)

        return rect

    def draw_tooltip(self, surface: pygame.Surface, pos: Tuple[int, int],
                     text: str, max_width: int = 200) -> pygame.Rect:
        """绘制工具提示"""
        font = self.font_manager.get_font(FontSizes.SMALL)

        # 计算文字尺寸
        lines = self._wrap_text(text, font, max_width)
        line_height = font.get_height()

        tooltip_width = min(max_width, max(
            font.size(line)[0] for line in lines)) + Spacing.MD * 2
        tooltip_height = len(lines) * line_height + Spacing.MD * 2

        # 调整位置避免超出屏幕
        x, y = pos
        screen_width = surface.get_width()
        screen_height = surface.get_height()

        if x + tooltip_width > screen_width:
            x = screen_width - tooltip_width - Spacing.SM
        if y + tooltip_height > screen_height:
            y = y - tooltip_height - Spacing.SM

        tooltip_rect = pygame.Rect(x, y, tooltip_width, tooltip_height)

        # 绘制背景
        tooltip_surface = create_rounded_rect_surface(
            tooltip_width, tooltip_height,
            BorderRadius.SM,
            Colors.DARK_SURFACE
        )

        # 绘制边框
        pygame.draw.rect(surface, Colors.GRAY_600,
                         tooltip_rect, 1, BorderRadius.SM)
        surface.blit(tooltip_surface, tooltip_rect.topleft)

        # 绘制文字
        text_y = y + Spacing.MD
        for line in lines:
            text_surface = self.font_manager.safe_render(
                font, line, Colors.WHITE)
            surface.blit(text_surface, (x + Spacing.MD, text_y))
            text_y += line_height

        return tooltip_rect

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int):
        """文字换行"""
        words = text.split(' ')
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def start_animation(self, name: str, duration: int, start_value: float = 0.0, end_value: float = 1.0):
        """开始动画"""
        self.animations[name] = {
            'start_time': time.time() * 1000,
            'duration': duration,
            'start_value': start_value,
            'end_value': end_value
        }

    def get_animation_value(self, name: str, easing_func=None) -> float:
        """获取动画当前值"""
        if name not in self.animations:
            return 0.0

        anim = self.animations[name]
        current_time = time.time() * 1000
        elapsed = current_time - anim['start_time']

        if elapsed >= anim['duration']:
            # 动画结束
            del self.animations[name]
            return anim['end_value']

        # 计算进度
        progress = elapsed / anim['duration']

        # 应用缓动函数
        if easing_func:
            progress = easing_func(progress)

        # 计算当前值
        return anim['start_value'] + (anim['end_value'] - anim['start_value']) * progress

    def is_animating(self, name: str) -> bool:
        """检查动画是否在进行"""
        return name in self.animations
