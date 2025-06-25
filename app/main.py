import os
import json
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- 設定値 ---
# 環境変数からデータファイルのパスを取得。未設定ならデフォルト値を使用。
DATA_FILE_PATH = os.getenv("DATA_FILE_PATH", "data/pen_data.json")
# 1分間の筆記で0.5%消費すると仮定 -> 1秒あたり (0.5 / 60) % 消費
INK_CONSUMPTION_RATE_PER_SECOND: float = 0.5 / 60
# 交換を推奨するインク残量の閾値
REPLACEMENT_THRESHOLD: float = 20.0
# インクの初期残量
INITIAL_INK_LEVEL: float = 100.0

# --- FastAPIアプリケーションの初期化 ---
app = FastAPI(
    title="IoT Pen Data API",
    description="IoTペンのインク残量や交換時期を計算・予測するAPI",
    version="1.0.0",
)

# --- APIのレスポンスモデル定義 ---
class PenStatus(BaseModel):
    deviceId: str
    inkLevel: float
    estimatedEmptyDate: Optional[str]
    replacementSuggestion: str
    lastUpdatedAt: str

# --- データ読み込み関数 ---
def load_pen_data() -> List[dict]:
    """データファイルを読み込み、JSONをパースして返す"""
    try:
        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"Data file not found at: {DATA_FILE_PATH}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse JSON data.")

# --- APIエンドポイント ---
@app.get("/pens/{device_id}/status", response_model=PenStatus)
def get_pen_status(device_id: str):
    """指定されたデバイスIDのペンの状態を返す"""
    all_data = load_pen_data()

    # 指定されたデバイスIDのデータのみを抽出
    device_data = [d for d in all_data if d.get("deviceId") == device_id]

    if not device_data:
        raise HTTPException(status_code=404, detail=f"Device ID '{device_id}' not found.")

    # タイムスタンプでデータを昇順にソート
    device_data.sort(key=lambda x: x["timestamp"])

    total_writing_duration_seconds = 0
    # isWritingがtrueの区間の時間を累積
    for i in range(1, len(device_data)):
        if device_data[i-1].get("isWriting", False):
            prev_time = datetime.fromisoformat(device_data[i-1]["timestamp"].replace('Z', '+00:00'))
            current_time = datetime.fromisoformat(device_data[i]["timestamp"].replace('Z', '+00:00'))
            duration = (current_time - prev_time).total_seconds()
            total_writing_duration_seconds += duration

    # インク残量計算
    consumed_ink = total_writing_duration_seconds * INK_CONSUMPTION_RATE_PER_SECOND
    current_ink_level = max(0, INITIAL_INK_LEVEL - consumed_ink)

    # インク枯渇予測
    estimated_empty_date_str = None
    if consumed_ink > 0:
        first_timestamp = datetime.fromisoformat(device_data[0]["timestamp"].replace('Z', '+00:00'))
        last_timestamp = datetime.fromisoformat(device_data[-1]["timestamp"].replace('Z', '+00:00'))
        total_period_seconds = (last_timestamp - first_timestamp).total_seconds()

        if total_period_seconds > 0:
            # 平均消費率 (消費量 / 期間)
            average_consumption_rate = consumed_ink / total_period_seconds
            if average_consumption_rate > 0:
                remaining_seconds = current_ink_level / average_consumption_rate
                estimated_empty_date = last_timestamp + timedelta(seconds=remaining_seconds)
                estimated_empty_date_str = estimated_empty_date.isoformat()

    # 交換推奨メッセージ
    suggestion = "まだ交換の必要はありません。"
    if current_ink_level < REPLACEMENT_THRESHOLD:
        suggestion = "インクの残量が少なくなっています。交換を推奨します。"
    if current_ink_level == 0:
        suggestion = "インクがなくなりました。交換してください。"


    return PenStatus(
        deviceId=device_id,
        inkLevel=round(current_ink_level, 2),
        estimatedEmptyDate=estimated_empty_date_str,
        replacementSuggestion=suggestion,
        lastUpdatedAt=device_data[-1]["timestamp"],
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the IoT Pen API. Access status at /pens/{device_id}/status"}