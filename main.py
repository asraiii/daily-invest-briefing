import os
import requests
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# -----------------------------
# 1. 시장 데이터 수집
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

            current_price = 0
            
            if current_price == 0:
                current_price = hist_1y["Close"].dropna().iloc[-1]
    
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
    
def get_fear_greed():

    try:

        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

        response = requests.get(url, timeout=10)

        score = response.json()["fear_and_greed"]["score"]

        if score >= 75:
            status = "극도의 탐욕"
        elif score >= 55:
            status = "탐욕"
        elif score >= 45:
            status = "중립"
        elif score >= 25:
            status = "공포"
        else:
            status = "극도의 공포"

        return score, status

    except Exception as e:
        print("Fear & Greed Error:", e)
        return 0, "확인불가"
        
# -----------------------------
# 2. 간단 점수 시스템
# -----------------------------


def get_market_comment(
    data,
    fear_score,
    fear_status
):

    comments = []

    
    sp = abs(data["S&P500"]["drawdown"])
    nd = abs(data["NASDAQ"]["drawdown"])
    vix = data["VIX"]["daily"]
    usdkrw = data["USDKRW"]["current"]

    # Fear & Greed 추가
    comments.append(
        f"Fear & Greed 지수는 {fear_score}점으로 현재 '{fear_status}' 구간입니다."
    )

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
    vix = data["VIX"]["current"]  # 이걸 써야 정상

if vix >= 25:
    comments.append("시장 변동성이 매우 높은 구간입니다.")
elif vix >= 18:
    comments.append("변동성이 다소 상승한 상태입니다.")
else:
    comments.append("변동성이 안정적인 구간입니다.")

    
    # 환율 코멘트

    if usdkrw >= 1400:

        comments.append(
            f"원달러 환율은 {usdkrw:.0f}원 수준으로 높은 편이며 해외자산 매수 시 환율 부담이 존재합니다."
        )

    elif usdkrw >= 1300:

        comments.append(
            f"원달러 환율은 {usdkrw:.0f}원 수준으로 다소 높은 구간입니다."
        )

    elif usdkrw >= 1200:

        comments.append(
            f"원달러 환율은 {usdkrw:.0f}원 수준으로 평균 범위에 위치하고 있습니다."
        )

    else:

        comments.append(
            f"원달러 환율은 {usdkrw:.0f}원 수준으로 비교적 낮은 편이며 달러 자산 매수에 유리한 환경입니다."
        )
        
    # 투자 전략
    comments.append("")
    comments.append("장기 투자 관점에서는 VOO, QQQM, SCHD 적립식을 유지하는 전략이 유효합니다.")

    return "\n".join(comments)


# -----------------------------
# 투자 신호 생성
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
# 경제 이슈 TOP5
# -----------------------------


def get_economic_issues():

    try:

        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = """
최근 24시간 내 가장 중요한 경제·금융 변화 3개를 작성해줘.

형식:

1. 제목

무슨 일:
시장영향:

2. 제목

무슨 일:
시장영향:

3. 제목

무슨 일:
시장영향:

반드시 최근 24시간 기준.
짧고 핵심만 작성.
"""

        response = model.generate_content(
    prompt,
    generation_config={
        "temperature": 0.3,
        "max_output_tokens": 800
    }
)

        return response.text[:1500]

    except Exception as e:

        print("Gemini Error:", e)

        return "경제 이슈를 불러오지 못했습니다."


# -----------------------------
# 종합 판단
# -----------------------------


def get_market_summary(
    signal,
    fear_score,
    fear_status,
    data
):

    sp = abs(data["S&P500"]["drawdown"])

    summary = f"""
Fear & Greed 지수는 {fear_score}점 ({fear_status}) 입니다.

S&P500은 최근 최고점 대비 {sp:.1f}% 하락 상태입니다.

현재 투자 신호는 {signal} 입니다.

장기 투자자는 VOO·QQQM·SCHD 적립식을 유지하는 전략이 적절합니다.
"""

    return summary.strip()


# -----------------------------
# 3. 브리핑 생성
# -----------------------------


def create_message(
    data,
    market_comment,
    signal,
    economic_issues,
    market_summary,
    fear_score,
    fear_status
):

    now = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"📊 투자 브리핑 ({now})",
        "",

        "[오늘 시장 등락]",
        f"S&P500 : {data['S&P500']['daily']}%",
        f"NASDAQ : {data['NASDAQ']['daily']}%",
        f"SCHD : {data['SCHD']['daily']}%",
        f"VIX : {data['VIX']['daily']}%",
        f"USD/KRW : {data['USDKRW']['daily']}%",
        f"환율 : {round(data['USDKRW']['current'])}원",
        f"Fear & Greed : {fear_score}점 ({fear_status})",
        "",

        "[최근 최고점 대비]",
        f"S&P500 : {data['S&P500']['drawdown']}%",
        f"NASDAQ : {data['NASDAQ']['drawdown']}%",
        f"SCHD : {data['SCHD']['drawdown']}%",
        "",
        
        "[투자 신호]",
        signal,
        "",

        "[24시간 내 중요 변화 TOP3]",
        economic_issues,
        "",

        "[종합 판단]",
        market_summary,
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

fear_score, fear_status = get_fear_greed()

signal = get_invest_signal(
    data,
    fear_score
)

market_comment = get_market_comment(
    data,
    fear_score,
    fear_status
)

economic_issues = get_economic_issues()

market_summary = get_market_summary(
    signal,
    fear_score,
    fear_status,
    data
)

message = create_message(
    data,
    market_comment,
    signal,
    economic_issues,
    market_summary,
    fear_score,
    fear_status
)

send_telegram(message)
