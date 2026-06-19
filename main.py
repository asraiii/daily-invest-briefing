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
            ticker = yf.Ticker(symbol)

            hist_5d = ticker.history(period="5d")
            if len(hist_5d) >= 2:
                close = hist_5d["Close"].tail(2).values
                daily_change = (close[-1] - close[-2]) / close[-2] * 100
            else:
                daily_change = 0

            hist_1y = ticker.history(period="1y")

            if len(hist_1y) > 0:
                current_price = hist_1y["Close"].dropna().iloc[-1]
                high_price = hist_1y["Close"].max()
                drawdown = (current_price - high_price) / high_price * 100
            else:
                current_price = 0
                drawdown = 0

            data[name] = {
                "daily": round(daily_change, 2),
                "drawdown": round(drawdown, 2),
                "current": round(current_price, 2)
            }

        except:
            data[name] = {"daily": 0, "drawdown": 0, "current": 0}

    return data


# -----------------------------
# 2. Fear & Greed (안정 버전)
# -----------------------------
def get_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        score = int(r.json()["fear_and_greed"]["score"])
        return score, "정상"

    except:
        return 50, "중립"


# -----------------------------
# 3. 투자 신호
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
# 4. 시장 코멘트 (정리됨)
# -----------------------------
def get_market_comment(data, fear_score):

    sp = abs(data["S&P500"]["drawdown"])
    vix = data["VIX"]["current"]
    usdkrw = data["USDKRW"]["current"]

    comments = []

    comments.append(f"Fear & Greed: {fear_score}")

    if sp < 5:
        comments.append("S&P500: 신고가 근처")
    elif sp < 10:
        comments.append("S&P500: 소폭 조정")
    elif sp < 20:
        comments.append("S&P500: 조정 구간")
    else:
        comments.append("S&P500: 큰 조정")

    if vix >= 25:
        comments.append("변동성 높음")
    elif vix >= 18:
        comments.append("변동성 상승")
    else:
        comments.append("변동성 안정")

    if usdkrw >= 1400:
        comments.append(f"환율 {usdkrw:.0f} (높음)")
    else:
        comments.append(f"환율 {usdkrw:.0f}")

    return "\n".join(comments)


# -----------------------------
# 5. 경제 이슈 (절대 안 끊기게 수정)
# -----------------------------
def get_economic_issues():
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = """
최근 24시간 경제/금융 이슈 3개.

각각 반드시 아래 형식 유지:

1. 제목
핵심:
영향:

2. 제목
핵심:
영향:

3. 제목
핵심:
영향:

짧고 끊지 말고 반드시 3개 모두 작성
"""

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 800
            }
        )

        text = response.text.strip()

        # 안전장치 (끊김 방지)
        if len(text) < 50:
            return "이슈 생성 실패"

        return text

    except:
        return "이슈 생성 실패"


# -----------------------------
# 6. 메시지 생성 (완전 정리)
# -----------------------------
def create_message(data, fear_score, fear_status, signal, issues):

    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"📊 투자 브리핑 ({now})",
        "",
        "[시장]",
        f"S&P500: {data['S&P500']['daily']}%",
        f"NASDAQ: {data['NASDAQ']['daily']}%",
        f"SCHD: {data['SCHD']['daily']}%",
        f"VIX: {data['VIX']['daily']}%",
        f"USD/KRW: {data['USDKRW']['current']}원",
        "",
        f"Fear & Greed: {fear_score} ({fear_status})",
        "",
        "[최근 최고점 대비]",
        f"S&P500: {data['S&P500']['drawdown']}%",
        f"NASDAQ: {data['NASDAQ']['drawdown']}%",
        f"SCHD: {data['SCHD']['drawdown']}%",
        "",
        "[신호]",
        signal,
        "",
        "[이슈]",
        issues
    ]

    return "\n".join(lines)


# -----------------------------
# 7. 텔레그램 전송
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
issues = get_economic_issues()

message = create_message(data, fear_score, fear_status, signal, issues)

send_telegram(message)
