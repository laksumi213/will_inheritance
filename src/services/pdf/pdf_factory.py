# src/services/pdf/pdf_factory.py
from typing import Optional

from src.services.pdf.banks.au_jibun import AuJibunBankService
from src.services.pdf.base_pdf_service import BaseBankPdfService

# from src.services.pdf.banks.mizuho import MizuhoBankService  # 作成したら追加


def generate_pdf_for_bank(case_id: int, bank_code: str = None, bank_name: str = "") -> str:
    """
    銀行情報に基づいて適切なServiceを選択し、PDFを生成する
    """
    service: Optional[BaseBankPdfService] = None

    # 銀行コードまたは名称でクラスを振り分け
    if bank_code == "0039" or "au" in bank_name or "じぶん" in bank_name:
        service = AuJibunBankService(case_id)

    # elif bank_code == "0001":
    #     service = MizuhoBankService(case_id)

    else:
        raise ValueError(f"対応していない銀行です: {bank_name} (Code: {bank_code})")

    if service:
        return service.execute()

    raise RuntimeError("Service initialization failed")
