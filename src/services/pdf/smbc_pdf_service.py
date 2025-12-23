# src/services/pdf/smbc_pdf_service.py
import os
import jaconv
import mojimoji
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# 設定ファイルからパス設定を読み込む
from src.config import settings

# PDF作成ユーティリティ
from src.utils.pdf_create import PdfCreate

# サービス
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
    """
    保存先ディレクトリパスを解決する。
    「残証申請書類」フォルダがあればそこを優先し、なければ案件フォルダ直下（またはデフォルト）を返す。
    """
    
    # 契約者氏名（スペースなし）
    contractor_name_clean = contractor_name.replace(" ", "").replace("　", "")
    
    base_directory = ""

    # 1. 基本となるパス（案件フォルダ）の特定
    if os.name == "nt":
        # Windows環境
        # DBからパスを取得
        db_path = get_case_folder_path_service(case_id)
        if db_path:
            base_directory = db_path
        else:
            # フォールバックパス
            base_directory = os.path.join(settings.BASE_DIR, "output")
            print(f"DBパス未取得のためフォールバック使用: {base_directory}")

    else:
        # POSIX環境 (Mac/Linux/Dockerなど)
        base_directory = os.path.join(settings.BASE_DIR, "output")
    
    # 2. 「残証申請書類」フォルダの探索ロジック
    target_keyword = "残証申請書類"
    final_output_dir = base_directory

    if base_directory and os.path.exists(base_directory):
        try:
            p = Path(base_directory)
            # 再帰的にディレクトリを検索
            matches = [d for d in p.rglob(f"*{target_keyword}*") if d.is_dir()]
            
            if matches:
                # 見つかった場合、最終更新日時が最も新しいものを採用
                best_match = max(matches, key=lambda d: d.stat().st_mtime)
                final_output_dir = str(best_match)
                print(f"フォルダ自動振り分け: {final_output_dir}")
            else:
                print(f"'{target_keyword}' フォルダが見つからないため、ルートに保存します。")
        except Exception as e:
            print(f"フォルダ探索中にエラーが発生しました: {e}")
            # エラー時はフォールバックとしてbase_directoryをそのまま使用

    # ディレクトリ作成（念のため）
    os.makedirs(final_output_dir, exist_ok=True)
    return final_output_dir


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
    filename = f"{case_number}{d_name}様_{bank_name}_残高証明書依頼書.pdf"
    output_path = os.path.join(output_directory, filename)
    
    # テンプレートパスの解決: assets/pdf/三井住友銀行_残高証明書依頼書.pdf
    template_path = settings.ASSETS_DIR / "pdf" / "三井住友銀行_残高証明書依頼書.pdf"

    if not template_path.exists():
        raise FileNotFoundError(f"テンプレートファイルが見つかりません: {template_path}")

    pdf.pdf_save(
        output_path,
        str(template_path),
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
    filename = f"{case_number}{d_name}様_{bank_name}_残高証明書依頼書_郵送専用.pdf"
    output_path = os.path.join(output_directory, filename)

    # テンプレートパス
    template_path = settings.ASSETS_DIR / "pdf" / "三井住友銀行_残高証明書依頼書_郵送専用.pdf"

    if not template_path.exists():
        raise FileNotFoundError(f"テンプレートファイルが見つかりません: {template_path}")

    pdf.pdf_save(
        output_path,
        str(template_path),
        page=1,
        open_bool=True,
    )
    
    return output_path