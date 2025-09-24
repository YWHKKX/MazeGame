#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
War for the Overworld - 角色图鉴系统
显示所有角色的详细信息、属性和头像
"""

import pygame
import os
from typing import List, Dict, Optional, Tuple
from src.entities.character_data import CharacterDatabase, CharacterData, CharacterType, MonsterCategory, character_db
from src.managers.font_manager import UnifiedFontManager
from src.core import emoji_constants
from src.core.ui_design import Colors, FontSizes, Spacing, BorderRadius, UIStyles
from src.ui.base_ui import BaseUI


class CharacterBestiary(BaseUI):
    """角色图鉴系统"""

    def __init__(self, screen_width: int, screen_height: int, font_manager: UnifiedFontManager = None):
        # 初始化基类
        super().__init__(font_manager)

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_open = False
        self.current_category = CharacterType.HERO
        self.selected_character = None
        self.scroll_offset = 0
        self.max_scroll = 0
        self.search_text = ""
        self.show_favorites = False
        self.favorite_characters = set()

        # 性能优化: 添加各种缓存
        self._cached_characters = None
        self._cache_key = None  # 用于检测缓存是否需要更新
        self._scaled_avatar_cache = {}  # 缓存缩放后的头像
        self._text_render_cache = {}  # 缓存文本渲染结果
        self._content_cache = None  # 缓存内容区域渲染
        self._content_cache_character = None  # 缓存的角色ID

        # UI设置 - 使用更现代的尺寸
        self.panel_width = min(screen_width - Spacing.XXXL * 2, 1200)  # 最大宽度限制
        self.panel_height = min(
            screen_height - Spacing.XXXL * 2, 800)  # 最大高度限制
        self.panel_x = (screen_width - self.panel_width) // 2
        self.panel_y = (screen_height - self.panel_height) // 2

        # 侧边栏设置 - 更合理的比例
        self.sidebar_width = 320
        self.list_item_height = 80  # 增加高度让内容更舒适
        self.content_area_x = self.panel_x + self.sidebar_width + Spacing.XL
        self.content_area_width = self.panel_width - self.sidebar_width - Spacing.XL * 2

        # 字体设置 - 使用设计系统的字体大小
        pygame.font.init()
        self.title_font = self.font_manager.get_font(FontSizes.H1)
        self.header_font = self.font_manager.get_font(FontSizes.H3)
        self.normal_font = self.font_manager.get_font(FontSizes.NORMAL)
        self.small_font = self.font_manager.get_font(FontSizes.SMALL)
        self.large_font = self.font_manager.get_font(FontSizes.LARGE)

        # 颜色 - 使用设计系统颜色
        self.bg_color = Colors.OVERLAY_DARK
        self.panel_color = Colors.DARK_SURFACE
        self.sidebar_color = Colors.DARK_CARD
        self.selected_color = Colors.PRIMARY
        self.text_color = Colors.WHITE
        self.border_color = Colors.GRAY_600
        self.search_color = Colors.DARK_BG
        self.favorite_color = Colors.ERROR

        # 悬停状态
        self.hover_item = None
        self.hover_button = None

        # 角色数据库
        self.character_db = character_db

        # 头像缓存
        self.avatar_cache = {}
        self._load_avatars()

        # 计算最大滚动
        self._calculate_max_scroll()

    def _safe_render_text(self, font, text, color):
        """安全渲染文本，使用 UnifiedFontManager 的 safe_render 方法"""
        return self.font_manager.safe_render(font, text, color)

    def _render_text(self, font, text, color):
        """统一的文本渲染方法"""
        return self._safe_render_text(font, text, color)

    def _render_emoji_text(self, font, emoji, text, color):
        """分别渲染 emoji 和文字，然后合并"""
        if not text.strip():
            # 如果没有文字，只渲染 emoji
            return self._safe_render_text(font, emoji, color)

        # 分别渲染 emoji 和文字
        emoji_surface = self._safe_render_text(font, emoji, color)
        text_surface = self._safe_render_text(font, f" {text}", color)

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

    def _get_star_rating(self, level: int) -> str:
        """获取星级评价字符串"""
        # 使用emoji_constants中的星级符号
        return emoji_constants.STAR * level

    def _is_key_pressed(self, event, key_chars):
        """增强的按键检测，支持输入法兼容性"""
        # 检查物理按键
        for char in key_chars:
            if char.lower() == 'b' and event.key == pygame.K_b:
                return True
            elif char.lower() == 'h' and event.key == pygame.K_h:
                return True
            elif char.lower() == 'm' and event.key == pygame.K_m:
                return True
            elif char.lower() == 'f' and event.key == pygame.K_f:
                return True

        # 检查unicode字符（输入法兼容）
        if event.unicode and event.unicode.lower() in [c.lower() for c in key_chars]:
            return True

        return False

    def _load_avatars(self):
        """加载角色头像"""
        all_characters = list(self.character_db.get_all_heroes().values()) + \
            list(self.character_db.get_all_monsters().values())

        for character in all_characters:
            if character.avatar and os.path.exists(character.avatar):
                try:
                    avatar_surface = pygame.image.load(character.avatar)
                    # 调整头像大小为合适尺寸
                    avatar_surface = pygame.transform.scale(
                        avatar_surface, (40, 40))
                    self.avatar_cache[character.id] = avatar_surface
                except pygame.error as e:
                    print(f"无法加载头像 {character.avatar}: {e}")
                    self.avatar_cache[character.id] = None
            else:
                self.avatar_cache[character.id] = None

    def _calculate_max_scroll(self):
        """计算最大滚动距离"""
        import time
        start_time = time.time()

        characters = self._get_filtered_characters()
        filter_time = time.time() - start_time

        total_height = len(characters) * self.list_item_height
        visible_height = self.panel_height - 200  # 减去标题、搜索框和按钮高度
        self.max_scroll = max(0, total_height - visible_height)

        # 移除调试日志，保持性能

    def _get_filtered_characters(self) -> List[CharacterData]:
        """获取过滤后的角色列表 - 带缓存优化"""
        import time

        # 生成缓存键
        current_cache_key = (
            self.current_category,
            self.search_text,
            self.show_favorites,
            tuple(sorted(self.favorite_characters))  # 转换为可哈希的tuple
        )

        # 检查缓存是否有效
        if self._cache_key == current_cache_key and self._cached_characters is not None:
            return self._cached_characters

        start_time = time.time()

        characters = self.character_db.get_character_list(
            self.current_category)
        db_time = time.time() - start_time

        # 应用搜索过滤
        search_start = time.time()
        if self.search_text:
            characters = [c for c in characters
                          if self.search_text.lower() in c.name.lower()
                          or self.search_text.lower() in c.english_name.lower()]
        search_time = time.time() - search_start

        # 应用收藏过滤
        fav_start = time.time()
        if self.show_favorites:
            characters = [
                c for c in characters if c.id in self.favorite_characters]
        fav_time = time.time() - fav_start

        total_time = time.time() - start_time

        # 更新缓存
        self._cached_characters = characters
        self._cache_key = current_cache_key

        # 移除调试日志，保持性能

        return characters

    def toggle_favorite(self, character_id: str):
        """切换角色收藏状态"""
        import time
        start_time = time.time()

        if character_id in self.favorite_characters:
            self.favorite_characters.remove(character_id)
        else:
            self.favorite_characters.add(character_id)

        # 使缓存失效
        self._cache_key = None

    def open(self):
        """打开角色图鉴"""
        self.is_open = True
        self.scroll_offset = 0
        self._calculate_max_scroll()

    def close(self):
        """关闭角色图鉴"""
        self.is_open = False

    def show(self):
        """显示图鉴（与open方法相同，为了兼容性）"""
        self.open()

    def hide(self):
        """隐藏图鉴（与close方法相同，为了兼容性）"""
        self.close()

    def toggle(self):
        """切换图鉴开关状态"""
        if self.is_open:
            self.close()
        else:
            self.open()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """处理事件，返回True表示事件已被处理"""
        if event.type == pygame.KEYDOWN:
            # B键可以在任何时候切换图鉴状态 (支持大小写和输入法兼容)
            if self._is_key_pressed(event, ['b', 'B']):
                self.toggle()
                return True

            # ESC键只能关闭图鉴
            elif event.key == pygame.K_ESCAPE and self.is_open:
                self.close()
                return True

        # 其他事件只在图鉴打开时处理
        if not self.is_open:
            return False

        if event.type == pygame.KEYDOWN:
            if self._is_key_pressed(event, ['h', 'H']):
                self.switch_category(CharacterType.HERO)
                return True
            elif self._is_key_pressed(event, ['m', 'M']):
                self.switch_category(CharacterType.MONSTER)
                return True
            elif self._is_key_pressed(event, ['f', 'F']):
                self.show_favorites = not self.show_favorites
                self._calculate_max_scroll()
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.search_text:
                    self.search_text = self.search_text[:-1]
                    self._cache_key = None  # 使缓存失效
                    self._calculate_max_scroll()
                return True
            elif event.unicode and event.unicode.isprintable():
                self.search_text += event.unicode
                self._cache_key = None  # 使缓存失效
                self._calculate_max_scroll()
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # 左键
                mouse_x, mouse_y = event.pos

                # 检查是否点击了关闭按钮
                close_rect = pygame.Rect(
                    self.panel_x + self.panel_width - 50, self.panel_y + 10, 40, 40)
                if close_rect.collidepoint(mouse_x, mouse_y):
                    self.close()
                    return True

                # 检查是否点击了分类按钮 - 使用与渲染一致的位置
                button_y = self.panel_y + 130
                button_width = 100
                button_height = 44
                button_spacing = Spacing.SM

                # 计算按钮位置 - 与渲染逻辑一致
                total_width = button_width * 3 + button_spacing * 2
                start_x = self.panel_x + \
                    (self.sidebar_width - total_width) // 2

                hero_btn_rect = pygame.Rect(
                    start_x, button_y, button_width, button_height)
                monster_btn_rect = pygame.Rect(
                    start_x + button_width + button_spacing, button_y, button_width, button_height)
                favorites_btn_rect = pygame.Rect(
                    start_x + (button_width + button_spacing) * 2, button_y, button_width, button_height)

                if hero_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.switch_category(CharacterType.HERO)
                    return True
                elif monster_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.switch_category(CharacterType.MONSTER)
                    return True
                elif favorites_btn_rect.collidepoint(mouse_x, mouse_y):
                    import time
                    start_time = time.time()
                    self.show_favorites = not self.show_favorites
                    self._cache_key = None  # 使缓存失效
                    self._calculate_max_scroll()
                    return True

                # 检查是否点击了角色列表项
                self._handle_character_list_click(mouse_x, mouse_y)
                return True

        elif event.type == pygame.MOUSEWHEEL:
            # 处理滚轮滚动
            self.scroll_offset = max(
                0, min(self.max_scroll, self.scroll_offset - event.y * 30))
            return True

        return False

    def _handle_character_list_click(self, mouse_x: int, mouse_y: int):
        """处理角色列表点击"""
        list_start_y = self.panel_y + 170  # 调整起始位置以容纳搜索框
        list_x = self.panel_x + 20

        # 检查是否在角色列表区域内
        if (list_x <= mouse_x <= list_x + self.sidebar_width - 40 and
                list_start_y <= mouse_y <= list_start_y + self.panel_height - 190):

            # 计算点击的角色索引
            relative_y = mouse_y - list_start_y + self.scroll_offset
            character_index = relative_y // self.list_item_height

            characters = self._get_filtered_characters()
            if 0 <= character_index < len(characters):
                character = characters[character_index]
                if self.selected_character != character:
                    self.selected_character = character
                    self._content_cache = None  # 使内容缓存失效

                # 检查是否点击了收藏按钮
                favorite_btn_x = list_x + self.sidebar_width - 50
                favorite_btn_y = list_start_y + character_index * \
                    self.list_item_height - self.scroll_offset + 10
                favorite_btn_rect = pygame.Rect(
                    favorite_btn_x, favorite_btn_y, 30, 30)

                if favorite_btn_rect.collidepoint(mouse_x, mouse_y):
                    self.toggle_favorite(character.id)

    def switch_category(self, category: CharacterType):
        """切换角色分类"""
        import time
        start_time = time.time()

        self.current_category = category
        self.selected_character = None
        self.scroll_offset = 0

        # 使缓存失效
        self._cache_key = None
        self._content_cache = None

        self._calculate_max_scroll()

    def render(self, screen: pygame.Surface):
        """渲染角色图鉴"""
        if not self.is_open:
            return

        import time
        render_start = time.time()

        # 创建半透明背景
        overlay_start = time.time()
        overlay = pygame.Surface(
            (self.screen_width, self.screen_height), pygame.SRCALPHA)
        overlay.fill(self.bg_color)
        screen.blit(overlay, (0, 0))
        overlay_time = time.time() - overlay_start

        # 简化主面板渲染 - 使用简单矩形
        panel_start = time.time()
        panel_rect = pygame.Rect(
            self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        pygame.draw.rect(screen, Colors.DARK_SURFACE, panel_rect)
        pygame.draw.rect(screen, Colors.GRAY_600, panel_rect, 2)
        panel_time = time.time() - panel_start

        # 绘制标题区域
        header_start = time.time()
        self._render_header(screen)
        header_time = time.time() - header_start

        # 绘制搜索框
        search_start = time.time()
        self._render_search_box(screen)
        search_time = time.time() - search_start

        # 绘制分类按钮
        buttons_start = time.time()
        self._render_category_buttons(screen)
        buttons_time = time.time() - buttons_start

        # 绘制侧边栏
        sidebar_start = time.time()
        self._render_sidebar(screen)
        sidebar_time = time.time() - sidebar_start

        # 绘制内容区域 - 使用缓存优化
        content_start = time.time()
        self._render_content_area_cached(screen)
        content_time = time.time() - content_start

        total_render_time = time.time() - render_start

        # 只在严重卡顿时警告
        if total_render_time > 0.033:  # 30fps阈值
            print(f"⚠️ 图鉴渲染: {total_render_time*1000:.0f}ms")

    def _render_header(self, screen: pygame.Surface):
        """渲染标题区域"""
        # 标题
        title_text = self._render_emoji_text(
            self.title_font, emoji_constants.BOOK, "角色图鉴", self.selected_color)
        title_x = self.panel_x + Spacing.XL
        title_y = self.panel_y + Spacing.LG
        screen.blit(title_text, (title_x, title_y))

        # 关闭按钮 - 使用新的按钮组件
        close_rect = pygame.Rect(
            self.panel_x + self.panel_width - 60, self.panel_y + Spacing.LG, 40, 40)

        # 检查悬停状态
        mouse_pos = pygame.mouse.get_pos()
        is_hover = close_rect.collidepoint(mouse_pos)

        close_style = {
            'bg_color': Colors.ERROR,
            'bg_hover': (200, 50, 50),
            'text_color': Colors.WHITE,
            'border_radius': BorderRadius.MD,
            'font_size': FontSizes.LARGE
        }

        self.draw_button(screen, close_rect,
                         emoji_constants.CROSS, close_style, hover=is_hover)

    def _render_search_box(self, screen: pygame.Surface):
        """渲染搜索框"""
        search_rect = pygame.Rect(
            self.panel_x + Spacing.XL,
            self.panel_y + 80,  # 调整位置给标题留更多空间
            self.sidebar_width - Spacing.XL * 2,
            36  # 增加高度
        )

        # 使用新的输入框组件
        self.draw_input_field(screen, search_rect,
                              self.search_text, "搜索角色...", focused=False)

        # 搜索图标
        icon_rect = pygame.Rect(
            search_rect.x + Spacing.SM, search_rect.centery - 8, 16, 16)
        search_icon = self._render_text(
            self.normal_font, emoji_constants.SEARCH, Colors.GRAY_400)
        screen.blit(search_icon, icon_rect.topleft)

    def _render_category_buttons(self, screen: pygame.Surface):
        """渲染分类按钮"""
        button_y = self.panel_y + 130  # 调整位置
        button_width = 100
        button_height = 44  # 增加高度
        button_spacing = Spacing.SM

        # 计算按钮位置
        total_width = button_width * 3 + button_spacing * 2
        start_x = self.panel_x + (self.sidebar_width - total_width) // 2

        hero_btn_rect = pygame.Rect(
            start_x, button_y, button_width, button_height)
        monster_btn_rect = pygame.Rect(
            start_x + button_width + button_spacing, button_y, button_width, button_height)
        favorites_btn_rect = pygame.Rect(
            start_x + (button_width + button_spacing) * 2, button_y, button_width, button_height)

        # 获取鼠标位置用于悬停检测
        mouse_pos = pygame.mouse.get_pos()

        # 英雄按钮
        is_selected = self.current_category == CharacterType.HERO
        is_hover = hero_btn_rect.collidepoint(mouse_pos)

        hero_style = UIStyles.BUTTON_PRIMARY.copy(
        ) if is_selected else UIStyles.BUTTON_SECONDARY.copy()
        hero_style['font_size'] = FontSizes.SMALL

        hero_text = f"{emoji_constants.COMBAT} 英雄"
        self.draw_button(screen, hero_btn_rect, hero_text,
                         hero_style, hover=is_hover)

        # 怪物按钮
        is_selected = self.current_category == CharacterType.MONSTER
        is_hover = monster_btn_rect.collidepoint(mouse_pos)

        monster_style = UIStyles.BUTTON_PRIMARY.copy(
        ) if is_selected else UIStyles.BUTTON_SECONDARY.copy()
        monster_style['font_size'] = FontSizes.SMALL

        monster_text = f"{emoji_constants.MONSTER} 怪物"
        self.draw_button(screen, monster_btn_rect, monster_text,
                         monster_style, hover=is_hover)

        # 收藏按钮
        is_selected = self.show_favorites
        is_hover = favorites_btn_rect.collidepoint(mouse_pos)

        favorites_style = {
            'bg_color': self.favorite_color if is_selected else Colors.GRAY_600,
            'bg_hover': (220, 50, 80) if is_selected else Colors.GRAY_500,
            'text_color': Colors.WHITE,
            'border_radius': BorderRadius.MD,
            'font_size': FontSizes.SMALL
        }

        favorites_text = f"{emoji_constants.HEART} 收藏"
        self.draw_button(screen, favorites_btn_rect,
                         favorites_text, favorites_style, hover=is_hover)

    def _render_sidebar(self, screen: pygame.Surface):
        """渲染侧边栏"""
        import time
        sidebar_start = time.time()

        sidebar_rect = pygame.Rect(
            self.panel_x + Spacing.XL,
            self.panel_y + 190,  # 调整位置
            self.sidebar_width - Spacing.XL,
            self.panel_height - 210
        )

        # 简化侧边栏背景 - 使用简单矩形代替复杂卡片
        card_start = time.time()
        pygame.draw.rect(screen, Colors.GRAY_800, sidebar_rect)
        pygame.draw.rect(screen, Colors.GRAY_600, sidebar_rect, 1)
        card_time = time.time() - card_start

        # 绘制角色列表
        filter_start = time.time()
        characters = self._get_filtered_characters()
        filter_time = time.time() - filter_start

        list_start_y = sidebar_rect.y + Spacing.MD
        list_x = sidebar_rect.x + Spacing.MD

        render_items_start = time.time()
        visible_items = 0

        # 计算可见范围，减少不必要的检查
        visible_start = max(0, self.scroll_offset // self.list_item_height)
        visible_end = min(len(characters),
                          visible_start + (sidebar_rect.height // self.list_item_height) + 2)

        for i in range(visible_start, visible_end):
            if i >= len(characters):
                break

            character = characters[i]
            item_y = list_start_y + i * self.list_item_height - self.scroll_offset

            # 只绘制真正可见的项目
            if (item_y + self.list_item_height >= list_start_y and
                    item_y <= list_start_y + sidebar_rect.height - Spacing.MD):
                self._render_character_list_item_optimized(
                    screen, character, list_x, item_y, i)
                visible_items += 1

        render_items_time = time.time() - render_items_start
        total_sidebar_time = time.time() - sidebar_start

        # 只在严重卡顿时警告
        if total_sidebar_time > 0.020:  # 20ms阈值
            print(f"⚠️ 侧边栏: {total_sidebar_time*1000:.0f}ms")

    def _render_character_list_item(self, screen: pygame.Surface, character: CharacterData, x: int, y: int, index: int):
        """渲染角色列表项"""
        item_rect = pygame.Rect(
            x, y, self.sidebar_width - Spacing.XL, self.list_item_height - Spacing.SM)

        # 优化悬停检测 - 减少鼠标位置查询
        is_selected = self.selected_character == character

        # 简化卡片渲染 - 减少复杂样式计算
        if is_selected:
            # 选中状态 - 简化边框
            pygame.draw.rect(screen, Colors.GRAY_800, item_rect)
            pygame.draw.rect(screen, self.selected_color, item_rect, 2)
        else:
            # 普通状态 - 简单背景
            pygame.draw.rect(screen, Colors.GRAY_700, item_rect)

        # 角色头像 - 更好的布局
        avatar_x = x + Spacing.MD
        avatar_y = y + Spacing.MD
        avatar_size = 48  # 稍微增大

        # 优化头像渲染 - 使用缓存的缩放头像
        avatar_cache_key = (character.id, avatar_size)

        if avatar_cache_key in self._scaled_avatar_cache:
            # 使用缓存的缩放头像
            scaled_avatar = self._scaled_avatar_cache[avatar_cache_key]
            screen.blit(scaled_avatar, (avatar_x, avatar_y))
        elif character.id in self.avatar_cache and self.avatar_cache[character.id] is not None:
            # 缩放并缓存头像
            avatar_surface = self.avatar_cache[character.id]
            scaled_avatar = pygame.transform.scale(
                avatar_surface, (avatar_size, avatar_size))
            self._scaled_avatar_cache[avatar_cache_key] = scaled_avatar
            screen.blit(scaled_avatar, (avatar_x, avatar_y))
        else:
            # 创建并缓存颜色圆形
            if avatar_cache_key not in self._scaled_avatar_cache:
                # 创建圆形头像表面
                circle_surface = pygame.Surface(
                    (avatar_size, avatar_size), pygame.SRCALPHA)
                pygame.draw.circle(circle_surface, character.color,
                                   (avatar_size // 2, avatar_size // 2), avatar_size // 2)
                pygame.draw.circle(circle_surface, Colors.WHITE,
                                   (avatar_size // 2, avatar_size // 2), avatar_size // 2, 2)
                self._scaled_avatar_cache[avatar_cache_key] = circle_surface

            screen.blit(
                self._scaled_avatar_cache[avatar_cache_key], (avatar_x, avatar_y))

        # 优化文本渲染 - 使用缓存
        name_cache_key = (character.name, 'name', self.text_color)
        if name_cache_key in self._text_render_cache:
            name_text = self._text_render_cache[name_cache_key]
        else:
            name_text = self._render_text(
                self.normal_font, character.name, self.text_color)
            self._text_render_cache[name_cache_key] = name_text

        name_x = x + avatar_size + Spacing.LG
        name_y = y + Spacing.MD
        screen.blit(name_text, (name_x, name_y))

        # 角色属性 - 使用缓存优化
        if character.character_type == CharacterType.HERO:
            stars = self._get_star_rating(character.threat_level)
            stats_text = f"威胁: {stars} • HP: {character.hp} • 攻击: {character.attack}"
        else:
            stats_text = f"成本: {character.cost}金 • HP: {character.hp} • 攻击: {character.attack}"

        stats_cache_key = (stats_text, 'stats', Colors.GRAY_300)
        if stats_cache_key in self._text_render_cache:
            stats_surface = self._text_render_cache[stats_cache_key]
        else:
            stats_surface = self._render_text(
                self.small_font, stats_text, Colors.GRAY_300)
            self._text_render_cache[stats_cache_key] = stats_surface

        screen.blit(stats_surface, (name_x, name_y + 24))

        # 简化收藏按钮渲染 - 直接绘制，避免复杂按钮逻辑
        favorite_btn_x = x + self.sidebar_width - 50
        favorite_btn_y = y + Spacing.MD
        favorite_btn_rect = pygame.Rect(favorite_btn_x, favorite_btn_y, 32, 32)

        is_favorited = character.id in self.favorite_characters

        # 简化收藏按钮 - 直接绘制图标
        favorite_color = self.favorite_color if is_favorited else Colors.GRAY_500
        favorite_icon = emoji_constants.HEART if is_favorited else emoji_constants.WHITE_HEART

        # 缓存收藏图标渲染
        fav_cache_key = (favorite_icon, favorite_color)
        if fav_cache_key in self._text_render_cache:
            fav_surface = self._text_render_cache[fav_cache_key]
        else:
            fav_font = self.font_manager.get_emoji_font(FontSizes.NORMAL)
            fav_surface = self.font_manager.safe_render(
                fav_font, favorite_icon, favorite_color)
            self._text_render_cache[fav_cache_key] = fav_surface

        fav_rect = fav_surface.get_rect(center=favorite_btn_rect.center)
        screen.blit(fav_surface, fav_rect)

    def _render_character_list_item_optimized(self, screen: pygame.Surface, character: CharacterData, x: int, y: int, index: int):
        """优化版本的角色列表项渲染"""
        item_rect = pygame.Rect(
            x, y, self.sidebar_width - Spacing.XL, self.list_item_height - Spacing.SM)

        # 超级简化的背景渲染
        is_selected = self.selected_character == character
        bg_color = Colors.GRAY_800 if is_selected else Colors.GRAY_700
        pygame.draw.rect(screen, bg_color, item_rect)

        if is_selected:
            pygame.draw.rect(screen, self.selected_color, item_rect, 2)

        # 角色头像 - 使用缓存
        avatar_x = x + Spacing.MD
        avatar_y = y + Spacing.MD
        avatar_size = 48
        avatar_cache_key = (character.id, avatar_size)

        if avatar_cache_key in self._scaled_avatar_cache:
            screen.blit(
                self._scaled_avatar_cache[avatar_cache_key], (avatar_x, avatar_y))
        else:
            # 创建简化的颜色圆形并缓存
            circle_surface = pygame.Surface(
                (avatar_size, avatar_size), pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, character.color,
                               (avatar_size // 2, avatar_size // 2), avatar_size // 2)
            self._scaled_avatar_cache[avatar_cache_key] = circle_surface
            screen.blit(circle_surface, (avatar_x, avatar_y))

        # 角色名称 - 使用缓存
        name_cache_key = (character.name, 'name_simple', self.text_color)
        if name_cache_key in self._text_render_cache:
            name_text = self._text_render_cache[name_cache_key]
        else:
            name_text = self._render_text(
                self.normal_font, character.name, self.text_color)
            self._text_render_cache[name_cache_key] = name_text

        name_x = x + avatar_size + Spacing.LG
        name_y = y + Spacing.MD
        screen.blit(name_text, (name_x, name_y))

        # 简化的属性显示 - 只显示最重要的信息
        if character.character_type == CharacterType.HERO:
            simple_stats = f"威胁: {character.threat_level}"
        else:
            simple_stats = f"成本: {character.cost}金"

        stats_cache_key = (simple_stats, 'simple_stats', Colors.GRAY_300)
        if stats_cache_key in self._text_render_cache:
            stats_surface = self._text_render_cache[stats_cache_key]
        else:
            stats_surface = self._render_text(
                self.small_font, simple_stats, Colors.GRAY_300)
            self._text_render_cache[stats_cache_key] = stats_surface

        screen.blit(stats_surface, (name_x, name_y + 24))

    def _render_content_area_cached(self, screen: pygame.Surface):
        """渲染内容区域 - 带缓存优化"""
        content_rect = pygame.Rect(
            self.content_area_x,
            self.panel_y + 190,
            self.content_area_width,
            self.panel_height - 210
        )

        # 简化内容区域背景
        pygame.draw.rect(screen, Colors.GRAY_800, content_rect)
        pygame.draw.rect(screen, Colors.GRAY_600, content_rect, 1)

        # 检查是否需要重新渲染内容
        if (self._content_cache is None or
                self._content_cache_character != self.selected_character):

            if self.selected_character:
                # 创建内容缓存表面
                self._content_cache = pygame.Surface(
                    (content_rect.width, content_rect.height), pygame.SRCALPHA)
                self._content_cache.fill((0, 0, 0, 0))  # 透明背景

                # 渲染到缓存表面
                temp_rect = pygame.Rect(
                    0, 0, content_rect.width, content_rect.height)
                self._render_character_details(
                    self._content_cache, self.selected_character, temp_rect)

                self._content_cache_character = self.selected_character
            else:
                # 无选中角色，创建提示信息缓存
                self._content_cache = pygame.Surface(
                    (content_rect.width, content_rect.height), pygame.SRCALPHA)
                self._content_cache.fill((0, 0, 0, 0))

                # 渲染提示信息到缓存
                center_x = content_rect.width // 2
                center_y = content_rect.height // 2

                hint_text = self._render_text(
                    self.header_font, "选择一个角色查看详细信息", self.text_color)
                hint_rect = hint_text.get_rect(
                    center=(center_x, center_y - 40))
                self._content_cache.blit(hint_text, hint_rect)

                hint2_text = self._render_text(
                    self.normal_font, "点击左侧列表中的角色名称", Colors.GRAY_400)
                hint2_rect = hint2_text.get_rect(center=(center_x, center_y))
                self._content_cache.blit(hint2_text, hint2_rect)

                self._content_cache_character = None

        # 绘制缓存的内容
        if self._content_cache:
            screen.blit(self._content_cache, content_rect.topleft)

    def _render_content_area(self, screen: pygame.Surface):
        """渲染内容区域"""
        content_rect = pygame.Rect(
            self.content_area_x,
            self.panel_y + 190,
            self.content_area_width,
            self.panel_height - 210
        )

        # 简化内容区域背景
        pygame.draw.rect(screen, Colors.GRAY_800, content_rect)
        pygame.draw.rect(screen, Colors.GRAY_600, content_rect, 1)

        if self.selected_character:
            self._render_character_details(
                screen, self.selected_character, content_rect)
        else:
            # 显示提示信息 - 更美观的布局
            center_x = content_rect.centerx
            center_y = content_rect.centery

            # 主提示
            hint_text = self._render_text(
                self.header_font, "选择一个角色查看详细信息", self.text_color)
            hint_rect = hint_text.get_rect(center=(center_x, center_y - 40))
            screen.blit(hint_text, hint_rect)

            # 副提示
            hint2_text = self._render_text(
                self.normal_font, "点击左侧列表中的角色名称", Colors.GRAY_400)
            hint2_rect = hint2_text.get_rect(center=(center_x, center_y))
            screen.blit(hint2_text, hint2_rect)

            # 操作提示 - 分行显示更清晰
            shortcuts = [
                "快捷键操作:",
                "H - 英雄角色",
                "M - 怪物角色",
                "F - 收藏列表",
                "输入文字搜索"
            ]

            for i, shortcut in enumerate(shortcuts):
                color = self.text_color if i == 0 else Colors.GRAY_500
                font = self.normal_font if i == 0 else self.small_font

                hint_surface = self._render_text(font, shortcut, color)
                hint_rect = hint_surface.get_rect(
                    center=(center_x, center_y + 60 + i * 20))
                screen.blit(hint_surface, hint_rect)

    def _render_character_details(self, screen: pygame.Surface, character: CharacterData, content_rect: pygame.Rect):
        """渲染角色详细信息"""
        x = content_rect.x + Spacing.XL
        y = content_rect.y + Spacing.XL

        # 角色头部信息
        y = self._render_character_header(screen, character, x, y)

        # 属性网格
        y = self._render_character_stats(screen, character, x, y + Spacing.XL)

        # 特殊能力
        y = self._render_special_ability(screen, character, x, y + Spacing.XL)

        # AI行为
        y = self._render_ai_behavior(screen, character, x, y + Spacing.LG)

        # 战术特点
        y = self._render_tactics(screen, character, x, y + Spacing.LG)

    def _render_character_header(self, screen: pygame.Surface, character: CharacterData, x: int, y: int) -> int:
        """渲染角色头部信息"""
        # 角色头像 - 更大更美观
        avatar_x = x
        avatar_y = y
        avatar_size = 140  # 增大头像
        avatar_rect = pygame.Rect(avatar_x, avatar_y, avatar_size, avatar_size)

        # 绘制头像背景卡片
        avatar_card_style = UIStyles.CARD.copy()
        avatar_card_style['border_radius'] = BorderRadius.XL
        self.draw_card(screen, avatar_rect, avatar_card_style)

        # 尝试显示真实头像，否则显示颜色背景
        inner_rect = pygame.Rect(
            avatar_x + 4, avatar_y + 4, avatar_size - 8, avatar_size - 8)

        if character.id in self.avatar_cache and self.avatar_cache[character.id] is not None:
            # 显示真实头像
            avatar_surface = self.avatar_cache[character.id]
            # 缩放头像到合适大小
            avatar_surface = pygame.transform.scale(
                avatar_surface, (avatar_size - 8, avatar_size - 8))
            screen.blit(avatar_surface, inner_rect.topleft)
        else:
            # 显示颜色背景
            pygame.draw.rect(screen, character.color,
                             inner_rect, border_radius=BorderRadius.LG)

        # 基本信息
        info_x = x + avatar_size + Spacing.XL
        info_y = y

        # 角色名称 - 更大的字体
        name_text = self._render_text(
            self.large_font, character.name, character.color)
        screen.blit(name_text, (info_x, info_y))

        # 英文名称 - 副标题样式
        english_name_text = self._render_text(
            self.normal_font, f"({character.english_name})", Colors.GRAY_400)
        screen.blit(english_name_text, (info_x, info_y + 32))

        # 角色类型和收藏状态
        type_y = info_y + 70
        if character.character_type == CharacterType.HERO:
            type_text = f"{emoji_constants.COMBAT} 英雄角色 (入侵者)"
        else:
            # 怪物角色 - 显示分类
            if character.monster_category == MonsterCategory.FUNCTIONAL:
                type_text = f"{emoji_constants.MONSTER} 怪物角色 (功能类)"
            elif character.monster_category == MonsterCategory.COMBAT:
                type_text = f"{emoji_constants.MONSTER} 怪物角色 (战斗类)"
            else:
                type_text = f"{emoji_constants.MONSTER} 怪物角色 (地下生物)"

        if character.id in self.favorite_characters:
            type_text += f" {emoji_constants.HEART}"

        type_surface = self._render_text(
            self.normal_font, type_text, Colors.GRAY_300)
        screen.blit(type_surface, (info_x, type_y))

        # 描述 - 更好的间距
        desc_lines = self._wrap_text(
            character.description, self.content_area_width - avatar_size - Spacing.XXXL)
        desc_y = type_y + 40
        for line in desc_lines:
            desc_surface = self._render_text(
                self.normal_font, line, Colors.GRAY_200)
            screen.blit(desc_surface, (info_x, desc_y))
            desc_y += 28  # 增加行间距

        return y + avatar_size + Spacing.XL

    def _render_character_stats(self, screen: pygame.Surface, character: CharacterData, x: int, y: int) -> int:
        """渲染角色属性网格"""
        stats = []

        if character.character_type == CharacterType.HERO:
            stats.append(("威胁等级", str(character.threat_level),
                         emoji_constants.WARNING))
        else:
            # 怪物属性
            stats.append(
                ("召唤成本", f"{character.cost}金币", emoji_constants.MONEY))

            # 添加怪物分类信息
            if character.monster_category == MonsterCategory.FUNCTIONAL:
                category_text = "功能类"
                category_emoji = emoji_constants.TOOLS if hasattr(
                    emoji_constants, 'TOOLS') else "🔧"
            elif character.monster_category == MonsterCategory.COMBAT:
                category_text = "战斗类"
                category_emoji = emoji_constants.COMBAT
            else:
                category_text = "未知"
                category_emoji = "❓"

            stats.append(("怪物分类", category_text, category_emoji))

        stats.extend([
            ("生命值", str(character.hp), emoji_constants.HEART),
            ("攻击力", str(character.attack), emoji_constants.COMBAT),
            ("移动速度", str(character.speed), emoji_constants.RUNNER),
            ("护甲值", str(character.armor), emoji_constants.SHIELD),
            ("攻击范围", str(character.attack_range), emoji_constants.TARGET),
            ("攻击冷却", f"{character.attack_cooldown}秒", emoji_constants.COOLDOWN)
        ])

        # 计算网格布局 - 更好的间距
        cols = 3
        rows = (len(stats) + cols - 1) // cols
        card_width = (self.content_area_width - Spacing.XXXL -
                      (cols - 1) * Spacing.LG) // cols
        card_height = 100  # 增加高度

        for i, (label, value, icon) in enumerate(stats):
            row = i // cols
            col = i % cols
            card_x = x + col * (card_width + Spacing.LG)
            card_y = y + row * (card_height + Spacing.MD)

            # 绘制属性卡片 - 使用新的卡片样式
            card_rect = pygame.Rect(card_x, card_y, card_width, card_height)

            stat_card_style = UIStyles.CARD.copy()
            stat_card_style['bg_color'] = Colors.GRAY_800
            stat_card_style['border_color'] = character.color
            stat_card_style['border_width'] = 1

            self.draw_card(screen, card_rect, stat_card_style)

            # 图标 - 顶部居中
            icon_surface = self._render_text(
                self.large_font, icon, character.color)
            icon_rect = icon_surface.get_rect(
                center=(card_x + card_width // 2, card_y + 25))
            screen.blit(icon_surface, icon_rect)

            # 数值 - 中央突出显示
            value_surface = self._render_text(
                self.header_font, value, Colors.WHITE)
            value_rect = value_surface.get_rect(
                center=(card_x + card_width // 2, card_y + 50))
            screen.blit(value_surface, value_rect)

            # 标签 - 底部居中
            label_surface = self._render_text(
                self.small_font, label, Colors.GRAY_400)
            label_rect = label_surface.get_rect(
                center=(card_x + card_width // 2, card_y + card_height - 15))
            screen.blit(label_surface, label_rect)

        return y + rows * (card_height + Spacing.MD) + Spacing.LG

    def _render_special_ability(self, screen: pygame.Surface, character: CharacterData, x: int, y: int) -> int:
        """渲染特殊能力"""
        # 标题
        title_surface = self._render_emoji_text(
            self.header_font, emoji_constants.SPARKLES, "特殊能力", character.color)
        screen.blit(title_surface, (x, y))

        # 能力描述
        ability_lines = self._wrap_text(
            character.special_ability, self.content_area_width - 40)
        ability_y = y + 35
        for line in ability_lines:
            ability_surface = self._render_text(
                self.normal_font, line, (221, 221, 221))
            screen.blit(ability_surface, (x, ability_y))
            ability_y += 25

        return ability_y + 10

    def _render_ai_behavior(self, screen: pygame.Surface, character: CharacterData, x: int, y: int) -> int:
        """渲染AI行为"""
        # 标题
        title_surface = self._render_emoji_text(
            self.header_font, emoji_constants.BRAIN, "AI行为", character.color)
        screen.blit(title_surface, (x, y))

        # 行为列表
        behavior_y = y + 35
        for behavior in character.ai_behavior:
            bullet_surface = self._render_text(
                self.normal_font, emoji_constants.BULLET, character.color)
            screen.blit(bullet_surface, (x, behavior_y))

            behavior_lines = self._wrap_text(
                behavior, self.content_area_width - 60)
            for i, line in enumerate(behavior_lines):
                behavior_surface = self._render_text(
                    self.normal_font, line, (221, 221, 221))
                screen.blit(behavior_surface, (x + 20, behavior_y + i * 25))
            behavior_y += len(behavior_lines) * 25 + 10

        return behavior_y + 10

    def _render_tactics(self, screen: pygame.Surface, character: CharacterData, x: int, y: int) -> int:
        """渲染战术特点"""
        # 标题
        title_surface = self._render_emoji_text(
            self.header_font, emoji_constants.TARGET, "战术特点", character.color)
        screen.blit(title_surface, (x, y))

        # 战术列表
        tactics_y = y + 35
        for tactic in character.tactics:
            bullet_surface = self._render_text(
                self.normal_font, emoji_constants.BULLET, character.color)
            screen.blit(bullet_surface, (x, tactics_y))

            tactic_surface = self._render_text(
                self.normal_font, tactic, (221, 221, 221))
            screen.blit(tactic_surface, (x + 20, tactics_y))
            tactics_y += 25

        return tactics_y + 10

    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """文本换行"""
        words = text.split(' ')
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            text_surface = self._render_text(
                self.normal_font, test_line, (255, 255, 255))

            if text_surface.get_width() <= max_width:
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

    def get_stats_summary(self) -> Dict[str, int]:
        """获取统计摘要"""
        heroes = self.character_db.get_all_heroes()
        monsters = self.character_db.get_all_monsters()

        return {
            'total_heroes': len(heroes),
            'total_monsters': len(monsters),
            'total_characters': len(heroes) + len(monsters),
            'favorite_count': len(self.favorite_characters),
            'heroes_with_avatars': len([h for h in heroes.values() if h.avatar and os.path.exists(h.avatar)]),
            'monsters_with_avatars': len([m for m in monsters.values() if m.avatar and os.path.exists(m.avatar)])
        }

    def save_favorites(self, filename: str = "favorites.json"):
        """保存收藏列表"""
        import json
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(list(self.favorite_characters),
                          f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存收藏列表失败: {e}")

    def load_favorites(self, filename: str = "favorites.json"):
        """加载收藏列表"""
        import json
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    self.favorite_characters = set(json.load(f))
        except Exception as e:
            print(f"加载收藏列表失败: {e}")

    def export_character_data(self, filename: str = "character_export.json"):
        """导出角色数据"""
        import json
        try:
            export_data = {
                'heroes': {},
                'monsters': {},
                'favorites': list(self.favorite_characters),
                'stats': self.get_stats_summary()
            }

            for hero_id, hero in self.character_db.get_all_heroes().items():
                export_data['heroes'][hero_id] = {
                    'name': hero.name,
                    'english_name': hero.english_name,
                    'threat_level': hero.threat_level,
                    'hp': hero.hp,
                    'attack': hero.attack,
                    'speed': hero.speed,
                    'armor': hero.armor,
                    'attack_range': hero.attack_range,
                    'attack_cooldown': hero.attack_cooldown,
                    'special_ability': hero.special_ability,
                    'description': hero.description,
                    'color': hero.color,
                    'size': hero.size,
                    'avatar': hero.avatar,
                    'ai_behavior': hero.ai_behavior,
                    'tactics': hero.tactics
                }

            for monster_id, monster in self.character_db.get_all_monsters().items():
                export_data['monsters'][monster_id] = {
                    'name': monster.name,
                    'english_name': monster.english_name,
                    'hp': monster.hp,
                    'attack': monster.attack,
                    'speed': monster.speed,
                    'armor': monster.armor,
                    'attack_range': monster.attack_range,
                    'attack_cooldown': monster.attack_cooldown,
                    'special_ability': monster.special_ability,
                    'description': monster.description,
                    'color': monster.color,
                    'size': monster.size,
                    'avatar': monster.avatar,
                    'ai_behavior': monster.ai_behavior,
                    'tactics': monster.tactics,
                    'cost': monster.cost
                }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            print(f"角色数据已导出到 {filename}")

        except Exception as e:
            print(f"导出角色数据失败: {e}")

    def clear_search(self):
        """清空搜索"""
        self.search_text = ""
        self._calculate_max_scroll()

    def reset_view(self):
        """重置视图"""
        self.selected_character = None
        self.scroll_offset = 0
        self.search_text = ""
        self.show_favorites = False
        self._calculate_max_scroll()
