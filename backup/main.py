# main.py

import re

from flet import (
    Colors,
    CrossAxisAlignment,
    Page,
    View,
    app,
)

from combine_code import combine_files

# サービス層をインポート
from services.db_setup import add_initial_data, init_db

# データベースの初期化とテストデータの追加（アプリケーション起動時に一度だけ行う）
init_db()  # テーブル作成
add_initial_data()  # 初期データ投入


# データベースのセットアップが完了した後で、DBに依存するコンポーネントをインポートする
from components.pages.case_hub import CaseHubView
from components.pages.client_register import ClientRegisterView
from components.pages.deceased_edit import DeceasedEditView
from components.pages.heir_edit import HeirEditView
from components.pages.home import CaseDashboardView


def main(page: Page):
    # アプリ起動時のブラウザ自動起動（warmup）は削除済み

    page.title = "顧客管理システム"
    page.bgcolor = Colors.AMBER_50
    page.horizontal_alignment = CrossAxisAlignment.CENTER

    page.window.width = 1400
    page.window.height = 850
    page.window.center()

    page.update()

    # ルーティングの処理
    def route_change(e):
        # --- 1. View スタックの安全性を確保 ---
        safe_views = [v for v in page.views if v is not None]
        page.views.clear()
        page.views.extend(safe_views)

        # --- 2. ルートマッチング開始 ---

        # --- 3. 案件ハブ（詳細画面とサイドバーサブ機能の統合） ---
        match_hub = re.match(r"^(/(detail|case)/(-?\d+))", e.route)

        if match_hub:
            case_id = int(match_hub.group(3))

            # 既存の CaseHubView インスタンスを取得するロジック
            hub_instance = None
            is_same_case = False

            # View スタックのトップを確認
            if page.views:
                top_view = page.views[-1]
                # カスタム属性として CaseHubView インスタンスが保持されているか確認
                if hasattr(top_view, "_hub_instance"):
                    hub_instance = top_view._hub_instance
                    # インスタンスの case_id がリクエストされた case_id と一致するか厳密にチェック
                    if hub_instance.case_id == case_id:
                        is_same_case = True

            if is_same_case:
                # 💡 同一案件内での遷移: 部分更新を行う
                print(f"Reuse Hub Instance for Case ID: {case_id} (Partial Update)")

                # route_to_content で self.main_content_column.update() を呼び出す
                hub_instance.route_to_content(e.route, update_ui=True)

                # Viewのルート情報も更新しておく
                page.views[-1].route = e.route

                # 💡 ここでは page.update() を呼ばないことで画面全体のちらつきを防ぐ

            else:
                # 💡 異なる案件、またはHub以外の画面からの遷移: 新しくViewを作成して全体描画
                print(f"Create New Hub Instance for Case ID: {case_id} (Full Update)")

                # 既存のスタックから、古いHubビューが残っていれば削除する（混在防止）
                # ホーム画面 ("/") は残す
                new_views = [v for v in page.views if v.route == "/"]

                # もしホームがなければ（ダイレクトアクセス等）、ホームを追加しておく
                if not new_views:
                    new_views.append(View(route="/", controls=[CaseDashboardView(page)]))

                page.views.clear()
                page.views.extend(new_views)

                # 新しいHubインスタンスを生成
                hub_instance = CaseHubView(page, case_id)

                # build() を実行し、Viewを取得
                hub_view = hub_instance.build()
                hub_view.route = e.route

                page.views.append(hub_view)

                # 💡 まだ画面に表示されていないので update_ui=False でコンテンツをセット
                hub_instance.route_to_content(e.route, update_ui=False)

                # 最後に全体を更新して表示
                page.update()

        # --- 4. 被相続人編集ページ (/deceased_edit/<id>) ---
        elif re.match(r"^/deceased_edit/(-?\d+)$", e.route):
            match = re.match(r"^/deceased_edit/(-?\d+)$", e.route)
            deceased_id = int(match.group(1))

            # 編集画面の View は、ハブ View の上に重ねる
            page.views.append(DeceasedEditView(page, deceased_id))
            page.update()

        # --- 5. 相続人編集ページ (/heir_edit/<id>?deceased_id=X) ---
        elif re.match(r"^/heir_edit/(\d+)(\?.*)?$", e.route):
            match = re.match(r"^/heir_edit/(\d+)(\?.*)?$", e.route)
            heir_id = int(match.group(1))

            query_params = {}
            if match.group(2):
                query_string = match.group(2).lstrip("?")
                query_params = dict(re.findall(r"([^?&=]+)=([^?&=]+)", query_string))

            deceased_id_from_url = int(query_params.get("deceased_id", 0))
            page.views.append(HeirEditView(page, heir_id, deceased_id_from_url))
            page.update()

        # --- 6. 新規相続人追加ページ (/heir_edit/new?deceased_id=X) ---
        elif re.match(r"^/heir_edit/new$", e.route) or e.route.startswith("/heir_edit/new?"):
            query_params = {}
            if "?" in e.route:
                query_string = e.route.split("?", 1)[1]
                query_params = dict(re.findall(r"([^?&=]+)=([^?&=]+)", query_string))

            deceased_id = int(query_params.get("deceased_id", 0))
            page.views.append(HeirEditView(page, 0, deceased_id))
            page.update()

        # --- 1. メイン画面 (ホーム) ---
        elif e.route == "/":
            # Viewスタックをクリアしてホームのみにする
            page.views.clear()
            page.views.append(View(route="/", controls=[CaseDashboardView(page)]))
            page.update()

        # --- 2. 新規案件登録 ---
        elif e.route == "/client_register":
            page.views.append(ClientRegisterView(page))
            page.update()

    def view_pop(view):
        page.views.pop()
        if page.views:
            top_view = page.views[-1]
            page.go(top_view.route)
        else:
            page.go("/")  # リストが空の場合はホームに戻る

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)


if __name__ == "__main__":
    app(target=main)
    combine_files()
