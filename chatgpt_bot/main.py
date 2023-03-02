from .bot import Bot
from .config import Config
import click
from .utils import get_logger, log


@click.command()
@click.option("--config-path", "-c", type=click.Path(exists=True), default="config.yaml")
@click.option("--log-level", "-l", type=click.Choice(["debug", "info", "warning", "error", "critical"]), default="info")
def main(config_path: str, log_level: str):
    # set up a logger
    logger = get_logger("cli", log_level)

    config = Config.read_from_yaml(config_path)
    log("info", "Config loaded", logger)

    bot = Bot(
        config.telegram.appid,
        config.telegram.apikey,
        config.telegram.botid,
        config.telegram.bottoken,
        config.openai.apikey,
    )
    log("info", "Bot started", logger)

    bot.client.run_until_disconnected()