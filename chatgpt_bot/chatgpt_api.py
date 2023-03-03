from typing import List, Dict, Optional, Union
import httpx
from pydantic import BaseModel
from .log import level_map
import logging
import tiktoken as tk


class ChatGptMessage(BaseModel):
    role: str
    content: str


class ChatGptRequest(BaseModel):
    model: str
    messages: List[ChatGptMessage]


class Choice(BaseModel):
    index: int
    finish_reason: Union[str, None]
    message: Optional[ChatGptMessage]
    messages: Optional[List[ChatGptMessage]]


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatGptResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


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

    async def __make_request(self, messages: List[ChatGptMessage]) -> ChatGptResponse:
        data = ChatGptRequest(model="gpt-3.5-turbo", messages=messages).dict()
        try:
            self.log("debug", f"Sending request to OpenAI:\n{data}")
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions", json=data
            )
            self.log("debug", f"Got response from OpenAI:\n{response.json()}")

            resp = ChatGptResponse.parse_obj(response.json()).choices[0].message
        except Exception as e:
            resp = ChatGptMessage(role="system", content=f"Error: {e}")
        return resp

    def __init__(self, apikey: str, parent_logger: logging.Logger, chatid: int) -> None:
        self.messages = []
        self.apikey = apikey
        self.logger = parent_logger.getChild(f"chat-{chatid}")
        self.client = httpx.AsyncClient(headers=self.__openapi_header())

    def log(self, level: str, msg: str):
        self.logger.log(level_map[level], msg)

    def clean_state(self):
        self.messages.clear()

    async def chat(self, prompt: str) -> str:
        self.messages.append(ChatGptMessage(role="user", content=prompt))
        self.__limit_messages()
        self.log("debug", f"Sending request to OpenAI: {self.messages}")
        msg = await self.__make_request(self.messages)
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
        self.log('debug', f"current token count: {self.__get_token_count()}")
        while self.__get_token_count() > self.token_limit and len(self.messages) > 1:
            self.messages.pop(0)
            self.log('debug', f"reached token limit, cleaning, current token count: {self.__get_token_count()}")
