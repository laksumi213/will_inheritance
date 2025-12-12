# tools/generate_pdf_test.py
import os
import sys

# プロジェクトルートをパスに追加して src モジュールを読み込めるようにする
# (toolsフォルダの親ディレクトリをルートとする)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.append(PROJECT_ROOT)

from src.utils.pdf_writer import PdfFormWriter

# ==========================================
# 設定エリア
# ==========================================

# 1. 読み込むPDFのパス
# Windowsパスのバックスラッシュに注意 (rをつけるか、\\にする)
INPUT_PDF_PATH = r"C:\Users\Gy488chester-PC\will_inheritance\assets\pdf\auじぶん銀行_相続届.pdf"

# 2. 出力するPDFのパス
# 実行環境に依存しないよう、プロジェクトルート直下の 'output' フォルダを自動指定します
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
OUTPUT_PDF_PATH = os.path.join(OUTPUT_DIR, "output_test.pdf")

# ==========================================
# 実行処理
# ==========================================
def main():
    # 入力チェック
    if not os.path.exists(INPUT_PDF_PATH):
        print(f"❌ エラー: 入力ファイルが見つかりません: {INPUT_PDF_PATH}")
        print("パスが正しいか、ファイル名が合っているか確認してください。")
        return

    # 出力ディレクトリが存在しない場合は作成する (これがないとSave Errorになります)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📁 出力フォルダを作成しました: {OUTPUT_DIR}")

    print(f"📖 読み込み中: {INPUT_PDF_PATH}")

    try:
        # PdfFormWriterを使ってPDFを開く
        with PdfFormWriter(INPUT_PDF_PATH, OUTPUT_PDF_PATH) as writer:
            print("✍️ 書き込み処理を開始します...")

            # ---------------------------------------------------------
            # 👇 ここにツールからコピーしたコードを貼り付けてください
            # ---------------------------------------------------------

            # Target PDF: auじぶん銀行_相続届.pdf
            # --- PDF描画コード ---
            writer.draw_text(page=1, x=524, y=502, ref_width=2339, text="テスト太郎", font_size=14)
            writer.draw_text(page=1, x=503, y=453, ref_width=2339, text="2025-01-01", font_size=14)
            # -------------------

            # ---------------------------------------------------------
            # 👆 貼り付けここまで
            # ---------------------------------------------------------

            # 保存
            writer.save()

        print(f"✅ 生成完了: {OUTPUT_PDF_PATH}")

        # Windowsなら自動で開く
        if os.path.exists(OUTPUT_PDF_PATH):
            if os.name == "nt":
                os.startfile(OUTPUT_PDF_PATH)
            elif os.name == "posix":
                import subprocess
                subprocess.call(["open", OUTPUT_PDF_PATH])
        else:
            print("⚠️ ファイルは生成されましたが、パスが見つかりません。")

    except Exception as e:
        print(f"❌ 予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()