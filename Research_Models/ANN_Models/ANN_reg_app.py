from MT5 import *
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")
import time
import pickle
from joblib import dump, load
import os
from sklearn.preprocessing import StandardScaler
import tensorflow
from keras.models import Sequential
from keras.layers import Dense

path = "C/Users/samma/PycharmProjects/AlphaQuant-Labs/Research_Models/ANN_Models/Models"



# Ex: C:/Desktop/Python_for_finance_and_algorithmic_trading/ChapterN/Models


def ANN():
    # Create the model
    nb_hidden_layer = 1

    # INTIALIZATION SEQUENTIAL MODEL
    alg = Sequential()

    # ADD HIDDEN LAYER
    for _ in range(nb_hidden_layer):
        alg.add(Dense(75, input_shape=(5,), activation="relu"))

    # OUTPUT LAYER DENSE
    alg.add(Dense(1, activation="linear"))

    # COMPILE THE MODEL
    alg.compile(loss="mse", optimizer="adam")
    return alg


def create_model_weights(symbol):
    """ Weights for Linear regression on the percentage change"""
    # Import the data
    data = MT5.get_data(symbol, 3500)[["close"]].pct_change(1)

    # Create new variable
    data.columns = ["returns"]

    # Features engeeniring
    data["returns t-1"] = data[["returns"]].shift(1)

    # Mean of returns
    data["mean returns 15"] = data[["returns"]].rolling(15).mean().shift(1)
    data["mean returns 60"] = data[["returns"]].rolling(60).mean().shift(1)

    # Volatility of returns
    data["volatility returns 15"] = data[["returns"]].rolling(15).std().shift(1)
    data["volatility returns 60"] = data[["returns"]].rolling(60).std().shift(1)

    # Split the data
    data = data.dropna()
    split = int(0.80 * len(data))

    # Train set creation
    X_train = data[["returns t-1", "mean returns 15", "mean returns 60",
                    "volatility returns 15",
                    "volatility returns 60"]].iloc[:split]
    y_train = data[["returns"]].iloc[:split]

    # Initialize the class
    sc = StandardScaler()

    # Standardize the data
    X_train = sc.fit_transform(X_train)

    alg = ANN()

    # TRAINING
    alg.fit(X_train, y_train, epochs=13, batch_size=32, verbose=1)

    # Save the model
    alg.save_weights(os.path.join(path, f"Models/ANN_reg_{symbol}"))


def ANN_cla_sig(symbol):
    """ Function for predict the value of tommorow using ARIMA model"""

    # Create the weights if there is not in the folder
    try:
        alg = ANN()
        alg.load_weights(os.path.join(path, f"Models/ANN_reg_{symbol}"))
    except:
        create_model_weights(symbol)
        alg = ANN()
        alg.load_weights(os.path.join(path, f"Models/ANN_reg_{symbol}"))

    # Take the lastest percentage of change
    data = MT5.get_data(symbol, 3500)[["close"]].pct_change(1)
    # Create new variable
    data.columns = ["returns"]

    # Features engeeniring

    # Mean of returns
    data["mean returns 15"] = data[["returns"]].rolling(15).mean()
    data["mean returns 60"] = data[["returns"]].rolling(60).mean()

    # Volatility of returns
    data["volatility returns 15"] = data[["returns"]].rolling(15).std()
    data["volatility returns 60"] = data[["returns"]].rolling(60).std()

    X = data[["returns", "mean returns 15", "mean returns 60",
              "volatility returns 15",
              "volatility returns 60"]].iloc[-1:, :].values

    # Find the signal
    prediction = alg.predict(X)
    prediction = np.where(prediction == 0, -1, 1)
    buy = prediction[0][0] > 0
    sell = not buy

    return buy, sell


# True = Live Trading and False = Screener
live = False

if live:
    current_account_info = mt5.account_info()
    print("------------------------------------------------------------------")
    print("Date: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"Balance: {current_account_info.balance} USD, \t"
          f"Equity: {current_account_info.equity} USD, \t"
          f"Profit: {current_account_info.profit} USD")
    print("------------------------------------------------------------------")

info_order = {
    "Bitcoin": ["BTCUSD", .10]
}

start = datetime.now().strftime("%H:%M:%S")
while True:
    """# Verfication for launch
    if datetime.now().weekday() not in (5, 1):
        is_time = datetime.now().strftime("%H:%M:%S") == start  # "23:59:59"
    else:
        is_time = False

    # Launch the algorithm
    if is_time:"""

    # Open the trades
    for asset in info_order.keys():

        # Initialize the inputs
        symbol = info_order[asset][0]
        lot = info_order[asset][1]

        # Create the signals
        buy, sell = ANN_cla_sig(symbol)
        print(buy,sell)

        # Run the algorithm
        if live:
            MT5.run(symbol, buy, sell, lot)

        else:
            print(f"Symbol: {symbol}\t"
                  f"Buy: {buy}\t"
                  f"Sell: {sell}")
        time.sleep(1)
