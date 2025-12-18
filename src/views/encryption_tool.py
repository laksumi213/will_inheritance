# src/views/encryption_tool.py
import os
from typing import List

from flet import (
    AlertDialog,
    ButtonStyle,
    Colors,
    Column,
    Container,
    ElevatedButton,
    FilePicker,
    FilePickerResultEvent,
    FontWeight,
    Icon,
    IconButton,
    Icons,
    ListView,
    MainAxisAlignment,
    Page,
    Row,
    ScrollMode,
    SnackBar,
    Text,
    TextField,
    border,
    padding,
)

from src.services.crypto_service import crypto_service


class EncryptionToolView(Column):
    """
    セキュリティZIP作成ツール画面
    - パスワードの手動設定/自動生成
    - ファイルの追記選択（何度でも追加可能）
    """

    def __init__(self, page: Page):
        super().__init__(expand=True, scroll=ScrollMode.AUTO, spacing=20)
        self.page = page

        # 選択されたファイルのパスを保持するリスト
        self.selected_files: List[str] = []

        # --- ファイルピッカーの初期化 ---
        self.file_picker = FilePicker(on_result=self._on_files_picked)
        self.save_picker = FilePicker(on_result=self._on_save_location_picked)
        # オーバーレイに追加（画面遷移しても使えるように）
        if self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)
        if self.save_picker not in self.page.overlay:
            self.page.overlay.append(self.save_picker)

        # --- UI部品の定義 ---

        # 1. ファイルリスト表示用
        self.file_list_view = ListView(
            height=200,
            spacing=5,
            padding=10,
        )

        # 2. パスワード入力欄
        self.password_field = TextField(
            label="設定パスワード",
            width=400,
            password=False,  # 確認しやすいように最初は平文表示（必要に応じてTrueに変更）
            can_reveal_password=True,  # パスワード表示/非表示の切り替えボタン
            hint_text="自動生成または手動で入力してください",
            helper_text="※初期表示は自動生成された強力なパスワードです。手動で書き換え可能です。",
        )

        # 3. 実行ボタン
        self.btn_encrypt = ElevatedButton(
            "ZIP作成を実行（保存先を選択）",
            icon=Icons.SAVE_ALT,
            on_click=self._open_save_dialog,
            style=ButtonStyle(
                bgcolor="primary",
                color="onPrimary",
                padding=20,
            ),
            disabled=True,  # ファイル未選択時は無効化
        )

        # --- 画面レイアウトの構築 ---
        self.controls = [
            # ヘッダー
            Container(
                content=Column(
                    [
                        Row(
                            [
                                Icon(Icons.ENHANCED_ENCRYPTION, size=30, color="primary"),
                                Text("セキュリティZIP作成ツール", size=24, weight=FontWeight.BOLD),
                            ]
                        ),
                        Text(
                            "AES-256暗号化を用いたZIPファイルを作成します。パスワードは手動で変更可能です。",
                            color="secondary",
                        ),
                    ]
                ),
                padding=padding.only(bottom=10),
            ),
            # エリア1: パスワード設定
            Container(
                content=Column(
                    [
                        Row(
                            [
                                Icon(Icons.KEY, color="primary"),
                                Text("1. パスワード設定", weight=FontWeight.BOLD, size=16),
                            ]
                        ),
                        Row(
                            [
                                self.password_field,
                                ElevatedButton(
                                    "再生成",
                                    icon=Icons.AUTORENEW,
                                    on_click=self._generate_password,
                                    tooltip="新しいランダムパスワードを生成します",
                                ),
                                IconButton(
                                    icon=Icons.COPY,
                                    tooltip="パスワードをクリップボードにコピー",
                                    icon_color="primary",
                                    on_click=self._copy_password,
                                ),
                            ]
                        ),
                    ]
                ),
                padding=15,
                border=border.all(1, "outline"),
                border_radius=10,
            ),
            # エリア2: ファイル選択（追記型）
            Container(
                content=Column(
                    [
                        Row(
                            [
                                Row(
                                    [
                                        Icon(Icons.FOLDER_OPEN, color="primary"),
                                        Text("2. ファイル選択", weight=FontWeight.BOLD, size=16),
                                    ]
                                ),
                                # アクションボタン群
                                Row(
                                    [
                                        ElevatedButton(
                                            "ファイルを追加",
                                            icon=Icons.ADD,
                                            bgcolor="primaryContainer",
                                            color="onPrimaryContainer",
                                            # 複数選択可能なダイアログを開く
                                            on_click=lambda _: self.file_picker.pick_files(
                                                allow_multiple=True,
                                                dialog_title="追加するファイルを選択",
                                            ),
                                        ),
                                        ElevatedButton(
                                            "全クリア",
                                            icon=Icons.DELETE_SWEEP,
                                            color=Colors.RED,
                                            on_click=self._clear_all_files,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                            ],
                            alignment=MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        Text(
                            "※「ファイルを追加」を押すと、現在のリストを保持したまま更にファイルを追加できます。",
                            size=12,
                            color="grey",
                        ),
                        # 選択済みリスト表示エリア
                        Container(
                            content=self.file_list_view,
                            border=border.all(1, "outlineVariant"),
                            border_radius=8,
                            bgcolor="surfaceVariant",
                            padding=10,
                            height=250,  # 高さを固定してスクロールさせる
                        ),
                    ]
                ),
                padding=15,
                border=border.all(1, "outline"),
                border_radius=10,
            ),
            # エリア3: 実行ボタン
            Container(
                content=Row([self.btn_encrypt], alignment=MainAxisAlignment.END),
                padding=padding.only(top=10, bottom=30),
            ),
        ]

    def did_mount(self):
        """画面が表示された直後に実行される処理"""
        # 初期パスワードを自動生成してセット
        self._generate_password(None)

    def _generate_password(self, e):
        """強力なパスワードを生成して入力欄にセット"""
        # crypto_serviceの関数を利用（12桁）
        pwd = crypto_service.generate_strong_password(length=12)
        self.password_field.value = pwd
        self.password_field.update()

        # ユーザーへのフィードバック（任意）
        if e:  # ボタンクリック時のみ通知
            self.page.open(SnackBar(Text("新しいパスワードを生成しました"), duration=1000))
            self.page.update()

    def _copy_password(self, e):
        """現在入力されているパスワードをコピー"""
        val = self.password_field.value
        if val:
            self.page.set_clipboard(val)
            self.page.open(SnackBar(Text("パスワードをコピーしました"), bgcolor=Colors.GREEN))
            self.page.update()

    def _on_files_picked(self, e: FilePickerResultEvent):
        """
        ファイル選択ダイアログが閉じられた時の処理
        既存のリストに新しいファイルを追加（追記）する
        """
        if e.files:
            added_count = 0
            for f in e.files:
                path = f.path
                # 重複チェック: まだリストにない場合のみ追加
                if path not in self.selected_files:
                    self.selected_files.append(path)
                    added_count += 1

            if added_count > 0:
                self._update_file_list_ui()
                self.page.open(
                    SnackBar(Text(f"{added_count}個のファイルを追加しました"), bgcolor=Colors.GREEN)
                )
            else:
                self.page.open(
                    SnackBar(
                        Text("選択されたファイルは既に追加されています"), bgcolor=Colors.ORANGE
                    )
                )

            self.page.update()

    def _update_file_list_ui(self):
        """内部データ(self.selected_files)に基づいてUIリストを再描画"""
        self.file_list_view.controls.clear()

        if not self.selected_files:
            self.file_list_view.controls.append(
                Text(
                    "ファイルがまだ選択されていません。\n「ファイルを追加」ボタンから選択してください。",
                    italic=True,
                    color="grey",
                )
            )
            self.btn_encrypt.disabled = True
        else:
            self.btn_encrypt.disabled = False
            # 逆順（新しく追加したものが上）で表示するとわかりやすい
            for i, path in enumerate(reversed(self.selected_files)):
                filename = os.path.basename(path)

                # 行ごとのレイアウト
                row = Container(
                    content=Row(
                        [
                            Icon(Icons.INSERT_DRIVE_FILE, size=20, color="primary"),
                            Text(filename, expand=True, weight=FontWeight.W_500),
                            # 削除ボタン
                            IconButton(
                                icon=Icons.CLOSE,
                                icon_color=Colors.RED_400,
                                tooltip="リストから削除",
                                on_click=lambda e, p=path: self._remove_single_file(p),
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    padding=5,
                    border=border.only(bottom=border.BorderSide(1, "outlineVariant")),
                )
                self.file_list_view.controls.append(row)

        self.btn_encrypt.update()
        self.file_list_view.update()

    def _remove_single_file(self, path_to_remove: str):
        """指定したファイルをリストから削除"""
        if path_to_remove in self.selected_files:
            self.selected_files.remove(path_to_remove)
            self._update_file_list_ui()

    def _clear_all_files(self, e):
        """全ファイルをクリア"""
        self.selected_files.clear()
        self._update_file_list_ui()

    def _open_save_dialog(self, e):
        """保存先選択ダイアログを開く"""
        current_password = self.password_field.value

        if not current_password:
            self.page.open(
                SnackBar(Text("パスワードが空です。設定してください。"), bgcolor=Colors.RED)
            )
            self.page.update()
            return

        if not self.selected_files:
            self.page.open(SnackBar(Text("ファイルが選択されていません。"), bgcolor=Colors.RED))
            self.page.update()
            return

        self.save_picker.save_file(
            dialog_title="作成するZIPファイルの保存先を指定してください",
            file_name="encrypted_archive.zip",
            allowed_extensions=["zip"],
        )

    def _on_save_location_picked(self, e: FilePickerResultEvent):
        """保存先が決定したら暗号化処理を実行"""
        if not e.path:
            return  # キャンセルされた場合

        save_path = e.path
        password = self.password_field.value

        # 処理中表示
        self.page.open(SnackBar(Text("暗号化圧縮を作成中..."), bgcolor=Colors.BLUE))
        self.page.update()

        # 暗号化処理の実行（エラーハンドリング付き）
        try:
            # Service層のロジックを呼び出し
            crypto_service.create_encrypted_zip(
                source_files=self.selected_files, output_path=save_path, password=password
            )

            # 完了ダイアログ
            def close_dlg(e):
                self.page.close(dlg)
                self.page.update()

            dlg = AlertDialog(
                title=Text("作成完了"),
                content=Column(
                    [
                        Text(f"以下の場所に保存しました:\n{save_path}", weight=FontWeight.BOLD),
                        Divider(),
                        Text(
                            f"設定パスワード: {password}",
                            color=Colors.RED,
                            size=16,
                            weight=FontWeight.BOLD,
                        ),
                        Text(
                            "※ パスワードを忘れると解凍できません。\n必ず控えておくか、別途送付してください。"
                        ),
                    ],
                    tight=True,
                ),
                actions=[
                    ElevatedButton(
                        "フォルダを開く", on_click=lambda _: self._open_folder(save_path)
                    ),
                    TextButton("閉じる", on_click=close_dlg),
                ],
                actions_alignment=MainAxisAlignment.END,
            )
            self.page.open(dlg)
            self.page.update()

        except Exception as ex:
            self.page.open(SnackBar(Text(f"作成エラー: {ex}"), bgcolor=Colors.RED))
            self.page.update()

    def _open_folder(self, file_path: str):
        """保存先のフォルダをOSのエクスプローラで開く"""
        folder = os.path.dirname(file_path)
        if os.name == "nt":  # Windows
            os.startfile(folder)
        elif os.name == "posix":  # Mac/Linux
            import subprocess

            subprocess.call(["open", folder])
