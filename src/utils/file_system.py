# src/utils/file_system.py
import platform
import subprocess
from typing import Callable

from flet import Colors, Page, SnackBar, Text


# 💡 FletのUI更新はメインスレッドで実行する必要があるため、スレッドセーフなラッパーを使用
def run_ui_update(page: Page, func: Callable, *args, **kwargs):
    """メインスレッドでFlet UI更新関数を実行する"""
    if hasattr(page, "run_thread"):
        page.run_thread(lambda: func(*args, **kwargs))
    else:
        func(*args, **kwargs)


def open_case_folder(page: Page, case_id: int, get_path_service: Callable[[int], str | None]):
    """
    案件IDに基づいてフォルダパスを取得し、OSに応じたコマンドでフォルダを開く。
    """
    try:
        folder_path = get_path_service(case_id)
    except Exception as e:
        print(f"フォルダパス取得エラー: {e}")
        folder_path = None

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
        except Exception as e:
            print(f"SnackBar表示エラー: {e}")

    if not folder_path:
        run_ui_update(
            page,
            show_snackbar,
            "⚠️ フォルダパスが登録されていません。",
            Colors.ORANGE_700,
            3000,
        )
        return

    _open_path_in_os(page, folder_path, show_snackbar)


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
        except Exception as e:
            print(f"SnackBar表示エラー: {e}")

    _open_path_in_os(page, path, show_snackbar)


def _open_path_in_os(page: Page, path: str, snackbar_func: Callable):
    """OSに応じたコマンドでパスを開く内部関数"""
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
            snackbar_func,
            f"⚠️ このOS ({current_os}) はサポートされていません。",
            Colors.RED_700,
            5000,
        )
        return

    try:
        subprocess.Popen(command)
        run_ui_update(
            page,
            snackbar_func,
            f"📁 開いています: {path}",
            Colors.BLUE_700,
        )
    except FileNotFoundError:
        run_ui_update(
            page,
            snackbar_func,
            f"エラー: '{command[0]}' コマンドが見つかりません。",
            Colors.RED_700,
            5000,
        )
    except Exception as ex:
        run_ui_update(
            page,
            snackbar_func,
            f"開くのに失敗しました: {ex}",
            Colors.RED_700,
            5000,
        )
