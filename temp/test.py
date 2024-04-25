import json

# データの読み込み
try:
    with open("config.json", "r") as file:
        data = json.load(file)
except FileNotFoundError:
    data = {"guild_id": [], "user_id": []}

# putコマンドの処理
def put_data(cmd, identifier, text):
    if cmd == "put":
        data[identifier].append(text)
        save_data()

# pullコマンドの処理
def pull_data(cmd, identifier, text):
    if cmd == "pull":
        if text in data[identifier]:
            data[identifier].remove(text)
            save_data()
        else:
            print("存在しません")

# データをファイルに保存
def save_data():
    with open("config.json", "w") as file:
        json.dump(data, file)

# コマンド入力と処理を続けるプログラム
while True:
    command = input("コマンドを入力 (put/pull/exit): ")
    if command == "exit":
        break
    elif command == "put":
        input_str = input("put ギルドID/ユーザーID \"文字列\": ")
        parts = input_str.split()
        if len(parts) != 3:
            print("無効な入力")
            continue
        cmd, identifier, text = parts[0], parts[1], parts[2][1:-1]  # クォーテーションを除去
        put_data(cmd, identifier, text)
    elif command == "pull":
        input_str = input("pull ギルドID/ユーザーID \"文字列\": ")
        parts = input_str.split()
        if len(parts) != 3:
            print("無効な入力")
            continue
        cmd, identifier, text = parts[0], parts[1], parts[2][1:-1]  # クォーテーションを除去
        pull_data(cmd, identifier, text)
    else:
        print("無効なコマンド")
