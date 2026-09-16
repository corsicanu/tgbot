import html
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import time
import requests
import os
from telegram import Message, Chat, Update, Bot, MessageEntity, ParseMode
from telegram.ext import CommandHandler, run_async, Filters
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher, CallbackContext, OWNER_ID, SUDO_USERS, SUPPORT_USERS, WHITELIST_USERS, BAN_STICKER
from tg_bot.__main__ import STATS, USER_INFO, GDPR
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin, is_user_admin
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.filters import CustomFilters

from geopy.geocoders import Nominatim
from telegram import Location

ETA_STRINGS = (
	"Flooding group chats...",
	"Starting time machine...",
	"Spamming XDA-general...",
	"Spamming the dev...",
	"Going to an oracle...",
	"Activating machine learning...",
	"Brute forcing password..."
)

RUN_STRINGS = (
    "Where do you think you're going?",
    "Huh? what? did they get away?",
    "ZZzzZZzz... Huh? what? oh, just them again, nevermind.",
    "Get back here!",
    "Not so fast...",
    "Look out for the wall!",
    "Don't leave me alone with them!!",
    "You run, you die.",
    "Jokes on you, I'm everywhere",
    "You're gonna regret that...",
    "You could also try /kickme, I hear that's fun.",
    "Go bother someone else, no-one here cares.",
    "You can run, but you can't hide.",
    "Is that all you've got?",
    "I'm behind you...",
    "You've got company!",
    "We can do this the easy way, or the hard way.",
    "You just don't get it, do you?",
    "Yeah, you better run!",
    "Please, remind me how much I care?",
    "I'd run faster if I were you.",
    "That's definitely the droid we're looking for.",
    "May the odds be ever in your favour.",
    "Famous last words.",
    "And they disappeared forever, never to be seen again.",
    "\"Oh, look at me! I'm so cool, I can run from a bot!\" - this person",
    "Yeah yeah, just tap /kickme already.",
    "Here, take this ring and head to Mordor while you're at it.",
    "Legend has it, they're still running...",
    "Unlike Harry Potter, your parents can't protect you from me.",
    "Fear leads to anger. Anger leads to hate. Hate leads to suffering. If you keep running in fear, you might "
    "be the next Vader.",
    "Multiple calculations later, I have decided my interest in your shenanigans is exactly 0.",
    "Legend has it, they're still running.",
    "Keep it up, not sure we want you here anyway.",
    "You're a wiza- Oh. Wait. You're not Harry, keep moving.",
    "NO RUNNING IN THE HALLWAYS!",
    "Hasta la vista, baby.",
    "Who let the dogs out?",
    "It's funny, because no one cares.",
    "Ah, what a waste. I liked that one.",
    "Frankly, my dear, I don't give a damn.",
    "My milkshake brings all the boys to yard... So run faster!",
    "You can't HANDLE the truth!",
    "A long time ago, in a galaxy far far away... Someone would've cared about that. Not anymore though.",
    "Hey, look at them! They're running from the inevitable banhammer... Cute.",
    "Han shot first. So will I.",
    "What are you running after, a white rabbit?",
    "As The Doctor would say... RUN!",
)

SLAP_TEMPLATES = (
    "{user1} {hits} {user2} with *{item}*. {emoji}",
    "{user1} {hits} {user2} in the face with *{item}*. {emoji}",
    "{user1} {hits} {user2} around a bit with *{item}*. {emoji}",
    "{user1} {throws} *{item}* at {user2}. {emoji}",
    "{user1} grabs *{item}* and {throws} it at {user2}'s face. {emoji}",
    "{user1} launches *{item}* in {user2}'s general direction. {emoji}",
    "{user1} starts slapping {user2} silly with *{item}*. {emoji}",
    "{user1} pins {user2} down and repeatedly {hits} them with *{item}*. {emoji}",
    "{user1} grabs up *{item}* and {hits} {user2} with it. {emoji}",
    "{user1} ties {user2} to a chair and {throws} *{item}* at them. {emoji}",
)

PUNCH_TEMPLATES = (
    "{user1} {punches} {user2} to assert dominance.",
    "{user1} {punches} {user2} to see if they shut the fuck up for once.",
    "{user1} {punches} {user2} because they were asking for it.",
    "It's over {user2}, they have the high ground.",
    "{user1} performs a superman punch on {user2}, {user2} is rekt now.",
    "{user1} kills off {user2} with a T.K.O",
    "{user1} attacks {user2} with a billiard cue. A bloody mess.",
    "{user1} disintegrates {user2} with a MG.",
    "A hit and run over {user2} performed by {user1}",
    "{user1} punches {user2} into the throat. Warning, choking hazard!",
    "{user1} drops a piano on top of {user2}. A harmonical death.",
    "{user1} throws rocks at {user2}",
    "{user1} forces {user2} to drink chlorox. What a painful death.",
    "{user2} got sliced in half by {user1}'s katana.",
    "{user1} makes {user2} fall on their sword. A stabby death lol.",
    "{user1} kangs {user2} 's life energy away.",
    "{user1} shoots {user2} into a million pieces. Hasta la vista baby.",
    "{user1} drops the frigde on {user2}. Beware of crushing.",
    "{user1} engages a guerilla tactic on {user2}",
    "{user1} ignites {user2} into flames. IT'S LIT FAM.",
    "{user1} pulls a loaded 12 gauge on {user2}.",
    "{user1} throws a Galaxy Note7 into {user2}'s general direction. A bombing massacre.",
    "{user1} walks with {user2} to the end of the world, then pushes him over the edge.",
    "{user1} performs a Stabby McStabby on {user2} with a butterfly.",
    "{user1} cuts {user2}'s neck off with a machete. A blood bath.",
    "{user1} secretly fills in {user2}'s cup with Belle Delphine's Gamer Girl Bathwater instead of water. Highly contagious herpes.",
    "{user1} is tea cupping on {user2} after a 1v1, to assert their dominance.",
    "{user1} asks for {user2}'s last words. {user2} is ded now.",
    "{user1} lets {user2} know their position.",
    "{user1} makes {user2} to his slave. What is your bidding? My Master.",
    "{user1} forces {user2} to commit suicide.",
    "{user1} shouts 'it's garbage day' at {user2}.",
    "{user1} throws his axe at {user2}.",
    "{user1} is now {user2}'s grim reaper.",
    "{user1} slappety slap's {user2}.",
    "{user1} ends the party.",
    "{user2} will never know what hit them.",
    "{user1} breaks {user2}'s neck like a kitkat.",
    "{user1} flings knives at {user2}.",
    "{user1} gangs {user2} in a drive by.",
    "Thanks to {user1}'s airstrike, {user2} is no more.",
    "{user1} waterboard's {user2}.",
    "{user1} hangs {user2} upside down.",
    "{user1} breaks (user2's) skull with a PS4.",
    "{user1} throws Xbox controller batteries at {user2}'s face.",
    "{user1} shouts 'Look at me, I'm the Captain now.' at {user2}.",
    "{user1} puts {user2} in their place.",
    "{user1} poisons {user2}'s meal, it was their last meal.",
    "{user1} burns {user2} into ashes.",
    "{user2} bites in the dust.",
    "{user1} stabs {user2} in their back, what a way to die.",
    "{user1} uses {user2} to play Fruit Ninja.",
    "{user1} blueballs {user2}.",
    "{user1} makes the fool die a fool's death.",
    "{user1} orders Agent 47 on {user2}'s ass.",
    "{user2} gets struck by a lightning. Warning, high tension.",
    "{user1} breaks all of {user2}'s bones.",
    "Someone save {user2} because {user1} is about to murder them.",
    "{user1} throws {user2} into a volcano.",
    "{user1} chokes {user2} through the force.",
    "{user1} throws their lightsaber at {user2}.",
    "{user1} orders a full broadside on {user2}.",
    "{user1} deploys the garrison on {user2}.",
    "{user1} lets freeze {user2} to death.",
    "{user1} throws {user2} across the room by the force.",
    "{user1} makes {user2} go crazy by high pitch sounds.",
    "{user1} rolls over {user2} with a Panzerkampfwagen VI Tiger.",
    "{user1} blows {user2} up with a bazooka.",
    "{user1} plays Sniper Elite with {user2} as the target.",
    "{user1} yeets {user2}'s ass.)",
    "{user1} puts a grenade in {user2}'s hood.",
    "{user1} throws an iPhone 11 Pro Max at {user2}'s face.",
    "{user1} throws a Galaxy S20 Ultra 5G at {user2}'s face.",
    "{user1} draws a dick on {user2}'s forehead.",
    "{user1} cuts open {user2}'s throat. Very bloody.",
    "{user1} shoots {user2} to dust with a AK-47.",
    "{user1} shoots {user2} to dust with the M1928 Thommy.",
    "{user1} shoots {user2} to dust with a StG-44.",
    "{user1} stashes a Glock.",
    "{user1} lands a headshot on {user2} with their M1911.",
    "{user1} lures {user2} on a minefield.",
    "{user1} wins over {user2} in a western 1v1.",
    "{user1} plays robbers and gendarmes with {user2}.",
    "{user1} shoots down {user2} with a MP-40.",
    "{user1} tries their new Model 37 shotgun on {user2}.",
    "{user1} steals all of {user2}'s money. Now they're broke af.",
    "{user1} drops a TV on {user2}.",
    "{user1} throws their Apple TV at {user2}.",
    "{user1} hijacks {user2}'s ship.",
    "Damn {user1}, why are you hating on {user2} so much? Show them some love.",
    "{user1} makes {user2} sign their death certificate.",
    "{user1} kangs everything what {user2} owns.",
    "{user1} manipulates {user2}'s breaks.",
    "{user1} ties {user2} down on the train tracks.",
    "{user1} chops {user2}'s arm off with their lightsaber.",
)

PUNCH = (
    "punches",
    "RKOs",
    "smashes the skull of",
    "throws a pipe wrench at",
)

ITEMS = (
    "a Samsung M10",
    "a Samsung S21 Ultra",
    "an iPhone XII Pro Max Ultra Lite",
    "a Note 20 Ultra",
    "knox 0x0",
    "knox 1x0",
    "knox 0x2",
    "OneUI 3.1",
    "OneUI 3.5",
    "OneUI 69.0",
    "TwoUI 1.0",
    "Secure Folder",
    "Samsung Pay",
    "Samsung Pass",
    "prenormal RMM state",
    "prenormal KG state",
    "a locked bootloader",
    "payment lock",
    "stock rom",
    "good rom",
    "latest Good Lock apps",
    "R OTA",
    "S OTA",
    "LineageOS 18.1",
    "LineageOS 19",
    "latest MIUI stable",
    "a bugless rom",
    "a kernel",
    "a kernal",
    "a karnal",
    "a karnel",
    "official TWRP",
    "official SHRP",
    "VOLTE",
    "kanged rom",
    "an antikang",
    "audio fix",
    "HWC fix",
    "mic fix",
    "random reboots",
    "bootloops",
    "unfiltered logs",
    "a keylogger",
    "120FPS",
    "120HZ",
    "144HZ",
    "a download link",
    "168h uptime",
    "a paypal link",
    "treble support",
    "EVO-X gsi",
    "R gsi",
    "R beta",
    "S beta",
    "a Rom Control",
    "a hamburger",
    "a cheeseburger",
    "a Big-Mac",
    "a Mercedes",
    "a Fiat",
)

THROW = (
    "throws",
    "flings",
    "chucks",
    "hurls",
)

HIT = (
    "hits",
    "whacks",
    "slaps",
    "smacks",
    "spanks",
    "bashes",
)
EMOJI = (
    "\U0001F923",
    "\U0001F602",
    "\U0001F922",
    "\U0001F605",
    "\U0001F606",
    "\U0001F609",
    "\U0001F60E",
    "\U0001F929",
    "\U0001F623",
    "\U0001F973",
    "\U0001F9D0",
    "\U0001F632",
)

GMAPS_LOC = "https://maps.googleapis.com/maps/api/geocode/json"
GMAPS_TIME = "https://maps.googleapis.com/maps/api/timezone/json"

SMACK_STRING = """[smack my beach up!!](https://vimeo.com/31482159)"""

@user_admin
def etaWen(update, context):
    eta = update.message.reply_text(text=random.choice(ETA_STRINGS))
    time.sleep(5)
    date = datetime.now() + timedelta(days=random.randrange(69, 969))
    eta.edit_text(date.strftime("%B %d, %Y") + "\n\nDate values might be inaccurate" + random.choice(EMOJI))

def runs(update: Update, context: CallbackContext):
    bot = context.bot
    running = update.effective_message
    if running.reply_to_message:
        update.effective_message.reply_to_message.reply_text(
            random.choice(RUN_STRINGS))
    else:
        update.effective_message.reply_text(random.choice(RUN_STRINGS))


def smack(update: Update, context: CallbackContext):
    bot = context.bot
    msg = update.effective_message
    if msg.reply_to_message:
        update.effective_message.reply_to_message.reply_text(
            SMACK_STRING,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True)
    else:
        update.effective_message.reply_text(SMACK_STRING,
                                            parse_mode=ParseMode.MARKDOWN,
                                            disable_web_page_preview=True)


def slap(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                                   msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id == bot.id or user_id == 777000:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user
    elif user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(SLAP_TEMPLATES)
    item = random.choice(ITEMS)
    hit = random.choice(HIT)
    throw = random.choice(THROW)
    emoji = random.choice(EMOJI)

    repl = temp.format(user1=user1,
                       user2=user2,
                       item=item,
                       hits=hit,
                       throws=throw,
                       emoji=emoji)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


def punch(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    msg = update.effective_message  # type: Optional[Message]

    # reply to correct message
    reply_text = msg.reply_to_message.reply_text if msg.reply_to_message else msg.reply_text

    # get user who sent message
    if msg.from_user.username:
        curr_user = "@" + escape_markdown(msg.from_user.username)
    else:
        curr_user = "[{}](tg://user?id={})".format(msg.from_user.first_name,
                                                   msg.from_user.id)

    user_id = extract_user(update.effective_message, args)
    if user_id == bot.id or user_id == 777000:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user
    elif user_id:
        slapped_user = bot.get_chat(user_id)
        user1 = curr_user
        if slapped_user.username:
            user2 = "@" + escape_markdown(slapped_user.username)
        else:
            user2 = "[{}](tg://user?id={})".format(slapped_user.first_name,
                                                   slapped_user.id)

    # if no target found, bot targets the sender
    else:
        user1 = "[{}](tg://user?id={})".format(bot.first_name, bot.id)
        user2 = curr_user

    temp = random.choice(PUNCH_TEMPLATES)
    punch = random.choice(PUNCH)

    repl = temp.format(user1=user1, user2=user2, punches=punch)

    reply_text(repl, parse_mode=ParseMode.MARKDOWN)


def get_id(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    user_id = extract_user(update.effective_message, args)
    if user_id:
        if update.effective_message.reply_to_message and update.effective_message.reply_to_message.forward_from:
            user1 = update.effective_message.reply_to_message.from_user
            user2 = update.effective_message.reply_to_message.forward_from
            update.effective_message.reply_text(
                "The original sender, {}, has an ID of `{}`.\nThe forwarder, {}, has an ID of `{}`."
                .format(escape_markdown(user2.first_name), user2.id,
                        escape_markdown(user1.first_name), user1.id),
                parse_mode=ParseMode.MARKDOWN)
        else:
            user = bot.get_chat(user_id)
            update.effective_message.reply_text("{}'s id is `{}`.".format(
                escape_markdown(user.first_name), user.id),
                                                parse_mode=ParseMode.MARKDOWN)
    else:
        chat = update.effective_chat  # type: Optional[Chat]
        if chat.type == "private":
            update.effective_message.reply_text("Your id is `{}`.".format(
                chat.id),
                                                parse_mode=ParseMode.MARKDOWN)

        else:
            update.effective_message.reply_text(
                "This group's id is `{}`.".format(chat.id),
                parse_mode=ParseMode.MARKDOWN)


def info(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    msg = update.effective_message  # type: Optional[Message]
    user_id = extract_user(update.effective_message, args)

    if user_id and int(user_id) != 777000 and int(user_id) != 1087968824:
        user = bot.get_chat(user_id)

    elif user_id and int(user_id) == 777000:
        msg.reply_text(
            "This is Telegram. Unless you manually entered this reserved account's ID, it is likely a old broadcast from a linked channel."
        )
        return

    elif user_id and int(user_id) == 1087968824:
        msg.reply_text(
            "This is Group Anonymous Bot. Unless you manually entered this reserved account's ID, it is likely a broadcast from a linked channel or anonymously sent message."
        )
        return

    elif not msg.reply_to_message and not args:
        user = msg.from_user

    elif not msg.reply_to_message and (
            not args or
        (len(args) >= 1 and not args[0].startswith("@")
         and not args[0].isdigit()
         and not msg.parse_entities([MessageEntity.TEXT_MENTION]))):
        msg.reply_text("I can't extract a user from this.")
        return
    else:
        return

    text = "<b>User info</b>:" \
           "\nID: <code>{}</code>" \
           "\nFirst Name: {}".format(user.id, html.escape(user.first_name))

    if user.last_name:
        text += "\nLast Name: {}".format(html.escape(user.last_name))

    if user.username:
        text += "\nUsername: @{}".format(html.escape(user.username))

    text += "\nPermanent user link: {}".format(mention_html(user.id, "link"))

    if user.id == OWNER_ID:
        text += "\n\nThis person is my owner - I would never do anything against them!"
    else:
        if user.id in SUDO_USERS:
            text += "\nThis person is one of my sudo users! " \
                    "Nearly as powerful as my owner - so watch it."
        else:
            if user.id in SUPPORT_USERS:
                text += "\nThis person is one of my support users! " \
                        "Not quite a sudo user, but can still gban you off the map."

            if user.id in WHITELIST_USERS:
                text += "\nThis person has been whitelisted! " \
                        "That means I'm not allowed to ban/kick them."

    for mod in USER_INFO:
        mod_info = mod.__user_info__(user.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


def get_time(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    location = " ".join(args)
    if location.lower() == bot.first_name.lower():
        update.effective_message.reply_text(
            "Its always banhammer time for me!")
        bot.send_sticker(update.effective_chat.id, BAN_STICKER)
        return

    res = requests.get(GMAPS_LOC, params=dict(address=location))

    if res.status_code == 200:
        loc = json.loads(res.text)
        if loc.get('status') == 'OK':
            lat = loc['results'][0]['geometry']['location']['lat']
            long = loc['results'][0]['geometry']['location']['lng']

            country = None
            city = None

            address_parts = loc['results'][0]['address_components']
            for part in address_parts:
                if 'country' in part['types']:
                    country = part.get('long_name')
                if 'administrative_area_level_1' in part['types'] and not city:
                    city = part.get('long_name')
                if 'locality' in part['types']:
                    city = part.get('long_name')

            if city and country:
                location = "{}, {}".format(city, country)
            elif country:
                location = country

            timenow = int(datetime.now(timezone.utc).timestamp())
            res = requests.get(GMAPS_TIME,
                               params=dict(location="{},{}".format(lat, long),
                                           timestamp=timenow))
            if res.status_code == 200:
                offset = json.loads(res.text)['dstOffset']
                timestamp = json.loads(res.text)['rawOffset']
                time_there = datetime.fromtimestamp(timenow + timestamp +
                                                    offset).strftime(
                                                        "%H:%M:%S on %A %d %B")
                update.message.reply_text("It's {} in {}".format(
                    time_there, location))


def echo(update: Update, context: CallbackContext):
    bot = context.bot
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message
    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)
    message.delete()


def gdpr(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if update.effective_user.id not in SUDO_USERS:
        update.effective_message.reply_text("Deleting identifiable data...")
        for mod in GDPR:
            mod.__gdpr__(update.effective_user.id)
        update.effective_message.reply_text(
            "Your personal data has been deleted.\n\nNote that this will not unban "
            "you from any chats, as that is telegram data, not this bot's data. "
            "Flooding, warns, and gbans are also preserved, as of "
            "[this](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/), "
            "which clearly states that the right to erasure does not apply "
            "\"for the performance of a task carried out in the public interest\", as is "
            "the case for the aforementioned pieces of data.",
            parse_mode=ParseMode.MARKDOWN)
    else:
        if len(args) == 0:
            update.effective_message.reply_text(
                "Deleting identifiable data...")
            for mod in GDPR:
                mod.__gdpr__(update.effective_user.id)
            update.effective_message.reply_text(
                "Your personal data has been deleted.\n\nNote that this will not unban "
                "you from any chats, as that is telegram data, not this bot's data. "
                "Flooding, warns, and gbans are also preserved, as of "
                "[this](https://ico.org.uk/for-organisations/guide-to-the-general-data-protection-regulation-gdpr/individual-rights/right-to-erasure/), "
                "which clearly states that the right to erasure does not apply "
                "\"for the performance of a task carried out in the public interest\", as is "
                "the case for the aforementioned pieces of data.",
                parse_mode=ParseMode.MARKDOWN)
        else:
            user_id = extract_user(update.effective_message, args)
            try:
                for mod in GDPR:
                    mod.__gdpr__(user_id)
                update.effective_message.reply_text(
                    "User data has been deleted",
                    parse_mode=ParseMode.MARKDOWN)
            except:
                update.effective_message.reply_text(
                    "User is not in my DB!", parse_mode=ParseMode.MARKDOWN)


MARKDOWN_HELP = """
Markdown is a very powerful formatting tool supported by telegram. {} has some enhancements, to make sure that \
saved messages are correctly parsed, and to allow you to create buttons.
- <code>_italic_</code>: wrapping text with '_' will produce italic text
- <code>*bold*</code>: wrapping text with '*' will produce bold text
- <code>`code`</code>: wrapping text with '`' will produce monospaced text, also known as 'code'
- <code>[sometext](someURL)</code>: this will create a link - the message will just show <code>sometext</code>, \
and tapping on it will open the page at <code>someURL</code>.
EG: <code>[test](example.com)</code>
- <code>[buttontext](buttonurl:someURL)</code>: this is a special enhancement to allow users to have telegram \
buttons in their markdown. <code>buttontext</code> will be what is displayed on the button, and <code>someurl</code> \
will be the url which is opened.
EG: <code>[This is a button](buttonurl:example.com)</code>
If you want multiple buttons on the same line, use :same, as such:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
This will create two buttons on a single line, instead of one button per line.
Keep in mind that your message <b>MUST</b> contain some text other than just a button!
""".format(dispatcher.bot.first_name)


def markdown_help(update: Update, context: CallbackContext):
    bot = context.bot
    update.effective_message.reply_text(MARKDOWN_HELP,
                                        parse_mode=ParseMode.HTML)
    update.effective_message.reply_text(
        "Try forwarding the following message to me, and you'll see!")
    update.effective_message.reply_text(
        "/save test This is a markdown test. _italics_, *bold*, `code`, "
        "[URL](example.com) [button](buttonurl:github.com) "
        "[button2](buttonurl://google.com:same)")


def stats(update: Update, context: CallbackContext):
    bot = context.bot
    update.effective_message.reply_text(
        "*Current stats:*\n" + "\n".join([mod.__stats__() for mod in STATS]),
        parse_mode=ParseMode.MARKDOWN)


def gps(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    if len(args) == 0:
        update.effective_message.reply_text(
            "That was a funny joke, but no really, put in a location")
    try:
        geolocator = Nominatim(user_agent="hades")
        location = " ".join(args)
        geoloc = geolocator.geocode(location)
        chat_id = update.effective_chat.id
        lon = geoloc.longitude
        lat = geoloc.latitude
        the_loc = Location(lon, lat)
        gm = "https://www.google.com/maps/search/{},{}".format(lat, lon)
        bot.send_location(chat_id, location=the_loc)
        update.message.reply_text("Open with: [Google Maps]({})".format(gm),
                                  parse_mode=ParseMode.MARKDOWN,
                                  disable_web_page_preview=True)
    except AttributeError:
        update.message.reply_text("I can't find that")


# /ip is for private use
__help__ = """
An "odds and ends" module for small, simple commands which don't really fit anywhere
 - /id: get the current group id. If used by replying to a message, gets that user's id.
 - /runs: reply a random string from an array of replies.
 - /spank: same as /slap but nastier.
 - /slap: slap a user, or get slapped if not a reply.
 - /info: get information about a user.
 - /gdpr: deletes your information from the bot's database. Private chats only.
 - /markdownhelp: quick summary of how markdown works in telegram - can only be called in private chats.
"""

__mod_name__ = "Misc"

ID_HANDLER = DisableAbleCommandHandler("id", get_id, run_async=True)

TIME_HANDLER = CommandHandler("time", get_time, run_async=True)

RUNS_HANDLER = DisableAbleCommandHandler("runs", runs, run_async=True)
SMACK_HANDLER = DisableAbleCommandHandler("smack", smack, run_async=True)
SLAP_HANDLER = DisableAbleCommandHandler("slap", slap, run_async=True)
PUNCH_HANDLER = DisableAbleCommandHandler("punch", punch, run_async=True)
SPANK_HANDLER = DisableAbleCommandHandler("spank", slap, run_async=True)
INFO_HANDLER = DisableAbleCommandHandler("info", info, run_async=True)
ETA_HANDLER = CommandHandler("eta",
                              etaWen,
                              filters=Filters.chat_type.groups,
                              run_async=True)
ECHO_HANDLER = CommandHandler("echo",
                              echo,
                              filters=Filters.user(OWNER_ID),
                              run_async=True)
MD_HELP_HANDLER = CommandHandler("markdownhelp",
                                 markdown_help,
                                 filters=Filters.private,
                                 run_async=True)

STATS_HANDLER = CommandHandler("stats",
                               stats,
                               filters=CustomFilters.sudo_filter,
                               run_async=True)
GDPR_HANDLER = CommandHandler("gdpr",
                              gdpr,
                              filters=Filters.private,
                              run_async=True)
GPS_HANDLER = DisableAbleCommandHandler("gps", gps, run_async=True)

dispatcher.add_handler(ID_HANDLER)
# dispatcher.add_handler(TIME_HANDLER)
dispatcher.add_handler(RUNS_HANDLER)
dispatcher.add_handler(SMACK_HANDLER)
dispatcher.add_handler(SLAP_HANDLER)
dispatcher.add_handler(PUNCH_HANDLER)
dispatcher.add_handler(SPANK_HANDLER)
dispatcher.add_handler(INFO_HANDLER)
dispatcher.add_handler(ECHO_HANDLER)
dispatcher.add_handler(ETA_HANDLER)
dispatcher.add_handler(MD_HELP_HANDLER)
dispatcher.add_handler(STATS_HANDLER)
dispatcher.add_handler(GDPR_HANDLER)
dispatcher.add_handler(GPS_HANDLER)

