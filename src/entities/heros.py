#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
英雄实体模块
"""

import math
import random
from typing import List, Dict, Optional, Tuple

# 导入需要的类型和配置
from src.core.constants import GameConstants, GameBalance
from src.core.enums import TileType, BuildMode
from src.core.game_state import Tile, GameState
from src.entities.configs import HeroConfig
from src.utils.logger import game_logger
from src.managers.movement_system import MovementSystem
from src.entities.creature import Creature
from src.systems.skill_system import skill_manager


class Hero(Creature):
    def __init__(self, x: int, y: int, hero_type: str = 'knight'):
        # 调用父类构造函数
        super().__init__(x, y, hero_type)

        # 英雄特有属性 - 统一阵营系统
        self.faction = "heroes"  # 英雄阵营

        # 英雄特有的初始化逻辑
        self._initialize_hero_specific_properties(hero_type)

        # 英雄特有的移动和状态属性
        self.target = None
        self.state = 'exploring'
        self.last_attack = 0

        # 设置特殊物理属性
        self._setup_special_physics_properties()

        # 战斗状态和回血系统
        self.in_combat = False
        self.last_combat_time = 0
        self.regeneration_rate = 1  # 每秒回血1点
        self.regeneration_delay = 10  # 脱离战斗10秒后开始回血

        # 攻击列表管理（继承自Creature，但可以重写方法）
        # 注意：attack_list已在父类Creature中初始化

        # 英雄范围伤害配置（覆盖父类配置）
        self.area_damage = self._get_hero_area_damage_config(hero_type)

        # 技能系统
        self.skills = []  # 技能列表
        self.mana = 100  # 法力值
        self.max_mana = 100  # 最大法力值
        self.mana_regen_rate = 2  # 每秒恢复法力值
        self.last_mana_regen = 0  # 上次恢复法力值时间

        # 为英雄分配技能
        self._assign_hero_skills(hero_type)

    def _initialize_hero_specific_properties(self, hero_type: str):
        """初始化英雄特有的属性"""
        # 注意：基础属性（size, health, attack等）已经在父类Creature中初始化
        # 这里只需要处理英雄特有的逻辑

        # 如果父类没有正确初始化英雄数据，则使用HeroConfig作为后备
        if not hasattr(self, 'character_data') or self.character_data is None:
            try:
                if hero_type not in HeroConfig.TYPES:
                    game_logger.info(
                        f"⚠️ 警告: 英雄类型 '{hero_type}' 不存在于HeroConfig中，使用默认配置")
                    hero_type = 'knight'  # 回退到默认类型
                config = HeroConfig.TYPES[hero_type]
                self.character_data = None
                self.size = config['size']
                self.health = config['health']
                self.max_health = config['health']
                self.attack = config['attack']
                self.speed = config['speed']
                self.color = config['color']
                self.armor = 0
                self.attack_range = config.get('attack_range', 30)
                self.attack_cooldown = config.get('attack_cooldown', 1.0)
                self.special_ability = "无"
                game_logger.info(f"✅ 使用HeroConfig初始化英雄: {hero_type}")
            except Exception as e:
                game_logger.info(f"❌ Hero配置初始化错误: {e}")
                # 使用最基本的默认配置
                self.size = 15
                self.health = 100
                self.max_health = 100
                self.attack = 20
                self.speed = 30
                self.color = (70, 130, 180)
                self.armor = 0
                self.attack_range = 30
                self.attack_cooldown = 1.0
                self.special_ability = "无"

    def update(self, delta_time: float, creatures: List, game_map: List[List[Tile]], effect_manager=None):
        """
        更新英雄状态 - 英雄特有的AI逻辑

        Args:
            delta_time: 时间增量（秒）
        """
        import time
        current_time = time.time()

        # 更新搜索冷却时间
        if self.target_search_cooldown > 0:
            self.target_search_cooldown -= delta_time

        # 更新技能系统
        self.update_skills(delta_time, game_instance=getattr(
            self, 'game_instance', None))

        # 恢复法力值
        self._regenerate_mana(delta_time)

        # 注意：攻击和移动逻辑现在由CombatSystem统一处理
        # 这里只处理非战斗的AI逻辑

        # 如果不在战斗中，进行探索
        if not self.in_combat:
            # 优先级1: 探索地牢之心
            if hasattr(self, 'known_dungeon_heart') and self.known_dungeon_heart:
                self.state = 'exploring'
                # 不直接移动，让CombatSystem处理
                return

            # 优先级2: 随机探索
            self.state = 'patrolling'
            # 不直接移动，让CombatSystem处理

    def _execute_attack(self, target: 'Creature', delta_time: float, effect_manager=None) -> bool:
        """执行攻击"""
        # 注意：攻击冷却时间检查应该在调用此方法之前进行
        # 这里直接执行攻击逻辑
        self._attack_target(target, delta_time, effect_manager)
        return True

    def _find_nearest_creature(self, creatures: List['Creature'], max_distance: float) -> Optional['Creature']:
        """寻找最近的生物"""
        nearest_creature = None
        nearest_distance = float('inf')

        for creature in creatures:
            distance = math.sqrt((creature.x - self.x) **
                                 2 + (creature.y - self.y) ** 2)
            if distance < max_distance and distance < nearest_distance:
                nearest_distance = distance
                nearest_creature = creature

        return nearest_creature

    def _find_highest_threat_creature(self, creatures: List['Creature'], max_distance: float) -> Optional['Creature']:
        """寻找威胁最大的敌方生物 - 按照COMBAT_SYSTEM.md威胁评估"""
        highest_threat_creature = None
        highest_threat_score = -1

        for creature in creatures:
            # 跳过非战斗单位
            if hasattr(creature, 'is_combat_unit') and not creature.is_combat_unit:
                continue

            # 跳过非敌方单位（英雄不应该攻击其他英雄）
            if not hasattr(creature, 'is_enemy') or not creature.is_enemy:
                continue

            distance = math.sqrt(
                (creature.x - self.x) ** 2 + (creature.y - self.y) ** 2)

            if distance <= max_distance:
                # 计算威胁分数：攻击力越高威胁越大，距离越近威胁越大
                threat_score = creature.attack / (distance + 1)  # +1避免除零

                if threat_score > highest_threat_score:
                    highest_threat_score = threat_score
                    highest_threat_creature = creature

        return highest_threat_creature

    def _attack_target(self, target: 'Creature', delta_time: float, effect_manager=None, camera_x: float = 0, camera_y: float = 0) -> bool:
        """攻击目标 - 已废弃，攻击逻辑已移至游戏主循环"""
        # 此方法已废弃，攻击逻辑现在由游戏主循环的_execute_attack_with_rules方法处理
        # 保留此方法仅为兼容性考虑
        return False

    def _create_attack_effect(self, target: 'Creature', damage: int, effect_manager, camera_x: float = 0, camera_y: float = 0) -> bool:
        """创建攻击特效 - 使用8大类特效系统"""
        game_logger.info(
            f"🔥 英雄 {self.type} 尝试创建攻击特效，目标: {target.type}, 伤害: {damage}")

        # 根据英雄类型选择特效
        effect_type = self._get_attack_effect_type()
        game_logger.info(f"   特效类型: {effect_type}")

        if effect_type:
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

                game_logger.info(
                    f"   世界坐标: 英雄({self.x:.1f}, {self.y:.1f})px, 目标({target.x:.1f}, {target.y:.1f})px")
                game_logger.info(
                    f"   屏幕坐标: 英雄({screen_x:.1f}, {screen_y:.1f})px, 目标({target_screen_x:.1f}, {target_screen_y:.1f})px")

                success = effect_manager.create_visual_effect(
                    effect_type=effect_type,
                    x=screen_x,
                    y=screen_y,
                    target_x=target_screen_x,
                    target_y=target_screen_y,
                    damage=damage
                )
                game_logger.info(f"   特效创建结果: {success}")
                return success
        else:
            game_logger.info(f"   未找到英雄类型 {self.type} 对应的特效类型")

        return False

    def _get_hero_area_damage_config(self, hero_type: str) -> Optional[Dict]:
        """
        获取英雄的范围伤害配置

        英雄范围伤害配置说明：
        - radius: 范围半径（像素）
        - damage_ratio: 伤害比例（正数=伤害，负数=治疗）
        - type: 范围类型（'enemy'=只攻击敌人，'ally'=只治疗友军，'all'=攻击所有）
        - effect_type: 特效类型（用于视觉表现）

        Args:
            hero_type: 英雄类型

        Returns:
            Optional[Dict]: 范围伤害配置，None表示无范围伤害
        """
        hero_area_damage_configs = {
            # 大法师 - 奥术范围伤害
            'archmage': {
                'radius': 120,  # 范围半径120像素
                'damage_ratio': 0.7,  # 范围伤害为基础伤害的70%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'chain_lightning'  # 使用闪电特效
            },

            # 德鲁伊 - 自然范围治疗
            'druid': {
                'radius': 80,  # 范围半径80像素
                'damage_ratio': -0.5,  # 负值表示治疗（50%基础攻击力的治疗）
                'type': 'ally',  # 只治疗友军
                'effect_type': 'healing_aura'  # 使用治疗特效
            },

            # 圣骑士 - 神圣范围伤害
            'paladin': {
                'radius': 90,  # 范围半径90像素
                'damage_ratio': 0.5,  # 范围伤害为基础伤害的50%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'divine_strike'  # 使用神圣特效
            }
        }

        return hero_area_damage_configs.get(hero_type, None)

    def _get_attack_effect_type(self) -> str:
        """
        根据英雄类型获取攻击特效类型 - 映射到8大类特效系统

        特效分类：
        - 斩击类 (slash): 半月形圆弧 - 近战英雄
        - 射击类 (projectile): 适当长度的短线条 - 远程英雄
        - 魔法类 (magic): 直接作用于目标，圆形爆炸 - 法师英雄

        Returns:
            str: 特效类型名称
        """
        effect_mapping = {
            # 斩击类 (slash) - 半月形圆弧
            'knight': 'melee_slash',           # 斩击类
            'paladin': 'divine_strike',        # 斩击类
            'assassin': 'shadow_slash',        # 斩击类
            'shadow_blade': 'shadow_slash',    # 斩击类
            'berserker': 'melee_heavy',        # 斩击类
            'thief': 'shadow_slash',           # 斩击类
            'dragon_knight': 'melee_heavy',    # 斩击类

            # 射击类 (projectile) - 适当长度的短线条
            'archer': 'arrow_shot',            # 射击类
            'ranger': 'tracking_arrow',        # 射击类
            'druid': 'nature_arrow',           # 射击类
            'engineer': 'arrow_shot',          # 射击类

            # 魔法类 (magic) - 直接作用于目标，圆形爆炸
            'wizard': 'fireball',              # 魔法类
            'archmage': 'chain_lightning',     # 魔法类
            'priest': 'healing_aura'           # 魔法类
        }
        return effect_mapping.get(self.type, 'melee_slash')

    def _is_melee_attack(self) -> bool:
        """判断是否为近战攻击"""
        melee_types = {
            'knight': True,
            'archer': False,
            'wizard': False,
            'paladin': True,
            'assassin': True,
            'ranger': False,
            'archmage': False,
            'druid': False,
            'dragon_knight': True,
            'shadow_blade': True,
            'berserker': True,
            'priest': False,
            'thief': True,
            'engineer': False
        }
        return melee_types.get(self.type, True)  # 默认为近战

    def _take_damage(self, damage: int, attacker: Optional['Creature'] = None) -> None:
        """英雄受到伤害"""
        self.health -= damage
        if self.health < 0:
            self.health = 0

        # 设置战斗状态
        import time
        current_time = time.time()
        self.in_combat = True
        self.last_combat_time = current_time

        # 触发被攻击响应（如果有攻击者）
        if attacker and hasattr(self, 'game_instance') and self.game_instance:
            self.game_instance.handle_unit_attacked_response(
                attacker, self, damage)

        # 英雄特有：如果被敌方攻击，将攻击者添加到攻击列表
        if attacker and hasattr(attacker, 'is_enemy') and attacker.is_enemy:
            # 这里可以调用战斗系统的方法来添加攻击目标
            # 暂时通过设置current_target来实现
            self.current_target = attacker
            self.target_last_seen_time = current_time

    def _regenerate_health(self, current_time: float) -> None:
        """回血处理"""
        if not hasattr(self, 'last_regeneration_time'):
            self.last_regeneration_time = 0

        # 每秒回血一次
        if current_time - self.last_regeneration_time >= 1.0:
            old_health = self.health
            self.health += self.regeneration_rate

            # 确保不超过最大生命值
            if self.health > self.max_health:
                self.health = self.max_health

            # 如果有实际回血，打印信息
            if self.health > old_health:
                game_logger.info(
                    f"💚 {self.type} 回血 {self.health - old_health} 点，当前生命值: {self.health}/{self.max_health}")

            self.last_regeneration_time = current_time

    def _setup_special_physics_properties(self) -> None:
        """设置特殊物理属性"""
        # 根据英雄类型设置特殊物理属性
        if self.type == 'paladin':
            # 圣骑士有神圣护盾，减少击退效果
            self.has_shield = True
        elif self.type == 'dragon_knight':
            # 龙骑士体型大，击退抗性强
            pass  # 抗性在计算中处理
        elif self.type == 'archmage':
            # 大法师有魔法护盾
            self.has_shield = True
        elif self.type == 'assassin':
            # 刺客敏捷，不容易被击退
            pass  # 可以添加特殊处理

        # 其他英雄使用默认设置

    def _safe_move(self, new_x: float, new_y: float, game_map: List[List[Tile]]) -> bool:
        """安全移动 - 只有在目标位置可通行时才移动"""
        if self._can_move_to_position(new_x, new_y, game_map):
            self.x = new_x
            self.y = new_y
            return True
        return False

    def _can_move_to_position(self, new_x: float, new_y: float, game_map: List[List[Tile]]) -> bool:
        """检查英雄是否可以移动到指定位置 - 英雄只能在已挖掘地块移动"""
        # 转换为瓦片坐标
        tile_x = int(new_x // GameConstants.TILE_SIZE)
        tile_y = int(new_y // GameConstants.TILE_SIZE)

        # 边界检查
        if not (0 <= tile_x < GameConstants.MAP_WIDTH and 0 <= tile_y < GameConstants.MAP_HEIGHT):
            return False

        tile = game_map[tile_y][tile_x]
        # 英雄只能在已挖掘的地块移动
        return tile.type == TileType.GROUND or tile.is_dug

    def _assign_hero_skills(self, hero_type: str):
        """为英雄分配技能"""
        skill_assignments = {
            'knight': ['whirlwind_slash'],
            'archer': ['multi_shot'],
            'paladin': ['whirlwind_slash'],
            'assassin': [],
            'ranger': ['multi_shot'],
            'wizard': [],
            'archmage': [],
            'druid': [],
            'dragon_knight': ['whirlwind_slash'],
            'shadow_blade': [],
            'berserker': ['whirlwind_slash'],
            'priest': [],
            'thief': [],
            'engineer': ['multi_shot']
        }

        skills_to_assign = skill_assignments.get(hero_type, [])
        for skill_id in skills_to_assign:
            skill_manager.assign_skill_to_unit(self, skill_id)

        # 更新本地技能列表
        self.skills = skill_manager.get_unit_skills(self)
        game_logger.info(f"🎯 为 {self.name} 分配了 {len(self.skills)} 个技能")

    def use_skill(self, skill_id: str, target=None, **kwargs) -> bool:
        """使用技能"""
        return skill_manager.use_skill(self, skill_id, target, **kwargs)

    def get_available_skills(self) -> List:
        """获取可用的技能列表"""
        return skill_manager.get_available_skills(self)

    def update_skills(self, delta_time: float, game_instance=None):
        """更新技能状态"""
        skill_manager.update_skills(self, delta_time)

        # 更新多重射击等需要持续更新的技能
        for skill in self.skills:
            if hasattr(skill, 'update_skill') and skill.is_charging:
                skill.update_skill(self, self.current_target, game_instance)

    def _regenerate_mana(self, delta_time: float):
        """恢复法力值"""
        import time
        current_time = time.time()
        if current_time - self.last_mana_regen >= 1.0:  # 每秒恢复一次
            if self.mana < self.max_mana:
                old_mana = self.mana
                self.mana = min(self.max_mana, self.mana +
                                self.mana_regen_rate)
                if self.mana > old_mana:
                    game_logger.info(
                        f"💙 {self.name} 恢复了 {self.mana - old_mana} 点法力值 ({self.mana}/{self.max_mana})")
            self.last_mana_regen = current_time
