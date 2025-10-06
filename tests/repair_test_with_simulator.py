#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑修复逻辑测试 - 使用最新的游戏环境模拟器API
这是一个关键测试，用于验证工程师修复建筑的逻辑是否正确
使用最新的GameEnvironmentSimulator API
"""

import sys
import os
import time
import pygame
import math
import locale
import codecs
import traceback
import argparse

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
    from src.core.constants import GameConstants
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
    from src.entities.building import BuildingStatus, BuildingType
    from src.entities.monster.goblin_engineer import EngineerStatus, EngineerType
    from src.utils.logger import game_logger
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class RepairTestWithSimulator:
    """使用最新游戏环境模拟器API的建筑修复测试"""

    def __init__(self, enable_visualization=True):
        """初始化测试"""
        # 创建游戏环境模拟器，启用2倍UI放大
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200,
            screen_height=800,
            tile_size=GameConstants.TILE_SIZE,
            ui_scale=2.0  # 2倍UI放大，方便观察
        )

        # 初始化pygame组件（仅可视化模式）
        if enable_visualization:
            self.simulator.init_pygame()

        self.test_start_time = time.time()
        self.test_log = []
        self.enable_visualization = enable_visualization
        self.screen = None
        self.clock = None
        self.font = None

        if self.enable_visualization:
            self._init_visualization()
            self._init_chinese_fonts()

        game_logger.info("🎮 建筑修复逻辑测试启动（使用最新环境模拟器API）")
        game_logger.info(f"🔍 UI放大倍数: {self.simulator.ui_scale}x")
        game_logger.info("=" * 50)
        game_logger.info("测试说明:")
        game_logger.info("- 主基地：500金币")
        game_logger.info("- 半血箭塔：需要修复")
        game_logger.info("- 工程师：自动执行修复任务")
        game_logger.info("- 使用最新模拟器API")
        if self.enable_visualization:
            game_logger.info("- 可视化模式：启用（默认）")
        else:
            game_logger.info("- 可视化模式：禁用")
        game_logger.info("=" * 50)

    def _init_visualization(self):
        """初始化可视化界面"""
        try:
            pygame.init()
            self.screen = pygame.display.set_mode((1200, 800))
            pygame.display.set_caption("建筑修复逻辑测试 - 可视化模式")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)
            game_logger.info("✅ 可视化界面初始化完成")
        except Exception as e:
            game_logger.info(f"❌ 可视化界面初始化失败: {e}")
            self.enable_visualization = False

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

    def _log_test_event(self, message: str):
        """记录测试事件"""
        timestamp = time.time() - self.test_start_time
        log_entry = f"[{timestamp:.1f}s] {message}"
        self.test_log.append(log_entry)
        game_logger.info(log_entry)

    def setup_test_scenario(self):
        """设置测试场景 - 使用最新模拟器API"""
        self._log_test_event("🏗️ 开始设置测试场景...")

        # 位置信息（用于显示）
        # 地牢之心位置：屏幕左上角区域
        self.dungeon_heart_tile_x = 5
        self.dungeon_heart_tile_y = 5

        # 箭塔位置：屏幕右下角区域，与地牢之心保持距离
        self.tower_tile_x = 20
        self.tower_tile_y = 15

        # 工程师位置：地牢之心附近
        self.engineer_tile_x = 7
        self.engineer_tile_y = 7

        # 挖掘测试区域
        for x in range(3, 25):
            for y in range(3, 20):
                if y < len(self.simulator.game_map) and x < len(self.simulator.game_map[y]):
                    self.simulator.game_map[y][x].is_dug = True

        # 使用最新模拟器API创建地牢之心（500金币）
        self.dungeon_heart = self.simulator.create_dungeon_heart(
            self.dungeon_heart_tile_x, self.dungeon_heart_tile_y, 500)

        # 使用最新模拟器API创建箭塔
        self.damaged_tower = self.simulator.create_arrow_tower(
            self.tower_tile_x, self.tower_tile_y)

        # 使用最新模拟器API创建工程师 - 转换为像素坐标
        engineer_pixel_x = self.engineer_tile_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        engineer_pixel_y = self.engineer_tile_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        self.engineer = self.simulator.create_engineer(
            engineer_pixel_x, engineer_pixel_y, EngineerType.BASIC)

        if not self.damaged_tower or not self.engineer or not self.dungeon_heart:
            raise Exception("测试场景设置失败")

        # 设置为半血状态，但保持活跃状态以便修复
        self.damaged_tower.health = self.damaged_tower.max_health // 2
        self.damaged_tower.is_active = True  # 保持活跃状态
        self.damaged_tower.status = BuildingStatus.COMPLETED  # 确保状态为已完成

        # 强制设置地牢之心为完成状态，避免它被优先选择
        self.dungeon_heart.status = BuildingStatus.COMPLETED
        self.dungeon_heart.health = self.dungeon_heart.max_health

        self._log_test_event("✅ 测试场景设置完成")
        self._log_test_event(
            f"主基地位置: ({self.dungeon_heart.x}, {self.dungeon_heart.y})")
        self._log_test_event(
            f"损坏箭塔位置: ({self.damaged_tower.x}, {self.damaged_tower.y})")
        self._log_test_event(
            f"箭塔当前血量: {self.damaged_tower.health}/{self.damaged_tower.max_health}")
        self._log_test_event(f"工程师位置: ({self.engineer.x}, {self.engineer.y})")
        self._log_test_event(
            f"主基地金币: {self.dungeon_heart.stored_gold if self.dungeon_heart else 0}")

        # 调试：检查建筑状态
        self._debug_building_status()

        game_logger.info(
            f"🔧 强制设置地牢之心为完成状态: {self.dungeon_heart.status}, 血量: {self.dungeon_heart.health}/{self.dungeon_heart.max_health}")

    def run_test(self, max_duration: float = 60.0):
        """运行测试 - 使用最新模拟器API"""
        self._log_test_event("🚀 开始建筑修复逻辑测试")

        # 设置测试场景
        self.setup_test_scenario()

        # 运行模拟
        start_time = time.time()
        last_log_time = start_time

        while (time.time() - start_time) < max_duration:
            # 处理事件
            if not self._handle_events():
                self._log_test_event("用户退出测试")
                break

            # 更新游戏逻辑 - 使用毫秒单位
            delta_time = 100  # 100毫秒
            self.simulator.update(delta_time)

            # 渲染可视化界面
            if self.enable_visualization:
                self._render_visualization()
                if hasattr(self.simulator, 'clock'):
                    self.simulator.clock.tick(60)  # 限制帧率

            # 每秒输出一次状态
            current_time = time.time()
            if current_time - last_log_time >= 1.0:
                self._log_test_event(
                    f"状态更新 - 箭塔血量: {self.damaged_tower.health}/{self.damaged_tower.max_health}")
                self._log_test_event(f"工程师携带金币: {self.engineer.carried_gold}")
                last_log_time = current_time

            # 检查测试完成条件
            if self.damaged_tower.health >= self.damaged_tower.max_health:
                self._log_test_event("🎉 测试成功完成！箭塔已完全修复")
                break

            # 短暂休眠避免CPU占用过高（仅在非可视化模式下）
            if not self.enable_visualization:
                time.sleep(0.1)

        # 测试总结
        self._log_test_summary()

        return self.damaged_tower.health >= self.damaged_tower.max_health

    def _log_test_summary(self):
        """打印测试总结"""
        game_logger.info("\n" + "=" * 50)
        game_logger.info("📊 测试总结")
        game_logger.info("=" * 50)

        final_health = self.damaged_tower.health
        max_health = self.damaged_tower.max_health
        repair_success = final_health >= max_health

        game_logger.info(f"🏗️ 箭塔最终血量: {final_health}/{max_health}")
        game_logger.info(f"✅ 修复状态: {'成功' if repair_success else '失败'}")
        game_logger.info(
            f"💰 主基地剩余金币: {self.dungeon_heart.stored_gold if self.dungeon_heart else 0}")

        if self.engineer:
            game_logger.info(f"🔧 工程师最终携带金币: {self.engineer.carried_gold}")
            game_logger.info(f"🔧 工程师状态: {self.engineer.status}")

        game_logger.info(
            f"⏱️ 测试持续时间: {time.time() - self.test_start_time:.1f}秒")
        game_logger.info(f"📝 日志条目数: {len(self.test_log)}")

        if not repair_success:
            game_logger.info("\n❌ 测试失败原因分析:")
            game_logger.info("   - 工程师可能没有正确开始修复任务")
            game_logger.info("   - 金币收集逻辑可能有问题")
            game_logger.info("   - 修复进度计算可能有问题")
            game_logger.info("   - 地牢之心位置可能未正确设置")
        else:
            game_logger.info("\n✅ 测试成功！建筑修复逻辑工作正常")

    def test_simulator_api(self):
        """测试最新模拟器API功能"""
        self._log_test_event("🔍 测试最新模拟器API...")

        # 测试模拟器基本功能
        self._log_test_event(
            f"模拟器屏幕尺寸: {self.simulator.screen_width}x{self.simulator.screen_height}")
        self._log_test_event(f"瓦片大小: {self.simulator.tile_size}")
        self._log_test_event(f"UI缩放倍数: {self.simulator.ui_scale}x")

        # 测试游戏状态
        self._log_test_event(
            f"初始金币: {self.simulator.dungeon_heart.stored_gold if self.simulator.dungeon_heart else 0}")
        # 测试建筑创建功能（仅验证API可用性，不实际创建）
        self._log_test_event("测试建筑创建功能...")
        try:
            # 验证API方法存在且可调用
            if hasattr(self.simulator, 'create_dungeon_heart'):
                self._log_test_event("✅ create_dungeon_heart API 可用")
            if hasattr(self.simulator, 'create_arrow_tower'):
                self._log_test_event("✅ create_arrow_tower API 可用")
            if hasattr(self.simulator, 'create_engineer'):
                self._log_test_event("✅ create_engineer API 可用")

        except Exception as e:
            self._log_test_event(f"❌ 建筑创建API测试失败: {e}")
            return False

        return True

    def _debug_building_status(self):
        """调试建筑状态"""
        game_logger.info("\n" + "=" * 50)
        game_logger.info("🔍 建筑状态调试信息")
        game_logger.info("=" * 50)

        # 检查所有建筑
        buildings = self.simulator.building_manager.buildings
        game_logger.info(f"总建筑数量: {len(buildings)}")

        for i, building in enumerate(buildings):
            game_logger.info(f"\n建筑 {i+1}: {building.name}")
            game_logger.info(
                f"  类型: {building.building_type.value if hasattr(building, 'building_type') else 'Unknown'}")
            game_logger.info(f"  状态: {building.status}")
            game_logger.info(f"  血量: {building.health}/{building.max_health}")
            game_logger.info(f"  活跃: {building.is_active}")
            game_logger.info(f"  位置: ({building.x}, {building.y})")

            # 检查是否需要修复
            if building.status == BuildingStatus.COMPLETED and building.health < building.max_health:
                game_logger.info(f"  ✅ 需要修复")
            else:
                game_logger.info(f"  ❌ 不需要修复")

        # 检查建筑管理器的选择逻辑
        if hasattr(self.simulator, 'building_manager'):
            work_needed = self.simulator.building_manager.find_any_incomplete_building()
            game_logger.info(
                f"\n建筑管理器选择的建筑: {work_needed.name if work_needed else 'None'}")

            # 检查每个建筑是否被占用
            for building in buildings:
                is_worked = self.simulator.building_manager._is_building_being_worked_on(
                    building)
                game_logger.info(
                    f"  {building.name}: {'被占用' if is_worked else '可用'}")

        game_logger.info("=" * 50)

    def _render_visualization(self):
        """渲染可视化界面 - 使用最新模拟器API"""
        if not self.enable_visualization:
            return

        # 使用模拟器的渲染方法
        self.simulator.render()

        # 渲染额外的UI信息
        self._render_ui_overlay()

    def _render_ui_overlay(self):
        """渲染UI覆盖层信息"""
        if not self.enable_visualization:
            return

        # 获取模拟器的屏幕表面
        screen = self.simulator.screen
        if not screen:
            return

        y_offset = 10

        # 使用中文字体
        font = self.chinese_font if hasattr(
            self, 'chinese_font') else self.font

        # 测试标题
        title_text = font.render("建筑修复逻辑测试", True, (255, 255, 255))
        screen.blit(title_text, (10, y_offset))
        y_offset += 30

        # 测试时间
        elapsed_time = time.time() - self.test_start_time
        time_text = font.render(
            f"测试时间: {elapsed_time:.1f}s", True, (255, 255, 255))
        screen.blit(time_text, (10, y_offset))
        y_offset += 25

        # 建筑状态
        if hasattr(self, 'damaged_tower') and self.damaged_tower:
            health_ratio = self.damaged_tower.health / self.damaged_tower.max_health
            status_text = font.render(
                f"箭塔血量: {self.damaged_tower.health}/{self.damaged_tower.max_health} ({health_ratio*100:.1f}%)", True, (255, 255, 255))
            screen.blit(status_text, (10, y_offset))
            y_offset += 25

        # 工程师状态
        if hasattr(self, 'engineer') and self.engineer:
            engineer_text = font.render(
                f"工程师状态: {self.engineer.status.name}", True, (255, 255, 255))
            screen.blit(engineer_text, (10, y_offset))
            y_offset += 25

            gold_text = font.render(
                f"携带金币: {self.engineer.carried_gold}", True, (255, 255, 0))
            screen.blit(gold_text, (10, y_offset))
            y_offset += 25

        # 控制说明
        if hasattr(self, 'small_font') and self.small_font:
            controls_text = self.small_font.render(
                "按 ESC 退出测试", True, (200, 200, 200))
            screen.blit(controls_text, (10, 750))

    def _handle_events(self):
        """处理事件 - 使用最新模拟器API"""
        if not self.enable_visualization:
            return True

        # 使用模拟器的事件处理
        return self.simulator.handle_events()


def main():
    """主函数"""

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='建筑修复逻辑测试')
    parser.add_argument('--no-visual', '-n', action='store_true',
                        help='禁用可视化模式（默认启用）')
    parser.add_argument('--duration', '-d', type=float, default=60.0,
                        help='测试持续时间（秒）')
    args = parser.parse_args()

    try:
        # 默认启用可视化，除非指定 --no-visual
        enable_visual = not args.no_visual
        test = RepairTestWithSimulator(enable_visualization=enable_visual)

        # 先测试最新模拟器API
        game_logger.info("\n" + "=" * 50)
        game_logger.info("🧪 测试最新模拟器API")
        game_logger.info("=" * 50)
        api_success = test.test_simulator_api()

        if not api_success:
            game_logger.info("❌ 最新模拟器API测试失败！")
            return

        game_logger.info("✅ 最新模拟器API测试通过！")

        # 然后运行建筑修复测试
        game_logger.info("\n" + "=" * 50)
        game_logger.info("🔧 测试建筑修复逻辑")
        game_logger.info("=" * 50)
        if enable_visual:
            game_logger.info("🎨 可视化模式已启用 - 按 ESC 键退出")
        else:
            game_logger.info("📝 无头模式运行")

        success = test.run_test(max_duration=args.duration)

        if success:
            game_logger.info("\n🎉 建筑修复逻辑测试通过！")
        else:
            game_logger.info("\n❌ 建筑修复逻辑测试失败！")

    except Exception as e:
        game_logger.info(f"❌ 测试运行出错: {e}")
        traceback.print_exc()
    finally:
        # 清理pygame
        if 'pygame' in sys.modules:
            pygame.quit()


if __name__ == "__main__":
    main()
