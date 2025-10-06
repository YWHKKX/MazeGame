#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后勤召唤UI面板
类似于怪物选择界面，但专门用于召唤后勤单位（地精工程师和哥布林苦工）
"""

import pygame
import math
from typing import List, Dict, Optional, Tuple

from src.core import emoji_constants
from src.core.ui_design import Colors, FontSizes, Spacing, BorderRadius, UIStyles
from src.ui.base_ui import BaseUI
from src.utils.logger import game_logger


class LogisticsSelectionUI(BaseUI):
    """后勤召唤选择界面"""

    def __init__(self, screen_width: int, screen_height: int, font_manager):
        """
        初始化后勤选择UI

        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            font_manager: 字体管理器
        """
        super().__init__(font_manager)
        self.screen_width = screen_width
        self.screen_height = screen_height

        # 字体 - 使用设计系统
        self.title_font = font_manager.get_font(FontSizes.H2)
        self.normal_font = font_manager.get_font(FontSizes.LARGE)
        self.small_font = font_manager.get_font(FontSizes.NORMAL)

        # UI状态
        self.is_visible = False
        self.selected_logistics = None  # 选中的后勤单位

        # 面板尺寸和位置 - 现代化尺寸
        self.panel_width = 500
        self.panel_height = 350
        self.panel_x = (screen_width - self.panel_width) // 2
        self.panel_y = (screen_height - self.panel_height) // 2

        # 后勤单位配置
        self.logistics_units = [
            {
                'id': 'goblin_engineer',
                'name': '地精工程师',
                'cost': 100,
                'emoji': emoji_constants.HAMMER,
                'color': (50, 205, 50),
                'abilities': ['建造建筑', '修理建筑', '建造陷阱']
            },
            {
                'id': 'goblin_worker',
                'name': '哥布林苦工',
                'cost': 80,
                'emoji': emoji_constants.PICKAXE,
                'color': (143, 188, 143),
                'abilities': ['挖掘金矿', '收集资源', '运输物资']
            }
        ]

        # 按钮配置
        self.unit_buttons = []
        self._initialize_buttons()

        game_logger.info("后勤召唤UI初始化完成")

    def _initialize_buttons(self):
        """初始化按钮"""
        button_width = 450
        button_height = 100
        start_y = self.panel_y + 80

        for i, unit in enumerate(self.logistics_units):
            button_rect = pygame.Rect(
                self.panel_x + Spacing.XL,
                start_y + i * (button_height + Spacing.LG),
                button_width,
                button_height
            )

            self.unit_buttons.append({
                'rect': button_rect,
                'unit': unit,
                'hovered': False
            })

    def show(self):
        """显示后勤选择面板"""
        self.is_visible = True
        self.selected_logistics = None
        game_logger.info("显示后勤召唤面板")

    def hide(self):
        """隐藏后勤选择面板"""
        self.is_visible = False
        game_logger.info("隐藏后勤召唤面板")

    def handle_event(self, event, character_db=None) -> bool:
        """
        处理事件

        Args:
            event: pygame事件
            character_db: 角色数据库（兼容性参数）

        Returns:
            bool: 是否处理了事件
        """
        if not self.is_visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_5:
                self.hide()
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                mouse_pos = event.pos

                # 检查是否点击了后勤单位按钮
                for button in self.unit_buttons:
                    if button['rect'].collidepoint(mouse_pos):
                        self.selected_logistics = button['unit']['id']
                        self.hide()
                        game_logger.info(
                            f"🎯 选择了后勤单位: {button['unit']['name']}")
                        return True

                # 检查是否点击了面板外部（关闭面板）
                panel_rect = pygame.Rect(
                    self.panel_x, self.panel_y, self.panel_width, self.panel_height)
                if not panel_rect.collidepoint(mouse_pos):
                    self.hide()
                    return True

        elif event.type == pygame.MOUSEMOTION:
            if self.is_visible:
                mouse_pos = event.pos
                # 更新按钮悬停状态
                for button in self.unit_buttons:
                    button['hovered'] = button['rect'].collidepoint(mouse_pos)

        return False

    def render(self, screen: pygame.Surface, font, small_font):
        """
        渲染后勤选择界面

        Args:
            screen: pygame屏幕表面
            font: 主字体
            small_font: 小字体
        """
        if not self.is_visible:
            return

        # 绘制半透明背景
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.set_alpha(150)
        overlay.fill(Colors.BLACK)
        screen.blit(overlay, (0, 0))

        # 绘制现代化面板
        panel_rect = pygame.Rect(
            self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        modal_style = {
            'bg_color': Colors.DARK_CARD,
            'border_color': Colors.PRIMARY,
            'border_width': 2,
            'border_radius': BorderRadius.XL
        }
        self.draw_panel(screen, panel_rect, modal_style)

        # 绘制标题 - 现代化标题样式
        title_bg_rect = pygame.Rect(
            self.panel_x + Spacing.LG,
            self.panel_y + Spacing.LG,
            self.panel_width - Spacing.LG * 2,
            50
        )
        header_style = {
            'bg_color': Colors.GRAY_700,
            'border_color': Colors.GRAY_600,
            'border_width': 1,
            'border_radius': BorderRadius.MD
        }
        self.draw_card(screen, title_bg_rect, header_style)

        # 分别渲染表情符号和文字
        emoji_text = self.font_manager.safe_render(
            self.title_font, emoji_constants.HAMMER, Colors.GOLD
        )
        title_text = self.font_manager.safe_render(
            self.title_font, "后勤召唤", Colors.GOLD
        )

        # 计算布局位置
        total_width = emoji_text.get_width() + 10 + title_text.get_width()  # 10px间距
        start_x = title_bg_rect.centerx - total_width // 2
        center_y = title_bg_rect.centery

        # 渲染表情符号
        emoji_rect = emoji_text.get_rect(midleft=(start_x, center_y))
        screen.blit(emoji_text, emoji_rect)

        # 渲染标题文字
        title_rect = title_text.get_rect(
            midleft=(start_x + emoji_text.get_width() + 10, center_y))
        screen.blit(title_text, title_rect)

        # 绘制后勤单位按钮 - 现代化卡片样式
        for button in self.unit_buttons:
            unit = button['unit']
            rect = button['rect']
            hovered = button['hovered']

            # 选择按钮样式
            if hovered:
                button_style = {
                    'bg_color': Colors.DARK_HOVER,
                    'border_color': Colors.PRIMARY,
                    'border_width': 2,
                    'border_radius': BorderRadius.MD
                }
            else:
                button_style = {
                    'bg_color': Colors.DARK_CARD,
                    'border_color': Colors.GRAY_700,
                    'border_width': 1,
                    'border_radius': BorderRadius.MD
                }

            # 绘制现代化卡片
            self.draw_card(screen, rect, button_style, hover=hovered)

            # 绘制单位信息
            self._render_unit_info(screen, unit, rect)

        # 绘制关闭提示 - 现代化提示样式
        hint_bg_rect = pygame.Rect(
            self.panel_x + Spacing.LG,
            self.panel_y + self.panel_height - 50,
            self.panel_width - Spacing.LG * 2,
            30
        )
        subtle_style = {
            'bg_color': Colors.GRAY_800,
            'border_color': Colors.GRAY_700,
            'border_width': 1,
            'border_radius': BorderRadius.SM
        }
        self.draw_card(screen, hint_bg_rect, subtle_style)

        close_hint = self.font_manager.safe_render(
            self.font_manager.get_font(FontSizes.SMALL),
            "按 ESC 取消", Colors.GRAY_400
        )
        close_rect = close_hint.get_rect(
            center=(self.panel_x + self.panel_width // 2, self.panel_y + Spacing.XXL + 35))
        screen.blit(close_hint, close_rect)

    def _render_unit_info(self, screen: pygame.Surface, unit: Dict, rect: pygame.Rect):
        """渲染单位信息"""
        # 单位图标区域 - 现代化图标设计
        icon_size = 80
        icon_x = rect.x + Spacing.LG
        icon_y = rect.y + Spacing.MD

        # 绘制图标背景 - 圆角设计
        icon_rect = pygame.Rect(icon_x, icon_y, icon_size, icon_size)
        icon_bg_style = {
            'bg_color': unit['color'],
            'border_radius': BorderRadius.LG,
            'border_color': Colors.WHITE,
            'border_width': 2
        }
        self.draw_card(screen, icon_rect, icon_bg_style)

        # 绘制表情符号图标
        emoji_text = self.font_manager.safe_render(
            self.title_font, unit['emoji'], Colors.WHITE
        )
        emoji_rect = emoji_text.get_rect(center=icon_rect.center)
        screen.blit(emoji_text, emoji_rect)

        # 文本区域布局
        text_x = icon_x + icon_size + Spacing.LG
        text_y = icon_y

        # 单位名称 - 大字体
        name_text = self.font_manager.safe_render(
            self.normal_font, unit['name'], Colors.WHITE
        )
        screen.blit(name_text, (text_x, text_y))

        # 成本信息 - 金色高亮
        cost_text = self.font_manager.safe_render(
            self.normal_font, f"💰 {unit['cost']}金币", Colors.GOLD
        )
        screen.blit(cost_text, (text_x, text_y + 25))

        # 能力列表 - 灰色小字体
        abilities_text = " • ".join(unit['abilities'])
        abilities_surface = self.font_manager.safe_render(
            self.font_manager.get_font(
                FontSizes.SMALL), f"⚡ {abilities_text}", Colors.GRAY_400
        )
        screen.blit(abilities_surface, (text_x, text_y + 70))

    def get_selected_logistics(self) -> Optional[str]:
        """获取选中的后勤单位ID"""
        if self.selected_logistics:
            selected = self.selected_logistics
            self.selected_logistics = None  # 清空选择
            return selected
        return None
