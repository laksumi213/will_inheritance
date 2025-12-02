# project_organizer.py
import re
import shutil
from pathlib import Path
from typing import Dict


def organize_project():
    """
    プロジェクトのフォルダ構成を自動整理し、不要なファイルをバックアップするスクリプト。
    Componentsフォルダの移行にも対応しています。
    main.py と同じ階層に置いて実行してください。
    """

    BASE_DIR = Path(__file__).parent
    BACKUP_DIR = BASE_DIR / "backup"

    # 1. 作成すべきディレクトリ構造
    REQUIRED_DIRS = [
        "assets/fonts",
        "models",
        "services",
        "views",
        "views/components",  # Componentsの移行先
        "utils",
        "temp",
        "output",
        "backup",
    ]

    # 2. ファイル移動ルール (ファイル名 -> 移動先フォルダ)
    FILE_MAPPING: Dict[str, str] = {
        "coordinate.py": "models",
        "pdf_service.py": "services",
        "coordinate_view.py": "views",
        "coordinate_selector.py": "views",
        "pdf_writer.py": "utils",
        "db_setup.py": "utils",
    }

    # 除外リスト
    EXCLUDE_FILES = {
        "main.py",
        "project_organizer.py",
        "__init__.py",
        ".gitignore",
        "requirements.txt",
        "README.md",
    }

    print(f"--- Starting Project Organization in: {BASE_DIR} ---")

    # 手順1: ディレクトリ作成
    print("\n[1] Creating directories...")
    for dir_path in REQUIRED_DIRS:
        target_dir = BASE_DIR / dir_path
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {dir_path}")

    # 手順2: Componentsフォルダの処理 (特別対応)
    print("\n[2] Checking 'Components' folder...")
    # 大文字小文字を考慮して探す
    comp_src = None
    if (BASE_DIR / "Components").exists():
        comp_src = BASE_DIR / "Components"
    elif (BASE_DIR / "components").exists():
        comp_src = BASE_DIR / "components"

    if comp_src and comp_src.is_dir():
        # views/components へ移動
        comp_dest = BASE_DIR / "views" / "components"
        print(f"  Found '{comp_src.name}'. Moving contents to 'views/components'...")

        # 中身を移動
        for item in comp_src.iterdir():
            if item.name == "__init__.py":
                continue  # 重複防止のためスキップ
            try:
                shutil.move(str(item), str(comp_dest / item.name))
                print(f"    Moved: {item.name}")
            except Exception as e:
                print(f"    Error moving {item.name}: {e}")

        # 元フォルダが空なら削除
        try:
            if not any(comp_src.iterdir()):
                comp_src.rmdir()
                print(f"  Removed empty folder: {comp_src.name}")
        except:
            pass
    else:
        print("  'Components' folder not found. Skipping.")

    # 手順3: main.py の簡易解析
    print("\n[3] Analyzing main.py dependencies...")
    main_py_path = BASE_DIR / "main.py"

    if main_py_path.exists():
        try:
            with open(main_py_path, "r", encoding="utf-8") as f:
                content = f.read()
                matches = re.findall(r"from\s+(\w+)\.(\w+)\s+import", content)
                for folder, file in matches:
                    print(f"  Found dependency: {file}.py (in {folder})")
        except Exception as e:
            print(f"  Warning: Could not analyze main.py: {e}")

    # 手順4: ファイルの移動 (ルートファイルの整理)
    print("\n[4] Moving root files...")
    all_files = [f for f in BASE_DIR.iterdir() if f.is_file()]

    for file_path in all_files:
        filename = file_path.name

        if filename in EXCLUDE_FILES or filename.startswith("."):
            continue

        # A. 定義済みマッピング
        if filename in FILE_MAPPING:
            target_folder = FILE_MAPPING[filename]
            dest_path = BASE_DIR / target_folder / filename
            _move_file(file_path, dest_path)
            continue

        # B. その他 (.pyファイルはバックアップへ)
        if filename.endswith(".py"):
            print(f"  Unknown file found: {filename} -> Moving to BACKUP")
            dest_path = BACKUP_DIR / filename
            _move_file(file_path, dest_path)

    print("\n--- Organization Complete! ---")
    print("重要: 'Components' フォルダの中身を 'views/components' に移動しました。")
    print("これに伴い、import文のパス変更が必要になる場合があります。")
    print("例: 'from Components.header import ...' -> 'from views.components.header import ...'")


def _move_file(src: Path, dest: Path):
    """ファイルを安全に移動するヘルパー関数"""
    try:
        if src.resolve() == dest.resolve():
            return

        if dest.exists():
            print(f"  ! Target exists in {dest.parent.name}, skipping overwrite of: {dest.name}")
            # 安全のため、同名ファイルがある場合はバックアップに日時をつけて退避などの処理も考えられるが
            # 今回は単純にスキップ、またはバックアップへ回す
            backup_dest = dest.parent.parent.parent / "backup" / f"{dest.name}_duplicate"
            shutil.move(str(src), str(backup_dest))
            print(f"    -> Moved to backup instead: {backup_dest.name}")
            return

        shutil.move(str(src), str(dest))
        print(f"  Moved: {src.name} -> {dest.parent.name}/{dest.name}")
    except Exception as e:
        print(f"  Error moving {src.name}: {e}")


if __name__ == "__main__":
    organize_project()
