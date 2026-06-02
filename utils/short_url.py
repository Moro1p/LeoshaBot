import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)
async def get_short_url(url: str) -> str:
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as session:
        try:
            async with session.get(f'https://clck.ru/--?url={url}') as response:
                if response.status == 200:
                    short_url = await response.text()
                    return short_url.strip()[8:]
                else:
                    logger.error(f"Error: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    