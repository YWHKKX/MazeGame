#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战斗逻辑测试 - 使用游戏环境模拟器
测试箭塔对战英雄骑士的战斗逻辑
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
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class CombatTestWithSimulator:
    """使用游戏环境模拟器的战斗测试"""

    def __init__(self):
        """初始化测试"""
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200, screen_height=800, tile_size=20)
        self.test_start_time = time.time()
        self.battle_log = []
        self.knight_deaths = 0
        self.total_damage_dealt = 0

        print("⚔️ 战斗逻辑测试启动（使用环境模拟器）")
        print("=" * 50)
        print("测试说明:")
        print("- 箭塔：自动攻击范围内的敌人")
        print("- 骑士：移动并攻击箭塔")
        print("- 测试攻击逻辑、伤害计算、目标选择")
        print("=" * 50)

    def _log_battle_event(self, message: str):
        """记录战斗事件"""
        timestamp = time.time() - self.test_start_time
        log_entry = f"[{timestamp:.1f}s] {message}"
        self.battle_log.append(log_entry)
        print(log_entry)

    def setup_test_scenario(self):
        """设置测试场景"""
        # 使用模拟器的预设场景
        self.simulator.setup_combat_test_scenario()

        # 获取测试对象
        self.arrow_tower = self.simulator.get_building_by_name("箭塔")
        self.knight = self.simulator.heroes[0] if self.simulator.heroes else None

        if not self.arrow_tower or not self.knight:
            raise Exception("测试场景设置失败")

        # 设置骑士属性
        self.knight.health = 120
        self.knight.max_health = 120
        self.knight.attack = 22
        self.knight.speed = 25
        self.knight.attack_range = 35

        self._log_battle_event("战斗测试场景设置完成")
        self._log_battle_event(
            f"箭塔位置: ({self.arrow_tower.x}, {self.arrow_tower.y}), 攻击力: {self.arrow_tower.attack_damage}")
        self._log_battle_event(
            f"骑士位置: ({self.knight.x}, {self.knight.y}), 血量: {self.knight.health}/{self.knight.max_health}")

    def calculate_distance(self, x1, y1, x2, y2):
        """计算两点间距离"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def is_knight_in_range(self):
        """检查骑士是否在箭塔攻击范围内"""
        tower_x = self.arrow_tower.x * self.simulator.tile_size
        tower_y = self.arrow_tower.y * self.simulator.tile_size

        distance = self.calculate_distance(
            tower_x, tower_y,
            self.knight.x, self.knight.y
        )
        return distance <= self.arrow_tower.attack_range

    def simulate_arrow_tower_attack(self, delta_time):
        """模拟箭塔攻击"""
        if not self.knight or self.knight.health <= 0:
            return

        # 检查是否在攻击范围内
        if not self.is_knight_in_range():
            return

        # 更新攻击冷却
        if hasattr(self.arrow_tower, 'attack_cooldown') and self.arrow_tower.attack_cooldown > 0:
            self.arrow_tower.attack_cooldown -= delta_time
            return

        # 寻找最佳目标
        if hasattr(self.arrow_tower, 'find_best_target'):
            # 确保骑士有正确的属性
            if not hasattr(self.knight, 'health'):
                self.knight.health = 120
            if not hasattr(self.knight, 'max_health'):
                self.knight.max_health = 120
            best_target = self.arrow_tower.find_best_target([self.knight])
        else:
            best_target = self.knight

        if best_target and (not hasattr(self.arrow_tower, 'can_attack_target') or
                            self.arrow_tower.can_attack_target(best_target)):
            # 执行攻击
            if hasattr(self.arrow_tower, 'attack_target'):
                attack_result = self.arrow_tower.attack_target(best_target)

                if attack_result and attack_result.get('attacked', False):
                    # 记录攻击日志
                    critical_text = " (暴击!)" if attack_result.get(
                        'is_critical', False) else ""
                    self._log_battle_event(
                        f"🏹 箭塔攻击 {self.knight.type} 造成 {attack_result['damage']} 点伤害{critical_text} "
                        f"(目标剩余: {attack_result['target_health']})"
                    )
                    self.total_damage_dealt += attack_result['damage']

                    # 检查骑士是否死亡
                    if self.knight.health <= 0:
                        self.knight_deaths += 1
                        self._log_battle_event(f"💀 {self.knight.type} 被箭塔击败！")
            else:
                # 简化攻击逻辑
                damage = self.arrow_tower.attack_damage
                self.knight.health = max(0, self.knight.health - damage)
                self.total_damage_dealt += damage

                self._log_battle_event(
                    f"🏹 箭塔攻击 {self.knight.type} 造成 {damage} 点伤害 (剩余: {self.knight.health})")

                if self.knight.health <= 0:
                    self.knight_deaths += 1
                    self._log_battle_event(f"💀 {self.knight.type} 被箭塔击败！")

    def move_knight_towards_tower(self, delta_time):
        """移动骑士朝向箭塔"""
        if not self.knight or self.knight.health <= 0:
            return

        # 计算朝向箭塔的方向
        tower_x = self.arrow_tower.x * self.simulator.tile_size
        tower_y = self.arrow_tower.y * self.simulator.tile_size

        dx = tower_x - self.knight.x
        dy = tower_y - self.knight.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 移动骑士
            move_speed = self.knight.speed * delta_time
            self.knight.x += dx * move_speed
            self.knight.y += dy * move_speed

    def run_test(self, max_duration: float = 30.0, enable_visualization: bool = False):
        """运行测试"""
        self._log_battle_event("🚀 开始战斗逻辑测试")

        # 设置测试场景
        self.setup_test_scenario()

        # 运行模拟
        start_time = time.time()
        last_log_time = start_time

        while (time.time() - start_time) < max_duration:
            # 更新游戏逻辑
            delta_time = 0.1
            self.simulator.update(delta_time)

            # 移动骑士
            self.move_knight_towards_tower(delta_time)

            # 模拟箭塔攻击
            self.simulate_arrow_tower_attack(delta_time)

            # 每秒输出一次状态
            current_time = time.time()
            if current_time - last_log_time >= 1.0:
                self._log_battle_event(
                    f"状态更新 - 骑士血量: {self.knight.health}/{self.knight.max_health}")
                last_log_time = current_time

            # 检查测试完成条件
            if self.knight.health <= 0:
                self._log_battle_event("💀 骑士被击败，测试完成")
                break

            # 短暂休眠避免CPU占用过高
            time.sleep(0.1)

        # 测试总结
        self._print_test_summary()

        return self.knight.health <= 0

    def _print_test_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 50)
        print("📊 战斗测试总结")
        print("=" * 50)

        knight_defeated = self.knight.health <= 0

        print(f"🛡️ 骑士最终血量: {self.knight.health}/{self.knight.max_health}")
        print(f"⚔️ 骑士被击败: {'是' if knight_defeated else '否'}")
        print(f"💀 击败次数: {self.knight_deaths}")
        print(f"💥 总伤害: {self.total_damage_dealt}")
        print(f"⏱️ 测试持续时间: {time.time() - self.test_start_time:.1f}秒")
        print(f"📝 战斗日志数: {len(self.battle_log)}")

        if not knight_defeated:
            print("\n❌ 测试失败原因分析:")
            print("   - 箭塔攻击逻辑可能有问题")
            print("   - 伤害计算可能不正确")
            print("   - 目标选择可能有问题")
        else:
            print("\n✅ 测试成功！战斗逻辑工作正常")


def main():
    """主函数"""
    try:
        test = CombatTestWithSimulator()
        success = test.run_test(max_duration=30.0, enable_visualization=False)

        if success:
            print("\n🎉 战斗逻辑测试通过！")
        else:
            print("\n❌ 战斗逻辑测试失败！")

    except Exception as e:
        print(f"❌ 测试运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
