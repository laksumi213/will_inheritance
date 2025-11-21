from google import genai
from google.genai.errors import APIError
import os
import pathlib
import shutil  # ファイルのコピー/移動に使用

try:
    # 1. クライアントの初期化
    # APIキーが環境変数に設定されていれば、引数なしでOK
    client = genai.Client()

except Exception as e:
    print("エラー: Gemini APIキーが正しく設定されていません。")
    print(f"詳細: {e}")
    # プログラムを終了
    exit()

# 処理するファイル名
ORIGINAL_FILE_PATH = r"C:\Users\Gy488chester-PC\souzoku\G2203【飯野紀一様】横浜市青葉区すみよし台９－３３不動産登記（土地全部事項）2025110500538755.PDF"

# コピー先の安全なファイル名 (英数字のみ)
TEMP_FILE_NAME = "temp_upload_file.pdf"

# 実行ディレクトリのパス
CURRENT_DIR = pathlib.Path(__file__).parent
TEMP_FILE_PATH = CURRENT_DIR / TEMP_FILE_NAME


def upload_and_extract_info(original_path: str, temp_path: pathlib.Path, prompt: str):
    """ファイルを一時的にコピー・リネームしてアップロードし、情報抽出を行う関数"""
    uploaded_file = None

    try:
        # --- ステップ A: ファイルのコピーとリネーム ---
        print(f"元のファイル '{original_path}' を安全なパス '{temp_path}' へコピー中...")
        # shutil.copy2 はメタデータもコピーします
        shutil.copy2(original_path, temp_path)
        print("コピー完了。")

        # --- ステップ B: コピーしたファイルをアップロード ---
        # Pathオブジェクトを渡すことで、エンコーディングエラーを回避しやすい
        print(f"ファイル '{TEMP_FILE_NAME}' のアップロードを開始します...")
        uploaded_file = client.files.upload(file=temp_path)
        print(f"アップロード完了。File Name: {uploaded_file.name}")

        # --- ステップ C: AIモデルによる情報抽出 ---
        # ... (以前の generate_content 処理を続ける) ...
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[uploaded_file, prompt]
        )

        print("\n--- 抽出結果 ---")
        print(response.text)
        print("----------------\n")

    # ... (APIError やその他の例外処理) ...

    finally:
        # --- ステップ D: クリーンアップ（最重要） ---
        # 1. アップロードしたファイルをサーバーから削除
        if uploaded_file:
            print(f"アップロードされたファイルをサーバーから削除しています: {uploaded_file.name}")
            client.files.delete(name=uploaded_file.name)
            print("サーバー上のファイル削除完了。")

        # 2. 一時的に作成したローカルファイルを削除
        if temp_path.exists():
            print(f"一時ローカルファイル '{TEMP_FILE_NAME}' を削除しています...")
            os.remove(temp_path)
            print("ローカルファイル削除完了。")


if __name__ == "__main__":
    client = genai.Client()  # クライアント初期化
    PROMPT = "この不動産登記簿に記載されている土地の所在、地番、地積（面積）をMarkdown形式の表にして取り出してください。"
    upload_and_extract_info(ORIGINAL_FILE_PATH, TEMP_FILE_PATH, PROMPT)