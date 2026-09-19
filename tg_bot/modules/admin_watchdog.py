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

import time
from datetime import datetime, timedelta

from telegram import Update
from telegram.error import BadRequest, Unauthorized, TelegramError
from telegram.ext import MessageHandler, Filters

from tg_bot import dispatcher, updater, CallbackContext, LOGGER, OWNER_ID
from tg_bot.modules.sql.users_sql import get_all_chats
from tg_bot.modules.sql import admin_watchdog_sql as sql

# how long a newly-added bot gets to be made admin before it leaves
GRACE_PERIOD = timedelta(hours=24)
# how often the watchdog re-checks every known chat
POLL_INTERVAL_SECONDS = 30 * 60
POLL_FIRST_DELAY_SECONDS = 60
# pause between leave_chat() calls so a big backlog doesn't trip
# Telegram's flood control (which would then crash the whole run)
LEAVE_THROTTLE_SECONDS = 0.3
# keep a single digest message under Telegram's ~4096 char limit
DIGEST_CHUNK_CHARS = 3500

# get_chat_member errors that mean "we're not usefully in this chat anymore" -
# clean up our record rather than treating it as a pending grace period
NOT_IN_CHAT_ERRORS = {
    "Chat_admin_required", "Chat not found", "Peer_id_invalid",
    "User not found", "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups",
}


def _leave(bot, chat_id, chat_name, reason):
    """Leave a chat. Returns True only once we're sure it's handled - if
    leave_chat itself fails with something like flood control, we
    deliberately leave the DB record alone so the *same* chat is retried
    on the next poll, instead of losing track of it and it staying stuck
    in limbo (which is what was causing chats to reappear in the leave
    notifications long after the bot had actually already left them)."""
    try:
        bot.leave_chat(int(chat_id))
    except (BadRequest, Unauthorized):
        pass  # already not in the chat one way or another - fine
    except TelegramError as excp:
        LOGGER.warning("admin_watchdog: leave_chat failed for %s: %s",
                       chat_id, excp)
        return False

    sql.remove_chat(chat_id)
    LOGGER.info("admin_watchdog: left chat %s (%s) - %s", chat_id, chat_name,
               reason)
    return True


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


def _notify_left(bot, left):
    """One digest DM (chunked if long) instead of one DM per chat - firing
    off hundreds of individual send_message calls back-to-back risks
    hitting flood control on the notification itself too."""
    header = "Left {} chat(s) this run:\n".format(len(left))
    lines = [
        "- <b>{}</b> (<code>{}</code>): {}".format(name or cid, cid, reason)
        for cid, name, reason in left
    ]

    chunk = header
    for line in lines:
        if len(chunk) + len(line) + 1 > DIGEST_CHUNK_CHARS:
            _send_digest_chunk(bot, chunk)
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        _send_digest_chunk(bot, chunk)


def _send_digest_chunk(bot, text):
    try:
        bot.send_message(OWNER_ID, text, parse_mode="HTML")
    except TelegramError as excp:
        LOGGER.warning("admin_watchdog: couldn't send leave digest: %s",
                       excp)


def check_admin_status(context: CallbackContext):
    bot = context.bot
    now = datetime.utcnow()
    left = []  # (chat_id, chat_name, reason) actually confirmed left this run

    for chat in get_all_chats() or []:
        chat_id = chat.chat_id
        chat_name = chat.chat_name

        try:
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

            reason = None
            if watch.ever_admin:
                reason = "was admin, got demoted/removed as admin"
            elif now - watch.first_seen >= GRACE_PERIOD:
                reason = "never made admin within {}".format(GRACE_PERIOD)

            if reason and _leave(bot, chat_id, chat_name, reason):
                left.append((chat_id, chat_name, reason))
                time.sleep(LEAVE_THROTTLE_SECONDS)
        except Exception:
            # never let one bad chat take the whole run down - that's what
            # left chats stuck half-processed and got them re-flagged (and
            # re-notified) on the following poll
            LOGGER.exception("admin_watchdog: unexpected error on chat %s",
                            chat_id)
            continue

    if left and OWNER_ID:
        _notify_left(bot, left)


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
