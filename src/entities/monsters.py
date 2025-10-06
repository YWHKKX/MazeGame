#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
怪物实体模块
"""

import math
import random
from typing import List, Dict, Optional, Tuple, Any

# 导入需要的类型和配置
from src.core.constants import GameConstants, GameBalance
from src.core.enums import TileType, BuildMode
from src.core.game_state import Tile, GameState
from src.entities.configs import CreatureConfig
from src.utils.logger import game_logger
from src.managers.movement_system import MovementSystem
from src.entities.creature import Creature
from src.systems.skill_system import skill_manager


class Monster(Creature):
    def __init__(self, x: int, y: int, monster_type: str = 'imp'):
        # 调用父类构造函数
        super().__init__(x, y, monster_type)

        # 调试日志
        game_logger.info(
            f"🏗️ Monster.__init__ 被调用: {monster_type} at ({x}, {y})")

        # 怪物特有属性 - 统一阵营系统
        self.faction = "monsters"  # 怪物阵营

        # 怪物特有的初始化逻辑
        self._initialize_monster_specific_properties(monster_type)

        # 怪物特有的移动和状态属性
        self.target = None
        self.state = 'idle'
        self.last_attack = 0

        # 战斗目标追踪（统一初始化）
        self.current_target = None  # 当前攻击目标
        self.target_last_seen_time = 0  # 上次看到目标的时间
        self.target_search_cooldown = 0  # 目标搜索冷却

        # 状态切换器相关属性
        self.last_state_change_time = 0  # 上次状态改变的时间
        self.waiting_start_time = 0  # 开始等待的时间
        self.state_change_cooldown = 0.2  # 状态切换冷却时间（秒）- 优化为0.2秒
        self.waiting_timeout = 2.5  # 等待超时时间（秒）- 保持2.5秒

        # 状态缓存机制
        self._state_cache = {}  # 状态缓存
        self._last_state_check_time = 0  # 上次状态检查时间
        self._state_check_interval = 0.5  # 状态检查间隔（秒）
        self._consecutive_wandering_count = 0  # 连续游荡次数
        self._max_consecutive_wandering = 3  # 最大连续游荡次数

        # 设置特殊物理属性
        self._setup_special_physics_properties()

        # 战斗状态和回血系统
        self.in_combat = False
        self.last_combat_time = 0
        self.regeneration_rate = 1  # 每秒回血1点
        self.regeneration_delay = 10  # 脱离战斗10秒后开始回血

        # 攻击列表管理（继承自Creature，但可以重写方法）
        # 注意：attack_list已在父类Creature中初始化

        # 怪物范围伤害配置（覆盖父类配置）
        self.area_damage = self._get_monster_area_damage_config(monster_type)

        # 技能系统
        self.skills = []  # 技能列表
        self.mana = 50   # 法力值
        self.max_mana = 50  # 最大法力值
        self.mana_regen_rate = 1  # 每秒恢复法力值
        self.last_mana_regen = 0  # 上次恢复法力值时间

        # 为怪物分配技能
        self._assign_monster_skills(monster_type)

    def _initialize_monster_specific_properties(self, monster_type: str):
        """初始化怪物特有的属性"""
        # 注意：基础属性（size, health, attack等）已经在父类Creature中初始化
        # 这里只需要处理怪物特有的逻辑

        # 如果父类没有正确初始化怪物数据，则使用CreatureConfig作为后备
        if not hasattr(self, 'character_data') or self.character_data is None:
            try:
                if monster_type not in CreatureConfig.TYPES:
                    game_logger.info(
                        f"⚠️ 警告: 怪物类型 '{monster_type}' 不存在于CreatureConfig中，使用默认配置")
                    monster_type = 'imp'  # 回退到默认类型
                config = CreatureConfig.TYPES[monster_type]
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
                game_logger.info(f"✅ 使用CreatureConfig初始化怪物: {monster_type}")
            except Exception as e:
                game_logger.info(f"❌ 怪物配置初始化错误: {e}")
                # 使用最基本的默认配置
                self.size = 15
                self.health = 100
                self.max_health = 100
                self.attack = 20
                self.speed = 30
                self.color = (255, 107, 107)
                self.armor = 0
                self.attack_range = 30
                self.attack_cooldown = 1.0
                self.special_ability = "无"

    def update(self, delta_time: float, creatures: List, game_map: List[List[Tile]], effect_manager=None, building_manager=None, heroes: List = None):
        """
        更新怪物状态 - 怪物特有的AI逻辑

        Args:
            delta_time: 时间增量（秒）
        """
        import time
        current_time = time.time()

        # 更新搜索冷却时间
        if self.target_search_cooldown > 0:
            self.target_search_cooldown -= delta_time

        # 更新技能系统
        self.update_skills(delta_time, game_instance=getattr(
            self, 'game_instance', None))

        # 恢复法力值
        self._regenerate_mana(delta_time)

        # 状态切换器 - 检查是否需要从等待状态切换到游荡状态
        self._update_state_switcher(current_time, game_map)

        # 注意：攻击和移动逻辑现在由CombatSystem统一处理
        # 这里只处理非战斗的AI逻辑

        # 如果不在战斗中，进行探索
        if not self.in_combat:
            # 优先级1: 探索地牢之心
            if hasattr(self, 'known_dungeon_heart') and self.known_dungeon_heart:
                self.state = 'exploring'
                # 不直接移动，让CombatSystem处理
                return

            # 优先级2: 随机探索
            self.state = 'patrolling'
            # 不直接移动，让CombatSystem处理

    def _execute_attack(self, target: 'Creature', delta_time: float, effect_manager=None) -> bool:
        """执行攻击"""
        # 注意：攻击冷却时间检查应该在调用此方法之前进行
        # 这里直接执行攻击逻辑
        self._attack_target(target, delta_time, effect_manager)
        return True

    def _find_nearest_hero(self, heroes: List['Creature'], max_distance: float) -> Optional['Creature']:
        """寻找最近的英雄"""
        nearest_hero = None
        nearest_distance = float('inf')

        for hero in heroes:
            distance = math.sqrt((hero.x - self.x) **
                                 2 + (hero.y - self.y) ** 2)
            if distance < max_distance and distance < nearest_distance:
                nearest_distance = distance
                nearest_hero = hero

        return nearest_hero

    def _find_highest_threat_creature(self, creatures: List['Creature'], max_distance: float) -> Optional['Creature']:
        """寻找威胁最大的敌方生物 - 按照COMBAT_SYSTEM.md威胁评估"""
        highest_threat_creature = None
        highest_threat_score = -1

        for creature in creatures:
            # 跳过非战斗单位
            if hasattr(creature, 'is_combat_unit') and not creature.is_combat_unit:
                continue

            # 跳过非敌方单位（怪物不应该攻击其他怪物）
            if not hasattr(creature, 'is_enemy') or creature.is_enemy:
                continue

            distance = math.sqrt(
                (creature.x - self.x) ** 2 + (creature.y - self.y) ** 2)

            if distance <= max_distance:
                # 计算威胁分数：攻击力越高威胁越大，距离越近威胁越大
                threat_score = creature.attack / (distance + 1)  # +1避免除零

                if threat_score > highest_threat_score:
                    highest_threat_score = threat_score
                    highest_threat_creature = creature

        return highest_threat_creature

    def _attack_target(self, target: 'Creature', delta_time: float, effect_manager=None, camera_x: float = 0, camera_y: float = 0) -> bool:
        """攻击目标 - 已废弃，攻击逻辑已移至游戏主循环"""
        # 此方法已废弃，攻击逻辑现在由游戏主循环的_execute_attack_with_rules方法处理
        # 保留此方法仅为兼容性考虑
        return False

    def _create_attack_effect(self, target: 'Creature', damage: int, effect_manager, camera_x: float = 0, camera_y: float = 0) -> bool:
        """创建攻击特效 - 使用8大类特效系统"""
        game_logger.info(
            f"🔥 怪物 {self.type} 尝试创建攻击特效，目标: {target.type}, 伤害: {damage}")

        # 根据怪物类型选择特效
        effect_type = self._get_attack_effect_type()
        game_logger.info(f"   特效类型: {effect_type}")

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

                game_logger.info(
                    f"   世界坐标: 怪物({self.x:.1f}, {self.y:.1f})px, 目标({target.x:.1f}, {target.y:.1f})px")
                game_logger.info(
                    f"   屏幕坐标: 怪物({screen_x:.1f}, {screen_y:.1f})px, 目标({target_screen_x:.1f}, {target_screen_y:.1f})px")

                success = effect_manager.create_visual_effect(
                    effect_type=effect_type,
                    x=screen_x,
                    y=screen_y,
                    target_x=target_screen_x,
                    target_y=target_screen_y,
                    damage=damage
                )
                game_logger.info(f"   特效创建结果: {success}")
                return success
        else:
            game_logger.info(f"   未找到怪物类型 {self.type} 对应的特效类型")

        return False

    def _get_monster_area_damage_config(self, monster_type: str) -> Optional[Dict]:
        """
        获取怪物的范围伤害配置

        怪物范围伤害配置说明：
        - radius: 范围半径（像素）
        - damage_ratio: 伤害比例（正数=伤害，负数=治疗）
        - type: 范围类型（'enemy'=只攻击敌人，'ally'=只治疗友军，'all'=攻击所有）
        - effect_type: 特效类型（用于视觉表现）

        Args:
            monster_type: 怪物类型

        Returns:
            Optional[Dict]: 范围伤害配置，None表示无范围伤害
        """
        monster_area_damage_configs = {
            # 火蜥蜴 - 火焰扇形范围伤害
            'fire_salamander': {
                'radius': 120,  # 范围半径120像素
                'damage_ratio': 0.7,  # 范围伤害为基础伤害的70%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'fire_breath'  # 使用火焰特效
            },

            # 骨龙 - 骨刺圆形范围伤害
            'bone_dragon': {
                'radius': 100,  # 范围半径100像素
                'damage_ratio': 0.4,  # 范围伤害为基础伤害的40%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'spine_storm'  # 使用骨刺特效
            },

            # 暗影领主 - 暗影范围伤害
            'shadow_lord': {
                'radius': 90,  # 范围半径90像素
                'damage_ratio': 0.5,  # 范围伤害为基础伤害的50%
                'type': 'enemy',  # 只攻击敌人
                'effect_type': 'shadow_blast'  # 使用暗影特效
            }
        }

        return monster_area_damage_configs.get(monster_type, None)

    def _get_attack_effect_type(self) -> str:
        """
        根据怪物类型获取攻击特效类型 - 映射到8大类特效系统

        特效分类：
        - 斩击类 (slash): 半月形圆弧 - 近战怪物
        - 射击类 (projectile): 适当长度的短线条 - 远程怪物
        - 魔法类 (magic): 直接作用于目标，圆形爆炸 - 法师怪物

        Returns:
            str: 特效类型名称
        """
        effect_mapping = {
            # 斩击类 (slash) - 半月形圆弧
            'imp': 'claw_attack',              # 斩击类
            'goblin_worker': 'beast_claw',     # 斩击类
            'goblin_engineer': 'arrow_shot',   # 射击类
            'orc_warrior': 'melee_heavy',      # 斩击类
            'gargoyle': 'beast_claw',          # 斩击类
            'shadow_lord': 'shadow_claw',      # 斩击类
            'stone_golem': 'beast_claw',       # 斩击类

            # 射击类 (projectile) - 适当长度的短线条
            'fire_salamander': 'fire_splash',     # 火焰类
            'hellhound': 'fire_breath',           # 火焰类

            # 魔法类 (magic) - 直接作用于目标，圆形爆炸
            'shadow_mage': 'shadow_penetration',  # 魔法类
            'succubus': 'charm_effect',           # 魔法类
            'bone_dragon': 'spine_storm',         # 冲击类
            'tree_guardian': 'vine_entangle'      # 缠绕类
        }
        return effect_mapping.get(self.type, 'melee_slash')

    def _is_melee_attack(self) -> bool:
        """判断是否为近战攻击"""
        melee_types = {
            'imp': True,
            'goblin_worker': True,
            'goblin_engineer': False,
            'orc_warrior': True,
            'gargoyle': True,
            'fire_salamander': False,
            'shadow_mage': False,
            'tree_guardian': True,
            'shadow_lord': True,
            'bone_dragon': False,
            'hellhound': False,
            'stone_golem': True,
            'succubus': False
        }
        return melee_types.get(self.type, True)  # 默认为近战

    def _take_damage(self, damage: int, attacker: Optional['Creature'] = None) -> None:
        """怪物受到伤害"""
        old_health = self.health
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

        # 怪物特有：如果被敌方攻击，将攻击者添加到攻击列表
        if attacker and hasattr(attacker, 'is_enemy') and not attacker.is_enemy:
            # 这里可以调用战斗系统的方法来添加攻击目标
            # 暂时通过设置current_target来实现
            self.current_target = attacker
            self.target_last_seen_time = current_time

        # 检查是否死亡，触发死亡技能
        if old_health > 0 and self.health <= 0:
            self._on_death()

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

            # 如果有实际回血，打印信息
            if self.health > old_health:
                game_logger.info(
                    f"💚 {self.type} 回血 {self.health - old_health} 点，当前生命值: {self.health}/{self.max_health}")

            self.last_regeneration_time = current_time

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

    def _update_state_switcher(self, current_time: float, game_map: List[List[Tile]]):
        """
        状态切换器 - 检查是否需要从等待状态切换到游荡状态（优化版本）

        Args:
            current_time: 当前时间
            game_map: 游戏地图
        """
        # 检查状态检查间隔，避免过于频繁的检查
        if current_time - self._last_state_check_time < self._state_check_interval:
            return

        self._last_state_check_time = current_time

        # 检查状态切换冷却时间
        if current_time - self.last_state_change_time < self.state_change_cooldown:
            return

        # 定义等待状态列表（排除wandering，避免wandering->wandering的循环）
        waiting_states = ['idle', 'waiting', 'patrolling', 'exploring']

        # 检查当前状态是否为等待状态
        if self.state in waiting_states:
            # 如果还没有记录等待开始时间，记录它
            if self.waiting_start_time == 0:
                self.waiting_start_time = current_time
                game_logger.debug(f"🕐 {self.type} 开始等待状态: {self.state}")

            # 检查是否超过等待超时时间
            waiting_duration = current_time - self.waiting_start_time
            if waiting_duration >= self.waiting_timeout:
                # 检查连续游荡次数，避免过度游荡
                if self._consecutive_wandering_count >= self._max_consecutive_wandering:
                    game_logger.debug(f"⚠️ {self.type} 连续游荡次数过多，跳过此次切换")
                    # 延长等待时间，避免频繁切换
                    self.waiting_start_time = current_time - self.waiting_timeout + 1.0
                    self._consecutive_wandering_count = 0
                    return

                # 切换到游荡状态
                old_state = self.state
                self.state = 'wandering'
                self.last_state_change_time = current_time

                # 缓存状态切换信息
                state_key = f"{old_state}_to_wandering"
                if state_key not in self._state_cache:
                    self._state_cache[state_key] = []

                self._state_cache[state_key].append({
                    'timestamp': current_time,
                    'duration': waiting_duration
                })

                # 保持缓存大小合理（只保留最近10次记录）
                if len(self._state_cache[state_key]) > 10:
                    self._state_cache[state_key] = self._state_cache[state_key][-10:]

                # 增加连续游荡计数
                if old_state == 'wandering':
                    self._consecutive_wandering_count += 1
                else:
                    self._consecutive_wandering_count = 1

                game_logger.info(
                    f"🎲 {self.type} 等待超时({waiting_duration:.1f}s)，从 {old_state} 切换到 {self.state} (连续游荡: {self._consecutive_wandering_count})")

                # 触发游荡行为
                self._start_wandering_behavior(current_time, game_map)

                # 重置等待开始时间，给游荡状态足够的时间
                self.waiting_start_time = 0
        else:
            # 不在等待状态，重置等待开始时间和连续游荡计数
            if self.waiting_start_time != 0:
                self.waiting_start_time = 0
            if self._consecutive_wandering_count > 0:
                self._consecutive_wandering_count = 0

    def _start_wandering_behavior(self, current_time: float, game_map: List[List[Tile]]):
        """
        开始游荡行为

        Args:
            current_time: 当前时间
            game_map: 游戏地图
        """
        # 子类可以重写此方法来实现特定的游荡行为
        # 默认实现：使用MovementSystem的游荡功能
        try:
            # 使用移动系统的游荡功能
            MovementSystem.start_wandering_phase(self, game_map)
            game_logger.debug(f"🎲 {self.type} 开始游荡行为")
        except Exception as e:
            game_logger.warning(f"⚠️ {self.type} 游荡行为启动失败: {e}")

    def get_state_cache_stats(self) -> Dict[str, Any]:
        """
        获取状态缓存统计信息

        Returns:
            包含状态切换统计信息的字典
        """
        stats = {
            'total_switches': 0,
            'switch_types': {},
            'average_duration': 0.0,
            'consecutive_wandering_count': self._consecutive_wandering_count,
            'cache_size': len(self._state_cache)
        }

        total_duration = 0.0
        total_switches = 0

        for state_key, records in self._state_cache.items():
            stats['switch_types'][state_key] = len(records)
            stats['total_switches'] += len(records)
            total_switches += len(records)

            for record in records:
                total_duration += record['duration']

        if total_switches > 0:
            stats['average_duration'] = total_duration / total_switches

        return stats

    def clear_state_cache(self):
        """清理状态缓存"""
        self._state_cache.clear()
        self._consecutive_wandering_count = 0
        game_logger.debug(f"🧹 {self.type} 状态缓存已清理")

    def _safe_move(self, new_x: float, new_y: float, game_map: List[List[Tile]]) -> bool:
        """安全移动 - 只有在目标位置可通行时才移动"""
        if self._can_move_to_position(new_x, new_y, game_map):
            self.x = new_x
            self.y = new_y
            return True
        return False

    def _can_move_to_position(self, new_x: float, new_y: float, game_map: List[List[Tile]]) -> bool:
        """检查怪物是否可以移动到指定位置 - 怪物只能在已挖掘地块移动"""
        # 转换为瓦片坐标
        tile_x = int(new_x // GameConstants.TILE_SIZE)
        tile_y = int(new_y // GameConstants.TILE_SIZE)

        # 边界检查
        if not (0 <= tile_x < GameConstants.MAP_WIDTH and 0 <= tile_y < GameConstants.MAP_HEIGHT):
            return False

        tile = game_map[tile_y][tile_x]
        # 怪物只能在已挖掘的地块移动
        return tile.type == TileType.GROUND or tile.is_dug

    def _assign_monster_skills(self, monster_type: str):
        """为怪物分配技能"""
        game_logger.info(f"🎯 开始为怪物 {self.name} (类型: {monster_type}) 分配技能")

        skill_assignments = {
            'imp': ['flame_explosion'],
            'orc_warrior': ['whirlwind_slash'],
            'goblin_worker': [],
            'goblin_engineer': [],
            'gargoyle': [],
            'fire_salamander': [],
            'shadow_mage': [],
            'tree_guardian': [],
            'shadow_lord': [],
            'bone_dragon': [],
            'hellhound': [],
            'stone_golem': [],
            'succubus': []
        }

        skills_to_assign = skill_assignments.get(monster_type, [])
        game_logger.info(f"🎯 怪物 {self.name} 的技能列表: {skills_to_assign}")

        for skill_id in skills_to_assign:
            game_logger.info(f"🎯 为 {self.name} 分配技能: {skill_id}")
            skill_manager.assign_skill_to_unit(self, skill_id)

        # 更新本地技能列表
        self.skills = skill_manager.get_unit_skills(self)
        game_logger.info(
            f"🎯 为 {self.name} 分配了 {len(self.skills)} 个技能: {[skill.name for skill in self.skills]}")

        # 调试：检查技能管理器中的技能
        unit_id = id(self)
        if unit_id in skill_manager.unit_skills:
            game_logger.info(
                f"🔍 技能管理器中 {self.name} 的技能: {[skill.name for skill in skill_manager.unit_skills[unit_id]]}")
        else:
            game_logger.warning(f"⚠️ 技能管理器中未找到 {self.name} 的技能记录！")

    def use_skill(self, skill_id: str, target=None, **kwargs) -> bool:
        """使用技能"""
        return skill_manager.use_skill(self, skill_id, target, **kwargs)

    def get_available_skills(self) -> List:
        """获取可用的技能列表"""
        return skill_manager.get_available_skills(self)

    def update_skills(self, delta_time: float, game_instance=None):
        """更新技能状态"""
        skill_manager.update_skills(self, delta_time)

        # 更新多重射击等需要持续更新的技能
        for skill in self.skills:
            if hasattr(skill, 'update_skill') and skill.is_charging:
                skill.update_skill(self, self.current_target, game_instance)

    def _regenerate_mana(self, delta_time: float):
        """恢复法力值"""
        import time
        current_time = time.time()
        if current_time - self.last_mana_regen >= 1.0:  # 每秒恢复一次
            if self.mana < self.max_mana:
                old_mana = self.mana
                self.mana = min(self.max_mana, self.mana +
                                self.mana_regen_rate)
                if self.mana > old_mana:
                    game_logger.info(
                        f"💙 {self.name} 恢复了 {self.mana - old_mana} 点法力值 ({self.mana}/{self.max_mana})")
            self.last_mana_regen = current_time

    def _on_death(self):
        """怪物死亡时触发被动技能"""
        # 检查是否有烈焰自爆等死亡触发技能
        for skill in self.skills:
            if hasattr(skill, 'skill_id') and skill.skill_id == 'flame_explosion':
                # 触发烈焰自爆
                game_instance = getattr(self, 'game_instance', None)
                if game_instance:
                    game_logger.info(f"💥 {self.name} 死亡时触发烈焰自爆技能")
                    skill.execute_skill(self, game_instance=game_instance)
                else:
                    game_logger.warning(
                        f"⚠️ {self.name} 死亡时无法触发技能：缺少 game_instance")
                break
