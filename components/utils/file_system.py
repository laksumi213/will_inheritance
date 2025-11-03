import platform
import subprocess
import threading

from flet import Colors, Page, SnackBar, Text


# 💡 FletのUI更新はメインスレッドで実行する必要があるため、スレッドセーフなラッパーを使用
def run_ui_update(page: Page, func: callable, *args, **kwargs):
    """メインスレッドでFlet UI更新関数を実行する"""
    if threading.current_thread() != threading.main_thread():
        page.run_thread(lambda: func(*args, **kwargs))
    else:
        func(*args, **kwargs)


def open_case_folder(page: Page, case_id: int, get_path_service: callable):
    """
    案件IDに基づいてフォルダパスを取得し、OSに応じたコマンドでフォルダを開く。
    :param page: FletのPageオブジェクト (SnackBar表示とスレッドセーフ更新のため)
    :param case_id: 開きたい案件のID
    :param get_path_service: フォルダパスを取得するサービス関数 (例: deceased_service.get_case_folder_path)
    """

    folder_path = get_path_service(case_id)

    def show_snackbar(message: str, color=Colors.BLUE_700, duration=1500):
        # メインスレッドでSnackBarを表示する
        page.open(
            SnackBar(
                content=Text(message, color=Colors.WHITE),
                bgcolor=color,
                duration=duration,
            )
        )
        page.update()

    if not folder_path:
        run_ui_update(
            page,
            show_snackbar,
            "⚠️ 案件のフォルダパスがデータベースに登録されていません。",
            Colors.ORANGE_700,
            3000,
        )
        return

    # 1. OSに応じて適切なコマンドを選択
    current_os = platform.system()
    command = []

    if current_os == "Windows":
        # Windowsの場合: 'explorer' または 'start' コマンド
        command = ["explorer", folder_path]
    elif current_os == "Darwin":  # macOS
        # macOSの場合: 'open' コマンド (Finder)
        command = ["open", folder_path]
    elif current_os == "Linux":
        # Linuxの場合 (一般的な 'xdg-open' を使用)
        command = ["xdg-open", folder_path]
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
            f"📁 フォルダを開いています: {folder_path}",
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
