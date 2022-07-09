import vectorbt as vbt

btc_price = vbt.YFData.download(
    "BTC-USD")
print(btc_price)

