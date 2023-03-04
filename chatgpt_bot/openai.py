from typing import List, Dict, Optional, Union, Tuple
import httpx
from pydantic import BaseModel
from .log import level_map
import logging
import tiktoken as tk
from io import BytesIO


class ChatGptMessage(BaseModel):
    role: str
    content: str


class ChatGptRequest(BaseModel):
    model: str
    messages: List[ChatGptMessage]


class ChatGptMessageChoice(BaseModel):
    index: int
    finish_reason: Union[str, None]
    message: Optional[ChatGptMessage]
    messages: Optional[List[ChatGptMessage]]


class ChatGptUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatGptResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[ChatGptMessageChoice]
    usage: ChatGptUsage


class WhisperResponse(BaseModel):
    text: str


class Chat:
    messages: List[ChatGptMessage]
    apikey: str
    token_limit = 3500
    logger: logging.Logger
    client: httpx.AsyncClient
    __tokenizer = tk.get_encoding("cl100k_base")

    def __openapi_header(self) -> httpx.Headers:
        header = {"Authorization": f"Bearer {self.apikey}"}
        return httpx.Headers(header)

    def set_token_limit(self, l: int) -> None:
        self.token_limit = l

    def __init__(self, apikey: str, parent_logger: logging.Logger, chatid: int) -> None:
        self.messages = []
        self.apikey = apikey
        self.logger = parent_logger.getChild(f"chat-{chatid}")
        # timeout set to 10s
        self.client = httpx.AsyncClient(
            headers=self.__openapi_header(),
            timeout=30.0,
            base_url="https://api.openai.com/v1/",
        )

    async def __make_chatgpt_request(
        self, messages: List[ChatGptMessage]
    ) -> ChatGptResponse:
        data = ChatGptRequest(model="gpt-3.5-turbo", messages=messages).dict()
        try:
            self.log("debug", f"Sending request to OpenAI ChatGPT:\n{data}")
            response = await self.client.post("/chat/completions", json=data)
            self.log("debug", f"Got response from OpenAI:\n{response.json()}")

            try:
                resp = ChatGptResponse.parse_obj(response.json()).choices[0].message
            except Exception as e:
                error_msg = f"Error while parsing response from OpenAI:\n{e};\n\nRaw response:\n{response.json()}"
                self.log("error", error_msg)
                resp = ChatGptMessage(role="system", content=error_msg)
        except Exception as e:
            self.log("error", f"Error while sending request to OpenAI: {e}")
            resp = ChatGptMessage(role="system", content=f"Error: {e}")
        return resp

    async def __make_whisper_request(self, audio: BytesIO) -> ChatGptMessage:
        try:
            self.log("debug", "Sending request to Whisper: audio file")
            response = await self.client.post(
                "/audio/transcriptions",
                data={
                    "model": "whisper-1",
                },
                files={"file": ("audio.m4a", audio)},
            )
            self.log("debug", f"Got response from OpenAI Whisper:\n{response.json()}")
            try:
                resp = WhisperResponse.parse_obj(response.json())
                chatgpt_msg = ChatGptMessage(role="user", content=resp.text)
            except Exception as e:
                error_msg = f"Error while parsing response from OpenAI Whisper:\n{e};\n\nRaw response:\n{response.json()}"
                self.log("error", error_msg)
                resp = WhisperResponse(text=error_msg)
                chatgpt_msg = ChatGptMessage(role="system", content=error_msg)
        except Exception as e:
            error_msg = f"Error while sending request to OpenAI Whisper: {e}"
            self.log("error", error_msg)
            resp = WhisperResponse(text=error_msg)
            chatgpt_msg = ChatGptMessage(role="system", content=error_msg)
        return chatgpt_msg

    def log(self, level: str, msg: str):
        self.logger.log(level_map[level], msg)

    def clean_state(self):
        self.messages.clear()

    async def chat(self, prompt: str) -> str:
        self.messages.append(ChatGptMessage(role="user", content=prompt))
        self.__limit_messages()
        self.log("debug", f"Sending request to OpenAI: {self.messages}")
        msg = await self.__make_chatgpt_request(self.messages)
        if msg.role != "system":
            self.messages.append(msg)
        elif msg.role == "system":
            # delete the unsent message
            self.messages.pop()
        return f"{msg.role}: {msg.content}"

    @staticmethod
    def __count_token_for_single_sentence(sentence: str):
        return len(Chat.__tokenizer.encode(sentence))

    def __get_token_count(self):
        return sum(
            [self.__count_token_for_single_sentence(m.content) for m in self.messages]
        )

    def __limit_messages(self):
        # if messages content sum are too long, remove the oldest messages
        # but if there is only one message, don't remove it
        self.log("debug", f"current token count: {self.__get_token_count()}")
        while self.__get_token_count() > self.token_limit and len(self.messages) > 1:
            self.messages.pop(0)
            self.log(
                "debug",
                f"reached token limit, cleaning, current token count: {self.__get_token_count()}",
            )

    async def handle_voice(self, audio: BytesIO) -> Tuple[str, str]:
        msg = await self.__make_whisper_request(audio)
        if msg.role == "system":
            return ("system error", msg.content)
        else:
            return (await self.chat(msg.content), msg.content)
