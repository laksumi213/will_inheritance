# src/app.py
import re
import sys
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

# パス解決: プロジェクトルートをsys.pathに追加してインポートエラーを防ぐ
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent))

from flet import (
    AppBar,
    Colors,
    IconButton,
    Icons,
    Page,
    RouteChangeEvent,
    SnackBar,
    Text,
    View,
)

# 設定ファイルのインポート
from src.config import APP_THEME, DEFAULT_THEME_MODE

# Viewのインポート
from src.views.case_hub import CaseHubView
from src.views.home import CaseDashboardView
from src.views.register import ClientRegisterView
from src.services.deceased_service import get_case_id_by_deceased_id

# 編集画面 (個別ファイルからのインポートを維持)
from src.views.deceased_edit import DeceasedEditView
from src.views.heir_edit import HeirEditView

# 💡 変更点: 旧ツール(pdf_tool)を廃止し、高機能版(coordinate_view)を採用
from src.views.coordinate_view import CoordinateSelectorView


def main(page: Page) -> None:
    """
    アプリケーションのメインロジック (ルート処理のホスト)
    """
    page.title = "遺産整理・相続業務システム"
    page.padding = 0

    # テーマ設定
    page.theme_mode = DEFAULT_THEME_MODE
    page.theme = APP_THEME

    # エラーハンドリング用ラッパー
    def handle_error(e: Exception) -> None:
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
    init_db()

    # -------------------------------------------------------------------------
    # 画面スタック構築ヘルパー (Uploaded版のロジックを採用)
    # -------------------------------------------------------------------------
    def _ensure_base_stack(case_id: int = None):
        """
        現在のViewスタックを確認し、ホーム画面と(必要なら)詳細画面を
        底に敷くように再構築する。
        これにより、編集画面でリロードしても「戻る」ボタンが機能する。
        """
        # 1. ホーム画面が先頭になければクリアして追加
        if not page.views or page.views[0].route != "/":
            page.views.clear()
            page.views.append(View(route="/", controls=[CaseDashboardView(page)]))

        # 2. case_id が指定されている場合、詳細画面(Hub)がスタックにあるか確認
        if case_id:
            detail_route = f"/detail/{case_id}"
            # 詳細画面がまだスタックにない場合のみ追加
            has_detail = any(v.route.startswith(f"/detail/{case_id}") or v.route.startswith(f"/case/{case_id}") for v in page.views)
            
            if not has_detail:
                print(f"DEBUG: Rebuilding stack - Adding CaseHubView for case_id={case_id}")
                
                # CaseHubViewを作成
                hub_instance = CaseHubView(page, case_id)
                
                # Viewを作成
                hub_view = View(
                    route=detail_route,
                    controls=[hub_instance],
                    padding=0,
                )
                # AppBarを設定
                client_name = getattr(hub_instance, "client_name", "")
                hub_view.appbar = AppBar(
                    title=Text(f"{client_name}の詳細画面 (ID:{case_id})"),
                    bgcolor=Colors.BLUE_GREY_700,
                    leading=IconButton(
                        Icons.ARROW_BACK, 
                        on_click=lambda e: page.go("/"),
                        tooltip="ホームに戻る"
                    ),
                )
                # インスタンス紐付け
                setattr(hub_view, "_hub_instance", hub_instance)
                
                # コンテンツ初期化
                hub_instance.route_to_content(detail_route, update_ui=False)
                
                page.views.append(hub_view)


    # =========================================================================
    # ルーティング処理 (page.on_route_change)
    # =========================================================================
    def route_change(e: RouteChangeEvent) -> None:
        print(f"Route changing to: {e.route}")

        # --- 1. View スタックのクリーニング ---
        # 無効なViewを取り除く
        page.views[:] = [v for v in page.views if v is not None]

        # --- 2. ルートマッチング ---

        # 💡 変更点: PDF座標取得ツール
        if e.route == "/pdf_tool":
            _ensure_base_stack() # ホームを下に敷く
            page.views.append(
                View(
                    route="/pdf_tool", 
                    controls=[CoordinateSelectorView(page)],
                    appbar=AppBar(
                        title=Text("PDF座標取得・編集ツール"),
                        bgcolor=Colors.BLUE_GREY_800,
                        leading=IconButton(Icons.ARROW_BACK, on_click=lambda _: page.go("/")),
                    )
                )
            )
            page.update()

        # --- 案件ハブ (詳細画面・サブ機能) ---
        elif re.match(r"^(/(detail|case)/(-?\d+))", e.route):
            match_hub = re.match(r"^(/(detail|case)/(-?\d+))", e.route)
            if match_hub:
                case_id = int(match_hub.group(3))

                # ホーム画面を確保
                if not page.views or page.views[0].route != "/":
                    page.views.clear()
                    page.views.append(View(route="/", controls=[CaseDashboardView(page)]))

                # 既存のHubインスタンスを探す (再利用ロジック)
                hub_instance: Optional[CaseHubView] = None
                target_view: Optional[View] = None
                
                for view in page.views:
                    if hasattr(view, "_hub_instance"):
                        instance = getattr(view, "_hub_instance")
                        if isinstance(instance, CaseHubView) and instance.case_id == case_id:
                            hub_instance = instance
                            target_view = view
                            break
                
                if hub_instance and target_view:
                    # 【再利用】不要な上層Viewを削除してHubを表示
                    while page.views[-1] != target_view:
                        page.views.pop()
                    
                    target_view.route = e.route
                    hub_instance.route_to_content(e.route, update_ui=True)
                    
                else:
                    # 【新規作成】
                    hub_instance = CaseHubView(page, case_id)
                    new_view = View(route=e.route, controls=[hub_instance], padding=0)
                    setattr(new_view, "_hub_instance", hub_instance)
                    
                    # AppBar設定
                    client_name = getattr(hub_instance, "client_name", "")
                    new_view.appbar = AppBar(
                        title=Text(f"{client_name}の詳細画面 (ID:{case_id})"),
                        bgcolor=Colors.BLUE_GREY_700,
                        leading=IconButton(Icons.ARROW_BACK, on_click=lambda e: page.go("/")),
                    )
                    
                    hub_instance.route_to_content(e.route, update_ui=False)
                    page.views.append(new_view)

                page.update()

        # --- 被相続人編集ページ ---
        elif re.match(r"^/deceased_edit/(-?\d+)(\?.*)?$", e.route):
            match = re.match(r"^/deceased_edit/(-?\d+)(\?.*)?$", e.route)
            deceased_id = int(match.group(1))

            # クエリパラメータから case_id 取得
            parsed_url = urlparse(e.route)
            query_params = parse_qs(parsed_url.query)
            case_id_list = query_params.get("case_id", [])
            case_id = int(case_id_list[0]) if case_id_list else 0
            
            # case_id が URL にない場合のフォールバック
            if case_id == 0 and deceased_id > 0:
                case_id = get_case_id_by_deceased_id(deceased_id) or 0

            # 詳細画面をスタックの下に敷く (戻るボタン対策)
            _ensure_base_stack(case_id)

            # 編集画面を追加
            page.views.append(DeceasedEditView(page, deceased_id, case_id))
            page.update()

        # --- 相続人編集ページ ---
        elif re.match(r"^/heir_edit/(\d+)(\?.*)?$", e.route):
            match = re.match(r"^/heir_edit/(\d+)(\?.*)?$", e.route)
            heir_id = int(match.group(1))
            
            parsed_url = urlparse(e.route)
            query_params = parse_qs(parsed_url.query)
            
            deceased_id_list = query_params.get("deceased_id", [])
            deceased_id = int(deceased_id_list[0]) if deceased_id_list else 0
            
            case_id_list = query_params.get("case_id", [])
            case_id = int(case_id_list[0]) if case_id_list else 0
            
            if case_id == 0 and deceased_id > 0:
                 case_id = get_case_id_by_deceased_id(deceased_id) or 0

            _ensure_base_stack(case_id)

            page.views.append(HeirEditView(page, heir_id, deceased_id, case_id))
            page.update()

        # --- 新規相続人追加ページ ---
        elif re.match(r"^/heir_edit/new(\?.*)?$", e.route):
            parsed_url = urlparse(e.route)
            query_params = parse_qs(parsed_url.query)
            
            deceased_id_list = query_params.get("deceased_id", [])
            deceased_id = int(deceased_id_list[0]) if deceased_id_list else 0
            
            case_id_list = query_params.get("case_id", [])
            case_id = int(case_id_list[0]) if case_id_list else 0
            
            if case_id == 0 and deceased_id > 0:
                 case_id = get_case_id_by_deceased_id(deceased_id) or 0

            _ensure_base_stack(case_id)

            page.views.append(HeirEditView(page, 0, deceased_id, case_id))
            page.update()

        # --- メイン画面 (ホーム) ---
        elif e.route == "/":
            page.views.clear()
            page.views.append(View(route="/", controls=[CaseDashboardView(page)]))
            page.update()

        # --- 新規案件登録 ---
        elif e.route == "/client_register":
            _ensure_base_stack()
            page.views.append(ClientRegisterView(page))
            page.update()

        # --- 不明なルート ---
        else:
            print(f"Unknown route: {e.route}")
            _ensure_base_stack()
            page.open(
                SnackBar(
                    content=Text(f"不明なルートです: {e.route}", color=Colors.WHITE),
                    bgcolor=Colors.RED,
                )
            )
            page.update()

    # =========================================================================
    # イベントハンドラ設定と初期起動
    # =========================================================================
    page.on_route_change = route_change
    
    def view_pop(e):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_view_pop = view_pop

    try:
        page.go(page.route)
    except Exception as e:
        handle_error(e)


if __name__ == "__main__":
    from flet import app
    app(target=main)