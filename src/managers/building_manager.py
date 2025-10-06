#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑管理器
统一管理所有建筑的建造、升级、维护等功能
"""

import time
import math
import random
from typing import List, Dict, Optional, Tuple, Any

from src.entities.building import Building, BuildingType, BuildingRegistry, BuildingStatus, BuildingCategory
from src.entities.monster.goblin_engineer import Engineer, EngineerType, EngineerRegistry, EngineerStatus
from src.core.constants import GameConstants
from src.core.enums import TileType
from src.core.game_state import Tile
from src.utils.logger import game_logger
from src.managers.resource_manager import get_resource_manager
from src.managers.auto_assigner import EngineerAssigner, AssignmentStrategy
# 移除时间管理器依赖，使用绝对时间


class BuildingManager:
    """建筑管理器 - 统一管理所有建筑相关功能"""

    def __init__(self):
        """初始化建筑管理器"""
        self.buildings = []                    # 所有建筑列表
        self.engineers = []                    # 所有工程师列表
        self.workers = []                      # 所有工人列表
        self.construction_queue = []           # 建造队列
        self.upgrade_queue = []               # 升级队列
        self.repair_queue = []                # 修理队列
        self.game_simulator = None            # 游戏模拟器引用（用于攻击响应）

        # 工程师分配器
        self.engineer_assigner = EngineerAssigner(AssignmentStrategy.BALANCED)

        # 统计信息
        self.total_buildings_built = 0
        self.total_gold_spent = 0

        # 魔法祭坛资源统计
        self.magic_altar_stats = {
            'total_mana_generated': 0.0,
            'total_mana_transferred': 0.0,
            'active_altars': 0,
            'altars_with_mages': 0,
            'total_uptime': 0.0,
            'average_efficiency': 0.0
        }

        # 日志控制
        self.debug_level = 1  # 0=无日志, 1=重要日志, 2=详细日志
        self.construction_time_saved = 0.0

        # 建造效率统计
        self.efficiency_stats = {
            'construction_time': 0.0,
            'projects_completed': 0,
            'repairs_completed': 0,
            'upgrades_completed': 0
        }

        game_logger.info("建筑管理器初始化完成 - 集成工程师分配器")

    def update(self, delta_time: float, game_state, game_map, workers: List = None) -> Dict[str, Any]:
        """
        更新建筑管理器

        Args:
            delta_time: 时间增量（秒）- 统一使用秒为单位
            game_state: 游戏状态
            game_map: 游戏地图

        Returns:
            Dict: 更新结果信息
        """
        # 直接使用传入的时间增量，统一使用绝对时间机制
        delta_seconds = delta_time
        result = {
            'buildings_updated': 0,
            'engineers_updated': 0,
            'constructions_completed': [],
            'repairs_completed': [],
            'upgrades_completed': [],
            'events': []
        }

        # 更新所有建筑
        for building in self.buildings[:]:
            old_status = building.status
            building_result = building.update(
                delta_seconds, game_state, self.engineers, workers)

            if building_result.get('production'):
                # 处理建筑产出
                self._handle_building_production(
                    building, building_result['production'], game_state)

            # 更新魔法祭坛统计
            if (hasattr(building, 'building_type') and
                building.building_type.value == 'magic_altar' and
                    hasattr(building, 'get_resource_statistics')):
                self._update_magic_altar_stats(building, delta_seconds)

            if building_result.get('status_changed'):
                result['events'].extend(building_result.get('events', []))

                # 检查建筑是否完成建造
                if old_status != BuildingStatus.COMPLETED and building.status == BuildingStatus.COMPLETED:
                    completion_result = self.complete_building_construction(
                        building, game_map)
                    if completion_result['completed']:
                        result['events'].append(completion_result['message'])
                        # 标记需要重新渲染
                        if completion_result.get('needs_rerender'):
                            result['needs_rerender'] = True

            result['buildings_updated'] += 1

        # 更新所有工程师
        for engineer in self.engineers[:]:
            engineer_result = engineer.update(
                delta_seconds, game_map, [], [], None, self)

            if engineer_result.get('work_completed'):
                result['constructions_completed'].extend(
                    engineer_result['work_completed'])

            # 处理工程师完成的建筑
            if engineer_result.get('building_completed'):
                building = engineer_result['building_completed']['building']
                game_logger.info(
                    f"🔍 [TREASURY_FLOW] 建筑管理器检测到 building_completed: {building.name}")
                if engineer_result['building_completed']['needs_map_update']:
                    game_logger.info(
                        f"🔍 [TREASURY_FLOW] 需要更新地图显示，调用 complete_building_construction")
                    # 手动触发建筑完成的地图更新
                    completion_result = self.complete_building_construction(
                        building, game_map)
                    game_logger.info(
                        f"🔍 [TREASURY_FLOW] complete_building_construction 结果: {completion_result}")
                    if completion_result['completed']:
                        result['events'].append(completion_result['message'])

            if engineer_result.get('status_changed'):
                result['events'].extend(engineer_result.get('events', []))

            result['engineers_updated'] += 1

        # 处理建造队列
        self._process_construction_queue(result)

        # 处理升级队列
        self._process_upgrade_queue(result)

        # 处理修理队列
        self._process_repair_queue(result)

        # 使用新的工程师分配器进行统一任务分配
        assigner_result = self.engineer_assigner.update(
            self.engineers, self.buildings, delta_seconds)

        # 合并分配器结果
        result['tasks_created'] = assigner_result.get('tasks_created', 0)
        result['tasks_assigned'] = assigner_result.get('tasks_assigned', 0)
        result['tasks_completed'] = assigner_result.get('tasks_completed', 0)
        result['engineers_reassigned'] = assigner_result.get(
            'engineers_reassigned', 0)
        result['events'].extend(assigner_result.get('events', []))

        return result

    def can_build(self, building_type: BuildingType, x: int, y: int,
                  game_state, game_map) -> Dict[str, Any]:
        """
        检查是否可以建造建筑

        Args:
            building_type: 建筑类型
            x, y: 瓦片坐标
            game_state: 游戏状态
            game_map: 游戏地图

        Returns:
            Dict: 检查结果
        """
        config = BuildingRegistry.get_config(building_type)
        if not config:
            return {
                'can_build': False,
                'reason': 'invalid_building_type',
                'message': f'未知的建筑类型: {building_type}'
            }

        # 新机制：放置阶段不检查资源，工程师建造期间提供金币
        # 注释掉资源检查，因为工程师会在建造时提供资源
        # from src.managers.resource_manager import get_resource_manager
        # resource_manager = get_resource_manager(self.game_simulator)
        # if not resource_manager.can_afford(gold_cost=config.cost_gold):
        #     gold_info = resource_manager.get_total_gold()
        #     return {
        #         'can_build': False,
        #         'reason': 'insufficient_gold',
        #         'message': f'金币不足，需要 {config.cost_gold}，当前 {gold_info.available}'
        #     }

        # 水晶资源已移除，不再检查水晶成本

        # 检查地形是否合适
        terrain_check = self._check_building_terrain(x, y, config, game_map)
        if not terrain_check['suitable']:
            return {
                'can_build': False,
                'reason': 'unsuitable_terrain',
                'message': terrain_check['message']
            }

        # 移除工程师数量检查 - 建筑可以无条件放置

        return {
            'can_build': True,
            'cost_gold': config.cost_gold,
            'build_time': config.build_time,
            'engineers_needed': config.engineer_requirement
        }

    def can_build_placement_only(self, building_type: BuildingType, x: int, y: int,
                                 game_map) -> Dict[str, Any]:
        """
        检查是否可以放置建筑（只检查地形和位置，不检查资源）

        Args:
            building_type: 建筑类型
            x, y: 瓦片坐标
            game_map: 游戏地图

        Returns:
            Dict: 检查结果
        """
        config = BuildingRegistry.get_config(building_type)
        if not config:
            return {
                'can_build': False,
                'reason': 'invalid_building_type',
                'message': f'未知的建筑类型: {building_type}'
            }

        # 检查地形是否合适
        terrain_check = self._check_building_terrain(x, y, config, game_map)
        if not terrain_check['suitable']:
            return {
                'can_build': False,
                'reason': 'unsuitable_terrain',
                'message': terrain_check['message']
            }

        return {
            'can_build': True,
            'cost_gold': config.cost_gold,
            'build_time': config.build_time,
            'engineers_needed': config.engineer_requirement
        }

    def start_construction(self, building_type: BuildingType, x: int, y: int,
                           game_state, game_map, priority: int = 1) -> Dict[str, Any]:
        """
        开始建造建筑 - 新机制：放置阶段不花费金币，工程师建造期间提供金币

        Args:
            building_type: 建筑类型
            x, y: 瓦片坐标
            game_state: 游戏状态
            game_map: 游戏地图
            priority: 优先级

        Returns:
            Dict: 建造结果
        """
        # 检查是否可以建造（不检查资源，因为工程师会提供）
        can_build_result = self.can_build_placement_only(
            building_type, x, y, game_map)
        if not can_build_result['can_build']:
            return {
                'started': False,
                'reason': can_build_result['reason'],
                'message': can_build_result['message']
            }

        config = BuildingRegistry.get_config(building_type)

        # 创建建筑
        building = BuildingRegistry.create_building(building_type, x, y)
        if not building:
            return {
                'started': False,
                'reason': 'creation_failed',
                'message': '建筑创建失败'
            }

        # 直接放置建筑为规划状态（无条件放置）
        # 但是预建建筑（如地牢之心）应该保持其原始状态
        if not hasattr(building, 'is_prebuilt') or not building.is_prebuilt:
            building.status = BuildingStatus.PLANNING  # 设置为规划状态

        # 添加到建筑列表
        self.buildings.append(building)

        # 更新地图 - 直接设置为建筑类型，开始渲染
        if 0 <= y < len(game_map) and 0 <= x < len(game_map[0]):
            game_map[y][x].type = TileType.ROOM
            # 直接设置为建筑类型，让建筑立即开始渲染
            game_map[y][x].room_type = building_type.value
            game_map[y][x].is_incomplete = True  # 标记为未完成，用于区分建造状态

        # 更新统计（不扣除资源，因为工程师会提供）
        self.total_buildings_built += 1

        return {
            'started': True,
            'building': building,
            'status': 'planning',
            'cost_gold': config.cost_gold,  # 返回建造成本供工程师参考
            'message': f'放置了 {config.name}，等待工程师建造（成本：{config.cost_gold}金币）'
        }

    def start_upgrade(self, building: Building, priority: int = 1) -> Dict[str, Any]:
        """
        开始升级建筑

        Args:
            building: 目标建筑
            priority: 优先级

        Returns:
            Dict: 升级结果
        """
        if building.status != BuildingStatus.COMPLETED:
            return {
                'started': False,
                'reason': 'building_not_ready',
                'message': '建筑尚未完成，无法升级'
            }

        if building.upgrade_level >= building.max_upgrade_level:
            return {
                'started': False,
                'reason': 'max_level_reached',
                'message': '建筑已达最高等级'
            }

        # 检查升级成本
        upgrade_costs = building.upgrade_costs.get(
            building.upgrade_level + 1, {})
        # 这里应该检查资源，但需要游戏状态参数

        # 寻找可升级的工程师
        available_engineers = [eng for eng in self.engineers
                               if eng.upgrade_capability and len(eng.current_projects) < eng.max_concurrent_projects]

        if not available_engineers:
            return {
                'started': False,
                'reason': 'no_upgrade_engineers',
                'message': '没有可用的升级工程师'
            }

        # 选择最合适的工程师
        best_engineer = max(available_engineers,
                            key=lambda e: e.build_efficiency)

        # 开始升级
        if building.upgrade([best_engineer]):
            best_engineer.assign_upgrade_project(building, priority)

            return {
                'started': True,
                'building': building,
                'engineer': best_engineer,
                'new_level': building.upgrade_level + 1,
                'message': f'开始升级 {building.name} 到 {building.upgrade_level + 1} 级'
            }
        else:
            return {
                'started': False,
                'reason': 'upgrade_failed',
                'message': '无法开始升级'
            }

    def start_repair(self, building: Building, priority: int = 2) -> Dict[str, Any]:
        """
        开始修理建筑

        Args:
            building: 目标建筑
            priority: 优先级

        Returns:
            Dict: 修理结果
        """
        if building.health >= building.max_health:
            return {
                'started': False,
                'reason': 'no_damage',
                'message': '建筑无需修理'
            }

        if building.status == BuildingStatus.DESTROYED:
            return {
                'started': False,
                'reason': 'building_destroyed',
                'message': '建筑已被摧毁，无法修理'
            }

        # 寻找可用的工程师
        available_engineers = [eng for eng in self.engineers
                               if len(eng.current_projects) < eng.max_concurrent_projects]

        if not available_engineers:
            return {
                'started': False,
                'reason': 'no_engineers',
                'message': '没有可用的工程师'
            }

        # 选择修理效率最高的工程师
        best_engineer = max(available_engineers,
                            key=lambda e: e.repair_efficiency)

        # 分配修理项目
        if best_engineer.assign_repair_project(building, priority):
            return {
                'started': True,
                'building': building,
                'engineer': best_engineer,
                'damage_to_repair': building.max_health - building.health,
                'message': f'开始修理 {building.name}'
            }
        else:
            return {
                'started': False,
                'reason': 'assignment_failed',
                'message': '无法分配修理任务'
            }

    def summon_engineer(self, engineer_type: EngineerType, x: float, y: float,
                        game_state) -> Dict[str, Any]:
        """
        召唤工程师

        Args:
            engineer_type: 工程师类型
            x, y: 世界坐标
            game_state: 游戏状态

        Returns:
            Dict: 召唤结果
        """
        config = EngineerRegistry.get_config(engineer_type)
        if not config:
            return {
                'summoned': False,
                'reason': 'invalid_type',
                'message': f'未知的工程师类型: {engineer_type}'
            }

        # 检查资源 - 使用ResourceManager
        resource_manager = get_resource_manager(self.game_simulator)
        if not resource_manager.can_afford(gold_cost=config.cost):
            gold_info = resource_manager.get_total_gold()
            return {
                'summoned': False,
                'reason': 'insufficient_gold',
                'message': f'金币不足，需要 {config.cost}，当前 {gold_info.available}'
            }

        # 扣除资源 - 使用ResourceManager
        gold_result = resource_manager.consume_gold(config.cost)
        if not gold_result['success']:
            return {
                'summoned': False,
                'reason': 'resource_consumption_failed',
                'message': f'资源消耗失败: {gold_result}'
            }

        # 创建工程师
        engineer = EngineerRegistry.create_engineer(engineer_type, x, y)
        if not engineer:
            return {
                'summoned': False,
                'reason': 'creation_failed',
                'message': '工程师创建失败'
            }

        # 设置游戏实例引用（如果建筑管理器有的话）
        if hasattr(self, 'game_instance') and self.game_instance:
            engineer.game_instance = self.game_instance

        # 添加到工程师列表
        self.engineers.append(engineer)

        return {
            'summoned': True,
            'engineer': engineer,
            'cost': config.cost,
            'message': f'召唤了 {config.name}'
        }

    def get_building_at(self, x: int, y: int) -> Optional[Building]:
        """
        获取指定位置的建筑

        Args:
            x, y: 瓦片坐标

        Returns:
            Optional[Building]: 建筑对象或None
        """
        for building in self.buildings:
            if building.x == x and building.y == y:
                return building
        return None

    def get_buildings_by_type(self, building_type: BuildingType) -> List[Building]:
        """
        根据类型获取建筑列表

        Args:
            building_type: 建筑类型

        Returns:
            List[Building]: 建筑列表
        """
        return [building for building in self.buildings
                if building.building_type == building_type]

    def get_buildings_by_status(self, status: BuildingStatus) -> List[Building]:
        """
        根据状态获取建筑列表

        Args:
            status: 建筑状态

        Returns:
            List[Building]: 建筑列表
        """
        return [building for building in self.buildings if building.status == status]

    def find_nearest_incomplete_building(self, engineer_x: float, engineer_y: float) -> Optional[Building]:
        """
        找到最近的未完成建筑

        Args:
            engineer_x, engineer_y: 工程师位置

        Returns:
            Optional[Building]: 最近的未完成建筑，如果没有则返回None
        """

        # 获取所有未完成的建筑（建造中、规划中、受损的）
        incomplete_buildings = []
        incomplete_buildings.extend(self.get_buildings_by_status(
            BuildingStatus.UNDER_CONSTRUCTION))
        incomplete_buildings.extend(
            self.get_buildings_by_status(BuildingStatus.PLANNING))

        if not incomplete_buildings:
            return None

        # 找到最近的建筑
        nearest_building = None
        min_distance = float('inf')

        for building in incomplete_buildings:
            # 检查建筑是否已经有工程师在工作
            if self._is_building_being_worked_on(building):
                continue

            # 计算建筑的世界坐标
            building_world_x = building.x * \
                GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
            building_world_y = building.y * \
                GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

            # 计算距离
            distance = math.sqrt((engineer_x - building_world_x)
                                 ** 2 + (engineer_y - building_world_y) ** 2)

            if distance < min_distance:
                min_distance = distance
                nearest_building = building

        return nearest_building

    def find_any_incomplete_building(self) -> Optional[Building]:
        """
        找到任意一个需要工作的建筑（全局查找，不考虑距离）
        包括：未完成建筑、需要修复建筑、空弹药箭塔

        Returns:
            Optional[Building]: 任意一个需要工作的建筑，如果没有则返回None
        """

        # 获取所有需要工作的建筑
        work_needed_buildings = []

        # 1. 未完成的建筑（建造中、规划中）
        work_needed_buildings.extend(self.get_buildings_by_status(
            BuildingStatus.UNDER_CONSTRUCTION))
        work_needed_buildings.extend(
            self.get_buildings_by_status(BuildingStatus.PLANNING))

        # 2. 需要修复的完成建筑（生命值不满）
        for building in self.get_buildings_by_status(BuildingStatus.COMPLETED):
            if building.health < building.max_health:
                work_needed_buildings.append(building)

        # 3. 空弹药的箭塔
        for building in self.buildings:
            if (hasattr(building, 'building_type') and
                building.building_type.value == 'arrow_tower' and
                building.status == BuildingStatus.COMPLETED and
                building.is_active and
                hasattr(building, 'current_ammunition') and
                    building.current_ammunition <= 0):
                work_needed_buildings.append(building)

        # 4. 需要临时金币的兽人巢穴和恶魔巢穴
        for building in self.buildings:
            if (hasattr(building, 'building_type') and
                building.building_type.value in ['orc_lair', 'demon_lair'] and
                building.status == BuildingStatus.COMPLETED and
                building.is_active and
                hasattr(building, 'can_accept_gold') and
                    building.can_accept_gold()):
                work_needed_buildings.append(building)

        # 5. 需要金币的魔法祭坛
        for building in self.buildings:
            if (hasattr(building, 'building_type') and
                building.building_type.value == 'magic_altar' and
                building.status == BuildingStatus.COMPLETED and
                building.is_active and
                hasattr(building, 'can_accept_gold') and
                    building.can_accept_gold()):
                work_needed_buildings.append(building)

        # 返回第一个需要工作的建筑（允许多个工程师选择同一建筑）
        # 只有在真正开始工作时才会锁定建筑，选择阶段不锁定
        if len(work_needed_buildings) > 0 and self.debug_level >= 2:
            game_logger.info(
                f"建筑管理器: 找到 {len(work_needed_buildings)} 个需要工作的建筑")

        # 找到所有没有被工程师在工作的建筑
        available_buildings = []
        for building in work_needed_buildings:
            if not self._is_building_being_worked_on(building):
                available_buildings.append(building)

        # 随机选择一个可用的建筑，避免所有工程师都选择同一个建筑
        if available_buildings:
            import random
            selected_building = random.choice(available_buildings)
            if self.debug_level >= 1:
                game_logger.info(
                    f"✅ 建筑管理器: 随机分配建筑 {selected_building.name} 给工程师")
            return selected_building

        return None

    def _is_building_being_worked_on(self, building) -> bool:
        """检查建筑是否已经有工程师在真正工作（建造、修理、升级中）"""

        # 使用缓存机制，避免重复计算
        if not hasattr(self, '_building_work_cache'):
            self._building_work_cache = {}
            self._cache_frame_counter = 0

        self._cache_frame_counter += 1

        # 每5帧更新一次缓存，提高响应性
        if self._cache_frame_counter % 5 == 0:
            self._building_work_cache.clear()

        # 检查缓存
        if building in self._building_work_cache:
            return self._building_work_cache[building]

        for engineer in self.engineers:
            # 只有当工程师真正在工作状态时才认为建筑被占用
            # 工程师只是设置了target_building但还在游荡或空闲状态时，建筑仍然可用
            if (engineer.target_building == building and
                    engineer.status in [
                        EngineerStatus.CONSTRUCTING,  # 建造中 - 锁定建筑
                        EngineerStatus.REPAIRING,     # 修理中 - 锁定建筑
                        EngineerStatus.UPGRADING,     # 升级中 - 锁定建筑
                        EngineerStatus.DEPOSITING_GOLD,  # 存储金币中 - 锁定建筑
                        EngineerStatus.RELOADING,    # 装填中 - 锁定建筑
                        # 注意：MOVING_TO_SITE 状态不锁定建筑，允许多个工程师前往同一建筑
                        # 注意：FETCHING_RESOURCES 状态不锁定建筑，允许其他工程师接手
                    ]):
                # 只在状态变化时输出日志
                if (building not in self._building_work_cache or not self._building_work_cache[building]) and self.debug_level >= 2:
                    game_logger.info(
                        f"🔒 建筑 {building.name} 被工程师 {engineer.name} 锁定")
                self._building_work_cache[building] = True
                return True

            # 检查工程师的项目列表中是否包含这个建筑
            for project in engineer.current_projects:
                if project['building'] == building:
                    if (building not in self._building_work_cache or not self._building_work_cache[building]) and self.debug_level >= 2:
                        game_logger.info(
                            f"🔒 建筑 {building.name} 在工程师 {engineer.name} 的项目中")
                    self._building_work_cache[building] = True
                    return True

        self._building_work_cache[building] = False
        return False

    def set_debug_level(self, level: int):
        """设置调试日志级别

        Args:
            level: 0=无日志, 1=重要日志, 2=详细日志
        """
        self.debug_level = level
        game_logger.info(f"🔧 建筑管理器调试级别设置为: {level}")

    def clear_building_lock_cache(self):
        """清除建筑锁定缓存，强制重新计算"""
        if hasattr(self, '_building_work_cache'):
            self._building_work_cache.clear()
            game_logger.info("🔧 建筑锁定缓存已清除")

    def get_building_lock_status(self, building) -> Dict[str, Any]:
        """获取建筑的锁定状态信息（用于调试）"""

        locked_by = []
        for engineer in self.engineers:
            if engineer.target_building == building:
                locked_by.append({
                    'engineer_name': engineer.name,
                    'status': engineer.status.value,
                    'carried_gold': engineer.carried_gold
                })

        return {
            'building_name': building.name,
            'is_locked': self._is_building_being_worked_on(building),
            'locked_by': locked_by
        }

    def complete_building_construction(self, building: Building, game_map) -> Dict[str, Any]:
        """
        完成建筑建造，更新地图显示

        Args:
            building: 完成的建筑
            game_map: 游戏地图

        Returns:
            Dict: 完成结果
        """

        # 确保建筑状态为COMPLETED
        if building.status != BuildingStatus.COMPLETED:
            building.status = BuildingStatus.COMPLETED
            building.is_active = True
            building.construction_progress = 1.0

            # 确保建筑生命值达到最大值
            if hasattr(building, 'max_health') and hasattr(building, 'health'):
                building.health = building.max_health

        # 更新地图 - 将灰色像素地块转化为原本像素块
        # 使用瓦片坐标而不是像素坐标
        x, y = building.tile_x, building.tile_y

        if 0 <= y < len(game_map) and 0 <= x < len(game_map[0]):
            tile = game_map[y][x]
            if tile:

                # 移除未完成标记
                tile.is_incomplete = False

                # 更新为正常的房间类型
                new_room_type = building.building_type.value
                tile.room_type = new_room_type
                tile.room = new_room_type  # 同时设置room属性，用于资源生成检查

                # 同步建筑生命值到tile对象
                if hasattr(building, 'max_health') and hasattr(building, 'health'):
                    tile.health = building.health
                    tile.max_health = building.max_health

                # 标记需要重新渲染
                tile.needs_rerender = True

                game_logger.info(
                    f"🔍 [TREASURY_FLOW] 更新瓦片属性 - room_type: {tile.room_type}, room: {tile.room}")

                game_logger.info(
                    f"✅ 建筑完成：{building.name} 地图瓦片已更新 - room_type: {tile.room_type}")
            else:
                game_logger.info(f"❌ 瓦片对象为None")
        else:
            game_logger.info(f"❌ 建筑位置超出地图范围！")

        # 注册建筑到ResourceManager
        self._register_building_to_resource_manager(building)

        result = {
            'completed': True,
            'building': building,
            'message': f'{building.name} 建造完成！',
            'needs_rerender': True  # 标记需要重新渲染
        }
        return result

    def _register_building_to_resource_manager(self, building: Building):
        """
        将建筑注册到ResourceManager

        Args:
            building: 建筑对象
        """
        try:
            resource_manager = get_resource_manager(self.game_simulator)

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

        except Exception as e:
            game_logger.info(f"❌ 注册建筑到ResourceManager失败: {e}")

    def get_magic_altar_statistics(self) -> Dict[str, Any]:
        """获取魔法祭坛统计信息"""
        stats = self.magic_altar_stats.copy()

        # 添加详细统计
        stats.update({
            'altar_details': [],
            'total_altars': 0,
            'completed_altars': 0,
            'under_construction_altars': 0,
        })

        # 统计各种状态的祭坛
        for building in self.buildings:
            if (hasattr(building, 'building_type') and
                    building.building_type.value == 'magic_altar'):
                stats['total_altars'] += 1

                if building.status == BuildingStatus.COMPLETED:
                    stats['completed_altars'] += 1
                elif building.status == BuildingStatus.UNDER_CONSTRUCTION:
                    stats['under_construction_altars'] += 1

                # 添加详细统计
                if hasattr(building, 'get_detailed_report'):
                    altar_report = building.get_detailed_report()
                    stats['altar_details'].append(altar_report)

        # 计算效率指标
        if stats['active_altars'] > 0:
            stats['mana_per_altar_per_hour'] = (stats['total_mana_generated'] /
                                                max(stats['total_uptime'], 1)) * 3600 / stats['active_altars']
            stats['transfer_efficiency'] = (stats['total_mana_transferred'] /
                                            max(stats['total_mana_generated'], 1)) * 100
        else:
            stats['mana_per_altar_per_hour'] = 0
            stats['transfer_efficiency'] = 0

        return stats

    def get_engineer_statistics(self) -> Dict[str, Any]:
        """获取工程师统计信息"""
        stats = {
            'total_engineers': len(self.engineers),
            'by_type': {},
            'by_status': {},
            'efficiency_stats': {
                'average_efficiency': 0.0,
                'total_projects': 0,
                'idle_engineers': 0,
                'busy_engineers': 0
            }
        }

        # 按类型统计
        for engineer_type in EngineerType:
            stats['by_type'][engineer_type.value] = len([
                eng for eng in self.engineers if eng.engineer_type == engineer_type
            ])

        # 按状态统计
        for status in EngineerStatus:
            stats['by_status'][status.value] = len([
                eng for eng in self.engineers if eng.status == status
            ])

        # 效率统计
        if self.engineers:
            total_efficiency = sum(
                eng.build_efficiency for eng in self.engineers)
            stats['efficiency_stats']['average_efficiency'] = total_efficiency / \
                len(self.engineers)
            stats['efficiency_stats']['total_projects'] = sum(
                len(eng.current_projects) for eng in self.engineers)
            stats['efficiency_stats']['idle_engineers'] = stats['by_status'].get(
                'idle', 0)
            stats['efficiency_stats']['busy_engineers'] = len(
                self.engineers) - stats['efficiency_stats']['idle_engineers']

        return stats

    def get_building_statistics(self) -> Dict[str, Any]:
        """获取建筑统计信息"""
        stats = {
            'total_buildings': len(self.buildings),
            'by_type': {},
            'by_status': {},
            'by_category': {},
            'construction_stats': {
                'total_built': self.total_buildings_built,
                'total_gold_spent': self.total_gold_spent,
                'under_construction': 0,
                'completed': 0,
            }
        }

        # 按类型统计
        for building_type in BuildingType:
            stats['by_type'][building_type.value] = len([
                building for building in self.buildings if building.building_type == building_type
            ])

        # 按状态统计
        for status in BuildingStatus:
            stats['by_status'][status.value] = len([
                building for building in self.buildings if building.status == status
            ])

        # 按分类统计
        for category in BuildingCategory:
            stats['by_category'][category.value] = len([
                building for building in self.buildings if building.category == category
            ])

        # 建造统计
        stats['construction_stats']['under_construction'] = stats['by_status'].get(
            'under_construction', 0)
        stats['construction_stats']['completed'] = stats['by_status'].get(
            'completed', 0)

        return stats

    def _check_building_terrain(self, x: int, y: int, config, game_map) -> Dict[str, Any]:
        """检查建筑地形是否合适"""
        # 边界检查
        if not (0 <= x < GameConstants.MAP_WIDTH and 0 <= y < GameConstants.MAP_HEIGHT):
            return {
                'suitable': False,
                'message': '位置超出地图边界'
            }

        # 检查占地面积
        width, height = config.size
        for dy in range(height):
            for dx in range(width):
                check_x, check_y = x + dx, y + dy
                if not (0 <= check_x < GameConstants.MAP_WIDTH and 0 <= check_y < GameConstants.MAP_HEIGHT):
                    return {
                        'suitable': False,
                        'message': f'建筑占地面积超出地图边界'
                    }

                tile = game_map[check_y][check_x]

                # 大部分建筑需要在已挖掘的地面上
                if config.building_type != BuildingType.DUNGEON_HEART:
                    if tile.type not in [TileType.GROUND] or not tile.is_dug:
                        return {
                            'suitable': False,
                            'message': f'位置({check_x}, {check_y})不是已挖掘的地面'
                        }

                # 检查是否已有建筑
                if tile.room_type is not None:
                    return {
                        'suitable': False,
                        'message': f'位置({check_x}, {check_y})已有建筑'
                    }

        return {'suitable': True}

    def _get_available_engineers(self, required_count: int = 1) -> List[Engineer]:
        """获取可用的工程师列表"""
        available = []
        for engineer in self.engineers:
            if len(engineer.current_projects) < engineer.max_concurrent_projects:
                available.append(engineer)
                if len(available) >= required_count * 2:  # 获取足够的候选者
                    break

        # 按效率排序
        available.sort(key=lambda e: e.build_efficiency, reverse=True)
        return available

    def _process_construction_queue(self, result: Dict[str, Any]):
        """处理建造队列"""
        # 这里可以实现更复杂的队列管理逻辑
        # 例如自动开始下一个建造项目
        pass

    def _process_upgrade_queue(self, result: Dict[str, Any]):
        """处理升级队列"""
        # 这里可以实现升级队列管理逻辑
        pass

    def _process_repair_queue(self, result: Dict[str, Any]):
        """处理修理队列"""
        # 自动修理生命值不满的完成建筑
        for building in self.get_buildings_by_status(BuildingStatus.COMPLETED):
            if building.health < building.max_health:
                # 检查是否已有工程师在修理
                being_repaired = any(
                    building in [p['building']
                                 for p in eng.current_projects if p['type'] == 'repair']
                    for eng in self.engineers
                )

                if not being_repaired:
                    repair_result = self.start_repair(
                        building, priority=3)  # 低优先级
                    if repair_result['started']:
                        result['events'].append(f"自动开始修理 {building.name}")

    def _handle_building_production(self, building: Building, production: Dict[str, Any], game_state):
        # 处理法力产出 - 使用ResourceManager
        if 'mana_generated' in production:
            resource_manager = get_resource_manager(self.game_simulator)
            resource_manager.add_mana(production['mana_generated'], building)

        # 处理召唤完成事件
        if 'summon_completed' in production and production['summon_completed']:
            self._handle_summon_completed(building, production, game_state)

        # 处理训练完成事件
        if 'training_completed' in production and production['training_completed']:
            self._handle_training_completed(building, production, game_state)

    def _handle_summon_completed(self, building: Building, production: Dict[str, Any], game_state):
        """处理召唤完成事件，将召唤的怪物添加到游戏世界"""
        if not hasattr(building, 'bound_monster') or not building.bound_monster:
            return

        summoned_creature = building.bound_monster

        # 将召唤的怪物添加到游戏世界的怪物列表中
        # 优先使用game_instance（真实游戏），其次使用game_simulator（模拟器）
        game_world = None
        if hasattr(self, 'game_instance') and self.game_instance:
            game_world = self.game_instance
        elif hasattr(self, 'game_simulator') and self.game_simulator:
            game_world = self.game_simulator

        if game_world and hasattr(game_world, 'monsters'):
            game_world.monsters.append(summoned_creature)
            game_logger.info(
                "🔮 召唤的怪物已添加到游戏世界: {creature_type} at ({x}, {y})",
                creature_type=summoned_creature.type, x=summoned_creature.x, y=summoned_creature.y)
        else:
            game_logger.warning(
                "⚠️ 无法访问游戏世界的monsters列表，无法添加召唤的怪物")

    def _handle_training_completed(self, building: Building, production: Dict[str, Any], game_state):
        """处理训练完成事件，将训练的怪物添加到游戏世界"""
        if not hasattr(building, 'bound_monster') or not building.bound_monster:
            return

        trained_creature = building.bound_monster

        # 将训练的怪物添加到游戏世界的怪物列表中
        # 优先使用game_instance（真实游戏），其次使用game_simulator（模拟器）
        game_world = None
        if hasattr(self, 'game_instance') and self.game_instance:
            game_world = self.game_instance
            game_logger.info(
                f"🏹 [TRAINING_COMPLETE] 使用真实游戏实例: {type(game_world).__name__}")
        elif hasattr(self, 'game_simulator') and self.game_simulator:
            game_world = self.game_simulator
            game_logger.info(
                f"🏹 [TRAINING_COMPLETE] 使用模拟器实例: {type(game_world).__name__}")
        else:
            game_logger.warning(f"🏹 [TRAINING_COMPLETE] 无法找到游戏世界实例")

        if game_world and hasattr(game_world, 'monsters'):
            game_world.monsters.append(trained_creature)
            game_logger.info(
                "🏹 训练的怪物已添加到游戏世界: {creature_type} at ({x}, {y})",
                creature_type=trained_creature.type, x=trained_creature.x, y=trained_creature.y)
        else:
            game_logger.warning(
                "⚠️ 无法访问游戏世界的monsters列表，无法添加训练的怪物")

        # 清理死亡的哥布林苦工（从游戏世界中移除）
        # 注意：这里只标记苦工为死亡，实际的清理由主循环的 _cleanup_dead_units 统一处理
        if game_world and hasattr(game_world, 'monsters'):
            # 查找并标记死亡的哥布林苦工
            for monster in game_world.monsters:
                if (hasattr(monster, 'type') and monster.type == 'goblin_worker' and
                        hasattr(monster, 'is_dead_flag') and monster.is_dead_flag):
                    # 苦工已经被标记为死亡，_cleanup_dead_units 会统一处理
                    game_logger.info(
                        "🏹 哥布林苦工已标记为死亡，等待统一清理: at ({x}, {y})",
                        x=monster.x, y=monster.y)

    def _update_magic_altar_stats(self, altar, delta_seconds: float):
        """更新魔法祭坛统计信息"""
        if not hasattr(altar, 'get_resource_statistics'):
            return

        # 获取祭坛的统计信息
        altar_stats = altar.get_resource_statistics()

        # 更新全局统计
        self.magic_altar_stats['total_mana_generated'] += altar_stats.get(
            'total_mana_generated', 0)
        self.magic_altar_stats['total_mana_transferred'] += altar_stats.get(
            'total_mana_transferred', 0)
        self.magic_altar_stats['total_uptime'] += delta_seconds

        # 计算活跃祭坛数量
        active_altars = 0
        altars_with_mages = 0

        for building in self.buildings:
            if (hasattr(building, 'building_type') and
                    building.building_type.value == 'magic_altar'):
                if building.status == BuildingStatus.COMPLETED and building.is_active:
                    active_altars += 1
                    if hasattr(building, 'assigned_mage') and building.assigned_mage:
                        altars_with_mages += 1

        self.magic_altar_stats['active_altars'] = active_altars
        self.magic_altar_stats['altars_with_mages'] = altars_with_mages

        # 计算平均效率
        if active_altars > 0:
            total_efficiency = 0
            for building in self.buildings:
                if (hasattr(building, 'building_type') and
                    building.building_type.value == 'magic_altar' and
                        building.status == BuildingStatus.COMPLETED and building.is_active):
                    if hasattr(building, 'get_resource_statistics'):
                        stats = building.get_resource_statistics()
                        total_efficiency += stats.get('efficiency_rating', 0)
            self.magic_altar_stats['average_efficiency'] = total_efficiency / active_altars

    def destroy_building(self, building: Building) -> Dict[str, Any]:
        """
        摧毁建筑

        Args:
            building: 目标建筑

        Returns:
            Dict: 摧毁结果
        """
        if building not in self.buildings:
            return {
                'destroyed': False,
                'reason': 'building_not_found',
                'message': '建筑不存在'
            }

        # 释放分配的工程师
        for engineer in building.assigned_engineers[:]:
            engineer.cancel_project(building)

        # 从建筑列表中移除
        self.buildings.remove(building)

        # 标记为摧毁状态
        building.status = BuildingStatus.DESTROYED
        building.is_active = False

        return {
            'destroyed': True,
            'building_name': building.name,
            'engineers_released': len(building.assigned_engineers),
            'message': f'{building.name} 已被摧毁'
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取建筑管理器统计信息"""
        stats = {
            'total_buildings': len(self.buildings),
            'total_engineers': len(self.engineers),
            'buildings_built': self.total_buildings_built,
            'gold_spent': self.total_gold_spent,
            'construction_queue_size': len(self.construction_queue),
            'upgrade_queue_size': len(self.upgrade_queue),
            'repair_queue_size': len(self.repair_queue),
            'efficiency_stats': self.efficiency_stats.copy(),
            'magic_altar_stats': self.magic_altar_stats.copy()
        }

        # 添加分配器统计信息
        assigner_stats = self.engineer_assigner.get_statistics()
        stats['assigner_stats'] = assigner_stats

        return stats

    def set_assigner_strategy(self, strategy: AssignmentStrategy):
        """设置工程师分配策略"""
        self.engineer_assigner.set_strategy(strategy)
        game_logger.info(f"建筑管理器: 分配策略已更改为 {strategy.value}")

    def get_assigner_statistics(self) -> Dict[str, Any]:
        """获取工程师分配器统计信息"""
        return self.engineer_assigner.get_statistics()

    def clear_all_assignments(self):
        """清除所有任务分配"""
        self.engineer_assigner.clear_all_tasks()
        game_logger.info("建筑管理器: 已清除所有任务分配")
