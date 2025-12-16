# src/views/touki_acquisition_view.py
import threading
from typing import Optional

from flet import (
    AlertDialog,
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
    ScrollMode
)

# サービス層のインポート
from src.services.real_estate_service import get_real_estates_by_case
from src.services.automation.touki_service import touki_service

class ToukiAcquisitionView(Column):
    """
    登記情報取得ツール画面
    DB登録済みの不動産または手動入力された情報に基づき、Seleniumを起動する。
    """
    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll=ScrollMode.AUTO, spacing=20)
        self.page = page
        self.case_id = case_id

        # --- 状態管理 ---
        self.input_mode = "db"  # "db" or "manual"
        self.target_type = "土地"  # "土地", "建物", "法人"

        # --- UIコンポーネント ---
        
        # 1. モード選択
        self.mode_radio = RadioGroup(
            content=Row([
                Radio(value="db", label="登録済み不動産から選択"),
                Radio(value="manual", label="手動入力"),
            ]),
            value="db",
            on_change=self._on_mode_change
        )

        # 2. 種別選択
        self.type_radio = RadioGroup(
            content=Row([
                Radio(value="土地", label="土地"),
                Radio(value="建物", label="建物"),
                Radio(value="法人", label="商業・法人"),
            ]),
            value="土地",
            on_change=self._on_type_change
        )

        # 3. DB選択用ドロップダウン
        self.asset_dropdown = Dropdown(
            label="取得対象の不動産を選択",
            width=600,
            options=[],
            on_change=self._on_asset_select,
            disabled=False
        )

        # 4. 手動入力フィールド
        self.address_field = TextField(
            label="所在・地番 (例: 東京都中央区銀座1丁目1-1)",
            width=600,
            read_only=True, # DBモード時は読み取り専用
            hint_text="都道府県 市区町村 地番・家屋番号を入力"
        )
        
        # 法人用フィールド (表示切替用)
        self.corp_name_field = TextField(
            label="会社・法人名 (例: 株式会社チェスター)",
            width=600,
            visible=False,
            hint_text="商号・名称を入力"
        )

        # 5. 実行ボタン
        self.execute_btn = ElevatedButton(
            text="登記情報を取得 (ブラウザ起動)",
            icon=Icons.SEARCH,
            style=ButtonStyle(
                bgcolor=Colors.INDIGO_600,
                color=Colors.WHITE,
                padding=20,
            ),
            on_click=self._on_execute_click
        )

        # --- レイアウト構築 ---
        self.controls = [
            Container(
                content=Column([
                    Row([
                        Icon(Icons.DOMAIN_VERIFICATION, size=30, color=Colors.INDIGO),
                        Text("登記情報取得ツール", size=24, weight=FontWeight.BOLD)
                    ]),
                    Text("自動操作ブラウザを起動し、登記情報提供サービスで検索を行います。", color="secondary"),
                ]),
                padding=padding.only(bottom=10)
            ),
            
            Card(
                content=Container(
                    padding=20,
                    content=Column([
                        Text("1. 入力方法を選択", weight=FontWeight.BOLD),
                        self.mode_radio,
                        Divider(),
                        
                        Text("2. 請求種別", weight=FontWeight.BOLD),
                        self.type_radio,
                        Divider(),

                        Text("3. 対象情報", weight=FontWeight.BOLD),
                        # DB選択エリア
                        self.asset_dropdown,
                        
                        # 手動/詳細入力エリア
                        self.corp_name_field,
                        self.address_field,
                        
                        Container(height=20),
                        
                        Row([
                            self.execute_btn
                        ], alignment="end")
                    ])
                )
            )
        ]

    def did_mount(self):
        """画面表示時のデータロード"""
        self._load_assets()

    def _load_assets(self):
        """DBから不動産リストを取得"""
        try:
            assets = get_real_estates_by_case(self.case_id)
            options = []
            for asset in assets:
                # ドロップダウンの表示名を作成
                label = f"【{asset.property_type}】 {asset.location} ({asset.lot_number or asset.house_number})"
                # 所在と地番を結合したものを値として保持 (簡易実装)
                # 実際にはIDを持たせて検索し直す方が堅牢だが、ここではlocation + lot_numberを値とする
                full_address = f"{asset.location} {asset.lot_number or asset.house_number}".strip()
                
                options.append(dropdown.Option(
                    key=full_address, # キーに住所情報を持たせる
                    text=label,
                    data={"type": asset.property_type} # 追加データ
                ))
            
            if not options:
                options.append(dropdown.Option("none", "登録された不動産がありません"))
                self.asset_dropdown.disabled = True
            
            self.asset_dropdown.options = options
            self.update()
            
        except Exception as e:
            self.page.open(SnackBar(Text(f"データ読込エラー: {e}"), bgcolor=Colors.RED))

    def _on_mode_change(self, e):
        """入力モード切替時のUI制御"""
        mode = self.mode_radio.value
        self.input_mode = mode
        
        # モード切替時は入力欄をリセット
        self.address_field.value = ""
        self.corp_name_field.value = ""
        
        if mode == "db":
            self.asset_dropdown.disabled = False
            self.address_field.read_only = True
            self.asset_dropdown.value = None
        else:
            self.asset_dropdown.disabled = True
            self.asset_dropdown.value = None
            self.address_field.read_only = False
            # 法人モードかつ手動入力の場合は書き込み可能にする
            if self.target_type == "法人":
                self.address_field.read_only = False
            
        self.update()

    def _on_type_change(self, e):
        """
        種別変更時のUI制御
        法人選択時はフィールド構成を変更し、フォーカスを当てる
        """
        type_val = self.type_radio.value
        self.target_type = type_val
        
        if type_val == "法人":
            self.corp_name_field.visible = True
            self.asset_dropdown.visible = False # 法人はDBの不動産からは選べない前提
            self.mode_radio.value = "manual"
            self.mode_radio.disabled = True
            
            # ラベル変更
            self.address_field.label = "本店所在地 (都道府県の識別に必要)"
            self.address_field.read_only = False
            
            # UI更新後にフォーカスを当てる
            self.update()
            self.corp_name_field.focus()
            
        else:
            self.corp_name_field.visible = False
            self.asset_dropdown.visible = True
            self.mode_radio.disabled = False
            self.address_field.label = "所在・地番 (例: 東京都中央区銀座1丁目1-1)"
            
            # モードに応じたReadOnly復帰
            if self.mode_radio.value == "db":
                self.address_field.read_only = True
            else:
                self.address_field.read_only = False
            
            self.update()

    def _on_asset_select(self, e):
        """ドロップダウン選択時に住所フィールドへ転記"""
        val = self.asset_dropdown.value
        if val and val != "none":
            self.address_field.value = val
            self.update()

    def _on_execute_click(self, e):
        """実行ボタンハンドラ"""
        address = self.address_field.value
        corp_name = self.corp_name_field.value
        
        if self.target_type == "法人":
            if not corp_name:
                self.page.open(SnackBar(Text("会社・法人名を入力してください"), bgcolor=Colors.RED))
                self.corp_name_field.focus()
                return
            if not address:
                self.page.open(SnackBar(Text("本店所在地を入力してください（都道府県特定のため）"), bgcolor=Colors.RED))
                self.address_field.focus()
                return
        else:
            if not address:
                self.page.open(SnackBar(Text("住所・地番が入力されていません"), bgcolor=Colors.RED))
                return

        # ボタンをローディング状態に
        self.execute_btn.content = Row([
            Icon(Icons.HOURGLASS_BOTTOM, color=Colors.WHITE),
            Text("処理中...", color=Colors.WHITE)
        ], alignment="center")
        self.execute_btn.disabled = True
        self.update()

        # 別スレッドで実行
        threading.Thread(
            target=self._run_automation_task,
            args=(address, self.target_type, corp_name),
            daemon=True
        ).start()

    def _run_automation_task(self, address, target_type, corp_name):
        """バックグラウンド実行タスク"""
        try:
            msg = ""
            if target_type == "法人":
                msg = touki_service.request_commercial(corp_name, address)
            else:
                msg = touki_service.request_real_estate(address, target_type)
            
            self.page.open(SnackBar(Text(msg), bgcolor=Colors.GREEN))
            
        except Exception as e:
            self.page.open(SnackBar(Text(f"エラー: {e}"), bgcolor=Colors.RED))
            
        finally:
            # ボタン復帰
            self.execute_btn.content = Row([
                Icon(Icons.SEARCH, color=Colors.WHITE),
                Text("登記情報を取得 (ブラウザ起動)", color=Colors.WHITE)
            ], alignment="center")
            self.execute_btn.disabled = False
            self.page.update()