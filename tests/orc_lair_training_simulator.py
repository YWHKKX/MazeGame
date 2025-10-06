#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
兽人巢穴训练测试模拟器

测试目标：
1. 创建兽人巢穴
2. 创建哥布林苦工（作为训练材料）
3. 创建工程师投入金币
4. 观察兽人巢穴将苦工训练成兽人战士的过程
5. 创建骑士在200px以内、100px以外的位置（测试巡逻和追击行为）
6. 验证训练系统的完整流程和兽人战士的AI行为

遵循完全自动化原则：
- 所有测试完全自动化运行，无需手动操作
- 使用真实API调用链
- 自动收集测试数据和结果
- 使用统一日志系统
"""

# 重要：必须先设置Python路径，再导入项目模块
import sys
import os
import time
import math
import random
import pygame
import traceback

# 设置Python路径
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

# 使用try-except处理导入错误
try:
    from src.utils.logger import game_logger
    from src.core.constants import GameConstants
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
except ImportError as e:
    print(f"导入错误: {e}")
    print("正在尝试修复路径问题...")
    # 重新设置路径
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # 再次尝试导入
    from src.utils.logger import game_logger
    from src.core.constants import GameConstants
    from src.managers.game_environment_simulator import GameEnvironmentSimulator


class OrcLairTrainingSimulator:
    """兽人巢穴训练测试模拟器"""

    def __init__(self):
        """初始化模拟器"""
        self.simulator = None
        self.dungeon_heart = None
        self.orc_lair = None
        self.engineer = None
        self.goblin_worker = None
        self.knight = None
        self.training_start_time = None
        self.training_completed = False
        self.test_results = {
            'training_started': False,
            'training_completed': False,
            'orc_warrior_created': False,
            'knight_created': False,
            'orc_warrior_patrolling': False,
            'orc_warrior_hunting': False,
            'total_test_duration': 0,
            'gold_invested': 0
        }

    def setup_test_scenario(self):
        """设置测试场景"""
        game_logger.info("[START] 开始设置兽人巢穴训练测试场景")

        # 创建模拟器
        self.simulator = GameEnvironmentSimulator(
            screen_width=1200,
            screen_height=800,
            tile_size=GameConstants.TILE_SIZE,
            ui_scale=2.0
        )

        # 初始化Pygame
        self.simulator.init_pygame()

        # 生成地图
        self.simulator.generate_blank_map(width=30, height=20)

        # 设置相机位置到地图中心
        self._setup_camera()

        # 创建地牢之心
        self._create_dungeon_heart()

        # 创建兽人巢穴
        self._create_orc_lair()

        # 创建工程师
        self._create_engineer()

        # 创建哥布林苦工
        self._create_goblin_worker()

        # 创建骑士
        self._create_knight()

        # 设置工程师任务
        self._setup_engineer_tasks()

        game_logger.info("[SUCCESS] 测试场景设置完成")

    def _setup_engineer_tasks(self):
        """设置工程师任务"""
        if not self.engineer or not self.orc_lair:
            return

        game_logger.info("[TASK_SETUP] 设置工程师任务")

        # 设置工程师目标建筑为兽人巢穴
        if hasattr(self.engineer, 'set_target_building'):
            self.engineer.set_target_building(self.orc_lair)
            game_logger.info("[TASK_SETUP] 工程师目标建筑设置为兽人巢穴")

        # 设置工程师任务类型为投资金币
        if hasattr(self.engineer, 'set_task_type'):
            self.engineer.set_task_type("invest_gold")
            game_logger.info("[TASK_SETUP] 工程师任务类型设置为投资金币")

        # 记录工程师任务设置结果
        game_logger.info(f"[TASK_SETUP] 工程师任务设置完成:")
        game_logger.info(
            f"  - 目标建筑: {getattr(self.engineer, 'target_building', None) is not None}")
        game_logger.info(
            f"  - 任务类型: {getattr(self.engineer, 'task_type', 'none')}")
        game_logger.info(
            f"  - 携带金币: {getattr(self.engineer, 'carried_gold', 0)}")

    def _setup_camera(self):
        """设置相机位置到地图中心"""
        map_center_x = 15
        map_center_y = 10

        # 计算相机位置（参考README中的公式）
        screen_center_x = 1200 // 2 // 2.0  # 屏幕宽度 / 2 / UI缩放
        screen_center_y = 800 // 2 // 2.0   # 屏幕高度 / 2 / UI缩放

        dungeon_heart_pixel_x = map_center_x * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        dungeon_heart_pixel_y = map_center_y * \
            GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        camera_x = dungeon_heart_pixel_x - screen_center_x
        camera_y = dungeon_heart_pixel_y - screen_center_y

        self.simulator.set_camera_position(x=camera_x, y=camera_y)
        game_logger.info(f"[CAMERA] 相机位置设置: ({camera_x:.1f}, {camera_y:.1f})")

    def _create_dungeon_heart(self):
        """创建地牢之心"""
        self.dungeon_heart = self.simulator.create_dungeon_heart(
            x=15, y=10, gold=1000, completed=True
        )
        game_logger.info(
            f"[BUILDING] 创建地牢之心: 位置(15, 10), 金币: {self.dungeon_heart.stored_gold}")

    def _create_orc_lair(self):
        """创建兽人巢穴"""
        # 在地牢之心右侧创建兽人巢穴
        self.orc_lair = self.simulator.create_orc_lair(
            x=18, y=10, stored_gold=0, completed=True
        )

        # 修复配置：将最大临时金币设置为30（根据用户要求）
        self.orc_lair.max_temp_gold = 30
        # 修改训练时长为10秒（用于测试）
        self.orc_lair.training_duration = 10.0

        game_logger.info(
            f"[BUILDING] 创建兽人巢穴: 位置(18, 10), 最大临时金币: {self.orc_lair.max_temp_gold}, 训练时长: {self.orc_lair.training_duration}秒")

    def _create_engineer(self):
        """创建工程师"""
        # 在地牢之心左侧创建工程师
        engineer_pixel_x = 12 * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        engineer_pixel_y = 10 * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        self.engineer = self.simulator.create_engineer(
            x=engineer_pixel_x, y=engineer_pixel_y
        )

        # 给工程师一些金币用于投入（需要30金币）
        self.engineer.carried_gold = 100

        game_logger.info(
            f"[UNIT] 创建工程师: 位置({engineer_pixel_x}, {engineer_pixel_y}), 携带金币: {self.engineer.carried_gold}")

    def _create_goblin_worker(self):
        """创建哥布林苦工"""
        # 在兽人巢穴附近创建苦工
        worker_pixel_x = 20 * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        worker_pixel_y = 12 * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        self.goblin_worker = self.simulator.create_worker(
            x=worker_pixel_x, y=worker_pixel_y
        )

        game_logger.info(
            f"[UNIT] 创建哥布林苦工: 位置({worker_pixel_x}, {worker_pixel_y})")

    def _create_knight(self):
        """创建骑士"""
        # 计算兽人巢穴的像素位置
        orc_lair_pixel_x = 18 * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2
        orc_lair_pixel_y = 10 * GameConstants.TILE_SIZE + GameConstants.TILE_SIZE // 2

        # 在兽人巢穴的200px以内、100px以外创建骑士（作为敌人）
        # 使用150像素距离，45度角方向
        import math
        angle = math.pi / 4  # 45度角
        distance = 150  # 150像素距离（在100-200px范围内）

        knight_pixel_x = orc_lair_pixel_x + distance * math.cos(angle)
        knight_pixel_y = orc_lair_pixel_y - distance * math.sin(angle)  # 向上偏移

        self.knight = self.simulator.create_hero(
            x=knight_pixel_x, y=knight_pixel_y, hero_type='knight'
        )

        # 计算实际距离并记录
        actual_distance = math.sqrt(
            (knight_pixel_x - orc_lair_pixel_x)**2 + (knight_pixel_y - orc_lair_pixel_y)**2)

        game_logger.info(
            f"[UNIT] 创建骑士: 位置({knight_pixel_x:.1f}, {knight_pixel_y:.1f})")
        game_logger.info(
            f"[UNIT] 骑士距离兽人巢穴: {actual_distance:.1f}像素 (目标: 100-200px范围内)")

    def run_training_test(self, max_duration: float = 120.0):
        """运行训练测试"""
        game_logger.info(f"[TEST] 开始运行训练测试，最大时长: {max_duration}秒")

        start_time = time.time()
        last_log_time = start_time
        last_status_check = start_time

        # 设置开始时间用于击退测试
        self._start_time = start_time

        # 重写模拟器的update方法以集成击退测试
        original_update = self.simulator.update

        def custom_update(delta_time):
            # 调用原始update方法
            result = original_update(delta_time)

            # 添加击退测试逻辑
            current_time = time.time()
            self._periodic_status_check(current_time, check_interval=5.0)

            return result

        self.simulator.update = custom_update

        # 运行模拟
        self.simulator.run_simulation(
            max_duration=max_duration,
            enable_visualization=True
        )

        # 收集测试结果
        self._collect_test_results(start_time)

        # 输出测试报告
        self._generate_test_report()

    def _log_training_status(self, current_time: float):
        """记录训练状态日志"""
        if not self.orc_lair:
            return

        # 记录兽人巢穴详细状态
        game_logger.info(f"[TRAINING_STATUS] 兽人巢穴状态检查:")
        game_logger.info(
            f"  - 临时金币: {getattr(self.orc_lair, 'temp_gold', 0)}/{getattr(self.orc_lair, 'max_temp_gold', 0)}")
        game_logger.info(
            f"  - 是否锁定: {getattr(self.orc_lair, 'is_locked', False)}")
        game_logger.info(
            f"  - 是否训练中: {getattr(self.orc_lair, 'is_training', False)}")
        game_logger.info(
            f"  - 已分配苦工: {getattr(self.orc_lair, 'assigned_worker', None) is not None}")
        game_logger.info(
            f"  - 绑定怪物: {getattr(self.orc_lair, 'bound_monster', None) is not None}")

        # 如果有绑定的怪物，记录详细信息
        if hasattr(self.orc_lair, 'bound_monster') and self.orc_lair.bound_monster:
            monster = self.orc_lair.bound_monster
            game_logger.info(
                f"  - 绑定怪物类型: {getattr(monster, 'type', 'unknown')}")
            game_logger.info(
                f"  - 绑定怪物生命值: {getattr(monster, 'health', 0)}/{getattr(monster, 'max_health', 0)}")

        # 如果有分配的苦工，记录详细信息
        if hasattr(self.orc_lair, 'assigned_worker') and self.orc_lair.assigned_worker:
            worker = self.orc_lair.assigned_worker
            game_logger.info(
                f"  - 分配苦工位置: ({getattr(worker, 'x', 0):.1f}, {getattr(worker, 'y', 0):.1f})")
            game_logger.info(
                f"  - 分配苦工任务: {getattr(worker, 'task_type', 'none')}")

        # 记录训练进度
        if hasattr(self.orc_lair, 'is_training') and self.orc_lair.is_training:
            if hasattr(self.orc_lair, 'training_start_time'):
                elapsed = current_time - self.orc_lair.training_start_time
                remaining = getattr(
                    self.orc_lair, 'training_duration', 90) - elapsed
                progress = (elapsed / getattr(self.orc_lair,
                            'training_duration', 90)) * 100
                game_logger.info(
                    f"  - 训练进度: {progress:.1f}% (已用时: {elapsed:.1f}秒, 剩余: {remaining:.1f}秒)")

    def _log_worker_status(self, current_time: float):
        """记录苦工状态日志"""
        if not self.goblin_worker:
            return

        game_logger.info(f"[WORKER_STATUS] 哥布林苦工状态:")
        game_logger.info(
            f"  - 位置: ({getattr(self.goblin_worker, 'x', 0):.1f}, {getattr(self.goblin_worker, 'y', 0):.1f})")
        game_logger.info(
            f"  - 生命值: {getattr(self.goblin_worker, 'health', 0)}/{getattr(self.goblin_worker, 'max_health', 0)}")
        game_logger.info(
            f"  - 是否死亡: {getattr(self.goblin_worker, 'health', 0) <= 0}")
        game_logger.info(
            f"  - 死亡标记: {getattr(self.goblin_worker, 'is_dead_flag', False)}")
        game_logger.info(
            f"  - 分配建筑: {getattr(self.goblin_worker, 'assigned_building', None) is not None}")
        game_logger.info(
            f"  - 目标建筑: {getattr(self.goblin_worker, 'target_building', None) is not None}")
        game_logger.info(
            f"  - 任务类型: {getattr(self.goblin_worker, 'task_type', 'none')}")
        game_logger.info(
            f"  - 状态: {getattr(self.goblin_worker, 'state', 'unknown')}")

        # 检查苦工是否在模拟器的怪物列表中
        if self.simulator and hasattr(self.simulator, 'monsters'):
            worker_in_list = self.goblin_worker in self.simulator.monsters
            game_logger.info(f"  - 在怪物列表中: {worker_in_list}")
            if worker_in_list:
                game_logger.info(f"  - 怪物列表总数: {len(self.simulator.monsters)}")

        # 计算到兽人巢穴的距离
        if self.orc_lair:
            distance = ((self.goblin_worker.x - self.orc_lair.x) ** 2 +
                        (self.goblin_worker.y - self.orc_lair.y) ** 2) ** 0.5
            game_logger.info(f"  - 到兽人巢穴距离: {distance:.1f}像素")

    def _log_engineer_status(self, current_time: float):
        """记录工程师状态日志"""
        if not self.engineer:
            return

        game_logger.info(f"[ENGINEER_STATUS] 工程师状态:")
        game_logger.info(
            f"  - 位置: ({getattr(self.engineer, 'x', 0):.1f}, {getattr(self.engineer, 'y', 0):.1f})")
        game_logger.info(
            f"  - 携带金币: {getattr(self.engineer, 'carried_gold', 0)}")
        game_logger.info(
            f"  - 状态: {getattr(self.engineer, 'status', 'unknown')}")

        # 记录工程师的工作进度
        if hasattr(self.engineer, 'work_progress'):
            game_logger.info(
                f"  - 工作进度: {getattr(self.engineer, 'work_progress', 0)}")

        # 计算到地牢之心的距离
        if self.dungeon_heart:
            distance = ((self.engineer.x - self.dungeon_heart.x) ** 2 +
                        (self.engineer.y - self.dungeon_heart.y) ** 2) ** 0.5
            game_logger.info(f"  - 到地牢之心距离: {distance:.1f}像素")

    def _log_knight_status(self, current_time: float):
        """记录骑士状态日志"""
        if not self.knight:
            return

        game_logger.info(f"[KNIGHT_STATUS] 骑士状态:")
        game_logger.info(
            f"  - 位置: ({getattr(self.knight, 'x', 0):.1f}, {getattr(self.knight, 'y', 0):.1f})")
        game_logger.info(
            f"  - 生命值: {getattr(self.knight, 'health', 0)}/{getattr(self.knight, 'max_health', 0)}")
        game_logger.info(
            f"  - 是否存活: {getattr(self.knight, 'health', 0) > 0}")
        game_logger.info(
            f"  - 攻击力: {getattr(self.knight, 'attack', 0)}")
        game_logger.info(
            f"  - 护甲: {getattr(self.knight, 'armor', 0)}")
        game_logger.info(
            f"  - 击退状态: {getattr(self.knight, 'knockback_state', None)}")

        # 计算到兽人巢穴的距离
        if self.orc_lair:
            distance = ((self.knight.x - self.orc_lair.x) ** 2 +
                        (self.knight.y - self.orc_lair.y) ** 2) ** 0.5
            game_logger.info(f"  - 到兽人巢穴距离: {distance:.1f}像素")

    def _log_orc_warrior_status(self, current_time: float):
        """记录兽人战士状态日志"""
        if not self.orc_lair or not self.orc_lair.bound_monster:
            return

        orc_warrior = self.orc_lair.bound_monster
        game_logger.info(f"[ORC_WARRIOR_STATUS] 兽人战士状态:")
        game_logger.info(
            f"  - 位置: ({getattr(orc_warrior, 'x', 0):.1f}, {getattr(orc_warrior, 'y', 0):.1f})")
        game_logger.info(
            f"  - 生命值: {getattr(orc_warrior, 'health', 0)}/{getattr(orc_warrior, 'max_health', 0)}")
        game_logger.info(
            f"  - 状态: {getattr(orc_warrior, 'state', 'unknown')}")
        game_logger.info(
            f"  - 有目标: {getattr(orc_warrior, 'target', None) is not None}")

        # 如果有目标，记录目标信息
        if hasattr(orc_warrior, 'target') and orc_warrior.target:
            target = orc_warrior.target
            distance_to_target = ((orc_warrior.x - target.x)
                                  ** 2 + (orc_warrior.y - target.y) ** 2) ** 0.5
            game_logger.info(f"  - 目标类型: {getattr(target, 'type', 'unknown')}")
            game_logger.info(f"  - 到目标距离: {distance_to_target:.1f}像素")

        # 计算到兽人巢穴的距离
        if self.orc_lair:
            distance_to_lair = ((orc_warrior.x - self.orc_lair.x) ** 2 +
                                (orc_warrior.y - self.orc_lair.y) ** 2) ** 0.5
            game_logger.info(f"  - 到巢穴距离: {distance_to_lair:.1f}像素")

            # 判断是否在巡逻范围内
            in_patrol_range = distance_to_lair <= 200
            game_logger.info(f"  - 在巡逻范围内: {in_patrol_range}")

    def _log_system_status(self, current_time: float):
        """记录系统状态日志"""
        game_logger.info(f"[SYSTEM_STATUS] 系统状态检查:")

        # 记录模拟器状态
        if self.simulator:
            game_logger.info(f"  - 模拟器运行中: {True}")
            game_logger.info(
                f"  - 建筑数量: {len(getattr(self.simulator, 'buildings', []))}")
            game_logger.info(
                f"  - 工程师数量: {len(getattr(self.simulator, 'engineers', []))}")
            game_logger.info(
                f"  - 苦工数量: {len(getattr(self.simulator, 'workers', []))}")
            game_logger.info(
                f"  - 怪物数量: {len(getattr(self.simulator, 'monsters', []))}")

        # 记录游戏状态
        if hasattr(self.simulator, 'game_state') and self.simulator.game_state:
            game_state = self.simulator.game_state
            game_logger.info(f"  - 游戏状态类型: {type(game_state).__name__}")
            game_logger.info(
                f"  - 游戏状态属性: {[attr for attr in dir(game_state) if not attr.startswith('_')]}")

    def _periodic_status_check(self, current_time: float, check_interval: float = 5.0):
        """定期状态检查"""
        if current_time - getattr(self, '_last_status_check_time', 0) >= check_interval:
            self._last_status_check_time = current_time
            game_logger.info(
                f"[PERIODIC_CHECK] 定期状态检查 - 运行时间: {current_time - getattr(self, '_start_time', current_time):.1f}秒")

            # 记录各种状态
            self._log_training_status(current_time)
            self._log_worker_status(current_time)
            self._log_engineer_status(current_time)
            self._log_knight_status(current_time)
            self._log_orc_warrior_status(current_time)
            self._log_system_status(current_time)

            game_logger.info("=" * 80)

    def _collect_test_results(self, start_time: float):
        """收集测试结果"""
        end_time = time.time()
        self.test_results['total_test_duration'] = end_time - start_time

        game_logger.info("[COLLECT_RESULTS] 开始收集测试结果")

        # 详细检查训练状态
        if self.orc_lair:
            game_logger.info(f"[COLLECT_RESULTS] 兽人巢穴最终状态:")
            game_logger.info(
                f"  - 临时金币: {getattr(self.orc_lair, 'temp_gold', 0)}/{getattr(self.orc_lair, 'max_temp_gold', 0)}")
            game_logger.info(
                f"  - 是否锁定: {getattr(self.orc_lair, 'is_locked', False)}")
            game_logger.info(
                f"  - 是否训练中: {getattr(self.orc_lair, 'is_training', False)}")
            game_logger.info(
                f"  - 已分配苦工: {getattr(self.orc_lair, 'assigned_worker', None) is not None}")
            game_logger.info(
                f"  - 绑定怪物: {getattr(self.orc_lair, 'bound_monster', None) is not None}")

            # 如果有绑定的怪物，详细记录
            if hasattr(self.orc_lair, 'bound_monster') and self.orc_lair.bound_monster:
                monster = self.orc_lair.bound_monster
                game_logger.info(f"  - 绑定怪物详情:")
                game_logger.info(
                    f"    * 类型: {getattr(monster, 'type', 'unknown')}")
                game_logger.info(
                    f"    * 生命值: {getattr(monster, 'health', 0)}/{getattr(monster, 'max_health', 0)}")
                game_logger.info(
                    f"    * 位置: ({getattr(monster, 'x', 0):.1f}, {getattr(monster, 'y', 0):.1f})")
                game_logger.info(
                    f"    * 是否存活: {getattr(monster, 'health', 0) > 0}")

        # 检查训练是否开始（改进逻辑：检查训练历史状态）
        training_started = False
        training_started_reason = ""

        # 方法1：检查当前训练状态
        if hasattr(self.orc_lair, 'is_training') and self.orc_lair.is_training:
            training_started = True
            training_started_reason = "当前正在训练中"

        # 方法2：检查是否有绑定怪物（说明训练已完成）
        elif hasattr(self.orc_lair, 'bound_monster') and self.orc_lair.bound_monster:
            training_started = True
            training_started_reason = "训练已完成，有绑定怪物"

        # 方法3：检查训练开始时间（历史记录）
        elif hasattr(self.orc_lair, 'training_start_time') and self.orc_lair.training_start_time > 0:
            training_started = True
            training_started_reason = "有训练历史记录"

        # 检查训练完成相关的日志
        game_logger.info(
            f"[ANALYSIS] 训练开始时间: {getattr(self.orc_lair, 'training_start_time', 'none')}")
        game_logger.info(
            f"[ANALYSIS] 训练时长: {getattr(self.orc_lair, 'training_duration', 'none')}秒")
        if hasattr(self.orc_lair, 'training_start_time') and self.orc_lair.training_start_time > 0:
            elapsed = end_time - self.orc_lair.training_start_time
            game_logger.info(f"[ANALYSIS] 训练已用时: {elapsed:.1f}秒")
            if hasattr(self.orc_lair, 'training_duration'):
                remaining = self.orc_lair.training_duration - elapsed
                game_logger.info(f"[ANALYSIS] 训练剩余时间: {remaining:.1f}秒")
                if remaining <= 0:
                    game_logger.info(
                        "[ANALYSIS] 训练应该已经完成，但可能_complete_training未被调用")

        self.test_results['training_started'] = training_started

        if training_started:
            game_logger.info(f"[SUCCESS] 训练已开始 ({training_started_reason})")
        else:
            game_logger.info("[FAIL] 训练未开始")

            # 分析为什么训练没有开始
            if not hasattr(self.orc_lair, 'temp_gold') or self.orc_lair.temp_gold < self.orc_lair.max_temp_gold:
                game_logger.info(
                    f"[ANALYSIS] 训练未开始原因: 金币不足 ({getattr(self.orc_lair, 'temp_gold', 0)}/{getattr(self.orc_lair, 'max_temp_gold', 0)})")
            elif not hasattr(self.orc_lair, 'assigned_worker') or not self.orc_lair.assigned_worker:
                game_logger.info("[ANALYSIS] 训练未开始原因: 没有分配苦工")
            elif hasattr(self.orc_lair, 'is_locked') and self.orc_lair.is_locked:
                game_logger.info("[ANALYSIS] 训练未开始原因: 建筑被锁定")

        # 检查是否有绑定的兽人战士
        if hasattr(self.orc_lair, 'bound_monster') and self.orc_lair.bound_monster:
            self.test_results['training_completed'] = True
            self.test_results['orc_warrior_created'] = True
            game_logger.info("[SUCCESS] 兽人战士已创建并绑定到巢穴")

            # 检查兽人战士是否存活
            monster = self.orc_lair.bound_monster
            if hasattr(monster, 'health') and monster.health > 0:
                game_logger.info("[SUCCESS] 兽人战士存活")

                # 检查兽人战士的AI行为
                if hasattr(monster, 'state'):
                    state = monster.state
                    if hasattr(state, 'value'):
                        state_str = state.value
                    else:
                        state_str = str(state)

                    game_logger.info(f"[AI_BEHAVIOR] 兽人战士当前状态: {state_str}")

                    # 检查是否进入巡逻状态
                    if state_str == 'patrolling':
                        self.test_results['orc_warrior_patrolling'] = True
                        game_logger.info("[SUCCESS] 兽人战士进入巡逻状态")

                    # 检查是否进入追击状态
                    if state_str == 'hunting':
                        self.test_results['orc_warrior_hunting'] = True
                        game_logger.info("[SUCCESS] 兽人战士进入追击状态")

                    # 检查是否有目标
                    if hasattr(monster, 'target') and monster.target:
                        game_logger.info(
                            f"[AI_BEHAVIOR] 兽人战士有目标: {getattr(monster.target, 'type', 'unknown')}")
                        distance_to_target = (
                            (monster.x - monster.target.x) ** 2 + (monster.y - monster.target.y) ** 2) ** 0.5
                        game_logger.info(
                            f"[AI_BEHAVIOR] 到目标距离: {distance_to_target:.1f}像素")
            else:
                game_logger.info("[WARNING] 兽人战士已死亡")
        else:
            game_logger.info("[FAIL] 没有创建兽人战士")

        # 检查骑士状态
        if self.knight:
            self.test_results['knight_created'] = True
            if hasattr(self.knight, 'health') and self.knight.health > 0:
                game_logger.info("[SUCCESS] 骑士存活")
            else:
                game_logger.info("[WARNING] 骑士已死亡")
        else:
            game_logger.info("[FAIL] 没有创建骑士")

            # 分析为什么没有创建兽人战士
            if not self.test_results['training_started']:
                game_logger.info("[ANALYSIS] 兽人战士未创建原因: 训练未开始")
            elif hasattr(self.orc_lair, 'is_training') and self.orc_lair.is_training:
                # 检查训练时间
                if hasattr(self.orc_lair, 'training_start_time'):
                    elapsed = end_time - self.orc_lair.training_start_time
                    required_time = getattr(
                        self.orc_lair, 'training_duration', 90)
                    game_logger.info(
                        f"[ANALYSIS] 兽人战士未创建原因: 训练时间不足 (已用时: {elapsed:.1f}秒, 需要: {required_time}秒)")

        # 统计投入的金币
        if hasattr(self.orc_lair, 'temp_gold'):
            self.test_results['gold_invested'] = self.orc_lair.temp_gold
            game_logger.info(
                f"[COLLECT_RESULTS] 投入金币统计: {self.test_results['gold_invested']}")

        # 检查苦工状态
        if self.goblin_worker:
            game_logger.info(f"[COLLECT_RESULTS] 苦工最终状态:")
            game_logger.info(
                f"  - 位置: ({getattr(self.goblin_worker, 'x', 0):.1f}, {getattr(self.goblin_worker, 'y', 0):.1f})")
            game_logger.info(
                f"  - 生命值: {getattr(self.goblin_worker, 'health', 0)}/{getattr(self.goblin_worker, 'max_health', 0)}")
            game_logger.info(
                f"  - 是否存活: {getattr(self.goblin_worker, 'health', 0) > 0}")
            game_logger.info(
                f"  - 死亡标记: {getattr(self.goblin_worker, 'is_dead_flag', False)}")
            game_logger.info(
                f"  - 分配状态: {getattr(self.goblin_worker, 'assigned_building', None) is not None}")
            game_logger.info(
                f"  - 任务类型: {getattr(self.goblin_worker, 'task_type', 'none')}")

            # 检查苦工是否在模拟器的怪物列表中
            if self.simulator and hasattr(self.simulator, 'monsters'):
                worker_in_list = self.goblin_worker in self.simulator.monsters
                game_logger.info(f"  - 在怪物列表中: {worker_in_list}")
                if worker_in_list:
                    game_logger.info(
                        f"  - 怪物列表总数: {len(self.simulator.monsters)}")

                    # 检查是否有其他死亡的苦工
                    dead_workers = [m for m in self.simulator.monsters if
                                    hasattr(m, 'type') and m.type == 'goblin_worker' and m.health <= 0]
                    game_logger.info(f"  - 死亡苦工数量: {len(dead_workers)}")

                    # 检查清理死亡单位的调用
                    game_logger.info(
                        f"  - 模拟器是否有_cleanup_dead_units方法: {hasattr(self.simulator, '_cleanup_dead_units')}")

        # 检查工程师状态
        if self.engineer:
            game_logger.info(f"[COLLECT_RESULTS] 工程师最终状态:")
            game_logger.info(
                f"  - 位置: ({getattr(self.engineer, 'x', 0):.1f}, {getattr(self.engineer, 'y', 0):.1f})")
            game_logger.info(
                f"  - 携带金币: {getattr(self.engineer, 'carried_gold', 0)}")
            game_logger.info(
                f"  - 状态: {getattr(self.engineer, 'status', 'unknown')}")

        # 检查骑士状态
        if self.knight:
            game_logger.info(f"[COLLECT_RESULTS] 骑士最终状态:")
            game_logger.info(
                f"  - 位置: ({getattr(self.knight, 'x', 0):.1f}, {getattr(self.knight, 'y', 0):.1f})")
            game_logger.info(
                f"  - 生命值: {getattr(self.knight, 'health', 0)}/{getattr(self.knight, 'max_health', 0)}")
            game_logger.info(
                f"  - 是否存活: {getattr(self.knight, 'health', 0) > 0}")
            game_logger.info(
                f"  - 攻击力: {getattr(self.knight, 'attack', 0)}")
            game_logger.info(
                f"  - 护甲: {getattr(self.knight, 'armor', 0)}")

        game_logger.info("[COLLECT_RESULTS] 测试结果收集完成")

    def _generate_test_report(self):
        """生成测试报告"""
        game_logger.info("[REPORT] 兽人巢穴训练测试报告")
        game_logger.info("=" * 50)

        # 测试结果统计
        game_logger.info(
            f"[TIME] 测试总时长: {self.test_results['total_test_duration']:.1f}秒")
        game_logger.info(f"[GOLD] 投入金币: {self.test_results['gold_invested']}")
        game_logger.info(
            f"[TRAINING] 训练开始: {'[SUCCESS] 是' if self.test_results['training_started'] else '[FAIL] 否'}")
        game_logger.info(
            f"[TRAINING] 训练完成: {'[SUCCESS] 是' if self.test_results['training_completed'] else '[FAIL] 否'}")
        game_logger.info(
            f"[UNIT] 兽人战士创建: {'[SUCCESS] 是' if self.test_results['orc_warrior_created'] else '[FAIL] 否'}")
        game_logger.info(
            f"[UNIT] 骑士创建: {'[SUCCESS] 是' if self.test_results['knight_created'] else '[FAIL] 否'}")
        game_logger.info(
            f"[AI] 兽人战士巡逻: {'[SUCCESS] 是' if self.test_results['orc_warrior_patrolling'] else '[FAIL] 否'}")
        game_logger.info(
            f"[AI] 兽人战士追击: {'[SUCCESS] 是' if self.test_results['orc_warrior_hunting'] else '[FAIL] 否'}")

        # 建筑状态
        if self.orc_lair:
            game_logger.info(
                f"[BUILDING] 兽人巢穴状态: 锁定={self.orc_lair.is_locked}, 训练中={getattr(self.orc_lair, 'is_training', False)}")
            game_logger.info(
                f"[GOLD] 临时金币: {getattr(self.orc_lair, 'temp_gold', 0)}/{getattr(self.orc_lair, 'max_temp_gold', 0)}")

        # 工程师状态
        if self.engineer:
            game_logger.info(
                f"[UNIT] 工程师状态: 携带金币={self.engineer.carried_gold}")

        # 苦工状态
        if self.goblin_worker:
            is_alive = self.goblin_worker.health > 0
            game_logger.info(
                f"[UNIT] 哥布林苦工状态: 存活={is_alive}, 生命值={self.goblin_worker.health}")

            # 分析苦工清除问题
            if not is_alive:
                game_logger.info("[ANALYSIS] 苦工已死亡")
                if hasattr(self.goblin_worker, 'is_dead_flag'):
                    game_logger.info(
                        f"[ANALYSIS] 苦工死亡标记: {self.goblin_worker.is_dead_flag}")

                # 检查是否在怪物列表中
                if self.simulator and hasattr(self.simulator, 'monsters'):
                    worker_in_list = self.goblin_worker in self.simulator.monsters
                    game_logger.info(f"[ANALYSIS] 苦工在怪物列表中: {worker_in_list}")

                    if not worker_in_list:
                        game_logger.info("[SUCCESS] 苦工已被正确清除 - 不在怪物列表中")
                        game_logger.info(
                            "[ANALYSIS] 说明: _cleanup_dead_units方法正常工作")
                    else:
                        game_logger.info("[WARNING] 苦工死亡后仍在怪物列表中")
                        game_logger.info(
                            "[ANALYSIS] 问题原因: _cleanup_dead_units方法可能未正确调用")

                # 统计当前怪物列表中的苦工数量
                if self.simulator and hasattr(self.simulator, 'monsters'):
                    goblin_workers = [m for m in self.simulator.monsters
                                      if hasattr(m, 'type') and m.type == 'goblin_worker']
                    game_logger.info(
                        f"[ANALYSIS] 当前怪物列表中的苦工数量: {len(goblin_workers)}")
            else:
                game_logger.info("[ANALYSIS] 苦工仍然存活，训练可能未成功完成")

        # 骑士状态
        if self.knight:
            game_logger.info(
                f"[UNIT] 骑士状态: 存活={self.knight.health > 0}")

        # 总体评价
        success_rate = sum([
            self.test_results['training_started'],
            self.test_results['training_completed'],
            self.test_results['orc_warrior_created'],
            self.test_results['knight_created'],
            self.test_results['orc_warrior_patrolling'],
            self.test_results['orc_warrior_hunting']
        ]) / 6 * 100

        game_logger.info(f"[RESULT] 测试成功率: {success_rate:.1f}%")

        if success_rate >= 100:
            game_logger.info("[SUCCESS] 测试完全成功！兽人巢穴训练系统工作正常")
        elif success_rate >= 66:
            game_logger.info("[WARNING] 测试部分成功，需要检查未通过的环节")
        else:
            game_logger.info("[ERROR] 测试失败，需要检查训练系统配置")

        game_logger.info("=" * 50)


def main():
    """主函数"""
    try:
        game_logger.info("[START] 启动兽人巢穴训练测试")

        # 创建测试模拟器
        simulator = OrcLairTrainingSimulator()

        # 设置测试场景
        simulator.setup_test_scenario()

        # 运行训练测试（30秒，足够完成10秒训练）
        simulator.run_training_test(max_duration=30.0)

        game_logger.info("[SUCCESS] 兽人巢穴训练测试完成")

    except Exception as e:
        game_logger.error(f"[ERROR] 测试运行失败: {str(e)}")
        game_logger.error(f"[DETAIL] 错误详情: {traceback.format_exc()}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
