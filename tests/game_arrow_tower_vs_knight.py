#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
箭塔对战英雄骑士模拟测试 - 使用游戏环境模拟器
测试箭塔的攻击逻辑、伤害计算、目标选择等功能
"""

import sys
import os
import time
import math
import random

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
    import pygame
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class ArrowTowerSimulation:
    """箭塔对战模拟器 - 使用游戏环境模拟器"""

    def __init__(self):
        """初始化模拟器"""
        pygame.init()

        # 屏幕设置
        self.screen_width = 1200
        self.screen_height = 800
        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height))
        pygame.display.set_caption("箭塔对战英雄骑士模拟测试")

        # 字体设置
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)

        # 模拟参数
        self.tile_size = 40
        self.clock = pygame.time.Clock()
        self.running = True

        # 创建游戏环境模拟器
        self.simulator = GameEnvironmentSimulator(
            screen_width=self.screen_width,
            screen_height=self.screen_height,
            tile_size=self.tile_size
        )

        # 初始化pygame组件
        self.simulator.init_pygame()

        # 检查模拟器状态
        print(f"🔍 模拟器状态检查:")
        print(f"  - building_ui: {hasattr(self.simulator, 'building_ui')}")
        print(f"  - font_manager: {hasattr(self.simulator, 'font_manager')}")
        if hasattr(self.simulator, 'building_ui'):
            print(f"  - building_ui类型: {type(self.simulator.building_ui)}")
        if hasattr(self.simulator, 'font_manager'):
            print(f"  - font_manager类型: {type(self.simulator.font_manager)}")

        # 检查模拟器的其他属性
        print(
            f"  - 模拟器属性: {[attr for attr in dir(self.simulator) if not attr.startswith('_')]}")

        # 使用API创建箭塔
        self.arrow_tower = self.simulator.create_arrow_tower(15, 10)
        print(f"🔍 箭塔创建结果: {self.arrow_tower}")
        if self.arrow_tower:
            print(
                f"🔍 箭塔属性: 类型={getattr(self.arrow_tower, 'building_type', 'None')}, 位置=({self.arrow_tower.x}, {self.arrow_tower.y})")
            print(
                f"🔍 箭塔方法: render={hasattr(self.arrow_tower, 'render')}, render_health_bar={hasattr(self.arrow_tower, 'render_health_bar')}")

        # 创建骑士英雄
        self.knight = self.simulator.create_hero(200, 200, 'knight')

        if not self.arrow_tower or not self.knight:
            raise Exception("测试场景设置失败")

        # 设置骑士属性
        self.knight.health = 120
        self.knight.max_health = 120
        self.knight.attack = 22
        self.knight.speed = 25
        self.knight.attack_range = 35
        self.knight.name = "骑士"

        # 禁用英雄的漫游移动以避免移动系统问题
        self.knight.wander_enabled = False

        # 重写英雄的update方法以避免移动系统问题
        original_update = self.knight.update

        def safe_update(delta_time, creatures, game_map):
            # 只更新基本属性，跳过移动系统
            if hasattr(self.knight, 'health') and self.knight.health <= 0:
                return
            # 不调用原始的update方法，避免移动系统问题
        self.knight.update = safe_update

        # 模拟状态
        self.simulation_time = 0.0
        self.battle_log = []
        self.knight_deaths = 0
        self.total_damage_dealt = 0

        # 颜色定义
        self.colors = {
            'background': (50, 50, 50),
            'tower': (169, 169, 169),
            'knight': (70, 130, 180),
            'attack_range': (255, 255, 0, 50),
            'attack_line': (255, 0, 0),
            'text': (255, 255, 255),
            'damage_text': (255, 100, 100),
            'critical_text': (255, 0, 0)
        }

    def spawn_new_knight(self):
        """生成新的骑士"""
        # 在随机位置生成新骑士
        spawn_x = random.randint(50, self.screen_width - 50)
        spawn_y = random.randint(50, self.screen_height - 50)

        # 使用模拟器创建新骑士
        knight = self.simulator.create_hero(spawn_x, spawn_y, 'knight')
        knight.name = f"骑士#{self.knight_deaths + 1}"
        knight.health = 120
        knight.max_health = 120
        knight.attack = 22
        knight.speed = 25
        knight.attack_range = 35

        return knight

    def calculate_distance(self, x1, y1, x2, y2):
        """计算两点间距离"""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def is_knight_in_range(self):
        """检查骑士是否在箭塔攻击范围内"""
        # 将瓦片坐标转换为像素坐标
        tower_x = self.arrow_tower.x * self.tile_size + self.tile_size // 2
        tower_y = self.arrow_tower.y * self.tile_size + self.tile_size // 2

        distance = self.calculate_distance(
            tower_x, tower_y,
            self.knight.x, self.knight.y
        )
        return distance <= self.arrow_tower.attack_range

    def _trigger_arrow_tower_attack(self):
        """触发箭塔攻击逻辑（使用箭塔内置的攻击系统）"""
        if not self.knight or self.knight.health <= 0:
            return

        # 使用箭塔的内置攻击逻辑
        if hasattr(self.arrow_tower, 'find_best_target') and hasattr(self.arrow_tower, 'attack_target'):
            # 寻找最佳目标
            best_target = self.arrow_tower.find_best_target([self.knight])

            if best_target and self.arrow_tower.can_attack_target(best_target):
                # 执行攻击
                attack_result = self.arrow_tower.attack_target(best_target)

                if attack_result and attack_result.get('attacked', False):
                    # 记录攻击日志
                    critical_text = " (暴击!)" if attack_result.get(
                        'is_critical', False) else ""
                    log_entry = {
                        'time': self.simulation_time,
                        'damage': attack_result['damage'],
                        'is_critical': attack_result.get('is_critical', False),
                        'knight_health': attack_result['target_health'],
                        'message': f"🏹 箭塔攻击 {getattr(self.knight, 'name', '骑士')} 造成 {attack_result['damage']} 点伤害{critical_text} (目标剩余: {attack_result['target_health']})"
                    }
                    self.battle_log.append(log_entry)
                    self.total_damage_dealt += attack_result['damage']

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
                    log_entry = {
                        'time': self.simulation_time,
                        'damage': attack_result['damage'],
                        'is_critical': attack_result.get('is_critical', False),
                        'knight_health': attack_result['target_health'],
                        'message': f"🏹 箭塔攻击 {getattr(self.knight, 'name', '骑士')} 造成 {attack_result['damage']} 点伤害{critical_text} (目标剩余: {attack_result['target_health']})"
                    }
                    self.battle_log.append(log_entry)
                    self.total_damage_dealt += attack_result['damage']

                    # 检查骑士是否死亡
                    if self.knight.health <= 0:
                        self.knight_deaths += 1
                        death_log = {
                            'time': self.simulation_time,
                            'message': f"💀 {getattr(self.knight, 'name', '骑士')} 被箭塔击败！"
                        }
                        self.battle_log.append(death_log)

                        # 生成新骑士
                        self.knight = self.spawn_new_knight()
                        spawn_log = {
                            'time': self.simulation_time,
                            'message': f"🛡️ 新的{getattr(self.knight, 'name', '骑士')} 加入战斗！"
                        }
                        self.battle_log.append(spawn_log)
            else:
                # 简化攻击逻辑
                damage = self.arrow_tower.attack_damage
                self.knight.health = max(0, self.knight.health - damage)
                self.total_damage_dealt += damage

                log_entry = {
                    'time': self.simulation_time,
                    'damage': damage,
                    'is_critical': False,
                    'knight_health': self.knight.health,
                    'message': f"🏹 箭塔攻击 {getattr(self.knight, 'name', '骑士')} 造成 {damage} 点伤害 (目标剩余: {self.knight.health})"
                }
                self.battle_log.append(log_entry)

                if self.knight.health <= 0:
                    self.knight_deaths += 1
                    death_log = {
                        'time': self.simulation_time,
                        'message': f"💀 {getattr(self.knight, 'name', '骑士')} 被箭塔击败！"
                    }
                    self.battle_log.append(death_log)

                    # 生成新骑士
                    self.knight = self.spawn_new_knight()
                    spawn_log = {
                        'time': self.simulation_time,
                        'message': f"🛡️ 新的{getattr(self.knight, 'name', '骑士')} 加入战斗！"
                    }
                    self.battle_log.append(spawn_log)

    def move_knight_towards_tower(self, delta_time):
        """移动骑士朝向箭塔"""
        if not self.knight or self.knight.health <= 0:
            return

        # 计算朝向箭塔的方向
        tower_x = self.arrow_tower.x * self.tile_size + self.tile_size // 2
        tower_y = self.arrow_tower.y * self.tile_size + self.tile_size // 2

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

    def render(self):
        """渲染场景"""
        self.screen.fill(self.colors['background'])

        # 绘制箭塔
        self.draw_arrow_tower()

        # 绘制骑士
        self.draw_knight()

        # 绘制攻击范围
        self.draw_attack_range()

        # 绘制攻击线
        if self.is_knight_in_range() and self.knight.health > 0:
            self.draw_attack_line()

        # 绘制UI信息
        self.draw_ui()

        # 绘制战斗日志
        self.draw_battle_log()

        pygame.display.flip()

    def draw_arrow_tower(self):
        """绘制箭塔"""
        # 将瓦片坐标转换为像素坐标
        tower_x = self.arrow_tower.x * self.tile_size
        tower_y = self.arrow_tower.y * self.tile_size
        center_x = tower_x + self.tile_size // 2
        center_y = tower_y + self.tile_size // 2

        # 绘制塔身
        pygame.draw.rect(self.screen, self.colors['tower'],
                         (tower_x, tower_y, self.tile_size, self.tile_size))
        pygame.draw.rect(self.screen, (100, 100, 100),
                         (tower_x, tower_y, self.tile_size, self.tile_size), 2)

        # 绘制尖顶
        points = [
            (center_x, tower_y),
            (tower_x, tower_y + self.tile_size),
            (tower_x + self.tile_size, tower_y + self.tile_size)
        ]
        pygame.draw.polygon(self.screen, (105, 105, 105), points)

        # 绘制箭塔标签
        label = self.font.render("箭塔", True, self.colors['text'])
        self.screen.blit(label, (tower_x, tower_y - 25))

        # 尝试使用箭塔的内置渲染方法（只在第一次调用时输出调试信息）
        if not hasattr(self, '_tower_render_debug_done'):
            print(f"🔍 尝试使用箭塔内置渲染方法...")
            print(
                f"🔍 箭塔属性: 类型={getattr(self.arrow_tower, 'building_type', 'None')}")
            print(
                f"🔍 模拟器状态: building_ui={hasattr(self.simulator, 'building_ui')}, font_manager={hasattr(self.simulator, 'font_manager')}")
            self._tower_render_debug_done = True

        try:
            if hasattr(self.arrow_tower, 'render'):
                # 检查是否有building_ui和font_manager
                if hasattr(self.simulator, 'building_ui') and hasattr(self.simulator, 'font_manager'):
                    self.arrow_tower.render(self.screen, tower_x, tower_y, self.tile_size,
                                            self.simulator.font_manager, self.simulator.building_ui)
                else:
                    self.arrow_tower.render(
                        self.screen, tower_x, tower_y, self.tile_size)
        except Exception as e:
            if not hasattr(self, '_tower_render_error_shown'):
                print(f"❌ 箭塔内置渲染失败: {e}")
                import traceback
                traceback.print_exc()
                self._tower_render_error_shown = True

    def draw_knight(self):
        """绘制骑士"""
        if not self.knight or self.knight.health <= 0:
            return

        # 绘制骑士
        pygame.draw.circle(self.screen, self.colors['knight'],
                           (int(self.knight.x), int(self.knight.y)), 15)
        pygame.draw.circle(self.screen, (50, 50, 50),
                           (int(self.knight.x), int(self.knight.y)), 15, 2)

        # 绘制生命条
        bar_width = 40
        bar_height = 6
        bar_x = int(self.knight.x - bar_width // 2)
        bar_y = int(self.knight.y - 25)

        # 背景
        pygame.draw.rect(self.screen, (100, 0, 0),
                         (bar_x, bar_y, bar_width, bar_height))

        # 生命值
        health_ratio = self.knight.health / self.knight.max_health
        health_width = int(bar_width * health_ratio)
        health_color = (0, 255, 0) if health_ratio > 0.5 else (
            255, 255, 0) if health_ratio > 0.25 else (255, 0, 0)
        pygame.draw.rect(self.screen, health_color,
                         (bar_x, bar_y, health_width, bar_height))

        # 骑士标签
        knight_name = getattr(self.knight, 'name', '骑士')
        label = self.font.render(knight_name, True, self.colors['text'])
        self.screen.blit(
            label, (int(self.knight.x - 20), int(self.knight.y + 20)))

    def draw_attack_range(self):
        """绘制攻击范围"""
        # 将瓦片坐标转换为像素坐标
        tower_x = self.arrow_tower.x * self.tile_size + self.tile_size // 2
        tower_y = self.arrow_tower.y * self.tile_size + self.tile_size // 2

        # 绘制半透明圆圈表示攻击范围
        surface = pygame.Surface((self.arrow_tower.attack_range * 2,
                                  self.arrow_tower.attack_range * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface, self.colors['attack_range'],
                           (self.arrow_tower.attack_range,
                            self.arrow_tower.attack_range),
                           self.arrow_tower.attack_range)

        self.screen.blit(surface, (tower_x - self.arrow_tower.attack_range,
                                   tower_y - self.arrow_tower.attack_range))

    def draw_attack_line(self):
        """绘制攻击线"""
        if self.knight and self.knight.health > 0:
            # 将瓦片坐标转换为像素坐标
            tower_x = self.arrow_tower.x * self.tile_size + self.tile_size // 2
            tower_y = self.arrow_tower.y * self.tile_size + self.tile_size // 2

            pygame.draw.line(self.screen, self.colors['attack_line'],
                             (tower_x, tower_y),
                             (int(self.knight.x), int(self.knight.y)), 2)

    def draw_ui(self):
        """绘制UI信息"""
        y_offset = 10

        # 箭塔信息
        tower_info = [
            f"箭塔攻击力: {self.arrow_tower.attack_damage}",
            f"攻击范围: {self.arrow_tower.attack_range}像素",
            f"攻击间隔: {self.arrow_tower.attack_interval}秒",
            f"暴击率: {int(self.arrow_tower.critical_chance * 100)}%",
            f"弹药类型: {self.arrow_tower.ammunition_type}"
        ]

        for info in tower_info:
            text = self.small_font.render(info, True, self.colors['text'])
            self.screen.blit(text, (10, y_offset))
            y_offset += 20

        # 骑士信息
        if self.knight and self.knight.health > 0:
            # 将瓦片坐标转换为像素坐标
            tower_x = self.arrow_tower.x * self.tile_size + self.tile_size // 2
            tower_y = self.arrow_tower.y * self.tile_size + self.tile_size // 2

            knight_info = [
                f"骑士生命值: {self.knight.health}/{self.knight.max_health}",
                f"骑士攻击力: {self.knight.attack}",
                f"骑士速度: {self.knight.speed}",
                f"距离箭塔: {int(self.calculate_distance(tower_x, tower_y, self.knight.x, self.knight.y))}像素"
            ]

            y_offset += 10
            for info in knight_info:
                text = self.small_font.render(info, True, self.colors['text'])
                self.screen.blit(text, (10, y_offset))
                y_offset += 20

        # 统计信息
        stats = [
            f"模拟时间: {self.simulation_time:.1f}秒",
            f"击败骑士数: {self.knight_deaths}",
            f"总伤害: {self.total_damage_dealt}",
            f"战斗日志数: {len(self.battle_log)}"
        ]

        y_offset += 10
        for stat in stats:
            text = self.small_font.render(stat, True, self.colors['text'])
            self.screen.blit(text, (10, y_offset))
            y_offset += 20

    def draw_battle_log(self):
        """绘制战斗日志"""
        log_x = self.screen_width - 400
        log_y = 10
        log_width = 380
        log_height = 300

        # 绘制日志背景
        pygame.draw.rect(self.screen, (30, 30, 30),
                         (log_x, log_y, log_width, log_height))
        pygame.draw.rect(self.screen, (100, 100, 100),
                         (log_x, log_y, log_width, log_height), 2)

        # 绘制日志标题
        title = self.font.render("战斗日志", True, self.colors['text'])
        self.screen.blit(title, (log_x + 10, log_y + 10))

        # 绘制最近的日志条目
        log_entries = self.battle_log[-15:]  # 只显示最近15条
        y_offset = log_y + 40

        for entry in log_entries:
            color = self.colors['critical_text'] if entry.get(
                'is_critical', False) else self.colors['text']
            text = self.small_font.render(entry['message'], True, color)

            # 如果文本太长，截断
            if text.get_width() > log_width - 20:
                text = self.small_font.render(
                    entry['message'][:50] + "...", True, color)

            self.screen.blit(text, (log_x + 10, y_offset))
            y_offset += 18

    def handle_events(self):
        """处理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    # 重置模拟
                    self.reset_simulation()
                elif event.key == pygame.K_SPACE:
                    # 暂停/继续
                    self.paused = not getattr(self, 'paused', False)

    def reset_simulation(self):
        """重置模拟"""
        self.simulation_time = 0.0
        self.battle_log = []
        self.knight_deaths = 0
        self.total_damage_dealt = 0

        # 重置模拟器
        self.simulator.reset()

        # 使用API重新创建箭塔
        self.arrow_tower = self.simulator.create_arrow_tower(15, 10)

        # 重新创建骑士英雄
        self.knight = self.simulator.create_hero(200, 200, 'knight')

        if self.knight:
            # 设置骑士属性
            self.knight.health = 120
            self.knight.max_health = 120
            self.knight.attack = 22
            self.knight.speed = 25
            self.knight.attack_range = 35
            self.knight.name = "骑士"

            # 禁用英雄的漫游移动以避免移动系统问题
            self.knight.wander_enabled = False

            # 重写英雄的update方法以避免移动系统问题
            original_update = self.knight.update

            def safe_update(delta_time, creatures, game_map):
                # 只更新基本属性，跳过移动系统
                if hasattr(self.knight, 'health') and self.knight.health <= 0:
                    return
                # 不调用原始的update方法，避免移动系统问题
            self.knight.update = safe_update

        if self.arrow_tower and hasattr(self.arrow_tower, 'attack_cooldown'):
            self.arrow_tower.attack_cooldown = 0
        if self.arrow_tower and hasattr(self.arrow_tower, 'current_target'):
            self.arrow_tower.current_target = None

    def run(self):
        """运行模拟"""
        print("🏹 箭塔对战英雄骑士模拟测试")
        print("=" * 50)
        print("控制说明:")
        print("- ESC: 退出模拟")
        print("- R: 重置模拟")
        print("- 空格: 暂停/继续")
        print("=" * 50)

        self.paused = False

        while self.running:
            delta_time = self.clock.tick(60) / 1000.0  # 转换为秒

            self.handle_events()

            if not self.paused:
                self.simulation_time += delta_time

                # 更新游戏环境模拟器（包含箭塔的自动攻击逻辑）
                self.simulator.update(delta_time)

                # 手动触发箭塔攻击逻辑（因为GameEnvironmentSimulator没有自动处理建筑攻击）
                self._trigger_arrow_tower_attack()

                # 移动骑士
                self.move_knight_towards_tower(delta_time)

                # 检查骑士是否死亡，如果死亡则生成新骑士
                if self.knight and self.knight.health <= 0:
                    self.knight_deaths += 1
                    death_log = {
                        'time': self.simulation_time,
                        'message': f"💀 {getattr(self.knight, 'name', '骑士')} 被箭塔击败！"
                    }
                    self.battle_log.append(death_log)

                    # 生成新骑士
                    self.knight = self.spawn_new_knight()
                    spawn_log = {
                        'time': self.simulation_time,
                        'message': f"🛡️ 新的{getattr(self.knight, 'name', '骑士')} 加入战斗！"
                    }
                    self.battle_log.append(spawn_log)

            self.render()

        pygame.quit()
        print("\n模拟结束!")
        print(f"总模拟时间: {self.simulation_time:.1f}秒")
        print(f"击败骑士数: {self.knight_deaths}")
        print(f"总伤害: {self.total_damage_dealt}")


def main():
    """主函数"""
    try:
        simulation = ArrowTowerSimulation()
        simulation.run()
    except Exception as e:
        print(f"❌ 模拟运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
