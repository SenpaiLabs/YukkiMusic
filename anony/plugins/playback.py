# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from pyrogram import filters, types

from anony import anon, app, db, lang, queue
from anony.helpers import admin_only, buttons


# Pause
@app.on_message(filters.command(["pause"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_only(allow_auth=True)
async def _pause(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if not await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_already_paused"])

    await anon.pause(m.chat.id)
    await m.reply_text(
        text=m.lang["play_paused"].format(m.from_user.mention),
        reply_markup=buttons.controls(m.chat.id),
    )


# Resume
@app.on_message(filters.command(["resume"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_only(allow_auth=True)
async def _resume(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_not_paused"])

    await anon.resume(m.chat.id)
    await m.reply_text(
        text=m.lang["play_resumed"].format(m.from_user.mention),
        reply_markup=buttons.controls(m.chat.id),
    )


# Stop / End
@app.on_message(filters.command(["end", "stop"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_only(allow_auth=True)
async def _stop(_, m: types.Message):
    if len(m.command) > 1:
        return

    call = await db.get_call(m.chat.id)
    await anon.stop(m.chat.id)
    if not call:
        return await m.reply_text(m.lang["not_playing"])

    await m.reply_text(m.lang["play_stopped"].format(m.from_user.mention))


# Skip / Next
@app.on_message(filters.command(["skip", "next"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_only(allow_auth=True)
async def _skip(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    await anon.play_next(m.chat.id)
    await m.reply_text(m.lang["play_skipped"].format(m.from_user.mention))


# Seek / Seekback
@app.on_message(filters.command(["seek", "seekback"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_only(allow_auth=True)
async def _seek(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["play_seek_usage"].format(m.command[0]))

    try:
        to_seek = int(m.command[1])
    except ValueError:
        return await m.reply_text(m.lang["play_seek_usage"].format(m.command[0]))
    if to_seek < 10:
        return await m.reply_text(m.lang["play_seek_min"])

    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    if not await db.playing(m.chat.id):
        return await m.reply_text(m.lang["play_already_paused"])

    media = queue.get_current(m.chat.id)
    if not media.duration_sec:
        return await m.reply_text(m.lang["play_seek_no_dur"])

    sent = await m.reply_text(m.lang["play_seeking"])
    if m.command[0] == "seekback":
        stype = m.lang["backward"]
        start_from = media.time - to_seek
        if start_from < 1:
            start_from = 1
    else:
        stype = m.lang["forward"]
        start_from = media.time + to_seek
        if start_from + 10 > media.duration_sec:
            start_from = media.duration_sec - 5

    await anon.play_media(m.chat.id, sent, media, start_from)
    media.time = start_from
    await sent.edit_text(
        m.lang["play_seeked"].format(stype, start_from, m.from_user.mention)
    )


# Loop
@app.on_message(filters.command(["loop"]) & filters.group & ~app.bl_users)
@lang.language()
@admin_only(allow_auth=True)
async def _loop(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text(m.lang["not_playing"])

    chat_id = m.chat.id
    if len(m.command) < 2:
        if count := await db.get_loop(chat_id):
            return await m.reply_text(m.lang["loop_count"].format(count))
        return await m.reply_text(m.lang["loop_usage"])

    disable = m.command[1].lower() in ["off", "disable"]
    if not m.command[1].isdigit() and not disable:
        return await m.reply_text(m.lang["loop_usage"])

    loop = int(m.command[1]) if not disable else 0
    if loop < 1:
        loop = 0
    elif loop > 10:
        loop = 10

    await db.set_loop(m.chat.id, loop)
    if loop == 0:
        return await m.reply_text(m.lang["loop_off"])
    await m.reply_text(m.lang["loop_set"].format(loop))
