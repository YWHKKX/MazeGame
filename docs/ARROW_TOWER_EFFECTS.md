# 箭塔特效系统文档

## 概述

本文档描述了箭塔攻击特效系统的实现，包括普通攻击特效、暴击特效和命中特效。箭塔由地精工程师建造和维护，支持工程师管理系统。

## 特效类型

### 1. 普通箭矢特效 (`tower_arrow_shot`)

- **类型**: 投射物特效
- **投射物类型**: `tower_arrow`
- **速度**: 600 像素/秒
- **伤害**: 30 点
- **颜色**: 灰色 (200, 200, 200)
- **特殊效果**: 拖尾效果
- **音效**: `tower_arrow.wav`
- **屏幕震动**: 轻微震动 (强度: 0.05, 持续时间: 0.05秒)

### 2. 暴击箭矢特效 (`tower_critical_arrow`)

- **类型**: 投射物特效
- **投射物类型**: `tower_arrow`
- **速度**: 700 像素/秒
- **伤害**: 60 点
- **颜色**: 金色 (255, 215, 0)
- **特殊效果**: 拖尾效果 + 发光效果
- **音效**: `tower_critical.wav`
- **屏幕震动**: 中等震动 (强度: 0.1, 持续时间: 0.1秒)

### 3. 命中特效 (`tower_arrow_impact`)

- **类型**: 粒子特效
- **粒子数量**: 8 个火花
- **颜色**: 白色 (255, 255, 255)
- **速度范围**: 80-150 像素/秒
- **大小范围**: 3-6 像素
- **音效**: `arrow_impact.wav`
- **屏幕震动**: 中等震动 (强度: 0.08, 持续时间: 0.08秒)

## 技术实现

### 投射物系统

在 `src/effects/projectile_system.py` 中添加了 `create_tower_arrow()` 方法：

```python
def create_tower_arrow(self, x: float, y: float, target_x: float, target_y: float,
                       speed: float = 600, damage: int = 30, is_critical: bool = False) -> Projectile:
    """创建箭塔箭矢"""
    if is_critical:
        # 暴击箭矢 - 金色，更大，更快
        arrow = self._get_or_create_projectile(
            x, y, target_x, target_y, speed, damage,
            (255, 215, 0), 6, "tower_arrow", 3000  # 金色，3秒生命周期
        )
        arrow.glow_effect = True
        arrow.trail_effect = True
    else:
        # 普通箭矢 - 灰色
        arrow = self._get_or_create_projectile(
            x, y, target_x, target_y, speed, damage,
            (200, 200, 200), 4, "tower_arrow", 3000  # 灰色，3秒生命周期
        )
        arrow.trail_effect = True
    
    return arrow
```

### 渲染系统

在 `src/effects/projectile_system.py` 中添加了 `_render_tower_arrow()` 方法：

- 绘制精美的箭矢形状
- 支持边框效果
- 暴击箭矢具有发光光环和高光效果
- 箭矢长度和宽度根据大小参数动态调整

### 特效管理器

在 `src/effects/effect_manager.py` 中添加了箭塔特效配置：

```python
"tower_arrow_shot": {
    "type": "projectile",
    "projectile_type": "tower_arrow",
    "speed": 600,
    "damage": 30,
    "color": (200, 200, 200),
    "trail_effect": True,
    "sound": "tower_arrow.wav",
    "screen_shake": {"intensity": 0.05, "duration": 0.05}
},
"tower_critical_arrow": {
    "type": "projectile",
    "projectile_type": "tower_arrow",
    "speed": 700,
    "damage": 60,
    "color": (255, 215, 0),
    "trail_effect": True,
    "glow_effect": True,
    "sound": "tower_critical.wav",
    "screen_shake": {"intensity": 0.1, "duration": 0.1}
},
"tower_arrow_impact": {
    "type": "particle",
    "particles": {"sparks": 8, "color": (255, 255, 255), "velocity_range": (80, 150), "size_range": (3, 6)},
    "sound": "arrow_impact.wav",
    "screen_shake": {"intensity": 0.08, "duration": 0.08}
}
```

### 游戏集成

在 `standalone_game.py` 中更新了箭塔攻击逻辑：

```python
if attack_result['attacked']:
    # 根据是否为暴击选择不同的特效
    if attack_result.get('is_critical', False):
        effect_type = 'tower_critical_arrow'
    else:
        effect_type = 'tower_arrow_shot'
    
    # 创建攻击特效
    self.effect_manager.create_effect(
        effect_type,
        tower.x * self.tile_size + self.tile_size // 2,
        tower.y * self.tile_size + self.tile_size // 2,
        best_target.x,
        best_target.y,
        damage=attack_result['damage']
    )
    
    # 创建命中特效
    self.effect_manager.create_effect(
        'tower_arrow_impact',
        best_target.x,
        best_target.y,
        None, None,
        damage=attack_result['damage']
    )
```

## 特效特点

### 视觉效果

1. **普通箭矢**: 灰色，简洁的箭矢形状，带有拖尾效果
2. **暴击箭矢**: 金色，更大尺寸，带有发光光环和高光效果
3. **命中特效**: 白色火花粒子爆炸效果

### 音效支持

- 普通攻击音效: `tower_arrow.wav`
- 暴击攻击音效: `tower_critical.wav`
- 命中音效: `arrow_impact.wav`

### 屏幕震动

- 普通攻击: 轻微震动
- 暴击攻击: 中等震动
- 命中效果: 中等震动

## 性能优化

- 使用对象池管理投射物
- 限制同时存在的特效数量
- 特效自动清理机制
- 低性能模式支持

## 测试验证

通过控制台测试验证了以下功能：

1. ✅ 箭塔攻击逻辑正常工作
2. ✅ 目标选择系统正常
3. ✅ 普通攻击特效创建成功
4. ✅ 暴击攻击特效创建成功
5. ✅ 命中特效创建成功
6. ✅ 特效更新系统正常
7. ✅ 特效配置正确加载

## 使用方法

箭塔特效系统会自动在箭塔攻击时触发，无需手动调用。系统会根据攻击结果自动选择：

- 普通攻击 → `tower_arrow_shot` 特效
- 暴击攻击 → `tower_critical_arrow` 特效
- 命中目标 → `tower_arrow_impact` 特效

## 扩展性

系统设计支持未来扩展：

- 可以添加更多箭矢类型
- 可以自定义特效参数
- 可以添加更多视觉和音效效果
- 支持不同箭塔类型的专属特效
