#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工程师分配器
统一管理工程师的任务分配和状态转换
"""

import time
import math
import random
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

from src.entities.building import Building, BuildingStatus
from src.entities.monster.goblin_engineer import Engineer, EngineerStatus
from src.entities.monster.goblin_worker import GoblinWorker, WorkerStatus
from src.core.constants import GameConstants
from src.entities.building import BuildingType
from src.utils.logger import game_logger


class AssignmentStrategy(Enum):
    """分配策略枚举"""
    NEAREST_FIRST = "nearest_first"      # 最近优先
    EFFICIENCY_FIRST = "efficiency_first"  # 效率优先
    RANDOM = "random"                     # 随机分配
    BALANCED = "balanced"                 # 平衡分配


class TaskPriority(Enum):
    """任务优先级枚举"""
    CRITICAL = 1    # 关键任务（紧急修理、重要建造）
    HIGH = 2        # 高优先级（正常建造、修理）
    NORMAL = 3      # 普通优先级（升级、装填）
    LOW = 4         # 低优先级（维护任务）
    TRAINING = 6    # 训练任务（苦工专用）


class WorkerType(Enum):
    """工作单位类型枚举"""
    ENGINEER = "engineer"    # 工程师
    WORKER = "worker"        # 苦工


class WorkTask:
    """工作任务类"""

    def __init__(self, building: Building, task_type: str, priority: TaskPriority,
                 required_gold: int = 0, estimated_duration: float = 0.0,
                 worker_type: WorkerType = WorkerType.ENGINEER):
        self.building = building
        # 'construction', 'repair', 'upgrade', 'reload', 'gold_deposit', 'training'
        self.task_type = task_type
        self.priority = priority
        self.required_gold = required_gold
        self.estimated_duration = estimated_duration
        self.worker_type = worker_type  # 指定需要的工作单位类型
        self.created_time = time.time()
        self.assigned_worker = None  # 分配的工作单位（工程师或苦工）
        self.is_completed = False

    def __repr__(self):
        return f"WorkTask({self.building.name}, {self.task_type}, {self.priority.name})"


class EngineerAssigner:
    """工程师分配器 - 专门管理工程师的任务分配"""

    def __init__(self, strategy: AssignmentStrategy = AssignmentStrategy.BALANCED):
        self.strategy = strategy
        self.work_tasks = []  # 待分配的任务列表
        self.assigned_tasks = {}  # 已分配的任务 {engineer: WorkTask}
        self.engineer_stats = {}  # 工程师统计信息 {engineer: stats}

        # 分配配置
        self.max_retry_attempts = 3
        self.assignment_cooldown = 0.1  # 分配冷却时间（秒）- 减少到0.1秒
        self.last_assignment_time = 0.0

        # 任务优先级权重
        self.priority_weights = {
            TaskPriority.CRITICAL: 10.0,
            TaskPriority.HIGH: 7.0,
            TaskPriority.NORMAL: 4.0,
            TaskPriority.LOW: 1.0,
            TaskPriority.TRAINING: 5.0   # 训练任务优先级
        }

        game_logger.info(f"工程师分配器初始化完成 - 策略: {strategy.value}")

    def update(self, engineers: List[Engineer], buildings: List[Building],
               delta_time: float) -> Dict[str, Any]:
        """
        更新分配器状态

        Args:
            engineers: 工程师列表
            buildings: 建筑列表
            delta_time: 时间增量

        Returns:
            Dict: 更新结果
        """
        result = {
            'tasks_created': 0,
            'tasks_assigned': 0,
            'tasks_completed': 0,
            'engineers_reassigned': 0,
            'events': []
        }

        # 1. 扫描建筑，创建工作任务
        self._scan_buildings_for_tasks(buildings, result)

        # 2. 检查分配冷却时间
        current_time = time.time()
        if current_time - self.last_assignment_time < self.assignment_cooldown:
            return result

        # 3. 处理已完成的任务
        self._process_completed_tasks(engineers, result)

        # 4. 重新分配空闲工程师
        self._reassign_idle_engineers(engineers, result)

        # 5. 分配新任务
        self._assign_new_tasks(engineers, result)

        # 6. 更新统计信息
        self._update_engineer_stats(engineers)

        self.last_assignment_time = current_time
        return result

    def _cleanup_invalid_tasks(self, buildings: List[Building], result: Dict[str, Any]):
        """清理无效的任务（如地牢之心的金币存储任务）"""
        invalid_tasks = []

        for task in self.work_tasks:
            if task.is_completed:
                continue

            # 检查地牢之心的金币存储任务
            if (hasattr(task.building, 'building_type') and
                task.building.building_type == BuildingType.DUNGEON_HEART and
                    task.task_type == 'gold_deposit'):

                # 检查地牢之心是否真的需要金币存储任务
                if hasattr(task.building, 'get_engineer_task_type'):
                    task_type = task.building.get_engineer_task_type()
                    if task_type != 'gold_deposit':
                        invalid_tasks.append(task)
                        result['events'].append(
                            f"清理无效任务: {task.building.name} ({task.task_type})")

        # 移除无效任务
        for task in invalid_tasks:
            if task in self.work_tasks:
                self.work_tasks.remove(task)
            # 如果任务已分配给工作单位，取消分配
            if task.assigned_worker:
                task.assigned_worker.target_building = None
                if isinstance(task.assigned_worker, Engineer):
                    task.assigned_worker.status = EngineerStatus.IDLE
                elif isinstance(task.assigned_worker, GoblinWorker):
                    task.assigned_worker.state = WorkerStatus.IDLE.value
                if task.assigned_worker in self.assigned_tasks:
                    del self.assigned_tasks[task.assigned_worker]

    def _scan_buildings_for_tasks(self, buildings: List[Building], result: Dict[str, Any]):
        """扫描建筑，创建工作任务"""
        # 首先清理无效的任务（如地牢之心的金币存储任务）
        self._cleanup_invalid_tasks(buildings, result)

        for building in buildings:
            # 检查是否已有相同建筑的任务
            existing_tasks = [task for task in self.work_tasks
                              if task.building == building and not task.is_completed]
            if existing_tasks:
                continue

            # 创建建造任务
            if building.status == BuildingStatus.PLANNING:
                required_gold = self._calculate_construction_gold(building)
                task = WorkTask(
                    building=building,
                    task_type='construction',
                    priority=TaskPriority.HIGH,
                    required_gold=required_gold,
                    estimated_duration=building.build_time
                )
                self.work_tasks.append(task)
                result['tasks_created'] += 1
                result['events'].append(f"创建建造任务: {building.name}")

            # 创建修理任务
            elif (building.status == BuildingStatus.COMPLETED and
                  building.health < building.max_health):
                required_gold = self._calculate_repair_gold(building)
                priority = TaskPriority.CRITICAL if building.health < building.max_health * \
                    0.3 else TaskPriority.HIGH
                task = WorkTask(
                    building=building,
                    task_type='repair',
                    priority=priority,
                    required_gold=required_gold,
                    estimated_duration=required_gold * 0.1  # 估算修理时间
                )
                self.work_tasks.append(task)
                result['tasks_created'] += 1
                result['events'].append(f"创建修理任务: {building.name}")

            # 创建装填任务
            elif self._needs_reload(building):
                required_gold = self._calculate_reload_gold(building)
                task = WorkTask(
                    building=building,
                    task_type='reload',
                    priority=TaskPriority.NORMAL,
                    required_gold=required_gold,
                    estimated_duration=required_gold * 0.05
                )
                self.work_tasks.append(task)
                result['tasks_created'] += 1
                result['events'].append(f"创建装填任务: {building.name}")

            # 创建金币存储任务
            elif self._needs_gold_deposit(building):
                required_gold = self._calculate_gold_deposit_gold(building)
                task = WorkTask(
                    building=building,
                    task_type='gold_deposit',
                    priority=TaskPriority.LOW,
                    required_gold=required_gold,
                    estimated_duration=required_gold * 0.02,
                    worker_type=WorkerType.ENGINEER
                )
                self.work_tasks.append(task)
                result['tasks_created'] += 1
                result['events'].append(f"创建金币存储任务: {building.name}")

    def _process_completed_tasks(self, engineers: List[Engineer], result: Dict[str, Any]):
        """处理已完成的任务"""
        completed_tasks = []

        for engineer in engineers:
            if engineer in self.assigned_tasks:
                task = self.assigned_tasks[engineer]

                # 检查任务是否完成
                if self._is_task_completed(engineer, task):
                    task.is_completed = True
                    completed_tasks.append(task)
                    result['tasks_completed'] += 1
                    result['events'].append(
                        f"任务完成: {engineer.name} - {task.building.name}")

                    # 清理工程师状态
                    self._cleanup_engineer_after_task(engineer)
                    del self.assigned_tasks[engineer]

        # 移除已完成的任务
        for task in completed_tasks:
            if task in self.work_tasks:
                self.work_tasks.remove(task)

    def _reassign_idle_engineers(self, engineers: List[Engineer], result: Dict[str, Any]):
        """重新分配空闲工程师"""
        for engineer in engineers:
            # 检查工程师是否处于空闲状态（WAITING已统一为IDLE）
            if (engineer.status == EngineerStatus.IDLE and
                engineer not in self.assigned_tasks and
                    len(engineer.current_projects) < engineer.max_concurrent_projects):

                # 寻找最适合的任务
                best_task = self._find_best_task_for_engineer(engineer)
                if best_task:
                    self._assign_task_to_engineer(engineer, best_task)
                    result['engineers_reassigned'] += 1
                    result['events'].append(
                        f"重新分配工程师: {engineer.name} - {best_task.building.name}")

    def _assign_new_tasks(self, engineers: List[Engineer], result: Dict[str, Any]):
        """分配新任务"""
        # 按优先级排序任务（只处理工程师任务）
        available_tasks = [task for task in self.work_tasks
                           if (not task.is_completed and task.assigned_worker is None and
                               task.worker_type == WorkerType.ENGINEER)]
        available_tasks.sort(key=lambda t: (t.priority.value, -t.created_time))

        for task in available_tasks:
            # 寻找最适合的工程师
            best_engineer = self._find_best_engineer_for_task(task, engineers)
            if best_engineer:
                self._assign_task_to_engineer(best_engineer, task)
                result['tasks_assigned'] += 1
                result['events'].append(
                    f"分配新任务: {best_engineer.name} - {task.building.name}")

    def _find_best_task_for_engineer(self, engineer: Engineer) -> Optional[WorkTask]:
        """为工程师寻找最适合的任务"""
        available_tasks = [task for task in self.work_tasks
                           if (not task.is_completed and task.assigned_worker is None and
                               task.worker_type == WorkerType.ENGINEER)]

        if not available_tasks:
            return None

        # 根据策略选择任务
        if self.strategy == AssignmentStrategy.NEAREST_FIRST:
            return self._select_nearest_task(engineer, available_tasks)
        elif self.strategy == AssignmentStrategy.EFFICIENCY_FIRST:
            return self._select_most_efficient_task(engineer, available_tasks)
        elif self.strategy == AssignmentStrategy.RANDOM:
            return random.choice(available_tasks)
        else:  # BALANCED
            return self._select_balanced_task(engineer, available_tasks)

    def _find_best_engineer_for_task(self, task: WorkTask, engineers: List[Engineer]) -> Optional[Engineer]:
        """为任务寻找最适合的工程师"""
        available_engineers = [eng for eng in engineers
                               if (eng.status in [EngineerStatus.IDLE, EngineerStatus.WANDERING] and
                                   eng not in self.assigned_tasks and
                                   len(eng.current_projects) < eng.max_concurrent_projects)]

        if not available_engineers:
            return None

        # 根据策略选择工程师
        if self.strategy == AssignmentStrategy.NEAREST_FIRST:
            return self._select_nearest_engineer(task, available_engineers)
        elif self.strategy == AssignmentStrategy.EFFICIENCY_FIRST:
            return self._select_most_efficient_engineer(task, available_engineers)
        elif self.strategy == AssignmentStrategy.RANDOM:
            return random.choice(available_engineers)
        else:  # BALANCED
            return self._select_balanced_engineer(task, available_engineers)

    def _assign_task_to_engineer(self, engineer: Engineer, task: WorkTask):
        """将任务分配给工程师"""
        # 设置任务分配
        task.assigned_worker = engineer
        self.assigned_tasks[engineer] = task

        # 设置工程师目标建筑
        engineer.target_building = task.building

        # 根据任务类型设置工程师状态
        if task.task_type == 'construction':
            engineer.status = EngineerStatus.MOVING_TO_SITE
        elif task.task_type == 'repair':
            engineer.status = EngineerStatus.MOVING_TO_SITE
        elif task.task_type == 'reload':
            engineer.status = EngineerStatus.MOVING_TO_SITE
        elif task.task_type == 'gold_deposit':
            engineer.status = EngineerStatus.MOVING_TO_SITE

        # 记录分配时间
        if not hasattr(engineer, 'last_assignment_time'):
            engineer.last_assignment_time = time.time()
        else:
            engineer.last_assignment_time = time.time()

        game_logger.info(
            f"分配任务: {engineer.name} -> {task.building.name} ({task.task_type})")

    def _cleanup_engineer_after_task(self, engineer: Engineer):
        """任务完成后清理工程师状态"""
        engineer.target_building = None
        engineer.status = EngineerStatus.IDLE  # 进入空闲状态，由IdleStateManager统一管理
        engineer.last_assignment_time = time.time()

    def _is_task_completed(self, engineer: Engineer, task: WorkTask) -> bool:
        """检查任务是否完成"""
        if not engineer.target_building or engineer.target_building != task.building:
            return True

        # 根据任务类型检查完成状态
        if task.task_type == 'construction':
            return (engineer.status == EngineerStatus.IDLE and
                    task.building.status == BuildingStatus.COMPLETED)
        elif task.task_type == 'repair':
            return (engineer.status == EngineerStatus.IDLE and
                    task.building.health >= task.building.max_health)
        elif task.task_type == 'reload':
            return (engineer.status == EngineerStatus.IDLE and
                    not self._needs_reload(task.building))
        elif task.task_type == 'gold_deposit':
            return (engineer.status == EngineerStatus.IDLE and
                    not self._needs_gold_deposit(task.building))

        return False

    def _select_nearest_task(self, engineer: Engineer, tasks: List[WorkTask]) -> Optional[WorkTask]:
        """选择最近的任务"""
        if not tasks:
            return None

        min_distance = float('inf')
        nearest_task = None

        for task in tasks:
            distance = self._calculate_distance(engineer, task.building)
            if distance < min_distance:
                min_distance = distance
                nearest_task = task

        return nearest_task

    def _select_most_efficient_task(self, engineer: Engineer, tasks: List[WorkTask]) -> Optional[WorkTask]:
        """选择最高效的任务"""
        if not tasks:
            return None

        best_score = -1
        best_task = None

        for task in tasks:
            # 计算效率分数：优先级权重 / 预估时间
            efficiency_score = (self.priority_weights[task.priority] /
                                max(task.estimated_duration, 0.1))

            if efficiency_score > best_score:
                best_score = efficiency_score
                best_task = task

        return best_task

    def _select_balanced_task(self, engineer: Engineer, tasks: List[WorkTask]) -> Optional[WorkTask]:
        """选择平衡的任务（考虑距离和效率）"""
        if not tasks:
            return None

        best_score = -1
        best_task = None

        for task in tasks:
            # 计算距离分数（距离越近分数越高）
            distance = self._calculate_distance(engineer, task.building)
            distance_score = 1.0 / max(distance, 1.0)

            # 计算效率分数
            efficiency_score = (self.priority_weights[task.priority] /
                                max(task.estimated_duration, 0.1))

            # 综合分数：距离权重0.3，效率权重0.7
            total_score = distance_score * 0.3 + efficiency_score * 0.7

            if total_score > best_score:
                best_score = total_score
                best_task = task

        return best_task

    def _select_nearest_engineer(self, task: WorkTask, engineers: List[Engineer]) -> Optional[Engineer]:
        """选择最近的工程师"""
        if not engineers:
            return None

        min_distance = float('inf')
        nearest_engineer = None

        for engineer in engineers:
            distance = self._calculate_distance(engineer, task.building)
            if distance < min_distance:
                min_distance = distance
                nearest_engineer = engineer

        return nearest_engineer

    def _select_most_efficient_engineer(self, task: WorkTask, engineers: List[Engineer]) -> Optional[Engineer]:
        """选择最高效的工程师"""
        if not engineers:
            return None

        best_score = -1
        best_engineer = None

        for engineer in engineers:
            # 计算工程师效率分数
            efficiency_score = engineer.build_efficiency

            if efficiency_score > best_score:
                best_score = efficiency_score
                best_engineer = engineer

        return best_engineer

    def _select_balanced_engineer(self, task: WorkTask, engineers: List[Engineer]) -> Optional[Engineer]:
        """选择平衡的工程师（考虑距离和效率）"""
        if not engineers:
            return None

        best_score = -1
        best_engineer = None

        for engineer in engineers:
            # 计算距离分数
            distance = self._calculate_distance(engineer, task.building)
            distance_score = 1.0 / max(distance, 1.0)

            # 计算效率分数
            efficiency_score = engineer.build_efficiency

            # 综合分数：距离权重0.4，效率权重0.6
            total_score = distance_score * 0.4 + efficiency_score * 0.6

            if total_score > best_score:
                best_score = total_score
                best_engineer = engineer

        return best_engineer

    def _calculate_distance(self, engineer: Engineer, building: Building) -> float:
        """计算工程师到建筑的距离"""
        dx = building.x - engineer.x
        dy = building.y - engineer.y
        return math.sqrt(dx * dx + dy * dy)

    def _calculate_construction_gold(self, building: Building) -> int:
        """计算建造所需金币"""
        if hasattr(building, 'construction_cost_gold'):
            return building.construction_cost_gold
        elif hasattr(building, 'config') and hasattr(building.config, 'cost_gold'):
            return building.config.cost_gold
        else:
            return 200  # 默认成本

    def _calculate_repair_gold(self, building: Building) -> int:
        """计算修理所需金币"""
        health_needed = building.max_health - building.health
        return int(health_needed / 5)  # 1金币回复5血量

    def _calculate_reload_gold(self, building: Building) -> int:
        """计算装填所需金币"""
        building_type = getattr(building, 'building_type', None)
        if not building_type or not hasattr(building_type, 'value'):
            return 0

        if building_type.value == 'arrow_tower':
            if hasattr(building, 'current_ammunition') and hasattr(building, 'max_ammunition'):
                return building.max_ammunition - building.current_ammunition
            return 60
        elif building_type.value in ['orc_lair', 'demon_lair']:
            if hasattr(building, 'max_temp_gold') and hasattr(building, 'temp_gold'):
                return building.max_temp_gold - building.temp_gold
            return 20
        elif building_type.value == 'magic_altar':
            if hasattr(building, 'max_temp_gold') and hasattr(building, 'temp_gold'):
                return building.max_temp_gold - building.temp_gold
            return 60

        return 0

    def _calculate_gold_deposit_gold(self, building: Building) -> int:
        """计算金币存储所需金币"""
        if hasattr(building, 'max_temp_gold') and hasattr(building, 'temp_gold'):
            needed_gold = building.max_temp_gold - building.temp_gold
            return min(needed_gold, 60)  # 工程师最多携带60金币
        return 20

    def _needs_reload(self, building: Building) -> bool:
        """检查建筑是否需要装填"""
        building_type = getattr(building, 'building_type', None)
        if not building_type or not hasattr(building_type, 'value'):
            return False

        if building_type.value == 'arrow_tower':
            return (hasattr(building, 'current_ammunition') and
                    building.current_ammunition <= 0)
        elif building_type.value in ['orc_lair', 'demon_lair', 'magic_altar']:
            return (hasattr(building, 'can_accept_gold') and
                    building.can_accept_gold())

        return False

    def _needs_gold_deposit(self, building: Building) -> bool:
        """检查建筑是否需要金币存储"""
        # 首先检查建筑是否支持金币存储
        if not (hasattr(building, 'can_accept_gold') and building.can_accept_gold()):
            return False

        # 然后检查建筑的任务类型，确保它确实需要金币存储任务
        if hasattr(building, 'get_engineer_task_type'):
            task_type = building.get_engineer_task_type()
            return task_type == 'gold_deposit'

        # 如果没有get_engineer_task_type方法，使用默认逻辑
        return True

    def _update_engineer_stats(self, engineers: List[Engineer]):
        """更新工程师统计信息"""
        for engineer in engineers:
            if engineer not in self.engineer_stats:
                self.engineer_stats[engineer] = {
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'efficiency_rating': 0.0,
                    'last_active_time': time.time()
                }

            stats = self.engineer_stats[engineer]
            if engineer.status in [EngineerStatus.CONSTRUCTING, EngineerStatus.REPAIRING,
                                   EngineerStatus.UPGRADING, EngineerStatus.RELOADING]:
                stats['last_active_time'] = time.time()

    def get_statistics(self) -> Dict[str, Any]:
        """获取分配器统计信息"""
        # 将engineer_stats转换为可序列化的格式
        engineer_stats = {}
        for engineer, stats in self.engineer_stats.items():
            engineer_stats[engineer.name] = stats.copy()

        return {
            'total_tasks': len(self.work_tasks),
            'assigned_tasks': len(self.assigned_tasks),
            'completed_tasks': sum(1 for task in self.work_tasks if task.is_completed),
            'strategy': self.strategy.value,
            'engineer_stats': engineer_stats
        }

    def set_strategy(self, strategy: AssignmentStrategy):
        """设置分配策略"""
        self.strategy = strategy
        game_logger.info(f"分配策略已更改为: {strategy.value}")

    def clear_all_tasks(self):
        """清除所有任务"""
        self.work_tasks.clear()
        self.assigned_tasks.clear()
        game_logger.info("已清除所有任务")


class WorkerAssigner:
    """苦工分配器 - 专门管理苦工的任务分配"""

    def __init__(self, strategy: AssignmentStrategy = AssignmentStrategy.BALANCED):
        self.strategy = strategy
        self.work_tasks = []  # 待分配的任务列表
        self.assigned_tasks = {}  # 已分配的任务 {worker: WorkTask}
        self.worker_stats = {}  # 苦工统计信息 {worker: stats}

        # 分配配置
        self.max_retry_attempts = 3
        self.assignment_cooldown = 0.1  # 分配冷却时间（秒）
        self.last_assignment_time = 0.0

        # 任务优先级权重
        self.priority_weights = {
            TaskPriority.TRAINING: 5.0   # 训练任务优先级
        }

        game_logger.info(f"苦工分配器初始化完成 - 策略: {strategy.value}")

    def update(self, workers: List[GoblinWorker], buildings: List[Building],
               delta_time: float) -> Dict[str, Any]:
        """
        更新分配器状态

        Args:
            workers: 苦工列表
            buildings: 建筑列表
            delta_time: 时间增量

        Returns:
            Dict: 更新结果
        """
        result = {
            'tasks_created': 0,
            'tasks_assigned': 0,
            'tasks_completed': 0,
            'workers_reassigned': 0,
            'events': []
        }

        # 1. 扫描建筑，创建苦工任务
        self._scan_buildings_for_worker_tasks(buildings, result)

        # 2. 检查分配冷却时间
        current_time = time.time()
        if current_time - self.last_assignment_time < self.assignment_cooldown:
            return result

        # 3. 处理已完成的任务
        self._process_completed_tasks(workers, result)

        # 4. 重新分配空闲苦工
        self._reassign_idle_workers(workers, result)

        # 5. 分配新任务
        self._assign_new_tasks(workers, result)

        # 6. 更新统计信息
        self._update_worker_stats(workers)

        self.last_assignment_time = current_time
        return result

    def _scan_buildings_for_worker_tasks(self, buildings: List[Building], result: Dict[str, Any]):
        """扫描建筑，创建苦工任务"""
        for building in buildings:
            # 检查是否已有相同建筑的任务
            existing_tasks = [task for task in self.work_tasks
                              if task.building == building and not task.is_completed]
            if existing_tasks:
                continue

            # 创建训练任务
            if self._needs_training(building):
                task = WorkTask(
                    building=building,
                    task_type='training',
                    priority=TaskPriority.TRAINING,
                    required_gold=0,
                    estimated_duration=30.0,  # 训练时间30秒
                    worker_type=WorkerType.WORKER
                )
                self.work_tasks.append(task)
                result['tasks_created'] += 1
                result['events'].append(f"创建训练任务: {building.name}")

    def _process_completed_tasks(self, workers: List[GoblinWorker], result: Dict[str, Any]):
        """处理已完成的任务"""
        completed_tasks = []

        for worker in workers:
            if worker in self.assigned_tasks:
                task = self.assigned_tasks[worker]

                # 检查任务是否完成
                if self._is_task_completed(worker, task):
                    task.is_completed = True
                    completed_tasks.append(task)
                    result['tasks_completed'] += 1
                    result['events'].append(
                        f"任务完成: {worker.name} - {task.building.name}")

                    # 清理苦工状态
                    self._cleanup_worker_after_task(worker)
                    del self.assigned_tasks[worker]

        # 移除已完成的任务
        for task in completed_tasks:
            if task in self.work_tasks:
                self.work_tasks.remove(task)

    def _reassign_idle_workers(self, workers: List[GoblinWorker], result: Dict[str, Any]):
        """重新分配空闲苦工"""
        for worker in workers:
            # 检查苦工是否处于空闲状态
            if (hasattr(worker, 'state') and worker.state == WorkerStatus.IDLE.value and
                worker not in self.assigned_tasks and
                    not hasattr(worker, 'assigned_building') or not worker.assigned_building):

                # 寻找最适合的任务
                best_task = self._find_best_task_for_worker(worker)
                if best_task:
                    self._assign_task_to_worker(worker, best_task)
                    result['workers_reassigned'] += 1
                    result['events'].append(
                        f"重新分配苦工: {worker.name} - {best_task.building.name}")

    def _assign_new_tasks(self, workers: List[GoblinWorker], result: Dict[str, Any]):
        """分配新任务"""
        # 按优先级排序任务
        available_tasks = [task for task in self.work_tasks
                           if (not task.is_completed and task.assigned_worker is None and
                               task.worker_type == WorkerType.WORKER)]
        available_tasks.sort(key=lambda t: (t.priority.value, -t.created_time))

        for task in available_tasks:
            # 寻找最适合的苦工
            best_worker = self._find_best_worker_for_task(task, workers)
            if best_worker:
                self._assign_task_to_worker(best_worker, task)
                result['tasks_assigned'] += 1
                result['events'].append(
                    f"分配新任务: {best_worker.name} - {task.building.name}")

    def _find_best_task_for_worker(self, worker: GoblinWorker) -> Optional[WorkTask]:
        """为苦工寻找最适合的任务"""
        available_tasks = [task for task in self.work_tasks
                           if (not task.is_completed and task.assigned_worker is None and
                               task.worker_type == WorkerType.WORKER)]

        if not available_tasks:
            return None

        # 根据策略选择任务
        if self.strategy == AssignmentStrategy.NEAREST_FIRST:
            return self._select_nearest_task(worker, available_tasks)
        elif self.strategy == AssignmentStrategy.EFFICIENCY_FIRST:
            return self._select_most_efficient_task(worker, available_tasks)
        elif self.strategy == AssignmentStrategy.RANDOM:
            return random.choice(available_tasks)
        else:  # BALANCED
            return self._select_balanced_task(worker, available_tasks)

    def _find_best_worker_for_task(self, task: WorkTask, workers: List[GoblinWorker]) -> Optional[GoblinWorker]:
        """为任务寻找最适合的苦工"""
        available_workers = [worker for worker in workers
                             if (hasattr(worker, 'state') and worker.state == WorkerStatus.IDLE.value and
                                 worker not in self.assigned_tasks and
                                 not hasattr(worker, 'assigned_building') or not worker.assigned_building)]

        if not available_workers:
            return None

        # 根据策略选择苦工
        if self.strategy == AssignmentStrategy.NEAREST_FIRST:
            return self._select_nearest_worker(task, available_workers)
        elif self.strategy == AssignmentStrategy.EFFICIENCY_FIRST:
            return self._select_most_efficient_worker(task, available_workers)
        elif self.strategy == AssignmentStrategy.RANDOM:
            return random.choice(available_workers)
        else:  # BALANCED
            return self._select_balanced_worker(task, available_workers)

    def _assign_task_to_worker(self, worker: GoblinWorker, task: WorkTask):
        """将任务分配给苦工"""
        # 设置任务分配
        task.assigned_worker = worker
        self.assigned_tasks[worker] = task

        # 设置苦工目标建筑和任务信息
        worker.target_building = task.building
        worker.assigned_building = task.building
        worker.task_type = task.task_type

        # 根据任务类型设置苦工状态
        if task.task_type == 'training':
            worker.state = WorkerStatus.MOVING_TO_TRAINING.value

        # 记录分配时间
        if not hasattr(worker, 'last_assignment_time'):
            worker.last_assignment_time = time.time()
        else:
            worker.last_assignment_time = time.time()

        game_logger.info(
            f"分配任务: {worker.name} -> {task.building.name} ({task.task_type})")

    def _cleanup_worker_after_task(self, worker: GoblinWorker):
        """任务完成后清理苦工状态"""
        worker.target_building = None
        worker.assigned_building = None
        worker.task_type = None
        worker.state = WorkerStatus.IDLE.value  # 进入空闲状态
        worker.last_assignment_time = time.time()

    def _is_task_completed(self, worker: GoblinWorker, task: WorkTask) -> bool:
        """检查任务是否完成"""
        if not worker.target_building or worker.target_building != task.building:
            return True

        # 根据任务类型检查完成状态
        if task.task_type == 'training':
            return (worker.state == WorkerStatus.IDLE.value and
                    not self._needs_training(task.building))

        return False

    def _select_nearest_task(self, worker: GoblinWorker, tasks: List[WorkTask]) -> Optional[WorkTask]:
        """选择最近的任务"""
        if not tasks:
            return None

        min_distance = float('inf')
        nearest_task = None

        for task in tasks:
            distance = self._calculate_distance(worker, task.building)
            if distance < min_distance:
                min_distance = distance
                nearest_task = task

        return nearest_task

    def _select_most_efficient_task(self, worker: GoblinWorker, tasks: List[WorkTask]) -> Optional[WorkTask]:
        """选择最高效的任务"""
        if not tasks:
            return None

        best_score = -1
        best_task = None

        for task in tasks:
            # 计算效率分数：优先级权重 / 预估时间
            efficiency_score = (self.priority_weights[task.priority] /
                                max(task.estimated_duration, 0.1))

            if efficiency_score > best_score:
                best_score = efficiency_score
                best_task = task

        return best_task

    def _select_balanced_task(self, worker: GoblinWorker, tasks: List[WorkTask]) -> Optional[WorkTask]:
        """选择平衡的任务（考虑距离和效率）"""
        if not tasks:
            return None

        best_score = -1
        best_task = None

        for task in tasks:
            # 计算距离分数（距离越近分数越高）
            distance = self._calculate_distance(worker, task.building)
            distance_score = 1.0 / max(distance, 1.0)

            # 计算效率分数
            efficiency_score = (self.priority_weights[task.priority] /
                                max(task.estimated_duration, 0.1))

            # 综合分数：距离权重0.3，效率权重0.7
            total_score = distance_score * 0.3 + efficiency_score * 0.7

            if total_score > best_score:
                best_score = total_score
                best_task = task

        return best_task

    def _select_nearest_worker(self, task: WorkTask, workers: List[GoblinWorker]) -> Optional[GoblinWorker]:
        """选择最近的苦工"""
        if not workers:
            return None

        min_distance = float('inf')
        nearest_worker = None

        for worker in workers:
            distance = self._calculate_distance(worker, task.building)
            if distance < min_distance:
                min_distance = distance
                nearest_worker = worker

        return nearest_worker

    def _select_most_efficient_worker(self, task: WorkTask, workers: List[GoblinWorker]) -> Optional[GoblinWorker]:
        """选择最高效的苦工"""
        if not workers:
            return None

        best_score = -1
        best_worker = None

        for worker in workers:
            # 计算苦工效率分数（基于挖掘效率）
            efficiency_score = getattr(worker, 'mining_efficiency', 1.0)

            if efficiency_score > best_score:
                best_score = efficiency_score
                best_worker = worker

        return best_worker

    def _select_balanced_worker(self, task: WorkTask, workers: List[GoblinWorker]) -> Optional[GoblinWorker]:
        """选择平衡的苦工（考虑距离和效率）"""
        if not workers:
            return None

        best_score = -1
        best_worker = None

        for worker in workers:
            # 计算距离分数
            distance = self._calculate_distance(worker, task.building)
            distance_score = 1.0 / max(distance, 1.0)

            # 计算效率分数
            efficiency_score = getattr(worker, 'mining_efficiency', 1.0)

            # 综合分数：距离权重0.4，效率权重0.6
            total_score = distance_score * 0.4 + efficiency_score * 0.6

            if total_score > best_score:
                best_score = total_score
                best_worker = worker

        return best_worker

    def _calculate_distance(self, worker: GoblinWorker, building: Building) -> float:
        """计算苦工到建筑的距离"""
        dx = building.x - worker.x
        dy = building.y - worker.y
        return math.sqrt(dx * dx + dy * dy)

    def _needs_training(self, building: Building) -> bool:
        """检查建筑是否需要训练任务"""
        # 检查建筑是否支持训练
        if not hasattr(building, 'can_train') or not building.can_train():
            return False

        # 检查建筑是否有空闲的训练槽位
        if hasattr(building, 'max_training_slots') and hasattr(building, 'current_training'):
            return len(building.current_training) < building.max_training_slots

        return True

    def _update_worker_stats(self, workers: List[GoblinWorker]):
        """更新苦工统计信息"""
        for worker in workers:
            if worker not in self.worker_stats:
                self.worker_stats[worker] = {
                    'total_tasks': 0,
                    'completed_tasks': 0,
                    'efficiency_rating': 0.0,
                    'last_active_time': time.time()
                }

            stats = self.worker_stats[worker]
            if (hasattr(worker, 'state') and worker.state in
                    [WorkerStatus.TRAINING.value]):
                stats['last_active_time'] = time.time()

    def get_statistics(self) -> Dict[str, Any]:
        """获取分配器统计信息"""
        # 将worker_stats转换为可序列化的格式
        worker_stats = {}
        for worker, stats in self.worker_stats.items():
            worker_stats[worker.name] = stats.copy()

        return {
            'total_tasks': len(self.work_tasks),
            'assigned_tasks': len(self.assigned_tasks),
            'completed_tasks': sum(1 for task in self.work_tasks if task.is_completed),
            'strategy': self.strategy.value,
            'worker_stats': worker_stats
        }

    def set_strategy(self, strategy: AssignmentStrategy):
        """设置分配策略"""
        self.strategy = strategy
        game_logger.info(f"苦工分配策略已更改为: {strategy.value}")

    def clear_all_tasks(self):
        """清除所有任务"""
        self.work_tasks.clear()
        self.assigned_tasks.clear()
        game_logger.info("已清除所有苦工任务")
