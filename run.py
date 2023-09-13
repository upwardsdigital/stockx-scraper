import asyncio
import requests
import json
from pathlib import Path
import numpy as np
from decouple import config
import multiprocessing

import stockx
from tools import formatted_products, post_products

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

SERVER_NUMBER = int(config('SERVER_NUMBER'))
NUM_PROCESSES = int(config('NUM_PROCESSES'))


def run_async_scrape_slugs(category):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(stockx.scrape_slugs(category))


def run_async_scrape_product(url):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(stockx.scrape_product(url))


async def run():
    stockx.BASE_CONFIG["cache"] = True

    # categories = np.array(stockx.get_all_categories())
    # split_categories = np.array_split(categories, 4)
    # categories_by_server_number = split_categories[SERVER_NUMBER - 1]
    # categories_by_server_number = ["https://stockx.com/" + item for item in categories_by_server_number]
    # pool = multiprocessing.Pool(processes=NUM_PROCESSES)
    # pool.map(run_async_scrape_slugs, categories_by_server_number)
    # pool.close()
    # pool.join()
    # print("All processes have completed successfully")

    with open('results/slugs.json', 'r') as f1:
        slugs = np.array(json.load(f1))
    split_slugs = np.array_split(slugs, 4)
    slugs_by_server_number = split_slugs[SERVER_NUMBER - 1]
    formatted_slugs_by_server_number = [
        "https://stockx.com/" + slug_by_server_number.get('slug')
        for slug_by_server_number in slugs_by_server_number
    ]
    formatted_slugs_by_server_number_splitted = np.array_split(
        formatted_slugs_by_server_number, len(formatted_slugs_by_server_number) / 4
    )
    for slug_parts in formatted_slugs_by_server_number_splitted:
        pool = multiprocessing.Pool(processes=NUM_PROCESSES)
        products = pool.map(run_async_scrape_product, slug_parts.tolist())
        products_formatted = formatted_products(products)
        post_products(products_formatted)
        pool.close()
        pool.join()
        print("All processes have completed successfully")


if __name__ == "__main__":
    asyncio.run(run())
