# src/views/register.py
from datetime import datetime

from flet import (
    AppBar,
    Colors,
    Column,
    Container,
    ElevatedButton,
    Icons,
    Page,
    SnackBar,
    Text,
    TextField,
    View,
    padding,
)

from src.models.database import SessionLocal
from src.models.tables import Case, Deceased


class ClientRegisterView(View):
    """新規案件（顧客）登録画面"""

    def __init__(self, page: Page):
        super().__init__(route="/client_register")
        self.page = page

        self.appbar = AppBar(
            title=Text("新規案件登録"), bgcolor=Colors.BLUE_500, color=Colors.WHITE
        )

        self.client_name = TextField(label="依頼者名", hint_text="例: 佐藤 一郎")
        self.deceased_name = TextField(label="被相続人名", hint_text="例: 佐藤 次郎")
        # 本来はカレンダー入力などが望ましいが、簡易的にテキスト入力
        self.deceased_date = TextField(label="死亡日", hint_text="YYYY-MM-DD (任意)")

        self.controls = [
            Container(
                content=Column(
                    [
                        Text("新しい相続案件を登録します。", size=16),
                        self.client_name,
                        self.deceased_name,
                        self.deceased_date,
                        ElevatedButton(
                            "登録して開始",
                            icon=Icons.ROCKET_LAUNCH,
                            bgcolor=Colors.BLUE_500,
                            color=Colors.WHITE,
                            on_click=self.register,
                        ),
                    ],
                    spacing=20,
                ),
                padding=padding.all(20),
            )
        ]

    def register(self, e):
        """DBへの保存処理"""
        # バリデーション
        if not self.client_name.value:
            self.page.open(SnackBar(Text("依頼者名は必須です"), bgcolor=Colors.RED))
            self.page.update()
            return
        if not self.deceased_name.value:
            self.page.open(SnackBar(Text("被相続人名は必須です"), bgcolor=Colors.RED))
            self.page.update()
            return

        db = SessionLocal()
        try:
            # 簡易的な案件番号生成 (実運用では採番ロジックが必要)
            timestamp_str = datetime.now().strftime("%Y%m%d%H%M")
            generated_case_number = f"G{timestamp_str}"

            # 1. 案件作成
            new_case = Case(
                case_number=generated_case_number,
                client_name=self.client_name.value,
                # その他の必須項目があればデフォルト値を設定
            )
            db.add(new_case)
            db.flush()  # ID確定

            # 2. 被相続人作成
            # 入力された死亡日を変換
            d_date = None
            if self.deceased_date.value:
                try:
                    d_date = datetime.strptime(self.deceased_date.value, "%Y-%m-%d").date()
                except ValueError:
                    pass  # フォーマットエラーは無視（None）

            # 姓名分割（簡易的）
            d_name = self.deceased_name.value.split(" ", 1)
            last = d_name[0]
            first = d_name[1] if len(d_name) > 1 else ""

            new_deceased = Deceased(
                case_id=new_case.case_id,
                name_last=last,
                name_first=first,
                date_of_death=d_date,
                relationship_type="本人",
            )
            db.add(new_deceased)

            db.commit()

            new_case_id = new_case.case_id

            # 成功通知
            self.page.open(
                SnackBar(Text(f"登録完了: {generated_case_number}"), bgcolor=Colors.GREEN)
            )
            self.page.update()

            # ダッシュボード経由で詳細へ遷移
            self.page.go(f"/detail/{new_case_id}/dashboard")

        except Exception as ex:
            db.rollback()
            print(ex)
            self.page.open(SnackBar(Text(f"登録エラー: {ex}"), bgcolor=Colors.RED))
            self.page.update()
        finally:
            db.close()
