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

    # 战斗系统常量
    DEFAULT_ATTACK_RANGE = 30
    DEFAULT_UNIT_SIZE = 15
    DEFAULT_CREATURE_DETECTION_RANGE = 150
    # 移除英雄检测范围常量，改为使用追击范围

    # 追击范围倍数
    MELEE_PURSUIT_MULTIPLIER = 2.5  # 近战单位追击范围倍数
    RANGED_PURSUIT_MULTIPLIER = 1.0  # 远程单位追击范围倍数

    # 移动和追击常量
    FLEE_DISTANCE = 100
    MAP_BORDER_BUFFER = 50
    APPROACH_BUFFER = 10
    TARGET_SWITCH_BUFFER = 15
    PURSUIT_RANGE_MULTIPLIER = 2.5  # 追击范围是攻击范围的倍数

    # 速度倍数
    DEFAULT_SPEED_MULTIPLIER = 1.0
    COMBAT_SPEED_MULTIPLIER = 1.2
    PATROL_SPEED_MULTIPLIER = 0.6
    WANDER_SPEED_MULTIPLIER = 0.5

    # 血量阈值
    FLEE_HEALTH_THRESHOLD = 0.3  # 30%血量以下逃跑

    # 时间常量
    FRAME_TIME_MS = 16.67  # 60 FPS的帧时间
    DELTA_TIME_DEFAULT = 16.67  # 默认delta_time

    # 物理系统常量
    COLLISION_RADIUS_MULTIPLIER = 0.6
    MIN_COLLISION_RADIUS = 5

    # 击退系统常量 - 固定距离机制
    KNOCKBACK_DISTANCE_WEAK = 8      # 弱击退距离
    KNOCKBACK_DISTANCE_NORMAL = 15   # 普通击退距离
    KNOCKBACK_DISTANCE_STRONG = 30   # 强击退距离
    KNOCKBACK_DURATION = 0.3         # 击退持续时间
    KNOCKBACK_SPEED = 50             # 击退速度
    WALL_COLLISION_DAMAGE_RATIO = 0.15
    MIN_WALL_DAMAGE = 2
    MAX_WALL_DAMAGE = 15
    WALL_BOUNCE_RATIO = 0.6
    MIN_BOUNCE_DISTANCE = 8
    SPATIAL_HASH_CELL_SIZE = 50
    MAX_UNITS_PER_CELL = 20
    UPDATE_FREQUENCY = 60

    # 移动系统常量
    STUCK_THRESHOLD = 30
    PATH_UPDATE_INTERVAL = 0.5
    MIN_DISTANCE_THRESHOLD = 20
    PATHFINDING_TIMEOUT = 2.0
    ARRIVAL_DISTANCE = 15
    SIDE_MOVE_DISTANCE = 0.5
    WANDER_ATTEMPT_COUNT = 10
    WANDER_RANGE = 3

    # 建筑系统常量
    DEFAULT_BUILD_TIME = 60.0
    DEFAULT_BUILD_HEALTH = 200
    DEFAULT_BUILD_ARMOR = 5
    UPGRADE_TIME_MULTIPLIER = 0.5
    EFFICIENCY_UPGRADE_BONUS = 0.1
    MAX_EFFICIENCY = 2.0

    # UI常量
    PANEL_ALPHA = 220
    HEALTH_BAR_HEIGHT = 4
    HEALTH_BAR_WIDTH = 20
    HEALTH_COLOR_HEALTHY = 0.6
    HEALTH_COLOR_WARNING = 0.3
    SCROLL_SPEED = 20
    BUTTON_HEIGHT = 25
    ITEM_HEIGHT = 20
    LIST_ITEM_HEIGHT = 30
    TEXT_LINE_SPACING = 20
    BUTTON_PADDING = 10
    TEXT_RIGHT_OFFSET = 80
    STARS_RIGHT_OFFSET = 100

    # 实体系统常量
    REGENERATION_DELAY = 10  # 脱离战斗后开始回血的延迟时间
    REGENERATION_RATE = 1  # 每秒回血量
    TARGET_SEARCH_COOLDOWN = 0.5  # 目标搜索冷却时间
    TARGET_VALIDITY_TIME = 3.0  # 目标有效性时间
    SEARCH_RANGE_IMP = 120
    SEARCH_RANGE_GARGOYLE = 150
    SEARCH_RANGE_FIRE_SALAMANDER = 140
    SEARCH_RANGE_SHADOW_MAGE = 160
    SEARCH_RANGE_TREE_GUARDIAN = 100
    SEARCH_RANGE_SHADOW_LORD = 180
    SEARCH_RANGE_BONE_DRAGON = 200
    SEARCH_RANGE_HELLHOUND = 130
    SEARCH_RANGE_STONE_GOLEM = 110
    SEARCH_RANGE_SUCCUBUS = 140
    SEARCH_RANGE_GOBLIN_ENGINEER = 80
    WANDER_SPEED_IMP = 0.6
    WANDER_SPEED_GARGOYLE = 0.4
    WANDER_SPEED_FIRE_SALAMANDER = 0.7
    WANDER_SPEED_SHADOW_MAGE = 0.5
    WANDER_SPEED_TREE_GUARDIAN = 0.3
    WANDER_SPEED_SHADOW_LORD = 0.8
    WANDER_SPEED_BONE_DRAGON = 0.6
    WANDER_SPEED_HELLHOUND = 0.7
    WANDER_SPEED_STONE_GOLEM = 0.4
    WANDER_SPEED_SUCCUBUS = 0.7
    WANDER_SPEED_GOBLIN_ENGINEER = 0.5

    # 颜色定义
    COLORS = {
        'background': (26, 26, 26),
        'rock': (68, 68, 68),
        'ground': (102, 102, 102),
        'gold_vein': (184, 134, 11),
        'treasury': (255, 170, 0),
        'ui_bg': (0, 0, 0, 200),
        'ui_border': (102, 102, 102),
        'text': (255, 255, 255),
        'highlight_green': (0, 255, 0),
        'highlight_red': (255, 0, 0),
        'highlight_gold': (255, 215, 0)
    }

    # 状态条常量
    STATUS_BAR_HEIGHT = 2  # 状态条高度（像素）
    STATUS_BAR_OFFSET = 4  # 状态条偏移量（像素）
    STATUS_BAR_PADDING = 8  # 状态条内边距（像素）

    # 状态条颜色
    STATUS_COLOR_AMMUNITION = (255, 165, 0)  # 橙色 - 弹药 / 金币
    STATUS_COLOR_GOLD = (255, 255, 0)  # 黄色 - 未使用
    STATUS_COLOR_DEFAULT = (255, 255, 255)  # 白色 - 默认

    # 金矿最大存储量
    GOLD_MINE_MAX_STORAGE = 500

    # 建筑状态常量
    BUILDING_STATUS_INCOMPLETE = 'incomplete'
    BUILDING_STATUS_DESTROYED = 'destroyed'
    BUILDING_STATUS_NEEDS_REPAIR = 'needs_repair'
    BUILDING_STATUS_COMPLETED = 'completed'
    BUILDING_STATUS_NO_AMMUNITION = 'no_ammunition'
    BUILDING_STATUS_TREASURY_FULL = 'treasury_full'
    BUILDING_STATUS_NEEDS_MAGE = 'needs_mage'  # 需要法师辅助
    BUILDING_STATUS_MANA_FULL = 'mana_full'    # 法力存储池已满
    BUILDING_STATUS_MANA_GENERATION = 'mana_generation'  # 魔力生成状态
    BUILDING_STATUS_TRAINING = 'training'  # 训练状态
    BUILDING_STATUS_SUMMONING = 'summoning'  # 召唤状态
    BUILDING_STATUS_SUMMONING_PAUSED = 'summoning_paused'  # 暂停召唤状态
    BUILDING_STATUS_LOCKED = 'locked'  # 锁定状态
    BUILDING_STATUS_READY_TO_TRAIN = 'ready_to_train'  # 准备训练
    BUILDING_STATUS_READY_TO_SUMMON = 'ready_to_summon'  # 准备召唤
    BUILDING_STATUS_ACCEPTING_GOLD = 'accepting_gold'  # 接受金币

    # 建筑状态颜色配置
    BUILDING_STATUS_COLORS = {
        BUILDING_STATUS_INCOMPLETE: (128, 128, 128),      # 灰色 - 未完成建筑
        BUILDING_STATUS_DESTROYED: (128, 128, 128),       # 灰色 - 被摧毁建筑
        BUILDING_STATUS_NEEDS_REPAIR: (255, 255, 0),      # 黄色 - 需要修复建筑
        BUILDING_STATUS_COMPLETED: (0, 255, 0),           # 绿色 - 完成建筑
        BUILDING_STATUS_NO_AMMUNITION: (255, 0, 0),       # 红色 - 空弹药
        BUILDING_STATUS_TREASURY_FULL: (255, 0, 0),       # 红色 - 金库爆满
        BUILDING_STATUS_NEEDS_MAGE: (255, 165, 0),        # 橙色 - 需要法师辅助
        BUILDING_STATUS_MANA_FULL: (0, 100, 255),         # 蓝色 - 法力存储池已满
        BUILDING_STATUS_MANA_GENERATION: (128, 0, 128),   # 紫色 - 魔力生成状态
        BUILDING_STATUS_TRAINING: (139, 69, 19),          # 棕色 - 训练状态
        BUILDING_STATUS_SUMMONING: (0, 255, 255),         # 青色 - 召唤状态
        BUILDING_STATUS_SUMMONING_PAUSED: (255, 0, 0),    # 红色 - 暂停召唤状态
        BUILDING_STATUS_LOCKED: (64, 64, 64),             # 深灰色 - 锁定状态
        BUILDING_STATUS_READY_TO_TRAIN: (160, 82, 45),    # 马鞍棕色 - 准备训练
        BUILDING_STATUS_READY_TO_SUMMON: (75, 0, 130),    # 靛青色 - 准备召唤
        BUILDING_STATUS_ACCEPTING_GOLD: (255, 215, 0),    # 金色 - 接受金币
    }

    # 建筑渲染常量
    BUILDING_BORDER_WIDTH = 2  # 建筑边框宽度
    BUILDING_PADDING = 4  # 建筑内边距
    BUILDING_OFFSET = 8  # 建筑偏移量
    BUILDING_FOUNDATION_HEIGHT = 3  # 建筑地基高度
    BUILDING_FOUNDATION_OFFSET = 2  # 建筑地基偏移量

    # 箭塔渲染常量
    ARROW_TOWER_BASE_OFFSET = 8  # 箭塔底座偏移
    ARROW_TOWER_ROOF_OFFSET = 6  # 箭塔尖顶偏移
    ARROW_TOWER_SLOT_WIDTH = 8  # 箭塔射击孔宽度
    ARROW_TOWER_SLOT_HEIGHT = 4  # 箭塔射击孔高度
    ARROW_TOWER_FLAG_HEIGHT = 6  # 箭塔旗帜高度
    ARROW_TOWER_FLAG_OFFSET = 4  # 箭塔旗帜偏移
    ARROW_TOWER_BRICK_WIDTH = 4  # 箭塔砖块宽度
    ARROW_TOWER_BRICK_HEIGHT = 3  # 箭塔砖块高度
    ARROW_TOWER_BRICK_OFFSET = 8  # 箭塔砖块偏移

    # 地牢之心渲染常量
    DUNGEON_HEART_BORDER_WIDTH = 3  # 地牢之心边框宽度
    DUNGEON_HEART_BORDER_OFFSET = 3  # 地牢之心边框偏移
    DUNGEON_HEART_CORNER_SIZE = 5  # 地牢之心装饰角大小
    DUNGEON_HEART_CORNER_OFFSET = 2  # 地牢之心装饰角偏移
    DUNGEON_HEART_LINE_WIDTH = 2  # 地牢之心装饰线宽度
    DUNGEON_HEART_LINE_OFFSET = 10  # 地牢之心装饰线偏移
    DUNGEON_HEART_HEALTH_BAR_OFFSET = 12  # 地牢之心生命条偏移

    # 金库渲染常量
    TREASURY_SAFE_WIDTH = 16  # 金库保险箱宽度
    TREASURY_SAFE_HEIGHT = 12  # 金库保险箱高度
    TREASURY_DOOR_WIDTH = 12  # 金库门宽度
    TREASURY_DOOR_HEIGHT = 8  # 金库门高度
    TREASURY_HANDLE_WIDTH = 3  # 金库把手宽度
    TREASURY_HANDLE_HEIGHT = 2  # 金库把手高度
    TREASURY_CORNER_SIZE = 3  # 金库装饰角大小
    TREASURY_COIN_OFFSET = 8  # 金库金币符号偏移


class GameBalance:
    """游戏平衡配置"""
    starting_gold = 1000
    starting_mana = 100
    starting_food = 50
    max_creatures = 20
    hero_spawn_rate = 0.0008
    gold_per_second_per_treasury = 1  # 改为整数，每秒1金币
    # 魔力增长：每5秒生成1点魔力（由地牢之心直接实现）
