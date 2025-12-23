# src/views/smbc_balance_doc_view.py
import time
from flet import (
    Page,
    Column,
    Row,
    Text,
    ElevatedButton,
    Card,
    Container,
    Divider,
    SnackBar,
    Colors,
    FontWeight,
    padding,
    MainAxisAlignment,
    CrossAxisAlignment,
    Icon,
    Icons,
    ButtonStyle,
    RoundedRectangleBorder,
)

# サービス層のインポート
from src.services.deceased_service import get_bank_cert_document_data
from src.services.pdf.smbc_pdf_service import generate_smbc_balance_certificate

def SmbcBalanceDocView(page: Page, case_id: int, bank_code: str):
    """
    三井住友銀行 残高証明書発行依頼書 作成画面
    関数ベースのViewコンポーネント。Containerを返す。
    """

    # --- データ取得 ---
    try:
        data = get_bank_cert_document_data(case_id, bank_code)
    except Exception as e:
        print(f"Data load error: {e}")
        data = None

    # --- エラーハンドリング: データが見つからない場合 ---
    if not data:
        return Container(
            content=Column(
                controls=[
                    Container(
                        content=Row(
                            controls=[
                                Icon(Icons.ERROR_OUTLINE, color=Colors.RED),
                                Text(
                                    "エラー: 案件情報または指定された銀行コードの口座情報が見つかりません。",
                                    size=16,
                                    color=Colors.RED,
                                ),
                            ]
                        ),
                        padding=20,
                    ),
                    ElevatedButton(
                        "戻る", 
                        on_click=lambda e: page.go(f"/case/{case_id}/doc/balance_cert")
                    ),
                ]
            ),
            expand=True
        )

    # --- UI用変数の展開 ---
    deceased = data.get("deceased", {})
    d_name = f"{deceased.get('last_name', '')} {deceased.get('first_name', '')}"
    
    contractor = data.get("contracting_party", {})
    c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}"

    bank_assets = data.get("bank_assets", [])
    bank_name = bank_assets[0]["bank_name"] if bank_assets else "銀行名不明"
    
    # --- ボタンコントロールの定義 ---
    # ボタンのスタイル定義
    def _button_style(color: str):
        return ButtonStyle(
            color=Colors.WHITE,
            bgcolor=color,
            padding=20,
            shape=RoundedRectangleBorder(radius=10),
        )

    mailing_btn = ElevatedButton(
        content=Row([Icon(Icons.MAIL), Text("作成（郵送専用）")]),
        style=_button_style(Colors.TEAL),
    )
    
    window_btn = ElevatedButton(
        content=Row([Icon(Icons.STORE), Text("作成（窓口用）")]),
        style=_button_style(Colors.INDIGO),
    )

    # --- イベントハンドラ ---
    def handle_create_pdf(e, is_mailing: bool):
        """PDF作成ボタン押下時の処理"""
        target_btn = mailing_btn if is_mailing else window_btn
        original_content = target_btn.content
        
        # 1. UIをローディング状態に変更
        target_btn.content = Row([Icon(Icons.HOURGLASS_TOP), Text("作成中...")])
        target_btn.disabled = True
        mailing_btn.update()
        window_btn.update()
        page.update()

        try:
            # 2. Service層の関数を呼び出し
            # スレッドで実行しないとUIがフリーズする可能性があるため、必要に応じて threading.Thread を検討
            # ここではシンプルに同期実行します (Fletのイベントハンドラはスレッドで動くため基本OK)
            output_path = generate_smbc_balance_certificate(
                data=data,
                bank_code=bank_code,
                case_id=case_id,
                is_mailing=is_mailing
            )

            # 3. 成功通知
            msg = "郵送用書類を作成しました" if is_mailing else "窓口用書類を作成しました"
            page.open(
                SnackBar(
                    content=Text(f"{msg}\n一覧画面に戻ります...", color=Colors.WHITE),
                    bgcolor=Colors.GREEN_700,
                )
            )
            page.update()
            
            # 4. 少し待機してから一覧画面へ遷移
            time.sleep(1.0)
            page.go(f"/case/{case_id}/doc/balance_cert")

        except Exception as err:
            # エラー処理
            print(f"PDF生成エラー: {err}")
            import traceback
            traceback.print_exc()
            
            page.open(
                SnackBar(
                    content=Text(f"エラーが発生しました: {str(err)}", color=Colors.WHITE),
                    bgcolor=Colors.RED_700,
                )
            )
            
            # ボタンの状態を復帰
            target_btn.content = original_content
            target_btn.disabled = False
            mailing_btn.update()
            window_btn.update()
            page.update()

    # コールバックの設定
    mailing_btn.on_click = lambda e: handle_create_pdf(e, is_mailing=True)
    window_btn.on_click = lambda e: handle_create_pdf(e, is_mailing=False)

    def _info_row(label: str, value: str) -> Row:
        """情報表示用のヘルパー行コンポーネント"""
        return Row(
            controls=[
                Text(label, width=150, color=Colors.GREY_700, weight=FontWeight.W_500),
                Text(value, weight=FontWeight.BOLD, size=16),
            ],
            alignment=MainAxisAlignment.START,
        )

    # --- 画面レイアウト ---
    return Container(
        content=Column(
            controls=[
                # ヘッダー
                Container(
                    content=Row(
                        controls=[
                            Icon(Icons.DESCRIPTION, size=30, color=Colors.BLUE),
                            Text(
                                f"{bank_name} ({bank_code}) 残高証明書申請書作成",
                                size=24,
                                weight=FontWeight.BOLD,
                                color=Colors.BLUE,
                            ),
                        ],
                        alignment=MainAxisAlignment.START,
                    ),
                    padding=padding.only(bottom=10),
                ),
                Divider(),

                # 案件・契約者情報カード
                Card(
                    content=Container(
                        content=Column(
                            controls=[
                                Text("案件情報", weight=FontWeight.BOLD, size=16),
                                Divider(),
                                _info_row("案件ID", str(case_id)),
                                _info_row("被相続人", d_name),
                                _info_row("契約者（請求者）", c_name),
                                _info_row("対象口座数", f"{len(bank_assets)} 口座"),
                            ],
                            spacing=10,
                        ),
                        padding=20,
                    ),
                    elevation=2,
                ),

                Container(height=20), # スペーサー

                # 操作ボタンエリア
                Text("作成オプション", weight=FontWeight.BOLD, size=16),
                Row(
                    controls=[
                        mailing_btn,
                        window_btn,
                    ],
                    spacing=20,
                ),
                
                Container(height=20),
                
                # 戻るボタン
                ElevatedButton(
                    "一覧に戻る", 
                    icon=Icons.ARROW_BACK,
                    on_click=lambda e: page.go(f"/case/{case_id}/doc/balance_cert")
                ),
            ],
            scroll="AUTO",
            expand=True,
        ),
        expand=True,
        padding=20,
    )