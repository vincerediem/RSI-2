import alpaca_trade_api as tradeapi
import pandas as pd
import datetime
import numpy as np
from pytz import timezone
import matplotlib.pyplot as plt
from collections import defaultdict

API_KEY = 'PK3ABIZYDFUBONQF8FCW'
SECRET_KEY = 'sinlF6QYXaoVKA6Y6WFqTyx8zfYyuwrpwgO2WL7v'
BASE_URL = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(API_KEY, SECRET_KEY, base_url=BASE_URL, api_version='v2')

#file_path = input("Enter file path of stock list (must be csv): ")
file_path = r"C:\Users\openshaw\Desktop\CODE\constituents_csv.csv"

df = pd.read_csv(file_path)
stock_list = [str(i) for i in df.iloc[:, 2].dropna().tolist() if str(i).isalpha()]


def get_historical_data(stock, start_date, end_date):
    bars = api.get_bars(stock, tradeapi.rest.TimeFrame.Day, start_date, end_date, limit=None, adjustment='raw').df
    return bars

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

def sell_stock(stock, row, positions, cash, trade_gains_losses, trade_set, index, percent_gains_losses):
    for i, purchase_price in enumerate(positions[stock]['purchase_price']):
        sold_price = row['close']
        
        trade_gains = sold_price * positions[stock]['num_shares'][i] - positions[stock]['purchase_price'][i]
        trade_gains_losses[stock].append(trade_gains)
        percent_gains = trade_gains / positions[stock]['purchase_price'][i]
        percent_gains_losses[stock].append(percent_gains)

    cash += row['close'] * sum(positions[stock]['num_shares'])
    del positions[stock]
    return cash

#function gives you two efficiency metrics, total and average
def eff_metrics(stock, percent_gains_losses, positions_eff):
    for stock, gains in percent_gains_losses.items():
        ave_efficiency = sum(gains) / len(gains)
        total_efficiency = sum(gains)
        #print(f"{stock} has an average efficiency of: %{(ave_efficiency * 100):.2f}"
        #    f" and total efficiency of: %{(total_efficiency * 100):.2f}")
        positions_eff[stock] = {
            'ave eff' : ave_efficiency,
            'tot eff' : total_efficiency
        }

    return ave_efficiency, total_efficiency

def rsi(data, periods=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=periods).mean()
    avg_loss = loss.rolling(window=periods).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def backtest_strategy(stock_list):
    
    start_date = (datetime.datetime.now(timezone('America/New_York')) - datetime.timedelta(days=365)).strftime(
        '%Y-%m-%d')
    end_date = (
        datetime.datetime.now(timezone('America/New_York')) - datetime.timedelta(minutes=15)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')


    trade_gains_losses = defaultdict(list)
    percent_gains_losses = defaultdict(list)
    stock_prices = defaultdict(list)
    rsi_values = defaultdict(list)


    cash = 100000  # Initialize the amount of cash you have
    num_shares = 1
    positions = {}  # The stocks you currently own
    positions_eff = {} # stocks and eff metrics to rank later
    trade_set = 0 #tells you what group of trades you are on for the stock (all stocks in one group are sold together)

    initial_balance = cash  # Keep track of your initial balance

    for stock in stock_list:
        historical_data = get_historical_data(stock, start_date, end_date)
        historical_data['rsi'] = rsi(historical_data['close'])
        
        for index, row in historical_data.iterrows():
            if pd.isna(row['rsi']):
                continue
            #buy and sell conditions
            if row['rsi'] < 30:
                cash = buy_stock(stock, num_shares, row, positions, cash,  index)
            elif stock in positions and row['rsi'] > 65:
                trade_set += 1
                cash = sell_stock(stock, row, positions, cash, trade_gains_losses, trade_set, index, percent_gains_losses)
            stock_prices[stock].append(row['close'])
            rsi_values[stock].append(row['rsi'])

    final_balance = cash

    eff_metrics(stock, percent_gains_losses, positions_eff)

    #sorts all positions in dictionary with eff data
    sorted_positions_eff = sorted(positions_eff.items(), key=lambda x: x[1]['ave eff'], reverse=True)
    #prints sorted positions
    for stock, stock_info in sorted_positions_eff:
        print(f"{stock} ave eff: {stock_info['ave eff'] * 100:.2f}"
            f" tot eff: {stock_info['tot eff'] * 100:.2f}")


    return final_balance, initial_balance


if __name__ == '__main__':
    final_balance, initial_balance = backtest_strategy(stock_list)
