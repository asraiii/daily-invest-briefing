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
        "VIX": "^VIX",
        "USDKRW": "KRW=X",
    }

    data = {}

    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)

            hist_5d = t.history(period="5d")
            hist_1y = t.history(period="1y")

            # daily change
            if len(hist_5d) >= 2:
                close = hist_5d["Close"].dropna().values
                daily = (close[-1] - close[-2]) / close[-2] * 100
            else:
                daily = 0

            # drawdown
            if len(hist_1y) > 0:
                current = hist_1y["Close"].dropna().iloc[-1]
                high = hist_1y["Close"].max()
                drawdown = (current - high) / high * 100
            else:
                current = 0
                drawdown = 0

            data[name] = {
                "daily": round(float(daily), 2),
                "drawdown": round(float(drawdown), 2),
                "current": round(float(current), 2),
            }

        except Exception as e:
            print(name, "error:", e)
            data[name] = {"daily": 0, "drawdown": 0, "current": 0}

    return data


# =========================
# 2. Fear & Greed (안깨지는 버전)
# =========================
def get_fear_greed():
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        r = requests.get(url, timeout=10)
        r.raise_for_status()

        score = r.json()["fear_and_greed"]["score"]
        return int(score), "정상"

    except Exception:
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
# 4. 시장 코멘트
# =========================
def get_comment(data, fear, status):
    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])
    vix = data["VIX"]["current"]
    usd = data["USDKRW"]["current"]

    out = []

    out.append(f"Fear & Greed: {fear} ({status})")

    if sp < 5:
        out.append(f"S&P500: 신고가 근처 ({sp:.1f}%)")
    elif sp < 10:
        out.append(f"S&P500: 소폭 조정 ({sp:.1f}%)")
    elif sp < 20:
        out.append(f"S&P500: 의미있는 조정 ({sp:.1f}%)")
    else:
        out.append(f"S&P500: 큰 조정 ({sp:.1f}%)")

    if vix >= 25:
        out.append("변동성 매우 높음")
    elif vix >= 18:
        out.append("변동성 상승")
    else:
        out.append("변동성 안정")

    if usd >= 1400:
        out.append(f"환율 {usd:.0f}원 (높음)")
    else:
        out.append(f"환율 {usd:.0f}원")

    return "\n".join(out)


# =========================
# 5. 경제 이슈 (안 끊기게 핵심 개선)
# =========================
def get_economic_issues():
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = """
최근 24시간 경제/금융 핵심 이슈 5개.

반드시 아래 형식 정확히:

1. 제목
영향: 긍정/부정/중립
설명: 1줄

2. 제목
영향: 긍정/부정/중립
설명: 1줄

3. 제목
영향: 긍정/부정/중립
설명: 1줄

4. 제목
영향: 긍정/부정/중립
설명: 1줄

5. 제목
영향: 긍정/부정/중립
설명: 1줄
"""

        res = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 1200},
        )

        return res.text.strip()

    except Exception as e:
        print("Gemini error:", e)
        return "이슈 불러오기 실패"


# =========================
# 6. 메시지 생성 (네가 원하는 최종 포맷)
# =========================
def build_message(data, fear, status, signal, issues):

    now = datetime.now().strftime("%Y-%m-%d")

    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])

    msg = f"""📊 투자 브리핑 ({now})

[오늘 시장 등락]
S&P500: {data['S&P500']['daily']}%
NASDAQ: {data['NASDAQ']['daily']}%
VIX: {data['VIX']['daily']}%
USD/KRW: {data['USDKRW']['daily']}%
환율: {data['USDKRW']['current']}원

[최근 1년 최고점 대비]
S&P500: {data['S&P500']['drawdown']}%
NASDAQ: {data['NASDAQ']['drawdown']}%

[투자 신호]
{signal}

[주요 경제 이슈 TOP5]
{issues}

[종합 판단]
S&P500: -{sp:.1f}%
NASDAQ: -{nd:.1f}%
현재 신호: {signal}

[시장 해설]
S&P500은 최근 고점 대비 {sp:.1f}% 수준 조정 상태입니다.
NASDAQ도 유사한 흐름입니다.
VIX 변동성은 시장 심리를 보여줍니다.
환율은 {data['USDKRW']['current']:.0f}원 수준입니다.
"""

    return msg


# =========================
# 7. 텔레그램 전송
# =========================
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})


# =========================
# 실행
# =========================
data = get_market_data()
fear, status = get_fear_greed()
signal = get_signal(data, fear)
issues = get_economic_issues()

message = build_message(data, fear, status, signal, issues)
send(message)
