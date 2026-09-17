"""
Leaves chats where the bot isn't admin.

- Bot gets added to a chat -> starts a grace timer. If it's still not admin
  once the timer expires, it leaves.
- Bot was admin and gets demoted -> leaves on the next poll (no grace period,
  since it was already trusted once and something changed).
- Bot leaves/gets removed and is re-added later -> treated as a brand new
  join, fresh grace timer.

There's no reliable "bot was promoted/demoted" event on this bot API version
(no my_chat_member updates), so this is poll-based: a repeating job checks
every known group's own membership status and acts on it.
"""

from datetime import datetime, timedelta

from telegram import Update
from telegram.error import BadRequest, Unauthorized
from telegram.ext import MessageHandler, Filters

from tg_bot import dispatcher, updater, CallbackContext, LOGGER, OWNER_ID
from tg_bot.modules.sql.users_sql import get_all_chats
from tg_bot.modules.sql import admin_watchdog_sql as sql

# how long a newly-added bot gets to be made admin before it leaves
GRACE_PERIOD = timedelta(hours=24)
# how often the watchdog re-checks every known chat
POLL_INTERVAL_SECONDS = 30 * 60
POLL_FIRST_DELAY_SECONDS = 60

# get_chat_member errors that mean "we're not usefully in this chat anymore" -
# clean up our record rather than treating it as a pending grace period
NOT_IN_CHAT_ERRORS = {
    "Chat_admin_required", "Chat not found", "Peer_id_invalid",
    "User not found", "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
}


def _leave(bot, chat_id, chat_name, reason):
    try:
        bot.leave_chat(int(chat_id))
    except (BadRequest, Unauthorized):
        pass
    sql.remove_chat(chat_id)
    LOGGER.info("admin_watchdog: left chat %s (%s) - %s", chat_id, chat_name,
               reason)
    if OWNER_ID:
        try:
            bot.send_message(
                OWNER_ID,
                "Left <b>{}</b> (<code>{}</code>): {}".format(
                    chat_name or chat_id, chat_id, reason),
                parse_mode="HTML")
        except (BadRequest, Unauthorized):
            pass


def on_bot_added(update: Update, context: CallbackContext):
    bot = context.bot
    msg = update.effective_message
    if not any(member.id == bot.id for member in msg.new_chat_members):
        return
    sql.mark_chat_joined(update.effective_chat.id)


def on_bot_removed(update: Update, context: CallbackContext):
    bot = context.bot
    msg = update.effective_message
    if msg.left_chat_member.id != bot.id:
        return
    sql.remove_chat(update.effective_chat.id)


def check_admin_status(context: CallbackContext):
    bot = context.bot
    now = datetime.utcnow()

    for chat in get_all_chats() or []:
        chat_id = chat.chat_id
        chat_name = chat.chat_name

        try:
            member = bot.get_chat_member(int(chat_id), bot.id)
        except BadRequest as excp:
            if excp.message in NOT_IN_CHAT_ERRORS:
                sql.remove_chat(chat_id)
            else:
                LOGGER.warning("admin_watchdog: couldn't check %s: %s",
                              chat_id, excp.message)
            continue
        except Unauthorized:
            # bot was kicked/banned - nothing to leave, just stop tracking
            sql.remove_chat(chat_id)
            continue

        if member.status in ('administrator', 'creator'):
            sql.mark_chat_admin(chat_id)
            continue

        # bot is in the chat, but not admin
        watch = sql.get_watch(chat_id)

        if not watch:
            # first time we've observed this chat not-admin - start the
            # grace period now rather than retroactively
            sql.mark_chat_joined(chat_id)
            continue

        if watch.ever_admin:
            _leave(bot, chat_id, chat_name,
                  "was admin, got demoted/removed as admin")
            continue

        if now - watch.first_seen >= GRACE_PERIOD:
            _leave(bot, chat_id, chat_name,
                  "never made admin within {}".format(GRACE_PERIOD))


__help__ = ""
__mod_name__ = "Admin Watchdog"

NEW_MEMBER_HANDLER = MessageHandler(Filters.status_update.new_chat_members,
                                    on_bot_added,
                                    run_async=True)
LEFT_MEMBER_HANDLER = MessageHandler(Filters.status_update.left_chat_member,
                                     on_bot_removed,
                                     run_async=True)

# unused elsewhere (existing groups: 0 default/welcome, 1-4, 6, 9-11) -
# own group so we only *observe* joins/leaves, never block group-0
# handlers like welcome.py's greet/goodbye messages
WATCHDOG_GROUP = 20

dispatcher.add_handler(NEW_MEMBER_HANDLER, WATCHDOG_GROUP)
dispatcher.add_handler(LEFT_MEMBER_HANDLER, WATCHDOG_GROUP)

updater.job_queue.run_repeating(check_admin_status,
                                interval=POLL_INTERVAL_SECONDS,
                                first=POLL_FIRST_DELAY_SECONDS,
                                name="admin_watchdog")
