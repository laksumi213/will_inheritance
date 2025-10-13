# /main.py

import re

from flet import Colors, CrossAxisAlignment, Page, View, app

from components.pages.detail import DeceasedDetailView

# from components.pages.home import DeceasedListView
from components.pages.home import CaseDashboardView

# サービス層をインポート
from services.db_setup import add_initial_data, init_db

# データベースの初期化とテストデータの追加（アプリケーション起動時に一度だけ行う）

init_db()  # テーブル作成
add_initial_data()  # 初期データ投入


def main(page: Page):
    page.title = "顧客管理システム"
    page.bgcolor = Colors.AMBER_50
    page.horizontal_alignment = CrossAxisAlignment.CENTER

    # 💡 画面サイズの調整
    page.window.width = 1400  # 幅を広めに設定
    page.window.height = 850  # 高さを設定 (タスクバーなどを考慮し、画面より少し小さく)
    page.window.center()

    # 💡 ウィンドウを最大化する設定を追加
    # page.window_maximizable = True  # 最大化ボタンを有効にする
    # page.window_maximized = True  # 起動時にウィンドウを最大化する
    # page.window_resizable = True

    page.update()

    # ルーティングの処理
    def route_change(route):
        page.views.clear()

        # 1. メイン画面 (被相続人一覧)
        if page.route == "/":
            page.views.append(View(route="/", controls=[CaseDashboardView(page)]))
            # page.views.append(CaseDashboardView(page))

        # 2. 詳細画面 (被相続人詳細/相続人管理)
        elif re.match(r"^/detail/(-?\d+)$", page.route):
            match = re.match(r"^/detail/(-?\d+)$", page.route)
            deceased_id = int(match.group(1))  # -1 や 0、正の数をintとして正しく取得
            page.views.append(DeceasedDetailView(page, deceased_id))

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)


if __name__ == "__main__":
    app(target=main)
