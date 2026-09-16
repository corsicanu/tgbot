import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User, MessageEntity
from telegram.error import BadRequest
from telegram.ext import run_async, CommandHandler, Filters
from telegram.utils.helpers import mention_html
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, User, CallbackQuery

from tg_bot import dispatcher, CallbackContext, BAN_STICKER, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_ban_protected, can_restrict, \
    is_user_admin, is_user_in_chat, is_bot_admin
from tg_bot.modules.helper_funcs.extraction import extract_user_and_text, extract_multiple_users
from tg_bot.modules.helper_funcs.string_handling import extract_time
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.perms import check_perms


@bot_admin
@can_restrict
@user_admin
@loggable
def ban(update: Update, context: CallbackContext):
    if not check_perms(update, 1):
        return
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    banType = 0
    userIds = extract_multiple_users(message, args)
    allTrue = True
    for id in userIds:
        if id is None or not isinstance(id, int) or id == "":
            allTrue = False
    if len(userIds) > 1 and allTrue:
        banType = 1
    if banType == 1:
        if len(userIds) == 0:
            message.reply_text("There was a problem parsing the user IDs")
            return ""
        log = "#BAN MUL\n Admin: " + user.first_name + "\n"
        for id in userIds:
            try:
                integerID = int(id)
                member = chat.get_member(integerID)
                if integerID == bot.id:
                    message.reply_text("I wont ban myself... " +
                                       str(integerID) + " is my ID.")
                    continue
                if integerID == 777000 or integerID == 1087968824:
                    message.reply_text(
                        str(integerID) +
                        " is an account reserved for telegram, I cannot ban it"
                    )
                    continue
                if is_user_ban_protected(chat, integerID, member):
                    message.reply_text("Can't ban " + str(integerID) +
                                       ", user is ban protected.")
                    continue
                try:
                    chat.ban_member(integerID)
                    # bot.send_sticker(update.effective_chat.id, BAN_STICKER)  # ban sticker
                    reply = "{} has been banned!".format(
                        mention_html(member.user.id, member.user.first_name))
                    message.reply_text(reply, parse_mode=ParseMode.HTML)
                    log += "ID: " + str(member.user.id) + "\n"
                except BadRequest as excp:
                    LOGGER.warning(update)
                    LOGGER.exception(
                        "ERROR banning user %s in chat %s (%s) due to %s",
                        integerID, chat.title, chat.id, excp.message)
                    message.reply_text("Well damn, I can't ban " +
                                       str(integerID))
            except ValueError:
                message.reply_text("Error parsing the ID: " + id +
                                   " is not a valid user ID")
            except BadRequest as excp:
                if excp.message == "User not found":
                    message.reply_text("User " + str(integerID) +
                                       "has not been found")
                    continue
                else:
                    raise
        return log

    else:
        user_id, reason = extract_user_and_text(message, args)
        if not user_id or int(user_id) == 777000 or int(user_id) == 1087968824:
            message.reply_text("You don't seem to be referring to a user.")
            return ""
        try:
            member = chat.get_member(user_id)
        except BadRequest as excp:
            if excp.message == "User not found":
                message.reply_text("404 - user not found")
                return ""
            else:
                raise
        if user_id == bot.id:
            message.reply_text("hahahahahahaha nice try.. nope")
            return ""
        if is_user_ban_protected(chat, user_id, member):
            message.reply_text("Can't do that, user is admin..")
            return ""
        log = "<b>{}:</b>" \
              "\n#BANNED" \
              "\n<b>Admin:</b> {}" \
              "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                           mention_html(user.id, user.first_name),
                                                           mention_html(member.user.id, member.user.first_name),
                                                           member.user.id)
        if reason:
            log += "\n<b>Reason:</b> {}".format(reason)
        try:
            chat.ban_member(user_id)
            bot.send_sticker(update.effective_chat.id,
                             BAN_STICKER)  # ban sticker
            reply = "{} has been banned!".format(
                mention_html(member.user.id, member.user.first_name))
            reply += "\nReason: <code>{}</code>".format(
                reason) if reason else ""

            message.reply_text(reply, parse_mode=ParseMode.HTML)
            return log
        except BadRequest as excp:
            if excp.message == "Reply message not found":
                # Do not reply
                message.reply_text('Banned!', quote=False)
                return log
            else:
                LOGGER.warning(update)
                LOGGER.exception(
                    "ERROR banning user %s in chat %s (%s) due to %s", user_id,
                    chat.title, chat.id, excp.message)
                message.reply_text("Well damn, I can't ban that user.")
        return ""


@bot_admin
@can_restrict
@user_admin
@loggable
def temp_ban(update: Update, context: CallbackContext):
    if not check_perms(update, 1):
        return
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id or int(user_id) == 777000 or int(user_id) == 1087968824:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("404 - user not found")
            return ""
        else:
            raise

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Can't do that, user is admin..")
        return ""

    if user_id == bot.id:
        message.reply_text("hahahahahahaha nice try.. nope")
        return ""

    if not reason:
        message.reply_text(
            "You haven't specified a time to ban this user for!")
        return ""

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return ""

    log = "<b>{}:</b>" \
          "\n#TEMP BANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)" \
          "\n<b>Time:</b> {}".format(html.escape(chat.title),
                                     mention_html(user.id, user.first_name),
                                     mention_html(member.user.id, member.user.first_name),
                                     member.user.id,
                                     time_val)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    try:
        chat.ban_member(user_id, until_date=bantime)
        bot.send_sticker(chat.id, BAN_STICKER)  # ban sticker
        reply = "\nReason: <code>{}</code>".format(reason) if reason else ""
        message.reply_text("Banned! {} will be banned for {}.".format(
            mention_html(member.user.id, member.user.first_name), time_val) +
                           reply,
                           parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Reply message not found":
            # Do not reply
            message.reply_text(
                "Banned! User will be banned for {}.".format(time_val),
                quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("ERROR banning user %s in chat %s (%s) due to %s",
                             user_id, chat.title, chat.id, excp.message)
            message.reply_text("Well damn, I can't ban that user.")

    return ""


@bot_admin
@can_restrict
@user_admin
@loggable
def kick(update: Update, context: CallbackContext):
    if not check_perms(update, 1):
        return
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    banType = 0
    userIds = extract_multiple_users(message, args)
    allTrue = True
    for id in userIds:
        if id is None or not isinstance(id, int) or id == "":
            allTrue = False
    if len(userIds) > 1 and allTrue:
        banType = 1

    if banType == 1:
        if len(userIds) == 0:
            message.reply_text("There was a problem parsing the user IDs")
            return ""
        log = "#KICK_MUL\n Admin: " + user.first_name + "\n"
        for id in userIds:
            try:
                integerID = int(id)
                member = chat.get_member(integerID)
                if is_user_ban_protected(chat, integerID, member):
                    message.reply_text("Can't kick " + str(integerID) +
                                       ", user is ban protected.")
                    continue
                if integerID == bot.id:
                    message.reply_text("I wont ban myself... " +
                                       str(integerID) + " is my ID.")
                    continue
                if integerID == 777000 or integerID == 1087968824:
                    message.reply_text(
                        str(integerID) +
                        " is an account reserved for telegram, I cannot kick it"
                    )
                    continue
                res = chat.unban_member(integerID)
                if res:
                    #bot.send_sticker(chat.id, BAN_STICKER)  # ban sticker
                    reply = "{} has been kicked!".format(
                        mention_html(member.user.id, member.user.first_name))
                    message.reply_text(reply, parse_mode=ParseMode.HTML)
                    log += "ID: " + str(member.user.id) + "\n"
                else:
                    message.reply_text("Well damn, I can't kick that user.")
            except ValueError:
                message.reply_text("Error parsing the ID: " + id +
                                   " is not a valid user ID")
            except BadRequest as excp:
                if excp.message == "User not found":
                    message.reply_text("User " + str(integerID) +
                                       "has not been found")
                    continue
                else:
                    raise
        return log
    else:
        user_id, reason = extract_user_and_text(message, args)
        if not user_id or int(user_id) == 777000 or int(user_id) == 1087968824:
            message.reply_text("You don't seem to be referring to a user.")
            return ""
        try:
            member = chat.get_member(user_id)
        except BadRequest as excp:
            if excp.message == "User not found":
                message.reply_text("404 - user not found")
                return ""
            else:
                raise

        if is_user_ban_protected(chat, user_id):
            message.reply_text(
                "I'm not gonna kick an admin... Though I reckon it'd be pretty funny."
            )
            return ""

        if user_id == bot.id:
            message.reply_text("hahahahahahaha nice try.. nope")
            return ""

        res = chat.unban_member(user_id)  # unban on current user = kick
        if res:
            bot.send_sticker(chat.id, BAN_STICKER)  # ban sticker
            reply = "{} has been kicked!".format(
                mention_html(member.user.id, member.user.first_name))
            reply += "\nReason: <code>{}</code>".format(
                reason) if reason else ""
            message.reply_text(reply, parse_mode=ParseMode.HTML)

            log = "<b>{}:</b>" \
                  "\n#KICKED" \
                  "\n<b>Admin:</b> {}" \
                  "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                               mention_html(user.id, user.first_name),
                                                               mention_html(member.user.id, member.user.first_name),
                                                               member.user.id)
            if reason:
                log += "\n<b>Reason:</b> {}".format(reason)

            return log

        else:
            message.reply_text("Well damn, I can't kick that user.")

        return ""


@bot_admin
@can_restrict
def banme(update: Update, context: CallbackContext):
    bot = context.bot
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Sorry, can't do that")
        return

    res = update.effective_chat.ban_member(user_id)
    if res:
        update.effective_message.reply_text("You shall be banned.")
    else:
        update.effective_message.reply_text("Sorry, can't do that")


@bot_admin
@can_restrict
def kickme(update: Update, context: CallbackContext):
    bot = context.bot
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text("Sorry, can't do that")
        return

    res = update.effective_chat.unban_member(
        user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("Okay...")
    else:
        update.effective_message.reply_text("Sorry, can't do that")


@bot_admin
@can_restrict
@user_admin
@loggable
def unban(update: Update, context: CallbackContext):
    if not check_perms(update, 1):
        return
    bot, args = context.bot, context.args
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    user_id, reason = extract_user_and_text(message, args)

    if not user_id or int(user_id) == 777000 or int(user_id) == 1087968824:
        message.reply_text("You don't seem to be referring to a user.")
        return ""

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("404 - user not found")
            return ""
        else:
            raise

    if user_id == bot.id:
        message.reply_text("How would I unban myself if I wasn't here...?")
        return ""

    if is_user_in_chat(chat, user_id):
        message.reply_text("User is already in the chat...")
        return ""

    chat.unban_member(user_id)
    message.reply_text("Yep, {} can join!".format(
        mention_html(member.user.id, member.user.first_name)),
                       parse_mode=ParseMode.HTML)

    log = "<b>{}:</b>" \
          "\n#UNBANNED" \
          "\n<b>Admin:</b> {}" \
          "\n<b>User:</b> {} (<code>{}</code>)".format(html.escape(chat.title),
                                                       mention_html(user.id, user.first_name),
                                                       mention_html(member.user.id, member.user.first_name),
                                                       member.user.id)
    if reason:
        log += "\n<b>Reason:</b> {}".format(reason)

    return log


__help__ = """
Some people need to be publicly banned; spammers, annoyances, or just trolls.
This module allows you to do that easily, by exposing some common actions, so everyone will see!

 - /kickme: kicks the user who issued the command.
 - /banme: bans the user who issued the command.

*Admin only:*
 - /ban <userhandle1> <userhandle2> <userhandle3>: bans users. (via handle, or reply)
 - /tban <userhandle> x(m/h/d): bans a user for x time. (via handle, or reply). m = minutes, h = hours, d = days.
 - /unban <userhandle>: unbans a user. (via handle, or reply)
 - /kick <userhandle1> <userhandle2> <userhandle3>: kicks users. (via handle, or reply)

An example of temporarily banning someone:
`/tban @username 2h`; this bans a user for 2 hours.
"""

__mod_name__ = "Bans"

BAN_HANDLER = CommandHandler("ban",
                             ban,
                             filters=Filters.chat_type.groups,
                             run_async=True)
TEMPBAN_HANDLER = CommandHandler(["tban", "tempban"],
                                 temp_ban,
                                 filters=Filters.chat_type.groups,
                                 run_async=True)
KICK_HANDLER = CommandHandler("kick",
                              kick,
                              filters=Filters.chat_type.groups,
                              run_async=True)
UNBAN_HANDLER = CommandHandler("unban",
                               unban,
                               filters=Filters.chat_type.groups,
                               run_async=True)
KICKME_HANDLER = DisableAbleCommandHandler("kickme",
                                           kickme,
                                           filters=Filters.chat_type.groups,
                                           run_async=True)
RIPME_HANDLER = DisableAbleCommandHandler("rip",
                                          kickme,
                                          filters=Filters.chat_type.groups,
                                          run_async=True)
AFK_HANDLER = DisableAbleCommandHandler("afk",
                                        kickme,
                                        filters=Filters.chat_type.groups,
                                        run_async=True)
BANME_HANDLER = DisableAbleCommandHandler("banme",
                                          banme,
                                          filters=Filters.chat_type.groups,
                                          run_async=True)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(KICK_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(KICKME_HANDLER)
dispatcher.add_handler(RIPME_HANDLER)
dispatcher.add_handler(AFK_HANDLER)
dispatcher.add_handler(BANME_HANDLER)

