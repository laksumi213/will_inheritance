# src/services/pdf/smbc_pdf_service.py
import os
import jaconv
import mojimoji
from datetime import datetime
from typing import Dict, Any, Optional

# 💡 修正: インポートパスを新しいディレクトリ構成 (src.utils) に変更
from src.utils.pdf_create import PdfCreate

# services は src の中
from src.services.deceased_service import get_case_folder_path_service


def generate_smbc_balance_certificate(
    data: Dict[str, Any], 
    bank_code: str, 
    case_id: int, 
    is_mailing: bool = False
) -> str:
    """
    三井住友銀行の残高証明書発行依頼書PDFを作成するメイン関数
    """
    if is_mailing:
        return _create_mailing_pdf(data, bank_code, case_id)
    else:
        return _create_window_pdf(data, bank_code, case_id)


def _get_output_directory(case_id: int, case_number: str, contractor_name: str) -> str:
    """保存先ディレクトリパスを解決する"""
    
    # 契約者氏名（スペースなし）
    contractor_name_clean = contractor_name.replace(" ", "").replace("　", "")
    
    output_directory = ""

    if os.name == "nt":
        # Windows環境
        # DBからパスを取得
        db_path = get_case_folder_path_service(case_id)
        if db_path:
            output_directory = db_path
        else:
            # フォールバックパス
            output_directory = rf"\\192.168.11.20\行政書士法人チェスター\01.個別ＪＯＢ\{case_number}{contractor_name_clean}"
            print(f"DBパス未取得のためフォールバック使用: {output_directory}")

    else:
        # POSIX環境 (Mac/Linux/Dockerなど) - 開発用
        # src/services/pdf/smbc_pdf_service.py から見てプロジェクトルートを探す
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        output_directory = os.path.join(base_dir, "generated_pdfs")
        os.makedirs(output_directory, exist_ok=True)
    
    return output_directory


def _create_window_pdf(data: Dict[str, Any], bank_code: str, case_id: int) -> str:
    """窓口用PDFを作成"""
    # --- データ展開 ---
    case_number = data["case_number"]
    deceased = data["deceased"]
    d_name = f"{deceased['last_name']} {deceased['first_name']}"
    d_death_date = deceased.get("date_of_death")

    contractor = data["contracting_party"]
    c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}"

    # 銀行情報
    bank_assets = data.get("bank_assets", [])
    bank_name = bank_assets[0]["bank_name"] if bank_assets else ""
    branch_name = bank_assets[0]["branch_name"] if bank_assets else ""
    branch_code = bank_assets[0].get("branch_code", "") if bank_assets else ""
    account_type = bank_assets[0]["account_type"] if bank_assets else ""
    account_number = bank_assets[0]["account_number"] if bank_assets else ""

    # 出力先取得
    output_directory = _get_output_directory(case_id, case_number, c_name)

    # PDF生成開始
    pdf = PdfCreate("A4")

    # 名前描画
    pdf.draw_string(62, 264, d_name)
    pdf.draw_string(62, 257, c_name)

    # 電話番号
    pdf.draw_string(125, 254, "050-6864-7034", 12)

    # 支店情報
    pdf.draw_string(50, 233, branch_name, 12)
    
    # 支店コード (3桁想定)
    if branch_code and len(branch_code) >= 3:
        pdf.draw_string(88, 233, branch_code[0], 12)
        pdf.draw_string(92.5, 233, branch_code[1], 12)
        pdf.draw_string(97, 233, branch_code[2], 12)

    # 口座種別
    if '普通' in account_type:
        pdf.draw_string(101.5, 232.5, '〇', 12)
    elif '当座' in account_type:
        pdf.draw_string(109, 232.5, '〇', 12)
    else:
        pdf.draw_string(118, 232.5, account_type, 8)

    # 口座番号
    if account_number:
        positions = [130, 134, 138.5, 143, 147.3, 152, 156.5]
        for i, char in enumerate(str(account_number)[:7]):
             if i < len(positions):
                pdf.draw_string(positions[i], 232, char, 12)

    pdf.draw_string(110, 189, f'担当：森町({case_number})', 10)

    # 死亡日
    if d_death_date:
        year_str = str(d_death_date.year)[2:] 
        year_draw = "     ".join(list(year_str))
        pdf.draw_string(63, 142, year_draw, 12)

        month_str = str(d_death_date.month).zfill(2)
        month_draw = "     ".join(list(month_str))
        pdf.draw_string(85, 142, month_draw, 12)

        day_str = str(d_death_date.day).zfill(2)
        day_draw = "     ".join(list(day_str))
        pdf.draw_string(109, 142, day_draw, 12)

    # 保存処理
    filename = f"{case_number}_{d_name}_{bank_name}_残高証明書依頼書.pdf"
    output_path = os.path.join(output_directory, filename)
    
    # テンプレートパスの解決: assets/pdf/三井住友銀行_残高証明書依頼書.pdf
    # src/services/pdf/smbc_pdf_service.py -> ../../../assets
    base_src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(
        base_src_dir,
        "assets", "pdf", "三井住友銀行_残高証明書依頼書.pdf"
    )

    pdf.pdf_save(
        output_path,
        template_path,
        page=1,
        open_bool=True,
    )
    
    return output_path


def _create_mailing_pdf(data: Dict[str, Any], bank_code: str, case_id: int) -> str:
    """郵送用PDFを作成"""
    # --- データ展開 ---
    case_number = data["case_number"]
    deceased = data["deceased"]
    d_name = f"{deceased['last_name']} {deceased['first_name']}"
    d_kana = f"{deceased['last_kana']} {deceased['first_kana']}"
    
    contractor = data["contracting_party"]
    c_name = f"{contractor.get('last_name', '')} {contractor.get('first_name', '')}"
    c_kana = f"{contractor.get('last_kana', '')} {contractor.get('first_kana', '')}"

    bank_assets = data.get("bank_assets", [])
    bank_name = bank_assets[0]["bank_name"] if bank_assets else "銀行名不明"

    # 出力先取得
    output_directory = _get_output_directory(case_id, case_number, c_name)

    pdf = PdfCreate("A4")

    # 住所など固定情報
    pdf.draw_string(52, 259, "103-0028")
    pdf.draw_string(52, 249, "東京", 12)
    pdf.draw_string(73, 251.5, "〇", 14)
    pdf.draw_string(84, 249, "東京都中央区八重洲一丁目7-20 八重洲口会館2階", 12)

    # 氏名・代理人情報
    c_kana_converted = mojimoji.zen_to_han(jaconv.hira2kata(c_kana)) if c_kana else ""
    pdf.draw_string(57, 240, f"ｿｳｿﾞｸﾆﾝ　{c_kana_converted}")
    pdf.draw_string(57, 236.5, "ﾀﾞｲﾘﾆﾝ　ｷﾞｮｳｾｲｼｮｼﾎｳｼﾞﾝﾁｪｽﾀｰ　ﾀﾞｲﾋｮｳｼｬｲﾝ　ｼﾐｽﾞ ｾﾝｻｸ")
    pdf.draw_string(57, 232, f"相続人　{c_name}")
    pdf.draw_string(57, 228, "代理人　行政書士法人チェスター　代表社員　清水　茜作")

    # 電話番号
    pdf.draw_string(54, 221, "050　　　6864　　　7034", 12)

    # 被相続人
    d_kana_converted = mojimoji.zen_to_han(jaconv.hira2kata(d_kana)) if d_kana else ""
    pdf.draw_string(57, 187, d_kana_converted)
    pdf.draw_string(57, 174, d_name, 14)
    pdf.draw_string(173, 180.5, "〇", 18)

    # 保存処理
    filename = f"{case_number}_{d_name}_{bank_name}_残高証明書依頼書_郵送専用.pdf"
    output_path = os.path.join(output_directory, filename)

    # テンプレートパス
    base_src_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    template_path = os.path.join(
        base_src_dir,
        "assets", "pdf", "三井住友銀行_残高証明書依頼書_郵送専用.pdf"
    )

    pdf.pdf_save(
        output_path,
        template_path,
        page=1,
        open_bool=True,
    )
    
    return output_path