#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
War for the Overworld - 角色数据定义
基于CHARACTER_DESIGN.md文档的角色属性和能力
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class CharacterType(Enum):
    """角色类型枚举"""
    HERO = "hero"
    MONSTER = "monster"


class CombatType(Enum):
    """战斗类型枚举"""
    MELEE = "melee"           # 近战
    RANGED = "ranged"         # 远程
    MAGIC = "magic"           # 魔法
    MIXED = "mixed"           # 混合


class MonsterCategory(Enum):
    """怪物分类枚举"""
    FUNCTIONAL = "functional"  # 功能类
    COMBAT = "combat"         # 战斗类


@dataclass
class CharacterData:
    """角色数据类"""
    id: str
    name: str
    english_name: str
    character_type: CharacterType
    threat_level: int
    hp: int
    attack: int
    speed: int
    armor: int = 0
    attack_range: int = 30
    attack_cooldown: float = 1.0
    special_ability: str = "无"
    description: str = ""
    color: tuple = (255, 255, 255)
    size: int = 15
    avatar: Optional[str] = None
    combat_type: CombatType = CombatType.MELEE
    ai_behavior: List[str] = None
    tactics: List[str] = None
    cost: Optional[int] = None  # 仅怪物角色使用
    monster_category: Optional['MonsterCategory'] = None  # 仅怪物角色使用


class CharacterDatabase:
    """角色数据库"""

    def __init__(self):
        self.heroes = self._init_heroes()
        self.monsters = self._init_monsters()

    def _init_heroes(self) -> Dict[str, CharacterData]:
        """初始化英雄角色数据"""
        heroes = {}

        # 骑士
        heroes['knight'] = CharacterData(
            id='knight',
            name='骑士',
            english_name='Knight',
            character_type=CharacterType.HERO,
            threat_level=2,
            hp=900,
            attack=18,
            speed=20,
            armor=5,
            attack_range=35,
            attack_cooldown=1.2,
            special_ability='无',
            description='重装战士，拥有高攻击力和护甲值，适合正面硬碰硬的战斗。',
            color=(77, 171, 247),  # 蓝色
            size=18,
            avatar='img/Hero/骑士.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '寻找并攻击威胁最大的生物',
                '优先攻击攻击力最高的目标',
                '无目标时探索地牢，寻找地牢之心'
            ],
            tactics=[
                '稳定输出',
                '正面作战',
                '威胁评估'
            ]
        )

        # 弓箭手
        heroes['archer'] = CharacterData(
            id='archer',
            name='弓箭手',
            english_name='Archer',
            character_type=CharacterType.HERO,
            threat_level=2,
            hp=700,
            attack=16,
            speed=25,
            armor=2,
            attack_range=120,
            attack_cooldown=1.0,
            special_ability='精准射击 - 有25%概率造成双倍伤害',
            description='远程射手，拥有120像素的攻击范围和精准射击能力。',
            color=(81, 207, 102),  # 绿色
            size=16,
            avatar='img/Hero/弓箭手.png',
            combat_type=CombatType.RANGED,
            ai_behavior=[
                '保持距离，远程攻击生物',
                '优先攻击脆弱的远程单位',
                '移动中寻找最佳射击位置'
            ],
            tactics=[
                '远程威胁',
                '精准打击',
                '机动性强'
            ]
        )

        # 法师
        heroes['wizard'] = CharacterData(
            id='wizard',
            name='法师',
            english_name='Wizard',
            character_type=CharacterType.HERO,
            threat_level=2,
            hp=500,
            attack=22,
            speed=18,
            armor=1,
            attack_range=100,
            attack_cooldown=2.0,
            special_ability='火球术 - 范围攻击，溅射伤害',
            description='魔法师，发射火球造成范围伤害，对群体敌人有效。',
            color=(151, 117, 250),  # 紫色
            size=16,
            avatar='img/Hero/法师.png',
            combat_type=CombatType.MAGIC,
            ai_behavior=[
                '远程魔法攻击生物',
                '寻找群体目标使用火球术',
                '保持安全距离，避免近战'
            ],
            tactics=[
                '范围攻击',
                '魔法伤害',
                '脆弱性'
            ]
        )

        # 圣骑士
        heroes['paladin'] = CharacterData(
            id='paladin',
            name='圣骑士',
            english_name='Paladin',
            character_type=CharacterType.HERO,
            threat_level=3,
            hp=1600,
            attack=28,
            speed=15,
            armor=10,
            attack_range=40,
            attack_cooldown=1.5,
            special_ability='神圣光环 - 周围友军获得20%攻击力加成',
            description='神圣战士，拥有极高的护甲值和生命值，为友军提供光环支持。',
            color=(255, 212, 59),  # 金色
            size=22,
            avatar='img/Hero/圣骑士.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '保护其他英雄，提供光环支持',
                '攻击威胁最大的生物',
                '使用治疗光环支援友军'
            ],
            tactics=[
                '团队支援',
                '高防御',
                '持续作战'
            ]
        )

        # 刺客
        heroes['assassin'] = CharacterData(
            id='assassin',
            name='刺客',
            english_name='Assassin',
            character_type=CharacterType.HERO,
            threat_level=3,
            hp=900,
            attack=38,
            speed=35,
            armor=3,
            attack_range=25,
            attack_cooldown=0.8,
            special_ability='暗杀 - 从背后攻击时造成三倍伤害',
            description='敏捷战士，拥有极高的移动速度和致命的暗杀能力。',
            color=(73, 80, 87),  # 黑色
            size=14,
            avatar='img/Hero/刺客.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '寻找背后攻击的机会',
                '使用潜行接近目标',
                '优先攻击脆弱的远程单位'
            ],
            tactics=[
                '高机动性',
                '致命攻击',
                '潜行威胁'
            ]
        )

        # 游侠
        heroes['ranger'] = CharacterData(
            id='ranger',
            name='游侠',
            english_name='Ranger',
            character_type=CharacterType.HERO,
            threat_level=3,
            hp=1000,
            attack=25,
            speed=22,
            armor=4,
            attack_range=150,
            attack_cooldown=1.2,
            special_ability='追踪箭 - 可以追踪移动目标',
            description='野外专家，发射的箭矢可以追踪移动目标，难以躲避。',
            color=(139, 69, 19),  # 棕色
            size=17,
            avatar='img/Hero/游侠.png',
            combat_type=CombatType.RANGED,
            ai_behavior=[
                '使用追踪箭攻击移动目标',
                '保持最大攻击范围',
                '优先攻击高价值目标'
            ],
            tactics=[
                '超远距离',
                '追踪攻击',
                '多重威胁'
            ]
        )

        # 大法师
        heroes['archmage'] = CharacterData(
            id='archmage',
            name='大法师',
            english_name='Archmage',
            character_type=CharacterType.HERO,
            threat_level=3,
            hp=800,
            attack=35,
            speed=16,
            armor=2,
            attack_range=120,
            attack_cooldown=2.5,
            special_ability='连锁闪电 - 可以跳跃攻击多个目标',
            description='高级魔法师，发射闪电可以跳跃攻击多个目标，对群体有效。',
            color=(54, 79, 199),  # 深蓝色
            size=18,
            avatar='img/Hero/大法师.png',
            combat_type=CombatType.MAGIC,
            ai_behavior=[
                '寻找群体目标使用连锁闪电',
                '保持安全距离，避免近战',
                '优先攻击聚集的生物'
            ],
            tactics=[
                '范围攻击',
                '跳跃攻击',
                '魔法伤害'
            ]
        )

        # 德鲁伊
        heroes['druid'] = CharacterData(
            id='druid',
            name='德鲁伊',
            english_name='Druid',
            character_type=CharacterType.HERO,
            threat_level=3,
            hp=1300,
            attack=22,
            speed=20,
            armor=6,
            attack_range=80,
            attack_cooldown=1.8,
            special_ability='自然形态 - 可以切换攻击模式',
            description='自然法师，近战远程兼备，可以使用治疗术支援友军。',
            color=(47, 158, 68),  # 深绿色
            size=19,
            avatar='img/Hero/德鲁伊.png',
            combat_type=CombatType.MIXED,
            ai_behavior=[
                '根据战况选择最佳攻击模式',
                '使用治疗术支援友军',
                '优先攻击威胁最大的目标'
            ],
            tactics=[
                '灵活作战',
                '团队支援',
                '自然抗性'
            ]
        )

        # 龙骑士
        heroes['dragon_knight'] = CharacterData(
            id='dragon_knight',
            name='龙骑士',
            english_name='Dragon Knight',
            character_type=CharacterType.HERO,
            threat_level=4,
            hp=2200,
            attack=48,
            speed=25,
            armor=12,
            attack_range=45,
            attack_cooldown=1.8,
            special_ability='龙息攻击 - 范围火焰攻击',
            description='龙骑士，可以短距离飞行，释放龙息对群体敌人造成伤害。',
            color=(255, 107, 53),  # 红金色
            size=28,
            avatar='img/Hero/龙骑士.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '使用龙息攻击群体敌人',
                '优先攻击威胁最大的目标',
                '利用飞行能力调整位置'
            ],
            tactics=[
                '空中优势',
                '范围攻击',
                '高防御'
            ]
        )

        # 暗影剑圣
        heroes['shadow_blade'] = CharacterData(
            id='shadow_blade',
            name='暗影剑圣',
            english_name='Shadow Blade',
            character_type=CharacterType.HERO,
            threat_level=5,
            hp=1400,
            attack=58,
            speed=30,
            armor=8,
            attack_range=35,
            attack_cooldown=1.0,
            special_ability='暗影步 - 可以瞬间移动到目标身后',
            description='暗影剑士，可以瞬间移动，利用分身提供战术优势。',
            color=(108, 92, 231),  # 深紫色
            size=20,
            avatar='img/Hero/暗影剑圣.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '使用暗影步寻找最佳攻击位置',
                '优先攻击高价值目标',
                '利用分身分散敌人注意力'
            ],
            tactics=[
                '瞬间移动',
                '致命攻击',
                '分身战术'
            ]
        )

        # 狂战士
        heroes['berserker'] = CharacterData(
            id='berserker',
            name='狂战士',
            english_name='Berserker',
            character_type=CharacterType.HERO,
            threat_level=3,
            hp=1200,
            attack=42,
            speed=28,
            armor=3,
            attack_range=30,
            attack_cooldown=0.8,
            special_ability='狂暴 - 血量越低攻击力越高，最高提升100%',
            description='狂暴战士，血量越低攻击力越强，是战场上最危险的存在。',
            color=(220, 38, 38),  # 深红色
            size=20,
            avatar='img/Hero/狂战士.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '血量越低越激进',
                '优先攻击血量高的敌人',
                '不畏惧死亡，持续战斗'
            ],
            tactics=[
                '狂暴输出',
                '血量换攻击',
                '不死不休'
            ]
        )

        # 牧师
        heroes['priest'] = CharacterData(
            id='priest',
            name='牧师',
            english_name='Priest',
            character_type=CharacterType.HERO,
            threat_level=2,
            hp=800,
            attack=10,
            speed=18,
            armor=3,
            attack_range=80,
            attack_cooldown=1.5,
            special_ability='治疗术 - 每秒治疗友军20点生命值',
            description='神圣治疗师，能够治疗友军并提供神圣护盾保护。',
            color=(255, 215, 0),  # 金色
            size=16,
            avatar='img/Hero/牧师.png',
            combat_type=CombatType.MAGIC,
            ai_behavior=[
                '优先治疗受伤的友军',
                '保持安全距离进行支援',
                '在友军身后提供治疗'
            ],
            tactics=[
                '团队支援',
                '持续治疗',
                '神圣保护'
            ]
        )

        # 盗贼
        heroes['thief'] = CharacterData(
            id='thief',
            name='盗贼',
            english_name='Thief',
            character_type=CharacterType.HERO,
            threat_level=2,
            hp=600,
            attack=28,
            speed=40,
            armor=1,
            attack_range=25,
            attack_cooldown=0.6,
            special_ability='偷窃 - 攻击时有机会偷取敌人金币',
            description='敏捷盗贼，拥有极高的移动速度和偷窃能力。',
            color=(128, 0, 128),  # 紫色
            size=13,
            avatar='img/Hero/盗贼.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '寻找落单的敌人',
                '优先攻击资源丰富的目标',
                '快速移动避免被包围'
            ],
            tactics=[
                '极速移动',
                '资源掠夺',
                '游击战术'
            ]
        )

        # 工程师
        heroes['engineer'] = CharacterData(
            id='engineer',
            name='工程师',
            english_name='Engineer',
            character_type=CharacterType.HERO,
            threat_level=3,
            hp=1100,
            attack=20,
            speed=15,
            armor=6,
            attack_range=60,
            attack_cooldown=2.0,
            special_ability='建造炮台 - 可以建造自动攻击炮台',
            description='机械工程师，能够建造防御炮台和陷阱来协助战斗。',
            color=(64, 64, 64),  # 深灰色
            size=18,
            avatar='img/Hero/工程师.png',
            combat_type=CombatType.RANGED,
            ai_behavior=[
                '寻找合适位置建造炮台',
                '保护建造的防御设施',
                '远程支援友军'
            ],
            tactics=[
                '阵地建造',
                '防御支援',
                '机械优势'
            ]
        )

        return heroes

    def _init_monsters(self) -> Dict[str, CharacterData]:
        """初始化怪物角色数据"""
        monsters = {}

        # 小恶魔
        monsters['imp'] = CharacterData(
            id='imp',
            name='小恶魔',
            english_name='Imp',
            character_type=CharacterType.MONSTER,
            threat_level=0,  # 怪物不计算威胁等级
            hp=800,
            attack=15,
            speed=25,
            armor=2,
            attack_range=30,
            attack_cooldown=1.0,
            special_ability='无',
            description='主力战士，平衡的攻防属性，适合作为基础战斗单位。',
            color=(255, 107, 107),  # 红色
            size=15,
            avatar='img/Monster/小恶魔.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '追击英雄 (距离 < 120像素)',
                '撤退 (血量 < 30%)',
                '随机巡逻 (无敌人时)'
            ],
            tactics=[
                '主力战士',
                '快速响应',
                '性价比高'
            ],
            cost=100,  # 基准战斗类怪物成本
            monster_category=MonsterCategory.COMBAT
        )

        # 哥布林苦工
        monsters['goblin_worker'] = CharacterData(
            id='goblin_worker',
            name='哥布林苦工',
            english_name='Goblin Worker',
            character_type=CharacterType.MONSTER,
            threat_level=0,
            hp=600,
            attack=8,
            speed=20,
            armor=0,
            attack_range=30,
            attack_cooldown=1.0,
            special_ability='挖掘黄金矿脉',
            description='经济单位，提供稳定的资源收入，需要其他生物保护。',
            color=(143, 188, 143),  # 浅绿色
            size=12,
            avatar='img/Monster/哥布林苦工.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '逃离敌人 (距离 < 60像素)',
                '挖掘黄金矿脉 (搜索半径 8格)',
                '随机巡逻 (无可达金矿时)'
            ],
            tactics=[
                '经济支柱',
                '风险单位',
                '数量优势'
            ],
            cost=80,  # 基准功能类怪物成本
            monster_category=MonsterCategory.FUNCTIONAL
        )

        # 石像鬼
        monsters['gargoyle'] = CharacterData(
            id='gargoyle',
            name='石像鬼',
            english_name='Gargoyle',
            character_type=CharacterType.MONSTER,
            threat_level=0,
            hp=1200,
            attack=25,
            speed=18,
            armor=6,
            attack_range=35,
            attack_cooldown=1.2,
            special_ability='重击 - 有30%概率造成双倍伤害',
            description='重装战士，高血量高攻击，适合正面作战和阵地防守。',
            color=(44, 62, 80),  # 深灰色
            size=20,
            avatar='img/Monster/石像鬼.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '追击英雄 (距离 < 100像素)',
                '保护友军 (附近有受伤生物时)',
                '巡逻防守 (无敌人时)'
            ],
            tactics=[
                '重装战士',
                '阵地防守',
                '团队保护'
            ],
            cost=150,  # 重新平衡的战斗类怪物成本
            monster_category=MonsterCategory.COMBAT
        )

        # 火蜥蜴
        monsters['fire_salamander'] = CharacterData(
            id='fire_salamander',
            name='火蜥蜴',
            english_name='Fire Salamander',
            character_type=CharacterType.MONSTER,
            threat_level=0,
            hp=1000,
            attack=28,
            speed=22,
            armor=3,
            attack_range=85,
            attack_cooldown=1.0,
            special_ability='火焰溅射 - 攻击造成范围伤害',
            description='远程火力，强大的远程攻击能力，能够同时攻击多个敌人。',
            color=(255, 71, 87),  # 橙红色
            size=18,
            avatar='img/Monster/火蜥蜴.png',
            combat_type=CombatType.RANGED,
            ai_behavior=[
                '远程攻击英雄 (距离 < 80像素)',
                '寻找最佳射击位置',
                '撤退到安全距离 (血量 < 40%)'
            ],
            tactics=[
                '远程火力',
                '范围伤害',
                '战术灵活性'
            ],
            cost=200,  # 重新平衡的战斗类怪物成本
            monster_category=MonsterCategory.COMBAT
        )

        # 暗影法师
        monsters['shadow_mage'] = CharacterData(
            id='shadow_mage',
            name='暗影法师',
            english_name='Shadow Mage',
            character_type=CharacterType.MONSTER,
            threat_level=0,
            hp=900,
            attack=22,
            speed=18,
            armor=2,
            attack_range=100,
            attack_cooldown=2.5,
            special_ability='暗影球 - 穿透攻击，伤害递减',
            description='魔法攻击，发射暗影球可以穿透所有敌人，对重甲单位有额外伤害。',
            color=(108, 92, 231),  # 深紫色
            size=16,
            avatar='img/Monster/暗影法师.png',
            combat_type=CombatType.MAGIC,
            ai_behavior=[
                '远程魔法攻击 (距离 < 100像素)',
                '寻找穿透最佳位置',
                '法力不足时撤退'
            ],
            tactics=[
                '穿透攻击',
                '远程威胁',
                '魔法伤害'
            ],
            cost=150,  # 魔法攻击成本
            monster_category=MonsterCategory.COMBAT
        )

        # 树人守护者
        monsters['tree_guardian'] = CharacterData(
            id='tree_guardian',
            name='树人守护者',
            english_name='Tree Guardian',
            character_type=CharacterType.MONSTER,
            threat_level=0,
            hp=2000,
            attack=35,
            speed=10,
            armor=10,
            attack_range=40,
            attack_cooldown=2.0,
            special_ability='藤蔓缠绕 - 减缓敌人移动速度',
            description='防守专家，超高的生命值和防御力，能够控制敌人。',
            color=(45, 80, 22),  # 深绿色
            size=25,
            avatar='img/Monster/树人守护者.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '保护关键位置',
                '攻击接近的敌人',
                '扎根防守 (无敌人时)'
            ],
            tactics=[
                '防守专家',
                '控制能力',
                '持续作战'
            ],
            cost=200,  # 防守专家成本
            monster_category=MonsterCategory.COMBAT
        )

        # 暗影领主
        monsters['shadow_lord'] = CharacterData(
            id='shadow_lord',
            name='暗影领主',
            english_name='Shadow Lord',
            character_type=CharacterType.MONSTER,
            threat_level=0,
            hp=3200,
            attack=55,
            speed=25,
            armor=12,
            attack_range=60,
            attack_cooldown=1.5,
            special_ability='暗影形态 - 可以切换近战和远程模式',
            description='全能战士，近战远程兼备，暗影传送提供极高的机动性。',
            color=(0, 0, 0),  # 纯黑色
            size=30,
            avatar='img/Monster/暗影领主.png',
            combat_type=CombatType.MIXED,
            ai_behavior=[
                '评估战斗情况，选择最佳攻击模式',
                '使用暗影传送调整位置',
                '保护其他生物'
            ],
            tactics=[
                '全能战士',
                '战术灵活性',
                '团队增益'
            ],
            cost=400,  # 全能战士成本
            monster_category=MonsterCategory.COMBAT
        )

        # 骨龙
        monsters['bone_dragon'] = CharacterData(
            id='bone_dragon',
            name='骨龙',
            english_name='Bone Dragon',
            character_type=CharacterType.MONSTER,
            threat_level=0,
            hp=4000,
            attack=60,
            speed=30,
            armor=18,
            attack_range=50,
            attack_cooldown=2.0,
            special_ability='骨刺风暴 - 范围攻击',
            description='终极武器，飞行能力提供战术优势，骨刺风暴对群体敌人有效。',
            color=(248, 249, 250),  # 骨白色
            size=35,
            avatar='img/Monster/骨龙.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '使用骨刺风暴攻击群体敌人',
                '追击单个强力敌人',
                '保护地下城核心'
            ],
            tactics=[
                '空中优势',
                '范围攻击',
                '终极威慑'
            ],
            cost=600,
            monster_category=MonsterCategory.COMBAT
        )

        # 地狱犬
        monsters['hellhound'] = CharacterData(
            id='hellhound',
            name='地狱犬',
            english_name='Hellhound',
            character_type=CharacterType.MONSTER,
            threat_level=3,
            hp=1100,
            attack=30,
            speed=35,
            armor=3,
            attack_range=25,
            attack_cooldown=0.8,
            special_ability='火焰吐息 - 攻击时造成持续火焰伤害',
            description='地狱猎犬，拥有极快的移动速度和火焰攻击能力。',
            color=(255, 69, 0),  # 橙红色
            size=16,
            avatar='img/Monster/地狱犬.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '快速追击敌人',
                '优先攻击脆弱的远程单位',
                '利用速度优势进行游击战'
            ],
            tactics=[
                '高速移动',
                '火焰攻击',
                '快速猎杀'
            ],
            cost=150,  # 高速猎犬成本
            monster_category=MonsterCategory.COMBAT
        )

        # 石魔像
        monsters['stone_golem'] = CharacterData(
            id='stone_golem',
            name='石魔像',
            english_name='Stone Golem',
            character_type=CharacterType.MONSTER,
            threat_level=4,
            hp=4500,
            attack=45,
            speed=8,
            armor=25,
            attack_range=40,
            attack_cooldown=2.5,
            special_ability='岩石护盾 - 减少50%受到的伤害',
            description='巨大的石魔像，拥有极高的防御力和生命值，是完美的坦克单位。',
            color=(105, 105, 105),  # 暗灰色
            size=30,
            avatar='img/Monster/石魔像.png',
            combat_type=CombatType.MELEE,
            ai_behavior=[
                '承受敌人攻击保护友军',
                '缓慢但坚定地推进',
                '优先攻击最近的敌人'
            ],
            tactics=[
                '无敌防御',
                '缓慢推进',
                '团队保护'
            ],
            cost=400,
            monster_category=MonsterCategory.COMBAT
        )

        # 魅魔
        monsters['succubus'] = CharacterData(
            id='succubus',
            name='魅魔',
            english_name='Succubus',
            character_type=CharacterType.MONSTER,
            threat_level=4,
            hp=1500,
            attack=32,
            speed=22,
            armor=5,
            attack_range=70,
            attack_cooldown=1.8,
            special_ability='魅惑 - 有30%概率让敌人攻击友军',
            description='魅惑恶魔，能够控制敌人的心智，让他们自相残杀。',
            color=(255, 20, 147),  # 深粉色
            size=17,
            avatar='img/Monster/魅魔.png',
            combat_type=CombatType.MAGIC,
            ai_behavior=[
                '优先魅惑高攻击力的敌人',
                '保持安全距离施法',
                '利用魅惑效果削弱敌人'
            ],
            tactics=[
                '心智控制',
                '混乱战术',
                '魔法干扰'
            ],
            cost=200,  # 心智控制成本
            monster_category=MonsterCategory.COMBAT
        )

        # 地精工程师
        monsters['goblin_engineer'] = CharacterData(
            id='goblin_engineer',
            name='地精工程师',
            english_name='Goblin Engineer',
            character_type=CharacterType.MONSTER,
            threat_level=2,
            hp=800,
            attack=12,
            speed=18,
            armor=2,
            attack_range=100,
            attack_cooldown=1.0,
            special_ability='建造陷阱 - 可以建造地雷和尖刺陷阱',
            description='地精工程师，能够建造各种陷阱来防御地下城。',
            color=(50, 205, 50),  # 酸绿色
            size=14,
            avatar='img/Monster/地精工程师.png',
            combat_type=CombatType.RANGED,
            ai_behavior=[
                '在关键位置建造陷阱',
                '保护建造的防御设施',
                '利用陷阱配合友军作战'
            ],
            tactics=[
                '陷阱建造',
                '防御支援',
                '地精科技'
            ],
            cost=100,  # 基准功能类怪物成本
            monster_category=MonsterCategory.FUNCTIONAL
        )

        return monsters

    def get_character(self, character_id: str) -> Optional[CharacterData]:
        """获取角色数据"""
        if character_id in self.heroes:
            return self.heroes[character_id]
        elif character_id in self.monsters:
            return self.monsters[character_id]
        return None

    def get_all_heroes(self) -> Dict[str, CharacterData]:
        """获取所有英雄数据"""
        return self.heroes

    def get_all_monsters(self) -> Dict[str, CharacterData]:
        """获取所有怪物数据"""
        return self.monsters

    def get_character_list(self, character_type: CharacterType) -> List[CharacterData]:
        """获取指定类型的角色列表"""
        if character_type == CharacterType.HERO:
            return list(self.heroes.values())
        elif character_type == CharacterType.MONSTER:
            return list(self.monsters.values())
        return []


# 全局角色数据库实例
character_db = CharacterDatabase()
