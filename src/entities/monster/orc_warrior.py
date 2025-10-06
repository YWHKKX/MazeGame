#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兽人战士 - 通过兽人巢穴训练产生的军事单位
参考骑士的属性设计，具有强大的近战攻击能力
"""

import time
import math
import random
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, TYPE_CHECKING
from src.entities.monsters import Monster
from src.core.constants import GameConstants
from src.core.enums import CreatureType
from src.utils.logger import game_logger
from src.managers.movement_system import MovementSystem

if TYPE_CHECKING:
    from src.entities.creature import Creature


class OrcWarriorStatus(Enum):
    """兽人战士状态枚举"""
    WANDERING = "wandering"          # 游荡中
    HUNTING = "hunting"             # 追击目标
    ATTACKING = "attacking"         # 攻击中
    RETURNING = "returning"         # 返回巢穴
    GUARDING = "guarding"           # 守卫巢穴
    PATROLLING = "patrolling"       # 巡逻中


class OrcWarrior(Monster):
    """兽人战士 - 野蛮的近战单位"""

    def __init__(self, x: float, y: float, creature_type: CreatureType = CreatureType.ORC_WARRIOR, summon_source: str = "normal"):
        # 调用Monster父类构造函数，包含技能分配逻辑
        super().__init__(x, y, creature_type.value)

        # 调试：检查技能分配结果
        game_logger.info(
            f"🔍 兽人战士 {self.name} 初始化完成，技能数量: {len(self.skills) if hasattr(self, 'skills') else '无skills属性'}")
        if hasattr(self, 'skills') and self.skills:
            game_logger.info(
                f"🔍 兽人战士 {self.name} 的技能: {[skill.name for skill in self.skills]}")
        else:
            game_logger.warning(f"⚠️ 兽人战士 {self.name} 没有技能！")

        # 召唤来源标识
        self.summon_source = summon_source  # "normal" 正常召唤, "training" 训练召唤

        # 状态管理
        self.state = OrcWarriorStatus.WANDERING  # 初始状态为游荡
        self.last_target_switch_time = 0.0  # 上次切换目标的时间

        # 战斗状态 - 与CombatSystem兼容
        self.last_attack = 0.0  # 上次攻击的绝对时间（CombatSystem期望的属性名）
        self.target = None
        self.is_attacking = False

        # 视觉效果
        self.attack_effect_color = (0, 150, 0)  # 深绿色攻击特效
        self.health_bar_color = (0, 200, 0)  # 深绿色血条

        # 敌我关系
        self.is_enemy = False  # 兽人战士是己方单位

        # 绑定信息
        self.bound_lair = None  # 绑定的兽人巢穴
        self.bound_lair_position = None  # 巢穴位置

    def update(self, delta_time: float, game_map: List, creatures: List, heroes: List = None, effect_manager=None, building_manager=None, game_instance=None) -> Dict[str, Any]:
        """更新兽人战士状态"""
        updates = {}

        if self.is_dead():
            return updates

        # 调用父类的update方法，包含技能更新逻辑
        parent_updates = super().update(delta_time, creatures, game_map, effect_manager)
        updates.update(parent_updates)

        # 管理空闲状态
        self._manage_idle_state(game_instance)

        # 更新行为逻辑
        self._update_orc_behavior(delta_time, game_map, heroes, game_instance)

        # 检查生命值
        if self.health <= 0:
            self._die()
            updates['died'] = True
            updates['position'] = (self.x, self.y)

        return updates

    def _manage_idle_state(self, game_instance=None):
        """管理空闲状态 - 与IdleStateManager兼容"""
        if not hasattr(self, '_idle_start_time'):
            self._idle_start_time = time.time()

        # 检查是否处于空闲状态（没有目标且不在攻击）
        is_idle = (not self.target and
                   self.state in [OrcWarriorStatus.WANDERING, OrcWarriorStatus.GUARDING])

        if not is_idle:
            # 重置空闲时间
            self._idle_start_time = time.time()

    def _update_orc_behavior(self, delta_time: float, game_map: List, heroes: List, game_instance=None):
        """更新兽人战士的行为逻辑"""
        # 根据召唤来源决定行为模式
        if self.summon_source == "training":
            # 训练召唤的兽人战士：巡逻/搜索逻辑
            self._update_training_orc_behavior(
                delta_time, game_map, heroes, game_instance)
        else:
            # 正常召唤的兽人战士：正常游荡/追敌逻辑
            self._update_normal_orc_behavior(
                delta_time, game_map, heroes, game_instance)

    def _update_training_orc_behavior(self, delta_time: float, game_map: List, heroes: List, game_instance=None):
        """训练召唤的兽人战士AI行为 - 巡逻/搜索逻辑"""
        if not heroes:
            heroes = []

        # 绑定的兽人战士：200像素搜索范围，200像素巡逻范围
        search_range = 200
        patrol_range = 200

        # 寻找最近的敌方英雄
        nearest_hero = self._find_nearest_hero(heroes, search_range)

        if nearest_hero:
            # 有目标时，更新目标并切换到追击状态
            if self.target != nearest_hero:
                self.target = nearest_hero
                self.state = OrcWarriorStatus.HUNTING
                game_logger.info(
                    f"⚔️ [训练兽人战士] 发现目标: {nearest_hero.name} at ({nearest_hero.x:.1f}, {nearest_hero.y:.1f})")
        else:
            # 没有目标时，清除当前目标
            if self.target:
                self.target = None
                game_logger.info("🔍 [训练兽人战士] 失去目标")

        # 根据当前状态执行相应行为
        if self.target and self.target.health > 0:
            # 有目标时的行为
            distance = self._calculate_distance_to_target()

            if distance <= self.attack_range:
                # 在攻击范围内，设置攻击状态
                self.state = OrcWarriorStatus.ATTACKING
                # 攻击逻辑由CombatSystem统一处理
            else:
                # 不在攻击范围内，追击目标
                self.state = OrcWarriorStatus.HUNTING
                target_pos = (self.target.x, self.target.y)
                MovementSystem.pathfind_and_move(
                    self, target_pos, delta_time, game_map, "A_STAR", 1.0)
        else:
            # 没有目标时的行为
            if self.bound_lair and self.bound_lair_position:
                # 有绑定巢穴时的行为
                distance_to_lair = self._calculate_distance_to_position(
                    self.bound_lair_position)

                if distance_to_lair > patrol_range:
                    # 超出巡逻范围，返回巢穴附近
                    self.state = OrcWarriorStatus.RETURNING
                    MovementSystem.pathfind_and_move(
                        self, self.bound_lair_position, delta_time, game_map, "A_STAR", 0.8)
                else:
                    # 在巡逻范围内，进行巡逻
                    self.state = OrcWarriorStatus.PATROLLING
                    self._patrol_around_lair(
                        delta_time, game_map, patrol_range)
            else:
                # 没有绑定巢穴时，自由游荡
                self.state = OrcWarriorStatus.WANDERING
                MovementSystem.wandering_movement(
                    self, delta_time, game_map, 0.5)

    def _update_normal_orc_behavior(self, delta_time: float, game_map: List, heroes: List, game_instance=None):
        """正常召唤的兽人战士AI行为 - 正常游荡/追敌逻辑"""
        if not heroes:
            heroes = []

        # 正常召唤的兽人战士：150像素搜索范围，不巡逻
        search_range = 150

        # 寻找最近的敌方英雄
        nearest_hero = self._find_nearest_hero(heroes, search_range)

        if nearest_hero:
            # 有目标时，更新目标并切换到追击状态
            if self.target != nearest_hero:
                self.target = nearest_hero
                self.state = OrcWarriorStatus.HUNTING
                game_logger.info(
                    f"⚔️ [正常兽人战士] 发现目标: {nearest_hero.name} at ({nearest_hero.x:.1f}, {nearest_hero.y:.1f})")
        else:
            # 没有目标时，清除当前目标
            if self.target:
                self.target = None
                game_logger.info("🔍 [正常兽人战士] 失去目标")

        # 根据当前状态执行相应行为
        if self.target and self.target.health > 0:
            # 有目标时的行为
            distance = self._calculate_distance_to_target()

            if distance <= self.attack_range:
                # 在攻击范围内，设置攻击状态
                self.state = OrcWarriorStatus.ATTACKING
                # 攻击逻辑由CombatSystem统一处理
            else:
                # 不在攻击范围内，追击目标
                self.state = OrcWarriorStatus.HUNTING
                target_pos = (self.target.x, self.target.y)
                MovementSystem.pathfind_and_move(
                    self, target_pos, delta_time, game_map, "A_STAR", 1.0)
        else:
            # 没有目标时，自由游荡
            self.state = OrcWarriorStatus.WANDERING
            MovementSystem.wandering_movement(
                self, delta_time, game_map, 0.5)

    def _find_nearest_hero(self, heroes: List, max_distance: float):
        """寻找最近的敌方英雄"""
        if not heroes:
            return None

        nearest_hero = None
        min_distance = max_distance

        for hero in heroes:
            if hero and hero.health > 0 and hasattr(hero, 'is_enemy') and hero.is_enemy:
                distance = self._calculate_distance_to_position(
                    (hero.x, hero.y))
                if distance < min_distance:
                    min_distance = distance
                    nearest_hero = hero

        return nearest_hero

    def _patrol_around_lair(self, delta_time: float, game_map: List, patrol_range: float):
        """在巢穴周围巡逻"""
        if not self.bound_lair_position:
            return

        # 检查是否已经有巡逻目标
        if not hasattr(self, '_patrol_target') or not self._patrol_target:
            # 生成新的巡逻目标（在巡逻范围内随机位置）
            self._patrol_target = self._generate_patrol_target(patrol_range)
            self._patrol_wait_time = 0.0

        if self._patrol_target:
            # 移动到巡逻目标
            distance_to_target = self._calculate_distance_to_position(
                self._patrol_target)

            if distance_to_target > 20:  # 距离目标超过20像素时移动
                MovementSystem.pathfind_and_move(
                    self, self._patrol_target, delta_time, game_map, "A_STAR", 0.4)
            else:
                # 到达目标，等待一段时间后选择新目标
                if not hasattr(self, '_patrol_wait_time'):
                    self._patrol_wait_time = 0.0

                self._patrol_wait_time += delta_time

                # 等待2-4秒后选择新目标
                if self._patrol_wait_time >= random.uniform(2.0, 4.0):
                    self._patrol_target = self._generate_patrol_target(
                        patrol_range)
                    self._patrol_wait_time = 0.0

    def _generate_patrol_target(self, patrol_range: float) -> Tuple[float, float]:
        """生成巡逻目标位置"""
        if not self.bound_lair_position:
            return None

        # 在巢穴周围的巡逻范围内生成随机位置
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(50, patrol_range)  # 距离巢穴50到巡逻范围之间

        target_x = self.bound_lair_position[0] + distance * math.cos(angle)
        target_y = self.bound_lair_position[1] + distance * math.sin(angle)

        return (target_x, target_y)

    def _calculate_distance_to_position(self, position: Tuple[float, float]) -> float:
        """计算到指定位置的距离"""
        dx = position[0] - self.x
        dy = position[1] - self.y
        return math.sqrt(dx * dx + dy * dy)

    def _calculate_distance_to_target(self) -> float:
        """计算到目标的距离"""
        if not self.target:
            return float('inf')

        dx = self.target.x - self.x
        dy = self.target.y - self.y
        return math.sqrt(dx * dx + dy * dy)

    def _can_attack(self, current_time: float) -> bool:
        """检查是否可以攻击（使用绝对时间机制）"""
        if self.last_attack <= 0:
            return True

        time_since_last_attack = current_time - self.last_attack
        return time_since_last_attack >= self.attack_cooldown

    def _move_towards_target(self, delta_time: float):
        """向目标移动"""
        if not self.target:
            return

        # 计算移动方向
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 移动
            move_distance = self.speed * delta_time
            self.x += dx * move_distance
            self.y += dy * move_distance

    def take_damage(self, damage: float) -> bool:
        """受到伤害"""
        # 应用魔法抗性
        if hasattr(self, 'magic_resistance'):
            damage = max(1.0, damage - self.magic_resistance)

        self.health -= damage
        self.health = max(0, self.health)

        return self.health <= 0

    def _die(self):
        """死亡处理"""
        self.health = 0
        self.is_dead_flag = True
        game_logger.info(f"💀 兽人战士死亡 at ({self.x:.1f}, {self.y:.1f})")

    def is_dead(self) -> bool:
        """检查是否死亡"""
        return getattr(self, 'is_dead_flag', False) or self.health <= 0

    def set_target(self, target):
        """设置攻击目标"""
        self.target = target

    def bind_to_lair(self, lair):
        """绑定到兽人巢穴"""
        self.bound_lair = lair
        if lair:
            self.bound_lair_position = (lair.x, lair.y)

    def get_attack_effect_info(self) -> Dict[str, Any]:
        """获取攻击特效信息"""
        return {
            'color': self.attack_effect_color,
            'size': 10,
            'duration': 0.3,
            'particle_count': 5
        }

    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            'health': self.health,
            'max_health': self.max_health,
            'health_ratio': self.health / self.max_health,
            'state': self.state.value if hasattr(self.state, 'value') else str(self.state),
            'is_attacking': self.is_attacking,
            'has_target': self.target is not None,
            'attack_cooldown': self.attack_cooldown,
            'bound_lair': self.bound_lair is not None
        }

    def get_attack_status(self) -> Dict[str, Any]:
        """获取攻击状态信息"""
        current_time = time.time()
        time_since_last_attack = current_time - \
            self.last_attack if self.last_attack > 0 else 0
        cooldown_remaining = max(
            0, self.attack_cooldown - time_since_last_attack)

        return {
            'cooldown_remaining': cooldown_remaining,
            'is_ready': cooldown_remaining <= 0,
            'attack_cooldown': self.attack_cooldown,
            'last_attack': self.last_attack
        }
