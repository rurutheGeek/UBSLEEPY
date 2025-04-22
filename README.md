
---

# UBSLEEPY

このプロジェクトは, 2023年から工学院ポケモンだいすきクラブのサークル活動のため開発されている PythonベースのDiscord Botのリポジトリです. 以下の手順を参考にセットアップを行い, プロジェクトを実行してください. 

---

## セットアップ手順

このプログラムを実行するには, Pythonをインストールする必要があります. 

### Pythonインストール手順

#### 1. Pythonの公式サイトからダウンロード

1. [Python公式ダウンロードページ](https://www.python.org/downloads/)にアクセスします. 
2. 「Download Python 3.x.x」（最新バージョン）ボタンをクリックします. 
   * Python 3.9以上をインストールしてください. 

#### 2. インストーラーの実行

1. ダウンロードしたインストーラー（例：`python-3.11.0-amd64.exe`）をダブルクリックして実行します. 
2. インストール画面が表示されたら, 以下のオプションにチェックを入れてください：
   * ✅ **Add Python 3.x to PATH**
   * ✅ **Install launcher for all users (recommended)**
#### 3. インストールの確認

1. インストールが完了したら, 「**Close**」をクリックします. 
2. Windowsのスタートメニューから「**コマンドプロンプト**」または「**PowerShell**」を検索して起動します. 
3. 以下のコマンドを入力してPythonが正しくインストールされたか確認します：

```
python --version
```

または

```
py --version
```

バージョン情報（例：`Python 3.11.0`）が表示されればインストール成功です. **特定のバージョンのPythonからコマンドがpythonの代わりにpyしか使えないことがあるようです. pythonコマンドに問題がある場合, pyコマンドを試してください. **
   
- 仮想環境（例: `venv`）の利用を推奨します. 

### 仮想環境`venv` 導入手順

```bash
# プロジェクトディレクトリに移動
cd UBSLEEPY

# 仮想環境の作成
python -m venv venv

# 仮想環境を有効化する方法
venv\Scripts\activate
```
### vscodeの場合
vscodeのターミナルを利用する場合, PowerShellで実行されます. このシェルは, デフォルトではスクリプトの実行が制限されています. そのため, `venv\Scripts\Activate.ps1`スクリプトを実行しようとすると, 以下のようなエラーが発生することがあります：

```
venv\Scripts\Activate.ps1 : このシステムではスクリプトの実行が無効になっているため, ファイル venv\Scripts\Activate.ps1 を読み込むことができません. 
```

#### VSCodeのsettings.jsonに設定を追加

VSCodeの設定ファイルに追記することで, PowerShellでスクリプト実行を許可できます：

1. VSCodeの設定ファイルを開きます：
   - `Ctrl+Shift+P`を押して, コマンドパレットを開きます
   - `Preferences: Open Settings (JSON)`と入力して選択します

2. 以下の設定を`settings.json`に追加します：

```json
{
    "terminal.integrated.profiles.windows": {
        "PowerShell": {
            "source": "PowerShell",
            "icon": "terminal-powershell",
            "args": ["-ExecutionPolicy", "Bypass"]
        }
    },
    "terminal.integrated.defaultProfile.windows": "PowerShell"
}
```

### 1. リポジトリをクローンする
以下のコマンドを使用してリポジトリをローカル環境にクローンします：
```bash
git clone https://github.com/rurutheGeek/UBSLEEPY.git
```
Gitをまだインストールしていない場合は, 以下の手順に従ってインストールしてください. 

#### Windows
1. [Git for Windows](https://gitforwindows.org/)の公式サイトにアクセスします. 
2. ダウンロードボタンをクリックして, インストーラーをダウンロードします. 
3. ダウンロードしたインストーラーを実行し, 画面の指示に従ってインストールを完了します. 
   - 基本的にはデフォルト設定のままで問題ありません. 
   - インストール完了後, 「Git Bash」または「コマンドプロンプト」から`git --version`コマンドを実行して, 正常にインストールされたか確認できます. 

#### macOS
1. **Homebrew**を使用する場合:
   ```bash
   brew install git
   ```
2. **インストーラー**を使用する場合:
   - [Git公式サイト](https://git-scm.com/download/mac)からインストーラーをダウンロードして実行します. 
3. インストール完了後, ターミナルで`git --version`コマンドを実行して確認します. 

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install git
```

### 2. 必要なパッケージをインストールする

```bash
pip install --no-cache-dir -r ./setup/requirements.txt
```

### 3. リソースファイルの配置
- main.py 以上の階層に以下のファイルを配置してください：
  - 必須:  `.env`
```.env
DISCORD_TOKEN=ここにDiscordBotのトークン
```
- resource ディレクトリに以下のファイルを配置してください：
  - 必須: `pokemon_database.csv`
  - オプション: `pokemon_senryu.csv` や `pokemon_calendar.csv`（データを使用する場合は配置）. 

### 4. Botを起動する
以下のコマンドで, Botを起動します：
```bash
python main.py
```

---

## ディレクトリ構成

以下はプロジェクト内の主なディレクトリの説明です：

- **`bot_module`**  
  `main.py` 内で呼び出す自作モジュールを格納します. 

- **`resource`**  
  ポケモン図鑑（例: `pokemon_database.csv`）やBotで使用する画像ファイルを格納します. 

- **`document`**  
  Botが投稿する文章が記載されたテキストファイルを格納します. 

- **`save`**  
  ユーザーデータや一時保存ファイル（キャッシュ）を格納します（共有対象外）. 

- **`log`**  
  ログファイルを格納します（共有対象外）. 

- **`setup`**  
  使用パッケージの一覧である requirements.txt や Dockerを利用したセットアップ用ファイルなど 起動のためのファイル格納します. 

- **`temp`**  
  開発中に作成したが共有しないファイルを格納します（共有対象外）. 

---

## 動作環境

- **Python バージョン**: 3.9以上を推奨. 
- 必要なPythonパッケージは `requirements.txt` に記載されています. 

---

## 使用方法

Botの具体的なコマンドや使い方については, ドキュメントやコード内のコメントを参照してください. 

---

## 貢献

このプロジェクトへの貢献は歓迎されています.  
バグ報告や新機能の提案など, [Issues](https://github.com/rurutheGeek/UBSLEEPY/issues) や [Pull Requests](https://github.com/rurutheGeek/UBSLEEPY/pulls) を通じてご参加ください. 

---

## ライセンス

このプロジェクトのライセンスは, **GNU General Public License (GPL v3)** に準拠しています. リポジトリ内の `LICENSE` ファイルを参照してください. 

---
