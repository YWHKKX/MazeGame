#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
具体建筑类型实现
根据 BUILDING_SYSTEM.md 文档实现各种建筑的特殊功能
"""

import time
import math
import random
from typing import List, Dict, Optional, Tuple, Any

from .building import Building, BuildingType, BuildingConfig, BuildingStatus
from src.core.constants import GameConstants


class DungeonHeart(Building):
    """地牢之心 - 核心建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 地牢之心特有属性
        self.gold_storage_capacity = float('inf')    # 无限金币存储
        self.mana_storage_capacity = float('inf')    # 无限法力存储
        self.engineer_training_capacity = 5          # 可同时训练5个工程师
        self.training_engineers = []                 # 正在训练的工程师

        # 地牢之心防御属性（根据BUILDING_SYSTEM.md设计）
        self.max_health = 1000                       # 最大生命值1000
        self.health = 1000                           # 当前生命值
        self.armor = 10                              # 护甲值10
        self.defense_radius = 120                    # 防御警报范围120像素
        self.is_core_destroyed = False               # 核心是否被摧毁
        self._needs_tile_update = False              # 是否需要更新tile对象

        # 地牢之心预建完成
        self.status = BuildingStatus.COMPLETED
        self.is_active = True
        self.construction_progress = 1.0

    def _update_production(self, delta_seconds: float, game_state) -> Dict[str, Any]:
        """更新地牢之心功能"""
        production = {}

        # 更新工程师训练
        self._update_engineer_training(delta_seconds, production)

        # 作为资源中转中心（无需特别处理，由游戏主逻辑管理）

        # 检查是否需要更新tile对象
        if self._needs_tile_update:
            production['needs_tile_update'] = True
            production['dungeon_heart'] = self
            self._needs_tile_update = False

        return production

    def _update_engineer_training(self, delta_seconds: float, production: Dict[str, Any]):
        """更新工程师训练"""
        completed_engineers = []

        for engineer_data in self.training_engineers[:]:
            engineer_data['remaining_time'] -= delta_seconds

            if engineer_data['remaining_time'] <= 0:
                completed_engineers.append(engineer_data)
                self.training_engineers.remove(engineer_data)

        if completed_engineers:
            production['engineers_completed'] = len(completed_engineers)
            production['engineer_types'] = [eng['type']
                                            for eng in completed_engineers]

    def train_engineer(self, engineer_type: str, cost: int) -> bool:
        """训练工程师"""
        if len(self.training_engineers) >= self.engineer_training_capacity:
            return False

        # 训练时间根据工程师类型
        training_times = {
            'basic': 60.0,      # 60秒
            'specialist': 120.0,  # 120秒
            'master': 300.0     # 300秒
        }

        training_time = training_times.get(engineer_type, 60.0)

        engineer_data = {
            'type': engineer_type,
            'remaining_time': training_time,
            'cost': cost
        }

        self.training_engineers.append(engineer_data)
        return True

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力"""
        if ability_name == "resource_storage":
            return {
                'activated': True,
                'effect': 'infinite_storage',
                'description': '提供无限资源存储'
            }
        elif ability_name == "engineer_training":
            return {
                'activated': True,
                'effect': 'engineer_training',
                'description': '可训练各种类型的工程师'
            }
        elif ability_name == "command_center":
            return {
                'activated': True,
                'effect': 'command_coordination',
                'description': '协调全地牢的建造和防御活动'
            }
        elif ability_name == "defense_status":
            return {
                'activated': True,
                'effect': 'defense_monitoring',
                'health': self.health,
                'max_health': self.max_health,
                'armor': self.armor,
                'health_percentage': self.get_health_percentage(),
                'description': f'生命值: {self.health}/{self.max_health}, 护甲: {self.armor}'
            }
        elif ability_name == "alarm_system":
            return {
                'activated': True,
                'effect': 'defense_alert',
                'range': self.defense_radius,
                'is_under_attack': self.is_under_attack(),
                'description': f'受到攻击时全地牢单位自动防御 (范围: {self.defense_radius}像素)'
            }

        return super()._execute_special_ability(ability_name, target)

    def _update_tile_health(self):
        """更新tile对象的血量信息"""
        # 这个方法需要在游戏主循环中调用，因为需要访问game_map
        # 这里只是标记需要更新
        self._needs_tile_update = True

    def take_damage(self, damage: int) -> Dict[str, Any]:
        """地牢之心受到伤害"""
        if self.is_core_destroyed:
            return {'damage_taken': 0, 'health_remaining': 0, 'is_destroyed': True}

        # 计算实际伤害（考虑护甲）
        actual_damage = max(1, damage - self.armor)  # 最少造成1点伤害
        self.health = max(0, self.health - actual_damage)

        result = {
            'damage_taken': actual_damage,
            'health_remaining': self.health,
            'is_destroyed': False
        }

        # 检查是否被摧毁
        if self.health <= 0:
            self.is_core_destroyed = True
            self.is_active = False
            result['is_destroyed'] = True
            result['game_over'] = True  # 地牢之心被摧毁，游戏结束
            print("💀 地牢之心被摧毁！游戏失败！")

        # 更新tile对象的血量信息
        self._update_tile_health()

        return result

    def heal(self, amount: int) -> int:
        """治疗地牢之心"""
        if self.is_core_destroyed:
            return 0

        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        healed_amount = self.health - old_health

        if healed_amount > 0:
            print(
                f"💚 地牢之心恢复了 {healed_amount} 点生命值 (当前: {self.health}/{self.max_health})")
            # 更新tile对象的血量信息
            self._update_tile_health()

        return healed_amount

    def get_health_percentage(self) -> float:
        """获取生命值百分比"""
        if self.max_health <= 0:
            return 0.0
        return (self.health / self.max_health) * 100

    def is_under_attack(self) -> bool:
        """检查是否正在受到攻击"""
        return self.health < self.max_health and not self.is_core_destroyed

    def get_defense_status(self) -> Dict[str, Any]:
        """获取防御状态信息"""
        return {
            'health': self.health,
            'max_health': self.max_health,
            'armor': self.armor,
            'health_percentage': self.get_health_percentage(),
            'is_destroyed': self.is_core_destroyed,
            'is_under_attack': self.is_under_attack(),
            'defense_radius': self.defense_radius
        }


class Treasury(Building):
    """金库 - 经济建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 金库特有属性
        self.gold_storage_capacity = 500            # 金库存储容量
        self.stored_gold = 0                        # 金库中存储的金币
        self.is_accessible = True                   # 是否可以被访问

    def _update_production(self, delta_seconds: float, game_state) -> Dict[str, Any]:
        """更新金库功能 - 移除被动收入，只管理存储"""
        production = {}
        # 金库不再生成被动收入，只作为存储设施
        return production

    def _update_maintenance(self, delta_seconds: float, game_state, result: Dict[str, Any]):
        """金库不需要维护成本"""
        # 金库作为存储设施，不需要维护成本
        pass

    def deposit_gold(self, amount: int) -> int:
        """存入金币到金库"""
        if not self.is_accessible:
            return 0

        available_space = self.gold_storage_capacity - self.stored_gold
        deposit_amount = min(amount, available_space)

        if deposit_amount > 0:
            self.stored_gold += deposit_amount
            print(
                f"💰 金库({self.name}) 在位置({self.x},{self.y}) 存入 {deposit_amount} 金币 (当前存储: {self.stored_gold}/{self.gold_storage_capacity})")

        return deposit_amount

    def withdraw_gold(self, amount: int) -> int:
        """从金库取出金币"""
        if not self.is_accessible:
            return 0

        withdraw_amount = min(amount, self.stored_gold)

        if withdraw_amount > 0:
            self.stored_gold -= withdraw_amount
            print(
                f"💰 金库({self.name}) 在位置({self.x},{self.y}) 取出 {withdraw_amount} 金币 (当前存储: {self.stored_gold}/{self.gold_storage_capacity})")

        return withdraw_amount

    def get_available_space(self) -> int:
        """获取可用存储空间"""
        return self.gold_storage_capacity - self.stored_gold

    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        return {
            'stored': self.stored_gold,
            'capacity': self.gold_storage_capacity,
            'available': self.get_available_space(),
            'usage_percentage': (self.stored_gold / self.gold_storage_capacity) * 100 if self.gold_storage_capacity > 0 else 0
        }

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力"""
        if ability_name == "gold_storage":
            return {
                'activated': True,
                'effect': 'storage_capacity',
                'value': self.gold_storage_capacity,
                'description': f'提供{self.gold_storage_capacity}金币存储容量'
            }
        elif ability_name == "gold_exchange":
            return {
                'activated': True,
                'effect': 'gold_exchange',
                'stored': self.stored_gold,
                'capacity': self.gold_storage_capacity,
                'description': f'当前存储{self.stored_gold}/{self.gold_storage_capacity}金币'
            }

        return super()._execute_special_ability(ability_name, target)


class Lair(Building):
    """巢穴 - 怪物住房"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 巢穴特有属性
        self.housing_capacity = 5                   # 容纳5个怪物
        self.healing_boost = 2.0                    # 治疗速度提升100%
        self.morale_boost_range = 60                # 士气加成范围60像素
        self.morale_boost_value = 0.1               # 攻击力+10%
        self.healing_rate = 2                       # 每秒回复2点生命值

        self.housed_creatures = []                  # 住房中的怪物

    def _update_production(self, delta_seconds: float, game_state) -> Dict[str, Any]:
        """更新巢穴功能"""
        production = {}

        # 更新治疗功能
        healed_creatures = self._update_healing(delta_seconds)
        if healed_creatures:
            production['creatures_healed'] = healed_creatures

        # 士气加成由游戏主循环处理（需要访问所有怪物）

        return production

    def _update_healing(self, delta_seconds: float) -> int:
        """更新治疗功能"""
        healed_count = 0
        current_time = time.time()

        if current_time - self.last_production_time >= 1.0:  # 每秒治疗
            for creature in self.housed_creatures[:]:
                if creature.health < creature.max_health:
                    old_health = creature.health
                    creature.health = min(creature.max_health,
                                          creature.health + self.healing_rate)
                    if creature.health > old_health:
                        healed_count += 1

            self.last_production_time = current_time

        return healed_count

    def add_creature(self, creature) -> bool:
        """添加怪物到巢穴"""
        if len(self.housed_creatures) >= self.housing_capacity:
            return False

        self.housed_creatures.append(creature)
        return True

    def remove_creature(self, creature) -> bool:
        """从巢穴移除怪物"""
        if creature in self.housed_creatures:
            self.housed_creatures.remove(creature)
            return True
        return False

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力"""
        if ability_name == "creature_housing":
            return {
                'activated': True,
                'effect': 'housing',
                'capacity': self.housing_capacity,
                'current': len(self.housed_creatures),
                'description': f'可容纳{self.housing_capacity}个怪物单位'
            }
        elif ability_name == "healing_boost":
            return {
                'activated': True,
                'effect': 'healing_acceleration',
                'boost': self.healing_boost,
                'description': f'怪物治疗速度提升{int(self.healing_boost * 100)}%'
            }
        elif ability_name == "morale_boost":
            return {
                'activated': True,
                'effect': 'morale_bonus',
                'range': self.morale_boost_range,
                'bonus': self.morale_boost_value,
                'description': f'{self.morale_boost_range}像素内怪物攻击力+{int(self.morale_boost_value * 100)}%'
            }

        return super()._execute_special_ability(ability_name, target)


class TrainingRoom(Building):
    """训练室 - 怪物训练"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 训练室特有属性
        self.training_capacity = 3                  # 同时训练3个怪物
        self.experience_multiplier = 1.5            # 1.5倍经验获得
        self.training_time_per_attribute = 60.0     # 每个属性60秒训练时间

        self.training_creatures = []                # 正在训练的怪物

    def _update_production(self, delta_seconds: float, game_state) -> Dict[str, Any]:
        """更新训练功能"""
        production = {}

        # 更新训练进度
        completed_training = self._update_training(delta_seconds)
        if completed_training:
            production['training_completed'] = completed_training

        return production

    def _update_training(self, delta_seconds: float) -> List[Dict[str, Any]]:
        """更新训练进度"""
        completed = []

        for training_data in self.training_creatures[:]:
            training_data['remaining_time'] -= delta_seconds

            if training_data['remaining_time'] <= 0:
                # 训练完成，应用属性提升
                creature = training_data['creature']
                attribute = training_data['attribute']

                self._apply_training_bonus(creature, attribute)
                completed.append({
                    'creature': creature,
                    'attribute': attribute,
                    'bonus_applied': True
                })

                self.training_creatures.remove(training_data)

        return completed

    def start_training(self, creature, attribute: str) -> bool:
        """开始训练怪物属性"""
        if len(self.training_creatures) >= self.training_capacity:
            return False

        training_data = {
            'creature': creature,
            'attribute': attribute,
            'remaining_time': self.training_time_per_attribute
        }

        self.training_creatures.append(training_data)
        return True

    def _apply_training_bonus(self, creature, attribute: str):
        """应用训练加成"""
        bonus_values = {
            'attack': 5,        # 攻击力+5
            'health': 20,       # 生命值+20
            'speed': 3,         # 速度+3
            'armor': 2          # 护甲+2
        }

        bonus = bonus_values.get(attribute, 0)

        if attribute == 'attack' and hasattr(creature, 'attack'):
            creature.attack += bonus
        elif attribute == 'health' and hasattr(creature, 'max_health'):
            creature.max_health += bonus
            creature.health += bonus  # 同时增加当前生命值
        elif attribute == 'speed' and hasattr(creature, 'speed'):
            creature.speed += bonus
        elif attribute == 'armor' and hasattr(creature, 'armor'):
            creature.armor += bonus

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力"""
        if ability_name == "creature_training":
            return {
                'activated': True,
                'effect': 'attribute_training',
                'capacity': self.training_capacity,
                'current': len(self.training_creatures),
                'description': f'可同时训练{self.training_capacity}个怪物'
            }
        elif ability_name == "experience_boost":
            return {
                'activated': True,
                'effect': 'experience_multiplier',
                'multiplier': self.experience_multiplier,
                'description': f'{self.experience_multiplier}倍经验获得'
            }

        return super()._execute_special_ability(ability_name, target)


class Library(Building):
    """图书馆 - 魔法研究"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 图书馆特有属性
        self.mana_generation_rate = 0.2             # 每秒生成0.2点法力
        self.spell_enhancement_range = 60           # 法术增强范围60像素
        self.spell_power_bonus = 0.15               # 法术威力+15%

        self.researched_spells = []                 # 已研究的法术
        self.current_research = None                # 当前研究项目

    def _update_production(self, delta_seconds: float, game_state) -> Dict[str, Any]:
        """更新图书馆功能"""
        production = {}

        # 生成法力
        current_time = time.time()
        if current_time - self.last_production_time >= 1.0:  # 每秒生成
            mana_generated = self.mana_generation_rate * self.efficiency

            if hasattr(game_state, 'mana'):
                game_state.mana = min(
                    200, game_state.mana + mana_generated)  # 法力上限200
                production['mana_generated'] = mana_generated

            self.last_production_time = current_time

        # 更新研究进度
        if self.current_research:
            research_progress = self._update_research(delta_seconds)
            if research_progress:
                production['research_progress'] = research_progress

        return production

    def _update_research(self, delta_seconds: float) -> Optional[Dict[str, Any]]:
        """更新研究进度"""
        if not self.current_research:
            return None

        self.current_research['remaining_time'] -= delta_seconds

        if self.current_research['remaining_time'] <= 0:
            # 研究完成
            spell_name = self.current_research['spell']
            self.researched_spells.append(spell_name)

            result = {
                'completed': True,
                'spell': spell_name,
                'description': f'研究完成：{spell_name}'
            }

            self.current_research = None
            return result

        return {
            'completed': False,
            'progress': 1.0 - (self.current_research['remaining_time'] /
                               self.current_research['total_time'])
        }

    def start_research(self, spell_name: str, research_time: float = 300.0) -> bool:
        """开始研究法术"""
        if self.current_research is not None:
            return False

        self.current_research = {
            'spell': spell_name,
            'remaining_time': research_time,
            'total_time': research_time
        }

        return True

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力"""
        if ability_name == "mana_generation":
            return {
                'activated': True,
                'effect': 'mana_production',
                'rate': self.mana_generation_rate,
                'description': f'每秒生成{self.mana_generation_rate}点法力'
            }
        elif ability_name == "spell_research":
            return {
                'activated': True,
                'effect': 'research_capability',
                'researched_count': len(self.researched_spells),
                'current_research': self.current_research['spell'] if self.current_research else None,
                'description': '解锁新的法术和技能'
            }
        elif ability_name == "spell_enhancement":
            return {
                'activated': True,
                'effect': 'spell_power_boost',
                'range': self.spell_enhancement_range,
                'bonus': self.spell_power_bonus,
                'description': f'{self.spell_enhancement_range}像素内法术威力+{int(self.spell_power_bonus * 100)}%'
            }

        return super()._execute_special_ability(ability_name, target)


class ArrowTower(Building):
    """箭塔 - 防御建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 箭塔特有属性 - 与弓箭手保持一致
        self.attack_range = 120
        self.attack_damage = 16
        self.attack_interval = 1.0
        self.critical_chance = 0.25
        self.critical_multiplier = 2.0
        self.ammunition_type = "精准箭矢"            # 弹药类型

        self.last_attack_time = 0.0
        self.current_target = None
        self.attack_cooldown = 0.0                  # 攻击冷却时间

    def _update_production(self, delta_seconds: float, game_state) -> Dict[str, Any]:
        """更新箭塔攻击"""
        production = {}

        # 更新攻击冷却时间
        if self.attack_cooldown > 0:
            self.attack_cooldown -= delta_seconds

        # 如果攻击冷却完成，标记为可以攻击
        if self.attack_cooldown <= 0 and self.current_target:
            production['ready_to_attack'] = True
            production['target'] = self.current_target
            production['tower_position'] = (self.x, self.y)
            production['attack_range'] = self.attack_range

        return production

    def can_attack_target(self, target) -> bool:
        """检查是否可以攻击目标"""
        if not target or not self.is_active:
            return False

        # 计算距离 - 优先使用pixel_x/pixel_y，如果没有则使用瓦片坐标
        if hasattr(self, 'pixel_x') and hasattr(self, 'pixel_y'):
            tower_pixel_x = self.pixel_x
            tower_pixel_y = self.pixel_y
        else:
            tower_pixel_x = self.x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            tower_pixel_y = self.y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        distance = math.sqrt((target.x - tower_pixel_x) **
                             2 + (target.y - tower_pixel_y) ** 2)

        return distance <= self.attack_range

    def find_best_target(self, enemies) -> Optional[Any]:
        """寻找最佳攻击目标 - 根据BUILDING_SYSTEM.md的AI行为优先级"""
        if not enemies or not self.is_active:
            return None

        valid_targets = []
        # 计算距离 - 优先使用pixel_x/pixel_y，如果没有则使用瓦片坐标
        if hasattr(self, 'pixel_x') and hasattr(self, 'pixel_y'):
            tower_pixel_x = self.pixel_x
            tower_pixel_y = self.pixel_y
        else:
            tower_pixel_x = self.x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            tower_pixel_y = self.y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        for enemy in enemies:
            if not hasattr(enemy, 'health') or enemy.health <= 0:
                continue

            # 计算距离
            distance = math.sqrt((enemy.x - tower_pixel_x)
                                 ** 2 + (enemy.y - tower_pixel_y) ** 2)

            if distance <= self.attack_range:
                # 计算威胁值：血量越低威胁越大，距离越近威胁越大
                threat_value = (1000 - getattr(enemy, 'health', 1000)) / \
                    1000.0 + (self.attack_range - distance) / self.attack_range
                valid_targets.append((enemy, threat_value, distance))

        if not valid_targets:
            return None

        # 按威胁值排序，选择威胁最大的目标
        valid_targets.sort(key=lambda x: x[1], reverse=True)
        return valid_targets[0][0]

    def attack_target(self, target) -> Dict[str, Any]:
        """攻击目标 - 根据BUILDING_SYSTEM.md的攻击功能"""
        if not self.can_attack_target(target):
            return {'attacked': False, 'reason': 'out_of_range'}

        if self.attack_cooldown > 0:
            return {'attacked': False, 'reason': 'cooldown'}

        # 计算伤害 - 精准箭矢，有25%概率造成双倍伤害
        damage = self.attack_damage
        is_critical = random.random() < self.critical_chance

        if is_critical:
            damage = int(damage * self.critical_multiplier)

        # 应用伤害
        if hasattr(target, 'health'):
            target.health -= damage
            if target.health < 0:
                target.health = 0

        # 重置攻击冷却
        self.attack_cooldown = self.attack_interval
        self.last_attack_time = time.time()
        self.current_target = target

        return {
            'attacked': True,
            'damage': damage,
            'is_critical': is_critical,
            'target_health': getattr(target, 'health', 0),
            'ammunition_type': self.ammunition_type,
            'tower_position': (self.x, self.y)
        }

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力 - 根据BUILDING_SYSTEM.md的AI行为"""
        if ability_name == "auto_attack":
            return {
                'activated': True,
                'effect': 'automatic_targeting',
                'range': self.attack_range,
                'damage': self.attack_damage,
                'description': f'自动攻击{self.attack_range}像素半径内的敌人，优先攻击威胁最大的目标'
            }
        elif ability_name == "range_attack":
            return {
                'activated': True,
                'effect': 'ranged_combat',
                'interval': self.attack_interval,
                'critical_chance': self.critical_chance,
                'ammunition_type': self.ammunition_type,
                'description': f'精准箭矢攻击，每{self.attack_interval}秒攻击一次，{int(self.critical_chance * 100)}%概率造成双倍伤害'
            }

        return super()._execute_special_ability(ability_name, target)


class MagicAltar(Building):
    """魔法祭坛 - 魔法建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 魔法祭坛特有属性
        self.mana_generation_rate = 1.0             # 每秒生成1.0点法力
        self.spell_amplification_range = 80         # 法术增强范围80像素
        self.spell_power_multiplier = 1.25          # 法术威力增强25%

        self.requires_mage_assistance = True        # 需要法师辅助
        self.assigned_mage = None

    def _update_production(self, delta_seconds: float, game_state) -> Dict[str, Any]:
        """更新魔法祭坛功能"""
        production = {}

        # 只有在有法师辅助时才能正常工作
        if not self.assigned_mage:
            return production

        # 生成法力
        current_time = time.time()
        if current_time - self.last_production_time >= 1.0:  # 每秒生成
            mana_generated = self.mana_generation_rate * self.efficiency

            if hasattr(game_state, 'mana'):
                game_state.mana = min(200, game_state.mana + mana_generated)
                production['mana_generated'] = mana_generated

            self.last_production_time = current_time

        return production

    def assign_mage(self, mage) -> bool:
        """分配法师"""
        if self.assigned_mage is not None:
            return False

        self.assigned_mage = mage
        return True

    def remove_mage(self) -> bool:
        """移除法师"""
        if self.assigned_mage is None:
            return False

        self.assigned_mage = None
        return True

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力"""
        if ability_name == "mana_generation":
            return {
                'activated': True,
                'effect': 'enhanced_mana_production',
                'rate': self.mana_generation_rate,
                'requires_mage': self.requires_mage_assistance,
                'description': f'每秒生成{self.mana_generation_rate}点法力（需要法师辅助）'
            }
        elif ability_name == "spell_amplification":
            return {
                'activated': True,
                'effect': 'spell_power_enhancement',
                'range': self.spell_amplification_range,
                'multiplier': self.spell_power_multiplier,
                'description': f'{self.spell_amplification_range}像素内法术威力增强{int((self.spell_power_multiplier - 1) * 100)}%'
            }

        return super()._execute_special_ability(ability_name, target)
