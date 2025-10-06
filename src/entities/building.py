#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑系统 - 基类和各种建筑类型
根据 BUILDING_SYSTEM.md 文档实现
"""

import time
import math
import random
import pygame
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from src.core.constants import GameConstants
from src.core.enums import TileType
from .tile import GameTile
from src.utils.logger import game_logger


class BuildingType(Enum):
    """建筑类型枚举"""
    # 基础设施建筑
    DUNGEON_HEART = "dungeon_heart"      # 地牢之心
    TREASURY = "treasury"                # 金库
    ORC_LAIR = "orc_lair"                # 兽人巢穴
    DEMON_LAIR = "demon_lair"            # 恶魔巢穴

    # 功能性建筑
    TRAINING_ROOM = "training_room"      # 训练室
    LIBRARY = "library"                  # 图书馆
    WORKSHOP = "workshop"                # 工坊

    # 军事建筑
    PRISON = "prison"                    # 监狱
    TORTURE_CHAMBER = "torture_chamber"  # 刑房
    ARROW_TOWER = "arrow_tower"          # 箭塔
    ARCANE_TOWER = "arcane_tower"        # 奥术塔
    DEFENSE_FORTIFICATION = "defense_fortification"  # 防御工事

    # 魔法建筑
    MAGIC_ALTAR = "magic_altar"          # 魔法祭坛
    SHADOW_TEMPLE = "shadow_temple"      # 暗影神殿
    MAGIC_RESEARCH_INSTITUTE = "magic_research_institute"  # 魔法研究院


class BuildingCategory(Enum):
    """建筑分类"""
    INFRASTRUCTURE = "infrastructure"    # 基础设施
    FUNCTIONAL = "functional"           # 功能性
    MILITARY = "military"               # 军事
    MAGICAL = "magical"                 # 魔法


class BuildingStatus(Enum):
    """建筑状态"""
    PLANNING = "planning"               # 规划阶段
    UNDER_CONSTRUCTION = "under_construction"  # 建造中
    COMPLETED = "completed"             # 已完成
    UPGRADING = "upgrading"             # 升级中
    DESTROYED = "destroyed"             # 摧毁


@dataclass
class BuildingConfig:
    """建筑配置数据"""
    name: str                          # 建筑名称
    building_type: BuildingType        # 建筑类型
    category: BuildingCategory         # 建筑分类
    cost_gold: int                     # 金币成本
    cost_crystal: int = 0              # 水晶成本
    build_time: float = 60.0           # 建造时间（秒）
    engineer_requirement: int = 1       # 工程师需求
    health: int = 200                  # 生命值
    armor: int = 5                     # 护甲值
    size: Tuple[int, int] = (1, 1)     # 占地面积（瓦片）
    color: Tuple[int, int, int] = (128, 128, 128)  # 颜色
    level: int = 1                     # 建筑等级（星级）
    special_abilities: List[str] = None  # 特殊能力
    description: str = ""              # 描述


class Building(GameTile):
    """建筑基类 - 继承自GameTile"""

    def __init__(self, x: int, y: int, building_type: BuildingType, config: BuildingConfig):
        """
        初始化建筑

        Args:
            x, y: 瓦片坐标
            building_type: 建筑类型
            config: 建筑配置
        """
        # 调用父类构造函数
        super().__init__(x, y, TileType.ROOM)

        self.building_type = building_type
        self.config = config

        # 坐标系统：区分瓦片坐标和像素坐标
        self.tile_x = x  # 瓦片坐标
        self.tile_y = y  # 瓦片坐标
        self.x = x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2  # 像素坐标（瓦片中心）
        self.y = y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2  # 像素坐标（瓦片中心）

        # 基础属性
        self.name = config.name
        self.category = config.category
        self.health = config.health
        self.max_health = config.health
        self.armor = config.armor
        # 建筑的size用于物理碰撞和击退，取最大边长作为单个数值
        self.size = max(config.size) if isinstance(
            config.size, (tuple, list)) else config.size
        self.building_size = config.size  # 保留原始的建筑占地面积
        self.color = config.color
        self.level = config.level

        # 状态管理
        self.status = BuildingStatus.PLANNING
        self.construction_progress = 0.0  # 建造进度 (0.0 - 1.0)
        self.construction_start_time = 0.0
        self.last_update_time = time.time()

        # 建造成本信息（供工程师参考）
        self.construction_cost_gold = config.cost_gold
        self.construction_cost_crystal = config.cost_crystal
        self.construction_cost_paid = 0  # 已支付的金币数量

        # 建造时间信息
        self.build_time = config.build_time

        # 工程师管理
        self.assigned_engineers = []       # 分配的工程师列表
        self.working_engineer = []        # 正在工作的工程师列表
        self.required_engineers = config.engineer_requirement

        # 功能状态
        self.is_active = False            # 是否激活
        self.efficiency = 1.0             # 效率倍数
        self.last_production_time = 0.0   # 上次生产时间

        # 升级系统
        self.upgrade_level = 1
        self.max_upgrade_level = 3
        self.upgrade_costs = self._calculate_upgrade_costs()

        # 特殊能力
        self.special_abilities = config.special_abilities or []
        self.ability_cooldowns = {}

        # 维护系统 - 取消维持费用，改为修复费用
        self.maintenance_cost = 0  # 取消维持费用
        self.last_maintenance_time = time.time()

        # 建筑管理器引用（用于清理缓存等操作）
        self.building_manager = None

        # 阵营系统 - 建筑默认属于英雄阵营
        self.faction = "heroes"  # 建筑属于英雄阵营
        self.is_combat_unit = False  # 建筑不是战斗单位（除了防御塔）

    def get_tile_position(self) -> Tuple[int, int]:
        """获取瓦片坐标"""
        return (self.tile_x, self.tile_y)

    def get_pixel_position(self) -> Tuple[int, int]:
        """获取像素坐标"""
        return (self.x, self.y)

    def set_tile_position(self, tile_x: int, tile_y: int):
        """设置瓦片坐标并更新像素坐标"""
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.x = tile_x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        self.y = tile_y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

    def update(self, delta_time: float, game_state, engineers: List = None, workers: List = None) -> Dict[str, Any]:
        """
        更新建筑状态

        Args:
            delta_time: 时间增量（毫秒）
            game_state: 游戏状态
            engineers: 可用工程师列表
            workers: 可用工人列表

        Returns:
            Dict: 更新结果信息
        """
        current_time = time.time()
        delta_seconds = delta_time  # delta_time 已经是秒单位，不需要转换

        result = {
            'status_changed': False,
            'production': {},
            'events': []
        }

        # 更新建造进度
        if self.status == BuildingStatus.UNDER_CONSTRUCTION:
            self._update_construction(delta_seconds, result)

        # 更新升级进度
        elif self.status == BuildingStatus.UPGRADING:
            self._update_upgrade(delta_seconds, result)

        # 更新正常运营
        elif self.status == BuildingStatus.COMPLETED and self.is_active:
            production = self._update_production(
                delta_seconds, game_state, workers)
            if production:
                result['production'] = production

        # 更新维护成本
        self._update_maintenance(delta_seconds, game_state, result)

        # 更新特殊能力冷却
        self._update_ability_cooldowns(delta_seconds)

        self.last_update_time = current_time
        return result

    def start_construction(self, engineers: List = None) -> bool:
        """
        开始建造

        Args:
            engineers: 分配的工程师列表

        Returns:
            bool: 是否成功开始建造
        """
        if self.status != BuildingStatus.PLANNING:
            return False

        # 分配工程师
        if engineers and len(engineers) >= self.required_engineers:
            self.assigned_engineers = engineers[:self.required_engineers]

        self.status = BuildingStatus.UNDER_CONSTRUCTION
        self.construction_start_time = time.time()
        self.construction_progress = 0.0

        return True

    def complete_construction(self) -> Dict[str, Any]:
        """
        完成建造

        Returns:
            Dict: 完成信息
        """
        self.status = BuildingStatus.COMPLETED
        self.is_active = True
        self.construction_progress = 1.0

        # 释放工程师
        engineers_released = len(self.assigned_engineers)
        self.assigned_engineers.clear()

        # 记录建筑完成日志
        from src.utils.logger import game_logger
        game_logger.info(f"🏗️ 建筑 {self.name} 建造完成！")
        game_logger.info(f"   📍 位置: ({self.x}, {self.y})")
        game_logger.info(f"   🏷️ 类型: {self.building_type.value}")
        game_logger.info(f"   💚 血量: {self.health}/{self.max_health}")
        game_logger.info(f"   🔓 释放工程师: {engineers_released} 个")

        return {
            'completed': True,
            'engineers_released': engineers_released,
            'building_type': self.building_type.value,
            'name': self.name
        }

    def upgrade(self, engineers: List = None) -> bool:
        """
        升级建筑

        Args:
            engineers: 分配的工程师列表

        Returns:
            bool: 是否成功开始升级
        """
        if (self.status != BuildingStatus.COMPLETED or
                self.upgrade_level >= self.max_upgrade_level):
            return False

        # 检查升级成本
        upgrade_cost = self.upgrade_costs.get(self.upgrade_level + 1, {})
        # 这里应该检查资源是否足够，但需要游戏状态参数

        self.status = BuildingStatus.UPGRADING
        self.construction_start_time = time.time()
        self.construction_progress = 0.0

        if engineers:
            self.assigned_engineers = engineers[:self.required_engineers]

        return True

    def _calculate_armor_reduction(self, damage: int) -> int:
        """
        统一的护甲减免计算API

        使用线性护甲减免公式：
        实际伤害 = max(1, 原始伤害 - 护甲值)

        Args:
            damage: 原始伤害值

        Returns:
            int: 应用护甲减免后的实际伤害
        """
        if not hasattr(self, 'armor') or self.armor <= 0:
            return damage

        # 线性护甲减免：每点护甲减少1点伤害
        actual_damage = max(1, damage - self.armor)
        return actual_damage

    def take_damage(self, damage: int) -> Dict[str, Any]:
        """
        受到伤害

        Args:
            damage: 伤害值

        Returns:
            Dict: 伤害结果
        """
        game_logger.info(f"🏗️ 建筑 {self.name} 受到 {damage} 点伤害")
        game_logger.info(
            f"🏗️ 当前状态: {self.status.value}, 生命值: {self.health}/{self.max_health}")
        game_logger.info(f"🏗️ 护甲值: {self.armor}")

        # 使用统一的护甲减免计算
        actual_damage = self._calculate_armor_reduction(damage)
        game_logger.info(f"🏗️ 护甲减免后实际伤害: {actual_damage}")

        old_health = self.health
        self.health -= actual_damage
        self.health = max(0, self.health)  # 确保生命值不为负数

        result = {
            'damage_taken': actual_damage,
            'health_remaining': self.health,
            'destroyed': False
        }

        game_logger.info(f"🏗️ 伤害后生命值: {old_health} -> {self.health}")

        if self.health <= 0:
            self.health = 0
            self.status = BuildingStatus.DESTROYED
            self.is_active = False
            result['destroyed'] = True
            game_logger.info(f"💀 建筑 {self.name} 被摧毁！")

        game_logger.info(f"🏗️ 返回结果: {result}")
        return result

    def repair(self, gold_amount: int, engineer_gold: int = 0) -> Dict[str, Any]:
        """
        修理建筑 - 由工程师携带金币进行修复

        Args:
            gold_amount: 工程师投入的金币数量
            engineer_gold: 工程师携带的总金币数量

        Returns:
            Dict: 修理结果
        """
        if self.status == BuildingStatus.DESTROYED:
            return {'repaired': False, 'reason': 'building_destroyed'}

        if gold_amount <= 0:
            return {'repaired': False, 'reason': 'invalid_amount', 'message': '投入金币数量必须大于0'}

        # 计算修复费用：每点生命值修复需要花费0.2金币
        repair_cost_per_hp = 0.2  # 固定每点生命值0.2金币

        # 根据金币数量计算可以修复的生命值
        hp_to_repair = int(gold_amount / repair_cost_per_hp)
        hp_needed = self.max_health - self.health

        # 实际修复的生命值不能超过需要的生命值
        actual_hp_to_repair = min(hp_to_repair, hp_needed)

        # 计算实际需要的金币
        actual_repair_cost = int(actual_hp_to_repair * repair_cost_per_hp)

        # 检查工程师是否有足够的金币
        if engineer_gold < actual_repair_cost:
            return {
                'repaired': False,
                'reason': 'insufficient_gold',
                'required_gold': actual_repair_cost,
                'available_gold': engineer_gold
            }

        # 执行修复
        old_health = self.health
        self.health = min(self.max_health, self.health + actual_hp_to_repair)
        actual_repair = self.health - old_health

        # 检查是否修复完成
        if self.health >= self.max_health:
            self.status = BuildingStatus.COMPLETED
            self.efficiency = 1.0

        return {
            'repaired': True,
            'repair_amount': actual_repair,
            'repair_cost': actual_repair_cost,
            'health': self.health,
            'max_health': self.max_health,
            'message': f'修复了 {actual_repair} 点生命值，花费 {actual_repair_cost} 金币'
        }

    def activate_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """
        激活特殊能力

        Args:
            ability_name: 能力名称
            target: 目标（如果需要）

        Returns:
            Dict: 激活结果
        """
        if (ability_name not in self.special_abilities or
                ability_name in self.ability_cooldowns):
            return {'activated': False, 'reason': 'unavailable_or_cooldown'}

        # 这里应该实现具体的能力效果
        # 不同建筑有不同的特殊能力
        result = self._execute_special_ability(ability_name, target)

        # 设置冷却时间
        if result.get('activated', False):
            cooldown_time = result.get('cooldown', 60.0)  # 默认60秒冷却
            self.ability_cooldowns[ability_name] = cooldown_time

        return result

    def pay_construction_cost(self, gold_amount: int) -> Dict[str, Any]:
        """
        工程师支付建造成本

        Args:
            gold_amount: 支付的金币数量

        Returns:
            Dict: 支付结果
        """
        if self.status != BuildingStatus.PLANNING and self.status != BuildingStatus.UNDER_CONSTRUCTION:
            return {
                'paid': False,
                'reason': 'invalid_status',
                'message': '建筑状态不允许支付成本'
            }

        # 计算还需要支付的金币
        remaining_cost = self.construction_cost_gold - self.construction_cost_paid
        if remaining_cost <= 0:
            return {
                'paid': False,
                'reason': 'already_paid',
                'message': '建造成本已完全支付'
            }

        # 计算实际支付金额
        actual_payment = min(gold_amount, remaining_cost)
        self.construction_cost_paid += actual_payment

        # 检查是否完全支付
        is_fully_paid = self.construction_cost_paid >= self.construction_cost_gold

        return {
            'paid': True,
            'amount_paid': actual_payment,
            'total_paid': self.construction_cost_paid,
            'remaining_cost': self.construction_cost_gold - self.construction_cost_paid,
            'is_fully_paid': is_fully_paid,
            'message': f'支付了 {actual_payment} 金币，剩余 {self.construction_cost_gold - self.construction_cost_paid} 金币'
        }

    def reject_engineer(self, engineer, reason: str = "建筑拒绝工程师") -> Dict[str, Any]:
        """
        建筑主动拒绝工程师进行建造

        Args:
            engineer: 被拒绝的工程师
            reason: 拒绝原因

        Returns:
            Dict: 拒绝结果
        """
        result = {
            'rejected': True,
            'reason': reason,
            'engineer_name': engineer.name if hasattr(engineer, 'name') else 'Unknown',
            'building_name': self.name,
            'status_changed': False,
            'actions_taken': []
        }

        # 如果工程师的目标建筑是当前建筑，清除其目标
        if hasattr(engineer, 'target_building') and engineer.target_building == self:
            engineer.target_building = None
            result['status_changed'] = True
            result['actions_taken'].append('cleared_target_building')

        # 如果工程师在相关状态，将其状态改为空闲
        if hasattr(engineer, 'status'):
            from src.entities.monster.goblin_engineer import EngineerStatus
            old_status = engineer.status
            if engineer.status in [
                EngineerStatus.MOVING_TO_SITE,
                EngineerStatus.FETCHING_RESOURCES,
                EngineerStatus.CONSTRUCTING,
                EngineerStatus.REPAIRING,
                EngineerStatus.UPGRADING
            ]:
                engineer.status = EngineerStatus.IDLE
                result['status_changed'] = True
                result['actions_taken'].append(
                    f'status_changed_from_{old_status.value}_to_idle')

        # 如果工程师在分配列表中，移除它
        if engineer in self.assigned_engineers:
            self.assigned_engineers.remove(engineer)
            result['status_changed'] = True
            result['actions_taken'].append('removed_from_assigned_engineers')

        # 清理工程师的工作进度（如果有的话）
        if hasattr(engineer, 'work_progress'):
            engineer.work_progress = 0.0
            result['actions_taken'].append('cleared_work_progress')

        # 清理工程师的建造目标位置（如果有的话）
        if hasattr(engineer, 'target_position'):
            engineer.target_position = None
            result['actions_taken'].append('cleared_target_position')

        # 清理建筑锁定缓存（如果存在建筑管理器）
        if hasattr(self, 'building_manager') and self.building_manager:
            self.building_manager.clear_building_lock_cache()
            result['cache_cleared'] = True
            result['actions_taken'].append('cleared_building_lock_cache')

        # 如果建筑正在建造中且没有工程师了，暂停建造
        if (self.status == BuildingStatus.UNDER_CONSTRUCTION and
                len(self.assigned_engineers) == 0):
            self.status = BuildingStatus.PLANNING
            result['status_changed'] = True
            result['actions_taken'].append('paused_construction')

        # 记录拒绝事件
        if hasattr(engineer, 'rejection_history'):
            if not hasattr(engineer, 'rejection_history'):
                engineer.rejection_history = []
            engineer.rejection_history.append({
                'building_name': self.name,
                'reason': reason,
                'timestamp': time.time()
            })

        return result

    def get_rejection_reasons(self) -> List[str]:
        """
        获取建筑可能拒绝工程师的所有原因

        Returns:
            List[str]: 拒绝原因列表
        """
        reasons = []

        if self.status == BuildingStatus.DESTROYED:
            reasons.append("建筑已被摧毁")
        elif self.status == BuildingStatus.COMPLETED:
            reasons.append("建筑已完成，无需建造")
        elif len(self.assigned_engineers) >= self.required_engineers:
            reasons.append(
                f"建筑已有足够的工程师 ({len(self.assigned_engineers)}/{self.required_engineers})")
        elif self.status == BuildingStatus.UPGRADING:
            reasons.append("建筑正在升级中")
        elif self.status == BuildingStatus.UNDER_CONSTRUCTION:
            if self.construction_cost_paid < self.construction_cost_gold:
                reasons.append(
                    f"建造成本未完全支付 ({self.construction_cost_paid}/{self.construction_cost_gold})")

        return reasons

    def process_engineer_list(self, engineers: List, reason_prefix: str = "建筑工程师列表处理") -> Dict[str, Any]:
        """
        处理工程师列表，执行拒绝逻辑

        Args:
            engineers: 工程师列表
            reason_prefix: 拒绝原因前缀

        Returns:
            Dict: 处理结果
        """
        result = {
            'processed': True,
            'total_engineers': len(engineers),
            'kept_engineers': [],
            'rejected_engineers': [],
            'actions_taken': [],
            'status_changed': False
        }

        if not engineers:
            result['message'] = '工程师列表为空'
            return result

        if len(engineers) > self.required_engineers:
            result['actions_taken'].append(
                f'工程师数量超过需求({len(engineers)}/{self.required_engineers})，拒绝多余的工程师')

            # 保留前required_engineers个工程师
            for i in range(min(self.required_engineers, len(engineers))):
                engineer = engineers[i]
                result['kept_engineers'].append({
                    'engineer_name': engineer.name if hasattr(engineer, 'name') else 'Unknown',
                    'index': i,
                    'reason': f'保留第{i + 1}个工程师（符合需求数量）'
                })

            # 拒绝多余的工程师
            for i in range(self.required_engineers, len(engineers)):
                engineer = engineers[i]
                reject_reason = f"{reason_prefix} - 工程师数量超过需求，拒绝第{i + 1}个工程师"
                reject_result = self.reject_engineer(engineer, reject_reason)

                result['rejected_engineers'].append({
                    'engineer_name': engineer.name if hasattr(engineer, 'name') else 'Unknown',
                    'index': i,
                    'reject_result': reject_result,
                    'reason': reject_reason
                })

                if reject_result.get('status_changed', False):
                    result['status_changed'] = True
        else:
            # 工程师数量符合要求，全部保留
            for i, engineer in enumerate(engineers):
                result['kept_engineers'].append({
                    'engineer_name': engineer.name if hasattr(engineer, 'name') else 'Unknown',
                    'index': i,
                    'reason': '工程师数量符合要求'
                })

        result['message'] = f"处理完成：保留{len(result['kept_engineers'])}个工程师，拒绝{len(result['rejected_engineers'])}个工程师"
        return result

    def auto_reject_excess_engineers(self, reason: str = "建筑自动拒绝多余工程师") -> Dict[str, Any]:
        """
        自动拒绝多余的工程师（基于当前分配的工程师列表）

        Args:
            reason: 拒绝原因

        Returns:
            Dict: 处理结果
        """
        if len(self.working_engineer) <= self.required_engineers:
            return {
                'processed': False,
                'message': f'当前工程师数量({len(self.working_engineer)})',
                'total_engineers': len(self.working_engineer),
                'kept_engineers': len(self.working_engineer),
                'rejected_engineers': 0
            }

        # 使用当前分配的工程师列表进行处理
        return self.process_engineer_list(self.working_engineer, reason)

    def can_accept_engineer(self, engineer) -> Dict[str, Any]:
        """
        检查建筑是否可以接受工程师

        Args:
            engineer: 要检查的工程师

        Returns:
            Dict: 检查结果
        """
        result = {
            'can_accept': True,
            'reason': '',
            'suggestions': []
        }

        # 检查建筑状态
        if self.status == BuildingStatus.DESTROYED:
            result['can_accept'] = False
            result['reason'] = '建筑已被摧毁'
            return result

        if self.status == BuildingStatus.COMPLETED:
            result['can_accept'] = False
            result['reason'] = '建筑已完成，无需建造'
            return result

        # 检查是否已有足够的工程师
        if len(self.assigned_engineers) >= self.required_engineers:
            result['can_accept'] = False
            result['reason'] = f'建筑已有足够的工程师 ({len(self.assigned_engineers)}/{self.required_engineers})'
            return result

        # 检查工程师是否已经在分配列表中
        if engineer in self.assigned_engineers:
            result['can_accept'] = False
            result['reason'] = '工程师已被分配到此建筑'
            return result

        # 检查建筑是否正在被其他工程师工作
        if hasattr(self, 'building_manager') and self.building_manager:
            if self.building_manager._is_building_being_worked_on(self):
                result['can_accept'] = False
                result['reason'] = '建筑正在被其他工程师工作'
                return result

        return result

    def set_building_manager(self, building_manager):
        """
        设置建筑管理器引用

        Args:
            building_manager: 建筑管理器实例
        """
        self.building_manager = building_manager

    def get_status_for_indicator(self) -> str:
        """
        获取建筑状态用于状态指示器

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

        # 如果建筑完成且正常
        return GameConstants.BUILDING_STATUS_COMPLETED

    def get_status(self) -> str:
        """
        获取建筑状态

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

        # 如果建筑完成且正常
        return GameConstants.BUILDING_STATUS_COMPLETED

    def get_engineer_task_type(self) -> str:
        """
        获取工程师任务类型

        Returns:
            str: 任务类型 ('construction', 'repair', 'reload', 'gold_deposit', 'idle')
        """
        # 如果建筑未完成，需要建造
        if self.status in [BuildingStatus.PLANNING, BuildingStatus.UNDER_CONSTRUCTION]:
            return 'construction'
        elif self.status == BuildingStatus.COMPLETED:
            # 已完成的建筑，优先检查是否需要弹药装填
            if (hasattr(self, 'can_accept_ammunition') and self.can_accept_ammunition()):
                return 'reload'
            # 其次检查是否需要金币存入
            elif (hasattr(self, 'can_accept_gold') and self.can_accept_gold()):
                return 'gold_deposit'
            # 再次检查是否需要修复（生命值不满）
            elif self.health < self.max_health:
                return 'repair'
            else:
                return 'idle'  # 已完成且不需要任何维护的建筑
        else:
            return 'construction'  # 默认为建造

    def accept_gold_deposit(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """
        接受工程师的金币存储（永久存储）

        Args:
            engineer: 工程师对象
            gold_amount: 金币数量

        Returns:
            Dict: 存储结果
        """
        # 默认实现：不支持金币存储
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': f'{self.name} 不支持金币存储功能'
        }

    def accept_gold_investment(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """
        接受工程师的金币投入（临时存储，用于触发功能）

        Args:
            engineer: 工程师对象
            gold_amount: 金币数量

        Returns:
            Dict: 投入结果
        """
        # 默认实现：不支持金币投入
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': f'{self.name} 不支持金币投入功能'
        }

    def accept_ammunition_reload(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """
        接受工程师的弹药装填

        Args:
            engineer: 工程师对象
            gold_amount: 金币数量

        Returns:
            Dict: 装填结果
        """
        # 默认实现：不支持弹药装填
        return {
            'deposited': False,
            'reason': 'not_supported',
            'message': f'{self.name} 不支持弹药装填功能'
        }

    def accept_repair_gold(self, engineer, gold_amount: int) -> Dict[str, Any]:
        """
        接受工程师的修复金币投入 - 通用实现

        Args:
            engineer: 工程师对象
            gold_amount: 金币数量

        Returns:
            Dict: 修复投入结果
        """
        if self.health >= self.max_health:
            return {
                'deposited': False,
                'reason': 'already_full_health',
                'message': f'{self.name}生命值已满，无需修复'
            }

        # 计算修复需要的金币（1金币回复5血量）
        health_to_repair = gold_amount * 5
        max_repair = self.max_health - self.health
        actual_repair = min(health_to_repair, max_repair)
        actual_cost = int(actual_repair / 5)

        if actual_repair > 0:
            self.health += actual_repair
            return {
                'deposited': True,
                'amount_deposited': actual_cost,
                'health_repaired': actual_repair,
                'current_health': self.health,
                'max_health': self.max_health,
                'message': f'修复了 {actual_repair} 点生命值 (当前: {self.health}/{self.max_health})'
            }
        else:
            return {
                'deposited': False,
                'reason': 'no_repair_needed',
                'message': f'{self.name}生命值已满，无需修复'
            }

    def _get_attack_effect_type(self) -> str:
        # 建筑攻击特效映射
        building_attack_effects = {
            'arrow_tower': 'tower_arrow_shot',
            'arcane_tower': 'tower_magic_impact',
            'dungeon_heart': 'impact_explosion',
            'treasury': 'impact_explosion',
            'magic_altar': 'magic_impact',
            'orc_lair': 'impact_explosion',
            'demon_lair': 'magic_impact'
        }
        return building_attack_effects.get(self.building_type.value, 'impact_explosion')

    def get_info(self) -> Dict[str, Any]:
        """
        获取建筑信息

        Returns:
            Dict: 建筑详细信息
        """
        return {
            'name': self.name,
            'type': self.building_type.value,
            'category': self.category.value,
            'position': (self.x, self.y),
            'size': self.size,
            'status': self.status.value,
            'health': self.health,
            'max_health': self.max_health,
            'armor': self.armor,
            'level': self.level,
            'upgrade_level': self.upgrade_level,
            'construction_progress': self.construction_progress,
            'is_active': self.is_active,
            'efficiency': self.efficiency,
            'assigned_engineers': len(self.assigned_engineers),
            'required_engineers': self.required_engineers,
            'special_abilities': self.special_abilities,
            'ability_cooldowns': dict(self.ability_cooldowns),
            'construction_cost_gold': self.construction_cost_gold,
            'construction_cost_paid': self.construction_cost_paid,
            'construction_cost_remaining': self.construction_cost_gold - self.construction_cost_paid
        }

    def _update_construction(self, delta_seconds: float, result: Dict[str, Any]):
        """更新建造进度"""
        if not self.assigned_engineers:
            return

        # 检查是否完全支付了建造成本
        if self.construction_cost_paid < self.construction_cost_gold:
            # 成本未完全支付，不能开始建造
            return

        # 计算建造速度（基于工程师效率）
        total_efficiency = sum(getattr(eng, 'build_efficiency', 1.0)
                               for eng in self.assigned_engineers)
        build_speed = total_efficiency / self.config.build_time

        # 更新进度
        old_progress = self.construction_progress
        self.construction_progress += build_speed * delta_seconds

        if self.construction_progress >= 1.0:
            self.construction_progress = 1.0
            completion_result = self.complete_construction()
            result.update(completion_result)
            result['status_changed'] = True
            result['events'].append(f"{self.name} 建造完成！")

    def _update_upgrade(self, delta_seconds: float, result: Dict[str, Any]):
        """更新升级进度"""
        if not self.assigned_engineers:
            return

        # 升级时间通常是建造时间的一半
        upgrade_time = self.config.build_time * 0.5
        total_efficiency = sum(getattr(eng, 'build_efficiency', 1.0)
                               for eng in self.assigned_engineers)
        upgrade_speed = total_efficiency / upgrade_time

        old_progress = self.construction_progress
        self.construction_progress += upgrade_speed * delta_seconds

        if self.construction_progress >= 1.0:
            self.construction_progress = 1.0
            self._complete_upgrade()
            result['status_changed'] = True
            result['events'].append(f"{self.name} 升级到 {self.upgrade_level} 级！")

    def _update_production(self, delta_seconds: float, game_state, workers: List = None) -> Dict[str, Any]:
        """更新生产（由子类重写）"""
        return {}

    def _update_maintenance(self, delta_seconds: float, game_state, result: Dict[str, Any]):
        """更新维护成本 - 已取消维持费用"""
        # 取消维持费用，建筑不再需要持续消耗金币
        # 修复费用将在修复时单独计算
        pass

    def can_accept_gold(self) -> bool:
        """
        检查建筑是否可以接受金币

        Returns:
            bool: 是否可以接受金币
        """
        # 检查建筑是否支持金币存入
        return hasattr(self, 'deposit_gold') and callable(getattr(self, 'deposit_gold'))

    def get_gold_capacity_info(self) -> Dict[str, Any]:
        """
        获取建筑的金币容量信息

        Returns:
            Dict: 容量信息
        """
        if hasattr(self, 'gold_storage_capacity'):
            return {
                'has_capacity': True,
                'capacity': self.gold_storage_capacity,
                'stored': getattr(self, 'stored_gold', 0),
                'available': self.gold_storage_capacity - getattr(self, 'stored_gold', 0)
            }
        else:
            return {
                'has_capacity': False,
                'message': f'{self.name} 没有金币存储容量'
            }

    def _update_ability_cooldowns(self, delta_seconds: float):
        """更新特殊能力冷却时间"""
        expired_abilities = []
        for ability, remaining_time in self.ability_cooldowns.items():
            remaining_time -= delta_seconds
            if remaining_time <= 0:
                expired_abilities.append(ability)
            else:
                self.ability_cooldowns[ability] = remaining_time

        # 移除已冷却完成的能力
        for ability in expired_abilities:
            del self.ability_cooldowns[ability]

    def attack_target(self, target) -> Dict[str, Any]:
        """攻击目标（由子类重写）"""
        return {}

    def can_attack_target(self, target) -> bool:
        return False

    def _complete_upgrade(self):
        """完成升级"""
        self.upgrade_level += 1
        self.status = BuildingStatus.COMPLETED
        self.construction_progress = 0.0

        # 释放工程师
        self.assigned_engineers.clear()

        # 提升建筑属性
        self._apply_upgrade_bonuses()

    def _apply_upgrade_bonuses(self):
        """应用升级加成"""
        # 每级升级增加20%生命值和10%效率
        bonus_multiplier = 1 + (self.upgrade_level - 1) * 0.2
        self.max_health = int(self.config.health * bonus_multiplier)
        self.health = self.max_health  # 升级时恢复满血
        self.efficiency = min(2.0, 1.0 + (self.upgrade_level - 1) * 0.1)

    def _calculate_upgrade_costs(self) -> Dict[int, Dict[str, int]]:
        """计算升级成本"""
        base_gold = self.config.cost_gold
        base_crystal = self.config.cost_crystal

        costs = {}
        for level in range(2, self.max_upgrade_level + 1):
            multiplier = level * 1.5
            costs[level] = {
                'gold': int(base_gold * multiplier),
                'crystal': int(base_crystal * multiplier)
            }

        return costs

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力（由子类重写）"""
        return {'activated': False, 'reason': 'not_implemented'}

    def render(self, screen: pygame.Surface, screen_x: int, screen_y: int, tile_size: int, font_manager=None, building_ui=None, ui_scale: float = 1.0):
        """
        渲染建筑外观 - 委托给BuildingUI处理

        Args:
            screen: pygame屏幕表面
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            font_manager: 字体管理器（可选）
            building_ui: BuildingUI实例（可选）
            ui_scale: UI缩放倍数
        """
        if building_ui:
            # 使用BuildingUI的渲染方法
            building_ui.render_building_appearance(
                screen, self.building_type.value, screen_x, screen_y, tile_size, None, ui_scale)
        else:
            # 回退到简单渲染
            self._render_simple_appearance(
                screen, screen_x, screen_y, tile_size)

    def _render_simple_appearance(self, screen: pygame.Surface, screen_x: int, screen_y: int, tile_size: int):
        """简单渲染外观 - 回退方案"""
        # 根据建筑类型获取颜色
        building_colors = {
            'treasury': (255, 215, 0),  # 金库 - 金色
            'dungeon_heart': (139, 0, 0),  # 地牢之心 - 深红色
            'arrow_tower': (169, 169, 169),  # 箭塔 - 石灰色
            'training_room': (112, 128, 144),  # 训练室 - 灰蓝色
            'library': (25, 25, 112),   # 图书馆 - 深蓝色
            'workshop': (139, 69, 19),  # 工坊 - 棕色
            'prison': (105, 105, 105),  # 监狱 - 深灰色
            'torture_chamber': (139, 0, 0),  # 刑房 - 深红色
            'defense_fortification': (169, 169, 169),  # 防御工事 - 灰色
            'magic_altar': (138, 43, 226),  # 魔法祭坛 - 紫色
            'shadow_temple': (72, 61, 139),  # 暗影神殿 - 暗紫色
            'magic_research_institute': (65, 105, 225),  # 魔法研究院 - 蓝色
        }

        color = building_colors.get(
            self.building_type.value, (128, 128, 128))  # 默认灰色

        # 绘制建筑
        building_rect = pygame.Rect(
            screen_x + 1, screen_y + 1, tile_size - 2, tile_size - 2)
        pygame.draw.rect(screen, color, building_rect)

        # 绘制边框
        border_rect = pygame.Rect(screen_x, screen_y, tile_size, tile_size)
        pygame.draw.rect(screen, (50, 50, 50), border_rect, 1)

    def render_health_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int, tile_size: int, font_manager=None, building_ui=None, ui_scale: float = 1.0):
        """
        渲染建筑生命条 - 委托给BuildingUI处理

        Args:
            screen: pygame屏幕表面
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            font_manager: 字体管理器（可选）
            building_ui: BuildingUI实例（可选）
            ui_scale: UI缩放倍数
        """
        if building_ui:
            # 使用BuildingUI的生命条渲染方法
            building_ui.render_building_health_bar(
                screen, screen_x, screen_y, tile_size, None, self, ui_scale)
        else:
            # 回退到简单生命条渲染
            self._render_simple_health_bar(
                screen, screen_x, screen_y, tile_size)

    def render_status_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int, tile_size: int, font_manager=None, building_ui=None, ui_scale: float = 1.0):
        """
        渲染建筑状态条 - 委托给BuildingUI处理

        Args:
            screen: pygame屏幕表面
            screen_x: 屏幕X坐标
            screen_y: 屏幕Y坐标
            tile_size: 瓦片大小
            font_manager: 字体管理器（可选）
            building_ui: BuildingUI实例（可选）
            ui_scale: UI缩放倍数
        """
        if building_ui:
            # 使用BuildingUI的状态条渲染方法
            building_ui.render_building_status_bar(
                screen, screen_x, screen_y, tile_size, None, self, ui_scale)

    def _render_simple_health_bar(self, screen: pygame.Surface, screen_x: int, screen_y: int, tile_size: int):
        """简单生命条渲染 - 回退方案"""
        if self.max_health <= 0:
            return

        # 计算生命值比例
        health_ratio = min(self.health / self.max_health, 1.0)

        # 生命条尺寸和位置
        bar_width = tile_size - 8
        bar_height = 4
        bar_x = screen_x + 4
        bar_y = screen_y + tile_size - 8

        # 绘制背景条
        bar_bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(screen, (100, 0, 0), bar_bg_rect)  # 深红色背景
        pygame.draw.rect(screen, (150, 0, 0), bar_bg_rect, 1)  # 深红色边框

        # 绘制生命条
        if health_ratio > 0:
            bar_fill_width = int(bar_width * health_ratio)
            bar_fill_rect = pygame.Rect(
                bar_x, bar_y, bar_fill_width, bar_height)

            # 根据生命值百分比选择颜色
            if health_ratio > 0.6:
                health_color = (0, 255, 0)  # 绿色（健康）
            elif health_ratio > 0.3:
                health_color = (255, 255, 0)  # 黄色（警告）
            else:
                health_color = (255, 0, 0)  # 红色（危险）

            pygame.draw.rect(screen, health_color, bar_fill_rect)


class BuildingRegistry:
    """建筑注册表 - 管理所有建筑配置"""

    # 建筑配置数据
    BUILDING_CONFIGS = {
        # 基础设施建筑
        BuildingType.DUNGEON_HEART: BuildingConfig(
            name="地牢之心",
            building_type=BuildingType.DUNGEON_HEART,
            category=BuildingCategory.INFRASTRUCTURE,
            cost_gold=0,  # 游戏开始时自动放置
            build_time=0,
            engineer_requirement=0,
            health=1000,
            armor=10,
            size=(2, 2),  # 占地面积2x2瓦片
            color=(139, 0, 0),  # 深红色
            level=5,
            special_abilities=["resource_storage",
                               "engineer_training", "command_center"],
            description="整个地下城的心脏和指挥中心"
        ),

        BuildingType.TREASURY: BuildingConfig(
            name="金库",
            building_type=BuildingType.TREASURY,
            category=BuildingCategory.INFRASTRUCTURE,
            cost_gold=100,
            build_time=60.0,
            engineer_requirement=1,
            health=200,
            armor=5,
            color=(255, 215, 0),  # 金黄色
            level=2,
            special_abilities=["gold_storage", "gold_exchange"],
            description="提供金币存储和交换功能"
        ),


        # 功能性建筑
        BuildingType.TRAINING_ROOM: BuildingConfig(
            name="训练室",
            building_type=BuildingType.TRAINING_ROOM,
            category=BuildingCategory.FUNCTIONAL,
            cost_gold=200,
            build_time=120.0,
            engineer_requirement=1,
            health=300,
            armor=6,
            color=(112, 128, 144),  # 铁灰色
            level=3,
            special_abilities=["creature_training", "experience_boost"],
            description="提升怪物能力和获得经验"
        ),

        BuildingType.LIBRARY: BuildingConfig(
            name="图书馆",
            building_type=BuildingType.LIBRARY,
            category=BuildingCategory.FUNCTIONAL,
            cost_gold=250,
            build_time=150.0,
            engineer_requirement=1,
            health=200,
            armor=5,
            color=(25, 25, 112),  # 深蓝色
            level=3,
            special_abilities=["mana_generation",
                               "spell_research", "spell_enhancement"],
            description="提供法力生成和法术研究"
        ),

        BuildingType.WORKSHOP: BuildingConfig(
            name="工坊",
            building_type=BuildingType.WORKSHOP,
            category=BuildingCategory.FUNCTIONAL,
            cost_gold=300,
            build_time=180.0,
            engineer_requirement=2,
            health=250,
            armor=7,
            color=(139, 69, 19),  # 棕色
            level=3,
            special_abilities=["trap_creation", "equipment_crafting"],
            description="制造陷阱和装备"
        ),

        # 军事建筑
        BuildingType.PRISON: BuildingConfig(
            name="监狱",
            building_type=BuildingType.PRISON,
            category=BuildingCategory.MILITARY,
            cost_gold=200,
            build_time=100.0,
            engineer_requirement=1,
            health=350,
            armor=8,
            color=(105, 105, 105),  # 暗灰色
            level=3,
            special_abilities=["prisoner_holding", "conversion"],
            description="关押俘虏并转换为己方单位"
        ),

        BuildingType.TORTURE_CHAMBER: BuildingConfig(
            name="刑房",
            building_type=BuildingType.TORTURE_CHAMBER,
            category=BuildingCategory.MILITARY,
            cost_gold=400,
            build_time=200.0,
            engineer_requirement=2,
            health=400,
            armor=8,
            color=(139, 0, 0),  # 深红色
            level=4,
            special_abilities=["conversion_acceleration", "fear_aura"],
            description="加速转换过程并散发恐惧光环"
        ),

        BuildingType.ARROW_TOWER: BuildingConfig(
            name="箭塔",
            building_type=BuildingType.ARROW_TOWER,
            category=BuildingCategory.MILITARY,
            cost_gold=200,  # 更新为文档中的200金币
            cost_crystal=0,
            build_time=100.0,
            engineer_requirement=1,
            health=800,  # 提升到800生命值
            armor=5,  # 更新为文档中的5点护甲
            color=(211, 211, 211),  # 石灰色
            level=3,
            special_abilities=["auto_attack", "range_attack"],
            description="自动攻击入侵者的防御建筑"
        ),

        BuildingType.ARCANE_TOWER: BuildingConfig(
            name="奥术塔",
            building_type=BuildingType.ARCANE_TOWER,
            category=BuildingCategory.MILITARY,
            cost_gold=200,  # 与箭塔一致
            cost_crystal=0,
            build_time=100.0,
            engineer_requirement=1,
            health=800,  # 提升到800生命值，与箭塔一致
            armor=5,  # 与箭塔一致
            color=(138, 43, 226),  # 紫色
            level=3,
            special_abilities=["auto_attack", "magic_attack"],
            description="使用奥术魔法进行范围攻击的防御建筑"
        ),


        BuildingType.DEFENSE_FORTIFICATION: BuildingConfig(
            name="防御工事",
            building_type=BuildingType.DEFENSE_FORTIFICATION,
            category=BuildingCategory.MILITARY,
            cost_gold=180,
            build_time=80.0,
            engineer_requirement=1,
            health=500,
            armor=12,
            color=(105, 105, 105),  # 暗灰色
            level=2,
            special_abilities=["area_defense", "damage_reduction"],
            description="提供区域防御和伤害减免"
        ),

        # 魔法建筑
        BuildingType.MAGIC_ALTAR: BuildingConfig(
            name="魔法祭坛",
            building_type=BuildingType.MAGIC_ALTAR,
            category=BuildingCategory.MAGICAL,
            cost_gold=120,
            cost_crystal=0,  # 移除水晶成本
            build_time=160.0,
            engineer_requirement=1,  # 需要法师辅助
            health=250,
            armor=6,
            color=(138, 43, 226),  # 蓝紫色
            level=4,
            special_abilities=["mana_generation",
                               "spell_amplification", "gold_storage"],
            description="生成法力、增强法术威力并提供金币临时存储"
        ),

        BuildingType.SHADOW_TEMPLE: BuildingConfig(
            name="暗影神殿",
            building_type=BuildingType.SHADOW_TEMPLE,
            category=BuildingCategory.MAGICAL,
            cost_gold=800,
            cost_crystal=0,  # 移除水晶成本
            build_time=300.0,
            engineer_requirement=3,
            health=600,
            armor=15,
            color=(75, 0, 130),  # 靛青色
            level=5,
            special_abilities=["advanced_magic",
                               "shadow_summoning", "dark_rituals"],
            description="最强大的魔法建筑，可施展高级魔法"
        ),

        BuildingType.MAGIC_RESEARCH_INSTITUTE: BuildingConfig(
            name="魔法研究院",
            building_type=BuildingType.MAGIC_RESEARCH_INSTITUTE,
            category=BuildingCategory.MAGICAL,
            cost_gold=600,
            cost_crystal=0,  # 移除水晶成本
            build_time=240.0,
            engineer_requirement=2,
            health=350,
            armor=8,
            color=(72, 61, 139),  # 暗石板蓝
            level=4,
            special_abilities=["spell_research",
                               "magic_knowledge", "spell_creation"],
            description="研究新法术和魔法知识"
        ),

        # 新建筑类型
        BuildingType.ORC_LAIR: BuildingConfig(
            name="兽人巢穴",
            building_type=BuildingType.ORC_LAIR,
            category=BuildingCategory.INFRASTRUCTURE,
            cost_gold=200,
            cost_crystal=0,
            build_time=150.0,
            engineer_requirement=1,
            health=500,
            armor=6,
            color=(139, 69, 19),  # 马鞍棕色
            level=3,
            special_abilities=["training", "monster_binding"],
            description="训练兽人战士的基础建筑"
        ),

        BuildingType.DEMON_LAIR: BuildingConfig(
            name="恶魔巢穴",
            building_type=BuildingType.DEMON_LAIR,
            category=BuildingCategory.INFRASTRUCTURE,
            cost_gold=200,
            cost_crystal=0,
            build_time=180.0,
            engineer_requirement=1,
            health=450,
            armor=6,
            color=(75, 0, 130),  # 靛青色
            level=4,
            special_abilities=["summoning",
                               "monster_binding", "mana_consumption"],
            description="召唤小恶魔的基础建筑"
        ),
    }

    @classmethod
    def get_config(cls, building_type: BuildingType) -> Optional[BuildingConfig]:
        """获取建筑配置"""
        return cls.BUILDING_CONFIGS.get(building_type)

    @classmethod
    def get_all_configs(cls) -> Dict[BuildingType, BuildingConfig]:
        """获取所有建筑配置"""
        return cls.BUILDING_CONFIGS.copy()

    @classmethod
    def get_configs_by_category(cls, category: BuildingCategory) -> Dict[BuildingType, BuildingConfig]:
        """根据分类获取建筑配置"""
        return {bt: config for bt, config in cls.BUILDING_CONFIGS.items()
                if config.category == category}

    @classmethod
    def create_building(cls, building_type: BuildingType, x: int, y: int) -> Optional[Building]:
        """创建建筑实例"""
        config = cls.get_config(building_type)
        if not config:
            return None

        # 根据建筑类型创建对应的子类实例
        if building_type == BuildingType.DUNGEON_HEART:
            from .building_types import DungeonHeart
            return DungeonHeart(x, y, building_type, config)
        elif building_type == BuildingType.TREASURY:
            from .building_types import Treasury
            return Treasury(x, y, building_type, config)
        elif building_type == BuildingType.ARROW_TOWER:
            from .building_types import ArrowTower
            return ArrowTower(x, y, building_type, config)
        elif building_type == BuildingType.ARCANE_TOWER:
            from .building_types import ArcaneTower
            return ArcaneTower(x, y, building_type, config)
        elif building_type == BuildingType.MAGIC_ALTAR:
            from .building_types import MagicAltar
            return MagicAltar(x, y, building_type, config)
        elif building_type == BuildingType.ORC_LAIR:
            from .building_types import OrcLair
            return OrcLair(x, y, building_type, config)
        elif building_type == BuildingType.DEMON_LAIR:
            from .building_types import DemonLair
            return DemonLair(x, y, building_type, config)
        # 其他建筑类型...
        else:
            # 使用基类
            return Building(x, y, building_type, config)
