# src/services/real_estate_service.py
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

# pdf2imageライブラリを使用 (要: pip install pdf2image)
from pdf2image import convert_from_path

from src.models.database import SessionLocal
from src.models.tables import Case, RealEstateAsset


def get_real_estates_by_case(case_id: int) -> List[RealEstateAsset]:
    """案件に紐づく不動産リストを取得"""
    db = SessionLocal()
    try:
        return db.query(RealEstateAsset).filter(RealEstateAsset.case_id == case_id).all()
    finally:
        db.close()


def add_real_estate(
    case_id: int, property_type: str, location: str, ownership_share: str = None
) -> Optional[RealEstateAsset]:
    """不動産情報の新規追加"""
    db = SessionLocal()
    try:
        asset = RealEstateAsset(
            case_id=case_id,
            property_type=property_type,
            location=location,
            ownership_share=ownership_share,  # 💡 追加
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset
    except Exception as e:
        db.rollback()
        print(f"Add RealEstate Error: {e}")
        return None
    finally:
        db.close()


def save_registry_document(case_id: int, real_estate_id: int, src_pdf_path: str) -> bool:
    """
    1. PDFを案件フォルダにコピー
    2. 先頭ページを画像変換して保存
    3. DBにパスを記録
    """
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        asset = db.query(RealEstateAsset).get(real_estate_id)

        if not case or not asset:
            raise ValueError("データが見つかりません")

        # 案件フォルダパス (なければ output/ を代用)
        base_folder = case.folder_path if case.folder_path else "output"

        # 保存先: {CaseFolder}/properties/{asset_id}/
        save_dir = Path(base_folder) / "properties" / str(real_estate_id)
        save_dir.mkdir(parents=True, exist_ok=True)

        # 1. PDFコピー
        file_name = f"registry_{uuid.uuid4().hex[:8]}.pdf"
        dest_pdf_path = save_dir / file_name
        shutil.copy2(src_pdf_path, dest_pdf_path)

        # 2. 画像変換 (同期処理)
        # Popplerのパス設定が必要な場合はここで指定 (ここではシステムPATH利用を想定)
        img_name = dest_pdf_path.stem + ".jpg"
        dest_img_path = save_dir / img_name

        try:
            # dpi=200で変換
            images = convert_from_path(str(dest_pdf_path), dpi=200, first_page=1, last_page=1)
            if images:
                images[0].save(str(dest_img_path), "JPEG")
            else:
                print("Warning: PDF conversion returned no images.")
        except Exception as e:
            print(f"PDF Conversion Error: {e}")
            # 画像変換失敗してもPDF保存は成功しているので続行

        # 3. DB更新
        asset.registry_pdf_path = str(dest_pdf_path)
        if dest_img_path.exists():
            asset.registry_image_path = str(dest_img_path)

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        print(f"Error saving registry doc: {e}")
        return False
    finally:
        db.close()


def delete_real_estate(asset_id: int) -> bool:
    """不動産情報の削除"""
    db = SessionLocal()
    try:
        asset = db.query(RealEstateAsset).get(asset_id)
        if asset:
            db.delete(asset)
            db.commit()
            return True
        return False
    finally:
        db.close()
