#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
瓦块实体类 - 专门管理瓦块相关功能
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List, Any
from ..core.enums import TileType
# 延迟导入Building类，避免循环导入


@dataclass
class TileResource:
    """瓦块资源信息"""
    gold_amount: int = 0
    is_gold_vein: bool = False
    being_mined: bool = False
    miners_count: int = 0  # 正在挖掘该金矿的苦工数量
    is_depleted: bool = False  # 是否已耗尽


@dataclass
class TileBuilding:
    """瓦块建筑信息"""
    building: Optional[Any] = None  # 使用Any避免循环导入
    room: Optional[str] = None
    room_type: Optional[str] = None
    is_incomplete: bool = False  # 是否为未完成建筑
    needs_rerender: bool = False  # 是否需要重新渲染
    just_rerendered: bool = False  # 是否刚刚重新渲染过


class GameTile:
    """游戏瓦块类 - 统一管理瓦块的所有属性和功能，兼容Tile类接口"""

    def __init__(self, x: int = 0, y: int = 0, tile_type: TileType = None, tile_size: int = 20, **kwargs):
        """
        初始化瓦块

        Args:
            x, y: 瓦块坐标（瓦块单位）
            tile_type: 瓦块类型
            tile_size: 瓦块大小（像素）
            **kwargs: 其他属性，用于兼容Tile类
        """
        self.x = x
        self.y = y
        self.tile_type = tile_type or TileType.ROCK
        self.tile_size = tile_size

        # 瓦块状态
        self.is_dug = False  # 是否已挖掘

        # 资源信息
        self.resource = TileResource()

        # 建筑信息
        self.building = TileBuilding()

        # 可达性标记
        self.is_reachable_from_base = False  # 是否可以从主基地到达
        self.reachability_checked = False  # 是否已检查过可达性
        self.last_reachability_check = 0.0  # 上次检查可达性的时间戳

        # 瓦块中心像素点（相对于地图的绝对坐标）
        self._center_pixel_x = None
        self._center_pixel_y = None
        self._update_center_pixel()

        # 兼容Tile类的属性
        self._init_compatibility_attributes(kwargs)

    @classmethod
    def from_tile(cls, tile_data: dict, x: int = 0, y: int = 0, tile_size: int = 20):
        """
        从Tile类数据创建GameTile实例

        Args:
            tile_data: Tile类的数据字典
            x, y: 瓦块坐标
            tile_size: 瓦块大小
        """
        return cls(
            x=x, y=y,
            tile_type=tile_data.get('type', TileType.ROCK),
            tile_size=tile_size,
            **tile_data
        )

    def __post_init__(self):
        """初始化后处理，保持向后兼容性"""
        # 同步属性
        self._sync_from_internal()

    def _init_compatibility_attributes(self, kwargs):
        """初始化兼容Tile类的属性"""
        # 从kwargs中获取Tile类的属性
        self.room = kwargs.get('room', None)
        self.room_type = kwargs.get('room_type', None)
        self.gold_amount = kwargs.get('gold_amount', 0)
        self.is_gold_vein = kwargs.get('is_gold_vein', False)
        self.being_mined = kwargs.get('being_mined', False)
        self.miners_count = kwargs.get('miners_count', 0)
        self.is_incomplete = kwargs.get('is_incomplete', False)
        self.needs_rerender = kwargs.get('needs_rerender', False)
        self.just_rerendered = kwargs.get('just_rerendered', False)

        # 同步到内部结构
        self.resource.gold_amount = self.gold_amount
        self.resource.is_gold_vein = self.is_gold_vein
        self.resource.being_mined = self.being_mined
        self.resource.miners_count = self.miners_count

        self.building.room = self.room
        self.building.room_type = self.room_type
        self.building.is_incomplete = self.is_incomplete
        self.building.needs_rerender = self.needs_rerender
        self.building.just_rerendered = self.just_rerendered

    def _update_center_pixel(self):
        """更新瓦块中心像素点坐标"""
        self._center_pixel_x = self.x * self.tile_size + self.tile_size // 2
        self._center_pixel_y = self.y * self.tile_size + self.tile_size // 2

    def _sync_to_internal(self):
        """将兼容性属性同步到内部结构"""
        self.resource.gold_amount = self.gold_amount
        self.resource.is_gold_vein = self.is_gold_vein
        self.resource.being_mined = self.being_mined
        self.resource.miners_count = self.miners_count

        self.building.room = self.room
        self.building.room_type = self.room_type
        self.building.is_incomplete = self.is_incomplete
        self.building.needs_rerender = self.needs_rerender
        self.building.just_rerendered = self.just_rerendered

    def _sync_from_internal(self):
        """从内部结构同步到兼容性属性"""
        self.gold_amount = self.resource.gold_amount
        self.is_gold_vein = self.resource.is_gold_vein
        self.being_mined = self.resource.being_mined
        self.miners_count = self.resource.miners_count

        self.room = self.building.room
        self.room_type = self.building.room_type
        self.is_incomplete = self.building.is_incomplete
        self.needs_rerender = self.building.needs_rerender
        self.just_rerendered = self.building.just_rerendered

    @property
    def type(self) -> TileType:
        """获取瓦块类型，兼容Tile类接口"""
        return self.tile_type

    @type.setter
    def type(self, value: TileType):
        """设置瓦块类型，兼容Tile类接口"""
        self.tile_type = value

    @property
    def center_pixel(self) -> Tuple[int, int]:
        """获取瓦块中心像素点坐标（相对于地图的绝对坐标）"""
        return (self._center_pixel_x, self._center_pixel_y)

    def get_screen_center_pixel(self, camera_x: int, camera_y: int) -> Tuple[int, int]:
        """获取瓦块中心像素点在屏幕上的坐标"""
        screen_x = self._center_pixel_x - camera_x
        screen_y = self._center_pixel_y - camera_y
        return (screen_x, screen_y)

    def is_passable(self) -> bool:
        """检查瓦块是否可通行"""
        return self.tile_type in [TileType.GROUND, TileType.ROOM]

    def has_building(self) -> bool:
        """检查瓦块上是否有建筑"""
        return self.building.building is not None

    def has_resource(self) -> bool:
        """检查瓦块上是否有资源"""
        return self.resource.is_gold_vein and self.resource.gold_amount > 0

    def is_gold_vein(self) -> bool:
        """检查是否为金矿脉"""
        return self.resource.is_gold_vein

    def is_being_mined(self) -> bool:
        """检查是否正在被挖掘"""
        return self.resource.being_mined

    def can_be_mined(self) -> bool:
        """检查是否可以挖掘"""
        return (self.is_gold_vein() and
                not self.is_being_mined() and
                self.resource.gold_amount > 0 and
                not self.resource.is_depleted)

    def set_building(self, building: Any):
        """设置瓦块上的建筑"""
        self.building.building = building
        self.building.room = building.building_type.value
        self.building.room_type = building.building_type.value
        self.tile_type = TileType.ROOM

    def remove_building(self):
        """移除瓦块上的建筑"""
        self.building.building = None
        self.building.room = None
        self.building.room_type = None
        self.building.is_incomplete = False
        self.tile_type = TileType.GROUND

    def set_gold_vein(self, gold_amount: int = 500):
        """设置金矿脉（兼容性方法，建议使用GoldMine类）"""
        self.resource.is_gold_vein = True
        self.resource.gold_amount = gold_amount
        self.resource.is_depleted = False

    def mine_gold(self, amount: int) -> int:
        """挖掘金矿，返回实际挖掘的金币数量（兼容性方法，建议使用GoldMine类）"""
        if not self.can_be_mined():
            return 0

        actual_amount = min(amount, self.resource.gold_amount)
        self.resource.gold_amount -= actual_amount

        if self.resource.gold_amount <= 0:
            self.resource.is_depleted = True
            self.resource.is_gold_vein = False
            self.tile_type = TileType.DEPLETED_VEIN

        return actual_amount

    def start_mining(self):
        """开始挖掘（兼容性方法，建议使用GoldMine类）"""
        if self.can_be_mined():
            self.resource.being_mined = True
            self.resource.miners_count += 1

    def stop_mining(self):
        """停止挖掘（兼容性方法，建议使用GoldMine类）"""
        if self.resource.being_mined:
            self.resource.being_mined = False
            self.resource.miners_count = max(0, self.resource.miners_count - 1)

    def dig(self, cost: int = 0, game_state=None, x: int = None, y: int = None) -> dict:
        """
        挖掘瓦块 - 统一挖掘逻辑，兼容Tile类接口

        Args:
            cost: 挖掘成本（金币）
            game_state: 游戏状态对象，用于扣除金币
            x, y: 瓦块坐标（可选，用于消息格式化）

        Returns:
            dict: 挖掘结果 {'success': bool, 'gold_discovered': int, 'message': str}
        """
        if self.tile_type != TileType.ROCK:
            return {'success': False, 'gold_discovered': 0, 'message': '不是岩石瓦块'}

        # 检查挖掘成本
        if cost > 0 and game_state and game_state.gold < cost:
            return {'success': False, 'gold_discovered': 0, 'message': '金币不足'}

        # 扣除挖掘成本
        if cost > 0 and game_state:
            game_state.gold -= cost

        # 在挖掘前先同步属性，检查是否包含金矿脉
        self._sync_to_internal()

        # 检查是否发现金矿脉（在挖掘前检查）
        gold_discovered = 0
        if x is not None and y is not None:
            message = f"挖掘了瓦片 ({x}, {y})"
        else:
            message = f"挖掘了瓦片 ({self.x}, {self.y})"

        if self.resource.is_gold_vein and self.resource.gold_amount > 0:
            # 发现金矿脉
            self.tile_type = TileType.GOLD_VEIN
            gold_discovered = self.resource.gold_amount
            if x is not None and y is not None:
                message = f"发现黄金矿脉！位置: ({x}, {y}) 储量: {gold_discovered} 原始黄金"
            else:
                message = f"发现黄金矿脉！位置: ({self.x}, {self.y}) 储量: {gold_discovered} 原始黄金"

            # 输出可达金矿日志
            self._log_reachable_gold_veins(x, y, gold_discovered)
        else:
            # 没有金矿脉，设置为普通地面
            self.tile_type = TileType.GROUND

        # 设置挖掘状态
        self.is_dug = True
        self.needs_rerender = True

        # 同步到兼容性属性
        self._sync_from_internal()

        return {
            'success': True,
            'gold_discovered': gold_discovered,
            'message': message
        }

    def _log_reachable_gold_veins(self, x: int, y: int, gold_amount: int):
        """
        输出可达金矿日志

        Args:
            x, y: 瓦块坐标
            gold_amount: 金矿储量
        """
        try:
            from ..systems.reachability_system import get_reachability_system
            reachability_system = get_reachability_system()

            # 获取当前所有可达的金矿脉
            # 注意：这里需要传入游戏地图，但我们在瓦块类中无法直接访问
            # 所以先尝试获取，如果失败则输出简单日志
            try:
                reachable_veins = reachability_system.get_reachable_gold_veins([
                ])
            except:
                reachable_veins = []

            print(f"📊 可达金矿统计 - 新发现金矿 ({x}, {y}) 储量: {gold_amount}")
            print(f"   🏆 当前总可达金矿脉数量: {len(reachable_veins)}")

            if reachable_veins:
                total_gold = sum(vein[2] for vein in reachable_veins)
                print(f"   💰 总储量: {total_gold} 原始黄金")

                # 显示前5个金矿的详细信息
                print(f"   📍 可达金矿列表:")
                for i, (vx, vy, vgold) in enumerate(reachable_veins[:5]):
                    status = "🆕 新发现" if (vx, vy) == (x, y) else "✅ 已知"
                    print(f"      {i+1}. {status} ({vx}, {vy}) 储量: {vgold}")

                if len(reachable_veins) > 5:
                    print(f"      ... 还有 {len(reachable_veins) - 5} 个金矿脉")

        except ImportError:
            # 如果无法导入可达性系统，输出简单日志
            print(f"📊 发现金矿脉 ({x}, {y}) 储量: {gold_amount}")
        except Exception as e:
            # 如果出现其他错误，输出简单日志
            print(f"📊 发现金矿脉 ({x}, {y}) 储量: {gold_amount} (日志系统错误: {e})")

    def is_reachable(self) -> bool:
        """检查瓦块是否可达（从主基地）"""
        return self.is_reachable_from_base

    def set_reachability(self, reachable: bool, check_time: float = None):
        """设置瓦块可达性状态"""
        import time
        self.is_reachable_from_base = reachable
        self.reachability_checked = True
        self.last_reachability_check = check_time or time.time()

    def needs_reachability_check(self, max_age: float = 5.0) -> bool:
        """检查是否需要重新检查可达性"""
        import time
        if not self.reachability_checked:
            return True
        return (time.time() - self.last_reachability_check) > max_age

    def get_render_info(self) -> dict:
        """获取渲染信息"""
        return {
            'tile_type': self.tile_type,
            'center_pixel': self.center_pixel,
            'has_building': self.has_building(),
            'has_resource': self.has_resource(),
            'is_gold_vein': self.is_gold_vein,
            'is_being_mined': self.is_being_mined(),
            'gold_amount': self.resource.gold_amount,
            'miners_count': self.resource.miners_count,
            'building': self.building.building,
            'room_type': self.building.room_type,
            'is_incomplete': self.building.is_incomplete,
            'needs_rerender': self.building.needs_rerender,
            'is_reachable': self.is_reachable()
        }

    def __str__(self) -> str:
        """字符串表示"""
        building_info = f"建筑:{self.building.room_type}" if self.has_building(
        ) else ""
        resource_info = f"金矿:{self.resource.gold_amount}" if self.has_resource(
        ) else ""
        return f"瓦块({self.x},{self.y}) 类型:{self.tile_type.value} {building_info} {resource_info}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"GameTile(x={self.x}, y={self.y}, type={self.tile_type.value}, "
                f"center=({self._center_pixel_x},{self._center_pixel_y}), "
                f"building={self.has_building()}, resource={self.has_resource()})")
