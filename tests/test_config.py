#!/usr/bin/env python3
"""
公主连结配置系统测试

1. argument.yaml (配置定义) → args.json (中间文件) → config_generated.py (生成代码)
2. config/template.json (用户配置) + config_generated.py → 运行时配置
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "."))


def main():
    print("=" * 60)
    print("公主连结配置系统测试")
    print("=" * 60)

    # 生成配置文件
    print("\n生成配置文件...")
    try:
        from module.config.config_updater import ConfigGenerator

        generator = ConfigGenerator()
        generator.generate()
        print("配置文件生成成功")
    except Exception as e:
        print(f"配置文件生成失败: {e}")
        return

    # 加载并使用配置
    print("\n加载配置...")
    try:
        from module.config.config import PriconneConfig

        # 加载模板配置
        config = PriconneConfig("template")
        print("配置加载成功")

        # 显示配置值
        print(f"  - 语言设置: {config.GameSettings_Language}")
        print(f"  - 服务器: {config.GameSettings_Server}")
        print(f"  - 自动战斗: {config.GameSettings_AutoBattle}")
        print(f"  - 战斗速度: {config.GameSettings_BattleSpeed}")
        print(f"  - 每日任务: {config.Daily_Enable}")

    except Exception as e:
        print(f"配置加载失败: {e}")
        import traceback

        traceback.print_exc()
        return

    # 修改并保存配置
    print("\n修改配置...")
    try:
        # 使用传统方式修改配置
        config.GameSettings_Language = "jp"
        config.GameSettings_BattleSpeed = "x4"
        config.Daily_ArenaChallenge = False

        # 保存配置
        config.save()
        print("配置修改并保存成功")
        print(f"  - 语言已改为: {config.GameSettings_Language}")
        print(f"  - 战斗速度已改为: {config.GameSettings_BattleSpeed}")
        print(f"  - 竞技场挑战: {config.Daily_ArenaChallenge}")

    except Exception as e:
        print(f"配置修改失败: {e}")
        return

    # 功能
    print("\n功能测试...")
    try:
        # 跨任务获取配置
        scheduler_enable = config.cross_get("Pcr.Scheduler.Enable")
        print(f"  - 调度器状态: {scheduler_enable}")

        # 使用新接口获取配置
        main_team = config.get_value("General.Character.MainTeam")
        print(f"  - 主力队伍: {main_team}")

        # 批量设置
        with config.multi_set():
            config.Equipment_AutoEnhance = True
            config.Equipment_AutoRank = True
            config.Character_AutoLevelUp = True

        print("批量设置完成")
        print(f"  - 自动强化装备: {config.Equipment_AutoEnhance}")
        print(f"  - 自动升级装备: {config.Equipment_AutoRank}")
        print(f"  - 自动升级角色: {config.Character_AutoLevelUp}")

    except Exception as e:
        print(f"高级功能演示失败: {e}")
        import traceback

        traceback.print_exc()
        return

    # 验证配置系统结构
    print("\n验证配置系统结构...")
    try:
        # 检查生成的文件
        files_to_check = [
            "module/config/argument/args.json",
            "module/config/config_generated.py",
            "config/template.json",
        ]

        for file_path in files_to_check:
            if os.path.exists(file_path):
                print(f"  {file_path} 存在")
            else:
                print(f"  {file_path} 不存在")

        # 显示配置类继承关系
        print(f"\n  配置类继承关系:")
        print(f"  PriconneConfig -> ConfigUpdater, GeneratedConfig")
        print(
            f"  配置属性数量: {len([attr for attr in dir(config) if not attr.startswith('_')])}"
        )

    except Exception as e:
        print(f"验证失败: {e}")

    print("\n" + "=" * 60)
    print("配置系统演示完成!")
    print(
        "配置定义 (argument.yaml) → 中间文件 (args.json) → 生成代码 (config_generated.py)"
    )
    print("用户配置 (config/*.json) + 生成代码 → 运行时配置")
    print("=" * 60)


if __name__ == "__main__":
    main()
