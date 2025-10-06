#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小恶魔实体模块
"""

import math
import random
import time
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING

# 导入需要的类型和配置
from src.core.constants import GameConstants, GameBalance
from src.core.enums import TileType, BuildMode
from src.core.game_state import Tile, GameState
from src.entities.monsters import Monster
from src.utils.logger import game_logger
from src.managers.movement_system import MovementSystem
from src.ui.status_indicator import StatusIndicator

if TYPE_CHECKING:
    from src.entities.creature import Creature


class Imp(Monster):
    """小恶魔 - 基础怪物单位"""

    def __init__(self, x: int, y: int):
        super().__init__(x, y, 'imp')

        # 设置友好的名称
        self.name = '小恶魔'

        # 设置为战斗单位
        self.is_combat_unit = True

        # 小恶魔特有属性 - 行为相关，不覆盖基础属性
        self.aggression_level = 0.7  # 攻击性等级 (0-1)
        self.fear_threshold = 0.3    # 恐惧阈值 (生命值比例)

        # 巢穴绑定
        self.bound_lair = None  # 绑定的恶魔巢穴
        self.bound_lair_position = None  # 巢穴位置

        # 注意：current_target, target_last_seen_time, last_attack 已在父类Monster中初始化

        # 初始化移动系统状态
        MovementSystem.initialize_unit(self)

        # 状态指示器 - 使用通用系统
        try:
            self.status_indicator = StatusIndicator()
        except ImportError:
            self.status_indicator = None

    def update(self, delta_time: float, game_map: List[List[Tile]], creatures: List['Creature'], heroes: List = None, effect_manager=None, building_manager=None, game_instance=None):
        """更新小恶魔行为"""
        # 首先调用父类的update方法，包含状态切换器
        super().update(delta_time, creatures, game_map, effect_manager)

        # 然后执行小恶魔特有的行为逻辑
        self._update_imp_behavior(
            delta_time, game_map, heroes or [], effect_manager)

        # 管理空闲状态
        self._manage_idle_state(game_instance)

    def _update_imp_behavior(self, delta_time: float, game_map: List[List[Tile]], heroes: List, effect_manager=None):
        """小恶魔行为更新 - 按照COMBAT_SYSTEM.md规范实现"""
        # 优先级1: 血量过低时逃跑
        if self.health <= self.max_health * self.fear_threshold:
            self.state = 'fleeing'
            # 寻找最近的英雄作为逃跑目标
            nearest_hero = self._find_nearest_hero(heroes, 200)
            if nearest_hero:
                # 使用逃离移动，速度提升30%
                MovementSystem.flee_movement(
                    self, (nearest_hero.x, nearest_hero.y), delta_time, game_map, 1.3)
            else:
                # 没有英雄时随机游荡
                MovementSystem.wandering_movement(
                    self, delta_time, game_map, 0.5)
            return

        # 优先级2: 寻找攻击目标
        if not self.current_target or not hasattr(self.current_target, 'health') or self.current_target.health <= 0:
            self.current_target = self._find_nearest_hero(heroes, 150)
            if self.current_target:
                self.state = 'hunting'
                self.target_last_seen_time = time.time()

        if self.current_target:
            # 计算到目标的距离
            dx = self.current_target.x - self.x
            dy = self.current_target.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= self.attack_range:
                # 在攻击范围内，设置攻击状态
                # 攻击逻辑由上层战斗系统统一处理
                self.state = 'attacking'
            else:
                # 不在攻击范围内，移动到目标
                self.state = 'hunting'
                target_pos = (self.current_target.x, self.current_target.y)
                MovementSystem.pathfind_and_move(
                    self, target_pos, delta_time, game_map, "A_STAR", 1.0)
        else:
            # 没有目标时游荡
            self.state = 'wandering'
            MovementSystem.wandering_movement(self, delta_time, game_map, 0.3)

    def _find_nearest_hero(self, heroes: List, max_distance: float):
        """寻找最近的敌方英雄"""
        nearest_hero = None
        nearest_distance = float('inf')

        for hero in heroes:
            # 只攻击敌方英雄
            if hasattr(hero, 'is_enemy') and hero.is_enemy:
                distance = math.sqrt((hero.x - self.x) **
                                     2 + (hero.y - self.y) ** 2)
                if distance < max_distance and distance < nearest_distance:
                    nearest_distance = distance
                    nearest_hero = hero

        return nearest_hero

    def _setup_special_physics_properties(self) -> None:
        """设置特殊物理属性"""
        # 小恶魔体型小，容易被击退
        self.size = 12  # 比默认稍小
        # 没有特殊护盾或抗性
        self.has_shield = False
        self.is_rooted = False

    def _get_attack_effect_type(self) -> str:
        """获取攻击特效类型"""
        return 'claw_attack'  # 小恶魔使用爪击特效

    def _is_melee_attack(self) -> bool:
        """判断是否为近战攻击"""
        return True  # 小恶魔是近战单位

    def bind_to_lair(self, lair):
        """绑定到恶魔巢穴"""
        self.bound_lair = lair
        if lair:
            self.bound_lair_position = (lair.x, lair.y)
            # 确保小恶魔是友方单位，不会攻击友方建筑
            self.is_enemy = False
            game_logger.info(
                f"🔗 {self.name} 绑定到恶魔巢穴 at ({lair.x}, {lair.y}) - 设置为友方单位")

    def render_status_indicator(self, screen, camera_x: int, camera_y: int):
        """渲染小恶魔状态指示器"""
        if not self.status_indicator:
            return

        # 计算屏幕位置
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        # 使用通用的状态指示器渲染
        self.status_indicator.render(
            screen, screen_x, screen_y, self.size, self.state)
