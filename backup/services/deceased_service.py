# src/services/deceased_service.py
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from src.models.database import SessionLocal
from src.models.tables import Case, CaseStatus, Deceased, Task, User


def get_all_users():
    """全てのユーザーIDと名前を取得する"""
    db = SessionLocal()
    try:
        users = db.query(User.id, User.name).order_by(User.id).all()
        return {id: name for id, name in users}
    finally:
        db.close()


def get_all_case_statuses():
    """全ての案件ステータスを取得する"""
    db = SessionLocal()
    try:
        return db.query(CaseStatus).order_by(CaseStatus.order_num).all()
    finally:
        db.close()


def get_case_folder_path(case_id: int) -> str | None:
    """Case ID に紐づくフォルダパスを取得する"""
    db = SessionLocal()
    try:
        case = db.query(Case).filter(Case.case_id == case_id).first()
        return case.folder_path if case and case.folder_path else None
    finally:
        db.close()


def get_case_list(search_term="", status_id=None, user_id=None):
    """
    案件一覧を取得する
    Taskテーブルを結合し、最新のタスク状況も取得する
    """
    db = SessionLocal()
    try:
        query = (
            db.query(
                Case,
                Deceased.name_last,
                Deceased.name_first,
                CaseStatus.name.label("status_name"),
                Task.description,
                Task.last_updated_at,
            )
            .join(Case.deceased_ref, isouter=True)
            .join(Case.status_ref, isouter=True)
            .join(Task, Case.case_id == Task.case_id, isouter=True)
            .order_by(Case.contract_date.desc())
        )

        if search_term:
            query = query.filter(
                (Case.case_number.ilike(f"%{search_term}%"))
                | (Case.client_name.ilike(f"%{search_term}%"))
                | (Case.client_name_kana.ilike(f"%{search_term}%"))
            )

        if status_id:
            query = query.filter(Case.current_status_id == status_id)

        if user_id:
            query = query.filter((Case.manager_id == user_id) | (Case.operator_id == user_id))

        # データ取得 (limitは一旦外すが、件数が多い場合は考慮が必要)
        cases_data = query.limit(100).all()

        case_list = []
        processed_ids = set()

        # 最新タスクを表示したいが、ここでは単純化のため重複行の最初を採用
        for case, d_last, d_first, status_name, description, last_updated_at in cases_data:
            if case.case_id in processed_ids:
                continue
            processed_ids.add(case.case_id)

            deceased_name = f"{d_last} {d_first}" if d_last else "N/A"
            role_label = ""
            if user_id:
                if case.manager_id == user_id and case.operator_id == user_id:
                    role_label = "担当1 & 2"
                elif case.manager_id == user_id:
                    role_label = "担当1"
                elif case.operator_id == user_id:
                    role_label = "担当2"

            case_list.append(
                {
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "client_name": case.client_name,
                    "deceased_name": deceased_name,
                    "contract_date": case.contract_date.strftime("%Y/%m/%d")
                    if case.contract_date
                    else "N/A",
                    "status": status_name if status_name else "未設定",
                    "role_label": role_label,
                    "manager_id": case.manager_id,
                    "operator_id": case.operator_id,
                    "description": description if description else "",
                    "last_updated_at": last_updated_at.strftime("%Y/%m/%d")
                    if last_updated_at
                    else "N/A",
                }
            )
        return case_list
    finally:
        db.close()


def get_my_cases(user_id: int, limit: int = 10):
    """特定のユーザーが担当する案件を取得する"""
    db = SessionLocal()
    try:
        query = (
            db.query(Case)
            .options(joinedload(Case.deceased_ref), joinedload(Case.status_ref))
            .filter((Case.manager_id == user_id) | (Case.operator_id == user_id))
            .order_by(Case.current_status_id, Case.contract_date.desc())
        )
        cases = query.limit(limit).all()
        case_list = []
        for case in cases:
            deceased_name = (
                case.deceased_ref.name_last + " " + case.deceased_ref.name_first
                if case.deceased_ref
                else "N/A"
            )
            case_list.append(
                {
                    "case_id": case.case_id,
                    "case_number": case.case_number,
                    "client_name": case.client_name,
                    "deceased_name": deceased_name,
                    "status": case.status_ref.name if case.status_ref else "N/A",
                }
            )
        return case_list
    finally:
        db.close()


def get_incomplete_tasks(user_id=None):
    """未完了のタスクを取得する"""
    db = SessionLocal()
    try:
        query = (
            db.query(Task, Case.case_number, User.name, Case.client_name)
            .join(Case, Task.case_id == Case.case_id)
            .join(User, Task.assigned_user_id == User.id)
            .filter(Task.is_completed == False)
        )

        if user_id:
            query = query.filter(Task.assigned_user_id == user_id)

        tasks = query.order_by(Task.due_date).limit(10).all()

        tasks_data = []
        for task, case_number, assigned_user_name, client_name in tasks:
            tasks_data.append(
                {
                    "task_id": task.task_id,
                    "case_id": task.case_id,
                    "case_number": case_number,
                    "description": task.description,
                    "due_date": task.due_date.strftime("%Y/%m/%d") if task.due_date else "N/A",
                    "assigned_user": assigned_user_name,
                    "client_name": client_name,
                }
            )
        return tasks_data
    finally:
        db.close()


def get_user_capacity_data():
    """全担当者の業務キャパシティ（未完了タスク数、担当案件数）を取得する"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        capacity_data = []
        for user in users:
            user_id = user.id
            task_count = (
                db.query(func.count(Task.task_id))
                .filter(Task.assigned_user_id == user_id, Task.is_completed == False)
                .scalar()
            )
            case_count = (
                db.query(func.count(Case.case_id))
                .filter((Case.manager_id == user_id) | (Case.operator_id == user_id))
                .scalar()
            )
            capacity_data.append(
                {
                    "user_id": user_id,
                    "name": user.name,
                    "role": user.role,
                    "total_incomplete_tasks": task_count,
                    "total_cases_handled": case_count,
                }
            )
        capacity_data.sort(key=lambda x: x["total_incomplete_tasks"], reverse=True)
        return capacity_data
    finally:
        db.close()
