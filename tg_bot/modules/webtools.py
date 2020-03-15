import html
import json
from datetime import datetime
from typing import Optional, List
import requests
import subprocess
import os
import speedtest
import time
from telegram import Message, Chat, Update, Bot, MessageEntity
from telegram import ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html
from tg_bot.modules.helper_funcs.extraction import extract_text

from tg_bot import dispatcher, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS
from tg_bot.modules.helper_funcs.filters import CustomFilters

# Kanged from PaperPlane Extended userbot


def speed_convert(size):
    """
    Hi human, you can't read bytes?
    """
    power = 2**10
    zero = 0
    units = {0: '', 1: 'Kb/s', 2: 'Mb/s', 3: 'Gb/s', 4: 'Tb/s'}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"


@run_async
def get_bot_ip(bot: Bot, update: Update):
    """ Sends the bot's IP address, so as to be able to ssh in if necessary.
        OWNER ONLY.
    """
    res = requests.get("http://ipinfo.io/ip")
    update.message.reply_text(res.text)


@run_async
def ping(bot: Bot, update: Update):
    start_time = time.time()
    test = send_message(update.effective_message, "Pong!")
    end_time = time.time()
    ping_time = float(end_time - start_time)
    bot.editMessageText(
        chat_id=update.effective_chat.id,
        message_id=test.message_id,
        text=tl(
            update.effective_message,
            "Pong!\nSpeed was: {0:.2f}s").format(
            round(
                ping_time,
                2) %
            60))


@run_async
def speedtst(bot: Bot, update: Update):
    test = speedtest.Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    result = test.results.dict()
    update.effective_message.reply_text(
        "Download "
        f"{speed_convert(result['download'])} \n"
        "Upload "
        f"{speed_convert(result['upload'])} \n"
        "Ping "
        f"{result['ping']} \n"
        "ISP "
        f"{result['client']['isp']}")


IP_HANDLER = CommandHandler("ip", get_bot_ip, filters=Filters.chat(OWNER_ID))
SPEED_HANDLER = CommandHandler(
    "speedtest",
    speedtst,
    filters=CustomFilters.sudo_filter)
PING_HANDLER = DisableAbleCommandHandler("ping", ping)

dispatcher.add_handler(IP_HANDLER)
dispatcher.add_handler(SPEED_HANDLER)
dispatcher.add_handler(PING_HANDLER)
