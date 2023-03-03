from .bot import Bot
from .config import Config
import click
from . import log


@click.command()
@click.option("--config-path", "-c", type=click.Path(exists=True), default="config.yaml")
@click.option("--log-level", "-l", type=click.Choice(["debug", "info", "warning", "error", "critical"]), default="info")
def main(config_path: str, log_level: str):
    config = Config.read_from_yaml(config_path)
    log.level = log_level.upper()
    logger = log.get_logger()

    bot = Bot(
        config.telegram.appid,
        config.telegram.apikey,
        config.telegram.botid,
        config.telegram.bottoken,
        config.openai.apikey,
        parent_logger=logger
    )
    logger.info("Bot started")

    bot.client.run_until_disconnected()