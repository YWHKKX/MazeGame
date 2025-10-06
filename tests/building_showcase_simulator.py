#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑展示模拟器
用于展示所有已支持建造的建筑类型及其UI效果
包括建筑外观、状态条、生命条、建造进度等

建筑状态系统说明：
- 未完成：建筑正在建造中或规划中
- 完成：建筑建造完成，生命值满，功能正常
- 需要修复：建筑已完成但生命值不满，需要工程师修复
- 摧毁：建筑生命值为0，被完全摧毁
- 特殊状态：建筑有特殊功能状态（如金库爆满、箭塔无弹药等）

注意：已移除损坏状态，简化了建筑状态管理逻辑
"""

import sys
import os
import time
import math
import random
import pygame
import traceback

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
    from src.entities.building import Building, BuildingType, BuildingRegistry, BuildingCategory, BuildingStatus
    from src.entities.building_types import ArrowTower, Treasury
    from src.ui.building_ui import BuildingUI
    from src.core.constants import GameConstants
    from src.utils.logger import game_logger
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


class BuildingShowcaseSimulator:
    """建筑展示模拟器 - 展示所有建筑类型"""

    def __init__(self):
        """初始化建筑展示模拟器"""
        # 创建游戏环境模拟器
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200,  # 增加屏幕宽度以容纳更多建筑
            screen_height=800,  # 增加屏幕高度以容纳更多建筑
            tile_size=GameConstants.TILE_SIZE,
            ui_scale=1.0,  # 使用原始UI缩放，避免地图变小
            map_width=80,   # 指定地图宽度（瓦片数量）
            map_height=60   # 指定地图高度（瓦片数量）
        )

        # 初始化pygame组件
        self.simulator.init_pygame()

        # 为建筑展示提供充足的初始资源
        # 创建地牢之心来提供资源（资源管理器从建筑中获取资源）
        self.dungeon_heart = self.simulator.create_dungeon_heart(
            0, 0, gold=10000, completed=True)
        if self.dungeon_heart:
            # 手动设置魔力
            self.dungeon_heart.stored_mana = 5000
            game_logger.info(
                f"💰 创建地牢之心提供资源: 金币={self.dungeon_heart.stored_gold}, 魔力={self.dungeon_heart.stored_mana}")
        else:
            game_logger.info("❌ 地牢之心创建失败，无法提供资源")

        # 检查建筑成本
        for building_type in [BuildingType.ARCANE_TOWER, BuildingType.ORC_LAIR, BuildingType.DEMON_LAIR]:
            config = BuildingRegistry.get_config(building_type)
            if config:
                game_logger.info(
                    f"🏗️ {config.name} 成本: 金币={config.cost_gold}, 魔力={config.cost_crystal}")
            else:
                game_logger.info(f"❌ 未找到建筑配置: {building_type}")

        # 检查资源管理器状态
        gold_info = self.simulator.resource_manager.get_total_gold()
        mana_info = self.simulator.resource_manager.get_total_mana()
        game_logger.info(
            f"💰 资源管理器状态: 金币={gold_info.available}/{gold_info.total}, 魔力={mana_info.available}/{mana_info.total}")
        game_logger.info(
            f"🏰 地牢之心状态: 金币={self.dungeon_heart.stored_gold if self.dungeon_heart else 0}, 魔力={self.dungeon_heart.stored_mana if self.dungeon_heart else 0}")

        # 获取字体管理器
        self.font_manager = self.simulator.font_manager
        if not self.font_manager:
            game_logger.info("字体管理器未初始化，使用默认字体")

        # 创建建筑UI管理器
        self.building_ui = BuildingUI(
            self.simulator.screen_width,
            self.simulator.screen_height,
            self.font_manager
        )
        if not self.building_ui:
            game_logger.info("建筑UI管理器创建失败")

        game_logger.info("建筑展示模拟器初始化完成")
        game_logger.info(
            f"屏幕大小: {self.simulator.screen_width}x{self.simulator.screen_height}")
        game_logger.info(
            f"地图大小: {self.simulator.map_width}x{self.simulator.map_height} 瓦片")
        game_logger.info(f"瓦片大小: {self.simulator.tile_size} 像素")
        game_logger.info(f"UI放大倍数: {self.simulator.get_ui_scale()}x")
        game_logger.info("=" * 60)

        # 建筑分类和配置
        self.building_categories = self._initialize_building_categories()

        # 当前展示状态
        self.current_category_index = 0
        self.current_building_index = 0

        # 建筑展示位置
        self.showcase_center_x = self.simulator.screen_width // 2
        self.showcase_center_y = self.simulator.screen_height // 2

        # 创建测试建筑
        self._create_test_buildings()

        # 初始化中文字体
        self._init_chinese_fonts()

    def _initialize_building_categories(self):
        """初始化建筑分类 - 按照建筑系统分类"""
        return {
            "1. 基础设施建筑": [
                ("treasury", "金库"),
            ],
            "2. 功能性建筑": [
                # ("training_room", "训练室"),
                # ("library", "图书馆"),
                # ("workshop", "工坊"),
            ],
            "3. 军事建筑": [
                # ("prison", "监狱"),
                # ("torture_chamber", "刑房"),
                ("arrow_tower", "箭塔"),
                ("arcane_tower", "奥术塔"),
                # ("defense_fortification", "防御工事"),
                ("orc_lair", "兽人巢穴"),
            ],
            "4. 魔法建筑": [
                ("magic_altar", "魔法祭坛"),
                # ("shadow_temple", "暗影神殿"),
                # ("magic_research_institute", "魔法研究院"),
                ("demon_lair", "恶魔巢穴"),
            ]
        }

    def _create_test_buildings(self):
        """创建测试建筑"""
        # 在屏幕中心创建一些测试建筑
        center_x = self.showcase_center_x
        center_y = self.showcase_center_y

        # 创建矩形排列的建筑位置
        building_positions = []

        # 矩形排列参数：每行一种状态，每列显示不同建筑
        # 注意：已移除损坏状态，现在建筑只有：未完成、完成、需要修复、摧毁、特殊状态
        building_types = [
            # BuildingType.DUNGEON_HEART,  # 地牢之心
            BuildingType.TREASURY,
            BuildingType.ARROW_TOWER,
            BuildingType.ARCANE_TOWER,  # 奥术塔
            BuildingType.MAGIC_ALTAR,
            # BuildingType.TRAINING_ROOM,
            # BuildingType.LIBRARY,
            # BuildingType.PRISON,
            BuildingType.ORC_LAIR,      # 兽人巢穴
            BuildingType.DEMON_LAIR,    # 恶魔巢穴
        ]

        building_states = [
            GameConstants.BUILDING_STATUS_INCOMPLETE,    # 第1行：未建造状态
            GameConstants.BUILDING_STATUS_COMPLETED,     # 第2行：完成状态
            GameConstants.BUILDING_STATUS_NEEDS_REPAIR,  # 第3行：50%生命值的需要修复状态
            GameConstants.BUILDING_STATUS_DESTROYED,     # 第4行：被摧毁状态
            'special'                                     # 第5行：特殊状态（金库爆满、箭塔无弹药、祭坛法力满）
        ]

        rows = len(building_states)  # 行数 = 状态数
        cols = len(building_types)   # 列数 = 建筑类型数

        # 间距设置 - 适应更大的地图
        spacing_x = 200  # 水平间距（增加间距）
        spacing_y = 150  # 垂直间距（增加间距）

        # 计算起始位置（从左上角开始）
        start_x = 100  # 距离左边缘100像素
        start_y = 100  # 距离上边缘100像素

        # 生成矩形排列的位置
        for row in range(rows):
            for col in range(cols):
                x = start_x + col * spacing_x
                y = start_y + row * spacing_y
                building_positions.append((x, y))

        self.building_positions = building_positions
        self.building_types = building_types
        self.building_states = building_states
        self.current_building_index = 0

        # 创建测试建筑实例
        self.test_buildings = []
        self._create_building_instances()

    def _create_building_instances(self):
        """通过模拟器接口创建建筑实例"""
        self.test_buildings = []

        # 为每种状态创建不同建筑类型的实例
        for row, state in enumerate(self.building_states):
            for col, building_type in enumerate(self.building_types):
                # 第5行只放置金库、箭塔、奥术塔、魔法祭坛、兽人巢穴和恶魔巢穴（特殊状态）
                if state == 'special' and building_type not in [BuildingType.TREASURY, BuildingType.ARROW_TOWER, BuildingType.MAGIC_ALTAR, BuildingType.ORC_LAIR, BuildingType.DEMON_LAIR]:
                    continue

                # 计算位置索引
                position_index = row * len(self.building_types) + col
                if position_index >= len(self.building_positions):
                    break

                pos_x, pos_y = self.building_positions[position_index]
                # 转换为瓦片坐标
                tile_x = int(pos_x // GameConstants.TILE_SIZE)
                tile_y = int(pos_y // GameConstants.TILE_SIZE)

                # 通过模拟器接口创建建筑
                building = None

                # 确定建筑是否完成（只有COMPLETED状态才是完成的）
                # 注意：需要修复状态（NEEDS_REPAIR）的建筑仍然是完成状态，只是生命值不满
                is_completed = (state == GameConstants.BUILDING_STATUS_COMPLETED or
                                state == GameConstants.BUILDING_STATUS_NEEDS_REPAIR or
                                state == GameConstants.BUILDING_STATUS_DESTROYED or
                                state == 'special')

                if building_type == BuildingType.DUNGEON_HEART:
                    # 使用模拟器的地牢之心创建API
                    building = self.simulator.create_dungeon_heart(
                        tile_x, tile_y, is_completed)
                elif building_type == BuildingType.ARROW_TOWER:
                    ammunition = 60  # 其他状态：满弹药
                    building = self.simulator.create_arrow_tower(
                        tile_x, tile_y, ammunition, is_completed)
                elif building_type == BuildingType.TREASURY:
                    stored_gold = 0    # 其他状态：空金库
                    building = self.simulator.create_treasury(
                        tile_x, tile_y, stored_gold, is_completed)
                elif building_type == BuildingType.TRAINING_ROOM:
                    building = self.simulator.create_training_room(
                        tile_x, tile_y, is_completed)
                elif building_type == BuildingType.LIBRARY:
                    building = self.simulator.create_library(
                        tile_x, tile_y, is_completed)
                elif building_type == BuildingType.PRISON:
                    building = self.simulator.create_prison(
                        tile_x, tile_y, is_completed)
                elif building_type == BuildingType.MAGIC_ALTAR:
                    # 使用模拟器的魔法祭坛创建API
                    stored_gold = 0
                    stored_mana = 0
                    if state == 'special':
                        stored_gold = 60  # 金币存储满
                        stored_mana = 100  # 一些魔力
                    building = self.simulator.create_magic_altar(
                        tile_x, tile_y, stored_gold, stored_mana, is_completed)
                elif building_type == BuildingType.ORC_LAIR:
                    # 使用便捷建筑创建API
                    stored_gold = 0
                    if state == 'special':
                        stored_gold = 50  # 特殊状态：满金币存储
                    game_logger.info(
                        f"🏹 尝试创建兽人巢穴: 位置({tile_x}, {tile_y}), 状态({state}), 存储金币({stored_gold}), 完成状态({is_completed})")
                    gold_info = self.simulator.resource_manager.get_total_gold()
                    mana_info = self.simulator.resource_manager.get_total_mana()
                    game_logger.info(
                        f"💰 当前资源: 金币={gold_info.available}, 魔力={mana_info.available}")
                    building = self.simulator.create_orc_lair(
                        tile_x, tile_y, stored_gold, is_completed)
                    if building:
                        game_logger.info(f"✅ 兽人巢穴创建成功")
                    else:
                        game_logger.info(f"❌ 兽人巢穴创建失败")
                elif building_type == BuildingType.DEMON_LAIR:
                    # 使用便捷建筑创建API
                    stored_gold = 0
                    if state == 'special':
                        stored_gold = 40  # 特殊状态：满金币存储
                    game_logger.info(
                        f"🔮 尝试创建恶魔巢穴: 位置({tile_x}, {tile_y}), 状态({state}), 存储金币({stored_gold}), 完成状态({is_completed})")
                    gold_info = self.simulator.resource_manager.get_total_gold()
                    mana_info = self.simulator.resource_manager.get_total_mana()
                    game_logger.info(
                        f"💰 当前资源: 金币={gold_info.available}, 魔力={mana_info.available}")
                    building = self.simulator.create_demon_lair(
                        tile_x, tile_y, stored_gold, is_completed)
                    if building:
                        game_logger.info(f"✅ 恶魔巢穴创建成功")
                    else:
                        game_logger.info(f"❌ 恶魔巢穴创建失败")
                elif building_type == BuildingType.ARCANE_TOWER:
                    # 使用便捷建筑创建API
                    game_logger.info(
                        f"🔮 尝试创建奥术塔: 位置({tile_x}, {tile_y}), 状态({state}), 完成状态({is_completed})")
                    gold_info = self.simulator.resource_manager.get_total_gold()
                    mana_info = self.simulator.resource_manager.get_total_mana()
                    game_logger.info(
                        f"💰 当前资源: 金币={gold_info.available}, 魔力={mana_info.available}")
                    building = self.simulator.create_arcane_tower(
                        tile_x, tile_y, is_completed)
                    if building:
                        game_logger.info(f"✅ 奥术塔创建成功")
                    else:
                        game_logger.info(f"❌ 奥术塔创建失败")
                else:
                    # 对于其他建筑类型，使用通用建筑创建API
                    building = self.simulator.create_building(
                        tile_x, tile_y, building_type, completed=is_completed)

                if building:
                    # 根据状态设置建筑属性 - 使用常量
                    # 注意：已移除损坏状态，现在只有5种状态
                    if state == GameConstants.BUILDING_STATUS_INCOMPLETE:
                        # 第1行：未建造状态
                        building.status = BuildingStatus.PLANNING
                        building.construction_progress = 0.0
                        building.health = 0.0
                        building.is_active = False
                    elif state == GameConstants.BUILDING_STATUS_COMPLETED:
                        # 第2行：完成状态（生命值满，功能正常）
                        building.status = BuildingStatus.COMPLETED
                        building.construction_progress = 1.0
                        building.health = building.max_health
                        building.is_active = True
                    elif state == GameConstants.BUILDING_STATUS_NEEDS_REPAIR:
                        # 第3行：需要修复状态（建筑已完成但生命值不满，需要工程师修复）
                        building.status = BuildingStatus.COMPLETED  # 状态仍为完成，只是生命值不满
                        building.construction_progress = 1.0
                        building.health = building.max_health * 0.5
                        building.is_active = True
                    elif state == GameConstants.BUILDING_STATUS_DESTROYED:
                        # 第4行：被摧毁状态（生命值为0，完全摧毁）
                        building.status = BuildingStatus.DESTROYED
                        building.construction_progress = 1.0
                        building.health = 0
                        building.is_active = False
                    elif state == 'special':
                        # 第5行：特殊状态（金库爆满、箭塔无弹药、魔法祭坛魔力生成等）
                        building.status = BuildingStatus.COMPLETED
                        building.construction_progress = 1.0
                        building.health = building.max_health
                        building.is_active = True

                        if building_type == BuildingType.ARROW_TOWER:
                            building.current_ammunition = 0
                        elif building_type == BuildingType.ARCANE_TOWER:
                            building.current_mana = 0  # 奥术塔魔力耗尽
                        elif building_type == BuildingType.TREASURY:
                            building.stored_gold = building.gold_storage_capacity
                        elif building_type == BuildingType.MAGIC_ALTAR:
                            # 魔法祭坛的金币已经在 create_magic_altar 中设置了
                            # 不直接设置 is_mana_generation_mode，让 _update_production 方法自然触发
                            game_logger.info(
                                f"🔮 魔法祭坛设置完成: 金币={building.temp_gold}, 魔力生成模式={building.is_mana_generation_mode}")
                        elif building_type == BuildingType.ORC_LAIR:
                            # 兽人巢穴特殊状态：临时金币满，准备训练
                            building.temp_gold = building.max_temp_gold
                            game_logger.info(
                                f"🏹 兽人巢穴设置完成: 临时金币={building.temp_gold}/{building.max_temp_gold}")
                        elif building_type == BuildingType.DEMON_LAIR:
                            # 恶魔巢穴特殊状态：临时金币满，准备召唤
                            building.temp_gold = building.max_temp_gold
                            game_logger.info(
                                f"🔮 恶魔巢穴设置完成: 临时金币={building.temp_gold}/{building.max_temp_gold}")

                    self.test_buildings.append(building)

    def _init_chinese_fonts(self):
        """初始化中文字体"""
        try:
            # 尝试加载系统中文字体
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/simhei.ttf",  # 黑体
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/arial.ttf",   # Arial
                "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方
                "/System/Library/Fonts/Arial.ttf",     # macOS Arial
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux Liberation
            ]

            self.chinese_font = None
            self.small_chinese_font = None
            self.large_chinese_font = None

            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        self.chinese_font = pygame.font.Font(font_path, 24)
                        self.small_chinese_font = pygame.font.Font(
                            font_path, 18)
                        self.large_chinese_font = pygame.font.Font(
                            font_path, 32)
                        game_logger.info(f"成功加载中文字体: {font_path}")
                        break
                    except Exception as e:
                        game_logger.info(f"字体加载失败 {font_path}: {e}")
                        continue

            if not self.chinese_font:
                # 如果都失败了，使用pygame默认字体
                self.chinese_font = pygame.font.Font(None, 24)
                self.small_chinese_font = pygame.font.Font(None, 18)
                self.large_chinese_font = pygame.font.Font(None, 32)
                game_logger.info("使用默认字体，中文可能显示为方块")

        except Exception as e:
            game_logger.info(f"字体初始化失败: {e}")
            self.chinese_font = pygame.font.Font(None, 24)
            self.small_chinese_font = pygame.font.Font(None, 18)
            self.large_chinese_font = pygame.font.Font(None, 32)

    def get_current_building(self):
        """获取当前展示的建筑"""
        category_name = list(self.building_categories.keys())[
            self.current_category_index]
        buildings = self.building_categories[category_name]
        if self.current_building_index < len(buildings):
            return buildings[self.current_building_index]
        return None

    def get_current_category(self):
        """获取当前分类名称"""
        return list(self.building_categories.keys())[self.current_category_index]

    def render_ui(self):
        """渲染UI信息"""
        screen = self.simulator.screen
        if not screen:
            return

        # 设置字体 - 使用字体管理器或回退到默认字体
        if self.font_manager:
            font = self.font_manager.get_font(24)
            small_font = self.font_manager.get_font(18)
            large_font = self.font_manager.get_font(32)
        else:
            font = self.chinese_font if hasattr(
                self, 'chinese_font') else pygame.font.Font(None, 24)
            small_font = self.small_chinese_font if hasattr(
                self, 'small_chinese_font') else pygame.font.Font(None, 18)
            large_font = self.large_chinese_font if hasattr(
                self, 'large_chinese_font') else pygame.font.Font(None, 32)

        # 渲染主UI面板背景 - 适应更大的屏幕
        ui_width = 350
        ui_height = 250
        ui_surface = pygame.Surface((ui_width, ui_height))
        ui_surface.set_alpha(220)
        ui_surface.fill((0, 0, 0))
        screen.blit(ui_surface, (20, 20))

        # 渲染标题
        title_text = font.render("建筑状态展示", True, (255, 215, 0))
        screen.blit(title_text, (30, 30))

        # 渲染状态说明
        state_desc = small_font.render(
            "每行一种状态，每列显示不同建筑", True, (200, 200, 200))
        screen.blit(state_desc, (30, 55))

        # 渲染状态颜色说明（简化版）
        color_info = [
            "灰色: 未完成/被摧毁",
            "黄色: 需要修复（生命值不满）",
            "绿色: 完成",
            "红色: 特殊状态",
            "紫色: 魔力生成/召唤",
            "棕色: 训练状态",
            "金色: 接受金币"
        ]
        for i, info in enumerate(color_info):
            color_text = small_font.render(info, True, (200, 200, 200))
            screen.blit(color_text, (30, 80 + i * 15))

        # 渲染控制说明
        controls_title = small_font.render("控制:", True, (255, 255, 255))
        screen.blit(controls_title, (30, 180))

        controls = [
            "WASD: 移动",
            "滚轮: 缩放",
            "ESC: 退出"
        ]

        y_offset = 200
        for control in controls:
            control_text = small_font.render(control, True, (200, 200, 200))
            screen.blit(control_text, (30, y_offset))
            y_offset += 15

    def _get_building_description(self, building_id):
        """获取建筑描述"""
        descriptions = {
            "dungeon_heart": "地牢之心，核心建筑，存储金币和魔力",
            "treasury": "提供金币存储和交换功能",
            "training_room": "提升怪物能力和获得经验",
            "library": "提供法力生成和法术研究",
            "workshop": "制造陷阱和装备",
            "prison": "关押俘虏并转换为己方单位",
            "torture_chamber": "加速转换过程并散发恐惧光环",
            "arrow_tower": "自动攻击入侵者的防御建筑",
            "arcane_tower": "使用奥术魔法进行范围攻击的防御建筑",
            "defense_fortification": "提供区域防御和伤害减免",
            "magic_altar": "生成法力、增强法术威力、金币存储和魔力生成",
            "shadow_temple": "最强大的魔法建筑，可施展高级魔法",
            "magic_research_institute": "研究新法术和魔法知识",
            "orc_lair": "训练兽人战士的军事建筑，提供临时金币存储",
            "demon_lair": "召唤小恶魔的魔法建筑，消耗魔力进行召唤"
        }
        return descriptions.get(building_id, "未知建筑类型")

    def render_buildings(self):
        """渲染测试建筑 - 使用模拟器API"""
        # 使用模拟器的建筑渲染API
        self.simulator._render_buildings()

    def handle_events(self):
        """处理事件 - 使用模拟器的默认按键设置"""
        # 使用模拟器的事件处理
        return self.simulator.handle_events()

    def update(self, delta_time):
        """更新逻辑"""
        # 使用模拟器的更新逻辑
        self.simulator.update(delta_time)

    def render(self):
        """渲染主循环"""
        # 清空屏幕
        self.simulator.screen.fill((30, 30, 50))

        # 使用模拟器的完整渲染API
        self.simulator.render()

        # 渲染UI
        self.render_ui()

        # 更新显示
        pygame.display.flip()

    def run_showcase(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            # 处理事件
            if not self.handle_events():
                running = False

            # 更新逻辑 - 使用与GameEnvironmentSimulator一致的时间单位（毫秒）
            delta_time = clock.tick(60)  # 保持毫秒单位，与模拟器一致
            self.update(delta_time)

            # 渲染
            self.render()

        game_logger.info("建筑展示模拟器结束")


def main():
    """主函数"""
    try:
        # 创建建筑展示模拟器
        showcase = BuildingShowcaseSimulator()

        # 运行展示
        showcase.run_showcase()

    except Exception as e:
        print(f"建筑展示模拟器运行出错: {e}")
        traceback.print_exc()
    finally:
        # 清理pygame
        if 'pygame' in sys.modules:
            pygame.quit()


if __name__ == "__main__":
    main()
