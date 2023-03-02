from typing import List, Dict, Optional
import httpx
from pydantic import BaseModel
from .utils import log, get_logger
import logging


class ChatGptMessage(BaseModel):
    role: str
    content: str


class ChatGptRequest(BaseModel):
    model: str
    messages: List[ChatGptMessage]


class Choice(BaseModel):
    index: int
    finish_reason: str
    message: ChatGptMessage
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
    word_limit = 5000
    logger: logging.Logger
    client: httpx.AsyncClient

    def __openapi_header(self) -> httpx.Headers:
        header = {"Authorization": f"Bearer {self.apikey}"}
        return httpx.Headers(header)

    async def __make_request(self, messages: List[ChatGptMessage]) -> ChatGptResponse:
        data = ChatGptRequest(model="gpt-3.5-turbo", messages=messages).dict()
        logging.debug(f"Sending request to OpenAI:\n{data}")
        response = await self.client.post(
            "https://api.openai.com/v1/chat/completions",
            json=data
        )
        logging.debug(f"Got response from OpenAI:\n{response.json()}")

        return ChatGptResponse.parse_obj(response.json())

    def __init__(self, apikey: str, log_level: str = "info") -> None:
        self.messages = []
        self.apikey = apikey
        self.logger = get_logger("chatgpt_api", log_level)
        self.client = httpx.AsyncClient(headers=self.__openapi_header())
    
    def log(self, level: str, msg: str):
        log(level, msg, self.logger)

    async def chat(self, prompt: str) -> str:
        self.messages.append(ChatGptMessage(role="user", content=prompt))
        self.limit_messages()
        self.log("debug", f"Sending request to OpenAI: {self.messages}")
        try: 
            completion = await self.__make_request(self.messages)
            resp_msg = completion.choices[0].message
            self.log("debug", f"Got response from OpenAI: {resp_msg}")
            self.messages.append(resp_msg)
        except Exception as e:
            self.log("error", f"Error when sending request to OpenAI: {e}")
            resp_msg = ChatGptMessage(role="bot", content=f"Error when sending request to OpenAI: {e}")
        return resp_msg.content

    def limit_messages(self):
        # if messages content sum are too long, remove the oldest messages
        # but if there is only one message, don't remove it
        total_len = 0
        for msg in self.messages[::-1]:
            total_len += len(msg.content)
            if total_len > self.word_limit and len(self.messages) > 1:
                self.log("debug", f"Removing message: {msg}, total_len: {total_len}")
                self.messages.pop()
                self.log("debug", f"Now total_len: {total_len - len(msg.content)}")
            else:
                break
