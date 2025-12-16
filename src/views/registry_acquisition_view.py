# src/views/registry_acquisition_view.py
from flet import (
    Colors,
    Column,
    Container,
    Divider,
    Dropdown,
    ElevatedButton,
    FontWeight,
    Icons,
    Page,
    Radio,
    RadioGroup,
    Row,
    SnackBar,
    Tab,
    Tabs,
    Text,
    TextField,
    dropdown,
    padding,
    alignment,
)

from src.services.automation.registry_automation_service import registry_service
from src.services.real_estate_service import get_real_estates_by_case

class RegistryAcquisitionView(Column):
    """
    登記情報取得画面
    """

    def __init__(self, page: Page, case_id: int):
        super().__init__(expand=True, scroll="auto")
        self.page = page
        self.case_id = case_id

        # --- Tab 1: 登録済み不動産から選択 ---
        self.asset_dropdown = Dropdown(
            label="登録済み不動産を選択",
            width=400,
            options=[],
            on_change=self._on_asset_selected
        )
        self.tab1_address_field = TextField(label="所在 (自動入力)", read_only=True, width=400)
        self.tab1_type_group = RadioGroup(
            content=Row([
                Radio(value="土地", label="土地"),
                Radio(value="建物", label="建物"),
            ]),
            value="土地"
        )

        tab1_content = Container(
            content=Column([
                Text("案件に登録されている不動産情報から取得します。", size=14, color="grey"),
                self.asset_dropdown,
                self.tab1_address_field,
                Text("種別:", weight=FontWeight.BOLD),
                self.tab1_type_group,
                ElevatedButton(
                    "登記情報を取得する",
                    icon=Icons.DOWNLOAD,
                    bgcolor=Colors.BLUE_600,
                    color=Colors.WHITE,
                    on_click=self._on_acquire_registered
                )
            ], spacing=20),
            padding=20
        )

        # --- Tab 2: 手動入力 ---
        self.manual_address_field = TextField(label="住所・地番 (例: 東京都千代田区1-1-1)", width=400)
        self.manual_type_group = RadioGroup(
            content=Row([
                Radio(value="土地", label="土地"),
                Radio(value="建物", label="建物"),
            ]),
            value="土地"
        )

        tab2_content = Container(
            content=Column([
                Text("未登録の不動産情報を手動で入力して取得します。", size=14, color="grey"),
                self.manual_address_field,
                Text("種別:", weight=FontWeight.BOLD),
                self.manual_type_group,
                ElevatedButton(
                    "登記情報を取得する",
                    icon=Icons.DOWNLOAD,
                    bgcolor=Colors.GREEN_600,
                    color=Colors.WHITE,
                    on_click=self._on_acquire_manual
                )
            ], spacing=20),
            padding=20
        )

        # --- Tab 3: 商業・法人 ---
        self.corp_name_field = TextField(label="会社・法人名", width=400)
        self.corp_pref_field = TextField(label="本店所在地 (都道府県)", width=200, value="東京都")

        tab3_content = Container(
            content=Column([
                Text("商業・法人登記情報を取得します。", size=14, color="grey"),
                self.corp_name_field,
                self.corp_pref_field,
                ElevatedButton(
                    "登記情報を取得する",
                    icon=Icons.BUSINESS,
                    bgcolor=Colors.ORANGE_600,
                    color=Colors.WHITE,
                    on_click=self._on_acquire_corp
                )
            ], spacing=20),
            padding=20
        )

        # --- Tabs ---
        self.tabs = Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                Tab(text="登録済不動産", content=tab1_content, icon=Icons.HOME),
                Tab(text="手動入力", content=tab2_content, icon=Icons.EDIT),
                Tab(text="商業・法人", content=tab3_content, icon=Icons.BUSINESS_CENTER),
            ],
            expand=True,
        )

        self.controls = [
            Text("📑 登記情報取得ツール", size=24, weight=FontWeight.BOLD),
            Divider(),
            self.tabs
        ]

    def did_mount(self):
        self._load_assets()

    def _load_assets(self):
        """DBから不動産リストを読み込む"""
        assets = get_real_estates_by_case(self.case_id)
        options = []
        # データ保持用
        self.assets_map = {}
        
        for a in assets:
            label = f"{a.property_type}: {a.location}"
            options.append(dropdown.Option(str(a.id), label))
            self.assets_map[str(a.id)] = a

        self.asset_dropdown.options = options
        self.asset_dropdown.update()

    def _on_asset_selected(self, e):
        asset_id = self.asset_dropdown.value
        if asset_id in self.assets_map:
            asset = self.assets_map[asset_id]
            self.tab1_address_field.value = asset.location
            # DBの種別をラジオボタンに反映
            type_map = {"Land": "土地", "Building": "建物", "Condo": "建物"} # 区分所有は建物扱いとする
            self.tab1_type_group.value = type_map.get(asset.property_type, "土地")
            
            self.tab1_address_field.update()
            self.tab1_type_group.update()

    def _run_acquisition(self, address, type_str):
        """自動操作実行 (共通処理)"""
        self.page.open(SnackBar(Text("ブラウザを起動して処理を開始します..."), bgcolor=Colors.BLUE))
        self.page.update()

        def task():
            if not registry_service.login():
                self.page.open(SnackBar(Text("ログインに失敗しました"), bgcolor=Colors.RED))
                self.page.update()
                return

            success = registry_service.request_real_estate(address, type_str)
            
            if success:
                self.page.open(SnackBar(Text("検索・確定処理が完了しました。ブラウザで確認してください。"), bgcolor=Colors.GREEN))
            else:
                self.page.open(SnackBar(Text("処理中にエラーが発生しました"), bgcolor=Colors.RED))
            self.page.update()

        self.page.run_thread(task)

    def _on_acquire_registered(self, e):
        address = self.tab1_address_field.value
        if not address:
            self.page.open(SnackBar(Text("不動産を選択してください"), bgcolor=Colors.RED))
            return
        self._run_acquisition(address, self.tab1_type_group.value)

    def _on_acquire_manual(self, e):
        address = self.manual_address_field.value
        if not address:
            self.page.open(SnackBar(Text("住所を入力してください"), bgcolor=Colors.RED))
            return
        self._run_acquisition(address, self.manual_type_group.value)

    def _on_acquire_corp(self, e):
        name = self.corp_name_field.value
        if not name:
            self.page.open(SnackBar(Text("会社名を入力してください"), bgcolor=Colors.RED))
            return
        
        self.page.open(SnackBar(Text("ブラウザを起動して処理を開始します..."), bgcolor=Colors.BLUE))
        self.page.update()

        def task():
            if not registry_service.login():
                self.page.open(SnackBar(Text("ログインに失敗しました"), bgcolor=Colors.RED))
                return
            
            success = registry_service.request_corporate(name, self.corp_pref_field.value)
            if success:
                self.page.open(SnackBar(Text("処理完了"), bgcolor=Colors.GREEN))
            else:
                self.page.open(SnackBar(Text("エラーが発生しました"), bgcolor=Colors.RED))
            self.page.update()

        self.page.run_thread(task)