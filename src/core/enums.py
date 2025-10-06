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


class CreatureType(Enum):
    """生物类型"""
    GOBLIN = 'goblin'
    GOBLIN_WORKER = 'goblin_worker'
    GOBLIN_ENGINEER = 'goblin_engineer'
    KNIGHT = 'knight'
    ARCHER = 'archer'
    MAGE = 'mage'
    ORC_WARRIOR = 'orc_warrior'  # 兽人战士
    LITTLE_DEMON = 'little_demon'  # 小恶魔


class AttackType(Enum):
    """攻击类型 - 用于击退效果计算"""
    NORMAL = 'normal'      # 普通攻击
    HEAVY = 'heavy'        # 重击攻击
    AREA = 'area'          # 范围攻击
    MAGIC = 'magic'        # 魔法攻击
    PIERCING = 'piercing'  # 穿透攻击
    RANGED = 'ranged'      # 远程攻击


class KnockbackType(Enum):
    """击退类型 - 用于选择击退强度"""
    NORMAL = 'normal'      # 普通击退
    STRONG = 'strong'      # 强击退
    WEAK = 'weak'          # 弱击退
    NONE = 'none'          # 无击退
