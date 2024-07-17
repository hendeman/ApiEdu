# import requests
import asyncio
import httpx
import xmltodict
from datetime import datetime

from aiocache import cached
from aiocache.serializers import JsonSerializer
from fastapi.exceptions import RequestValidationError


@cached(ttl=60, serializer=JsonSerializer())  # TTL в секундах (60 секунд)
async def get_exchange_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return xmltodict.parse(response.content)
    except httpx.HTTPStatusError as err:
        raise RequestValidationError([
            {
                'loc': ['body'],
                'msg': f"HTTP error occurred: {err}",
                'type': 'http_error'
            }
        ])
    except httpx.RequestError as err:
        # get_exchange_data.cache.delete(url)
        raise RequestValidationError([
            {
                'loc': ['body'],
                'msg': "Сервер недоступен",
                'type': 'server_unavailable'
            }
        ])
    except Exception as err:
        raise RequestValidationError([
            {
                'loc': ['body'],
                'msg': f"Unexpected error occurred: {err}",
                'type': 'unexpected_error'
            }
        ])


async def convert_currency(value, from_currency, to_currency, data):
    if from_currency == "BYN" or to_currency == "BYN":
        currency = from_currency if to_currency == "BYN" else to_currency
        for item in data['DailyExCards']['Currency']:
            if currency == item['CharCode']:
                scale = int(item["Scale"])
                if from_currency == "BYN":
                    return round(value * scale / float(item['RateSell']), 2), currency
                else:
                    return round(value * float(item['RateBuy']) / scale, 2), "BYN"
    else:
        for item in data['DailyExCards']['Currency']:
            if set(from_currency + to_currency).issubset(set(item['CharCode'])):
                if from_currency == item['CharCode'].split("(")[0]:
                    return round(value * float(item['RateBuy']), 2), to_currency
                else:
                    return round(value / float(item['RateBuy']), 2), to_currency
    return None, None


async def main():
    current_date = datetime.now().strftime("%d/%m/%Y")
    url = f"https://www.belapb.by/api/ExCardsDaily/?ondate={current_date}"
    value = 1000
    conversion = ['USD', 'BYN']
    # conversion = ['BYN', 'USD']
    data = await get_exchange_data(url)
    converted_value, currency = await convert_currency(value, conversion[0], conversion[1], data)
    if converted_value:
        print(converted_value, currency)
    else:
        print("Конвертация не удалась")


if __name__ == "__main__":
    asyncio.run(main())
