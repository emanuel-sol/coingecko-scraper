from bs4 import BeautifulSoup
import requests
import pandas as pd
import time, re
import pickle
import numpy as np

coingecko_table_df = pd.DataFrame(columns=[
    "name", 
    "symbol",
    "price",
    "volume",
    "mkt_cap", 
    "coingecko_rank",
    "vol / mkt_cap",
    "dominance"])

total_crypto_mkt_cap = 1521620816260
url = "https://www.coingecko.com/en"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
headers = {'user-agent': USER_AGENT}
num_pages = 84

## TODO Implement for loop over pages
for i in range(1, num_pages+1):
    print(f"Scraping page {i}\n")
    response = requests.get(url, headers=headers, params={"page": i})
    print(f"Responded with {response.status_code}\n")
    html_text = response.text
    coingecko_soup = BeautifulSoup(html_text, 'lxml')
    table_of_coins = coingecko_soup.find("div", class_="coin-table").table.tbody
    rows = table_of_coins.find_all("tr")
    num_rows = len(rows)
    print(f"Found {num_rows} rows\n")
    

## TODO Implement for loop over rows
    for j in range(num_rows):
        row = rows[j]
        row_data = row.find_all("td")

        # Get initial data from coin page
        coingecko_rank = row_data[1].text.strip()
        if coingecko_rank:
            coingecko_rank = int(coingecko_rank)
        else:
            coingecko_rank = np.nan

        name_sym = row_data[2].find_all("a")
        name = name_sym[0].text.strip()
        symbol = name_sym[1].text.strip()

        #link_list.append(name_sym[0]['href'])   
        price = row_data[3].text.strip()
        if "?" in price or "N/A":
            price = np.nan
        else:
            price = float(price.replace(',',"").replace('$', ""))

        volume = row_data[7].text.strip()
        if "?" in volume:
            volume = np.nan
        else:
            volume = float(volume.replace(',',"").replace('$', ""))

        mkt_cap = row_data[8].text.strip()
        if "?" in mkt_cap:
            mkt_cap = np.nan
        else:
            mkt_cap = float(mkt_cap.replace(',',"").replace('$', ""))

        vol_cap = 0.0
        dominance = 0.0

        if mkt_cap > 0:
            vol_cap = round(volume / mkt_cap, 3)
            dominance = round(mkt_cap / total_crypto_mkt_cap, 10)
        else:
            vol_cap = np.nan
            dominance = np.nan

        tmp_dict = {"name": name,
                    "symbol": symbol,
                    "price": price,
                    "volume": volume,
                    "mkt_cap": mkt_cap,
                    "coingecko_rank": coingecko_rank,
                    "vol / mkt_cap": vol_cap,
                    "dominance": dominance}
        tmp_df = pd.DataFrame(tmp_dict, index=[0])
        coingecko_table_df = coingecko_table_df.append(tmp_df, ignore_index=True)
    time.sleep(1) # Done scraping data from page i pause before making next request to a coin's page

coingecko_table_df.to_csv("coingecko.csv")