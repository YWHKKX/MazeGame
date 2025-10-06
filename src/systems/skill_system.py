#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技能系统
处理所有技能相关的逻辑，包括主动技能和被动技能
"""

import time
import math
import random
from typing import List, Dict, Optional, Any, Tuple
from abc import ABC, abstractmethod
from enum import Enum

from src.core.constants import GameConstants
from src.utils.logger import game_logger


class SkillType(Enum):
    """技能类型枚举"""
    ACTIVE = "active"    # 主动技能
    PASSIVE = "passive"  # 被动技能


class SkillTargetType(Enum):
    """技能目标类型枚举"""
    SELF = "self"           # 自身
    ENEMY = "enemy"         # 敌人
    ALLY = "ally"          # 友军
    ALL = "all"            # 所有单位
    AREA = "area"          # 范围


class SkillEffectType(Enum):
    """技能特效类型枚举"""
    DAMAGE = "damage"           # 伤害
    HEAL = "heal"              # 治疗
    BUFF = "buff"              # 增益
    DEBUFF = "debuff"          # 减益
    MOVEMENT = "movement"      # 移动
    SPECIAL = "special"        # 特殊效果


class Skill(ABC):
    """技能基类"""

    def __init__(self, skill_id: str, name: str, skill_type: SkillType,
                 cooldown: float = 0.0, mana_cost: int = 0,
                 description: str = ""):
        self.skill_id = skill_id
        self.name = name
        self.skill_type = skill_type
        self.cooldown = cooldown
        self.mana_cost = mana_cost
        self.description = description

        # 冷却时间管理
        self.last_used_time = 0.0
        self.is_on_cooldown = False

        # 技能状态
        self.is_active = True
        self.level = 1

    def can_use(self, caster) -> bool:
        """检查技能是否可以使用"""
        if not self.is_active:
            # 获取像素坐标 - 直接使用世界坐标，不乘以20
            pixel_x = caster.x if hasattr(caster, 'x') else 0
            pixel_y = caster.y if hasattr(caster, 'y') else 0
            game_logger.info(
                f"❌ 技能失效: {caster.name} 的 {self.name} 技能未激活 (位置: {pixel_x:.1f}, {pixel_y:.1f})")
            return False

        if self.skill_type == SkillType.ACTIVE:
            # 检查冷却时间
            current_time = time.time()
            if current_time - self.last_used_time < self.cooldown:
                # 获取像素坐标 - 直接使用世界坐标，不乘以20
                pixel_x = caster.x if hasattr(caster, 'x') else 0
                pixel_y = caster.y if hasattr(caster, 'y') else 0
                remaining_cooldown = self.cooldown - \
                    (current_time - self.last_used_time)
                game_logger.info(
                    f"❌ 技能失效: {caster.name} 的 {self.name} 技能冷却中 (剩余: {remaining_cooldown:.1f}秒, 位置: {pixel_x:.1f}, {pixel_y:.1f})")
                return False

            # 检查法力值
            if hasattr(caster, 'mana') and caster.mana < self.mana_cost:
                # 获取像素坐标 - 直接使用世界坐标，不乘以20
                pixel_x = caster.x if hasattr(caster, 'x') else 0
                pixel_y = caster.y if hasattr(caster, 'y') else 0
                game_logger.info(
                    f"❌ 技能失效: {caster.name} 的 {self.name} 技能法力不足 (需要: {self.mana_cost}, 当前: {caster.mana}, 位置: {pixel_x:.1f}, {pixel_y:.1f})")
                return False

        return True

    def use_skill(self, caster, target=None, **kwargs) -> bool:
        """使用技能"""
        if not self.can_use(caster):
            return False

        # 消耗法力值
        if hasattr(caster, 'mana') and self.mana_cost > 0:
            caster.mana -= self.mana_cost

        # 记录使用时间
        self.last_used_time = time.time()

        # 执行技能效果
        result = self.execute_skill(caster, target, **kwargs)

        if result:
            game_logger.info(f"🎯 {caster.name} 使用了技能: {self.name}")

        return result

    @abstractmethod
    def execute_skill(self, caster, target=None, **kwargs) -> bool:
        """执行技能效果 - 子类必须实现"""
        pass

    def update_cooldown(self):
        """更新冷却状态"""
        if self.skill_type == SkillType.ACTIVE:
            current_time = time.time()
            self.is_on_cooldown = current_time - self.last_used_time < self.cooldown


class ActiveSkill(Skill):
    """主动技能基类"""

    def __init__(self, skill_id: str, name: str, damage: int, range: float,
                 direction: float, cooldown: float, mana_cost: int = 0,
                 description: str = ""):
        super().__init__(skill_id, name, SkillType.ACTIVE, cooldown, mana_cost, description)
        self.damage = damage
        self.range = range
        self.direction = direction


class PassiveSkill(Skill):
    """被动技能基类"""

    def __init__(self, skill_id: str, name: str, description: str = ""):
        super().__init__(skill_id, name, SkillType.PASSIVE, 0.0, 0, description)


class WhirlwindSlash(ActiveSkill):
    """旋风斩 - 骑士和兽人战士的主动技能"""

    def __init__(self):
        super().__init__(
            skill_id="whirlwind_slash",
            name="旋风斩",
            damage=80,
            range=0.0,  # 动态范围，基于释放者攻击距离的1.5倍
            direction=0.0,  # 以自身为中心
            cooldown=8.0,  # 8秒冷却
            mana_cost=30,
            description="以自身为中心进行圆形范围攻击，对周围敌人造成伤害"
        )
        self.effect_type = "circular_slash"

    def execute_skill(self, caster, target=None, **kwargs) -> bool:
        """执行旋风斩技能"""
        if not caster or not hasattr(caster, 'x') or not hasattr(caster, 'y'):
            return False

        # 获取游戏实例
        game_instance = kwargs.get('game_instance')
        if not game_instance:
            return False

        # 动态计算范围：释放者攻击距离的1.5倍
        caster_attack_range = getattr(caster, 'attack_range', 30)  # 默认30像素
        self.range = caster_attack_range * 1.5
        game_logger.info(
            f"💨 {caster.name} 旋风斩范围: {self.range:.1f}像素 (基于攻击距离{caster_attack_range}的1.5倍)")

        # 寻找范围内的敌人
        enemies = self._find_enemies_in_range(caster, game_instance)
        game_logger.info(
            f"💨 {caster.name} 旋风斩搜索敌人 - 范围:{self.range:.1f}像素, 找到{len(enemies)}个目标")

        if not enemies:
            game_logger.info(f"💨 {caster.name} 的旋风斩没有找到目标")
            return False

        # 对每个敌人造成伤害
        total_damage = 0
        for i, enemy in enumerate(enemies):
            # 计算距离衰减
            distance = math.sqrt((enemy.x - caster.x) **
                                 2 + (enemy.y - caster.y)**2)
            distance_factor = max(0.3, 1.0 - (distance / self.range))
            final_damage = int(self.damage * distance_factor)

            game_logger.info(
                f"💨 {caster.name} 旋风斩目标{i+1}: {enemy.name} 距离:{distance:.1f}像素 衰减系数:{distance_factor:.2f} 最终伤害:{final_damage}")

            # 造成伤害
            if hasattr(enemy, '_take_damage'):
                enemy._take_damage(final_damage, caster)
                game_logger.info(
                    f"💨 {caster.name} 旋风斩对 {enemy.name} 造成 {final_damage} 点伤害 (使用_take_damage)")
            else:
                old_health = enemy.health
                enemy.health -= final_damage
                enemy.health = max(0, enemy.health)
                actual_damage = old_health - enemy.health
                game_logger.info(
                    f"💨 {caster.name} 旋风斩对 {enemy.name} 造成 {actual_damage} 点伤害 (直接修改health: {old_health}->{enemy.health})")

            total_damage += final_damage

        # 创建特效
        self._create_whirlwind_effect(caster, game_instance)

        game_logger.info(
            f"💨 {caster.name} 的旋风斩对 {len(enemies)} 个敌人造成了 {total_damage} 点伤害")
        return True

    def _find_enemies_in_range(self, caster, game_instance) -> List:
        """寻找范围内的敌人"""
        enemies = []

        # 获取所有可能的敌人
        all_units = []
        if hasattr(game_instance, 'monsters'):
            all_units.extend(game_instance.monsters)
            game_logger.info(f"💨 找到 {len(game_instance.monsters)} 个怪物")
        if hasattr(game_instance, 'heroes'):
            all_units.extend(game_instance.heroes)
            game_logger.info(f"💨 找到 {len(game_instance.heroes)} 个英雄")

        game_logger.info(f"💨 总单位数: {len(all_units)}")

        for unit in all_units:
            if not unit or unit.health <= 0 or unit == caster:
                if not unit:
                    game_logger.info(f"💨 跳过空单位")
                elif unit.health <= 0:
                    game_logger.info(f"💨 跳过死亡单位: {unit.name}")
                elif unit == caster:
                    game_logger.info(f"💨 跳过自己: {unit.name}")
                continue

            # 检查是否为敌人
            is_enemy = self._is_enemy(caster, unit)

            if is_enemy:
                # 计算距离
                distance = math.sqrt((unit.x - caster.x) **
                                     2 + (unit.y - caster.y)**2)
                game_logger.info(
                    f"💨 {unit.name} 距离: {distance:.1f}像素, 范围: {self.range:.1f}像素")

                if distance <= self.range:
                    enemies.append(unit)
                    game_logger.info(f"💨 添加敌人: {unit.name} 到攻击列表")

        return enemies

    def _is_enemy(self, caster, target) -> bool:
        """判断是否为敌人 - 统一使用faction判断"""
        # 检查阵营 - 不同阵营即为敌人
        if hasattr(caster, 'faction') and hasattr(target, 'faction'):
            is_enemy = caster.faction != target.faction
            return is_enemy
        return True

    def _create_whirlwind_effect(self, caster, game_instance):
        """创建旋风斩特效"""
        if not hasattr(game_instance, 'effect_manager') or not game_instance.effect_manager:
            return

        try:
            game_instance.effect_manager.create_visual_effect(
                effect_type="whirlwind_slash",
                x=caster.x,
                y=caster.y,
                target_x=caster.x,
                target_y=caster.y,
                damage=self.damage,
                range=self.range,  # 使用动态计算的范围
                attacker_name=caster.name,
                duration=1.0,
                size=8,
                color=(255, 200, 0)  # 金色
            )
        except Exception as e:
            game_logger.warning(f"⚠️ 旋风斩特效创建失败: {e}")


class MultiShot(ActiveSkill):
    """多重射击 - 弓箭手的主动技能"""

    def __init__(self):
        super().__init__(
            skill_id="multi_shot",
            name="多重射击",
            damage=40,
            range=120.0,  # 射程
            direction=0.0,  # 朝向目标
            cooldown=6.0,  # 6秒冷却
            mana_cost=25,
            description="连续进行4次快速射击，每次间隔0.2秒"
        )
        self.shot_count = 4
        self.shot_interval = 0.2
        self.current_shot = 0
        self.last_shot_time = 0.0
        self.is_charging = False
        self.original_target = None  # 记住初始目标

    def execute_skill(self, caster, target=None, **kwargs) -> bool:
        """执行多重射击技能"""
        if not caster or not target:
            return False

        # 开始多重射击序列
        self.current_shot = 0
        self.last_shot_time = time.time()
        self.is_charging = True
        self.original_target = target  # 保存初始目标

        # 立即执行第一次射击
        self._execute_single_shot(caster, target, kwargs.get('game_instance'))

        game_logger.info(f"🏹 {caster.name} 开始多重射击序列")
        return True

    def update_skill(self, caster, target, game_instance) -> bool:
        """更新多重射击状态 - 需要在游戏主循环中调用"""
        if not self.is_charging:
            return False

        # 使用保存的初始目标，而不是传入的target
        actual_target = self.original_target

        # 验证目标是否仍然有效
        if not actual_target or not hasattr(actual_target, 'health') or actual_target.health <= 0:
            game_logger.info(f"🏹 {caster.name} 多重射击中断：目标无效")
            self.is_charging = False
            return False

        current_time = time.time()

        # 检查是否到了下一次射击时间
        if current_time - self.last_shot_time >= self.shot_interval:
            self.current_shot += 1
            self.last_shot_time = current_time

            if self.current_shot < self.shot_count:
                # 继续射击
                game_logger.info(
                    f"🏹 {caster.name} 多重射击第 {self.current_shot + 1} 发")
                self._execute_single_shot(caster, actual_target, game_instance)
            else:
                # 完成所有射击
                self.is_charging = False
                game_logger.info(f"🏹 {caster.name} 完成多重射击")
        else:
            # 调试：显示等待信息
            remaining_time = self.shot_interval - \
                (current_time - self.last_shot_time)
            if self.current_shot < self.shot_count:
                game_logger.debug(
                    f"🏹 {caster.name} 多重射击等待中... 第{self.current_shot + 1}发，剩余时间: {remaining_time:.2f}秒")

        return self.is_charging

    def _execute_single_shot(self, caster, target, game_instance):
        """执行单次射击"""
        if not target or target.health <= 0:
            self.is_charging = False
            return False

        # 计算到目标的距离
        distance = math.sqrt((target.x - caster.x)**2 +
                             (target.y - caster.y)**2)

        # 检查是否在射程内
        if distance > self.range:
            self.is_charging = False
            return False

        # 造成伤害
        if hasattr(target, '_take_damage'):
            target._take_damage(self.damage, caster)
        else:
            target.health -= self.damage
            target.health = max(0, target.health)

        # 创建射击特效
        self._create_shot_effect(caster, target, game_instance)

        game_logger.info(
            f"🏹 {caster.name} 多重射击第 {self.current_shot + 1} 发命中目标")
        return True

    def _create_shot_effect(self, caster, target, game_instance):
        """创建射击特效"""
        if not hasattr(game_instance, 'effect_manager') or not game_instance.effect_manager:
            return

        try:
            # 为每次射击添加随机偏移，让箭矢从不同位置发射
            import random
            offset_range = 15.0  # 随机偏移范围（像素）

            # 计算朝向目标的方向
            dx = target.x - caster.x
            dy = target.y - caster.y
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                # 归一化方向向量
                dx /= distance
                dy /= distance

                # 计算垂直方向（用于随机偏移）
                perp_x = -dy
                perp_y = dx

                # 添加随机偏移
                random_offset = random.uniform(-offset_range, offset_range)
                start_x = caster.x + perp_x * random_offset
                start_y = caster.y + perp_y * random_offset

                # 为终点也添加一些随机偏移，增加视觉多样性
                target_offset_x = random.uniform(-5, 5)
                target_offset_y = random.uniform(-5, 5)
                end_x = target.x + target_offset_x
                end_y = target.y + target_offset_y
            else:
                # 如果距离为0，使用原始位置
                start_x = caster.x
                start_y = caster.y
                end_x = target.x
                end_y = target.y

            game_instance.effect_manager.create_visual_effect(
                effect_type="arrow_shot",
                x=start_x,
                y=start_y,
                target_x=end_x,
                target_y=end_y,
                damage=self.damage,
                attacker_name=caster.name,
                duration=0.3,
                size=4,
                color=(100, 200, 255)  # 蓝色
            )
        except Exception as e:
            game_logger.warning(f"⚠️ 多重射击特效创建失败: {e}")


class FlameExplosion(PassiveSkill):
    """烈焰自爆 - 小恶魔的被动技能"""

    def __init__(self, explosion_count: int = 3):
        super().__init__(
            skill_id="flame_explosion",
            name="烈焰自爆",
            description=f"死亡时对周围随机目标释放{explosion_count}次扇形范围攻击"
        )
        self.explosion_count = explosion_count
        self.explosion_range = 80.0
        self.explosion_damage = 60
        self.explosion_angle = 60.0  # 扇形角度

    def execute_skill(self, caster, target=None, **kwargs) -> bool:
        """执行烈焰自爆技能 - 在单位死亡时触发"""
        if not caster:
            return False

        # 获取游戏实例
        game_instance = kwargs.get('game_instance')
        if not game_instance:
            return False

        # 寻找范围内的敌人
        enemies = self._find_enemies_in_range(caster, game_instance)

        if not enemies:
            game_logger.info(f"💥 {caster.name} 的烈焰自爆没有找到目标")
            return False

        # 随机选择目标进行扇形攻击
        selected_targets = random.sample(
            enemies, min(self.explosion_count, len(enemies)))

        total_damage = 0
        for i, target in enumerate(selected_targets):
            # 计算扇形攻击方向
            angle = (360.0 / self.explosion_count) * i
            self._execute_fan_attack(caster, target, angle, game_instance)
            total_damage += self.explosion_damage

        game_logger.info(
            f"💥 {caster.name} 的烈焰自爆对 {len(selected_targets)} 个敌人造成了 {total_damage} 点伤害")
        return True

    def _find_enemies_in_range(self, caster, game_instance) -> List:
        """寻找范围内的敌人"""
        enemies = []

        # 获取所有可能的敌人
        all_units = []
        if hasattr(game_instance, 'monsters'):
            all_units.extend(game_instance.monsters)
        if hasattr(game_instance, 'heroes'):
            all_units.extend(game_instance.heroes)

        for unit in all_units:
            if not unit or unit.health <= 0 or unit == caster:
                continue

            # 检查是否为敌人
            if self._is_enemy(caster, unit):
                # 计算距离
                distance = math.sqrt((unit.x - caster.x) **
                                     2 + (unit.y - caster.y)**2)
                if distance <= self.explosion_range:
                    enemies.append(unit)

        return enemies

    def _is_enemy(self, caster, target) -> bool:
        """判断是否为敌人"""
        # 检查阵营
        if hasattr(caster, 'faction') and hasattr(target, 'faction'):
            return caster.faction != target.faction

        # 检查敌我属性
        if hasattr(caster, 'is_enemy') and hasattr(target, 'is_enemy'):
            return caster.is_enemy != target.is_enemy

        # 检查英雄和怪物
        if hasattr(caster, 'is_hero') and hasattr(target, 'is_hero'):
            return caster.is_hero != target.is_hero

        return False

    def _execute_fan_attack(self, caster, target, angle, game_instance):
        """执行扇形攻击"""
        # 计算攻击方向
        radians = math.radians(angle)
        dx = math.cos(radians)
        dy = math.sin(radians)

        # 造成伤害
        if hasattr(target, '_take_damage'):
            target._take_damage(self.explosion_damage, caster)
        else:
            target.health -= self.explosion_damage
            target.health = max(0, target.health)

        # 创建扇形攻击特效
        self._create_fan_effect(caster, target, angle, game_instance)

    def _create_fan_effect(self, caster, target, angle, game_instance):
        """创建扇形攻击特效"""
        if not hasattr(game_instance, 'effect_manager') or not game_instance.effect_manager:
            return

        try:
            # 计算扇形攻击的目标位置
            radians = math.radians(angle)
            target_x = caster.x + math.cos(radians) * self.explosion_range
            target_y = caster.y + math.sin(radians) * self.explosion_range

            game_instance.effect_manager.create_visual_effect(
                effect_type="fire_breath",
                x=caster.x,
                y=caster.y,
                target_x=target_x,
                target_y=target_y,
                damage=self.explosion_damage,
                attacker_name=caster.name,
                duration=0.8,
                size=6,
                color=(255, 100, 0)  # 橙红色
            )
        except Exception as e:
            game_logger.warning(f"⚠️ 烈焰自爆特效创建失败: {e}")


class SkillManager:
    """技能管理器"""

    def __init__(self):
        self.skills = {}  # 技能字典 {skill_id: skill_instance}
        self.unit_skills = {}  # 单位技能字典 {unit_id: [skill_ids]}

    def register_skill(self, skill: Skill):
        """注册技能"""
        self.skills[skill.skill_id] = skill
        game_logger.info(f"📚 注册技能: {skill.name} ({skill.skill_id})")

    def assign_skill_to_unit(self, unit, skill_id: str):
        """为单位分配技能"""
        if skill_id not in self.skills:
            game_logger.warning(f"⚠️ 技能不存在: {skill_id}")
            return False

        unit_id = id(unit)
        if unit_id not in self.unit_skills:
            self.unit_skills[unit_id] = []

        # 检查技能是否已存在
        existing_skill_ids = [
            skill.skill_id for skill in self.unit_skills[unit_id]]
        if skill_id in existing_skill_ids:
            game_logger.info(f"🎯 {unit.name} 已有技能: {skill_id}")
            return True

        # 为每个单位创建独立的技能实例
        skill_template = self.skills[skill_id]
        if skill_template.skill_type == SkillType.ACTIVE:
            # 创建主动技能实例
            if skill_id == "whirlwind_slash":
                skill_instance = WhirlwindSlash()
            elif skill_id == "multi_shot":
                skill_instance = MultiShot()
            else:
                # 默认创建基础主动技能
                skill_instance = ActiveSkill(
                    skill_id=skill_template.skill_id,
                    name=skill_template.name,
                    damage=skill_template.damage,
                    range=skill_template.range,
                    direction=skill_template.direction,
                    cooldown=skill_template.cooldown,
                    mana_cost=skill_template.mana_cost,
                    description=skill_template.description
                )
        else:
            # 创建被动技能实例
            if skill_id == "flame_explosion":
                skill_instance = FlameExplosion()
            else:
                # 默认创建基础被动技能
                skill_instance = PassiveSkill(
                    skill_id=skill_template.skill_id,
                    name=skill_template.name,
                    description=skill_template.description
                )

        self.unit_skills[unit_id].append(skill_instance)
        game_logger.info(
            f"🎯 为 {unit.name} 分配技能: {skill_instance.name}")
        return True

    def get_unit_skills(self, unit) -> List[Skill]:
        """获取单位的技能列表"""
        unit_id = id(unit)
        if unit_id not in self.unit_skills:
            return []

        # 直接返回该单位的独立技能实例
        return self.unit_skills[unit_id]

    def use_skill(self, unit, skill_id: str, target=None, **kwargs) -> bool:
        """使用技能"""
        unit_id = id(unit)
        if unit_id not in self.unit_skills:
            return False

        # 查找该单位的独立技能实例
        skill = None
        for skill_instance in self.unit_skills[unit_id]:
            if skill_instance.skill_id == skill_id:
                skill = skill_instance
                break

        if not skill:
            return False

        return skill.use_skill(unit, target, **kwargs)

    def update_skills(self, unit, delta_time: float):
        """更新单位的所有技能状态"""
        skills = self.get_unit_skills(unit)
        for skill in skills:
            skill.update_cooldown()

    def get_available_skills(self, unit) -> List[Skill]:
        """获取单位可用的技能"""
        skills = self.get_unit_skills(unit)
        return [skill for skill in skills if skill.can_use(unit)]


# 全局技能管理器实例
skill_manager = SkillManager()

# 注册所有技能
skill_manager.register_skill(WhirlwindSlash())
skill_manager.register_skill(MultiShot())
skill_manager.register_skill(FlameExplosion())
