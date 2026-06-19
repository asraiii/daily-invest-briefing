import os
import requests
import yfinance as yf
from datetime import datetime
import google.generativeai as genai

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
os.environ["GEMINI_API_KEY"]
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-1.5-flash")

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

def get_ai_summary(data, score):
    try:
        prompt = f"""
너는 투자 애널리스트다.

S&P500: {data.get('S&P500')}
NASDAQ: {data.get('NASDAQ')}
VIX: {data.get('VIX')}
USD/KRW: {data.get('USDKRW')}

점수: {score}

5줄 요약으로 설명
"""

        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        print("AI ERROR:", e)
        return f"AI 분석 실패 ({str(e)[:50]})"
        
# -----------------------------
# 3. 브리핑 생성
# -----------------------------
def create_message(data, score, ai_summary=""):
    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"📊 투자 브리핑 ({now})",
        "",
        "[시장 상태]",
        f"S&P500: {data.get('S&P500')}%",
        f"NASDAQ: {data.get('NASDAQ')}%",
        f"VIX: {data.get('VIX')}%",
        f"USD/KRW: {data.get('USDKRW')}%",
        "",
        "[핵심 이슈]",
        ai_summary if ai_summary else "데이터 수집 중...",
        "",
        "[추가매수 점수]",
        f"{score}/100",
        ""
    ]

    if score < 55:
        lines.append("🟢 정기매수 유지")
    elif score < 70:
        lines.append("🟡 관망")
    elif score < 85:
        lines.append("🔴 분할매수")
    else:
        lines.append("🚨 적극 매수")

    return "\n".join(lines)


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

ai_summary = get_ai_summary(data, score)

message = create_message(data, score, ai_summary)

send_telegram(message)
