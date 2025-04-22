
---

# UBSLEEPY

このプロジェクトは、2023年から工学院ポケモンだいすきクラブのサークル活動のため開発されている PythonベースのDiscord Botのリポジトリです。以下の手順を参考にセットアップを行い、プロジェクトを実行してください。

---

## セットアップ手順

### 1. リポジトリをクローンする
以下のコマンドを使用してリポジトリをローカル環境にクローンします：
```bash
git clone https://github.com/rurutheGeek/UBSLEEPY.git
```
Gitをまだインストールしていない場合は、以下の手順に従ってインストールしてください。

#### Windows
1. [Git for Windows](https://gitforwindows.org/)の公式サイトにアクセスします。
2. ダウンロードボタンをクリックして、インストーラーをダウンロードします。
3. ダウンロードしたインストーラーを実行し、画面の指示に従ってインストールを完了します。
   - 基本的にはデフォルト設定のままで問題ありません。
   - インストール完了後、「Git Bash」または「コマンドプロンプト」から`git --version`コマンドを実行して、正常にインストールされたか確認できます。

#### macOS
1. **Homebrew**を使用する場合:
   ```bash
   brew install git
   ```
2. **インストーラー**を使用する場合:
   - [Git公式サイト](https://git-scm.com/download/mac)からインストーラーをダウンロードして実行します。
3. インストール完了後、ターミナルで`git --version`コマンドを実行して確認します。

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install git
```

### 2. 必要なパッケージをインストールする
- 仮想環境（例: `venv`）の利用を推奨します。

```bash
pip install -r UBSLEEPY/setup/requirements.txt
```

### 3. リソースファイルの配置
- resource ディレクトリに以下のファイルを配置してください：
  - 必須: `pokemon_database.csv`
  - オプション: `pokemon_senryu.csv` や `pokemon_calendar.csv`（必要に応じて配置）。

### 4. Botを起動する
以下のコマンドから選択して、Botを起動します：

#### Linux/macOS
```bash
python main.py
```

#### Windows（Python Launcherを使用）
```bash
py main.py
```

---

## ディレクトリ構成

以下はプロジェクト内の主なディレクトリの説明です：

- **`bot_module`**  
  `main.py` 内で呼び出す自作モジュールを格納します。

- **`resource`**  
  ポケモン図鑑（例: `pokemon_database.csv`）やBotで使用する画像ファイルを格納します。

- **`document`**  
  Botが投稿する文章が記載されたテキストファイルを格納します。

- **`save`**  
  ユーザーデータや一時保存ファイル（キャッシュ）を格納します（共有対象外）。

- **`log`**  
  ログファイルを格納します（共有対象外）。

- **`setup`**  
  使用パッケージの一覧である requirements.txt や Dockerを利用したセットアップ用ファイルなど 起動のためのファイル格納します。

- **`temp`**  
  開発中に作成したが共有しないファイルを格納します（共有対象外）。

---

## 動作環境

- **Python バージョン**: 3.9以上を推奨。
- 必要なパッケージは `requirements.txt` に記載されています。

---

## 使用方法

Botの具体的なコマンドや使い方については、ドキュメントやコード内のコメントを参照してください。

---

## 貢献

このプロジェクトへの貢献は歓迎されています！  
バグ報告や新機能の提案など、[Issues](https://github.com/rurutheGeek/UBSLEEPY/issues) や [Pull Requests](https://github.com/rurutheGeek/UBSLEEPY/pulls) を通じてご参加ください。

---

## ライセンス

このプロジェクトのライセンスは、**GNU General Public License (GPL v3)** に準拠しています。リポジトリ内の `LICENSE` ファイルを参照してください。

---
