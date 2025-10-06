#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
具体建筑类型实现
根据 BUILDING_SYSTEM.md 文档实现各种建筑的特殊功能
"""

import time
import math
import random
import pygame
from typing import List, Dict, Optional, Tuple, Any

from .building import Building, BuildingType, BuildingConfig, BuildingStatus
from src.core.constants import GameConstants
from src.core.enums import CreatureType
from src.effects.effect_manager import EffectManager
from src.utils.logger import game_logger
from src.entities.monster.orc_warrior import OrcWarrior
from src.entities.monster.imp import Imp


class DungeonHeart(Building):
    """地牢之心 - 核心建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 地牢之心特有属性
        self.gold_storage_capacity = 1000            # 最大金币存储1000
        self.stored_gold = 1000                      # 地牢之心存储的金币（初始1000）
        self.mana_storage_capacity = 1000            # 最大魔力存储1000
        self.stored_mana = 500                       # 地牢之心存储的魔力（初始500）
        self.engineer_training_capacity = 5          # 可同时训练5个工程师
        self.training_engineers = []                 # 正在训练的工程师

        # 魔力生成系统 - 参考MagicAltar设计风格
        self.mana_generation_rate = 0.2               # 每秒生成0.2点魔力（相当于每5秒1点）
        self.last_mana_generation_time = 0            # 上次魔力生成时间
        self.mana_generation_interval = 1.0           # 魔力生成间隔（秒）

        # 魔力生成统计系统
        self.mana_generation_stats = {
            'total_mana_generated': 0.0,              # 总生成魔力量
            'generation_sessions': 0,                 # 生成会话次数
            'peak_generation_rate': 0.0,              # 峰值生成速率
            'average_generation_rate': 0.0,           # 平均生成速率
            'last_generation_time': 0.0,              # 上次生成时间
            'generation_efficiency': 1.0              # 生成效率
        }

        # 地牢之心防御属性（根据BUILDING_SYSTEM.md设计）
        self.defense_radius = 120                    # 防御警报范围120像素
        self.is_core_destroyed = False               # 核心是否被摧毁
        self._needs_tile_update = False              # 是否需要更新tile对象

        # 地牢之心预建完成
        self.status = BuildingStatus.COMPLETED
        self.is_active = True
        self.construction_progress = 1.0

        # 标记为预建建筑，不应被建筑管理器重置状态
        self.is_prebuilt = True

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新地牢之心功能"""
        production = {}

        # 更新工程师训练
        self._update_engineer_training(delta_seconds, production)

        # 魔力增长系统
        self._update_magic_generation(delta_seconds, game_state, production)

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

    def _update_magic_generation(self, delta_seconds: float, game_state, production: Dict[str, Any]):
        """更新魔力生成系统 - 参考MagicAltar设计风格"""
        current_time = time.time()

        # 更新运行时间统计
        self.mana_generation_stats['total_operating_time'] = getattr(
            self.mana_generation_stats, 'total_operating_time', 0) + delta_seconds

        # 检查是否应该生成魔力（只有在建筑完成时才能生成）
        if self.status != BuildingStatus.COMPLETED:
            return

        # 每秒生成魔力
        if current_time - self.last_mana_generation_time >= self.mana_generation_interval:
            # 计算基础魔力生成量
            base_mana_generated = self.mana_generation_rate * \
                self.mana_generation_stats['generation_efficiency']

            # 检查存储容量
            available_storage = self.mana_storage_capacity - self.stored_mana
            if available_storage > 0:
                # 生成魔力（取整数部分）
                actual_mana_generated = min(
                    int(base_mana_generated), available_storage)
                if actual_mana_generated > 0:
                    self.stored_mana += actual_mana_generated
                    self.last_mana_generation_time = current_time

                    # 记录生成统计
                    self._record_mana_generation(
                        actual_mana_generated, current_time)
                    production['mana_generated'] = actual_mana_generated

                    # 只在魔力达到特定阈值时输出日志
                    if self.stored_mana % 50 == 0 or self.stored_mana >= self.mana_storage_capacity * 0.9:
                        game_logger.info(
                            "💖 地牢之心魔力: {stored}/{capacity}",
                            stored=self.stored_mana,
                            capacity=self.mana_storage_capacity
                        )
            else:
                # 存储已满，记录警告
                if self.stored_mana >= self.mana_storage_capacity:
                    game_logger.warning(
                        "💖 地牢之心魔力存储已满，无法生成更多魔力"
                    )

    def _record_mana_generation(self, mana_amount: float, current_time: float):
        """记录魔力生成统计 - 参考MagicAltar设计风格"""
        # 更新总生成量
        self.mana_generation_stats['total_mana_generated'] += mana_amount

        # 更新生成会话次数
        self.mana_generation_stats['generation_sessions'] += 1

        # 更新峰值生成速率
        current_rate = mana_amount / self.mana_generation_interval
        if current_rate > self.mana_generation_stats['peak_generation_rate']:
            self.mana_generation_stats['peak_generation_rate'] = current_rate

        # 更新平均生成速率
        if self.mana_generation_stats['generation_sessions'] > 0:
            total_time = current_time - \
                self.mana_generation_stats.get('start_time', current_time)
            if total_time > 0:
                self.mana_generation_stats['average_generation_rate'] = (
                    self.mana_generation_stats['total_mana_generated'] / total_time
                )

        # 更新上次生成时间
        self.mana_generation_stats['last_generation_time'] = current_time

        # 设置开始时间（如果未设置）
        if 'start_time' not in self.mana_generation_stats:
            self.mana_generation_stats['start_time'] = current_time

    def get_mana_generation_stats(self) -> Dict[str, Any]:
        """获取魔力生成统计信息 - 参考MagicAltar设计风格"""
        return {
            'total_mana_generated': self.mana_generation_stats['total_mana_generated'],
            'generation_sessions': self.mana_generation_stats['generation_sessions'],
            'peak_generation_rate': self.mana_generation_stats['peak_generation_rate'],
            'average_generation_rate': self.mana_generation_stats['average_generation_rate'],
            'current_stored_mana': self.stored_mana,
            'mana_storage_capacity': self.mana_storage_capacity,
            'generation_efficiency': self.mana_generation_stats['generation_efficiency'],
            'last_generation_time': self.mana_generation_stats['last_generation_time']
        }

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

        # 使用统一的护甲减免计算
        actual_damage = self._calculate_armor_reduction(damage)

        # 只在伤害较大时输出日志
        if actual_damage >= 5:
            game_logger.warning(
                "💖 地牢之心受伤 {damage} 点 (生命: {health}/{max_health})",
                damage=actual_damage, health=self.health, max_health=self.max_health)

        old_health = self.health
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
            self.logger.error("💀 地牢之心被摧毁！游戏失败！")

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
            game_logger.info(
                "💚 地牢之心恢复了 {healed} 点生命值 (当前: {health}/{max_health})",
                healed=healed_amount, health=self.health, max_health=self.max_health)
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

    def get_status_for_indicator(self) -> str:
        """
        获取地牢之心状态用于状态指示器

        Returns:
            str: 状态名称
        """
        from src.core.constants import GameConstants

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁，返回摧毁状态
        if self.status == BuildingStatus.DESTROYED or self.is_core_destroyed:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 默认返回完成状态
        return GameConstants.BUILDING_STATUS_COMPLETED

    def get_engineer_task_type(self) -> str:
        """
        获取地牢之心的工程师任务类型

        地牢之心作为核心建筑，不需要工程师进行维护工作
        它应该专注于资源生成和存储功能

        Returns:
            str: 任务类型，地牢之心始终返回 'idle'
        """
        # 地牢之心不需要工程师维护，始终返回空闲状态
        return 'idle'

    def accept_gold_deposit(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币存储（永久存储）- 地牢之心重写"""
        # 地牢之心有无限存储容量，可以接受所有金币
        if gold_amount <= 0:
            return {
                'deposited': False,
                'reason': 'invalid_amount',
                'message': '存入数量必须大于0'
            }

        # 直接存储金币（无限容量）
        self.stored_gold += gold_amount

        return {
            'deposited': True,
            'amount_deposited': gold_amount,
            'new_stored_gold': self.stored_gold,
            'message': f'地牢之心存储了 {gold_amount} 金币 (当前: {self.stored_gold})'
        }

    def accept_gold_investment(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币投入（临时存储）- 地牢之心不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '地牢之心不支持金币投入功能'
        }

    def accept_ammunition_reload(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的弹药装填 - 地牢之心不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '地牢之心不支持弹药装填功能'
        }

    def can_accept_gold(self) -> bool:
        """检查地牢之心是否可以接受金币"""
        # 地牢之心只有在金币存储未满时才接受金币
        # 这样可以避免工程师无意义地存储金币到已满的地牢之心
        return self.stored_gold < self.gold_storage_capacity


class Treasury(Building):
    """金库 - 经济建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 金库特有属性
        self.gold_storage_capacity = 500            # 金库存储容量
        self.stored_gold = 0                        # 金库中存储的金币
        self.is_accessible = True                   # 是否可以被访问

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新金库功能 - 移除被动收入，只管理存储"""
        production = {}
        # 金库不再生成被动收入，只作为存储设施
        return production

    def _update_maintenance(self, delta_seconds: float, game_state, result: Dict[str, Any]):
        """金库不需要维护成本"""
        # 金库作为存储设施，不需要维护成本
        pass

    def can_accept_gold(self) -> bool:
        """
        检查金库是否可以接受金币存储

        Returns:
            bool: 只有在金库没有爆满时才返回True
        """
        # 金库只有在没有爆满时才接受金币存储
        return self.is_accessible and self.stored_gold < self.gold_storage_capacity

    def withdraw_gold(self, amount: int) -> int:
        """从金库取出金币"""
        if not self.is_accessible:
            return 0

        withdraw_amount = min(amount, self.stored_gold)

        if withdraw_amount > 0:
            self.stored_gold -= withdraw_amount
            game_logger.info(
                "💰 金库({name}) 在位置({x},{y}) 取出 {amount} 金币 (当前存储: {stored}/{capacity})",
                name=self.name, x=self.x, y=self.y, amount=withdraw_amount,
                stored=self.stored_gold, capacity=self.gold_storage_capacity)

        return withdraw_amount

    def get_available_space(self) -> int:
        """获取可用存储空间"""
        return max(0, self.gold_storage_capacity - self.stored_gold)

    def is_full(self) -> bool:
        """检查金库是否已满"""
        return self.stored_gold >= self.gold_storage_capacity

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

    def accept_gold_deposit(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币存储（永久存储）- 金库重写"""
        if not self.is_accessible:
            return {
                'deposited': False,
                'reason': 'not_accessible',
                'message': '金库不可访问，无法存储金币'
            }

        if self.stored_gold >= self.gold_storage_capacity:
            return {
                'deposited': False,
                'reason': 'already_full',
                'message': '金库存储已满，无法存储更多金币'
            }

        # 计算可以存储的金币数量
        available_space = self.gold_storage_capacity - self.stored_gold
        actual_gold_stored = min(gold_amount, available_space)

        # 存储金币
        self.stored_gold += actual_gold_stored

        return {
            'deposited': True,
            'amount_deposited': actual_gold_stored,
            'new_stored_gold': self.stored_gold,
            'max_storage_capacity': self.gold_storage_capacity,
            'remaining_space': self.gold_storage_capacity - self.stored_gold,
            'message': f'金库存储了 {actual_gold_stored} 金币 (当前: {self.stored_gold}/{self.gold_storage_capacity})'
        }

    def accept_gold_investment(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币投入（临时存储）- 金库不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '金库不支持金币投入功能'
        }

    def accept_ammunition_reload(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的弹药装填 - 金库不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '金库不支持弹药装填功能'
        }

    def get_status_for_indicator(self) -> str:
        """
        获取金库状态用于状态指示器

        Returns:
            str: 状态名称
        """
        from src.core.constants import GameConstants

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁，返回摧毁状态
        if self.status == BuildingStatus.DESTROYED:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 如果金库爆满
        if self.stored_gold >= self.gold_storage_capacity:
            return GameConstants.BUILDING_STATUS_TREASURY_FULL

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 如果建筑完成且正常
        return GameConstants.BUILDING_STATUS_COMPLETED


class TrainingRoom(Building):
    """训练室 - 怪物训练"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 训练室特有属性
        self.training_capacity = 3                  # 同时训练3个怪物
        self.experience_multiplier = 1.5            # 1.5倍经验获得
        self.training_time_per_attribute = 60.0     # 每个属性60秒训练时间

        self.training_creatures = []                # 正在训练的怪物

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
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

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新图书馆功能"""
        production = {}

        # 生成法力 - 使用ResourceManager
        current_time = time.time()
        if current_time - self.last_production_time >= 1.0:  # 每秒生成
            mana_generated = self.mana_generation_rate * self.efficiency

            # 使用ResourceManager添加魔力
            from src.managers.resource_manager import get_resource_manager
            resource_manager = get_resource_manager(game_state)
            resource_manager.add_mana(mana_generated, self)
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

        # 箭塔特有属性 - 与文档BUILDING_SYSTEM.md保持一致
        self.attack_range = 100  # 100像素半径，与文档一致
        self.attack_damage = 30  # 30点物理伤害，与文档一致
        self.attack_interval = 1.5  # 1.5秒攻击间隔，与文档一致
        self.critical_chance = 0.25
        self.critical_multiplier = 1.5
        self.ammunition_type = "精准箭矢"            # 弹药类型

        # 战斗单位设置
        self.is_combat_unit = True  # 箭塔是战斗单位

        # 击退系统配置 - 使用新的固定距离机制
        self.has_strong_knockback = True  # 具有强击退能力
        self.knockback_type = None  # 动态确定击退类型（普通/强击退）

        # 弹药系统
        self.max_ammunition = 60                     # 最大弹药值
        self.current_ammunition = 60                 # 当前弹药值
        self.ammunition_per_shot = 1                 # 每次射击消耗的弹药

        self.last_attack_time = 0.0
        self.current_target = None
        self.attack_cooldown = 0.0                  # 攻击冷却时间

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新箭塔攻击 - 使用绝对时间避免时间漂移"""
        production = {}

        # 使用绝对时间检查攻击冷却，与combat_system保持一致
        current_time = time.time()
        if hasattr(self, 'last_attack_time') and self.last_attack_time > 0:
            time_since_last_attack = current_time - self.last_attack_time
            if time_since_last_attack >= self.attack_interval:
                # 攻击冷却完成
                if self.current_target:
                    production['ready_to_attack'] = True
                    production['target'] = self.current_target
                    production['tower_position'] = (self.x, self.y)
                    production['attack_range'] = self.attack_range

        return production

    def can_attack_target(self, target) -> bool:
        """检查是否可以攻击目标"""
        if not target or not self.is_active:
            return False

        # 检查弹药是否足够
        if self.current_ammunition < self.ammunition_per_shot:
            return False

        # 计算距离 - Building的x,y已经是像素坐标
        tower_pixel_x = self.x
        tower_pixel_y = self.y

        distance = math.sqrt((target.x - tower_pixel_x) **
                             2 + (target.y - tower_pixel_y) ** 2)

        return distance <= self.attack_range

    def find_best_target(self, enemies) -> Optional[Any]:
        """寻找最佳攻击目标 - 根据BUILDING_SYSTEM.md的AI行为优先级"""
        if not enemies or not self.is_active:
            return None

        valid_targets = []
        # 计算距离 - Building的x,y已经是像素坐标
        tower_pixel_x = self.x
        tower_pixel_y = self.y

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
        """攻击目标 - 穿透范围攻击"""

        if not self.can_attack_target(target):
            return {'attacked': False, 'reason': 'out_of_range'}

        # 时间检查已由combat_system统一处理，这里不再重复检查
        # if self.attack_cooldown > 0:
        #     return {'attacked': False, 'reason': 'cooldown'}

        # 检查弹药是否足够
        if self.current_ammunition < self.ammunition_per_shot:
            return {'attacked': False, 'reason': 'no_ammunition'}

        # 计算伤害 - 精准箭矢，有25%概率造成双倍伤害
        damage = self.attack_damage
        is_critical = random.random() < self.critical_chance

        if is_critical:
            damage = int(damage * self.critical_multiplier)

        # 设置暴击标志用于击退计算
        self.is_critical_attack = is_critical

        # 计算攻击方向（从箭塔指向目标）
        direction = math.atan2(target.y - self.y, target.x - self.x)
        direction_degrees = math.degrees(direction)

        # 特效创建已移至高级范围攻击系统统一处理

        # 使用高级范围攻击系统进行穿透范围攻击
        if hasattr(target, 'game_instance') and target.game_instance:
            from src.systems.advanced_area_damage import get_advanced_area_damage_system, AreaAttackConfig, AreaAttackType

            if is_critical:
                game_logger.info(
                    "🏹 箭塔暴击! 对 {target} 造成 {damage} 点伤害 (位置: {x},{y})",
                    target=target, damage=damage, x=self.x, y=self.y)
                area_config = AreaAttackConfig(
                    attack_type=AreaAttackType.SECTOR,
                    damage_ratio=0.8,  # 穿透攻击伤害为原伤害的80%
                    target_type='enemy',  # 恢复为只攻击敌人
                    effect_type='tower_critical_arrow',
                    radius=140.0,  # 穿透射程140像素
                    angle=15.0,  # 狭窄的扇形角度，模拟穿透箭矢
                    direction=direction_degrees
                )
            else:
                area_config = AreaAttackConfig(
                    attack_type=AreaAttackType.SECTOR,
                    damage_ratio=0.7,  # 穿透攻击伤害为原伤害的70%
                    target_type='enemy',  # 恢复为只攻击敌人
                    effect_type='tower_arrow_shot',
                    radius=120.0,  # 穿透射程120像素
                    angle=15.0,  # 狭窄的扇形角度，模拟穿透箭矢
                    direction=direction_degrees
                )

            # 应用穿透范围攻击
            area_system = get_advanced_area_damage_system(target.game_instance)
            area_result = area_system.apply_area_damage(
                attacker=self,
                primary_target=target,
                damage=damage,
                start_x=self.x,
                start_y=self.y,
                direction=direction_degrees,
                area_config=area_config
            )

            game_logger.info(
                "🏹 箭塔穿透范围攻击: 命中{targets}个目标，总伤害{damage}",
                targets=area_result.targets_hit, damage=area_result.total_damage)
        else:
            # 备用方法：直接对目标造成伤害
            if hasattr(target, 'health'):
                if hasattr(target, '_take_damage'):
                    target._take_damage(damage, attacker=self)
                else:
                    target.health -= damage
                    if target.health < 0:
                        target.health = 0

        # 消耗弹药
        self.current_ammunition -= self.ammunition_per_shot

        # 重置攻击冷却 - 只更新last_attack_time，使用绝对时间机制
        self.last_attack_time = time.time()
        self.current_target = target

        result = {
            'attacked': True,
            'damage': damage,
            'is_critical': is_critical,
            'target_health': getattr(target, 'health', 0),
            'ammunition_type': self.ammunition_type,
            'tower_position': (self.x, self.y),
            'ammunition_remaining': self.current_ammunition,
            'attack_type': 'piercing'
        }

        return result

    def can_accept_gold(self) -> bool:
        """
        检查箭塔是否可以接受金币装填

        Returns:
            bool: 只有在弹药为空时才返回True
        """
        # 箭塔只有在弹药为空时才接受金币装填
        return self.current_ammunition <= 0

    def accept_gold_deposit(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币存储 - 箭塔不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '箭塔不支持金币存储功能'
        }

    def accept_ammunition_reload(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的弹药装填 - 箭塔重写"""
        if self.current_ammunition >= self.max_ammunition:
            return {
                'deposited': False,
                'reason': 'already_full',
                'message': '箭塔弹药已满，无需装填'
            }

        # 记录装填前的弹药数量
        old_ammunition = self.current_ammunition

        # 计算可以装填的弹药数量（1金币=1弹药）
        ammunition_needed = self.max_ammunition - self.current_ammunition
        actual_gold_used = min(gold_amount, ammunition_needed)
        actual_ammunition_added = actual_gold_used

        # 装填弹药
        self.current_ammunition += actual_ammunition_added

        return {
            'deposited': True,
            'amount_deposited': actual_gold_used,
            'ammunition_added': actual_ammunition_added,
            'old_ammunition': old_ammunition,
            'new_ammunition': self.current_ammunition,
            'max_ammunition': self.max_ammunition,
            'message': f'装填了 {actual_ammunition_added} 发弹药，消耗 {actual_gold_used} 金币'
        }

    def get_status_for_indicator(self) -> str:
        """
        获取箭塔状态用于状态指示器

        Returns:
            str: 状态名称
        """
        from src.core.constants import GameConstants

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁，返回摧毁状态
        if self.status == BuildingStatus.DESTROYED:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 如果弹药为空
        if self.current_ammunition <= 0:
            return GameConstants.BUILDING_STATUS_NO_AMMUNITION

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 如果建筑完成且正常
        return GameConstants.BUILDING_STATUS_COMPLETED

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

    def can_accept_ammunition(self) -> bool:
        """
        检查箭塔是否可以接受弹药装填

        Returns:
            bool: 只有在弹药为空时才返回True
        """
        # 箭塔只有在弹药为空时才接受弹药装填
        return self.current_ammunition <= 0

    def set_knockback_type(self, knockback_type):
        """
        设置箭塔的击退类型

        Args:
            knockback_type: 击退类型（NORMAL, STRONG, WEAK, NONE）
        """
        from src.core.enums import KnockbackType
        self.knockback_type = knockback_type
        game_logger.info(f"🏹 箭塔击退类型设置为: {knockback_type.value}")

    def get_knockback_info(self) -> dict:
        """
        获取箭塔的击退信息

        Returns:
            dict: 击退信息
        """
        from src.core.enums import KnockbackType
        from src.core.constants import GameConstants

        return {
            'has_strong_knockback': self.has_strong_knockback,
            'knockback_type': self.knockback_type.value if self.knockback_type else 'dynamic',
            'available_types': ['normal', 'strong'],
            'distances': {
                'normal': GameConstants.KNOCKBACK_DISTANCE_NORMAL,
                'strong': GameConstants.KNOCKBACK_DISTANCE_STRONG
            }
        }


class ArcaneTower(Building):
    """奥术塔 - 魔法防御建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 奥术塔特有属性 - 参考箭塔设计
        self.attack_range = 100  # 100像素半径，与箭塔一致
        self.attack_damage = 40  # 40点魔法伤害，提升伤害
        self.attack_interval = 2.5  # 2.5秒攻击间隔，比箭塔慢
        self.critical_chance = 0.25
        self.critical_multiplier = 2.0
        self.attack_type = "magic"  # 魔法攻击类型

        # 战斗单位设置
        self.is_combat_unit = True  # 奥术塔是战斗单位

        # 击退系统配置 - 奥术塔设置为无击退
        self.has_strong_knockback = False  # 不具有强击退能力
        self.knockback_type = None  # 设置为无击退类型

        # 魔力消耗配置（不存储魔力，通过资源管理器消耗）
        self.mana_per_shot = 1  # 每次攻击消耗的魔力

        self.last_attack_time = 0.0
        self.current_target = None
        self.attack_cooldown = 0.0  # 攻击冷却时间

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新奥术塔攻击 - 使用绝对时间避免时间漂移"""
        production = {}

        # 使用绝对时间检查攻击冷却，与combat_system保持一致
        current_time = time.time()
        if hasattr(self, 'last_attack_time') and self.last_attack_time > 0:
            time_since_last_attack = current_time - self.last_attack_time
            if time_since_last_attack >= self.attack_interval:
                # 攻击冷却完成
                if self.current_target:
                    production['ready_to_attack'] = True
                    production['target'] = self.current_target
                    production['tower_position'] = (self.x, self.y)
                    production['attack_range'] = self.attack_range

        return production

    def can_attack_target(self, target) -> bool:
        """检查是否可以攻击目标"""
        if not target or not self.is_active:
            return False

        # 检查魔力是否足够（通过资源管理器检查）
        if hasattr(self, 'game_instance') and self.game_instance:
            from src.managers.resource_consumption_manager import ResourceConsumptionManager
            consumption_manager = ResourceConsumptionManager(
                self.game_instance)
            can_afford, _ = consumption_manager.can_afford(
                mana_cost=self.mana_per_shot)
            if not can_afford:
                return False

        # 计算距离 - Building的x,y已经是像素坐标
        tower_pixel_x = self.x
        tower_pixel_y = self.y

        distance = math.sqrt((target.x - tower_pixel_x) **
                             2 + (target.y - tower_pixel_y) ** 2)

        return distance <= self.attack_range

    def find_best_target(self, enemies) -> Optional[Any]:
        """寻找最佳攻击目标 - 根据BUILDING_SYSTEM.md的AI行为优先级"""
        if not enemies or not self.is_active:
            return None

        valid_targets = []
        # 计算距离 - Building的x,y已经是像素坐标
        tower_pixel_x = self.x
        tower_pixel_y = self.y

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
        """攻击目标 - 魔法圆形范围攻击"""

        if not self.can_attack_target(target):
            return {'attacked': False, 'reason': 'out_of_range'}

        # 检查并消耗魔力（通过资源管理器）
        if hasattr(self, 'game_instance') and self.game_instance:
            from src.managers.resource_consumption_manager import ResourceConsumptionManager
            consumption_manager = ResourceConsumptionManager(
                self.game_instance)
            consumption_result = consumption_manager.consume_resources(
                mana_cost=self.mana_per_shot)
            if not consumption_result.success:
                return {'attacked': False, 'reason': 'no_mana', 'message': consumption_result.message}
        else:
            return {'attacked': False, 'reason': 'no_game_instance'}

        # 计算伤害 - 奥术魔法，有25%概率造成双倍伤害
        damage = self.attack_damage
        is_critical = random.random() < self.critical_chance

        if is_critical:
            damage = int(damage * self.critical_multiplier)

        # 计算攻击方向（从奥术塔指向目标）
        direction = math.atan2(target.y - self.y, target.x - self.x)
        direction_degrees = math.degrees(direction)

        # 特效创建已移至高级范围攻击系统统一处理

        # 使用高级范围攻击系统进行圆形魔法攻击
        if hasattr(target, 'game_instance') and target.game_instance:
            from src.systems.advanced_area_damage import get_advanced_area_damage_system, AreaAttackConfig, AreaAttackType

            # 创建圆形魔法攻击配置
            area_config = AreaAttackConfig(
                attack_type=AreaAttackType.CIRCLE,
                damage_ratio=0.8,  # 范围攻击伤害为原伤害的80%
                target_type='enemy',  # 只攻击敌人
                effect_type='tower_magic_impact',
                radius=60.0,  # 圆形攻击半径60像素
                angle=360.0,  # 全圆形攻击
                direction=0.0  # 方向不重要，因为是圆形
            )

            # 应用圆形魔法攻击
            area_system = get_advanced_area_damage_system(target.game_instance)
            area_result = area_system.apply_area_damage(
                attacker=self,
                primary_target=target,
                damage=damage,
                start_x=target.x,  # 圆形攻击以目标为中心
                start_y=target.y,
                direction=direction_degrees,
                area_config=area_config
            )

            game_logger.info(
                "🔮 奥术塔魔法范围攻击: 命中{targets}个目标，总伤害{damage}",
                targets=area_result.targets_hit, damage=area_result.total_damage)
        else:
            # 备用方法：直接对目标造成伤害
            if hasattr(target, 'health'):
                if hasattr(target, '_take_damage'):
                    target._take_damage(damage, attacker=self)
                else:
                    target.health -= damage
                    if target.health < 0:
                        target.health = 0

        # 重置攻击冷却 - 只更新last_attack_time，使用绝对时间机制
        self.last_attack_time = time.time()
        self.current_target = target

        result = {
            'attacked': True,
            'damage': damage,
            'is_critical': is_critical,
            'target_health': getattr(target, 'health', 0),
            'attack_type': 'magic_circle',
            'tower_position': (self.x, self.y),
            'mana_consumed': self.mana_per_shot
        }

        return result

    def can_accept_gold(self) -> bool:
        """检查奥术塔是否可以接受金币"""
        # 奥术塔不支持金币存储
        return False

    def get_status_for_indicator(self) -> str:
        """获取奥术塔状态用于状态指示器"""
        from src.core.constants import GameConstants

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁，返回摧毁状态
        if self.status == BuildingStatus.DESTROYED:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 检查魔力是否足够（通过资源管理器）
        if hasattr(self, 'game_instance') and self.game_instance:
            from src.managers.resource_consumption_manager import ResourceConsumptionManager
            consumption_manager = ResourceConsumptionManager(
                self.game_instance)
            can_afford, _ = consumption_manager.can_afford(
                mana_cost=self.mana_per_shot)
            if not can_afford:
                return GameConstants.BUILDING_STATUS_NO_AMMUNITION  # 复用弹药耗尽状态

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 如果建筑完成且正常
        return GameConstants.BUILDING_STATUS_COMPLETED

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力 - 奥术塔的魔法攻击能力"""
        if ability_name == "auto_attack":
            return {
                'activated': True,
                'effect': 'magic_auto_targeting',
                'range': self.attack_range,
                'damage': self.attack_damage,
                'description': f'自动魔法攻击{self.attack_range}像素半径内的敌人，优先攻击威胁最大的目标'
            }
        elif ability_name == "magic_attack":
            return {
                'activated': True,
                'effect': 'magic_ranged_combat',
                'interval': self.attack_interval,
                'critical_chance': self.critical_chance,
                'mana_type': '奥术魔力',
                'description': f'奥术魔法攻击，每{self.attack_interval}秒攻击一次，{int(self.critical_chance * 100)}%概率造成双倍伤害'
            }

        return super()._execute_special_ability(ability_name, target)

    def set_knockback_type(self, knockback_type):
        """
        设置奥术塔的击退类型

        Args:
            knockback_type: 击退类型（NORMAL, STRONG, WEAK, NONE）
        """
        from src.core.enums import KnockbackType
        self.knockback_type = knockback_type
        game_logger.info(f"🔮 奥术塔击退类型设置为: {knockback_type.value}")

    def get_knockback_info(self) -> dict:
        """
        获取奥术塔的击退信息

        Returns:
            dict: 击退信息
        """
        from src.core.enums import KnockbackType
        from src.core.constants import GameConstants

        return {
            'has_strong_knockback': self.has_strong_knockback,
            'knockback_type': self.knockback_type.value if self.knockback_type else 'none',
            'available_types': ['none'],  # 奥术塔只支持无击退
            'distances': {
                'none': 0  # 无击退距离为0
            }
        }


class MagicAltar(Building):
    """魔法祭坛 - 魔法建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 魔法祭坛特有属性
        self.mana_generation_rate = 1.0             # 每秒生成1.0点法力
        self.spell_amplification_range = 80         # 法术增强范围80像素
        self.spell_power_multiplier = 1.25          # 法术威力增强25%

        # 法力存储系统
        self.mana_storage_capacity = 500            # 法力存储容量
        self.stored_mana = 0                        # 当前存储的法力

        # 临时金币系统
        self.temp_gold = 0                          # 临时金币
        self.max_temp_gold = 60                     # 最大临时金币

        # 法师辅助系统
        self.requires_mage_assistance = True        # 需要法师辅助
        self.assigned_mage = None
        self.mage_bonus_multiplier = 1.5            # 有法师时的法力生成倍率

        # 魔力生成状态系统
        self.is_mana_generation_mode = False        # 是否处于魔力生成状态
        self.last_mana_generation_time = 0          # 上次魔力生成时间
        self.mana_generation_interval = 2.0         # 魔力生成间隔（秒）

        # 粒子特效系统 - 直接使用游戏主循环的EffectManager
        self.mana_particle_max_range = 20.0
        self.mana_particle_max_count = 40
        self.mana_particle_spawn_timer = 0.0
        self.mana_particle_spawn_interval = 0.2  # 每0.2秒生成一个魔力粒子

        # 魔法光环效果
        self.magic_aura_radius = 100                # 魔法光环半径
        self.aura_enhancement_bonus = 0.1           # 光环内单位法术威力+10%

        # 资源统计系统
        self.resource_stats = {
            'total_mana_generated': 0.0,            # 总生成法力量
            'total_mana_stored': 0.0,               # 总存储法力量
            'total_temp_gold_stored': 0.0,          # 总存储临时金币量
            'generation_sessions': 0,               # 生成会话次数
            'temp_gold_storage_sessions': 0,        # 临时金币存储会话次数
            'peak_storage_usage': 0.0,              # 峰值存储使用量
            'peak_temp_gold_usage': 0.0,            # 峰值临时金币使用量
            'average_generation_rate': 0.0,         # 平均生成速率
            'average_temp_gold_storage_rate': 0.0,  # 平均临时金币存储速率
            'efficiency_rating': 1.0,               # 效率评级
            'uptime_percentage': 0.0,               # 运行时间百分比
            'last_generation_time': 0.0,            # 最后生成时间
            'last_temp_gold_storage_time': 0.0,     # 最后临时金币存储时间
            'total_operating_time': 0.0,            # 总运行时间
            'idle_time': 0.0,                       # 空闲时间
            'maintenance_cost': 0,                  # 维护成本
            'upgrade_cost': 0,                      # 升级成本
            'resource_efficiency': 1.0              # 资源效率
        }

        # 历史记录
        self.generation_history = []                # 生成历史记录
        self.temp_gold_storage_history = []         # 临时金币存储历史记录
        self.efficiency_history = []                # 效率历史记录

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新魔法祭坛功能"""
        production = {}
        current_time = time.time()

        # 调试信息已移除，减少输出噪音

        # 更新运行时间统计
        self.resource_stats['total_operating_time'] += delta_seconds

        # 检查是否应该进入魔力生成状态（只有在建筑完成时才能进入）
        if (not self.is_mana_generation_mode and
            self.status == BuildingStatus.COMPLETED and
                self.temp_gold >= self.max_temp_gold):
            self.is_mana_generation_mode = True
            game_logger.info(
                "🔮 魔法祭坛({name}) 临时金币存储已满，进入魔力生成状态！", name=self.name)

            # 魔力生成状态：消耗金币生成法力
        if self.is_mana_generation_mode:
            # 直接使用游戏主循环的EffectManager
            if hasattr(game_state, 'effect_manager') and game_state.effect_manager:
                # 更新粒子特效 - 使用瓦块中心像素坐标
                center_x = self.tile_x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
                center_y = self.tile_y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

                # 生成魔力粒子
                self.mana_particle_spawn_timer += delta_seconds
                if (self.mana_particle_spawn_timer >= self.mana_particle_spawn_interval and
                        game_state.effect_manager.get_mana_particle_count() < self.mana_particle_max_count):
                    game_state.effect_manager.create_mana_particle(
                        center_x, center_y, self.mana_particle_max_range)
                    self.mana_particle_spawn_timer = 0.0

                # 注意：粒子系统由主游戏循环统一更新，这里不需要重复更新

            if self.temp_gold > 0 and current_time - self.last_mana_generation_time >= self.mana_generation_interval:
                # 消耗1枚临时金币
                self.temp_gold -= 1

                # 生成1点法力
                available_storage = self.mana_storage_capacity - self.stored_mana
                if available_storage > 0:
                    self.stored_mana += 1
                    self.last_mana_generation_time = current_time

                    # 记录生成统计
                    self._record_mana_generation(1.0, current_time)
                else:
                    game_logger.warning(
                        "🔮 魔法祭坛({name}) 法力存储已满，无法生成更多法力", name=self.name)

                # 如果临时金币消耗殆尽，退出魔力生成状态
                if self.temp_gold <= 0:
                    self.is_mana_generation_mode = False
                    # 清除所有魔力粒子
                    if hasattr(game_state, 'effect_manager') and game_state.effect_manager:
                        game_state.effect_manager.clear_mana_particles()
                    game_logger.info(
                        "🔮 魔法祭坛({name}) 临时金币消耗殆尽，退出魔力生成状态", name=self.name)

            # 在魔力生成状态下，不进行常规法力生成
            self._update_efficiency_stats(delta_seconds)
            return production

        # 只有在有法师辅助时才能正常工作
        if not self.assigned_mage:
            # 记录空闲时间
            self.resource_stats['idle_time'] += delta_seconds
            return production

        # 生成法力到存储池
        if current_time - self.last_production_time >= 1.0:  # 每秒生成
            # 计算基础法力生成量
            base_mana_generated = self.mana_generation_rate * self.efficiency

            # 如果有法师辅助，应用倍率加成
            if self.assigned_mage:
                base_mana_generated *= self.mage_bonus_multiplier

            # 存储到祭坛的法力池
            available_storage = self.mana_storage_capacity - self.stored_mana
            mana_to_store = min(base_mana_generated, available_storage)

            if mana_to_store > 0:
                self.stored_mana += mana_to_store

                # 记录生成统计
                self._record_mana_generation(mana_to_store, current_time)

                game_logger.info(
                    "🔮 魔法祭坛({name}) 在位置({x},{y}) 生成了 {mana:.1f} 点法力 (存储: {stored}/{capacity})",
                    name=self.name, x=self.x, y=self.y, mana=mana_to_store,
                    stored=self.stored_mana, capacity=self.mana_storage_capacity)

            self.last_production_time = current_time

        # 更新效率统计
        self._update_efficiency_stats(delta_seconds)

        return production

    def assign_mage(self, mage) -> bool:
        """分配法师"""
        if self.assigned_mage is not None:
            return False

        self.assigned_mage = mage
        game_logger.info(
            "🔮 魔法祭坛({name}) 在位置({x},{y}) 分配了法师 {mage_name}",
            name=self.name, x=self.x, y=self.y,
            mage_name=mage.name if hasattr(mage, 'name') else 'Unknown')
        return True

    def remove_mage(self) -> bool:
        """移除法师"""
        if self.assigned_mage is None:
            return False

        game_logger.info("🔮 魔法祭坛({name}) 在位置({x},{y}) 移除了法师",
                         name=self.name, x=self.x, y=self.y)
        self.assigned_mage = None
        return True

    def get_mana_storage_info(self) -> Dict[str, Any]:
        """获取法力存储信息"""
        return {
            'stored': self.stored_mana,
            'capacity': self.mana_storage_capacity,
            'available': self.mana_storage_capacity - self.stored_mana,
            'usage_percentage': (self.stored_mana / self.mana_storage_capacity) * 100 if self.mana_storage_capacity > 0 else 0,
            'has_mage': self.assigned_mage is not None,
            'generation_rate': self.mana_generation_rate * (self.mage_bonus_multiplier if self.assigned_mage else 1.0)
        }

    def get_gold_storage_info(self) -> Dict[str, Any]:
        """获取临时金币存储信息"""
        return {
            'stored': self.temp_gold,
            'capacity': self.max_temp_gold,
            'available': self.max_temp_gold - self.temp_gold,
            'usage_percentage': (self.temp_gold / self.max_temp_gold) * 100 if self.max_temp_gold > 0 else 0,
            'total_stored': self.resource_stats['total_temp_gold_stored']
        }

    def get_magic_aura_units(self, all_units) -> List[Any]:
        """获取魔法光环范围内的单位"""
        aura_units = []
        if not all_units:
            return aura_units

        for unit in all_units:
            if not hasattr(unit, 'x') or not hasattr(unit, 'y'):
                continue

            distance = math.sqrt((unit.x - self.x) **
                                 2 + (unit.y - self.y) ** 2)
            if distance <= self.magic_aura_radius:
                aura_units.append(unit)

        return aura_units

    def can_accept_gold(self) -> bool:
        """检查是否可以接受金币"""
        # 只有在建筑完成且临时金币未满且不在魔力生成状态时才能接受金币
        return (self.status == BuildingStatus.COMPLETED and
                self.temp_gold < self.max_temp_gold and
                not self.is_mana_generation_mode)

    def get_status(self) -> str:
        """获取魔法祭坛状态"""
        from src.core.constants import GameConstants

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁，返回摧毁状态
        if self.status == BuildingStatus.DESTROYED:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 魔法祭坛特殊状态
        if self.is_mana_generation_mode:
            return "Generating Mana"
        elif self.temp_gold < self.max_temp_gold:
            return "Needs Gold"
        else:
            return GameConstants.BUILDING_STATUS_COMPLETED

    def accept_gold_deposit(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币存储（永久存储）- 魔法祭坛不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '魔法祭坛不支持金币存储功能'
        }

    def accept_gold_investment(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币投入（临时存储，用于魔力生成）- 魔法祭坛重写"""
        # 检查是否处于魔力生成状态
        if self.is_mana_generation_mode:
            return {
                'deposited': False,
                'reason': 'mana_generation_active',
                'message': '魔法祭坛正在魔力生成中，无法接受金币投入'
            }

        # 检查是否已经满了
        if self.temp_gold >= self.max_temp_gold:
            return {
                'deposited': False,
                'reason': 'already_full',
                'message': '魔法祭坛临时金币存储已满'
            }

        # 计算可以存储的临时金币数量
        available_space = self.max_temp_gold - self.temp_gold
        actual_gold_stored = min(gold_amount, available_space)

        # 存储临时金币
        self.temp_gold += actual_gold_stored
        current_time = time.time()
        self._record_temp_gold_storage(actual_gold_stored, current_time)

        # 注意：不在这里设置魔力生成状态，让 _update_production 统一处理
        # 这样可以避免重复修改和竞态条件

        return {
            'deposited': True,
            'amount_deposited': actual_gold_stored,
            'temp_gold': self.temp_gold,
            'max_temp_gold': self.max_temp_gold,
            'is_mana_generation_mode': self.is_mana_generation_mode,
            'message': f'投入了 {actual_gold_stored} 临时金币用于魔力生成 (存储: {self.temp_gold}/{self.max_temp_gold})'
        }

    def accept_ammunition_reload(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的弹药装填 - 魔法祭坛不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '魔法祭坛不支持弹药装填功能'
        }

    def render_mana_particles(self, screen, effect_manager, ui_scale: float = 1.0, camera_x: float = 0, camera_y: float = 0):
        """渲染魔力生成粒子特效"""
        if self.is_mana_generation_mode and effect_manager:
            # 渲染魔力粒子
            effect_manager.particle_system.render(
                screen, ui_scale, camera_x, camera_y)

    def set_particle_max_count(self, max_particles: int):
        """设置粒子最大数量"""
        self.mana_particle_max_count = max_particles
        # 调试信息已移除，减少输出噪音

    def get_particle_info(self, effect_manager) -> Dict[str, Any]:
        """获取粒子系统信息"""
        if not effect_manager:
            return {'current_count': 0, 'is_active': False}
        return {
            'current_count': effect_manager.get_mana_particle_count(),
            'max_particles': self.mana_particle_max_count,
            'is_active': effect_manager.is_mana_active(),
            'is_mana_generation_mode': self.is_mana_generation_mode
        }

    def set_particle_glow_intensity(self, effect_manager, intensity: float):
        """设置粒子发光强度"""
        # 通过特效管理器设置发光强度
        if effect_manager:
            effect_manager.particle_system.set_glow_intensity(intensity)

    def set_particle_glow_enabled(self, effect_manager, enabled: bool):
        """启用或禁用粒子发光效果"""
        # 通过特效管理器设置发光效果
        if effect_manager:
            effect_manager.particle_system.set_glow_enabled(enabled)

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力"""
        if ability_name == "mana_generation":
            return {
                'activated': True,
                'effect': 'enhanced_mana_production',
                'rate': self.mana_generation_rate,
                'storage_capacity': self.mana_storage_capacity,
                'stored_mana': self.stored_mana,
                'requires_mage': self.requires_mage_assistance,
                'has_mage': self.assigned_mage is not None,
                'description': f'每秒生成{self.mana_generation_rate}点法力到存储池（需要法师辅助，当前存储: {self.stored_mana}/{self.mana_storage_capacity}）'
            }
        elif ability_name == "spell_amplification":
            return {
                'activated': True,
                'effect': 'spell_power_enhancement',
                'range': self.spell_amplification_range,
                'multiplier': self.spell_power_multiplier,
                'description': f'{self.spell_amplification_range}像素内法术威力增强{int((self.spell_power_multiplier - 1) * 100)}%'
            }
        elif ability_name == "magic_aura":
            return {
                'activated': True,
                'effect': 'magic_aura_enhancement',
                'radius': self.magic_aura_radius,
                'bonus': self.aura_enhancement_bonus,
                'description': f'{self.magic_aura_radius}像素内所有单位法术威力+{int(self.aura_enhancement_bonus * 100)}%'
            }
        elif ability_name == "mana_storage":
            storage_info = self.get_mana_storage_info()
            return {
                'activated': True,
                'effect': 'mana_storage',
                'stored': storage_info['stored'],
                'capacity': storage_info['capacity'],
                'usage_percentage': storage_info['usage_percentage'],
                'description': f'法力存储池: {storage_info["stored"]}/{storage_info["capacity"]} ({storage_info["usage_percentage"]:.1f}%)'
            }
        elif ability_name == "gold_storage":
            gold_info = self.get_gold_storage_info()
            return {
                'activated': True,
                'effect': 'gold_storage',
                'stored': gold_info['stored'],
                'capacity': gold_info['capacity'],
                'usage_percentage': gold_info['usage_percentage'],
                'total_stored': gold_info['total_stored'],
                'description': f'金币存储池: {gold_info["stored"]}/{gold_info["capacity"]} ({gold_info["usage_percentage"]:.1f}%)'
            }

        return super()._execute_special_ability(ability_name, target)

    def _record_mana_generation(self, amount: float, timestamp: float):
        """记录法力生成统计"""
        self.resource_stats['total_mana_generated'] += amount
        self.resource_stats['total_mana_stored'] += amount
        self.resource_stats['generation_sessions'] += 1
        self.resource_stats['last_generation_time'] = timestamp

        # 更新峰值存储使用量
        current_usage = (self.stored_mana / self.mana_storage_capacity) * 100
        if current_usage > self.resource_stats['peak_storage_usage']:
            self.resource_stats['peak_storage_usage'] = current_usage

        # 记录到历史
        self.generation_history.append({
            'timestamp': timestamp,
            'amount': amount,
            'stored_after': self.stored_mana,
            'efficiency': self.efficiency
        })

        # 保持历史记录在合理范围内
        if len(self.generation_history) > 1000:
            self.generation_history = self.generation_history[-500:]

    def _record_temp_gold_storage(self, amount: int, timestamp: float):
        """记录临时金币存储统计"""
        self.resource_stats['total_temp_gold_stored'] += amount
        self.resource_stats['temp_gold_storage_sessions'] += 1
        self.resource_stats['last_temp_gold_storage_time'] = timestamp

        # 更新峰值临时金币使用量
        current_gold_usage = (
            self.temp_gold / self.max_temp_gold) * 100
        if current_gold_usage > self.resource_stats['peak_temp_gold_usage']:
            self.resource_stats['peak_temp_gold_usage'] = current_gold_usage

        # 记录到历史
        self.temp_gold_storage_history.append({
            'timestamp': timestamp,
            'amount': amount,
            'stored_after': self.temp_gold,
            'efficiency': self.efficiency
        })

        # 保持历史记录在合理范围内
        if len(self.temp_gold_storage_history) > 1000:
            self.temp_gold_storage_history = self.temp_gold_storage_history[-500:]

    def _update_efficiency_stats(self, delta_seconds: float):
        """更新效率统计"""
        # 计算平均生成速率
        if self.resource_stats['total_operating_time'] > 0:
            self.resource_stats['average_generation_rate'] = (
                self.resource_stats['total_mana_generated'] /
                self.resource_stats['total_operating_time']
            )

        # 计算运行时间百分比
        total_time = self.resource_stats['total_operating_time'] + \
            self.resource_stats['idle_time']
        if total_time > 0:
            self.resource_stats['uptime_percentage'] = (
                self.resource_stats['total_operating_time'] / total_time * 100
            )

        # 计算效率评级
        base_efficiency = self.efficiency
        mage_bonus = self.mage_bonus_multiplier if self.assigned_mage else 1.0
        uptime_bonus = self.resource_stats['uptime_percentage'] / 100.0
        self.resource_stats['efficiency_rating'] = base_efficiency * \
            mage_bonus * uptime_bonus

        # 资源效率设为1.0（不再有转移功能）
        self.resource_stats['resource_efficiency'] = 1.0

        # 记录效率历史
        self.efficiency_history.append({
            'timestamp': time.time(),
            'efficiency_rating': self.resource_stats['efficiency_rating'],
            'uptime_percentage': self.resource_stats['uptime_percentage'],
            'resource_efficiency': self.resource_stats['resource_efficiency']
        })

        # 保持历史记录在合理范围内
        if len(self.efficiency_history) > 1000:
            self.efficiency_history = self.efficiency_history[-500:]

    def get_resource_statistics(self) -> Dict[str, Any]:
        """获取资源统计信息"""
        stats = self.resource_stats.copy()

        # 添加实时数据
        stats.update({
            'current_stored_mana': self.stored_mana,
            'storage_usage_percentage': (self.stored_mana / self.mana_storage_capacity) * 100,
            'has_mage': self.assigned_mage is not None,
            'is_active': self.is_active,
            'current_generation_rate': self.mana_generation_rate * (self.mage_bonus_multiplier if self.assigned_mage else 1.0),
            'is_mana_generation_mode': self.is_mana_generation_mode,
            'current_gold_stored': self.temp_gold,
            'gold_storage_usage_percentage': (self.temp_gold / self.max_temp_gold) * 100
        })

        # 添加历史数据摘要
        if self.generation_history:
            recent_generations = self.generation_history[-10:]  # 最近10次生成
            stats['recent_generation_average'] = sum(
                g['amount'] for g in recent_generations) / len(recent_generations)

        if self.temp_gold_storage_history:
            # 最近10次临时金币存储
            recent_gold_storage = self.temp_gold_storage_history[-10:]
            stats['recent_gold_storage_average'] = sum(
                g['amount'] for g in recent_gold_storage) / len(recent_gold_storage)

        return stats

    def get_detailed_report(self) -> Dict[str, Any]:
        """获取详细报告"""
        report = {
            'building_info': {
                'name': self.name,
                'position': (self.x, self.y),
                'status': self.status.value if hasattr(self.status, 'value') else str(self.status),
                'health': f"{self.health}/{self.max_health}",
                'efficiency': self.efficiency
            },
            'resource_stats': self.get_resource_statistics(),
            'performance_metrics': {
                'generation_per_hour': self.resource_stats['average_generation_rate'] * 3600,
                'storage_efficiency': (self.resource_stats['total_mana_stored'] /
                                       max(self.resource_stats['total_mana_stored'], 1)) * 100,
                'uptime_hours': self.resource_stats['total_operating_time'] / 3600,
                'idle_hours': self.resource_stats['idle_time'] / 3600
            },
            'recent_activity': {
                'last_generation': self.resource_stats['last_generation_time'],
                'last_gold_storage': self.resource_stats['last_gold_storage_time'],
                'generation_count': self.resource_stats['generation_sessions'],
                'gold_storage_count': self.resource_stats['gold_storage_sessions']
            }
        }

        return report

    def get_status_for_indicator(self) -> str:
        """
        获取魔法祭坛状态用于状态指示器

        Returns:
            str: 状态名称
        """
        from src.core.constants import GameConstants

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁，返回摧毁状态
        if self.status == BuildingStatus.DESTROYED:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 如果处于魔力生成状态，返回紫色状态
        if self.is_mana_generation_mode:
            return GameConstants.BUILDING_STATUS_MANA_GENERATION

        # 如果法力存储池已满
        if self.stored_mana >= self.mana_storage_capacity:
            return GameConstants.BUILDING_STATUS_MANA_FULL

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 默认返回完成状态
        return GameConstants.BUILDING_STATUS_COMPLETED


class OrcLair(Building):
    """兽人巢穴 - 训练建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 兽人巢穴特有属性
        self.temp_gold = 0  # 临时金币
        self.max_temp_gold = 30  # 最大临时金币
        self.bound_monster = None  # 绑定的怪物
        self.is_training = False  # 是否在训练状态
        self.training_start_time = 0.0  # 训练开始时间
        self.training_duration = 90.0  # 训练持续时间（秒）
        self.is_locked = False  # 是否锁定（有绑定怪物时锁定）
        self.assigned_worker = None  # 分配的苦工

        # 敌我关系设置
        self.is_enemy = False

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新兽人巢穴状态"""
        production = {}

        # 检查是否进入训练状态（需要苦工参与）
        if (not self.is_locked and not self.is_training and
            self.temp_gold >= self.max_temp_gold and
                self.assigned_worker is None):
            game_logger.info("🏹 兽人巢穴开始分配苦工进行训练")
            # 寻找可用的苦工进行训练
            self._assign_worker_for_training(game_state, workers)
            if self.assigned_worker:
                production['worker_assigned'] = True
                production['building_position'] = (self.x, self.y)
                game_logger.info(f"🏹 兽人巢穴成功分配苦工: {self.assigned_worker}")
            else:
                game_logger.info("🏹 兽人巢穴未能找到可用的苦工")

        # 检查训练是否完成
        if self.is_training:
            current_time = time.time()
            if current_time - self.training_start_time >= self.training_duration:
                # 训练完成，生成兽人战士
                self._complete_training()
                production['training_completed'] = True
                production['building_position'] = (self.x, self.y)

        return production

    def _assign_worker_for_training(self, game_state, workers: List = None):
        """分配苦工进行训练"""
        # 调试：检查传入的workers列表
        if workers is None:
            workers = []
            game_logger.info("🏹 没有传入workers列表，使用空列表")
        else:
            game_logger.info(f"🏹 接收到{len(workers)}个苦工")

        # 筛选出哥布林苦工
        available_workers = []
        for worker in workers:
            if (hasattr(worker, 'type') and worker.type == 'goblin_worker' and
                worker.health > 0 and
                    (not hasattr(worker, 'assigned_building') or worker.assigned_building is None)):
                available_workers.append(worker)

        game_logger.info(f"🏹 筛选出{len(available_workers)}个可用的哥布林苦工")

        if available_workers:
            # 选择第一个可用的苦工
            worker = available_workers[0]

            # 分配苦工到兽人巢穴
            self.assigned_worker = worker
            worker.assigned_building = self
            worker.target_building = self
            worker.task_type = 'training'

            # 设置苦工移动到兽人巢穴
            target_x = self.x  # self.x 已经是像素坐标
            target_y = self.y  # self.y 已经是像素坐标
            worker.set_target(target_x, target_y)

            game_logger.info(
                f"🏹 兽人巢穴分配苦工进行训练: 苦工位置({worker.x:.1f}, {worker.y:.1f}) -> 巢穴({target_x}, {target_y})")
        else:
            game_logger.info("🏹 没有可用的哥布林苦工进行训练")

    def start_training(self, worker):
        """开始训练（当苦工到达建筑时调用）"""
        if worker == self.assigned_worker and not self.is_training:
            self.is_training = True
            self.training_start_time = time.time()
            game_logger.info(
                f"🏹 兽人巢穴开始训练: 苦工已到达，训练时间{self.training_duration}秒")

    def _complete_training(self):
        """完成训练，生成兽人战士"""
        game_logger.info(f"🏹 [TRAINING_COMPLETE] 开始执行训练完成逻辑")

        # 创建兽人战士实例
        # 在巢穴附近生成兽人战士
        warrior_x = self.x + 16  # self.x 已经是像素坐标，只需偏移到中心
        warrior_y = self.y + 16

        orc_warrior = OrcWarrior(warrior_x, warrior_y,
                                 CreatureType.ORC_WARRIOR, summon_source="training")
        orc_warrior.bind_to_lair(self)

        # 设置游戏实例引用，用于触发攻击响应和击退效果
        if hasattr(self, 'game_instance') and self.game_instance:
            orc_warrior.game_instance = self.game_instance

        # 绑定到巢穴
        self.bound_monster = orc_warrior
        self.is_training = False
        self.is_locked = True
        self.temp_gold = 0  # 清空临时金币

        game_logger.info(f"🏹 [TRAINING_COMPLETE] 兽人战士已创建并绑定到巢穴")

        # 将兽人战士添加到游戏世界的怪物列表中
        if hasattr(self, 'game_instance') and self.game_instance:
            if hasattr(self.game_instance, 'monsters'):
                self.game_instance.monsters.append(orc_warrior)
                game_logger.info(f"🏹 [TRAINING_COMPLETE] 兽人战士已添加到游戏世界怪物列表")
            else:
                game_logger.warning(f"🏹 [TRAINING_COMPLETE] 游戏实例没有monsters列表")
        else:
            game_logger.warning(f"🏹 [TRAINING_COMPLETE] 无法访问游戏实例")

        # 删除苦工（苦工被训练成兽人战士）
        if self.assigned_worker:
            game_logger.info(
                f"🏹 [TRAINING_COMPLETE] 开始删除分配的苦工: {self.assigned_worker}")

            # 标记苦工为死亡状态
            self.assigned_worker.health = 0
            self.assigned_worker.is_dead_flag = True

            # 清除苦工的绑定关系
            self.assigned_worker.assigned_building = None
            self.assigned_worker.target_building = None
            self.assigned_worker.task_type = None

            game_logger.info(f"🏹 [TRAINING_COMPLETE] 哥布林苦工被训练成兽人战士，苦工已标记为死亡")
            game_logger.info(
                f"🏹 [TRAINING_COMPLETE] 苦工生命值: {self.assigned_worker.health}")
            game_logger.info(
                f"🏹 [TRAINING_COMPLETE] 苦工死亡标记: {self.assigned_worker.is_dead_flag}")

            # 清空引用
            self.assigned_worker = None
            game_logger.info(f"🏹 [TRAINING_COMPLETE] 苦工引用已清空")
        else:
            game_logger.info(f"🏹 [TRAINING_COMPLETE] 警告：没有分配的苦工需要删除")

        game_logger.info(
            f"🏹 [TRAINING_COMPLETE] 兽人巢穴完成训练，生成兽人战士 at ({warrior_x}, {warrior_y})")

    def on_bound_monster_died(self):
        """当绑定的怪物死亡时调用"""
        game_logger.info("🏹 兽人巢穴: 绑定的兽人战士死亡，解除绑定")
        self.bound_monster = None
        self.is_locked = False
        self.temp_gold = 0  # 清空临时金币

    def add_temp_gold(self, amount: int) -> bool:
        """添加临时金币"""
        if self.is_locked or self.is_training:
            return False

        self.temp_gold = min(self.temp_gold + amount, self.max_temp_gold)
        return True

    def can_accept_gold(self) -> bool:
        """检查是否可以接受金币"""
        return not self.is_locked and not self.is_training and self.temp_gold < self.max_temp_gold

    def accept_gold_deposit(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币存储（永久存储）- 兽人巢穴不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '兽人巢穴不支持金币存储功能'
        }

    def accept_gold_investment(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币投入（临时存储，用于训练怪物）- 兽人巢穴重写"""
        if self.is_locked:
            return {
                'deposited': False,
                'reason': 'locked',
                'message': '兽人巢穴已锁定，无法接受金币'
            }

        if self.is_training:
            return {
                'deposited': False,
                'reason': 'training',
                'message': '兽人巢穴正在训练中，无法接受金币'
            }

        if self.temp_gold >= self.max_temp_gold:
            return {
                'deposited': False,
                'reason': 'already_full',
                'message': '兽人巢穴临时金币已满'
            }

        # 计算可以存储的金币数量
        available_space = self.max_temp_gold - self.temp_gold
        actual_gold_stored = min(gold_amount, available_space)

        # 存储临时金币
        self.temp_gold += actual_gold_stored

        return {
            'deposited': True,
            'amount_deposited': actual_gold_stored,
            'new_temp_gold': self.temp_gold,
            'max_temp_gold': self.max_temp_gold,
            'message': f'兽人巢穴投入了 {actual_gold_stored} 金币用于训练怪物 (当前: {self.temp_gold}/{self.max_temp_gold})'
        }

    def accept_ammunition_reload(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的弹药装填 - 兽人巢穴不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '兽人巢穴不支持弹药装填功能'
        }

    def get_status(self) -> str:
        """获取建筑状态"""
        if self.is_training:
            return GameConstants.BUILDING_STATUS_TRAINING
        elif self.bound_monster:
            return GameConstants.BUILDING_STATUS_LOCKED
        elif self.assigned_worker and not self.is_training:
            return GameConstants.BUILDING_STATUS_READY_TO_TRAIN
        elif self.temp_gold >= self.max_temp_gold:
            return GameConstants.BUILDING_STATUS_READY_TO_TRAIN
        elif self.temp_gold > 0:
            return GameConstants.BUILDING_STATUS_ACCEPTING_GOLD
        else:
            return GameConstants.BUILDING_STATUS_COMPLETED

    def get_status_for_indicator(self) -> str:
        """
        获取兽人巢穴状态用于状态指示器

        Returns:
            str: 状态名称
        """
        from src.entities.building import BuildingStatus

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁
        if self.status == BuildingStatus.DESTROYED:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 兽人巢穴特殊状态
        if self.is_training:
            return GameConstants.BUILDING_STATUS_TRAINING
        elif self.bound_monster:
            return GameConstants.BUILDING_STATUS_LOCKED
        elif self.assigned_worker and not self.is_training:
            return GameConstants.BUILDING_STATUS_READY_TO_TRAIN
        elif self.temp_gold >= self.max_temp_gold:
            return GameConstants.BUILDING_STATUS_READY_TO_TRAIN
        elif self.temp_gold > 0:
            return GameConstants.BUILDING_STATUS_ACCEPTING_GOLD
        else:
            return GameConstants.BUILDING_STATUS_COMPLETED


class DemonLair(Building):
    """恶魔巢穴 - 召唤建筑"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        super().__init__(x, y, building_type, config)

        # 恶魔巢穴特有属性
        self.temp_gold = 0  # 临时金币
        self.max_temp_gold = 20  # 最大临时金币
        self.bound_monster = None  # 绑定的怪物
        self.is_summoning = False  # 是否在召唤状态
        self.is_summoning_paused = False  # 是否暂停召唤状态
        self.summon_start_time = 0.0  # 召唤开始时间
        self.summon_duration = 60.0  # 召唤持续时间（秒）- 恢复为60秒
        self.summon_elapsed_time = 0.0  # 已召唤时间（用于暂停后恢复）
        self.is_locked = False  # 是否锁定（有绑定怪物时锁定）
        self.mana_consumption_rate = 1.0  # 每秒消耗的魔力值
        self.last_mana_consumption_time = 0.0  # 上次消耗魔力的时间

        # 敌我关系设置
        self.is_enemy = False

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新恶魔巢穴状态"""
        production = {}

        # 详细状态日志：每5秒记录一次状态
        if hasattr(self, '_last_log_time'):
            if time.time() - self._last_log_time >= 5.0:
                self._last_log_time = time.time()
                game_logger.info(
                    "🔮 恶魔巢穴状态: 临时金币={temp_gold}/{max_temp_gold}, 召唤中={summoning}, 锁定={locked}, 绑定怪物={bound}",
                    temp_gold=self.temp_gold, max_temp_gold=self.max_temp_gold,
                    summoning=self.is_summoning, locked=self.is_locked,
                    bound=self.bound_monster is not None)
        else:
            self._last_log_time = time.time()

        # 检查是否进入召唤状态
        if not self.is_locked and not self.is_summoning and not self.is_summoning_paused and self.temp_gold >= self.max_temp_gold:
            self.is_summoning = True
            self.is_summoning_paused = False
            self.summon_start_time = time.time()
            self.summon_elapsed_time = 0.0
            production['summon_started'] = True
            production['building_position'] = (self.x, self.y)
            game_logger.info(
                "🔮 恶魔巢穴开始召唤: 临时金币={temp_gold}, 最大临时金币={max_temp_gold}, 召唤持续时间={duration}秒",
                temp_gold=self.temp_gold, max_temp_gold=self.max_temp_gold, duration=self.summon_duration)

        # 检查是否从暂停状态恢复召唤
        if not self.is_locked and not self.is_summoning and self.is_summoning_paused and self.temp_gold >= self.max_temp_gold:
            # 检查魔力是否足够
            from src.managers.resource_manager import get_resource_manager
            resource_manager = get_resource_manager(game_state)
            mana_info = resource_manager.get_total_mana()

            if mana_info.available >= self.mana_consumption_rate:
                self.is_summoning = True
                self.is_summoning_paused = False
                self.summon_start_time = time.time() - self.summon_elapsed_time  # 恢复之前的进度
                production['summon_resumed'] = True
                production['building_position'] = (self.x, self.y)
                game_logger.info(
                    "🔮 恶魔巢穴恢复召唤: 已召唤{elapsed:.1f}秒, 剩余{duration:.1f}秒",
                    elapsed=self.summon_elapsed_time, duration=self.summon_duration - self.summon_elapsed_time)

        # 检查召唤是否完成
        if self.is_summoning:
            current_time = time.time()
            summon_elapsed = current_time - self.summon_start_time
            summon_remaining = self.summon_duration - summon_elapsed

            # 每秒记录召唤进度
            if hasattr(self, '_last_progress_log_time'):
                if current_time - self._last_progress_log_time >= 1.0:
                    self._last_progress_log_time = current_time
                    progress_percent = (
                        summon_elapsed / self.summon_duration) * 100
                    game_logger.info(
                        "🔮 恶魔巢穴召唤进度: {progress:.1f}% ({elapsed:.1f}s/{duration:.1f}s, 剩余{remaining:.1f}s)",
                        progress=progress_percent, elapsed=summon_elapsed,
                        duration=self.summon_duration, remaining=summon_remaining)
            else:
                self._last_progress_log_time = current_time

            # 每秒消耗魔力值 - 添加时间间隔控制
            from src.managers.resource_manager import get_resource_manager
            resource_manager = get_resource_manager(game_state)

            # 检查是否到了消耗魔力的时间（每秒一次）
            if current_time - self.last_mana_consumption_time >= 1.0:
                self.last_mana_consumption_time = current_time

                # 检查魔力是否足够
                mana_info = resource_manager.get_total_mana()
                if mana_info.available >= self.mana_consumption_rate:
                    # 消耗魔力
                    mana_result = resource_manager.consume_mana(
                        self.mana_consumption_rate)
                    if mana_result['success']:
                        game_logger.debug(
                            "🔮 恶魔巢穴消耗 {rate} 魔力值进行召唤 (剩余魔力: {remaining})",
                            rate=self.mana_consumption_rate, remaining=mana_info.available - self.mana_consumption_rate)
                    else:
                        # 魔力不足，暂停召唤
                        self.is_summoning = False
                        self.is_summoning_paused = True
                        self.summon_elapsed_time = summon_elapsed  # 保存已召唤时间
                        production['summon_paused'] = True
                        production['reason'] = 'insufficient_mana'
                        production['building_position'] = (self.x, self.y)
                        game_logger.warning(
                            "🔮 恶魔巢穴暂停召唤: 魔力不足 (需要{need}, 可用{available}), 已召唤{elapsed:.1f}秒",
                            need=self.mana_consumption_rate, available=mana_info.available, elapsed=summon_elapsed)
                        return production
                else:
                    # 魔力不足，暂停召唤
                    self.is_summoning = False
                    self.is_summoning_paused = True
                    self.summon_elapsed_time = summon_elapsed  # 保存已召唤时间
                    production['summon_paused'] = True
                    production['reason'] = 'insufficient_mana'
                    production['building_position'] = (self.x, self.y)
                    game_logger.warning(
                        "🔮 恶魔巢穴暂停召唤: 魔力不足 (需要{need}, 可用{available}), 已召唤{elapsed:.1f}秒",
                        need=self.mana_consumption_rate, available=mana_info.available, elapsed=summon_elapsed)
                    return production

            # 检查召唤是否完成
            if current_time - self.summon_start_time >= self.summon_duration:
                # 召唤完成，生成小恶魔
                game_logger.info(
                    "🔮 恶魔巢穴召唤即将完成: 已召唤{elapsed:.1f}秒, 总时长{duration:.1f}秒",
                    elapsed=summon_elapsed, duration=self.summon_duration)
                self._complete_summoning()
                production['summon_completed'] = True
                production['building_position'] = (self.x, self.y)

        return production

    def _complete_summoning(self):
        """完成召唤，生成小恶魔"""
        # 创建小恶魔实例 - 使用专用的 Imp 类
        # 在巢穴附近生成小恶魔
        # 使用建筑的像素坐标，而不是瓦片坐标
        demon_x = self.x + GameConstants.TILE_SIZE // 2  # 建筑中心位置
        demon_y = self.y + GameConstants.TILE_SIZE // 2

        little_demon = Imp(demon_x, demon_y)

        # 绑定小恶魔到巢穴
        little_demon.bind_to_lair(self)

        # 绑定到巢穴
        self.bound_monster = little_demon
        self.is_summoning = False
        self.is_locked = True
        self.temp_gold = 0  # 清空临时金币

        game_logger.info(
            "🔮 恶魔巢穴完成召唤，生成小恶魔 at ({x}, {y}) - 属性: 血量{hp}, 攻击{atk}, 速度{speed}, 护甲{armor}",
            x=demon_x, y=demon_y, hp=little_demon.max_health, atk=little_demon.attack,
            speed=little_demon.speed, armor=little_demon.armor)

        # 记录巢穴状态变化
        game_logger.info(
            "🔮 恶魔巢穴状态更新: 召唤完成, 已锁定, 绑定怪物={bound}, 临时金币已清空",
            bound=self.bound_monster is not None)

        # 注意：小恶魔将通过建筑管理器的召唤完成事件处理添加到游戏世界

    def on_bound_monster_died(self):
        """当绑定的怪物死亡时调用"""
        self.bound_monster = None
        self.is_locked = False
        self.temp_gold = 0

    def add_temp_gold(self, amount: int) -> bool:
        """添加临时金币"""
        if self.is_locked or self.is_summoning or self.is_summoning_paused:
            return False

        self.temp_gold = min(self.temp_gold + amount, self.max_temp_gold)
        return True

    def can_accept_gold(self) -> bool:
        """检查是否可以接受金币"""
        return not self.is_locked and not self.is_summoning and not self.is_summoning_paused and self.temp_gold < self.max_temp_gold

    def accept_gold_deposit(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币存储（永久存储）- 恶魔巢穴不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '恶魔巢穴不支持金币存储功能'
        }

    def accept_gold_investment(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的金币投入（临时存储，用于召唤怪物）- 恶魔巢穴重写"""
        if self.is_locked:
            return {
                'deposited': False,
                'reason': 'locked',
                'message': '恶魔巢穴已锁定，无法接受金币'
            }

        if self.is_summoning:
            return {
                'deposited': False,
                'reason': 'summoning',
                'message': '恶魔巢穴正在召唤中，无法接受金币'
            }

        if self.temp_gold >= self.max_temp_gold:
            return {
                'deposited': False,
                'reason': 'already_full',
                'message': '恶魔巢穴临时金币已满'
            }

        # 计算可以存储的金币数量
        available_space = self.max_temp_gold - self.temp_gold
        actual_gold_stored = min(gold_amount, available_space)

        # 存储临时金币
        self.temp_gold += actual_gold_stored

        return {
            'deposited': True,
            'amount_deposited': actual_gold_stored,
            'new_temp_gold': self.temp_gold,
            'max_temp_gold': self.max_temp_gold,
            'message': f'恶魔巢穴投入了 {actual_gold_stored} 金币用于召唤怪物 (当前: {self.temp_gold}/{self.max_temp_gold})'
        }

    def accept_ammunition_reload(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """接受工程师的弹药装填 - 恶魔巢穴不支持"""
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': '恶魔巢穴不支持弹药装填功能'
        }

    def get_status(self) -> str:
        """获取建筑状态"""
        if self.is_summoning:
            return GameConstants.BUILDING_STATUS_SUMMONING
        elif self.bound_monster:
            return GameConstants.BUILDING_STATUS_LOCKED
        elif self.temp_gold >= self.max_temp_gold:
            return GameConstants.BUILDING_STATUS_READY_TO_SUMMON
        elif self.temp_gold > 0:
            return GameConstants.BUILDING_STATUS_ACCEPTING_GOLD
        else:
            return GameConstants.BUILDING_STATUS_COMPLETED

    def get_status_for_indicator(self) -> str:
        """
        获取恶魔巢穴状态用于状态指示器

        Returns:
            str: 状态名称
        """
        from src.core.constants import GameConstants

        # 如果建筑未完成，返回未完成状态
        if self.status != BuildingStatus.COMPLETED:
            return GameConstants.BUILDING_STATUS_INCOMPLETE

        # 如果建筑被摧毁，返回摧毁状态
        if self.status == BuildingStatus.DESTROYED:
            return GameConstants.BUILDING_STATUS_DESTROYED

        # 如果建筑需要修复（生命值不满）
        if self.health < self.max_health:
            return GameConstants.BUILDING_STATUS_NEEDS_REPAIR

        # 恶魔巢穴特殊状态
        if self.is_summoning:
            return GameConstants.BUILDING_STATUS_SUMMONING
        elif self.is_summoning_paused:
            return GameConstants.BUILDING_STATUS_SUMMONING_PAUSED
        elif self.bound_monster:
            return GameConstants.BUILDING_STATUS_LOCKED
        elif self.temp_gold >= self.max_temp_gold:
            return GameConstants.BUILDING_STATUS_READY_TO_SUMMON
        elif self.temp_gold > 0:
            return GameConstants.BUILDING_STATUS_ACCEPTING_GOLD
        else:
            return GameConstants.BUILDING_STATUS_COMPLETED
