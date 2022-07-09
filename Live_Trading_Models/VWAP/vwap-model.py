""" Trending (Momentum ) Model
 Author: Sammarieo Brown
 Date: 2022-06-19
 All rights reserved
"""
import time

from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands

from MT5 import *


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
        "comment": "Trending Model",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    order_result = mt5.order_send(request)
    comment = order_result.comment

    print(f"Buy Order Execution Status: {comment}\n")

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
                "comment": "Trending Model",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            order_result = mt5.order_send(request)
            comment = order_result.comment

            # print(f"Close Order Execution Status: {comment}\n"
            # f"Symbol: {assetname}")
            # engine.say(f"Close Order Execution{comment} for {assetname}")
            # engine.runAndWait()

            return order_result

    return 'Ticket does not exist'


def strategy(symbol, timeframe, sma_period, upper_rdi, lower_rdi):
    df = MT5.get_data(symbol, timeframe, sma_period)
    slowEma = EMAIndicator(df.close, window=50).ema_indicator()  # ema
    fastEma = EMAIndicator(df.close, window=21).ema_indicator()  # ema
    ema30 = EMAIndicator(df.close, window=21).ema_indicator()  # ema 30
    rsi = RSIIndicator(df.close, 14).rsi()  # rsi
    distance = (df.close[-1] - slowEma.iloc[-1])  # distance between the last candle and the 30 day ema
    rdi = round((100 * (distance * 100) / slowEma.iloc[-1]), 2)
    ndi = ADXIndicator(df.high, df.low, df.close).adx_neg()  # Negative directional Index
    pdi = ADXIndicator(df.high, df.low, df.close).adx_pos()  # Positive directional Index

    signal = ''

    """# Buy Logic
    if (pdi.iloc[-1]>ndi.iloc[-1]) and \
            (slowEma.iloc[-1]<fastEma.iloc[-1]<df.close.iloc[-1])and(rdi<upper_rdi):
        signal = 'buy'
        return signal

    # Sell Logic
    elif (pdi.iloc[-1]<ndi.iloc[-1]) and \
            (slowEma.iloc[-1]>fastEma.iloc[-1]>df.close.iloc[-1]) and (rdi>-lower_rdi):
        signal = 'sell'
        return signal
    else:
        signal = 'None'

    return signal"""

    for tick in mt5.positions_get(symbol=symbol):
        ticket = tick.ticket
        profit = tick.profit
        price = tick.price_current

        # Buy Logic
        if (pdi.iloc[-1] > ndi.iloc[-1]) and (price > slowEma.iloc[-1]):
            signal = 'buy'
            return signal

        # Sell Logic
        elif (pdi.iloc[-1] < ndi.iloc[-1]) and (price < slowEma.iloc[-1]) :
            signal = 'sell'
            return signal
        else:
            signal = 'None'

        return signal


def closeOut(symbol, timeframe, sma_period):
    """
    If the price is below the middle Bollinger Band, close all sell orders. If the price is above the middle Bollinger Band,
    close all buy orders

    :param symbol: The currency pair you want to trade
    :param timeframe: The timeframe of the data you want to use
    :param sma_period: The number of candles to use for the SMA calculation
    """

    df = MT5.get_data(symbol, timeframe, sma_period)
    middle = BollingerBands(df.close, 20, 2).bollinger_mavg()
    upper = BollingerBands(df.close, 20, 2).bollinger_hband()
    lower = BollingerBands(df.close, 20, 2).bollinger_lband()
    rsi = RSIIndicator(df.close, 14).rsi()  # rsi

    for tick in mt5.positions_get(symbol=symbol):
        ticket = tick.ticket
        if tick.type == 1 and rsi.iloc[-1] < 10:  # pos.type == 1 represent a sell order
            close_order(ticket)
        elif tick.type == 0 and rsi.iloc[-1] > 90:  # pos.type># pos.type == 0 represent a buy order
            close_order(ticket)


def isInvested(symbol):
    """
    If the positionInfo variable is empty, then the function returns False. If the positionInfo variable is not empty, then
    the function returns True.

    :param symbol: The symbol you want to check if you have a position in
    :return: A tuple of dictionaries.
    """

    positionInfo = mt5.positions_get(symbol=symbol)
    if (positionInfo) == ():
        return False
    elif (positionInfo) != ():
        return True


def trail_sl(symbol, timeframe, sma_period,
             stop_loss, max_stop_loss_distance,
             trail_amount, **kwargs):
    """
    It checks if the distance between the current price and the stoploss is greater than the maximum distance allowed, if
    yes, it updates the stoploss

    :param symbol: The symbol you want to trade
    :param timeframe: The timeframe you want to use for the SMA
    :param sma_period: The period of the SMA indicator
    :return: The result of the function is the result of the order_send function.
    """

    df = MT5.get_data(symbol, timeframe, sma_period)
    rsi = RSIIndicator(df.close, 14).rsi()  # rsi
    ema30 = EMAIndicator(df.close, window=30).ema_indicator()  # ema 30
    distance = (df.close[-1] - ema30.iloc[-1])  # distance between the last candle and the 30 day ema
    rdi = round((100 * (distance * 100) / ema30.iloc[-1]), 2)

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
        pips = abs(round(price_current - price_open, 6)) * 100

        trailing_stop = {
            'Symbol': symbol,
            'Pips': pips,
            'SL Distance': dist_from_sl,
            'RDI': rdi,

        }
        trailing_stop = pd.DataFrame.from_dict(trailing_stop, orient='index').T
        trailing_stop = str(trailing_stop)

        print(trailing_stop)
        print('\n')

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


def riskManagement(profit, symbol):
    """
    It takes the profit and symbol as arguments and returns the percentage of profit

    :param profit: The profit of the account
    :param symbol: The currency pair you want to trade
    :return: The percent of profit or loss
    """

    balance = 25000
    percent = round(((profit * 100) / balance), 2)

    if percent <= -2:
        # if

        for tick in mt5.positions_get(symbol=symbol):
            ticket = tick.ticket
            close_order(ticket)
        # shut down connection to the MetaTrader 5 terminal

    elif percent <= -2.5:

        for tick in mt5.positions_get(symbol=symbol):
            ticket = tick.ticket

            close_order(ticket)
        # shut down connection to the MetaTrader 5 terminal
        mt5.shutdown()

    elif percent >= 3:
        print('Target reached. Closing positions')
        for tick in mt5.positions_get(symbol=symbol):
            ticket = tick.ticket
            close_order(ticket)

    return percent


if __name__ == '__main__':

    # ************* Trade Parameters ***************#
    current_account_info = mt5.account_info()
    account_info_dict = mt5.account_info()._asdict()
    balance = account_info_dict.get('balance')

    assets = {

        "EURAUD": ["EURAUD",
                   2.10,
                   mt5.TIMEFRAME_M15,
                   0.00700,  # maximum stoploss distance
                   0.00600,  # trailing amount
                   0.00900,  # default stoploss point
                   30,  # (upper) relative distance index value
                   -30,  # (lower) relative distance index value
                   ],

        "Gold": ["XAUUSD",
                 1.10,
                 mt5.TIMEFRAME_M15,
                 0.100,  # maximum stoploss distance
                 0.100,  # trailing amount
                 0.300,  # default stoploss point
                 30,  # (upper) relative distance index value
                 -30,  # (lower) relative distance index value
                 ],
        "EURUSD": ["EURUSD",
                   2.10,
                   mt5.TIMEFRAME_M15,
                   0.00200,  # maximum stoploss distance
                   0.00200,  # trailing amount
                   0.00400,  # default stoploss point
                   30,  # (upper) relative distance index value
                   -30,  # (lower) relative distance index value
                   ],

        "Silver": ["XAGUSD",
                   1.10,
                   mt5.TIMEFRAME_M15,
                   0.100,  # maximum stoploss distance
                   0.050,  # trailing amount
                   0.300,  # default stoploss point
                   50,  # (upper) relative distance index value
                   -50,  # (lower) relative distance index value
                   ],

        "USOIL": ["USOIL.cash",
                  1.10,
                  mt5.TIMEFRAME_M15,
                  1.500,  # maximum stoploss distance
                  1.000,  # trailing amount
                  3.500,  # default stoploss point
                  50,  # (upper) relative distance index value
                  -50,  # (lower) relative distance index value
                  ]
    }
    asset1 = {

        "EURUSD": ["EURUSD",
                   5.10,
                   mt5.TIMEFRAME_M1,
                   0.00100,  # maximum stoploss distance
                   0.00100,  # trailing amount
                   0.00100,  # default stoploss point
                   3,  # (upper) relative distance index value
                   -3,  # (lower) relative distance index value
                   ],

    }

    securites = asset1
    DEVIATION = 5  # for order slippage
    SMA = 100  # Simple Moving Average Period

    while True:
        for asset in securites.keys():
            assetname = asset
            # ********************* Symbol Params #***************** ****
            symbol = securites[asset][0]
            lot = securites[asset][1]
            TIMEFRAME = securites[asset][2]
            max_stop_loss_distance = securites[asset][3]
            trail_amount = securites[asset][4]
            stoploss_point = securites[asset][5]
            rdi_upper = securites[asset][6]
            rdi_lower = securites[asset][7]

            total_positions = mt5.positions_total()
            signal = strategy(symbol, TIMEFRAME, SMA, rdi_upper, rdi_lower)
            isOpen = isInvested(symbol=symbol)
            trail_stop = trail_sl(symbol, TIMEFRAME, SMA, stoploss_point, max_stop_loss_distance, trail_amount)

            if signal == 'buy':
                if not isOpen:
                    entry = 'buy'
                    market_order(symbol, lot, entry)
            elif signal == 'sell':
                if not isOpen:
                    entry = 'sell'
                    market_order(symbol, lot, entry)

            elif signal == 'sell':
                if isOpen == True:
                    for tick in mt5.positions_get(symbol=symbol):
                        ticket = tick.ticket
                        if tick.type == 0:  # pos.type == 0 represent a buy order
                            close_order(ticket)
            elif signal == 'buy':
                if isOpen == True:
                    for tick in mt5.positions_get(symbol=symbol):
                        ticket = tick.ticket
                        if tick.type == 1:  # pos.type == 0 represent a buy order
                            close_order(ticket)

            profit = 0

            for tick in mt5.positions_get(symbol=symbol):
                ticket = tick.ticket
                profit = tick.profit
                price = tick.price_current

            percent = riskManagement(profit, symbol)

            strategyInfo = {
                'Symbol': symbol,
                'Signal': signal,
                'Invested': isOpen,
                'P&L(%)': percent,
                'P&L': profit,
                'Price': price,
            }
            strategyInfo = pd.DataFrame.from_dict(strategyInfo, orient='index').T
            strategyInfo = str(strategyInfo)
            print(strategyInfo)
            print("----------------------------------------------------------------------------")

        time.sleep(1)
