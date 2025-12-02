# check_db.py (一時的に作成して実行するファイル)

from services.deceased_service import get_address_info, get_all_heirs


def check_heir_data():
    heirs_list = get_all_heirs()

    if not heirs_list:
        print("🔍 現在、登録されている相続人はいません。")
        return

    #     print("--- 👨‍👩‍👧‍👦 データベース上の全相続人リスト ---")
    for heir in heirs_list:
        # 被相続人情報に安全にアクセス
        deceased = heir.deceased

        deceased_name_full = "N/A"
        deceased_kana_full = "N/A"
        deceased_dob_str = "N/A"
        deceased_dod_str = "N/A"
        case_number = "N/A"

        if deceased:
            deceased_name_full = (
                f"{deceased.name_last or ''} {deceased.name_first or ''}".strip()
            )
            deceased_kana_full = (
                f"{deceased.name_last_kana or ''} {deceased.name_first_kana or ''}".strip()
                or "未登録"
            )
            deceased_dob_str = (
                str(deceased.date_of_birth) if deceased.date_of_birth else "未登録"
            )
            deceased_dod_str = (
                str(deceased.date_of_death) if deceased.date_of_death else "未登録"
            )

            if deceased.case:
                case_number = deceased.case.case_number

        # 住所情報も確認したい場合は、get_address_info を使って個別に取得
        address_info = get_address_info("heir", heir.id)
        address_str = f"{address_info.get('prefecture', '')}{address_info.get('city_ward_town', '')}{address_info.get('street_address', '')} {address_info.get('building_name', '')}".strip()
        if not address_str:
            address_str = "未登録"

        print(f"ID: {heir.id} (案件: {case_number})")
        print(
            f"  相続人: {heir.name_last} {heir.name_first} / 続柄: {heir.relationship_type} / 契約者: {'✅' if heir.is_contracting_party else '❌'}"
        )
        print(f"  現住所: {address_str}")
        print("----- 👤 紐づく被相続人情報 -----")
        print(f"  被相続人ID: {heir.deceased_id}")
        print(f"  被相続人: {deceased_name_full}")
        print(f"  ふりがな: {deceased_kana_full}")
        print(f"  生年月日: {deceased_dob_str}")
        print(f"  死亡日: {deceased_dod_str}")
        print(f"  本籍地: {deceased.hometown or '未登録'}")
        print("---------------------------------")

        # # 💡 追加: 住所情報を取得
        # address_info = get_address_info("heir", heir.id)
        # address_str = f"{address_info.get('prefecture', '')}{address_info.get('city_ward_town', '')}{address_info.get('street_address', '')} {address_info.get('building_name', '')}".strip()
        # if not address_str:
        #     address_str = "未登録"

        # print(f"ID: {heir.id}")
        # print(f"  名前: {heir.name_last} {heir.name_first}")
        # print(f"  続柄: {heir.relationship_type}")
        # print(f"  契約者フラグ: {'✅' if heir.is_contracting_party else '❌'}")
        # print(f"  被相続人ID: {heir.deceased_id} (被相続人: {deceased_name})")
        # print(f"  案件番号: {case_number}")
        # print(f"  現住所: {address_str}")  # 💡 住所を出力
        # print("---------------------------------")


if __name__ == "__main__":
    check_heir_data()
