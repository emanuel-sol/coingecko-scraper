import gecko_helpers
from gecko_helpers import getPrice_Likes, getTable1Info, getTable2Info
gecko_helpers.logging.info("Program started")

gecko = gecko_helpers.pd.read_csv("gecko_final_7.csv")
save_interval = 400

base_url = "https://www.coingecko.com/en"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
headers = {'user-agent': USER_AGENT}
with open("list_of_links.pkl", 'rb') as f:
    links = gecko_helpers.pickle.load(f)

div_RHS = "body > div.container > div.mt-3 > div.col-12.row.p-0.m-0.mb-2.tw-flex.flex-column-reverse.flex-sm-row > div.col-md-3.col-lg-5.text-center.text-md-right.mt-3.mt-md-0.pr-0 > div"
div_LHS = "body > div.container > div.mt-3 > div.col-12.row.p-0.m-0.mb-2.tw-flex.flex-column-reverse.flex-sm-row > div.col-md-9.col-lg-7.p-0 > div"
price_selector = "body > div.container > div.mt-3"

for i in range(len(links)):
    # Periodically save dataset
    if i % save_interval == 0:
        gecko.to_csv(f"gecko_{i/save_interval}.csv")

    # Make request to page
    url = base_url
    link = links[i]
    url = url.replace("/en", link)
    gecko_helpers.logging.info(f"Scraping {url} at iteration {i}")
    response = gecko_helpers.requests.get(url, headers=headers)
    gecko_helpers.logging.info(f"Status code: {response.status_code}")

    coin_html_text = response.text
    coin_soup = gecko_helpers.BeautifulSoup(coin_html_text, 'lxml')

    try:
        gecko = getPrice_Likes(coin_soup, price_selector, gecko, i)
        gecko = getTable1Info(coin_soup, div_LHS, gecko, i)
        gecko = getTable2Info(coin_soup, div_RHS, gecko, i)
    except Exception as e:
        gecko_helpers.logging.exception(f"Program failled at iteration {i} with error {e}")
        gecko_helpers.time.sleep(1)

gecko.to_csv(f"gecko_final_8.csv", index=False)