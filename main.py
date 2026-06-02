import asyncio
import os

import logging
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

from dotenv import load_dotenv, set_key
from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.type import AuthScope

from core.yandex_music_service import YandexMusicService
from core.command_registry import CommandRegistry
from core.twitch_bot_service import TwitchBotService
from commands.np import execute
from utils.get_ya_token import get_yandex_music_token

load_dotenv()


async def main():
    logger.info("Initializing Application")
    # === Токены для Twitch ===
    app_id = os.getenv("APP_ID")
    app_secret = os.getenv("APP_SECRET")
    target_channel = os.getenv("TARGET_CHANNEL")
    ref_token = os.getenv("TW_REF_TOKEN")

    twitch = await Twitch(app_id, app_secret)
    scope = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]

    if ref_token:
        try:
            token, new_ref = await refresh_access_token(ref_token, app_id, app_secret)
            await twitch.set_user_authentication(token, scope, new_ref)
            if new_ref != ref_token:
                set_key('.env', 'TW_REF_TOKEN', new_ref)
        except Exception:
            ref_token = None
            logger.info("Twitch Refresh Token not available, starting authorization")

    if not ref_token:
        auth = UserAuthenticator(twitch, scope)
        token, new_ref = await auth.authenticate()
        await twitch.set_user_authentication(token, scope, new_ref)
        set_key('.env', 'TW_REF_TOKEN', new_ref)

    # === Токен для Яндекса ===
    ya_token = os.getenv("YA_AC_TOKEN")
    if not ya_token:
        logger.info("Yandex token not available, starting authorization")
        ya_token = get_yandex_music_token()   # GUI-окно
        if ya_token:
            set_key('.env', 'YA_AC_TOKEN', ya_token)
        else:
            raise RuntimeError("Не удалось получить токен Яндекс.Музыки")
    ym_service = YandexMusicService(ya_token)

    # === Реестр команд ===
    registry = CommandRegistry()
    async def np_handler(cmd):
        await execute(cmd, ym_service)
    registry.register('np', np_handler)
    registry.register('song', np_handler)
    registry.register('music', np_handler)
    registry.register('песня', np_handler)
    registry.register('музыка', np_handler)

    # === Бот ===
    bot = TwitchBotService(twitch, target_channel, registry)
    await bot.start()
    logger.info("App is ready to work")
    # Ждём остановки (например, через asyncio.Event)
    try:
        await asyncio.Event().wait()
    finally:
        logger.info("Application finished, closing connections")
        if bot.chat:
            bot.chat.stop()
        await twitch.close()

if __name__ == "__main__":
    asyncio.run(main())