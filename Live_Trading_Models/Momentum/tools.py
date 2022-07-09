import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from MT5 import *

# moving average crossover function for two series
def crossover(fast_ema, prev_fast_ema, slow_ema) -> bool:
    if fast_ema > slow_ema > prev_fast_ema:
        return True
    elif fast_ema < slow_ema < prev_fast_ema:
        return True
    else:
        return False


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





