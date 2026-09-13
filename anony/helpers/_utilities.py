# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import shutil

from pyrogram import enums, types

from anony import app


class Utilities:
    def __init__(self):
        pass

    def get_sys_info(self) -> dict:
        disk = shutil.disk_usage("/")
        disk_used_gb = f"{disk.used / (1024**3):.2f}"
        disk_total_gb = f"{disk.total / (1024**3):.2f}"
        disk_percent = round((disk.used / disk.total) * 100, 1)

        cpu_count = os.cpu_count() or 1
        cpu_percent = 0.0
        if hasattr(os, "getloadavg"):
            try:
                cpu_percent = round((os.getloadavg()[0] / cpu_count) * 100, 1)
            except Exception:
                pass

        mem_total_gb = 0
        mem_percent = 0.0
        mem_rss_mb = "0.00"

        if os.path.exists("/proc/meminfo"):
            try:
                mem = {}
                with open("/proc/meminfo") as f:
                    for line in f:
                        parts = line.split(":")
                        if len(parts) == 2:
                            mem[parts[0].strip()] = int(parts[1].split()[0])
                total = mem.get("MemTotal", 0)
                avail = mem.get("MemAvailable", mem.get("MemFree", 0))
                if total:
                    mem_total_gb = round(total / (1024**2))
                    mem_percent = round(((total - avail) / total) * 100, 1)
            except Exception:
                pass

        if os.path.exists("/proc/self/status"):
            try:
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            rss_kb = int(line.split()[1])
                            mem_rss_mb = f"{rss_kb / 1024:.2f}"
                            break
            except Exception:
                pass
        elif hasattr(os, "sysconf"):
            try:
                pages = os.sysconf("SC_PHYS_PAGES")
                page_size = os.sysconf("SC_PAGE_SIZE")
                mem_total_gb = round((pages * page_size) / (1024**3))
            except Exception:
                pass

        return {
            "cpu_count": cpu_count,
            "cpu_percent": cpu_percent,
            "disk_percent": disk_percent,
            "disk_used_gb": disk_used_gb,
            "disk_total_gb": disk_total_gb,
            "mem_percent": mem_percent,
            "mem_total_gb": mem_total_gb,
            "mem_rss_mb": mem_rss_mb,
        }

    def format_eta(self, seconds: int) -> str:
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d} min"
        else:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h}:{m:02d}:{s:02d} h"

    def format_size(self, bytes: int) -> str:
        if bytes >= 1024**3:
            return f"{bytes / 1024 ** 3:.2f} GB"
        elif bytes >= 1024**2:
            return f"{bytes / 1024 ** 2:.2f} MB"
        else:
            return f"{bytes / 1024:.2f} KB"

    def to_seconds(self, time: str) -> int:
        parts = [int(p) for p in time.strip().split(":")]
        return sum(value * 60**i for i, value in enumerate(reversed(parts)))


    def get_url(self, message_1: types.Message) -> str | None:
        link = None
        messages = [message_1]

        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            entities = message.entities or message.caption_entities or []

            for entity in entities:
                if entity.type == enums.MessageEntityType.TEXT_LINK:
                    link = entity.url
                    break
                elif entity.type == enums.MessageEntityType.URL:
                    text = message.text or message.caption
                    if not text:
                        continue
                    link = text[entity.offset: entity.offset + entity.length]
                    break

        if link:
            return link.split("&si")[0].split("?si")[0]
        return None


    async def extract_user(self, msg: types.Message) -> types.User | None:
        if msg.reply_to_message:
            return msg.reply_to_message.from_user

        if msg.entities:
            for e in msg.entities:
                if e.type == enums.MessageEntityType.TEXT_MENTION:
                    return e.user

        if msg.text:
            try:
                if m := re.search(r"@(\w{5,32})", msg.text):
                    return await app.get_users(m.group(0))
                if m := re.search(r"\b\d{6,15}\b", msg.text):
                    return await app.get_users(int(m.group(0)))
            except Exception:
                pass

        return None


    async def play_log(
        self,
        m: types.Message,
        link: str,
        title: str,
        duration: str,
    ) -> None:
        if m.chat.id == app.logger:
            return
        _text = m.lang["play_log"].format(
            app.name,
            m.chat.id,
            m.chat.title,
            m.from_user.id,
            m.from_user.mention,
            link,
            title,
            duration,
        )
        await app.send_message(chat_id=app.logger, text=_text)

    async def send_log(self, m: types.Message, chat: bool = False) -> None:
        if chat:
            user = m.from_user
            return await app.send_message(
                chat_id=app.logger,
                text=m.lang["log_chat"].format(
                    m.chat.id,
                    m.chat.title,
                    user.id if user else 0,
                    user.mention if user else "Anonymous",
                ),
            )

        await app.send_message(
            chat_id=app.logger,
            text=m.lang["log_user"].format(
                m.from_user.id,
                f"@{m.from_user.username}",
                m.from_user.mention,
            ),
        )
