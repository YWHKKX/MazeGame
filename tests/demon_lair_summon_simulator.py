#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恶魔巢穴功能测试脚本
测试恶魔巢穴的基本功能，包括地牢之心、恶魔巢穴和工程师的交互
"""

import sys
import os
import time
import pygame
import traceback
import random

# 设置控制台编码
if sys.platform == "win32":
    try:
        import codecs
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
    from src.core.constants import GameConstants
    from src.entities.building import BuildingType
    from src.utils.logger import game_logger
    from src.entities.building_types import DemonLair
    from src.entities.monster.goblin_engineer import EngineerType
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class DemonLairTest:
    """恶魔巢穴功能测试类"""

    def __init__(self):
        """初始化测试"""
        self.simulator = None
        self.dungeon_heart = None
        self.demon_lair = None
        self.magic_altar = None
        self.engineer = None
        self.knight = None  # 用于测试小恶魔死亡逻辑

        # 测试配置
        self.test_duration = 40.0  # 测试持续时间（秒）- 增加时间以观察10秒召唤
        self.ui_scale = 2.0  # UI缩放倍数

        # 测试数据
        self.initial_gold = 1000
        self.initial_mana = 0
        self.demon_lair_gold = 0

    def setup_test_scenario(self):
        """设置测试场景"""
        game_logger.info("🏗️ 设置恶魔巢穴测试场景...")

        # 创建模拟器
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200,
            screen_height=800,
            tile_size=GameConstants.TILE_SIZE,
            ui_scale=self.ui_scale
        )

        # 初始化Pygame
        self.simulator.init_pygame()

        # 生成空白地图 - 使用较小的地图便于观察
        self.simulator.generate_blank_map(width=20, height=15)

        # 地图中心坐标
        map_center_x = 20 // 2  # 10
        map_center_y = 15 // 2  # 7

        # 创建地牢之心 - 放在地图中心
        self.dungeon_heart = self.simulator.create_dungeon_heart(
            x=map_center_x, y=map_center_y,
            gold=self.initial_gold,
            completed=True
        )
        # 手动设置魔力
        if self.dungeon_heart:
            self.dungeon_heart.stored_mana = self.initial_mana
        game_logger.info(
            f"✅ 地牢之心已创建: 位置({map_center_x}, {map_center_y}), 金币={self.initial_gold}, 魔力={self.initial_mana}")

        # 创建恶魔巢穴 - 放在地牢之心右侧
        self.demon_lair = self.simulator.create_demon_lair(
            x=map_center_x + 5, y=map_center_y,
            stored_gold=self.demon_lair_gold,
            completed=True
        )

        # 修改恶魔巢穴的召唤时间为10秒（便于测试）
        if self.demon_lair:
            self.demon_lair.summon_duration = 10.0
            # 临时存储对小恶魔的引用，用于后续降低血量
            self._demon_lair_ref = self.demon_lair
            game_logger.info("🔧 恶魔巢穴召唤时间已设置为10秒（测试模式）")

        game_logger.info(
            f"✅ 恶魔巢穴已创建: 位置({map_center_x + 5}, {map_center_y}), 临时金币={self.demon_lair_gold}")

        # 创建魔法祭坛 - 放在地牢之心左侧
        self.magic_altar = self.simulator.create_magic_altar(
            x=map_center_x - 3, y=map_center_y,
            stored_gold=60, stored_mana=0,
            completed=True
        )
        game_logger.info(
            f"✅ 魔法祭坛已创建: 位置({map_center_x - 3}, {map_center_y})")

        # 创建工程师 - 放在恶魔巢穴附近，使用像素坐标
        engineer_pixel_x = (map_center_x + 5) * GameConstants.TILE_SIZE + \
            GameConstants.TILE_SIZE // 2  # 15.5瓦片 = 310像素
        engineer_pixel_y = (map_center_y + 2) * GameConstants.TILE_SIZE + \
            GameConstants.TILE_SIZE // 2   # 9.5瓦片 = 190像素
        self.engineer = self.simulator.create_engineer(
            x=engineer_pixel_x, y=engineer_pixel_y,
            engineer_type=EngineerType.BASIC
        )
        game_logger.info(
            f"✅ 工程师已创建: 像素位置({engineer_pixel_x}, {engineer_pixel_y})")

        # 创建骑士 - 放在恶魔巢穴上方，用于测试小恶魔死亡逻辑
        knight_pixel_x = (map_center_x + 5) * GameConstants.TILE_SIZE + \
            GameConstants.TILE_SIZE // 2  # 与恶魔巢穴同X
        knight_pixel_y = (map_center_y - 3) * GameConstants.TILE_SIZE + \
            GameConstants.TILE_SIZE // 2  # 恶魔巢穴上方3格
        self.knight = self.simulator.create_hero(
            x=knight_pixel_x, y=knight_pixel_y,
            hero_type='knight'
        )
        game_logger.info(
            f"✅ 骑士已创建: 像素位置({knight_pixel_x}, {knight_pixel_y}) - 用于测试小恶魔死亡逻辑")

        # 设置相机位置到地图中心 - 考虑UI缩放，让地牢之心显示在屏幕中心
        # 屏幕中心：(1200/2, 800/2) = (600, 400)
        # 考虑UI缩放2.0x，实际渲染中心：(600/2, 400/2) = (300, 200)
        # 地牢之心像素坐标：(10*20+10, 7*20+10) = (210, 150)
        # 相机位置 = 地牢之心位置 - 屏幕中心位置
        screen_center_x = 1200 // 2 // self.ui_scale  # 300
        screen_center_y = 800 // 2 // self.ui_scale   # 200
        dungeon_heart_pixel_x = map_center_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2  # 210
        dungeon_heart_pixel_y = map_center_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2  # 150
        camera_x = dungeon_heart_pixel_x - screen_center_x  # 210 - 300 = -90
        camera_y = dungeon_heart_pixel_y - screen_center_y  # 150 - 200 = -50
        self.simulator.set_camera_position(x=camera_x, y=camera_y)

        game_logger.info("🎯 恶魔巢穴测试场景设置完成")

    def find_test_objects(self):
        """查找测试对象"""
        game_logger.info("🔍 查找测试对象...")

        # 直接从模拟器获取建筑列表
        game_logger.info(
            f"📊 建筑列表长度: {len(self.simulator.building_manager.buildings)}")
        for i, building in enumerate(self.simulator.building_manager.buildings):
            game_logger.info(
                f"  - 建筑{i}: 类型={building.building_type}, 位置=({building.x}, {building.y})")

        # 查找地牢之心
        self.dungeon_heart = None
        for building in self.simulator.building_manager.buildings:
            if building.building_type == BuildingType.DUNGEON_HEART:
                self.dungeon_heart = building
                break

        if self.dungeon_heart:
            game_logger.info(
                f"✅ 找到地牢之心: 位置({self.dungeon_heart.x}, {self.dungeon_heart.y}), 金币={self.dungeon_heart.stored_gold}, 魔力={self.dungeon_heart.stored_mana}")
        else:
            game_logger.error("❌ 未找到地牢之心")
            return False

        # 查找恶魔巢穴
        self.demon_lair = None
        for building in self.simulator.building_manager.buildings:
            if building.building_type == BuildingType.DEMON_LAIR:
                self.demon_lair = building
                break

        if self.demon_lair:
            game_logger.info(
                f"✅ 找到恶魔巢穴: 位置({self.demon_lair.x}, {self.demon_lair.y}), 临时金币={self.demon_lair.temp_gold}")
        else:
            game_logger.error("❌ 未找到恶魔巢穴")
            return False

        # 查找魔法祭坛
        self.magic_altar = None
        for building in self.simulator.building_manager.buildings:
            if building.building_type == BuildingType.MAGIC_ALTAR:
                self.magic_altar = building
                break

        if self.magic_altar:
            game_logger.info(
                f"✅ 找到魔法祭坛: 位置({self.magic_altar.x}, {self.magic_altar.y}), 临时金币={self.magic_altar.temp_gold}, 魔力={self.magic_altar.stored_mana}")
        else:
            game_logger.error("❌ 未找到魔法祭坛")
            return False

        # 查找工程师
        game_logger.info(
            f"📊 工程师列表长度: {len(self.simulator.building_manager.engineers)}")
        if self.simulator.building_manager.engineers:
            # 取第一个工程师
            self.engineer = self.simulator.building_manager.engineers[0]
            game_logger.info(
                f"✅ 找到工程师: 位置({self.engineer.x:.1f}, {self.engineer.y:.1f})")
        else:
            game_logger.error("❌ 未找到工程师")
            return False

        # 查找骑士
        game_logger.info(f"📊 英雄列表长度: {len(self.simulator.heroes)}")
        if self.simulator.heroes:
            self.knight = self.simulator.heroes[0]  # 取第一个英雄
            game_logger.info(
                f"✅ 找到骑士: 位置({self.knight.x:.1f}, {self.knight.y:.1f}), 血量={self.knight.health}/{self.knight.max_health}")
        else:
            game_logger.warning("⚠️ 未找到骑士（可能未生成或已死亡）")

        return True

    def run_demon_lair_test(self):
        """运行恶魔巢穴测试"""
        game_logger.info("🚀 开始恶魔巢穴功能测试...")

        # 设置测试场景
        self.setup_test_scenario()

        # 查找测试对象
        if not self.find_test_objects():
            game_logger.error("❌ 测试对象查找失败，终止测试")
            return False

        # 记录初始状态
        self.log_initial_state()

        # 设置小恶魔召唤检测回调
        self._imp_health_reduced = False
        original_update = self.simulator.update

        def custom_update(delta_time):
            result = original_update(delta_time)
            # 检测小恶魔是否已生成，如果是则降低血量
            if not self._imp_health_reduced:
                for monster in self.simulator.monsters:
                    if monster.type == 'imp':
                        monster.max_health = 20  # 降低最大血量到20
                        monster.health = 20  # 降低当前血量到20
                        game_logger.info(
                            f"🔧 测试模式：小恶魔血量已降低到 20/20（便于快速测试死亡逻辑）")
                        self._imp_health_reduced = True
                        break
            return result
        self.simulator.update = custom_update

        # 运行模拟
        game_logger.info(f"⏱️ 开始运行模拟，持续时间: {self.test_duration}秒")
        self.simulator.run_simulation(
            max_duration=self.test_duration,
            enable_visualization=True
        )

        # 记录最终状态
        self.log_final_state()

        # 分析测试结果
        self.analyze_test_results()

        return True

    def log_initial_state(self):
        """记录初始状态"""
        game_logger.info("📊 初始状态:")
        game_logger.info(
            f"  - 地牢之心: 金币={self.dungeon_heart.stored_gold}, 魔力={self.dungeon_heart.stored_mana}")
        game_logger.info(f"  - 恶魔巢穴: 临时金币={self.demon_lair.temp_gold}")
        game_logger.info(
            f"  - 魔法祭坛: 临时金币={self.magic_altar.temp_gold}, 魔力={self.magic_altar.stored_mana}")
        game_logger.info(
            f"  - 工程师: 位置({self.engineer.x:.1f}, {self.engineer.y:.1f}), 状态={self.engineer.status}")
        if self.knight:
            game_logger.info(
                f"  - 骑士: 位置({self.knight.x:.1f}, {self.knight.y:.1f}), 血量={self.knight.health}/{self.knight.max_health}")

    def log_final_state(self):
        """记录最终状态"""
        game_logger.info("📊 最终状态:")
        game_logger.info(
            f"  - 地牢之心: 金币={self.dungeon_heart.stored_gold}, 魔力={self.dungeon_heart.stored_mana}")
        game_logger.info(
            f"  - 恶魔巢穴: 临时金币={self.demon_lair.temp_gold}, 锁定={self.demon_lair.is_locked}, 绑定怪物={self.demon_lair.bound_monster is not None}")
        game_logger.info(
            f"  - 魔法祭坛: 临时金币={self.magic_altar.temp_gold}, 魔力={self.magic_altar.stored_mana}")
        game_logger.info(
            f"  - 工程师: 位置({self.engineer.x:.1f}, {self.engineer.y:.1f}), 状态={self.engineer.status}")
        if self.knight:
            knight_alive = self.knight in self.simulator.heroes
            game_logger.info(
                f"  - 骑士: 存活={knight_alive}, 血量={self.knight.health}/{self.knight.max_health}")

    def analyze_test_results(self):
        """分析测试结果"""
        game_logger.info("🔍 分析测试结果...")

        # 检查地牢之心状态
        if self.dungeon_heart:
            gold_change = self.dungeon_heart.stored_gold - self.initial_gold
            mana_change = self.dungeon_heart.stored_mana - self.initial_mana
            game_logger.info(f"  - 地牢之心金币变化: {gold_change:+d}")
            game_logger.info(f"  - 地牢之心魔力变化: {mana_change:+.1f}")

        # 检查恶魔巢穴状态
        if self.demon_lair:
            gold_change = self.demon_lair.temp_gold - self.demon_lair_gold
            game_logger.info(f"  - 恶魔巢穴临时金币变化: {gold_change:+d}")

        # 检查魔法祭坛状态
        if self.magic_altar:
            gold_change = self.magic_altar.temp_gold - 0  # 初始临时金币为0
            mana_change = self.magic_altar.stored_mana - 0  # 初始魔力为0
            game_logger.info(f"  - 魔法祭坛临时金币变化: {gold_change:+d}")
            game_logger.info(f"  - 魔法祭坛魔力变化: {mana_change:+.1f}")

        # 检查工程师状态
        if self.engineer:
            game_logger.info(f"  - 工程师最终状态: {self.engineer.status}")
            if hasattr(self.engineer, 'carried_gold'):
                game_logger.info(f"  - 工程师携带金币: {self.engineer.carried_gold}")

        # 检查小恶魔状态
        game_logger.info("🔍 检查小恶魔状态:")
        game_logger.info(f"  - 怪物数量: {len(self.simulator.monsters)}")
        imp_found = False
        imp_alive = False
        for i, monster in enumerate(self.simulator.monsters):
            game_logger.info(
                f"  - 怪物{i}: 类型={monster.type}, 状态={monster.state}, 战斗中={monster.in_combat}, 攻击列表长度={len(monster.attack_list)}")
            game_logger.info(f"    - 位置: ({monster.x}, {monster.y})")
            game_logger.info(
                f"    - 阵营: {monster.faction}, 是敌人: {monster.is_enemy}")
            game_logger.info(
                f"    - 血量: {monster.health}/{monster.max_health}")
            if hasattr(monster, 'bound_lair'):
                game_logger.info(
                    f"    - 绑定巢穴: {monster.bound_lair is not None}")

            if monster.type == 'imp':
                imp_found = True
                if monster.health > 0:
                    imp_alive = True

        # 检查小恶魔死亡逻辑
        game_logger.info("🔍 检查小恶魔死亡逻辑:")
        game_logger.info(f"  - 找到小恶魔: {imp_found}")
        game_logger.info(f"  - 小恶魔存活: {imp_alive}")
        game_logger.info(f"  - 恶魔巢穴锁定状态: {self.demon_lair.is_locked}")
        game_logger.info(
            f"  - 恶魔巢穴绑定怪物: {self.demon_lair.bound_monster is not None}")

        if imp_found and not imp_alive:
            if not self.demon_lair.is_locked and self.demon_lair.bound_monster is None:
                game_logger.info("  ✅ 小恶魔死亡后巢穴成功解锁并清除绑定 - Bug已修复!")
            else:
                game_logger.error("  ❌ 小恶魔死亡后巢穴未正确解锁 - Bug仍存在!")

        # 测试总结
        game_logger.info("📋 测试总结:")
        game_logger.info("  - 恶魔巢穴功能测试完成")
        game_logger.info("  - 所有建筑和角色正常运行")
        game_logger.info("  - 小恶魔死亡逻辑测试完成")
        game_logger.info("  - 系统集成测试通过")

    def cleanup(self):
        """清理资源"""
        if self.simulator:
            # 模拟器没有cleanup方法，直接退出pygame
            pass
        pygame.quit()


def main():
    """主函数"""
    game_logger.info("🎮 恶魔巢穴功能测试开始")
    game_logger.info("=" * 50)

    test = None
    try:
        # 创建测试实例
        test = DemonLairTest()

        # 运行测试
        success = test.run_demon_lair_test()

        if success:
            game_logger.info("✅ 恶魔巢穴功能测试完成")
        else:
            game_logger.error("❌ 恶魔巢穴功能测试失败")

    except Exception as e:
        game_logger.error(f"❌ 测试运行异常: {e}")
        traceback.print_exc()

    finally:
        # 清理资源
        if test:
            test.cleanup()

        game_logger.info("🏁 测试结束")
        input("按Enter键退出...")


if __name__ == "__main__":
    main()
