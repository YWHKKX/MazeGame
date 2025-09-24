#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主游戏UI渲染模块
美化的游戏界面组件
"""

import pygame
from typing import List, Dict, Tuple, Optional
from src.core import emoji_constants
from src.core.ui_design import Colors, FontSizes, Spacing, BorderRadius, UIStyles
from src.ui.base_ui import BaseUI


class GameUI(BaseUI):
    """主游戏UI渲染器"""

    def __init__(self, screen: pygame.Surface, font_manager):
        super().__init__(font_manager)
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

    def render_resource_panel(self, game_state, creatures_count, max_creatures, building_manager=None):
        """渲染美化的资源面板"""
        panel_x, panel_y = Spacing.LG, Spacing.LG
        panel_width, panel_height = 240, 200  # 增加尺寸

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # 绘制面板背景
        panel_style = UIStyles.PANEL.copy()
        panel_style['bg_color'] = Colors.DARK_SURFACE
        self.draw_panel(self.screen, panel_rect, panel_style)

        # 标题
        title_y = panel_y + Spacing.LG
        title_text = self._render_emoji_text(
            self.font_manager.get_font(FontSizes.LARGE),
            emoji_constants.CHART, "资源状况", Colors.PRIMARY
        )
        title_rect = title_text.get_rect(
            center=(panel_x + panel_width // 2, title_y))
        self.screen.blit(title_text, title_rect)

        # 计算总金币（包括金库中的金币）
        total_gold = game_state.get_total_gold(building_manager)

        # 资源信息
        resources = [
            ('gold', emoji_constants.MONEY,
             f"{int(total_gold)}", "黄金", Colors.GOLD),
            ('mana', "🔮", f"{int(game_state.mana)}", "法力", Colors.MANA),
            ('food', "🍖", f"{int(game_state.food)}", "食物", Colors.WARNING),
            ('raw_gold', "⚡", f"{int(game_state.raw_gold)}",
             "原始黄金", Colors.GOLD),
            ('creatures', emoji_constants.MONSTER,
             f"{creatures_count}/{max_creatures}", "怪物", Colors.ERROR),
            ('score', "🏆", f"{int(game_state.score)}", "分数", Colors.WHITE)
        ]

        # 计算布局
        item_height = 20
        start_y = title_y + 40

        for i, (resource_id, emoji, value, label, color) in enumerate(resources):
            y = start_y + i * (item_height + Spacing.SM)

            # 资源项背景
            item_rect = pygame.Rect(
                panel_x + Spacing.MD, y - 2, panel_width - Spacing.MD * 2, item_height + 4)
            if i % 2 == 0:  # 交替背景色
                pygame.draw.rect(self.screen, Colors.GRAY_800,
                                 item_rect, border_radius=BorderRadius.SM)

            # Emoji
            emoji_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.NORMAL), emoji, color)
            self.screen.blit(emoji_surface, (panel_x + Spacing.LG, y))

            # 数值 - 右对齐
            value_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.NORMAL), value, color)
            value_rect = value_surface.get_rect(
                right=panel_x + panel_width - Spacing.LG, centery=y + item_height // 2)
            self.screen.blit(value_surface, value_rect)

            # 标签
            label_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.SMALL), label, Colors.GRAY_300)
            self.screen.blit(label_surface, (panel_x + Spacing.LG + 25, y))

    def render_build_panel(self, build_mode, game_state):
        """渲染美化的建造面板"""
        panel_x = self.screen_width - 250  # 右上角
        panel_y = Spacing.LG
        panel_width, panel_height = 230, 280  # 增加尺寸

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # 绘制面板背景
        panel_style = UIStyles.PANEL.copy()
        panel_style['bg_color'] = Colors.DARK_SURFACE
        self.draw_panel(self.screen, panel_rect, panel_style)

        # 标题
        title_y = panel_y + Spacing.LG
        title_text = self._render_emoji_text(
            self.font_manager.get_font(FontSizes.LARGE),
            emoji_constants.BUILD, "建造选项", Colors.PRIMARY
        )
        title_rect = title_text.get_rect(
            center=(panel_x + panel_width // 2, title_y))
        self.screen.blit(title_text, title_rect)

        # 建造选项
        build_options = [
            ("1", emoji_constants.PICKAXE, "挖掘", 10, "EXCAVATE"),
            ("2", emoji_constants.BUILD, "建筑面板", "面板", "BUILDING_PANEL"),
            ("4", emoji_constants.MONSTER, "召唤怪物", "动态", "SUMMON_CREATURE"),
            ("5", emoji_constants.HAMMER, "后勤召唤", "动态", "SUMMON_LOGISTICS")
        ]

        start_y = title_y + 50

        for i, (key, emoji, name, cost, mode_name) in enumerate(build_options):
            y = start_y + i * 40

            # 检查是否为当前选中的模式
            is_selected = (build_mode.name == mode_name if hasattr(
                build_mode, 'name') else False)

            # 选项背景
            item_rect = pygame.Rect(
                panel_x + Spacing.MD, y - 4, panel_width - Spacing.MD * 2, 32)

            if is_selected:
                # 选中状态
                pygame.draw.rect(self.screen, Colors.PRIMARY,
                                 item_rect, border_radius=BorderRadius.SM)
                text_color = Colors.WHITE
                cost_color = Colors.WHITE
            else:
                # 未选中状态
                pygame.draw.rect(self.screen, Colors.GRAY_800,
                                 item_rect, border_radius=BorderRadius.SM)
                text_color = Colors.GRAY_300
                cost_color = Colors.GOLD

            # 快捷键
            key_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.SMALL), f"[{key}]", Colors.GRAY_400)
            self.screen.blit(key_surface, (panel_x + Spacing.LG, y))

            # Emoji
            emoji_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.NORMAL), emoji, text_color)
            self.screen.blit(emoji_surface, (panel_x + Spacing.LG + 30, y))

            # 名称
            name_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.SMALL), name, text_color)
            self.screen.blit(name_surface, (panel_x + Spacing.LG + 55, y))

            # 成本
            if isinstance(cost, int):
                cost_text = f"{cost}金"
            else:
                cost_text = cost

            cost_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.SMALL), cost_text, cost_color)
            cost_rect = cost_surface.get_rect(
                right=panel_x + panel_width - Spacing.LG, centery=y + 8)
            self.screen.blit(cost_surface, cost_rect)

    def render_status_panel(self, mouse_world_x, mouse_world_y, camera_x, camera_y, build_mode, debug_mode):
        """渲染美化的状态面板"""
        panel_x = Spacing.LG
        panel_y = self.screen_height - 140  # 底部
        panel_width, panel_height = 300, 120

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # 绘制面板背景
        panel_style = UIStyles.PANEL.copy()
        panel_style['bg_color'] = Colors.DARK_SURFACE
        self.draw_panel(self.screen, panel_rect, panel_style)

        # 标题
        title_y = panel_y + Spacing.LG
        title_text = self._render_emoji_text(
            self.font_manager.get_font(FontSizes.MEDIUM),
            "🔧", "状态信息", Colors.INFO
        )
        self.screen.blit(title_text, (panel_x + Spacing.LG, title_y))

        # 状态信息
        status_info = [
            f"鼠标: ({mouse_world_x}, {mouse_world_y})",
            f"相机: ({camera_x}, {camera_y})",
            f"模式: {build_mode.name if hasattr(build_mode, 'name') else 'NONE'}",
            f"调试: {'开启' if debug_mode else '关闭'}"
        ]

        start_y = title_y + 30

        for i, info in enumerate(status_info):
            y = start_y + i * 18
            info_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.SMALL), info, Colors.GRAY_300)
            self.screen.blit(info_surface, (panel_x + Spacing.LG, y))

    def render_game_info_panel(self, wave_number):
        """渲染游戏信息面板"""
        panel_x = self.screen_width - 250
        panel_y = self.screen_height - 100
        panel_width, panel_height = 230, 80

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)

        # 绘制面板背景
        panel_style = UIStyles.PANEL.copy()
        panel_style['bg_color'] = Colors.DARK_SURFACE
        self.draw_panel(self.screen, panel_rect, panel_style)

        # 波次信息
        wave_text = self._render_emoji_text(
            self.font_manager.get_font(FontSizes.MEDIUM),
            "🌊", f"第 {wave_number} 波", Colors.INFO
        )
        wave_rect = wave_text.get_rect(
            center=(panel_x + panel_width // 2, panel_y + 25))
        self.screen.blit(wave_text, wave_rect)

        # 快捷键提示
        hint_text = "按 B 打开角色图鉴"
        hint_surface = self.font_manager.safe_render(
            self.font_manager.get_font(FontSizes.SMALL), hint_text, Colors.GRAY_400)
        hint_rect = hint_surface.get_rect(
            center=(panel_x + panel_width // 2, panel_y + 50))
        self.screen.blit(hint_surface, hint_rect)

    def _render_emoji_text(self, font, emoji, text, color):
        """分别渲染 emoji 和文字，然后合并"""
        if not text.strip():
            # 如果没有文字，只渲染 emoji
            return self.font_manager.safe_render(font, emoji, color)

        # 分别渲染 emoji 和文字
        emoji_surface = self.font_manager.safe_render(font, emoji, color)
        text_surface = self.font_manager.safe_render(font, f" {text}", color)

        # 计算合并后的尺寸
        total_width = emoji_surface.get_width() + text_surface.get_width()
        total_height = max(emoji_surface.get_height(),
                           text_surface.get_height())

        # 创建合并的表面
        combined_surface = pygame.Surface(
            (total_width, total_height), pygame.SRCALPHA)
        combined_surface.fill((0, 0, 0, 0))  # 透明背景

        # 绘制 emoji 和文字
        combined_surface.blit(emoji_surface, (0, 0))
        combined_surface.blit(text_surface, (emoji_surface.get_width(), 0))

        return combined_surface
