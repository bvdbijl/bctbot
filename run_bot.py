import sys
import argparse
from bctbot.tradingbot import TradingBot

import bctbot.logging_setup as log_setup
logger = log_setup.logging.getLogger(__name__)


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Specify a config file")
    return parser.parse_args(args)


def main():
    parser = parse_args(sys.argv[1:])
    t = TradingBot()
    bot_config = parser.config if parser.config else "trading_bot_config.json"
    t.load_session(bot_config)
    while t.active:
        t.loop()


if __name__ == "__main__":
    logger.info(f"Running the bot")
    main()
