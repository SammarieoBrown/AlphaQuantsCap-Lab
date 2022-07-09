import time

import pyttsx3
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator
from ta.trend import EMAIndicator
from ta.trend import PSARIndicator
from ta.volatility import BollingerBands
from ta.momentum import WilliamsRIndicator
import talib as TA

from MT5 import *

# audio of system to respond
engine = pyttsx3.init()
rate = engine.getProperty('rate')
engine.setProperty('rate', 250)
volume = engine.getProperty('volume')
engine.setProperty('volume', 1.0)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[2].id)

mt5.initialize()


def market_order(symbol, volume, order_type, **kwargs):
    tick = mt5.symbol_info_tick(symbol)

    order_dict = {'buy': 0,
                  'sell': 1}
    price_dict = {'buy': tick.ask,
                  'sell': tick.bid}

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_dict[order_type],
        "price": price_dict[order_type],
        "deviation": DEVIATION,
        "magic": 100,
        "comment": "Mean-Reversion",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    order_result = mt5.order_send(request)
    comment = order_result.comment

    # print(f"Buy Order Execution Status: {comment}\n"
    # f"Symbol: {assetname}")
    engine.say(f"Buy Order Execution {comment} for {assetname}")
    engine.runAndWait()

    return order_result


def close_order(ticket):
    positions = mt5.positions_get(symbol=symbol)

    for pos in positions:
        tick = mt5.symbol_info_tick(pos.symbol)
        type_dict = {0: 1, 1: 0}  # 0 represents buy, 1 represents sell - inverting order_type to close the position
        price_dict = {0: tick.ask, 1: tick.bid}
        if pos.ticket == ticket:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos.ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": type_dict[pos.type],
                "price": price_dict[pos.type],
                "deviation": DEVIATION,
                "magic": 100,
                "comment": "python close order",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            order_result = mt5.order_send(request)
            comment = order_result.comment

            # print(f"Close Order Execution Status: {comment}\n"
            # f"Symbol: {assetname}")
            engine.say(f"Close Order Execution{comment} for {assetname}")
            engine.runAndWait()

            return order_result

    return 'Ticket does not exist'


def strategy(symbol, timeframe, sma_period):
    df = MT5.get_data(symbol, timeframe, sma_period)

    # ema
    ema100 = EMAIndicator(df.close, window=100).ema_indicator()
    ema20 = EMAIndicator(df.close, window=20).ema_indicator()

    # bollinger band
    upper = BollingerBands(df.close, 20, 2).bollinger_hband()
    lower = BollingerBands(df.close, 20, 2).bollinger_lband()
    middle = BollingerBands(df.close, 20, 2).bollinger_mavg()

    # rsi
    rsi = RSIIndicator(df.close, 14).rsi()

    willy = TA.WILLR(df.high, df.low, df.close, 21)

    distance = (df.close[-1] - ema20[-1])
    RDI = round((100 * (distance * 100) / ema20[-1]), 2)

    signal = ''

    print(f'Relative Distance Index: {RDI}\n'
          f'WilliamR   {round(willy[-1], 2)} \n'
          f'Symbol  {symbol} ')

    if (df.close[-1] > ema100[-1]) and (df.close[-2] < df.close[-1]) and (df.close[-1] > middle[-1]) and (
            df.close[-1] < upper[-1]) and RDI <= 11.00:
        signal = 'buy'
        return signal


    # Sell Logic
    elif (df.close[-1] < ema100[-1]) and (df.close[-2] > middle[-1]) and (df.close[-1] < middle[-1]) and (
            df.close[-1] > lower[-1]) and RDI <= 11.00:
        signal = 'sell'
        return signal

    # Close buy order logic

    elif (df.close[-1] > upper[-1]) or (willy[-1] > -20):
        signal = 'close buy'
        return signal

    # Close Sell order Logic
    elif (df.close[-1] < lower[-1]) or (willy[-1] < -80):
        signal = 'close sell'
        return signal

    else:
        signal = 'No Signal Found !'
        return signal

    return signal


def closeOut(symbol, timeframe, sma_period):
    df = MT5.get_data(symbol, timeframe, sma_period)
    middle = BollingerBands(df.close, 20, 2).bollinger_mavg()

    for tick in mt5.positions_get(symbol=symbol):
        ticket = tick.ticket
        if tick.type == 1 and df.close[-1] > middle[-1]:  # pos.type == 1 represent a sell order
            close_order(ticket)
        elif tick.type == 0 and df.close[-1] < middle[-1]:  # pos.type == 0 represent a buy order
            close_order(ticket)


def isInvested(symbol):
    positionInfo = mt5.positions_get(symbol=symbol)
    if (positionInfo) == ():
        return False
    elif (positionInfo) != ():
        return True


def riskManagement(profit, symbol):
    balance = 1000
    percent = round(((profit * 100) / balance), 2)

    if percent <= -3:
        engine.say(f"Account at high risk. Closing {symbol}positions")
        engine.runAndWait()
        for tick in mt5.positions_get(symbol=symbol):
            ticket = tick.ticket
            close_order(ticket)
        # shut down connection to the MetaTrader 5 terminal
        mt5.shutdown()

    elif percent >= 5:
        engine.say("Target met! Account looks great")
        engine.runAndWait()
    return percent


if __name__ == '__main__':

    # ************* Trade Parameters ***************#
    current_account_info = mt5.account_info()
    account_info_dict = mt5.account_info()._asdict()
    balance = account_info_dict.get('balance')

    US30 = {
        "US30": ["US30.cash", .20, mt5.TIMEFRAME_H1]
    }
    assets = {
        "US30": ["US30.cash", 1.0, mt5.TIMEFRAME_M1],
        "US Oil": ["USOIL.cash", 1.0, mt5.TIMEFRAME_M1],
        "Gold": ["XAUUSD", 1.1, mt5.TIMEFRAME_M1],
        "Etherum": ["ETHUSD", 1.10, mt5.TIMEFRAME_M1],
        "Bitcoin": ["BTCUSD", 1.10, mt5.TIMEFRAME_M1],
        "XAG vs USD": ["XAGUSD", 1.11, mt5.TIMEFRAME_M1],
        "XAU vs USD": ["XAUUSD", 1.11, mt5.TIMEFRAME_M1],
        "AUD vs CAD": ["AUDCAD", 1.11, mt5.TIMEFRAME_M1],
        "AUD vs USD": ["AUDUSD", 1.11, mt5.TIMEFRAME_M1],
        "AUD vs CHF": ["AUDCHF", 1.11, mt5.TIMEFRAME_M1],
        "AUD vs NZD": ["AUDNZD", 1.11, mt5.TIMEFRAME_M1],
        "CAD vs CHF": ["CADCHF", 1.11, mt5.TIMEFRAME_M1],
        "CAD vs JPY": ["CADJPY", 1.11, mt5.TIMEFRAME_M1],
        "EUR vs AUD": ["EURAUD", 1.11, mt5.TIMEFRAME_M1],
        "EUR vs CAD": ["EURAUD", 1.11, mt5.TIMEFRAME_M1],
        "EUR vs CHF": ["EURCHF", 1.11, mt5.TIMEFRAME_M1],
        "EUR vs GBP": ["EURGBP", 1.11, mt5.TIMEFRAME_M1],
        "GBP vs CHF": ["GBPCHF", 1.11, mt5.TIMEFRAME_M1],
        "GBP vs JYP": ["GBPJPY", 1.11, mt5.TIMEFRAME_M1],
        "GBP vs NZD": ["GBPNZD", 1.11, mt5.TIMEFRAME_M1],
        "NZD vs JPY": ["NZDJPY", 1.11, mt5.TIMEFRAME_M1],
        "NZD vs USD": ["NZDUSD", 1.11, mt5.TIMEFRAME_M1],

    }
    gold = {
        "Gold": ["XAUUSD", .10, mt5.TIMEFRAME_D1]}
    crypto = {
        "Etherum": ["ETHUSD", .50, mt5.TIMEFRAME_M30],
        "Bitcoin": ["BTCUSD", .10, mt5.TIMEFRAME_M30],
        "Litecoin": ["LTCUSD", .50, mt5.TIMEFRAME_M30],
        # "Ripple": ["XRPUSD", 1.0, mt5.TIMEFRAME_M30],
    }
    FX = {
        "XAG vs USD": ["XAGUSD", .11, mt5.TIMEFRAME_M15],
        "XAU vs USD": ["XAUUSD", .11, mt5.TIMEFRAME_M15],
        "AUD vs CAD": ["AUDCAD", .11, mt5.TIMEFRAME_M15],
        "AUD vs USD": ["AUDUSD", .11, mt5.TIMEFRAME_M15],
        "AUD vs CHF": ["AUDCHF", .11, mt5.TIMEFRAME_M15],
        "AUD vs NZD": ["AUDNZD", .11, mt5.TIMEFRAME_M15],
        "CAD vs CHF": ["CADCHF", .11, mt5.TIMEFRAME_M15],
        "CAD vs JPY": ["CADJPY", .11, mt5.TIMEFRAME_M15],
        "EUR vs AUD": ["EURAUD", .11, mt5.TIMEFRAME_M15],
        "EUR vs CAD": ["EURAUD", .11, mt5.TIMEFRAME_M15],
        "EUR vs CHF": ["EURCHF", .11, mt5.TIMEFRAME_M15],
        "EUR vs GBP": ["EURGBP", .11, mt5.TIMEFRAME_M15],
        "GBP vs CHF": ["GBPCHF", .11, mt5.TIMEFRAME_M15],
        "GBP vs JYP": ["GBPJPY", .11, mt5.TIMEFRAME_M15],
        "GBP vs NZD": ["GBPNZD", .11, mt5.TIMEFRAME_M15],
        "NZD vs JPY": ["NZDJPY", .11, mt5.TIMEFRAME_M15],
        "NZD vs USD": ["NZDUSD", .11, mt5.TIMEFRAME_M15],
    }
    futures = {
        # "US30": ["US30", .20, mt5.TIMEFRAME_M15],
        "Gold": ["XAUUSD", .10, mt5.TIMEFRAME_M15],
        "Silver": ["XAGUSD", .10, mt5.TIMEFRAME_M15],

    }

    indices = {
        "Gold": ["XAUUSD", .10, mt5.TIMEFRAME_H1],
        "UK100": ["UK100", .10, mt5.TIMEFRAME_M15],
        "US100": ["US100", .10, mt5.TIMEFRAME_M15],
        # "Silver": ["XAGUSD", .10, mt5.TIMEFRAME_M15],

    }

    securites = futures

    DEVIATION = 20  # for order slippage
    SMA = 100  # Simple Moving Average Period

    while True:
        for asset in securites.keys():
            assetname = asset
            # ********************* Initialize the inputs #***************** ****
            symbol = securites[asset][0]
            lot = securites[asset][1]
            TIMEFRAME = securites[asset][2]

            total_positions = mt5.positions_total()
            signal = strategy(symbol, TIMEFRAME, SMA)
            # closeOut(symbol,TIMEFRAME, SMA)
            isOpen = isInvested(symbol=symbol)

            if signal == 'buy':
                if isOpen == False:
                    entry = 'buy'
                    market_order(symbol, lot, entry)
            elif signal == 'sell':
                if isOpen == False:
                    entry = 'sell'
                    market_order(symbol, lot, entry)

            elif signal == 'close buy':
                if isOpen == True:
                    for tick in mt5.positions_get(symbol=symbol):
                        ticket = tick.ticket
                        if tick.type == 0:  # pos.type == 0 represent a buy order
                            close_order(ticket)

            elif signal == 'close sell':
                if isOpen == True:
                    for tick in mt5.positions_get(symbol=symbol):
                        ticket = tick.ticket
                        if tick.type == 1:  # pos.type == 1 represent a sell order
                            close_order(ticket)
            profit = 0

            for tick in mt5.positions_get(symbol=symbol):
                ticket = tick.ticket
                profit = tick.profit

            percent = riskManagement(profit, symbol)

            print(f"Signal: {signal} \n"
                  f"Symbol  {symbol}\n"
                  f"Is invested  {isOpen}\n"
                  f"P&L(%)  {percent}%")
            print("----------------------------------------------------------------------------")

        time.sleep(100)
