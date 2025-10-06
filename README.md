# War for the Overworld - Python 独立版本 v1.1.0

🏰 一个基于 Python 和 Pygame 开发的地牢管理策略游戏，复刻经典游戏《War for the Overworld》的核心玩法。

## 📖 游戏简介

在这个游戏中，你扮演一个地下世界的统治者，需要挖掘地牢、管理资源、召唤怪物，并抵御入侵的英雄。游戏融合了策略、资源管理和实时战斗等多种元素。

## 🚀 快速启动

### 一键启动

#### Windows用户
双击运行 `PLAY_STANDALONE.bat` 文件

#### 所有平台
```bash
python start.py
```

### 系统要求
- Python 3.7+
- Pygame 2.0+
- Windows / macOS / Linux
- 内存: 512MB+ (推荐1GB+)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd GameTest
```

2. **安装依赖**
```bash
pip install pygame>=2.0.0 emoji
```

3. **启动游戏**
```bash
python standalone_game.py
```

## 🎮 游戏操作

### 基础控制
- **数字键**: 选择建造模式
  - 1: 挖掘 (10金)
  - 2: 建筑面板 (建造各种建筑)
  - 4: 召唤怪物 (弹出选择界面)
  - 5: 后勤召唤 (工程师/苦工选择)
- **鼠标左键**: 执行建造/召唤
- **鼠标右键**: 取消建造模式
- **WASD**: 移动相机
- **ESC**: 取消建造模式
- **B键**: 打开/关闭角色图鉴
- **P键**: 切换调试模式

### 游戏目标
1. **扩展地牢**：挖掘更大的地下空间
2. **资源积累**：通过挖矿和时间获得资源
3. **防御英雄**：召唤生物抵御英雄入侵
4. **战略布局**：合理规划地牢结构

## 🎮 核心功能

### 🏗️ 地牢建设系统
- **挖掘系统**：挖掘岩石创建地下空间
- **房间建造**：建造金库、巢穴等功能性房间
- **地牢之心**：游戏的核心建筑，位于起始区域中央

### 👹 生物管理系统
- **生物召唤**：召唤多种不同类型的怪物
- **移动限制**：生物只能在已挖掘区域内移动
- **智能AI**：生物具备巡逻、挖矿、战斗等行为

### ⚔️ 战斗系统
- **英雄入侵**：定期有英雄入侵地牢
- **实时战斗**：生物与英雄进行实时战斗
- **策略防御**：通过地牢布局引导战斗

### 💰 资源管理
- **多种资源**：黄金、法力、食物、原始黄金
- **资源生成**：通过时间和特殊行为获得资源
- **成本平衡**：建造和召唤需要消耗相应资源
- **整数系统**：所有资源都是整数，避免小数显示

### 🔨 特殊单位
- **哥布林苦工**：专门的挖矿单位，可以挖掘金矿脉获取原始黄金
- **地精工程师**：专门的建造单位，可以建造各种建筑和房间
- **智能寻路**：生物会自动寻找可达的目标区域
- **状态指示器**：所有单位都有实时的状态可视化指示器

## 🏛️ 项目结构

```
MazeMaster/
├── standalone_game.py      # 主游戏文件
├── start.py               # 一键启动器
├── PLAY_STANDALONE.bat    # Windows启动脚本
├── src/                   # 核心源代码模块
│   ├── core/             # 核心常量和配置
│   │   ├── constants.py  # 游戏常量配置
│   │   ├── enums.py      # 枚举定义
│   │   ├── game_state.py # 游戏状态管理
│   │   ├── emoji_constants.py # Emoji常量
│   │   └── ui_design.py  # UI设计系统
│   ├── managers/         # 游戏管理器
│   │   ├── font_manager.py # 统一字体管理器
│   │   ├── movement_system.py # 移动系统
│   │   ├── building_manager.py # 建筑管理器
│   │   ├── resource_manager.py # 资源管理器
│   │   ├── tile_manager.py # 瓦片管理器
│   │   ├── gold_mine_manager.py # 金矿管理器
│   │   ├── auto_assigner.py # 自动分配器
│   │   ├── engineer_assigner.py # 工程师分配器
│   │   ├── optimized_mining_system.py # 优化挖矿系统
│   │   ├── resource_consumption_manager.py # 资源消耗管理
│   │   └── game_environment_simulator.py # 游戏环境模拟器
│   ├── entities/         # 游戏实体
│   │   ├── character_data.py # 角色数据
│   │   ├── creature.py   # 生物实体基类
│   │   ├── building.py   # 建筑实体
│   │   ├── building_types.py # 建筑类型定义
│   │   ├── configs.py    # 实体配置
│   │   ├── tile.py       # 瓦片实体
│   │   ├── gold_mine.py  # 金矿实体
│   │   ├── heros.py      # 英雄实体
│   │   ├── monsters.py   # 怪物实体
│   │   ├── hero/         # 英雄子模块
│   │   │   ├── archer.py # 弓箭手
│   │   │   └── knight.py # 骑士
│   │   └── monster/      # 怪物子模块
│   │       ├── goblin_engineer.py # 地精工程师
│   │       ├── goblin_worker.py  # 哥布林苦工
│   │       ├── imp.py           # 小恶魔
│   │       └── orc_warrior.py   # 兽人战士
│   ├── systems/          # 游戏系统
│   │   ├── combat_system.py # 战斗系统
│   │   ├── physics_system.py # 物理系统
│   │   ├── placement_system.py # 放置系统
│   │   ├── skill_system.py # 技能系统
│   │   ├── advanced_pathfinding.py # 高级寻路
│   │   ├── bstar_pathfinding.py # B*寻路算法
│   │   ├── unified_pathfinding.py # 统一寻路系统
│   │   ├── navmesh_system.py # 导航网格系统
│   │   ├── reachability_system.py # 可达性系统
│   │   ├── advanced_area_damage.py # 高级区域伤害
│   │   └── knockback_animation.py # 击退动画
│   ├── effects/          # 特效系统
│   │   ├── effect_manager.py # 特效管理器
│   │   ├── effect_pool.py # 特效对象池
│   │   ├── effect_renderer.py # 特效渲染器
│   │   ├── particle_system.py # 粒子系统
│   │   ├── projectile_system.py # 投射物系统
│   │   ├── area_effect_system.py # 区域特效系统
│   │   ├── blade_trail_effect.py # 刀光特效
│   │   └── glow_effect.py # 发光特效
│   ├── ui/               # 用户界面
│   │   ├── base_ui.py    # UI基类
│   │   ├── game_ui.py    # 游戏主UI
│   │   ├── character_bestiary.py # 角色图鉴
│   │   ├── monster_selection.py # 怪物选择界面
│   │   ├── logistics_selection.py # 后勤选择界面
│   │   ├── building_ui.py # 建筑UI
│   │   └── status_indicator.py # 状态指示器
│   ├── utils/            # 工具模块
│   │   ├── logger.py     # 日志系统
│   │   └── tile_converter.py # 瓦片转换器
│   ├── game/             # 游戏逻辑
│   └── migration/        # 数据迁移
├── docs/                 # 文档目录
│   ├── README.md         # 文档中心
│   ├── VERSION_1.1.0.md  # 版本1.1.0文档
│   ├── STANDALONE.md     # 独立版本文档
│   ├── CHARACTER_DESIGN.md # 角色设计文档
│   ├── BUILDING_SYSTEM.md # 建筑系统文档
│   ├── COMBAT_SYSTEM.md  # 战斗系统文档
│   ├── PHYSICS_SYSTEM.md # 物理系统文档
│   ├── MINING_SYSTEM.md  # 挖矿系统文档
│   ├── MOVEMENT_SYSTEM.md # 移动系统文档
│   ├── STATUS_INDICATOR.md # 状态指示器文档
│   ├── UI_BEAUTIFICATION.md # UI美化文档
│   ├── GOLD_SYSTEM.md    # 金币系统文档
│   ├── SKILL_SYSTEM.md   # 技能系统文档
│   ├── EFFECTS_SYSTEM.md # 特效系统文档
│   ├── UNIFIED_FACTION_SYSTEM.md # 统一阵营系统
│   ├── UNIFIED_PLACEMENT_INTEGRATION.md # 统一放置集成
│   ├── KNOCKBACK_REFACTOR.md # 击退重构文档
│   └── GAME_ENVIRONMENT_SIMULATOR.md # 游戏环境模拟器
├── img/                  # 游戏图片资源
│   ├── Hero/            # 英雄图片
│   └── Monster/         # 怪物图片
├── tests/                # 测试文件
│   ├── README.md         # 测试说明
│   ├── building_showcase_simulator.py # 建筑展示模拟器
│   ├── demon_lair_summon_simulator.py # 恶魔巢穴召唤模拟器
│   ├── orc_lair_training_simulator.py # 兽人巢穴训练模拟器
│   ├── arcane_tower_attack_simulator.py # 奥术塔攻击模拟器
│   ├── arrow_tower_attack_simulator.py # 箭塔攻击模拟器
│   ├── treasury_storage_simulator.py # 金库存储模拟器
│   └── repair_test_with_simulator.py # 修复测试模拟器
├── requirements_standalone.txt # Python依赖
├── README.md             # 项目说明
└── CHANGELOG.md          # 更新日志
```

## 🔧 技术特性

### 🎨 用户界面
- **现代化设计**：深色主题，圆角设计，现代化UI组件
- **统一字体管理**：自动检测并使用系统中文字体
- **实时信息显示**：资源状态、建造选项、游戏状态
- **视觉反馈**：emoji图标和颜色编码
- **响应式布局**：自适应不同屏幕尺寸
- **交互反馈**：悬停效果和状态指示

### 🧠 游戏AI
- **智能寻路**：生物自动寻找可移动路径
- **行为树**：不同类型单位有不同的AI行为
- **动态目标**：根据环境变化调整行为目标

### ⚡ 性能优化
- **视野裁剪**：只渲染屏幕内的元素
- **高效碰撞检测**：优化的移动验证系统
- **内存管理**：合理的对象生命周期管理
- **资源累积器**：高效的资源更新机制

### 🎯 新特性
- 🔧 **模块化架构**：清晰的代码组织结构
- 🎨 **统一字体管理**：emoji和文字分离渲染
- 📊 **完整的角色图鉴系统**：详细的角色信息展示
- 💾 **状态指示器系统**：生物状态可视化
- 🎨 **美化的UI界面**：现代化的用户界面设计
- 💰 **整数资源系统**：清晰的资源显示

## 🎨 游戏界面

游戏界面包含：
- 🗺️ **主游戏区域**：显示地牢地图和单位
- 📊 **资源面板**：实时显示各种资源状态
- 🔨 **建造面板**：显示可用的建造选项
- 📊 **状态面板**：显示当前游戏状态信息
- 📚 **角色图鉴**：详细的角色信息和属性
- 👹 **怪物选择**：美观的怪物召唤界面

### UI面板详情

**资源面板** (左上角):
- 💰 黄金数量
- 🔮 法力值
- 🍖 食物储备
- ⚡ 原始黄金
- 👹 怪物数量
- 🏆 当前分数

**建造面板** (右上角):
- 🔨 建造选项列表
- 💰 建造成本显示
- ✅ 当前选中模式高亮

**状态面板** (左下角):
- 🖱️ 鼠标坐标信息
- 🌍 世界坐标显示
- 📹 相机位置
- 🔧 当前建造模式

## 📋 依赖要求

```bash
pip install pygame>=2.0.0 emoji
```

## 🐛 问题反馈

如果遇到问题，请检查：
1. Python版本是否为3.7+
2. Pygame是否正确安装
3. 系统是否支持中文字体显示
4. 是否有足够的系统权限

## 🔧 开发文档

项目包含完整的开发文档：
- `docs/CHARACTER_DESIGN.md` - 角色设计文档
- `docs/COMBAT_SYSTEM.md` - 战斗系统文档
- `docs/MINING_SYSTEM.md` - 挖矿系统文档
- `docs/MOVEMENT_SYSTEM.md` - 移动系统文档
- `docs/STATUS_INDICATOR.md` - 状态指示器文档
- `docs/UI_BEAUTIFICATION.md` - UI美化文档

## 📝 开发计划

### 已完成
- ✅ 模块化架构重构
- ✅ 统一字体管理系统
- ✅ 角色图鉴系统
- ✅ 状态指示器系统
- ✅ UI界面美化
- ✅ 资源整数化
- ✅ emoji常量管理

### 已完成
- ✅ 地精工程师建造系统
- ✅ 状态指示器系统
- ✅ 智能金币管理
- ✅ 统一移动系统
- ✅ 建筑管理系统

### 计划中
- [ ] 添加更多房间类型
- [ ] 实现保存/加载功能
- [ ] 添加音效和背景音乐
- [ ] 增加更多生物类型
- [ ] 实现多层地牢系统
- [ ] 添加魔法系统

## 🎯 游戏特色

### 策略深度
- **资源管理**：平衡收入与支出
- **空间规划**：合理设计地牢布局
- **时机把握**：选择合适的召唤时机
- **战术配合**：不同单位的协同作战

### 视觉体验
- **现代化UI**：深色主题，圆角设计
- **流畅动画**：平滑的移动和战斗效果
- **直观反馈**：清晰的状态指示和视觉提示
- **中文支持**：完整的中文界面和字体

### 技术亮点
- **模块化设计**：易于扩展和维护
- **统一管理**：字体、颜色、样式的统一管理
- **性能优化**：高效的渲染和更新机制
- **跨平台**：支持Windows、macOS、Linux

## 📄 许可证

本项目仅供学习和研究使用。

## 🙏 致谢

感谢原版《War for the Overworld》游戏的灵感启发。

---

🎮 **开始你的地下王国征程吧！** 🏰