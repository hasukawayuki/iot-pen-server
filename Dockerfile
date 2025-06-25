# ベースとなるPythonイメージを指定
FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /code

# 環境変数としてデータファイルのデフォルトパスを設定
# この値は `docker run` コマンドの `-e` オプションで上書き可能
ENV DATA_FILE_PATH=/code/data/pen_data.json

# 依存ライブラリの定義ファイルをコンテナにコピー
COPY ./requirements.txt /code/requirements.txt

# 依存ライブラリをインストール
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# アプリケーションコードをコンテナにコピー
COPY ./app /code/app

# (任意) データファイルをコンテナ内にコピーする場合
COPY ./data /code/data

# コンテナがリッスンするポートを指定
EXPOSE 80

# コンテナ起動時に実行するコマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]