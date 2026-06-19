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

            if len(hist) >= 2:
                close = hist["Close"].tail(2).values
                change = ((close[-1] - close[-2]) / close[-2]) * 100
                data[name] = round(float(change), 2)
            else:
                data[name] = 0.0

        except Exception as e:
            print(f"{name} error:", e)
            data[name] = 0.0

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

    message = []
    message.append(f"📊 투자 브리핑 ({now})\n")

    message.append("[시장 변화]")
    message.append(f"S&P500: {data.get('S&P500')}%")
    message.append(f"NASDAQ: {data.get('NASDAQ')}%")
    message.append(f"VIX: {data.get('VIX')}%")
    message.append(f"USD/KRW: {data.get('USDKRW')}%\n")

    message.append("[추가매수 점수]")
    message.append(f"전체 점수: {score}/100\n")

    if score < 55:
        message.append("🟢 정기 적립 유지")
    elif score < 70:
        message.append("🟡 관심 구간")
    else:
        message.append("🔴 추가매수 고려")

    message.append("\n[포트폴리오]")
    message.append("- VOO / QQQM / SCHD / TIGER ETF")

    return "\n".join(message)


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
