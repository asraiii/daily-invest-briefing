import os
import requests
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


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

    score += data.get("S&P500", 0) * 1
    score += data.get("NASDAQ", 0) * 1.5
    score -= data.get("VIX", 0) * 0.5

    return max(0, min(100, round(score, 1)))

def get_market_comment(data, score):

    sp = data.get("S&P500", 0)
    nd = data.get("NASDAQ", 0)
    vix = data.get("VIX", 0)

    comments = []

    if nd > 1:
        comments.append("나스닥이 강세를 보이며 성장주 투자심리가 개선되고 있습니다.")

    if sp > 0.5:
        comments.append("S&P500 상승으로 미국 주식 전반의 분위기는 긍정적입니다.")

    if vix < -5:
        comments.append("VIX가 크게 하락하여 시장 불안감은 완화된 상태입니다.")

    if score >= 75:
        comments.append("다만 시장이 강세 구간이므로 공격적인 추가매수는 신중하게 접근하는 것이 좋습니다.")

    return "\n".join(comments)

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

    if score < 50:
        lines.append("🟢 정기매수 유지")
    elif score < 65:
        lines.append("🟡 관망")
    elif score < 80:
        lines.append("🟠 관심 구간")
    elif score < 90:
        lines.append("🔴 추가매수 검토")
    else:
        lines.append("🚨 강력 추가매수")

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
ai_summary = get_market_comment(data, score)

message = create_message(data, score, ai_summary)

send_telegram(message)
