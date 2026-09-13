# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from functools import wraps

from pyrogram import StopPropagation, enums, types

from anony import app, db


def admin_only(allow_auth: bool = False):
    def decorator(func):
        @wraps(func)
        async def wrapper(_, update: types.Message | types.CallbackQuery, *args, **kwargs):
            chat = (
                update.chat
                if isinstance(update, types.Message)
                else update.message.chat
            )
            if chat.type == enums.ChatType.PRIVATE:
                return await func(_, update, *args, **kwargs)

            user_id = update.from_user.id
            if user_id in app.sudoers:
                return await func(_, update, *args, **kwargs)

            if allow_auth and await db.is_auth(chat.id, user_id):
                return await func(_, update, *args, **kwargs)

            admins = await db.get_admins(chat.id)
            if user_id in admins:
                return await func(_, update, *args, **kwargs)

            msg = update.lang["user_no_perms"]
            if isinstance(update, types.Message):
                return await update.reply_text(msg)
            return await update.answer(msg, show_alert=True)

        return wrapper
    return decorator


def admin_check(func):
    return admin_only(allow_auth=False)(func)


def can_manage_vc(func):
    return admin_only(allow_auth=True)(func)


async def is_admin(chat_id: int, user_id: int) -> bool:
    if user_id in await db.get_admins(chat_id):
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        return member.status in [
            enums.ChatMemberStatus.ADMINISTRATOR,
            enums.ChatMemberStatus.OWNER,
        ]
    except Exception:
        raise StopPropagation


async def reload_admins(chat_id: int) -> list[int]:
    try:
        admins = [
            admin
            async for admin in app.get_chat_members(
                chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS
            )
            if not admin.user.is_bot
        ]
        return [admin.user.id for admin in admins]
    except Exception:
        return []
