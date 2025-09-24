#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑系统UI界面
支持建造选择、状态显示、工程师管理等功能
"""

import pygame
import math
from typing import List, Dict, Optional, Tuple, Any

from src.entities.building import BuildingType, BuildingRegistry, BuildingCategory, BuildingStatus
from src.core.constants import GameConstants
from src.core import emoji_constants
from src.core.ui_design import Colors, FontSizes, Spacing, BorderRadius, UIStyles
from src.ui.base_ui import BaseUI


class BuildingUI(BaseUI):
    """建筑系统UI管理器"""

    def __init__(self, screen_width: int, screen_height: int, font_manager):
        """
        初始化建筑UI

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
        self.normal_font = font_manager.get_font(FontSizes.NORMAL)
        self.small_font = font_manager.get_font(FontSizes.SMALL)

        # UI状态
        self.show_building_panel = False
        self.show_statistics_panel = False
        self.selected_building_category = None
        self.selected_building_type = None

        # 面板位置和大小
        self.building_panel_rect = pygame.Rect(50, 50, 300, 400)
        self.engineer_panel_rect = pygame.Rect(370, 50, 250, 300)
        self.statistics_panel_rect = pygame.Rect(50, 470, 570, 200)

        # 按钮列表
        self.building_buttons = []
        self.category_buttons = []

        # 建筑信息显示
        # 建筑信息面板已移除

        # 滚动支持
        self.building_scroll_offset = 0
        self.max_building_scroll = 0

        # 地精工程师计数
        self.goblin_engineer_count = 0

        self._initialize_ui_elements()

    def _initialize_ui_elements(self):
        """初始化UI元素"""
        # 建筑分类按钮
        category_y = self.building_panel_rect.y + 55
        for i, category in enumerate(BuildingCategory):
            button_rect = pygame.Rect(
                self.building_panel_rect.x + 10 + (i % 2) * 140,
                category_y + (i // 2) * 30,
                130, 25
            )
            self.category_buttons.append({
                'rect': button_rect,
                'category': category,
                'text': self._get_category_display_name(category)
            })

    def handle_event(self, event, building_manager=None) -> bool:
        """
        处理UI事件

        Args:
            event: pygame事件
            building_manager: 建筑管理器

        Returns:
            bool: 是否处理了事件
        """
        if event.type == pygame.KEYDOWN:
            # 快捷键处理
            if event.key == pygame.K_2:
                self.show_building_panel = not self.show_building_panel
                return True
            elif event.key == pygame.K_TAB:
                self.show_statistics_panel = not self.show_statistics_panel
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                return self._handle_mouse_click(event.pos, building_manager)
            elif event.button == 3:  # 右键
                # 右键关闭面板
                self.show_building_panel = False
                self.show_engineer_panel = False
                self.selected_building_category = None
                return True

        elif event.type == pygame.MOUSEWHEEL:
            # 处理滚轮滚动
            if self.show_building_panel and self.building_panel_rect.collidepoint(pygame.mouse.get_pos()):
                self.building_scroll_offset -= event.y * 20
                self.building_scroll_offset = max(
                    0, min(self.building_scroll_offset, self.max_building_scroll))
                return True

        return False

    def _handle_mouse_click(self, pos: Tuple[int, int], building_manager) -> bool:
        """处理鼠标点击"""
        # 检查建筑分类按钮
        if self.show_building_panel:
            for button in self.category_buttons:
                if button['rect'].collidepoint(pos):
                    self.selected_building_category = button['category']
                    self.selected_building_type = None
                    self._update_building_list()
                    return True

            # 检查建筑类型按钮
            for button in self.building_buttons:
                if button['rect'].collidepoint(pos):
                    self.selected_building_type = button['type']
                    return True

        return False

    def render(self, screen: pygame.Surface, building_manager=None, game_state=None):
        """
        渲染建筑UI

        Args:
            screen: pygame屏幕表面
            building_manager: 建筑管理器
            game_state: 游戏状态
        """
        # 渲染建筑面板
        if self.show_building_panel:
            self._render_building_panel(screen, building_manager, game_state)

        # 渲染统计面板
        if self.show_statistics_panel:
            self._render_statistics_panel(screen, building_manager)

        # 渲染建筑信息面板
        # 建筑信息面板已移除

        # 渲染快捷键提示
        self._render_hotkey_hints(screen)

    def _render_building_panel(self, screen: pygame.Surface, building_manager, game_state):
        """渲染建筑面板"""
        # 使用现代化面板样式
        panel_style = {
            'bg_color': Colors.DARK_SURFACE,
            'border_color': Colors.GRAY_600,
            'border_width': 2,
            'border_radius': BorderRadius.LG
        }
        self.draw_panel(screen, self.building_panel_rect, panel_style)

        # 绘制标题 - 使用现代化标题样式
        title_bg_rect = pygame.Rect(
            self.building_panel_rect.x + Spacing.SM,
            self.building_panel_rect.y + Spacing.SM,
            self.building_panel_rect.width - Spacing.SM * 2,
            50
        )
        header_style = {
            'bg_color': Colors.GRAY_700,
            'border_color': Colors.GRAY_600,
            'border_width': 1,
            'border_radius': BorderRadius.MD
        }
        self.draw_card(screen, title_bg_rect, header_style)

        # 分别渲染表情符号和标题文字
        emoji_text = self.font_manager.safe_render(
            self.title_font, emoji_constants.BUILD, Colors.GOLD
        )
        title_text = self.font_manager.safe_render(
            self.title_font, "建筑系统", Colors.GOLD
        )

        # 计算布局位置
        total_width = emoji_text.get_width() + 10 + title_text.get_width()  # 10px间距
        start_x = title_bg_rect.centerx - total_width // 2
        center_y = title_bg_rect.centery - 8

        # 渲染表情符号
        emoji_rect = emoji_text.get_rect(midleft=(start_x, center_y))
        screen.blit(emoji_text, emoji_rect)

        # 渲染标题文字
        title_rect = title_text.get_rect(
            midleft=(start_x + emoji_text.get_width() + 10, center_y))
        screen.blit(title_text, title_rect)

        # 分别渲染地精工程师计数的表情符号和文字
        engineer_emoji_text = self.font_manager.safe_render(
            self.small_font, emoji_constants.HAMMER, Colors.SUCCESS
        )
        # 动态获取地精工程师计数
        current_count = self._get_goblin_engineer_count(
            building_manager) if building_manager else self.goblin_engineer_count
        engineer_text = self.font_manager.safe_render(
            self.small_font, f"地精工程师: {current_count}", Colors.SUCCESS
        )

        # 计算工程师计数布局位置
        engineer_total_width = engineer_emoji_text.get_width() + 8 + \
            engineer_text.get_width()  # 8px间距
        engineer_start_x = title_bg_rect.centerx - engineer_total_width // 2
        engineer_center_y = title_bg_rect.centery + 12

        # 渲染工程师表情符号
        engineer_emoji_rect = engineer_emoji_text.get_rect(
            midleft=(engineer_start_x, engineer_center_y))
        screen.blit(engineer_emoji_text, engineer_emoji_rect)

        # 渲染工程师文字
        engineer_rect = engineer_text.get_rect(midleft=(
            engineer_start_x + engineer_emoji_text.get_width() + 8, engineer_center_y))
        screen.blit(engineer_text, engineer_rect)

        # 绘制分类按钮 - 使用现代化按钮样式
        for button in self.category_buttons:
            is_selected = button['category'] == self.selected_building_category

            # 选择按钮样式
            if is_selected:
                button_style = {
                    'bg_color': Colors.PRIMARY,
                    'text_color': Colors.WHITE,
                    'border_radius': BorderRadius.MD
                }
            else:
                button_style = {
                    'bg_color': Colors.GRAY_600,
                    'text_color': Colors.WHITE,
                    'border_radius': BorderRadius.MD
                }

            # 绘制按钮
            self.draw_button(
                screen, button['rect'], button['text'], button_style, hover=False)

            # 选中状态的额外高亮
            if is_selected:
                highlight_rect = pygame.Rect(
                    button['rect'].x - 2, button['rect'].y - 2,
                    button['rect'].width + 4, button['rect'].height + 4
                )
                pygame.draw.rect(screen, Colors.PRIMARY, highlight_rect, 2)

        # 绘制建筑列表
        if self.selected_building_category:
            self._render_building_list(screen, building_manager, game_state)

    def _render_building_list(self, screen: pygame.Surface, building_manager, game_state):
        """渲染建筑列表"""
        configs = BuildingRegistry.get_configs_by_category(
            self.selected_building_category)

        start_y = self.building_panel_rect.y + 145 - self.building_scroll_offset
        button_height = 35
        visible_area = pygame.Rect(
            self.building_panel_rect.x,
            self.building_panel_rect.y + 145,
            self.building_panel_rect.width,
            self.building_panel_rect.height - 145
        )

        self.building_buttons.clear()

        for i, (building_type, config) in enumerate(configs.items()):
            button_y = start_y + i * (button_height + 5)

            # 只渲染可见的按钮
            if button_y + button_height < visible_area.y or button_y > visible_area.bottom:
                continue

            button_rect = pygame.Rect(
                self.building_panel_rect.x + 10,
                button_y,
                self.building_panel_rect.width - 20,
                button_height
            )

            # 检查是否可以建造
            can_build = True
            if building_manager and game_state:
                # 这里需要实际的位置信息，暂时假设可以建造
                can_build = game_state.gold >= config.cost_gold

            # 选择按钮样式
            if building_type == self.selected_building_type:
                button_style = {
                    'bg_color': Colors.PRIMARY,
                    'border_color': Colors.PRIMARY_LIGHT,
                    'border_radius': BorderRadius.MD
                }
            elif can_build:
                button_style = {
                    'bg_color': Colors.DARK_CARD,
                    'border_color': Colors.GRAY_600,
                    'border_radius': BorderRadius.MD
                }
            else:
                button_style = {
                    'bg_color': Colors.GRAY_800,
                    'border_color': Colors.GRAY_700,
                    'border_radius': BorderRadius.MD
                }

            # 绘制现代化按钮
            self.draw_card(screen, button_rect, button_style)

            # 建筑信息布局 - 现代化卡片内容
            content_x = button_rect.x + Spacing.MD
            content_y = button_rect.y + Spacing.SM

            # 建筑名称
            name_surface = self.font_manager.safe_render(
                self.normal_font, config.name, Colors.WHITE
            )
            screen.blit(name_surface, (content_x, content_y))

            # 成本信息
            cost_text = f"{config.cost_gold}金"
            if config.cost_crystal > 0:
                cost_text += f" + {config.cost_crystal}晶"

            cost_color = Colors.GOLD if can_build else Colors.GRAY_500
            cost_surface = self.font_manager.safe_render(
                self.small_font, cost_text, cost_color
            )
            screen.blit(cost_surface, (content_x, content_y + 20))

            # 建造时间
            time_text = f"⏱️ {config.build_time:.0f}秒"
            time_surface = self.font_manager.safe_render(
                self.small_font, time_text, Colors.GRAY_400
            )
            screen.blit(time_surface, (button_rect.right - 80, content_y + 20))

            # 建筑等级星星
            stars = "⭐" * config.level
            stars_surface = self.font_manager.safe_render(
                self.small_font, stars, Colors.GOLD
            )
            screen.blit(stars_surface, (button_rect.right - 100, content_y))

            self.building_buttons.append({
                'rect': button_rect,
                'type': building_type,
                'config': config,
                'can_build': can_build
            })

        # 更新滚动范围
        total_height = len(configs) * (button_height + 5)
        visible_height = self.building_panel_rect.height - 120
        self.max_building_scroll = max(0, total_height - visible_height)

    def _render_engineer_panel(self, screen: pygame.Surface, building_manager, game_state):
        """渲染工程师面板"""
        # 绘制面板背景
        panel_surface = pygame.Surface(
            (self.engineer_panel_rect.width, self.engineer_panel_rect.height))
        panel_surface.set_alpha(220)
        panel_surface.fill((30, 30, 30))
        screen.blit(panel_surface, self.engineer_panel_rect.topleft)

        # 绘制边框
        pygame.draw.rect(screen, (100, 100, 100), self.engineer_panel_rect, 2)

        # 分别渲染工程师面板的表情符号和标题文字
        engineer_emoji_text = self.font_manager.safe_render(
            self.title_font, emoji_constants.HAMMER, (255, 215, 0)
        )
        engineer_title_text = self.font_manager.safe_render(
            self.title_font, "工程师", (255, 215, 0)
        )

        # 渲染工程师面板表情符号和标题
        engineer_start_x = self.engineer_panel_rect.x + 10
        engineer_y = self.engineer_panel_rect.y + 5

        screen.blit(engineer_emoji_text, (engineer_start_x, engineer_y))
        screen.blit(engineer_title_text, (engineer_start_x +
                    engineer_emoji_text.get_width() + 8, engineer_y))

        # 绘制工程师按钮
        for button in self.engineer_buttons:
            can_summon = game_state and game_state.gold >= button['config'].cost

            if button['type'] == self.selected_engineer_type:
                color = (0, 100, 200)
            elif can_summon:
                color = (50, 50, 50)
            else:
                color = (80, 40, 40)

            pygame.draw.rect(screen, color, button['rect'])
            pygame.draw.rect(screen, (150, 150, 150), button['rect'], 1)

            # 工程师信息
            name_text = button['config'].name
            cost_text = f"{button['config'].cost}金"
            efficiency_text = f"效率: {button['config'].build_efficiency}x"

            name_surface = self.font_manager.safe_render(
                self.small_font, name_text, (255, 255, 255)
            )
            cost_surface = self.font_manager.safe_render(
                self.small_font, cost_text, (255, 215, 0) if can_summon else (
                    150, 150, 150)
            )
            efficiency_surface = self.font_manager.safe_render(
                self.small_font, efficiency_text, (200, 200, 200)
            )

            screen.blit(
                name_surface, (button['rect'].x + 5, button['rect'].y + 2))
            screen.blit(
                cost_surface, (button['rect'].x + 5, button['rect'].y + 16))
            screen.blit(efficiency_surface,
                        (button['rect'].right - 80, button['rect'].y + 16))

        # 显示当前工程师状态
        if building_manager:
            self._render_engineer_status(screen, building_manager)

    def _render_engineer_status(self, screen: pygame.Surface, building_manager):
        """渲染工程师状态"""
        stats = building_manager.get_engineer_statistics()

        status_y = self.engineer_panel_rect.y + 140
        status_texts = [
            f"总工程师: {stats['total_engineers']}",
            f"空闲: {stats['efficiency_stats']['idle_engineers']}",
            f"忙碌: {stats['efficiency_stats']['busy_engineers']}",
            f"项目数: {stats['efficiency_stats']['total_projects']}"
        ]

        for i, text in enumerate(status_texts):
            text_surface = self.font_manager.safe_render(
                self.small_font, text, (200, 200, 200)
            )
            screen.blit(
                text_surface, (self.engineer_panel_rect.x + 10, status_y + i * 18))

    def _render_statistics_panel(self, screen: pygame.Surface, building_manager):
        """渲染统计面板"""
        if not building_manager:
            return

        # 使用现代化面板样式
        panel_style = {
            'bg_color': Colors.DARK_SURFACE,
            'border_color': Colors.GRAY_600,
            'border_width': 2,
            'border_radius': BorderRadius.LG
        }
        self.draw_panel(screen, self.statistics_panel_rect, panel_style)

        # 分别渲染统计面板的表情符号和标题文字
        stats_emoji_text = self.font_manager.safe_render(
            self.title_font, emoji_constants.CHART, (255, 215, 0)
        )
        stats_title_text = self.font_manager.safe_render(
            self.title_font, "建筑统计", (255, 215, 0)
        )

        # 渲染统计面板表情符号和标题
        stats_start_x = self.statistics_panel_rect.x + 10
        stats_y = self.statistics_panel_rect.y + 5

        screen.blit(stats_emoji_text, (stats_start_x, stats_y))
        screen.blit(stats_title_text, (stats_start_x +
                    stats_emoji_text.get_width() + 8, stats_y))

        # 获取统计数据
        building_stats = building_manager.get_building_statistics()
        engineer_stats = building_manager.get_engineer_statistics()

        # 建筑统计
        building_col_x = self.statistics_panel_rect.x + 10
        stats_y = self.statistics_panel_rect.y + 35

        building_texts = [
            "=== 建筑统计 ===",
            f"总建筑: {building_stats['total_buildings']}",
            f"已完成: {building_stats['construction_stats']['completed']}",
            f"建造中: {building_stats['construction_stats']['under_construction']}",
            f"受损: {building_stats['construction_stats']['damaged']}",
            f"总花费: {building_stats['construction_stats']['total_gold_spent']}金"
        ]

        for i, text in enumerate(building_texts):
            color = (255, 215, 0) if text.startswith(
                "===") else (200, 200, 200)
            text_surface = self.font_manager.safe_render(
                self.small_font, text, color)
            screen.blit(text_surface, (building_col_x, stats_y + i * 18))

        # 工程师统计
        engineer_col_x = self.statistics_panel_rect.x + 200

        engineer_texts = [
            "=== 工程师统计 ===",
            f"总工程师: {engineer_stats['total_engineers']}",
            f"基础: {engineer_stats['by_type'].get('basic', 0)}",
            f"专业: {engineer_stats['by_type'].get('specialist', 0)}",
            f"大师: {engineer_stats['by_type'].get('master', 0)}",
            f"平均效率: {engineer_stats['efficiency_stats']['average_efficiency']:.1f}x"
        ]

        for i, text in enumerate(engineer_texts):
            color = (255, 215, 0) if text.startswith(
                "===") else (200, 200, 200)
            text_surface = self.font_manager.safe_render(
                self.small_font, text, color)
            screen.blit(text_surface, (engineer_col_x, stats_y + i * 18))

        # 分类统计
        category_col_x = self.statistics_panel_rect.x + 390

        category_texts = ["=== 建筑分类 ==="]
        for category, count in building_stats['by_category'].items():
            category_name = self._get_category_display_name_by_value(category)
            category_texts.append(f"{category_name}: {count}")

        for i, text in enumerate(category_texts):
            color = (255, 215, 0) if text.startswith(
                "===") else (200, 200, 200)
            text_surface = self.font_manager.safe_render(
                self.small_font, text, color)
            screen.blit(text_surface, (category_col_x, stats_y + i * 18))

    def _render_building_info_panel(self, screen: pygame.Surface):
        """渲染建筑信息面板"""
        # 建筑信息面板已移除，此方法保留为空
        pass

    def _render_hotkey_hints(self, screen: pygame.Surface):
        """渲染快捷键提示"""
        hints = [
            "2 - 建筑面板",
            "TAB - 统计面板",
            "5 - 地精工程师",
            "右键 - 关闭面板"
        ]

        hint_y = self.screen_height - 80
        for i, hint in enumerate(hints):
            text_surface = self.font_manager.safe_render(
                self.small_font, hint, (150, 150, 150)
            )
            screen.blit(text_surface, (10, hint_y + i * 16))

    def _get_category_display_name(self, category: BuildingCategory) -> str:
        """获取建筑分类显示名称"""
        names = {
            BuildingCategory.INFRASTRUCTURE: "基础设施",
            BuildingCategory.FUNCTIONAL: "功能建筑",
            BuildingCategory.MILITARY: "军事建筑",
            BuildingCategory.MAGICAL: "魔法建筑"
        }
        return names.get(category, category.value)

    def _get_category_display_name_by_value(self, category_value: str) -> str:
        """根据值获取建筑分类显示名称"""
        names = {
            "infrastructure": "基础设施",
            "functional": "功能建筑",
            "military": "军事建筑",
            "magical": "魔法建筑"
        }
        return names.get(category_value, category_value)

    def _update_building_list(self):
        """更新建筑列表"""
        self.building_scroll_offset = 0

    def get_selected_building_type(self) -> Optional[BuildingType]:
        """获取选中的建筑类型"""
        return self.selected_building_type

    def clear_selections(self):
        """清空所有选择"""
        self.selected_building_type = None
        self.selected_building_category = None

    # 建筑信息面板相关方法已移除

    def _get_goblin_engineer_count(self, building_manager) -> int:
        """获取地精工程师计数"""
        if not building_manager:
            return 0

        # 从建筑管理器中统计地精工程师数量
        from src.entities.goblin_engineer import EngineerType
        return len([eng for eng in building_manager.engineers
                   if eng.engineer_type == EngineerType.BASIC])

    def set_goblin_engineer_count(self, count: int):
        """设置地精工程师计数（从游戏主循环传入）"""
        self.goblin_engineer_count = count

    def render_building_appearance(self, screen: pygame.Surface, building_type: str,
                                   screen_x: int, screen_y: int, tile_size: int, tile=None):
        """
        渲染建筑外观

        Args:
            screen: pygame屏幕表面
            building_type: 建筑类型
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            tile: 瓦片对象（可选，用于获取额外信息）
        """
        if building_type == 'treasury':
            self._render_treasury_appearance(
                screen, screen_x, screen_y, tile_size, tile)
        elif building_type == 'dungeon_heart':
            self._render_dungeon_heart_appearance(
                screen, screen_x, screen_y, tile_size, tile)
        elif building_type == 'lair':
            self._render_lair_appearance(
                screen, screen_x, screen_y, tile_size, tile)
        else:
            self._render_default_building_appearance(
                screen, building_type, screen_x, screen_y, tile_size, tile)

    def _render_treasury_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                    tile_size: int, tile=None):
        """渲染金库外观 - 现代化设计"""
        # 金库渲染开始
        # 金库基础颜色配置
        base_color = (255, 215, 0)        # 金黄色
        border_color = (184, 134, 11)     # 深金色
        highlight_color = (255, 255, 150)  # 高光色
        shadow_color = (139, 69, 19)      # 阴影色

        # 绘制主背景 - 渐变效果
        main_rect = pygame.Rect(
            screen_x + 1, screen_y + 1, tile_size - 2, tile_size - 2)
        pygame.draw.rect(screen, base_color, main_rect)

        # 绘制阴影效果
        shadow_rect = pygame.Rect(
            screen_x + 3, screen_y + 3, tile_size - 4, tile_size - 4)
        pygame.draw.rect(screen, shadow_color, shadow_rect)

        # 绘制高光效果
        highlight_rect = pygame.Rect(
            screen_x + 2, screen_y + 2, tile_size - 6, tile_size - 6)
        pygame.draw.rect(screen, highlight_color, highlight_rect)

        # 绘制边框 - 双层边框效果
        outer_border = pygame.Rect(
            screen_x, screen_y, tile_size, tile_size)
        inner_border = pygame.Rect(
            screen_x + 2, screen_y + 2, tile_size - 4, tile_size - 4)
        pygame.draw.rect(screen, border_color, outer_border, 2)
        pygame.draw.rect(screen, (255, 255, 255), inner_border, 1)

        # 绘制金库图标 - 保险箱设计
        center_x = screen_x + tile_size // 2
        center_y = screen_y + tile_size // 2

        # 绘制保险箱主体
        safe_rect = pygame.Rect(
            center_x - 8, center_y - 6, 16, 12)
        pygame.draw.rect(screen, (200, 200, 200), safe_rect)
        pygame.draw.rect(screen, (100, 100, 100), safe_rect, 2)

        # 绘制保险箱门
        door_rect = pygame.Rect(
            center_x - 6, center_y - 4, 12, 8)
        pygame.draw.rect(screen, (150, 150, 150), door_rect)
        pygame.draw.rect(screen, (80, 80, 80), door_rect, 1)

        # 绘制保险箱把手
        handle_rect = pygame.Rect(
            center_x + 2, center_y - 1, 3, 2)
        pygame.draw.rect(screen, (100, 100, 100), handle_rect)

        # 绘制金币符号
        coin_text = self.font_manager.safe_render(
            self.small_font, "💰", (255, 255, 255))
        coin_rect = coin_text.get_rect(center=(center_x, center_y + 8))
        screen.blit(coin_text, coin_rect)

        # 绘制装饰性边框 - 四个角的装饰
        corner_size = 3
        corners = [
            (screen_x + 1, screen_y + 1),  # 左上
            (screen_x + tile_size - 4, screen_y + 1),  # 右上
            (screen_x + 1, screen_y + tile_size - 4),  # 左下
            (screen_x + tile_size - 4, screen_y + tile_size - 4)  # 右下
        ]
        for cx, cy in corners:
            pygame.draw.rect(screen, (255, 255, 255),
                             (cx, cy, corner_size, corner_size))

    def _render_dungeon_heart_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                         tile_size: int, tile=None):
        """渲染地牢之心外观 - 2x2瓦片适配版本"""

        # 检查是否是2x2地牢之心的中心瓦片
        is_center_tile = True
        if (hasattr(tile, 'is_dungeon_heart_part') and tile.is_dungeon_heart_part and
                hasattr(tile, 'dungeon_heart_center')):
            # 需要从tile对象获取当前瓦片坐标来判断是否是中心
            # 这里我们假设传入的screen_x, screen_y对应的是中心瓦片
            is_center_tile = True

        if is_center_tile:
            # 中心瓦片：渲染完整的2x2地牢之心
            self._render_2x2_dungeon_heart(
                screen, screen_x, screen_y, tile_size, tile)
        else:
            # 边缘瓦片：只渲染深红色背景
            heart_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                        tile_size - 2, tile_size - 2)
            pygame.draw.rect(screen, (139, 0, 0), heart_bg_rect)  # 深红色背景

    def _render_2x2_dungeon_heart(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                  tile_size: int, tile=None):
        """渲染2x2地牢之心的完整外观"""
        # 计算2x2区域的总尺寸
        total_width = tile_size * 2
        total_height = tile_size * 2

        # 背景：深红色渐变 - 覆盖2x2区域
        heart_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                    total_width - 2, total_height - 2)
        pygame.draw.rect(screen, (139, 0, 0), heart_bg_rect)  # 深红色背景

        # 边框：双层边框效果 - 覆盖2x2区域
        outer_border = pygame.Rect(
            screen_x, screen_y, total_width, total_height)
        inner_border = pygame.Rect(
            screen_x + 3, screen_y + 3, total_width - 6, total_height - 6)
        pygame.draw.rect(screen, (255, 0, 0), outer_border, 3)  # 外边框：鲜红色，更粗
        pygame.draw.rect(screen, (255, 69, 0), inner_border, 2)  # 内边框：橙红色，更粗

        # 中心装饰：心形符号 + 邪恶光环 - 居中在2x2区域
        center_x = screen_x + total_width // 2
        center_y = screen_y + total_height // 2

        # 使用更大的字体渲染心形符号
        heart_text = self.font_manager.safe_render(
            self.normal_font, "💖", (255, 255, 255))  # 使用normal_font，更大
        heart_rect = heart_text.get_rect(center=(center_x, center_y))
        screen.blit(heart_text, heart_rect)

        # 邪恶光环：四个角的装饰 - 适配2x2区域
        corner_size = 5  # 更大的装饰
        corners = [
            (screen_x + 2, screen_y + 2),  # 左上
            (screen_x + total_width - 7, screen_y + 2),  # 右上
            (screen_x + 2, screen_y + total_height - 7),  # 左下
            (screen_x + total_width - 7, screen_y + total_height - 7)  # 右下
        ]
        for cx, cy in corners:
            pygame.draw.rect(screen, (255, 0, 0),
                             (cx, cy, corner_size, corner_size))

        # 添加额外的装饰线条，增强2x2效果
        # 水平装饰线
        mid_y = screen_y + total_height // 2
        pygame.draw.line(screen, (255, 100, 100),
                         (screen_x + 10, mid_y), (screen_x + total_width - 10, mid_y), 2)

        # 垂直装饰线
        mid_x = screen_x + total_width // 2
        pygame.draw.line(screen, (255, 100, 100),
                         (mid_x, screen_y + 10), (mid_x, screen_y + total_height - 10), 2)

        # 为2x2地牢之心渲染适配的生命条
        self._render_2x2_dungeon_heart_health_bar(
            screen, screen_x, screen_y, tile_size, tile)

    def _render_2x2_dungeon_heart_health_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                             tile_size: int, tile=None):
        """渲染2x2地牢之心的生命条"""
        # 获取生命值信息
        health = 0
        max_health = 0

        if tile and hasattr(tile, 'health') and hasattr(tile, 'max_health'):
            health = tile.health
            max_health = tile.max_health

        if max_health <= 0:
            return

        # 计算生命值比例
        health_ratio = min(health / max_health, 1.0)

        # 2x2地牢之心的生命条尺寸和位置
        total_width = tile_size * 2
        total_height = tile_size * 2  # 添加缺失的total_height定义
        bar_width = total_width - 16  # 更宽的生命条
        bar_height = 6  # 更高的生命条
        bar_x = screen_x + 8
        bar_y = screen_y + total_height - 12  # 位置调整

        # 绘制背景条
        bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (100, 0, 0), bar_bg_rect)  # 深红色背景
        pygame.draw.rect(screen, (150, 0, 0), bar_bg_rect, 1)  # 深红色边框

        # 绘制生命条
        if health_ratio > 0:
            bar_fill_width = int(bar_width * health_ratio)
            bar_fill_rect = pygame.Rect(
                bar_x, bar_y, bar_fill_width, bar_height)

            # 根据生命值百分比选择颜色
            if health_ratio > 0.6:
                health_color = (0, 255, 0)  # 绿色（健康）
            elif health_ratio > 0.3:
                health_color = (255, 255, 0)  # 黄色（警告）
            else:
                health_color = (255, 0, 0)  # 红色（危险）

            pygame.draw.rect(screen, health_color, bar_fill_rect)

        # 生命值数字显示已移除，只显示生命条

    def _render_lair_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                tile_size: int, tile=None):
        """渲染巢穴外观"""
        # 背景：深棕色
        lair_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                   tile_size - 2, tile_size - 2)
        pygame.draw.rect(screen, (101, 67, 33), lair_bg_rect)  # 深棕色背景

        # 边框：棕色边框
        border_rect = pygame.Rect(screen_x, screen_y, tile_size, tile_size)
        pygame.draw.rect(screen, (139, 69, 19), border_rect, 2)  # 马鞍棕色边框

        # 中心装饰：巢穴符号
        center_x = screen_x + tile_size // 2
        center_y = screen_y + tile_size // 2
        lair_text = self.font_manager.safe_render(
            self.small_font, "🏠", (255, 255, 255))  # 白色房屋
        lair_rect = lair_text.get_rect(center=(center_x, center_y))
        screen.blit(lair_text, lair_rect)

    def _render_arrow_tower_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                       tile_size: int, tile=None):
        """渲染箭塔外观 - 尖顶塔设计"""
        # 箭塔颜色配置
        tower_base_color = (169, 169, 169)    # 石灰色主体
        tower_roof_color = (105, 105, 105)    # 深灰色尖顶
        tower_border_color = (80, 80, 80)     # 深灰色边框
        tower_highlight_color = (200, 200, 200)  # 高光色
        tower_shadow_color = (100, 100, 100)  # 阴影色

        # 计算塔的尺寸和位置
        center_x = screen_x + tile_size // 2
        center_y = screen_y + tile_size // 2

        # 塔身主体 - 矩形底座
        tower_base_width = tile_size - 8
        tower_base_height = tile_size - 12
        tower_base_x = screen_x + 4
        tower_base_y = screen_y + 8

        # 绘制塔身阴影
        shadow_rect = pygame.Rect(
            tower_base_x + 2, tower_base_y + 2,
            tower_base_width, tower_base_height
        )
        pygame.draw.rect(screen, tower_shadow_color, shadow_rect)

        # 绘制塔身主体
        tower_rect = pygame.Rect(
            tower_base_x, tower_base_y,
            tower_base_width, tower_base_height
        )
        pygame.draw.rect(screen, tower_base_color, tower_rect)

        # 绘制塔身边框
        pygame.draw.rect(screen, tower_border_color, tower_rect, 2)

        # 绘制塔身高光
        highlight_rect = pygame.Rect(
            tower_base_x + 2, tower_base_y + 2,
            tower_base_width - 4, 4
        )
        pygame.draw.rect(screen, tower_highlight_color, highlight_rect)

        # 绘制尖顶 - 三角形
        roof_points = [
            (center_x, screen_y + 2),  # 塔尖
            (screen_x + 6, tower_base_y),  # 左下角
            (screen_x + tile_size - 6, tower_base_y)  # 右下角
        ]

        # 绘制尖顶阴影
        shadow_roof_points = [
            (center_x + 1, screen_y + 3),
            (screen_x + 7, tower_base_y + 1),
            (screen_x + tile_size - 5, tower_base_y + 1)
        ]
        pygame.draw.polygon(screen, tower_shadow_color, shadow_roof_points)

        # 绘制尖顶主体
        pygame.draw.polygon(screen, tower_roof_color, roof_points)
        pygame.draw.polygon(screen, tower_border_color, roof_points, 2)

        # 绘制箭塔装饰 - 射击孔
        arrow_slot_width = 8
        arrow_slot_height = 4
        arrow_slot_x = center_x - arrow_slot_width // 2
        arrow_slot_y = tower_base_y + tower_base_height // 2 - arrow_slot_height // 2

        # 射击孔背景
        arrow_slot_rect = pygame.Rect(
            arrow_slot_x, arrow_slot_y, arrow_slot_width, arrow_slot_height
        )
        pygame.draw.rect(screen, (50, 50, 50), arrow_slot_rect)

        # 射击孔边框
        pygame.draw.rect(screen, (30, 30, 30), arrow_slot_rect, 1)

        # 绘制箭矢装饰
        arrow_text = self.font_manager.safe_render(
            self.small_font, "🏹", (255, 255, 255)
        )
        arrow_rect = arrow_text.get_rect(center=(center_x, arrow_slot_y - 8))
        screen.blit(arrow_text, arrow_rect)

        # 绘制塔顶旗帜装饰
        flag_pole_x = center_x
        flag_pole_y = screen_y + 2
        flag_height = 6

        # 旗杆
        pygame.draw.line(screen, (139, 69, 19),
                         (flag_pole_x, flag_pole_y),
                         (flag_pole_x, flag_pole_y + flag_height), 2)

        # 旗帜
        flag_points = [
            (flag_pole_x, flag_pole_y + 1),
            (flag_pole_x + 4, flag_pole_y + 2),
            (flag_pole_x, flag_pole_y + 3)
        ]
        pygame.draw.polygon(screen, (220, 20, 60), flag_points)  # 深红色旗帜

        # 绘制塔身纹理 - 石砖效果
        brick_width = 4
        brick_height = 3
        for row in range(2):
            for col in range(tower_base_width // brick_width):
                brick_x = tower_base_x + col * brick_width
                brick_y = tower_base_y + 8 + row * brick_height

                if brick_x + brick_width <= tower_base_x + tower_base_width:
                    brick_rect = pygame.Rect(
                        brick_x, brick_y, brick_width - 1, brick_height - 1)
                    pygame.draw.rect(screen, (150, 150, 150), brick_rect, 1)

        # 绘制塔基 - 地基
        foundation_rect = pygame.Rect(
            screen_x + 2, screen_y + tile_size - 4,
            tile_size - 4, 3
        )
        pygame.draw.rect(screen, (120, 120, 120), foundation_rect)
        pygame.draw.rect(screen, (100, 100, 100), foundation_rect, 1)

    def _render_default_building_appearance(self, screen: pygame.Surface, building_type: str,
                                            screen_x: int, screen_y: int, tile_size: int, tile=None):
        """渲染默认建筑外观"""
        # 特殊处理箭塔 - 使用专门的尖顶塔设计
        if building_type == 'arrow_tower':
            self._render_arrow_tower_appearance(
                screen, screen_x, screen_y, tile_size, tile)
            return

        # 根据建筑类型获取颜色
        building_colors = {
            'treasury': (255, 170, 0),  # 金库 - 金色
            'lair': (101, 67, 33),      # 巢穴 - 棕色
            'training_room': (112, 128, 144),  # 训练室 - 灰蓝色
            'library': (25, 25, 112),   # 图书馆 - 深蓝色
            'workshop': (139, 69, 19),  # 工坊 - 棕色
            'prison': (105, 105, 105),  # 监狱 - 深灰色
            'torture_chamber': (139, 0, 0),  # 刑房 - 深红色
            'defense_fortification': (169, 169, 169),  # 防御工事 - 灰色
            'magic_altar': (138, 43, 226),  # 魔法祭坛 - 紫色
            'shadow_temple': (72, 61, 139),  # 暗影神殿 - 暗紫色
            'magic_research_institute': (65, 105, 225),  # 魔法研究院 - 蓝色
            'advanced_gold_mine': (255, 215, 0),  # 高级金矿 - 金黄色
        }

        color = building_colors.get(building_type, (128, 128, 128))  # 默认灰色

        # 绘制建筑
        building_rect = pygame.Rect(
            screen_x + 1, screen_y + 1, tile_size - 2, tile_size - 2)
        pygame.draw.rect(screen, color, building_rect)

        # 绘制边框
        border_rect = pygame.Rect(screen_x, screen_y, tile_size, tile_size)
        pygame.draw.rect(screen, (50, 50, 50), border_rect, 1)

    def render_building_health_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                   tile_size: int, tile=None, building=None):
        """
        渲染建筑生命条 - 统一的生命值渲染方法

        Args:
            screen: pygame屏幕表面
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            tile: 瓦片对象（可选）
            building: 建筑对象（可选）
        """
        # 获取生命值信息
        health = 0
        max_health = 0

        if tile and hasattr(tile, 'health') and hasattr(tile, 'max_health'):
            health = tile.health
            max_health = tile.max_health
        elif building and hasattr(building, 'health') and hasattr(building, 'max_health'):
            health = building.health
            max_health = building.max_health

        if max_health <= 0:
            return

        # 计算生命值比例
        health_ratio = min(health / max_health, 1.0)

        # 生命条尺寸和位置
        bar_width = tile_size - 8
        bar_height = 4
        bar_x = screen_x + 4
        bar_y = screen_y + tile_size - 8

        # 绘制背景条
        bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (100, 0, 0), bar_bg_rect)  # 深红色背景
        pygame.draw.rect(screen, (150, 0, 0), bar_bg_rect, 1)  # 深红色边框

        # 绘制生命条
        if health_ratio > 0:
            bar_fill_width = int(bar_width * health_ratio)
            bar_fill_rect = pygame.Rect(
                bar_x, bar_y, bar_fill_width, bar_height)

            # 根据生命值百分比选择颜色
            if health_ratio > 0.6:
                health_color = (0, 255, 0)  # 绿色（健康）
            elif health_ratio > 0.3:
                health_color = (255, 255, 0)  # 黄色（警告）
            else:
                health_color = (255, 0, 0)  # 红色（危险）

            pygame.draw.rect(screen, health_color, bar_fill_rect)

        # 生命值数字显示已移除，只显示生命条
