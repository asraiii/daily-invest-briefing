import os
import requests
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)


# =========================
# 1. 시장 데이터
# =========================
def get_market_data():
    tickers = {
        "S&P500": "^GSPC",
        "NASDAQ": "^NDX",
        "VIX": "^VIX",
        "USDKRW": "KRW=X",
    }

    data = {}

    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)

            h5 = t.history(period="5d")
            h1 = t.history(period="1y")

            # daily
            if len(h5) >= 2:
                c = h5["Close"].dropna().values
                daily = (c[-1] - c[-2]) / c[-2] * 100
            else:
                daily = 0

            # drawdown
            if len(h1) > 0:
                current = h1["Close"].dropna().iloc[-1]
                high = h1["Close"].max()
                drawdown = (current - high) / high * 100
            else:
                current = 0
                drawdown = 0

            data[name] = {
                "daily": round(float(daily), 2),
                "drawdown": round(float(drawdown), 2),
                "current": round(float(current), 2),
            }

        except:
            data[name] = {"daily": 0, "drawdown": 0, "current": 0}

    return data


# =========================
# 2. Fear & Greed
# =========================
def get_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        score = r.json()["fear_and_greed"]["score"]
        return int(score), "정상"

    except:
        return 50, "중립"


# =========================
# 3. 투자 신호
# =========================
def get_signal(data, fear):
    sp = abs(data["S&P500"]["drawdown"])

    if sp >= 25 or fear <= 20:
        return "🔴 공격매수"
    elif sp >= 10 or fear <= 40:
        return "🟡 적극매수"
    else:
        return "🟢 정기매수"


# =========================
# 4. 메시지 생성 (핵심만)
# =========================
def build_message(data, fear, status, signal):

    now = datetime.now().strftime("%Y-%m-%d")

    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])

    msg = f"""📊 투자 브리핑 ({now})

[시장]
S&P500: {data['S&P500']['daily']}%
NASDAQ: {data['NASDAQ']['daily']}%
VIX: {data['VIX']['daily']}%
USD/KRW: {data['USDKRW']['current']}원

[최근 최고점 대비]
S&P500: {data['S&P500']['drawdown']}%
NASDAQ: {data['NASDAQ']['drawdown']}%

[투자 신호]
{signal}

[요약]
S&P500: -{sp:.1f}%
NASDAQ: -{nd:.1f}%
신호: {signal}
"""

    return msg


# =========================
# 5. 텔레그램 전송
# =========================
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})


# =========================
# 실행
# =========================
data = get_market_data()
fear, status = get_fear_greed()
signal = get_signal(data, fear)

message = build_message(data, fear, status, signal)
send(message)
