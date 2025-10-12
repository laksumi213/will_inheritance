# /services/task_generation_logic.py

import os
import sys
from datetime import date, datetime, time, timedelta

# プロジェクトのルートディレクトリをパスに追加 (インポートエラー対策)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".", "..")))

# 既存のインポートをそのまま続ける
from services.db_setup import (
    Base,  # 💡 クラス: データベースの宣言的ベースクラス (SQLAlchemy)
    Case,  # 💡 クラス: 案件情報 (ケース) を格納するDBモデル
    CaseStatus,  # 💡 クラス: 案件のステータス (例: 受託、作業中) を格納するDBモデル
    Engine,  # 💡 クラス: データベース接続エンジン (SQLAlchemy)
    Session,  # 💡 クラス: データベース操作を行うセッションクラス (SQLAlchemy)
    Task,  # 💡 クラス: 個別のタスク (TODO) を格納するDBモデル
    TaskTemplate,  # 💡 クラス: 定型タスクのテンプレート情報を格納するDBモデル
    User,  # 💡 クラス: ユーザー (担当者) 情報を格納するDBモデル
)

# --- DBモデル定義の重複を回避するため、TaskTemplateなどのクラス定義は全てdb_setup.pyに移動します ---

# --- 2. タスク生成コアロジック ---


def generate_case_tasks(db, case_id: int):
    """
    特定の案件が受託された際に、定型タスクテンプレートに基づき、
    TaskテーブルにTODOレコードを一括生成するコアロジック。
    """
    # 💡 変数: データベースセッションオブジェクト
    # 💡 変数: タスクを生成する対象案件のID
    case = (
        db.query(Case).filter(Case.case_id == case_id).first()
    )  # 💡 変数: 取得した案件 (Case) のDBレコード
    if not case:
        print(f"Error: 案件ID {case_id} が見つかりません。")
        return False

    # 1. 案件情報から担当者IDと契約日を取得
    manager_id = case.manager_id  # 💡 変数: 案件の担当者1 (マネージャー) のユーザーID
    operator_id = (
        case.operator_id
    )  # 💡 変数: 案件の担当者2 (オペレーター/事務担当) のユーザーID
    # 契約日をトリガーとする (contract_dateがNoneの場合は今日の日付を使用)
    trigger_date = (
        case.contract_date if case.contract_date else date.today()
    )  # 💡 変数: タスク期限日計算の起算日（基本は契約日）

    # 2. 全てのタスクテンプレートを取得 (依存関係ロジックは省略し、単純生成を行う)
    templates = (
        db.query(TaskTemplate).order_by(TaskTemplate.template_id).all()
    )  # 💡 変数: 全てのタスクテンプレート (TaskTemplate) のリスト

    new_tasks = []  # 💡 変数: 新規に作成されたTaskオブジェクトを一時的に保持するリスト

    for template in (
        templates
    ):  # 💡 変数: リストtemplatesから取り出された個別のTaskTemplateオブジェクト
        # 3. 担当者割り当てと期限の計算
        assigned_id = (
            manager_id if template.is_manager_task else operator_id
        )  # 💡 変数: タスクが割り当てられるユーザーのID (担当1 or 担当2)

        # 期限日を計算 (契約日 + デフォルト日数)
        due_date = datetime.combine(trigger_date, time.min) + timedelta(
            days=template.default_due_days
        )  # 💡 変数: 計算されたタスクの期限日

        # 4. 新しいTaskレコードを作成
        new_task = Task(  # 💡 変数: 新規作成されたTask (TODO) のDBレコードオブジェクト
            case_id=case_id,
            template_id=template.template_id,
            description=template.description,
            assigned_user_id=assigned_id,
            due_date=due_date,
        )
        new_tasks.append(new_task)

    db.add_all(new_tasks)
    db.commit()
    print(f"案件 {case.case_number} に {len(new_tasks)} 件のタスクを自動生成しました。")
    return True


# --- 3. タスクテンプレートとテストデータ投入関数 ---


def setup_task_templates(db):
    """データベースに定型タスクテンプレート（TaskTemplate）を初期投入する"""

    # 役割: 担当2(False) または 担当1(True)
    templates = [
        # T001 - T005: 初期準備と発送
        {
            "id": 1,
            "description": "【送付準備】契約書・委任状等初期一式作成",
            "days": 1,
            "manager": False,
        },
        {
            "id": 2,
            "description": "【原本・情報】返送書類一覧表作成",
            "days": 1,
            "manager": False,
        },
        {
            "id": 3,
            "description": "【承認】T001・T002のチェック依頼",
            "days": 2,
            "manager": True,
        },  # 担当1のチェック (承認)
        {
            "id": 4,
            "description": "【費用入力】レターパック代金の実費入力",
            "days": 1,
            "manager": False,
        },  # 必須費用入力
        {
            "id": 5,
            "description": "【郵送・発送】契約書等初期書類一式の発送",
            "days": 0,
            "manager": False,
        },
        # T006 - T007: 書類受領とデジタル保全
        {
            "id": 6,
            "description": "【原本チェック】返送書類のリスト照合と有効期限記録",
            "days": 1,
            "manager": False,
        },
        {
            "id": 7,
            "description": "【デジタル保全】全返送書類のスキャンとアップロード",
            "days": 1,
            "manager": False,
        },
        # T012 - T013: 依頼と実行 (戸籍・凍結)
        {
            "id": 12,
            "description": "【戸籍依頼】依頼表の作成と戸籍担当者への依頼（名寄帳含む）",
            "days": 1,
            "manager": False,
        },
        {
            "id": 13,
            "description": "【凍結実行】金融機関への凍結連絡（Web/電話）",
            "days": 1,
            "manager": False,
        },
        # T022 - T023: 目録作成
        {
            "id": 22,
            "description": "【目録作成】全調査結果を統合した財産目録のドラフト作成",
            "days": 5,
            "manager": False,
        },
        {
            "id": 23,
            "description": "【承認】財産目録ドラフトの最終チェックと承認",
            "days": 1,
            "manager": True,
        },  # 担当1のチェック
    ]

    for t in (
        templates
    ):  # 💡 変数: リストtemplatesから取り出された個別のテンプレートデータ (辞書)
        # TaskTemplateモデルが存在することを前提にクエリを実行
        if (
            not db.query(TaskTemplate)
            .filter(TaskTemplate.template_id == t["id"])
            .first()
        ):
            db.add(
                TaskTemplate(
                    template_id=t["id"],
                    description=t["description"],
                    default_due_days=t["days"],
                    is_manager_task=t["manager"],
                )
            )
    db.commit()


def seed_db_users_and_cases(db):
    """UserとCaseの初期データを投入する (タスク生成テスト用)"""
    # 💡 変数: データベースセッションオブジェクト
    # ユーザー
    users_data = [  # 💡 変数: 投入するユーザーの初期データ (辞書のリスト)
        {"windows_id": "tanaka_a", "role": "Manager", "name": "田中 篤志"},
        {"windows_id": "sato_b", "role": "Operator", "name": "佐藤 華子"},
    ]
    # ... (ユーザー、ステータスの初期投入ロジックはdb_setup.pyから分離され、この関数で実行されます)
    for data in (
        users_data
    ):  # 💡 変数: リストusers_dataから取り出された個別のユーザーデータ (辞書)
        if not db.query(User).filter(User.windows_id == data["windows_id"]).first():
            db.add(User(**data))

    # ステータス
    if not db.query(CaseStatus).filter(CaseStatus.name == "受託").first():
        db.add(CaseStatus(name="受託", order_num=4))

    db.commit()
    tanaka = (
        db.query(User).filter(User.windows_id == "tanaka_a").first()
    )  # 💡 変数: ユーザー「田中 篤志」のDBレコードオブジェクト
    sato = (
        db.query(User).filter(User.windows_id == "sato_b").first()
    )  # 💡 変数: ユーザー「佐藤 華子」のDBレコードオブジェクト

    # 案件 (受託済みを想定)
    case_number = "G0001"  # 💡 変数: テスト用案件番号
    if not db.query(Case).filter(Case.case_number == case_number).first():
        status_accepted_id = (
            db.query(CaseStatus).filter(CaseStatus.name == "受託").first().id
        )  # 💡 変数: ステータス「受託」のID
        case1 = (
            Case(  # 💡 変数: 新規作成されたテスト用の案件 (Case) DBレコードオブジェクト
                case_number=case_number,
                client_name="高橋 健太",
                manager_id=tanaka.id,
                operator_id=sato.id,
                contract_date=date.today(),
                current_status_id=status_accepted_id,
            )
        )
        db.add(case1)
        db.commit()
        return case1.case_id, tanaka.id, sato.id  # 💡 戻り値: 案件ID、田中ID、佐藤ID

    return (
        db.query(Case)
        .filter(Case.case_number == case_number)
        .first()
        .case_id,  # 💡 戻り値: 案件ID
        tanaka.id,  # 💡 戻り値: 田中ID
        sato.id,  # 💡 戻り値: 佐藤ID
    )


# --- 4. 実行ブロック (テスト) ---

if __name__ == "__main__":
    from services.db_setup import Base, Engine, Session
    # 💡 クラス: データベースの宣言的ベースクラス (SQLAlchemy)
    # 💡 クラス: データベース接続エンジン (SQLAlchemy)
    # 💡 クラス: データベース操作を行うセッションクラス (SQLAlchemy)

    # DBテーブル構造の作成（db_setup.pyで定義した全てのテーブルを作成）
    Base.metadata.create_all(Engine)

    # DBセッション開始
    with Session() as db:  # 💡 変数: データベースセッションオブジェクト
        # ユーザーとテンプレートの初期投入
        case_id, tanaka_id, sato_id = seed_db_users_and_cases(
            db
        )  # 💡 変数: case_id (案件ID), tanaka_id (担当1 ID), sato_id (担当2 ID)
        setup_task_templates(db)

        # 既存タスクをクリア (テスト再実行用)
        db.query(Task).delete()
        db.commit()

        # 案件ID:1をトリガーにしてタスクを自動生成
        print("---------------------------------------")
        print(f"案件ID: {case_id} のタスク生成を開始します。")
        generate_case_tasks(db, case_id)
        print("---------------------------------------")

        # 結果の確認
        generated_tasks = db.query(
            Task
        ).all()  # 💡 変数: 生成された全てのタスク (Task) のDBレコードリスト
        print(f"生成されたタスク総数: {len(generated_tasks)} 件")
