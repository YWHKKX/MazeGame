#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑修复逻辑测试 - 使用游戏环境模拟器
这是一个关键测试，用于验证工程师修复建筑的逻辑是否正确
"""

import sys
import os
import time

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
    from src.entities.goblin_engineer import EngineerStatus
    from src.entities.building import BuildingStatus
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class RepairTestWithSimulator:
    """使用游戏环境模拟器的建筑修复测试"""

    def __init__(self):
        """初始化测试"""
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200, screen_height=800, tile_size=20)
        self.test_start_time = time.time()
        self.test_log = []

        print("🎮 建筑修复逻辑测试启动（使用环境模拟器）")
        print("=" * 50)
        print("测试说明:")
        print("- 主基地：500金币")
        print("- 半血箭塔：需要修复")
        print("- 工程师：自动执行修复任务")
        print("=" * 50)

    def _log_test_event(self, message: str):
        """记录测试事件"""
        timestamp = time.time() - self.test_start_time
        log_entry = f"[{timestamp:.1f}s] {message}"
        self.test_log.append(log_entry)
        print(log_entry)

    def setup_test_scenario(self):
        """设置测试场景"""
        # 使用模拟器的预设场景
        self.simulator.setup_repair_test_scenario()

        # 获取测试对象
        self.damaged_tower = self.simulator.get_building_by_name("箭塔")
        self.engineer = self.simulator.engineers[0] if self.simulator.engineers else None
        self.dungeon_heart = self.simulator.dungeon_heart

        if not self.damaged_tower or not self.engineer or not self.dungeon_heart:
            raise Exception("测试场景设置失败")

        self._log_test_event("测试场景设置完成")
        self._log_test_event(
            f"主基地位置: ({self.dungeon_heart.x}, {self.dungeon_heart.y})")
        self._log_test_event(
            f"损坏箭塔位置: ({self.damaged_tower.x}, {self.damaged_tower.y})")
        self._log_test_event(
            f"箭塔当前血量: {self.damaged_tower.health}/{self.damaged_tower.max_health}")
        self._log_test_event(f"工程师位置: ({self.engineer.x}, {self.engineer.y})")

    def run_test(self, max_duration: float = 60.0, enable_visualization: bool = False):
        """运行测试"""
        self._log_test_event("🚀 开始建筑修复逻辑测试")

        # 设置测试场景
        self.setup_test_scenario()

        # 运行模拟
        start_time = time.time()
        last_log_time = start_time

        while (time.time() - start_time) < max_duration:
            # 更新游戏逻辑
            delta_time = 0.1
            self.simulator.update(delta_time)

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

            # 短暂休眠避免CPU占用过高
            time.sleep(0.1)

        # 测试总结
        self._print_test_summary()

        return self.damaged_tower.health >= self.damaged_tower.max_health

    def _print_test_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 50)
        print("📊 测试总结")
        print("=" * 50)

        final_health = self.damaged_tower.health
        max_health = self.damaged_tower.max_health
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
    try:
        test = RepairTestWithSimulator()
        success = test.run_test(max_duration=60.0, enable_visualization=False)

        if success:
            print("\n🎉 建筑修复逻辑测试通过！")
        else:
            print("\n❌ 建筑修复逻辑测试失败！")

    except Exception as e:
        print(f"❌ 测试运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
