from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
import pickle
import numpy as np
import logging

total_crypto_mkt_cap = 1521620816260

logging.basicConfig(filename="scraper.log", level=logging.DEBUG,
    format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

def getPrice_Likes(gecko_soup, price_selector, gecko_df, idx):
    try:
        # Get price data
        price_text = gecko_soup.select(price_selector)[0].find("span").text
        price = float(price_text.strip().replace(",", "").replace("$",""))
        gecko_df.at[idx, "price"] = price
        logging.info("Obtained price data")
    except Exception as e:
        logging.debug(f"Price data not available {e}")

    try:
        gecko_df.at[idx, "coingecko_likes"] = int(
            gecko_soup.find(
                "div", class_="my-1").find(
                    "span", class_="ml-1").text.split(" ")[0].replace(",", ""))

        logging.info("Obtained coingecko likes data")
    except Exception as e:
        logging.debug(f"Likes data not available {e}")

    return gecko_df


def getTable1Info(gecko_soup, table_selector, gecko_df, idx):
    # Table 1 info present for all coins

    table_1 = gecko_soup.select(table_selector)[0]
    ## Get website url, twitter url, check for whitepaper, explorer url, tag
    table_1_categories = table_1.find_all("span", class_="coin-link-title")
    table_1_rows = table_1.find_all("div", class_="coin-link-row")
    category_dict = {"web": (False, 0),
                "explorer": (False, 0),
                "tag": (False, 0),
                "contract": (False, 0),
                "community": (False, 0)}

    idx = 0
    # Check if the categories we want exist
    for category in table_1_categories:
        if category.text.strip() == "Website":
            category_dict['web'] = (True, idx)
        elif category.text.strip() == "Explorers":
            category_dict['explorer'] = (True, idx)
        elif category.text.strip() == "Contract":
            category_dict['contract'] = (True, idx)
        elif category.text.strip() == "Community":
            category_dict['community'] = (True, idx)
        elif category.text.strip() == "Tags":
            category_dict['tag'] = (True, idx)
        idx += 1

    # Grab data if it exists, since we can only store one link per cell just grab the 
    # the first one
    for k, v in category_dict.items():
        if k == "web" and v[0]:
            web_row = table_1_rows[v[1]]
            web_row_links = web_row.find_all("a")
            # Check for link to whitepaper
            if web_row_links:
                for r in web_row_links:
                    if r.text == "Whitepaper":
                        gecko_df.at[idx, "whitepaper"] = 1
                gecko_df.at[idx, "website"] = web_row_links[0]['href']
                logging.info("Obtained website data")
        
        elif k == "explorer" and v[0]:
            exp_row = table_1_rows[v[1]]
            gecko_df.at[idx, "explorer"] = exp_row.find("a")['href']
            logging.info("Obtained explorer data")

        elif k == "contract" and v[0]:
            contract_row = table_1_rows[v[1]]
            contract_row = table_1_rows[v[1]]
            # Sometimes contract category idx and correct div don't line up exactly
            try:
                gecko_df.at[0, "contract_addr"] = contract_row.find("i")['data-address']
            except:
                contract_row = table_1_rows[v[1]+1]
                gecko_df.at[0, "contract_addr"] = contract_row.find("i")['data-address']
            logging.info("Obtained contract address")

        # We only care about twitter data for now
        elif k == "community" and v[0]:
            community_row = table_1_rows[v[1]]
            community_links = community_row.find_all("a")
            for l in community_links:
                if l.text == "Twitter":
                    gecko_df.at[idx, "twitter_url"] = l['href']
                    logging.info("Obtained twitter url")
        
        elif k == "tag" and v[0]:
            tag_row = table_1_rows[v[1]]
            try:
                gecko_df.at[idx, "tag"] = tag_row.div.findChildren()[0].text
                logging.info("Obtained tag data")
            except:
                logging.debug("Tag data unavailable")
                gecko_df.at[idx, "tag"] = "None"
    
    return gecko_df

def getTable2Info(gecko_soup, table_selector, gecko_df, idx):
    # Table 2 not present for smaller cap coins
    try:
        table_2 = gecko_soup.select(table_selector)[0]
        fully_diluted_valuation = getValuation(table_2, gecko_df)
        curr_supply, max_supply = getSupply(table_2, gecko_df)

        # Try to calculate fully_diluted_valuation from price and max_supply
        price_supply = np.array([gecko_df.at[idx, "price"], max_supply])
        if not np.all(np.isnan(price_supply)) and np.isnan(fully_diluted_valuation):
            fully_diluted_valuation = price_supply[0] * price_supply[1]
            gecko_df.at[idx, "fully_diluted_valuation"] = fully_diluted_valuation
            logging.info("Obtained fully diluted valuation from price and max supply")
        elif not np.isnan(fully_diluted_valuation):
            logging.info("Obtained fully diluted valuation from table")
            gecko_df.at[idx, "fully_diluted_valuation"] = fully_diluted_valuation
        else:
            logging.debug("Cannot obtain fully diluted valuation")
            gecko_df.at[idx, "fully_diluted_valuation"] = fully_diluted_valuation

        # Try to calculate mkt_cap from price and curr_supply
        price_supply = np.array([gecko_df.at[idx, "price"], curr_supply])
        if not np.all(np.isnan(price_supply)) and np.isnan(gecko_df.at[idx, "mkt_cap"]):
            mkt_cap = price_supply[0] * price_supply[1]
            gecko_df.at[idx, "mkt_cap"] = mkt_cap
            logging.info("Obtained market cap from price and current supply")
            # Now that we have mkt_cap we can update dominace
            gecko_df.at[idx, "dominance"] = mkt_cap / total_crypto_mkt_cap
            logging.info("Updated dominance value")
            # If we have volume we can update "vol / mkt_cap" value now
            if not (
                np.isnan(
                    gecko_df.at[idx, "volume"])) and (gecko_df.at[idx, "mkt_cap"] > 0):
                gecko_df.at[idx, "vol / mkt_cap"] = gecko_df.at[idx, "volume"] / gecko_df.at[idx, "mkt_cap"]
                logging.info("Updated vol / mkt_cap value")
            else:
                logging.debug("Couldn't obtain vol / mkt_cap value")    
    except:
        logging.debug("Table 2 does not exist")
    # Be a polite and don't overload the webserver with requests
    time.sleep(1)
    return gecko_df

## Determine if table_2 has value for fully diluted valuation
def getValuation(table_2, gecko_df):
    table_2_categories = table_2.find_all("div", class_="font-weight-bold")

    fully_diluted_valuation = np.nan
    has_fully_diluted_valuation = False
    idx = 0
    for tag in table_2_categories:
        label = tag.text.strip()
        if label == "Fully Diluted Valuation":
            has_fully_diluted_valuation = True
            break
        idx += 1

    if has_fully_diluted_valuation:
        table_2_values = table_2.find_all("div",class_="mt-1")
        fully_diluted_valuation = float(table_2_values[idx].span.text.strip(
            ).replace(",", "").replace("$",""))
    
    return fully_diluted_valuation

## Determine if table_2 has circulating supply data
def getSupply(table_2, gecko_df):
    table_2_categories = table_2.find_all("div", class_="font-weight-bold")
    has_circ_supply = False
    idx = 0

    for tag in table_2_categories:
        label = tag.text.strip()
        if label == "Circulating Supply":
            has_circ_supply = True
            break
        idx += 1

    if has_circ_supply:
        table_2_values = table_2.find_all("div",class_="mt-1")

        try:
            curr_supply = int(table_2_values[idx].text.split("/")[0].strip().replace(",", ""))
        except:
            curr_supply = np.nan
            logging.debug("Current supply is an invalid value")
        try: 
            max_supply = int(table_2_values[idx].text.split("/")[1].strip().replace(",", ""))
        except:
            logging.debug("Max supply is an invalid value")
            max_supply = np.nan
        
        return curr_supply, max_supply
    else:
        return np.nan, np.nan
        