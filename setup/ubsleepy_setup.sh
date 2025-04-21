#!/bin/bash

echo "このスクリプトは以下のコマンドで実行できます"
echo "  sudo bash ubsleepy_setup.sh"
echo "このスクリプトを中断する場合はCtrl+Cを押してください"

echo "[権限の確認]"
if [ "$EUID" -ne 0 ]; then
	echo "sudoで実行されていません"
	echo "このスクリプトをsudoで実行していない場合, 正常に進行しない可能性があります"
else
	echo "sudo で実行されています"
fi

echo "[オペレーティングシステムの確認]"
if [ `uname` = "Linux" ]; then
    echo "Linux が検出されました"
else 
	echo "Linux 以外のOSが検出されました"
	echo "スクリプトが正常に進行しない可能性があります"
fi
echo ""


echo "[apt のインストールを確認]"
if command -v apt &> /dev/null; then
	echo "apt が検出されました"
elif command -v apt-get &> /dev/null; then
	echo "apt-get が検出されました"
else
	echo "apt または apt-get が見つかりません"
	echo "このスクリプトはその他のパッケージ管理システムに対応していません"
	echo "スクリプトを終了します..."
	exit 1
fi
echo ""


echo "[Docker のインストールを確認]"
if ! command -v docker &> /dev/null
then
	echo "Docker がインストールされていません"
	echo "Docker をお使いの端末にインストールしますか？(y/n)"
	read -r answer
	if [[ $answer == "y" || $answer == "Y" ]]; then
		echo "Docker をインストールしています..."
		sudo apt-get update
		sudo apt-get install -y docker.io
		echo "Docker のインストールが完了しました"\

		echo "Docker を起動しています..."
		sudo systemctl start docker
		echo "Docker の自動起動を設定しています..."
		sudo systemctl enable docker
	else
		echo "Docker を手動でインストールしてください"
		exit 1
	fi
else
	echo "Docker インストール済"
fi
echo ""

echo "[Docker プロジェクトを作成]"
echo "Docker プロジェクトディレクトリを作成します"
mkdir -p /home/$SUDO_USER/docker_project_ubsleepy/
echo "docker_project_ubsleepy 作業ディレクトリを作成しました"
cd /home/$SUDO_USER/docker_project_ubsleepy
echo "$(pwd) に移動しました"
mkdir save
echo "docker_project_ubsleepy/save ボリュームディレクトリを作成しました"
mkdir resource
echo "docker_project_ubsleepy/resource ボリュームディレクトリを作成しました"
mkdir log
echo "docker_project_ubsleepy/log ボリュームディレクトリを作成しました"

# Dockerfileの作成
cat > Dockerfile << 'EOF'
FROM python:3.13

WORKDIR /app

# リポジトリをクローン
RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/rurutheGeek/UBSLEEPY.git ./UBSLEEPY/

# 必要なPythonパッケージをインストール
RUN pip install --no-cache-dir -r UBSLEEPY/setup/requirements.txt

# メインプログラムを実行するコマンドを設定
# CMD ["python", "UBSLEEPY/main.py"]
CMD ["/bin/bash"]
EOF
echo "Dockerfile を作成しました"

echo ""
echo "[Docker イメージのビルド]"
echo "Dockerイメージをビルドしています..."
# 同じイメージ名が存在する場合はスキップ
if docker image ls | grep -q "ubsleepy_image"; then
	echo "イメージ名: ubsleepy_image はすでに存在します"
	echo "イメージを削除しますか？(y/n)"
	read -r answer
	if [[ $answer == "y" || $answer == "Y" ]]; then
		echo "イメージを削除しています..."
		docker image rm -f ubsleepy_image
		echo "既存のイメージ: ubsleepy_image を削除しました"
		
		if ! docker build -t ubsleepy_image .; then
			echo "Dockerイメージのビルドに失敗しました。"
			exit 1
		else
			echo "イメージ: ubsleepy_imageが正常にビルドされました"
		fi
	else
		echo "イメージを削除せずに続行します"
	fi
elif ! docker build -t ubsleepy_image .; then
	echo "Dockerイメージのビルドに失敗しました。"
	exit 1
else
	echo "イメージ: ubsleepy_imageが正常にビルドされました"
fi

echo ""
echo "[Docker コンテナの作成]"
echo "ubsleepy コンテナを作成しています..."

# コンテナ名がすでに存在する場合は削除
if docker ps -a --format '{{.Names}}' | grep -q "ubsleepy"; then
	echo "コンテナ: ubsleepy はすでに存在します"
	echo "コンテナを削除しますか？(y/n)"
	read -r answer
	if [[ $answer == "y" || $answer == "Y" ]]; then
		echo "コンテナを削除しています..."
		docker rm -f ubsleepy
		echo "既存のコンテナ: ubsleepy を削除しました"
	else
		echo "コンテナを削除せずに続行します"
	fi
fi

# コンテナを作成
if ! docker run -d \
  -v $(pwd)/log:/app/UBSLEEPY/log \
  -v $(pwd)/resource:/app/UBSLEEPY/resource \
  -v $(pwd)/save:/app/UBSLEEPY/save \
  --name ubsleepy ubsleepy_image \
  tail -f /dev/null; then
    echo "コンテナの作成に失敗しました。"
else
    echo "コンテナ: ubsleepy を作成しました"
fi


echo ""
echo "[UBSLEEPY 環境のセットアップ]"
echo "コンテナ内に .env または環境変数にBOTトークンを設定しないと, BOTが起動しません"
echo "BOTトークンはDiscord Developer Portal (https://discord.com/developers/applications/) から発行できます"
echo "トークンを入力し, コンテナ内に .env ファイルを作成しますか？(y/n)"
read -r answer
if [[ $answer == "y" || $answer == "Y" ]]; then
	echo "コンテナ内に .env ファイルを作成します"
	echo "DISCORD_TOKEN を入力してください: "
	read token
	docker exec ubsleepy bash -c "echo \"DISCORD_TOKEN=${token}\" > /app/.env"
	echo ".env ファイルを作成しました"
	docker exec -it ubsleepy cat /app/.env
else
	echo ".env ファイルは作成されませんでした"
fi

#echo ""
#echo "resource ディレクトリにGoogle Driveからソースファイルをダウンロードしますか？(y/n)"
#read -r answer
#if [[ $answer == "y" || $answer == "Y" ]]; then
#	echo "Google Driveからソースファイルをダウンロードしています..."
#	# Google DriveのファイルIDを指定
#	echo "ダウンロードが完了しました"
#	docker exec -it ubsleepy bash -c 'cd /app/UBSLEEPY/resource && unzip source.zip'
#	echo "source.zip を解凍しました"
#else
#	echo "Google Driveからのダウンロードはスキップされました"
#fi


# Dockerコンテナの使用方法の説明
echo ""
echo "[Docker コマンド説明]"
echo "Docker のコマンドについての説明を聞きますか？(y/n)"
read -r answer
if [[ $answer == "y" || $answer == "Y" ]]; then
	echo "以下のコマンドでコンテナを作成できる:"
	echo "  docker run -d -v $(pwd)/save --name コンテナ名 ubsleepy_image"
	echo ""
	echo "以下のコマンドでコンテナを起動できる:"
	echo "以下のコマンドでコンテナのプロンプトを表示できる:"
	echo "  docker exec -it コンテナ名 /bin/bash"
	echo ""
	echo "起動中のコンテナを確認するには以下のコマンドを実行する:"
	echo "  docker ps"
	echo "停止中のコンテナも確認するにはオプション -a を追加する:"
	echo "  docker ps -a"
	echo ""
	echo "作成したコンテナを起動するには以下のコマンドを実行する:"
	echo "  docker start コンテナ名"
	echo "作成したコンテナを削除するには以下のコマンドを実行する:"
	echo "  docker rm コンテナ名"
	echo ""
	echo "コンテナのログを確認するには以下のコマンドを実行する:"
	echo "  docker logs コンテナ名"
	echo "イメージを確認するには以下のコマンドを実行する:"
	echo "  docker image ls"
	echo "イメージを削除するには以下のコマンドを実行する:"
	echo "  docker image rm イメージ名"
	echo ""
	echo ".env ファイルの DISCORD_TOKEN の値を変更するには以下のコマンドを実行する:"
	echo "  docker exec -it ubsleepy bash -c 'echo "DISCORD_TOKEN=BOTトークン" > /app/.env'"
	echo "コンテナ内の .env ファイルを確認するには以下のコマンドを実行する:"
	echo "  docker exec -it ubsleepy cat /app/.env"
else
	echo "Docker コマンドの説明はスキップされました"
fi


echo ""
echo "[UBSLEEPY 環境ガイド]"
echo "docker_project_ubsleepy ディレクトリ内にあるsave, resource, log ディレクトリはコンテナと共有されています"
echo ""