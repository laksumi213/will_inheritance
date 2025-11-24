# main.py

import re

from flet import (
    Colors,
    CrossAxisAlignment,
    Page,
    View,
    app,
)

# サービス層をインポート (動作確認のためのダミー)
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
    page.title = "顧客管理システム"
    page.bgcolor = Colors.AMBER_50
    page.horizontal_alignment = CrossAxisAlignment.CENTER

    page.window.width = 1400
    page.window.height = 850
    page.window.center()

    page.update()

    # ルーティングの処理
    def route_change(e):
        # View スタックの安全性を確保 (今回はこのロジックを維持)
        safe_views = [v for v in page.views if v is not None]
        page.views.clear()
        page.views.extend(safe_views)

        # 既存のビューをクリアする前に、現在のビューがハブ関連かどうかをチェックし、
        # ハブ関連であれば、ビューをスタックに残す

        # 2. ルートマッチング開始

        # --- 3. 案件ハブ（詳細画面とサイドバーサブ機能の統合） ---
        match_hub = re.match(r"^(/(detail|case)/(-?\d+))", e.route)

        if match_hub:
            case_id = int(match_hub.group(3))

            # 💡 [重要修正] 既存の CaseHubView インスタンスを取得するロジック
            hub_instance = None

            # View スタックのトップがハブ View かつ同一案件IDかチェック
            is_hub_on_top = (
                page.views
                and page.views[-1].route
                and (
                    page.views[-1].route.startswith(f"/case/{case_id}/")
                    or page.views[-1].route.startswith(f"/detail/{case_id}")
                )
                # 既存の View に、カスタム属性として CaseHubView インスタンスが保持されているか確認
                and hasattr(page.views[-1], "_hub_instance")
            )

            if is_hub_on_top:
                # View スタック操作はスキップし、内部コンテンツの更新のみ行う
                # 💡 修正: 既存のインスタンスを取得して route_to_content を呼び出す
                hub_instance = page.views[-1]._hub_instance
                hub_instance.route_to_content(e.route)

            else:
                # View スタックのトップにハブ View がない場合、スタックをクリアして View を追加する

                # 💡 修正: CaseHubView インスタンスを生成し、その build() を実行
                hub_instance = CaseHubView(page, case_id)
                hub_view = hub_instance.build()

                # page.views.clear() は行わない (上部で実行済み)
                page.views.append(hub_view)

                # 内部コンテンツを切り替える (build() 時に初期化済みだが、念のためルートと同期させる)
                hub_instance.route_to_content(e.route)

        # --- 4. 被相続人編集ページ (/deceased_edit/<id>) ---
        elif re.match(r"^/deceased_edit/(-?\d+)$", e.route):
            match = re.match(r"^/deceased_edit/(-?\d+)$", e.route)
            deceased_id = int(match.group(1))

            # 🚨 編集画面の View は、ハブ View の上に重ねる
            page.views.append(DeceasedEditView(page, deceased_id))

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

        # --- 6. 新規相続人追加ページ (/heir_edit/new?deceased_id=X) ---
        elif re.match(r"^/heir_edit/new$", e.route) or e.route.startswith("/heir_edit/new?"):
            query_params = {}
            if "?" in e.route:
                query_string = e.route.split("?", 1)[1]
                query_params = dict(re.findall(r"([^?&=]+)=([^?&=]+)", query_string))

            deceased_id = int(query_params.get("deceased_id", 0))
            page.views.append(HeirEditView(page, 0, deceased_id))

        # --- 1. メイン画面 (被相続人一覧) ---
        elif e.route == "/":
            # 🚨 修正: 他の画面がなかった場合にのみホームを追加
            # 💡 修正: Viewスタックの安全策で View がクリアされているため、常に再追加が必要
            if not page.views or page.views[-1].route != "/":
                page.views.append(View(route="/", controls=[CaseDashboardView(page)]))

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
