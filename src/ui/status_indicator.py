"""
状态指示器系统
为游戏中的生物提供统一的状态可视化指示器
"""

import pygame
from typing import Dict, Tuple, Optional
from enum import Enum
from src.core.ui_design import Colors, BorderRadius
from src.core.constants import GameConstants


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
        self.default_colors = self._get_default_colors()

        # 自定义颜色配置（可以被覆盖）
        self.custom_colors = {}

    def _get_default_colors(self) -> Dict[str, Tuple[int, int, int]]:
        """获取默认状态颜色配置 - 动态引用枚举"""
        colors = {}

        # 通用状态
        colors.update({
            'fighting': Colors.ERROR,           # 红色 - 战斗中
            'moving': Colors.SUCCESS,           # 绿色 - 移动中
            'fleeing': Colors.GRAY_600,         # 深灰色 - 逃跑中
            'wandering': Colors.WARNING,        # 橙色 - 游荡中
            'idle': Colors.WHITE,               # 白色 - 空闲
            'default': Colors.GRAY_500,         # 默认灰色
        })

        # 动态导入并添加通用生物状态
        try:
            from src.entities.creature import CreatureStatus
            colors.update({
                CreatureStatus.IDLE.value: Colors.WHITE,                    # 白色 - 空闲
                CreatureStatus.WANDERING.value: Colors.WARNING,             # 橙色 - 游荡中
                CreatureStatus.FIGHTING.value: Colors.ERROR,                # 红色 - 战斗中
                CreatureStatus.FLEEING.value: Colors.GRAY_600,              # 深灰色 - 逃跑中
                CreatureStatus.MOVING.value: Colors.SUCCESS,                # 绿色 - 移动中
            })
        except ImportError:
            pass

        # 动态导入并添加工程师状态
        try:
            from src.entities.monster.goblin_engineer import EngineerStatus
            colors.update({
                EngineerStatus.IDLE.value: Colors.WHITE,                    # 白色 - 空闲
                EngineerStatus.WANDERING.value: Colors.WARNING,             # 橙色 - 游荡中
                EngineerStatus.FETCHING_RESOURCES.value: Colors.SUCCESS,    # 绿色 - 获取资源中
                EngineerStatus.MOVING_TO_SITE.value: Colors.SUCCESS,        # 绿色 - 前往工地
                EngineerStatus.CONSTRUCTING.value: Colors.WARNING,          # 橙色 - 建造中
                EngineerStatus.REPAIRING.value: Colors.GOLD,                # 黄色 - 修理中
                EngineerStatus.UPGRADING.value: Colors.MANA,                # 紫色 - 升级中
                EngineerStatus.RELOADING.value: Colors.WARNING,             # 橙色 - 装填中
                EngineerStatus.DEPOSITING_GOLD.value: Colors.WARNING,       # 橙色 - 存储金币中
                EngineerStatus.RETURNING_TO_BASE.value: Colors.INFO,        # 青色 - 返回基地
            })
        except ImportError:
            pass

        # 动态导入并添加苦工状态
        try:
            from src.entities.monster.goblin_worker import WorkerStatus
            colors.update({
                WorkerStatus.IDLE.value: Colors.WHITE,                      # 白色 - 空闲
                WorkerStatus.WANDERING.value: Colors.WARNING,               # 橙色 - 游荡中
                WorkerStatus.MOVING_TO_MINE.value: Colors.SUCCESS,          # 绿色 - 移动到挖掘点
                WorkerStatus.MINING.value: Colors.WARNING,                  # 橙色 - 挖掘中
                WorkerStatus.RETURNING_TO_BASE.value: Colors.INFO,          # 青色 - 返回基地
                WorkerStatus.MOVING_TO_TRAINING.value: Colors.SUCCESS,      # 绿色 - 前往训练地点
                # 褐色 - 训练中
                WorkerStatus.TRAINING.value: (139, 69, 19),
                WorkerStatus.FLEEING.value: Colors.GRAY_600,                # 深灰色 - 逃跑中
            })
        except ImportError:
            pass

        # 动态导入并添加兽人战士状态
        try:
            from src.entities.monster.orc_warrior import OrcWarriorStatus
            colors.update({
                OrcWarriorStatus.WANDERING.value: Colors.WARNING,           # 橙色 - 游荡中
                OrcWarriorStatus.HUNTING.value: Colors.SUCCESS,             # 绿色 - 追击目标
                OrcWarriorStatus.ATTACKING.value: Colors.ERROR,             # 红色 - 攻击中
                OrcWarriorStatus.RETURNING.value: Colors.INFO,              # 青色 - 返回巢穴
                OrcWarriorStatus.GUARDING.value: Colors.MANA,               # 紫色 - 守卫巢穴
                # 浅绿色 - 巡逻中
                OrcWarriorStatus.PATROLLING.value: (100, 200, 100),
            })
        except ImportError:
            pass

        # 建筑状态 - 统一使用常量配置
        colors.update({
            GameConstants.BUILDING_STATUS_INCOMPLETE: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_INCOMPLETE],
            GameConstants.BUILDING_STATUS_DESTROYED: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_DESTROYED],
            GameConstants.BUILDING_STATUS_NEEDS_REPAIR: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_NEEDS_REPAIR],
            GameConstants.BUILDING_STATUS_COMPLETED: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_COMPLETED],
            GameConstants.BUILDING_STATUS_NO_AMMUNITION: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_NO_AMMUNITION],
            GameConstants.BUILDING_STATUS_TREASURY_FULL: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_TREASURY_FULL],
            GameConstants.BUILDING_STATUS_NEEDS_MAGE: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_NEEDS_MAGE],
            GameConstants.BUILDING_STATUS_MANA_FULL: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_MANA_FULL],
            GameConstants.BUILDING_STATUS_MANA_GENERATION: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_MANA_GENERATION],
            GameConstants.BUILDING_STATUS_TRAINING: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_TRAINING],
            GameConstants.BUILDING_STATUS_SUMMONING: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_SUMMONING],
            GameConstants.BUILDING_STATUS_SUMMONING_PAUSED: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_SUMMONING_PAUSED],
            GameConstants.BUILDING_STATUS_LOCKED: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_LOCKED],
            GameConstants.BUILDING_STATUS_READY_TO_TRAIN: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_READY_TO_TRAIN],
            GameConstants.BUILDING_STATUS_READY_TO_SUMMON: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_READY_TO_SUMMON],
            GameConstants.BUILDING_STATUS_ACCEPTING_GOLD: GameConstants.BUILDING_STATUS_COLORS[GameConstants.BUILDING_STATUS_ACCEPTING_GOLD],
        })

        # 金矿状态
        colors.update({
            'mining_normal': Colors.SUCCESS,    # 绿色 - 正常挖掘
            'mining_busy': Colors.WARNING,      # 黄色 - 较多挖掘者
            'mining_full': Colors.ERROR,        # 红色 - 满员挖掘
            'depleted': Colors.WARNING,         # 橙色 - 枯竭矿脉
        })

        return colors

    def _get_status_descriptions(self) -> Dict[str, str]:
        """获取状态描述配置 - 动态引用枚举"""
        descriptions = {}

        # 通用状态
        descriptions.update({
            'fighting': '战斗中',
            'moving': '移动中',
            'fleeing': '逃跑中',
            'wandering': '游荡中',
            'idle': '空闲',
        })

        # 动态导入并添加通用生物状态描述
        try:
            from src.entities.creature import CreatureStatus
            descriptions.update({
                CreatureStatus.IDLE.value: '空闲',
                CreatureStatus.WANDERING.value: '游荡中',
                CreatureStatus.FIGHTING.value: '战斗中',
                CreatureStatus.FLEEING.value: '逃跑中',
                CreatureStatus.MOVING.value: '移动中',
            })
        except ImportError:
            pass

        # 动态导入并添加工程师状态描述
        try:
            from src.entities.monster.goblin_engineer import EngineerStatus
            descriptions.update({
                EngineerStatus.IDLE.value: '空闲',
                EngineerStatus.WANDERING.value: '游荡中',
                EngineerStatus.FETCHING_RESOURCES.value: '获取资源',
                EngineerStatus.MOVING_TO_SITE.value: '前往工地',
                EngineerStatus.CONSTRUCTING.value: '建造中',
                EngineerStatus.REPAIRING.value: '修理中',
                EngineerStatus.UPGRADING.value: '升级中',
                EngineerStatus.RELOADING.value: '装填中',
                EngineerStatus.DEPOSITING_GOLD.value: '存储金币中',
                EngineerStatus.RETURNING_TO_BASE.value: '返回基地',
            })
        except ImportError:
            pass

        # 动态导入并添加苦工状态描述
        try:
            from src.entities.monster.goblin_worker import WorkerStatus
            descriptions.update({
                WorkerStatus.IDLE.value: '空闲',
                WorkerStatus.WANDERING.value: '游荡中',
                WorkerStatus.MOVING_TO_MINE.value: '移动到挖掘点',
                WorkerStatus.MINING.value: '挖掘中',
                WorkerStatus.RETURNING_TO_BASE.value: '返回基地',
                WorkerStatus.MOVING_TO_TRAINING.value: '前往训练地点',
                WorkerStatus.TRAINING.value: '训练中',
                WorkerStatus.FLEEING.value: '逃跑中',
            })
        except ImportError:
            pass

        # 动态导入并添加兽人战士状态描述
        try:
            from src.entities.monster.orc_warrior import OrcWarriorStatus
            descriptions.update({
                OrcWarriorStatus.WANDERING.value: '游荡中',
                OrcWarriorStatus.HUNTING.value: '追击目标',
                OrcWarriorStatus.ATTACKING.value: '攻击中',
                OrcWarriorStatus.RETURNING.value: '返回巢穴',
                OrcWarriorStatus.GUARDING.value: '守卫巢穴',
                OrcWarriorStatus.PATROLLING.value: '巡逻中',
            })
        except ImportError:
            pass

        # 建筑状态描述
        descriptions.update({
            GameConstants.BUILDING_STATUS_INCOMPLETE: '未完成建筑',
            GameConstants.BUILDING_STATUS_DESTROYED: '被摧毁建筑',
            GameConstants.BUILDING_STATUS_NEEDS_REPAIR: '需要修复',
            GameConstants.BUILDING_STATUS_NO_AMMUNITION: '空弹药',
            GameConstants.BUILDING_STATUS_TREASURY_FULL: '金库爆满',
            GameConstants.BUILDING_STATUS_COMPLETED: '完成建筑',
            GameConstants.BUILDING_STATUS_NEEDS_MAGE: '需要法师',
            GameConstants.BUILDING_STATUS_MANA_FULL: '法力已满',
            GameConstants.BUILDING_STATUS_MANA_GENERATION: '魔力生成',
        })

        # 金矿状态描述
        descriptions.update({
            'mining_normal': '正常挖掘',
            'mining_busy': '较多挖掘者',
            'mining_full': '满员挖掘',
            'depleted': '枯竭矿脉'
        })

        return descriptions

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
               creature_size: int, state: str, ui_scale: float = 1.0) -> None:
        """
        渲染状态指示器

        Args:
            screen: pygame屏幕对象
            creature_x: 生物屏幕X坐标
            creature_y: 生物屏幕Y坐标
            creature_size: 生物大小（已应用UI缩放）
            state: 生物当前状态
            ui_scale: UI缩放倍数
        """
        # 计算指示器位置（生物右上角），应用UI缩放
        scaled_width = int(self.width * ui_scale)
        scaled_height = int(self.height * ui_scale)
        scaled_border_thickness = max(1, int(self.border_thickness * ui_scale))

        indicator_x = creature_x + creature_size//2 - scaled_width//2
        indicator_y = creature_y - creature_size//2 - \
            scaled_height - max(1, int(2 * ui_scale))

        # 获取状态颜色
        color = self.get_color(state)

        # 绘制圆角矩形指示器，更美观
        indicator_rect = pygame.Rect(
            indicator_x, indicator_y, scaled_width, scaled_height)
        pygame.draw.rect(screen, color, indicator_rect,
                         scaled_border_thickness, BorderRadius.SM)

    def render_building_highlight(self, screen: pygame.Surface, screen_x: int,
                                  screen_y: int, tile_size: int, status: str, ui_scale: float = 1.0) -> None:
        """
        渲染建筑状态高亮 - 只绘制边框，不填充中间区域

        Args:
            screen: pygame屏幕对象
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            status: 建筑状态 ('incomplete', 'destroyed', 'needs_repair', 'completed', 'no_ammunition', 'treasury_full')
            ui_scale: UI缩放倍数
        """
        # 使用常量检查状态
        valid_statuses = [
            GameConstants.BUILDING_STATUS_INCOMPLETE,
            GameConstants.BUILDING_STATUS_DESTROYED,
            GameConstants.BUILDING_STATUS_NEEDS_REPAIR,
            GameConstants.BUILDING_STATUS_COMPLETED,
            GameConstants.BUILDING_STATUS_NO_AMMUNITION,
            GameConstants.BUILDING_STATUS_TREASURY_FULL,
            GameConstants.BUILDING_STATUS_NEEDS_MAGE,
            GameConstants.BUILDING_STATUS_MANA_FULL,
            GameConstants.BUILDING_STATUS_MANA_GENERATION,
            GameConstants.BUILDING_STATUS_TRAINING,
            GameConstants.BUILDING_STATUS_SUMMONING,
            GameConstants.BUILDING_STATUS_SUMMONING_PAUSED,
            GameConstants.BUILDING_STATUS_LOCKED,
            GameConstants.BUILDING_STATUS_READY_TO_TRAIN,
            GameConstants.BUILDING_STATUS_READY_TO_SUMMON,
            GameConstants.BUILDING_STATUS_ACCEPTING_GOLD
        ]
        if status not in valid_statuses:
            return

        # 获取原始颜色，保持100%亮度
        original_color = self.get_color(status)
        # 保持100%颜色亮度
        border_color = original_color
        base_border_width = 1.5  # 统一使用1.5px边框

        # 应用UI缩放
        scaled_tile_size = int(tile_size * ui_scale)
        border_width = max(1, int(base_border_width * ui_scale))

        # 绘制状态边框 - 只绘制边框，不填充中间区域
        # 直接使用传入的tile_size参数，支持2x2建筑
        pygame.draw.rect(screen, border_color,
                         (screen_x, screen_y, scaled_tile_size, scaled_tile_size), border_width)

    def render_mining_highlight(self, screen: pygame.Surface, screen_x: int,
                                screen_y: int, tile_size: int, miners_count: int, ui_scale: float = 1.0) -> None:
        """
        渲染金矿挖掘状态高亮

        Args:
            screen: pygame屏幕对象
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            miners_count: 挖掘者数量
            ui_scale: UI缩放倍数
        """
        # 根据挖掘者数量选择边框颜色和样式
        if miners_count >= 3:
            # 满员：红色脉冲边框
            border_color = self.get_color('mining_full')
            base_border_width = 3
        elif miners_count >= 2:
            # 较多：黄色边框
            border_color = self.get_color('mining_busy')
            base_border_width = 2
        else:
            # 正常：绿色边框
            border_color = self.get_color('mining_normal')
            base_border_width = 2

        # 应用UI缩放
        scaled_tile_size = int(tile_size * ui_scale)
        border_width = max(1, int(base_border_width * ui_scale))

        # 绘制挖掘状态边框
        pygame.draw.rect(screen, border_color,
                         (screen_x, screen_y, scaled_tile_size, scaled_tile_size), border_width)

    def get_status_description(self, state: str) -> str:
        """
        获取状态的文字描述

        Args:
            state: 状态名称

        Returns:
            状态描述文字
        """
        descriptions = self._get_status_descriptions()
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

    def render_carried_gold(self, screen: pygame.Surface, character_x: int, character_y: int,
                            character_size: int, carried_gold: int, ui_scale: float = 1.0,
                            font: pygame.font.Font = None, cached_texts: Dict = None,
                            font_manager=None) -> None:
        """
        渲染角色携带的金币数 - 使用新的字体管理器

        Args:
            screen: pygame屏幕对象
            character_x: 角色屏幕X坐标
            character_y: 角色屏幕Y坐标
            character_size: 角色大小（已应用UI缩放）
            carried_gold: 携带的金币数量
            ui_scale: UI缩放倍数
            font: 字体对象，如果为None则使用默认字体
            cached_texts: 文本缓存字典，用于性能优化
            font_manager: 字体管理器，用于高质量渲染
        """
        if carried_gold <= 0:
            return

        # 使用传入的字体或创建默认字体（适当大小并加粗）
        if font is None:
            # 创建加粗字体 - 使用系统字体并设置加粗，增大字体尺寸
            try:
                font = pygame.font.SysFont("Arial", 16, bold=True)
            except:
                # 回退到默认字体
                font = pygame.font.Font(None, 16)

        # 生成缓存键
        gold_key = f"gold_{carried_gold}_medium"

        # 如果提供了字体管理器，使用高质量加粗渲染
        if font_manager is not None:
            if cached_texts is not None:
                if gold_key not in cached_texts:
                    # 使用字体管理器的专门金币文本渲染方法（加粗、抗锯齿）
                    cached_texts[gold_key] = font_manager.render_gold_text(
                        f"${carried_gold}", (255, 255, 0), 16)
                gold_surface = cached_texts[gold_key]
            else:
                # 直接使用字体管理器渲染
                gold_surface = font_manager.render_gold_text(
                    f"${carried_gold}", (255, 255, 0), 16)
        else:
            # 回退到传统渲染方式（使用加粗字体）
            if cached_texts is not None:
                if gold_key not in cached_texts:
                    cached_texts[gold_key] = font.render(
                        f"${carried_gold}", True, (255, 255, 0))
                gold_surface = cached_texts[gold_key]
            else:
                gold_surface = font.render(
                    f"${carried_gold}", True, (255, 255, 0))

        # 计算文本位置（角色上方）
        text_offset = int(15 * ui_scale)
        text_x = character_x
        text_y = character_y - text_offset

        # 渲染文本
        screen.blit(gold_surface, (text_x, text_y))


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
