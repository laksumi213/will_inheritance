# src/services/real_estate_service.py
import shutil
import uuid
import glob
import os
from pathlib import Path
from typing import List, Optional

# pdf2imageライブラリを使用
from pdf2image import convert_from_path

from src.models.database import SessionLocal
from src.models.tables import Case, RealEstateAsset
# Popplerパス解決のためにインポート
from src.services.pdf_service import pdf_service


def get_real_estates_by_case(case_id: int) -> List[RealEstateAsset]:
    """案件に紐づく不動産リストを取得"""
    db = SessionLocal()
    try:
        return db.query(RealEstateAsset).filter(RealEstateAsset.case_id == case_id).all()
    finally:
        db.close()


def add_real_estate(
    case_id: int,
    property_type: str,
    location: str,
    ownership_share: str = None,
    lot_number: str = None,
    land_category: str = None,
    land_area: float = None,
    house_number: str = None,
    structure: str = None,
    floor_area: str = None,
) -> Optional[RealEstateAsset]:
    """
    不動産情報の新規追加
    """
    db = SessionLocal()
    try:
        asset = RealEstateAsset(
            case_id=case_id,
            property_type=property_type,
            location=location,
            ownership_share=ownership_share,
            lot_number=lot_number,
            land_category=land_category,
            land_area=land_area,
            house_number=house_number,
            structure=structure,
            floor_area=floor_area,
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


def update_real_estate(
    asset_id: int,
    property_type: str,
    location: str,
    ownership_share: str = None,
    lot_number: str = None,
    land_category: str = None,
    land_area: float = None,
    house_number: str = None,
    structure: str = None,
    floor_area: str = None,
) -> bool:
    """
    不動産情報の更新
    """
    db = SessionLocal()
    try:
        asset = db.query(RealEstateAsset).get(asset_id)
        if not asset:
            return False

        asset.property_type = property_type
        asset.location = location
        asset.ownership_share = ownership_share
        asset.lot_number = lot_number
        asset.land_category = land_category
        asset.land_area = land_area
        asset.house_number = house_number
        asset.structure = structure
        asset.floor_area = floor_area

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Update RealEstate Error: {e}")
        return False
    finally:
        db.close()


def save_registry_document(case_id: int, real_estate_id: int, src_pdf_path: str) -> bool:
    """
    1. PDFを案件フォルダにコピー
    2. 全ページを画像変換して保存 (registry_page_X.jpg)
    3. DBにパスを記録 (1ページ目を代表として保存)
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

        # 古い画像を削除（クリーンアップ）
        for old_img in save_dir.glob("registry_page_*.jpg"):
            try:
                os.remove(old_img)
            except OSError:
                pass

        # 1. PDFコピー
        file_name = f"registry_{uuid.uuid4().hex[:8]}.pdf"
        dest_pdf_path = save_dir / file_name
        shutil.copy2(src_pdf_path, dest_pdf_path)

        # Popplerパスを取得
        poppler_path = pdf_service.get_poppler_path()
        first_page_image_path = None

        # 2. 画像変換 (全ページ)
        try:
            # dpi=200で変換
            images = convert_from_path(
                str(dest_pdf_path), 
                dpi=200,
                poppler_path=poppler_path
            )
            
            if not images:
                print("Warning: PDF conversion returned no images.")
                return False

            for i, image in enumerate(images):
                # ページ番号は1から開始
                page_num = i + 1
                img_name = f"registry_page_{page_num}.jpg"
                dest_img_path = save_dir / img_name
                
                # JPEG保存
                image.save(str(dest_img_path), "JPEG")
                
                # 1ページ目のパスを保持
                if page_num == 1:
                    first_page_image_path = str(dest_img_path)

        except Exception as e:
            print(f"PDF Conversion Error: {e}")
            # 画像変換に失敗してもPDF自体は保存されているため、処理自体は継続するか検討
            # ここでは失敗として扱う
            return False

        # 3. DB更新
        asset.registry_pdf_path = str(dest_pdf_path)
        if first_page_image_path and os.path.exists(first_page_image_path):
            asset.registry_image_path = first_page_image_path

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