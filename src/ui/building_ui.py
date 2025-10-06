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

    def __init__(self, screen_width: int, screen_height: int, font_manager, game_instance=None):
        """
        初始化建筑UI

        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            font_manager: 字体管理器
            game_instance: 游戏实例引用（可选）
        """
        super().__init__(font_manager)
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.game_instance = game_instance  # 接受外部传入的游戏实例

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
                self.building_scroll_offset -= event.y * GameConstants.SCROLL_SPEED
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

    def render(self, screen: pygame.Surface, building_manager=None, game_state=None, ui_scale: float = 1.0):
        """
        渲染建筑UI

        Args:
            screen: pygame屏幕表面
            building_manager: 建筑管理器
            game_state: 游戏状态
            ui_scale: UI缩放倍数
        """
        # 渲染建筑面板
        if self.show_building_panel:
            self._render_building_panel(
                screen, building_manager, game_state, ui_scale)

        # 渲染统计面板
        if self.show_statistics_panel:
            self._render_statistics_panel(screen, building_manager)

        # 渲染建筑信息面板
        # 建筑信息面板已移除

        # 渲染快捷键提示
        self._render_hotkey_hints(screen)

    def _render_building_panel(self, screen: pygame.Surface, building_manager, game_state, ui_scale: float = 1.0):
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
            self.title_font, emoji_constants.BUILD, Colors.GOLD, False, ui_scale
        )
        title_text = self.font_manager.safe_render(
            self.title_font, "建筑系统", Colors.GOLD, False, ui_scale
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
            self.small_font, emoji_constants.HAMMER, Colors.SUCCESS, False, ui_scale
        )
        # 动态获取地精工程师计数
        current_count = self._get_goblin_engineer_count(
            building_manager) if building_manager else self.goblin_engineer_count
        engineer_text = self.font_manager.safe_render(
            self.small_font, f"地精工程师: {current_count}", Colors.SUCCESS, False, ui_scale
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
            self._render_building_list(
                screen, building_manager, game_state, ui_scale)

    def _render_building_list(self, screen: pygame.Surface, building_manager, game_state, ui_scale: float = 1.0):
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
                self.building_panel_rect.x + GameConstants.BUTTON_PADDING,
                button_y,
                self.building_panel_rect.width - GameConstants.BUTTON_PADDING * 2,
                button_height
            )

            # 检查是否可以建造
            can_build = True
            if building_manager and game_state:
                # 这里需要实际的位置信息，暂时假设可以建造
                # 使用ResourceManager检查资源
                from src.managers.resource_manager import get_resource_manager
                resource_manager = get_resource_manager(self.game_instance)
                can_build = resource_manager.can_afford(
                    gold_cost=config.cost_gold)

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
                self.normal_font, config.name, Colors.WHITE, False, ui_scale
            )
            screen.blit(name_surface, (content_x, content_y))

            # 成本信息
            cost_text = f"{config.cost_gold}金"

            cost_color = Colors.GOLD if can_build else Colors.GRAY_500
            cost_surface = self.font_manager.safe_render(
                self.small_font, cost_text, cost_color, False, ui_scale
            )
            screen.blit(cost_surface, (content_x, content_y +
                        GameConstants.TEXT_LINE_SPACING))

            # 建造时间
            time_text = f"⏱️ {config.build_time:.0f}秒"
            time_surface = self.font_manager.safe_render(
                self.small_font, time_text, Colors.GRAY_400, False, ui_scale
            )
            screen.blit(time_surface, (button_rect.right - GameConstants.TEXT_RIGHT_OFFSET,
                        content_y + GameConstants.TEXT_LINE_SPACING))

            # 建筑等级星星
            stars = "⭐" * config.level
            stars_surface = self.font_manager.safe_render(
                self.small_font, stars, Colors.GOLD, False, ui_scale
            )
            screen.blit(stars_surface, (button_rect.right -
                        GameConstants.STARS_RIGHT_OFFSET, content_y))

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
        panel_surface.fill(Colors.DARK_SURFACE)
        screen.blit(panel_surface, self.engineer_panel_rect.topleft)

        # 绘制边框
        pygame.draw.rect(screen, Colors.GRAY_600, self.engineer_panel_rect, 2)

        # 分别渲染工程师面板的表情符号和标题文字
        engineer_emoji_text = self.font_manager.safe_render(
            self.title_font, emoji_constants.HAMMER, Colors.GOLD
        )
        engineer_title_text = self.font_manager.safe_render(
            self.title_font, "工程师", Colors.GOLD
        )

        # 渲染工程师面板表情符号和标题
        engineer_start_x = self.engineer_panel_rect.x + 10
        engineer_y = self.engineer_panel_rect.y + 5

        screen.blit(engineer_emoji_text, (engineer_start_x, engineer_y))
        screen.blit(engineer_title_text, (engineer_start_x +
                    engineer_emoji_text.get_width() + 8, engineer_y))

        # 绘制工程师按钮
        for button in self.engineer_buttons:
            # 使用ResourceManager检查资源
            if game_state:
                from src.managers.resource_manager import get_resource_manager
                resource_manager = get_resource_manager(self.game_instance)
                can_summon = resource_manager.can_afford(
                    gold_cost=button['config'].cost)
            else:
                can_summon = False

            if button['type'] == self.selected_engineer_type:
                color = Colors.PRIMARY
            elif can_summon:
                color = Colors.GRAY_800
            else:
                color = Colors.DISABLED_RED

            pygame.draw.rect(screen, color, button['rect'])
            pygame.draw.rect(screen, Colors.GRAY_400, button['rect'], 1)

            # 工程师信息
            name_text = button['config'].name
            cost_text = f"{button['config'].cost}金"
            efficiency_text = f"效率: {button['config'].build_efficiency}x"

            name_surface = self.font_manager.safe_render(
                self.small_font, name_text, Colors.WHITE
            )
            cost_surface = self.font_manager.safe_render(
                self.small_font, cost_text, Colors.GOLD if can_summon else Colors.GRAY_400
            )
            efficiency_surface = self.font_manager.safe_render(
                self.small_font, efficiency_text, Colors.GRAY_300
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
                self.small_font, text, Colors.GRAY_300
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
            self.title_font, emoji_constants.CHART, Colors.GOLD
        )
        stats_title_text = self.font_manager.safe_render(
            self.title_font, "建筑统计", Colors.GOLD
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
            f"总花费: {building_stats['construction_stats']['total_gold_spent']}金"
        ]

        for i, text in enumerate(building_texts):
            color = Colors.GOLD if text.startswith(
                "===") else Colors.GRAY_300
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
            color = Colors.GOLD if text.startswith(
                "===") else Colors.GRAY_300
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
            color = Colors.GOLD if text.startswith(
                "===") else Colors.GRAY_300
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
                self.small_font, hint, Colors.GRAY_500
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
        from src.entities.monster.goblin_engineer import EngineerType
        return len([eng for eng in building_manager.engineers
                   if eng.engineer_type == EngineerType.BASIC])

    def set_goblin_engineer_count(self, count: int):
        """设置地精工程师计数（从游戏主循环传入）"""
        self.goblin_engineer_count = count

    def render_building_appearance(self, screen: pygame.Surface, building_type: str,
                                   screen_x: int, screen_y: int, tile_size: int, tile=None, ui_scale: float = 1.0):
        """
        渲染建筑外观

        Args:
            screen: pygame屏幕表面
            building_type: 建筑类型
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            tile: 瓦片对象（可选，用于获取额外信息）
            ui_scale: UI缩放倍数
        """
        if building_type == 'treasury':
            self._render_treasury_appearance(
                screen, screen_x, screen_y, tile_size, tile, ui_scale)
        elif building_type == 'dungeon_heart':
            self._render_2x2_dungeon_heart(
                screen, screen_x, screen_y, tile_size, tile, ui_scale)
        elif building_type == 'arrow_tower':
            self._render_arrow_tower_appearance(
                screen, screen_x, screen_y, tile_size, tile, ui_scale)
        elif building_type == 'arcane_tower':
            self._render_arcane_tower_appearance(
                screen, screen_x, screen_y, tile_size, tile, ui_scale)
        elif building_type == 'magic_altar':
            self._render_magic_altar_appearance(
                screen, screen_x, screen_y, tile_size, tile, ui_scale)
        elif building_type == 'orc_lair':
            self._render_orc_lair_appearance(
                screen, screen_x, screen_y, tile_size, tile, ui_scale)
        elif building_type == 'demon_lair':
            self._render_demon_lair_appearance(
                screen, screen_x, screen_y, tile_size, tile, ui_scale)
        else:
            self._render_default_building_appearance(
                screen, building_type, screen_x, screen_y, tile_size, tile, ui_scale)

    def _render_treasury_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                    tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染金库外观 - 现代化设计"""
        # 金库渲染开始
        # 金库基础颜色配置
        base_color = (255, 215, 0)        # 金黄色
        border_color = (184, 134, 11)     # 深金色
        highlight_color = (255, 255, 150)  # 高光色
        shadow_color = (139, 69, 19)      # 阴影色

        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)
        border_width = max(1, int(2 * ui_scale))
        inner_border_width = max(1, int(1 * ui_scale))

        # 绘制主背景 - 渐变效果
        main_rect = pygame.Rect(
            screen_x + 1, screen_y + 1, scaled_tile_size - 2, scaled_tile_size - 2)
        pygame.draw.rect(screen, base_color, main_rect)

        # 绘制阴影效果
        shadow_rect = pygame.Rect(
            screen_x + 3, screen_y + 3, scaled_tile_size - 4, scaled_tile_size - 4)
        pygame.draw.rect(screen, shadow_color, shadow_rect)

        # 绘制高光效果
        highlight_rect = pygame.Rect(
            screen_x + 2, screen_y + 2, scaled_tile_size - 6, scaled_tile_size - 6)
        pygame.draw.rect(screen, highlight_color, highlight_rect)

        # 绘制边框 - 双层边框效果
        outer_border = pygame.Rect(
            screen_x, screen_y, scaled_tile_size, scaled_tile_size)
        inner_border = pygame.Rect(
            screen_x + 2, screen_y + 2, scaled_tile_size - 4, scaled_tile_size - 4)
        pygame.draw.rect(screen, border_color, outer_border, border_width)
        pygame.draw.rect(screen, (255, 255, 255),
                         inner_border, inner_border_width)

        # 绘制金库图标 - 保险箱设计
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2

        # 应用UI缩放到保险箱尺寸
        safe_width = int(16 * ui_scale)
        safe_height = int(12 * ui_scale)
        door_width = int(12 * ui_scale)
        door_height = int(8 * ui_scale)
        handle_width = max(1, int(3 * ui_scale))
        handle_height = max(1, int(2 * ui_scale))
        safe_border_width = max(1, int(2 * ui_scale))
        door_border_width = max(1, int(1 * ui_scale))

        # 绘制保险箱主体
        safe_rect = pygame.Rect(
            center_x - safe_width // 2, center_y - safe_height // 2, safe_width, safe_height)
        pygame.draw.rect(screen, (200, 200, 200), safe_rect)
        pygame.draw.rect(screen, (100, 100, 100), safe_rect, safe_border_width)

        # 绘制保险箱门
        door_rect = pygame.Rect(
            center_x - door_width // 2, center_y - door_height // 2, door_width, door_height)
        pygame.draw.rect(screen, (150, 150, 150), door_rect)
        pygame.draw.rect(screen, (80, 80, 80), door_rect, door_border_width)

        # 绘制保险箱把手
        handle_rect = pygame.Rect(
            center_x + int(2 * ui_scale), center_y - int(1 * ui_scale), handle_width, handle_height)
        pygame.draw.rect(screen, (100, 100, 100), handle_rect)

        # 绘制金币符号
        coin_text = self.font_manager.safe_render(
            self.small_font, "💰", (255, 255, 255))
        coin_rect = coin_text.get_rect(
            center=(center_x, center_y + int(8 * ui_scale)))
        screen.blit(coin_text, coin_rect)

        # 绘制装饰性边框 - 四个角的装饰
        corner_size = max(1, int(3 * ui_scale))
        corners = [
            (screen_x + 1, screen_y + 1),  # 左上
            (screen_x + scaled_tile_size - corner_size - 1, screen_y + 1),  # 右上
            (screen_x + 1, screen_y + scaled_tile_size - corner_size - 1),  # 左下
            (screen_x + scaled_tile_size - corner_size - 1,
             screen_y + scaled_tile_size - corner_size - 1)  # 右下
        ]
        for cx, cy in corners:
            pygame.draw.rect(screen, (255, 255, 255),
                             (cx, cy, corner_size, corner_size))

    def _render_magic_altar_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                       tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染魔法祭坛外观 - 神秘的魔法祭坛设计"""
        # 魔法祭坛颜色配置
        altar_base_color = (138, 43, 226)      # 蓝紫色主体
        altar_highlight_color = (186, 85, 211)  # 淡紫色高光
        altar_shadow_color = (75, 0, 130)      # 深紫色阴影
        altar_crystal_color = (147, 112, 219)  # 水晶色
        altar_gold_color = (255, 215, 0)       # 金色装饰
        altar_magic_color = (221, 160, 221)    # 魔法光效色

        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)
        border_width = max(1, int(2 * ui_scale))

        # 计算中心位置
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2

        # 绘制祭坛基座 - 圆形底座（确保在瓦片范围内）
        base_radius = int((scaled_tile_size - 8) // 2)  # 移除重复的ui_scale
        base_center = (center_x, center_y + int(4 * ui_scale))  # 减小偏移

        # 绘制基座阴影
        shadow_center = (base_center[0] + 2, base_center[1] + 2)
        pygame.draw.circle(screen, altar_shadow_color,
                           shadow_center, base_radius)

        # 绘制基座主体
        pygame.draw.circle(screen, altar_base_color, base_center, base_radius)
        pygame.draw.circle(screen, altar_highlight_color,
                           base_center, base_radius, border_width)

        # 绘制祭坛台面 - 圆形平台（确保在瓦片范围内）
        platform_radius = int(base_radius * 0.7)  # 减小平台大小
        platform_center = (center_x, center_y - int(2 * ui_scale))  # 减小偏移

        # 绘制台面阴影
        platform_shadow = (platform_center[0] + 1, platform_center[1] + 1)
        pygame.draw.circle(screen, altar_shadow_color,
                           platform_shadow, platform_radius)

        # 绘制台面主体
        pygame.draw.circle(screen, altar_highlight_color,
                           platform_center, platform_radius)
        pygame.draw.circle(screen, altar_base_color,
                           platform_center, platform_radius, border_width)

        # 绘制魔法水晶 - 中心水晶球（确保在瓦片范围内）
        crystal_radius = int(4 * ui_scale)  # 减小水晶大小
        crystal_center = (center_x, center_y - int(4 * ui_scale))  # 减小偏移

        # 水晶球主体
        pygame.draw.circle(screen, altar_crystal_color,
                           crystal_center, crystal_radius)
        pygame.draw.circle(screen, altar_highlight_color,
                           crystal_center, crystal_radius, 1)

        # 水晶球内部高光
        inner_highlight_radius = int(crystal_radius * 0.6)
        highlight_center = (
            crystal_center[0] - int(2 * ui_scale), crystal_center[1] - int(2 * ui_scale))
        pygame.draw.circle(screen, altar_magic_color,
                           highlight_center, inner_highlight_radius)

        # 绘制魔法符文 - 围绕水晶的装饰符文（确保在瓦片范围内）
        rune_distance = int(platform_radius * 0.8)  # 符文距离平台边缘的距离
        rune_positions = [
            (center_x, platform_center[1] - rune_distance),  # 上方
            (center_x, platform_center[1] + rune_distance),  # 下方
            (center_x - rune_distance, platform_center[1]),  # 左侧
            (center_x + rune_distance, platform_center[1]),  # 右侧
        ]

        for rune_x, rune_y in rune_positions:
            # 绘制符文圆圈（确保在瓦片范围内）
            rune_circle_radius = int(2 * ui_scale)  # 减小符文圆圈大小
            pygame.draw.circle(screen, altar_gold_color,
                               (rune_x, rune_y), rune_circle_radius)
            pygame.draw.circle(screen, altar_base_color,
                               (rune_x, rune_y), rune_circle_radius, 1)

        # 绘制魔法光环 - 围绕整个祭坛的光环（完全移除）
        # halo_radius = int(base_radius + 3 * ui_scale)  # 减小光环半径
        # halo_center = (center_x, center_y)

        # 外层光环（完全移除）
        # halo_color = (*altar_magic_color[:3], 100)  # 降低透明度
        # pygame.draw.circle(screen, altar_magic_color, halo_center,
        #                    halo_radius, max(1, int(1 * ui_scale)))  # 减小线条宽度

        # 内层光环（移除，减少视觉干扰）
        # inner_halo_radius = int(halo_radius - 4 * ui_scale)
        # pygame.draw.circle(screen, altar_crystal_color, halo_center,
        #                    inner_halo_radius, max(1, int(1 * ui_scale)))

        # 绘制魔法符号 - 中心魔法符号（减弱效果）
        magic_symbol = self.font_manager.safe_render(
            self.small_font, "✦", (200, 200, 255))  # 使用更简单的符号和更淡的颜色
        symbol_rect = magic_symbol.get_rect(
            center=(crystal_center[0], crystal_center[1]))
        screen.blit(magic_symbol, symbol_rect)

        # 绘制装饰性边框 - 四个角的魔法符文（减弱效果）
        corner_size = max(1, int(2 * ui_scale))  # 减小装饰大小
        corner_offset = int(1 * ui_scale)  # 减小偏移
        corners = [
            (screen_x + corner_offset, screen_y + corner_offset),  # 左上
            (screen_x + scaled_tile_size - corner_size -
             corner_offset, screen_y + corner_offset),  # 右上
            (screen_x + corner_offset, screen_y +
             scaled_tile_size - corner_size - corner_offset),  # 左下
            (screen_x + scaled_tile_size - corner_size - corner_offset,
             screen_y + scaled_tile_size - corner_size - corner_offset)  # 右下
        ]

        for cx, cy in corners:
            # 使用更淡的颜色
            corner_color = (
                altar_gold_color[0] // 2, altar_gold_color[1] // 2, altar_gold_color[2] // 2)
            pygame.draw.rect(screen, corner_color,
                             (cx, cy, corner_size, corner_size))
            pygame.draw.rect(screen, altar_base_color,
                             (cx, cy, corner_size, corner_size), 1)

        # 绘制魔法能量线条 - 连接符文和中心的能量线（减弱效果）
        for rune_x, rune_y in rune_positions:
            # 绘制从符文到水晶的能量线（更细更淡）
            line_width = max(1, int(0.5 * ui_scale))  # 减小线条宽度
            # 使用更淡的颜色
            energy_color = (
                altar_magic_color[0] // 2, altar_magic_color[1] // 2, altar_magic_color[2] // 2)
            pygame.draw.line(screen, energy_color,
                             (rune_x, rune_y), crystal_center, line_width)

    def _render_2x2_dungeon_heart(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                  tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染地牢之心外观 - 2x2瓦片版本"""
        # 计算2x2区域的总尺寸，应用UI缩放
        scaled_tile_size = int(tile_size * ui_scale)
        total_width = scaled_tile_size * 2
        total_height = scaled_tile_size * 2

        # 背景：深红色渐变 - 覆盖2x2区域
        heart_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                    total_width - 2, total_height - 2)
        pygame.draw.rect(screen, (139, 0, 0), heart_bg_rect)  # 深红色背景

        # 边框：双层边框效果 - 覆盖2x2区域
        outer_border_width = max(1, int(3 * ui_scale))
        inner_border_width = max(1, int(2 * ui_scale))
        border_offset = max(1, int(3 * ui_scale))

        outer_border = pygame.Rect(
            screen_x, screen_y, total_width, total_height)
        inner_border = pygame.Rect(
            screen_x + border_offset, screen_y + border_offset,
            total_width - border_offset * 2, total_height - border_offset * 2)
        pygame.draw.rect(screen, (255, 0, 0), outer_border,
                         outer_border_width)  # 外边框：鲜红色，更粗
        pygame.draw.rect(screen, (255, 69, 0), inner_border,
                         inner_border_width)  # 内边框：橙红色，更粗

        # 中心装饰：心形符号 + 邪恶光环 - 居中在2x2区域
        center_x = screen_x + total_width // 2
        center_y = screen_y + total_height // 2

        # 使用更大的字体渲染心形符号
        heart_text = self.font_manager.safe_render(
            self.normal_font, "💖", (255, 255, 255))  # 使用normal_font，更大
        heart_rect = heart_text.get_rect(center=(center_x, center_y))
        screen.blit(heart_text, heart_rect)

        # 邪恶光环：四个角的装饰 - 适配2x2区域
        corner_size = max(1, int(5 * ui_scale))  # 更大的装饰
        corner_offset = max(1, int(2 * ui_scale))
        corners = [
            (screen_x + corner_offset, screen_y + corner_offset),  # 左上
            (screen_x + total_width - corner_size -
             corner_offset, screen_y + corner_offset),  # 右上
            (screen_x + corner_offset, screen_y +
             total_height - corner_size - corner_offset),  # 左下
            (screen_x + total_width - corner_size - corner_offset,
             screen_y + total_height - corner_size - corner_offset)  # 右下
        ]
        for cx, cy in corners:
            pygame.draw.rect(screen, (255, 0, 0),
                             (cx, cy, corner_size, corner_size))

        # 添加额外的装饰线条，增强2x2效果
        line_width = max(1, int(2 * ui_scale))
        line_offset = max(1, int(10 * ui_scale))

        # 水平装饰线
        mid_y = screen_y + total_height // 2
        pygame.draw.line(screen, (255, 100, 100),
                         (screen_x + line_offset, mid_y), (screen_x + total_width - line_offset, mid_y), line_width)

        # 垂直装饰线
        mid_x = screen_x + total_width // 2
        pygame.draw.line(screen, (255, 100, 100),
                         (mid_x, screen_y + line_offset), (mid_x, screen_y + total_height - line_offset), line_width)

        # 为2x2地牢之心渲染适配的生命条
        self._render_2x2_dungeon_heart_health_bar(
            screen, screen_x, screen_y, tile_size, tile, ui_scale)

    def _render_2x2_dungeon_heart_health_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                             tile_size: int, tile=None, ui_scale: float = 1.0):
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

        # 2x2地牢之心的生命条尺寸和位置，应用UI缩放
        scaled_tile_size = int(tile_size * ui_scale)
        total_width = scaled_tile_size * 2
        total_height = scaled_tile_size * 2
        bar_width = total_width - int(16 * ui_scale)  # 更宽的生命条
        bar_height = max(1, int(6 * ui_scale))  # 更高的生命条
        bar_x = screen_x + int(8 * ui_scale)
        bar_y = screen_y + total_height - int(12 * ui_scale)  # 位置调整

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

    def render_building_status_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                   tile_size: int, tile=None, building=None, ui_scale: float = 1.0):
        """
        渲染建筑状态条 - 显示弹药量、金币存储量等状态信息

        Args:
            screen: pygame屏幕表面
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            tile: 瓦片对象（可选）
            building: 建筑对象（可选）
            ui_scale: UI缩放倍数
        """
        # 获取建筑类型
        building_type = None
        if building and hasattr(building, 'building_type'):
            building_type = building.building_type.value
        elif tile and hasattr(tile, 'room_type'):
            building_type = tile.room_type

        # 根据建筑类型决定是否显示状态条
        if not building_type or building_type in ['dungeon_heart', 'lair', 'training_room', 'library', 'workshop', 'prison', 'torture_chamber', 'defense_fortification']:
            return  # 这些建筑不显示状态条

        # 获取状态信息
        status_value = 0
        max_status_value = 0
        status_color = GameConstants.STATUS_COLOR_DEFAULT  # 默认白色

        if building_type == 'arrow_tower':
            # 箭塔：显示弹药量（橙色）
            if building and hasattr(building, 'current_ammunition') and hasattr(building, 'max_ammunition'):
                status_value = building.current_ammunition
                max_status_value = building.max_ammunition
                status_color = GameConstants.STATUS_COLOR_AMMUNITION
        elif building_type == 'treasury':
            # 金库：显示金币存储量（金色）
            if building and hasattr(building, 'stored_gold') and hasattr(building, 'gold_storage_capacity'):
                status_value = building.stored_gold
                max_status_value = building.gold_storage_capacity
                status_color = Colors.GOLD
        elif building_type == 'magic_altar':
            # 魔法祭坛：显示法力存储量（紫色）
            if building and hasattr(building, 'stored_mana') and hasattr(building, 'mana_storage_capacity'):
                status_value = building.stored_mana
                max_status_value = building.mana_storage_capacity
                status_color = (0, 100, 255)  # 蓝色
        elif building_type == 'arcane_tower':
            # 奥术塔：显示魔力消耗状态（紫色）
            # 奥术塔不存储魔力，而是消耗地牢之心的魔力
            # 这里显示魔力消耗能力状态
            if building and hasattr(building, 'mana_per_shot'):
                # 检查是否有足够的魔力进行攻击
                if hasattr(building, 'game_instance') and building.game_instance:
                    from src.managers.resource_consumption_manager import ResourceConsumptionManager
                    consumption_manager = ResourceConsumptionManager(
                        building.game_instance)
                    can_afford, _ = consumption_manager.can_afford(
                        mana_cost=building.mana_per_shot)
                    if can_afford:
                        # 有足够魔力，显示为满状态
                        status_value = 1
                        max_status_value = 1
                        status_color = (147, 112, 219)  # 紫色
                    else:
                        # 魔力不足，显示为0状态
                        status_value = 0
                        max_status_value = 1
                        status_color = (100, 50, 150)  # 暗紫色
                else:
                    # 无法检查魔力状态，显示为未知
                    status_value = 0
                    max_status_value = 1
                    status_color = (100, 100, 100)  # 灰色
        elif building_type == 'orc_lair':
            # 兽人巢穴：显示训练进度（橙色/褐色）
            if building and hasattr(building, 'is_training') and hasattr(building, 'assigned_worker'):
                if building.is_training and building.assigned_worker:
                    # 训练中：显示进度
                    if hasattr(building, 'training_start_time') and hasattr(building, 'training_duration'):
                        import time
                        current_time = time.time()
                        training_elapsed = current_time - building.training_start_time
                        status_value = min(
                            training_elapsed, building.training_duration)
                        max_status_value = building.training_duration
                        status_color = (255, 165, 0)  # 橙色 - 训练中
                    else:
                        status_value = 0
                        max_status_value = 1
                        status_color = (255, 165, 0)  # 橙色
                elif building.assigned_worker and not building.is_training:
                    # 苦工已分配但未开始训练：显示等待状态
                    status_value = 0
                    max_status_value = 1
                    status_color = (139, 69, 19)  # 褐色 - 等待训练
                else:
                    # 没有苦工分配
                    return
        elif building_type == 'demon_lair':
            # 恶魔巢穴：显示召唤进度（青色/红色）
            if building and hasattr(building, 'is_summoning') and hasattr(building, 'is_summoning_paused'):
                if building.is_summoning:
                    # 召唤中：显示进度
                    if hasattr(building, 'summon_start_time') and hasattr(building, 'summon_duration'):
                        import time
                        current_time = time.time()
                        summon_elapsed = current_time - building.summon_start_time
                        status_value = min(
                            summon_elapsed, building.summon_duration)
                        max_status_value = building.summon_duration
                        status_color = (0, 255, 255)  # 青色 - 召唤中
                    else:
                        status_value = 0
                        max_status_value = 1
                        status_color = (0, 255, 255)  # 青色
                elif building.is_summoning_paused:
                    # 暂停召唤：显示暂停状态
                    if hasattr(building, 'summon_elapsed_time') and hasattr(building, 'summon_duration'):
                        status_value = building.summon_elapsed_time
                        max_status_value = building.summon_duration
                        status_color = (255, 0, 0)  # 红色 - 暂停召唤
                    else:
                        status_value = 0
                        max_status_value = 1
                        status_color = (255, 0, 0)  # 红色
                else:
                    # 不在召唤状态
                    return

        if max_status_value <= 0:
            return

        # 计算状态值比例
        status_ratio = min(status_value / max_status_value, 1.0)

        # 状态条尺寸和位置，应用UI缩放
        # 位于生命条下方，长度和生命条一样，宽度为生命条的一半
        scaled_tile_size = int(tile_size * ui_scale)
        bar_width = scaled_tile_size - \
            int(GameConstants.STATUS_BAR_PADDING * ui_scale)  # 与生命条相同长度
        bar_height = max(
            1, int(GameConstants.STATUS_BAR_HEIGHT * ui_scale))  # 生命条高度的一半
        bar_x = screen_x + int(GameConstants.STATUS_BAR_OFFSET * ui_scale)
        bar_y = screen_y + scaled_tile_size - \
            int(GameConstants.STATUS_BAR_OFFSET * ui_scale)  # 生命条下方

        # 绘制背景条
        bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        # 使用更暗的背景色
        bg_color = tuple(max(0, int(c * 0.3)) for c in status_color)
        pygame.draw.rect(screen, bg_color, bar_bg_rect)
        pygame.draw.rect(screen, tuple(max(0, int(c * 0.5))
                         for c in status_color), bar_bg_rect, 1)

        # 绘制状态条
        if status_ratio > 0:
            bar_fill_width = int(bar_width * status_ratio)
            bar_fill_rect = pygame.Rect(
                bar_x, bar_y, bar_fill_width, bar_height)
            pygame.draw.rect(screen, status_color, bar_fill_rect)

    def _render_lair_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染巢穴外观"""
        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)
        border_width = max(
            1, int(GameConstants.BUILDING_BORDER_WIDTH * ui_scale))

        # 背景：深棕色
        lair_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                   scaled_tile_size - 2, scaled_tile_size - 2)
        pygame.draw.rect(screen, (101, 67, 33), lair_bg_rect)  # 深棕色背景

        # 边框：棕色边框
        border_rect = pygame.Rect(
            screen_x, screen_y, scaled_tile_size, scaled_tile_size)
        pygame.draw.rect(screen, (139, 69, 19), border_rect,
                         border_width)  # 马鞍棕色边框

        # 中心装饰：巢穴符号
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2
        lair_text = self.font_manager.safe_render(
            self.small_font, "🏠", (255, 255, 255))  # 白色房屋
        lair_rect = lair_text.get_rect(center=(center_x, center_y))
        screen.blit(lair_text, lair_rect)

    def _render_arrow_tower_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                       tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染箭塔外观 - 尖顶塔设计"""
        # 箭塔颜色配置
        tower_base_color = (169, 169, 169)    # 石灰色主体
        tower_roof_color = (105, 105, 105)    # 深灰色尖顶
        tower_border_color = (80, 80, 80)     # 深灰色边框
        tower_highlight_color = (200, 200, 200)  # 高光色
        tower_shadow_color = (100, 100, 100)  # 阴影色

        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)

        # 计算塔的尺寸和位置
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2

        # 塔身主体 - 矩形底座
        tower_base_width = scaled_tile_size - \
            int(GameConstants.STATUS_BAR_PADDING * ui_scale)
        tower_base_height = scaled_tile_size - int(12 * ui_scale)
        tower_base_x = screen_x + \
            int(GameConstants.STATUS_BAR_OFFSET * ui_scale)
        tower_base_y = screen_y + \
            int(GameConstants.ARROW_TOWER_BASE_OFFSET * ui_scale)

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
        border_width = max(
            1, int(GameConstants.BUILDING_BORDER_WIDTH * ui_scale))
        pygame.draw.rect(screen, tower_border_color, tower_rect, border_width)

        # 绘制塔身高光
        highlight_rect = pygame.Rect(
            tower_base_x + 2, tower_base_y + 2,
            tower_base_width - 4, 4
        )
        pygame.draw.rect(screen, tower_highlight_color, highlight_rect)

        # 绘制尖顶 - 三角形
        roof_offset = int(GameConstants.ARROW_TOWER_ROOF_OFFSET * ui_scale)
        roof_points = [
            (center_x, screen_y + int(2 * ui_scale)),  # 塔尖
            (screen_x + roof_offset, tower_base_y),  # 左下角
            (screen_x + scaled_tile_size - roof_offset, tower_base_y)  # 右下角
        ]

        # 绘制尖顶阴影
        shadow_roof_points = [
            (center_x + 1, screen_y + int(3 * ui_scale)),
            (screen_x + roof_offset + 1, tower_base_y + 1),
            (screen_x + scaled_tile_size - roof_offset + 1, tower_base_y + 1)
        ]
        pygame.draw.polygon(screen, tower_shadow_color, shadow_roof_points)

        # 绘制尖顶主体
        pygame.draw.polygon(screen, tower_roof_color, roof_points)
        pygame.draw.polygon(screen, tower_border_color,
                            roof_points, border_width)

        # 绘制箭塔装饰 - 射击孔
        arrow_slot_width = int(GameConstants.ARROW_TOWER_SLOT_WIDTH * ui_scale)
        arrow_slot_height = int(
            GameConstants.ARROW_TOWER_SLOT_HEIGHT * ui_scale)
        arrow_slot_x = center_x - arrow_slot_width // 2
        arrow_slot_y = tower_base_y + tower_base_height // 2 - arrow_slot_height // 2

        # 射击孔背景
        arrow_slot_rect = pygame.Rect(
            arrow_slot_x, arrow_slot_y, arrow_slot_width, arrow_slot_height
        )
        pygame.draw.rect(screen, (50, 50, 50), arrow_slot_rect)

        # 射击孔边框
        pygame.draw.rect(screen, (30, 30, 30), arrow_slot_rect, 1)

        # 绘制塔顶旗帜装饰
        flag_pole_x = center_x
        flag_pole_y = screen_y + int(2 * ui_scale)
        flag_height = int(GameConstants.ARROW_TOWER_FLAG_HEIGHT * ui_scale)
        flag_line_width = max(
            1, int(GameConstants.BUILDING_BORDER_WIDTH * ui_scale))

        # 旗杆
        pygame.draw.line(screen, (139, 69, 19),
                         (flag_pole_x, flag_pole_y),
                         (flag_pole_x, flag_pole_y + flag_height), flag_line_width)

        # 旗帜
        flag_offset = int(GameConstants.ARROW_TOWER_FLAG_OFFSET * ui_scale)
        flag_points = [
            (flag_pole_x, flag_pole_y + 1),
            (flag_pole_x + flag_offset, flag_pole_y + 2),
            (flag_pole_x, flag_pole_y + 3)
        ]
        pygame.draw.polygon(screen, (220, 20, 60), flag_points)  # 深红色旗帜

        # 绘制塔身纹理 - 石砖效果
        brick_width = int(GameConstants.ARROW_TOWER_BRICK_WIDTH * ui_scale)
        brick_height = int(GameConstants.ARROW_TOWER_BRICK_HEIGHT * ui_scale)
        brick_offset = int(GameConstants.ARROW_TOWER_BRICK_OFFSET * ui_scale)
        for row in range(2):
            for col in range(tower_base_width // brick_width):
                brick_x = tower_base_x + col * brick_width
                brick_y = tower_base_y + brick_offset + row * brick_height

                if brick_x + brick_width <= tower_base_x + tower_base_width:
                    brick_rect = pygame.Rect(
                        brick_x, brick_y, brick_width - 1, brick_height - 1)
                    pygame.draw.rect(screen, (150, 150, 150), brick_rect, 1)

        # 绘制塔基 - 地基
        foundation_offset = int(
            GameConstants.BUILDING_FOUNDATION_OFFSET * ui_scale)
        foundation_height = int(
            GameConstants.BUILDING_FOUNDATION_HEIGHT * ui_scale)
        foundation_rect = pygame.Rect(
            screen_x + foundation_offset, screen_y +
            scaled_tile_size - int(GameConstants.STATUS_BAR_OFFSET * ui_scale),
            scaled_tile_size - foundation_offset * 2, foundation_height
        )
        pygame.draw.rect(screen, (120, 120, 120), foundation_rect)
        pygame.draw.rect(screen, (100, 100, 100), foundation_rect, 1)

    def _render_arcane_tower_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                        tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染奥术塔外观 - 神秘的魔法塔设计"""
        # 奥术塔颜色配置
        tower_base_color = (138, 43, 226)      # 蓝紫色主体
        tower_roof_color = (186, 85, 211)      # 淡紫色尖顶
        tower_border_color = (75, 0, 130)      # 深紫色边框
        tower_highlight_color = (221, 160, 221)  # 高光色
        tower_shadow_color = (72, 61, 139)     # 阴影色
        tower_magic_color = (147, 112, 219)    # 魔法光效色
        tower_crystal_color = (255, 255, 255)  # 水晶色
        tower_rune_color = (255, 215, 0)       # 符文金色

        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)

        # 计算塔的尺寸和位置
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2

        # 塔身主体 - 圆形底座（魔法塔特色）
        tower_base_radius = int((scaled_tile_size - 8) // 2)
        tower_base_center = (center_x, center_y + int(2 * ui_scale))

        # 绘制塔身阴影
        shadow_center = (tower_base_center[0] + 2, tower_base_center[1] + 2)
        pygame.draw.circle(screen, tower_shadow_color,
                           shadow_center, tower_base_radius)

        # 绘制塔身主体
        pygame.draw.circle(screen, tower_base_color,
                           tower_base_center, tower_base_radius)

        # 绘制塔身边框
        border_width = max(1, int(2 * ui_scale))
        pygame.draw.circle(screen, tower_border_color,
                           tower_base_center, tower_base_radius, border_width)

        # 绘制塔身高光
        highlight_radius = int(tower_base_radius * 0.8)
        highlight_center = (tower_base_center[0] - 2, tower_base_center[1] - 2)
        pygame.draw.circle(screen, tower_highlight_color,
                           highlight_center, highlight_radius, 1)

        # 绘制魔法尖顶 - 五角星形状（奥术塔特色）
        roof_offset = int(4 * ui_scale)
        star_size = int(8 * ui_scale)
        star_center = (center_x, screen_y + roof_offset)

        # 绘制五角星
        import math
        star_points = []
        for i in range(10):
            angle = math.pi * 2 * i / 10 - math.pi / 2
            if i % 2 == 0:
                # 外点
                radius = star_size
            else:
                # 内点
                radius = star_size * 0.4
            x = star_center[0] + radius * math.cos(angle)
            y = star_center[1] + radius * math.sin(angle)
            star_points.append((x, y))

        # 绘制星形阴影
        shadow_star_points = [(p[0] + 1, p[1] + 1) for p in star_points]
        pygame.draw.polygon(screen, tower_shadow_color, shadow_star_points)

        # 绘制星形主体
        pygame.draw.polygon(screen, tower_roof_color, star_points)
        pygame.draw.polygon(screen, tower_border_color,
                            star_points, border_width)

        # 绘制魔法水晶球 - 中心水晶
        crystal_radius = int(6 * ui_scale)
        crystal_center = (center_x, center_y - int(4 * ui_scale))

        # 水晶球阴影
        crystal_shadow = (crystal_center[0] + 1, crystal_center[1] + 1)
        pygame.draw.circle(screen, tower_shadow_color,
                           crystal_shadow, crystal_radius)

        # 水晶球主体
        pygame.draw.circle(screen, tower_crystal_color,
                           crystal_center, crystal_radius)
        pygame.draw.circle(screen, tower_magic_color,
                           crystal_center, crystal_radius, 1)

        # 水晶球内部高光
        inner_highlight_radius = int(crystal_radius * 0.6)
        highlight_center = (crystal_center[0] - 2, crystal_center[1] - 2)
        pygame.draw.circle(screen, tower_highlight_color,
                           highlight_center, inner_highlight_radius)

        # 绘制魔法符文 - 围绕塔身的装饰符文
        rune_distance = int(tower_base_radius * 0.8)
        rune_positions = [
            (center_x, tower_base_center[1] - rune_distance),  # 上方
            (center_x, tower_base_center[1] + rune_distance),  # 下方
            (center_x - rune_distance, tower_base_center[1]),  # 左侧
            (center_x + rune_distance, tower_base_center[1]),  # 右侧
        ]

        for rune_x, rune_y in rune_positions:
            # 绘制符文圆圈
            rune_radius = int(3 * ui_scale)
            pygame.draw.circle(screen, tower_rune_color,
                               (rune_x, rune_y), rune_radius)
            pygame.draw.circle(screen, tower_base_color,
                               (rune_x, rune_y), rune_radius, 1)

            # 绘制符文中心点
            center_radius = int(1 * ui_scale)
            pygame.draw.circle(screen, tower_crystal_color,
                               (rune_x, rune_y), center_radius)

        # 绘制魔法能量线条 - 连接符文和水晶的能量线
        for rune_x, rune_y in rune_positions:
            line_width = max(1, int(1 * ui_scale))
            pygame.draw.line(screen, tower_magic_color,
                             (rune_x, rune_y), crystal_center, line_width)

        # 绘制奥术塔装饰 - 魔法符号
        magic_symbol = self.font_manager.safe_render(
            self.small_font, "✦", (255, 255, 255)
        )
        symbol_rect = magic_symbol.get_rect(
            center=(crystal_center[0], crystal_center[1]))
        screen.blit(magic_symbol, symbol_rect)

        # 绘制塔基 - 魔法阵地基
        foundation_offset = int(2 * ui_scale)
        foundation_height = int(4 * ui_scale)
        foundation_radius = int(tower_base_radius + 2)
        foundation_center = (center_x, screen_y +
                             scaled_tile_size - foundation_height)

        # # 绘制魔法阵
        # pygame.draw.circle(screen, tower_magic_color,
        #                    foundation_center, foundation_radius, border_width)

        # # 绘制魔法阵内圈
        # inner_radius = int(foundation_radius * 0.7)
        # pygame.draw.circle(screen, tower_highlight_color,
        #                    foundation_center, inner_radius, 1)

        # # 绘制魔法阵中心点
        # center_radius = int(2 * ui_scale)
        # pygame.draw.circle(screen, tower_crystal_color,
        #                    foundation_center, center_radius)

        # 装饰性魔法光环已移除

    def _render_orc_lair_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                    tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染兽人巢穴外观 - 野蛮的军事建筑设计"""
        # 兽人巢穴颜色配置
        lair_base_color = (139, 69, 19)      # 马鞍棕色主体
        lair_roof_color = (101, 67, 33)      # 深棕色屋顶
        lair_border_color = (80, 50, 20)     # 深棕色边框
        lair_highlight_color = (160, 82, 45)  # 高光色
        lair_shadow_color = (60, 30, 10)     # 阴影色
        lair_metal_color = (105, 105, 105)   # 金属色
        lair_fire_color = (255, 69, 0)       # 火焰色
        lair_bone_color = (245, 245, 220)    # 骨白色

        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)

        # 计算中心位置
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2

        # 绘制巢穴主体 - 不规则形状（野蛮风格）
        lair_width = scaled_tile_size - 4
        lair_height = scaled_tile_size - 4
        lair_x = screen_x + 2
        lair_y = screen_y + 2

        # 绘制主体阴影
        shadow_rect = pygame.Rect(
            lair_x + 2, lair_y + 2, lair_width, lair_height)
        pygame.draw.rect(screen, lair_shadow_color, shadow_rect)

        # 绘制主体
        lair_rect = pygame.Rect(lair_x, lair_y, lair_width, lair_height)
        pygame.draw.rect(screen, lair_base_color, lair_rect)

        # 绘制边框
        border_width = max(1, int(2 * ui_scale))
        pygame.draw.rect(screen, lair_border_color, lair_rect, border_width)

        # 绘制屋顶 - 倾斜的茅草屋顶
        roof_height = int(8 * ui_scale)
        roof_points = [
            (lair_x, lair_y + lair_height - roof_height),  # 左下
            (center_x, lair_y),  # 顶部中心
            (lair_x + lair_width, lair_y + lair_height - roof_height)  # 右下
        ]
        pygame.draw.polygon(screen, lair_roof_color, roof_points)
        pygame.draw.polygon(screen, lair_border_color,
                            roof_points, border_width)

        # 绘制茅草纹理
        for i in range(3):
            straw_y = lair_y + int(i * 2 * ui_scale)
            straw_points = [
                (lair_x + int(2 * ui_scale), straw_y),
                (center_x, straw_y + int(2 * ui_scale)),
                (lair_x + lair_width - int(2 * ui_scale), straw_y)
            ]
            pygame.draw.polygon(screen, lair_highlight_color, straw_points)

        # 绘制入口 - 拱形门洞
        door_width = int(12 * ui_scale)
        door_height = int(16 * ui_scale)
        door_x = center_x - door_width // 2
        door_y = lair_y + lair_height - door_height

        # 门洞背景
        door_rect = pygame.Rect(door_x, door_y, door_width, door_height)
        pygame.draw.rect(screen, (40, 20, 10), door_rect)

        # 门洞边框
        pygame.draw.rect(screen, lair_border_color, door_rect, 1)

        # 绘制兽人图腾 - 中心装饰
        totem_radius = int(6 * ui_scale)
        totem_center = (center_x, center_y + int(2 * ui_scale))

        # 图腾主体
        pygame.draw.circle(screen, lair_bone_color, totem_center, totem_radius)
        pygame.draw.circle(screen, lair_border_color,
                           totem_center, totem_radius, 1)

        # 图腾装饰 - 兽人符号
        totem_symbol = self.font_manager.safe_render(
            self.small_font, "⚔", (139, 69, 19))
        symbol_rect = totem_symbol.get_rect(center=totem_center)
        screen.blit(totem_symbol, symbol_rect)

        # 绘制武器架 - 两侧装饰
        weapon_width = int(8 * ui_scale)
        weapon_height = int(12 * ui_scale)

        # 左侧武器架
        left_weapon_x = lair_x + int(2 * ui_scale)
        left_weapon_y = lair_y + int(4 * ui_scale)
        left_weapon_rect = pygame.Rect(
            left_weapon_x, left_weapon_y, weapon_width, weapon_height)
        pygame.draw.rect(screen, lair_metal_color, left_weapon_rect)
        pygame.draw.rect(screen, lair_border_color, left_weapon_rect, 1)

        # 右侧武器架
        right_weapon_x = lair_x + lair_width - weapon_width - int(2 * ui_scale)
        right_weapon_y = lair_y + int(4 * ui_scale)
        right_weapon_rect = pygame.Rect(
            right_weapon_x, right_weapon_y, weapon_width, weapon_height)
        pygame.draw.rect(screen, lair_metal_color, right_weapon_rect)
        pygame.draw.rect(screen, lair_border_color, right_weapon_rect, 1)

        # 绘制火焰装饰 - 入口两侧
        fire_radius = int(3 * ui_scale)
        left_fire_center = (lair_x + int(4 * ui_scale),
                            lair_y + lair_height - int(6 * ui_scale))
        right_fire_center = (lair_x + lair_width - int(4 * ui_scale),
                             lair_y + lair_height - int(6 * ui_scale))

        # 左侧火焰
        pygame.draw.circle(screen, lair_fire_color,
                           left_fire_center, fire_radius)
        pygame.draw.circle(screen, (255, 140, 0),
                           left_fire_center, fire_radius - 1)

        # 右侧火焰
        pygame.draw.circle(screen, lair_fire_color,
                           right_fire_center, fire_radius)
        pygame.draw.circle(screen, (255, 140, 0),
                           right_fire_center, fire_radius - 1)

        # 绘制装饰性边框 - 四个角的兽骨装饰
        bone_size = max(1, int(3 * ui_scale))
        corners = [
            (lair_x + 1, lair_y + 1),  # 左上
            (lair_x + lair_width - bone_size - 1, lair_y + 1),  # 右上
            (lair_x + 1, lair_y + lair_height - bone_size - 1),  # 左下
            (lair_x + lair_width - bone_size - 1,
             lair_y + lair_height - bone_size - 1)  # 右下
        ]
        for cx, cy in corners:
            pygame.draw.rect(screen, lair_bone_color,
                             (cx, cy, bone_size, bone_size))
            pygame.draw.rect(screen, lair_border_color,
                             (cx, cy, bone_size, bone_size), 1)

    def _render_demon_lair_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                      tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染恶魔巢穴外观 - 恐怖地狱洞穴设计"""
        # 恶魔巢穴颜色配置 - 赤红色主题
        cave_wall_color = (80, 20, 20)       # 洞穴墙壁 - 深赤红色
        flesh_ground_color = (120, 30, 30)   # 血肉地面 - 赤红色
        bone_color = (220, 200, 180)         # 骨白色 - 略带暖色
        dark_altar_color = (60, 15, 15)      # 黑暗祭坛 - 深赤红色
        pulsing_heart_color = (200, 0, 0)    # 脉动心脏 - 鲜红色
        evil_green_fire = (255, 100, 0)      # 地狱火焰 - 橙红色
        evil_green_bright = (255, 150, 50)   # 亮橙红色
        vein_color = (150, 30, 30)           # 血管纹理 - 赤红色
        rune_glow = (200, 50, 50)            # 符文发光 - 赤红色
        shadow_deep = (20, 5, 5)             # 深层阴影 - 深赤色
        crack_color = (100, 20, 20)          # 裂缝颜色 - 赤红色

        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)
        center_x = screen_x + scaled_tile_size // 2
        center_y = screen_y + scaled_tile_size // 2

        # 绘制洞穴背景墙壁 - 脉动的血管纹理
        cave_bg_rect = pygame.Rect(screen_x + 1, screen_y + 1,
                                   scaled_tile_size - 2, scaled_tile_size - 2)
        pygame.draw.rect(screen, cave_wall_color, cave_bg_rect)

        # 绘制血管纹理 - 脉动的血管网络
        vein_width = max(1, int(1 * ui_scale))
        vein_positions = [
            # 主要血管 - 垂直和水平
            (screen_x + 3, screen_y + 5, screen_x +
             3, screen_y + scaled_tile_size - 5),
            (screen_x + scaled_tile_size - 3, screen_y + 5, screen_x +
             scaled_tile_size - 3, screen_y + scaled_tile_size - 5),
            (screen_x + 5, screen_y + 3, screen_x +
             scaled_tile_size - 5, screen_y + 3),
            (screen_x + 5, screen_y + scaled_tile_size - 3, screen_x +
             scaled_tile_size - 5, screen_y + scaled_tile_size - 3),
            # 分支血管
            (screen_x + 8, screen_y + 8, screen_x + 12, screen_y + 12),
            (screen_x + scaled_tile_size - 8, screen_y + 8,
             screen_x + scaled_tile_size - 12, screen_y + 12),
            (screen_x + 8, screen_y + scaled_tile_size - 8,
             screen_x + 12, screen_y + scaled_tile_size - 12),
            (screen_x + scaled_tile_size - 8, screen_y + scaled_tile_size - 8,
             screen_x + scaled_tile_size - 12, screen_y + scaled_tile_size - 12)
        ]

        for start_x, start_y, end_x, end_y in vein_positions:
            pygame.draw.line(screen, vein_color,
                             (start_x, start_y), (end_x, end_y), vein_width)

        # 绘制血肉地面 - 破裂的深色地砖
        ground_rect = pygame.Rect(screen_x + 2, screen_y + scaled_tile_size - 8,
                                  scaled_tile_size - 4, 6)
        pygame.draw.rect(screen, flesh_ground_color, ground_rect)

        # 绘制地面裂缝
        crack_width = max(1, int(1 * ui_scale))
        ground_cracks = [
            (screen_x + 4, screen_y + scaled_tile_size - 6, screen_x +
             scaled_tile_size - 4, screen_y + scaled_tile_size - 4),
            (screen_x + 6, screen_y + scaled_tile_size - 8,
             screen_x + 8, screen_y + scaled_tile_size - 2),
            (screen_x + scaled_tile_size - 6, screen_y + scaled_tile_size - 8,
             screen_x + scaled_tile_size - 8, screen_y + scaled_tile_size - 2)
        ]

        for start_x, start_y, end_x, end_y in ground_cracks:
            pygame.draw.line(screen, crack_color,
                             (start_x, start_y), (end_x, end_y), crack_width)

        # 绘制散落的骨头
        bone_positions = [
            (screen_x + 4, screen_y + scaled_tile_size - 10),  # 左下骨头
            (screen_x + scaled_tile_size - 6,
             screen_y + scaled_tile_size - 8),  # 右下骨头
            (screen_x + 6, screen_y + 8),  # 左上骨头
            (screen_x + scaled_tile_size - 8, screen_y + 6)   # 右上骨头
        ]

        for bone_x, bone_y in bone_positions:
            # 绘制骨头 - 小矩形
            bone_size = max(1, int(3 * ui_scale))
            bone_rect = pygame.Rect(bone_x, bone_y, bone_size, bone_size)
            pygame.draw.rect(screen, bone_color, bone_rect)
            pygame.draw.rect(screen, shadow_deep, bone_rect, 1)

        # 绘制燃烧的幽绿色火把
        torch_radius = int(2 * ui_scale)
        torch_positions = [
            (screen_x + 3, screen_y + 5),   # 左上火把
            (screen_x + scaled_tile_size - 3, screen_y + 5)  # 右上火把
        ]

        for torch_x, torch_y in torch_positions:
            # 火把火焰 - 地狱橙红色
            pygame.draw.circle(screen, evil_green_fire,
                               (torch_x, torch_y), torch_radius)
            pygame.draw.circle(screen, evil_green_bright,
                               (torch_x, torch_y), torch_radius - 1)

        # 绘制悬挂的茧 - 顶部装饰
        cocoon_positions = [
            (center_x - int(6 * ui_scale), screen_y + 2),
            (center_x + int(6 * ui_scale), screen_y + 2)
        ]

        for cocoon_x, cocoon_y in cocoon_positions:
            # 茧 - 椭圆形
            cocoon_width = int(4 * ui_scale)
            cocoon_height = int(6 * ui_scale)
            cocoon_rect = pygame.Rect(
                cocoon_x - cocoon_width//2, cocoon_y, cocoon_width, cocoon_height)
            pygame.draw.ellipse(screen, (120, 40, 40), cocoon_rect)  # 赤红色茧
            pygame.draw.ellipse(screen, shadow_deep, cocoon_rect, 1)

        # 绘制黑暗祭坛 - 场景中央的核心物件
        altar_width = int(12 * ui_scale)
        altar_height = int(8 * ui_scale)
        altar_x = center_x - altar_width // 2
        altar_y = center_y - altar_height // 2
        altar_rect = pygame.Rect(altar_x, altar_y, altar_width, altar_height)

        # 祭坛阴影
        altar_shadow_rect = pygame.Rect(
            altar_x + 1, altar_y + 1, altar_width, altar_height)
        pygame.draw.rect(screen, shadow_deep, altar_shadow_rect)

        # 祭坛主体
        pygame.draw.rect(screen, dark_altar_color, altar_rect)
        pygame.draw.rect(screen, (100, 50, 50), altar_rect, 1)

        # 绘制脉动的恶魔心脏 - 祭坛上方
        heart_radius = int(5 * ui_scale)
        heart_center = (center_x, center_y - int(6 * ui_scale))

        # 心脏阴影
        heart_shadow = (heart_center[0] + 1, heart_center[1] + 1)
        pygame.draw.circle(screen, shadow_deep, heart_shadow, heart_radius)

        # 心脏主体 - 脉动的暗红色
        pygame.draw.circle(screen, pulsing_heart_color,
                           heart_center, heart_radius)
        pygame.draw.circle(screen, (100, 0, 0), heart_center, heart_radius, 1)

        # 心脏内部高光
        inner_heart_radius = int(heart_radius * 0.6)
        heart_highlight = (heart_center[0] - 1, heart_center[1] - 1)
        pygame.draw.circle(screen, (200, 0, 0),
                           heart_highlight, inner_heart_radius)

        # 绘制邪恶符文 - 发光的深紫色符文
        rune_size = int(3 * ui_scale)
        rune_positions = [
            (altar_x - int(2 * ui_scale), altar_y + altar_height // 2),  # 祭坛左侧
            (altar_x + altar_width + int(2 * ui_scale),
             altar_y + altar_height // 2),  # 祭坛右侧
            (altar_x + altar_width // 2, altar_y - int(2 * ui_scale)),  # 祭坛上方
            (altar_x + altar_width // 2, altar_y +
             altar_height + int(2 * ui_scale))  # 祭坛下方
        ]

        for rune_x, rune_y in rune_positions:
            # 符文发光效果
            pygame.draw.circle(screen, rune_glow, (rune_x, rune_y), rune_size)
            pygame.draw.circle(screen, (150, 0, 200),
                               (rune_x, rune_y), rune_size - 1)

        # 绘制破损的仪式器具 - 祭坛周围
        ritual_items = [
            (altar_x - int(4 * ui_scale), altar_y +
             int(2 * ui_scale), int(2 * ui_scale)),  # 左侧器具
            (altar_x + altar_width + int(2 * ui_scale), altar_y +
             int(2 * ui_scale), int(2 * ui_scale)),  # 右侧器具
        ]

        for item_x, item_y, item_size in ritual_items:
            # 破损的器具 - 小矩形
            item_rect = pygame.Rect(item_x, item_y, item_size, item_size)
            pygame.draw.rect(screen, (100, 50, 50), item_rect)  # 赤红色器具
            pygame.draw.rect(screen, shadow_deep, item_rect, 1)

        # 绘制恶魔巢穴边框 - 不规则的邪恶边框
        border_width = max(1, int(2 * ui_scale))
        border_rect = pygame.Rect(
            screen_x, screen_y, scaled_tile_size, scaled_tile_size)
        pygame.draw.rect(screen, (150, 30, 30), border_rect, border_width)

        # 绘制四个角的邪恶装饰
        corner_decor_size = max(1, int(3 * ui_scale))
        corner_offset = int(1 * ui_scale)
        corners = [
            (screen_x + corner_offset, screen_y + corner_offset),  # 左上
            (screen_x + scaled_tile_size - corner_decor_size -
             corner_offset, screen_y + corner_offset),  # 右上
            (screen_x + corner_offset, screen_y + scaled_tile_size -
             corner_decor_size - corner_offset),  # 左下
            (screen_x + scaled_tile_size - corner_decor_size - corner_offset,
             screen_y + scaled_tile_size - corner_decor_size - corner_offset)  # 右下
        ]

        for cx, cy in corners:
            # 邪恶装饰 - 五角星
            decor_points = []
            for i in range(10):
                angle = i * 3.14159 / 5 - 3.14159 / 2
                if i % 2 == 0:
                    radius = corner_decor_size
                else:
                    radius = corner_decor_size // 2
                x = cx + corner_decor_size//2 + int(radius * math.cos(angle))
                y = cy + corner_decor_size//2 + int(radius * math.sin(angle))
                decor_points.append((x, y))

            if len(decor_points) >= 3:
                pygame.draw.polygon(screen, rune_glow, decor_points)
                pygame.draw.polygon(screen, (250, 100, 100), decor_points, 1)

    def _render_default_building_appearance(self, screen: pygame.Surface, building_type: str,
                                            screen_x: int, screen_y: int, tile_size: int, tile=None, ui_scale: float = 1.0):
        """渲染默认建筑外观"""
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
            'arcane_tower': (138, 43, 226),  # 奥术塔 - 蓝紫色
            'shadow_temple': (72, 61, 139),  # 暗影神殿 - 暗紫色
            'magic_research_institute': (65, 105, 225),  # 魔法研究院 - 蓝色
            'orc_lair': (139, 69, 19),  # 兽人巢穴 - 马鞍棕色
            'demon_lair': (75, 0, 130),  # 恶魔巢穴 - 深紫色
        }

        color = building_colors.get(building_type, Colors.GRAY_500)  # 默认灰色

        # 应用UI缩放到尺寸
        scaled_tile_size = int(tile_size * ui_scale)
        border_width = max(
            1, int(GameConstants.BUILDING_BORDER_WIDTH * ui_scale))

        # 绘制建筑
        building_rect = pygame.Rect(
            screen_x + 1, screen_y + 1, scaled_tile_size - 2, scaled_tile_size - 2)
        pygame.draw.rect(screen, color, building_rect)

        # 绘制边框
        border_rect = pygame.Rect(
            screen_x, screen_y, scaled_tile_size, scaled_tile_size)
        pygame.draw.rect(screen, Colors.GRAY_800, border_rect, border_width)

    def render_building_health_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int,
                                   tile_size: int, tile=None, building=None, ui_scale: float = 1.0):
        """
        渲染建筑生命条 - 统一的生命值渲染方法

        Args:
            screen: pygame屏幕表面
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            tile: 瓦片对象（可选）
            building: 建筑对象（可选）
            ui_scale: UI缩放倍数
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

        # 生命条尺寸和位置，应用UI缩放
        scaled_tile_size = int(tile_size * ui_scale)
        bar_width = scaled_tile_size - \
            int(GameConstants.STATUS_BAR_PADDING * ui_scale)
        bar_height = max(1, int(4 * ui_scale))
        bar_x = screen_x + int(GameConstants.STATUS_BAR_OFFSET * ui_scale)
        bar_y = screen_y + scaled_tile_size - \
            int(GameConstants.STATUS_BAR_PADDING * ui_scale)

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

    def render_magic_altar_resource_stats(self, screen: pygame.Surface, altar, screen_x: int, screen_y: int,
                                          tile_size: int, ui_scale: float = 1.0):
        """渲染魔法祭坛资源统计信息"""
        if not hasattr(altar, 'get_resource_statistics'):
            return

        stats = altar.get_resource_statistics()
        scaled_tile_size = int(tile_size * ui_scale)

        # 计算位置
        stats_x = screen_x + scaled_tile_size + 5
        stats_y = screen_y

        # 背景
        bg_width = 200
        bg_height = 120
        bg_rect = pygame.Rect(stats_x, stats_y, bg_width, bg_height)
        pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
        pygame.draw.rect(screen, (0, 100, 255), bg_rect, 2)

        # 标题
        title_text = self.font_manager.safe_render(
            self.small_font, "魔法祭坛统计", (255, 255, 255))
        screen.blit(title_text, (stats_x + 5, stats_y + 5))

        # 统计信息
        y_offset = 25
        line_height = 15

        # 存储量
        storage_text = f"存储: {stats['current_stored_mana']:.1f}/{stats['storage_capacity']:.0f}"
        storage_surface = self.font_manager.safe_render(
            self.small_font, storage_text, (147, 112, 219))
        screen.blit(storage_surface, (stats_x + 5, stats_y + y_offset))
        y_offset += line_height

        # 生成速率
        gen_rate = stats.get('current_generation_rate', 0)
        gen_text = f"生成: {gen_rate:.1f}/s"
        gen_surface = self.font_manager.safe_render(
            self.small_font, gen_text, (186, 85, 211))
        screen.blit(gen_surface, (stats_x + 5, stats_y + y_offset))
        y_offset += line_height

        # 转移速率
        transfer_rate = stats.get('current_transfer_rate', 0)
        transfer_text = f"转移: {transfer_rate:.1f}/s"
        transfer_surface = self.font_manager.safe_render(
            self.small_font, transfer_text, (221, 160, 221))
        screen.blit(transfer_surface, (stats_x + 5, stats_y + y_offset))
        y_offset += line_height

        # 效率评级
        efficiency = stats.get('efficiency_rating', 0)
        eff_text = f"效率: {efficiency:.2f}"
        eff_color = (0, 255, 0) if efficiency > 1.0 else (
            255, 255, 0) if efficiency > 0.5 else (255, 0, 0)
        eff_surface = self.font_manager.safe_render(
            self.small_font, eff_text, eff_color)
        screen.blit(eff_surface, (stats_x + 5, stats_y + y_offset))
        y_offset += line_height

        # 运行时间
        uptime = stats.get('uptime_percentage', 0)
        uptime_text = f"运行: {uptime:.1f}%"
        uptime_surface = self.font_manager.safe_render(
            self.small_font, uptime_text, (255, 255, 255))
        screen.blit(uptime_surface, (stats_x + 5, stats_y + y_offset))
        y_offset += line_height

        # 法师状态
        mage_status = "有法师" if stats.get('has_mage', False) else "无法师"
        mage_color = (0, 255, 0) if stats.get(
            'has_mage', False) else (255, 0, 0)
        mage_surface = self.font_manager.safe_render(
            self.small_font, mage_status, mage_color)
        screen.blit(mage_surface, (stats_x + 5, stats_y + y_offset))
