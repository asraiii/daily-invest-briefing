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

            # 오늘 등락률
            hist_5d = ticker.history(period="5d")

            if len(hist_5d) >= 2:
                close = hist_5d["Close"].tail(2).values

                daily_change = (
                    (close[-1] - close[-2])
                    / close[-2]
                ) * 100
            else:
                daily_change = 0

            # 1년 최고점 대비 하락률
            hist_1y = ticker.history(period="1y")

            if len(hist_1y) >= 2:
                current_price = hist_1y["Close"].iloc[-1]
                high_price = hist_1y["Close"].max()

                drawdown = (
                    (current_price - high_price)
                    / high_price
                ) * 100
            else:
                drawdown = 0

            data[name] = {
                "daily": round(float(daily_change), 2),
                "drawdown": round(float(drawdown), 2)
            }

        except Exception as e:
            print(f"{name} error:", e)

            data[name] = {
                "daily": 0,
                "drawdown": 0
            }

    return data


# -----------------------------
# 2. 간단 점수 시스템
# -----------------------------
def score_market(data):

    score = 0

    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])

    if sp >= 5:
        score += 20
    if sp >= 10:
        score += 20
    if sp >= 15:
        score += 20
    if sp >= 20:
        score += 20
    if sp >= 30:
        score += 20

    if nd >= 8:
        score += 10
    if nd >= 15:
        score += 15
    if nd >= 20:
        score += 15
    if nd >= 30:
        score += 20

    return min(score, 100)
def get_market_comment(data, score):

    sp = data["S&P500"]["drawdown"]
    nd = data["NASDAQ"]["drawdown"]

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
        
        "[오늘 시장 등락]",
        f"S&P500: {data['S&P500']['daily']}%",
        f"NASDAQ: {data['NASDAQ']['daily']}%",
        f"VIX: {data['VIX']['daily']}%",
        f"USD/KRW: {data['USDKRW']['daily']}%",
        "",

        "[최근 1년 최고점 대비]",
        f"S&P500: {data['S&P500']['drawdown']}%",
        f"NASDAQ: {data['NASDAQ']['drawdown']}%",
        f"VIX: {data['VIX']['drawdown']}%",
        f"USD/KRW: {data['USDKRW']['drawdown']}%",
        "",
        
        
        "[핵심 이슈]",
        ai_summary if ai_summary else "데이터 수집 중...",
        "",
        
        "[추가매수 점수]",
        f"{score}/100",
        ""
    ]

    if score == 0:
        lines.append("🟢 정기매수만 진행")

    elif score <= 20:
        lines.append("🟡 약한 추가매수 구간")

    elif score <= 40:
        lines.append("🟠 분할 추가매수 시작")

    elif score <= 60:
        lines.append("🔴 적극 추가매수")

    elif score <= 80:
        lines.append("🚨 강한 추가매수")

    else:
        lines.append("🔥 역사적 저점 수준")

    
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
