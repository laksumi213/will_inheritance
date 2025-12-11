# tools/generate_pdf_test.py
import os
import sys

# プロジェクトルートをパスに追加して src モジュールを読み込めるようにする
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.utils.pdf_writer import PdfFormWriter

# ==========================================
# 設定エリア
# ==========================================
# 1. 読み込むPDFのパス (ツールで開いたものと同じパス)
INPUT_PDF_PATH = r"/Users/laksumi/will_inheritance/assets/pdf/auじぶん銀行_相続届.pdf"

# 2. 出力するPDFのパス (デスクトップやoutputフォルダなど)
OUTPUT_PDF_PATH = r"/Users/laksumi/will_inheritance/output/output_test.pdf"


# ==========================================
# 実行処理
# ==========================================
def main():
    if not os.path.exists(INPUT_PDF_PATH):
        print(f"エラー: 入力ファイルが見つかりません: {INPUT_PDF_PATH}")
        return

    print(f"読み込み中: {INPUT_PDF_PATH}")

    # PdfFormWriterを使ってPDFを開く
    # フォントは src/utils/pdf_writer.py のロジックで自動解決されます
    with PdfFormWriter(INPUT_PDF_PATH, OUTPUT_PDF_PATH) as writer:
        print("書き込み処理を開始します...")

        # ---------------------------------------------------------
        # 👇 ここにツールからコピーしたコードを貼り付けてください
        # ---------------------------------------------------------

        # ---------------------------------------------------------
        # 👆 貼り付けここまで
        # ---------------------------------------------------------

        # 保存（withブロックを抜ける時に自動でcloseされますが、明示的にsaveを呼ぶ設計の場合）
        writer.save()

    print(f"✅ 生成完了: {OUTPUT_PDF_PATH}")

    # Windowsなら自動で開く
    if os.name == "nt":
        os.startfile(OUTPUT_PDF_PATH)
    elif os.name == "posix":
        import subprocess

        subprocess.call(["open", OUTPUT_PDF_PATH])


if __name__ == "__main__":
    main()
