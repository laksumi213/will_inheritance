# src/views/mizuho_visit_reserve_process.py
import threading

from flet import Colors, Page, SnackBar, Text

from src.services.automation_service import automation_service  # 共通AutomationServiceを利用
from src.services.deceased_service import get_financial_asset_automation_data

_active_reservations = {}


def start_mizuho_reservation(page: Page, case_id: int, branch: str, proc: str):
    data = get_financial_asset_automation_data(case_id, "0001")
    if not data:
        page.open(SnackBar(Text("データ不足"), bgcolor=Colors.RED))
        return

    def run():
        # AutomationServiceを使った実装例（またはSelenium直接記述）
        # ここではデモ用の簡易実装
        print(f"Starting Mizuho reservation for {branch}...")
        automation_service.navigate_to("https://www.mizuhobank.co.jp/")
        page.open(SnackBar(Text("ブラウザを起動しました"), bgcolor=Colors.BLUE))
        _active_reservations[case_id] = True

    threading.Thread(target=run).start()


def continue_mizuho_reservation(page: Page, case_id: int):
    if case_id not in _active_reservations:
        page.open(SnackBar(Text("Step1から開始してください"), bgcolor=Colors.RED))
        return

    def run():
        print("Continuing Mizuho reservation...")
        # フォーム入力ロジックなど
        page.open(SnackBar(Text("入力完了"), bgcolor=Colors.GREEN))
        del _active_reservations[case_id]

    threading.Thread(target=run).start()
