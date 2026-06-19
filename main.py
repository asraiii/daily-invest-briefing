import os
import requests
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# -----------------------------
# 1. 시장 데이터 수집 (안정 버전)
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
            t = yf.Ticker(symbol)

            hist_5d = t.history(period="5d")
            hist_1y = t.history(period="1y")

            if hist_5d.empty or hist_1y.empty:
                raise ValueError("No data")

            # 오늘 등락률
            if len(hist_5d) >= 2:
                close = hist_5d["Close"].dropna().values
                daily = (close[-1] - close[-2]) / close[-2] * 100
            else:
                daily = 0

            # 현재가
            current = hist_1y["Close"].dropna().iloc[-1]

            # 1년 최고 대비
            high = hist_1y["Close"].dropna().max()
            drawdown = (current - high) / high * 100

            data[name] = {
                "daily": round(float(daily), 2),
                "drawdown": round(float(drawdown), 2),
                "current": round(float(current), 2)
            }

        except Exception as e:
            print(name, "error:", e)

            data[name] = {
                "daily": 0,
                "drawdown": 0,
                "current": 0
            }

    return data


# -----------------------------
# 2. 시장 해설
# -----------------------------
def get_market_comment(data):

    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])
    vix = data["VIX"]["daily"]
    usdkrw = data["USDKRW"]["current"]

    comments = []

    # S&P500 상태
    if sp < 5:
        comments.append("S&P500: 신고가 근처")
    elif sp < 10:
        comments.append("S&P500: 소폭 조정")
    elif sp < 20:
        comments.append("S&P500: 의미 있는 조정")
    else:
        comments.append("S&P500: 큰 조정")

    # NASDAQ
    if nd < 5:
        comments.append("NASDAQ: 강세 유지")
    elif nd < 15:
        comments.append("NASDAQ: 조정 구간")
    else:
        comments.append("NASDAQ: 변동성 확대")

    # VIX
    if vix > 10:
        comments.append("VIX: 변동성 확대")
    elif vix < -5:
        comments.append("VIX: 공포 완화")

    # 환율
    if usdkrw >= 1400:
        comments.append(f"환율: {usdkrw:.0f}원 (높은 수준)")
    else:
        comments.append(f"환율: {usdkrw:.0f}원")

    return "\n".join(comments)


# -----------------------------
# 3. 메시지 생성 (최종 포맷)
# -----------------------------
def create_message(data, comment):

    now = datetime.now().strftime("%Y-%m-%d")

    return f"""📊 투자 브리핑 ({now})

[시장]
S&P500: {data['S&P500']['daily']}%
NASDAQ: {data['NASDAQ']['daily']}%
VIX: {data['VIX']['daily']}%
USD/KRW: {data['USDKRW']['current']}원

[최근 최고점 대비]
S&P500: {data['S&P500']['drawdown']}%
NASDAQ: {data['NASDAQ']['drawdown']}%
VIX: {data['VIX']['drawdown']}%
USD/KRW: {data['USDKRW']['drawdown']}%

[시장 해설]
{comment}
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
comment = get_market_comment(data)
message = create_message(data, comment)

send_telegram(message)
