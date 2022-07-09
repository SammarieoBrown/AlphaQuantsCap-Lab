import warnings

warnings.filterwarnings("ignore")
from MT5 import *
import numpy as np
import pandas as pd
import warnings

from statsmodels.tsa.arima_model import ARIMA
import time


def sig_ARIMA_model(symbol):
    """ Function for predict the value of tommorow using ARIMA model"""

    train_set = MT5.get_data(symbol, 3500)["close"]

    # Define model
    p = 1
    q = 1
    d = 1
    model = ARIMA(train_set, order=(p, d, q))

    # Fit the model
    model_fit = model.fit(disp=0)

    # Make forecast
    forecast = model_fit.forecast()

    value_forecasted = forecast[0][0]
    buy = train_set.iloc[-1] < value_forecasted
    sell = not buy
    return buy, sell


# True = Live Trading and False = Screener
live = True

if live:
    current_account_info = mt5.account_info()
    print("------------------------------------------------------------------")
    print("Date: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Balance: {current_account_info.balance} USD, \t"
          f"Equity: {current_account_info.equity} USD, \t"
          f"Profit: {current_account_info.profit} USD")
    print("------------------------------------------------------------------")

info_order = {
    "Bitcoin": ["BTCUSD", 0.01]
}

start = datetime.now().strftime("%H:%M:%S")
while True:
    # Verfication for launch
    if datetime.now().weekday() not in (5, 6):
        is_time = datetime.now().strftime("%H:%M:%S") == start  # "23:59:59"
    else:
        is_time = False

    # Launch the algorithm
    if is_time:

        # Open the trades
        for asset in info_order.keys():

            # Initialize the inputs
            symbol = info_order[asset][0]
            lot = info_order[asset][1]

            # Create the signals
            buy, sell = sig_ARIMA_model(symbol)

            # Run the algorithm
            if live:
                MT5.run(symbol, buy, sell, lot)

            else:
                print(f"Symbol: {symbol}\t"
                      f"Buy: {buy}\t"
                      f"Sell: {sell}")
    time.sleep(1)