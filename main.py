import os
import requests
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# -----------------------------
# API 설정
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)


# -----------------------------
# 1. 시장 데이터
# -----------------------------
def get_market_data():
    tickers = {
        "S&P500": "^GSPC",
        "NASDAQ": "^NDX",
        "SCHD": "SCHD",
        "VIX": "^VIX",
        "USDKRW": "KRW=X"
    }

    data = {}

    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)

            hist_5d = t.history(period="5d")
            hist_1y = t.history(period="1y")

            # 하루 변화
            if len(hist_5d) >= 2:
                close = hist_5d["Close"].tail(2).values
                daily = (close[-1] - close[-2]) / close[-2] * 100
            else:
                daily = 0

            # 현재가
            current = hist_1y["Close"].dropna().iloc[-1]

            # 최고점 대비
            high = hist_1y["Close"].max()
            drawdown = (current - high) / high * 100

            data[name] = {
                "daily": round(float(daily), 2),
                "drawdown": round(float(drawdown), 2),
                "current": round(float(current), 2)
            }

        except:
            data[name] = {"daily": 0, "drawdown": 0, "current": 0}

    return data


# -----------------------------
# 2. Fear & Greed
# -----------------------------
def get_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        score = r.json()["fear_and_greed"]["score"]
        return int(score), "정상"

    except:
        return 50, "중립(기본값)"


# -----------------------------
# 3. 시장 해설
# -----------------------------
def get_market_comment(data, fear_score, fear_status):

    comments = []

    sp = abs(data["S&P500"]["drawdown"])
    vix = data["VIX"]["current"]
    usd = data["USDKRW"]["current"]

    comments.append(f"Fear & Greed: {fear_score} ({fear_status})")

    # S&P
    if sp < 5:
        comments.append("시장 신고가 근처")
    elif sp < 10:
        comments.append("완만한 조정")
    elif sp < 20:
        comments.append("의미있는 조정")
    else:
        comments.append("큰 조정 구간")

    # VIX
    if vix >= 25:
        comments.append("변동성 매우 높음")
    elif vix >= 18:
        comments.append("변동성 상승")
    else:
        comments.append("변동성 안정")

    # 환율
    if usd >= 1400:
        comments.append(f"환율 {usd:.0f}원 (높음)")
    elif usd >= 1300:
        comments.append(f"환율 {usd:.0f}원 (중간)")
    else:
        comments.append(f"환율 {usd:.0f}원 (양호)")

    comments.append("")
    comments.append("VOO / QQQM / SCHD 적립 유지")

    return "\n".join(comments)


# -----------------------------
# 4. 투자 신호
# -----------------------------
def get_invest_signal(data, fear_score):

    sp = abs(data["S&P500"]["drawdown"])

    if sp >= 25 or fear_score <= 20:
        return "🔴 공격매수"
    elif sp >= 10 or fear_score <= 40:
        return "🟡 적극매수"
    else:
        return "🟢 정기매수"


# -----------------------------
# 5. 경제 이슈
# -----------------------------
def get_economic_issues():

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = """
최근 24시간 경제 이슈 3개만:

1. 제목
무슨 일:
시장영향:

2. 제목
무슨 일:
시장영향:

3. 제목
무슨 일:
시장영향:
"""

        res = model.generate_content(prompt)
        return res.text

    except:
        return "경제 이슈 불러오기 실패"


# -----------------------------
# 6. 종합 판단
# -----------------------------
def get_market_summary(signal, fear_score, fear_status, data):

    sp = abs(data["S&P500"]["drawdown"])

    return f"""
Fear & Greed: {fear_score} ({fear_status})
S&P500 조정: {sp:.1f}%

현재 신호: {signal}

장기투자: VOO / QQQM / SCHD 유지
""".strip()


# -----------------------------
# 7. 메시지 생성
# -----------------------------
def create_message(data, comment, signal, news, summary, fear_score, fear_status):

    now = datetime.now().strftime("%Y-%m-%d")

    return f"""
📊 투자 브리핑 ({now})

[시장]
S&P500: {data['S&P500']['daily']}%
NASDAQ: {data['NASDAQ']['daily']}%
SCHD: {data['SCHD']['daily']}%
VIX: {data['VIX']['daily']}%
USD/KRW: {data['USDKRW']['current']}원

Fear & Greed: {fear_score} ({fear_status})

[신호]
{signal}

[이슈]
{news}

[요약]
{summary}

[해설]
{comment}
"""


# -----------------------------
# 8. 텔레그램
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
fear_score, fear_status = get_fear_greed()

signal = get_invest_signal(data, fear_score)
comment = get_market_comment(data, fear_score, fear_status)
news = get_economic_issues()
summary = get_market_summary(signal, fear_score, fear_status, data)

msg = create_message(data, comment, signal, news, summary, fear_score, fear_status)

send_telegram(msg)
