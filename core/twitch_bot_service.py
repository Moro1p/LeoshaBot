from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator, refresh_access_token
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
import asyncio
import json 
import os
from dotenv import load_dotenv, set_key
from core.command_registry import CommandRegistry
import logging
load_dotenv()

class TwitchBotService:
    def __init__(self, twitch: Twitch, target_channel: str, registry: CommandRegistry):
        self.target_channel = target_channel
        self.registry = registry
        self.twitch = twitch
        self.chat = None
        self.logger = logging.getLogger(self.__class__.__name__)
  
    async def start(self):
        self.chat = await Chat(self.twitch)

        # Регистрируем все команды из реестра
        for cmd_name, handler in self.registry.get_all_commands().items():
            self.chat.register_command(cmd_name, handler)
            self.logger.info(f"Registered command {cmd_name}")

        self.chat.start()
        self.logger.info("Connecting to chat...")
        await self.chat.join_room(self.target_channel)
        
