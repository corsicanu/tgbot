from functools import wraps
from typing import Optional

from telegram import User, Chat, ChatMember, Update, Bot
from telegram.error import BadRequest

from tg_bot import CallbackContext, DEL_CMDS, SUDO_USERS, WHITELIST_USERS

# Errors that just mean "I can't tell / I'm not in a position to check" -
# never let these bubble up as unhandled exceptions from a per-message check.
IGNORABLE_MEMBER_ERRORS = {
    "Chat_admin_required", "Chat not found", "User not found",
    "Peer_id_invalid", "Not enough rights to restrict/unrestrict chat member",
    "Method is available for supergroup and channel chats only",
    "Method is available only for supergroups", "User_not_participant",
}


def _safe_get_member(chat: Chat, user_id: int) -> Optional[ChatMember]:
    """chat.get_member() that swallows the errors we can't do anything about
    (e.g. bot isn't admin, chat is a channel we can't query) instead of
    raising and taking down whatever handler called it."""
    try:
        return chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message in IGNORABLE_MEMBER_ERRORS:
            return None
        raise


def can_delete(chat: Chat, bot_id: int) -> bool:
    member = _safe_get_member(chat, bot_id)
    return bool(member) and member.can_delete_messages


def is_user_ban_protected(chat: Chat,
                          user_id: int,
                          member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or user_id in WHITELIST_USERS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = _safe_get_member(chat, user_id)
    if not member:
        return False
    return member.status in ('administrator', 'creator')


def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = _safe_get_member(chat, user_id)
    if not member:
        return False
    return member.status in ('administrator', 'creator')


def is_bot_admin(chat: Chat,
                 bot_id: int,
                 bot_member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = _safe_get_member(chat, bot_id)
    if not bot_member:
        return False
    return bot_member.status in ('administrator', 'creator')


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = _safe_get_member(chat, user_id)
    if not member:
        return False
    return member.status not in ('left', 'kicked')


def bot_can_delete(func):
    @wraps(func)
    def delete_rights(update: Update, context: CallbackContext, *args,
                      **kwargs):
        bot = context.bot
        if can_delete(update.effective_chat, bot.id):
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                "I can't delete messages here! "
                "Make sure I'm admin and can delete other user's messages.")

    return delete_rights


def can_pin(func):
    @wraps(func)
    def pin_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        member = _safe_get_member(update.effective_chat, bot.id)
        if member and member.can_pin_messages:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                "I can't pin messages here! "
                "Make sure I'm admin and can pin messages.")

    return pin_rights


def can_promote(func):
    @wraps(func)
    def promote_rights(update: Update, context: CallbackContext, *args,
                       **kwargs):
        bot = context.bot
        member = _safe_get_member(update.effective_chat, bot.id)
        if member and member.can_promote_members:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                "I can't promote/demote people here! "
                "Make sure I'm admin and can appoint new admins.")

    return promote_rights


def can_restrict(func):
    @wraps(func)
    def promote_rights(update: Update, context: CallbackContext, *args,
                       **kwargs):
        bot = context.bot
        member = _safe_get_member(update.effective_chat, bot.id)
        if member and member.can_restrict_members:
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text(
                "I can't restrict people here! "
                "Make sure I'm admin and can appoint new admins.")

    return promote_rights


def bot_admin(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        if is_bot_admin(update.effective_chat, bot.id):
            return func(update, context, *args, **kwargs)
        else:
            update.effective_message.reply_text("I'm not admin!")

    return is_admin


def user_admin(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user  # type: Optional[User]
        if user and is_user_admin(update.effective_chat, user.id):
            return func(update, context, *args, **kwargs)

        elif not user:
            pass

        else:
            update.effective_message.delete()

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user = update.effective_user  # type: Optional[User]
        if user and is_user_admin(update.effective_chat, user.id):
            return func(update, context, *args, **kwargs)

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

    return is_admin


def user_not_admin(func):
    @wraps(func)
    def is_not_admin(update: Update, context: CallbackContext, *args,
                     **kwargs):
        bot = context.bot
        user = update.effective_user  # type: Optional[User]
        if user and not is_user_admin(update.effective_chat, user.id):
            return func(update, context, *args, **kwargs)

    return is_not_admin

