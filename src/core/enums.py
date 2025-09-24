#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏枚举定义
"""

from enum import Enum


class TileType(Enum):
    """瓦片类型"""
    ROCK = 0
    GROUND = 1
    ROOM = 2
    GOLD_VEIN = 3
    DEPLETED_VEIN = 4


class BuildMode(Enum):
    """建造模式"""
    NONE = None
    DIG = 'dig'
    TREASURY = 'treasury'
    LAIR = 'lair'
    SUMMON = 'summon'
    SUMMON_SELECTION = 'summon_selection'  # 怪物选择模式
    SUMMON_LOGISTICS = 'summon_logistics'  # 后勤召唤模式

    # 建筑系统建造模式
    BUILD_INFRASTRUCTURE = 'build_infrastructure'  # 基础设施建筑
    BUILD_FUNCTIONAL = 'build_functional'          # 功能性建筑
    BUILD_MILITARY = 'build_military'              # 军事建筑
    BUILD_MAGICAL = 'build_magical'                # 魔法建筑
    BUILD_SPECIFIC = 'build_specific'              # 特定建筑类型

    # 工程师相关模式
    SUMMON_ENGINEER = 'summon_engineer'            # 召唤工程师
