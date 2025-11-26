# test_task_crud.py
from services.deceased_service import (
    delete_task,
    get_all_tasks_for_case,
    save_task,
    toggle_task_completion,
)

# テスト用のダミー案件ID (DBに存在するIDを指定してください)
CASE_ID = 1

print("--- 1. 新規タスク作成 ---")
save_task(CASE_ID, None, "戸籍謄本の収集", "2025-12-31", None, False)
save_task(CASE_ID, None, "銀行への連絡", "2025-11-30", None, False)

print("\n--- 2. タスク一覧取得 ---")
tasks = get_all_tasks_for_case(CASE_ID)
for t in tasks:
    print(t)

if tasks:
    target_task_id = tasks[0]["task_id"]

    print(f"\n--- 3. タスク更新 (ID: {target_task_id}) ---")
    save_task(CASE_ID, target_task_id, "戸籍謄本の収集 (至急)", "2025-12-01", None, False)

    print("\n--- 4. 完了状態の切り替え ---")
    toggle_task_completion(target_task_id, True)

    print("\n--- 5. 削除 ---")
    delete_task(target_task_id)

print("\n--- 最終確認 ---")
final_tasks = get_all_tasks_for_case(CASE_ID)
print(f"残りのタスク数: {len(final_tasks)}")
