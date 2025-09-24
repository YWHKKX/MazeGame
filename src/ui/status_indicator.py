"""
状态指示器系统
为游戏中的生物提供统一的状态可视化指示器
"""

import pygame
from typing import Dict, Tuple, Optional
from src.core.ui_design import Colors, BorderRadius


class StatusIndicator:
    """状态指示器类 - 为生物、建筑和金矿提供状态可视化"""

    def __init__(self, width: int = 8, height: int = 4, border_thickness: int = 1):
        """
        初始化状态指示器

        Args:
            width: 指示器宽度（像素）
            height: 指示器高度（像素）
            border_thickness: 边框厚度（像素）
        """
        self.width = width
        self.height = height
        self.border_thickness = border_thickness

        # 默认状态颜色配置 - 使用设计系统颜色
        self.default_colors = {
            # 通用状态
            'fighting': Colors.ERROR,           # 红色 - 战斗中
            'moving': Colors.SUCCESS,           # 绿色 - 移动中
            'fleeing': Colors.GRAY_600,         # 深灰色 - 逃跑中
            'wandering': Colors.WARNING,        # 橙色 - 游荡中
            'idle': Colors.WHITE,               # 白色 - 空闲
            'default': Colors.GRAY_500,         # 默认灰色

            # 苦工专用状态
            'moving_to_mine': Colors.SUCCESS,   # 绿色 - 移动到挖掘点
            'mining': (139, 69, 19),            # 深棕色 - 挖掘中
            'returning_to_base': Colors.INFO,   # 青色 - 返回基地

            # 工程师专用状态
            'moving_to_site': Colors.SUCCESS,   # 绿色 - 前往工地
            'constructing': (139, 69, 19),      # 深棕色 - 建造中
            'repairing': Colors.GOLD,           # 黄色 - 修理中
            'upgrading': (138, 43, 226),        # 紫色 - 升级中
            'returning': Colors.INFO,           # 青色 - 返回中

            # 建筑状态
            'incomplete': (255, 100, 100),      # 红色 - 未完成建筑
            'destroyed': (255, 0, 0),           # 深红色 - 被摧毁建筑
            'damaged': (255, 255, 0),           # 黄色 - 受损建筑
            'completed': Colors.SUCCESS,        # 绿色 - 完成建筑

            # 金矿状态
            'mining_normal': (0, 255, 0),       # 绿色 - 正常挖掘
            'mining_busy': (255, 255, 0),       # 黄色 - 较多挖掘者
            'mining_full': (255, 100, 100),     # 红色 - 满员挖掘
            'depleted': (139, 69, 19),          # 棕色 - 枯竭矿脉
        }

        # 自定义颜色配置（可以被覆盖）
        self.custom_colors = {}

    def set_custom_color(self, state: str, color: Tuple[int, int, int]) -> None:
        """
        设置自定义状态颜色

        Args:
            state: 状态名称
            color: RGB颜色值
        """
        self.custom_colors[state] = color

    def get_color(self, state: str) -> Tuple[int, int, int]:
        """
        获取状态对应的颜色

        Args:
            state: 状态名称

        Returns:
            RGB颜色值
        """
        # 优先使用自定义颜色，然后使用默认颜色
        if state in self.custom_colors:
            return self.custom_colors[state]
        elif state in self.default_colors:
            return self.default_colors[state]
        else:
            return self.default_colors['default']

    def render(self, screen: pygame.Surface, creature_x: int, creature_y: int,
               creature_size: int, state: str) -> None:
        """
        渲染状态指示器

        Args:
            screen: pygame屏幕对象
            creature_x: 生物屏幕X坐标
            creature_y: 生物屏幕Y坐标
            creature_size: 生物大小
            state: 生物当前状态
        """
        # 计算指示器位置（生物右上角）
        indicator_x = creature_x + creature_size//2 - self.width//2
        indicator_y = creature_y - creature_size//2 - self.height - 2

        # 获取状态颜色
        color = self.get_color(state)

        # 绘制圆角矩形指示器，更美观
        indicator_rect = pygame.Rect(
            indicator_x, indicator_y, self.width, self.height)
        pygame.draw.rect(screen, color, indicator_rect,
                         self.border_thickness, BorderRadius.SM)

    def render_building_highlight(self, screen: pygame.Surface, screen_x: int,
                                  screen_y: int, tile_size: int, status: str) -> None:
        """
        渲染建筑状态高亮 - 只绘制边框，不填充中间区域

        Args:
            screen: pygame屏幕对象
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            status: 建筑状态 ('incomplete', 'destroyed', 'damaged', 'completed')
        """
        if status not in ['incomplete', 'destroyed', 'damaged', 'completed']:
            return

        # 获取原始颜色并降低透明度
        original_color = self.get_color(status)
        # 将颜色调暗，避免遮挡生命条
        border_color = tuple(max(0, int(c * 0.6)) for c in original_color)
        border_width = 1  # 减少边框宽度

        # 根据状态调整边框样式 - 进一步削弱
        if status == 'destroyed':
            border_width = 2  # 被摧毁建筑使用稍粗的边框
        elif status == 'incomplete':
            border_width = 1  # 未完成建筑使用最细的边框
        elif status == 'completed':
            border_width = 1  # 完成建筑使用最细的边框
        elif status == 'damaged':
            border_width = 1  # 受损建筑使用最细的边框

        # 绘制状态边框 - 只绘制边框，不填充中间区域
        pygame.draw.rect(screen, border_color,
                         (screen_x, screen_y, tile_size, tile_size), border_width)

    def render_mining_highlight(self, screen: pygame.Surface, screen_x: int,
                                screen_y: int, tile_size: int, miners_count: int) -> None:
        """
        渲染金矿挖掘状态高亮

        Args:
            screen: pygame屏幕对象
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            miners_count: 挖掘者数量
        """
        # 根据挖掘者数量选择边框颜色和样式
        if miners_count >= 3:
            # 满员：红色脉冲边框
            border_color = self.get_color('mining_full')
            border_width = 3
        elif miners_count >= 2:
            # 较多：黄色边框
            border_color = self.get_color('mining_busy')
            border_width = 2
        else:
            # 正常：绿色边框
            border_color = self.get_color('mining_normal')
            border_width = 2

        # 绘制挖掘状态边框
        pygame.draw.rect(screen, border_color,
                         (screen_x, screen_y, tile_size, tile_size), border_width)

    def get_status_description(self, state: str) -> str:
        """
        获取状态的文字描述

        Args:
            state: 状态名称

        Returns:
            状态描述文字
        """
        descriptions = {
            # 通用状态
            'fighting': '战斗中',
            'moving': '移动中',
            'fleeing': '逃跑中',
            'wandering': '游荡中',
            'idle': '空闲',

            # 苦工专用状态
            'moving_to_mine': '移动到挖掘点',
            'mining': '挖掘中',
            'returning_to_base': '返回基地',

            # 工程师专用状态
            'moving_to_site': '前往工地',
            'constructing': '建造中',
            'repairing': '修理中',
            'upgrading': '升级中',
            'returning': '返回中',

            # 建筑状态
            'incomplete': '未完成建筑',
            'destroyed': '被摧毁建筑',
            'damaged': '受损建筑',
            'completed': '完成建筑',

            # 金矿状态
            'mining_normal': '正常挖掘',
            'mining_busy': '较多挖掘者',
            'mining_full': '满员挖掘',
            'depleted': '枯竭矿脉'
        }
        return descriptions.get(state, '未知状态')

    def get_all_states(self) -> list:
        """
        获取所有支持的状态列表

        Returns:
            状态名称列表
        """
        return list(self.default_colors.keys())

    def get_status_info(self, state: str) -> Dict:
        """
        获取状态的完整信息

        Args:
            state: 状态名称

        Returns:
            包含颜色、描述等信息的字典
        """
        return {
            'state': state,
            'color': self.get_color(state),
            'description': self.get_status_description(state),
            'rgb': self.get_color(state)
        }


class StatusIndicatorManager:
    """状态指示器管理器 - 管理多个状态指示器实例"""

    def __init__(self):
        """初始化管理器"""
        self.indicators = {}
        self.default_indicator = StatusIndicator()

    def create_indicator(self, name: str, width: int = 4, height: int = 8,
                         border_thickness: int = 1) -> StatusIndicator:
        """
        创建新的状态指示器

        Args:
            name: 指示器名称
            width: 指示器宽度
            height: 指示器高度
            border_thickness: 边框厚度

        Returns:
            新创建的状态指示器
        """
        indicator = StatusIndicator(width, height, border_thickness)
        self.indicators[name] = indicator
        return indicator

    def get_indicator(self, name: str) -> StatusIndicator:
        """
        获取指定的状态指示器

        Args:
            name: 指示器名称

        Returns:
            状态指示器实例，如果不存在则返回默认指示器
        """
        return self.indicators.get(name, self.default_indicator)

    def remove_indicator(self, name: str) -> bool:
        """
        移除指定的状态指示器

        Args:
            name: 指示器名称

        Returns:
            是否成功移除
        """
        if name in self.indicators:
            del self.indicators[name]
            return True
        return False

    def list_indicators(self) -> list:
        """
        获取所有指示器名称列表

        Returns:
            指示器名称列表
        """
        return list(self.indicators.keys())
