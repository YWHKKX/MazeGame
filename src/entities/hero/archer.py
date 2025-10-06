#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
弓箭手英雄实体模块
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


class Archer(Hero):
    """弓箭手 - 远程英雄单位"""

    def __init__(self, x: int, y: int):
        super().__init__(x, y, 'archer')

        # 设置友好的名称
        self.name = '弓箭手'

        # 弓箭手特有属性
        self.arrow_count = 50  # 箭矢数量
        self.max_arrows = 50   # 最大箭矢数量
        self.arrow_damage = 25  # 箭矢伤害
        self.critical_chance = 0.25  # 暴击概率
        self.critical_multiplier = 2.0  # 暴击倍数
        self.piercing_shot_chance = 0.15  # 穿透射击概率
        self.multi_shot_chance = 0.1  # 多重射击概率
        self.arrow_regen_rate = 1  # 每秒恢复箭矢数量
        self.last_arrow_regen = 0  # 上次恢复箭矢时间

        # 初始化移动系统状态
        MovementSystem.initialize_unit(self)

        # 状态指示器 - 使用通用系统
        try:
            self.status_indicator = StatusIndicator()
        except ImportError:
            self.status_indicator = None

    def update(self, delta_time: float, creatures: List, game_map: List[List[Tile]], effect_manager=None):
        """更新弓箭手行为"""
        # 恢复箭矢
        self._regenerate_arrows(delta_time)

        # 调用父类更新方法
        super().update(delta_time, creatures, game_map, effect_manager)

    def _regenerate_arrows(self, delta_time: float):
        """恢复箭矢"""
        current_time = time.time()
        if current_time - self.last_arrow_regen >= 1.0:  # 每秒恢复一次
            if self.arrow_count < self.max_arrows:
                old_count = self.arrow_count
                self.arrow_count = min(
                    self.max_arrows, self.arrow_count + self.arrow_regen_rate)
                if self.arrow_count > old_count:
                    game_logger.info(
                        f"🏹 {self.name} 恢复了 {self.arrow_count - old_count} 支箭矢 ({self.arrow_count}/{self.max_arrows})")
            self.last_arrow_regen = current_time

    def _execute_attack(self, target: 'Creature', delta_time: float, effect_manager=None) -> bool:
        """执行攻击 - 重写父类方法，添加箭矢检查"""
        if not target or target.health <= 0:
            return False

        # 检查箭矢数量
        if self.arrow_count <= 0:
            game_logger.info(f"🏹 {self.name} 没有箭矢了！")
            return False

        # 计算到目标的距离
        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        # 检查是否在攻击范围内
        if distance > self.attack_range:
            return False

        # 消耗箭矢
        self.arrow_count -= 1

        # 调用父类攻击逻辑
        result = super()._execute_attack(target, delta_time, effect_manager)

        # 记录箭矢状态
        game_logger.info(
            f"🏹 {self.name} 剩余箭矢: {self.arrow_count}/{self.max_arrows}")

        return result

    def _calculate_damage_modifiers(self, base_damage: int, target: 'Creature') -> int:
        """弓箭手伤害修正：暴击和特殊射击"""
        # 检查暴击
        is_critical = random.random() < self.critical_chance
        if is_critical:
            base_damage = int(base_damage * self.critical_multiplier)
            game_logger.info(f"💥 {self.name} 暴击射击！")

        # 检查特殊射击
        shot_type = self._determine_shot_type()
        if shot_type == 'piercing':
            base_damage = int(base_damage * 1.5)  # 穿透射击伤害增加50%
            game_logger.info(f"🏹 {self.name} 使用穿透射击！")
        elif shot_type == 'multi':
            # 多重射击：对附近敌人造成伤害
            self._perform_multi_shot(target, base_damage)
            return base_damage  # 返回基础伤害，多重射击会单独处理

        return base_damage

    def _determine_shot_type(self) -> str:
        """确定射击类型"""
        if random.random() < self.piercing_shot_chance:
            return 'piercing'
        elif random.random() < self.multi_shot_chance:
            return 'multi'
        else:
            return 'normal'

    def _perform_multi_shot(self, primary_target: 'Creature', damage: int):
        """执行多重射击"""
        # 寻找附近的敌人
        nearby_targets = self._find_nearby_enemies(
            primary_target, 80)  # 80像素范围内

        # 对附近敌人造成伤害
        for target in nearby_targets[:2]:  # 最多攻击2个额外目标
            if target != primary_target:
                # 使用战斗系统处理多重射击伤害
                if hasattr(self, 'game_instance') and self.game_instance and hasattr(self.game_instance, 'combat_system'):
                    self.game_instance.combat_system._apply_damage(
                        self, target, int(damage * 0.7))
                else:
                    target._take_damage(int(damage * 0.7), self)

        game_logger.info(
            f"🏹 {self.name} 多重射击，攻击了 {len(nearby_targets) + 1} 个目标")

    def _find_nearby_enemies(self, primary_target: 'Creature', radius: float) -> List['Creature']:
        """寻找附近的敌人"""
        nearby_enemies = []
        for creature in self.game_instance.monsters if hasattr(self, 'game_instance') and self.game_instance else []:
            if creature == primary_target or creature.health <= 0:
                continue

            # 检查是否为敌人
            if not self._is_enemy_of(creature):
                continue

            # 计算距离
            dx = creature.x - self.x
            dy = creature.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance <= radius:
                nearby_enemies.append(creature)

        return nearby_enemies

    def _create_shot_effect(self, target: 'Creature', damage: int, effect_manager, shot_type: str, camera_x: float = 0, camera_y: float = 0) -> bool:
        """创建射击特效"""
        # 计算攻击方向
        dx = target.x - self.x
        dy = target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 归一化方向向量
            dx /= distance
            dy /= distance

            # 将世界坐标转换为屏幕坐标
            screen_x = self.x - camera_x
            screen_y = self.y - camera_y
            target_screen_x = target.x - camera_x
            target_screen_y = target.y - camera_y

            # 根据射击类型选择特效
            effect_type = 'arrow_shot'
            if shot_type == 'piercing':
                effect_type = 'piercing_arrow'
            elif shot_type == 'multi':
                effect_type = 'multi_arrow'

            success = effect_manager.create_visual_effect(
                effect_type=effect_type,
                x=screen_x,
                y=screen_y,
                target_x=target_screen_x,
                target_y=target_screen_y,
                damage=damage
            )
            return success

        return False

    def _setup_special_physics_properties(self) -> None:
        """设置特殊物理属性"""
        # 弓箭手体型较小，容易被击退
        self.size = 14
        # 没有特殊护盾
        self.has_shield = False

    def _get_attack_effect_type(self) -> str:
        """获取攻击特效类型"""
        return 'arrow_shot'  # 弓箭手使用箭矢特效

    def _is_melee_attack(self) -> bool:
        """判断是否为近战攻击"""
        return False  # 弓箭手是远程单位

    def get_arrow_status(self) -> Dict[str, any]:
        """获取箭矢状态"""
        return {
            'current_arrows': self.arrow_count,
            'max_arrows': self.max_arrows,
            'regen_rate': self.arrow_regen_rate,
            'critical_chance': self.critical_chance,
            'piercing_chance': self.piercing_shot_chance,
            'multi_shot_chance': self.multi_shot_chance
        }

    def add_arrows(self, amount: int) -> int:
        """添加箭矢"""
        old_count = self.arrow_count
        self.arrow_count = min(self.max_arrows, self.arrow_count + amount)
        added = self.arrow_count - old_count
        if added > 0:
            game_logger.info(
                f"🏹 {self.name} 获得了 {added} 支箭矢 ({self.arrow_count}/{self.max_arrows})")
        return added

    def render_status_indicator(self, screen, camera_x: int, camera_y: int):
        """渲染弓箭手状态指示器"""
        if not self.status_indicator:
            return

        # 计算屏幕位置
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        # 使用通用的状态指示器渲染
        self.status_indicator.render(
            screen, screen_x, screen_y, self.size, self.state)
