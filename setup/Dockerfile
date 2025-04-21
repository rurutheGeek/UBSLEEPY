FROM python:3.13

WORKDIR /app

# リポジトリをクローン
RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/rurutheGeek/UBSLEEPY.git ./UBSLEEPY/

# 必要なPythonパッケージをインストール
RUN pip install --no-cache-dir -r UBSLEEPY/requirements.txt

# メインプログラムを実行するコマンドを設定
# CMD ["python", "UBSLEEPY/main.py"]
CMD ["/bin/bash"]