#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体配置数据
"""


class CreatureConfig:
    """生物配置"""
    TYPES = {
        'imp': {
            'name': '小恶魔',
            'size': 15,
            'health': 70,   # 降低生命值
            'attack': 14,   # 降低攻击力，平衡性价比
            'speed': 28,    # 提高移动速度
            'color': (255, 107, 107),
            'upkeep': 1,
            'abilities': ['dig', 'fight'],
            'attack_range': 30,  # 近战攻击范围
            'attack_cooldown': 0.9  # 稍微提高攻击冷却
        },
        'goblin_worker': {
            'name': '哥布林苦工',
            'size': 12,
            'health': 65,   # 保持生命值
            'attack': 12,   # 保持攻击力
            'speed': 32,    # 保持移动速度
            'color': (143, 188, 143),
            'upkeep': 1,
            'abilities': ['mine', 'dig', 'work'],
            'mining_speed': 2.0,
            'mining_efficiency': 1.5,
            'attack_range': 28,  # 保持攻击范围
            'attack_cooldown': 1.0  # 保持攻击冷却
        },
        'orc': {
            'name': '兽人',
            'size': 18,
            'health': 140,  # 提高生命值
            'attack': 28,   # 提高攻击力
            'speed': 22,    # 稍微提高移动速度
            'color': (139, 69, 19),
            'upkeep': 2,
            'abilities': ['fight', 'guard'],
            'attack_range': 35,  # 近战攻击范围
            'attack_cooldown': 1.2  # 降低攻击冷却
        },
        'goblin_engineer': {
            'name': '哥布林工程师',
            'size': 13,
            'health': 75,   # 保持生命值
            'attack': 15,   # 保持攻击力
            'speed': 28,    # 保持移动速度
            'color': (143, 188, 143),
            'upkeep': 1,
            'abilities': ['fight', 'work'],
            'attack_range': 110,  # 保持远程攻击范围
            'attack_cooldown': 0.9  # 保持攻击冷却
        },
        'fire_salamander': {
            'name': '火蜥蜴',
            'size': 16,
            'health': 100,  # 提高生命值
            'attack': 30,   # 提高攻击力
            'speed': 25,    # 降低移动速度，平衡远程优势
            'color': (255, 69, 0),
            'upkeep': 2,
            'abilities': ['fight', 'fire_breath'],
            'attack_range': 85,  # 稍微提高远程攻击范围
            'attack_cooldown': 1.2  # 大幅降低攻击冷却，提高攻击频率
        }
    }


class HeroConfig:
    """英雄配置"""
    TYPES = {
        'knight': {
            'name': '骑士',
            'size': 15,
            'health': 120,  # 提高生命值
            'attack': 22,   # 提高攻击力
            'speed': 25,    # 降低移动速度
            'color': (70, 130, 180),
            'attack_range': 35,  # 近战攻击范围
            'attack_cooldown': 1.0  # 降低攻击冷却
        },
        'archer': {
            'name': '弓箭手',
            'size': 14,
            'health': 70,   # 降低生命值
            'attack': 20,   # 提高攻击力
            'speed': 40,    # 提高移动速度
            'color': (81, 207, 102),
            'attack_range': 120,  # 远程攻击范围
            'attack_cooldown': 0.9  # 降低攻击冷却
        },
        'wizard': {
            'name': '法师',
            'size': 13,
            'health': 50,   # 降低生命值
            'attack': 28,   # 大幅提高攻击力
            'speed': 18,    # 降低移动速度
            'color': (147, 112, 219),
            'attack_range': 100,  # 远程攻击范围
            'attack_cooldown': 1.3  # 降低攻击冷却
        }
    }
