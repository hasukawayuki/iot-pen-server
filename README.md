# IoT Pen Backend Server

## 概要

このプロジェクトは、IoTペンから送信される利用状況データ（JSON形式）を分析し、インク残量や交換時期予測などを提供するバックエンドサーバーです。
Dockerコンテナとして動作するように設計されています。

## 機能

* **インク残量の計算**: ペンの筆記時間に基づいて現在のインク残量を計算します。
* **インク枯渇予測**: 過去の利用ペースから、インクがなくなるおおよその日時を予測します。
* **交換時期の通知**: インク残量が事前に設定した閾値を下回った場合に、交換を推奨するメッセージを表示します。

## 技術スタック

* **言語**: Python 3.9
* **フレームワーク**: FastAPI
* **実行環境**: Docker

## ディレクトリ構成

```plaintext
iot-pen-server/
│
├── app/
│   └── main.py         # FastAPIアプリケーション本体
│
├── data/
│   └── pen_data.json     # IoTペンからのデータ
│
├── .env                  # (任意) 環境変数を記述するファイル
├── Dockerfile            # Dockerイメージの定義ファイル
├── requirements.txt      # Pythonの依存ライブラリ
└── README.md             # このファイル
```

## セットアップと実行方法

### 前提条件

* [Docker](https://www.docker.com/get-started) がインストールされていること。

### 手順

1.  **リポジトリのクローンまたはファイルの配置**:
    このプロジェクトのファイルを上記のディレクトリ構成通りに配置します。

2.  **データファイルの配置**:
    `data/` ディレクトリに、IoTペンから取得した `pen_data.json` を配置します。

3.  **Dockerイメージのビルド**:
    プロジェクトのルートディレクトリで以下のコマンドを実行し、Dockerイメージをビルドします。
    ```bash
    docker build -t iot-pen-server .
    ```

4.  **Dockerコンテナの実行**:
    ビルドしたイメージを元にコンテナを起動します。
    ```bash
    docker run -d -p 8000:80 --name my-pen-server iot-pen-server
    ```
    * `-d`: バックグラウンドで実行
    * `-p 8000:80`: ホストOSのポート8000をコンテナのポート80にマッピング
    * `--name my-pen-server`: コンテナに名前を付けます

    **データファイルをホストマシンからマウントする場合:**
    `data`ディレクトリをコンテナに直接マウントすることで、コンテナを再ビルドせずにデータを更新できます。
    ```bash
    # `$(pwd)` は現在のディレクトリの絶対パスに置き換わります (Linux/macOS)
    # Windows (PowerShell) の場合は `${PWD}` を使用してください
    docker run -d -p 8000:80 \
      -v "$(pwd)/data:/code/data" \
      --name my-pen-server \
      iot-pen-server
    ```

## API仕様

### ペンの状態を取得

* **エンドポイント**: `GET /pens/{device_id}/status`
* **メソッド**: `GET`
* **パスパラメータ**:
    * `device_id` (string, required): 状態を取得したいペンのデバイスID。

#### 成功レスポンス (200 OK)

```json
{
  "deviceId": "PEN-ABC-12345",
  "inkLevel": 99.9,
  "estimatedEmptyDate": "2025-07-06T03:36:23.000000+00:00",
  "replacementSuggestion": "まだ交換の必要はありません。",
  "lastUpdatedAt": "2025-06-22T12:23:31Z"
}
```

#### エラーレスポンス (404 Not Found)

指定した `device_id` がデータ内に存在しない場合に返されます。
```json
{
  "detail": "Device ID 'PEN-UNKNOWN-000' not found."
}
```

## 設定可能な環境変数

コンテナ起動時に `-e` オプションを使用することで、アプリケーションの挙動を一部変更できます。

* **`DATA_FILE_PATH`**:
    * 説明: 読み込むデータファイルのパスをコンテナ内で指定します。
    * デフォルト値: `/code/data/pen_data.json`
    * 設定例:
        ```bash
        docker run -d -p 8000:80 \
          -e DATA_FILE_PATH="/app/custom_data/another_pen.json" \
          -v "/path/to/host/data:/app/custom_data" \
          --name my-pen-server \
          iot-pen-server
        ```

## 計算モデルについて

* **インク消費モデル**:
    * インクの初期残量を100%とします。
    * `isWriting`が`true`である筆記時間1分あたり`0.5%`のインクを消費するという、単純な線形モデルを採用しています。この値は `app/main.py` 内の `INK_CONSUMPTION_RATE_PER_SECOND` 定数で変更可能です。
* **インク枯渇予測**:
    * データ全体（最初の記録から最後の記録まで）の平均インク消費率を算出します。
    * 現在のインク残量をこの平均消費率で割り、インクがなくなるまでの残り時間を計算します。
    * 最後の記録日時にこの残り時間を加算して、予測日時を算出しています。