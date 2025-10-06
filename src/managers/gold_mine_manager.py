#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金矿管理器 - 独立于可达性系统的金矿信息管理
"""

import time
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict

from src.core.enums import TileType
from src.core.constants import GameConstants
from src.utils.logger import game_logger


class GoldMineManager:
    """金矿管理器 - 独立于可达性系统的金矿信息管理"""

    def __init__(self):
        self.gold_mines: Dict[Tuple[int, int],
                              Dict] = {}  # {(x, y): mine_info}
        self.available_mines: Set[Tuple[int, int]] = set()  # 可用的金矿
        self.exhausted_mines: Set[Tuple[int, int]] = set()  # 已枯竭的金矿
        self.last_update = 0.0
        self.update_interval = 0.1  # 更短的更新间隔（100ms）
        self.mining_assignments: Dict[Tuple[int, int],
                                      Set[str]] = defaultdict(set)  # 挖掘者分配
        self.gold_mine_objects: Dict[Tuple[int,
                                           int], 'GoldMine'] = {}  # 金矿对象引用

        # 统计信息
        self.total_gold_amount = 0
        self.total_available_gold = 0
        self.mine_count = 0
        self.available_mine_count = 0

    def register_gold_mine_object(self, x: int, y: int, gold_mine: 'GoldMine'):
        """注册金矿对象引用"""
        self.gold_mine_objects[(x, y)] = gold_mine

    def update_gold_mines(self, game_map: List[List]) -> bool:
        """更新金矿信息"""
        current_time = time.time()

        # 检查是否需要更新
        if current_time - self.last_update < self.update_interval:
            return False

        # 清空旧数据
        old_gold_mines = self.gold_mines.copy()
        self.gold_mines.clear()
        self.available_mines.clear()
        self.exhausted_mines.clear()
        self.total_gold_amount = 0
        self.total_available_gold = 0
        self.mine_count = 0
        self.available_mine_count = 0

        # 扫描地图中的金矿
        for y in range(len(game_map)):
            for x in range(len(game_map[0])):
                tile = game_map[y][x]

                # 检查是否为金矿脉
                is_gold_vein = False
                gold_amount = 0
                miners_count = 0

                if hasattr(tile, 'is_gold_vein'):
                    # Tile类
                    is_gold_vein = tile.is_gold_vein
                    gold_amount = getattr(tile, 'gold_amount', 0)
                    miners_count = getattr(tile, 'miners_count', 0)
                elif hasattr(tile, 'resource'):
                    # GameTile类
                    is_gold_vein = tile.resource.is_gold_vein
                    gold_amount = getattr(tile.resource, 'gold_amount', 0)
                    miners_count = getattr(tile.resource, 'miners_count', 0)

                if is_gold_vein:
                    mine_info = {
                        'gold_amount': gold_amount,
                        'miners_count': miners_count,
                        'is_available': gold_amount > 0 and miners_count < 3,
                        'tile_type': getattr(tile, 'type', None),
                        'last_updated': current_time
                    }

                    self.gold_mines[(x, y)] = mine_info
                    self.total_gold_amount += gold_amount
                    self.mine_count += 1

                    if mine_info['is_available']:
                        self.available_mines.add((x, y))
                        self.total_available_gold += gold_amount
                        self.available_mine_count += 1
                    else:
                        self.exhausted_mines.add((x, y))

        # 检查变化
        changes_detected = self._detect_changes(old_gold_mines)

        self.last_update = current_time

        if changes_detected:
            game_logger.info(
                f"💰 金矿信息更新: {self.mine_count} 个金矿，{self.available_mine_count} 个可用，总储量: {self.total_gold_amount}")

        return changes_detected

    def _detect_changes(self, old_gold_mines: Dict[Tuple[int, int], Dict]) -> bool:
        """检测金矿变化"""
        changes = False

        # 检查新增的金矿
        for pos, mine_info in self.gold_mines.items():
            if pos not in old_gold_mines:
                game_logger.info(
                    f"🆕 发现新金矿: {pos} 储量: {mine_info['gold_amount']}")
                changes = True

        # 检查枯竭的金矿
        for pos, old_info in old_gold_mines.items():
            if pos not in self.gold_mines:
                game_logger.info(f"💔 金矿消失: {pos}")
                changes = True
            elif (old_info['gold_amount'] > 0 and
                  self.gold_mines[pos]['gold_amount'] == 0):
                game_logger.info(f"💔 金矿枯竭: {pos}")
                changes = True

        return changes

    def get_available_gold_mines(self) -> List[Tuple[int, int, int]]:
        """获取可用的金矿列表"""
        return [(x, y, self.gold_mines[(x, y)]['gold_amount'])
                for x, y in self.available_mines]

    def get_gold_mine_info(self, x: int, y: int) -> Optional[Dict]:
        """获取指定金矿的信息"""
        return self.gold_mines.get((x, y))

    def is_mine_available(self, x: int, y: int) -> bool:
        """检查金矿是否可用"""
        return (x, y) in self.available_mines

    def assign_miner(self, x: int, y: int, miner_id: str) -> bool:
        """分配挖掘者到金矿"""
        if not self.is_mine_available(x, y):
            return False

        mine_info = self.gold_mines.get((x, y))
        if not mine_info or mine_info['miners_count'] >= 3:
            return False

        # 更新挖掘者计数
        mine_info['miners_count'] += 1
        self.mining_assignments[(x, y)].add(miner_id)

        # 检查是否仍然可用
        if mine_info['miners_count'] >= 3:
            self.available_mines.discard((x, y))
            self.available_mine_count -= 1

        # 更新实际的金矿对象状态
        if (x, y) in self.gold_mine_objects:
            gold_mine = self.gold_mine_objects[(x, y)]
            result = gold_mine.assign_miner(miner_id, f"挖掘者{miner_id}")
            if not result['success']:
                game_logger.warning(f"⚠️ 金矿对象分配挖掘者失败: {result['message']}")
            else:
                game_logger.info(
                    f"✅ 金矿对象状态更新成功: 位置=({x}, {y}), 状态={gold_mine.status.name}, 挖掘者={len(gold_mine.mining_assignments)}")

        game_logger.info(
            f"👷 挖掘者 {miner_id} 分配到金矿 ({x}, {y})，当前挖掘者: {mine_info['miners_count']}/3")
        return True

    def remove_miner(self, x: int, y: int, miner_id: str) -> bool:
        """从金矿移除挖掘者"""
        mine_info = self.gold_mines.get((x, y))
        if not mine_info:
            return False

        if miner_id not in self.mining_assignments[(x, y)]:
            return False

        # 更新挖掘者计数
        mine_info['miners_count'] -= 1
        self.mining_assignments[(x, y)].discard(miner_id)

        # 检查是否重新可用
        if mine_info['miners_count'] < 3 and mine_info['gold_amount'] > 0:
            self.available_mines.add((x, y))
            self.available_mine_count += 1

        # 更新实际的金矿对象状态
        if (x, y) in self.gold_mine_objects:
            gold_mine = self.gold_mine_objects[(x, y)]
            result = gold_mine.remove_miner(miner_id)
            if not result['success']:
                game_logger.warning(f"⚠️ 金矿对象移除挖掘者失败: {result['message']}")

        game_logger.info(
            f"👷 挖掘者 {miner_id} 离开金矿 ({x}, {y})，当前挖掘者: {mine_info['miners_count']}/3")
        return True

    def get_stats(self) -> Dict:
        """获取金矿统计信息"""
        return {
            'total_mines': self.mine_count,
            'available_mines': self.available_mine_count,
            'exhausted_mines': len(self.exhausted_mines),
            'total_gold_amount': self.total_gold_amount,
            'total_available_gold': self.total_available_gold,
            'last_update': self.last_update,
            'update_interval': self.update_interval
        }

    def force_update(self, game_map: List[List]) -> bool:
        """强制更新金矿信息"""
        self.last_update = 0  # 重置更新时间，强制更新
        return self.update_gold_mines(game_map)


# 全局金矿管理器实例
_gold_mine_manager = None


def get_gold_mine_manager() -> GoldMineManager:
    """获取全局金矿管理器实例"""
    global _gold_mine_manager
    if _gold_mine_manager is None:
        _gold_mine_manager = GoldMineManager()
    return _gold_mine_manager
