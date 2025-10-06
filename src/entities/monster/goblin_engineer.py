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
from src.entities.monsters import Monster
from src.entities.building import BuildingStatus
from src.managers.movement_system import MovementSystem
from src.managers.resource_manager import get_resource_manager
from src.utils.logger import game_logger
from src.ui.status_indicator import StatusIndicator


class EngineerType(Enum):
    """工程师类型"""
    BASIC = "basic"                    # 基础工程师
    SPECIALIST = "specialist"          # 专业工程师
    MASTER = "master"                  # 大师工程师


class EngineerStatus(Enum):
    """工程师状态枚举 - 备用定义"""
    IDLE = "idle"                      # 空闲
    WANDERING = "wandering"            # 游荡
    FETCHING_RESOURCES = "fetching_resources"  # 前往主基地获取资源
    MOVING_TO_SITE = "moving_to_site"  # 前往建造点
    CONSTRUCTING = "constructing"      # 建造中
    REPAIRING = "repairing"            # 修理中
    UPGRADING = "upgrading"            # 升级中
    RELOADING = "reloading"            # 装填中
    DEPOSITING_GOLD = "depositing_gold"  # 存储金币中
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
    resource_type: str = 'gold'        # 资源类型 ('gold' 或 'mana')


class Engineer(Monster):
    """工程师基类 - 继承自Monster"""

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

        # 战斗相关属性（继承自Creature但需要重新设置）
        self.is_enemy = False  # 工程师不是敌人
        self.attack_list = []  # 攻击列表
        self.in_combat = False  # 战斗状态
        self.last_combat_time = 0  # 最后战斗时间

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
        self.last_building_search_time = 0.0  # 上次查找建筑的时间
        self.waiting_start_time = 0.0  # 等待状态开始时间
        self.waiting_timeout = 5.0  # 等待超时时间（秒）
        self.status_indicator = StatusIndicator()

    def update(self, delta_time: float, game_map, creatures: List = None, heroes: List = None, effect_manager=None, building_manager=None, game_instance=None) -> Dict[str, Any]:
        """
        更新工程师状态 - 重写父类的update方法

        Args:
            delta_time: 时间增量（秒）
            game_map: 游戏地图
            creatures: 生物列表（父类兼容性）
            heroes: 英雄列表（父类兼容性）
            effect_manager: 特效管理器（父类兼容性）
            building_manager: 建筑管理器

        Returns:
            Dict: 更新结果
        """
        # 首先调用父类的update方法，包含状态切换器
        super().update(delta_time, creatures or [], game_map, effect_manager)

        current_time = time.time()
        delta_seconds = delta_time  # 游戏系统已统一使用秒为单位

        # 设置游戏实例引用（从building_manager获取，仅在未设置时）
        if not hasattr(self, 'game_instance') or not self.game_instance:
            if building_manager and hasattr(building_manager, 'game_instance'):
                self.game_instance = building_manager.game_instance
            elif building_manager and hasattr(building_manager, 'game_simulator'):
                self.game_instance = building_manager.game_simulator

        result = {
            'status_changed': False,
            'work_completed': [],
            'events': [],
            'building_completed': None  # 添加building_completed字段
        }

        # 检查等待超时
        self._check_waiting_timeout(current_time, result)

        # 记录状态变化
        if hasattr(self, '_last_debug_status') and self._last_debug_status != self.status:
            game_logger.info(
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
        elif self.status == EngineerStatus.RELOADING:
            self._update_reload_state(delta_seconds, result)
        elif self.status == EngineerStatus.DEPOSITING_GOLD:
            self._update_depositing_gold_state(delta_seconds, result)
        elif self.status == EngineerStatus.RETURNING_TO_BASE:
            self._update_returning_to_base_state(
                delta_seconds, game_map, result)

        # 如果状态发生变化，重置空闲时间
        if result.get('status_changed', False):
            self.idle_start_time = time.time()

        # 管理空闲状态（使用全局管理器，但保留原有的1秒超时逻辑作为备用）
        self._manage_idle_state(game_instance)

        # 如果工程师不再处于工作状态，从working_engineer列表中移除
        if (self.status != EngineerStatus.CONSTRUCTING and
            self.status != EngineerStatus.REPAIRING and
            self.status != EngineerStatus.UPGRADING and
            self.status != EngineerStatus.RELOADING and
            self.status != EngineerStatus.DEPOSITING_GOLD and
            self.target_building and
                self in self.target_building.working_engineer):
            self.target_building.working_engineer.remove(self)

        # 同步工程师状态到生物对象的state属性
        engineer_state = self.get_status_for_indicator()
        self.state = engineer_state

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
        # 检查工程师是否已达到最大项目数量限制
        if len(self.current_projects) >= self.max_concurrent_projects:
            game_logger.info(
                f"🔒 {self.name} 已达到最大项目数量限制 ({len(self.current_projects)}/{self.max_concurrent_projects})")
            return False

        # 如果工程师空闲且没有目标建筑，直接分配
        if self.status == EngineerStatus.IDLE and not self.target_building:
            self.target_building = building
            # 将项目添加到当前项目列表
            self.current_projects.append({
                'building': building,
                'type': 'construction',
                'priority': priority,
                'start_time': time.time()
            })
            # 将工程师添加到建筑的分配列表中（避免重复添加）
            if self not in building.assigned_engineers:
                building.assigned_engineers.append(self)
                game_logger.debug(f"📋 {self.name} 添加到建筑 {building.name} 的分配列表")
            else:
                game_logger.debug(f"📋 {self.name} 已在建筑 {building.name} 的分配列表中")
            game_logger.info(
                f"📋 {self.name} 接受建造任务: {building.name} (项目数: {len(self.current_projects)}/{self.max_concurrent_projects})")
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
            # 将工程师添加到建筑的分配列表中（避免重复添加）
            if self not in building.assigned_engineers:
                building.assigned_engineers.append(self)
                game_logger.debug(f"📋 {self.name} 添加到建筑 {building.name} 的分配列表")
            else:
                game_logger.debug(f"📋 {self.name} 已在建筑 {building.name} 的分配列表中")
            game_logger.info(f"🔧 {self.name} 接受修理任务: {building.name}")
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
            # 将工程师添加到建筑的分配列表中（避免重复添加）
            if self not in building.assigned_engineers:
                building.assigned_engineers.append(self)
                game_logger.debug(f"📋 {self.name} 添加到建筑 {building.name} 的分配列表")
            else:
                game_logger.debug(f"📋 {self.name} 已在建筑 {building.name} 的分配列表中")
            game_logger.info(f"⬆️ {self.name} 接受升级任务: {building.name}")
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
            game_logger.info(f"❌ {self.name} 取消任务: {building.name}")
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
        """更新空闲状态 - 使用新的分配器系统"""

        # 优先级1: 如果没有目标建筑，返回主基地将所有金币归还
        if not self.target_building and self.carried_gold > 0:
            game_logger.info(f"💰 [{self.name}] 没有目标建筑但携带金币，返回主基地")
            self.status = EngineerStatus.RETURNING_TO_BASE
            result['status_changed'] = True
            return

        # 优先级2: 检查是否已被分配器分配了任务
        # 如果工程师有target_building，说明分配器已经分配了任务
        if self.target_building:
            game_logger.info(
                f"✅ [{self.name}] 已被分配器分配任务: {self.target_building.name}")
            return

        # 优先级3: 如果没有被分配任务，进入游荡状态
        # 分配器系统会统一管理任务分配，工程师在游荡期间等待任务
        game_logger.info(f"🎲 [{self.name}] 没有任务分配，开始游荡...")
        self.status = EngineerStatus.WANDERING
        result['status_changed'] = True

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
        """更新游荡状态 - 游荡期间等待分配器分配任务"""

        # 优先级1: 检查是否已被分配器分配了任务
        if self.target_building:
            game_logger.info(
                f"🎯 [{self.name}] 游荡中被分配任务: {self.target_building.name}，转换到空闲状态处理")
            # 立即转换到空闲状态，让空闲状态处理建筑任务
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 优先级2: 如果没有被分配任务，继续进行游荡移动
        # 游荡期间等待分配器分配任务，工程师不需要自己寻找任务
        # 工程师游荡速度使用0.5倍速，符合文档规范
        MovementSystem.wandering_movement(
            self, delta_seconds, game_map, 0.5)

    def _determine_task_type(self, building) -> str:
        """根据建筑状态确定任务类型 - 调用建筑的API"""
        if hasattr(building, 'get_engineer_task_type'):
            return building.get_engineer_task_type()
        else:
            # 兼容旧代码，使用默认逻辑
            if building.status in [BuildingStatus.PLANNING, BuildingStatus.UNDER_CONSTRUCTION]:
                return 'construction'
            elif building.status == BuildingStatus.COMPLETED:
                if building.health < building.max_health:
                    return 'repair'
                else:
                    return 'idle'
            else:
                return 'construction'

    def _update_moving_state(self, delta_seconds: float, game_map, result: Dict[str, Any], building_manager=None):
        """更新移动状态"""

        if not self.target_building:
            game_logger.info(f"⚠️ [{self.name}] 移动状态但没有目标建筑，返回空闲")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 添加移动调试信息
        if not hasattr(self, '_move_debug_counter'):
            self._move_debug_counter = 0
        self._move_debug_counter += 1

        if self._move_debug_counter % 60 == 1:
            game_logger.info(
                f"🚶 [{self.name}] 移动中 -> {self.target_building.name} 位置:({self.x:.1f}, {self.y:.1f})px")

        # 检查目标建筑是否被其他工程师占用（每60帧检查一次，减少频率）
        if not hasattr(self, '_target_check_counter'):
            self._target_check_counter = 0
        self._target_check_counter += 1

        if self._target_check_counter % 60 == 0:  # 每60帧检查一次，减少频率
            if building_manager and building_manager._is_building_being_worked_on(self.target_building):
                game_logger.info(f"🔄 [{self.name}] 目标建筑被占用，寻找新目标")
                # 清除目标连线
                MovementSystem.clear_unit_target_lines(self.name)
                # 寻找新目标
                self.target_building = None
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return
            else:
                game_logger.info(
                    f"✅ [{self.name}] 目标建筑 {self.target_building.name} 未被占用，继续移动")

        # 使用新的分离式寻路+移动系统
        try:
            # 计算建筑位置 - Building的x,y已经是像素坐标
            building_x = self.target_building.x
            building_y = self.target_building.y
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
                self, target_pos, delta_seconds, game_map, "A_STAR", 1.0)
        except Exception as e:
            game_logger.info(f"❌ {self.name} 移动系统调用失败: {e}")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 手动检查是否真的到达目标位置
        if arrived:
            # 计算实际距离 - Building的x,y已经是像素坐标
            building_x = self.target_building.x
            building_y = self.target_building.y
            current_x, current_y = self.get_current_position()
            actual_distance = math.sqrt(
                (current_x - building_x) ** 2 + (current_y - building_y) ** 2)

            # 只有真正接近目标时才开始工作
            if actual_distance <= 20:  # 20像素的工作范围（增加20px避免建筑碰撞体积）
                # 只在移动状态时转换到建造状态，避免重复转换
                if self.status == EngineerStatus.MOVING_TO_SITE:
                    game_logger.info(
                        f"✅ {self.name} 到达建筑工作范围，距离: {actual_distance:.1f}px <= 20px")

                    # 再次检查建筑是否被其他工程师占用（竞争检查）
                    if building_manager and building_manager._is_building_being_worked_on(self.target_building):
                        game_logger.info(f"❌ {self.name} 建筑已被占用，寻找新目标")
                        # 清除目标连线
                        MovementSystem.clear_unit_target_lines(self.name)
                        # 寻找新目标
                        self.target_building = None
                        self.status = EngineerStatus.IDLE
                        result['status_changed'] = True
                        return

                    # 清除目标连线（到达目标后不再需要连线）
                    MovementSystem.clear_unit_target_lines(self.name)

                    # 新系统：根据任务类型开始相应的工作
                    if self.target_building:
                        game_logger.info(
                            f"{self.name} 目标建筑检查: {self.target_building.name if hasattr(self.target_building, 'name') else 'Unknown'}")
                        task_type = self._determine_task_type(
                            self.target_building)

                        if task_type == 'construction':
                            game_logger.info(
                                f"🔨 {self.name} 开始建造 {self.target_building.name}")
                            self.status = EngineerStatus.CONSTRUCTING
                        elif task_type == 'repair':
                            game_logger.info(
                                f"🔧 {self.name} 开始修理 {self.target_building.name}")
                            self.status = EngineerStatus.REPAIRING
                        elif task_type == 'reload':
                            game_logger.info(
                                f"🔫 {self.name} 开始装填 {self.target_building.name}")
                            self.status = EngineerStatus.RELOADING
                        elif task_type == 'gold_deposit':
                            game_logger.info(
                                f"💰 {self.name} 开始存入金币到 {self.target_building.name}")
                            self.status = EngineerStatus.DEPOSITING_GOLD  # 使用专门的金币存储状态
                        else:
                            game_logger.info(
                                f"🔨 {self.name} 开始建造 {self.target_building.name} (默认)")
                            self.status = EngineerStatus.CONSTRUCTING

                        self.work_start_time = time.time()
                        self.work_progress = 0.0
                        # 将工程师添加到建筑的working_engineer列表中
                        if self not in self.target_building.working_engineer:
                            self.target_building.working_engineer.append(self)
                        result['status_changed'] = True
                        game_logger.info(
                            f"{self.name} 状态转换完成，target_building: {self.target_building.name if self.target_building else 'None'}")
                    else:
                        game_logger.info(f"⚠️ {self.name} 到达工作范围但没有目标建筑")
                        self.status = EngineerStatus.IDLE
                        result['status_changed'] = True

    def _update_construction_state(self, delta_seconds: float, result: Dict[str, Any]):
        """更新建造状态 - 根据任务类型分发到具体处理方法"""
        if not self.target_building:
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 根据当前状态直接调用对应的处理方法
        if self.status == EngineerStatus.CONSTRUCTING:
            self._update_construction_work(delta_seconds, result)
        elif self.status == EngineerStatus.RELOADING:
            self._update_reload_work(delta_seconds, result)
        elif self.status == EngineerStatus.DEPOSITING_GOLD:
            self._update_depositing_gold_state(delta_seconds, result)
        elif self.status == EngineerStatus.REPAIRING:
            self._update_repair_state(delta_seconds, result)
        else:
            game_logger.info(f"❌ {self.name} 未知工作状态: {self.status}")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True

    def _update_construction_work(self, delta_seconds: float, result: Dict[str, Any]):
        """处理建造工作 - 直接处理建造逻辑"""
        if not self.target_building:
            return

        # 检查建筑是否还需要建造
        if self.target_building.status == BuildingStatus.COMPLETED:
            # 建筑已完成，检查是否需要其他任务
            task_type = self._determine_task_type(self.target_building)
            if task_type != 'construction':
                # 切换到其他任务类型
                if task_type == 'gold_deposit':
                    self.status = EngineerStatus.DEPOSITING_GOLD
                elif task_type == 'reload':
                    self.status = EngineerStatus.RELOADING
                elif task_type == 'repair':
                    self.status = EngineerStatus.REPAIRING
                else:
                    # 没有其他任务，完成当前项目
                    self._complete_current_project(result)
                result['status_changed'] = True
                return

        # 检查是否有金币可以存放
        if self.carried_gold <= 0:
            game_logger.info(f"💸 {self.name} 建造时金币耗尽，前往主基地获取金币")
            self._handle_insufficient_gold(result)
            return

        # 获取建筑所需的总金币
        required_gold = self._get_building_required_gold(self.target_building)

        # 初始化工程师的投入计数（如果没有的话）
        if not hasattr(self, 'deposit_count'):
            self.deposit_count = 0
            game_logger.info(
                f"🏗️ {self.name} 开始建造 {self.target_building.name}")
            game_logger.info(f"   💰 建筑成本: {required_gold} 金币")
            game_logger.info(f"   💼 工程师携带: {self.carried_gold} 金币")
            game_logger.info(f"   ⚡ 建造速度: {self.deposit_rate} 金币/秒")

        # 执行金币投入 - 直接处理建造逻辑
        current_time = time.time()
        if self.last_deposit_time == 0:
            self.last_deposit_time = current_time

        # 检查时间间隔
        time_since_last_deposit = current_time - self.last_deposit_time
        if time_since_last_deposit < self.once_time:
            return

        gold_to_deposit = min(self.deposit_rate, self.carried_gold)
        if gold_to_deposit > 0:
            # 检测是否有其他工程师正在建造同一个建筑
            other_engineers = [eng for eng in self.target_building.assigned_engineers
                               if eng != self and eng.status == EngineerStatus.CONSTRUCTING]

            if other_engineers:
                # 有其他工程师正在建造，主动退出
                game_logger.info(
                    f"🔓 {self.name} 发现其他工程师正在建造 {self.target_building.name}，主动退出建造")
                game_logger.info(
                    f"   👥 其他工程师: {[eng.name for eng in other_engineers]}")

                # 从建筑分配列表中移除自己
                if self in self.target_building.assigned_engineers:
                    self.target_building.assigned_engineers.remove(self)
                    game_logger.info(
                        f"🔓 {self.name} 从建筑 {self.target_building.name} 的分配列表中移除")

                # 返回空闲状态
                self.status = EngineerStatus.IDLE
                self.target_building = None
                result['status_changed'] = True
                return

            # 直接处理建造投入
            actual_deposited = min(
                gold_to_deposit, required_gold - self.target_building.construction_cost_paid)

            if actual_deposited > 0:
                # 扣除工程师金币
                self.carried_gold -= actual_deposited
                self.deposit_count += 1
                self.last_deposit_time = current_time

                # 更新建筑的建造进度
                self.target_building.construction_cost_paid += actual_deposited
                self.target_building.construction_progress = self.target_building.construction_cost_paid / required_gold

                # 更新建造进度和血量
                self._update_construction_progress(actual_deposited)

                # 检查是否完成建造
                if self.target_building.construction_cost_paid >= required_gold:
                    # 标记建筑为完成状态
                    self.target_building.status = BuildingStatus.COMPLETED
                    self.target_building.health = self.target_building.max_health

                    game_logger.info(
                        f"🎉 ✅ {self.name} 完成了 {self.target_building.name} 的建造!")
                    game_logger.info(
                        f"🏗️ 建筑 {self.target_building.name} 建造完成，状态: {self.target_building.status}")
                    game_logger.info(
                        f"   🏗️ 总投入: {self.target_building.construction_cost_paid} 金币")
                    game_logger.info(f"   💼 工程师剩余: {self.carried_gold} 金币")
                    game_logger.info(f"   📊 总投入次数: {self.deposit_count} 次")

                    # 检查是否需要其他任务
                    task_type = self._determine_task_type(self.target_building)
                    if task_type == 'gold_deposit':
                        # 继续金币存储任务
                        self.status = EngineerStatus.DEPOSITING_GOLD
                        result['status_changed'] = True
                    else:
                        # 完成当前项目
                        self._complete_current_project(result)

    def _update_construction_progress(self, gold_deposited: int):
        """
        更新建造进度和血量

        Args:
            gold_deposited: 投入的金币数量
        """
        if not self.target_building:
            return

        # 更新血量 - 根据建造进度按比例增加
        if hasattr(self.target_building, 'max_health') and hasattr(self.target_building, 'health'):
            if hasattr(self.target_building, 'construction_progress'):
                progress = self.target_building.construction_progress
                target_health = int(self.target_building.max_health * progress)
                self.target_building.health = target_health

    def _handle_insufficient_gold(self, result: Dict[str, Any]):
        """
        处理金币不足的情况 - 前往主基地获取金币

        Args:
            result: 结果字典
        """
        # 检查主基地是否有足够金币
        if hasattr(self, 'game_instance') and self.game_instance:
            if hasattr(self.game_instance, 'dungeon_heart') and self.game_instance.dungeon_heart:
                dungeon_heart = self.game_instance.dungeon_heart
                if hasattr(dungeon_heart, 'stored_gold') and dungeon_heart.stored_gold > 0:
                    game_logger.info(
                        f"💰 主基地有足够金币 ({dungeon_heart.stored_gold}/120)，前往获取")
                    # 转换状态为获取资源
                    self.status = EngineerStatus.FETCHING_RESOURCES
                    result['status_changed'] = True
                    return

        # 如果没有主基地或金币不足，标记为需要等待
        game_logger.info(f"❌ 主基地金币不足，工程师等待")
        self.status = EngineerStatus.IDLE
        result['status_changed'] = True

    def _update_reload_work(self, delta_seconds: float, result: Dict[str, Any]):
        """处理装填工作 - 为箭塔等建筑装填弹药"""
        if not self.target_building:
            return

        # 检查建筑是否还需要装填
        if not self.target_building.can_accept_gold():
            game_logger.info(
                f"✅ {self.name} 建筑 {self.target_building.name} 不再需要装填，任务完成")
            self._complete_current_project(result)
            return

        # 检查是否有金币可以存放
        if self.carried_gold <= 0:
            game_logger.info(f"💸 {self.name} 装填时金币耗尽，前往主基地获取金币")
            self._handle_insufficient_gold(result)
            return

        # 获取建筑所需的总金币
        required_gold = self._get_building_required_gold(self.target_building)

        # 如果不需要装填，完成任务
        if required_gold <= 0:
            game_logger.info(
                f"✅ {self.name} 建筑 {self.target_building.name} 不需要装填")
            self._complete_current_project(result)
            return

        # 检测是否有其他工程师正在建造同一个建筑
        other_engineers = [eng for eng in self.target_building.assigned_engineers
                           if eng != self and eng.status == EngineerStatus.CONSTRUCTING]

        if other_engineers:
            # 有其他工程师正在建造，主动退出
            game_logger.info(
                f"🔓 {self.name} 发现其他工程师正在建造 {self.target_building.name}，主动退出装填")
            game_logger.info(
                f"   👥 其他工程师: {[eng.name for eng in other_engineers]}")

            # 从建筑分配列表中移除自己
            if self in self.target_building.assigned_engineers:
                self.target_building.assigned_engineers.remove(self)
                game_logger.info(
                    f"🔓 {self.name} 从建筑 {self.target_building.name} 的分配列表中移除")

            # 返回空闲状态
            self.status = EngineerStatus.IDLE
            self.target_building = None
            result['status_changed'] = True
            return

        # 执行金币投入（转换为弹药）- 使用建筑的专门装填API
        if hasattr(self.target_building, 'accept_ammunition_reload'):
            # 计算本次可以存放的金币数量
            current_time = time.time()
            if self.last_deposit_time == 0:
                self.last_deposit_time = current_time

            # 检查时间间隔
            time_since_last_deposit = current_time - self.last_deposit_time
            if time_since_last_deposit < self.once_time:
                return

            # 根据建筑需求和工程师能力计算装填量
            gold_to_deposit = min(
                self.deposit_rate, self.carried_gold, required_gold)
            if gold_to_deposit > 0:
                # 调用建筑的装填API
                deposit_result = self.target_building.accept_ammunition_reload(
                    self, gold_to_deposit)

                if deposit_result.get('deposited', False):
                    # 存储成功，扣除工程师金币
                    actual_deposited = deposit_result.get(
                        'amount_deposited', 0)
                    self.carried_gold -= actual_deposited
                    self.deposit_count += 1
                    self.last_deposit_time = current_time

                    # 检查是否完成装填
                    if hasattr(self.target_building, 'current_ammunition') and hasattr(self.target_building, 'max_ammunition'):
                        if self.target_building.current_ammunition >= self.target_building.max_ammunition:
                            game_logger.info(
                                f"🎉 ✅ {self.name} 完成了 {self.target_building.name} 的装填!")
                            game_logger.info(
                                f"   🏹 弹药: {self.target_building.current_ammunition}/{self.target_building.max_ammunition}")
                            game_logger.info(
                                f"   💼 工程师剩余: {self.carried_gold} 金币")
                            self._complete_current_project(result)

    def _update_depositing_gold_state(self, delta_seconds: float, result: Dict[str, Any]):
        """更新金币存储状态 - 专门处理金币存储任务，需要工作2秒钟"""
        if not self.target_building:
            game_logger.info(f"❌ {self.name} 金币存储状态但没有目标建筑，返回空闲")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 检查建筑是否还需要金币存储
        if not self.target_building.can_accept_gold():
            game_logger.info(
                f"✅ {self.name} 建筑 {self.target_building.name} 不再需要金币存储，任务完成")
            self._complete_current_project(result)
            return

        # 检查是否有金币可以存放
        if self.carried_gold <= 0:
            game_logger.info(f"💸 {self.name} 存储金币时金币耗尽，前往主基地获取金币")
            self._handle_insufficient_gold(result)
            return

        # 检测是否有其他工程师正在建造同一个建筑
        other_engineers = [eng for eng in self.target_building.assigned_engineers
                           if eng != self and eng.status == EngineerStatus.CONSTRUCTING]

        if other_engineers:
            # 有其他工程师正在建造，主动退出
            game_logger.info(
                f"🔓 {self.name} 发现其他工程师正在建造 {self.target_building.name}，主动退出金币存储")
            game_logger.info(
                f"   👥 其他工程师: {[eng.name for eng in other_engineers]}")

            # 从建筑分配列表中移除自己
            if self in self.target_building.assigned_engineers:
                self.target_building.assigned_engineers.remove(self)
                game_logger.info(
                    f"🔓 {self.name} 从建筑 {self.target_building.name} 的分配列表中移除")

            # 返回空闲状态
            self.status = EngineerStatus.IDLE
            self.target_building = None
            result['status_changed'] = True
            return

        # 初始化工作开始时间（如果没有的话或者为None）
        if not hasattr(self, 'gold_deposit_start_time') or self.gold_deposit_start_time is None:
            self.gold_deposit_start_time = time.time()
            game_logger.info(f"💰 {self.name} 开始金币存储工作，需要工作2秒钟")

        # 检查是否已经工作了2秒钟
        current_time = time.time()
        work_duration = current_time - self.gold_deposit_start_time
        required_work_time = 2.0  # 需要工作2秒钟

        if work_duration >= required_work_time:
            # 工作完成，执行金币存储
            # 获取建筑所需的总金币
            required_gold = self._get_building_required_gold(
                self.target_building)

            # 根据建筑需求和工程师能力计算投入量
            gold_to_deposit = min(self.carried_gold, required_gold)
            if gold_to_deposit > 0:
                # 判断是永久存储还是临时投入
                if (hasattr(self.target_building, 'accept_gold_deposit') and
                        self.target_building.accept_gold_deposit(self, 0).get('deposited', False) != False):
                    # 永久存储建筑（地牢之心、金库）
                    deposit_result = self.target_building.accept_gold_deposit(
                        self, gold_to_deposit)
                    action_type = "存储"
                elif hasattr(self.target_building, 'accept_gold_investment'):
                    # 临时投入建筑（魔法祭坛、兽人巢穴、恶魔巢穴）
                    deposit_result = self.target_building.accept_gold_investment(
                        self, gold_to_deposit)
                    action_type = "投入"
                else:
                    # 回退到旧API（兼容性）
                    deposit_result = self.target_building.accept_gold_deposit(
                        self, gold_to_deposit)
                    action_type = "存储"

                if deposit_result.get('deposited', False):
                    # 存储成功，扣除工程师金币
                    actual_deposited = deposit_result.get(
                        'amount_deposited', 0)
                    if actual_deposited is not None:
                        self.carried_gold -= actual_deposited
                        self.deposit_count += 1

                        game_logger.info(
                            f"💰 {self.name} 完成了 {self.target_building.name} 的金币{action_type}!")
                        game_logger.info(
                            f"   💰 {action_type}金币: {actual_deposited}")
                        game_logger.info(f"   💼 工程师剩余: {self.carried_gold} 金币")
                        game_logger.info(f"   ⏱️ 工作时间: {work_duration:.1f}秒")
                        game_logger.info(
                            f"   📝 {deposit_result.get('message', '')}")

                        # 重置工作开始时间，准备下次工作
                        self.gold_deposit_start_time = None

                        # 检查是否还需要继续存储
                        if not self.target_building.can_accept_gold() or self.carried_gold <= 0:
                            # 建筑不再需要存储或工程师没有金币了，完成任务
                            game_logger.info(
                                f"✅ {self.name} 建筑 {self.target_building.name} 不再需要金币存储，任务完成")
                            self._complete_current_project(result)
                        return
                    else:
                        # 存储失败
                        reason = deposit_result.get('reason', 'unknown')
                        message = deposit_result.get('message', '未知原因')
                        game_logger.info(f"❌ {self.name} 金币存储失败: {message}")

                        if reason in ['already_full', 'mana_generation_mode', 'locked', 'training', 'summoning']:
                            # 建筑状态不允许存储，完成任务
                            game_logger.info(f"✅ {self.name} 建筑状态不允许存储，任务完成")
                            self.gold_deposit_start_time = None
                            self._complete_current_project(result)
                            return
                        else:
                            # 其他原因，返回空闲状态
                            game_logger.info(f"⚠️ {self.name} 存储失败，返回空闲状态")
                            self.gold_deposit_start_time = None
                            self.status = EngineerStatus.IDLE
                            result['status_changed'] = True
                            return
                else:
                    # 没有金币可以存储，但工作已完成
                    game_logger.info(f"✅ {self.name} 金币存储工作完成，但没有金币需要存储")
                    self.gold_deposit_start_time = None
                    self._complete_current_project(result)
                    return
            else:
                game_logger.info(
                    f"❌ {self.name} 建筑 {self.target_building.name} 不支持金币存储功能")
                self.gold_deposit_start_time = None
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return
        else:
            # 还在工作中，显示工作进度
            remaining_time = required_work_time - work_duration
            if not hasattr(self, '_last_progress_log_time') or current_time - self._last_progress_log_time >= 0.5:
                progress_percent = (work_duration / required_work_time) * 100
                game_logger.info(
                    f"💰 {self.name} 金币存储工作中... {progress_percent:.0f}% ({remaining_time:.1f}秒剩余)")
                self._last_progress_log_time = current_time

    def _update_repair_state(self, delta_seconds: float, result: Dict[str, Any]):
        """更新修理状态 - 使用工程师携带的金币进行修复"""
        if not self.target_building:
            game_logger.info(f"❌ {self.name} 修理状态但没有目标建筑，返回空闲")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 初始化修理进度（如果没有的话）
        if not hasattr(self, 'repair_progress'):
            self.repair_progress = 0.0
            self.repair_deposit_count = 0
            game_logger.info(f"🔧 {self.name} 开始修理 {self.target_building.name}")
            game_logger.info(
                f"   💰 建筑建造成本: {self.target_building.config.cost_gold} 金币")
            game_logger.info(f"   💼 工程师携带: {self.carried_gold} 金币")
            game_logger.info(f"   ⚡ 修理速度: {self.deposit_rate} 金币/秒")

        current_time = time.time()
        if self.last_deposit_time == 0:
            self.last_deposit_time = current_time

        # 优化时间间隔：每1秒投入金币进行修理
        time_since_last_deposit = current_time - self.last_deposit_time
        if time_since_last_deposit >= 1.0:  # 每1秒投入
            # 计算每次投入的金币数量（与建造相同）
            gold_to_deposit = min(self.deposit_rate, self.carried_gold)
            if gold_to_deposit > 0:
                # 使用建筑的专门修复API
                if hasattr(self.target_building, 'accept_repair_gold'):
                    repair_result = self.target_building.accept_repair_gold(
                        self, gold_to_deposit)

                    if repair_result.get('deposited', False):
                        # 修复成功，扣除工程师金币
                        actual_cost = repair_result.get('amount_deposited', 0)
                        actual_repair = repair_result.get('health_repaired', 0)

                        self.carried_gold -= actual_cost
                        self.repair_progress += actual_repair / self.target_building.max_health
                        self.repair_deposit_count += 1
                        self.last_deposit_time = current_time

                    # 每5次投入显示一次详细日志
                    if self.repair_deposit_count % 5 == 0:
                        progress_percent = (
                            self.target_building.health / self.target_building.max_health) * 100
                        game_logger.info(
                            f"🔧 {self.name} 修复进度: {progress_percent:.1f}% ({self.target_building.health}/{self.target_building.max_health}) - 第{self.repair_deposit_count}次投入")
                        game_logger.info(f"   💼 工程师剩余金币: {self.carried_gold}")
                        game_logger.info(
                            f"   💰 本次花费: {actual_cost} 金币，修复: {actual_repair} 点生命值")

                    result['events'].append(
                        f"{self.name} 修理了 {actual_repair} 点生命值，花费 {actual_cost} 金币")

                    # 检查是否完全修复
                    if self.target_building.health >= self.target_building.max_health:
                        game_logger.info(
                            f"🎉 ✅ {self.name} 完成了 {self.target_building.name} 的修复!")
                        game_logger.info(
                            f"   🏥 建筑生命值: {self.target_building.health}/{self.target_building.max_health}")
                        game_logger.info(f"   💼 工程师剩余金币: {self.carried_gold}")
                        self._complete_current_project(result)
                        return
                else:
                    # 无法修复更多血量（可能已经满血）
                    game_logger.info(f"✅ {self.name} 建筑已满血，无需继续修复")
                    self._complete_current_project(result)
                    return
            else:
                # 金币不足，检查是否需要获取更多金币
                game_logger.info(f"💸 {self.name} 修理时金币耗尽，前往主基地获取金币")

                # 检查主基地是否有足够的金币
                if hasattr(self, 'game_instance') and self.game_instance:
                    # 使用新的修复API计算修理成本
                    repair_cost_estimate = self._get_repair_required_gold(
                        self.target_building)
                    # 使用ResourceManager检查资源
                    resource_manager = get_resource_manager(self.game_instance)
                    available_gold = resource_manager.get_total_gold().available

                    if available_gold >= repair_cost_estimate:
                        game_logger.info(
                            f"💰 主基地有足够金币 ({available_gold}/{repair_cost_estimate})，前往获取")
                        self.status = EngineerStatus.FETCHING_RESOURCES
                        result['status_changed'] = True
                        return
                    else:
                        game_logger.info(
                            f"🚫 主基地金币不足 ({available_gold}/{repair_cost_estimate})，放弃修理")
                        self.target_building = None
                        self.status = EngineerStatus.IDLE
                        result['status_changed'] = True
                        return
                else:
                    game_logger.info(f"❌ 无法访问游戏实例，放弃修理")
                    self.target_building = None
                    self.status = EngineerStatus.IDLE
                    result['status_changed'] = True
                    return

            # 更新时间戳（只有在尝试修复后才更新）
            self.last_deposit_time = current_time

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

    def _update_reload_state(self, delta_seconds: float, result: Dict[str, Any]):
        """更新装填状态 - 一次性将所有金币用于装填弹药"""
        if not self.target_building:
            game_logger.info(f"❌ {self.name} 装填状态但没有目标建筑，返回空闲")
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 检查是否有金币可以用于装填
        if self.carried_gold <= 0:
            game_logger.info(f"💸 {self.name} 装填时金币耗尽，前往主基地获取金币")

            # 检查主基地是否有足够的金币
            if hasattr(self, 'game_instance') and self.game_instance:
                # 装填需要金币，估算装填成本
                reload_cost_estimate = 60  # 默认最大弹药值
                if hasattr(self.target_building, 'max_ammunition'):
                    reload_cost_estimate = self.target_building.max_ammunition
                # 使用ResourceManager检查资源
                resource_manager = get_resource_manager(self.game_instance)
                available_gold = resource_manager.get_total_gold().available

                if available_gold >= reload_cost_estimate:
                    game_logger.info(
                        f"💰 主基地有足够金币 ({available_gold}/{reload_cost_estimate})，前往获取")
                    self.status = EngineerStatus.FETCHING_RESOURCES
                    result['status_changed'] = True
                    return
                else:
                    game_logger.info(
                        f"🚫 主基地金币不足 ({available_gold}/{reload_cost_estimate})，放弃装填")
                    # 放弃当前装填任务
                    self.target_building = None
                    self.status = EngineerStatus.RETURNING_TO_BASE
                    result['status_changed'] = True
                    return
            else:
                game_logger.info(f"❌ 无法访问游戏实例，放弃装填")
                self.target_building = None
                self.status = EngineerStatus.IDLE
                result['status_changed'] = True
                return

        # 检查目标建筑是否支持弹药装填
        if not hasattr(self.target_building, 'accept_ammunition_reload'):
            game_logger.info(f"❌ {self.name} 目标建筑不支持弹药装填")
            self.target_building = None
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            return

        # 执行装填 - 一次性将所有金币用于装填
        game_logger.info(f"🔫 {self.name} 开始装填 {self.target_building.name}")
        game_logger.info(f"   💰 工程师携带: {self.carried_gold} 金币")
        game_logger.info(
            f"   🎯 箭塔当前弹药: {self.target_building.current_ammunition}/{self.target_building.max_ammunition}")

        # 使用专用的弹药装填API
        deposit_result = self.target_building.accept_ammunition_reload(
            self, self.carried_gold)

        if deposit_result['deposited']:
            # 扣除工程师的金币
            amount_deposited = deposit_result.get('amount_deposited', 0)
            if amount_deposited is None:
                game_logger.info(
                    f"❌ {self.name} 装填结果异常: amount_deposited为None")
                amount_deposited = 0
            self.carried_gold -= amount_deposited

            game_logger.info(
                f"🎉 ✅ {self.name} 完成了 {self.target_building.name} 的装填!")
            game_logger.info(
                f"   🔫 装填弹药: {deposit_result['ammunition_added']} 发")
            game_logger.info(
                f"   💰 消耗金币: {amount_deposited} 金币")
            game_logger.info(
                f"   🎯 箭塔弹药: {deposit_result['old_ammunition']} -> {deposit_result['new_ammunition']}")
            game_logger.info(f"   💼 工程师剩余: {self.carried_gold} 金币")

            result['events'].append(
                f"{self.name} 装填了 {deposit_result['ammunition_added']} 发弹药，消耗 {amount_deposited} 金币")

            # 装填完成，返回基地
            self._complete_current_project(result)
            return
        else:
            game_logger.info(f"❌ {self.name} 装填失败：{deposit_result['reason']}")
            result['events'].append(
                f"{self.name} 装填失败：{deposit_result['message']}")

            # 装填失败，返回基地
            self.target_building = None
            self.status = EngineerStatus.RETURNING_TO_BASE
            result['status_changed'] = True
            return

    def _update_fetching_resources_state(self, delta_seconds: float, game_map, result: Dict[str, Any]):
        """更新获取资源状态 - 前往主基地获取金币"""
        dungeon_heart_positions = self._get_dungeon_heart_position()
        if not dungeon_heart_positions:
            game_logger.info(f"❌ {self.name} 无法找到主基地位置")
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
            game_logger.info(
                f"🏠 [{self.name}] 前往主基地 - 当前位置: ({self.x:.1f}, {self.y:.1f}), 目标: ({closest_position[0]:.1f}, {closest_position[1]:.1f}), 距离: {distance:.1f}px")

        if distance > 20:  # 还没到达主基地（恢复正常的交互范围）
            # 使用新的分离式寻路+移动系统
            MovementSystem.pathfind_and_move(
                self, closest_position, delta_seconds, game_map, "A_STAR", 1.0)
        else:
            # 到达主基地，获取金币
            game_logger.info(
                f"🏠 {self.name} 到达主基地，距离: {distance:.1f}px <= 20px")

            # 工程师从主基地获取金币时总是补充到最大值60
            max_carry_gold = min(60, self.max_carry_capacity)
            gold_to_fetch = max_carry_gold - self.carried_gold

            if gold_to_fetch > 0:
                # 从游戏资源中获取金币
                target_name = self.target_building.name if self.target_building else "未知建筑"
                game_logger.info(
                    f"🏦 {self.name} 开始从主基地获取金币 - 目标建筑: {target_name}")
                game_logger.info(
                    f"📊 资源状态: 当前携带 {self.carried_gold}/{max_carry_gold}, 计划获取 {gold_to_fetch} 金币补充到最大值")

                if hasattr(self, 'game_instance') and self.game_instance:
                    # 使用ResourceManager检查资源
                    resource_manager = get_resource_manager(self.game_instance)
                    available_gold = resource_manager.get_total_gold().available
                    actual_fetch = min(gold_to_fetch, available_gold)

                    game_logger.info(
                        f"🏛️ 主基地金库状态: {available_gold} 金币可用, 实际获取 {actual_fetch} 金币")

                    if actual_fetch > 0:
                        # 执行金币转移 - 使用ResourceManager
                        old_carried_gold = self.carried_gold

                        # 消耗金币
                        gold_result = resource_manager.consume_gold(
                            actual_fetch)
                        if gold_result['success']:
                            self.carried_gold += actual_fetch
                            game_logger.info(f"💰 ✅ {self.name} 成功从主基地获取金币!")
                            game_logger.info(f"   📤 主基地: 消耗 {actual_fetch} 金币")
                            game_logger.info(
                                f"   📥 工程师: {old_carried_gold} → {self.carried_gold} (+{actual_fetch})")
                            game_logger.info(
                                f"   💼 携带状态: {self.carried_gold}/{self.max_carry_capacity} ({self.carried_gold/self.max_carry_capacity*100:.1f}%)")
                        else:
                            game_logger.info(f"❌ 金币消耗失败: {gold_result}")

                        # 成功获取金币，继续建造
                        if self.target_building:
                            game_logger.info(
                                f"🔙 {self.name} 获取资源完成，返回建筑 {self.target_building.name}")
                            self.status = EngineerStatus.MOVING_TO_SITE
                            result['status_changed'] = True
                            return
                        else:
                            self.status = EngineerStatus.IDLE
                            result['status_changed'] = True
                            game_logger.info(f"⚠️ {self.name} 没有目标建筑，返回空闲状态")
                            return
                    else:
                        game_logger.info(f"💸 ❌ {self.name} 主基地金币不足!")
                        game_logger.info(
                            f"   🏛️ 可用金币: {available_gold}, 需要金币: {gold_to_fetch}")

                        # 主基地金币不足，放弃当前目标建筑
                        if self.target_building:
                            game_logger.info(
                                f"🚫 {self.name} 主基地金币不足，放弃目标建筑 {self.target_building.name}")
                            self.target_building = None

                        # 如果有携带金币，返回基地存储
                        if self.carried_gold > 0:
                            game_logger.info(
                                f"💾 {self.name} 携带 {self.carried_gold} 金币，返回基地存储")
                            self.status = EngineerStatus.RETURNING_TO_BASE
                            result['status_changed'] = True
                            return
                        else:
                            # 没有金币也没有目标，进入空闲状态
                            self.status = EngineerStatus.IDLE
                            result['status_changed'] = True
                            game_logger.info(
                                f"😴 {self.name} 金币不足且无携带金币，进入空闲状态")
                            return
                else:
                    game_logger.info(f"❌ {self.name} 无法访问游戏实例，无法获取金币")
                    # 无法访问游戏实例，返回空闲状态
                    self.target_building = None
                    self.status = EngineerStatus.IDLE
                    result['status_changed'] = True
                    return
            else:
                # 获取建筑所需金币数量
                building_required_gold = self._get_building_required_gold(
                    self.target_building) if self.target_building else 0
                game_logger.info(
                    f"✅ {self.name} 金币充足，无需获取更多金币 (携带: {self.carried_gold}/{building_required_gold})")

                # 转换到移动到建筑状态
                if self.target_building:
                    # 获取资源期间不锁定建筑，直接返回建筑进行竞争
                    game_logger.info(
                        f"🔙 {self.name} 获取资源完成，返回建筑 {self.target_building.name}")
                    self.status = EngineerStatus.MOVING_TO_SITE
                    result['status_changed'] = True
                    return
                else:
                    self.status = EngineerStatus.IDLE
                    result['status_changed'] = True
                    game_logger.info(f"⚠️ {self.name} 没有目标建筑，返回空闲状态")
                    return

    def _update_returning_to_base_state(self, delta_seconds: float, game_map, result: Dict[str, Any]):
        """更新返回主基地状态 - 存储剩余金币"""
        # 寻找最近的存储点（金库或主基地）
        storage_target = self._find_nearest_storage()
        if not storage_target:
            game_logger.info(f"❌ {self.name} 无法找到存储点，进入空闲状态")
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
                self, target_pos, delta_seconds, game_map, "A_STAR", 1.0)
        else:
            # 到达存储点，存储金币
            game_logger.info(
                f"🏠 {self.name} 到达存储点，距离: {distance:.1f}px <= 20px")

            if self.carried_gold > 0:
                game_logger.info(f"🏦 {self.name} 开始向存储点存储剩余金币")
                game_logger.info(f"💼 当前携带: {self.carried_gold} 金币")

                # 存储到指定存储点
                self._deposit_gold_to_storage(storage_target)
            else:
                game_logger.info(f"💼 {self.name} 没有剩余金币需要存储")

            # 转换到空闲状态
            self.status = EngineerStatus.IDLE
            result['status_changed'] = True
            game_logger.info(f"😴 {self.name} 完成存储，进入空闲状态")

    def _find_nearest_storage(self) -> Optional[Dict[str, Any]]:
        """寻找最近的存储点（仅金库或主基地）"""
        # 寻找金库
        nearest_treasury = None
        min_distance = float('inf')

        if hasattr(self, 'game_instance') and self.game_instance:
            # 检查建筑管理器中的金库
            if hasattr(self.game_instance, 'building_manager'):
                for building in self.game_instance.building_manager.buildings:
                    # 只选择金库（treasury）
                    if (hasattr(building, 'building_type') and
                        building.building_type.value == 'treasury' and
                            building.is_active and not building.is_full()):

                        # Building的x,y已经是像素坐标
                        building_pixel_x = building.x
                        building_pixel_y = building.y

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

    def _is_storage_full(self, building) -> bool:
        """检查建筑存储是否已满（仅用于金库）"""
        if not building.can_accept_gold():
            return True

        # 仅检查金库
        if hasattr(building, 'building_type'):
            if building.building_type.value == 'treasury':
                return building.is_full()

        return True

    def _deposit_gold_to_storage(self, storage_target: Dict[str, Any]):
        """存储金币到指定存储点（使用 ResourceManager API）- 仅支持金库和主基地"""
        if not hasattr(self, 'game_instance') or not self.game_instance:
            game_logger.info(f"❌ {self.name} 无法访问游戏实例，无法存储金币")
            return

        resource_manager = get_resource_manager(self.game_instance)

        carried_gold_int = int(self.carried_gold)
        if carried_gold_int <= 0:
            return

        if storage_target['type'] == 'treasury':
            # 存储到金库 - 使用专用的金币存储API
            treasury = storage_target['building']
            if treasury and hasattr(treasury, 'accept_gold_deposit'):
                result = treasury.accept_gold_deposit(self, carried_gold_int)
                if result['deposited']:
                    amount_deposited = result.get('amount_deposited', 0)
                    if amount_deposited is None:
                        game_logger.info(
                            f"❌ {self.name} 存储结果异常: amount_deposited为None")
                        amount_deposited = 0
                    self.carried_gold -= amount_deposited
                    game_logger.info(
                        f"💰 {self.name} 存储了 {amount_deposited} 金币到金库({treasury.name}) 位置({treasury.x},{treasury.y})")
                    game_logger.info(f"   📝 {result['message']}")
                else:
                    game_logger.info(
                        f"⚠️ 金库({treasury.name}) 在位置({treasury.x},{treasury.y}) 无法存储金币: {result['message']}")
            else:
                game_logger.info(f"❌ 金库不可用，无法存储金币")
        else:
            # 存储到主基地 - 使用 ResourceManager API
            result = resource_manager.add_gold(
                carried_gold_int, self.game_instance.dungeon_heart)

            if result['success']:
                amount = result.get('amount', 0)
                if amount is None:
                    game_logger.info(f"❌ {self.name} 主基地存储结果异常: amount为None")
                    amount = 0
                self.carried_gold -= amount
                game_logger.info(
                    f"💰 {self.name} 存储了 {amount} 金币到主基地(地牢之心)")
                game_logger.info(
                    f"   📥 主基地: {result['old_amount']} → {result['new_amount']}")
            else:
                game_logger.info(
                    f"⚠️ 无法存储金币到主基地: {result.get('message', '未知错误')}")

        # 如果还有剩余金币，输出警告
        if self.carried_gold > 0:
            game_logger.info(f"⚠️ 存储已满，剩余 {self.carried_gold} 金币无法存储")

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

            # 注册建筑到ResourceManager
            self._register_building_to_resource_manager(building)

            # building_completed标志已设置，无需额外处理
        except Exception as e:
            game_logger.info(f"❌ {self.name} 完成建筑时出错: {e}")

        result['events'].append(f"{self.name} 完成了 {building.name} 的建造")

        # 从建筑的分配列表中移除自己
        if self in building.assigned_engineers:
            building.assigned_engineers.remove(self)
            game_logger.info(f"🔓 {self.name} 从建筑 {building.name} 的分配列表中移除")

        # 从当前项目列表中移除完成的项目
        if self.current_projects:
            completed_project = None
            for project in self.current_projects:
                if project.get('building') == building:
                    completed_project = project
                    break
            if completed_project:
                self.current_projects.remove(completed_project)
                game_logger.info(
                    f"📋 {self.name} 完成项目: {building.name} (剩余项目: {len(self.current_projects)}/{self.max_concurrent_projects})")

        # 重置工作状态
        self.work_progress = 0.0
        self.target_building = None
        self.target_position = None
        self.last_deposit_time = 0.0
        self.deposit_count = 0  # 重置投入次数计数器

        # 进入空闲状态，等待新任务分配
        self.status = EngineerStatus.IDLE
        result['status_changed'] = True

    def _register_building_to_resource_manager(self, building):
        """
        将建筑注册到ResourceManager

        Args:
            building: 建筑对象
        """
        try:
            # 检查是否有游戏实例引用
            if not hasattr(self, 'game_instance') or not self.game_instance:
                game_logger.info(
                    f"⚠️ {self.name} 无法访问游戏实例，无法注册建筑: {building.name}")
                return

            resource_manager = get_resource_manager(self.game_instance)

            if not resource_manager:
                game_logger.info(
                    f"⚠️ ResourceManager未初始化，无法注册建筑: {building.name}")
                return

            # 根据建筑类型注册到相应的资源列表
            building_type = getattr(building, 'building_type', None)
            if building_type:
                if building_type.value == 'treasury':
                    resource_manager.register_treasury(building)
                elif building_type.value == 'magic_altar':
                    resource_manager.register_magic_altar(building)
                # 地牢之心已经在游戏初始化时注册，不需要重复注册
                else:
                    game_logger.info(
                        f"ℹ️ 建筑 {building.name} 类型为 {building_type.value}，无需注册到ResourceManager")
            else:
                game_logger.info(f"⚠️ 建筑 {building.name} 没有building_type属性")

        except Exception as e:
            game_logger.info(f"❌ {self.name} 注册建筑到ResourceManager失败: {e}")

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

        # 边界检查 - 修复：添加对空game_map的检查，避免IndexError
        if not game_map or len(game_map) == 0 or len(game_map[0]) == 0:
            return False

        if not (0 <= tile_x < GameConstants.MAP_WIDTH and 0 <= tile_y < GameConstants.MAP_HEIGHT):
            return False

        tile = game_map[tile_y][tile_x]
        # 只能在已挖掘的地块移动（地面或房间）
        return tile.type == TileType.GROUND or tile.is_dug

    def get_status_for_indicator(self) -> str:
        """获取用于状态指示器的状态字符串 - 复用 status_indicator.py 的状态定义"""
        status_mapping = {
            EngineerStatus.IDLE: 'idle',
            EngineerStatus.WANDERING: 'wandering',
            EngineerStatus.FETCHING_RESOURCES: 'fetching_resources',
            EngineerStatus.MOVING_TO_SITE: 'moving_to_site',
            EngineerStatus.CONSTRUCTING: 'constructing',
            EngineerStatus.REPAIRING: 'repairing',
            EngineerStatus.UPGRADING: 'upgrading',
            EngineerStatus.RELOADING: 'reloading',
            EngineerStatus.DEPOSITING_GOLD: 'depositing_gold',
            EngineerStatus.RETURNING_TO_BASE: 'returning_to_base'
        }
        return status_mapping.get(self.status, 'idle')

    def _get_construction_required_gold(self, building) -> int:
        """获取建造所需的金币数量（返回建筑成本的一半）"""
        if not building:
            return 0

        # 尝试从建筑配置获取建造成本
        try:
            # 优先从建筑实例的construction_cost_gold获取（这是从config.cost_gold复制的）
            if hasattr(building, 'construction_cost_gold'):
                return building.construction_cost_gold // 2  # 返回成本的一半
            # 然后尝试从建筑配置获取cost_gold
            elif hasattr(building, 'config') and hasattr(building.config, 'cost_gold'):
                return building.config.cost_gold // 2  # 返回成本的一半
            # 兼容旧代码：尝试从建筑配置获取cost
            elif hasattr(building, 'config') and hasattr(building.config, 'cost'):
                return building.config.cost // 2  # 返回成本的一半
            elif hasattr(building, 'cost'):
                return building.cost // 2  # 返回成本的一半
            else:
                # 根据建筑类型从BuildingRegistry获取真实成本
                from src.entities.building import BuildingRegistry, BuildingType

                building_type = getattr(building, 'building_type', 'unknown')
                if hasattr(building_type, 'value'):
                    building_type = building_type.value

                # 从BuildingRegistry获取真实成本
                if hasattr(BuildingType, str(building_type).upper()):
                    try:
                        building_type_enum = getattr(
                            BuildingType, str(building_type).upper())
                        if building_type_enum in BuildingRegistry.BUILDING_CONFIGS:
                            config = BuildingRegistry.BUILDING_CONFIGS[building_type_enum]
                            return config.cost_gold // 2  # 返回真实成本的一半
                    except Exception as e:
                        game_logger.error(f"获取建筑类型 {building_type} 的配置失败: {e}")

                # 如果无法获取建筑配置，记录错误并返回0
                game_logger.error(
                    f"无法获取建筑 {building.name if hasattr(building, 'name') else 'unknown'} 的建造成本")
                return 0
        except Exception as e:
            game_logger.error(f"计算建筑建造成本时出错: {e}")
            return 0

    def _get_repair_required_gold(self, building) -> int:
        """获取修复所需的金币数量 - 1金币回复5血量"""
        if not building:
            return 0

        # 计算需要修复的血量
        health_needed = building.max_health - building.health
        if health_needed <= 0:
            return 0

        # 1金币回复5血量
        return int(health_needed / 5)

    def _get_reload_required_gold(self, building) -> int:
        """获取装填所需的金币数量"""
        if not building:
            return 0

        # 根据建筑类型确定装填需求
        building_type = getattr(building, 'building_type', None)
        if building_type and hasattr(building_type, 'value'):
            building_type_value = building_type.value
        else:
            return 0

        if building_type_value == 'arrow_tower':
            # 箭塔装填弹药
            if hasattr(building, 'current_ammunition') and hasattr(building, 'max_ammunition'):
                return building.max_ammunition - building.current_ammunition
            else:
                return 60  # 默认最大弹药值
        elif building_type_value in ['orc_lair', 'demon_lair']:
            # 兽人巢穴和恶魔巢穴的临时金币
            if hasattr(building, 'max_temp_gold') and hasattr(building, 'temp_gold'):
                return building.max_temp_gold - building.temp_gold
            else:
                return 20  # 默认临时金币最大值
        elif building_type_value == 'magic_altar':
            # 魔法祭坛的临时金币存储
            if hasattr(building, 'max_temp_gold') and hasattr(building, 'temp_gold'):
                return building.max_temp_gold - building.temp_gold
            else:
                return 60  # 默认临时金币存储容量
        else:
            return 0  # 其他建筑类型不支持装填

    def _get_building_required_gold(self, building) -> int:
        """获取建筑所需的金币数量 - 根据任务类型调用相应的API"""
        if not building:
            return 0

        # 确定任务类型
        task_type = self._determine_task_type(building)

        if task_type == 'construction':
            return self._get_construction_required_gold(building)
        elif task_type == 'repair':
            return self._get_repair_required_gold(building)
        elif task_type == 'reload':
            return self._get_reload_required_gold(building)
        elif task_type == 'gold_deposit':
            return self._get_gold_deposit_required_gold(building)
        else:
            return 0

    def _get_gold_deposit_required_gold(self, building) -> int:
        """获取金币存储任务所需的金币数量"""
        if not building:
            return 0

        # 对于金币存储任务，工程师需要携带足够的金币来填满建筑的存储空间
        if hasattr(building, 'max_temp_gold') and hasattr(building, 'temp_gold'):
            # 计算还需要多少金币来填满存储
            needed_gold = building.max_temp_gold - building.temp_gold
            # 工程师每次最多携带60金币，所以取最小值
            return min(needed_gold, 60)
        elif hasattr(building, 'max_temp_gold'):
            # 如果建筑有最大存储容量但没有当前存储量，返回最大容量
            return min(building.max_temp_gold, 60)
        else:
            # 默认情况，携带20金币
            return 20

    def _get_dungeon_heart_position(self):
        """获取地牢之心位置（考虑2x2大小）"""
        if hasattr(self, 'game_instance') and self.game_instance:
            if hasattr(self.game_instance, 'dungeon_heart_pos'):
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
            else:
                game_logger.info(f"❌ [{self.name}] 游戏实例没有dungeon_heart_pos属性")
        else:
            game_logger.info(f"❌ [{self.name}] 没有游戏实例引用")
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

    def _check_waiting_timeout(self, current_time: float, result: Dict[str, Any]):
        """检查等待超时并处理"""
        # 检查是否处于等待状态
        if self.status == EngineerStatus.IDLE and self.target_building:
            # 如果等待时间未设置，设置开始时间
            if self.waiting_start_time == 0.0:
                self.waiting_start_time = current_time

            # 检查是否超时
            waiting_duration = current_time - self.waiting_start_time
            if waiting_duration >= self.waiting_timeout:
                game_logger.info(
                    f"⏰ [{self.name}] 等待超时 ({waiting_duration:.1f}秒 >= {self.waiting_timeout}秒)，从分配工作中剔除")

                # 从建筑的分配列表中移除
                if self.target_building and hasattr(self.target_building, 'assigned_engineers'):
                    if self in self.target_building.assigned_engineers:
                        self.target_building.assigned_engineers.remove(self)
                        game_logger.info(
                            f"🔓 [{self.name}] 从建筑 {self.target_building.name} 的分配列表中移除")

                # 从建筑的working_engineer列表中移除
                if self.target_building and hasattr(self.target_building, 'working_engineer'):
                    if self in self.target_building.working_engineer:
                        self.target_building.working_engineer.remove(self)
                        game_logger.info(
                            f"🔓 [{self.name}] 从建筑 {self.target_building.name} 的工作列表中移除")

                # 清理工程师状态
                self.target_building = None
                self.status = EngineerStatus.WANDERING
                self.waiting_start_time = 0.0

                result['status_changed'] = True
                result['events'].append(f"工程师等待超时，设置为游荡状态")

                game_logger.info(f"🔄 [{self.name}] 等待超时处理完成，状态设置为游荡")
        else:
            # 如果不是等待状态，重置等待时间
            self.waiting_start_time = 0.0

    def _update_state_switcher(self, current_time: float, game_map: List[List[Tile]]):
        """
        重写状态切换器 - 工程师特有的状态管理逻辑

        Args:
            current_time: 当前时间
            game_map: 游戏地图
        """
        # 工程师有自己的状态管理逻辑，重写父类的方法以保持兼容性
        # 检查状态切换冷却时间
        if current_time - self.last_state_change_time < self.state_change_cooldown:
            return

        # 工程师特有的等待状态列表（排除工作中的状态和wandering，避免循环）
        waiting_states = [EngineerStatus.IDLE]

        # 检查当前状态是否为等待状态
        if self.status in waiting_states:
            # 如果还没有记录等待开始时间，记录它
            if self.waiting_start_time == 0:
                self.waiting_start_time = current_time
                game_logger.debug(
                    f"🕐 工程师 {self.name} 开始等待状态: {self.status.value}")

            # 检查是否超过等待超时时间
            waiting_duration = current_time - self.waiting_start_time
            if waiting_duration >= self.waiting_timeout:
                # 工程师在等待超时后应该切换到游荡状态
                old_status = self.status
                self.status = EngineerStatus.WANDERING
                self.last_state_change_time = current_time
                self.waiting_start_time = 0  # 重置等待开始时间

                game_logger.info(
                    f"🎲 工程师 {self.name} 等待超时({waiting_duration:.1f}s)，从 {old_status.value} 切换到 {self.status.value}")

                # 工程师在游荡时会自动寻找工作，不需要额外的游荡行为
        else:
            # 不在等待状态，重置等待开始时间
            if self.waiting_start_time != 0:
                self.waiting_start_time = 0


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
