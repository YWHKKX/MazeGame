#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
战斗系统
处理所有战斗相关的逻辑，包括攻击、反击、逃跑、战斗状态管理等
"""

import time
import math
import random
from typing import Optional, Dict, Any
from typing import Any, Optional, List, Tuple
from src.core.constants import GameConstants
from src.core.enums import AttackType
from src.utils.logger import game_logger
from src.managers.movement_system import MovementSystem
from src.entities.building import BuildingStatus
from src.systems.advanced_area_damage import get_advanced_area_damage_system
from src.systems.skill_system import skill_manager


class CombatSystem:
    """战斗系统 - 处理战斗相关的逻辑"""

    def __init__(self):
        """初始化战斗系统"""
        self._debug_mode = False  # 调试模式开关
        self.game_instance = None   # 游戏实例引用

    def set_game_instance(self, game_instance):
        """设置游戏实例引用"""
        self.game_instance = game_instance

    def set_debug_mode(self, enabled: bool):
        """设置调试模式"""
        self._debug_mode = enabled

    # ==================== 攻击列表管理 ====================
    # 注意：攻击列表管理现在由Creature和Hero类自己处理

    def handle_unit_attacked_response(self, attacker, target, damage: float):
        """
        处理单位被攻击时的响应逻辑

        Args:
            attacker: 攻击者
            target: 被攻击的目标
            damage: 受到的伤害
        """
        if not target or target.health <= 0 or not self.game_instance:
            return

        # 检查是否为敌对关系
        is_enemy = self._is_enemy_of(attacker, target)

        if not is_enemy:
            return  # 不是敌人，不触发反击

        # 判断目标单位类型并执行相应的响应
        if self._is_combat_unit(target):
            # 战斗单位（英雄和战斗怪物）：将攻击者添加到攻击列表
            target.add_to_attack_list(attacker)
            game_logger.info(f"🎯 战斗单位 {target.type} 将 {attacker.type} 添加到攻击列表")

        elif self._is_functional_unit(target):
            # 功能性单位（苦工和工程师）：立刻逃跑远离攻击者
            self._make_functional_unit_flee(target, attacker)

    def _is_friendly_building(self, building) -> bool:
        """判断是否为友方建筑（玩家拥有的建筑）"""
        if not hasattr(building, 'building_type'):
            return False

        # 友方建筑类型
        friendly_building_types = {
            'dungeon_heart',    # 地牢之心
            'treasury',         # 金库
            'magic_altar',      # 魔法祭坛
            'arrow_tower',      # 箭塔
            'training_room',   # 训练室
            'library',         # 图书馆
            'workshop',        # 工坊
            'prison',          # 监狱
            'torture_chamber',  # 刑房
            'defense_fortification',  # 防御工事
            'shadow_temple',   # 暗影神殿
            'magic_research_institute',  # 魔法研究院
            'orc_lair',        # 兽人巢穴
            'demon_lair',      # 恶魔巢穴
        }

        return building.building_type.value in friendly_building_types

    def _is_combat_unit(self, unit) -> bool:
        """判断是否为战斗单位"""
        # 检查is_combat_unit属性
        if hasattr(unit, 'is_combat_unit'):
            return unit.is_combat_unit

        # 英雄总是战斗单位
        if hasattr(unit, 'is_hero') and unit.is_hero:
            return True

        # 根据怪物类型判断
        combat_monsters = ['imp', 'gargoyle', 'fire_salamander', 'shadow_mage',
                           'tree_guardian', 'shadow_lord', 'bone_dragon', 'hellhound',
                           'stone_golem', 'succubus', 'orc_warrior']

        if hasattr(unit, 'type') and unit.type in combat_monsters:
            return True

        return False

    def _is_enemy_of(self, unit1, unit2) -> bool:
        """判断两个单位是否为敌对关系 - 统一使用faction判断"""
        # 检查阵营 - 不同阵营即为敌人
        if hasattr(unit1, 'faction') and hasattr(unit2, 'faction'):
            return unit1.faction != unit2.faction

        # 如果目标没有faction属性，默认为敌人（兼容性考虑）
        return True

    def _is_functional_unit(self, unit) -> bool:
        """判断是否为功能性单位"""
        # 苦工和工程师是功能性单位
        if hasattr(unit, 'type') and unit.type in ['goblin_worker', 'goblin_engineer']:
            return True

        # 检查is_combat_unit属性
        if hasattr(unit, 'is_combat_unit'):
            return not unit.is_combat_unit

        return False

    def _set_combat_unit_target(self, target, attacker):
        """设置战斗单位的目标为攻击者"""
        if not target or not attacker or not self.game_instance:
            return

        # 设置当前目标为攻击者
        target.current_target = attacker
        target.target_last_seen_time = time.time()

        # 对于战斗单位，应该移动到攻击者附近进行反击
        if hasattr(attacker, 'x') and hasattr(attacker, 'y'):
            # 获取攻击者的像素坐标
            # 注意：Building类的x,y已经是像素坐标，不需要再次转换
            attacker_pixel_x = attacker.x
            attacker_pixel_y = attacker.y

            # 计算到攻击者的距离
            dx = attacker_pixel_x - target.x
            dy = attacker_pixel_y - target.y
            distance_to_attacker = math.sqrt(dx * dx + dy * dy)

            # 获取目标的攻击范围
            target_attack_range = getattr(
                target, 'attack_range', GameConstants.DEFAULT_ATTACK_RANGE)

            # 检查是否需要设置新的移动目标
            needs_new_target = False

            # 如果没有移动目标，或者距离攻击者太远，需要设置新目标
            if not hasattr(target, 'has_movement_target') or not target.has_movement_target:
                needs_new_target = True
            elif distance_to_attacker > target_attack_range + GameConstants.TARGET_SWITCH_BUFFER:  # 给更大的缓冲距离，避免频繁重新设置目标
                needs_new_target = True

            # 如果距离攻击者太远，移动到攻击者的攻击范围内
            if needs_new_target and distance_to_attacker > target_attack_range:
                # 标准化方向向量（从目标指向攻击者）
                dx /= distance_to_attacker
                dy /= distance_to_attacker

                # 计算接近位置：从当前位置向攻击者方向移动
                approach_distance = distance_to_attacker - \
                    target_attack_range + GameConstants.APPROACH_BUFFER  # 移动到攻击范围内，给一些缓冲
                target_x = target.x + dx * approach_distance
                target_y = target.y + dy * approach_distance

                # 使用MovementSystem设置移动目标
                if self.game_instance and hasattr(self.game_instance, 'game_map'):
                    MovementSystem.target_seeking_movement(
                        target, (target_x, target_y), GameConstants.DELTA_TIME_DEFAULT, self.game_instance.game_map, speed_multiplier=GameConstants.DEFAULT_SPEED_MULTIPLIER)

        # 设置反击状态
        target.in_combat = True
        target.state = 'fighting'

    def _make_functional_unit_flee(self, target, attacker):
        """让功能性单位逃跑远离攻击者"""
        if not target or not attacker or not self.game_instance:
            return

        # 计算逃跑方向（远离攻击者的方向）
        dx = target.x - attacker.x
        dy = target.y - attacker.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > 0:
            # 标准化方向向量
            dx /= distance
            dy /= distance

            # 计算逃跑目标位置（远离攻击者）
            flee_distance = GameConstants.FLEE_DISTANCE
            flee_x = target.x + dx * flee_distance
            flee_y = target.y + dy * flee_distance

            # 确保逃跑目标在地图范围内
            if self.game_instance and hasattr(self.game_instance, 'game_map'):
                map_width = len(
                    self.game_instance.game_map[0]) * GameConstants.TILE_SIZE
                map_height = len(self.game_instance.game_map) * \
                    GameConstants.TILE_SIZE
                flee_x = max(GameConstants.MAP_BORDER_BUFFER, min(
                    flee_x, map_width - GameConstants.MAP_BORDER_BUFFER))
                flee_y = max(GameConstants.MAP_BORDER_BUFFER, min(
                    flee_y, map_height - GameConstants.MAP_BORDER_BUFFER))

                # 使用MovementSystem设置逃跑目标
                MovementSystem.target_seeking_movement(
                    target, (flee_x, flee_y), GameConstants.DELTA_TIME_DEFAULT, self.game_instance.game_map, speed_multiplier=GameConstants.COMBAT_SPEED_MULTIPLIER)

        # 设置逃跑状态
        target.state = 'fleeing'

    # ==================== 主要战斗处理方法 ====================

    def handle_combat(self, delta_time: float, creatures: List, heroes: List, building_manager=None):
        """
        处理战斗系统 - 主要入口点

        战斗系统处理流程：
        1. 验证输入参数和游戏状态
        2. 检测敌人并更新攻击列表
        3. 处理战斗单位的攻击和移动
        4. 处理非战斗单位的移动
        5. 处理生命值恢复

        Args:
            delta_time: 时间增量
            creatures: 生物列表
            heroes: 英雄列表
            building_manager: 建筑管理器
        """
        # 输入验证和早期返回
        if not self._validate_inputs(delta_time, creatures, heroes):
            return

        current_time = time.time()

        try:
            # 性能统计（可选）
            if hasattr(self, '_debug_mode') and self._debug_mode:
                start_time = time.time()

            # 阶段1: 战斗检测和状态更新
            self._phase_combat_detection(
                creatures, heroes, current_time, building_manager)

            # 阶段2: 战斗单位处理（包含建筑攻击）
            self._phase_combat_units(
                creatures, heroes, delta_time, current_time, building_manager)

            # 阶段3: 非战斗单位处理
            self._phase_non_combat_units(creatures, heroes, delta_time)

            # 阶段4: 生命值恢复
            self._phase_health_regeneration(creatures, heroes, current_time)

            # 性能统计（可选）
            if hasattr(self, '_debug_mode') and self._debug_mode:
                end_time = time.time()
                processing_time = (end_time - start_time) * 1000  # 转换为毫秒
                if processing_time > GameConstants.FRAME_TIME_MS:  # 超过一帧的时间
                    game_logger.info(f"⚠️ 战斗系统处理时间过长: {processing_time:.2f}ms")

        except Exception as e:
            game_logger.info(f"❌ 战斗系统处理错误: {e}")
            # 记录错误但不中断游戏

    def _validate_inputs(self, delta_time: float, creatures: List, heroes: List) -> bool:
        """验证输入参数的有效性"""
        if delta_time <= 0:
            return False

        if not creatures and not heroes:
            return False

        if not self.game_instance:
            return False

        return True

    def _phase_combat_detection(self, creatures: List, heroes: List, current_time: float, building_manager=None):
        """阶段1: 战斗检测和状态更新"""
        # 过滤有效的战斗单位
        valid_creatures = [
            c for c in creatures if c and c.health > 0 and self._is_combat_unit(c)]
        valid_heroes = [h for h in heroes if h and h.health > 0]

        # 使用完整的战斗检测方法
        if valid_creatures or valid_heroes:
            self._detect_and_add_enemies_to_attack_lists(
                valid_creatures, valid_heroes, current_time, building_manager)

    def _phase_combat_units(self, creatures: List, heroes: List, delta_time: float, current_time: float, building_manager=None):
        """阶段2: 战斗单位处理（包含建筑攻击）"""
        # 过滤有效的战斗单位
        valid_creatures = [
            c for c in creatures if c and c.health > 0 and self._is_combat_unit(c)]
        valid_heroes = [h for h in heroes if h and h.health > 0]

        # 处理所有单位的攻击逻辑
        if valid_creatures or valid_heroes:
            self._process_attack_lists(
                valid_creatures, valid_heroes, delta_time, current_time)

        # 处理英雄攻击建筑物（整合自_phase_building_combat）
        if valid_heroes and building_manager:
            self._handle_hero_attack_buildings(
                valid_heroes, building_manager, current_time, delta_time)

    def _phase_non_combat_units(self, creatures: List, heroes: List, delta_time: float):
        """阶段3: 非战斗单位处理"""
        # 过滤有效的非战斗单位
        valid_creatures = [c for c in creatures if c and c.health > 0]
        valid_heroes = [h for h in heroes if h and h.health > 0]

        # 处理非战斗单位的移动
        if valid_creatures or valid_heroes:
            self._handle_non_combat_movement(
                valid_creatures, valid_heroes, delta_time)

    def _phase_health_regeneration(self, creatures: List, heroes: List, current_time: float):
        """阶段4: 生命值恢复"""
        # 过滤有效的单位
        valid_creatures = [c for c in creatures if c and c.health > 0]
        valid_heroes = [h for h in heroes if h and h.health > 0]

        # 处理回血系统
        if valid_creatures or valid_heroes:
            self._handle_health_regeneration(
                valid_creatures, valid_heroes, current_time)

    def _handle_non_combat_movement(self, creatures: List, heroes: List, delta_time: float):
        """处理非战斗单位的移动 - 使用MovementSystem接口"""
        if not self.game_instance or not hasattr(self.game_instance, 'game_map'):
            return

        # 处理非战斗状态的英雄
        for hero in heroes[:]:
            if not hero.in_combat:
                if hero.state == 'exploring' and hasattr(hero, 'known_dungeon_heart') and hero.known_dungeon_heart:
                    # 探索地牢之心
                    MovementSystem.target_seeking_movement(
                        hero, hero.known_dungeon_heart, delta_time, self.game_instance.game_map)
                elif hero.state == 'patrolling':
                    # 随机探索
                    MovementSystem.wandering_movement(
                        hero, delta_time, self.game_instance.game_map, GameConstants.PATROL_SPEED_MULTIPLIER)

        # 处理非战斗状态的生物
        for creature in creatures[:]:
            if not creature.in_combat and self._is_combat_unit(creature):
                if creature.state == 'fleeing' and creature.health <= creature.max_health * GameConstants.FLEE_HEALTH_THRESHOLD:
                    # 血量过低时撤退
                    # 寻找最近的英雄并逃离
                    for hero in self.game_instance.heroes:
                        if hero.health > 0:
                            MovementSystem.flee_movement(
                                creature, (hero.x, hero.y), delta_time, self.game_instance.game_map)
                            break
                elif creature.state == 'wandering':
                    # 游荡巡逻
                    wander_speed = creature._get_wander_speed_multiplier() if hasattr(
                        creature, '_get_wander_speed_multiplier') else GameConstants.WANDER_SPEED_MULTIPLIER
                    MovementSystem.wandering_movement(
                        creature, delta_time, self.game_instance.game_map, wander_speed)

    def _handle_combat_pursuit(self, unit, target, delta_time: float, distance: float):
        """处理战斗追击 - 当单位在追击范围内但不在攻击范围内时主动追击"""
        # 跳过非战斗单位
        if hasattr(unit, 'is_combat_unit') and not unit.is_combat_unit:
            return

        # 检查目标是否死亡或被摧毁
        target_destroyed = False
        if hasattr(target, 'health'):
            target_destroyed = target.health <= 0
        elif hasattr(target, 'is_active'):
            target_destroyed = not target.is_active
        elif hasattr(target, 'status'):
            # 检查建筑状态
            target_destroyed = target.status == BuildingStatus.DESTROYED

        if target_destroyed:
            unit.in_combat = False
            # 从攻击列表中移除目标
            if hasattr(unit, 'attack_list') and target in unit.attack_list:
                unit.attack_list.remove(target)
            unit.state = 'wandering' if hasattr(unit, 'type') and unit.type in [
                'imp', 'gargoyle'] else 'exploring'
            return

        if unit.health <= 0:
            return

        # 获取攻击范围
        unit_attack_range = getattr(
            unit, 'attack_range', GameConstants.DEFAULT_ATTACK_RANGE)

        # 如果单位不在攻击范围内，主动追击目标
        if distance > unit_attack_range and unit.in_combat:
            unit.state = 'moving'
            # 使用移动系统追击目标
            if self.game_instance and hasattr(self.game_instance, 'game_map'):
                MovementSystem.target_seeking_movement(
                    unit, (target.x,
                           target.y), delta_time, self.game_instance.game_map,
                    speed_multiplier=GameConstants.COMBAT_SPEED_MULTIPLIER)

    def _detect_and_add_enemies_to_attack_lists(self, creatures: List, heroes: List, current_time: float, building_manager=None):
        """检测最大攻击范围内的敌人，添加到攻击列表 - 主协调函数"""
        # 如果没有英雄，清理所有生物的战斗状态
        if not heroes:
            self._clear_creatures_combat_state(creatures)
            return

        # 清理死亡目标
        self._clean_dead_targets(creatures, heroes)

        # 分别处理不同类型的战斗检测
        self._detect_creature_vs_hero_combat(creatures, heroes, current_time)
        self._detect_hero_vs_creature_combat(creatures, heroes, current_time)
        self._detect_hero_vs_building_combat(
            heroes, building_manager, current_time)
        self._detect_creature_vs_building_combat(
            creatures, building_manager, current_time)

    def _clear_creatures_combat_state(self, creatures: List):
        """清理所有生物的战斗状态"""
        for creature in creatures[:]:
            if not self._is_combat_unit(creature):
                continue
            # 清理战斗状态，让生物回到游荡状态
            creature.in_combat = False
            creature.attack_list.clear()
            if creature.state == 'fighting':
                creature.state = 'wandering'

    def _clean_dead_targets(self, creatures: List, heroes: List):
        """清理死亡目标"""
        for creature in creatures[:]:
            if creature.attack_list:
                creature.clean_dead_targets()

        for hero in heroes[:]:
            if hero.attack_list:
                hero.clean_dead_targets()

    def _detect_creature_vs_hero_combat(self, creatures: List, heroes: List, current_time: float):
        """检测怪物攻击英雄"""
        for creature in creatures[:]:
            if not self._is_combat_unit(creature):
                continue

            for hero in heroes[:]:
                if hero.health <= 0:
                    continue

                # 计算距离
                distance = self._calculate_distance(creature, hero)

                # 获取检测范围
                creature_detection_range = self._get_creature_detection_range(
                    creature)

                # 如果在检测范围内，添加到攻击列表
                if distance <= creature_detection_range:
                    self._set_combat_state(creature, hero, current_time)
                # 如果英雄已经在攻击这个怪物，怪物应该反击（反击范围无限大）
                elif hero.in_combat and creature in hero.attack_list:
                    self._set_combat_state(creature, hero, current_time)
                # 如果生物已经在攻击这个英雄，英雄应该反击（反击范围无限大）
                elif creature.in_combat and hero in creature.attack_list:
                    self._set_combat_state(hero, creature, current_time)

    def _detect_hero_vs_creature_combat(self, creatures: List, heroes: List, current_time: float):
        """检测英雄攻击怪物"""
        for hero in heroes[:]:
            for creature in creatures[:]:
                if creature.health <= 0:
                    continue

                # 计算距离
                distance = self._calculate_distance(hero, creature)

                # 获取英雄追击范围（近战单位：攻击范围 × 2.5，远程单位：攻击范围 × 1.0）
                attack_range = getattr(
                    hero, 'attack_range', GameConstants.DEFAULT_ATTACK_RANGE)
                if hasattr(hero, '_is_melee_attack') and hero._is_melee_attack():
                    pursuit_range = attack_range * GameConstants.MELEE_PURSUIT_MULTIPLIER  # 近战：攻击范围 × 2.5
                else:
                    pursuit_range = attack_range * \
                        GameConstants.RANGED_PURSUIT_MULTIPLIER  # 远程：攻击范围 × 1.0

                # 如果在追击范围内，添加到攻击列表
                if distance <= pursuit_range:
                    self._set_combat_state(hero, creature, current_time)
                # 如果怪物已经在攻击这个英雄，英雄应该反击（反击范围无限大）
                elif creature.in_combat and hero in creature.attack_list:
                    self._set_combat_state(hero, creature, current_time)

    def _detect_hero_vs_building_combat(self, heroes: List, building_manager, current_time: float):
        """检测英雄攻击建筑"""
        if not building_manager or not building_manager.buildings:
            return

        for hero in heroes[:]:
            for building in building_manager.buildings:
                if not building.is_active or building.health <= 0:
                    continue

                # 计算距离
                distance = self._calculate_distance(hero, building)

                # 获取英雄追击范围（近战单位：攻击范围 × 2.5，远程单位：攻击范围 × 1.0）
                attack_range = getattr(
                    hero, 'attack_range', GameConstants.DEFAULT_ATTACK_RANGE)
                if hasattr(hero, '_is_melee_attack') and hero._is_melee_attack():
                    pursuit_range = attack_range * GameConstants.MELEE_PURSUIT_MULTIPLIER  # 近战：攻击范围 × 2.5
                else:
                    pursuit_range = attack_range * \
                        GameConstants.RANGED_PURSUIT_MULTIPLIER  # 远程：攻击范围 × 1.0

                # 如果在追击范围内，添加到攻击列表
                if distance <= pursuit_range:
                    self._set_combat_state(hero, building, current_time)

    def _detect_creature_vs_building_combat(self, creatures: List, building_manager, current_time: float):
        """检测怪物攻击建筑"""
        if not building_manager or not building_manager.buildings:
            return

        for creature in creatures[:]:
            if not self._is_combat_unit(creature):
                continue

            for building in building_manager.buildings:
                if not building.is_active or building.health <= 0:
                    continue

                # 检查是否为友方建筑（地牢之心、金库、魔法祭坛等）
                if self._is_friendly_building(building):
                    continue

                # 计算距离
                distance = self._calculate_distance(creature, building)

                # 获取生物检测范围
                creature_detection_range = getattr(
                    creature, 'detection_range', GameConstants.DEFAULT_CREATURE_DETECTION_RANGE)

                # 如果在检测范围内，添加到攻击列表
                if distance <= creature_detection_range:
                    self._set_combat_state(creature, building, current_time)

    def _calculate_distance(self, unit1, unit2):
        """计算两个单位之间的距离"""
        dx = unit1.x - unit2.x
        dy = unit1.y - unit2.y
        return math.sqrt(dx * dx + dy * dy)

    def _get_creature_detection_range(self, creature):
        """获取生物的检测范围"""
        # 使用生物自己的搜索范围，如果没有则使用默认检测范围
        if hasattr(creature, '_get_search_range'):
            return creature._get_search_range()
        else:
            return getattr(
                creature, 'detection_range', GameConstants.DEFAULT_CREATURE_DETECTION_RANGE)

    def _set_combat_state(self, attacker, target, current_time: float):
        """设置战斗状态"""
        attacker.add_to_attack_list(target)
        attacker.in_combat = True
        attacker.last_combat_time = current_time
        attacker.state = 'fighting'

    def _process_attack_lists(self, creatures: List, heroes: List, delta_time: float, current_time: float):
        """处理所有单位的攻击列表"""
        # 处理生物的攻击列表
        for creature in creatures[:]:
            if not self._is_combat_unit(creature):
                continue
            self._process_unit_attack_list(creature, delta_time, current_time)

        # 处理英雄的攻击列表
        for hero in heroes[:]:
            self._process_unit_attack_list(hero, delta_time, current_time)

    def _process_unit_attack_list(self, unit, delta_time: float, current_time: float):
        """处理单个单位的攻击列表 - 简化版本"""
        if not unit.attack_list:
            return

        # 获取最近的攻击目标
        nearest_target = unit.get_nearest_target()
        if not nearest_target:
            return

        # 计算到目标的距离
        dx = nearest_target.x - unit.x
        dy = nearest_target.y - unit.y
        distance = math.sqrt(dx * dx + dy * dy)

        # 获取攻击范围
        attack_range = getattr(unit, 'attack_range',
                               GameConstants.DEFAULT_ATTACK_RANGE)

        # 判断行为：攻击、追击或移动
        if distance <= attack_range:
            # 在攻击范围内，执行攻击
            self._execute_attack_sequence(
                unit, nearest_target, delta_time, current_time, distance)
        else:
            # 不在攻击范围内，执行追击
            self._handle_combat_pursuit(
                unit, nearest_target, delta_time, distance)

    def _execute_attack_sequence(self, attacker, target, delta_time: float, current_time: float, distance: float):
        """执行攻击序列：技能判定 -> 生成特效 -> 造成伤害"""
        # 检查攻击冷却时间
        if current_time - attacker.last_attack < attacker.attack_cooldown:
            return

        # 检查是否可以使用主动技能
        skill_used = self._try_use_active_skill(attacker, target, current_time)

        # 如果没有使用技能，执行普通攻击
        if not skill_used:
            # 造成伤害
            damage_dealt = self._apply_damage(attacker, target)

            # 生成攻击特效（在伤害判定之后，避免范围伤害重复生成特效）
            # 如果返回的是范围伤害标记，说明特效已经由范围伤害系统处理，跳过常规特效
            if damage_dealt != 'area_damage_applied':
                effect_created = self._create_attack_effect(attacker, target)
                if not effect_created:
                    return

        attacker.last_attack = current_time

        # 设置战斗状态
        attacker.in_combat = True
        attacker.last_combat_time = current_time
        target.in_combat = True
        target.last_combat_time = current_time

        # 如果目标死亡，从攻击列表中移除
        if target.health <= 0:
            attacker.remove_from_attack_list(target)

    def _create_attack_effect(self, attacker, target):
        """步骤2: 特效生成"""
        if not self.game_instance or not self.game_instance.effect_manager:
            return True  # 如果没有特效系统，跳过特效生成

        try:
            # 获取攻击特效类型 - 使用攻击者自己的方法
            if hasattr(attacker, '_get_attack_effect_type'):
                # 使用攻击者自己的方法（包括建筑、英雄、怪物）
                effect_type = attacker._get_attack_effect_type()
            else:
                # 如果攻击者没有此方法，使用默认特效
                effect_type = 'melee_slash'

            if not effect_type:
                return True

            # 计算攻击方向
            dx = target.x - attacker.x
            dy = target.y - attacker.y
            distance = math.sqrt(dx * dx + dy * dy)

            if distance > 0:
                # 归一化方向向量
                dx /= distance
                dy /= distance

                # 使用世界坐标创建特效，特效系统会处理坐标转换
                success = self.game_instance.effect_manager.create_visual_effect(
                    effect_type=effect_type,
                    x=attacker.x,
                    y=attacker.y,
                    target_x=target.x,
                    target_y=target.y,
                    damage=attacker.attack,
                    attacker_name=getattr(attacker, 'name', attacker.type)
                )

                return success
            else:
                return True

        except Exception as e:
            return True

    def _apply_damage(self, attacker, target):
        """步骤3: 伤害判定"""
        try:
            # 计算伤害
            damage = attacker.attack

            # 如果是建筑，使用建筑的 take_damage 方法
            if hasattr(target, 'take_damage') and hasattr(target, 'armor'):
                result = target.take_damage(damage)
                actual_damage = result.get('damage_taken', 0)
            else:
                # 非建筑单位使用原有逻辑
                actual_damage = self._calculate_armor_reduction(damage, target)
                target.health -= actual_damage
                target.health = max(0, target.health)  # 确保生命值不为负数

            # 检查是否有范围伤害
            if hasattr(attacker, 'area_damage') and attacker.area_damage:
                # 使用新的高级范围攻击系统
                area_damage_system = get_advanced_area_damage_system(
                    self.game_instance)

                # 计算攻击方向（从攻击者指向目标）
                direction = math.degrees(math.atan2(
                    target.y - attacker.y, target.x - attacker.x))

                # 应用范围伤害
                result = area_damage_system.apply_area_damage(
                    attacker, target, damage,
                    attacker.x, attacker.y, direction
                )

                if result.success:
                    game_logger.info(f"🎯 {result.message}")

                # 如果有范围伤害，返回特殊标记，让调用者知道不要生成常规特效
                return 'area_damage_applied'

            # 应用物理击退效果（所有攻击类型）
            if (self.game_instance and self.game_instance.physics_system):
                # 获取攻击类型
                attack_type = self._get_attack_type(attacker)

                # 执行击退（支持所有攻击类型）
                knockback_success = self._execute_knockback_with_animation(
                    attacker, target, damage, attack_type
                )

            return actual_damage

        except Exception as e:
            return 0

    def _calculate_armor_reduction(self, damage: int, target) -> int:
        """
        统一的护甲减免计算API

        使用线性护甲减免公式：
        实际伤害 = max(1, 原始伤害 - 护甲值)

        Args:
            damage: 原始伤害值
            target: 目标对象

        Returns:
            int: 应用护甲减免后的实际伤害
        """
        if not hasattr(target, 'armor') or target.armor <= 0:
            return damage

        # 线性护甲减免：每点护甲减少1点伤害
        actual_damage = max(1, damage - target.armor)
        return actual_damage

    def _apply_area_damage(self, attacker, primary_target, damage: float):
        """
        应用范围伤害

        范围攻击逻辑：
        1. 获取范围伤害配置（半径、伤害比例、类型）
        2. 计算范围伤害值（基础伤害 * 伤害比例）
        3. 获取范围内的所有目标
        4. 对每个目标计算距离衰减伤害
        5. 应用护甲减免
        6. 造成伤害并触发击退动画
        7. 创建范围伤害特效

        Args:
            attacker: 攻击者
            primary_target: 主要目标（已受到伤害）
            damage: 基础伤害值
        """
        if not self.game_instance:
            return

        # 获取范围伤害参数
        area_damage_config = getattr(attacker, 'area_damage', {})
        area_radius = area_damage_config.get('radius', 50)  # 范围半径，默认50像素
        area_damage_ratio = area_damage_config.get(
            'damage_ratio', 0.5)  # 范围伤害比例，默认50%
        area_type = area_damage_config.get(
            'type', 'enemy')  # 范围类型：enemy, all, ally

        # 计算范围伤害/治疗
        area_damage = int(damage * area_damage_ratio)
        is_healing = area_damage < 0
        if is_healing:
            area_damage = abs(area_damage)  # 治疗值转为正数

        # 获取范围内的目标
        affected_targets = self._get_targets_in_area(
            attacker, primary_target.x, primary_target.y, area_radius, area_type)

        # 对范围内的目标造成伤害
        for target in affected_targets:
            is_primary_target = (target == primary_target)

            # 计算距离衰减
            distance = math.sqrt((target.x - primary_target.x)
                                 ** 2 + (target.y - primary_target.y)**2)
            if distance > area_radius:
                continue

            # 距离衰减计算（距离越近伤害越高）
            distance_factor = max(0.1, 1.0 - (distance / area_radius))
            final_area_damage = max(1, int(area_damage * distance_factor))

            # 应用护甲减免（使用统一的线性护甲计算）
            final_area_damage = self._calculate_armor_reduction(
                final_area_damage, target)

            # 造成范围伤害或治疗（仅对非主要目标）
            if not is_primary_target:
                if is_healing:
                    # 治疗
                    old_health = target.health
                    target.health += final_area_damage
                    if hasattr(target, 'max_health'):
                        target.health = min(target.health, target.max_health)
                    actual_healing = target.health - old_health
                    game_logger.info(
                        f"💚 {attacker.type} 的范围治疗对 {target.type} 治疗 {actual_healing} 点生命值 (距离: {distance:.1f})")
                else:
                    # 伤害
                    target.health -= final_area_damage
                    target.health = max(0, target.health)
                    # 只在伤害较大时输出日志
                    if final_area_damage >= 5:
                        game_logger.info(
                            f"💥 {attacker.type} 范围攻击 {target.type} 造成 {final_area_damage} 点伤害")

                # 触发范围伤害事件
                if hasattr(target, '_take_damage'):
                    target._take_damage(final_area_damage, attacker)

                # 触发击退动画效果（仅对造成伤害的目标）
                if not is_healing and (self.game_instance and self.game_instance.physics_system and
                                       self.game_instance.knockback_animation):
                    attack_type = self._get_attack_type(attacker)
                    self._execute_knockback_with_animation(
                        attacker, target, final_area_damage, attack_type
                    )

            # 创建范围伤害特效（只有主目标创建攻击特效）
            if self.game_instance.effect_manager and is_primary_target:
                self._create_area_damage_effect(
                    attacker, target, final_area_damage, is_primary_target)

    def _get_targets_in_area(self, attacker, center_x: float, center_y: float, radius: float, area_type: str):
        """
        获取范围内的目标

        目标筛选逻辑：
        1. 获取所有可能的单位（生物、英雄、建筑）
        2. 计算每个单位到范围中心的距离
        3. 筛选出距离小于半径的单位
        4. 根据范围类型进一步筛选：
           - 'enemy': 只攻击敌人
           - 'ally': 只治疗友军
           - 'all': 攻击所有单位

        Args:
            attacker: 攻击者
            center_x, center_y: 范围中心坐标
            radius: 范围半径
            area_type: 范围类型 ('enemy', 'all', 'ally')

        Returns:
            List: 范围内的目标列表
        """
        targets = []

        if not self.game_instance:
            return targets

        # 获取所有可能的目标
        all_units = []

        # 添加生物
        if hasattr(self.game_instance, 'monsters'):
            all_units.extend(self.game_instance.monsters)

        # 添加英雄
        if hasattr(self.game_instance, 'heroes'):
            all_units.extend(self.game_instance.heroes)

        # 添加建筑（如果攻击者是英雄或怪物）
        if hasattr(self.game_instance, 'building_manager') and self.game_instance.building_manager:
            buildings = self.game_instance.building_manager.buildings
            if buildings:
                all_units.extend(buildings)

        # 筛选目标
        for unit in all_units:
            if not unit or unit.health <= 0:
                continue

            # 计算距离
            distance = math.sqrt((unit.x - center_x) **
                                 2 + (unit.y - center_y)**2)
            if distance > radius:
                continue

            # 根据范围类型筛选
            if area_type == 'enemy':
                # 只攻击敌人
                if self._is_enemy_of(attacker, unit):
                    targets.append(unit)
            elif area_type == 'ally':
                # 只攻击友军（治疗）
                if not self._is_enemy_of(attacker, unit) and unit != attacker:
                    targets.append(unit)
            elif area_type == 'all':
                # 攻击所有单位
                if unit != attacker:
                    targets.append(unit)

        return targets

    def _create_area_damage_effect(self, attacker, target, damage: float, is_primary_target: bool = False):
        """创建范围伤害特效"""
        try:
            # 根据伤害类型选择特效
            if hasattr(attacker, 'area_damage'):
                area_config = attacker.area_damage
                effect_type = area_config.get('effect_type', 'area_explosion')

                # 计算范围伤害值（使用area_damage API）
                if hasattr(attacker, 'attack') and 'damage_ratio' in area_config:
                    base_damage = attacker.attack
                    damage_ratio = area_config['damage_ratio']
                    area_damage = int(base_damage * damage_ratio)

                    # 计算距离衰减
                    if hasattr(attacker, 'x') and hasattr(attacker, 'y') and hasattr(target, 'x') and hasattr(target, 'y'):
                        distance = ((attacker.x - target.x) ** 2 +
                                    (attacker.y - target.y) ** 2) ** 0.5
                        area_radius = area_config.get('radius', 40)
                        distance_factor = max(
                            0.1, 1.0 - (distance / area_radius))
                        final_damage = max(
                            1, int(area_damage * distance_factor))
                    else:
                        final_damage = area_damage
                else:
                    final_damage = int(damage)
            else:
                effect_type = 'area_explosion'
                final_damage = int(damage)

            # 为主要目标使用攻击特效，为范围目标使用范围特效
            if is_primary_target:
                # 主要目标创建攻击特效
                if effect_type in ['fire_breath', 'fire_splash', 'flame_wave', 'acid_spray']:
                    # 火焰类特效从攻击者位置开始
                    effect = self.game_instance.effect_manager.create_visual_effect(
                        effect_type=effect_type,
                        x=attacker.x,
                        y=attacker.y,
                        target_x=target.x,
                        target_y=target.y,
                        damage=final_damage,
                        attacker_name=getattr(attacker, 'name', attacker.type),
                        duration=0.5,  # 主目标特效持续时间较长
                        size=5,
                        color=(255, 150, 0)  # 更亮的橙红色表示主目标攻击
                    )
                else:
                    # 其他类型特效在目标位置
                    effect = self.game_instance.effect_manager.create_visual_effect(
                        effect_type=effect_type,
                        x=target.x,
                        y=target.y,
                        target_x=target.x,
                        target_y=target.y,
                        damage=final_damage,
                        attacker_name=getattr(attacker, 'name', attacker.type),
                        duration=0.5,  # 主目标特效持续时间较长
                        size=5,
                        color=(255, 150, 0)  # 更亮的橙红色表示主目标攻击
                    )
            else:
                # 范围目标使用范围特效
                # 火焰类特效应该从攻击者位置开始，朝向目标
                if effect_type in ['fire_breath', 'fire_splash', 'flame_wave', 'acid_spray']:
                    # 火焰类特效从攻击者位置开始
                    effect = self.game_instance.effect_manager.create_visual_effect(
                        effect_type=effect_type,
                        x=attacker.x,
                        y=attacker.y,
                        target_x=target.x,
                        target_y=target.y,
                        damage=final_damage,
                        attacker_name=getattr(attacker, 'name', attacker.type),
                        duration=0.3,  # 范围伤害特效持续时间较短
                        size=3,
                        color=(255, 100, 0)  # 橙红色表示范围伤害
                    )
                else:
                    # 其他类型特效在目标位置
                    effect = self.game_instance.effect_manager.create_visual_effect(
                        effect_type=effect_type,
                        x=target.x,
                        y=target.y,
                        target_x=target.x,
                        target_y=target.y,
                        damage=final_damage,
                        attacker_name=getattr(attacker, 'name', attacker.type),
                        duration=0.3,  # 范围伤害特效持续时间较短
                        size=3,
                        color=(255, 100, 0)  # 橙红色表示范围伤害
                    )
                # 标记这是范围目标特效，不需要绘制火源
                if effect:
                    effect.is_area_target = True
        except Exception as e:
            game_logger.info(f"❌ 范围伤害特效创建错误: {e}")

    def _execute_knockback_with_animation(self, attacker, target, damage: float, attack_type: str):
        """
        执行击退并触发动画效果

        击退动画逻辑：
        1. 计算击退效果（距离、方向、持续时间）
        2. 应用击退到目标单位
        3. 触发击退动画效果（粒子、闪烁、屏幕震动）
        4. 支持所有攻击类型（近战、远程、范围）

        Args:
            attacker: 攻击者
            target: 目标单位
            damage: 伤害值
            attack_type: 攻击类型

        Returns:
            bool: 是否成功执行击退
        """
        try:
            # 计算击退效果
            knockback_result = self.game_instance.physics_system.calculate_knockback(
                attacker, target, damage, attack_type
            )

            # 应用击退
            knockback_success = self.game_instance.physics_system.apply_knockback(
                target, knockback_result)

            # 触发击退动画效果
            if knockback_success and self.game_instance.knockback_animation and target.knockback_state:
                # 计算击退方向向量
                dx = target.knockback_state.target_x - target.knockback_state.start_x
                dy = target.knockback_state.target_y - target.knockback_state.start_y
                distance = (dx**2 + dy**2)**0.5
                if distance > 0:
                    normalized_direction = (dx/distance, dy/distance)
                    self.game_instance.knockback_animation.create_knockback_effect(
                        target, normalized_direction, distance
                    )

            return knockback_success
        except Exception as e:
            game_logger.info(f"❌ 击退动画执行错误: {e}")
            return False

    def _get_attack_type(self, attacker):
        """获取攻击类型用于击退计算"""
        # 检查是否为建筑攻击
        if hasattr(attacker, 'building_type'):
            if attacker.building_type.value == 'arrow_tower':
                return AttackType.PIERCING.value  # 箭塔使用穿透类型
            elif attacker.building_type.value == 'arcane_tower':
                return AttackType.AREA.value  # 奥术塔使用范围攻击类型

        # 根据单位类型返回攻击类型
        heavy_attackers = {'gargoyle', 'stone_golem',
                           'dragon_knight', 'paladin'}
        area_attackers = {'fire_salamander', 'archmage'}
        magic_attackers = {'shadow_mage', 'wizard', 'archmage', 'druid'}
        # 远程攻击者 - 使用25%击退效果
        ranged_attackers = {'archer', 'ranger', 'engineer'}

        if attacker.type in heavy_attackers:
            return AttackType.HEAVY.value
        elif attacker.type in area_attackers:
            return AttackType.AREA.value
        elif attacker.type in magic_attackers:
            return AttackType.MAGIC.value
        elif attacker.type in ranged_attackers:
            return AttackType.RANGED.value  # 远程攻击 - 25%击退效果
        else:
            return AttackType.NORMAL.value

    def _is_melee_attack(self, unit) -> bool:
        """判断单位是否为近战攻击类型"""
        if not unit:
            return False

        # 检查单位是否有_is_melee_attack方法
        if hasattr(unit, '_is_melee_attack'):
            return unit._is_melee_attack()

        # 如果没有此方法，根据单位类型判断
        if hasattr(unit, 'type'):
            melee_types = {
                'knight': True,
                'paladin': True,
                'assassin': True,
                'dragon_knight': True,
                'shadow_blade': True,
                'berserker': True,
                'thief': True,
                'orc_warrior': True,
                'goblin_worker': True,  # 苦工也是近战
                'goblin_engineer': True,  # 工程师也是近战
                'stone_golem': True,
                'gargoyle': True,
                # 远程类型
                'archer': False,
                'ranger': False,
                'wizard': False,
                'archmage': False,
                'druid': False,
                'engineer': False,
                'priest': False
            }
            return melee_types.get(unit.type, True)  # 默认为近战

        return True  # 默认为近战

    def _handle_hero_attack_buildings(self, heroes: List, building_manager, current_time: float, delta_time: float):
        """处理英雄攻击建筑物"""
        if not building_manager or not building_manager.buildings:
            return

        for hero in heroes[:]:
            if not hasattr(hero, 'attack_range') or not hasattr(hero, 'attack_cooldown'):
                continue

            hero_attack_range = hero.attack_range
            hero_can_attack = current_time - hero.last_attack >= hero.attack_cooldown

            if not hero_can_attack:
                continue

            # 优先检查攻击列表中的建筑物
            buildings_to_attack = []

            # 首先检查攻击列表中的建筑物
            if hasattr(hero, 'attack_list') and hero.attack_list:
                for target in hero.attack_list[:]:
                    if hasattr(target, 'building_type') and target.is_active:
                        buildings_to_attack.append(target)

            # 如果没有攻击列表中的建筑物，则检查所有建筑物
            if not buildings_to_attack:
                buildings_to_attack = [building for building in building_manager.buildings
                                       if building.is_active]

            # 寻找建筑物进行攻击（使用新的攻击序列逻辑）
            for building in buildings_to_attack:
                # 建筑物现在直接使用像素坐标
                if not self.game_instance:
                    continue

                building_x = building.x  # 已经是像素坐标
                building_y = building.y  # 已经是像素坐标

                # 计算距离
                dx = building_x - hero.x
                dy = building_y - hero.y
                distance_squared = dx * dx + dy * dy
                distance = math.sqrt(distance_squared)

                # 计算追击范围（英雄追击范围是攻击范围的倍数）
                pursuit_range = hero_attack_range * GameConstants.PURSUIT_RANGE_MULTIPLIER

                # 检查是否应该攻击这个建筑
                should_attack = False

                # 情况1: 这是英雄的当前反击目标，无视距离限制
                if hasattr(hero, 'current_target') and hero.current_target == building:
                    should_attack = True

                # 情况2: 在攻击列表中的建筑物，在追击范围内
                elif building in getattr(hero, 'attack_list', []) and distance <= pursuit_range:
                    should_attack = True

                # 情况3: 在正常追击范围内（非攻击列表中的建筑物）
                elif distance <= pursuit_range:
                    should_attack = True

                # 执行攻击
                if should_attack:
                    # 设置战斗状态
                    hero.in_combat = True
                    hero.last_combat_time = current_time
                    hero.state = 'fighting'

                    # 如果距离大于攻击范围，使用统一的追击系统
                    if distance > hero_attack_range:
                        # 使用统一的追击系统，确保持续追击
                        self._handle_combat_pursuit(
                            hero, building, delta_time, distance)
                    else:
                        # 在攻击范围内，执行攻击
                        self._execute_attack_sequence(
                            hero, building, delta_time, current_time, distance)
                    break  # 一次只能攻击一个目标

    def _handle_health_regeneration(self, creatures: List, heroes: List, current_time: float):
        """处理回血系统"""
        # 处理生物的回血
        for creature in creatures:
            if not creature.in_combat and creature.health < creature.max_health:
                # 检查是否脱离战斗足够长时间
                time_since_combat = current_time - creature.last_combat_time
                if time_since_combat >= creature.regeneration_delay:
                    # 开始回血
                    creature._regenerate_health(current_time)

        # 处理英雄的回血
        for hero in heroes:
            if not hero.in_combat and hero.health < hero.max_health:
                # 检查是否脱离战斗足够长时间
                time_since_combat = current_time - hero.last_combat_time
                if time_since_combat >= hero.regeneration_delay:
                    # 开始回血
                    hero._regenerate_health(current_time)

    def handle_defense_tower_attacks(self, delta_time: float, building_manager, heroes: List):
        """处理防御塔攻击 - 使用与handle_combat相同的时间机制"""
        if not building_manager:
            return

        # 获取所有防御塔（包括箭塔、奥术塔等）
        defense_towers = [building for building in building_manager.buildings
                          if hasattr(building, 'building_type') and
                          building.building_type.value in ['arrow_tower', 'arcane_tower', 'magic_tower', 'cannon_tower'] and
                          building.is_active]

        if not defense_towers or not heroes:
            return

        # 使用与handle_combat相同的时间机制：使用time.time()获取当前时间
        current_time = time.time()

        # 为每个防御塔处理攻击
        for tower in defense_towers:
            # 使用绝对时间检查攻击冷却，而不是依赖delta_time
            # 这与handle_combat中的_execute_attack_sequence方法保持一致

            # 寻找最佳目标
            best_target = tower.find_best_target(heroes)

            if best_target:
                # 更新当前目标
                tower.current_target = best_target

                # 使用与handle_combat相同的攻击冷却检查机制
                # 检查攻击冷却时间（使用绝对时间，与_execute_attack_sequence一致）
                if (tower.can_attack_target(best_target) and
                    hasattr(tower, 'last_attack_time') and
                        current_time - tower.last_attack_time >= tower.attack_interval):

                    # 直接调用建筑物的 attack_target 方法
                    # 建筑物内部会处理攻击逻辑、特效创建和击退动画
                    attack_result = tower.attack_target(best_target)

                    # 注意：last_attack_time会在tower.attack_target内部更新，无需手动更新
            else:
                # 没有目标，清除当前目标
                tower.current_target = None

    def apply_advanced_area_damage(self, attacker, primary_target, damage: float,
                                   start_x: float, start_y: float, direction: float = 0.0,
                                   area_config: Optional[Dict[str, Any]] = None):
        """
        应用高级范围伤害（新API）

        Args:
            attacker: 攻击者对象
            primary_target: 主要目标（已受到伤害的目标）
            damage: 基础伤害值
            start_x, start_y: 范围攻击起始位置
            direction: 攻击方向（度，0度为右方向）
            area_config: 范围攻击配置，如果为None则使用攻击者的area_damage配置

        Returns:
            AreaAttackResult: 范围攻击结果
        """
        area_damage_system = get_advanced_area_damage_system(
            self.game_instance)

        return area_damage_system.apply_area_damage(
            attacker, primary_target, damage, start_x, start_y, direction, area_config
        )

    def _try_use_active_skill(self, attacker, target, current_time: float) -> bool:
        """尝试使用主动技能"""
        if not hasattr(attacker, 'skills') or not attacker.skills:
            game_logger.info(f"🎯 {attacker.name} 没有技能或技能列表为空")
            return False

        game_logger.info(
            f"🎯 {attacker.name} 有 {len(attacker.skills)} 个技能: {[skill.name for skill in attacker.skills]}")

        # 获取可用的主动技能
        available_skills = [skill for skill in attacker.skills
                            if skill.skill_type.value == 'active' and skill.can_use(attacker)]

        game_logger.info(
            f"🎯 {attacker.name} 可用技能: {[skill.name for skill in available_skills]}")

        if not available_skills:
            game_logger.info(f"🎯 {attacker.name} 没有可用的主动技能")
            return False

        # 随机选择技能使用（可以根据AI策略调整）
        import random
        skill = random.choice(available_skills)

        game_logger.info(f"🎯 {attacker.name} 尝试使用技能: {skill.name}")

        # 使用技能
        success = skill.use_skill(
            attacker, target, game_instance=self.game_instance)

        if success:
            game_logger.info(f"🎯 {attacker.name} 使用了技能: {skill.name}")
        else:
            game_logger.info(f"🎯 {attacker.name} 技能使用失败: {skill.name}")

        return success
