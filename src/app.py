# src/app.py
import re
import sys
from pathlib import Path
from typing import List, Optional

# パス解決: プロジェクトルートをsys.pathに追加してインポートエラーを防ぐ
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from flet import Colors, Page, RouteChangeEvent, SnackBar, Text, View

# 💡 修正: 設定ファイルのインポート
from src.config import APP_THEME, DEFAULT_THEME_MODE
from src.views.case_hub import CaseHubView
from src.views.editors import DeceasedEditView, HeirEditView
from src.views.home import CaseDashboardView
from src.views.pdf_tool import PdfToolView
from src.views.register import ClientRegisterView


def main(page: Page) -> None:
    """
    アプリケーションのメインロジック (ルート処理のホスト)
    """
    page.title = "遺産整理・相続業務システム"
    page.padding = 0

    # 💡 テーマ設定の集約: configから読み込み、常にダークモードを適用
    page.theme_mode = DEFAULT_THEME_MODE
    page.theme = APP_THEME

    # page.update() # main.pyからapp_main(page)が呼ばれるため、ここでは不要

    # エラーハンドリング用ラッパー
    def handle_error(e: Exception) -> None:
        """エラー発生時にSnackBarで通知する"""
        print(f"Global Error: {e}")
        page.open(
            SnackBar(
                content=Text(f"エラーが発生しました: {str(e)}", color=Colors.WHITE),
                bgcolor=Colors.RED,
            )
        )
        page.update()

    # --- DB初期化処理 ---
    from src.models.database import init_db

    init_db()  # アプリ起動時にテーブルがない場合は作成する

    # =========================================================================
    # ルーティング処理 (page.on_route_change)
    # =========================================================================
    def route_change(e: RouteChangeEvent) -> None:
        print(f"Route changing to: {e.route}")

        # --- 1. View スタックの安全性を確保 ---
        safe_views: List[View] = [v for v in page.views if v is not None]
        page.views.clear()
        page.views.extend(safe_views)

        # --- 2. ルートマッチング開始 ---

        # 💡 PDFツールへのルーティング
        if e.route == "/pdf_tool":
            page.views.append(View(route="/pdf_tool", controls=[PdfToolView(page)], appbar=None))
            page.update()

        # --- 3. 案件ハブ ---
        elif re.match(r"^(/(detail|case)/(-?\d+))", e.route):
            match_hub = re.match(r"^(/(detail|case)/(-?\d+))", e.route)
            if match_hub:
                case_id = int(match_hub.group(3))

                # 既存インスタンス再利用ロジック
                hub_instance: Optional[CaseHubView] = None
                is_same_case = False
                if page.views:
                    top_view = page.views[-1]
                    if hasattr(top_view, "_hub_instance"):
                        hub_instance = top_view._hub_instance
                        if hub_instance.case_id == case_id:
                            is_same_case = True

                if is_same_case and hub_instance:
                    hub_instance.route_to_content(e.route, update_ui=True)
                    page.views[-1].route = e.route
                else:
                    # ホーム画面を残してスタッククリア
                    new_views = [v for v in page.views if v.route == "/"]
                    if not new_views:
                        new_views.append(View(route="/", controls=[CaseDashboardView(page)]))

                    page.views.clear()
                    page.views.extend(new_views)

                    hub_instance = CaseHubView(page, case_id)
                    hub_view = View(
                        route=e.route,
                        controls=[hub_instance],
                        padding=0,
                        appbar=None,
                    )
                    setattr(hub_view, "_hub_instance", hub_instance)
                    page.views.append(hub_view)
                    hub_instance.route_to_content(e.route, update_ui=False)
                    page.update()

        # --- 4. 被相続人編集ページ ---
        elif re.match(r"^/deceased_edit/(-?\d+)$", e.route):
            match = re.match(r"^/deceased_edit/(-?\d+)$", e.route)
            deceased_id = int(match.group(1))
            page.views.append(DeceasedEditView(page, deceased_id))
            page.update()

        # --- 5. 相続人編集ページ ---
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

        # --- 6. 新規相続人追加ページ ---
        elif re.match(r"^/heir_edit/new$", e.route) or e.route.startswith("/heir_edit/new?"):
            query_params = {}
            if "?" in e.route:
                query_string = e.route.split("?", 1)[1]
                query_params = dict(re.findall(r"([^?&=]+)=([^?&=]+)", query_string))
            deceased_id = int(query_params.get("deceased_id", 0))
            page.views.append(HeirEditView(page, 0, deceased_id))
            page.update()

        # --- 7. メイン画面 (ホーム) ---
        elif e.route == "/":
            page.views.clear()
            page.views.append(View(route="/", controls=[CaseDashboardView(page)]))
            page.update()

        # --- 8. 新規案件登録 ---
        elif e.route == "/client_register":
            page.views.append(ClientRegisterView(page))
            page.update()

        # --- 9. 不明なルート ---
        else:
            print(f"Unknown route: {e.route}")
            if e.route != "/pdf_tool":  # PDFツール以外の場合のみエラー
                page.open(
                    SnackBar(
                        content=Text(f"不明なルートです: {e.route}", color=Colors.WHITE),
                        bgcolor=Colors.RED,
                    )
                )
            if len(page.views) == 0:
                page.go("/")

    # =========================================================================
    # イベントハンドラ設定と初期起動
    # =========================================================================
    page.on_route_change = route_change
    page.on_view_pop = lambda e: (
        page.views.pop(),
        page.go(page.views[-1].route) if page.views else None,
    )

    try:
        page.go(page.route)
    except Exception as e:
        handle_error(e)


if __name__ == "__main__":
    from flet import app

    app(target=main)
