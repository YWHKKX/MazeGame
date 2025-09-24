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
from src.managers.movement_system import MovementSystem


class Hero:
    def __init__(self, x: int, y: int, hero_type: str = 'knight'):
        self.x = x
        self.y = y
        self.type = hero_type

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
        self.is_rooted = False       # 是否扎根
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
                character_data = character_db.get_character(hero_type)
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
                else:
                    # 如果角色数据不存在，使用默认配置
                    if hero_type not in HeroConfig.TYPES:
                        print(
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
            else:
                # 如果图鉴系统不可用，使用默认配置
                if hero_type not in HeroConfig.TYPES:
                    print(f"⚠️ 警告: 英雄类型 '{hero_type}' 不存在于HeroConfig中，使用默认配置")
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
        except Exception as e:
            print(f"❌ Hero初始化错误: {e}")
            print(f"   英雄类型: {hero_type}")
            print(f"   图鉴系统可用: {BESTIARY_AVAILABLE}")
            # 使用最基本的默认配置
            self.character_data = None
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

    def update(self, delta_time: float, creatures: List, game_map: List[List[Tile]], effect_manager=None):
        """更新英雄状态 - 优化版本，使用目标追踪系统"""
        import time
        current_time = time.time()

        # 更新搜索冷却时间
        if self.target_search_cooldown > 0:
            self.target_search_cooldown -= delta_time

        # 优先级1: 战斗 - 使用目标追踪系统
        target_creature = self._get_optimal_target(creatures, current_time)
        if target_creature:
            # 使用平方距离避免开方运算
            dx = self.x - target_creature.x
            dy = self.y - target_creature.y
            distance_squared = dx * dx + dy * dy
            distance = math.sqrt(distance_squared)

            if distance <= self.attack_range:
                # 在攻击范围内，执行攻击
                self.state = 'fighting'
                self._execute_attack(
                    target_creature, delta_time, effect_manager)
                # 更新目标追踪
                self.current_target = target_creature
                self.target_last_seen_time = current_time
                return
            else:
                # 移动到攻击范围内
                self.state = 'moving'
                self.target = (target_creature.x, target_creature.y)
                MovementSystem.smart_target_seeking_movement_with_simulation(
                    self, self.target, delta_time, game_map, speed_multiplier=1.2)
                # 更新目标追踪
                self.current_target = target_creature
                self.target_last_seen_time = current_time
                return

        # 优先级2: 探索地牢之心
        if hasattr(self, 'known_dungeon_heart') and self.known_dungeon_heart:
            self.state = 'exploring'
            MovementSystem.smart_target_seeking_movement_with_simulation(
                self, self.known_dungeon_heart, delta_time, game_map)
            return

        # 优先级3: 随机探索
        self.state = 'patrolling'
        MovementSystem.wandering_movement(self, delta_time, game_map, 0.6)

    def _get_optimal_target(self, creatures: List, current_time: float):
        """获取最优目标 - 使用目标追踪系统优化搜索"""
        # 检查当前目标是否仍然有效
        if (self.current_target and
            self.current_target in creatures and
            self.current_target.health > 0 and
                current_time - self.target_last_seen_time < 3.0):  # 3秒内看到的目标仍然有效

            # 计算到当前目标的距离
            dx = self.x - self.current_target.x
            dy = self.y - self.current_target.y
            distance_squared = dx * dx + dy * dy

            # 如果在搜索范围内，继续追踪当前目标
            if distance_squared <= (120 * 120):  # 120像素搜索范围
                return self.current_target

        # 如果搜索冷却时间未结束，不进行新搜索
        if self.target_search_cooldown > 0:
            return None

        # 寻找新目标
        target_creature = self._find_highest_threat_creature(creatures, 120)
        if target_creature:
            # 设置搜索冷却时间（避免频繁搜索）
            self.target_search_cooldown = 0.5  # 0.5秒冷却
            self.current_target = target_creature
            self.target_last_seen_time = current_time

        return target_creature

    def _execute_attack(self, target, delta_time: float, effect_manager=None):
        """执行攻击"""
        # 注意：攻击冷却时间检查应该在调用此方法之前进行
        # 这里直接执行攻击逻辑
        self._attack_target(target, delta_time, effect_manager)

    def _find_nearest_creature(self, creatures: List, max_distance: float):
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

    def _find_highest_threat_creature(self, creatures: List, max_distance: float):
        """寻找威胁最大的生物 - 按照COMBAT_SYSTEM.md威胁评估"""
        highest_threat_creature = None
        highest_threat_score = -1

        for creature in creatures:
            # 跳过非战斗单位
            if hasattr(creature, 'is_combat_unit') and not creature.is_combat_unit:
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

    def _attack_target(self, target, delta_time: float, effect_manager=None, camera_x=0, camera_y=0):
        """攻击目标 - 已废弃，攻击逻辑已移至游戏主循环"""
        # 此方法已废弃，攻击逻辑现在由游戏主循环的_execute_attack_with_rules方法处理
        # 保留此方法仅为兼容性考虑
        pass

    def _create_attack_effect(self, target, damage: int, effect_manager, camera_x=0, camera_y=0):
        """创建攻击特效"""
        print(f"🔥 英雄 {self.type} 尝试创建攻击特效，目标: {target.type}, 伤害: {damage}")

        # 根据英雄类型选择特效
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
                    f"   世界坐标: 英雄({self.x:.1f}, {self.y:.1f})px, 目标({target.x:.1f}, {target.y:.1f})px")
                print(
                    f"   屏幕坐标: 英雄({screen_x:.1f}, {screen_y:.1f})px, 目标({target_screen_x:.1f}, {target_screen_y:.1f})px")

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
            print(f"   未找到英雄类型 {self.type} 对应的特效类型")

    def _get_attack_effect_type(self) -> str:
        """根据英雄类型获取攻击特效类型"""
        effect_mapping = {
            'knight': 'melee_slash',
            'archer': 'arrow_shot',
            'wizard': 'fireball',
            'paladin': 'divine_strike',
            'assassin': 'shadow_slash',
            'ranger': 'tracking_arrow',
            'archmage': 'chain_lightning',
            'druid': 'nature_arrow',
            'dragon_knight': 'fire_breath',
            'shadow_blade': 'shadow_slash',
            'berserker': 'melee_heavy',
            'priest': 'healing_aura',
            'thief': 'shadow_slash',
            'engineer': 'arrow_shot'
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

    def _setup_special_physics_properties(self):
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

    def _safe_move(self, new_x: float, new_y: float, game_map: List[List[Tile]]):
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

    def _find_simple_patrol_target(self, game_map: List[List[Tile]]) -> Optional[Tuple[float, float]]:
        """寻找简单的巡逻目标 - 英雄版本"""
        current_tile_x = int(self.x // GameConstants.TILE_SIZE)
        current_tile_y = int(self.y // GameConstants.TILE_SIZE)

        # 英雄搜索范围更大一些
        for distance in range(1, 5):
            for dy in range(-distance, distance + 1):
                for dx in range(-distance, distance + 1):
                    if abs(dx) + abs(dy) != distance:  # 只检查当前距离圈层
                        continue

                    target_x = current_tile_x + dx
                    target_y = current_tile_y + dy

                    if (0 <= target_x < GameConstants.MAP_WIDTH and
                            0 <= target_y < GameConstants.MAP_HEIGHT):
                        tile = game_map[target_y][target_x]
                        if tile.type == TileType.GROUND or tile.is_dug:
                            return (target_x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                                    target_y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)

        return None

    def _find_exploration_target(self, game_map: List[List[Tile]]) -> Tuple[float, float]:
        """寻找探索目标 - 优先选择已挖掘区域"""
        # 首先尝试找到已挖掘区域
        for _ in range(20):  # 尝试20次
            x = random.randint(1, GameConstants.MAP_WIDTH - 2)
            y = random.randint(1, GameConstants.MAP_HEIGHT - 2)
            tile = game_map[y][x]

            if tile.type == TileType.GROUND or tile.is_dug:
                return (x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                        y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)

        # 如果找不到已挖掘区域，随机选择一个位置
        x = random.randint(100, (GameConstants.MAP_WIDTH - 1)
                           * GameConstants.TILE_SIZE - 100)
        y = random.randint(100, (GameConstants.MAP_HEIGHT - 1)
                           * GameConstants.TILE_SIZE - 100)
        return (x, y)
