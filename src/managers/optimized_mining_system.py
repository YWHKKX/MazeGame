#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化挖掘系统 - 综合强制更新和分离缓存的优化方案
"""

import time
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum

from src.systems.reachability_system import get_reachability_system
from src.managers.gold_mine_manager import get_gold_mine_manager
from src.utils.logger import game_logger


class MiningEventType(Enum):
    """挖掘事件类型"""
    GOLD_VEIN_DISCOVERED = "gold_vein_discovered"
    GOLD_VEIN_EXHAUSTED = "gold_vein_exhausted"
    GOLD_VEIN_FULL = "gold_vein_full"
    GOLD_VEIN_AVAILABLE = "gold_vein_available"
    MAP_CHANGED = "map_changed"


class OptimizedMiningSystem:
    """优化挖掘系统 - 综合优化方案"""

    def __init__(self):
        self.reachability_system = get_reachability_system()
        self.gold_mine_manager = get_gold_mine_manager()

        # 事件管理
        self.pending_events: Set[Tuple[MiningEventType, int, int]] = set()
        self.last_event_processing = 0.0
        self.event_processing_interval = 0.1  # 事件处理间隔

        # 性能统计
        self.stats = {
            'force_updates_triggered': 0,
            'gold_mine_updates': 0,
            'events_processed': 0,
            'last_optimization_time': 0.0
        }

        # 智能更新策略
        self.adaptive_update_enabled = True
        self.update_frequency_multiplier = 1.0

    def register_event(self, event_type: MiningEventType, x: int, y: int):
        """注册挖掘事件"""
        self.pending_events.add((event_type, x, y))
        game_logger.info(f"🔔 注册挖掘事件: {event_type.value} at ({x}, {y})")

    def process_events(self, game_map: List[List]) -> bool:
        """处理待处理的事件"""
        current_time = time.time()

        # 检查是否需要处理事件
        if current_time - self.last_event_processing < self.event_processing_interval:
            return False

        if not self.pending_events:
            return False

        events_processed = 0
        force_update_needed = False

        # 处理事件
        for event_type, x, y in self.pending_events:
            if self._process_single_event(event_type, x, y, game_map):
                force_update_needed = True
            events_processed += 1

        # 清除已处理的事件
        self.pending_events.clear()
        self.last_event_processing = current_time
        self.stats['events_processed'] += events_processed

        # 如果需要强制更新，触发更新
        if force_update_needed:
            self._trigger_optimized_update(game_map)

        return force_update_needed

    def _process_single_event(self, event_type: MiningEventType, x: int, y: int, game_map: List[List]) -> bool:
        """处理单个事件"""
        force_update_needed = False

        if event_type == MiningEventType.GOLD_VEIN_DISCOVERED:
            # 新金矿发现 - 需要强制更新可达性
            self.reachability_system.register_force_update_event(
                "gold_vein_discovered", x, y)
            force_update_needed = True
            game_logger.info(f"🆕 新金矿发现事件处理: ({x}, {y})")

        elif event_type == MiningEventType.GOLD_VEIN_EXHAUSTED:
            # 金矿枯竭 - 需要强制更新可达性
            self.reachability_system.register_force_update_event(
                "gold_vein_exhausted", x, y)
            force_update_needed = True
            game_logger.info(f"💔 金矿枯竭事件处理: ({x}, {y})")

        elif event_type == MiningEventType.GOLD_VEIN_FULL:
            # 金矿满员 - 只需要更新金矿管理器
            self.gold_mine_manager.force_update(game_map)
            game_logger.info(f"👥 金矿满员事件处理: ({x}, {y})")

        elif event_type == MiningEventType.GOLD_VEIN_AVAILABLE:
            # 金矿可用 - 只需要更新金矿管理器
            self.gold_mine_manager.force_update(game_map)
            game_logger.info(f"✅ 金矿可用事件处理: ({x}, {y})")

        elif event_type == MiningEventType.MAP_CHANGED:
            # 地图变化 - 需要强制更新两个系统
            self.reachability_system.register_force_update_event(
                "map_changed", x, y)
            self.gold_mine_manager.force_update(game_map)
            force_update_needed = True
            game_logger.info(f"🗺️ 地图变化事件处理: ({x}, {y})")

        return force_update_needed

    def _trigger_optimized_update(self, game_map: List[List]):
        """触发优化更新"""
        start_time = time.time()

        # 更新金矿管理器（快速）
        gold_mine_updated = self.gold_mine_manager.update_gold_mines(game_map)

        # 更新可达性系统（可能触发强制更新）
        reachability_updated = self.reachability_system.update_reachability(
            game_map)

        # 更新统计信息
        if reachability_updated:
            self.stats['force_updates_triggered'] += 1
        if gold_mine_updated:
            self.stats['gold_mine_updates'] += 1

        self.stats['last_optimization_time'] = time.time() - start_time

        update_type = "强制更新" if reachability_updated else "常规更新"
        game_logger.info(
            f"🔄 优化挖掘系统{update_type}完成，耗时: {self.stats['last_optimization_time']:.3f}秒")

    def get_reachable_gold_mines(self, game_map: List[List]) -> List[Tuple[int, int, int]]:
        """获取可达的金矿 - 综合两个系统"""
        # 处理待处理的事件
        self.process_events(game_map)

        # 直接使用可达性系统获取可达的金矿脉（包括接壤的未挖掘金矿脉）
        reachable_mines = self.reachability_system.get_reachable_gold_veins(
            game_map)

        return reachable_mines

    def is_mine_available(self, x: int, y: int) -> bool:
        """检查金矿是否可用"""
        return self.gold_mine_manager.is_mine_available(x, y)

    def assign_miner(self, x: int, y: int, miner_id: str) -> bool:
        """分配挖掘者"""
        return self.gold_mine_manager.assign_miner(x, y, miner_id)

    def remove_miner(self, x: int, y: int, miner_id: str) -> bool:
        """移除挖掘者"""
        return self.gold_mine_manager.remove_miner(x, y, miner_id)

    def get_system_stats(self) -> Dict:
        """获取系统统计信息"""
        return {
            'optimization_stats': self.stats,
            'reachability_stats': self.reachability_system.get_stats(),
            'gold_mine_stats': self.gold_mine_manager.get_stats(),
            'pending_events': len(self.pending_events)
        }

    def enable_adaptive_updates(self, enabled: bool = True):
        """启用/禁用自适应更新"""
        self.adaptive_update_enabled = enabled
        game_logger.info(f"🔧 自适应更新: {'启用' if enabled else '禁用'}")

    def set_update_frequency(self, multiplier: float):
        """设置更新频率倍数"""
        self.update_frequency_multiplier = max(0.1, min(5.0, multiplier))
        self.event_processing_interval = 0.1 / self.update_frequency_multiplier
        game_logger.info(f"⚡ 更新频率倍数设置为: {self.update_frequency_multiplier}")


# 全局优化挖掘系统实例
_optimized_mining_system = None


def get_optimized_mining_system() -> OptimizedMiningSystem:
    """获取全局优化挖掘系统实例"""
    global _optimized_mining_system
    if _optimized_mining_system is None:
        _optimized_mining_system = OptimizedMiningSystem()
    return _optimized_mining_system
