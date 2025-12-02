# project_organizer.py
import re
import shutil
from pathlib import Path
from typing import Dict


def organize_project():
    """
    プロジェクトのフォルダ構成を自動整理し、不要なファイルをバックアップするスクリプト。
    main.py と同じ階層に置いて実行してください。
    """

    # プロジェクトルート（このスクリプトがある場所）
    BASE_DIR = Path(__file__).parent
    BACKUP_DIR = BASE_DIR / "backup"

    # 1. 作成すべきディレクトリ構造
    REQUIRED_DIRS = [
        "assets/fonts",
        "models",
        "services",
        "views",
        "utils",
        "temp",
        "output",
        "backup",
    ]

    # 2. ファイル移動ルール (ファイル名 -> 移動先フォルダ)
    # ここに定義されたファイルは「必要なファイル」として扱われます
    FILE_MAPPING: Dict[str, str] = {
        "coordinate.py": "models",
        "pdf_service.py": "services",
        "coordinate_view.py": "views",
        "coordinate_selector.py": "views",  # 念のため別名も考慮
        "pdf_writer.py": "utils",
        "db_setup.py": "utils",
        # 必要に応じて追加
    }

    # 除外リスト（移動もバックアップもせず、ルートに残すファイル）
    EXCLUDE_FILES = {
        "main.py",
        "project_organizer.py",  # 自分自身
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
        else:
            print(f"  Exists:  {dir_path}")

    # 手順2: main.py の簡易解析 (依存関係の確認)
    print("\n[2] Analyzing main.py dependencies...")
    main_py_path = BASE_DIR / "main.py"
    detected_dependencies = set()

    if main_py_path.exists():
        try:
            with open(main_py_path, "r", encoding="utf-8") as f:
                content = f.read()
                # from folder import file 形式や import file 形式を簡易抽出
                # 例: from views.coordinate_view import ... -> coordinate_view
                matches = re.findall(r"from\s+(\w+)\.(\w+)\s+import", content)
                for folder, file in matches:
                    print(f"  Found dependency: {file}.py (in {folder})")
                    detected_dependencies.add(f"{file}.py")
        except Exception as e:
            print(f"  Warning: Could not analyze main.py: {e}")
    else:
        print("  Warning: main.py not found.")

    # 手順3: ファイルの移動
    print("\n[3] Moving known files to appropriate folders...")

    # ルートにある全ファイルを取得
    all_files = [f for f in BASE_DIR.iterdir() if f.is_file()]

    for file_path in all_files:
        filename = file_path.name

        # 除外ファイルはスキップ
        if filename in EXCLUDE_FILES or filename.startswith("."):
            continue

        # A. 定義済みマッピングにある場合 -> 指定フォルダへ移動
        if filename in FILE_MAPPING:
            target_folder = FILE_MAPPING[filename]
            dest_path = BASE_DIR / target_folder / filename
            _move_file(file_path, dest_path)
            continue

        # B. main.pyが依存しているファイルの場合 -> バックアップせず残す？
        # しかし、今回はフォルダ構成を正したいので、もしルートにあったら
        # 警告を出しつつバックアップに入れるか、あるいはマッピング漏れとして扱う。
        # 今回は「紐づいていないファイルをバックアップ」なので、
        # マッピングになく、かつルートにある .py ファイルはバックアップ対象とする。

        # バックアップ対象の判定 (Pythonファイルのみ対象)
        if filename.endswith(".py"):
            print(f"  Unknown file found: {filename} -> Moving to BACKUP")
            dest_path = BACKUP_DIR / filename
            _move_file(file_path, dest_path)

    print("\n--- Organization Complete! ---")
    print("Next Steps:")
    print("1. output/ や temp/ フォルダが作成されていることを確認してください。")
    print("2. backup/ フォルダの中身を確認し、本当に不要かチェックしてください。")
    print("3. main.py を実行してアプリが正常に起動することを確認してください。")


def _move_file(src: Path, dest: Path):
    """ファイルを安全に移動するヘルパー関数"""
    try:
        if src.resolve() == dest.resolve():
            return  # 移動先が同じなら何もしない

        if dest.exists():
            print(f"  ! Target exists, overwriting: {dest.name}")

        shutil.move(str(src), str(dest))
        print(f"  Moved: {src.name} -> {dest.parent.name}/{dest.name}")
    except Exception as e:
        print(f"  Error moving {src.name}: {e}")


if __name__ == "__main__":
    organize_project()
