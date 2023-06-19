#file to contain lots of functions that I would like to call for RSI purposes
#not specific to stategies unless otherwise stated

def get_historical_data(stock, start_date, end_date):
    bars = api.get_bars(stock, tradeapi.rest.TimeFrame.Day, start_date, end_date, limit=None, adjustment='raw').df
    return bars

def rsi(data, periods=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=periods).mean()
    avg_loss = loss.rolling(window=periods).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def eff_metrics(stock, percent_gains_losses):
    for stock, gains in percent_gains_losses.items():
        ave_efficiency = sum(gains) / len(gains)
        total_efficiency = sum(gains)
        print(f"{stock} has an average efficiency of: %{(ave_efficiency * 100):.2f}")
        print(f"{stock} has an total efficiency of: %{(total_efficiency * 100):.2f}")
        print(f"numer of trades: {len(gains)}")

    return ave_efficiency, total_efficiency