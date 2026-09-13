# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import datetime
import time

from pyrogram import filters, types
from anony import app, anon, boot, config, lang
from anony.helpers import buttons, utils


@app.on_message(filters.command(["alive", "ping"]) & ~app.bl_users)
@lang.language()
async def _ping(_, m: types.Message):
    start = time.time()
    sent = await m.reply_text(m.lang["pinging"])
    uptime = str(datetime.timedelta(seconds=int(time.time() - boot)))
    latency = round((time.time() - start) * 1000, 2)
    sys_info = utils.get_sys_info()
    await sent.edit_media(
        media=types.InputMediaPhoto(
            media=config.PING_IMG,
            caption=m.lang["ping_pong"].format(
                latency,
                uptime,
                sys_info["cpu_percent"],
                sys_info["mem_percent"],
                sys_info["disk_percent"],
                await anon.ping(),
            )
        ),
        reply_markup=buttons.ping_markup(m.lang["support"]),
    )
