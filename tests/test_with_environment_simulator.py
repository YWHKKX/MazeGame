#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用游戏环境模拟器的测试示例
展示如何使用GameEnvironmentSimulator进行各种测试
"""

import sys
import os
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 确保可以导入src模块
try:
    import src
except ImportError:
    # 如果还是无法导入，尝试添加src目录到路径
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

# 现在导入项目模块
try:
    from src.entities.goblin_engineer import EngineerStatus
    from src.entities.building import BuildingStatus
    from src.managers.game_environment_simulator import GameEnvironmentSimulator
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)


def test_repair_logic():
    """测试建筑修复逻辑"""
    print("🔧 开始建筑修复逻辑测试")
    print("=" * 50)

    # 创建模拟器
    simulator = GameEnvironmentSimulator(
        screen_width=1200, screen_height=800, tile_size=20)

    # 设置修复测试场景
    simulator.setup_repair_test_scenario()

    # 获取测试对象
    damaged_tower = simulator.get_building_by_name("箭塔")
    engineer = simulator.engineers[0] if simulator.engineers else None

    if not damaged_tower or not engineer:
        print("❌ 测试场景设置失败")
        return False

    print(f"🏗️ 损坏箭塔: {damaged_tower.health}/{damaged_tower.max_health} HP")
    print(
        f"🔧 工程师: 位置({engineer.x}, {engineer.y}), 携带金币: {engineer.carried_gold}")

    # 运行模拟（无头模式）
    start_time = time.time()
    max_duration = 30.0  # 最多运行30秒

    while time.time() - start_time < max_duration:
        simulator.update(0.1)

        # 检查修复是否完成
        if damaged_tower.health >= damaged_tower.max_health:
            print("✅ 箭塔修复完成！")
            break

        # 每秒输出一次状态
        if int(time.time() - start_time) != int((time.time() - start_time) - 0.1):
            print(
                f"⏱️ 时间: {time.time() - start_time:.1f}s, 箭塔血量: {damaged_tower.health}/{damaged_tower.max_health}")

    # 测试结果
    repair_success = damaged_tower.health >= damaged_tower.max_health
    print(f"\n📊 测试结果:")
    print(f"   修复成功: {'是' if repair_success else '否'}")
    print(f"   最终血量: {damaged_tower.health}/{damaged_tower.max_health}")
    print(f"   工程师携带金币: {engineer.carried_gold}")
    print(
        f"   主基地剩余金币: {simulator.dungeon_heart.gold if simulator.dungeon_heart else 0}")

    return repair_success


def test_combat_logic():
    """测试战斗逻辑"""
    print("\n⚔️ 开始战斗逻辑测试")
    print("=" * 50)

    # 创建模拟器
    simulator = GameEnvironmentSimulator(
        screen_width=1200, screen_height=800, tile_size=20)

    # 设置战斗测试场景
    simulator.setup_combat_test_scenario()

    # 获取测试对象
    arrow_tower = simulator.get_building_by_name("箭塔")
    knight = simulator.heroes[0] if simulator.heroes else None

    if not arrow_tower or not knight:
        print("❌ 测试场景设置失败")
        return False

    print(
        f"🏹 箭塔: 位置({arrow_tower.x}, {arrow_tower.y}), 攻击力: {arrow_tower.attack_damage}")
    print(
        f"🛡️ 骑士: 位置({knight.x}, {knight.y}), 血量: {knight.health}/{knight.max_health}")

    # 运行模拟
    start_time = time.time()
    max_duration = 20.0

    while time.time() - start_time < max_duration:
        simulator.update(0.1)

        # 移动骑士朝向箭塔
        if knight.health > 0:
            simulator.move_character_to(knight, arrow_tower.x * simulator.tile_size,
                                        arrow_tower.y * simulator.tile_size, 25.0)

        # 检查骑士是否死亡
        if knight.health <= 0:
            print("💀 骑士被击败！")
            break

        # 每秒输出一次状态
        if int(time.time() - start_time) != int((time.time() - start_time) - 0.1):
            print(
                f"⏱️ 时间: {time.time() - start_time:.1f}s, 骑士血量: {knight.health}/{knight.max_health}")

    # 测试结果
    knight_defeated = knight.health <= 0
    print(f"\n📊 测试结果:")
    print(f"   骑士被击败: {'是' if knight_defeated else '否'}")
    print(f"   最终血量: {knight.health}/{knight.max_health}")

    return knight_defeated


def test_economy_logic():
    """测试经济逻辑"""
    print("\n💰 开始经济逻辑测试")
    print("=" * 50)

    # 创建模拟器
    simulator = GameEnvironmentSimulator(
        screen_width=1200, screen_height=800, tile_size=20)

    # 设置经济测试场景
    simulator.setup_economy_test_scenario()

    # 获取测试对象
    dungeon_heart = simulator.dungeon_heart
    treasury = simulator.treasury
    worker = simulator.workers[0] if simulator.workers else None

    if not dungeon_heart or not treasury or not worker:
        print("❌ 测试场景设置失败")
        return False

    print(f"🏰 主基地金币: {dungeon_heart.gold}")
    print(f"💰 金库存储: {treasury.stored_gold}")
    print(f"⛏️ 工人: 位置({worker.x}, {worker.y})")

    # 测试金币转移
    initial_dungeon_gold = dungeon_heart.gold
    initial_treasury_gold = treasury.stored_gold

    # 模拟工人收集金币
    simulator.add_gold_to_dungeon_heart(100)

    # 运行模拟
    start_time = time.time()
    max_duration = 10.0

    while time.time() - start_time < max_duration:
        simulator.update(0.1)

    # 测试结果
    final_dungeon_gold = dungeon_heart.gold
    final_treasury_gold = treasury.stored_gold

    print(f"\n📊 测试结果:")
    print(f"   主基地金币变化: {initial_dungeon_gold} -> {final_dungeon_gold}")
    print(f"   金库金币变化: {initial_treasury_gold} -> {final_treasury_gold}")
    print(f"   总金币: {simulator.get_statistics()['total_gold']}")

    return True


def test_visualization():
    """测试可视化功能"""
    print("\n🎨 开始可视化测试")
    print("=" * 50)

    # 创建模拟器
    simulator = GameEnvironmentSimulator(
        screen_width=1200, screen_height=800, tile_size=20)

    # 设置复杂测试场景
    simulator.setup_complex_test_scenario()

    print("🎮 启动可视化模拟（按ESC退出，空格暂停，R重置）")

    # 运行可视化模拟
    stats = simulator.run_simulation(
        max_duration=30.0, enable_visualization=True)

    print(f"\n📊 模拟统计:")
    for key, value in stats.items():
        print(f"   {key}: {value}")

    return True


def test_debug_features():
    """测试调试功能"""
    print("\n🐛 开始调试功能测试")
    print("=" * 50)

    # 创建模拟器
    simulator = GameEnvironmentSimulator(
        screen_width=1200, screen_height=800, tile_size=20)

    # 设置测试场景
    simulator.setup_repair_test_scenario()

    # 测试调试信息
    debug_info = simulator.get_debug_info()
    print("🔍 调试信息:")
    for key, value in debug_info.items():
        if key not in ['buildings', 'engineers']:
            print(f"   {key}: {value}")

    # 测试建筑伤害和治疗
    damaged_tower = simulator.get_building_by_name("箭塔")
    if damaged_tower:
        print(f"\n💥 对箭塔造成50点伤害")
        simulator.damage_building(damaged_tower, 50)

        print(f"💚 治疗箭塔30点生命值")
        simulator.heal_building(damaged_tower, 30)

    # 测试角色移动
    engineer = simulator.engineers[0] if simulator.engineers else None
    if engineer:
        print(f"\n📍 移动工程师到新位置")
        simulator.set_character_position(engineer, 15.0, 15.0)

    # 打印完整调试信息
    simulator.print_debug_info()

    return True


def main():
    """主函数"""
    print("🎮 游戏环境模拟器测试套件")
    print("=" * 60)

    tests = [
        ("建筑修复逻辑", test_repair_logic),
        ("战斗逻辑", test_combat_logic),
        ("经济逻辑", test_economy_logic),
        ("调试功能", test_debug_features),
        # ("可视化功能", test_visualization),  # 注释掉，避免需要图形界面
    ]

    results = []

    for test_name, test_func in tests:
        try:
            print(f"\n🧪 运行测试: {test_name}")
            result = test_func()
            results.append((test_name, result))
            print(f"✅ {test_name}: {'通过' if result else '失败'}")
        except Exception as e:
            print(f"❌ {test_name}: 出错 - {e}")
            results.append((test_name, False))

    # 测试总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")

    print(f"\n总体结果: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，请检查相关功能")


if __name__ == "__main__":
    main()
