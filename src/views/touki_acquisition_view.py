# src/views/touki_acquisition_view.py
import threading
from typing import Optional, List, Dict

from flet import (
    ButtonStyle,
    Card,
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FontWeight,
    Icon,
    Icons,
    Page,
    Radio,
    RadioGroup,
    Row,
    SnackBar,
    Text,
    TextField,
    dropdown,
    padding,
    ScrollMode,
    MainAxisAlignment,
    CrossAxisAlignment,
    ControlEvent,
)

# サービス層のインポート
from src.services.real_estate_service import get_real_estates_by_case
from src.services.automation.touki_service import touki_service

class ToukiAcquisitionView(Column):
    """
    登記情報取得ツール画面
    DB登録済みの不動産選択に応じて種別（土地・建物）を自動判別し、手動選択を不要にします。
    """
    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll=ScrollMode.AUTO, spacing=20)
        self.page = page
        self.case_id = case_id

        # --- 状態管理 ---
        self.input_mode = "db"  # "db" (DBから選択) or "manual" (手動入力)
        self.category_mode = "real_estate" # "real_estate" (土地・建物) or "commercial" (商業・法人)
        self.target_type = "土地" # 自動判別された種別を保持する内部変数

        # --- UIコンポーネント ---
        
        # 1. 請求カテゴリ選択
        self.category_radio = RadioGroup(
            content=Row([
                Radio(value="real_estate", label="土地・建物"),
                Radio(value="commercial", label="商業・法人"),
            ]),
            value="real_estate",
            on_change=self._on_category_change
        )

        # 2. 入力方法選択
        self.mode_radio = RadioGroup(
            content=Row([
                Radio(value="db", label="登録済み不動産から選択"),
                Radio(value="manual", label="手動入力"),
            ]),
            value="db",
            on_change=self._on_mode_change
        )

        # 3. DB選択用ドロップダウン
        self.asset_dropdown = Dropdown(
            label="取得対象の不動産を選択",
            width=600,
            options=[],
            on_change=self._on_asset_select,
        )

        # 4. 住所・法人名入力フィールド
        self.address_field = TextField(
            label="所在・地番 (例: 東京都中央区銀座1丁目1-1)",
            width=600,
            read_only=True,
            hint_text="都道府県 市区町村 地番・家屋番号を入力",
            color="onSurface",
        )
        
        self.corp_name_field = TextField(
            label="会社・法人名 (例: 株式会社チェスター)",
            width=600,
            visible=False,
            hint_text="商号・名称を正確に入力してください",
            color="onSurface",
        )

        # 5. 実行ボタン
        self.execute_btn = ElevatedButton(
            text="登記情報を取得 (ブラウザ起動)",
            icon=Icons.SEARCH,
            style=ButtonStyle(
                bgcolor="primary",
                color="onPrimary",
                padding=20,
            ),
            on_click=self._on_execute_click
        )

        # 6. オプション表示エリア (種別選択ラジオを削除)
        self.real_estate_options_area = Column([
            Text("2. 入力方法を選択", weight=FontWeight.BOLD, color="onSurface"),
            self.mode_radio,
            Divider(),
        ], visible=True)

        # --- レイアウト構築 ---
        self.controls = [
            Container(
                content=Column([
                    Row([
                        Icon(Icons.DOMAIN_VERIFICATION, size=30, color="primary"),
                        Text("登記情報取得ツール", size=24, weight=FontWeight.BOLD, color="onSurface")
                    ]),
                    Text("自動操作ブラウザを起動し、登記情報提供サービスで検索を行います。", color="secondary"),
                ]),
                padding=padding.only(bottom=10)
            ),
            
            Card(
                content=Container(
                    padding=20,
                    content=Column([
                        Text("1. 請求カテゴリを選択", weight=FontWeight.BOLD, color="onSurface"),
                        self.category_radio,
                        Divider(),

                        # 不動産専用オプション
                        self.real_estate_options_area,

                        Text("対象情報入力", weight=FontWeight.BOLD, color="onSurface"),
                        self.asset_dropdown,
                        self.corp_name_field,
                        self.address_field,
                        
                        Container(height=20),
                        
                        Row([
                            self.execute_btn
                        ], alignment=MainAxisAlignment.END)
                    ], spacing=10)
                )
            )
        ]

    def did_mount(self) -> None:
        """画面マウント時にデータをロード"""
        self._load_assets()

    def _load_assets(self) -> None:
        """DBから不動産を取得し、日本語ラベルと判別用データを付与してドロップダウンを生成"""
        try:
            assets = get_real_estates_by_case(self.case_id)
            options = []
            
            # DBの内部コードを画面表示用の日本語にマッピング
            type_display_map = {"Land": "土地", "Building": "建物", "Condo": "区分所有"}
            
            for asset in assets:
                # ブラウザ自動操作へ渡すための正規化種別 (土地 or 建物)
                normalized_type = "建物" if asset.property_type in ["Building", "Condo"] else "土地"
                
                # ドロップダウン表示用テキスト
                display_type = type_display_map.get(asset.property_type, "不明")
                label = f"【{display_type}】 {asset.location} ({asset.lot_number or asset.house_number})"
                
                # 値には検索用の住所（所在 + 地番）を使用
                search_addr = f"{asset.location} {asset.lot_number or asset.house_number}".strip()
                
                options.append(dropdown.Option(
                    key=search_addr,
                    text=label,
                    # data属性に種別を隠し持たせることで自動判別を可能にする
                    data={"normalized_type": normalized_type}
                ))
            
            if not options:
                options.append(dropdown.Option("none", "登録された不動産がありません"))
                self.asset_dropdown.disabled = True
            else:
                self.asset_dropdown.disabled = False
            
            self.asset_dropdown.options = options
            self.update()
            
        except Exception as e:
            self._show_error(f"データ読込エラー: {e}")

    def _on_category_change(self, e: ControlEvent) -> None:
        """カテゴリ（土地建物/商業法人）変更時の表示制御"""
        self.category_mode = self.category_radio.value
        
        if self.category_mode == "commercial":
            self.real_estate_options_area.visible = False
            self.asset_dropdown.visible = False
            self.corp_name_field.visible = True
            self.address_field.label = "本店所在地 (都道府県の識別に必要)"
            self.address_field.read_only = False
            self.address_field.value = ""
        else:
            self.real_estate_options_area.visible = True
            self.asset_dropdown.visible = (self.input_mode == "db")
            self.corp_name_field.visible = False
            self.address_field.label = "所在・地番 (例: 東京都中央区銀座1丁目1-1)"
            self.address_field.read_only = (self.input_mode == "db")
            self.address_field.value = ""

        self.update()

    def _on_mode_change(self, e: ControlEvent) -> None:
        """入力モード（DB選択/手動入力）変更時の表示制御"""
        self.input_mode = self.mode_radio.value
        self.address_field.value = ""
        
        if self.input_mode == "db":
            self.asset_dropdown.visible = True
            self.address_field.read_only = True
        else:
            self.asset_dropdown.visible = False
            self.address_field.read_only = False
            # 手動入力時は暫定的に土地とする
            self.target_type = "土地"
            
        self.update()

    def _on_asset_select(self, e: ControlEvent) -> None:
        """【重要】ドロップダウン選択時に住所と種別を自動的に連動させる"""
        # 現在選択されたOptionオブジェクトを特定
        selected_option = next((opt for opt in self.asset_dropdown.options if opt.key == self.asset_dropdown.value), None)
        
        if selected_option and selected_option.key != "none":
            # 1. 住所フィールドに値を反映
            self.address_field.value = selected_option.key
            
            # 2. data属性から種別を読み取り、内部変数を自動更新
            if selected_option.data:
                detected_type = selected_option.data.get("normalized_type")
                if detected_type:
                    self.target_type = detected_type
            
            self.update()

    def _on_execute_click(self, e: ControlEvent) -> None:
        """実行ボタン処理"""
        address = self.address_field.value.strip() if self.address_field.value else ""
        corp_name = self.corp_name_field.value.strip() if self.corp_name_field.value else ""
        
        # バリデーション
        if self.category_mode == "commercial":
            if not corp_name:
                self._show_error("会社・法人名を入力してください")
                return
            if not address:
                self._show_error("所在地を入力してください")
                return
        else:
            if not address:
                self._show_error("対象が指定されていません")
                return

        # ボタンをローディング状態（視覚的フィードバック）にする
        # ※ 以前動かなかった箇所を修正
        self.page.open(SnackBar(Text('ブラウザを起動します。しばらくお待ちください...'), bgcolor=Colors.BLUE_700))
        self.execute_btn.disabled = True
        self.update()

        # 別スレッドでSeleniumタスクを実行
        threading.Thread(
            target=self._run_automation_task,
            args=(address, self.target_type, corp_name),
            daemon=True
        ).start()

    def _run_automation_task(self, address: str, target_type: str, corp_name: str) -> None:
        """バックグラウンドで実行される自動化タスク"""
        try:
            if self.category_mode == "commercial":
                msg = touki_service.request_commercial(corp_name, address)
            else:
                # target_type はドロップダウン連動により最新の「土地」or「建物」が自動セットされている
                msg = touki_service.request_real_estate(address, target_type)
            
            self.page.open(SnackBar(Text(msg), bgcolor=Colors.GREEN))
            
        except Exception as ex:
            self._show_error(str(ex))
            
        finally:
            # UIの復帰
            self.execute_btn.disabled = False
            self.update()

    def _show_error(self, message: str) -> None:
        """エラー通知用SnackBarを表示"""
        self.page.open(SnackBar(Text(message), bgcolor=Colors.RED))
        self.page.update()