import sys
from dotenv import load_dotenv, find_dotenv

def check():
    # .envファイルを探す
    dotenv_path = find_dotenv(usecwd=True)
    if not dotenv_path:
        print("エラー: .envファイルが見つかりません")
        return False
    else:
        print(f"成功: .envファイルが見つかりました: {dotenv_path}")

    # .envファイルを読み込む
    success = load_dotenv(dotenv_path)
    
    if success:
        print(f"成功: .envファイルが正常に読み込まれました")
        return True
    else:
        print("失敗: .envファイルの読み込みに失敗しました")
        return False

if __name__ == "__main__":
    if check():
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # エラー