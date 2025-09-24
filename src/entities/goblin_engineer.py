#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地精工程师系统
根据 BUILDING_SYSTEM.md 文档实现基础、专业、大师工程师
"""

import time
import math
import random
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from src.core.constants import GameConstants
from src.core.enums import TileType
from src.core.game_state import Tile
from src.entities.creature import Creature
from src.managers.movement_system import MovementSystem


class EngineerType(Enum):
    """工程师类型"""
    BASIC = "basic"                    # 基础工程师
    SPECIALIST = "specialist"          # 专业工程师
    MASTER = "master"                  # 大师工程师


class EngineerStatus(Enum):
    """工程师状态"""
    IDLE = "idle"                      # 空闲
    WANDERING = "wandering"            # 游荡
    FETCHING_RESOURCES = "fetching_resources"  # 前往主基地获取资源
    MOVING_TO_SITE = "moving_to_site"  # 前往建造点
    CONSTRUCTING = "constructing"      # 建造中
    REPAIRING = "repairing"            # 修理中
    UPGRADING = "upgrading"            # 升级中
    RETURNING_TO_BASE = "returning_to_base"  # 返回主基地存储金币


@dataclass
class EngineerConfig:
    """工程师配置数据"""
    name: str                          # 工程师名称
    engineer_type: EngineerType        # 工程师类型
    cost: int                          # 召唤成本
    health: int                        # 生命值
    speed: int                         # 移动速度
    build_efficiency: float            # 建造效率
    color: Tuple[int, int, int]        # 颜色
    size: int                          # 体型大小
    level: int                         # 工程师等级
    max_concurrent_projects: int       # 同时项目数
    repair_efficiency: float           # 修理效率
    upgrade_capability: bool           # 升级能力
    special_abilities: List[str]       # 特殊能力
    description: str                   # 描述


class Engineer(Creature):
    """工程师基类 - 继承自Creature"""

    def __init__(self, x: float, y: float, engineer_type: EngineerType, config: EngineerConfig):
        """
        初始化工程师

        Args:
            x, y: 世界坐标
            engineer_type: 工程师类型
            config: 工程师配置
        """
        # 调用父类构造函数，使用 'goblin_engineer' 作为生物类型
        super().__init__(x, y, 'goblin_engineer')

        # 设置友好的名称
        self.name = '工程师'

        # 设置为非战斗单位
        self.is_combat_unit = False

        self.engineer_type = engineer_type
        self.config = config

        # 工程师特有属性
        self.name = config.name
        self.build_efficiency = config.build_efficiency
        self.level = config.level

        # 工作能力
        self.max_concurrent_projects = config.max_concurrent_projects
        self.repair_efficiency = config.repair_efficiency
        self.upgrade_capability = config.upgrade_capability
        self.special_abilities = config.special_abilities or []

        # 状态管理
        self.status = EngineerStatus.IDLE
        self.current_projects = []         # 当前项目列表
        self.target_building = None        # 目标建筑
        self.work_progress = 0.0           # 工作进度

        # 资源管理
        self.carried_gold = 0              # 携带的金币数量
        self.max_carry_capacity = 60       # 最大携带容量
        self.deposit_rate = 4              # 每次存放金币速度（每秒4金币）
        self.once_time = 1                 # 每次存放金币间隔时间（秒）
        self.deposit_count = 0             # 存放次数计数器（用于日志显示）
        self.last_deposit_time = 0.0       # 上次存放金币时间

        # 移动系统
        self.target_position = None        # 目标位置
        self.dungeon_heart_pos = None      # 主基地位置缓存

        # 时间管理
        self.last_update_time = time.time()
        self.work_start_time = 0.0
        self.idle_start_time = time.time()  # 空闲状态开始时间

        # 状态指示器 - 使用通用系统
        try:
            from src.ui.status_indicator import StatusIndicator
            self.status_indicator = StatusIndicator()
        except ImportError:
            self.status_indicator = None

    def update(self, delta_time: float, game_map, creatures: List = None, heroes: List = None, effect_manager=None, building_manager=None) -> Dict[str, Any]:
        """
        更新工程师状态 - 重写父类的update方法

        Args:
            delta_time: 时间增量（毫秒）
            game_map: 游戏地图
            creatures: 生物列表（父类兼容性）
            heroes: 英雄列表（父类兼容性）
            effect_manager: 特效管理器（父类兼容性）
            building_manager: 建筑管理器

        Returns:
            Dict: 更新结果
        """
        current_time = time.time()
        delta_seconds = delta_time / 1000.0

        result = {
            'status_changed': False,
            'work_completed': [],
            'events': [],
            'building_completed': None  # 添加building_completed字段
        }

        # 记录状态变化
        if hasattr(self, '_last_debug_status') and self._last_debug_status != self.status:
            print(
                f"🔄 [{self.name}] 状态变化: {self._last_debug_status} -> {self.status}")
        self._last_debug_status = self.status

        # 更新工程师状态机 - 参考哥布林苦工的优先级模式
        if self.status == EngineerStatus.IDLE:
            self._update_idle_state(delta_seconds, result, building_manager)
        elif self.status == EngineerStatus.WANDERING:
            self._update_wandering_state(
                delta_seconds, game_map, result, building_manager)
        elif self.status == EngineerStatus.FETCHING_RESOURCES:
            self._update_fetching_resources_state(
                delta_seconds, game_map, result)
        elif self.status == EngineerStatus.MOVING_TO_SITE:
            self._update_moving_state(
                delta_seconds, game_map, result, building_manager)
        elif self.status == EngineerStatus.CONSTRUCTING:
            self._update_construction_state(delta_seconds, result)
        elif self.status == EngineerStatus.REPAIRING:
            self._update_repair_state(delta_seconds, result)
        elif self.status == EngineerStatus.UPGRADING:
            self._update_upgrade_state(delta_seconds, result)
        elif self.status == EngineerStatus.RETURNING_TO_BASE:
            self._update_returning_to_base_state(
                delta_seconds, game_map, result)

        # 如果状态发生变化，重置空闲时间
        if result.get('status_changed', False):
            self.idle_start_time = time.time()

            # 如果工程师不再处于工作状态，从working_engineer列表中移除
            if (self.status != EngineerStatus.CONSTRUCTING and
                self.status != EngineerStatus.REPAIRING and
                self.status != EngineerStatus.UPGRADING and
                self.target_building and
                    self in self.target_building.working_engineer):
                self.target_building.working_engineer.remove(self)

        # 同步工程师状态到生物对象的state属性
        engineer_state = self.get_status_for_indicator()
        self.state = engineer_state

        # 状态指示器会自动根据状态更新，无需手动更新

        # building_completed字段已在各个状态更新方法中设置

        self.last_update_time = current_time
        return result

    def assign_construction_project(self, building, priority: int = 1) -> bool:
        """
        分配建造项目 - 新系统兼容性方法

        Args:
            building: 目标建筑
            priority: 优先级

        Returns:
            bool: 是否成功分配
        """
        # 如果工程师空闲且没有目标建筑，直接分配
        if self.status == EngineerStatus.IDLE and not self.target_building:
            self.target_building = building
            # 将工程师添加到建筑的分配列表中
            if self not in building.assigned_engineers:
                building.assigned_engineers.append(self)
            print(f"📋 {self.name} 接受建造任务: {building.name}")
            return True

        return False  # 工程师忙碌中

    def assign_repair_project(self, building, priority: int = 2) -> bool:
        """
        分配修理项目 - 新系统兼容性方法

        Args:
            building: 目标建筑
            priority: 优先级

        Returns:
            bool: 是否成功分配
        """
        # 如果工程师空闲且没有目标建筑，直接分配
        if self.status == EngineerStatus.IDLE and not self.target_building:
            self.target_building = building
            # 将工程师添加到建筑的分配列表中
            if self not in building.assigned_engineers:
                building.assigned_engineers.append(self)
            print(f"🔧 {self.name} 接受修理任务: {building.name}")
            return True

        return False  # 工程师忙碌中

    def assign_upgrade_project(self, building, priority: int = 1) -> bool:
        """
        分配升级项目 - 新系统兼容性方法

        Args:
            building: 目标建筑
            priority: 优先级

        Returns:
            bool: 是否成功分配
        """
        if not self.upgrade_capability:
            return False

        # 如果工程师空闲且没有目标建筑，直接分配
        if self.status == EngineerStatus.IDLE and not self.target_building:
            self.target_building = building
            # 将工程师添加到建筑的分配列表中
            if self not in building.assigned_engineers:
                building.assigned_engineers.append(self)
            print(f"⬆️ {self.name} 接受升级任务: {building.name}")
            return True

        return False  # 工程师忙碌中

    def cancel_project(self, building) -> bool:
        """
        取消项目 - 新系统兼容性方法

        Args:
            building: 目标建筑

        Returns:
            bool: 是否成功取消
        """
        # 如果取消的是当前正在进行的项目
        if self.target_building == building:
            print(f"❌ {self.name} 取消任务: {building.name}")
            self.target_building = None
            self.work_progress = 0.0
            self.last_deposit_time = 0.0
            self.status = EngineerStatus.IDLE
            # 从建筑的分配列表中移除工程师
            if self in building.assigned_engineers:
                building.assigned_engineers.remove(self)
            return True

        return False

    def get_work_status(self) -> Dict[str, Any]:
        """获取工作状态"""
        return {
            'engineer_type': self.engineer_type.value,
            'name': self.name,
            'status': self.status.value,
            'health': self.health,
            'position': (self.x, self.y),
            'current_projects': len(self.current_projects),
            'max_projects': self.max_concurrent_projects,
            'work_progress': self.work_progress,
            'target_building': self.target_building.name if self.target_building else None,
            'efficiency': self.build_efficiency,
            'level': self.level
        }

    def use_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """
        使用特殊能力

        Args:
            ability_name: 能力名称
            target: 目标（如果需要）

        Returns:
            Dict: 使用结果
        """
        if ability_name not in self.special_abilities:
            return {'used': False, 'reason': 'ability_not_available'}

        return self._execute_special_ability(ability_name, target)

    def get_current_position(self) -> Tuple[float, float]:
        """获取当前位置"""
        return (self.x, self.y)

    def _update_idle_state(self, delta_seconds: float, result: Dict[str, Any], building_manager=None):
        """更新空闲状态 - 参考哥布林苦工的优先级模式"""

        # 检查空闲时间，如果超过1秒且没有目标建筑，自动转为游荡状态
        current_time = time.time()
        idle_duration = current_time - self.idle_start_time

        if not self.target_building and idle_duration >= 1.0:
            self.status = EngineerStatus.WANDERING
            result['status_changed'] = True
            return

        # 优先级1: 如果没有目标建筑，返回主基地将所有金币归还
        if not self.target_building and self.carried_gold > 0:
            print(f"💰 [{self.name}] 没有目标建筑但携带金币，返回主基地")
            self.status = EngineerStatus.RETURNING_TO_BASE
            result['status_changed'] = True
            return

        # 优先级2: 寻找全局未完成建筑（不限制范围）
        if building_manager:
            nearest_building = building_manager.find_any_incomplete_building()
            print(
                f"🔍 [{self.name}] 建筑管理器返回: {nearest_building.name if nearest_building else 'None'}")

            if nearest_building:
                print(f"✅ [{self.name}] 找到目标建筑: {nearest_building.name}")
                # 检查建筑所需金币
                required_gold = self._get_building_required_gold(
                    nearest_building)
                print(
                    f"🔍 [{self.name}] _get_building_required_gold返回: {required_gold}")

                # 优先级3: 如果携带金币不足，先去主基地获取资源
                print(
                    f"💰 [{self.name}] 检查建筑金币需求: 需要{required_gold}, 携带{self.carried_gold}")
                if self.carried_gold < required_gold:
                    print(
                        f"💸 [{self.name}] 金币不足，前往主基地获取资源 - 目标建筑: {nearest_building.name}")
                    self.target_building = nearest_building  # 记住目标建筑
                    # 将工程师添加到建筑的分配列表中
                    if self not in nearest_building.assigned_engineers:
                        nearest_building.assigned_engineers.append(self)
                        print(
                            f"📋 [{self.name}] 已添加到建筑 {nearest_building.name} 的分配列表")
                    self.status = EngineerStatus.FETCHING_RESOURCES
                    result['status_changed'] = True
                    print(
                        f"   💰 需要金币: {required_gold}, 当前携带: {self.carried_gold}")
                    print(f"   🔓 建筑 {nearest_building.name} 暂时解锁，其他工程师可以接手")
                    return
                else:
                    # 优先级4: 金币充足，直接前往建筑
                    print(
                        f"✅ [{self.name}] 金币充足，直接前往建筑 {nearest_building.name}")
                    self.target_building = nearest_building
                    # 将工程师添加到建筑的分配列表中
                    if self not in nearest_building.assigned_engineers:
                        nearest_building.assigned_engineers.append(self)
                        print(
                            f"📋 [{self.name}] 已添加到建筑 {nearest_building.name} 的分配列表")
                    self.status = EngineerStatus.MOVING_TO_SITE
                    result['status_changed'] = True

                    # 更新目标可视化（灰色虚线）
                    from src.managers.movement_system import MovementSystem
                    target_x = nearest_building.x * 32 + 16  # 建筑中心点
                    target_y = nearest_building.y * 32 + 16
                    print(
                        f"🎯 [{self.name}] 创建目标连线: ({self.x:.1f}, {self.y:.1f}) -> ({target_x}, {target_y})")
                    MovementSystem.update_target_line(
                        (self.x, self.y), (target_x, target_y),
                        self.name, (128, 128, 128)  # 灰色
                    )
                    print(f"🎯 {self.name} 发现目标建筑 {nearest_building.name}，开始前往")
                    return

    def _start_wandering(self, delta_seconds: float, result: Dict[str, Any]):
        """开始游荡"""
        self.status = EngineerStatus.WANDERING
        result['status_changed'] = True
        # 初始化游荡相关属性
        if not hasattr(self, 'wander_target'):
            self.wander_target = None
        if not hasattr(self, 'wander_wait_time'):
            self.wander_wait_time = 0

    def _update_wandering_state(self, delta_seconds: float, game_map, result: Dict[str, Any], building_manager=None):
        """更新游荡状态 - 游荡是优先级最低的行为，应该持续寻找工作"""

        # 优先级1: 在游荡过程中持续检查是否有新工作（工作优先于游荡）
        if building_manager:
            nearest_building = building_manager.find_any_incomplete_building()

            if nearest_building:
                print(
                    f"🎯 [{self.name}] 游荡中发现建筑 {nearest_building.name}，转换到空闲状态处理")
                # 立即转换到空闲状态，让空闲状态处理建筑任务
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return

        # 优先级2: 如果没有工作可做，继续进行游荡移动
        # 游荡是优先级最低的行为，只有在确实没有工作时才进行
        from src.managers.movement_system import MovementSystem
        # 工程师游荡速度使用0.5倍速，符合文档规范
        MovementSystem.wandering_movement(
            self, delta_seconds * 1000, game_map, 0.5)

    def _determine_task_type(self, building) -> str:
        """根据建筑状态确定任务类型"""
        from src.entities.building import BuildingStatus

        if building.status == BuildingStatus.DAMAGED:
            return 'repair'
        elif building.status in [BuildingStatus.PLANNING, BuildingStatus.UNDER_CONSTRUCTION]:
            return 'construction'
        else:
            return 'construction'  # 默认为建造

    def _update_moving_state(self, delta_seconds: float, game_map, result: Dict[str, Any], building_manager=None):
        """更新移动状态"""

        if not self.target_building:
            print(f"⚠️ [{self.name}] 移动状态但没有目标建筑，返回空闲")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 添加移动调试信息
        if not hasattr(self, '_move_debug_counter'):
            self._move_debug_counter = 0
        self._move_debug_counter += 1

        if self._move_debug_counter % 60 == 1:
            print(
                f"🚶 [{self.name}] 移动中 -> {self.target_building.name} 位置:({self.x:.1f}, {self.y:.1f})px")

        # 检查目标建筑是否被其他工程师占用（每60帧检查一次，减少频率）
        if not hasattr(self, '_target_check_counter'):
            self._target_check_counter = 0
        self._target_check_counter += 1

        if self._target_check_counter % 60 == 0:  # 每60帧检查一次，减少频率
            if building_manager and building_manager._is_building_being_worked_on(self.target_building):
                print(f"🔄 [{self.name}] 目标建筑被占用，寻找新目标")
                # 清除目标连线
                MovementSystem.clear_unit_target_lines(self.name)
                # 寻找新目标
                self.target_building = None
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return
            else:
                print(
                    f"✅ [{self.name}] 目标建筑 {self.target_building.name} 未被占用，继续移动")

        # 使用新的分离式寻路+移动系统
        try:
            # 计算建筑位置
            building_x = self.target_building.x * \
                GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            building_y = self.target_building.y * \
                GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            target_pos = (building_x, building_y)

            # 智能更新目标连线（基于位置变化和距离）
            if not hasattr(self, '_last_target_line_pos'):
                self._last_target_line_pos = (0, 0)
                self._last_target_line_target = (0, 0)

            current_pos = (self.x, self.y)
            pos_changed = (abs(current_pos[0] - self._last_target_line_pos[0]) > 10 or
                           abs(current_pos[1] - self._last_target_line_pos[1]) > 10)
            target_changed = (abs(target_pos[0] - self._last_target_line_target[0]) > 5 or
                              abs(target_pos[1] - self._last_target_line_target[1]) > 5)

            if pos_changed or target_changed:
                MovementSystem.update_target_line(
                    current_pos, target_pos,
                    self.name, (128, 128, 128)  # 灰色
                )
                self._last_target_line_pos = current_pos
                self._last_target_line_target = target_pos

            # 使用统一API进行寻路+移动
            arrived = MovementSystem.pathfind_and_move(
                self, target_pos, delta_seconds * 1000, game_map, "A_STAR", 1.0)
        except Exception as e:
            print(f"❌ {self.name} 移动系统调用失败: {e}")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 手动检查是否真的到达目标位置
        if arrived:
            # 计算实际距离
            building_x = self.target_building.x * \
                GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            building_y = self.target_building.y * \
                GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            current_x, current_y = self.get_current_position()
            actual_distance = math.sqrt(
                (current_x - building_x) ** 2 + (current_y - building_y) ** 2)

            # 只有真正接近目标时才开始工作
            if actual_distance <= 20:  # 20像素的工作范围（增加20px避免建筑碰撞体积）
                # 只在移动状态时转换到建造状态，避免重复转换
                if self.status == EngineerStatus.MOVING_TO_SITE:
                    print(
                        f"✅ {self.name} 到达建筑工作范围，距离: {actual_distance:.1f}px <= 20px")

                    # 再次检查建筑是否被其他工程师占用（竞争检查）
                    if building_manager and building_manager._is_building_being_worked_on(self.target_building):
                        print(f"❌ {self.name} 建筑已被占用，寻找新目标")
                        # 清除目标连线
                        MovementSystem.clear_unit_target_lines(self.name)
                        # 寻找新目标
                        self.target_building = None
                        self.status = EngineerStatus.IDLE
                        result['status_changed'] = True
                        return

                    # 清除目标连线（到达目标后不再需要连线）
                    MovementSystem.clear_unit_target_lines(self.name)

                    # 新系统：直接根据目标建筑开始建造
                    if self.target_building:
                        print(f"🔨 {self.name} 开始建造 {self.target_building.name}")
                        self.status = EngineerStatus.CONSTRUCTING
                        self.work_start_time = time.time()
                        self.work_progress = 0.0
                        # 将工程师添加到建筑的working_engineer列表中
                        if self not in self.target_building.working_engineer:
                            self.target_building.working_engineer.append(self)
                        result['status_changed'] = True
                else:
                    print(f"⚠️ {self.name} 到达工作范围但没有目标建筑")
                    self.status = EngineerStatus.IDLE
                    result['status_changed'] = True

    def _update_construction_state(self, delta_seconds: float, result: Dict[str, Any]):
        """更新建造状态 - 每秒投入4金币，每5次投入显示一次日志"""
        if not self.target_building:
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 检查是否有金币可以存放
        if self.carried_gold <= 0:
            print(f"💸 {self.name} 建造时金币耗尽，前往主基地获取金币")

            # 检查主基地是否有足够的金币
            if hasattr(self, 'game_instance') and self.game_instance:
                required_gold = self._get_building_required_gold(
                    self.target_building)
                available_gold = self.game_instance.game_state.gold

                if available_gold >= required_gold:
                    print(
                        f"💰 主基地有足够金币 ({available_gold}/{required_gold})，前往获取")
                    self.status = EngineerStatus.FETCHING_RESOURCES
                    result['status_changed'] = True
                    return
                else:
                    print(f"🚫 主基地金币不足 ({available_gold}/{required_gold})，放弃建造")
                    # 放弃当前建筑，返回基地存储剩余金币
                    self.target_building = None
                    self.status = EngineerStatus.RETURNING_TO_BASE
                    result['status_changed'] = True
                    return
            else:
                print(f"❌ 无法访问游戏实例，放弃建造")
                self.target_building = None
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return

        # 获取建筑所需的总金币
        required_gold = self._get_building_required_gold(self.target_building)

        # 在投入金币前，先检查建筑是否应该拒绝这个工程师
        self.target_building.auto_reject_excess_engineers()

        # 初始化建筑的金币存储（如果没有的话）
        if not hasattr(self.target_building, 'invested_gold'):
            self.target_building.invested_gold = 0
            self.deposit_count = 0  # 重置计数器
            print(f"🏗️ {self.name} 开始建造 {self.target_building.name}")
            print(f"   💰 建筑成本: {required_gold} 金币")
            print(f"   💼 工程师携带: {self.carried_gold} 金币")
            print(f"   ⚡ 建造速度: {self.deposit_rate} 金币/秒")
            print(f"   🔍 调试信息: 建筑类型={self.target_building.building_type}, config.cost_gold={getattr(self.target_building.config, 'cost_gold', 'N/A')}, construction_cost_gold={getattr(self.target_building, 'construction_cost_gold', 'N/A')}")

        current_time = time.time()
        if self.last_deposit_time == 0:
            self.last_deposit_time = current_time

        # 每秒投入4金币
        time_since_last_deposit = current_time - self.last_deposit_time
        if time_since_last_deposit >= self.once_time:  # 每秒检查一次

            # 计算本次可以存放的金币数量
            gold_to_deposit = min(self.deposit_rate, self.carried_gold)
            remaining_needed = required_gold - self.target_building.invested_gold
            actual_deposit = min(gold_to_deposit, remaining_needed)

            if actual_deposit > 0:
                # 执行金币存放到建筑
                old_carried = self.carried_gold
                old_invested = self.target_building.invested_gold

                self.carried_gold -= actual_deposit
                self.target_building.invested_gold += actual_deposit
                self.deposit_count += 1  # 增加投入次数

                # 每5次投入显示一次简化日志
                if self.deposit_count % 5 == 0:
                    progress = self.target_building.invested_gold / required_gold
                    print(
                        f"🔨 {self.name} 建造进度: {progress*100:.1f}% ({self.target_building.invested_gold}/{required_gold}) - 第{self.deposit_count}次投入")

                # 更新建造进度
                if hasattr(self.target_building, 'construction_progress'):
                    progress = self.target_building.invested_gold / required_gold
                    self.target_building.construction_progress = min(
                        1.0, progress)

                    # 同步进度到地图瓦片（如果工程师有游戏实例引用）
                    if hasattr(self, 'game_instance') and self.game_instance:
                        x, y = self.target_building.x, self.target_building.y
                        if (0 <= y < len(self.game_instance.game_map) and
                                0 <= x < len(self.game_instance.game_map[0])):
                            tile = self.game_instance.game_map[y][x]
                            tile.construction_progress = self.target_building.construction_progress

                self.last_deposit_time = current_time

                # 检查是否完成建造
                if self.target_building.invested_gold >= required_gold:
                    print(
                        f"🎉 ✅ {self.name} 完成了 {self.target_building.name} 的建造!")
                    print(
                        f"   🏗️ 总投入: {self.target_building.invested_gold} 金币")
                    print(f"   💼 工程师剩余: {self.carried_gold} 金币")
                    print(f"   📊 总投入次数: {self.deposit_count} 次")
                    self._complete_current_project(result)
                    return
            else:
                # 无需更多金币，建造完成
                print(f"✅ {self.name} {self.target_building.name} 已完成建造 - 无需更多金币")
                self._complete_current_project(result)
                return

    def _update_repair_state(self, delta_seconds: float, result: Dict[str, Any]):
        """更新修理状态 - 使用工程师携带的金币进行修复"""
        if not self.target_building:
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 检查是否有金币可以用于修理
        if self.carried_gold <= 0:
            print(f"💸 {self.name} 修理时金币耗尽，前往主基地获取金币")

            # 检查主基地是否有足够的金币
            if hasattr(self, 'game_instance') and self.game_instance:
                # 修理通常需要较少的金币，估算修理成本
                repair_cost_estimate = max(
                    20, int(self.target_building.max_health * 0.1))  # 估算修理成本
                available_gold = self.game_instance.game_state.gold

                if available_gold >= repair_cost_estimate:
                    print(
                        f"💰 主基地有足够金币 ({available_gold}/{repair_cost_estimate})，前往获取")
                    self.status = EngineerStatus.FETCHING_RESOURCES
                    result['status_changed'] = True
                    return
                else:
                    print(
                        f"🚫 主基地金币不足 ({available_gold}/{repair_cost_estimate})，放弃修理")
                    # 放弃当前修理任务
                    self.target_building = None
                    self.status = EngineerStatus.RETURNING_TO_BASE
                    result['status_changed'] = True
                    return
            else:
                print(f"❌ 无法访问游戏实例，放弃修理")
                self.target_building = None
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return

        # 初始化修理进度（如果没有的话）
        if not hasattr(self, 'repair_progress'):
            self.repair_progress = 0.0
            self.repair_deposit_count = 0
            print(f"🔧 {self.name} 开始修理 {self.target_building.name}")
            print(f"   💰 建筑建造成本: {self.target_building.config.cost_gold} 金币")
            print(f"   💼 工程师携带: {self.carried_gold} 金币")
            print(f"   ⚡ 修理速度: {self.deposit_rate} 金币/秒")

        current_time = time.time()
        if self.last_deposit_time == 0:
            self.last_deposit_time = current_time

        # 每秒投入金币进行修理
        if current_time - self.last_deposit_time >= 1.0:  # 每秒投入
            # 计算每次投入的金币数量（与建造相同）
            gold_to_deposit = min(self.deposit_rate, self.carried_gold)

            if gold_to_deposit > 0:
                # 计算可以修复的生命值
                repair_cost_per_hp = self.target_building.config.cost_gold * 0.001
                hp_to_repair = int(gold_to_deposit / repair_cost_per_hp)

                # 执行修复
                repair_result = self.target_building.repair(
                    hp_to_repair, gold_to_deposit)

                if repair_result['repaired']:
                    # 扣除工程师的金币
                    self.carried_gold -= repair_result['repair_cost']
                    self.repair_progress += repair_result['repair_amount'] / \
                        self.target_building.max_health
                    self.repair_deposit_count += 1

                    # 每5次投入显示一次日志
                    if self.repair_deposit_count % 5 == 0:
                        print(
                            f"🔧 {self.name} 修理进度: {self.repair_progress*100:.1f}% (投入 {repair_result['repair_cost']} 金币)")
                        print(f"   💼 工程师剩余金币: {self.carried_gold}")
                        print(
                            f"   🏥 建筑生命值: {self.target_building.health}/{self.target_building.max_health}")

                    result['events'].append(
                        f"{self.name} 修理了 {repair_result['repair_amount']} 点生命值，花费 {repair_result['repair_cost']} 金币")
                else:
                    if repair_result.get('reason') == 'insufficient_gold':
                        result['events'].append(
                            f"{self.name} 修理失败：金币不足（需要 {repair_result['required_gold']} 金币，当前 {repair_result['available_gold']} 金币）")

                        # 检查主基地是否有足够的金币
                        if hasattr(self, 'game_instance') and self.game_instance:
                            repair_cost_estimate = max(
                                20, int(self.target_building.max_health * 0.1))
                            available_gold = self.game_instance.game_state.gold

                            if available_gold >= repair_cost_estimate:
                                print(
                                    f"💰 主基地有足够金币 ({available_gold}/{repair_cost_estimate})，前往获取")
                                self.status = EngineerStatus.FETCHING_RESOURCES
                                result['status_changed'] = True
                                return
                            else:
                                print(
                                    f"🚫 主基地金币不足 ({available_gold}/{repair_cost_estimate})，放弃修理")
                                self.target_building = None
                                self.status = EngineerStatus.RETURNING_TO_BASE
                                result['status_changed'] = True
                                return
                        else:
                            print(f"❌ 无法访问游戏实例，放弃修理")
                            self.target_building = None
                            self.status = EngineerStatus.IDLE
                            result['status_changed'] = True
                            return

                self.last_deposit_time = current_time

        # 检查修理是否完成
        if self.target_building.health >= self.target_building.max_health * 0.5 and self.target_building.status.value == 'damaged':
            print(f"✅ {self.name} {self.target_building.name} 修理完成")
            self._complete_current_project(result)
            return

        # 检查是否需要更多金币
        if self.carried_gold <= 0:
            print(f"💸 {self.name} 修理时金币耗尽，前往主基地获取金币")

            # 检查主基地是否有足够的金币
            if hasattr(self, 'game_instance') and self.game_instance:
                # 修理通常需要较少的金币，估算修理成本
                repair_cost_estimate = max(
                    20, int(self.target_building.max_health * 0.1))  # 估算修理成本
                available_gold = self.game_instance.game_state.gold

                if available_gold >= repair_cost_estimate:
                    print(
                        f"💰 主基地有足够金币 ({available_gold}/{repair_cost_estimate})，前往获取")
                    self.status = EngineerStatus.FETCHING_RESOURCES
                    result['status_changed'] = True
                    return
                else:
                    print(
                        f"🚫 主基地金币不足 ({available_gold}/{repair_cost_estimate})，放弃修理")
                    # 放弃当前修理任务
                    self.target_building = None
                    self.status = EngineerStatus.RETURNING_TO_BASE
                    result['status_changed'] = True
                    return
            else:
                print(f"❌ 无法访问游戏实例，放弃修理")
                self.target_building = None
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return

    def _update_upgrade_state(self, delta_seconds: float, result: Dict[str, Any]):
        """更新升级状态"""
        if not self.target_building or not self.current_projects:
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        current_project = self.current_projects[0]

        # 计算升级进度 - 简化版本
        progress_increment = self.build_efficiency / \
            current_project['estimated_time'] * delta_seconds
        self.work_progress += progress_increment

        # 更新建筑的升级进度
        if hasattr(self.target_building, 'construction_progress'):
            self.target_building.construction_progress = min(
                1.0, self.work_progress)

        if self.work_progress >= 1.0:
            # 升级完成
            self._complete_current_project(result)

    def _update_fetching_resources_state(self, delta_seconds: float, game_map, result: Dict[str, Any]):
        """更新获取资源状态 - 前往主基地获取金币"""
        dungeon_heart_positions = self._get_dungeon_heart_position()
        if not dungeon_heart_positions:
            print(f"❌ {self.name} 无法找到主基地位置")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 计算到主基地所有块的最短距离
        min_distance = float('inf')
        closest_position = None

        for pos in dungeon_heart_positions:
            dx = pos[0] - self.x
            dy = pos[1] - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance < min_distance:
                min_distance = distance
                closest_position = pos

        distance = min_distance

        # 添加调试信息
        if not hasattr(self, '_fetch_debug_counter'):
            self._fetch_debug_counter = 0
        self._fetch_debug_counter += 1

        if self._fetch_debug_counter % 60 == 1:  # 每秒输出一次
            print(f"🏠 [{self.name}] 前往主基地 - 当前位置: ({self.x:.1f}, {self.y:.1f}), 目标: ({closest_position[0]:.1f}, {closest_position[1]:.1f}), 距离: {distance:.1f}px")

        if distance > 20:  # 还没到达主基地（恢复正常的交互范围）
            # 使用新的分离式寻路+移动系统
            MovementSystem.pathfind_and_move(
                self, closest_position, delta_seconds * 1000, game_map, "A_STAR", 1.0)
        else:
            # 到达主基地，获取金币
            print(f"🏠 {self.name} 到达主基地，距离: {distance:.1f}px <= 20px")

            # 工程师从主基地获取金币时总是补充到最大值60
            max_carry_gold = min(60, self.max_carry_capacity)
            gold_to_fetch = max_carry_gold - self.carried_gold

            if gold_to_fetch > 0:
                # 从游戏资源中获取金币
                target_name = self.target_building.name if self.target_building else "未知建筑"
                print(f"🏦 {self.name} 开始从主基地获取金币 - 目标建筑: {target_name}")
                print(
                    f"📊 资源状态: 当前携带 {self.carried_gold}/{max_carry_gold}, 计划获取 {gold_to_fetch} 金币补充到最大值")

                if hasattr(self, 'game_instance') and self.game_instance:
                    available_gold = self.game_instance.game_state.gold
                    actual_fetch = min(gold_to_fetch, available_gold)

                    print(
                        f"🏛️ 主基地金库状态: {available_gold} 金币可用, 实际获取 {actual_fetch} 金币")

                    if actual_fetch > 0:
                        # 执行金币转移
                        old_base_gold = self.game_instance.game_state.gold
                        old_carried_gold = self.carried_gold

                        self.game_instance.game_state.gold -= actual_fetch
                        self.carried_gold += actual_fetch

                        print(f"💰 ✅ {self.name} 成功从主基地获取金币!")
                        print(
                            f"   📤 主基地: {old_base_gold} → {self.game_instance.game_state.gold} (-{actual_fetch})")
                        print(
                            f"   📥 工程师: {old_carried_gold} → {self.carried_gold} (+{actual_fetch})")
                        print(
                            f"   💼 携带状态: {self.carried_gold}/{self.max_carry_capacity} ({self.carried_gold/self.max_carry_capacity*100:.1f}%)")

                        # 成功获取金币，继续建造
                        if self.target_building:
                            print(
                                f"🔙 {self.name} 获取资源完成，返回建筑 {self.target_building.name}")
                            self.status = EngineerStatus.MOVING_TO_SITE
                            result['status_changed'] = True
                            return
                        else:
                            self.status = EngineerStatus.IDLE
                            result['status_changed'] = True
                            print(f"⚠️ {self.name} 没有目标建筑，返回空闲状态")
                            return
                    else:
                        print(f"💸 ❌ {self.name} 主基地金币不足!")
                        print(
                            f"   🏛️ 可用金币: {available_gold}, 需要金币: {gold_to_fetch}")

                        # 主基地金币不足，放弃当前目标建筑
                        if self.target_building:
                            print(
                                f"🚫 {self.name} 主基地金币不足，放弃目标建筑 {self.target_building.name}")
                            self.target_building = None

                        # 如果有携带金币，返回基地存储
                        if self.carried_gold > 0:
                            print(
                                f"💾 {self.name} 携带 {self.carried_gold} 金币，返回基地存储")
                            self.status = EngineerStatus.RETURNING_TO_BASE
                            result['status_changed'] = True
                            return
                        else:
                            # 没有金币也没有目标，进入空闲状态
                            self.status = EngineerStatus.IDLE
                            result['status_changed'] = True
                            print(f"😴 {self.name} 金币不足且无携带金币，进入空闲状态")
                            return
                else:
                    print(f"❌ {self.name} 无法访问游戏实例，无法获取金币")
                    # 无法访问游戏实例，返回空闲状态
                    self.target_building = None
                    self.status = EngineerStatus.IDLE
                    result['status_changed'] = True
                    return
            else:
                # 获取建筑所需金币数量
                building_required_gold = self._get_building_required_gold(
                    self.target_building) if self.target_building else 0
                print(
                    f"✅ {self.name} 金币充足，无需获取更多金币 (携带: {self.carried_gold}/{building_required_gold})")

                # 转换到移动到建筑状态
                if self.target_building:
                    # 获取资源期间不锁定建筑，直接返回建筑进行竞争
                    print(
                        f"🔙 {self.name} 获取资源完成，返回建筑 {self.target_building.name}")
                    self.status = EngineerStatus.MOVING_TO_SITE
                    result['status_changed'] = True
                    return
                else:
                    self.status = EngineerStatus.IDLE
                    result['status_changed'] = True
                    print(f"⚠️ {self.name} 没有目标建筑，返回空闲状态")
                    return

    def _update_returning_to_base_state(self, delta_seconds: float, game_map, result: Dict[str, Any]):
        """更新返回主基地状态 - 存储剩余金币"""
        # 寻找最近的存储点（金库或主基地）
        storage_target = self._find_nearest_storage()
        if not storage_target:
            print(f"❌ {self.name} 无法找到存储点，进入空闲状态")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        target_pos = (storage_target['x'], storage_target['y'])

        # 计算到存储点的距离
        dx = target_pos[0] - self.x
        dy = target_pos[1] - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 20:  # 还没到达存储点（恢复正常的交互范围）
            # 使用新的分离式寻路+移动系统
            MovementSystem.pathfind_and_move(
                self, target_pos, delta_seconds * 1000, game_map, "A_STAR", 1.0)
        else:
            # 到达存储点，存储金币
            print(f"🏠 {self.name} 到达存储点，距离: {distance:.1f}px <= 20px")

            if self.carried_gold > 0:
                print(f"🏦 {self.name} 开始向存储点存储剩余金币")
                print(f"💼 当前携带: {self.carried_gold} 金币")

                # 存储到指定存储点
                self._deposit_gold_to_storage(storage_target)
            else:
                print(f"💼 {self.name} 没有剩余金币需要存储")

            # 转换到空闲状态
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            print(f"😴 {self.name} 完成存储，进入空闲状态")

    def _find_nearest_storage(self) -> Optional[Dict[str, Any]]:
        """寻找最近的存储点（金库或主基地）"""
        # 首先寻找金库
        nearest_treasury = None
        min_distance = float('inf')

        if hasattr(self, 'game_instance') and self.game_instance:
            # 检查建筑管理器中的金库
            if hasattr(self.game_instance, 'building_manager'):
                for building in self.game_instance.building_manager.buildings:
                    if (hasattr(building, 'building_type') and
                        building.building_type.value == 'treasury' and
                            building.is_active):
                        # 将建筑的瓦片坐标转换为像素坐标
                        building_pixel_x = building.x * \
                            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
                        building_pixel_y = building.y * \
                            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

                        dx = building_pixel_x - self.x
                        dy = building_pixel_y - self.y
                        distance = math.sqrt(dx * dx + dy * dy)

                        if distance < min_distance:
                            min_distance = distance
                            nearest_treasury = {
                                'type': 'treasury',
                                'building': building,
                                'x': building_pixel_x,
                                'y': building_pixel_y,
                                'distance': distance
                            }

        # 如果找到金库且距离合理，优先选择金库
        if nearest_treasury and min_distance < 200:  # 200像素内优先选择金库
            return nearest_treasury

        # 否则选择主基地
        dungeon_heart_positions = self._get_dungeon_heart_position()
        if dungeon_heart_positions:
            # 计算到地牢之心所有块的最短距离
            min_distance = float('inf')
            closest_position = None

            for pos in dungeon_heart_positions:
                dx = pos[0] - self.x
                dy = pos[1] - self.y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < min_distance:
                    min_distance = distance
                    closest_position = pos

            return {
                'type': 'dungeon_heart',
                'building': None,
                'x': closest_position[0],
                'y': closest_position[1],
                'distance': min_distance
            }

        return None

    def _deposit_gold_to_storage(self, storage_target: Dict[str, Any]):
        """存储金币到指定存储点"""
        if storage_target['type'] == 'treasury':
            # 存储到金库
            treasury = storage_target['building']
            if treasury and hasattr(treasury, 'deposit_gold'):
                deposited = treasury.deposit_gold(int(self.carried_gold))
                if deposited > 0:
                    self.carried_gold -= deposited
                    print(
                        f"💰 {self.name} 存储了 {deposited} 金币到金库({treasury.name}) 位置({treasury.x},{treasury.y})")
                else:
                    print(
                        f"⚠️ 金库({treasury.name}) 在位置({treasury.x},{treasury.y}) 已满，无法存储更多金币")
            else:
                print(f"❌ 金库不可用，无法存储金币")
        else:
            # 存储到主基地
            if hasattr(self, 'game_instance') and self.game_instance:
                # 检查主基地存储容量
                game_state = self.game_instance.game_state
                available_space = game_state.max_gold_capacity - game_state.gold
                deposit_amount = min(int(self.carried_gold), available_space)

                if deposit_amount > 0:
                    old_gold = int(game_state.gold)
                    game_state.gold += deposit_amount
                    self.carried_gold -= deposit_amount
                    # 确保金币始终为整数
                    game_state.gold = int(game_state.gold)
                    print(f"💰 {self.name} 存储了 {deposit_amount} 金币到主基地(地牢之心)")
                    print(
                        f"   📥 主基地: {old_gold} → {game_state.gold} (当前存储: {game_state.gold}/{game_state.max_gold_capacity})")

                    if self.carried_gold > 0:
                        print(f"⚠️ 主基地存储已满，剩余 {self.carried_gold} 金币无法存储")
                else:
                    print(f"⚠️ 主基地存储已满，无法存储金币")
            else:
                print(f"❌ {self.name} 无法访问游戏实例，无法存储金币")

    def _complete_current_project(self, result: Dict[str, Any]):
        """完成当前项目"""
        if not self.target_building:
            return

        building = self.target_building

        # 执行建筑完成逻辑
        try:
            completion_result = building.complete_construction()

            result['work_completed'].append({
                'type': 'construction',
                'building': building.name,
                'result': completion_result
            })

            # 标记建筑需要更新地图显示
            result['building_completed'] = {
                'building': building,
                'needs_map_update': True
            }

            # building_completed标志已设置，无需额外处理
        except Exception as e:
            print(f"❌ {self.name} 完成建筑时出错: {e}")

        result['events'].append(f"{self.name} 完成了 {building.name} 的建造")

        # 重置工作状态
        self.work_progress = 0.0
        self.target_building = None
        self.target_position = None
        self.last_deposit_time = 0.0
        self.deposit_count = 0  # 重置投入次数计数器

        # 返回空闲状态
        self.status = EngineerStatus.IDLE
        result['status_changed'] = True

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """执行特殊能力（由子类重写）"""
        return {'used': False, 'reason': 'not_implemented'}

    def _safe_move(self, new_x: float, new_y: float, game_map):
        """安全移动 - 只有在目标位置可通行时才移动"""
        if self._can_move_to_position(new_x, new_y, game_map):
            self.x = new_x
            self.y = new_y
            return True
        return False

    def _can_move_to_position(self, new_x: float, new_y: float, game_map) -> bool:
        """检查是否可以移动到指定位置 - 只能在已挖掘的地块移动"""
        # 转换为瓦片坐标
        tile_x = int(new_x // GameConstants.TILE_SIZE)
        tile_y = int(new_y // GameConstants.TILE_SIZE)

        # 边界检查
        if not (0 <= tile_x < GameConstants.MAP_WIDTH and 0 <= tile_y < GameConstants.MAP_HEIGHT):
            return False

        tile = game_map[tile_y][tile_x]
        # 只能在已挖掘的地块移动（地面或房间）
        from src.core.enums import TileType
        return tile.type == TileType.GROUND or tile.is_dug

    def get_status_for_indicator(self) -> str:
        """获取用于状态指示器的状态字符串"""
        status_mapping = {
            EngineerStatus.IDLE: 'idle',
            EngineerStatus.WANDERING: 'wandering',
            EngineerStatus.FETCHING_RESOURCES: 'moving',
            EngineerStatus.MOVING_TO_SITE: 'moving_to_site',
            EngineerStatus.CONSTRUCTING: 'constructing',
            EngineerStatus.REPAIRING: 'repairing',
            EngineerStatus.UPGRADING: 'upgrading',
            EngineerStatus.RETURNING_TO_BASE: 'returning'
        }
        return status_mapping.get(self.status, 'idle')

    def _get_building_required_gold(self, building) -> int:
        """获取建筑所需的金币数量"""
        if not building:
            return 0

        # 尝试从建筑配置获取成本
        try:
            # 优先从建筑实例的construction_cost_gold获取（这是从config.cost_gold复制的）
            if hasattr(building, 'construction_cost_gold'):
                return building.construction_cost_gold
            # 然后尝试从建筑配置获取cost_gold
            elif hasattr(building, 'config') and hasattr(building.config, 'cost_gold'):
                return building.config.cost_gold
            # 兼容旧代码：尝试从建筑配置获取cost
            elif hasattr(building, 'config') and hasattr(building.config, 'cost'):
                return building.config.cost
            elif hasattr(building, 'cost'):
                return building.cost
            else:
                # 根据建筑类型返回默认成本
                building_costs = {
                    'lair': 150,
                    'hatchery': 150,
                    'treasure_room': 100,
                    'library': 250,
                    'training_room': 200,
                    'workshop': 300,
                    'guard_post': 200,
                    'arrow_tower': 200,
                    'bridge': 15,
                    'door': 10
                }
                building_type = getattr(building, 'building_type', 'unknown')
                if hasattr(building_type, 'value'):
                    building_type = building_type.value
                return building_costs.get(str(building_type).lower(), 200)
        except:
            return 200  # 默认成本

    def _get_dungeon_heart_position(self):
        """获取地牢之心位置（考虑2x2大小）"""
        if hasattr(self, 'game_instance') and self.game_instance:
            heart_x, heart_y = self.game_instance.dungeon_heart_pos
            # 地牢之心是2x2建筑，返回所有4个块的中心位置
            positions = []
            for dy in range(2):
                for dx in range(2):
                    block_x = (heart_x + dx) * GameConstants.TILE_SIZE + \
                        GameConstants.TILE_SIZE // 2
                    block_y = (heart_y + dy) * GameConstants.TILE_SIZE + \
                        GameConstants.TILE_SIZE // 2
                    positions.append((block_x, block_y))
            return positions
        return None

    def render_status_indicator(self, screen, camera_x: int, camera_y: int):
        """渲染工程师状态指示器"""
        if not self.status_indicator:
            return

        # 计算屏幕位置
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        # 获取状态字符串
        state = self.get_status_for_indicator()

        # 使用通用的状态指示器渲染
        self.status_indicator.render(
            screen, screen_x, screen_y, self.size, state)


class EngineerRegistry:
    """工程师注册表"""

    # 工程师配置数据
    ENGINEER_CONFIGS = {
        EngineerType.BASIC: EngineerConfig(
            name="地精工程师",
            engineer_type=EngineerType.BASIC,
            cost=100,
            health=800,
            speed=25,  # 修正为基础速度25，符合文档规范
            build_efficiency=1.0,
            color=(50, 205, 50),  # 酸绿色
            size=14,
            level=2,
            max_concurrent_projects=1,
            repair_efficiency=0.5,
            upgrade_capability=False,
            special_abilities=["trap_building"],
            description="地精工程师，能够建造各种陷阱来防御地下城"
        ),
    }

    @classmethod
    def get_config(cls, engineer_type: EngineerType) -> Optional[EngineerConfig]:
        """获取工程师配置"""
        return cls.ENGINEER_CONFIGS.get(engineer_type)

    @classmethod
    def create_engineer(cls, engineer_type: EngineerType, x: float, y: float) -> Optional[Engineer]:
        """创建工程师实例"""
        config = cls.get_config(engineer_type)
        if not config:
            return None

        if engineer_type == EngineerType.BASIC:
            return BasicEngineer(x, y, engineer_type, config)
        else:
            return Engineer(x, y, engineer_type, config)


class BasicEngineer(Engineer):
    """基础工程师"""

    def __init__(self, x: float, y: float, engineer_type: EngineerType, config: EngineerConfig):
        super().__init__(x, y, engineer_type, config)

    def _execute_special_ability(self, ability_name: str, target=None) -> Dict[str, Any]:
        """基础工程师没有特殊能力"""
        return {'used': False, 'reason': 'no_special_abilities'}
