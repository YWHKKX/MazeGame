#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
骑士英雄实体模块
"""

import math
import random
import time
from typing import List, Dict, Optional, Tuple

# 导入需要的类型和配置
from src.core.constants import GameConstants, GameBalance
from src.core.enums import TileType, BuildMode
from src.core.game_state import Tile, GameState
from src.entities.heros import Hero
from src.utils.logger import game_logger
from src.managers.movement_system import MovementSystem
from src.ui.status_indicator import StatusIndicator


class Knight(Hero):
    """骑士 - 近战英雄单位"""

    def __init__(self, x: int, y: int):
        super().__init__(x, y, 'knight')

        # 设置友好的名称
        self.name = '骑士'

        # 骑士特有属性
        self.armor_value = 5  # 护甲值
        self.shield_block_chance = 0.3  # 盾牌格挡概率

        # 初始化移动系统状态
        MovementSystem.initialize_unit(self)

        # 状态指示器 - 使用通用系统
        try:
            self.status_indicator = StatusIndicator()
        except ImportError:
            self.status_indicator = None

    def update(self, delta_time: float, creatures: List, game_map: List[List[Tile]], effect_manager=None):
        """更新骑士行为"""
        # 调用父类更新方法
        super().update(delta_time, creatures, game_map, effect_manager)

    def _calculate_damage_modifiers(self, base_damage: int, target: 'Creature') -> int:
        """骑士伤害修正：无特殊修正"""
        # 骑士使用基础伤害，无护甲穿透
        return base_damage

    def _take_damage(self, damage: int, attacker: Optional['Creature'] = None) -> None:
        """骑士受到伤害 - 重写父类方法，加入护甲和格挡"""
        # 计算护甲减伤
        armor_reduction = min(self.armor_value, damage // 2)  # 护甲最多减少一半伤害
        actual_damage = damage - armor_reduction

        # 检查盾牌格挡
        if random.random() < self.shield_block_chance:
            actual_damage = 0
            game_logger.info(f"🛡️ {self.name} 盾牌格挡了攻击！")
        else:
            # 应用护甲减伤
            if armor_reduction > 0:
                game_logger.info(f"🛡️ {self.name} 护甲减少了 {armor_reduction} 点伤害")

        # 调用父类方法处理实际伤害
        super()._take_damage(actual_damage, attacker)

    def _setup_special_physics_properties(self) -> None:
        """设置特殊物理属性"""
        # 骑士有重甲，减少击退效果
        self.has_shield = True
        # 骑士体型较大
        self.size = 18

    def _get_attack_effect_type(self) -> str:
        """获取攻击特效类型"""
        return 'melee_slash'  # 骑士使用斩击特效

    def _is_melee_attack(self) -> bool:
        """判断是否为近战攻击"""
        return True  # 骑士是近战单位

    def render_status_indicator(self, screen, camera_x: int, camera_y: int):
        """渲染骑士状态指示器"""
        if not self.status_indicator:
            return

        # 计算屏幕位置
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        # 使用通用的状态指示器渲染
        self.status_indicator.render(
            screen, screen_x, screen_y, self.size, self.state)
