from telethon import TelegramClient, events
from typing import Dict
from .chatgpt_api import Chat
from .utils import get_logger, log
import logging


class Bot:
    appid: int
    apikey: str
    bot_token: str
    client: TelegramClient
    chatgptbots: Dict[int, Chat]
    logger: logging.Logger

    def __init__(
        self, appid: int, apikey: str, botid: str, bot_token: str, openai_apikey: str, log_level: str = "info"
    ) -> None:
        self.appid = appid
        self.apikey = apikey
        self.bot_token = bot_token
        self.botid = botid
        self.client = TelegramClient(self.botid, self.appid, self.apikey).start(
            bot_token=self.bot_token
        )
        self.logger = get_logger("tg_bot", log_level)
        self.log("info", "Bot started")
        self.openai_apikey = openai_apikey
        self.chatgptbots = {}
        self.client.add_event_handler(self.handler, events.NewMessage)
    
    def log(self, level: str, msg: str):
        log(level, msg, self.logger)

    async def handler(self, event: events.NewMessage):
        if event.is_private:
            self.log("info", f"Got message from {event.sender_id}: {event.text}")
            if event.sender_id not in self.chatgptbots:
                self.chatgptbots[event.sender_id] = Chat(self.openai_apikey)
            chat = self.chatgptbots[event.sender_id]
            if event.text == "/clear":
                chat.clean_state()
                await event.respond("cleaned bot brain")
                return
            await event.respond(await chat.chat(event.text))
