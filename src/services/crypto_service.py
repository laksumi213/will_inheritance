# src/services/crypto_service.py
import os
import secrets
import string
from typing import List

import pyzipper


class CryptoService:
    """
    ファイルの暗号化・圧縮に関するサービス
    AES-256暗号化を用いたZIP作成機能を提供します。
    """

    @staticmethod
    def generate_strong_password(length: int = 12) -> str:
        """
        ランダムで強力なパスワードを生成する

        Args:
            length (int): パスワードの長さ

        Returns:
            str: 生成されたパスワード
        """
        # 英字(大小)、数字、記号を含む
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(chars) for _ in range(length))

    @staticmethod
    def create_encrypted_zip(source_files: List[str], output_path: str, password: str) -> bool:
        """
        指定されたファイルをAES-256で暗号化してZIP圧縮する

        Args:
            source_files (List[str]): 圧縮するファイルのパスリスト
            output_path (str): 出力先ZIPファイルのパス
            password (str): 解凍用パスワード

        Returns:
            bool: 成功すればTrue
        """
        try:
            # 出力先ディレクトリがない場合は作成
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # pyzipperを使用してAES暗号化ZIPを作成
            with pyzipper.AESZipFile(
                output_path,
                "w",
                compression=pyzipper.ZIP_LZMA,  # 高圧縮率
                encryption=pyzipper.WZ_AES,
            ) as zf:
                zf.setpassword(password.encode("utf-8"))

                for file_path in source_files:
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        # アーカイブ内のファイル名は、パスを含まないファイル名のみとする
                        arcname = os.path.basename(file_path)
                        zf.write(file_path, arcname=arcname)
                    else:
                        print(f"Warning: File not found or invalid: {file_path}")

            return True
        except Exception as e:
            print(f"Encryption Error: {e}")
            raise e


# シングルトンとして利用
crypto_service = CryptoService()
