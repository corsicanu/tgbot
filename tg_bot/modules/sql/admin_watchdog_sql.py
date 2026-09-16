import threading
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime

from tg_bot.modules.sql import BASE, SESSION


class ChatAdminWatch(BASE):
    __tablename__ = "chat_admin_watch"
    chat_id = Column(String(14), primary_key=True)
    first_seen = Column(DateTime, nullable=False)
    ever_admin = Column(Boolean, default=False, nullable=False)

    def __init__(self, chat_id, first_seen=None, ever_admin=False):
        self.chat_id = str(chat_id)
        self.first_seen = first_seen or datetime.utcnow()
        self.ever_admin = ever_admin

    def __repr__(self):
        return "<ChatAdminWatch {} (ever_admin={})>".format(
            self.chat_id, self.ever_admin)


ChatAdminWatch.__table__.create(checkfirst=True)

INSERTION_LOCK = threading.RLock()


def get_watch(chat_id):
    try:
        return SESSION.query(ChatAdminWatch).get(str(chat_id))
    finally:
        SESSION.close()


def mark_chat_joined(chat_id):
    """Record the first time we saw ourselves in this chat, without a
    confirmed admin status yet. No-op if we already have a record - joining
    again shouldn't reset an existing grace timer."""
    with INSERTION_LOCK:
        watch = SESSION.query(ChatAdminWatch).get(str(chat_id))
        if not watch:
            watch = ChatAdminWatch(chat_id)
            SESSION.add(watch)
            SESSION.commit()
        else:
            SESSION.close()


def mark_chat_admin(chat_id):
    """We've confirmed we're admin in this chat - clears the grace timer
    concern going forward, since demotion is handled separately."""
    with INSERTION_LOCK:
        watch = SESSION.query(ChatAdminWatch).get(str(chat_id))
        if not watch:
            watch = ChatAdminWatch(chat_id, ever_admin=True)
            SESSION.add(watch)
        else:
            watch.ever_admin = True
            SESSION.add(watch)
        SESSION.commit()


def remove_chat(chat_id):
    """Drop the record - used when we leave/are removed from a chat, so a
    future re-add starts a fresh grace period."""
    with INSERTION_LOCK:
        watch = SESSION.query(ChatAdminWatch).get(str(chat_id))
        if watch:
            SESSION.delete(watch)
            SESSION.commit()
        else:
            SESSION.close()
