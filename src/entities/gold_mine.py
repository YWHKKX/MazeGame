#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金矿类 - 专门管理金矿相关功能
继承自GameTile，与Building类平级
"""

import time
import math
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .tile import GameTile
from ..core.enums import TileType
from ..core.constants import GameConstants


class GoldMineStatus(Enum):
    """金矿状态枚举"""
    UNDISCOVERED = "undiscovered"      # 未发现
    DISCOVERED = "discovered"          # 已发现
    BEING_MINED = "being_mined"        # 正在挖掘
    DEPLETED = "depleted"              # 已耗尽
    ABANDONED = "abandoned"            # 已废弃


@dataclass
class MiningAssignment:
    """挖掘分配信息"""
    miner_id: str                      # 挖掘者ID
    miner_name: str                    # 挖掘者名称
    assigned_time: float               # 分配时间
    mining_efficiency: float = 1.0     # 挖掘效率
    is_active: bool = True             # 是否活跃


class GoldMine(GameTile):
    """金矿类 - 继承自GameTile，专门管理金矿功能"""

    def __init__(self, x: int, y: int, gold_amount: int = 500, tile_size: int = 20):
        """
        初始化金矿

        Args:
            x, y: 瓦块坐标
            gold_amount: 金矿储量
            tile_size: 瓦块大小
        """
        # 调用父类构造函数
        super().__init__(x, y, TileType.ROCK, tile_size)

        # 金矿特有属性
        self.gold_amount = gold_amount
        self.max_gold_amount = gold_amount
        self.is_gold_vein = True
        self.status = GoldMineStatus.UNDISCOVERED

        # 挖掘管理
        self.mining_assignments: List[MiningAssignment] = []
        self.max_miners = 3  # 最大挖掘者数量
        self.mining_efficiency = 1.0  # 挖掘效率倍数

        # 挖掘统计
        self.total_mined = 0  # 总挖掘量
        self.discovery_time = 0.0  # 发现时间
        self.last_mining_time = 0.0  # 上次挖掘时间

        # 挖掘配置
        self.base_mining_rate = 1.0  # 基础挖掘速率（金币/秒）
        self.mining_range = 20  # 挖掘范围（像素）

        # 同步到父类资源系统
        self._sync_to_parent_resource()

    def _sync_to_parent_resource(self):
        """同步到父类资源系统"""
        self.resource.gold_amount = self.gold_amount
        self.resource.is_gold_vein = self.is_gold_vein
        self.resource.being_mined = self.status == GoldMineStatus.BEING_MINED
        self.resource.miners_count = len(
            [a for a in self.mining_assignments if a.is_active])
        self.resource.is_depleted = self.status == GoldMineStatus.DEPLETED

        # 同步到瓦片对象属性（用于状态指示器渲染）
        self.being_mined = self.status == GoldMineStatus.BEING_MINED
        self.miners_count = len(
            [a for a in self.mining_assignments if a.is_active])

    def discover(self) -> Dict[str, Any]:
        """
        发现金矿

        Returns:
            Dict: 发现结果
        """
        if self.status != GoldMineStatus.UNDISCOVERED:
            return {'success': False, 'message': '金矿已被发现'}

        self.status = GoldMineStatus.DISCOVERED
        self.discovery_time = time.time()
        self.tile_type = TileType.GOLD_VEIN
        self.is_dug = True

        # 同步到父类
        self._sync_to_parent_resource()

        return {
            'success': True,
            'gold_amount': self.gold_amount,
            'message': f"发现黄金矿脉！位置: ({self.x}, {self.y}) 储量: {self.gold_amount} 原始黄金"
        }

    def assign_miner(self, miner_id: str, miner_name: str, efficiency: float = 1.0) -> Dict[str, Any]:
        """
        分配挖掘者

        Args:
            miner_id: 挖掘者ID
            miner_name: 挖掘者名称
            efficiency: 挖掘效率

        Returns:
            Dict: 分配结果
        """
        # 检查是否已分配
        for assignment in self.mining_assignments:
            if assignment.miner_id == miner_id and assignment.is_active:
                return {'success': False, 'message': '挖掘者已分配到此金矿'}

        # 检查是否已满
        active_miners = len(
            [a for a in self.mining_assignments if a.is_active])
        if active_miners >= self.max_miners:
            return {'success': False, 'message': '金矿挖掘者已满'}

        # 检查金矿状态 - 允许未发现的金矿被挖掘（会自动发现）
        if self.status not in [GoldMineStatus.UNDISCOVERED, GoldMineStatus.DISCOVERED, GoldMineStatus.BEING_MINED]:
            return {'success': False, 'message': '金矿不可挖掘'}

        # 创建分配
        assignment = MiningAssignment(
            miner_id=miner_id,
            miner_name=miner_name,
            assigned_time=time.time(),
            mining_efficiency=efficiency
        )
        self.mining_assignments.append(assignment)

        # 更新状态
        if self.status == GoldMineStatus.UNDISCOVERED:
            self.status = GoldMineStatus.DISCOVERED
            self.discovery_time = time.time()
        elif self.status == GoldMineStatus.DISCOVERED:
            self.status = GoldMineStatus.BEING_MINED

        # 同步到父类
        self._sync_to_parent_resource()

        return {
            'success': True,
            'message': f"{miner_name} 开始挖掘金矿 ({self.x}, {self.y})",
            'miners_count': len([a for a in self.mining_assignments if a.is_active])
        }

    def remove_miner(self, miner_id: str) -> Dict[str, Any]:
        """
        移除挖掘者

        Args:
            miner_id: 挖掘者ID

        Returns:
            Dict: 移除结果
        """
        for assignment in self.mining_assignments:
            if assignment.miner_id == miner_id and assignment.is_active:
                assignment.is_active = False

                # 检查是否还有活跃挖掘者
                active_miners = len(
                    [a for a in self.mining_assignments if a.is_active])
                if active_miners == 0 and self.status == GoldMineStatus.BEING_MINED:
                    self.status = GoldMineStatus.DISCOVERED

                # 同步到父类
                self._sync_to_parent_resource()

                return {
                    'success': True,
                    'message': f"{assignment.miner_name} 停止挖掘金矿",
                    'miners_count': active_miners
                }

        return {'success': False, 'message': '未找到指定的挖掘者'}

    def mine_gold(self, delta_time: float) -> Dict[str, Any]:
        """
        挖掘金矿

        Args:
            delta_time: 时间增量（毫秒）

        Returns:
            Dict: 挖掘结果
        """
        if self.status != GoldMineStatus.BEING_MINED:
            return {'mined': 0, 'remaining': self.gold_amount, 'depleted': False}

        # 计算总挖掘效率
        active_assignments = [
            a for a in self.mining_assignments if a.is_active]
        if not active_assignments:
            return {'mined': 0, 'remaining': self.gold_amount, 'depleted': False}

        total_efficiency = sum(a.mining_efficiency for a in active_assignments)
        mining_rate = self.base_mining_rate * total_efficiency * self.mining_efficiency

        # 计算挖掘量
        delta_seconds = delta_time / 1000.0
        mined_amount = min(
            mining_rate * delta_seconds,
            self.gold_amount
        )

        # 更新金矿储量
        self.gold_amount -= mined_amount
        self.total_mined += mined_amount
        self.last_mining_time = time.time()

        # 检查是否耗尽
        depleted = False
        if self.gold_amount <= 0:
            self.gold_amount = 0
            self.status = GoldMineStatus.DEPLETED
            self.is_gold_vein = False
            self.tile_type = TileType.DEPLETED_VEIN
            depleted = True

            # 移除所有挖掘者
            for assignment in self.mining_assignments:
                assignment.is_active = False

        # 同步到父类
        self._sync_to_parent_resource()

        return {
            'mined': mined_amount,
            'remaining': self.gold_amount,
            'depleted': depleted,
            'miners': [a.miner_name for a in active_assignments]
        }

    def get_mining_info(self) -> Dict[str, Any]:
        """
        获取挖掘信息

        Returns:
            Dict: 挖掘信息
        """
        active_miners = [a for a in self.mining_assignments if a.is_active]

        return {
            'position': (self.x, self.y),
            'gold_amount': self.gold_amount,
            'max_gold_amount': self.max_gold_amount,
            'status': self.status.value,
            'miners_count': len(active_miners),
            'max_miners': self.max_miners,
            'mining_efficiency': self.mining_efficiency,
            'total_mined': self.total_mined,
            'miners': [
                {
                    'id': a.miner_id,
                    'name': a.miner_name,
                    'efficiency': a.mining_efficiency,
                    'assigned_time': a.assigned_time
                }
                for a in active_miners
            ]
        }

    def can_be_mined(self) -> bool:
        """检查是否可以挖掘"""
        return (self.status in [GoldMineStatus.DISCOVERED, GoldMineStatus.BEING_MINED] and
                self.gold_amount > 0 and
                not self.is_depleted())

    def is_depleted(self) -> bool:
        """检查是否已耗尽"""
        return self.status == GoldMineStatus.DEPLETED

    def get_mining_progress(self) -> float:
        """获取挖掘进度 (0.0 - 1.0)"""
        if self.max_gold_amount <= 0:
            return 1.0
        return 1.0 - (self.gold_amount / self.max_gold_amount)

    def abandon(self) -> Dict[str, Any]:
        """
        废弃金矿

        Returns:
            Dict: 废弃结果
        """
        # 移除所有挖掘者
        for assignment in self.mining_assignments:
            assignment.is_active = False

        self.status = GoldMineStatus.ABANDONED
        self._sync_to_parent_resource()

        return {
            'success': True,
            'message': f"金矿 ({self.x}, {self.y}) 已废弃",
            'miners_released': len(self.mining_assignments)
        }

    def restore(self, gold_amount: int = None) -> Dict[str, Any]:
        """
        恢复金矿

        Args:
            gold_amount: 恢复的金矿储量，None表示恢复到最大储量

        Returns:
            Dict: 恢复结果
        """
        if self.status != GoldMineStatus.DEPLETED:
            return {'success': False, 'message': '金矿未耗尽，无法恢复'}

        self.gold_amount = gold_amount or self.max_gold_amount
        self.is_gold_vein = True
        self.tile_type = TileType.GOLD_VEIN
        self.status = GoldMineStatus.DISCOVERED
        self._sync_to_parent_resource()

        return {
            'success': True,
            'message': f"金矿 ({self.x}, {self.y}) 已恢复，储量: {self.gold_amount}",
            'gold_amount': self.gold_amount
        }

    def get_render_info(self) -> Dict[str, Any]:
        """获取渲染信息（重写父类方法）"""
        base_info = super().get_render_info()
        base_info.update({
            'gold_mine_status': self.status.value,
            'mining_progress': self.get_mining_progress(),
            'active_miners': len([a for a in self.mining_assignments if a.is_active]),
            'max_miners': self.max_miners,
            'total_mined': self.total_mined
        })
        return base_info

    def __str__(self) -> str:
        """字符串表示"""
        status_emoji = {
            GoldMineStatus.UNDISCOVERED: "❓",
            GoldMineStatus.DISCOVERED: "💰",
            GoldMineStatus.BEING_MINED: "⛏️",
            GoldMineStatus.DEPLETED: "💀",
            GoldMineStatus.ABANDONED: "🚫"
        }

        emoji = status_emoji.get(self.status, "❓")
        miners_info = f" 挖掘者:{len([a for a in self.mining_assignments if a.is_active])}/{self.max_miners}"

        return f"{emoji}金矿({self.x},{self.y}) 储量:{self.gold_amount}/{self.max_gold_amount}{miners_info}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"GoldMine(x={self.x}, y={self.y}, gold={self.gold_amount}/{self.max_gold_amount}, "
                f"status={self.status.value}, miners={len([a for a in self.mining_assignments if a.is_active])})")
