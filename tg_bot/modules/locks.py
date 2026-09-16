import html
from typing import Optional, List

import telegram.ext as tg
from telegram import Message, Chat, Update, Bot, ParseMode, User, MessageEntity, ChatPermissions
from telegram import TelegramError
from telegram.error import BadRequest
from telegram.ext import MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.locks_sql as sql
from tg_bot import dispatcher, CallbackContext, SUDO_USERS, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import can_delete, is_user_admin, user_not_admin, user_admin, \
    bot_can_delete, is_bot_admin, is_user_in_chat
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import users_sql
from tg_bot.modules.helper_funcs.perms import check_perms

LOCK_TYPES = {
    'sticker':
    Filters.sticker,
    'audio':
    Filters.audio,
    'voice':
    Filters.voice,
    'document':
    Filters.document & ~Filters.animation
    & CustomFilters.mime_type("application/vnd.android.package-archive"),
    'video':
    Filters.video,
    'videonote':
    Filters.video_note,
    'contact':
    Filters.contact,
    'photo':
    Filters.photo,
    'gif':
    Filters.animation,
    'url':
    Filters.entity(MessageEntity.URL)
    | Filters.caption_entity(MessageEntity.URL),
    'bots':
    Filters.status_update.new_chat_members,
    'forward':
    Filters.forwarded,
    'game':
    Filters.game,
    'location':
    Filters.location,
    'emoji':
    CustomFilters.has_emoji,
    'bigemoji':
    CustomFilters.is_emoji,
    'anonchannel':
    CustomFilters.is_anon_channel
}

GIF = Filters.animation
OTHER = Filters.game | Filters.sticker | GIF
MEDIA = Filters.audio | Filters.document & CustomFilters.mime_type(
    "application/vnd.android.package-archive"
) | Filters.video | Filters.video_note | Filters.voice | Filters.photo
MESSAGES = Filters.text | Filters.contact | Filters.location | Filters.venue | Filters.command | MEDIA | OTHER
PREVIEWS = Filters.entity("url")

RESTRICTION_TYPES = {
    'messages': MESSAGES,
    'media': MEDIA,
    'other': OTHER,
    # 'previews': PREVIEWS, # NOTE: this has been removed cos its useless atm.
    'all': Filters.all
}

PERM_GROUP = 1
REST_GROUP = 2


class CustomCommandHandler(tg.CommandHandler):
    def __init__(self, command, callback, **kwargs):
        super().__init__(command, callback, **kwargs)

    def check_update(self, update):
        if super().check_update(update) and not (sql.is_restr_locked(
                update.effective_chat.id, 'messages') and not is_user_admin(
                    update.effective_chat, update.effective_user.id)):
            args = update.effective_message.text.split()[1:]
            filter_result = self.filters(update)
            if filter_result:
                return args, filter_result
            else:
                return False


CommandHandler = CustomCommandHandler


# NOT ASYNC
def restr_members(bot,
                  chat_id,
                  members,
                  messages=False,
                  media=False,
                  other=False,
                  previews=False):
    for mem in members:
        if (mem.user in SUDO_USERS):
            pass
        elif mem.user == 777000 or mem.user == 1087968824:
            pass
        try:
            bot.restrict_chat_member(chat_id,
                                     mem.user,
                                     permissions=ChatPermissions(
                                         can_send_messages=messages,
                                         can_send_media_messages=media,
                                         can_send_other_messages=other,
                                         can_add_web_page_previews=previews))
        except TelegramError:
            pass


# NOT ASYNC
def unrestr_members(bot,
                    chat_id,
                    members,
                    messages=True,
                    media=True,
                    other=True,
                    previews=True):
    for mem in members:
        try:
            bot.restrict_chat_member(chat_id,
                                     mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


def locktypes(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        "\n - ".join(["Locks: "] + list(LOCK_TYPES) + list(RESTRICTION_TYPES)))


@user_admin
@bot_can_delete
@loggable
def lock(update: Update, context: CallbackContext) -> str:
    if not check_perms(update, 1):
        return
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if can_delete(chat, bot.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sql.update_lock(chat.id, args[0], locked=True)
                message.reply_text(
                    "Locked {} messages for all non-admins!".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[0], locked=True)
                if args[0] == "previews":
                    members = users_sql.get_chat_members(str(chat.id))
                    restr_members(bot,
                                  chat.id,
                                  members,
                                  messages=True,
                                  media=True,
                                  other=True)
                    bot.restrict_chat_member(
                        chat.id,
                        int(777000),
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True))

                    bot.restrict_chat_member(
                        chat.id,
                        int(1087968824),
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True))

                message.reply_text("Locked {} for all non-admins!".format(
                    args[0]))
                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            else:
                message.reply_text(
                    "What are you trying to lock...? Try /locktypes for the list of lockables"
                )

    else:
        message.reply_text(
            "I'm not an administrator, or haven't got delete rights.")

    return ""


@user_admin
@loggable
def unlock(update: Update, context: CallbackContext) -> str:
    if not check_perms(update, 1):
        return
    bot, args = context.bot, context.args
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]

    if is_user_admin(chat, message.from_user.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sql.update_lock(chat.id, args[0], locked=False)
                message.reply_text("Unlocked {} for everyone!".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[0], locked=False)
                """
                members = users_sql.get_chat_members(chat.id)
                if args[0] == "messages":
                    unrestr_members(bot, chat.id, members, media=False, other=False, previews=False)

                elif args[0] == "media":
                    unrestr_members(bot, chat.id, members, other=False, previews=False)

                elif args[0] == "other":
                    unrestr_members(bot, chat.id, members, previews=False)

                elif args[0] == "previews":
                    unrestr_members(bot, chat.id, members)

                elif args[0] == "all":
                    unrestr_members(bot, chat.id, members, True, True, True, True)
                """
                message.reply_text("Unlocked {} for everyone!".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])
            else:
                message.reply_text(
                    "What are you trying to unlock...? Try /locktypes for the list of lockables"
                )

        else:
            bot.sendMessage(chat.id, "What are you trying to unlock...?")

    return ""


@user_not_admin
def del_lockables(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user
    if int(user.id) == 777000 or int(
            user.id
    ) == 1087968824:  #777000 is the telegram notification service bot ID.
        return  #Group channel notifications are sent via this bot. This adds exception to this userid

    for lockable, filter in LOCK_TYPES.items():
        if filter(update) and sql.is_locked(chat.id, lockable) and can_delete(
                chat, bot.id):
            if lockable == "bots":
                new_members = update.effective_message.new_chat_members
                for new_mem in new_members:
                    if new_mem.is_bot:
                        if not is_bot_admin(chat, bot.id):
                            message.reply_text(
                                "I see a bot, and I've been told to stop them joining... "
                                "but I'm not admin!")
                            return

                        chat.ban_member(new_mem.id)
                        message.reply_text(
                            "Only admins are allowed to add bots to this chat! Get outta here."
                        )
            else:
                try:
                    message.delete()
                except BadRequest as excp:
                    if excp.message == "Message to delete not found":
                        pass
                    else:
                        LOGGER.exception("ERROR in lockables")

            break


@user_not_admin
def rest_handler(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user
    if (user.id == 777000) or (
            user.id == 1087968824
    ):  #777000 is the telegram notification service bot ID.
        return  #Group channel notifications are sent via this bot. This adds exception to this userid

    for restriction, filter in RESTRICTION_TYPES.items():
        if filter(update) and sql.is_restr_locked(
                chat.id, restriction) and can_delete(chat, bot.id):
            try:
                msg.delete()
            except BadRequest as excp:
                if excp.message == "Message to delete not found":
                    pass
                else:
                    LOGGER.exception("ERROR in restrictions")
            break


def build_lock_message(chat_id):
    locks = sql.get_locks(chat_id)
    restr = sql.get_restr(chat_id)
    if not (locks or restr):
        res = "There are no current locks in this chat."
    else:
        res = "These are the locks in this chat:"
        if locks:
            res += "\n - sticker = `{}`" \
                   "\n - audio = `{}`" \
                   "\n - voice = `{}`" \
                   "\n - document = `{}`" \
                   "\n - video = `{}`" \
                   "\n - videonote = `{}`" \
                   "\n - contact = `{}`" \
                   "\n - photo = `{}`" \
                   "\n - gif = `{}`" \
                   "\n - url = `{}`" \
                   "\n - bots = `{}`" \
                   "\n - forward = `{}`" \
                   "\n - game = `{}`" \
                   "\n - location = `{}`" \
                   "\n - emoji = `{}`" \
                   "\n - bigemoji = `{}`" \
                   "\n - anonchannel = `{}`".format(locks.sticker, locks.audio, locks.voice, locks.document,
                                                 locks.video, locks.videonote, locks.contact, locks.photo, locks.gif, locks.url,
                                                 locks.bots, locks.forward, locks.game, locks.location, locks.emoji, locks.bigemoji,
                                                 locks.anonchannel)
        if restr:
            res += "\n - messages = `{}`" \
                   "\n - media = `{}`" \
                   "\n - other = `{}`" \
                   "\n - previews = `{}`" \
                   "\n - all = `{}`".format(restr.messages, restr.media, restr.other, restr.preview,
                                            all([restr.messages, restr.media, restr.other, restr.preview]))
    return res


@user_admin
def list_locks(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]

    res = build_lock_message(chat.id)

    update.effective_message.reply_text(res, parse_mode=ParseMode.MARKDOWN)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return build_lock_message(chat_id)


__help__ = """
Do stickers annoy you? or want to avoid people sharing links? or pictures? \
You're in the right place!

The locks module allows you to lock away some common items in the \
telegram world; the bot will automatically delete them!

 - /locktypes: a list of possible locktypes

*Admin only:*
 - /lock <type>: lock items of a certain type (not available in private)
 - /unlock <type>: unlock items of a certain type (not available in private)
 - /locks: the current list of locks in this chat.

Locks can be used to restrict a group's users.
eg:
Locking urls will auto-delete all messages with urls, locking stickers will delete all \
stickers, etc.
Locking bots will stop non-admins from adding bots to the chat.
"""

__mod_name__ = "Locks"

LOCKTYPES_HANDLER = DisableAbleCommandHandler("locktypes",
                                              locktypes,
                                              run_async=True)
LOCK_HANDLER = CommandHandler("lock", lock, filters=Filters.chat_type.groups)
UNLOCK_HANDLER = CommandHandler("unlock",
                                unlock,
                                run_async=True,
                                filters=Filters.chat_type.groups)
LOCKED_HANDLER = CommandHandler("locks",
                                list_locks,
                                filters=Filters.chat_type.groups,
                                run_async=True)

dispatcher.add_handler(LOCK_HANDLER)
dispatcher.add_handler(UNLOCK_HANDLER)
dispatcher.add_handler(LOCKTYPES_HANDLER)
dispatcher.add_handler(LOCKED_HANDLER)

dispatcher.add_handler(
    MessageHandler(Filters.all & Filters.chat_type.groups,
                   del_lockables,
                   run_async=True), PERM_GROUP)
dispatcher.add_handler(
    MessageHandler(Filters.all & Filters.chat_type.groups,
                   rest_handler,
                   run_async=True), REST_GROUP)

