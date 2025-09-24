#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生物实体模块
"""

import math
import random
import time
from typing import List, Dict, Optional, Tuple

# 导入需要的类型和配置
from src.core.constants import GameConstants, GameBalance
from src.core.enums import TileType, BuildMode
from src.core.game_state import Tile, GameState
from src.entities.configs import CreatureConfig
from src.managers.movement_system import MovementSystem


class Creature:
    def __init__(self, x: int, y: int, creature_type: str = 'imp'):
        self.x = x
        self.y = y
        self.type = creature_type
        self.name = creature_type  # 添加name属性，默认为creature_type

        # 战斗属性
        self.is_combat_unit = True  # 是否为战斗单位（默认是）

        # 攻击目标追踪（用于近战攻击限制）
        self.melee_target = None  # 当前近战攻击的目标

        # 目标追踪系统（优化战斗搜索）
        self.current_target = None  # 当前追踪的目标
        self.target_last_seen_time = 0  # 目标最后被看到的时间
        self.target_search_cooldown = 0  # 目标搜索冷却时间

        # 物理系统属性
        self.collision_radius = None  # 碰撞半径（由物理系统计算）
        self.knockback_state = None   # 击退状态
        self.can_move = True         # 是否可以移动
        self.can_attack = True       # 是否可以攻击

        # 特殊物理状态
        self.immunities = set()      # 免疫列表
        self.is_rooted = False       # 是否扎根（树人守护者等）
        self.has_shield = False      # 是否有护盾

        # 导入角色图鉴系统
        try:
            from src.ui.character_bestiary import CharacterBestiary
            from src.entities.character_data import character_db
            BESTIARY_AVAILABLE = True
        except ImportError:
            BESTIARY_AVAILABLE = False

        try:
            # 使用character_data.py中的角色数据
            if BESTIARY_AVAILABLE:
                character_data = character_db.get_character(creature_type)
                if character_data:
                    self.character_data = character_data
                    self.size = character_data.size
                    self.health = character_data.hp
                    self.max_health = character_data.hp
                    self.attack = character_data.attack
                    self.speed = character_data.speed
                    self.color = character_data.color
                    self.armor = character_data.armor
                    self.attack_range = character_data.attack_range
                    self.attack_cooldown = character_data.attack_cooldown
                    self.special_ability = character_data.special_ability
                    self.cost = character_data.cost if character_data.cost else 100
                    self.abilities = [character_data.special_ability]
                    self.upkeep = 0  # 暂时设置为0
                else:
                    # 如果角色数据不存在，使用默认配置
                    if creature_type not in CreatureConfig.TYPES:
                        print(
                            f"⚠️ 警告: 怪物类型 '{creature_type}' 不存在于CreatureConfig中，使用默认配置")
                        creature_type = 'imp'  # 回退到默认类型
                    config = CreatureConfig.TYPES[creature_type]
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
                    self.cost = 100
                    self.abilities = config['abilities']
                    self.upkeep = config['upkeep']
            else:
                # 如果图鉴系统不可用，使用默认配置
                if creature_type not in CreatureConfig.TYPES:
                    print(
                        f"⚠️ 警告: 怪物类型 '{creature_type}' 不存在于CreatureConfig中，使用默认配置")
                    creature_type = 'imp'  # 回退到默认类型
                config = CreatureConfig.TYPES[creature_type]
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
                self.cost = 100
                self.abilities = config['abilities']
                self.upkeep = config['upkeep']
        except Exception as e:
            print(f"❌ Creature初始化错误: {e}")
            print(f"   怪物类型: {creature_type}")
            print(f"   图鉴系统可用: {BESTIARY_AVAILABLE}")
            # 使用最基本的默认配置
            self.character_data = None
            self.size = 15
            self.health = 80
            self.max_health = 80
            self.attack = 15
            self.speed = 25
            self.color = (255, 107, 107)
            self.armor = 0
            self.attack_range = 30
            self.attack_cooldown = 1.0
            self.special_ability = "无"
            self.cost = 100
            self.abilities = ['dig', 'fight']
            self.upkeep = 1

        self.target = None
        self.state = 'idle'
        self.last_attack = 0
        self.mining_target = None
        self.path = []

        # 战斗状态和回血系统
        self.in_combat = False
        self.last_combat_time = 0
        self.regeneration_rate = 1  # 每秒回血1点
        self.regeneration_delay = 10  # 脱离战斗10秒后开始回血

        # 设置特殊物理属性
        self._setup_special_physics_properties()

        # 特定生物类型的特殊属性会在子类中初始化

    def update(self, delta_time: float, game_map: List[List[Tile]], creatures: List['Creature'], heroes: List = None, effect_manager=None, building_manager=None):
        """更新生物状态 - 基类方法，由子类重写具体行为"""
        # 基础生物行为更新
        self._update_basic_behavior(delta_time, game_map, effect_manager)

    def _find_nearest_hero(self, heroes: List, max_distance: float):
        """寻找最近的英雄 - 通用方法"""
        nearest_hero = None
        nearest_distance = float('inf')

        for hero in heroes:
            distance = math.sqrt((hero.x - self.x) **
                                 2 + (hero.y - self.y) ** 2)
            if distance < max_distance and distance < nearest_distance:
                nearest_distance = distance
                nearest_hero = hero

        return nearest_hero

    def _update_basic_behavior(self, delta_time: float, game_map: List[List[Tile]], effect_manager=None):
        """基础生物行为更新 - 只有战斗单位才主动寻找敌人"""
        # 只有战斗单位才使用战斗行为
        if self.is_combat_unit:
            self._update_combat_behavior(delta_time, game_map, effect_manager)

    def _update_combat_behavior(self, delta_time: float, game_map: List[List[Tile]], effect_manager=None):
        """通用怪物战斗行为 - 优化版本，使用目标追踪系统"""
        import time
        current_time = time.time()

        # 更新搜索冷却时间
        if self.target_search_cooldown > 0:
            self.target_search_cooldown -= delta_time

        # 如果游戏实例存在，寻找英雄
        if hasattr(self, 'game_instance') and self.game_instance:
            heroes = self.game_instance.heroes

            # 优先级1: 使用目标追踪系统寻找英雄
            target_hero = self._get_optimal_target(heroes, current_time)
            if target_hero:
                # 使用平方距离避免开方运算
                dx = self.x - target_hero.x
                dy = self.y - target_hero.y
                distance_squared = dx * dx + dy * dy
                distance = math.sqrt(distance_squared)

                if distance <= self.attack_range:
                    # 在攻击范围内，执行攻击
                    self.state = 'fighting'
                    self._execute_attack(
                        target_hero, delta_time, effect_manager)
                    # 更新目标追踪
                    self.current_target = target_hero
                    self.target_last_seen_time = current_time
                    return
                else:
                    # 移动到攻击范围内
                    self.state = 'moving'
                    MovementSystem.smart_target_seeking_movement_with_simulation(
                        self, (target_hero.x, target_hero.y), delta_time, game_map, speed_multiplier=1.2)
                    # 更新目标追踪
                    self.current_target = target_hero
                    self.target_last_seen_time = current_time
                    return

            # 优先级2: 血量过低时撤退
            if self.health <= self.max_health * 0.3:
                self.state = 'fleeing'
                # 寻找最近的英雄并逃离
                if target_hero:
                    MovementSystem.flee_movement(
                        self, (target_hero.x, target_hero.y), delta_time, game_map)
                return

        # 优先级3: 无敌人时游荡巡逻
        self.state = 'wandering'
        # 根据怪物类型调整游荡速度
        wander_speed = self._get_wander_speed_multiplier()
        MovementSystem.wandering_movement(
            self, delta_time, game_map, wander_speed)

    def _get_optimal_target(self, heroes: List, current_time: float):
        """获取最优目标 - 使用目标追踪系统优化搜索"""
        # 检查当前目标是否仍然有效
        if (self.current_target and
            self.current_target in heroes and
            self.current_target.health > 0 and
                current_time - self.target_last_seen_time < 3.0):  # 3秒内看到的目标仍然有效

            # 计算到当前目标的距离
            dx = self.x - self.current_target.x
            dy = self.y - self.current_target.y
            distance_squared = dx * dx + dy * dy

            # 如果在搜索范围内，继续追踪当前目标
            search_range = self._get_search_range()
            if distance_squared <= (search_range * search_range):
                return self.current_target

        # 如果搜索冷却时间未结束，不进行新搜索
        if self.target_search_cooldown > 0:
            return None

        # 寻找新目标
        search_range = self._get_search_range()
        nearest_hero = self._find_nearest_hero(heroes, search_range)
        if nearest_hero:
            # 设置搜索冷却时间（避免频繁搜索）
            self.target_search_cooldown = 0.5  # 0.5秒冷却
            self.current_target = nearest_hero
            self.target_last_seen_time = current_time

        return nearest_hero

    def _get_search_range(self) -> float:
        """根据怪物类型获取搜索敌人的范围"""
        search_ranges = {
            'imp': 120,           # 小恶魔 - 中等搜索范围
            'gargoyle': 150,      # 石像鬼 - 较大搜索范围
            'fire_salamander': 140,  # 火蜥蜴 - 中等搜索范围
            'shadow_mage': 160,   # 暗影法师 - 大搜索范围
            'tree_guardian': 100,  # 树人守护者 - 较小搜索范围（防守型）
            'shadow_lord': 180,   # 暗影领主 - 最大搜索范围
            'bone_dragon': 200,   # 骨龙 - 超大搜索范围
            'hellhound': 130,     # 地狱犬 - 中等搜索范围
            'stone_golem': 90,    # 石魔像 - 较小搜索范围（防守型）
            'succubus': 170,      # 魅魔 - 大搜索范围
            'goblin_engineer': 80,  # 地精工程师 - 小搜索范围（非战斗型）
        }
        return search_ranges.get(self.type, 120)  # 默认120像素

    def _get_wander_speed_multiplier(self) -> float:
        """根据怪物类型获取游荡速度倍数"""
        wander_speeds = {
            'imp': 0.6,           # 小恶魔 - 标准游荡速度
            'gargoyle': 0.4,      # 石像鬼 - 较慢（重型单位）
            'fire_salamander': 0.7,  # 火蜥蜴 - 较快
            'shadow_mage': 0.5,   # 暗影法师 - 较慢（施法者）
            'tree_guardian': 0.3,  # 树人守护者 - 很慢（防守型）
            'shadow_lord': 0.8,   # 暗影领主 - 快速
            'bone_dragon': 0.9,   # 骨龙 - 很快（飞行单位）
            'hellhound': 0.8,     # 地狱犬 - 快速
            'stone_golem': 0.2,   # 石魔像 - 很慢（重型防守）
            'succubus': 0.7,      # 魅魔 - 较快
            'goblin_engineer': 0.5,  # 地精工程师 - 较慢（非战斗型）
        }
        return wander_speeds.get(self.type, 0.6)  # 默认0.6倍速

    def _attack_target(self, target, delta_time: float, effect_manager=None, camera_x=0, camera_y=0):
        """攻击目标 - 已废弃，攻击逻辑已移至游戏主循环"""
        # 此方法已废弃，攻击逻辑现在由游戏主循环的_execute_attack_with_rules方法处理
        # 保留此方法仅为兼容性考虑
        pass

    def _create_attack_effect(self, target, damage: int, effect_manager, camera_x=0, camera_y=0):
        """创建攻击特效"""
        print(f"🔥 怪物 {self.type} 尝试创建攻击特效，目标: {target.type}, 伤害: {damage}")

        # 根据怪物类型选择特效
        effect_type = self._get_attack_effect_type()
        print(f"   特效类型: {effect_type}")

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

                print(
                    f"   世界坐标: 怪物({self.x:.1f}, {self.y:.1f})px, 目标({target.x:.1f}, {target.y:.1f})px")
                print(
                    f"   屏幕坐标: 怪物({screen_x:.1f}, {screen_y:.1f})px, 目标({target_screen_x:.1f}, {target_screen_y:.1f})px")

                success = effect_manager.create_effect(
                    effect_type=effect_type,
                    x=screen_x,
                    y=screen_y,
                    target_x=target_screen_x,
                    target_y=target_screen_y,
                    damage=damage
                )
                print(f"   特效创建结果: {success}")
        else:
            print(f"   未找到怪物类型 {self.type} 对应的特效类型")

    def _get_attack_effect_type(self) -> str:
        """根据怪物类型获取攻击特效类型"""
        effect_mapping = {
            'imp': 'melee_slash',
            'goblin_worker': 'melee_slash',  # 虽然苦工很少攻击
            'gargoyle': 'melee_heavy',
            'fire_salamander': 'fire_splash',
            'shadow_mage': 'shadow_penetration',
            'tree_guardian': 'vine_entangle',
            'shadow_lord': 'shadow_slash',
            'bone_dragon': 'spine_storm',
            'hellhound': 'fire_breath',
            'stone_golem': 'melee_heavy',
            'succubus': 'charm_effect',
            'goblin_engineer': 'arrow_shot'
        }
        return effect_mapping.get(self.type, 'melee_slash')

    def _is_melee_attack(self) -> bool:
        """判断是否为近战攻击"""
        melee_types = {
            'imp': True,
            'goblin_worker': True,
            'gargoyle': True,
            'fire_salamander': False,
            'shadow_mage': False,
            'tree_guardian': True,
            'shadow_lord': True,
            'bone_dragon': False,
            'hellhound': False,
            'stone_golem': True,
            'succubus': False,
            'goblin_engineer': False
        }
        return melee_types.get(self.type, True)  # 默认为近战

    def _take_damage(self, damage: int):
        """受到伤害"""
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def _regenerate_health(self, current_time: float):
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
                print(
                    f"💚 {self.type} 回血 {self.health - old_health} 点，当前生命值: {self.health}/{self.max_health}")

            self.last_regeneration_time = current_time

    def _safe_move(self, new_x: float, new_y: float, game_map: List[List[Tile]]):
        """安全移动 - 只有在目标位置可通行时才移动"""
        if self._can_move_to_position(new_x, new_y, game_map):
            self.x = new_x
            self.y = new_y
            return True
        return False

    def _can_move_to_position(self, new_x: float, new_y: float, game_map: List[List[Tile]]) -> bool:
        """检查是否可以移动到指定位置 - 检查环境碰撞，不检查单位碰撞"""
        # 转换为瓦片坐标
        tile_x = int(new_x // GameConstants.TILE_SIZE)
        tile_y = int(new_y // GameConstants.TILE_SIZE)

        # 边界检查
        if not (0 <= tile_x < GameConstants.MAP_WIDTH and 0 <= tile_y < GameConstants.MAP_HEIGHT):
            return False

        tile = game_map[tile_y][tile_x]
        # 只能在已挖掘的地块移动（地面或房间）
        # 注意：这里只检查环境碰撞，不检查单位碰撞
        # 单位碰撞由物理系统处理，不应该影响路径规划
        return tile.type == TileType.GROUND or tile.is_dug

    def _execute_attack(self, target, delta_time: float, effect_manager=None):
        """执行攻击"""
        # 注意：攻击冷却时间检查应该在调用此方法之前进行
        # 这里直接执行攻击逻辑
        self._attack_target(target, delta_time, effect_manager)

    def _setup_special_physics_properties(self):
        """设置特殊物理属性"""
        # 根据怪物类型设置特殊物理属性
        if self.type == 'stone_golem':
            # 石魔像有岩石护盾，减少击退效果
            self.has_shield = True
        elif self.type == 'bone_dragon':
            # 骨龙飞行单位，有击退抗性
            pass  # 抗性在计算中处理
        elif self.type == 'tree_guardian':
            # 树人守护者可以扎根，免疫击退
            self.is_rooted = False  # 默认不扎根，可以通过技能激活
        elif self.type == 'shadow_lord':
            # 暗影领主有特殊免疫
            pass  # 可以添加特殊免疫

        # 其他怪物使用默认设置
