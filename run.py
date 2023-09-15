import asyncio
import time

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
    return loop.run_until_complete(stockx.scrape_slugs(category))


def run_async_scrape_product(url):
    loop = asyncio.get_event_loop()
    time.sleep(0.5)
    return loop.run_until_complete(stockx.scrape_product(url))


async def run():
    stockx.BASE_CONFIG["cache"] = True

    # categories = np.array(stockx.get_all_categories())
    # split_categories = np.array_split(categories, 4)
    # categories_by_server_number = split_categories[SERVER_NUMBER - 1]
    # categories = stockx.get_all_categories()
    # categories = ["https://stockx.com/" + item for item in categories]
    # formatted_categories_by_process_number = np.array_split(
    #     categories, len(categories) / 15
    # )
    # for c in formatted_categories_by_process_number:
    #     pool = multiprocessing.Pool(processes=NUM_PROCESSES)
    #     slugs = pool.map(run_async_scrape_slugs, c.tolist())
    #     slugs = [item for sublist in slugs for item in sublist]
    #     pool.close()
    #     pool.join()
    #     with open('results/slugs_new.json', 'r') as f1:
    #         s = json.load(f1)
    #     new_slugs = s + slugs
    #     with open('results/slugs_new.json', 'w') as f2:
    #         json.dump(new_slugs, f2)
    #     print("All processes have completed successfully")

    with open('results/slugs_new.json', 'r') as f1:
        slugs = np.array(json.load(f1))
    slugs = [dict(s) for s in set(frozenset(d.items()) for d in slugs)][20050:]
    slugs = [
        "https://stockx.com/" + slug_by_server_number.get('slug')
        for slug_by_server_number in slugs
    ]
    formatted_slugs = np.array_split(
        slugs, len(slugs) / 10
    )
    for slug_parts in formatted_slugs:
        pool = multiprocessing.Pool(processes=NUM_PROCESSES)
        products = pool.map(run_async_scrape_product, slug_parts.tolist())
        pool.close()
        pool.join()
        products_formatted = formatted_products(products)
        post_products(products_formatted)
        print("All processes have completed successfully")


if __name__ == "__main__":
    asyncio.run(run())
