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
from keras.models import Sequential
from keras.layers import Dense, LSTM, Dropout

path = "C:/Users/samma/PycharmProjects/AlphaQuant-Labs/Research_Models/RNN_Models/Models"


# Ex: C:/Desktop/Python_for_finance_and_algorithmic_trading/ChapterN/Models


def X_3d_RNN(X_s, y_s, lag):
    # Simple verification
    if len(X_s) != len(y_s):
        print("Warnings")

    # Create the X_train
    X_train = []
    for variable in range(0, X_s.shape[1]):
        X = []
        for i in range(lag, X_s.shape[0]):
            X.append(X_s[i - lag:i, variable])
        X_train.append(X)
    X_train, np.array(X_train)
    X_train = np.swapaxes(np.swapaxes(X_train, 0, 1), 1, 2)

    # Create the y_train
    y_train = []
    for i in range(lag, y_s.shape[0]):
        y_train.append(y_s[i, :].reshape(-1, 1).transpose())
    y_train = np.concatenate(y_train, axis=0)
    return X_train, y_train


def RNN():
    # Create the model
    number_hidden_layer = 15
    number_neurons = 10
    loss = "mse"
    metrics = ["mae"]
    activation = "linear"
    optimizer = "adam"
    pct_dropout = 0.5

    # INITIALIZATION OF THE DATA
    model = Sequential()

    # ADD LSTM LAYER
    model.add(LSTM(units=number_neurons, return_sequences=True, input_shape=(15, 5,)))

    # ADD DROPOUT LAYER
    model.add(Dropout(pct_dropout))

    # LOOP WHICH ADD LSTM AND DROPPOUT LAYER
    for _ in range(number_hidden_layer):
        model.add(LSTM(units=number_neurons, return_sequences=True))
        model.add(Dropout(pct_dropout))

    # LAST LSTM LAYER BUT WITH return_sequences = False
    model.add(LSTM(units=number_neurons, return_sequences=False))

    # ADD DROPOUT LAYER
    model.add(Dropout(pct_dropout))

    # OUTPUT DENSE LAYER
    model.add(Dense(1, activation=activation))

    # COMPILE THE MODEL
    model.compile(loss=loss, optimizer=optimizer, metrics=metrics)
    return model


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
    y_train = np.round(data[["returns"]].iloc[:split] + 0.5)

    # Initialize the class
    sc = StandardScaler()

    # Standardize the data
    X_train = sc.fit_transform(X_train)

    lag = 15
    X_train, y_train = X_3d_RNN(X_train, y_train.values, 15)

    alg = RNN()

    # TRAINING
    alg.fit(X_train, y_train, epochs=1, batch_size=32, verbose=1)

    # Save the model
    print("Train the model because there are no existed weights")
    alg.save_weights(os.path.join(path, f"Models/RNN_reg_{symbol}"))


def RNN_reg_sig(symbol):
    """ Function for predict the value of tommorow using ARIMA model"""

    # Create the weights if there is not in the folder
    try:
        alg = RNN()
        alg.load_weights(os.path.join(path, f"Models/RNN_reg_{symbol}"))
    except:
        create_model_weights(symbol)
        alg = RNN()
        alg.load_weights(os.path.join(path, f"Models/RNN_reg_{symbol}"))

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
              "volatility returns 60"]]

    # Initialize the class
    sc = StandardScaler()

    # Standardize the data
    X = sc.fit_transform(X)

    y = data[["returns t-1"]]

    X, _ = X_3d_RNN(X, y.values, 15)

    X = X[-1:, :, :]

    # Find the signal
    prediction = alg.predict(X)
    buy = prediction[0][0] > 0
    sell = not buy

    return buy, sell


# True = Live Trading and Flse = Screener
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
    "BTCUSD": ["BTCUSD", .10]
}

start = datetime.now().strftime("%H:%M:%S")
while True:
    """# Verfication for launch
    if datetime.now().weekday() not in (5, 1):
        is_time = datetime.now().strftime("%H:%M:%S") == start  # "23:59:59"
    else:
        is_time = False

    # Launch the algorithm
    if is_time:

    # Open the trades"""
    for asset in info_order.keys():

        # Initialize the inputs
        symbol = info_order[asset][0]
        lot = info_order[asset][1]

        # Create the signals
        buy, sell = RNN_reg_sig(symbol)

        # Run the algorithm
        if live:
            MT5.run(symbol, buy, sell, lot)

        else:
            print(f"Symbol: {symbol}\t"
                  f"Buy: {buy}\t"
                  f"Sell: {sell}")
    time.sleep(1)
