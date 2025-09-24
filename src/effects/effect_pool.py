#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特效对象池管理模块
"""

from typing import Dict, List, Any, TypeVar, Type
from abc import ABC, abstractmethod

T = TypeVar('T')


class Poolable(ABC):
    """可池化对象接口"""

    @abstractmethod
    def reset(self):
        """重置对象状态"""
        pass


class EffectPool:
    """特效对象池管理器"""

    def __init__(self, pool_size: int = 50):
        self.pool_size = pool_size
        self.pools: Dict[type, List[Poolable]] = {}
        self.active_objects: Dict[type, List[Poolable]] = {}

    def get_object(self, object_type: Type[T], *args, **kwargs) -> T:
        """从对象池获取对象"""
        if object_type not in self.pools:
            self.pools[object_type] = []
            self.active_objects[object_type] = []

        pool = self.pools[object_type]
        active = self.active_objects[object_type]

        # 尝试从池中获取对象
        if pool:
            obj = pool.pop()
            obj.reset()
            active.append(obj)
            return obj

        # 创建新对象
        obj = object_type(*args, **kwargs)
        active.append(obj)
        return obj

    def return_object(self, obj: Poolable):
        """将对象返回到池中"""
        obj_type = type(obj)

        if obj_type not in self.pools:
            return

        active = self.active_objects[obj_type]
        pool = self.pools[obj_type]

        # 从活跃列表中移除
        if obj in active:
            active.remove(obj)

        # 检查池大小限制
        if len(pool) < self.pool_size:
            pool.append(obj)

    def get_pool_status(self) -> Dict[str, int]:
        """获取对象池状态"""
        status = {}
        for obj_type, pool in self.pools.items():
            active_count = len(self.active_objects.get(obj_type, []))
            pool_count = len(pool)
            status[f"{obj_type.__name__}"] = {
                "active": active_count,
                "pooled": pool_count,
                "total": active_count + pool_count
            }
        return status

    def clear_pool(self, object_type: Type[T] = None):
        """清空对象池"""
        if object_type is None:
            # 清空所有池
            self.pools.clear()
            self.active_objects.clear()
        else:
            # 清空特定类型的池
            if object_type in self.pools:
                del self.pools[object_type]
            if object_type in self.active_objects:
                del self.active_objects[object_type]

    def cleanup_inactive_objects(self):
        """清理非活跃对象"""
        for obj_type, active_list in self.active_objects.items():
            # 移除已完成的对象
            active_list[:] = [
                obj for obj in active_list if not getattr(obj, 'finished', False)]


class PooledParticle:
    """池化粒子类"""

    def __init__(self, x: float = 0, y: float = 0, vx: float = 0, vy: float = 0,
                 color: tuple = (255, 255, 255), size: float = 2, life: float = 1000):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.life = life
        self.max_life = life
        self.gravity = 0.0
        self.fade = True
        self.finished = False

    def reset(self):
        """重置粒子状态"""
        self.finished = False
        self.life = self.max_life
        self.gravity = 0.0
        self.fade = True


class PooledProjectile:
    """池化投射物类"""

    def __init__(self, x: float = 0, y: float = 0, target_x: float = 0, target_y: float = 0,
                 speed: float = 100, damage: int = 10, color: tuple = (255, 255, 255),
                 size: float = 5, projectile_type: str = "default", max_life: float = 3000):
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y
        self.speed = speed
        self.damage = damage
        self.color = color
        self.size = size
        self.projectile_type = projectile_type
        self.max_life = max_life
        self.life = max_life

        self.trail_points = [(x, y)]
        self.max_trail_length = 15
        self.rotation = 0.0
        self.rotation_speed = 0.0
        self.tracking = False
        self.penetration = False
        self.bounces = 0
        self.max_bounces = 0
        self.finished = False
        self.hit_target = False

        # 计算初始速度
        import math
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx * dx + dy * dy)
        if distance > 0:
            self.vx = (dx / distance) * speed
            self.vy = (dy / distance) * speed
        else:
            self.vx = 0
            self.vy = 0

    def reset(self):
        """重置投射物状态"""
        self.finished = False
        self.hit_target = False
        self.trail_points.clear()
        self.trail_points.append((self.x, self.y))
        self.life = self.max_life
        self.bounces = 0
        self.rotation = 0.0


class PooledAreaEffect:
    """池化区域特效类"""

    def __init__(self, x: float = 0, y: float = 0, radius: float = 10,
                 duration: float = 1000, effect_type: str = "default",
                 damage_per_second: int = 0, color: tuple = (255, 255, 255),
                 opacity: float = 0.5):
        self.x = x
        self.y = y
        self.radius = radius
        self.duration = duration
        self.effect_type = effect_type
        self.damage_per_second = damage_per_second
        self.color = color
        self.opacity = opacity
        self.pulse_speed = 1.0
        self.growth_rate = 0.0
        self.max_radius = radius
        self.current_time = 0.0
        self.finished = False
        self.particles = None
        self.damage_tick = 0.0

    def reset(self):
        """重置区域特效状态"""
        self.finished = False
        self.current_time = 0.0
        self.damage_tick = 0.0
        self.particles = None
        if self.max_radius == 0:
            self.max_radius = self.radius
