#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏环境模拟器
提供完整的游戏环境模拟，包括地图、建筑、角色、管理器等
用于测试各种游戏逻辑
"""

from src.core.constants import GameConstants
from src.managers.movement_system import MovementSystem
from src.managers.tile_manager import TileManager
from src.managers.building_manager import BuildingManager
from src.entities.creature import Creature
from src.entities.hero import Hero
from src.entities.goblin_worker import GoblinWorker
from src.entities.goblin_engineer import Engineer, EngineerType, EngineerConfig
from src.entities.building_types import ArrowTower, DungeonHeart, Treasury, Lair
from src.entities.building import Building, BuildingType, BuildingConfig, BuildingStatus, BuildingCategory
from src.core.enums import TileType
from src.core.game_state import GameState, Tile
from src.ui.building_ui import BuildingUI
import sys
import os
import time
import pygame
import math
import random
from typing import List, Dict, Any, Optional, Tuple

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class GameEnvironmentSimulator:
    """游戏环境模拟器 - 提供完整的游戏环境"""

    def __init__(self, screen_width: int = 1200, screen_height: int = 800, tile_size: int = 20):
        """
        初始化游戏环境模拟器

        Args:
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            tile_size: 瓦片大小
        """
        # 基础设置
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.tile_size = tile_size
        self.map_width = screen_width // tile_size
        self.map_height = screen_height // tile_size

        # 初始化Pygame（可选）
        self.pygame_initialized = False
        self.screen = None
        self.clock = None
        self.font = None
        self.small_font = None

        # 游戏状态
        self.game_state = GameState()

        # 管理器
        self.building_manager = BuildingManager()
        self.tile_manager = TileManager(tile_size)
        self.movement_system = MovementSystem()

        # UI管理器
        self.building_ui = None  # 延迟初始化
        self.font_manager = None  # 字体管理器

        # 地图数据
        self.game_map = self._create_map()

        # 游戏对象
        self.buildings = []  # 所有建筑
        self.engineers = []  # 所有工程师
        self.workers = []    # 所有工人
        self.heroes = []     # 所有英雄
        self.creatures = []  # 所有生物

        # 特殊建筑引用
        self.dungeon_heart = None
        self.treasury = None

        # 主基地位置（用于工程师寻找）
        self.dungeon_heart_pos = None

        # 模拟状态
        self.simulation_time = 0.0
        self.is_paused = False

        print("🎮 游戏环境模拟器初始化完成")
        print(f"   🗺️ 地图大小: {self.map_width}x{self.map_height}")
        print(f"   📐 瓦片大小: {self.tile_size}像素")

    def init_pygame(self):
        """初始化Pygame（用于可视化测试）"""
        if not self.pygame_initialized:
            pygame.init()
            self.screen = pygame.display.set_mode(
                (self.screen_width, self.screen_height))
            pygame.display.set_caption("游戏环境模拟器")
            self.clock = pygame.time.Clock()
            self.font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)

            from src.managers.font_manager import UnifiedFontManager
            self.font_manager = UnifiedFontManager()
            self.building_ui = BuildingUI(
                self.screen_width, self.screen_height, self.font_manager)

            self.pygame_initialized = True
            print("🎨 Pygame初始化完成")

    def _create_map(self) -> List[List[Tile]]:
        """创建游戏地图"""
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

        print(f"🗺️ 创建地图: {self.map_width}x{self.map_height}")
        return game_map

    def get_map_as_array(self) -> List[List[int]]:
        """获取地图作为2D数组，用于路径查找"""
        map_array = []
        for y in range(self.map_height):
            row = []
            for x in range(self.map_width):
                tile = self.game_map[y][x]
                # 0 = 可通行, 1 = 不可通行
                # 只有ROCK类型不可通行，其他都可通行
                if tile.tile_type == TileType.ROCK:
                    row.append(1)
                else:
                    row.append(0)
            map_array.append(row)
        return map_array

    # ==================== 建筑管理 ====================

    def create_dungeon_heart(self, x: int, y: int, gold: int = 500) -> DungeonHeart:
        """创建地牢之心（主基地）"""
        config = BuildingConfig(
            name="地牢之心",
            building_type=BuildingType.DUNGEON_HEART,
            category=BuildingCategory.INFRASTRUCTURE,
            cost_gold=0,
            cost_crystal=0,
            build_time=0,
            health=1000,
            armor=10,
            size=(2, 2)  # 2x2建筑
        )

        dungeon_heart = DungeonHeart(x, y, BuildingType.DUNGEON_HEART, config)
        dungeon_heart.gold = gold
        dungeon_heart.status = BuildingStatus.COMPLETED
        dungeon_heart.is_active = True

        self.buildings.append(dungeon_heart)
        self.building_manager.buildings.append(dungeon_heart)
        self.dungeon_heart = dungeon_heart

        # 设置主基地位置（用于工程师寻找）
        self.dungeon_heart_pos = (x, y)

        print(f"🏰 创建地牢之心: 位置({x}, {y}), 金币({gold})")
        return dungeon_heart

    def create_arrow_tower(self, x: int, y: int, health_ratio: float = 1.0) -> ArrowTower:
        """创建箭塔"""
        config = BuildingConfig(
            name="箭塔",
            building_type=BuildingType.ARROW_TOWER,
            category=BuildingCategory.MILITARY,
            cost_gold=100,
            cost_crystal=0,
            build_time=30,
            health=200,
            armor=5
        )

        arrow_tower = ArrowTower(x, y, BuildingType.ARROW_TOWER, config)

        # 设置血量
        if health_ratio < 1.0:
            arrow_tower.health = int(arrow_tower.max_health * health_ratio)
            arrow_tower.status = BuildingStatus.DAMAGED
            arrow_tower.is_active = False
        else:
            arrow_tower.status = BuildingStatus.COMPLETED
            arrow_tower.is_active = True

        self.buildings.append(arrow_tower)
        self.building_manager.buildings.append(arrow_tower)

        print(
            f"🏹 创建箭塔: 位置({x}, {y}), 血量({arrow_tower.health}/{arrow_tower.max_health})")
        return arrow_tower

    def create_treasury(self, x: int, y: int, stored_gold: int = 0) -> Treasury:
        """创建金库"""
        config = BuildingConfig(
            name="金库",
            building_type=BuildingType.TREASURY,
            category=BuildingCategory.INFRASTRUCTURE,
            cost_gold=50,
            cost_crystal=0,
            build_time=20,
            health=150,
            armor=3
        )

        treasury = Treasury(x, y, BuildingType.TREASURY, config)
        treasury.stored_gold = stored_gold
        treasury.status = BuildingStatus.COMPLETED
        treasury.is_active = True

        self.buildings.append(treasury)
        self.building_manager.buildings.append(treasury)
        self.treasury = treasury

        print(f"💰 创建金库: 位置({x}, {y}), 存储金币({stored_gold})")
        return treasury

    def create_lair(self, x: int, y: int) -> Lair:
        """创建巢穴"""
        config = BuildingConfig(
            name="巢穴",
            building_type=BuildingType.LAIR,
            category=BuildingCategory.INFRASTRUCTURE,
            cost_gold=30,
            cost_crystal=0,
            build_time=15,
            health=100,
            armor=2
        )

        lair = Lair(x, y, BuildingType.LAIR, config)
        lair.status = BuildingStatus.COMPLETED
        lair.is_active = True

        self.buildings.append(lair)
        self.building_manager.buildings.append(lair)

        print(f"🏠 创建巢穴: 位置({x}, {y})")
        return lair

    # ==================== 角色管理 ====================

    def create_engineer(self, x: float, y: float, engineer_type: EngineerType = EngineerType.BASIC) -> Engineer:
        """创建工程师"""
        config = EngineerConfig(
            name="工程师",
            engineer_type=engineer_type,
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
            description="基础工程师"
        )

        engineer = Engineer(x, y, engineer_type, config)
        engineer.carried_gold = 0

        # 设置游戏实例引用，让工程师能找到主基地
        engineer.game_instance = self

        self.engineers.append(engineer)
        self.building_manager.engineers.append(engineer)

        print(f"🔧 创建工程师: 位置({x}, {y}), 类型({engineer_type.value})")
        return engineer

    def create_worker(self, x: float, y: float) -> GoblinWorker:
        """创建工人"""
        worker = GoblinWorker(x, y)

        self.workers.append(worker)

        print(f"⛏️ 创建工人: 位置({x}, {y})")
        return worker

    def create_hero(self, x: float, y: float, hero_type: str = 'knight') -> Hero:
        """创建英雄"""
        hero = Hero(x, y, hero_type)

        self.heroes.append(hero)

        print(f"🛡️ 创建英雄: 位置({x}, {y}), 类型({hero_type})")
        return hero

    def create_creature(self, x: float, y: float, creature_type: str = 'goblin') -> Creature:
        """创建生物"""
        creature = Creature(x, y, creature_type)

        self.creatures.append(creature)

        print(f"👹 创建生物: 位置({x}, {y}), 类型({creature_type})")
        return creature

    # ==================== 游戏逻辑更新 ====================

    def update(self, delta_time: float):
        """更新游戏逻辑"""
        if self.is_paused:
            return

        self.simulation_time += delta_time

        # 获取地图数组用于路径查找
        map_array = self.get_map_as_array()

        # 更新建筑管理器
        building_updates = self.building_manager.update(
            delta_time, self.game_state, self.game_map)

        # 更新所有角色
        for engineer in self.engineers:
            if hasattr(engineer, 'update'):
                engineer.update(delta_time, map_array,
                                building_manager=self.building_manager)

        for worker in self.workers:
            if hasattr(worker, 'update'):
                worker.update(delta_time, map_array)

        for hero in self.heroes:
            if hasattr(hero, 'update'):
                hero.update(delta_time, self.creatures, map_array)

        for creature in self.creatures:
            if hasattr(creature, 'update'):
                creature.update(delta_time, self.game_state, map_array)

    # ==================== 测试场景预设 ====================

    def setup_repair_test_scenario(self):
        """设置建筑修复测试场景"""
        # 创建主基地
        self.create_dungeon_heart(10, 10, 500)

        # 创建半血箭塔
        damaged_tower = self.create_arrow_tower(25, 15, 0.5)
        self.building_manager.repair_queue.append(damaged_tower)

        # 创建工程师
        self.create_engineer(12, 12)

        print("🔧 建筑修复测试场景设置完成")

    def setup_combat_test_scenario(self):
        """设置战斗测试场景"""
        # 创建箭塔
        self.create_arrow_tower(15, 10)

        # 创建英雄骑士
        knight = self.create_hero(200, 200, 'knight')
        knight.health = 120
        knight.max_health = 120
        knight.attack = 22
        knight.speed = 25

        print("⚔️ 战斗测试场景设置完成")

    def setup_economy_test_scenario(self):
        """设置经济测试场景"""
        # 创建主基地
        self.create_dungeon_heart(10, 10, 1000)

        # 创建金库
        self.create_treasury(15, 10, 500)

        # 创建工人
        self.create_worker(12, 12)

        print("💰 经济测试场景设置完成")

    # ==================== 渲染系统 ====================

    def render(self):
        """渲染游戏画面"""
        if not self.pygame_initialized:
            return

        self.screen.fill((50, 50, 50))  # 深灰色背景

        # 绘制地图
        self._render_map()

        # 绘制建筑
        self._render_buildings()

        # 绘制角色
        self._render_characters()

        # 绘制UI
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
        for building in self.buildings:
            screen_x = building.x * self.tile_size
            screen_y = building.y * self.tile_size

            # 使用建筑对象自己的渲染方法，传递building_ui
            building.render(self.screen, screen_x, screen_y,
                            self.tile_size, self.font_manager, self.building_ui)

            # 渲染生命条
            building.render_health_bar(
                self.screen, screen_x, screen_y, self.tile_size, self.font_manager, self.building_ui)

    def _render_characters(self):
        """渲染角色"""
        # 渲染工程师
        for engineer in self.engineers:
            screen_x = int(engineer.x * self.tile_size)
            screen_y = int(engineer.y * self.tile_size)

            pygame.draw.circle(self.screen, (100, 100, 255),
                               (screen_x + self.tile_size // 2,
                                screen_y + self.tile_size // 2),
                               self.tile_size // 3)

            if engineer.carried_gold > 0:
                gold_text = self.small_font.render(
                    f"${engineer.carried_gold}", True, (255, 255, 0))
                self.screen.blit(gold_text, (screen_x, screen_y - 15))

        # 渲染工人
        for worker in self.workers:
            screen_x = int(worker.x * self.tile_size)
            screen_y = int(worker.y * self.tile_size)

            pygame.draw.circle(self.screen, (0, 255, 0),
                               (screen_x + self.tile_size // 2,
                                screen_y + self.tile_size // 2),
                               self.tile_size // 4)

        # 渲染英雄
        for hero in self.heroes:
            screen_x = int(hero.x)
            screen_y = int(hero.y)

            pygame.draw.circle(self.screen, (70, 130, 180),
                               (screen_x, screen_y), 15)
            pygame.draw.circle(self.screen, (50, 50, 50),
                               (screen_x, screen_y), 15, 2)

            # 绘制生命条
            if hasattr(hero, 'max_health') and hero.max_health > 0:
                bar_width = 40
                bar_height = 6
                bar_x = screen_x - bar_width // 2
                bar_y = screen_y - 25

                pygame.draw.rect(self.screen, (100, 0, 0),
                                 (bar_x, bar_y, bar_width, bar_height))

                health_ratio = hero.health / hero.max_health
                health_width = int(bar_width * health_ratio)
                health_color = (0, 255, 0) if health_ratio > 0.5 else (
                    255, 255, 0) if health_ratio > 0.25 else (255, 0, 0)
                pygame.draw.rect(self.screen, health_color,
                                 (bar_x, bar_y, health_width, bar_height))

    def _render_ui(self):
        """渲染UI信息"""
        y_offset = 10

        # 模拟时间
        time_text = self.font.render(
            f"模拟时间: {self.simulation_time:.1f}s", True, (255, 255, 255))
        self.screen.blit(time_text, (10, y_offset))
        y_offset += 30

        # 建筑数量
        building_text = self.font.render(
            f"建筑数量: {len(self.buildings)}", True, (255, 255, 255))
        self.screen.blit(building_text, (10, y_offset))
        y_offset += 25

        # 角色数量
        character_text = self.font.render(
            f"工程师: {len(self.engineers)}, 工人: {len(self.workers)}, 英雄: {len(self.heroes)}", True, (255, 255, 255))
        self.screen.blit(character_text, (10, y_offset))
        y_offset += 25

        # 主基地信息
        if self.dungeon_heart:
            heart_text = self.font.render(
                f"主基地金币: {self.dungeon_heart.gold}", True, (255, 255, 255))
            self.screen.blit(heart_text, (10, y_offset))
            y_offset += 25

    # ==================== 工具方法 ====================

    def get_building_at(self, x: int, y: int) -> Optional[Building]:
        """获取指定位置的建筑"""
        for building in self.buildings:
            if building.x == x and building.y == y:
                return building
        return None

    def get_engineer_at(self, x: float, y: float, tolerance: float = 1.0) -> Optional[Engineer]:
        """获取指定位置的工程师"""
        for engineer in self.engineers:
            if abs(engineer.x - x) <= tolerance and abs(engineer.y - y) <= tolerance:
                return engineer
        return None

    def pause(self):
        """暂停模拟"""
        self.is_paused = True
        print("⏸️ 模拟已暂停")

    def resume(self):
        """恢复模拟"""
        self.is_paused = False
        print("▶️ 模拟已恢复")

    def reset(self):
        """重置模拟环境"""
        self.simulation_time = 0.0
        self.is_paused = False

        # 清空所有对象
        self.buildings.clear()
        self.engineers.clear()
        self.workers.clear()
        self.heroes.clear()
        self.creatures.clear()

        # 重置管理器
        self.building_manager = BuildingManager()

        # 重置特殊引用
        self.dungeon_heart = None
        self.treasury = None

        print("🔄 模拟环境已重置")

    def get_statistics(self) -> Dict[str, Any]:
        """获取模拟统计信息"""
        return {
            'simulation_time': self.simulation_time,
            'buildings_count': len(self.buildings),
            'engineers_count': len(self.engineers),
            'workers_count': len(self.workers),
            'heroes_count': len(self.heroes),
            'creatures_count': len(self.creatures),
            'dungeon_heart_gold': self.dungeon_heart.gold if self.dungeon_heart else 0,
            'treasury_gold': self.treasury.stored_gold if self.treasury else 0,
            'total_gold': self.game_state.gold + (self.dungeon_heart.gold if self.dungeon_heart else 0) + (self.treasury.stored_gold if self.treasury else 0)
        }

    # ==================== 事件处理 ====================

    def handle_events(self):
        """处理Pygame事件"""
        if not self.pygame_initialized:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.is_paused = not self.is_paused
                    print("⏸️ 模拟已暂停" if self.is_paused else "▶️ 模拟已恢复")
                elif event.key == pygame.K_r:
                    self.reset()
                    print("🔄 模拟环境已重置")
        return True

    # ==================== 运行循环 ====================

    def run_simulation(self, max_duration: float = 60.0, enable_visualization: bool = True):
        """运行模拟"""
        if enable_visualization:
            self.init_pygame()
            print("🎮 开始可视化模拟")
        else:
            print("🎮 开始无头模拟")

        start_time = time.time()
        running = True

        while running and (time.time() - start_time) < max_duration:
            if enable_visualization:
                running = self.handle_events()
                if not running:
                    break

            # 更新游戏逻辑
            delta_time = 0.1 if not enable_visualization else self.clock.tick(
                60) / 1000.0
            self.update(delta_time)

            # 渲染（仅可视化模式）
            if enable_visualization:
                self.render()

        if enable_visualization:
            pygame.quit()
            self.pygame_initialized = False

        print(f"🏁 模拟结束，运行时间: {time.time() - start_time:.1f}秒")
        return self.get_statistics()

    # ==================== 测试辅助方法 ====================

    def wait_for_condition(self, condition_func, timeout: float = 10.0, check_interval: float = 0.1) -> bool:
        """等待某个条件满足"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(check_interval)
        return False

    def get_engineer_by_name(self, name: str) -> Optional[Engineer]:
        """根据名称获取工程师"""
        for engineer in self.engineers:
            if engineer.name == name:
                return engineer
        return None

    def get_building_by_name(self, name: str) -> Optional[Building]:
        """根据名称获取建筑"""
        for building in self.buildings:
            if building.name == name:
                return building
        return None

    def get_hero_by_name(self, name: str) -> Optional[Hero]:
        """根据名称获取英雄"""
        for hero in self.heroes:
            if hero.name == name:
                return hero
        return None

    def add_gold_to_dungeon_heart(self, amount: int):
        """向主基地添加金币"""
        if self.dungeon_heart:
            self.dungeon_heart.gold += amount
            print(f"💰 向主基地添加 {amount} 金币，当前金币: {self.dungeon_heart.gold}")

    def damage_building(self, building: Building, damage: int):
        """对建筑造成伤害"""
        if building:
            old_health = building.health
            building.health = max(0, building.health - damage)
            print(
                f"💥 {building.name} 受到 {damage} 点伤害: {old_health} -> {building.health}")

            if building.health <= 0:
                building.status = BuildingStatus.DESTROYED
                building.is_active = False
                print(f"💀 {building.name} 被摧毁！")
            elif building.health < building.max_health * 0.5:
                building.status = BuildingStatus.DAMAGED
                building.is_active = False
                print(f"🔧 {building.name} 需要修复！")

    def heal_building(self, building: Building, heal_amount: int):
        """治疗建筑"""
        if building:
            old_health = building.health
            building.health = min(building.max_health,
                                  building.health + heal_amount)
            print(
                f"💚 {building.name} 恢复 {heal_amount} 点生命值: {old_health} -> {building.health}")

            if building.health >= building.max_health * 0.5:
                building.status = BuildingStatus.COMPLETED
                building.is_active = True
                print(f"✅ {building.name} 已修复！")

    def move_character_to(self, character, target_x: float, target_y: float, speed: float = 30.0):
        """移动角色到指定位置"""
        if not character:
            return

        # 计算移动方向
        dx = target_x - character.x
        dy = target_y - character.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 移动角色
            move_distance = speed * 0.1  # 假设每帧0.1秒
            character.x += dx * move_distance
            character.y += dy * move_distance

    def set_character_position(self, character, x: float, y: float):
        """设置角色位置"""
        if character:
            character.x = x
            character.y = y
            print(
                f"📍 {character.name if hasattr(character, 'name') else '角色'} 移动到 ({x}, {y})")

    # ==================== 日志和调试 ====================

    def log_event(self, message: str):
        """记录事件日志"""
        timestamp = f"[{self.simulation_time:.1f}s]"
        print(f"{timestamp} {message}")

    def get_debug_info(self) -> Dict[str, Any]:
        """获取调试信息"""
        debug_info = {
            'simulation_time': self.simulation_time,
            'is_paused': self.is_paused,
            'pygame_initialized': self.pygame_initialized,
            'map_size': f"{self.map_width}x{self.map_height}",
            'tile_size': self.tile_size
        }

        # 建筑信息
        debug_info['buildings'] = []
        for building in self.buildings:
            debug_info['buildings'].append({
                'name': building.name,
                'type': building.building_type.value,
                'position': (building.x, building.y),
                'health': f"{building.health}/{building.max_health}",
                'status': building.status.value,
                'is_active': building.is_active
            })

        # 工程师信息
        debug_info['engineers'] = []
        for engineer in self.engineers:
            debug_info['engineers'].append({
                'name': engineer.name,
                'position': (engineer.x, engineer.y),
                'carried_gold': engineer.carried_gold,
                'status': engineer.status.value if hasattr(engineer, 'status') else 'unknown'
            })

        return debug_info

    def print_debug_info(self):
        """打印调试信息"""
        debug_info = self.get_debug_info()
        print("\n" + "=" * 50)
        print("🐛 调试信息")
        print("=" * 50)

        for key, value in debug_info.items():
            if key not in ['buildings', 'engineers']:
                print(f"{key}: {value}")

        print(f"\n建筑列表 ({len(debug_info['buildings'])}):")
        for building in debug_info['buildings']:
            print(
                f"  - {building['name']} ({building['type']}) at {building['position']} - {building['health']} HP")

        print(f"\n工程师列表 ({len(debug_info['engineers'])}):")
        for engineer in debug_info['engineers']:
            print(
                f"  - {engineer['name']} at {engineer['position']} - ${engineer['carried_gold']} gold")

        print("=" * 50)

    # ==================== 预设测试场景扩展 ====================

    def setup_complex_test_scenario(self):
        """设置复杂测试场景"""
        # 创建主基地
        self.create_dungeon_heart(5, 5, 1000)

        # 创建金库
        self.create_treasury(8, 5, 200)

        # 创建多个箭塔（不同状态）
        self.create_arrow_tower(15, 10)  # 完整箭塔
        self.create_arrow_tower(20, 15, 0.3)  # 严重损坏
        self.create_arrow_tower(25, 20, 0.7)  # 轻微损坏

        # 创建巢穴
        self.create_lair(12, 8)

        # 创建多个工程师
        self.create_engineer(6, 6)  # 靠近主基地
        self.create_engineer(10, 10)  # 中间位置

        # 创建工人
        self.create_worker(7, 7)

        # 创建英雄
        knight = self.create_hero(200, 200, 'knight')
        knight.health = 100
        knight.max_health = 100

        print("🏗️ 复杂测试场景设置完成")

    def setup_stress_test_scenario(self):
        """设置压力测试场景"""
        # 创建大量建筑
        for i in range(10):
            for j in range(10):
                if (i + j) % 3 == 0:  # 每3个位置创建一个建筑
                    self.create_arrow_tower(
                        i * 3, j * 3, random.uniform(0.3, 1.0))

        # 创建主基地
        self.create_dungeon_heart(15, 15, 5000)

        # 创建大量工程师
        for i in range(20):
            self.create_engineer(random.uniform(0, 30), random.uniform(0, 30))

        print("⚡ 压力测试场景设置完成")

    def __del__(self):
        """析构函数"""
        if self.pygame_initialized:
            pygame.quit()
