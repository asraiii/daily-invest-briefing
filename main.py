import os
import requests
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -----------------------------
# 1. 시장 데이터 수집
# -----------------------------
def get_market_data():
    tickers = {
        "S&P500": "^GSPC",
        "NASDAQ": "^NDX",
        "VIX": "^VIX",
        "USDKRW": "KRW=X"
    }

    data = {}

    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) > 1:
                change = ((hist["Close"][-1] - hist["Close"][-2]) / hist["Close"][-2]) * 100
                data[name] = round(change, 2)
            else:
                data[name] = 0
        except:
            data[name] = 0

    return data


# -----------------------------
# 2. 간단 점수 시스템
# -----------------------------
def score_market(data):
    score = 50

    score += data.get("S&P500", 0) * 2
    score += data.get("NASDAQ", 0) * 3
    score -= data.get("VIX", 0) * 1.5

    return max(0, min(100, round(score, 1)))


# -----------------------------
# 3. 브리핑 생성
# -----------------------------
def create_message(data, score):
    now = datetime.now().strftime("%Y-%m-%d")

    return f"""
📊 투자 브리핑 ({now})

[시장 변화]
S&P500: {data.get('S&P500')}%
NASDAQ: {data.get('NASDAQ')}%
VIX: {data.get('VIX')}%
USD/KRW: {data.get('USDKRW')}%

[추가매수 점수]
전체 점수: {score}/100

[판단]
{'🟢 정기 적립 유지' if score < 55 else '🟡 관심 구간' if score < 70 else '🔴 추가매수 고려'}

[포트폴리오]
- VOO / QQQM / SCHD / TIGER ETF
"""


# -----------------------------
# 4. 텔레그램 전송
# -----------------------------
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": message
    })


# -----------------------------
# 실행
# -----------------------------
data = get_market_data()
score = score_market(data)
message = create_message(data, score)

send_telegram(message)
