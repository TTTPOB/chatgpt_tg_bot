from telethon import TelegramClient, events
from typing import Dict
from .chatgpt_api import Chat
import logging
from .log import level_map


class Bot:
    appid: int
    apikey: str
    bot_token: str
    client: TelegramClient
    chatgptbots: Dict[int, Chat]
    logger: logging.Logger

    def __init__(
        self,
        appid: int,
        apikey: str,
        botid: str,
        bot_token: str,
        openai_apikey: str,
        parent_logger: logging.Logger,
    ) -> None:
        self.appid = appid
        self.apikey = apikey
        self.bot_token = bot_token
        self.botid = botid
        self.client = TelegramClient(self.botid, self.appid, self.apikey).start(
            bot_token=self.bot_token
        )
        self.openai_apikey = openai_apikey
        self.chatgptbots = {}
        self.logger = parent_logger.getChild(f"tgbot-{botid}")
        self.client.add_event_handler(self.handler, events.NewMessage)

    def log(self, level: str, message: str) -> None:
        self.logger.log(level_map[level], message)

    async def handler(self, event: events.NewMessage):
        if event.is_private:
            self.log("info", f"Got message from {event.sender_id}: {event.text}")
            if event.sender_id not in self.chatgptbots:
                self.chatgptbots[event.sender_id] = Chat(self.openai_apikey, self.logger, event.sender_id)
            chat = self.chatgptbots[event.sender_id]
            text = ''
            if event.text == "/clear":
                chat.clean_state()
                text = "Cleaned bot brain."
            elif event.text.startswith("/set_token_limit"):
                l = int(event.text.split(" ")[1])
                chat.set_token_limit(l)
                text = 'Set token limit to ' + str(l)
            else:
                text = await chat.chat(event.text)
            await event.respond(text)
            self.log("info", f"Sent response to {event.sender_id}: {text}")
