import alpaca_trade_api as tradeapi
import pandas as pd
import datetime
from pytz import timezone
import matplotlib.pyplot as plt
from collections import defaultdict
import plotly.graph_objs as go
from plotly.subplots import make_subplots

API_KEY = 'PK3ABIZYDFUBONQF8FCW'
SECRET_KEY = 'sinlF6QYXaoVKA6Y6WFqTyx8zfYyuwrpwgO2WL7v'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL, api_version='v2')

def plot_graphs(historical_data, buy_dates, buy_prices, sell_dates, sell_prices, start_date, end_date):
    close_prices = historical_data['close']
    date_range = historical_data.index

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Stock price", "RSI"), vertical_spacing=0.05, row_heights=[0.6, 0.4])

    # Stock prices
    fig.add_trace(go.Scatter(x=date_range, y=close_prices, mode='lines', name='Stock Price'), row=1, col=1)

    # RSI values
    rsi_values = historical_data['rsi']
    fig.add_trace(go.Scatter(x=date_range, y=rsi_values, mode='lines', name='RSI'), row=2, col=1)

    # RSI 35 and 70 lines
    fig.add_trace(go.Scatter(x=date_range, y=[30]*len(rsi_values), mode='lines', name='RSI 35', line=dict(color='green', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=date_range, y=[65]*len(rsi_values), mode='lines', name='RSI 70', line=dict(color='red', width=1)), row=2, col=1)

    # Buy dates and prices
    for stock, dates in buy_dates.items():
        fig.add_trace(go.Scatter(x=dates, y=buy_prices[stock], mode='markers', name=f'Buy ({stock})', marker=dict(color='limegreen', symbol='triangle-up')), row=1, col=1)
        rsi_buy_values = rsi_values.loc[dates]
        fig.add_trace(go.Scatter(x=dates, y=rsi_buy_values, mode='markers', name=f'Buy ({stock})', marker=dict(color='limegreen', symbol='triangle-up')), row=2, col=1)


    # Sell dates and prices
    for stock, dates in sell_dates.items():
        fig.add_trace(go.Scatter(x=dates, y=sell_prices[stock], mode='markers', name=f'Sell ({stock})', marker=dict(color='red', symbol='triangle-down')), row=1, col=1)
        rsi_sell_values = rsi_values.loc[dates]
        fig.add_trace(go.Scatter(x=dates, y=rsi_sell_values, mode='markers', name=f'Sell ({stock})', marker=dict(color='red', symbol='triangle-down')), row=2, col=1)


    # Update hover interaction
    fig.update_layout(hovermode='x unified')

    fig.update_layout(height=600, width=800, title_text='Stock Prices and RSI')
    return fig



def stock_list(input_str):
    # Split the string and convert each value to integer, creating an array
    stock_list = input_str.split()
    return stock_list

def get_historical_data(stock, start_date, end_date):
    bars = api.get_bars(stock, tradeapi.rest.TimeFrame.Day, start_date, end_date, limit=None, adjustment='raw').df
    return bars

def set_timeframe():
    start_date = (datetime.datetime.now(timezone('America/New_York')) - datetime.timedelta(days=365)).strftime(
        '%Y-%m-%d')
    end_date = (
        datetime.datetime.now(timezone('America/New_York')) - datetime.timedelta(minutes=15)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    
    return start_date, end_date

#buy condition as function
def buy_condition(row):
    buy_condition_met = False

    if row['rsi'] < 30:
        buy_condition_met = True

    return buy_condition_met

#sell condition
def sell_condition(stock, positions, row):
    sell_condition_met = False

    if stock in positions and row['rsi'] > 65:
        sell_condition_met = True
    
    return sell_condition_met

def buy_stock(stock, num_shares, row, positions, cash, index):
    cash -= row['close'] * num_shares
    if stock not in positions:
        positions[stock] = {
            'num_shares': [num_shares],
            #purchase price includes price of all shares, this will change if I change share amount
            'purchase_price': [row['close'] * num_shares],
            'purchase_date': [index],
            'buy_price' : [row['close']]
        }
    else:
        positions[stock]['num_shares'].append(num_shares)
        positions[stock]['purchase_price'].append(row['close'] * num_shares)
        positions[stock]['buy_price'].append(row['close'])
        positions[stock]['purchase_date'].append(index)
    
    return cash

def sell_stock(stock, row, positions, cash, trade_gains_losses, positions_sold, index, percent_gains_losses, trade_set):
    for i, purchase_price in enumerate(positions[stock]['purchase_price']):
        sold_price = row['close']
        sold_date = index
        
        trade_gains = sold_price * positions[stock]['num_shares'][i] - positions[stock]['purchase_price'][i]
        trade_gains_losses[stock].append(trade_gains)
        percent_gains = trade_gains / positions[stock]['purchase_price'][i]
        percent_gains_losses[stock].append(percent_gains)

        #dictionary with info about stocks once theyve been sold
        if stock not in positions_sold:
            positions_sold[stock] = {
            'sold_price': [sold_price],
            'purchase_price': [positions[stock]['purchase_price'][i]],
            'purchase_date': [positions[stock]['purchase_date'][i]],
            'sold_date' : [sold_date],
            'buy_price' : [row['close']],
            'percent_gain' : [percent_gains],
            'trade_gains' : [trade_gains],
            'trade_set' : [trade_set],
            'trade_count' : [i+1]  # Add trade_count to track the trade count within the trade set
            }
        else:
            positions_sold[stock]['sold_price'].append(sold_price)
            positions_sold[stock]['purchase_price'].append(positions[stock]['purchase_price'][i])
            positions_sold[stock]['purchase_date'].append(positions[stock]['purchase_date'][i])
            positions_sold[stock]['sold_date'].append(sold_date)
            positions_sold[stock]['buy_price'].append(row['close'])
            positions_sold[stock]['percent_gain'].append(percent_gains)
            positions_sold[stock]['trade_gains'].append(trade_gains)
            positions_sold[stock]['trade_set'].append(trade_set)
            positions_sold[stock]['trade_count'].append(i+1)
                
    cash += row['close'] * sum(positions[stock]['num_shares'])
    del positions[stock]
    return cash

#makes trades a list of dicts per trade, and creates a dataframe
def trade_metrics(stock, positions_sold):
    trades_metrics = []
    if positions_sold.get(stock) is not None:  # Only proceed if the stock exists in positions_sold
        for i, _ in enumerate(positions_sold[stock]['purchase_price']):
            trade = {
                'trade_id': f"{positions_sold[stock]['trade_set'][i]}.{positions_sold[stock]['trade_count'][i]}", #trade set and number of trade
                'stock': stock.capitalize(),
                'purchase_date': positions_sold[stock]['purchase_date'][i].date(),
                'purchase_price': positions_sold[stock]['buy_price'][i],
                'sold_date': positions_sold[stock]['sold_date'][i].date(),
                'sold_price': positions_sold[stock]['sold_price'][i],
                'trade_gains': positions_sold[stock]['trade_gains'][i],
                'percent_gain': positions_sold[stock]['percent_gain'][i] * 100
            }
            trades_metrics.append(trade)
    closed_df = pd.DataFrame(trades_metrics)
    return trades_metrics, closed_df
    
#function to display final metrics
def final_metrics(final_balance, initial_balance, stock, positions, trade_gains_losses, percent_gains_losses):
    final_metrics = {}


    for stock in positions:
        for i, price in enumerate(positions[stock]['purchase_price']):
            final_metrics[f"{stock}_final_share_price"] = price / positions[stock]['num_shares'][i]

    #total gains/losses
    for stock in trade_gains_losses:
        final_metrics[f"{stock}_total_gains_losses"] = sum(trade_gains_losses[stock])
        final_metrics[f'{stock}_num_of_trades'] = len(trade_gains_losses[stock])
        final_metrics[f"{stock}_ave_gains_losses"] = final_metrics[f"{stock}_total_gains_losses"] / final_metrics[f'{stock}_num_of_trades']

    for stock, gains in percent_gains_losses.items():
        final_metrics[f'{stock}_ave_efficiency'] = sum(gains) / len(gains)
        final_metrics[f'{stock}_total_efficiency'] = sum(gains)

    #portfolio change metrics
    final_metrics['initial_balance'] = initial_balance
    final_metrics['final_balance'] = final_balance
    final_metrics['profit_percent'] = ((final_balance - initial_balance) / initial_balance) * 100
    final_metrics['profit_absolute'] = final_balance - initial_balance
    return final_metrics


def rsi(data, periods=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=periods).mean()
    avg_loss = loss.rolling(window=periods).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def backtest_strategy(stock_list):

    start_date, end_date = set_timeframe()

    trade_gains_losses = defaultdict(list)
    percent_gains_losses = defaultdict(list)
    stock_prices = defaultdict(list)
    rsi_values = defaultdict(list)

    buy_dates = defaultdict(list)
    buy_prices = defaultdict(list)
    sell_dates = defaultdict(list)
    sell_prices = defaultdict(list)


    cash = 100000  # Initialize the amount of cash you have
    num_shares = 1
    positions = {}  # The stocks you currently own
    positions_sold = {}
    trade_set = 0 #tells you what group of trades you are on for the stock (all stocks in one group are sold together)

    initial_balance = cash  # Keep track of your initial balance

    for stock in stock_list:
        historical_data = get_historical_data(stock, start_date, end_date)
        historical_data['rsi'] = rsi(historical_data['close'])
        
        for index, row in historical_data.iterrows():
            if pd.isna(row['rsi']):
                continue
            #buy and sell conditions
            if buy_condition(row):
                cash = buy_stock(stock, num_shares, row, positions, cash,  index)
                buy_dates[stock].append(pd.to_datetime(index))
                buy_prices[stock].append(row['close'])
            elif sell_condition(stock, positions, row):
                trade_set += 1
                cash = sell_stock(stock, row, positions, cash, trade_gains_losses, positions_sold, index, percent_gains_losses, trade_set)
                sell_dates[stock].append(pd.to_datetime(index))
                sell_prices[stock].append(row['close'])
            stock_prices[stock].append(row['close'])
            rsi_values[stock].append(row['rsi'])
    
    #debugg pannel:
    fig = plot_graphs(historical_data, buy_dates, buy_prices, sell_dates, sell_prices, start_date, end_date)
    #end

    final_balance = cash

    #create dataframe of positions dict
    open_df=pd.DataFrame(positions)

    return final_balance, initial_balance, stock, positions, trade_gains_losses, positions_sold, open_df, percent_gains_losses, fig


if __name__ == '__main__':
    stocks = input("Enter stocks separated by space: ")
    final_balance, initial_balance, stock, positions, trade_gains_losses, positions_sold, open_df, percent_gains_losses, fig = backtest_strategy(stock_list(stocks))
    trades_metrics, closed_df = trade_metrics(stock, positions_sold)
    final_metrics(final_balance, initial_balance, stock, positions, trade_gains_losses, percent_gains_losses)