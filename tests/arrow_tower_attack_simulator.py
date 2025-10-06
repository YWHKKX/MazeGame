#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
箭塔弹药补充逻辑测试
测试工程师自动为箭塔补充弹药的完整流程
"""

import sys
import os
import time
import math
import random
import pygame
import locale
import codecs
import traceback

# 设置控制台编码
if sys.platform == "win32":
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
    except:
        pass

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 确保可以导入src模块
try:
    import src
except ImportError:
    # 如果还是无法导入，尝试添加src目录到路径
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

# 现在导入项目模块
try:
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
    from src.managers.movement_system import MovementSystem
    from src.utils.logger import game_logger
    from src.core.constants import GameConstants
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class ArrowTowerAmmunitionTest:
    """箭塔弹药补充测试"""

    def __init__(self):
        """初始化测试"""
        # 创建游戏环境模拟器，启用2倍UI放大
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200,
            screen_height=800,
            tile_size=GameConstants.TILE_SIZE,
            ui_scale=2.0  # 2倍UI放大，方便观察
        )

        # 初始化pygame组件
        self.simulator.init_pygame()

        game_logger.info("🎮 箭塔弹药逻辑测试初始化完成")
        game_logger.info(f"🔍 UI放大倍数: {self.simulator.get_ui_scale()}x")
        game_logger.info("=" * 60)

        # 测试状态
        self.test_duration = 60.0  # 测试持续时间（秒）
        self.start_time = None
        self.ammunition_stats = {
            'reload_attempts': 0,
            'reload_successes': 0,
            'ammunition_consumed': 0,
            'engineer_assignments': 0,
            'gold_spent': 0
        }

        # 攻击冷却时间测试统计
        self.attack_timing_stats = {
            'attacks_count': 0,
            'last_attack_time': 0.0,
            'attack_intervals': [],
            'cooldown_violations': 0
        }

        # 范围攻击统计
        self.range_attack_stats = {
            'total_attacks': 0,
            'range_attacks': 0,
            'single_target_attacks': 0,
            'targets_hit_per_attack': [],
            'total_damage_dealt': 0,
            'range_damage_logs': []
        }

        # 位置信息（用于显示）
        # 计算屏幕中心位置
        self.screen_center_x = int(self.simulator.screen_width // 2)   # 600
        self.screen_center_y = int(self.simulator.screen_height // 2)   # 400

        # 地牢之心位置：地图中心偏左区域 (30x20地图)
        self.dungeon_heart_tile_x = 6
        self.dungeon_heart_tile_y = 8

        # 箭塔位置：地牢之心右侧，适当靠近
        self.tower_tile_x = 10
        self.tower_tile_y = 8

        # 工程师位置：靠近地牢之心，便于快速获取金币
        self.engineer_tile_x = 8
        self.engineer_tile_y = 10

        # 设置测试场景
        self.setup_ammunition_test_scenario()

        # 获取测试对象引用
        self.arrow_tower = None
        self.dungeon_heart = None
        self.engineer = None
        self._find_test_objects()

        # 设置范围攻击日志拦截
        self.setup_range_attack_logging()

        # 初始化中文字体
        self._init_chinese_fonts()

    def _init_chinese_fonts(self):
        """初始化中文字体"""
        try:
            # 设置Windows编码
            if sys.platform == "win32":
                try:
                    locale.setlocale(locale.LC_ALL, 'Chinese_China.utf8')
                    game_logger.info("✅ Windows编码设置完成")
                except:
                    try:
                        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
                        game_logger.info("✅ Windows编码设置完成")
                    except:
                        game_logger.info("⚠️ 无法设置Windows编码，使用默认编码")

            # 尝试加载系统中文字体
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/arial.ttf",   # Arial
                "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            ]

            self.chinese_font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        self.chinese_font = pygame.font.Font(font_path, 24)
                        game_logger.info(f"✅ 成功加载中文字体: {font_path}")
                        break
                    except Exception as e:
                        game_logger.info(f"⚠️ 字体加载失败 {font_path}: {e}")
                        continue

            if not self.chinese_font:
                # 如果都失败了，使用pygame默认字体
                self.chinese_font = pygame.font.Font(None, 24)
                game_logger.info("⚠️ 使用默认字体，中文可能显示为方块")

        except Exception as e:
            game_logger.info(f"❌ 字体初始化失败: {e}")
            self.chinese_font = pygame.font.Font(None, 24)

        game_logger.info(f"🏹 弹药测试场景设置完成")
        game_logger.info(
            f"   - 地牢之心瓦片坐标: ({self.dungeon_heart.tile_x}, {self.dungeon_heart.tile_y})")
        game_logger.info(
            f"   - 地牢之心像素坐标: ({self.dungeon_heart.x:.1f}, {self.dungeon_heart.y:.1f})px")
        game_logger.info(
            f"   - 地牢之心金币: {self.simulator.dungeon_heart.stored_gold if self.simulator.dungeon_heart else 0}")
        game_logger.info(
            f"   - 箭塔瓦片坐标: ({self.arrow_tower.tile_x}, {self.arrow_tower.tile_y})")
        game_logger.info(
            f"   - 箭塔像素坐标: ({self.arrow_tower.x:.1f}, {self.arrow_tower.y:.1f})px")
        game_logger.info(f"   - 箭塔最大弹药: {self.arrow_tower.max_ammunition}")
        game_logger.info(f"   - 箭塔当前弹药: {self.arrow_tower.current_ammunition}")
        # 计算工程师的瓦片坐标
        engineer_tile_x = int(self.engineer.x // GameConstants.TILE_SIZE)
        engineer_tile_y = int(self.engineer.y // GameConstants.TILE_SIZE)
        game_logger.info(
            f"   - 工程师瓦片坐标: ({engineer_tile_x}, {engineer_tile_y})")
        game_logger.info(
            f"   - 工程师像素坐标: ({self.engineer.x:.1f}, {self.engineer.y:.1f})px")

        # 计算地牢之心到箭塔的距离
        distance = self.calculate_distance(
            self.dungeon_heart.x, self.dungeon_heart.y,
            self.arrow_tower.x, self.arrow_tower.y)
        game_logger.info(f"   - 地牢之心到箭塔距离: {distance:.1f}像素")
        game_logger.info(f"   - TILE_SIZE: {self.simulator.tile_size}")

    def setup_ammunition_test_scenario(self):
        """设置弹药测试场景"""

        # 挖掘测试区域 - 根据实际地图大小设置
        # 地图大小: 30x20 (1200//40 x 800//40)
        map_width = len(
            self.simulator.game_map[0]) if self.simulator.game_map else 30
        map_height = len(
            self.simulator.game_map) if self.simulator.game_map else 20

        game_logger.info(f"🗺️ 实际地图大小: {map_width}x{map_height}")
        game_logger.info(f"🗺️ 挖掘范围: x(3-{map_width-3}), y(3-{map_height-3})")

        for x in range(3, map_width - 3):  # 留出边界
            for y in range(3, map_height - 3):  # 留出边界
                if y < len(self.simulator.game_map) and x < len(self.simulator.game_map[y]):
                    self.simulator.game_map[y][x].is_dug = True

        # 创建地牢之心（500金币）
        self.simulator.create_dungeon_heart(
            self.dungeon_heart_tile_x, self.dungeon_heart_tile_y, 500)
        self.simulator.dungeon_heart_pos = (
            self.dungeon_heart_tile_x, self.dungeon_heart_tile_y)

        # 创建箭塔（设置最大弹药为10）
        self.simulator.create_arrow_tower(self.tower_tile_x, self.tower_tile_y)

        # 创建工程师（使用像素坐标）
        engineer_pixel_x = self.engineer_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        engineer_pixel_y = self.engineer_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        self.engineer = self.simulator.create_engineer(
            engineer_pixel_x, engineer_pixel_y)

        # 创建骑士用于消耗弹药（放置在箭塔攻击范围内）
        # 计算箭塔的像素坐标
        tower_pixel_x = self.tower_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        tower_pixel_y = self.tower_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        # 骑士位置：确保在地图范围内且在穿透攻击范围内
        # 地图大小：30x20瓦片，每个瓦片40像素（考虑UI放大）
        # 骑士1：箭塔右侧2个瓦片距离
        knight_pixel_x = tower_pixel_x + 80  # 箭塔右侧80像素（2个瓦片）
        knight_pixel_y = tower_pixel_y

        # 使用模拟器API创建骑士
        knight = self.simulator.create_hero(
            knight_pixel_x, knight_pixel_y, 'knight')
        knight.name = "弹药测试骑士"
        knight.wander_enabled = False  # 禁用游荡，让骑士专注于攻击箭塔
        knight.is_enemy = True  # 修复：骑士应该是敌人，这样箭塔才能攻击他们
        knight.faction = "heroes"

        # 骑士2：测试穿透攻击的多目标效果
        knight2_pixel_x = tower_pixel_x + 100  # 箭塔右侧100像素，在穿透范围内
        knight2_pixel_y = tower_pixel_y + 10  # 稍微偏移10像素，避免重叠但仍在线性穿透范围内

        knight2 = self.simulator.create_hero(
            knight2_pixel_x, knight2_pixel_y, 'knight')
        knight2.name = "穿透测试骑士2"
        knight2.wander_enabled = False  # 禁用游荡，让骑士专注于攻击箭塔
        knight2.is_enemy = True  # 修复：骑士应该是敌人，这样箭塔才能攻击他们
        knight2.faction = "heroes"

        game_logger.info("🏗️ 弹药测试场景设置完成")
        game_logger.info(
            f"   - 地牢之心: 瓦片坐标({self.dungeon_heart_tile_x}, {self.dungeon_heart_tile_y}), 500金币")
        game_logger.info(
            f"   - 箭塔: 瓦片坐标({self.tower_tile_x}, {self.tower_tile_y})")
        game_logger.info(
            f"   - 工程师: 瓦片坐标({self.engineer_tile_x}, {self.engineer_tile_y}) -> 像素坐标({engineer_pixel_x}, {engineer_pixel_y})")
        game_logger.info(f"   - 骑士1: 像素坐标({knight_pixel_x}, {knight_pixel_y})")
        game_logger.info(
            f"   - 骑士2: 像素坐标({knight2_pixel_x}, {knight2_pixel_y})")

        # 计算各建筑之间的距离
        heart_pixel_x = self.dungeon_heart_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        heart_pixel_y = self.dungeon_heart_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        tower_pixel_x = self.tower_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        tower_pixel_y = self.tower_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        engineer_pixel_x = self.engineer_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        engineer_pixel_y = self.engineer_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        heart_to_tower = math.sqrt(
            (tower_pixel_x - heart_pixel_x)**2 + (tower_pixel_y - heart_pixel_y)**2)
        heart_to_engineer = math.sqrt(
            (engineer_pixel_x - heart_pixel_x)**2 + (engineer_pixel_y - heart_pixel_y)**2)
        engineer_to_tower = math.sqrt(
            (tower_pixel_x - engineer_pixel_x)**2 + (tower_pixel_y - engineer_pixel_y)**2)

        game_logger.info(f"   - 地牢之心到箭塔距离: {heart_to_tower:.1f}像素")
        game_logger.info(f"   - 地牢之心到工程师距离: {heart_to_engineer:.1f}像素")
        game_logger.info(f"   - 工程师到箭塔距离: {engineer_to_tower:.1f}像素")
        game_logger.info(
            f"   - 箭塔到骑士1距离: {math.sqrt((knight_pixel_x - tower_pixel_x)**2 + (knight_pixel_y - tower_pixel_y)**2):.1f}像素")
        game_logger.info(
            f"   - 箭塔到骑士2距离: {math.sqrt((knight2_pixel_x - tower_pixel_x)**2 + (knight2_pixel_y - tower_pixel_y)**2):.1f}像素")

    def _find_test_objects(self):
        """查找测试对象 - 使用模拟器统一API"""
        # 查找箭塔
        buildings = self.simulator.building_manager.buildings
        for building in buildings:
            if hasattr(building, 'building_type') and building.building_type.value == 'arrow_tower':
                self.arrow_tower = building
                # 使用建筑API设置弹药（如果建筑支持的话）
                if hasattr(building, 'set_ammunition'):
                    building.set_ammunition(0, 10)  # 当前弹药0，最大弹药10
                else:
                    # 如果建筑不支持API，直接设置（仅用于测试）
                    self.arrow_tower.max_ammunition = 10
                    self.arrow_tower.current_ammunition = 0
                break

        # 查找地牢之心
        for building in buildings:
            if hasattr(building, 'building_type') and building.building_type.value == 'dungeon_heart':
                self.dungeon_heart = building
                break

        # 查找工程师
        engineers = self.simulator.building_manager.engineers
        if engineers:
            self.engineer = engineers[0]  # 取第一个工程师

        # 查找骑士 - 使用模拟器API
        heroes = self.simulator.heroes
        knight_count = 0
        for hero in heroes:
            if hasattr(hero, 'type') and hero.type == 'knight':
                knight_count += 1
                if knight_count == 1:
                    self.knight = hero  # 第一个骑士作为主要测试对象

                # 为所有骑士设置攻击目标
                if self.arrow_tower:
                    # 使用MovementSystem设置移动目标
                    MovementSystem.set_target(
                        hero, (self.arrow_tower.x, self.arrow_tower.y))

                    # 设置攻击目标
                    if hasattr(hero, 'add_to_attack_list'):
                        hero.add_to_attack_list(self.arrow_tower)
                        game_logger.info(
                            f"✅ 为骑士 {hero.name} 设置攻击目标: {self.arrow_tower.building_type.value}")

                # 只处理前两个骑士
                if knight_count >= 2:
                    break

        if not self.arrow_tower or not self.dungeon_heart or not self.engineer or not self.knight:
            raise Exception("❌ 无法找到测试对象：箭塔、地牢之心、工程师或骑士")

    def calculate_distance(self, x1, y1, x2, y2):
        """计算两点间距离"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def setup_range_attack_logging(self):
        """设置范围攻击日志拦截"""
        if not self.arrow_tower:
            game_logger.info("⚠️ 无法设置范围攻击日志：箭塔未找到")
            return

        # 拦截箭塔的attack_target方法
        original_attack_target = self.arrow_tower.attack_target

        def logged_attack_target(target):
            """带日志的攻击目标方法"""
            game_logger.info(
                f"[RANGE DEBUG] 箭塔开始攻击: {target.name if hasattr(target, 'name') else target.type}")

            # 记录攻击前的目标血量
            targets_before = {}
            for hero in self.simulator.heroes:
                if hasattr(hero, 'health'):
                    targets_before[hero] = hero.health

            # 调用原始攻击方法
            result = original_attack_target(target)

            # 记录攻击后的目标血量变化
            targets_after = {}
            targets_damaged = []
            for hero in self.simulator.heroes:
                if hasattr(hero, 'health') and hero in targets_before:
                    targets_after[hero] = hero.health
                    damage = targets_before[hero] - targets_after[hero]
                    if damage > 0:
                        targets_damaged.append({
                            'target': hero.name if hasattr(hero, 'name') else hero.type,
                            'damage': damage,
                            'health_before': targets_before[hero],
                            'health_after': targets_after[hero]
                        })

            # 更新统计
            self.range_attack_stats['total_attacks'] += 1
            if len(targets_damaged) > 1:
                self.range_attack_stats['range_attacks'] += 1
                game_logger.info(
                    f"[RANGE DEBUG] ✅ 范围攻击生效！命中{len(targets_damaged)}个目标")
            else:
                self.range_attack_stats['single_target_attacks'] += 1
                game_logger.info(
                    f"[RANGE DEBUG] ❌ 单目标攻击，命中{len(targets_damaged)}个目标")

            self.range_attack_stats['targets_hit_per_attack'].append(
                len(targets_damaged))

            # 记录详细日志
            attack_log = {
                'attack_number': self.range_attack_stats['total_attacks'],
                'primary_target': target.name if hasattr(target, 'name') else target.type,
                'targets_damaged': targets_damaged,
                'total_targets_hit': len(targets_damaged),
                'is_range_attack': len(targets_damaged) > 1
            }
            self.range_attack_stats['range_damage_logs'].append(attack_log)

            # 输出详细伤害信息
            for target_info in targets_damaged:
                game_logger.info(
                    f"[RANGE DEBUG]   - {target_info['target']}: {target_info['damage']}伤害 ({target_info['health_before']} -> {target_info['health_after']})")

            return result

        # 替换攻击方法
        self.arrow_tower.attack_target = logged_attack_target

        # 注意：高级区域伤害系统已被移除，不再需要拦截
        game_logger.info("✅ 攻击日志拦截设置完成（高级区域伤害系统已移除）")

    def monitor_ammunition_reload(self):
        """监控弹药补充过程"""
        # 检查工程师是否被分配到箭塔
        if (self.engineer.target_building and
            hasattr(self.engineer.target_building, 'building_type') and
                self.engineer.target_building.building_type.value == 'arrow_tower'):

            if self.engineer.status.name == "RELOADING":
                # 检查是否是新开始的装填（避免重复计数）
                if not hasattr(self, '_reload_in_progress'):
                    self._reload_in_progress = True
                    self.ammunition_stats['reload_attempts'] += 1
                    game_logger.info(
                        f"🔄 工程师开始为箭塔补充弹药 (尝试 #{self.ammunition_stats['reload_attempts']})")

            elif self.engineer.status.name == "FETCHING_RESOURCES":
                game_logger.info(
                    f"💰 工程师前往地牢之心获取金币 (携带: {self.engineer.carried_gold})")

            elif self.engineer.status.name == "MOVING_TO_SITE":
                game_logger.info(f"🚶 工程师前往箭塔位置")

            elif self.engineer.status.name == "IDLE":
                # 重置装填进度标记
                if hasattr(self, '_reload_in_progress'):
                    delattr(self, '_reload_in_progress')

                # 检查是否需要分配工程师到箭塔
                # 工程师会自动通过建筑管理器找到需要装填的箭塔，无需手动分配
                if (self.arrow_tower.current_ammunition < self.arrow_tower.max_ammunition and
                        not self.engineer.target_building):
                    # 工程师会在下次update时自动通过建筑管理器找到需要装填的箭塔
                    game_logger.info(f"📋 工程师将在下次更新时自动寻找需要装填的箭塔")

        # 监控弹药变化来检测成功的装填
        if not hasattr(self, '_last_ammunition_count'):
            self._last_ammunition_count = self.arrow_tower.current_ammunition

        # 如果弹药增加了，说明装填成功
        if self.arrow_tower.current_ammunition > self._last_ammunition_count:
            ammo_increase = self.arrow_tower.current_ammunition - self._last_ammunition_count
            self.ammunition_stats['reload_successes'] += 1
            self.ammunition_stats['gold_spent'] += ammo_increase
            game_logger.info(f"✅ 检测到弹药补充成功: +{ammo_increase}发")
            self._last_ammunition_count = self.arrow_tower.current_ammunition

    def monitor_attack_timing(self):
        """监控箭塔攻击时间间隔"""
        current_time = time.time()

        # 检查箭塔是否刚完成攻击（通过弹药减少检测）
        if not hasattr(self, '_last_ammunition_count'):
            self._last_ammunition_count = self.arrow_tower.current_ammunition

        # 如果弹药减少了，说明箭塔刚攻击了
        if self.arrow_tower.current_ammunition < self._last_ammunition_count:
            self.attack_timing_stats['attacks_count'] += 1

            # 计算攻击间隔
            if self.attack_timing_stats['last_attack_time'] > 0:
                interval = current_time - \
                    self.attack_timing_stats['last_attack_time']
                self.attack_timing_stats['attack_intervals'].append(interval)

                # 检查是否违反1.5秒冷却时间（允许0.1秒误差）
                if interval < 1.4:  # 1.5 - 0.1 = 1.4秒
                    self.attack_timing_stats['cooldown_violations'] += 1
                    game_logger.info(f"⚠️ 箭塔攻击间隔过短: {interval:.3f}秒 (应该≥1.5秒)")
                else:
                    game_logger.info(f"✅ 箭塔攻击间隔正常: {interval:.3f}秒")

            self.attack_timing_stats['last_attack_time'] = current_time
            self._last_ammunition_count = self.arrow_tower.current_ammunition

    def run_ammunition_test(self):
        """运行弹药测试"""
        game_logger.info("🔫 开始箭塔弹药补充自动化测试")
        game_logger.info("=" * 60)
        game_logger.info("测试说明:")
        game_logger.info(
            f"- 地牢之心位置：瓦片坐标({self.dungeon_heart_tile_x}, {self.dungeon_heart_tile_y})，金币: {self.simulator.dungeon_heart.stored_gold if self.simulator.dungeon_heart else 0}")
        game_logger.info(
            f"- 箭塔位置：瓦片坐标({self.tower_tile_x}, {self.tower_tile_y})")
        game_logger.info(f"- 箭塔最大弹药：{self.arrow_tower.max_ammunition}发")
        game_logger.info(f"- 箭塔当前弹药：{self.arrow_tower.current_ammunition}发")
        game_logger.info(
            f"- 工程师位置：瓦片坐标({self.engineer_tile_x}, {self.engineer_tile_y})")
        game_logger.info("- 骑士会攻击箭塔，消耗弹药")
        game_logger.info("- 箭塔使用穿透范围攻击，可以同时命中多个目标")
        game_logger.info("- 工程师会自动为箭塔补充弹药")
        game_logger.info("- 测试将持续60秒，完全自动化运行")
        game_logger.info("- 按 ESC 键或关闭窗口可提前退出测试")
        game_logger.info("=" * 60)

        self.start_time = time.time()

        # 使用模拟器的运行循环
        try:
            while (time.time() - self.start_time) < self.test_duration:
                # 处理事件
                if not self.simulator.handle_events():
                    break

                # 更新游戏逻辑
                delta_time_ms = self.simulator.clock.tick(60)
                delta_time = delta_time_ms  # 传递毫秒给模拟器，模拟器内部会转换为秒

                self.simulator.update(delta_time)

                # 监控弹药补充逻辑
                self.monitor_ammunition_reload()

                # 监控攻击时间间隔
                self.monitor_attack_timing()

                # 渲染场景
                self.simulator.render()

        except KeyboardInterrupt:
            game_logger.info("\n⏹️ 测试被用户中断")

        # 输出测试结果
        self._log_test_results()

    def _log_test_results(self):
        """打印测试结果"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        game_logger.info("\n" + "=" * 60)
        game_logger.info("🏆 箭塔弹药补充逻辑测试结果")
        game_logger.info("=" * 60)
        game_logger.info(f"⏱️ 测试时间: {elapsed_time:.1f}秒")
        game_logger.info(
            f"🔫 弹药消耗次数: {self.ammunition_stats['ammunition_consumed']}")
        game_logger.info(
            f"🔄 弹药补充尝试次数: {self.ammunition_stats['reload_attempts']}")
        game_logger.info(
            f"✅ 弹药补充成功次数: {self.ammunition_stats['reload_successes']}")
        game_logger.info(
            f"👷 工程师分配次数: {self.ammunition_stats['engineer_assignments']}")
        game_logger.info(f"💰 消耗金币: {self.ammunition_stats['gold_spent']}")

        # 攻击时间间隔统计
        game_logger.info(f"\n🏹 箭塔攻击时间间隔统计:")
        game_logger.info(
            f"   总攻击次数: {self.attack_timing_stats['attacks_count']}")
        game_logger.info(
            f"   冷却时间违规次数: {self.attack_timing_stats['cooldown_violations']}")
        if self.attack_timing_stats['attack_intervals']:
            avg_interval = sum(self.attack_timing_stats['attack_intervals']) / len(
                self.attack_timing_stats['attack_intervals'])
            min_interval = min(self.attack_timing_stats['attack_intervals'])
            max_interval = max(self.attack_timing_stats['attack_intervals'])
            game_logger.info(f"   平均攻击间隔: {avg_interval:.3f}秒")
            game_logger.info(f"   最短攻击间隔: {min_interval:.3f}秒")
            game_logger.info(f"   最长攻击间隔: {max_interval:.3f}秒")
            game_logger.info(f"   预期间隔: 1.5秒")

        # 范围攻击统计
        game_logger.info(f"\n🎯 箭塔范围攻击统计:")
        game_logger.info(
            f"   总攻击次数: {self.range_attack_stats['total_attacks']}")
        game_logger.info(
            f"   范围攻击次数: {self.range_attack_stats['range_attacks']}")
        game_logger.info(
            f"   单目标攻击次数: {self.range_attack_stats['single_target_attacks']}")

        if self.range_attack_stats['total_attacks'] > 0:
            range_attack_rate = (
                self.range_attack_stats['range_attacks'] / self.range_attack_stats['total_attacks']) * 100
            game_logger.info(f"   范围攻击成功率: {range_attack_rate:.1f}%")

            if self.range_attack_stats['targets_hit_per_attack']:
                avg_targets = sum(self.range_attack_stats['targets_hit_per_attack']) / len(
                    self.range_attack_stats['targets_hit_per_attack'])
                max_targets = max(
                    self.range_attack_stats['targets_hit_per_attack'])
                game_logger.info(f"   平均命中目标数: {avg_targets:.1f}")
                game_logger.info(f"   最大命中目标数: {max_targets}")

        # 详细范围攻击日志
        if self.range_attack_stats['range_damage_logs']:
            game_logger.info(f"\n📋 范围攻击详细日志:")
            # 显示最后5次攻击
            for log in self.range_attack_stats['range_damage_logs'][-5:]:
                status = "✅ 范围攻击" if log['is_range_attack'] else "❌ 单目标"
                game_logger.info(
                    f"   攻击#{log['attack_number']}: {status} - 命中{log['total_targets_hit']}个目标")
                for target_info in log['targets_damaged']:
                    game_logger.info(
                        f"     - {target_info['target']}: {target_info['damage']}伤害")

        # 最终状态
        game_logger.info(f"\n📊 最终状态:")
        game_logger.info(
            f"   - 箭塔弹药: {self.arrow_tower.current_ammunition}/{self.arrow_tower.max_ammunition}")
        game_logger.info(
            f"   - 地牢之心金币: {self.simulator.dungeon_heart.stored_gold if self.simulator.dungeon_heart else 0}")
        game_logger.info(f"   - 工程师状态: {self.engineer.status}")
        game_logger.info(f"   - 工程师携带金币: {self.engineer.carried_gold}")

        # 测试结果评估
        if self.ammunition_stats['reload_successes'] > 0:
            game_logger.info(f"\n✅ 测试成功: 弹药补充逻辑正常工作")
            success_rate = (self.ammunition_stats['reload_successes'] / max(
                1, self.ammunition_stats['reload_attempts'])) * 100
            game_logger.info(f"   - 补充成功率: {success_rate:.1f}%")
        else:
            # 检查是否弹药确实被补充了（即使统计没有记录）
            if self.arrow_tower.current_ammunition > 0:
                game_logger.info(f"\n✅ 测试成功: 弹药补充逻辑正常工作（弹药已补充）")
                game_logger.info(
                    f"   - 最终弹药: {self.arrow_tower.current_ammunition}/{self.arrow_tower.max_ammunition}")
                game_logger.info(f"   - 注意: 统计系统可能需要调整")
            else:
                game_logger.info(f"\n❌ 测试失败: 弹药补充逻辑未正常工作")
                game_logger.info(f"   - 可能原因: 工程师未正确分配到箭塔")
                game_logger.info(f"   - 可能原因: 建筑管理器优先级问题")
                game_logger.info(f"   - 可能原因: 金币不足或工程师状态异常")

        # 获取模拟器统计信息
        simulator_stats = self.simulator.get_statistics()
        game_logger.info(f"\n📈 模拟器统计:")
        game_logger.info(f"   - 建筑数量: {simulator_stats['buildings_count']}")
        game_logger.info(f"   - 生物数量: {simulator_stats['creatures_count']}")
        game_logger.info(
            f"   - 模拟时间: {simulator_stats['simulation_time']:.1f}s")

        game_logger.info("=" * 60)

    def cleanup(self):
        """清理资源"""
        if hasattr(self.simulator, 'screen') and self.simulator.screen:
            pygame.quit()
        game_logger.info("🧹 资源清理完成")


def main():
    """主函数"""
    test = None
    try:
        test = ArrowTowerAmmunitionTest()
        test.run_ammunition_test()

    except Exception as e:
        game_logger.info(f"❌ 测试运行出错: {e}")
        traceback.print_exc()
    finally:
        if test:
            test.cleanup()


if __name__ == "__main__":
    main()
