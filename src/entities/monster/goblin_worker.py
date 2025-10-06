#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哥布林苦工行动类
从 Creature 类中提取的苦工专用逻辑
"""

import math
import time
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

from src.core.constants import GameConstants
from src.core.enums import TileType
from src.core.game_state import Tile
from src.entities.monsters import Monster
from src.utils.logger import game_logger
from src.managers.movement_system import MovementSystem
from src.systems.reachability_system import get_reachability_system
from src.managers.gold_mine_manager import get_gold_mine_manager
from src.managers.optimized_mining_system import get_optimized_mining_system, MiningEventType
from src.ui.status_indicator import StatusIndicator


class WorkerStatus(Enum):
    """苦工状态枚举 - 备用定义"""
    IDLE = "idle"                          # 空闲
    WANDERING = "wandering"                # 游荡
    MOVING_TO_MINE = "moving_to_mine"      # 移动到挖掘点
    MINING = "mining"                      # 挖掘中
    RETURNING_TO_BASE = "returning_to_base"  # 返回基地
    MOVING_TO_TRAINING = "moving_to_training"  # 前往训练地点
    TRAINING = "training"                  # 训练中
    FLEEING = "fleeing"                    # 逃跑中


class GoblinWorker(Monster):
    """哥布林苦工 - 专门负责挖掘和资源收集"""

    def __init__(self, x: int, y: int):
        super().__init__(x, y, 'goblin_worker')

        # 设置友好的名称
        self.name = '苦工'

        # 设置工人类型（用于模拟器渲染识别）
        self.worker_type = 'goblin_worker'

        # 设置为非战斗单位
        self.is_combat_unit = False

        # 苦工特有属性
        self.carried_gold = 0  # 携带的金币数量
        self.max_carry_capacity = 20  # 最大携带容量
        self.deposit_target = None  # 存储目标（地牢之心）
        self.mining_target = None  # 挖掘目标

        # 初始化移动系统状态
        MovementSystem.initialize_unit(self)

        # 挖掘状态管理
        self.is_mining_assigned = False  # 是否已注册为挖掘者
        self.last_mining_time = 0  # 上次挖掘时间

        # 调试计数器
        self._debug_counter = 0

        # 挖掘日志计数器 - 每5次挖掘输出一次日志
        self._mining_log_counter = 0

        # 训练任务相关属性
        self.assigned_building = None  # 分配的建筑
        self.task_type = None  # 任务类型
        self.target_building = None  # 目标建筑

        # 目标稳定性管理
        self._target_switch_cooldown = 0  # 目标切换冷却时间
        self._last_target_switch_time = 0  # 上次切换目标的时间
        self.status_indicator = StatusIndicator()

        # 工作分配器（延迟导入避免循环依赖）
        self.worker_assigner = None

        # 设置苦工初始状态
        self.state = WorkerStatus.IDLE.value

    def update(self, delta_time: float, game_map: List[List[Tile]], creatures: List = None, heroes: List = None, effect_manager=None, building_manager=None, game_instance=None):
        """更新哥布林苦工行为"""
        # 保存游戏实例引用
        if game_instance:
            self.game_instance = game_instance

        # 首先调用父类的update方法，包含状态切换器
        super().update(delta_time, creatures or [], game_map, effect_manager)

        # 然后执行苦工特有的行为逻辑
        self._update_goblin_behavior(
            delta_time, game_map, heroes or [], effect_manager)

        # 管理空闲状态和任务分配
        self._manage_idle_state(game_instance, building_manager)

    def _update_goblin_behavior(self, delta_time: float, game_map: List[List[Tile]], heroes: List, effect_manager=None):
        """哥布林苦工行为更新 - 按照COMBAT_SYSTEM.md规范实现

        优先级顺序：
        1. WorkerAssigner任务 - 自动分配的任务，来自target_building（训练任务等）
        2. 逃离敌人 - 安全第二，60像素检测范围
        3. 存储金币 - 当携带金币达到最大容量时
        4. 挖掘金矿 - 主要工作，寻找并挖掘金矿
        5. 游荡 - 空闲状态，寻找新目标
        """
        # 添加调试信息
        if not hasattr(self, '_debug_update_counter'):
            self._debug_update_counter = 0
        self._debug_update_counter += 1

        if self._debug_update_counter % 60 == 0:  # 每秒输出一次
            game_logger.info(
                f"🔧 苦工 {self.name} 状态更新: 状态={self.state}, 位置=({self.x:.1f}, {self.y:.1f}), 目标={self.mining_target}")
        # 优先级1: 检查WorkerAssigner分配的任务 - 最高优先级
        if hasattr(self, 'target_building') and self.target_building and hasattr(self, 'task_type'):
            if self.task_type == 'training':
                self._handle_training_task(delta_time, game_map)
                return

        # 优先级2: 逃离敌人 (60像素检测范围) - 安全第二
        nearest_hero = self._find_nearest_hero(heroes, 60)
        if nearest_hero:
            self._cleanup_mining_assignment(game_map)
            self.mining_target = None
            self.state = WorkerStatus.FLEEING.value
            # 使用逃离移动，速度提升20%
            MovementSystem.flee_movement(
                self, (nearest_hero.x, nearest_hero.y), delta_time, game_map, 1.2)
            return

        # 优先级3: 存储金币 - 当携带金币达到最大容量的80%时就开始存储（智能存储触发）
        storage_threshold = int(
            self.max_carry_capacity)
        if int(self.carried_gold) >= storage_threshold:
            self.state = WorkerStatus.RETURNING_TO_BASE.value
            # 寻找最近的存储点（金库或主基地）
            storage_target = self._find_nearest_storage(game_map)
            if storage_target:
                target_pos = (storage_target['x'], storage_target['y'])
                # 计算到存储点的距离
                dx = target_pos[0] - self.x
                dy = target_pos[1] - self.y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance > 20:  # 恢复正常的交互范围
                    # 还没到达，使用新的分离式寻路+移动系统
                    MovementSystem.pathfind_and_move(
                        self, target_pos, delta_time, game_map, "A_STAR", 1.0)
                else:
                    # 到达存储点，存储金币
                    self._deposit_gold_to_storage(storage_target)
            else:
                # 没有找到存储点，直接存储到主基地
                game_logger.info(f"⚠️ 苦工没有找到金库，直接存储到主基地")
                self._deposit_gold()
            return

        # 优先级4: 挖掘金矿
        if not self.mining_target:
            # 检查目标切换冷却时间
            import time
            current_time = time.time()
            if current_time - self._last_target_switch_time > 0.2:  # 状态冷却优化到0.2秒，提高响应速度
                self.mining_target = self._find_best_reachable_gold_vein(
                    game_map)
                if self.mining_target:
                    game_logger.info(f"🎯 苦工选择金矿目标: {self.mining_target}")
                    self._last_target_switch_time = current_time

        if self.mining_target:
            mx, my = self.mining_target
            target_pos = (mx * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                          my * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)

            # 检查矿脉是否仍然有效（包括已挖掘的金矿和接壤的未挖掘金矿）
            # 修复：添加对空game_map的检查，避免IndexError
            if not game_map or len(game_map) == 0 or len(game_map[0]) == 0:
                tile = None
            else:
                tile = game_map[my][mx] if (0 <= mx < len(
                    game_map[0]) and 0 <= my < len(game_map)) else None
            is_valid_vein = False

            if tile:
                # 检查金矿脉状态
                is_gold_vein = getattr(tile, 'is_gold_vein', False)
                gold_amount = getattr(tile, 'gold_amount', 0)
                tile_type = getattr(tile, 'type', None)

                if is_gold_vein and gold_amount > 0:
                    # 有效的金矿脉（有储量）
                    is_valid_vein = True

            # 检查是否已经到达目标位置
            dx = target_pos[0] - self.x
            dy = target_pos[1] - self.y
            distance_to_target = math.sqrt(dx * dx + dy * dy)
            is_at_target = distance_to_target <= 25  # 25像素范围内算到达

            if not is_valid_vein:
                # 矿脉无效，寻找新目标
                game_logger.info(f"❌ 矿脉 ({mx}, {my}) 无效，寻找新目标")
                self._cleanup_mining_assignment(game_map)
                self.mining_target = None
            elif not is_at_target:
                # 目标仍然有效但未到达，使用新的分离式寻路+移动系统
                self.state = WorkerStatus.MOVING_TO_MINE.value

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

                MovementSystem.pathfind_and_move(
                    self, target_pos, delta_time, game_map, "A_STAR", 1.5)
                # 添加调试信息
                if not hasattr(self, '_debug_counter'):
                    self._debug_counter = 0
                self._debug_counter += 1
                if self._debug_counter % 60 == 0:  # 每秒输出一次
                    game_logger.info(
                        f"🚶 苦工继续移动到金矿 ({mx}, {my})，当前距离: {distance_to_target:.1f}px，当前位置: ({self.x:.1f}, {self.y:.1f})px")
            elif is_valid_vein and is_at_target:
                # 目标仍然有效且已到达，继续当前目标

                # 增大采矿范围以避免环境碰撞体积冲突
                mining_range = 20

                if distance_to_target > mining_range:
                    # 还没到达金矿，继续移动
                    self.state = WorkerStatus.MOVING_TO_MINE.value

                    # 记录移动前的位置
                    old_x, old_y = self.x, self.y

                    # 执行移动
                    # 添加移动系统状态调试
                    unit_state = MovementSystem.get_unit_state(self)
                    game_logger.info(
                        f"   移动前状态: {unit_state.movement_state.value}, 目标队列: {len(unit_state.target_queue)}")

                    # 更新目标可视化（灰色虚线）
                    MovementSystem.update_target_line(
                        (self.x, self.y), target_pos,
                        self.name, (128, 128, 128)  # 灰色
                    )

                    movement_result = MovementSystem.pathfind_and_move(
                        self, target_pos, delta_time, game_map, "A_STAR", 1.5)

                    # 添加移动后状态调试
                    unit_state_after = MovementSystem.get_unit_state(self)
                    game_logger.info(
                        f"   移动后状态: {unit_state_after.movement_state.value}, 目标队列: {len(unit_state_after.target_queue)}")

                    # 记录移动后的位置
                    new_x, new_y = self.x, self.y
                    moved_distance = math.sqrt(
                        (new_x - old_x) ** 2 + (new_y - old_y) ** 2)

                    # 添加调试信息
                    self._debug_counter += 1
                    if self._debug_counter % 60 == 0:  # 每秒输出一次
                        game_logger.info(
                            f"🚶 苦工移动到金矿 ({mx}, {my})，当前距离: {distance_to_target:.1f}px，目标范围: {mining_range}px")
                        game_logger.info(
                            f"   位置变化: ({old_x:.1f}, {old_y:.1f})px -> ({new_x:.1f}, {new_y:.1f})px")
                        game_logger.info(
                            f"   移动距离: {moved_distance:.1f}px，移动结果: {movement_result}")
                        game_logger.info(
                            f"   目标像素坐标: ({target_pos[0]}, {target_pos[1]})px")
                else:
                    # 重置调试计数器，避免无限累积
                    self._debug_counter = 0

                    # 检查是否为未挖掘的金矿脉
                    if (hasattr(tile, 'is_gold_vein') and tile.is_gold_vein and
                            hasattr(tile, 'type') and tile.type == TileType.ROCK):  # 未挖掘的金矿脉
                        # 清除目标连线（到达目标后开始挖掘）
                        MovementSystem.clear_unit_target_lines(self.name)

                        # 先挖掘金矿脉 - 使用新的挖掘方法
                        game_logger.info(f"⛏️ 苦工开始挖掘金矿脉 ({mx}, {my})")
                        dig_result = tile.dig(
                            cost=0, game_state=None, x=mx, y=my)
                        if dig_result['success']:
                            game_logger.info(f"💰 {dig_result['message']}")
                            # 挖掘成功后，金矿变为可挖掘状态
                            tile.type = TileType.GOLD_VEIN

                            # 注册新金矿发现事件
                            mining_system = get_optimized_mining_system()
                            mining_system.register_event(
                                MiningEventType.GOLD_VEIN_DISCOVERED, mx, my)

                            # 继续处理挖掘逻辑
                        else:
                            game_logger.info(
                                f"❌ 挖掘金矿脉失败: {dig_result['message']}")
                            self.mining_target = None
                            return

                    if hasattr(self, 'is_mining_assigned') and self.is_mining_assigned:
                        # 已经注册为挖掘者，直接挖掘
                        self.state = WorkerStatus.MINING.value
                        self._perform_mining(game_map, delta_time)
                    else:
                        # 尚未注册，尝试开始挖掘
                        game_logger.info(f"🔧 苦工尝试注册金矿 ({mx}, {my}) 进行挖掘")
                        if self._start_mining(game_map):
                            # 成功注册，开始挖掘
                            game_logger.info(f"✅ 苦工成功注册金矿 ({mx}, {my})，开始挖掘")
                            self.state = WorkerStatus.MINING.value
                            self._perform_mining(game_map, delta_time)
                        else:
                            # 注册失败（金矿满员），寻找新目标
                            game_logger.info(f"⚠️ 金矿 ({mx}, {my}) 注册失败，寻找新目标")
                            old_target = self.mining_target

                            # 检查目标切换冷却时间
                            import time
                            current_time = time.time()
                            if current_time - self._last_target_switch_time > 0.2:  # 保持0.2秒冷却时间，避免过于频繁切换
                                self.mining_target = self._find_best_reachable_gold_vein(
                                    game_map)
                                if self.mining_target and self.mining_target != old_target:
                                    game_logger.info(
                                        f"🎯 苦工切换金矿目标: {old_target} -> {self.mining_target}")
                                    self._last_target_switch_time = current_time
                                elif not self.mining_target:
                                    self.state = WorkerStatus.WANDERING.value
                                    game_logger.info("🎲 没有其他可用金矿，开始游荡")
                            else:
                                # 冷却时间内，暂时游荡
                                self.state = WorkerStatus.WANDERING.value
                                game_logger.info("⏰ 目标切换冷却中，暂时游荡")
        else:
            # 优先级5: 游荡 - 在游荡时也要尝试寻找金矿
            self.state = WorkerStatus.WANDERING.value

            # 在游荡时也要检查是否有可用的金矿（高频检查，支持中断）
            import time
            current_time = time.time()
            if current_time - self._last_target_switch_time > 0.2:  # 游荡时寻找目标冷却优化到0.2秒，提高响应速度
                new_target = self._find_best_reachable_gold_vein(game_map)
                if new_target:
                    self.mining_target = new_target
                    game_logger.info(f"🎯 苦工在游荡中发现金矿目标: {new_target}")
                    self._last_target_switch_time = current_time
                    # 找到目标后立即切换到移动状态，中断当前游荡
                    return

            # 定义中断检查函数
            def check_for_work_interrupt():
                """检查是否有工作机会需要中断游荡"""
                import time
                interrupt_time = time.time()
                if interrupt_time - self._last_target_switch_time > 0.1:  # 更短的冷却时间，支持快速响应
                    new_target = self._find_best_reachable_gold_vein(game_map)
                    if new_target:
                        self.mining_target = new_target
                        game_logger.info(f"🎯 苦工在游荡移动中发现金矿目标: {new_target}")
                        self._last_target_switch_time = interrupt_time
                        return True  # 需要中断游荡
                return False  # 继续游荡

            # 执行支持中断的游荡移动
            wandering_completed = MovementSystem.wandering_movement(
                self, delta_time, game_map, 0.3, interrupt_check=check_for_work_interrupt)

            # 如果游荡被中断（发现工作），立即返回
            if wandering_completed and self.mining_target:
                return

    def _find_nearest_hero(self, heroes: List, max_distance: float):
        """寻找最近的英雄"""
        nearest_hero = None
        nearest_distance = float('inf')

        for hero in heroes:
            distance = math.sqrt((hero.x - self.x) **
                                 2 + (hero.y - self.y) ** 2)
            if distance < max_distance and distance < nearest_distance:
                nearest_distance = distance
                nearest_hero = hero

        return nearest_hero

    def _get_dungeon_heart_position(self, game_map: List[List[Tile]]):
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

    def _find_best_reachable_gold_vein(self, game_map: List[List[Tile]]) -> Optional[Tuple[int, int]]:
        """寻找最佳可达金矿 - 使用综合优化系统"""
        # 修复：检查game_map是否为空，避免IndexError
        if not game_map or len(game_map) == 0 or len(game_map[0]) == 0:
            game_logger.info("❌ 游戏地图为空，无法寻找金矿")
            return None

        # 获取综合优化挖掘系统
        mining_system = get_optimized_mining_system()

        # 确保可达性系统已初始化
        if hasattr(self, 'game_instance') and self.game_instance:
            dungeon_heart_pos = self.game_instance.dungeon_heart_pos
            if dungeon_heart_pos:
                mining_system.reachability_system.set_base_position(
                    dungeon_heart_pos[0], dungeon_heart_pos[1])
                game_logger.info(f"🏰 设置主基地位置: {dungeon_heart_pos}")
                # 强制更新可达性
                mining_system.reachability_system.update_reachability(
                    game_map, force_update=True)
            else:
                game_logger.info("⚠️ 主基地位置未设置")
                # 如果没有主基地位置，尝试使用苦工当前位置作为起点
                current_tile_x = int(self.x // GameConstants.TILE_SIZE)
                current_tile_y = int(self.y // GameConstants.TILE_SIZE)
                mining_system.reachability_system.set_base_position(
                    current_tile_x, current_tile_y)
                game_logger.info(
                    f"🏰 使用苦工位置作为起点: ({current_tile_x}, {current_tile_y})")
                # 强制更新可达性
                mining_system.reachability_system.update_reachability(
                    game_map, force_update=True)
        else:
            game_logger.info("⚠️ 游戏实例未设置")
            # 如果没有游戏实例，尝试使用苦工当前位置作为起点
            current_tile_x = int(self.x // GameConstants.TILE_SIZE)
            current_tile_y = int(self.y // GameConstants.TILE_SIZE)
            mining_system.reachability_system.set_base_position(
                current_tile_x, current_tile_y)
            game_logger.info(
                f"🏰 使用苦工位置作为起点: ({current_tile_x}, {current_tile_y})")
            # 强制更新可达性
            mining_system.reachability_system.update_reachability(
                game_map, force_update=True)

        # 强制更新金矿管理器，确保获取最新信息
        mining_system.gold_mine_manager.force_update(game_map)

        # 获取金矿管理器统计信息
        gold_mine_stats = mining_system.gold_mine_manager.get_stats()
        game_logger.info(
            f"💰 金矿管理器统计: 总金矿={gold_mine_stats['total_mines']}, 可用金矿={gold_mine_stats['available_mines']}, 总储量={gold_mine_stats['total_gold_amount']}")

        # 获取可达性系统统计信息
        reachability_stats = mining_system.reachability_system.get_stats()
        game_logger.info(
            f"🗺️ 可达性系统统计: 可达瓦片={reachability_stats['reachable_tiles_count']}, 主基地位置={reachability_stats['base_position']}")

        # 获取可达的金矿（综合优化）
        reachable_veins = mining_system.get_reachable_gold_mines(game_map)

        game_logger.info(
            f"🔍 苦工 {self.name} 寻找金矿: 找到 {len(reachable_veins)} 个可达金矿")

        if not reachable_veins:
            game_logger.info(f"❌ 苦工 {self.name} 没有找到可达的金矿")
            return None

        # 获取当前苦工位置
        current_tile_x = int(self.x // GameConstants.TILE_SIZE)
        current_tile_y = int(self.y // GameConstants.TILE_SIZE)

        # 收集候选金矿
        candidate_veins = []
        search_radius = 15  # 搜索半径

        for x, y, gold_amount in reachable_veins:
            # 使用欧几里得距离计算
            distance_to_worker = math.sqrt(
                (x - current_tile_x) ** 2 + (y - current_tile_y) ** 2)

            # 只搜索指定半径内的金矿
            if distance_to_worker > search_radius:
                continue

            # 使用金矿管理器检查金矿是否可用
            if not mining_system.is_mine_available(x, y):
                continue

            # 获取金矿信息
            mine_info = mining_system.gold_mine_manager.get_gold_mine_info(
                x, y)
            if not mine_info:
                continue

            miners_count = mine_info['miners_count']

            # 排除当前目标，避免重复选择
            if self.mining_target and (x, y) == self.mining_target:
                continue

            # 计算到主基地的距离（使用欧几里得距离）
            if hasattr(self, 'game_instance') and self.game_instance:
                heart_x, heart_y = self.game_instance.dungeon_heart_pos
                distance_to_heart = math.sqrt(
                    (x - heart_x) ** 2 + (y - heart_y) ** 2)
            else:
                distance_to_heart = 0

            # 计算综合评分：考虑距离、黄金储量、挖掘者数量
            # 评分越高越好：距离近、黄金多、挖掘者少
            gold_score = gold_amount  # 黄金储量
            miner_penalty = miners_count * 15  # 增加挖掘者惩罚，鼓励选择挖掘者少的金矿
            distance_penalty = distance_to_worker * 2  # 距离惩罚

            # 添加苦工个人偏好，让不同苦工选择不同目标
            personal_preference = hash(
                self.name) % 100 / 100.0  # 0-1之间的个人偏好值

            # 综合评分 = 黄金储量 - 挖掘者惩罚 - 距离惩罚 + 个人偏好
            total_score = gold_score - miner_penalty - \
                distance_penalty + personal_preference * 5

            candidate_veins.append(
                (x, y, total_score, distance_to_worker, gold_amount, miners_count))

        if not candidate_veins:
            game_logger.info("❌ 在搜索半径内没有可用的金矿")
            return None

        # 按综合评分排序
        candidate_veins.sort(key=lambda vein: vein[2], reverse=True)

        # 智能选择策略：优先选择挖掘者少的金矿，避免所有苦工挤在同一个金矿
        import random

        # 如果候选金矿较多，给每个苦工一些选择余地
        if len(candidate_veins) > 1:
            # 从评分最高的前3个金矿中随机选择一个，增加分散性
            top_candidates = candidate_veins[:min(3, len(candidate_veins))]
            # 但优先选择挖掘者少的金矿
            top_candidates.sort(key=lambda vein: vein[5])  # 按挖掘者数量排序
            selected_vein = top_candidates[0] if top_candidates[0][5] < 3 else random.choice(
                top_candidates)
        else:
            selected_vein = candidate_veins[0]

        game_logger.info(
            f"🎯 苦工选择金矿目标: ({selected_vein[0]}, {selected_vein[1]}) 评分: {selected_vein[2]:.1f} 距离: {selected_vein[3]:.1f} 黄金: {selected_vein[4]} 挖掘者: {selected_vein[5]}")

        return (selected_vein[0], selected_vein[1])

    def _check_path_reachability(self, start: Tuple[int, int], end: Tuple[int, int], game_map: List[List[Tile]]) -> bool:
        """检查两点之间的路径是否可达（简单直线检查）"""
        x0, y0 = start
        x1, y1 = end

        # 使用Bresenham算法检查直线路径
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x_step = 1 if x0 < x1 else -1
        y_step = 1 if y0 < y1 else -1

        error = dx - dy
        x, y = x0, y0

        while True:
            # 检查当前点是否可通行 - 修复：添加对空game_map的检查
            if not game_map or len(game_map) == 0 or len(game_map[0]) == 0:
                return False

            if (x < 0 or x >= len(game_map[0]) or y < 0 or y >= len(game_map)):
                return False

            tile = game_map[y][x]
            if tile.type == TileType.ROCK:
                return False

            if x == x1 and y == y1:
                break

            e2 = 2 * error
            if e2 > -dy:
                error -= dy
                x += x_step
            if e2 < dx:
                error += dx
                y += y_step

        return True

    def _start_mining(self, game_map: List[List[Tile]]):
        """开始挖掘 - 注册为挖掘者"""
        # 检查是否已经注册
        if hasattr(self, 'is_mining_assigned') and self.is_mining_assigned:
            return True

        # 检查是否有有效的挖掘目标
        if not self.mining_target:
            return False

        mx, my = self.mining_target

        # 检查坐标是否有效 - 修复：添加对空game_map的检查
        if not game_map or len(game_map) == 0 or len(game_map[0]) == 0:
            game_logger.info(f"❌ 游戏地图为空，无法访问金矿坐标: ({mx}, {my})")
            return False

        if not (0 <= mx < len(game_map[0]) and 0 <= my < len(game_map)):
            game_logger.info(f"❌ 金矿坐标无效: ({mx}, {my})")
            return False

        tile = game_map[my][mx]

        # 使用综合优化系统检查金矿是否可用
        mining_system = get_optimized_mining_system()
        if not mining_system.is_mine_available(mx, my):
            game_logger.info(f"❌ 金矿 ({mx}, {my}) 不可用")
            return False

        # 使用综合优化系统注册挖掘者
        if mining_system.assign_miner(mx, my, self.name):
            self.is_mining_assigned = True
            return True
        else:
            game_logger.info(f"❌ 综合优化系统注册挖掘失败: ({mx}, {my})")
            return False

    def _find_nearest_storage(self, game_map: List[List[Tile]]) -> Optional[Dict[str, Any]]:
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
        if nearest_treasury and min_distance < 300:  # 增加到300像素内优先选择金库，提高存储效率
            return nearest_treasury

        # 否则选择主基地
        dungeon_heart_positions = self._get_dungeon_heart_position(game_map)
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
        """存储金币到指定存储点（使用 ResourceManager API）"""
        if not hasattr(self, 'game_instance') or not self.game_instance:
            game_logger.info(f"❌ 无法访问游戏实例，无法存储金币")
            return

        from src.managers.resource_manager import get_resource_manager
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
                    self.carried_gold -= result['amount_deposited']
                    game_logger.info(
                        f"💰 哥布林苦工存储了 {result['amount_deposited']} 金币到金库({treasury.name}) 位置({treasury.x},{treasury.y})")
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
                self.carried_gold -= result['amount']
                game_logger.info(f"💰 哥布林苦工存储了 {result['amount']} 金币到主基地(地牢之心)")
                game_logger.info(
                    f"   📥 主基地: {result['old_amount']} → {result['new_amount']}")
            else:
                game_logger.info(
                    f"⚠️ 无法存储金币到主基地: {result.get('message', '未知错误')}")

        # 如果还有剩余金币，输出警告
        if self.carried_gold > 0:
            game_logger.info(f"⚠️ 存储已满，剩余 {self.carried_gold} 金币无法存储")

    def _deposit_gold(self):
        """在地牢之心存储金币 - 使用 ResourceManager API"""
        if self.carried_gold > 0:
            if hasattr(self, 'game_instance') and self.game_instance:
                from src.managers.resource_manager import get_resource_manager
                resource_manager = get_resource_manager(self.game_instance)

                carried_gold_int = int(self.carried_gold)

                # 使用 ResourceManager 添加金币
                result = resource_manager.add_gold(
                    carried_gold_int, self.game_instance.dungeon_heart)

                if result['success']:
                    # 成功存储，更新携带的金币
                    self.carried_gold -= result['amount']
                    game_logger.info(
                        f"💰 哥布林苦工存储了 {result['amount']} 金币到主基地(地牢之心)")
                    game_logger.info(
                        f"   📥 主基地: {result['old_amount']} → {result['new_amount']}")
                else:
                    game_logger.info(
                        f"⚠️ 无法存储金币到主基地: {result.get('message', '未知错误')}")

                # 如果还有剩余金币，输出警告
                if self.carried_gold > 0:
                    game_logger.info(
                        f"⚠️ 主基地存储已满，剩余 {self.carried_gold} 金币无法存储")
            else:
                game_logger.info(f"⚠️ 无法访问游戏实例，无法存储金币")

            # 清空携带的金币
            self.carried_gold = 0
            self.deposit_target = None
            self.state = WorkerStatus.IDLE.value

    def _perform_mining(self, game_map: List[List[Tile]], delta_time: float):
        """执行挖掘操作 - 将金币存储到苦工身上"""
        if not self.mining_target:
            game_logger.info("❌ 挖掘时没有目标，返回空闲状态")
            self.state = WorkerStatus.IDLE.value
            return

        mx, my = self.mining_target

        # 验证坐标有效性 - 修复：添加对空game_map的检查
        if not game_map or len(game_map) == 0 or len(game_map[0]) == 0:
            game_logger.info(f"❌ 游戏地图为空，无法验证挖掘目标坐标: ({mx}, {my})")
            self._cleanup_mining_assignment(game_map)
            self.mining_target = None
            self.state = WorkerStatus.IDLE.value
            return

        if not (0 <= mx < len(game_map[0]) and 0 <= my < len(game_map)):
            game_logger.info(f"❌ 挖掘目标坐标无效: ({mx}, {my})")
            self._cleanup_mining_assignment(game_map)
            self.mining_target = None
            self.state = WorkerStatus.IDLE.value
            return

        tile = game_map[my][mx]

        # 使用综合优化系统检查矿脉是否仍然有效
        mining_system = get_optimized_mining_system()
        if not mining_system.is_mine_available(mx, my):
            game_logger.info(f"💔 金矿脉 ({mx}, {my}) 已枯竭或无效")
            self._cleanup_mining_assignment(game_map)
            self.mining_target = None
            self.state = WorkerStatus.IDLE.value
            return

        self.state = WorkerStatus.MINING.value

        # 挖掘冷却时间检查 (每1秒挖掘一次)
        current_time = time.time()
        if not hasattr(self, 'last_mining_time'):
            self.last_mining_time = current_time

        if current_time - self.last_mining_time >= 1.0:  # 1秒间隔，每1秒挖掘2单位黄金
            # 获取金矿信息
            mine_info = mining_system.gold_mine_manager.get_gold_mine_info(
                mx, my)
            if not mine_info:
                game_logger.info(f"❌ 无法获取金矿信息: ({mx}, {my})")
                return

            # 计算可挖掘数量（考虑携带容量限制） - 确保整数
            available_space = int(self.max_carry_capacity - self.carried_gold)
            mining_amount = min(2, int(mine_info['gold_amount']),
                                available_space)  # 每次挖掘2金币

            if mining_amount > 0:
                # 从矿脉中挖掘
                tile.gold_amount -= mining_amount
                tile.being_mined = True

                # 存储到苦工身上 - 确保整数
                self.carried_gold = int(self.carried_gold + mining_amount)

                # 每5次挖掘输出一次日志，并添加金矿坐标
                self._mining_log_counter += 1
                if self._mining_log_counter >= 5:
                    game_logger.info(
                        f"⛏️ 哥布林苦工挖掘了 {mining_amount} 金币 (携带: {self.carried_gold}/{int(self.max_carry_capacity)}) 金矿位置: ({mx}, {my})")
                    self._mining_log_counter = 0  # 重置计数器

                self.last_mining_time = current_time

                # 检查是否需要停止挖掘
                if mine_info['gold_amount'] <= 0:
                    # 矿脉枯竭，清理所有相关状态
                    game_logger.info(f"💔 金矿脉 ({mx}, {my}) 已枯竭")
                    tile.is_gold_vein = False
                    tile.being_mined = False
                    tile.miners_count = 0  # 重置挖掘者计数

                    # 注册金矿枯竭事件
                    mining_system.register_event(
                        MiningEventType.GOLD_VEIN_EXHAUSTED, mx, my)

                    self._cleanup_mining_assignment(game_map)
                    self.mining_target = None
                    self.state = WorkerStatus.IDLE.value
                elif self.carried_gold >= self.max_carry_capacity:
                    # 携带满了，准备返回基地
                    game_logger.info(f"🎒 哥布林苦工携带满了，准备回基地存储")
                    tile.being_mined = False
                    self._cleanup_mining_assignment(game_map)
                    self.mining_target = None
                    # 状态会在下一次更新中变为 returning_to_base
            else:
                # 无法挖掘（携带满了或矿脉空了）
                if available_space <= 0:
                    game_logger.info(f"🎒 哥布林苦工携带已满，无法继续挖掘")
                    self._cleanup_mining_assignment(game_map)
                    self.mining_target = None

    def _cleanup_mining_assignment(self, game_map: List[List[Tile]]):
        """清理挖掘分配 - 从金矿的挖掘者列表中移除自己"""
        # 只有在已注册的情况下才需要清理
        if not (hasattr(self, 'is_mining_assigned') and self.is_mining_assigned):
            return

        # 检查是否有有效的挖掘目标
        if not (hasattr(self, 'mining_target') and self.mining_target):
            self.is_mining_assigned = False
            return

        mx, my = self.mining_target

        # 检查坐标是否有效 - 修复：添加对空game_map的检查
        if not game_map or len(game_map) == 0 or len(game_map[0]) == 0:
            game_logger.info(f"⚠️ 游戏地图为空，无法清理挖掘分配: ({mx}, {my})")
            self.is_mining_assigned = False
            return

        if not (0 <= mx < len(game_map[0]) and 0 <= my < len(game_map)):
            game_logger.info(f"⚠️ 清理挖掘分配时发现无效坐标: ({mx}, {my})")
            self.is_mining_assigned = False
            return

        tile = game_map[my][mx]

        # 使用综合优化系统移除挖掘者
        mining_system = get_optimized_mining_system()
        if mining_system.remove_miner(mx, my, self.name):
            game_logger.info(f"📤 挖掘者 {self.name} 从金矿 ({mx}, {my}) 移除成功")
        else:
            game_logger.info(f"⚠️ 综合优化系统移除挖掘者失败: ({mx}, {my})")

        # 重置自身状态
        self.is_mining_assigned = False

    def render_status_indicator(self, screen, camera_x: int, camera_y: int):
        """渲染苦工状态指示器"""
        if not self.status_indicator:
            return

        # 计算屏幕位置
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)

        # 使用通用的状态指示器渲染
        self.status_indicator.render(
            screen, screen_x, screen_y, self.size, self.state)

    def set_target(self, target_x: float, target_y: float):
        """设置移动目标"""
        MovementSystem.set_target(self, (target_x, target_y))

    def _handle_training_task(self, delta_time: float, game_map: List[List[Tile]]):
        """处理训练任务"""
        # 检查是否有WorkerAssigner分配的任务
        if not self.target_building:
            # 清理任务分配
            self.assigned_building = None
            self.task_type = None
            self.target_building = None
            return

        # 移动到目标建筑
        target_x = self.target_building.x  # self.target_building.x 已经是像素坐标
        target_y = self.target_building.y  # self.target_building.y 已经是像素坐标

        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 20:  # 20像素范围内算到达
            # 还没到达，继续移动
            self.state = WorkerStatus.MOVING_TO_TRAINING.value
            MovementSystem.pathfind_and_move(
                self, (target_x, target_y), delta_time, game_map, "A_STAR", 1.0)
        else:
            # 到达建筑，开始训练
            self.state = WorkerStatus.TRAINING.value
            if hasattr(self.target_building, 'start_training'):
                self.target_building.start_training(self)

            # 训练期间苦工停留在建筑附近
            # 不需要额外处理，苦工会保持当前位置

    def _manage_idle_state(self, game_instance, building_manager):
        """管理苦工的空闲状态和任务分配"""
        if not game_instance or not building_manager:
            return

        # 延迟导入WorkerAssigner避免循环依赖
        if self.worker_assigner is None:
            try:
                from src.managers.auto_assigner import WorkerAssigner, AssignmentStrategy
                self.worker_assigner = WorkerAssigner(
                    AssignmentStrategy.BALANCED)
            except ImportError as e:
                game_logger.error(f"❌ 无法导入WorkerAssigner: {e}")
                return

        # 获取所有苦工列表（这里只有当前苦工，但WorkerAssigner需要列表）
        workers = [self]

        # 获取所有建筑列表
        buildings = building_manager.buildings if hasattr(
            building_manager, 'buildings') else []

        # 更新WorkerAssigner
        result = self.worker_assigner.update(
            workers, buildings, 0.016)  # 假设60FPS

        # 检查是否有新任务分配
        if result.get('tasks_assigned', 0) > 0:
            game_logger.info(f"🎯 苦工 {self.name} 获得新任务分配")

        # 检查是否有任务重新分配
        if result.get('workers_reassigned', 0) > 0:
            game_logger.info(f"🔄 苦工 {self.name} 任务重新分配")

        # 检查任务完成情况
        if result.get('tasks_completed', 0) > 0:
            game_logger.info(f"✅ 苦工 {self.name} 完成任务")
            # 清理已完成的任务
            self._cleanup_completed_task()

        # 如果苦工处于空闲状态且没有任务，尝试寻找挖掘目标
        if (self.state == WorkerStatus.IDLE.value and
                not hasattr(self, 'target_building') or not self.target_building):
            # 苦工会自动寻找金矿进行挖掘
            pass

    def _update_state_switcher(self, current_time: float, game_map: List[List[Tile]]):
        """
        重写状态切换器 - 苦工特有的状态管理逻辑（优化版本）

        Args:
            current_time: 当前时间
            game_map: 游戏地图
        """
        # 检查状态检查间隔，避免过于频繁的检查
        if current_time - self._last_state_check_time < self._state_check_interval:
            return

        self._last_state_check_time = current_time

        # 苦工有自己的状态管理逻辑，重写父类的方法以保持兼容性
        # 检查状态切换冷却时间
        if current_time - self.last_state_change_time < self.state_change_cooldown:
            return

        # 苦工特有的等待状态列表（排除工作中的状态和wandering，避免循环）
        waiting_states = ['idle']

        # 检查当前状态是否为等待状态
        if self.state in waiting_states:
            # 如果还没有记录等待开始时间，记录它
            if self.waiting_start_time == 0:
                self.waiting_start_time = current_time
                game_logger.debug(f"🕐 苦工 {self.name} 开始等待状态: {self.state}")

            # 检查是否超过等待超时时间
            waiting_duration = current_time - self.waiting_start_time
            if waiting_duration >= self.waiting_timeout:
                # 检查连续游荡次数，避免过度游荡
                if self._consecutive_wandering_count >= self._max_consecutive_wandering:
                    game_logger.debug(f"⚠️ 苦工 {self.name} 连续游荡次数过多，跳过此次切换")
                    # 延长等待时间，避免频繁切换
                    self.waiting_start_time = current_time - self.waiting_timeout + 1.0
                    self._consecutive_wandering_count = 0
                    return

                # 苦工在等待超时后应该继续寻找工作，而不是游荡
                old_state = self.state
                self.state = WorkerStatus.WANDERING.value
                self.last_state_change_time = current_time

                # 缓存状态切换信息
                state_key = f"{old_state}_to_wandering"
                if state_key not in self._state_cache:
                    self._state_cache[state_key] = []

                self._state_cache[state_key].append({
                    'timestamp': current_time,
                    'duration': waiting_duration
                })

                # 保持缓存大小合理（只保留最近10次记录）
                if len(self._state_cache[state_key]) > 10:
                    self._state_cache[state_key] = self._state_cache[state_key][-10:]

                # 增加连续游荡计数
                if old_state == 'wandering':
                    self._consecutive_wandering_count += 1
                else:
                    self._consecutive_wandering_count = 1

                game_logger.info(
                    f"🎲 苦工 {self.name} 等待超时({waiting_duration:.1f}s)，从 {old_state} 切换到 {self.state} (连续游荡: {self._consecutive_wandering_count})")

                # 苦工在游荡时会自动寻找金矿，不需要额外的游荡行为

                # 重置等待开始时间，给游荡状态足够的时间
                self.waiting_start_time = 0
        else:
            # 不在等待状态，重置等待开始时间和连续游荡计数
            if self.waiting_start_time != 0:
                self.waiting_start_time = 0
            if self._consecutive_wandering_count > 0:
                self._consecutive_wandering_count = 0

    def _cleanup_completed_task(self):
        """清理已完成的任务"""
        if hasattr(self, 'target_building') and self.target_building:
            # 检查任务是否完成
            if self.task_type == 'training':
                # 训练任务完成，清理状态
                if self.state == WorkerStatus.IDLE.value:
                    self.target_building = None
                    self.assigned_building = None
                    self.task_type = None
                    game_logger.info(f"✅ 苦工 {self.name} 完成训练任务")
