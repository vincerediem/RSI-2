import alpaca_trade_api as tradeapi
import pandas as pd
import datetime
from pytz import timezone
import matplotlib.pyplot as plt
from collections import defaultdict

API_KEY = 'PK3ABIZYDFUBONQF8FCW'
SECRET_KEY = 'sinlF6QYXaoVKA6Y6WFqTyx8zfYyuwrpwgO2WL7v'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL, api_version='v2')

def stock_list():
    input_str = input("Enter stocks separated by space: ")
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
            'sold_date' : [index],
            'buy_price' : [row['close']],
            'percent_gain' : [percent_gains],
            'trade_gains' : [trade_gains]
            }
        else:
            positions_sold[stock]['sold_price'].append(sold_price)
            positions_sold[stock]['purchase_price'].append(positions[stock]['purchase_price'][i])
            positions_sold[stock]['purchase_date'].append(positions[stock]['purchase_date'][i])
            positions_sold[stock]['sold_date'].append(index)
            positions_sold[stock]['buy_price'].append(row['close'])
            positions_sold[stock]['percent_gain'].append(percent_gains)
            positions_sold[stock]['trade_gains'].append(trade_gains)
                
    cash += row['close'] * sum(positions[stock]['num_shares'])
    del positions[stock]
    return cash

def trade_metrics(stock, row, positions, cash, trade_gains_losses, trade_set, index, percent_gains_losses, positions_sold):
    for i, _ in enumerate(positions_sold[stock]['purchase_price']):
        print(f"Trade {trade_set}.{i+1} of {stock.capitalize()}:")
        print(f"Purchased on {positions_sold[stock]['purchase_date'][i].date()} for ${positions_sold[stock]['buy_price'][i]:.2f}")
        print(f"Sold on {positions_sold[stock]['sold_date'][i].date()} for ${positions_sold[stock]['sold_price'][i]:.2f}")
        print(f"Trade gains from {stock} trade {trade_set}.{i + 1}, ${float(positions_sold[stock]['trade_gains'][i]):.2f}")
        print(f"You made %{(positions_sold[stock]['percent_gain'][i] * 100):.2f}")
        print(f" ")
        #displays metrics then deletes position
    
#function to display final metrics
def display_final_metrics(final_balance, initial_balance, stock, row, positions, cash, trade_gains_losses):
    for stock in positions:
        for i, price in enumerate(positions[stock]['purchase_price']):
            print(f"You have shares worth ${price / positions[stock]['num_shares'][i]} at end of period")
    for stock in trade_gains_losses:
        print(f"Total gains/losses for {stock}: {sum(trade_gains_losses[stock]):.2f}")
    print(f"Initial account balance: ${initial_balance:.2f}")
    print(f"Final account balance: ${final_balance:.2f}")
    print(f"You made: {((final_balance - initial_balance) / initial_balance) * 100:.2f}%")
    print(f"You made: {(final_balance - initial_balance):.2f}$")


def rsi(data, periods=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=periods).mean()
    avg_loss = loss.rolling(window=periods).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def backtest_strategy(stock_list):
    
    #set stocklist function
    stock_list = stock_list()

    start_date, end_date = set_timeframe()

    trade_gains_losses = defaultdict(list)
    percent_gains_losses = defaultdict(list)
    stock_prices = defaultdict(list)
    rsi_values = defaultdict(list)


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
            elif sell_condition(stock, positions, row):
                trade_set += 1
                cash = sell_stock(stock, row, positions, cash, trade_gains_losses, positions_sold, index, percent_gains_losses, trade_set)
                trade_metrics(stock, row, positions, cash, trade_gains_losses, trade_set, index, percent_gains_losses, positions_sold)
            stock_prices[stock].append(row['close'])
            rsi_values[stock].append(row['rsi'])

    final_balance = cash

    return final_balance, initial_balance, stock, row, positions, cash, trade_gains_losses



if __name__ == '__main__':
    final_balance, initial_balance, stock, row, positions, cash, trade_gains_losses = backtest_strategy(stock_list)
    display_final_metrics(final_balance, initial_balance, stock, row, positions, cash, trade_gains_losses)