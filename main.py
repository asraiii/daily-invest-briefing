import os
import requests
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# -----------------------------
# API
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)


# -----------------------------
# 시장 데이터
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

            h5 = t.history(period="5d")
            h1 = t.history(period="1y")

            # 일간 변화
            if len(h5) >= 2:
                close = h5["Close"].tail(2).values
                daily = (close[-1] - close[-2]) / close[-2] * 100
            else:
                daily = 0

            current = h1["Close"].dropna().iloc[-1]
            high = h1["Close"].max()
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
# Fear & Greed
# -----------------------------
def get_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        score = r.json()["fear_and_greed"]["score"]
        return int(score), "정상"

    except:
        return 50, "중립"


# -----------------------------
# 투자 신호
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
# 시장 해설 (간단)
# -----------------------------
def get_market_comment(data, fear_score, fear_status):

    sp = abs(data["S&P500"]["drawdown"])
    vix = data["VIX"]["current"]
    usd = data["USDKRW"]["current"]

    lines = []

    lines.append(f"Fear & Greed {fear_score} ({fear_status})")

    # S&P
    if sp < 5:
        lines.append(f"S&P500 신고가 근처 (-{sp:.1f}%)")
    elif sp < 10:
        lines.append(f"S&P500 소폭 조정 (-{sp:.1f}%)")
    elif sp < 20:
        lines.append(f"S&P500 조정 구간 (-{sp:.1f}%)")
    else:
        lines.append(f"S&P500 큰 조정 (-{sp:.1f}%)")

    # VIX
    if vix >= 25:
        lines.append("변동성 매우 높음")
    elif vix >= 18:
        lines.append("변동성 상승")
    else:
        lines.append("변동성 안정")

    # 환율
    lines.append(f"환율 {usd:.0f}원")

    return "\n".join(lines)


# -----------------------------
# 경제 이슈 (수정 핵심)
# -----------------------------
def get_economic_issues():

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = """
최근 24시간 경제/금융 이슈 3개만 매우 짧게:

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

        res = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 600
            }
        )

        return res.text.strip()

    except Exception as e:
        print("Gemini error:", e)
        return "경제 이슈 데이터 없음"


# -----------------------------
# 종합 판단
# -----------------------------
def get_market_summary(signal, fear_score, fear_status, data):

    sp = abs(data["S&P500"]["drawdown"])

    return f"""
Fear & Greed: {fear_score} ({fear_status})
S&P500: -{sp:.1f}%

신호: {signal}
""".strip()


# -----------------------------
# 메시지 생성 (깔끔 버전)
# -----------------------------
def create_message(data, signal, news, summary, fear_score, fear_status):

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

[최근 최고점 대비]
S&P500: {data['S&P500']['drawdown']}%
NASDAQ: {data['NASDAQ']['drawdown']}%
SCHD: {data['SCHD']['drawdown']}%

[신호]
{signal}

[이슈]
{news}

[요약]
{summary}
""".strip()


# -----------------------------
# 텔레그램
# -----------------------------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": msg
    })


# -----------------------------
# 실행
# -----------------------------
data = get_market_data()
fear_score, fear_status = get_fear_greed()

signal = get_invest_signal(data, fear_score)
news = get_economic_issues()
summary = get_market_summary(signal, fear_score, fear_status, data)

msg = create_message(data, signal, news, summary, fear_score, fear_status)

send_telegram(msg)
