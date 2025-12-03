# main.py
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List

# Fletのインポート規約準拠
from flet import (
    Colors,
    Column,
    CrossAxisAlignment,
    MainAxisAlignment,
    Page,
    ProgressRing,
    SnackBar,
    Text,
)
from flet import app as flet_app

# --- 設定 ---
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"
BACKUP_DIR = PROJECT_ROOT / "backup"
ASSETS_DIR = PROJECT_ROOT / "assets"

# 移動・整理対象の定義 (キー: 探索する部分パス/ファイル名, 値: 移動先)
MIGRATION_MAP: Dict[str, str] = {
    # 画面系
    "components/pages": "src/views",
    "pages": "src/views",
    "home.py": "src/views/home.py",
    "login.py": "src/views/auth/login.py",
    # データ・モデル系
    "database": "src/models",
    "models": "src/models",
    "db.py": "src/models/database.py",
    # ロジック・サービス系
    "selenium": "src/services/automation",
    "ai_service": "src/services/ai",
    # アセット
    "components/assets": "assets",
    "assets": "assets",
}

# --- ユーティリティ関数 ---


def run_combine_code() -> None:
    """combine_code.pyが存在すれば実行する"""
    combine_script = PROJECT_ROOT / "combine_code.py"
    if combine_script.exists():
        try:
            print("Running combine_code.py...")
            subprocess.run([sys.executable, str(combine_script)], check=True)
        except Exception as e:
            print(f"Error running combine_code.py: {e}")


def update_file_header(file_path: Path, relative_path: str) -> None:
    """ファイルの1行目にパス情報のコメントを書き込む/更新する"""
    try:
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        header_comment = f"# {relative_path}"

        if lines and lines[0].startswith("#"):
            lines[0] = header_comment
        else:
            lines.insert(0, header_comment)

        file_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception as e:
        print(f"Failed to update header for {file_path}: {e}")


def migrate_files() -> List[str]:
    """ファイル構成を再編し、移動したファイルのリストを返す"""
    moved_files = []

    # 1. 必要なディレクトリの作成
    for d in [SRC_DIR, BACKUP_DIR, ASSETS_DIR]:
        d.mkdir(exist_ok=True)

    # src内部の構造作成
    (SRC_DIR / "views").mkdir(exist_ok=True, parents=True)
    (SRC_DIR / "models").mkdir(exist_ok=True, parents=True)
    (SRC_DIR / "services").mkdir(exist_ok=True, parents=True)
    (SRC_DIR / "components").mkdir(exist_ok=True, parents=True)
    (SRC_DIR / "utils").mkdir(exist_ok=True, parents=True)

    # 2. ファイルの移動とヘッダー更新
    # プロジェクトルート内の全ファイルを走査（除外リストあり）
    exclude_dirs = {".git", ".venv", "venv", "__pycache__", ".idea", "src", "backup", "assets"}
    exclude_files = {"main.py", "combine_code.py", "requirements.txt", ".gitignore"}

    for item in PROJECT_ROOT.iterdir():
        if item.name in exclude_dirs or item.name in exclude_files:
            continue

        target_path = None
        is_backup = True

        # マッピング定義に基づいて移動先を決定
        for key, dest_rel_path in MIGRATION_MAP.items():
            if key in str(item):  # 部分一致判定
                is_backup = False
                base_dest = PROJECT_ROOT / dest_rel_path

                if item.is_file():
                    # ファイル名の維持または変更
                    dest_file_name = (
                        Path(dest_rel_path).name
                        if Path(dest_rel_path).suffix == ".py"
                        else item.name
                    )
                    target_path = (
                        base_dest.parent / dest_file_name
                        if Path(dest_rel_path).suffix == ".py"
                        else base_dest / dest_file_name
                    )

                    # ディレクトリなら作成
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                elif item.is_dir():
                    # ディレクトリの中身を移動
                    target_path = PROJECT_ROOT / dest_rel_path
                    target_path.mkdir(parents=True, exist_ok=True)
                break

        # 移動処理
        try:
            if is_backup:
                # バックアップへ移動
                target_path = BACKUP_DIR / item.name
                shutil.move(str(item), str(target_path))
                moved_files.append(f"Backing up: {item.name}")
            else:
                # 指定場所へ移動
                if item.is_file() and target_path:
                    # 移動前にコピーを作成し、元を削除（安全策）
                    shutil.copy2(str(item), str(target_path))
                    os.remove(str(item))

                    # ヘッダー更新
                    rel_path_str = str(target_path.relative_to(PROJECT_ROOT)).replace("\\", "/")
                    update_file_header(target_path, rel_path_str)
                    moved_files.append(f"Migrated: {item.name} -> {rel_path_str}")

                elif item.is_dir() and target_path:
                    # ディレクトリごとの移動
                    for sub_item in item.rglob("*"):
                        if sub_item.is_file():
                            rel_sub = sub_item.relative_to(item)
                            final_dest = target_path / rel_sub
                            final_dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(str(sub_item), str(final_dest))

                            # ヘッダー更新
                            rel_path_str = str(final_dest.relative_to(PROJECT_ROOT)).replace(
                                "\\", "/"
                            )
                            if final_dest.suffix == ".py":
                                update_file_header(final_dest, rel_path_str)

                    shutil.rmtree(str(item))
                    moved_files.append(f"Migrated Dir: {item.name} -> {target_path.name}")

        except Exception as e:
            print(f"Error moving {item.name}: {e}")

    # src/__init__.py の作成 (パッケージ化)
    (SRC_DIR / "__init__.py").touch()

    return moved_files


# --- メイン処理 ---


def main(page: Page):
    # 💡 ウィンドウ設定をここに集約
    # 起動時にウィンドウを最大化する（フルスクリーンではなく、ウィンドウ枠ありの最大サイズ）
    page.window.maximized = True
    
    # 固定サイズにしたい場合は以下を使用し、maximized = False にしてください
    # page.window.width = 1400
    # page.window.height = 850
    # page.window.center()

    page.title = "遺産整理業務アプリ Launcher"
    page.vertical_alignment = MainAxisAlignment.CENTER
    page.horizontal_alignment = CrossAxisAlignment.CENTER

    status_text = Text("システム構成を確認中...", size=16)
    loading = ProgressRing()

    page.add(
        Column(
            [
                Text("System Bootstrapper", size=30, weight="bold", color=Colors.BLUE_500),
                loading,
                status_text,
            ],
            alignment=MainAxisAlignment.CENTER,
            horizontal_alignment=CrossAxisAlignment.CENTER,
        )
    )
    page.update()

    # 1. combine_code.py の実行
    run_combine_code()

    # 2. マイグレーション実行
    if not (SRC_DIR / "app.py").exists():
        status_text.value = "ファイル構成を最適化しています..."
        page.update()
        time.sleep(1)

        logs = migrate_files()

        create_new_app_entry()

        status_text.value = f"完了: {len(logs)}個のファイルを処理しました。"
        status_text.color = Colors.GREEN
        loading.visible = False
        page.update()
        time.sleep(2)

    # 3. アプリケーション本体の起動
    try:
        page.clean()
        sys.path.append(str(PROJECT_ROOT))
        from src.app import main as app_main

        app_main(page)

    except ImportError as e:
        page.open(
            SnackBar(
                Text(f"起動エラー: アプリケーションファイルが見つかりません。\n{e}"),
                bgcolor=Colors.RED,
            )
        )
        page.update()
        print(f"Import Error details: {e}")
        traceback.print_exc()

    except Exception as e:
        page.open(SnackBar(Text(f"予期せぬエラーが発生しました: {e}"), bgcolor=Colors.RED))
        page.update()
        print(f"Unexpected Error details: {e}")
        traceback.print_exc()


def create_new_app_entry():
    """src/app.py が存在しない場合にテンプレートを作成する"""
    app_path = SRC_DIR / "app.py"
    if not app_path.exists():
        code = """# src/app.py
from flet import Page, Text, Colors, AppBar, SnackBar

def main(page: Page):
    page.title = "遺産整理・相続業務システム"
    page.theme_mode = "dark"
    
    page.appbar = AppBar(
        title=Text("相続業務管理"),
        bgcolor=Colors.BLUE_500,
        color=Colors.WHITE,
    )

    page.add(
        Text("システムは正常に再構築され、起動しました。", size=20, color=Colors.GREEN_700),
    )
"""
        app_path.write_text(code, encoding="utf-8")


def run_flet_app():
    """Fletアプリケーションを起動するラッパー"""
    try:
        print("Starting Flet application...")
        flet_app(target=main)
    except Exception as e:
        print(f"FATAL ERROR during Flet startup: {e}", file=sys.stderr)
        print("--- Traceback ---", file=sys.stderr)
        traceback.print_exc()


if __name__ == "__main__":
    run_flet_app()