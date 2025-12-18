# src/services/real_estate_service.py
import shutil
import uuid
import os
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# pdf2imageライブラリを使用
from pdf2image import convert_from_path

from src.models.database import SessionLocal
from src.models.tables import Case, RealEstateAsset

# ロガー設定
logger = logging.getLogger(__name__)

def get_real_estates_by_case(case_id: int) -> List[RealEstateAsset]:
    """案件に紐づく不動産リストを取得"""
    db = SessionLocal()
    try:
        return db.query(RealEstateAsset).filter(RealEstateAsset.case_id == case_id).all()
    finally:
        db.close()

def _find_target_nayose_folder(base_path: str) -> Path:
    """
    案件フォルダ内から「名寄帳」という名前を含むフォルダを再帰的に検索する。
    複数見つかった場合は、最終更新日時（mtime）が最も新しいものを返す。
    見つからない場合は、案件直下に「名寄帳」フォルダを新規作成して返す。
    """
    base_dir = Path(base_path)
    if not base_dir.exists():
        os.makedirs(base_dir, exist_ok=True)

    # 「名寄帳」を含むディレクトリを再帰的に検索
    matches = [d for d in base_dir.rglob("*名寄帳*") if d.is_dir()]

    if not matches:
        # 見つからない場合は標準の「名寄帳」フォルダを作成
        new_path = base_dir / "名寄帳"
        new_path.mkdir(parents=True, exist_ok=True)
        return new_path

    if len(matches) == 1:
        return matches[0]

    # 複数見つかった場合：最終更新日時が最新のものを選択
    logger.info(f"複数の名寄帳フォルダを検出。最新を選択: {len(matches)}件")
    return max(matches, key=lambda d: d.stat().st_mtime)

def save_registry_document(case_id: int, real_estate_id: int, src_pdf_path: str) -> bool:
    """
    1. 案件フォルダ内の「名寄帳」フォルダを自動特定
    2. PDFを特定フォルダ内の properties/{asset_id}/ へ保存
    3. 全ページを画像変換して保存
    4. DBにパスを記録
    """
    # 循環インポート回避のため関数内でインポート
    from src.services.pdf_service import pdf_service
    
    db = SessionLocal()
    try:
        case = db.query(Case).get(case_id)
        asset = db.query(RealEstateAsset).get(real_estate_id)

        if not case or not asset:
            raise ValueError("案件データまたは不動産データが見つかりません")

        # 案件のベースフォルダを取得
        case_folder = case.folder_path if case.folder_path else "output"
        
        # 「名寄帳」キーワードを含むフォルダを自動探索
        nayose_root = _find_target_nayose_folder(case_folder)
        
        # 保存先: {特定された名寄帳フォルダ}/properties/{asset_id}/
        save_dir = nayose_root / "properties" / str(real_estate_id)
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
            images = convert_from_path(
                str(dest_pdf_path), 
                dpi=200,
                poppler_path=poppler_path
            )
            
            if not images:
                logger.warning("PDF conversion returned no images.")
                return False

            for i, image in enumerate(images):
                page_num = i + 1
                img_name = f"registry_page_{page_num}.jpg"
                dest_img_path = save_dir / img_name
                image.save(str(dest_img_path), "JPEG")
                
                if page_num == 1:
                    first_page_image_path = str(dest_img_path)

        except Exception as e:
            logger.error(f"PDF Conversion Error: {e}")
            return False

        # 3. DB更新
        asset.registry_pdf_path = str(dest_pdf_path)
        if first_page_image_path and os.path.exists(first_page_image_path):
            asset.registry_image_path = first_page_image_path

        db.commit()
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error saving registry doc: {e}")
        return False
    finally:
        db.close()

def add_real_estate(case_id: int, property_type: str, location: str, **kwargs) -> Optional[RealEstateAsset]:
    """不動産情報の新規追加"""
    db = SessionLocal()
    try:
        asset = RealEstateAsset(
            case_id=case_id,
            property_type=property_type,
            location=location,
            ownership_share=kwargs.get("ownership_share"),
            lot_number=kwargs.get("lot_number"),
            land_category=kwargs.get("land_category"),
            land_area=kwargs.get("land_area"),
            house_number=kwargs.get("house_number"),
            structure=kwargs.get("structure"),
            floor_area=kwargs.get("floor_area"),
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset
    except Exception as e:
        db.rollback()
        logger.error(f"Add RealEstate Error: {e}")
        return None
    finally:
        db.close()

def update_real_estate(asset_id: int, **kwargs) -> bool:
    """不動産情報の更新"""
    db = SessionLocal()
    try:
        asset = db.query(RealEstateAsset).get(asset_id)
        if not asset: return False
        for key, value in kwargs.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Update RealEstate Error: {e}")
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

def get_real_estate_image(asset_id: int) -> Optional[str]:
    """登記画像のパスを取得"""
    db = SessionLocal()
    try:
        asset = db.query(RealEstateAsset).get(asset_id)
        return asset.registry_image_path if asset else None
    finally:
        db.close()