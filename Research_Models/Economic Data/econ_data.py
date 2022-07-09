import investpy
import datetime
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import seaborn as sns


def getData():
    data = investpy.news.economic_calendar(
        from_date='30/5/2022',
        to_date=dt_stamp,
        countries=['united states'],
        importances=['High', 'Medium'],
        categories=["credit", "employment", "economic_activity", "inflation", "central_banks", "confidence", "balance",
                    "bonds"]
    )
    data = pd.DataFrame(data)
    data = data.dropna()

    return data


if __name__ == "__main__":
    dt_stamp = datetime.datetime.now().strftime('%d/%m/%Y')
    df = getData()

    x = df.loc[df['event'] == 'Initial Jobless Claims']
    for i in range(len(x)):
        x.iloc[i]['actual'] = x.iloc[i]['actual'].replace('K', '000')
        x.iloc[i]['forecast'] = x.iloc[i]['forecast'].replace('K', '000')
        x.iloc[i]['previous'] = x.iloc[i]['previous'].replace('K', '000')


    print(x)


    # x.to_csv('data.csv')
    # df.to_csv(r'C:\Users\samma\PycharmProjects\AlphaQuant-Labs\export_dataframe.csv', index=None, header=True)
