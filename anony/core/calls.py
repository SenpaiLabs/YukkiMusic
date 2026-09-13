# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from ntgcalls import (ConnectionError, ConnectionNotFound,
                      RTMPStreamingUnsupported, TelegramServerError,
                      TransportParseException)
from pyrogram.errors import (ChatSendMediaForbidden, ChatSendPhotosForbidden,
                             MessageIdInvalid)
from pyrogram.types import InputMediaPhoto, Message
from pytgcalls import PyTgCalls, exceptions, types
from pytgcalls.pytgcalls_session import PyTgCallsSession

from anony import (app, config, db, lang, logger,
                   queue, thumb, userbot, yt)
from anony.helpers import Media, buttons


class TgCall:
    def __init__(self):
        self.clients = []

    async def _toggle(self, chat_id: int, pause: bool) -> bool:
        client = await db.get_assistant(chat_id)
        await db.playing(chat_id, paused=pause)
        try:
            method = client.pause if pause else client.resume
            return await method(chat_id)
        except (ConnectionNotFound, exceptions.NotInCallError):
            await self.stop(chat_id)
            return False

    async def pause(self, chat_id: int) -> bool:
        return await self._toggle(chat_id, pause=True)

    async def resume(self, chat_id: int) -> bool:
        return await self._toggle(chat_id, pause=False)

    async def stop(self, chat_id: int) -> None:
        client = await db.get_assistant(chat_id)
        queue.clear(chat_id)
        await db.remove_call(chat_id)
        await db.set_loop(chat_id, 0)

        try:
            await client.leave_call(chat_id, close=False)
        except Exception:
            pass

    async def _send_or_edit_track_ui(
        self,
        chat_id: int,
        message: Message,
        text: str,
        thumb_path: str | None,
        keyboard,
    ) -> int:
        try:
            if thumb_path:
                await message.edit_media(
                    media=InputMediaPhoto(media=thumb_path, caption=text),
                    reply_markup=keyboard,
                )
            else:
                await message.edit_text(text, reply_markup=keyboard)
            return message.id
        except (ChatSendMediaForbidden, ChatSendPhotosForbidden, MessageIdInvalid):
            if thumb_path:
                sent = await app.send_photo(
                    chat_id=chat_id,
                    photo=thumb_path,
                    caption=text,
                    reply_markup=keyboard,
                )
            else:
                sent = await app.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard,
                )
            return sent.id

    async def play_media(
        self,
        chat_id: int,
        message: Message,
        media: Media,
        seek_time: int = 0,
        _lang: dict = None,
    ) -> None:
        client = await db.get_assistant(chat_id)
        if _lang is None:
            _lang = await lang.get_lang(chat_id)

        _thumb = (
            await thumb.generate(media)
            if media.thumbnail
            else config.DEFAULT_THUMB
        ) if config.THUMB_GEN else None

        if not media.file_path:
            await message.edit_text(_lang["error_no_file"].format(config.SUPPORT_CHAT))
            return await self.play_next(chat_id)

        stream = types.MediaStream(
            media_path=media.file_path,
            audio_parameters=types.AudioQuality.HIGH,
            video_parameters=types.VideoQuality.HD_720p,
            audio_flags=types.MediaStream.Flags.REQUIRED,
            video_flags=(
                types.MediaStream.Flags.AUTO_DETECT
                if media.video
                else types.MediaStream.Flags.IGNORE
            ),
            ffmpeg_parameters=f"-ss {seek_time}" if seek_time > 1 else None,
        )
        try:
            await client.play(
                chat_id=chat_id,
                stream=stream,
                config=types.GroupCallConfig(auto_start=False),
            )
            if not seek_time:
                media.time = 1
                await db.add_call(chat_id)
                text = _lang["play_media"].format(
                    media.url,
                    media.title,
                    media.duration,
                    media.user,
                )
                keyboard = buttons.controls(chat_id)
                media.message_id = await self._send_or_edit_track_ui(
                    chat_id=chat_id,
                    message=message,
                    text=text,
                    thumb_path=_thumb,
                    keyboard=keyboard,
                )
        except (FileNotFoundError, exceptions.NoAudioSourceFound) as e:
            if isinstance(e, FileNotFoundError):
                err_text = _lang["error_no_file"].format(config.SUPPORT_CHAT)
            else:
                err_text = _lang["error_no_audio"]
            await message.edit_text(err_text)
            await self.play_next(chat_id)
        except (
            exceptions.NoActiveGroupCall,
            ConnectionError,
            ConnectionNotFound,
            TelegramServerError,
            TransportParseException,
            TimeoutError,
            RTMPStreamingUnsupported,
        ) as e:
            err_map = {
                exceptions.NoActiveGroupCall: "error_no_call",
                RTMPStreamingUnsupported: "error_rtmp",
            }
            err_key = err_map.get(type(e), "error_tg_server")
            await self.stop(chat_id)
            await message.edit_text(_lang[err_key])

    async def replay(self, chat_id: int) -> None:
        if not await db.get_call(chat_id):
            return

        media = queue.get_current(chat_id)
        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_again"])
        media.message_id = msg.id
        await self.play_media(chat_id, msg, media, _lang=_lang)

    async def play_next(self, chat_id: int) -> None:
        if loop := await db.get_loop(chat_id):
            await db.set_loop(chat_id, loop - 1)
            return await self.replay(chat_id)

        media = queue.get_next(chat_id)
        try:
            if media and media.message_id:
                await app.delete_messages(
                    chat_id=chat_id,
                    message_ids=media.message_id,
                    revoke=True,
                )
                media.message_id = 0
        except Exception:
            pass

        if not media:
            return await self.stop(chat_id)

        _lang = await lang.get_lang(chat_id)
        msg = await app.send_message(chat_id=chat_id, text=_lang["play_next"])
        if not media.file_path:
            media.file_path = await yt.download(media.id, video=media.video)
            if not media.file_path:
                await self.play_next(chat_id)
                return await msg.edit_text(
                    _lang["error_no_file"].format(config.SUPPORT_CHAT)
                )

        media.message_id = msg.id
        await self.play_media(chat_id, msg, media, _lang=_lang)

    async def ping(self) -> float:
        pings = [c.ping for c in self.clients]
        return round(sum(pings) / (len(pings) or 1), 2)

    async def decorators(self, client: PyTgCalls) -> None:
        @client.on_update()
        async def update_handler(_, update: types.Update) -> None:
            if isinstance(update, types.StreamEnded):
                if update.stream_type == types.StreamEnded.Type.AUDIO:
                    await self.play_next(update.chat_id)
            elif isinstance(update, types.ChatUpdate):
                if update.status in [
                    types.ChatUpdate.Status.KICKED,
                    types.ChatUpdate.Status.LEFT_GROUP,
                    types.ChatUpdate.Status.CLOSED_VOICE_CHAT,
                ]:
                    await self.stop(update.chat_id)

    async def boot(self) -> None:
        PyTgCallsSession.notice_displayed = True
        for ub in userbot.clients:
            client = PyTgCalls(ub, cache_duration=100)
            await client.start()
            self.clients.append(client)
            await self.decorators(client)
        logger.info("PyTgCalls client(s) started.")
