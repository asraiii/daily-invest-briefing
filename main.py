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

            close = hist_5d["Close"].dropna().tail(2).values

            if len(close) >= 2:
                daily_change = (
                    (close[-1] - close[-2])
                    / close[-2]
                ) * 100
            else:
                daily_change = 0

            # 1년 최고점 대비 하락률
            hist_1y = ticker.history(period="1y")
            close_1y = hist_1y["Close"].dropna()

            if len(close_1y) >= 2:
                current_price = close_1y.iloc[-1]
                high_price = close_1y.max()

                drawdown = (
                    (current_price - high_price)
                    / high_price
                ) * 100
            else:
                current_price = 0
                drawdown = 0

            data[name] = {
                "daily": round(float(daily_change), 2),
                "drawdown": round(float(drawdown), 2),
                "current": round(float(current_price), 2)
            }

        except Exception as e:
            print(f"{name} error:", e)

            data[name] = {
                "daily": 0,
                "drawdown": 0,
                "current": 0
            }

    return data


# -----------------------------
# 2. 간단 점수 시스템
# -----------------------------
def score_market(data):

    print(data)

    score = 0

    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])

    # S&P500 기준
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

    # NASDAQ 보정
    if nd >= 10:
        score += 10

    if nd >= 15:
        score += 10

    if nd >= 20:
        score += 10

    return min(score, 100)
def get_market_comment(data):

    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])
    vix = data["VIX"]["daily"]

    comments = []

    # 시장 위치
    if sp < 5:

        comments.append(
            f"S&P500은 최근 1년 최고점 대비 {sp:.1f}% 하락에 불과하며 사실상 신고가 부근입니다."
        )

        comments.append(
            f"NASDAQ100도 최고점 대비 {nd:.1f}% 하락 수준으로 성장주 강세 흐름이 유지되고 있습니다."
        )

        comments.append(
            "시장은 낙관적인 분위기가 우세하며 투자심리가 안정적인 상태입니다."
        )

    elif sp < 10:

        comments.append(
            f"S&P500은 최고점 대비 {sp:.1f}% 하락한 상태입니다."
        )

        comments.append(
            "정상적인 조정 범위로 볼 수 있으며 장기 상승 추세는 아직 유지되고 있습니다."
        )

    elif sp < 20:

        comments.append(
            f"S&P500은 최고점 대비 {sp:.1f}% 하락했습니다."
        )

        comments.append(
            "과거 기준으로 의미 있는 조정 구간에 진입한 상태입니다."
        )

        comments.append(
            "장기 투자자라면 추가 자금을 분할 투입하기 시작할 수 있는 구간입니다."
        )

    else:

        comments.append(
            f"S&P500은 최고점 대비 {sp:.1f}% 하락했습니다."
        )

        comments.append(
            "역사적으로 드물게 나타나는 큰 폭의 조정 구간입니다."
        )

        comments.append(
            "장기 투자자에게는 적극적인 매수 기회가 될 수 있습니다."
        )

    # 변동성
    vix_now = data["VIX"]["current"]

    if vix_now < 15:
        comments.append(
            f"현재 VIX는 {vix_now:.2f}로 비교적 안정·낙관 국면에 해당합니다."
        )

    elif vix_now < 20:
        comments.append(
            f"현재 VIX는 {vix_now:.2f}로 보통 수준의 변동성 환경입니다."
        )

    elif vix_now < 30:
        comments.append(
            f"현재 VIX는 {vix_now:.2f}로 불안감이 커지는 구간입니다."
        )

    else:
        comments.append(
            f"현재 VIX는 {vix_now:.2f}로 공포가 확대된 상태입니다."
        )

    return "\n".join(comments)

# -----------------------------
# 3. 브리핑 생성
# -----------------------------
def create_message(data, market_comment):

    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"📊 투자 브리핑 ({now})",
        "",

        "[오늘 시장 등락]",
        f"S&P500 : {data['S&P500']['daily']}%",
        f"NASDAQ : {data['NASDAQ']['daily']}%",
        f"환율 : {data['USDKRW']['current']:,.0f}원",
        "",

        "[VIX 지수]",
        f"현재 VIX : {data['VIX']['current']:.2f}",
        "",

        "[최근 1년 최고점 대비]",
        f"S&P500 : {data['S&P500']['drawdown']}%",
        f"NASDAQ : {data['NASDAQ']['drawdown']}%",
        "",

        "[시장 해설]",
        market_comment
    ]

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

market_comment = get_market_comment(data)

message = create_message(
    data,
    market_comment
)

send_telegram(message)
