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
            hist = ticker.history(period="5d")

            if len(hist) >= 2:
                close = hist["Close"].tail(2).values
                change = ((close[-1] - close[-2]) / close[-2]) * 100
                data[name] = round(float(change), 2)
            else:
                data[name] = 0.0

        except Exception as e:
            print(f"{name} error:", e)
            data[name] = 0.0

    return data
