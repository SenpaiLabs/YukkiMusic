# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import platform
import sys

from pyrogram import __version__, filters, types
from pytgcalls import __version__ as pytgver

from anony import app, config, db, lang, userbot
from anony.helpers import utils
from anony.plugins import all_modules


@app.on_message(filters.command(["stats"]) & filters.group & ~app.bl_users)
@lang.language()
async def _stats(_, m: types.Message):
    sent = await m.reply_photo(
        photo=config.PING_IMG,
        caption=m.lang["stats_fetching"],
    )

    _utext = m.lang["stats_user"].format(
        app.name,
        len(userbot.clients),
        config.AUTO_LEAVE,
        len(db.blacklisted),
        len(app.bl_users),
        len(app.sudoers),
        len(await db.get_chats()),
        len(await db.get_users()),
    )
    if m.from_user.id in app.sudoers:
        sys_info = utils.get_sys_info()
        _utext += m.lang["stats_sudo"].format(
            len(all_modules),
            platform.system(),
            sys_info["mem_rss_mb"],
            sys_info["mem_total_gb"],
            sys_info["cpu_percent"],
            sys_info["cpu_count"],
            sys_info["disk_used_gb"],
            sys_info["disk_total_gb"],
            sys.version.split()[0],
            __version__,
            pytgver,
        )
    await sent.edit_caption(_utext)
