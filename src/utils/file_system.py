# src/utils/file_system.py
import platform
import subprocess
import threading
from typing import Callable, Optional

from flet import Colors, Page, SnackBar, Text


# 💡 FletのUI更新はメインスレッドで実行する必要があるため、スレッドセーフなラッパーを使用
def run_ui_update(page: Page, func: Callable, *args, **kwargs):
    """メインスレッドでFlet UI更新関数を実行する"""
    if hasattr(page, "run_thread"):
        page.run_thread(lambda: func(*args, **kwargs))
    else:
        func(*args, **kwargs)


def open_case_folder(page: Page, case_id: int, get_path_service: Callable[[int], Optional[str]]):
    """
    案件IDに基づいてフォルダパスを取得し、OSに応じたコマンドでフォルダを開く。
    :param page: FletのPageオブジェクト
    :param case_id: 開きたい案件のID
    :param get_path_service: フォルダパスを取得するサービス関数
    """

    try:
        folder_path = get_path_service(case_id)
    except Exception as e:
        print(f"Path retrieval failed: {e}")
        folder_path = None

    def show_snackbar(message: str, color=Colors.BLUE_700, duration=1500):
        # メインスレッドでSnackBarを表示する
        try:
            page.open(
                SnackBar(
                    content=Text(message, color=Colors.WHITE),
                    bgcolor=color,
                    duration=duration,
                )
            )
            page.update()
        except Exception:
            pass

    if not folder_path:
        run_ui_update(
            page,
            show_snackbar,
            "⚠️ 案件のフォルダパスがデータベースに登録されていません。",
            Colors.ORANGE_700,
            3000,
        )
        return

    open_path(page, folder_path)


def open_path(page: Page, path: str):
    """指定されたパスをOSのエクスプローラー等で開く"""

    def show_snackbar(message: str, color=Colors.BLUE_700, duration=1500):
        try:
            page.open(
                SnackBar(
                    content=Text(message, color=Colors.WHITE),
                    bgcolor=color,
                    duration=duration,
                )
            )
            page.update()
        except Exception:
            pass

    # 1. OSに応じて適切なコマンドを選択
    current_os = platform.system()
    command = []

    if current_os == "Windows":
        command = ["explorer", path]
    elif current_os == "Darwin":  # macOS
        command = ["open", path]
    elif current_os == "Linux":
        command = ["xdg-open", path]
    else:
        run_ui_update(
            page,
            show_snackbar,
            f"⚠️ このOS ({current_os}) はサポートされていません。",
            Colors.RED_700,
            5000,
        )
        return

    # 2. 外部プロセスとしてコマンドを実行
    try:
        # Popen を使用してアプリケーションのフリーズを防ぐ
        subprocess.Popen(command)
        run_ui_update(
            page,
            show_snackbar,
            f"📁 フォルダを開いています: {path}",
            Colors.BLUE_700,
        )
    except FileNotFoundError:
        run_ui_update(
            page,
            show_snackbar,
            f"エラー: '{command[0]}' コマンドが見つかりません。",
            Colors.RED_700,
            5000,
        )
    except Exception as ex:
        run_ui_update(
            page,
            show_snackbar,
            f"フォルダを開くのに失敗しました: {ex}",
            Colors.RED_700,
            5000,
        )