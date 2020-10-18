import re, html, time
from bs4 import BeautifulSoup
from requests import get
from telegram import Message, Update, Bot, User, Chat, ParseMode, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, updater
from tg_bot.modules.disable import DisableAbleCommandHandler

GITHUB = 'https://github.com'
DEVICES_DATA = 'https://raw.githubusercontent.com/androidtrackers/certified-android-devices/master/by_device.json'

@run_async
def magisk(bot, update):
    url = 'https://raw.githubusercontent.com/topjohnwu/magisk_files/'
    releases = ""
    for type, branch in {"Stable":["master/stable","master"], "Beta":["master/beta","master"], "Canary":["canary/debug","canary"]}.items():
        data = get(url + branch[0] + '.json').json()
        if str(type) == "Canary":
            data["magisk"]["link"] = "https://github.com/topjohnwu/magisk_files/raw/canary/" + data["magisk"]["link"]
            data["app"]["link"] = "https://github.com/topjohnwu/magisk_files/raw/canary/" + data["app"]["link"]
            data["uninstaller"]["link"] = "https://github.com/topjohnwu/magisk_files/raw/canary/" + data["uninstaller"]["link"]
        releases += f'*{type}*: \n' \
                    f'• [Changelog](https://github.com/topjohnwu/magisk_files/blob/{branch[1]}/notes.md)\n' \
                    f'• Zip - [{data["magisk"]["version"]}-{data["magisk"]["versionCode"]}]({data["magisk"]["link"]}) \n' \
                    f'• App - [{data["app"]["version"]}-{data["app"]["versionCode"]}]({data["app"]["link"]}) \n' \
                    f'• Uninstaller - [{data["magisk"]["version"]}-{data["magisk"]["versionCode"]}]({data["uninstaller"]["link"]})\n\n'
                        

    del_msg = update.message.reply_text("*Latest Magisk Releases:*\n{}".format(releases),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    time.sleep(300)
    try:
        del_msg.delete()
        update.effective_message.delete()
    except BadRequest as err:
        if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
            return

@run_async
def device(bot, update, args):
    if len(args) == 0:
        reply = f'No codename provided, write a codename for fetching informations.'
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return
    device = " ".join(args)
    db = get(DEVICES_DATA).json()
    newdevice = device.strip('lte') if device.startswith('beyond') else device
    try:
        reply = f'Search results for {device}:\n\n'
        brand = db[newdevice][0]['brand']
        name = db[newdevice][0]['name']
        model = db[newdevice][0]['model']
        codename = newdevice
        reply += f'<b>{brand} {name}</b>\n' \
            f'Model: <code>{model}</code>\n' \
            f'Codename: <code>{codename}</code>\n\n'  
    except KeyError as err:
        reply = f"Couldn't find info about {device}!\n"
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return
    update.message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.HTML, disable_web_page_preview=True)

@run_async
def checkfw(bot, update, args):
    if not len(args) == 2:
        reply = f'Give me something to fetch, like:\n`/checkfw SM-N975F DBT`'
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return
    temp,csc = args
    model = f'sm-'+temp if not temp.upper().startswith('SM-') else temp
    fota = get(f'http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.xml')
    test = get(f'http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.test.xml')
    if test.status_code != 200:
        reply = f"Couldn't check for {temp.upper()} and {csc.upper()}, please refine your search or try again later!"
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return
    page1 = BeautifulSoup(fota.content, 'lxml')
    page2 = BeautifulSoup(test.content, 'lxml')
    os1 = page1.find("latest").get("o")
    os2 = page2.find("latest").get("o")
    if page1.find("latest").text.strip():
        pda1,csc1,phone1=page1.find("latest").text.strip().split('/')
        reply = f'*Latest released firmware for {model.upper()} and {csc.upper()} is:*\n'
        reply += f'• PDA: `{pda1}`\n• CSC: `{csc1}`\n'
        if phone1:
            reply += f'• Phone: `{phone1}`\n'
        if os1:
            reply += f'• Android: `{os1}`\n'
        reply += f'\n'
    else:
        reply = f'*No public release found for {model.upper()} and {csc.upper()}.*\n\n'
    reply += f'*Latest test firmware for {model.upper()} and {csc.upper()} is:*\n'
    if len(page2.find("latest").text.strip().split('/')) == 3:
        pda2,csc2,phone2=page2.find("latest").text.strip().split('/')
        reply += f'• PDA: `{pda2}`\n• CSC: `{csc2}`\n'
        if phone2:
            reply += f'• Phone: `{phone2}`\n'
        if os2:
            reply += f'• Android: `{os2}`\n'
        reply += f'\n'
    else:
        md5=page2.find("latest").text.strip()
        reply += f'• Hash: `{md5}`\n• Android: `{os2}`\n\n'
    
    update.message.reply_text("{}".format(reply),
                           parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@run_async
def getfw(bot, update, args):
    if not len(args) == 2:
        reply = f'Give me something to fetch, like:\n`/getfw SM-N975F DBT`'
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return
    temp,csc = args
    model = f'sm-'+temp if not temp.upper().startswith('SM-') else temp
    test = get(f'http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.test.xml')
    if test.status_code != 200:
        reply = f"Couldn't find any firmware downloads for {temp.upper()} and {csc.upper()}, please refine your search or try again later!"
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return
    url1 = f'https://samfrew.com/model/{model.upper()}/region/{csc.upper()}/'
    url2 = f'https://www.sammobile.com/samsung/firmware/{model.upper()}/{csc.upper()}/'
    url3 = f'https://sfirmware.com/samsung-{model.lower()}/#tab=firmwares'
    url4 = f'https://samfw.com/firmware/{model.upper()}/{csc.upper()}/'
    fota = get(f'http://fota-cloud-dn.ospserver.net/firmware/{csc.upper()}/{model.upper()}/version.xml')
    page = BeautifulSoup(fota.content, 'lxml')
    os = page.find("latest").get("o")
    reply = ""
    if page.find("latest").text.strip():
        pda,csc2,phone=page.find("latest").text.strip().split('/')
        reply += f'*Latest firmware for {model.upper()} and {csc.upper()} is:*\n'
        reply += f'• PDA: `{pda}`\n• CSC: `{csc2}`\n'
        if phone:
            reply += f'• Phone: `{phone}`\n'
        if os:
            reply += f'• Android: `{os}`\n'
    reply += f'\n'
    reply += f'*Downloads for {model.upper()} and {csc.upper()}*\n'
    reply += f'• [samfrew.com]({url1})\n'
    reply += f'• [sammobile.com]({url2})\n'
    reply += f'• [sfirmware.com]({url3})\n'
    reply += f'• [samfw.com]({url4})\n'
    update.message.reply_text("{}".format(reply),
                           parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

@run_async
def twrp(bot, update, args):
    if len(args) == 0:
        reply='No codename provided, write a codename for fetching informations.'
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return

    device = " ".join(args)
    url = get(f'https://eu.dl.twrp.me/{device}/')
    if url.status_code == 404:
        reply = f"Couldn't find twrp downloads for {device}!\n"
        del_msg = update.effective_message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        time.sleep(5)
        try:
            del_msg.delete()
            update.effective_message.delete()
        except BadRequest as err:
            if (err.message == "Message to delete not found" ) or (err.message == "Message can't be deleted" ):
                return
    else:
        reply = f'*Latest Official TWRP for {device}*\n'            
        db = get(DEVICES_DATA).json()
        newdevice = device.strip('lte') if device.startswith('beyond') else device
        try:
            brand = db[newdevice][0]['brand']
            name = db[newdevice][0]['name']
            reply += f'*{brand} - {name}*\n'
        except KeyError as err:
            pass
        page = BeautifulSoup(url.content, 'lxml')
        date = page.find("em").text.strip()
        reply += f'*Updated:* {date}\n'
        trs = page.find('table').find_all('tr')
        row = 2 if trs[0].find('a').text.endswith('tar') else 1
        for i in range(row):
            download = trs[i].find('a')
            dl_link = f"https://eu.dl.twrp.me{download['href']}"
            dl_file = download.text
            size = trs[i].find("span", {"class": "filesize"}).text
            reply += f'[{dl_file}]({dl_link}) - {size}\n'

        update.message.reply_text("{}".format(reply),
                               parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)

__help__ = """
*Android related commands:*

 - /magisk - gets the latest magisk release for Stable/Beta/Canary
 - /device <codename> - gets android device basic info from its codename
 - /twrp <codename> -  gets latest twrp for the android device using the codename
 - /checkfw <model> <csc> - Samsung only - shows the latest firmware info for the given device, taken from samsung servers
 - /getfw <model> <csc> - Samsung only - gets firmware download links from samfrew, sammobile and sfirmwares for the given device
 
 *Examples:*
  /device greatlte
  /twrp a5y17lte
  /checkfw SM-A305F INS
  /getfw SM-M205FN SER
 
"""

__mod_name__ = "Android"

MAGISK_HANDLER = DisableAbleCommandHandler("magisk", magisk)
DEVICE_HANDLER = DisableAbleCommandHandler("device", device, pass_args=True)
TWRP_HANDLER = DisableAbleCommandHandler("twrp", twrp, pass_args=True)
GETFW_HANDLER = DisableAbleCommandHandler("getfw", getfw, pass_args=True)
CHECKFW_HANDLER = DisableAbleCommandHandler("checkfw", checkfw, pass_args=True)

dispatcher.add_handler(MAGISK_HANDLER)
dispatcher.add_handler(DEVICE_HANDLER)
dispatcher.add_handler(TWRP_HANDLER)
dispatcher.add_handler(GETFW_HANDLER)
dispatcher.add_handler(CHECKFW_HANDLER)
