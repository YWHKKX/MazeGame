#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生物实体模块
"""

import math
import random
import time
from typing import List, Dict, Optional, Tuple
from enum import Enum

# 导入需要的类型和配置
from src.core.constants import GameConstants, GameBalance
from src.core.enums import TileType, BuildMode
from src.core.game_state import Tile, GameState
from src.entities.configs import CreatureConfig
from src.managers.movement_system import MovementSystem
from src.utils.logger import game_logger


class CreatureStatus(Enum):
    """
    通用生物状态枚举

    注意：这些状态值复用自 status_indicator.py 中的状态定义
    状态值必须与 StatusIndicator.default_colors 中的键名一致
    """
    IDLE = "idle"                          # 空闲
    WANDERING = "wandering"                # 游荡
    FIGHTING = "fighting"                  # 战斗中
    FLEEING = "fleeing"                    # 逃跑中
    MOVING = "moving"                      # 移动中


class Creature:
    def __init__(self, x: int, y: int, creature_type: str = 'imp'):
        self.x = x
        self.y = y
        self.type = creature_type
        self.name = creature_type  # 添加name属性，默认为creature_type

        # 战斗属性
        self.is_combat_unit = True  # 是否为战斗单位（默认是）

        # 范围伤害配置（可选）
        self.area_damage = self._get_area_damage_config(creature_type)

        # 阵营系统 - 统一使用faction属性
        self.faction = "monsters"  # 默认怪物阵营，子类可以重写

        # 攻击目标追踪（用于近战攻击限制）
        self.melee_target = None  # 当前近战攻击的目标

        # 目标追踪系统（优化战斗搜索）
        self.current_target = None  # 当前追踪的目标
        self.target_last_seen_time = 0  # 目标最后被看到的时间
        self.target_search_cooldown = 0  # 目标搜索冷却时间

        # 攻击列表管理
        self.attack_list = []  # 攻击目标列表
        self.attack_list_last_update = 0  # 攻击列表最后更新时间

        # 物理系统属性
        self.collision_radius = None  # 碰撞半径（由物理系统计算）
        self.knockback_state = None   # 击退状态
        self.can_move = True         # 是否可以移动
        self.can_attack = True       # 是否可以攻击

        # 特殊物理状态
        self.immunities = set()      # 免疫列表
        self.is_rooted = False       # 是否扎根（树人守护者等）
        self.has_shield = False      # 是否有护盾

        # 导入角色图鉴系统
        try:
            from src.ui.character_bestiary import CharacterBestiary
            from src.entities.character_data import character_db
            BESTIARY_AVAILABLE = True
        except ImportError:
            BESTIARY_AVAILABLE = False

        try:
            # 使用character_data.py中的角色数据
            if BESTIARY_AVAILABLE:
                character_data = character_db.get_character(creature_type)
                if character_data:
                    self.character_data = character_data
                    self.size = character_data.size
                    self.health = character_data.hp
                    self.max_health = character_data.hp
                    self.attack = character_data.attack
                    self.speed = character_data.speed
                    self.color = character_data.color
                    self.armor = character_data.armor
                    self.attack_range = character_data.attack_range
                    self.attack_cooldown = character_data.attack_cooldown
                    self.special_ability = character_data.special_ability
                    self.cost = character_data.cost if character_data.cost else 100
                    self.abilities = [character_data.special_ability]
                    self.upkeep = 0  # 暂时设置为0
                else:
                    # 如果角色数据不存在，使用默认配置
                    if creature_type not in CreatureConfig.TYPES:
                        creature_type = 'imp'  # 回退到默认类型
                    config = CreatureConfig.TYPES[creature_type]
                    self.character_data = None
                    self.size = config['size']
                    self.health = config['health']
                    self.max_health = config['health']
                    self.attack = config['attack']
                    self.speed = config['speed']
                    self.color = config['color']
                    self.armor = 0
                    self.attack_range = config.get('attack_range', 30)
                    self.attack_cooldown = config.get('attack_cooldown', 1.0)
                    self.special_ability = "无"
                    self.cost = 100
                    self.abilities = config['abilities']
                    self.upkeep = config['upkeep']
            else:
                # 如果图鉴系统不可用，使用默认配置
                if creature_type not in CreatureConfig.TYPES:
                    creature_type = 'imp'  # 回退到默认类型
                config = CreatureConfig.TYPES[creature_type]
                self.character_data = None
                self.size = config['size']
                self.health = config['health']
                self.max_health = config['health']
                self.attack = config['attack']
                self.speed = config['speed']
                self.color = config['color']
                self.armor = 0
                self.attack_range = config.get('attack_range', 30)
                self.attack_cooldown = config.get('attack_cooldown', 1.0)
                self.special_ability = "无"
                self.cost = 100
                self.abilities = config['abilities']
                self.upkeep = config['upkeep']
        except Exception as e:
            # 使用最基本的默认配置
            self.character_data = None
            self.size = 15
            self.health = 80
            self.max_health = 80
            self.attack = 15
            self.speed = 25
            self.color = (255, 107, 107)
            self.armor = 0
            self.attack_range = 30
            self.attack_cooldown = 1.0
            self.special_ability = "无"
            self.cost = 100
            self.abilities = ['dig', 'fight']
            self.upkeep = 1

        self.target = None
        self.state = CreatureStatus.IDLE.value
        self.last_attack = 0
        self._idle_state_registered = False  # 空闲状态注册标记
        self.mining_target = None
        self.path = []

        # 战斗状态和回血系统
        self.in_combat = False
        self.last_combat_time = 0
        self.regeneration_rate = GameConstants.REGENERATION_RATE  # 每秒回血量
        self.regeneration_delay = GameConstants.REGENERATION_DELAY  # 脱离战斗后开始回血的延迟时间

        # 设置特殊物理属性
        self._setup_special_physics_properties()

        # 特定生物类型的特殊属性会在子类中初始化

    def update(self, delta_time: float, game_map: List[List[Tile]], creatures: List['Creature'], heroes: List = None, effect_manager=None, building_manager=None, game_instance=None):
        """
        更新生物状态 - 基类方法，由子类重写具体行为

        Args:
            delta_time: 时间增量（秒）
            game_instance: 游戏实例引用（用于空闲状态管理）
        """
        # 基础生物行为更新
        self._update_basic_behavior(delta_time, game_map, effect_manager)

        # 管理空闲状态
        self._manage_idle_state(game_instance)

    def _find_nearest_hero(self, heroes: List, max_distance: float) -> Optional:
        """寻找最近的英雄 - 通用方法"""
        nearest_hero = None
        nearest_distance = float('inf')

        for hero in heroes:
            distance = math.sqrt((hero.x - self.x) **
                                 2 + (hero.y - self.y) ** 2)
            if distance < max_distance and distance < nearest_distance:
                nearest_distance = distance
                nearest_hero = hero

        return nearest_hero

    def _update_basic_behavior(self, delta_time: float, game_map: List[List[Tile]], effect_manager=None):
        """基础生物行为更新 - 只有战斗单位才主动寻找敌人"""
        # 只有战斗单位才使用战斗行为
        if self.is_combat_unit:
            self._update_combat_behavior(delta_time, game_map, effect_manager)

    def _update_combat_behavior(self, delta_time: float, game_map: List[List[Tile]], effect_manager=None):
        """通用怪物战斗行为 - 优化版本，使用目标追踪系统"""
        import time
        current_time = time.time()

        # 更新搜索冷却时间
        if self.target_search_cooldown > 0:
            self.target_search_cooldown -= delta_time

        # 注意：攻击和移动逻辑现在由CombatSystem统一处理
        # 这里只处理非战斗的AI逻辑

        # 优先级1: 血量过低时撤退
        if self.health <= self.max_health * GameConstants.FLEE_HEALTH_THRESHOLD:
            self.state = CreatureStatus.FLEEING.value
            # 不直接移动，让CombatSystem处理
            return

        # 优先级2: 无敌人时游荡巡逻
        if not self.in_combat:
            self.state = CreatureStatus.WANDERING.value
            # 不直接移动，让CombatSystem处理
        else:
            # 在战斗中时设置为战斗状态
            self.state = CreatureStatus.FIGHTING.value

    def _manage_idle_state(self, game_instance=None):
        """管理空闲状态的注册和取消注册"""
        if self.state == CreatureStatus.IDLE.value:
            if not self._idle_state_registered and game_instance and hasattr(game_instance, 'idle_state_manager'):
                game_instance.idle_state_manager.register_idle_unit(self)
                self._idle_state_registered = True
        else:
            if self._idle_state_registered and game_instance and hasattr(game_instance, 'idle_state_manager'):
                game_instance.idle_state_manager.unregister_idle_unit(self)
                self._idle_state_registered = False

    def _get_search_range(self) -> float:
        """根据怪物类型获取搜索敌人的范围"""
        search_ranges = {
            'imp': GameConstants.SEARCH_RANGE_IMP,           # 小恶魔 - 中等搜索范围
            'gargoyle': GameConstants.SEARCH_RANGE_GARGOYLE,      # 石像鬼 - 较大搜索范围
            'fire_salamander': GameConstants.SEARCH_RANGE_FIRE_SALAMANDER,  # 火蜥蜴 - 中等搜索范围
            'shadow_mage': GameConstants.SEARCH_RANGE_SHADOW_MAGE,   # 暗影法师 - 大搜索范围
            'tree_guardian': GameConstants.SEARCH_RANGE_TREE_GUARDIAN,  # 树人守护者 - 较小搜索范围（防守型）
            'shadow_lord': GameConstants.SEARCH_RANGE_SHADOW_LORD,   # 暗影领主 - 最大搜索范围
            'bone_dragon': GameConstants.SEARCH_RANGE_BONE_DRAGON,   # 骨龙 - 超大搜索范围
            'hellhound': GameConstants.SEARCH_RANGE_HELLHOUND,     # 地狱犬 - 中等搜索范围
            'stone_golem': GameConstants.SEARCH_RANGE_STONE_GOLEM,    # 石魔像 - 较小搜索范围（防守型）
            'succubus': GameConstants.SEARCH_RANGE_SUCCUBUS,      # 魅魔 - 大搜索范围
            'goblin_engineer': GameConstants.SEARCH_RANGE_GOBLIN_ENGINEER,  # 地精工程师 - 小搜索范围（非战斗型）
        }
        # 默认搜索范围
        return search_ranges.get(self.type, GameConstants.SEARCH_RANGE_IMP)

    def _get_wander_speed_multiplier(self) -> float:
        """根据怪物类型获取游荡速度倍数"""
        wander_speeds = {
            'imp': GameConstants.WANDER_SPEED_IMP,           # 小恶魔 - 标准游荡速度
            'gargoyle': GameConstants.WANDER_SPEED_GARGOYLE,      # 石像鬼 - 较慢（重型单位）
            'fire_salamander': GameConstants.WANDER_SPEED_FIRE_SALAMANDER,  # 火蜥蜴 - 较快
            'shadow_mage': GameConstants.WANDER_SPEED_SHADOW_MAGE,   # 暗影法师 - 较慢（施法者）
            'tree_guardian': GameConstants.WANDER_SPEED_TREE_GUARDIAN,  # 树人守护者 - 很慢（防守型）
            'shadow_lord': GameConstants.WANDER_SPEED_SHADOW_LORD,   # 暗影领主 - 快速
            'bone_dragon': GameConstants.WANDER_SPEED_BONE_DRAGON,   # 骨龙 - 很快（飞行单位）
            'hellhound': GameConstants.WANDER_SPEED_HELLHOUND,     # 地狱犬 - 快速
            'stone_golem': GameConstants.WANDER_SPEED_STONE_GOLEM,   # 石魔像 - 很慢（重型防守）
            'succubus': GameConstants.WANDER_SPEED_SUCCUBUS,      # 魅魔 - 较快
            'goblin_engineer': GameConstants.WANDER_SPEED_GOBLIN_ENGINEER,  # 地精工程师 - 较慢（非战斗型）
        }
        # 默认游荡速度
        return wander_speeds.get(self.type, GameConstants.WANDER_SPEED_IMP)

    def _attack_target(self, target: 'Creature', delta_time: float, effect_manager=None, camera_x: float = 0, camera_y: float = 0) -> bool:
        """攻击目标 - 统一的攻击逻辑"""
        if not target or target.health <= 0:
            return False

        # 计算基础伤害
        base_damage = self.attack
        damage_variance = int(base_damage * 0.15)  # 15%伤害浮动
        actual_damage = base_damage + \
            random.randint(-damage_variance, damage_variance)
        actual_damage = max(1, actual_damage)  # 确保至少1点伤害

        # 应用特殊伤害修正（子类可以重写）
        actual_damage = self._calculate_damage_modifiers(actual_damage, target)

        # 优先通过战斗系统处理攻击（包含击退效果和抖动特效）
        if hasattr(self, 'game_instance') and self.game_instance and hasattr(self.game_instance, 'combat_system'):
            # 通过战斗系统处理攻击，获得完整的击退效果和抖动特效
            game_logger.info(
                f"🎯 [ATTACK_DEBUG] {self.type} 攻击 {target.type} - 通过战斗系统处理")
            self.game_instance.combat_system._apply_damage(
                self, target, actual_damage)
            game_logger.info(
                f"⚔️ {self.name} 通过战斗系统攻击 {target.type}，造成 {actual_damage} 点伤害")
        else:
            # 备用方案：直接对目标造成伤害
            game_logger.info(
                f"🎯 [ATTACK_DEBUG] {self.type} 攻击 {target.type} - 使用备用方案（直接攻击）")
            game_logger.info(
                f"🎯 [ATTACK_DEBUG] game_instance存在: {hasattr(self, 'game_instance')}")
            game_logger.info(
                f"🎯 [ATTACK_DEBUG] game_instance不为空: {hasattr(self, 'game_instance') and self.game_instance is not None}")
            game_logger.info(
                f"🎯 [ATTACK_DEBUG] combat_system存在: {hasattr(self, 'game_instance') and self.game_instance and hasattr(self.game_instance, 'combat_system')}")

            target._take_damage(actual_damage, self)

            # 创建攻击特效
            if effect_manager:
                self._create_attack_effect(
                    target, actual_damage, effect_manager, camera_x, camera_y)

            game_logger.info(
                f"⚔️ {self.name} 直接攻击 {target.type}，造成 {actual_damage} 点伤害")

        return True

    def _calculate_damage_modifiers(self, base_damage: int, target: 'Creature') -> int:
        """计算伤害修正（子类可以重写）"""
        return base_damage

    def _create_attack_effect(self, target: 'Creature', damage: int, effect_manager, camera_x: float = 0, camera_y: float = 0) -> bool:
        """创建攻击特效 - 使用8大类特效系统"""
        # 根据怪物类型选择特效
        effect_type = self._get_attack_effect_type()

        if effect_type:
            # 计算攻击方向
            dx = target.x - self.x
            dy = target.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > 0:
                # 归一化方向向量
                dx /= distance
                dy /= distance

                # 将世界坐标转换为屏幕坐标
                screen_x = self.x - camera_x
                screen_y = self.y - camera_y
                target_screen_x = target.x - camera_x
                target_screen_y = target.y - camera_y

                # 计算屏幕坐标

                success = effect_manager.create_visual_effect(
                    effect_type=effect_type,
                    x=screen_x,
                    y=screen_y,
                    target_x=target_screen_x,
                    target_y=target_screen_y,
                    damage=damage
                )
                return success

        return False

    def _get_area_damage_config(self, creature_type: str) -> Optional[Dict]:
        """
        获取生物的范围伤害配置

        生物范围伤害配置说明：
        - radius: 范围半径（像素）
        - damage_ratio: 伤害比例（正数=伤害，负数=治疗）
        - type: 范围类型（'enemy'=只攻击敌人，'ally'=只治疗友军，'all'=攻击所有）
        - effect_type: 特效类型（用于视觉表现）

        Args:
            creature_type: 生物类型

        Returns:
            Optional[Dict]: 范围伤害配置，None表示无范围伤害
        """
        area_damage_configs = {
            # 火蜥蜴 - 火焰扇形范围伤害
            'fire_salamander': {
                'area_type': 'sector',  # 扇形攻击
                'radius': 80,  # 范围半径80像素
                'angle': 60,  # 扇形角度60度
                'damage_ratio': 0.6,  # 范围伤害为基础伤害的60%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'fire_breath'  # 使用火焰特效
            },

            # 骨龙 - 骨刺圆形范围伤害
            'bone_dragon': {
                'area_type': 'circle',  # 圆形攻击
                'radius': 100,  # 范围半径100像素
                'damage_ratio': 0.4,  # 范围伤害为基础伤害的40%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'spine_storm'  # 使用骨刺特效
            },

            # 地狱犬 - 火焰扇形范围伤害
            'hellhound': {
                'area_type': 'sector',  # 扇形攻击
                'radius': 40,  # 扇形半径40像素（与特效range一致）
                'angle': 60,  # 扇形角度60度
                'damage_ratio': 0.3,  # 范围伤害为基础伤害的30%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'flame_wave'
            }
        }

        return area_damage_configs.get(creature_type, None)

    def _get_attack_effect_type(self) -> str:
        """
        根据怪物类型获取攻击特效类型 - 映射到8大类特效系统

        特效分类：
        - 斩击类 (slash): 半月形圆弧 - 近战生物
        - 射击类 (projectile): 适当长度的短线条 - 远程生物
        - 魔法类 (magic): 直接作用于目标，圆形爆炸 - 法师生物
        - 火焰类 (flame): 前方扇形区域，粒子特效 - 火焰生物
        - 冲击类 (impact): 以自身为中心扩展冲击波 - 重击生物
        - 闪电类 (lightning): 连接目标与自身的电流折线 - 闪电生物
        - 爪击类 (claw): 3条半月形细曲线 - 野兽生物
        - 缠绕类 (entangle): 缠绕样式的弧形线条 - 自然生物

        Returns:
            str: 特效类型名称
        """
        effect_mapping = {
            # 爪击类 (claw) - 使用3条细曲线来模拟爪击
            'imp': 'claw_attack',              # 爪击类 - 橙色爪击
            'goblin_worker': 'beast_claw',     # 爪击类 - 棕色野兽爪（虽然苦工很少攻击）
            'gargoyle': 'beast_claw',          # 爪击类 - 棕色野兽爪
            'shadow_lord': 'shadow_claw',      # 爪击类 - 紫色暗影爪
            'stone_golem': 'beast_claw',       # 爪击类 - 棕色野兽爪

            # 射击类 (projectile) - 适当长度的短线条
            'goblin_engineer': 'arrow_shot',   # 射击类

            # 魔法类 (magic) - 直接作用于目标，圆形爆炸
            'shadow_mage': 'shadow_penetration',  # 魔法类
            'succubus': 'charm_effect',           # 魔法类

            # 火焰类 (flame) - 前方扇形区域，需要生成粒子特效
            'fire_salamander': 'fire_splash',     # 火焰类
            'hellhound': 'fire_breath',           # 火焰类

            # 冲击类 (impact) - 以自身为中心扩展冲击波
            'bone_dragon': 'spine_storm',         # 冲击类

            # 缠绕类 (entangle) - 直接作用于目标，缠绕样式的弧形线条
            'tree_guardian': 'vine_entangle'      # 缠绕类
        }
        return effect_mapping.get(self.type, 'melee_slash')

    def _is_melee_attack(self) -> bool:
        """判断是否为近战攻击"""
        melee_types = {
            'imp': True,
            'goblin_worker': True,
            'gargoyle': True,
            'fire_salamander': False,
            'shadow_mage': False,
            'tree_guardian': True,
            'shadow_lord': True,
            'bone_dragon': False,
            'hellhound': False,
            'stone_golem': True,
            'succubus': False,
            'goblin_engineer': False
        }
        return melee_types.get(self.type, True)  # 默认为近战

    def _take_damage(self, damage: int, attacker: Optional['Creature'] = None) -> None:
        """受到伤害"""
        self.health -= damage
        if self.health < 0:
            self.health = 0

        # 设置战斗状态
        import time
        current_time = time.time()
        self.in_combat = True
        self.last_combat_time = current_time

        # 触发被攻击响应（如果有攻击者）
        if attacker and hasattr(self, 'game_instance') and self.game_instance:
            self.game_instance.handle_unit_attacked_response(
                attacker, self, damage)

    def _regenerate_health(self, current_time: float) -> None:
        """回血处理"""
        if not hasattr(self, 'last_regeneration_time'):
            self.last_regeneration_time = 0

        # 每秒回血一次
        if current_time - self.last_regeneration_time >= 1.0:
            old_health = self.health
            self.health += self.regeneration_rate

            # 确保不超过最大生命值
            if self.health > self.max_health:
                self.health = self.max_health

            # 回血完成

            self.last_regeneration_time = current_time

    def _safe_move(self, new_x: float, new_y: float, game_map: List[List[Tile]]) -> bool:
        """安全移动 - 只有在目标位置可通行时才移动"""
        if self._can_move_to_position(new_x, new_y, game_map):
            self.x = new_x
            self.y = new_y
            return True
        return False

    def _can_move_to_position(self, new_x: float, new_y: float, game_map: List[List[Tile]]) -> bool:
        """检查是否可以移动到指定位置 - 检查环境碰撞，不检查单位碰撞"""
        # 转换为瓦片坐标
        tile_x = int(new_x // GameConstants.TILE_SIZE)
        tile_y = int(new_y // GameConstants.TILE_SIZE)

        # 边界检查
        if not (0 <= tile_x < GameConstants.MAP_WIDTH and 0 <= tile_y < GameConstants.MAP_HEIGHT):
            return False

        tile = game_map[tile_y][tile_x]
        # 只能在已挖掘的地块移动（地面或房间）
        # 注意：这里只检查环境碰撞，不检查单位碰撞
        # 单位碰撞由物理系统处理，不应该影响路径规划
        return tile.type == TileType.GROUND or tile.is_dug

    def _execute_attack(self, target: 'Creature', delta_time: float, effect_manager=None) -> bool:
        """执行攻击"""
        # 注意：攻击冷却时间检查应该在调用此方法之前进行
        # 这里直接执行攻击逻辑
        self._attack_target(target, delta_time, effect_manager)
        return True

    def _setup_special_physics_properties(self) -> None:
        """设置特殊物理属性"""
        # 根据怪物类型设置特殊物理属性
        if self.type == 'stone_golem':
            # 石魔像有岩石护盾，减少击退效果
            self.has_shield = True
        elif self.type == 'bone_dragon':
            # 骨龙飞行单位，有击退抗性
            pass  # 抗性在计算中处理
        elif self.type == 'tree_guardian':
            # 树人守护者可以扎根，免疫击退
            self.is_rooted = False  # 默认不扎根，可以通过技能激活
        elif self.type == 'shadow_lord':
            # 暗影领主有特殊免疫
            pass  # 可以添加特殊免疫

        # 其他怪物使用默认设置

    # ==================== 攻击列表管理 ====================

    def add_to_attack_list(self, target: 'Creature') -> bool:
        """将目标添加到攻击列表"""
        if not target or target.health <= 0:
            return False

        # 检查是否为敌对关系
        if not self._is_enemy_of(target):
            return False  # 不是敌人，不添加到攻击列表

        # 检查目标是否已在列表中
        if target in self.attack_list:
            return False  # 目标已在列表中

        self.attack_list.append(target)
        self.attack_list_last_update = time.time()

        return True

    def remove_from_attack_list(self, target: 'Creature') -> bool:
        """从攻击列表中移除目标"""
        if target in self.attack_list:
            self.attack_list.remove(target)
            self.attack_list_last_update = time.time()

            return True
        return False

    def clean_dead_targets(self) -> bool:
        """清理攻击列表中的死亡目标"""
        dead_targets = []
        for target in self.attack_list[:]:  # 使用切片复制避免修改迭代中的列表
            if not target or target.health <= 0:
                dead_targets.append(target)
                self.attack_list.remove(target)

        if dead_targets:
            self.attack_list_last_update = time.time()

        return len(dead_targets) > 0

    def get_nearest_target(self) -> Optional['Creature']:
        """获取攻击列表中距离最近的目标 - 优先攻击生物而不是建筑"""
        if not self.attack_list:
            return None

        # 分类目标：生物和建筑
        creature_targets = []
        building_targets = []

        for target in self.attack_list:
            if not target or target.health <= 0:
                continue

            # 计算距离
            dx = target.x - self.x
            dy = target.y - self.y
            distance = math.sqrt(dx * dx + dy * dy)

            # 区分生物和建筑
            is_building = hasattr(target, 'building_type')
            if is_building:
                building_targets.append((target, distance))
            else:
                creature_targets.append((target, distance))

        # 优先级1: 如果有生物目标，返回最近的生物
        if creature_targets:
            creature_targets.sort(key=lambda x: x[1])
            return creature_targets[0][0]

        # 优先级2: 如果没有生物目标，返回最近的建筑
        if building_targets:
            building_targets.sort(key=lambda x: x[1])
            return building_targets[0][0]

        return None

    def _is_enemy_of(self, target: 'Creature') -> bool:
        """判断目标是否为敌人 - 统一使用faction判断"""
        # 检查阵营 - 不同阵营即为敌人
        if hasattr(self, 'faction') and hasattr(target, 'faction'):
            return self.faction != target.faction

        # 如果目标没有faction属性，默认为敌人（兼容性考虑）
        return True
