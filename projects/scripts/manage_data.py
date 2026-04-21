#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据目录管理 CLI
用于设置 Obsidian 集成和迁移数据
"""
import os
import sys
import argparse

# 添加项目根目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from src.utils.data_paths import get_path_manager


def cmd_status(args):
    """显示数据目录状态"""
    pm = get_path_manager()
    status = pm.get_status()

    print("\n" + "=" * 50)
    print("[STATUS] Data Directory Status")
    print("=" * 50)

    print(f"\nWorkspace: {status['workspace']}")
    print(f"Projects Dir: {status['projects_dir']}")
    print(f"Projects Count: {status['projects_count']}")

    print("\nDirectory Status:")
    for name, exists in status['directories_exist'].items():
        icon = "[OK]" if exists else "[X]"
        print(f"  {icon} {name}")

    if status['obsidian_enabled']:
        print(f"\nObsidian Integration: ENABLED")
        print(f"   Vault: {status['obsidian_vault']}")
        if 'symlink_active' in status:
            link_status = "symlink" if status['symlink_active'] else "copy mode"
            print(f"   Connection: {link_status}")
    else:
        print(f"\nObsidian Integration: NOT ENABLED")

    print()


def cmd_setup_obsidian(args):
    """设置 Obsidian 集成"""
    pm = get_path_manager()

    vault_path = args.vault_path
    if not vault_path:
        print("[ERROR] Please specify Obsidian Vault path")
        print("   Usage: python manage_data.py setup-obsidian <vault_path>")
        return 1

    if not os.path.exists(vault_path):
        print(f"[ERROR] Path does not exist: {vault_path}")
        return 1

    print(f"\n[INFO] Setting up Obsidian integration...")
    print(f"   Vault: {vault_path}")

    result = pm.setup_obsidian_integration(
        vault_path=vault_path,
        use_symlink=not args.copy_mode,
        projects_folder=args.projects_folder,
        daily_folder=args.daily_folder
    )

    if result['success']:
        print(f"\n[OK] Setup successful!")
        print(f"   Method: {result['method']}")
        print(f"   {result['message']}")
    else:
        print(f"\n[ERROR] Setup failed: {result['message']}")
        return 1

    return 0


def cmd_migrate(args):
    """从旧结构迁移数据"""
    pm = get_path_manager()

    legacy_path = args.legacy_path
    if not legacy_path:
        print("[ERROR] Please specify legacy Vault path")
        print("   Usage: python manage_data.py migrate <legacy_vault_path>")
        return 1

    print(f"\n[INFO] Migrating data...")
    print(f"   Source: {legacy_path}")
    print(f"   Target: {pm.projects_dir}")

    result = pm.migrate_from_legacy(
        legacy_vault_path=legacy_path,
        backup=not args.no_backup
    )

    if result['success']:
        print(f"\n[OK] Migration successful!")
        print(f"   Migrated projects: {len(result['migrated_files'])}")
        for project in result['migrated_files']:
            print(f"     - {project}")

        if result['backup_path']:
            print(f"\n   Backup location: {result['backup_path']}")
    else:
        print(f"\n[ERROR] Migration failed")
        for error in result['errors']:
            print(f"   - {error}")
        return 1

    return 0


def cmd_ensure(args):
    """确保目录存在"""
    pm = get_path_manager()
    pm.ensure_directories()

    print("\n[OK] Directories created:")
    print(f"   - {pm.projects_dir}")
    print(f"   - {pm.memory_dir}")
    print(f"   - {pm.daily_notes_dir}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Pulse Learning System - Data Directory Manager"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # status
    p_status = subparsers.add_parser('status', help='Show data directory status')
    p_status.set_defaults(func=cmd_status)

    # setup-obsidian
    p_obsidian = subparsers.add_parser('setup-obsidian', help='Setup Obsidian integration')
    p_obsidian.add_argument('vault_path', nargs='?', help='Obsidian Vault path')
    p_obsidian.add_argument('--copy', dest='copy_mode', action='store_true',
                             help='Use copy mode instead of symlink')
    p_obsidian.add_argument('--projects-folder', default='Projects/PulseLearning',
                             help='Projects folder name')
    p_obsidian.add_argument('--daily-folder', default='Daily',
                             help='Daily notes folder name')
    p_obsidian.set_defaults(func=cmd_setup_obsidian)

    # migrate
    p_migrate = subparsers.add_parser('migrate', help='Migrate from legacy structure')
    p_migrate.add_argument('legacy_path', nargs='?', help='Legacy Vault path')
    p_migrate.add_argument('--no-backup', action='store_true',
                           help='Skip backup creation')
    p_migrate.set_defaults(func=cmd_migrate)

    # ensure
    p_ensure = subparsers.add_parser('ensure', help='Ensure directories exist')
    p_ensure.set_defaults(func=cmd_ensure)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
