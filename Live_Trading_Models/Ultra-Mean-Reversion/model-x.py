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
import telegram_send as tele

mt5.initialize()

def market_order(symbol, volume, order_type, **kwargs):
    """
    The function takes in a symbol, volume, and order type (buy or sell) and returns an order result.

    :param symbol: The symbol you want to trade
    :param volume: The number of shares to buy
    :param order_type: This is the type of order you want to place. It can be either buy or sell
    :return: The order_result is being returned.
    """
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
        "comment": "Adj.Mean-Reversion",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    order_result = mt5.order_send(request)
    comment = order_result.comment

    print(f"Buy Order Execution Status: {comment}\n")

    return order_result
def close_order(ticket):
    """
    It takes a ticket number as an argument, finds the position with that ticket number, and closes it

    :param ticket: The ticket number of the position you want to close
    :return: The order_result is being returned.
    """
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
                "comment": "Adj.Mean-Reversion",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            order_result = mt5.order_send(request)
            comment = order_result.comment

            print(f"Close Order Execution Status: {comment}\n")



            return order_result

    return 'Ticket does not exist'
def RSI(symbol, timeframe, sma_period):
    df = MT5.get_data(symbol, timeframe, sma_period)


    # rsi
    rsi = RSIIndicator(df.close, 17).rsi()

    return rsi.iloc[-1]
def strategy(symbol, timeframe, sma_period):
    """
    If the price is above the middle Bollinger Band and the price is increasing, then buy. If the price is below the middle
    Bollinger Band and the price is decreasing, then sell

    :param symbol: The symbol you want to run the strategy on
    :param timeframe: The timeframe you want to use for the strategy
    :param sma_period: The number of candles to use for the SMA calculation
    :return: a string value of either 'buy', 'sell', or 'None'
    """

    df = MT5.get_data(symbol, timeframe, sma_period)



    # ema
    ema100 = EMAIndicator(df.close, window=100).ema_indicator()
    ema20 = EMAIndicator(df.close, window=20).ema_indicator()

    # bollinger band
    upper = BollingerBands(df.close, 30, 2.3).bollinger_hband()
    lower = BollingerBands(df.close, 30, 2.3).bollinger_lband()
    middle = BollingerBands(df.close, 30, 2.3).bollinger_mavg()

    # rsi
    rsi = RSI(symbol, timeframe, sma_period)


    willy = TA.WILLR(df.high, df.low, df.close, 21)

    distance = (df.close[-1] - ema20[-1])
    RDI = round((100 * (distance * 100) / ema20[-1]), 2)

    signal = ''

    # SELL Logic
    if (df.close.iloc[-2] < middle.iloc[-1]) and (df.close.iloc[-1] > middle.iloc[-1]) and (df.close.iloc[-1] > lower.iloc[-1]):
        signal = 'buy'
        return signal

    # BUY Logic
    elif(df.close.iloc[-2] > middle.iloc[-1]) and (df.close.iloc[-1] < middle.iloc[-1]) and (df.close.iloc[-1] < upper.iloc[-1]):
        signal = 'sell'
        return signal
    else:
        signal = None


    return signal
def closeOut(symbol,timeframe,sma_period):
    """
    If the RSI is above 70 and the position is a buy order, close the order. If the RSI is below 40 and the position is a
    sell order, close the order

    :param symbol: The currency pair you want to trade
    :param timeframe: The timeframe of the data you want to use
    :param sma_period: The number of candles to use for the SMA calculation
    """

    df = MT5.get_data(symbol, timeframe, sma_period)
    middle = BollingerBands(df.close, 20, 2).bollinger_mavg()
    upper = BollingerBands(df.close, 20, 2).bollinger_hband()
    lower = BollingerBands(df.close, 20, 2).bollinger_lband()
    rsi = RSIIndicator(df.close, 14).rsi()

    for tick in mt5.positions_get(symbol=symbol):
        ticket = tick.ticket
        if tick.type == 1 and rsi.iloc[-1]<10:  # pos.type == 1 represent a sell order
            close_order(ticket)
        elif tick.type == 0 and rsi.iloc[-1] > 70:  # pos.type == 0 represent a buy order
            close_order(ticket)
def trail_sl(symbol, timeframe, sma_period, stop_loss,max_stop_loss_distance, trail_amount,**kwargs):
    """
    It checks if the distance between the current price and the stoploss is greater than the maximum distance allowed, if
    yes, it updates the stoploss

    :param symbol: The symbol you want to trade
    :param timeframe: The timeframe you want to use for the SMA
    :param sma_period: The period of the SMA indicator
    :return: The result of the function is the result of the order_send function.
    """

    df = MT5.get_data(symbol, timeframe, sma_period)

    profit = 0
    ticket = 0

    # fetch ticket from symbol
    for tick in mt5.positions_get(symbol=symbol):
        ticket = tick.ticket
        profit = tick.profit
        position = mt5.positions_get(ticket=ticket)
        # get position data
        order_type = tick.type
        price_current = tick.price_current
        price_open = tick.price_open
        sl = tick.sl
        dist_from_sl = abs(round(price_current - sl, 6))
        pips = abs(round(price_current - price_open, 6))*100

        trailing_stop = {
            'Symbol': symbol,
            'Open Price': price_open,
            'Pips': pips,
            'Current Price': price_current,
            'SL Distance': dist_from_sl,

        }
        trailing_stop = pd.DataFrame.from_dict(trailing_stop, orient='index').T
        trailing_stop = str(trailing_stop)

        print(trailing_stop)

        if dist_from_sl >= max_stop_loss_distance:
            # calculating new sl
            if sl != 0.0:
                if order_type == 0 and price_current > 0:  # 0 stands for BUY
                    new_sl = sl + trail_amount

                elif order_type == 1 and price_current > 0:  # 1 stands for SELL
                    new_sl = sl - trail_amount

            elif sl == 0.0:
                # setting default SL if the is no SL on the symbol
                new_sl = price_open - stop_loss if order_type == 0 else price_open + stop_loss

            request = {
                'action': mt5.TRADE_ACTION_SLTP,
                'position': tick.ticket,
                'sl': new_sl,
            }

            result = mt5.order_send(request)

            return result
def isInvested(symbol):
    """
    If the positionInfo variable is empty, then the function returns False. If the positionInfo variable is not empty, then
    the function returns True.

    :param symbol: The symbol of the asset you want to check
    :return: A list of dictionaries.
    """

    positionInfo = mt5.positions_get(symbol=symbol)
    if (positionInfo) == ():
        return False
    elif (positionInfo) != ():
        return True
def riskManagement(profit, symbol):
    """
    If the account is at risk, close all positions

    :param profit: The profit of the account
    :param symbol: The currency pair you want to trade
    """

    balance = 25000
    percent = round(((profit * 100) / balance), 2)

    if percent <= -3:

        for tick in mt5.positions_get(symbol=symbol):
            ticket = tick.ticket

            close_order(ticket)
        # shut down connection to the MetaTrader 5 terminal
        mt5.shutdown()

    elif percent >= 10:
        for tick in mt5.positions_get(symbol=symbol):
            ticket = tick.ticket

            close_order(ticket)
        print("Target met! Account looks great")



    return percent

# The above code is a simple strategy that is trading the US30 index.
# This is a way to run the code in the terminal.
if __name__ == '__main__':

    # ************* Trade Parameters ***************#
    current_account_info = mt5.account_info()
    account_info_dict = mt5.account_info()._asdict()
    balance = account_info_dict.get('balance')


    stocks = {
        "Apple": ["AAPL", 1.0, mt5.TIMEFRAME_H1],
        "Microsoft": ["MSFT", 1.0, mt5.TIMEFRAME_H1],
        "Google": ["GOOG", 1.0, mt5.TIMEFRAME_H1],
        "Amazon": ["AMZN", 1.0, mt5.TIMEFRAME_H1],
        "Alibaba": ["BABA", 1.0, mt5.TIMEFRAME_H1],
        "Facebook": ["FB", 1.0, mt5.TIMEFRAME_H1],

    }
    commodities = {
        "Gold": ["XAUUSD", 1.10,
                 mt5.TIMEFRAME_M5,
                 11.44,     # default stop loss point
                 5.0,       # max stop loss distance in pips
                 0.5],      # trail amount is the amount by which the stop loss will update
        "Silver": ["XAGUSD", 1.10,
                    mt5.TIMEFRAME_M5,
                    0.280, # default stop loss point
                    0.100, # max_stop_loss_distance stop loss distance in pips
                    0.100],# trail amount is the amount by which the stop loss will update
    }
    securites =commodities
    DEVIATION = 20  # for order slippage
    SMA = 100  # Simple Moving Average Period

    while True:
        for asset in securites.keys():
            assetname = asset
            # ********************* Initialize the inputs #***************** ****
            symbol = securites[asset][0]
            lot = securites[asset][1]
            TIMEFRAME = securites[asset][2]
            stoploss_point = securites[asset][3]
            max_stop_loss_distance = securites[asset][4]
            trail_amount = securites[asset][5]

            total_positions = mt5.positions_total()
            signal = strategy(symbol, TIMEFRAME, SMA)
            isOpen = isInvested(symbol=symbol)
            rsi = RSI(symbol, TIMEFRAME, SMA)
            trail_stop = trail_sl(symbol, TIMEFRAME, SMA, stoploss_point,max_stop_loss_distance,trail_amount)

            # This is the main logic of the strategy. If the signal is buy and the position is not open, then buy. If the
            # signal is sell and the position is not open, then sell.
            if signal == 'buy':
                if not isOpen:
                    entry = 'buy'
                    market_order(symbol, lot, entry)
            elif signal == 'sell':
                if not isOpen:
                    entry = 'sell'
                    market_order(symbol, lot, entry)

            profit = 0
            ticket = 0
            sl =0

            for tick in mt5.positions_get(symbol=symbol):
                ticket = tick.ticket
                profit = tick.profit
                sl = tick.sl

            percent = riskManagement(profit, symbol)
            closeOut(symbol, TIMEFRAME, SMA)

            strategyInfo = {
                            'Symbol': symbol,
                            'Signal':signal,
                            'Invested':isOpen,
                            'P&L(%)': percent,
                            'P&L':profit,
                            'RSI':round(rsi,2),

                            }
            strategyInfo= pd.DataFrame.from_dict(strategyInfo, orient='index').T
            strategyInfo = str(strategyInfo)

            print(strategyInfo)
            print("----------------------------------------------------")

        time.sleep(1)

# ************* End of Trade Parameters ***************#