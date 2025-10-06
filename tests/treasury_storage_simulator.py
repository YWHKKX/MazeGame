#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金库存储测试脚本
测试金库的金币存储功能，包括苦工挖矿和存储到金库的完整流程
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
    from src.entities.building_types import Treasury
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class TreasuryStorageTest:
    """金库存储测试类"""

    def __init__(self):
        """初始化测试"""
        # 创建游戏环境模拟器，启用2倍UI放大
        # 明确指定地图大小，避免UI缩放影响地图大小计算
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200,
            screen_height=800,
            tile_size=GameConstants.TILE_SIZE,
            ui_scale=2.0,  # 2倍UI放大，方便观察
            map_width=30,  # 明确指定地图宽度
            map_height=20  # 明确指定地图高度
        )

        # 初始化pygame组件
        self.simulator.init_pygame()

        game_logger.info("金库存储测试初始化完成")
        game_logger.info(f"UI放大倍数: {self.simulator.get_ui_scale()}x")
        game_logger.info(
            f"地图大小: {self.simulator.map_width}x{self.simulator.map_height}")
        game_logger.info("=" * 60)

        # 测试状态
        self.test_duration = 60.0  # 测试持续时间（秒）
        self.start_time = None
        self.storage_stats = {
            'gold_mined': 0,
            'gold_stored': 0,
            'storage_operations': 0,
            'mining_operations': 0,
            'total_gold_in_treasury': 0
        }

        # 位置信息（用于显示）
        # 计算屏幕中心位置
        self.screen_center_x = int(self.simulator.screen_width // 2)   # 600
        self.screen_center_y = int(self.simulator.screen_height // 2)   # 400

        # 地牢之心位置：地图中心偏左区域 (30x20地图)
        self.dungeon_heart_tile_x = 6
        self.dungeon_heart_tile_y = 8

        # 金库位置：地牢之心右侧
        self.treasury_tile_x = 10
        self.treasury_tile_y = 8

        # 金矿位置：多个金矿分散分布
        self.gold_mines = [
            (14, 8),   # 金矿1：金库右侧
            (18, 12),  # 金矿2：右下方
            (20, 5),   # 金矿3：右上角
            (16, 15),  # 金矿4：右下角
        ]

        # 苦工位置：分散在各个金矿附近（4个苦工）
        self.worker_positions = [
            (16, 8),   # 苦工1：金矿1附近
            (17, 12),  # 苦工2：金矿2附近
            (19, 5),   # 苦工3：金矿3附近
            (15, 15),  # 苦工4：金矿4附近
        ]

        # 初始化苦工列表
        self.workers = []  # 改为多个苦工

        # 设置测试场景
        self.setup_test_scenario()

        # 获取测试对象引用
        self.treasury = None
        self.dungeon_heart = None
        self.gold_mine = None
        self._find_test_objects()

    def setup_test_scenario(self):
        """设置金库存储测试场景"""

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

        # 创建金库（初始存储0金币）
        self.simulator.create_treasury(
            self.treasury_tile_x, self.treasury_tile_y, stored_gold=0, completed=True)

        # 验证所有金矿位置是否在地图范围内
        for i, (mine_x, mine_y) in enumerate(self.gold_mines):
            if (mine_x >= self.simulator.map_width or mine_y >= self.simulator.map_height):
                game_logger.warning(
                    f"⚠️ 金矿{i+1}位置({mine_x}, {mine_y})超出地图范围({self.simulator.map_width}x{self.simulator.map_height})")
                # 调整金矿位置到地图范围内
                self.gold_mines[i] = (
                    min(mine_x, self.simulator.map_width - 1),
                    min(mine_y, self.simulator.map_height - 1)
                )
                game_logger.info(
                    f"📍 金矿{i+1}位置已调整为: {self.gold_mines[i]}")

        # 创建多个金矿（每个100金币） - 使用模拟器API
        for i, (mine_x, mine_y) in enumerate(self.gold_mines):
            self.simulator.add_gold_mine(mine_x, mine_y, gold_amount=100)
            game_logger.info(f"📍 金矿{i+1}位置: ({mine_x}, {mine_y}), 100金币")

        # 创建4个苦工（金矿附近不同位置）
        for i, (tile_x, tile_y) in enumerate(self.worker_positions):
            # 计算像素坐标，每个苦工位置略有偏移
            worker_pixel_x = tile_x * GameConstants.TILE_SIZE + \
                GameConstants.TILE_SIZE // 2 - 80 + (i * 20)
            worker_pixel_y = tile_y * GameConstants.TILE_SIZE + \
                GameConstants.TILE_SIZE // 2 + (i * 10)

            worker = self.simulator.create_worker(
                worker_pixel_x, worker_pixel_y)
            worker.name = f"金库存储测试苦工{i+1}"
            self.workers.append(worker)

        game_logger.info("金库存储测试场景设置完成")
        game_logger.info(
            f"   - 地牢之心: 瓦片坐标({self.dungeon_heart_tile_x}, {self.dungeon_heart_tile_y}), 500金币")
        game_logger.info(
            f"   - 金库: 瓦片坐标({self.treasury_tile_x}, {self.treasury_tile_y}), 0金币")
        # 显示所有金矿信息
        for i, (mine_x, mine_y) in enumerate(self.gold_mines):
            game_logger.info(f"   - 金矿{i+1}: 瓦片坐标({mine_x}, {mine_y}), 100金币")
        for i, (tile_x, tile_y) in enumerate(self.worker_positions):
            game_logger.info(f"   - 苦工{i+1}: 瓦片坐标({tile_x}, {tile_y})")

    def _find_test_objects(self):
        """查找测试对象 - 使用模拟器直接API"""
        # 使用模拟器的直接属性访问
        self.dungeon_heart = self.simulator.dungeon_heart
        self.treasury = self.simulator.treasury

        # 金矿在gold_mines列表中
        if self.simulator.gold_mines:
            self.gold_mine = self.simulator.gold_mines[0]  # 取第一个金矿
        else:
            self.gold_mine = None

        # 苦工在monsters列表中，通过名称查找
        self.workers = []
        for monster in self.simulator.monsters:
            if (hasattr(monster, 'name') and '金库存储测试苦工' in monster.name):
                self.workers.append(monster)

        if not self.treasury or not self.dungeon_heart or not self.gold_mine or len(self.workers) == 0:
            raise Exception("无法找到测试对象：金库、地牢之心、金矿或苦工")

        game_logger.info(f"金库存储测试场景设置完成")
        game_logger.info(
            f"   - 地牢之心瓦片坐标: ({self.dungeon_heart.tile_x}, {self.dungeon_heart.tile_y})")
        game_logger.info(
            f"   - 地牢之心像素坐标: ({self.dungeon_heart.x:.1f}, {self.dungeon_heart.y:.1f})px")
        game_logger.info(
            f"   - 地牢之心金币: {self.dungeon_heart.stored_gold}")
        game_logger.info(
            f"   - 金库瓦片坐标: ({self.treasury.tile_x}, {self.treasury.tile_y})")
        game_logger.info(
            f"   - 金库像素坐标: ({self.treasury.x:.1f}, {self.treasury.y:.1f})px")
        game_logger.info(
            f"   - 金库金币: {self.treasury.stored_gold}")
        game_logger.info(
            f"   - 金矿瓦片坐标: ({self.gold_mine.x}, {self.gold_mine.y})")
        game_logger.info(
            f"   - 金矿像素坐标: ({self.gold_mine.x * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2:.1f}, {self.gold_mine.y * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2:.1f})px")
        game_logger.info(
            f"   - 金矿金币: {self.gold_mine.gold_amount}")
        for i, worker in enumerate(self.workers):
            game_logger.info(
                f"   - 苦工{i+1}像素坐标: ({worker.x:.1f}, {worker.y:.1f})px")
            game_logger.info(f"   - 苦工{i+1}携带金币: {worker.carried_gold}")

    def run_treasury_storage_test(self):
        """运行金库存储测试"""
        game_logger.info("开始金库存储自动化测试")
        game_logger.info("=" * 60)
        game_logger.info("测试说明:")
        game_logger.info(
            f"- 地牢之心位置：瓦片坐标({self.dungeon_heart_tile_x}, {self.dungeon_heart_tile_y})，金币: {self.dungeon_heart.stored_gold}")
        game_logger.info(
            f"- 金库位置：瓦片坐标({self.treasury_tile_x}, {self.treasury_tile_y})，金币: {self.treasury.stored_gold}")
        # 显示所有金矿信息
        for i, (mine_x, mine_y) in enumerate(self.gold_mines):
            if i < len(self.simulator.gold_mines):
                mine = self.simulator.gold_mines[i]
                game_logger.info(
                    f"- 金矿{i+1}位置：瓦片坐标({mine_x}, {mine_y})，金币: {mine.gold_amount}")
        for i, worker in enumerate(self.workers):
            game_logger.info(
                f"- 苦工{i+1}位置：瓦片坐标({self.worker_positions[i][0]}, {self.worker_positions[i][1]})，携带金币: {worker.carried_gold}")
        game_logger.info("- 4个苦工会自动挖矿并将金币存储到金库")
        game_logger.info("- 测试金库的金币存储和检索功能")
        game_logger.info("- 使用最新的自动分配器API进行任务分配")
        game_logger.info("- 测试可达性系统和金矿任务创建")
        game_logger.info("- 测试将持续60秒，完全自动化运行")
        game_logger.info("- 按 ESC 键或关闭窗口可提前退出测试")
        game_logger.info("=" * 60)

        self.start_time = time.time()

        # 清理所有现有的任务分配
        game_logger.info("🧹 清理现有任务分配...")
        if hasattr(self.simulator, 'clear_all_assignments'):
            self.simulator.clear_all_assignments()
            game_logger.info("✅ 任务分配已清理")

        # 测试可达性系统
        game_logger.info("🗺️ 测试可达性系统...")
        if hasattr(self.simulator, 'update_reachability_system'):
            success = self.simulator.update_reachability_system()
            if success:
                game_logger.info("✅ 可达性系统测试成功")
            else:
                game_logger.warning("⚠️ 可达性系统测试失败")

        # 强制重新分配任务
        game_logger.info("🔄 强制重新分配任务...")
        if hasattr(self.simulator, 'force_reassign_all'):
            self.simulator.force_reassign_all()
            game_logger.info("✅ 任务重新分配完成")

        # 显示初始苦工状态
        game_logger.info("📊 初始苦工状态:")
        for i, worker in enumerate(self.workers):
            game_logger.info(f"   苦工{i+1}: 状态={getattr(worker, 'state', 'unknown')}, "
                             f"携带金币={worker.carried_gold}, "
                             f"位置=({worker.x:.1f}, {worker.y:.1f}), "
                             f"挖掘目标={getattr(worker, 'mining_target', None)}")

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

                # 监控金库存储
                self.monitor_treasury_storage()

                # 监控自动分配器状态
                self.monitor_assigner_status()

                # 渲染场景
                self.simulator.render()

        except KeyboardInterrupt:
            game_logger.info("\n测试被用户中断")

        # 输出测试结果
        self._log_test_results()

    def monitor_treasury_storage(self):
        """监控金库存储"""
        # 监控金库的金币变化
        if not hasattr(self, '_last_treasury_gold'):
            self._last_treasury_gold = self.treasury.stored_gold

        # 如果金库金币增加了，说明有存储操作
        current_treasury_gold = self.treasury.stored_gold
        if current_treasury_gold > self._last_treasury_gold:
            gold_stored = current_treasury_gold - self._last_treasury_gold
            self.storage_stats['gold_stored'] += gold_stored
            self.storage_stats['storage_operations'] += 1
            self.storage_stats['total_gold_in_treasury'] = current_treasury_gold
            game_logger.info(
                f"💰 检测到金库存储: 增加{gold_stored}金币，金库总金币{current_treasury_gold}")
            self._last_treasury_gold = current_treasury_gold

        # 监控所有苦工的金币变化
        if not hasattr(self, '_last_workers_gold'):
            self._last_workers_gold = [
                worker.carried_gold for worker in self.workers]

        # 检查每个苦工的金币变化
        for i, worker in enumerate(self.workers):
            current_worker_gold = worker.carried_gold
            last_worker_gold = self._last_workers_gold[i]

            if current_worker_gold < last_worker_gold:
                gold_used = last_worker_gold - current_worker_gold
                self.storage_stats['mining_operations'] += 1
                game_logger.info(
                    f"⛏️ 检测到苦工{i+1}操作: 使用{gold_used}金币，当前携带{current_worker_gold}金币")
                self._last_workers_gold[i] = current_worker_gold
            elif current_worker_gold > last_worker_gold:
                gold_mined = current_worker_gold - last_worker_gold
                self.storage_stats['gold_mined'] += gold_mined
                game_logger.info(
                    f"⛏️ 检测到苦工{i+1}挖矿: 获得{gold_mined}金币，当前携带{current_worker_gold}金币")
                self._last_workers_gold[i] = current_worker_gold

        # 定期显示苦工状态（每5秒一次）
        if not hasattr(self, '_last_worker_status_time'):
            self._last_worker_status_time = time.time()

        current_time = time.time()
        if current_time - self._last_worker_status_time >= 5.0:
            game_logger.info("📊 苦工状态报告:")
            for i, worker in enumerate(self.workers):
                game_logger.info(f"   苦工{i+1}: 状态={getattr(worker, 'state', 'unknown')}, "
                                 f"携带金币={worker.carried_gold}, "
                                 f"位置=({worker.x:.1f}, {worker.y:.1f}), "
                                 f"挖掘目标={getattr(worker, 'mining_target', None)}")
            self._last_worker_status_time = current_time

    def monitor_assigner_status(self):
        """监控自动分配器状态"""
        if not hasattr(self, '_last_assigner_check_time'):
            self._last_assigner_check_time = time.time()

        # 每5秒检查一次分配器状态
        current_time = time.time()
        if current_time - self._last_assigner_check_time >= 5.0:
            try:
                assigner_status = self.simulator.get_assignment_status()

                # 检查工程师分配器状态
                if assigner_status['engineer_assigner']['available']:
                    engineer_info = assigner_status['engineer_assigner']
                    game_logger.info(f"🔨 工程师分配器: 策略={engineer_info['strategy']}, "
                                     f"活跃任务={engineer_info['active_tasks']}, "
                                     f"已分配工程师={engineer_info['assigned_engineers']}")

                # 检查苦工分配器状态
                if assigner_status['worker_assigner']['available']:
                    worker_info = assigner_status['worker_assigner']
                    game_logger.info(f"⛏️ 苦工分配器: 策略={worker_info['strategy']}, "
                                     f"活跃任务={worker_info['active_tasks']}, "
                                     f"已分配苦工={worker_info['assigned_workers']}")

                self._last_assigner_check_time = current_time

            except Exception as e:
                game_logger.warning(f"⚠️ 监控自动分配器状态时出错: {e}")

    def _log_test_results(self):
        """打印测试结果"""
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        game_logger.info("\n" + "=" * 60)
        game_logger.info("金库存储功能测试结果")
        game_logger.info("=" * 60)
        game_logger.info(f"测试时间: {elapsed_time:.1f}秒")
        game_logger.info(f"苦工挖矿次数: {self.storage_stats['mining_operations']}")
        game_logger.info(f"金库存储次数: {self.storage_stats['storage_operations']}")
        game_logger.info(f"总挖矿金币: {self.storage_stats['gold_mined']}")
        game_logger.info(f"总存储金币: {self.storage_stats['gold_stored']}")

        # 最终状态
        game_logger.info(f"\n最终状态:")
        game_logger.info(f"   - 地牢之心金币: {self.dungeon_heart.stored_gold}")
        game_logger.info(f"   - 金库金币: {self.treasury.stored_gold}")
        # 显示所有金矿剩余金币
        for i, mine in enumerate(self.simulator.gold_mines):
            game_logger.info(f"   - 金矿{i+1}剩余金币: {mine.gold_amount}")
        for i, worker in enumerate(self.workers):
            game_logger.info(f"   - 苦工{i+1}携带金币: {worker.carried_gold}")

        # 计算效率
        if elapsed_time > 0:
            mining_rate = self.storage_stats['mining_operations'] / \
                elapsed_time
            storage_rate = self.storage_stats['storage_operations'] / elapsed_time
            game_logger.info(f"\n效率统计:")
        game_logger.info(f"   - 挖矿频率: {mining_rate:.2f}次/秒")
        game_logger.info(f"   - 存储频率: {storage_rate:.2f}次/秒")

        # 显示自动分配器最终状态
        try:
            final_assigner_status = self.simulator.get_assignment_status()
            game_logger.info(f"\n自动分配器最终状态:")
            if final_assigner_status['engineer_assigner']['available']:
                engineer_info = final_assigner_status['engineer_assigner']
                game_logger.info(f"   - 工程师分配器: 策略={engineer_info['strategy']}, "
                                 f"活跃任务={engineer_info['active_tasks']}, "
                                 f"已分配工程师={engineer_info['assigned_engineers']}")
            if final_assigner_status['worker_assigner']['available']:
                worker_info = final_assigner_status['worker_assigner']
                game_logger.info(f"   - 苦工分配器: 策略={worker_info['strategy']}, "
                                 f"活跃任务={worker_info['active_tasks']}, "
                                 f"已分配苦工={worker_info['assigned_workers']}")
        except Exception as e:
            game_logger.warning(f"⚠️ 获取自动分配器最终状态时出错: {e}")

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
        test = TreasuryStorageTest()
        test.run_treasury_storage_test()

    except Exception as e:
        game_logger.info(f"测试运行出错: {e}")
        traceback.print_exc()
    finally:
        if test:
            test.cleanup()


if __name__ == "__main__":
    main()
