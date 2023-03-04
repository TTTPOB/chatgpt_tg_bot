from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from typing import Dict
from .openai import Chat
import logging
from .log import level_map
from .utils import temp_file
from io import BytesIO
import tempfile
import ffmpeg


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

    async def handler(self, msg: Message):
        if msg.is_private:
            self.log("info", f"Got message from {msg.sender_id}: {msg.text}")
            if msg.sender_id not in self.chatgptbots:
                self.chatgptbots[msg.sender_id] = Chat(
                    self.openai_apikey, self.logger, msg.sender_id
                )
            chat = self.chatgptbots[msg.sender_id]
            bot_response_text = ""
            if msg.text == "/clear":
                chat.clean_state()
                bot_response_text = "Cleaned bot brain."
            elif msg.text.startswith("/set_token_limit"):
                l = int(msg.text.split(" ")[1])
                chat.set_token_limit(l)
                bot_response_text = "Set token limit to " + str(l)
            else:
                # if event contain a voice, invoke the voice handler
                chatgpt_input = msg.text
                if msg.audio or msg.voice:
                    audio = await self.__transform_audio(msg)
                    chatgpt_response_text, audio_text = await chat.handle_voice(audio)
                else:
                    chatgpt_response_text = await chat.chat(chatgpt_input)
                bot_response_text += chatgpt_response_text
                if msg.audio or msg.voice:
                    bot_response_text += (
                        f"\n\nMessage transcibed from audio: {audio_text}"
                    )
            await msg.respond(bot_response_text)
            self.log("info", f"Sent response to {msg.sender_id}: {bot_response_text}")

    @staticmethod
    def __convert_to_m4a(audio: BytesIO, suffix: str) -> BytesIO:
        with temp_file(suffix) as i:
            with open(i, "wb") as f:
                f.write(audio.getvalue())
                f.flush()
            with temp_file(".m4a") as o:
                ffmpeg.input(i).output(o, acodec="aac").global_args("-y").run()
                with open(o, "rb") as f:
                    return BytesIO(f.read())

    async def __transform_audio(self, msg: Message) -> BytesIO:
        if msg.audio:
            filename = msg.file.name
            self.log("info", f"Got audio message from {msg.sender_id}")
        if msg.voice:
            filename = f"{msg.voice.dc_id}_{msg.voice.id}.ogg"
            self.log("info", f"Got voice message from {msg.sender_id}")
        audio_bytes = BytesIO()
        await msg.download_media(audio_bytes)
        if not filename.endswith(".m4a"):
            self.log("info", f"Converting {filename} to m4a")
            suffix = f".{filename.split('.')[-1]}"
            audio_bytes = self.__convert_to_m4a(audio_bytes, suffix)
        return audio_bytes
