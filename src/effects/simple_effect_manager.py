#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化特效管理器 - 避免性能问题的轻量级版本
"""

import pygame
import time
from typing import List, Dict, Any, Optional, Tuple


class SimpleEffectManager:
    """简化特效管理器 - 不显示任何视觉特效，只提供接口兼容性"""

    def __init__(self):
        # 移除伤害数字相关属性
        pass

    def create_effect(self, effect_type: str, x: float, y: float,
                      target_x: float = None, target_y: float = None,
                      damage: int = 0, **kwargs) -> bool:
        """创建特效 - 不显示伤害数字，只记录特效创建"""
        # 添加详细日志排查问题
        print(
            f"🎆 特效创建请求: 类型={effect_type}, 位置=({x:.1f}px, {y:.1f}px), 伤害={damage}")
        if target_x is not None and target_y is not None:
            print(f"   目标位置: ({target_x:.1f}px, {target_y:.1f}px)")
        if kwargs:
            print(f"   额外参数: {kwargs}")

        # 记录特效创建，但不显示伤害数字
        return True

    def update(self, delta_time: float, targets: List = None):
        """更新特效 - 无需更新任何内容"""
        pass

    def render(self, screen: pygame.Surface):
        """渲染特效 - 不渲染伤害数字"""
        # 不渲染任何内容，直接返回屏幕
        return screen

    def get_performance_stats(self) -> Dict[str, int]:
        """获取性能统计"""
        return {
            "particles": 0,
            "projectiles": 0,
            "area_effects": 0,
            "damage_numbers": 0
        }

    def clear(self):
        """清空所有特效 - 无需清空任何内容"""
        pass
