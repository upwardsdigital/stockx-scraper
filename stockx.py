import json
import math
import time
from typing import Dict, List

import requests
from loguru import logger as log
from nested_lookup import nested_lookup
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

from tools import get_category_paths
from decouple import config

SCRAPFLY = ScrapflyClient(key=config('SCRAPFLY_KEY'))
BASE_CONFIG = {
    "asp": True,
}
selector = 'div>div>div>a[data-testid="RouterSwitcherLink"]'
selector_button = 'a[role="tab"]'


def parse_nextjs(result: ScrapeApiResponse) -> Dict:
    time.sleep(1)
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    if not data:
        data = result.selector.css("script[data-name=query]::text").get()
        data = data.split("=", 1)[-1].strip().strip(";")
    data = json.loads(data)
    return data


def parse_urls(result: ScrapeApiResponse, selector) -> List:
    models = []
    try:
        for element in result.soup.select(selector):
            models.append(
                {
                    "slug": element.get('href')[1:],
                    "parsed": False
                }

            )
    except Exception as e:
        log.info(e)
    return models


def max_page(result: ScrapeApiResponse, selector_button):
    try:
        max_page = [i.get_text() for i in result.soup.select(selector_button)][-1]
        return int(max_page)
    except Exception as e:
        log.info(e)
        return 1


def get_all_categories():
    response = requests.get('https://atlasservice.space/api/category/15')
    assert response.status_code == 200
    categories = response.json()
    paths = get_category_paths(categories["data"]["children"])
    return paths


async def scrape_slugs(url: str) -> list:
    log.info("scraping slug {}", url)
    res = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    page = max_page(res, selector_button)
    slugs = list()
    for i in range(1, page + 1):
        result = await SCRAPFLY.async_scrape(ScrapeConfig(url + f"?page={i}", **BASE_CONFIG))
        log.info("Requesting {} Status {}".format(url + f"?page={i}", result.status_code))
        slugs.extend(parse_urls(result, selector))
    return slugs


async def scrape_product(url: str) -> Dict:
    log.info("scraping product {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_nextjs(result)
    products = nested_lookup("product", data)
    try:
        product = next(p for p in products if p.get("urlKey") in result.context["url"])
    except StopIteration:
        raise ValueError("Could not find product dataset in page cache", result.context)
    return product


async def scrape_search(url: str, max_pages: int = 25) -> List[Dict]:
    log.info("scraping search {}", url)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_nextjs(first_page)
    _first_page_results = nested_lookup("results", data)[0]
    _paging_info = _first_page_results["pageInfo"]
    total_pages = _paging_info["pageCount"] or math.ceil(_paging_info["total"] / _paging_info["limit"])
    if max_pages < total_pages:
        total_pages = max_pages

    product_previews = [edge["node"] for edge in _first_page_results["edges"]]

    log.info("scraping search {} pagination ({} more pages)", url, total_pages - 1)
    _other_pages = [
        ScrapeConfig(f"{first_page.context['url']}&page={page}", **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(_other_pages):
        data = parse_nextjs(result)
        _page_results = nested_lookup("results", data)[0]
        product_previews.extend([edge["node"] for edge in _page_results["edges"]])
    log.info("scraped {} products from {}", len(product_previews), url)
    return product_previews
