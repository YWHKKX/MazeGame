#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI设计常量和样式配置
统一管理所有UI组件的视觉样式
"""

# ===== 颜色配置 =====


class Colors:
    """颜色常量"""

    # 基础色调
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    TRANSPARENT = (0, 0, 0, 0)

    # 深色主题
    DARK_BG = (18, 18, 18)          # 深色背景
    DARK_SURFACE = (28, 28, 28)     # 深色表面
    DARK_CARD = (35, 35, 35)        # 卡片背景
    DARK_HOVER = (45, 45, 45)       # 悬停状态

    # 中性色
    GRAY_100 = (245, 245, 245)
    GRAY_200 = (229, 229, 229)
    GRAY_300 = (209, 213, 219)
    GRAY_400 = (156, 163, 175)
    GRAY_500 = (107, 114, 128)
    GRAY_600 = (75, 85, 99)
    GRAY_700 = (55, 65, 81)
    GRAY_800 = (31, 41, 55)
    GRAY_900 = (17, 24, 39)

    # 主题色
    PRIMARY = (59, 130, 246)        # 蓝色主题
    PRIMARY_DARK = (37, 99, 235)
    PRIMARY_LIGHT = (147, 197, 253)

    # 功能色
    SUCCESS = (34, 197, 94)         # 成功绿色
    WARNING = (245, 158, 11)        # 警告黄色
    ERROR = (239, 68, 68)           # 错误红色
    INFO = (59, 130, 246)           # 信息蓝色

    # 游戏专用色
    GOLD = (255, 215, 0)            # 金色
    MANA = (138, 43, 226)           # 法力紫色
    HEALTH = (220, 38, 127)         # 生命红色
    ENERGY = (34, 197, 94)          # 能量绿色

    # 半透明遮罩
    OVERLAY_LIGHT = (0, 0, 0, 100)
    OVERLAY_MEDIUM = (0, 0, 0, 150)
    OVERLAY_DARK = (0, 0, 0, 200)


class FontSizes:
    """字体大小常量"""

    # 标准字体大小
    TINY = 12
    SMALL = 14
    NORMAL = 16
    MEDIUM = 18
    LARGE = 20
    XL = 24
    XXL = 28
    HUGE = 32

    # 标题字体大小
    H1 = 48
    H2 = 36
    H3 = 28
    H4 = 24
    H5 = 20
    H6 = 18


class Spacing:
    """间距常量"""

    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24
    XXXL = 32


class BorderRadius:
    """圆角半径常量"""

    NONE = 0
    SM = 4
    MD = 6
    LG = 8
    XL = 12
    XXL = 16
    FULL = 999


class Shadows:
    """阴影效果"""

    @staticmethod
    def get_shadow_surface(width, height, radius=8, alpha=50):
        """创建阴影表面"""
        import pygame
        shadow = pygame.Surface(
            (width + radius * 2, height + radius * 2), pygame.SRCALPHA)
        # 简单的阴影实现
        for i in range(radius):
            alpha_val = alpha * (radius - i) // radius
            pygame.draw.rect(shadow, (*Colors.BLACK, alpha_val),
                             (i, i, width + (radius - i) * 2, height + (radius - i) * 2))
        return shadow


class UIStyles:
    """UI组件样式配置"""

    # 面板样式
    PANEL = {
        'bg_color': Colors.DARK_SURFACE,
        'border_color': Colors.GRAY_600,
        'border_width': 2,
        'border_radius': BorderRadius.LG,
        'padding': Spacing.LG,
        'shadow': True
    }

    # 卡片样式
    CARD = {
        'bg_color': Colors.DARK_CARD,
        'border_color': Colors.GRAY_700,
        'border_width': 1,
        'border_radius': BorderRadius.MD,
        'padding': Spacing.MD,
        'shadow': True
    }

    # 按钮样式
    BUTTON_PRIMARY = {
        'bg_color': Colors.PRIMARY,
        'bg_hover': Colors.PRIMARY_DARK,
        'text_color': Colors.WHITE,
        'border_radius': BorderRadius.MD,
        'padding_x': Spacing.LG,
        'padding_y': Spacing.SM,
        'font_size': FontSizes.NORMAL
    }

    BUTTON_SECONDARY = {
        'bg_color': Colors.GRAY_600,
        'bg_hover': Colors.GRAY_500,
        'text_color': Colors.WHITE,
        'border_radius': BorderRadius.MD,
        'padding_x': Spacing.LG,
        'padding_y': Spacing.SM,
        'font_size': FontSizes.NORMAL
    }

    BUTTON_DISABLED = {
        'bg_color': Colors.GRAY_800,
        'bg_hover': Colors.GRAY_800,
        'text_color': Colors.GRAY_500,
        'border_radius': BorderRadius.MD,
        'padding_x': Spacing.LG,
        'padding_y': Spacing.SM,
        'font_size': FontSizes.NORMAL
    }

    # 面板变体样式
    PANEL_DARK = {
        'bg_color': Colors.DARK_SURFACE,
        'border_color': Colors.GRAY_600,
        'border_width': 2,
        'border_radius': BorderRadius.LG,
        'padding': Spacing.LG,
        'shadow': True
    }

    PANEL_MODAL = {
        'bg_color': Colors.DARK_CARD,
        'border_color': Colors.PRIMARY,
        'border_width': 2,
        'border_radius': BorderRadius.XL,
        'padding': Spacing.XL,
        'shadow': True
    }

    # 卡片变体样式
    CARD_HEADER = {
        'bg_color': Colors.GRAY_700,
        'border_color': Colors.GRAY_600,
        'border_width': 1,
        'border_radius': BorderRadius.MD,
        'padding': Spacing.MD,
        'shadow': False
    }

    CARD_HOVER = {
        'bg_color': Colors.DARK_HOVER,
        'border_color': Colors.PRIMARY,
        'border_width': 2,
        'border_radius': BorderRadius.MD,
        'padding': Spacing.MD,
        'shadow': True
    }

    CARD_SUBTLE = {
        'bg_color': Colors.GRAY_800,
        'border_color': Colors.GRAY_700,
        'border_width': 1,
        'border_radius': BorderRadius.SM,
        'padding': Spacing.SM,
        'shadow': False
    }

    # 输入框样式
    INPUT = {
        'bg_color': Colors.DARK_BG,
        'border_color': Colors.GRAY_600,
        'border_focus': Colors.PRIMARY,
        'border_width': 2,
        'border_radius': BorderRadius.SM,
        'padding_x': Spacing.MD,
        'padding_y': Spacing.SM,
        'text_color': Colors.WHITE,
        'placeholder_color': Colors.GRAY_400
    }

    # 标题样式
    TITLE = {
        'color': Colors.WHITE,
        'font_size': FontSizes.H2,
        'margin_bottom': Spacing.XL
    }

    SUBTITLE = {
        'color': Colors.GRAY_300,
        'font_size': FontSizes.H4,
        'margin_bottom': Spacing.LG
    }


class Animations:
    """动画配置"""

    # 动画持续时间（毫秒）
    FAST = 150
    NORMAL = 250
    SLOW = 400

    # 缓动函数
    @staticmethod
    def ease_out_cubic(t):
        """三次缓出函数"""
        return 1 - pow(1 - t, 3)

    @staticmethod
    def ease_in_out_cubic(t):
        """三次缓入缓出函数"""
        return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


class Layout:
    """布局常量"""

    # 网格系统
    GRID_COLUMNS = 12
    GRID_GUTTER = Spacing.MD

    # 容器最大宽度
    CONTAINER_SM = 640
    CONTAINER_MD = 768
    CONTAINER_LG = 1024
    CONTAINER_XL = 1280

    # 侧边栏宽度
    SIDEBAR_WIDTH = 280
    SIDEBAR_COLLAPSED_WIDTH = 60

    # 头部高度
    HEADER_HEIGHT = 64

    # 底部高度
    FOOTER_HEIGHT = 48


def create_rounded_rect_surface(width, height, radius, color):
    """创建圆角矩形表面"""
    import pygame
    surface = pygame.Surface((width, height), pygame.SRCALPHA)

    if radius <= 0:
        surface.fill(color)
        return surface

    # 限制圆角半径
    radius = min(radius, width // 2, height // 2)

    # 填充主体矩形
    pygame.draw.rect(surface, color, (radius, 0, width - 2 * radius, height))
    pygame.draw.rect(surface, color, (0, radius, width, height - 2 * radius))

    # 绘制四个圆角
    pygame.draw.circle(surface, color, (radius, radius), radius)
    pygame.draw.circle(surface, color, (width - radius, radius), radius)
    pygame.draw.circle(surface, color, (radius, height - radius), radius)
    pygame.draw.circle(
        surface, color, (width - radius, height - radius), radius)

    return surface


def create_gradient_surface(width, height, start_color, end_color, vertical=True):
    """创建渐变表面"""
    import pygame
    surface = pygame.Surface((width, height))

    if vertical:
        for y in range(height):
            ratio = y / height
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))
    else:
        for x in range(width):
            ratio = x / width
            r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
            g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
            b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
            pygame.draw.line(surface, (r, g, b), (x, 0), (x, height))

    return surface


def draw_text_with_shadow(surface, font, text, pos, color, shadow_color=None, shadow_offset=(2, 2)):
    """绘制带阴影的文字"""
    import pygame

    if shadow_color is None:
        shadow_color = Colors.BLACK

    # 绘制阴影
    shadow_surface = font.render(text, True, shadow_color)
    shadow_pos = (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1])
    surface.blit(shadow_surface, shadow_pos)

    # 绘制主文字
    text_surface = font.render(text, True, color)
    surface.blit(text_surface, pos)

    return text_surface.get_rect(topleft=pos)
