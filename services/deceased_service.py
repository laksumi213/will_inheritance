# /services/deceased_service.py

from sqlalchemy.orm import Session, joinedload

from services.db_setup import Deceased, Engine, Heir

# 被相続人関連のデータアクセスロジック


def get_all_deceased():
    with Session(bind=Engine) as session:
        return session.query(Deceased).all()


def get_deceased_by_id(deceased_id: int):
    with Session(bind=Engine) as session:
        # joinedload(Deceased.heirs) を追加
        deceased = (
            session.query(Deceased).options(joinedload(Deceased.heirs)).get(deceased_id)
        )
        # セッションが閉じる前に、deceased.heirs のデータもロードされる
        return deceased


def add_deceased(name: str, dob: str):
    new_deceased = Deceased(name=name, date_of_birth=dob)
    with Session(bind=Engine) as session:
        session.add(new_deceased)
        session.commit()


def delete_deceased(deceased_id: int):
    with Session(bind=Engine) as session:
        deceased_to_delete = session.query(Deceased).get(deceased_id)
        if deceased_to_delete:
            session.delete(deceased_to_delete)
            session.commit()


def update_deceased(deceased_id: int, name: str, dob: str):
    """指定されたIDの被相続人の名前と生年月日を更新する。"""
    with Session(bind=Engine) as session:
        deceased = session.query(Deceased).get(deceased_id)
        if deceased:
            deceased.name = name
            deceased.date_of_birth = dob
            session.commit()


# 相続人関連のデータアクセスロジック（必要に応じてheir_service.pyに分離しても良い）


def add_heir(deceased_id: int, name: str, rel: str):
    new_heir = Heir(name=name, relationship_name=rel, deceased_id=deceased_id)
    with Session(bind=Engine) as session:
        session.add(new_heir)
        session.commit()


def delete_heir(heir_id: int):
    with Session(bind=Engine) as session:
        heir_to_delete = session.query(Heir).get(heir_id)
        if heir_to_delete:
            session.delete(heir_to_delete)
            session.commit()


def update_heir(heir_id: int, name: str, rel: str):
    """指定されたIDの相続人の名前と続柄を更新する。"""
    with Session(bind=Engine) as session:
        heir = session.query(Heir).get(heir_id)
        if heir:
            heir.name = name
            heir.relationship_name = rel
            session.commit()
