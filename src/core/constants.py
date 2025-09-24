#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏常量和配置
"""


class GameConstants:
    """游戏基础常量"""
    MAP_WIDTH = 50
    MAP_HEIGHT = 30
    TILE_SIZE = 20
    FPS_TARGET = 60

    # 窗口设置
    WINDOW_WIDTH = 1200
    WINDOW_HEIGHT = 800

    # 颜色定义
    COLORS = {
        'background': (26, 26, 26),
        'rock': (68, 68, 68),
        'ground': (102, 102, 102),
        'gold_vein': (184, 134, 11),
        'treasury': (255, 170, 0),
        'lair': (139, 69, 19),
        'ui_bg': (0, 0, 0, 200),
        'ui_border': (102, 102, 102),
        'text': (255, 255, 255),
        'highlight_green': (0, 255, 0),
        'highlight_red': (255, 0, 0),
        'highlight_gold': (255, 215, 0)
    }


class GameBalance:
    """游戏平衡配置"""
    starting_gold = 1000
    starting_mana = 100
    starting_food = 50
    max_creatures = 20
    hero_spawn_rate = 0.0008
    gold_per_second_per_treasury = 1  # 改为整数，每秒1金币
    mana_regen_per_second = 1  # 改为整数，每秒1法力
