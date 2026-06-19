import os
import requests
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

# =========================
# API 설정
# =========================
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

            # daily
            if len(hist_5d) >= 2:
                close = hist_5d["Close"].tail(2).values
                daily = (close[-1] - close[-2]) / close[-2] * 100
            else:
                daily = 0

            # current
            current = hist_1y["Close"].dropna().iloc[-1]

            # drawdown
            high = hist_1y["Close"].max()
            drawdown = (current - high) / high * 100

            data[name] = {
                "daily": round(daily, 2),
                "current": round(float(current), 2),
                "drawdown": round(float(drawdown), 2)
            }

        except Exception as e:
            print(name, e)
            data[name] = {"daily": 0, "current": 0, "drawdown": 0}

    return data


# =========================
# 2. Fear & Greed (안끊김 버전)
# =========================
def get_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        score = int(r.json()["fear_and_greed"]["score"])
        return score, "정상"

    except Exception as e:
        print("Fear & Greed error:", e)
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
# 4. 시장 해설 (중복 없음)
# =========================
def get_comment(data, fear, status):
    sp = abs(data["S&P500"]["drawdown"])
    vix = data["VIX"]["current"]
    usd = data["USDKRW"]["current"]

    out = []

    out.append(f"Fear & Greed: {fear} ({status})")

    if sp < 5:
        out.append(f"S&P500: 신고가 근처 ({sp:.1f}%)")
    elif sp < 10:
        out.append(f"S&P500: 소폭 조정 ({sp:.1f}%)")
    else:
        out.append(f"S&P500: 조정 구간 ({sp:.1f}%)")

    if vix >= 25:
        out.append("변동성: 매우 높음")
    elif vix >= 18:
        out.append("변동성: 상승")
    else:
        out.append("변동성: 안정")

    out.append(f"환율: {usd:.0f}원")

    return "\n".join(out)


# =========================
# 5. 경제 이슈 (끊김 방지 핵심 수정)
# =========================
def get_economic_issues():
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = """
최근 24시간 경제/금융 이슈 3개.

형식:
1. 제목 - 핵심요약 (1줄)
2. 제목 - 핵심요약 (1줄)
3. 제목 - 핵심요약 (1줄)

절대 길게 쓰지 말고 한 줄로 끝낼 것.
"""

        res = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 300
            }
        )

        text = res.text.strip()

        # 🔥 끊김 방지 핵심
        lines = [l for l in text.split("\n") if l.strip()]
        return "\n".join(lines[:3])

    except Exception as e:
        print("Gemini error:", e)
        return "이슈 로딩 실패"


# =========================
# 6. 최고점 대비
# =========================
def get_drawdowns(data):
    return {
        k: data[k]["drawdown"]
        for k in ["S&P500", "NASDAQ", "SCHD"]
    }


# =========================
# 7. 메시지 생성 (중복 제거 완료)
# =========================
def create_message(data, fear, status, signal, issues):

    today = datetime.now().strftime("%Y-%m-%d")
    dd = get_drawdowns(data)

    msg = f"""📊 투자 브리핑 ({today})

[시장]
S&P500: {data['S&P500']['daily']}%
NASDAQ: {data['NASDAQ']['daily']}%
SCHD: {data['SCHD']['daily']}%
VIX: {data['VIX']['daily']}%
USD/KRW: {data['USDKRW']['current']}원

Fear & Greed: {fear} ({status})

[최근 최고점 대비]
S&P500: {dd['S&P500']}%
NASDAQ: {dd['NASDAQ']}%
SCHD: {dd['SCHD']}%

[신호]
{signal}

[이슈]
{issues}
"""

    return msg


# =========================
# 8. 텔레그램
# =========================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text
    })


# =========================
# 실행
# =========================
data = get_market_data()
fear, status = get_fear_greed()
signal = get_signal(data, fear)
issues = get_economic_issues()

message = create_message(data, fear, status, signal, issues)
send_telegram(message)
