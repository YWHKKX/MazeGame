#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏模拟测试 - 建筑修复逻辑测试
这是一个关键测试文件，用于验证建筑修复逻辑的正确性
"""

import sys
import os
import time
import math

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
    from typing import List, Dict, Any, Optional, Tuple
    from src.core.game_state import GameState, Tile
    from src.core.enums import TileType
    from src.entities.building import Building, BuildingType, BuildingConfig, BuildingStatus, BuildingCategory
    from src.entities.building_types import ArrowTower, DungeonHeart
    from src.entities.goblin_engineer import Engineer, EngineerType, EngineerConfig
    from src.managers.building_manager import BuildingManager
    from src.managers.tile_manager import TileManager
    from src.core.constants import GameConstants
    import pygame
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class GameSimulationTest:
    """游戏模拟测试类 - 用于测试建筑修复逻辑"""

    def __init__(self):
        """初始化测试环境"""
        self.screen_width = 1200
        self.screen_height = 800
        self.tile_size = 20

        # 初始化Pygame
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height))
        pygame.display.set_caption("建筑修复逻辑测试 - 游戏模拟")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        # 游戏状态
        self.game_state = GameState()
        self.game_state.gold = 500  # 设置500金币

        # 管理器
        self.building_manager = BuildingManager()
        self.tile_manager = TileManager(self.tile_size)

        # 地图数据
        self.map_width = 60  # 60个瓦片宽
        self.map_height = 40  # 40个瓦片高
        self.game_map = self._create_test_map()

        # 测试对象
        self.dungeon_heart = None
        self.damaged_arrow_tower = None
        self.engineer = None

        # 测试状态
        self.test_start_time = time.time()
        self.test_phase = "初始化"
        self.test_log = []

        # 创建测试场景
        self._setup_test_scenario()

        print("🎮 游戏模拟测试初始化完成")
        print(f"   💰 主基地金币: {self.game_state.gold}")
        print(f"   🗺️ 地图大小: {self.map_width}x{self.map_height}")

    def _create_test_map(self) -> List[List[Tile]]:
        """创建测试地图"""
        game_map = []

        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                # 创建基础地面瓦片
                tile = self.tile_manager.create_tile(
                    x=x, y=y,
                    tile_type=TileType.GROUND,
                    is_gold_vein=False,
                    gold_amount=0
                )
                row.append(tile)
            game_map.append(row)

        print(f"🗺️ 创建测试地图: {self.map_width}x{self.map_height}")
        return game_map

    def _setup_test_scenario(self):
        """设置测试场景"""
        # 1. 创建主基地（地牢之心）- 500金币
        self.dungeon_heart = DungeonHeart(
            x=10, y=10,
            building_type=BuildingType.DUNGEON_HEART,
            config=BuildingConfig(
                name="主基地",
                building_type=BuildingType.DUNGEON_HEART,
                category=BuildingCategory.INFRASTRUCTURE,
                cost_gold=0,  # 主基地免费
                cost_crystal=0,
                build_time=0,
                health=1000,
                armor=10
            )
        )
        self.dungeon_heart.gold = 500  # 设置500金币
        self.building_manager.buildings.append(self.dungeon_heart)

        # 2. 创建半血的箭塔
        self.damaged_arrow_tower = ArrowTower(
            x=25, y=15,
            building_type=BuildingType.ARROW_TOWER,
            config=BuildingConfig(
                name="损坏的箭塔",
                building_type=BuildingType.ARROW_TOWER,
                category=BuildingCategory.MILITARY,
                cost_gold=100,
                cost_crystal=0,
                build_time=30,
                health=200,
                armor=5
            )
        )
        # 设置为半血状态
        self.damaged_arrow_tower.health = self.damaged_arrow_tower.max_health // 2
        self.damaged_arrow_tower.status = BuildingStatus.DAMAGED
        self.damaged_arrow_tower.is_active = False  # 损坏的建筑不活跃
        self.building_manager.buildings.append(self.damaged_arrow_tower)

        # 3. 创建工程师
        engineer_config = EngineerConfig(
            name="测试工程师",
            engineer_type=EngineerType.BASIC,
            cost=50,
            health=100,
            speed=30,
            build_efficiency=1.0,
            color=(100, 100, 255),
            size=15,
            level=1,
            max_concurrent_projects=1,
            repair_efficiency=1.0,
            upgrade_capability=False,
            special_abilities=[],
            description="测试用工程师"
        )
        self.engineer = Engineer(
            x=12, y=12,  # 靠近主基地
            engineer_type=EngineerType.BASIC,
            config=engineer_config
        )
        self.engineer.carried_gold = 0  # 初始没有携带金币
        self.building_manager.engineers.append(self.engineer)

        # 4. 将损坏的箭塔添加到修理队列
        self.building_manager.repair_queue.append(self.damaged_arrow_tower)

        self._log_test_event("测试场景设置完成")
        self._log_test_event(
            f"主基地位置: ({self.dungeon_heart.x}, {self.dungeon_heart.y})")
        self._log_test_event(
            f"损坏箭塔位置: ({self.damaged_arrow_tower.x}, {self.damaged_arrow_tower.y})")
        self._log_test_event(
            f"箭塔当前血量: {self.damaged_arrow_tower.health}/{self.damaged_arrow_tower.max_health}")
        self._log_test_event(f"工程师位置: ({self.engineer.x}, {self.engineer.y})")

    def _log_test_event(self, message: str):
        """记录测试事件"""
        timestamp = time.time() - self.test_start_time
        log_entry = f"[{timestamp:.1f}s] {message}"
        self.test_log.append(log_entry)
        print(log_entry)

    def update(self, delta_time: float):
        """更新游戏逻辑"""
        # 更新建筑管理器
        building_updates = self.building_manager.update(
            delta_time, self.game_state, self.game_map)

        # 检查工程师状态
        if self.engineer:
            if hasattr(self.engineer, 'current_task') and self.engineer.current_task:
                if self.engineer.current_task == "repairing":
                    self.test_phase = "工程师正在修复建筑"
                elif self.engineer.current_task == "collecting_gold":
                    self.test_phase = "工程师正在收集金币"
            else:
                self.test_phase = "工程师待命"

        # 检查箭塔修复状态
        if self.damaged_arrow_tower:
            if self.damaged_arrow_tower.health >= self.damaged_arrow_tower.max_health:
                if self.damaged_arrow_tower.status != BuildingStatus.COMPLETED:
                    self.damaged_arrow_tower.status = BuildingStatus.COMPLETED
                    self.damaged_arrow_tower.is_active = True
                    self._log_test_event("🎉 箭塔修复完成！")
                    self.test_phase = "测试完成 - 箭塔已修复"
            elif self.damaged_arrow_tower.health > self.damaged_arrow_tower.max_health // 2:
                self._log_test_event(
                    f"🔧 箭塔修复中: {self.damaged_arrow_tower.health}/{self.damaged_arrow_tower.max_health}")

    def render(self):
        """渲染游戏画面"""
        self.screen.fill((50, 50, 50))  # 深灰色背景

        # 绘制地图
        self._render_map()

        # 绘制建筑
        self._render_buildings()

        # 绘制工程师
        self._render_engineer()

        # 绘制UI信息
        self._render_ui()

        pygame.display.flip()

    def _render_map(self):
        """渲染地图瓦片"""
        for y in range(self.map_height):
            for x in range(self.map_width):
                tile = self.game_map[y][x]
                screen_x = x * self.tile_size
                screen_y = y * self.tile_size

                # 根据瓦片类型选择颜色
                if tile.tile_type == TileType.GROUND:
                    color = (100, 150, 100)  # 绿色地面
                elif tile.tile_type == TileType.WALL:
                    color = (80, 80, 80)     # 灰色墙壁
                else:
                    color = (120, 120, 120)  # 默认颜色

                pygame.draw.rect(self.screen, color,
                                 (screen_x, screen_y, self.tile_size, self.tile_size))
                pygame.draw.rect(self.screen, (60, 60, 60),
                                 (screen_x, screen_y, self.tile_size, self.tile_size), 1)

    def _render_buildings(self):
        """渲染建筑"""
        for building in self.building_manager.buildings:
            screen_x = building.x * self.tile_size
            screen_y = building.y * self.tile_size

            # 根据建筑类型选择颜色
            if building.building_type == BuildingType.DUNGEON_HEART:
                color = (200, 100, 100)  # 红色主基地
            elif building.building_type == BuildingType.ARROW_TOWER:
                # 根据血量选择颜色
                health_ratio = building.health / building.max_health
                if health_ratio >= 1.0:
                    color = (100, 200, 100)  # 绿色 - 完全健康
                elif health_ratio >= 0.5:
                    color = (200, 200, 100)  # 黄色 - 半血
                else:
                    color = (200, 100, 100)  # 红色 - 严重损坏
            else:
                color = (150, 150, 150)  # 默认灰色

            # 绘制建筑
            pygame.draw.rect(self.screen, color,
                             (screen_x, screen_y, self.tile_size * 2, self.tile_size * 2))
            pygame.draw.rect(self.screen, (255, 255, 255),
                             (screen_x, screen_y, self.tile_size * 2, self.tile_size * 2), 2)

            # 绘制血量条
            if building.max_health > 0:
                health_width = int(
                    (building.health / building.max_health) * (self.tile_size * 2))
                health_color = (100, 255, 100) if building.health >= building.max_health else (
                    255, 100, 100)
                pygame.draw.rect(self.screen, health_color,
                                 (screen_x, screen_y - 5, health_width, 3))

    def _render_engineer(self):
        """渲染工程师"""
        if self.engineer:
            screen_x = int(self.engineer.x * self.tile_size)
            screen_y = int(self.engineer.y * self.tile_size)

            # 绘制工程师（蓝色圆圈）
            pygame.draw.circle(self.screen, (100, 100, 255),
                               (screen_x + self.tile_size // 2,
                                screen_y + self.tile_size // 2),
                               self.tile_size // 3)

            # 绘制携带的金币数量
            if self.engineer.carried_gold > 0:
                gold_text = self.small_font.render(
                    f"${self.engineer.carried_gold}", True, (255, 255, 0))
                self.screen.blit(gold_text, (screen_x, screen_y - 15))

    def _render_ui(self):
        """渲染UI信息"""
        y_offset = 10

        # 测试阶段
        phase_text = self.font.render(
            f"测试阶段: {self.test_phase}", True, (255, 255, 255))
        self.screen.blit(phase_text, (10, y_offset))
        y_offset += 30

        # 主基地信息
        if self.dungeon_heart:
            heart_text = self.font.render(
                f"主基地金币: {self.dungeon_heart.gold}", True, (255, 255, 255))
            self.screen.blit(heart_text, (10, y_offset))
            y_offset += 25

        # 箭塔信息
        if self.damaged_arrow_tower:
            tower_text = self.font.render(
                f"箭塔血量: {self.damaged_arrow_tower.health}/{self.damaged_arrow_tower.max_health}",
                True, (255, 255, 255)
            )
            self.screen.blit(tower_text, (10, y_offset))
            y_offset += 25

            tower_status = self.font.render(
                f"箭塔状态: {self.damaged_arrow_tower.status.value}",
                True, (255, 255, 255)
            )
            self.screen.blit(tower_status, (10, y_offset))
            y_offset += 25

        # 工程师信息
        if self.engineer:
            engineer_text = self.font.render(
                f"工程师携带金币: {self.engineer.carried_gold}",
                True, (255, 255, 255)
            )
            self.screen.blit(engineer_text, (10, y_offset))
            y_offset += 25

            if hasattr(self.engineer, 'current_task') and self.engineer.current_task:
                task_text = self.font.render(
                    f"工程师任务: {self.engineer.current_task}",
                    True, (255, 255, 255)
                )
                self.screen.blit(task_text, (10, y_offset))
                y_offset += 25

        # 测试日志（显示最近5条）
        y_offset += 20
        log_title = self.font.render("测试日志:", True, (255, 255, 0))
        self.screen.blit(log_title, (10, y_offset))
        y_offset += 25

        recent_logs = self.test_log[-5:]  # 显示最近5条日志
        for log_entry in recent_logs:
            log_text = self.small_font.render(log_entry, True, (200, 200, 200))
            self.screen.blit(log_text, (10, y_offset))
            y_offset += 20

    def run_test(self, max_duration: float = 60.0):
        """运行测试"""
        print("🚀 开始建筑修复逻辑测试")
        print("=" * 50)

        running = True
        start_time = time.time()

        while running and (time.time() - start_time) < max_duration:
            # 处理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # 空格键手动触发工程师开始修复
                        if self.engineer and not hasattr(self.engineer, 'current_task'):
                            self.engineer.start_repair_task(
                                self.damaged_arrow_tower)
                            self._log_test_event("手动触发工程师开始修复任务")

            # 更新游戏逻辑
            delta_time = self.clock.tick(60) / 1000.0  # 转换为秒
            self.update(delta_time)

            # 渲染
            self.render()

            # 检查测试完成条件
            if (self.damaged_arrow_tower and
                    self.damaged_arrow_tower.health >= self.damaged_arrow_tower.max_health):
                self._log_test_event("🎉 测试成功完成！箭塔已完全修复")
                time.sleep(3)  # 显示3秒成功信息
                break

        # 测试总结
        self._print_test_summary()

        # 保持窗口打开直到用户关闭
        print("\n按ESC键或关闭窗口退出测试")
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            self.render()
            self.clock.tick(60)

        pygame.quit()

    def _print_test_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 50)
        print("📊 测试总结")
        print("=" * 50)

        if self.damaged_arrow_tower:
            final_health = self.damaged_arrow_tower.health
            max_health = self.damaged_arrow_tower.max_health
            repair_success = final_health >= max_health

            print(f"🏗️ 箭塔最终血量: {final_health}/{max_health}")
            print(f"✅ 修复状态: {'成功' if repair_success else '失败'}")
            print(
                f"💰 主基地剩余金币: {self.dungeon_heart.gold if self.dungeon_heart else 'N/A'}")

            if self.engineer:
                print(f"🔧 工程师最终携带金币: {self.engineer.carried_gold}")

        print(f"⏱️ 测试持续时间: {time.time() - self.test_start_time:.1f}秒")
        print(f"📝 日志条目数: {len(self.test_log)}")

        if not repair_success:
            print("\n❌ 测试失败原因分析:")
            print("   - 工程师可能没有正确开始修复任务")
            print("   - 金币收集逻辑可能有问题")
            print("   - 修复进度计算可能有问题")
        else:
            print("\n✅ 测试成功！建筑修复逻辑工作正常")


def main():
    """主函数"""
    print("🎮 建筑修复逻辑测试启动")
    print("=" * 50)
    print("测试说明:")
    print("- 红色建筑: 主基地（500金币）")
    print("- 黄色/红色建筑: 半血箭塔（需要修复）")
    print("- 蓝色圆圈: 工程师")
    print("- 按空格键手动触发修复")
    print("- 按ESC键退出测试")
    print("=" * 50)

    try:
        test = GameSimulationTest()
        test.run_test(max_duration=120.0)  # 最多运行2分钟
    except Exception as e:
        print(f"❌ 测试运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
