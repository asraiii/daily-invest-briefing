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
            hist = ticker.history(period="1y")

            if len(hist) >= 2:

                current_price = hist["Close"].iloc[-1]
                high_price = hist["Close"].max()

                drawdown = (
                    (current_price - high_price)
                    / high_price
                ) * 100

                data[name] = round(float(drawdown), 2)

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

    sp = abs(data.get("S&P500", 0))
    nd = abs(data.get("NASDAQ", 0))

    avg_drop = (sp + nd) / 2

    if avg_drop < 5:
        return 0

    elif avg_drop < 10:
        return 20

    elif avg_drop < 15:
        return 40

    elif avg_drop < 20:
        return 60

    elif avg_drop < 30:
        return 80

    else:
        return 100

def get_market_comment(data, score):

    sp = data.get("S&P500", 0)
    nd = data.get("NASDAQ", 0)

    comments = []

    comments.append(
        f"S&P500은 최근 1년 최고점 대비 {abs(sp):.1f}% 하락 상태입니다."
    )

    comments.append(
        f"NASDAQ100은 최근 1년 최고점 대비 {abs(nd):.1f}% 하락 상태입니다."
    )

    if nd <= -10:
        comments.append(
            "기술주 중심의 조정이 진행되고 있습니다."
        )

    if nd <= -20:
        comments.append(
            "과거 기준으로 의미있는 매수 구간에 접근하고 있습니다."
        )

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

    if score < 20:
        lines.append("🟢 정기매수만 진행")

    elif score < 40:
        lines.append("🟡 관심 구간")

    elif score < 60:
        lines.append("🟠 추가매수 검토")

    elif score < 80:
        lines.append("🔴 추가매수")

    else:
        lines.append("🚨 강력 추가매수")

    if score >= 60:
        lines.extend([
            "",
            "[추천 비율]",
            "QQQM 40%",
            "VOO 40%",
            "SCHD 20%"
        ])

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
