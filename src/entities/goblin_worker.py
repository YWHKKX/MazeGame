#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
哥布林苦工行动类
从 Creature 类中提取的苦工专用逻辑
"""

import math
import time
from typing import List, Dict, Optional, Tuple, Any

from src.core.constants import GameConstants
from src.core.enums import TileType
from src.core.game_state import Tile
from src.entities.creature import Creature
from src.managers.movement_system import MovementSystem


class GoblinWorker(Creature):
    """哥布林苦工 - 专门负责挖掘和资源收集"""

    def __init__(self, x: int, y: int):
        super().__init__(x, y, 'goblin_worker')

        # 设置友好的名称
        self.name = '苦工'

        # 设置为非战斗单位
        self.is_combat_unit = False

        # 苦工特有属性
        self.carried_gold = 0  # 携带的金币数量
        self.max_carry_capacity = 10  # 最大携带容量
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

        # 目标稳定性管理
        self._target_switch_cooldown = 0  # 目标切换冷却时间
        self._last_target_switch_time = 0  # 上次切换目标的时间

        # 状态指示器 - 使用通用系统
        try:
            from src.ui.status_indicator import StatusIndicator
            self.status_indicator = StatusIndicator()
        except ImportError:
            self.status_indicator = None

    def update(self, delta_time: float, game_map: List[List[Tile]], creatures: List['Creature'], heroes: List = None, effect_manager=None, building_manager=None):
        """更新哥布林苦工行为"""
        self._update_goblin_behavior(
            delta_time, game_map, heroes or [], effect_manager)

    def _update_goblin_behavior(self, delta_time: float, game_map: List[List[Tile]], heroes: List, effect_manager=None):
        """哥布林苦工行为更新 - 按照COMBAT_SYSTEM.md规范实现"""
        # 优先级1: 逃离敌人 (60像素检测范围)
        nearest_hero = self._find_nearest_hero(heroes, 60)
        if nearest_hero:
            self._cleanup_mining_assignment(game_map)
            self.mining_target = None
            self.state = 'fleeing'
            # 使用逃离移动，速度提升20%
            MovementSystem.flee_movement(
                self, (nearest_hero.x, nearest_hero.y), delta_time, game_map, 1.2)
            return

        # 优先级2: 存储金币
        if int(self.carried_gold) >= int(self.max_carry_capacity):
            self.state = 'returning_to_base'
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
            return

        # 优先级3: 挖掘金矿
        if not self.mining_target:
            # 检查目标切换冷却时间
            import time
            current_time = time.time()
            if current_time - self._last_target_switch_time > 3.0:  # 增加冷却时间到3秒
                self.mining_target = self._find_best_reachable_gold_vein(
                    game_map)
                if self.mining_target:
                    print(f"🎯 苦工选择金矿目标: {self.mining_target}")
                    self._last_target_switch_time = current_time

        if self.mining_target:
            mx, my = self.mining_target
            target_pos = (mx * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2,
                          my * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2)

            # 检查矿脉是否仍然有效（包括已挖掘的金矿和接壤的未挖掘金矿）
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
                print(f"❌ 矿脉 ({mx}, {my}) 无效，寻找新目标")
                self._cleanup_mining_assignment(game_map)
                self.mining_target = None
            elif not is_at_target:
                # 目标仍然有效但未到达，使用新的分离式寻路+移动系统
                self.state = 'moving_to_mine'

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
                    print(
                        f"🚶 苦工继续移动到金矿 ({mx}, {my})，当前距离: {distance_to_target:.1f}px，当前位置: ({self.x:.1f}, {self.y:.1f})px")
            elif is_valid_vein and is_at_target:
                # 目标仍然有效且已到达，继续当前目标

                # 增大采矿范围以避免环境碰撞体积冲突
                mining_range = 20

                if distance_to_target > mining_range:
                    # 还没到达金矿，继续移动
                    self.state = 'moving_to_mine'

                    # 记录移动前的位置
                    old_x, old_y = self.x, self.y

                    # 执行移动
                    # 添加移动系统状态调试
                    unit_state = MovementSystem.get_unit_state(self)
                    print(
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
                    print(
                        f"   移动后状态: {unit_state_after.movement_state.value}, 目标队列: {len(unit_state_after.target_queue)}")

                    # 记录移动后的位置
                    new_x, new_y = self.x, self.y
                    moved_distance = math.sqrt(
                        (new_x - old_x) ** 2 + (new_y - old_y) ** 2)

                    # 添加调试信息
                    self._debug_counter += 1
                    if self._debug_counter % 60 == 0:  # 每秒输出一次
                        print(
                            f"🚶 苦工移动到金矿 ({mx}, {my})，当前距离: {distance_to_target:.1f}px，目标范围: {mining_range}px")
                        print(
                            f"   位置变化: ({old_x:.1f}, {old_y:.1f})px -> ({new_x:.1f}, {new_y:.1f})px")
                        print(
                            f"   移动距离: {moved_distance:.1f}px，移动结果: {movement_result}")
                        print(
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
                        print(f"⛏️ 苦工开始挖掘金矿脉 ({mx}, {my})")
                        dig_result = tile.dig(
                            cost=0, game_state=None, x=mx, y=my)
                        if dig_result['success']:
                            print(f"💰 {dig_result['message']}")
                            # 挖掘成功后，金矿变为可挖掘状态
                            tile.type = TileType.GOLD_VEIN
                            # 继续处理挖掘逻辑
                        else:
                            print(f"❌ 挖掘金矿脉失败: {dig_result['message']}")
                            self.mining_target = None
                            return

                    if hasattr(self, 'is_mining_assigned') and self.is_mining_assigned:
                        # 已经注册为挖掘者，直接挖掘
                        self.state = 'mining'
                        self._perform_mining(game_map, delta_time)
                    else:
                        # 尚未注册，尝试开始挖掘
                        print(f"🔧 苦工尝试注册金矿 ({mx}, {my}) 进行挖掘")
                        if self._start_mining(game_map):
                            # 成功注册，开始挖掘
                            print(f"✅ 苦工成功注册金矿 ({mx}, {my})，开始挖掘")
                            self.state = 'mining'
                            self._perform_mining(game_map, delta_time)
                        else:
                            # 注册失败（金矿满员），寻找新目标
                            print(f"⚠️ 金矿 ({mx}, {my}) 注册失败，寻找新目标")
                            old_target = self.mining_target

                            # 检查目标切换冷却时间
                            import time
                            current_time = time.time()
                            if current_time - self._last_target_switch_time > 2.0:  # 增加冷却时间到2秒
                                self.mining_target = self._find_best_reachable_gold_vein(
                                    game_map)
                                if self.mining_target and self.mining_target != old_target:
                                    print(
                                        f"🎯 苦工切换金矿目标: {old_target} -> {self.mining_target}")
                                    self._last_target_switch_time = current_time
                                elif not self.mining_target:
                                    self.state = 'wandering'
                                    print("🎲 没有其他可用金矿，开始游荡")
                            else:
                                # 冷却时间内，暂时游荡
                                self.state = 'wandering'
                                print("⏰ 目标切换冷却中，暂时游荡")
        else:
            # 优先级4: 游荡 - 在游荡时也要尝试寻找金矿
            self.state = 'wandering'

            # 在游荡时也要检查是否有可用的金矿
            import time
            current_time = time.time()
            if current_time - self._last_target_switch_time > 0.5:  # 增加冷却时间到0.5秒
                new_target = self._find_best_reachable_gold_vein(game_map)
                if new_target:
                    self.mining_target = new_target
                    print(f"🎯 苦工在游荡中发现金矿目标: {new_target}")
                    self._last_target_switch_time = current_time
                    # 找到目标后立即切换到移动状态
                    return

            MovementSystem.wandering_movement(self, delta_time, game_map, 0.3)

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
        """寻找最佳可达金矿 - 使用可达性系统优化"""
        # 导入可达性系统
        from ..systems.reachability_system import get_reachability_system

        # 获取可达性系统
        reachability_system = get_reachability_system()

        # 确保可达性系统已初始化
        if hasattr(self, 'game_instance') and self.game_instance:
            dungeon_heart_pos = self.game_instance.dungeon_heart_pos
            if dungeon_heart_pos:
                reachability_system.set_base_position(
                    dungeon_heart_pos[0], dungeon_heart_pos[1])

        # 更新可达性（如果需要）
        reachability_system.update_reachability(game_map)

        # 获取当前苦工位置
        current_tile_x = int(self.x // GameConstants.TILE_SIZE)
        current_tile_y = int(self.y // GameConstants.TILE_SIZE)

        # 获取所有可达的金矿脉
        reachable_veins = reachability_system.get_reachable_gold_veins(
            game_map)

        if not reachable_veins:
            return None

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

            tile = game_map[y][x]

            # 检查金矿是否可用：考虑已挖掘的金矿脉和接壤的未挖掘金矿脉
            is_available = False
            miners_count = 0

            if (hasattr(tile, 'is_gold_vein') and tile.is_gold_vein and tile.gold_amount > 0 and
                    hasattr(tile, 'type') and tile.type == TileType.GOLD_VEIN):
                # 已挖掘的金矿脉
                is_available = tile.miners_count < 3
                miners_count = tile.miners_count
            elif (hasattr(tile, 'is_gold_vein') and tile.is_gold_vein and
                  hasattr(tile, 'type') and tile.type == TileType.ROCK):  # 未挖掘的金矿脉
                # 未挖掘的金矿脉，需要先挖掘，可以挖掘
                is_available = True
                miners_count = 0

            if is_available:
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
                miner_penalty = miners_count * 10  # 挖掘者惩罚
                distance_penalty = distance_to_worker * 2  # 距离惩罚

                # 综合评分 = 黄金储量 - 挖掘者惩罚 - 距离惩罚
                total_score = gold_score - miner_penalty - distance_penalty

                candidate_veins.append(
                    (x, y, total_score, distance_to_worker, gold_amount, miners_count))

        if not candidate_veins:
            print("❌ 在搜索半径内没有可用的金矿")
            return None

        # 按综合评分排序，返回最佳金矿
        candidate_veins.sort(key=lambda vein: vein[2], reverse=True)
        best_vein = candidate_veins[0]

        print(
            f"🎯 找到最佳金矿: ({best_vein[0]}, {best_vein[1]}) 评分: {best_vein[2]:.1f} 距离: {best_vein[3]:.1f} 黄金: {best_vein[4]} 挖掘者: {best_vein[5]}")

        return (best_vein[0], best_vein[1])

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
            # 检查当前点是否可通行
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

        # 检查坐标是否有效
        if not (0 <= mx < len(game_map[0]) and 0 <= my < len(game_map)):
            print(f"❌ 金矿坐标无效: ({mx}, {my})")
            return False

        tile = game_map[my][mx]

        # 检查是否仍是有效的金矿
        if not (tile.is_gold_vein and tile.gold_amount > 0):
            print(f"❌ 金矿 ({mx}, {my}) 已无效或枯竭")
            return False

        # 检查金矿是否还有空位
        if tile.miners_count >= 3:
            print(f"⚠️ 金矿 ({mx}, {my}) 已满员 ({tile.miners_count}/3)，新苦工无法加入")
            return False

        # 注册为挖掘者
        tile.miners_count += 1
        self.is_mining_assigned = True
        print(f"📝 哥布林苦工开始挖掘金矿 ({mx}, {my})，当前挖掘者: {tile.miners_count}/3")
        return True

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
        """存储金币到指定存储点"""
        if storage_target['type'] == 'treasury':
            # 存储到金库
            treasury = storage_target['building']
            if treasury and hasattr(treasury, 'deposit_gold'):
                deposited = treasury.deposit_gold(int(self.carried_gold))
                if deposited > 0:
                    self.carried_gold -= deposited
                    print(
                        f"💰 哥布林苦工存储了 {deposited} 金币到金库({treasury.name}) 位置({treasury.x},{treasury.y})")
                else:
                    print(
                        f"⚠️ 金库({treasury.name}) 在位置({treasury.x},{treasury.y}) 已满，无法存储更多金币")
            else:
                print(f"❌ 金库不可用，无法存储金币")
        else:
            # 存储到主基地
            self._deposit_gold()

    def _deposit_gold(self):
        """在地牢之心存储金币"""
        if self.carried_gold > 0:
            # 将携带的金币转移到游戏资源 - 确保整数
            if hasattr(self, 'game_instance') and self.game_instance:
                carried_gold_int = int(self.carried_gold)
                # 检查主基地存储容量
                game_state = self.game_instance.game_state
                available_space = game_state.max_gold_capacity - game_state.gold
                deposit_amount = min(carried_gold_int, available_space)

                if deposit_amount > 0:
                    old_gold = int(game_state.gold)
                    game_state.gold += deposit_amount
                    self.carried_gold -= deposit_amount
                    # 确保金币始终为整数
                    game_state.gold = int(game_state.gold)
                    print(f"💰 哥布林苦工存储了 {deposit_amount} 金币到主基地(地牢之心)")
                    print(
                        f"   📥 主基地: {old_gold} → {game_state.gold} (当前存储: {game_state.gold}/{game_state.max_gold_capacity})")

                    if self.carried_gold > 0:
                        print(f"⚠️ 主基地存储已满，剩余 {self.carried_gold} 金币无法存储")
                else:
                    print(f"⚠️ 主基地存储已满，无法存储金币")

            # 清空携带的金币
            self.carried_gold = 0
            self.deposit_target = None
            self.state = 'idle'

    def _perform_mining(self, game_map: List[List[Tile]], delta_time: float):
        """执行挖掘操作 - 将金币存储到苦工身上"""
        if not self.mining_target:
            print("❌ 挖掘时没有目标，返回空闲状态")
            self.state = 'idle'
            return

        mx, my = self.mining_target

        # 验证坐标有效性
        if not (0 <= mx < len(game_map[0]) and 0 <= my < len(game_map)):
            print(f"❌ 挖掘目标坐标无效: ({mx}, {my})")
            self._cleanup_mining_assignment(game_map)
            self.mining_target = None
            self.state = 'idle'
            return

        tile = game_map[my][mx]

        # 检查矿脉是否仍然有效
        if not tile.is_gold_vein or tile.gold_amount <= 0:
            print(f"💔 金矿脉 ({mx}, {my}) 已枯竭或无效")
            self._cleanup_mining_assignment(game_map)
            self.mining_target = None
            self.state = 'idle'
            return

        self.state = 'mining'

        # 挖掘冷却时间检查 (每1秒挖掘一次)
        current_time = time.time()
        if not hasattr(self, 'last_mining_time'):
            self.last_mining_time = current_time

        if current_time - self.last_mining_time >= 1.0:  # 1秒间隔，每1秒挖掘2单位黄金
            # 计算可挖掘数量（考虑携带容量限制） - 确保整数
            available_space = int(self.max_carry_capacity - self.carried_gold)
            mining_amount = min(2, int(tile.gold_amount),
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
                    print(
                        f"⛏️ 哥布林苦工挖掘了 {mining_amount} 金币 (携带: {self.carried_gold}/{int(self.max_carry_capacity)}) 金矿位置: ({mx}, {my})")
                    self._mining_log_counter = 0  # 重置计数器

                self.last_mining_time = current_time

                # 检查是否需要停止挖掘
                if tile.gold_amount <= 0:
                    # 矿脉枯竭，清理所有相关状态
                    print(f"💔 金矿脉 ({mx}, {my}) 已枯竭")
                    tile.is_gold_vein = False
                    tile.being_mined = False
                    tile.miners_count = 0  # 重置挖掘者计数
                    self._cleanup_mining_assignment(game_map)
                    self.mining_target = None
                    self.state = 'idle'
                elif self.carried_gold >= self.max_carry_capacity:
                    # 携带满了，准备返回基地
                    print(f"🎒 哥布林苦工携带满了，准备回基地存储")
                    tile.being_mined = False
                    self._cleanup_mining_assignment(game_map)
                    self.mining_target = None
                    # 状态会在下一次更新中变为 returning_to_base
            else:
                # 无法挖掘（携带满了或矿脉空了）
                if available_space <= 0:
                    print(f"🎒 哥布林苦工携带已满，无法继续挖掘")
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

        # 检查坐标是否有效
        if not (0 <= mx < len(game_map[0]) and 0 <= my < len(game_map)):
            print(f"⚠️ 清理挖掘分配时发现无效坐标: ({mx}, {my})")
            self.is_mining_assigned = False
            return

        tile = game_map[my][mx]

        # 减少挖掘者计数
        if tile.miners_count > 0:
            tile.miners_count -= 1
            print(f"📤 哥布林苦工离开金矿 ({mx}, {my})，剩余挖掘者: {tile.miners_count}/3")
        else:
            print(f"⚠️ 金矿 ({mx}, {my}) 挖掘者计数异常: {tile.miners_count}")

        # 如果没有挖掘者了，清理矿脉状态
        if tile.miners_count <= 0:
            tile.being_mined = False

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
