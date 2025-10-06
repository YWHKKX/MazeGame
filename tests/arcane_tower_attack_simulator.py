#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奥术塔测试脚本
测试奥术塔的攻击、魔力消耗和范围攻击功能
"""

import sys
import os
import time
import pygame
import math
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
    from src.entities.building_types import ArcaneTower
    from src.utils.logger import game_logger
    from src.entities.building import BuildingType, BuildingConfig, BuildingCategory
    from src.entities.creature import Creature
    from src.core.constants import GameConstants
    from src.managers.movement_system import MovementSystem
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


# 不需要导入角色数据，直接使用字符串类型


class ArcaneTowerTest:
    """奥术塔测试类"""

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

        game_logger.info("奥术塔测试初始化完成")
        game_logger.info(f"UI放大倍数: {self.simulator.get_ui_scale()}x")
        game_logger.info("=" * 60)

        # 测试状态
        self.test_duration = 60.0  # 测试持续时间（秒）
        self.start_time = None
        self.mana_stats = {
            'mana_consumed': 0,
            'attacks_count': 0,
            'range_attacks': 0,
            'single_target_attacks': 0,
            'targets_hit_per_attack': [],
            'total_damage_dealt': 0
        }

        # 位置信息（用于显示）
        # 计算屏幕中心位置
        self.screen_center_x = int(self.simulator.screen_width // 2)   # 600
        self.screen_center_y = int(self.simulator.screen_height // 2)   # 400

        # 地牢之心位置：地图中心偏左区域 (30x20地图)
        self.dungeon_heart_tile_x = 6
        self.dungeon_heart_tile_y = 8

        # 奥术塔位置：地牢之心右侧，适当靠近
        self.tower_tile_x = 10
        self.tower_tile_y = 8

        # 设置测试场景
        self.setup_test_scenario()

        # 获取测试对象引用
        self.arcane_tower = None
        self.dungeon_heart = None
        self.test_creatures = []
        self._find_test_objects()

        # 初始化中文字体
        self._init_chinese_fonts()

    def _init_chinese_fonts(self):
        """初始化中文字体"""
        try:
            # 设置Windows编码
            if sys.platform == "win32":
                try:
                    locale.setlocale(locale.LC_ALL, 'Chinese_China.utf8')
                    game_logger.info("Windows编码设置完成")
                except:
                    try:
                        locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
                        game_logger.info("Windows编码设置完成")
                    except:
                        game_logger.info("无法设置Windows编码，使用默认编码")

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
                        game_logger.info(f"成功加载中文字体: {font_path}")
                        break
                    except Exception as e:
                        game_logger.info(f"字体加载失败 {font_path}: {e}")
                        continue

            if not self.chinese_font:
                # 如果都失败了，使用pygame默认字体
                self.chinese_font = pygame.font.Font(None, 24)
                game_logger.info("使用默认字体，中文可能显示为方块")

        except Exception as e:
            game_logger.info(f"字体初始化失败: {e}")
            self.chinese_font = pygame.font.Font(None, 24)

    def setup_test_scenario(self):
        """设置奥术塔测试场景"""

        # 挖掘测试区域 - 根据实际地图大小设置
        # 地图大小: 30x20 (1200//40 x 800//40)
        map_width = len(
            self.simulator.game_map[0]) if self.simulator.game_map else 30
        map_height = len(
            self.simulator.game_map) if self.simulator.game_map else 20

        game_logger.info(f"实际地图大小: {map_width}x{map_height}")
        game_logger.info(f"挖掘范围: x(3-{map_width-3}), y(3-{map_height-3})")

        for x in range(3, map_width - 3):  # 留出边界
            for y in range(3, map_height - 3):  # 留出边界
                if y < len(self.simulator.game_map) and x < len(self.simulator.game_map[y]):
                    self.simulator.game_map[y][x].is_dug = True

        # 创建地牢之心（500金币）
        self.simulator.create_dungeon_heart(
            self.dungeon_heart_tile_x, self.dungeon_heart_tile_y, 500)
        self.simulator.dungeon_heart_pos = (
            self.dungeon_heart_tile_x, self.dungeon_heart_tile_y)

        # 创建奥术塔 - 使用模拟器API
        self.simulator.create_arcane_tower(
            self.tower_tile_x, self.tower_tile_y)

        # 创建魔法祭坛（奥术塔左侧）
        magic_altar_tile_x = self.tower_tile_x - 2
        magic_altar_tile_y = self.tower_tile_y
        self.simulator.create_magic_altar(
            magic_altar_tile_x, magic_altar_tile_y,
            stored_gold=0, stored_mana=0, completed=True)

        # 创建地精工程师（奥术塔下方）
        engineer_tile_x = self.tower_tile_x
        engineer_tile_y = self.tower_tile_y + 2
        engineer_pixel_x = engineer_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        engineer_pixel_y = engineer_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        engineer = self.simulator.create_engineer(
            engineer_pixel_x, engineer_pixel_y)
        engineer.name = "奥术塔测试工程师"

        # 将地牢之心的魔力值设置为 0
        if hasattr(self.simulator, 'dungeon_heart') and self.simulator.dungeon_heart:
            self.simulator.dungeon_heart.stored_mana = 0
            game_logger.info(
                f"地牢之心魔力值已设置为: {self.simulator.dungeon_heart.stored_mana}")

        # 创建骑士用于测试攻击（放置在奥术塔攻击范围内）
        # 计算奥术塔的像素坐标
        tower_pixel_x = self.tower_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        tower_pixel_y = self.tower_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        # 骑士位置：确保在奥术塔攻击范围内
        # 骑士1：奥术塔右侧2个瓦片距离
        knight_pixel_x = tower_pixel_x + 80  # 奥术塔右侧80像素（2个瓦片）
        knight_pixel_y = tower_pixel_y

        # 使用模拟器API创建骑士
        knight = self.simulator.create_hero(
            knight_pixel_x, knight_pixel_y, 'knight')
        knight.name = "奥术塔测试骑士"
        knight.wander_enabled = False  # 禁用游荡，让骑士专注于攻击奥术塔
        knight.is_enemy = True  # 骑士应该是敌人，这样奥术塔才能攻击他们
        knight.faction = "heroes"

        # 骑士2：测试圆形范围攻击的多目标效果
        knight2_pixel_x = tower_pixel_x + 60  # 奥术塔右侧60像素，在圆形范围内
        knight2_pixel_y = tower_pixel_y + 40  # 稍微偏移40像素，在圆形攻击范围内

        knight2 = self.simulator.create_hero(
            knight2_pixel_x, knight2_pixel_y, 'knight')
        knight2.name = "圆形范围测试骑士2"
        knight2.wander_enabled = False  # 禁用游荡，让骑士专注于攻击奥术塔
        knight2.is_enemy = True  # 骑士应该是敌人，这样奥术塔才能攻击他们
        knight2.faction = "heroes"

        game_logger.info("奥术塔测试场景设置完成")
        game_logger.info(
            f"   - 地牢之心: 瓦片坐标({self.dungeon_heart_tile_x}, {self.dungeon_heart_tile_y}), 500金币, 0魔力")
        game_logger.info(
            f"   - 奥术塔: 瓦片坐标({self.tower_tile_x}, {self.tower_tile_y})")
        game_logger.info(
            f"   - 魔法祭坛: 瓦片坐标({magic_altar_tile_x}, {magic_altar_tile_y}), 100金币, 0魔力")
        game_logger.info(
            f"   - 地精工程师: 瓦片坐标({engineer_tile_x}, {engineer_tile_y})")
        game_logger.info(f"   - 骑士1: 像素坐标({knight_pixel_x}, {knight_pixel_y})")
        game_logger.info(
            f"   - 骑士2: 像素坐标({knight2_pixel_x}, {knight2_pixel_y})")

    def _find_test_objects(self):
        """查找测试对象 - 使用模拟器统一API"""
        # 查找奥术塔
        buildings = self.simulator.building_manager.buildings
        for building in buildings:
            if hasattr(building, 'building_type') and building.building_type.value == 'arcane_tower':
                self.arcane_tower = building
                break

        # 查找地牢之心
        for building in buildings:
            if hasattr(building, 'building_type') and building.building_type.value == 'dungeon_heart':
                self.dungeon_heart = building
                break

        # 查找骑士
        heroes = self.simulator.heroes
        knight_count = 0
        for hero in heroes:
            if hasattr(hero, 'type') and hero.type == 'knight':
                knight_count += 1
                self.test_creatures.append(hero)
                if knight_count == 1:
                    self.knight = hero  # 第一个骑士作为主要测试对象

                # 为所有骑士设置攻击目标
                if self.arcane_tower:
                    # 使用MovementSystem设置移动目标
                    MovementSystem.set_target(
                        hero, (self.arcane_tower.x, self.arcane_tower.y))

                    # 设置攻击目标
                    if hasattr(hero, 'add_to_attack_list'):
                        hero.add_to_attack_list(self.arcane_tower)
                        game_logger.info(
                            f"为骑士 {hero.name} 设置攻击目标: {self.arcane_tower.building_type.value}")

                # 只处理前两个骑士
                if knight_count >= 2:
                    break

        if not self.arcane_tower or not self.dungeon_heart:
            raise Exception("无法找到测试对象：奥术塔或地牢之心")

        game_logger.info(f"奥术塔测试场景设置完成")
        game_logger.info(
            f"   - 地牢之心瓦片坐标: ({self.dungeon_heart.tile_x}, {self.dungeon_heart.tile_y})")
        game_logger.info(
            f"   - 地牢之心像素坐标: ({self.dungeon_heart.x:.1f}, {self.dungeon_heart.y:.1f})px")
        game_logger.info(
            f"   - 地牢之心金币: {self.simulator.dungeon_heart.stored_gold if self.simulator.dungeon_heart else 0}")
        game_logger.info(
            f"   - 奥术塔瓦片坐标: ({self.arcane_tower.tile_x}, {self.arcane_tower.tile_y})")
        game_logger.info(
            f"   - 奥术塔像素坐标: ({self.arcane_tower.x:.1f}, {self.arcane_tower.y:.1f})px")
        game_logger.info(
            f"   - 奥术塔魔力消耗: {self.arcane_tower.mana_per_shot}点/攻击")
        game_logger.info(f"   - 奥术塔攻击范围: {self.arcane_tower.attack_range}")
        game_logger.info(f"   - 奥术塔攻击伤害: {self.arcane_tower.attack_damage}")
        game_logger.info(f"   - 奥术塔攻击间隔: {self.arcane_tower.attack_interval}秒")
        game_logger.info(f"   - 测试骑士数量: {len(self.test_creatures)}")

    def calculate_distance(self, x1, y1, x2, y2):
        """计算两点间距离"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def run_arcane_tower_test(self):
        """运行奥术塔测试"""
        game_logger.info("开始奥术塔自动化测试")
        game_logger.info("=" * 60)
        game_logger.info("测试说明:")
        game_logger.info(
            f"- 地牢之心位置：瓦片坐标({self.dungeon_heart_tile_x}, {self.dungeon_heart_tile_y})，金币: {self.simulator.dungeon_heart.stored_gold if self.simulator.dungeon_heart else 0}，魔力: 0")
        game_logger.info(
            f"- 奥术塔位置：瓦片坐标({self.tower_tile_x}, {self.tower_tile_y})")
        game_logger.info(
            f"- 魔法祭坛位置：瓦片坐标({self.tower_tile_x - 2}, {self.tower_tile_y})，提供魔力支持")
        game_logger.info(
            f"- 地精工程师位置：瓦片坐标({self.tower_tile_x}, {self.tower_tile_y + 2})")
        game_logger.info(f"- 奥术塔每次攻击消耗：{self.arcane_tower.mana_per_shot}点魔力")
        game_logger.info("- 骑士会攻击奥术塔，奥术塔会消耗魔力进行反击")
        game_logger.info("- 奥术塔使用圆形范围攻击，可以同时命中多个目标")
        game_logger.info("- 地精工程师可以修复建筑，魔法祭坛提供魔力支持")
        game_logger.info("- 测试将持续60秒，完全自动化运行")
        game_logger.info("- 按 ESC 键或关闭窗口可提前退出测试")
        game_logger.info("=" * 60)

        self.start_time = time.time()

        # 使用模拟器的运行循环
        try:
            while (time.time() - self.start_time) < self.test_duration:
                # 处理事件，检查是否需要退出
                should_continue = self.simulator.handle_events()
                if not should_continue:
                    game_logger.info("\n用户请求退出测试")
                    break

                # 更新游戏逻辑
                delta_time_ms = self.simulator.clock.tick(60)
                delta_time = delta_time_ms  # 传递毫秒给模拟器，模拟器内部会转换为秒

                # 更新游戏逻辑
                self.simulator.update(delta_time)

                # 监控奥术塔攻击
                self.monitor_arcane_tower_attacks()

                # 渲染场景
                self.simulator.render()

        except KeyboardInterrupt:
            game_logger.info("\n测试被用户中断")

        # 输出测试结果
        self._log_test_results()

    def monitor_arcane_tower_attacks(self):
        """监控奥术塔攻击"""
        # 监控地牢之心的魔力变化来检测攻击
        if not hasattr(self, '_last_dungeon_heart_mana'):
            if hasattr(self, 'dungeon_heart') and self.dungeon_heart:
                self._last_dungeon_heart_mana = self.dungeon_heart.stored_mana
            else:
                self._last_dungeon_heart_mana = 500  # 默认初始值

        # 如果地牢之心魔力减少了，说明奥术塔刚攻击了
        if hasattr(self, 'dungeon_heart') and self.dungeon_heart:
            current_mana = self.dungeon_heart.stored_mana
            if current_mana < self._last_dungeon_heart_mana:
                mana_consumed = self._last_dungeon_heart_mana - current_mana
                self.mana_stats['mana_consumed'] += mana_consumed
                self.mana_stats['attacks_count'] += 1
                game_logger.info(
                    f"🔮 检测到奥术塔攻击: 消耗{mana_consumed}点魔力，地牢之心剩余{current_mana}魔力")
                self._last_dungeon_heart_mana = current_mana

    def _log_test_results(self):
        """打印测试结果"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        game_logger.info("\n" + "=" * 60)
        game_logger.info("奥术塔功能测试结果")
        game_logger.info("=" * 60)
        game_logger.info(f"测试时间: {elapsed_time:.1f}秒")
        game_logger.info(f"魔力消耗: {self.mana_stats['mana_consumed']}")
        game_logger.info(f"攻击次数: {self.mana_stats['attacks_count']}")
        game_logger.info(f"圆形范围攻击次数: {self.mana_stats['range_attacks']}")
        game_logger.info(
            f"单目标攻击次数: {self.mana_stats['single_target_attacks']}")

        # 最终状态
        game_logger.info(f"\n最终状态:")
        if hasattr(self, 'dungeon_heart') and self.dungeon_heart:
            game_logger.info(f"   - 地牢之心魔力: {self.dungeon_heart.stored_mana}")

        # 查找魔法祭坛
        magic_altar = None
        for building in self.simulator.building_manager.buildings:
            if hasattr(building, 'building_type') and building.building_type.value == 'magic_altar':
                magic_altar = building
                break

        if magic_altar:
            game_logger.info(f"   - 魔法祭坛魔力: {magic_altar.stored_mana}")

        # 查找地精工程师
        engineer_count = 0
        for engineer in self.simulator.building_manager.engineers:
            if hasattr(engineer, 'name') and '奥术塔测试工程师' in engineer.name:
                engineer_count += 1
                game_logger.info(
                    f"   - 地精工程师血量: {engineer.health}/{engineer.max_health}")

        game_logger.info(f"   - 测试骑士数量: {len(self.test_creatures)}")
        for i, knight in enumerate(self.test_creatures):
            game_logger.info(
                f"   - 骑士{i+1}血量: {knight.health}/{knight.max_health}")

        game_logger.info("=" * 60)

    def cleanup(self):
        """清理资源"""
        if hasattr(self.simulator, 'screen') and self.simulator.screen:
            pygame.quit()
        game_logger.info("资源清理完成")


def main():
    """主函数"""
    test = None
    try:
        test = ArcaneTowerTest()
        test.run_arcane_tower_test()

    except Exception as e:
        game_logger.info(f"测试运行出错: {e}")
        traceback.print_exc()
    finally:
        if test:
            test.cleanup()


if __name__ == "__main__":
    main()
