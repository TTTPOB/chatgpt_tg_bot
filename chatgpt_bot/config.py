import yaml
from pydantic import BaseModel


class Telegram(BaseModel):
    appid: str
    apikey: str
    botid: str
    bottoken: str


class Openai(BaseModel):
    apikey: str


class Config(BaseModel):
    telegram: Telegram
    openai: Openai

    @classmethod
    def read_from_yaml(cls, path: str) -> "Config":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        # use pydantic style initialization
        return Config.parse_obj(data)
