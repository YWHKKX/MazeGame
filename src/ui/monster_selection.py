#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
怪物选择UI模块
"""

import pygame
from typing import List, Dict, Optional, Tuple
from src.core import emoji_constants
from src.core.ui_design import Colors, FontSizes, Spacing, BorderRadius, UIStyles
from src.ui.base_ui import BaseUI


class MonsterSelectionUI(BaseUI):
    """怪物选择UI界面"""

    def __init__(self, screen_width: int, screen_height: int, font_manager=None):
        # 初始化基类
        super().__init__(font_manager)

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_visible = False
        self.selected_monster = None

        # UI布局参数 - 更现代的尺寸
        self.panel_width = min(screen_width - Spacing.XXXL * 2, 800)  # 增加宽度
        self.panel_height = min(screen_height - Spacing.XXXL * 2, 600)  # 增加高度
        self.panel_x = (screen_width - self.panel_width) // 2
        self.panel_y = (screen_height - self.panel_height) // 2

        # 保持向后兼容
        self.emoji_mapper = None

        # 怪物列表配置 - 使用emoji常量模块，现在消耗魔力而不是金币
        self.monsters = [
            ('imp', (emoji_constants.MONSTER, '小恶魔'), 100, 'mana'),
            ('orc_warrior', (emoji_constants.SWORD, '兽人战士'), 120, 'mana'),
            ('gargoyle', (emoji_constants.EAGLE, '石像鬼'), 200, 'mana'),
            ('hellhound', (emoji_constants.FIRE, '地狱犬'), 250, 'mana'),
            ('fire_salamander', (emoji_constants.SALAMANDER, '火蜥蜴'), 300, 'mana'),
            ('succubus', (emoji_constants.MONSTER, '魅魔'), 450, 'mana'),
            ('shadow_mage', (emoji_constants.MAGE, '暗影法师'), 400, 'mana'),
            ('tree_guardian', (emoji_constants.TREE, '树人守护者'), 350, 'mana'),
            ('stone_golem', (emoji_constants.STONE, '石魔像'), 600, 'mana'),
            ('shadow_lord', (emoji_constants.CROWN, '暗影领主'), 800, 'mana'),
            ('bone_dragon', (emoji_constants.DRAGON, '骨龙'), 1000, 'mana'),
        ]

        # 网格布局 - 更好的比例
        self.cols = 3
        self.rows = 4  # 11个怪物，3列需要4行
        self.button_width = 220  # 增加宽度
        self.button_height = 100  # 增加高度
        self.button_spacing = Spacing.LG

    def show(self):
        """显示选择界面"""
        self.is_visible = True
        self.selected_monster = None

    def hide(self):
        """隐藏选择界面"""
        self.is_visible = False
        # 不清空selected_monster，让主游戏逻辑处理

    def handle_event(self, event, character_db=None):
        """处理事件"""
        if not self.is_visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.hide()
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                return self._handle_mouse_click(event.pos)

        return False

    def _select_monster(self, index: int):
        """选择怪物"""
        if 0 <= index < len(self.monsters):
            self.selected_monster = self.monsters[index][0]
            self.hide()

    def _handle_mouse_click(self, pos):
        """处理鼠标点击"""
        # 计算点击位置是否在按钮区域内
        for i, (monster_id, name_data, cost, resource_type) in enumerate(self.monsters):
            row = i // self.cols
            col = i % self.cols

            button_x = self.panel_x + 20 + col * \
                (self.button_width + self.button_spacing)
            button_y = self.panel_y + 60 + row * \
                (self.button_height + self.button_spacing)

            if (button_x <= pos[0] <= button_x + self.button_width and
                    button_y <= pos[1] <= button_y + self.button_height):
                self.selected_monster = monster_id
                self.hide()
                return True
        return False

    def render(self, screen, font, small_font):
        """渲染UI"""
        if not self.is_visible:
            return

        # 半透明背景
        overlay = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill(Colors.OVERLAY_DARK)
        screen.blit(overlay, (0, 0))

        # 主面板 - 使用新的面板组件
        panel_rect = pygame.Rect(
            self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        self.draw_panel(screen, panel_rect)

        # 标题 - 更美观的样式
        title_text = self._render_emoji_text(
            self.font_manager.get_font(FontSizes.H2),
            emoji_constants.MONSTER,
            "选择召唤怪物",
            Colors.PRIMARY
        )
        title_rect = title_text.get_rect(
            center=(self.panel_x + self.panel_width // 2, self.panel_y + Spacing.XXL))
        screen.blit(title_text, title_rect)

        # 关闭提示
        close_hint = self.font_manager.safe_render(
            self.font_manager.get_font(FontSizes.SMALL),
            "按 ESC 取消", Colors.GRAY_400
        )
        close_rect = close_hint.get_rect(
            center=(self.panel_x + self.panel_width // 2, self.panel_y + Spacing.XXL + 35))
        screen.blit(close_hint, close_rect)

        # 渲染怪物按钮
        grid_start_y = self.panel_y + 90  # 调整起始位置

        for i, (monster_id, name_data, cost, resource_type) in enumerate(self.monsters):
            row = i // self.cols
            col = i % self.cols

            # 计算按钮位置 - 居中对齐
            grid_width = self.cols * self.button_width + \
                (self.cols - 1) * self.button_spacing
            grid_start_x = self.panel_x + (self.panel_width - grid_width) // 2

            button_x = grid_start_x + col * \
                (self.button_width + self.button_spacing)
            button_y = grid_start_y + row * \
                (self.button_height + self.button_spacing)

            # 按钮矩形
            button_rect = pygame.Rect(
                button_x, button_y, self.button_width, self.button_height)

            # 检查悬停状态
            mouse_pos = pygame.mouse.get_pos()
            is_hover = button_rect.collidepoint(mouse_pos)

            # 使用新的卡片样式绘制按钮
            card_style = UIStyles.CARD.copy()
            card_style['bg_color'] = Colors.GRAY_700
            card_style['border_color'] = Colors.PRIMARY if is_hover else Colors.GRAY_600
            card_style['border_width'] = 2 if is_hover else 1

            self.draw_card(screen, button_rect, card_style, hover=is_hover)

            # 渲染怪物信息 - 更美观的布局
            emoji_char, chinese_name = name_data

            # Emoji图标 - 顶部居中
            emoji_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.XXL), emoji_char, Colors.WHITE)
            emoji_rect = emoji_surface.get_rect(
                center=(button_x + self.button_width // 2, button_y + 25))
            screen.blit(emoji_surface, emoji_rect)

            # 怪物名称 - 中央
            name_surface = self.font_manager.safe_render(
                self.font_manager.get_font(FontSizes.NORMAL), chinese_name, Colors.WHITE)
            name_rect = name_surface.get_rect(
                center=(button_x + self.button_width // 2, button_y + 55))
            screen.blit(name_surface, name_rect)

            # 根据资源类型渲染成本
            if resource_type == 'mana':
                # 魔力消耗
                cost_emoji_surface = self.font_manager.safe_render(
                    self.font_manager.get_font(FontSizes.SMALL), emoji_constants.MAGIC, Colors.PURPLE)
                cost_text_surface = self.font_manager.safe_render(
                    self.font_manager.get_font(FontSizes.SMALL), f"{cost}魔", Colors.PURPLE)
            else:
                # 金币消耗（向后兼容）
                cost_emoji_surface = self.font_manager.safe_render(
                    self.font_manager.get_font(FontSizes.SMALL), emoji_constants.MONEY, Colors.GOLD)
                cost_text_surface = self.font_manager.safe_render(
                    self.font_manager.get_font(FontSizes.SMALL), f"{cost}金", Colors.GOLD)

            # 计算成本布局位置
            cost_total_width = cost_emoji_surface.get_width(
            ) + 4 + cost_text_surface.get_width()  # 4px间距
            cost_start_x = button_x + self.button_width // 2 - cost_total_width // 2
            cost_y = button_y + self.button_height - 20

            # 渲染成本表情符号
            screen.blit(cost_emoji_surface, (cost_start_x, cost_y))

            # 渲染成本文字
            screen.blit(cost_text_surface, (cost_start_x +
                        cost_emoji_surface.get_width() + 4, cost_y))

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

    def _safe_render_text(self, font, text, color):
        """安全渲染文本，优先使用图片"""

        # 如果表情符号映射器可用，尝试使用图片
        if self.emoji_mapper and any(ord(char) > 127 for char in text):
            # 检查是否包含表情符号
            emojis_in_text = []
            for char in text:
                if ord(char) > 127 and char in self.emoji_mapper.EMOJI_MAPPING:
                    emojis_in_text.append(char)

            if emojis_in_text:
                # 如果文本只包含一个表情符号，直接返回图片
                if len(emojis_in_text) == 1 and len(text.strip()) == 1:
                    emoji = emojis_in_text[0]
                    image = self.emoji_mapper.get_image(emoji)
                    if image:
                        # 缩放图片到合适大小
                        target_size = 32
                        if image.get_width() > target_size or image.get_height() > target_size:
                            scale = min(target_size / image.get_width(),
                                        target_size / image.get_height())
                            new_width = int(image.get_width() * scale)
                            new_height = int(image.get_height() * scale)
                            image = pygame.transform.scale(
                                image, (new_width, new_height))
                        return image

        # 回退到字体管理器的渲染
        return self.font_manager.safe_render(font, text, color)
