/*
 * ● YukkiMusic
 * ○ A high-performance engine for streaming music in Telegram voicechats.
 *
 * Copyright (C) 2026 TheTeamVivek
 *
 * This program is free software: you can redistribute it and/or modify it under the
 * terms of the GNU General Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT ANY
 * WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
 * PARTICULAR PURPOSE. See the GNU General Public License for more details.
 *
 * Repository: https://github.com/TheTeamVivek/YukkiMusic
 */

package core

import (
	"os"
	"path/filepath"

	"github.com/Laky-64/gologging"

	state "main/internal/core/models"
)

// check if a track is used in any room (other than the given room)
func isTrackUsed(trackID string, skipRoomID int64) bool {
	for _, room := range rooms {
		if room == nil || room.ID == skipRoomID {
			continue
		}

		room.mu.RLock()
		track := room.track
		inQueue := isTrackInQueue(trackID, room.queue)
		room.mu.RUnlock()

		if track != nil && track.ID == trackID {
			return true
		}

		if inQueue {
			return true
		}
	}
	return false
}

// checks first N (2) queued tracks
func isTrackInQueue(trackID string, queue []*state.Track) bool {
	limit := 2
	if len(queue) < limit {
		limit = len(queue)
	}

	for _, q := range queue[:limit] {
		if q != nil && q.ID == trackID {
			return true
		}
	}
	return false
}

// releaseTrackFile removes a track's file if unused in other rooms
func releaseTrackFile(track *state.Track, skipRoomID int64) {
	if track == nil {
		return
	}

	roomsMu.RLock()
	used := isTrackUsed(track.ID, skipRoomID)
	roomsMu.RUnlock()

	if used {
		gologging.DebugF(
			"file still in use, skipped remove: %s:%s",
			string(track.Source),
			track.ID,
		)
		return
	}

	findAndRemove(track)
}

// release current track file if unused elsewhere
func (r *RoomState) releaseFile() {
	if r == nil {
		return
	}

	r.mu.RLock()
	track := r.track
	r.mu.RUnlock()

	releaseTrackFile(track, r.ID)
}

// cleanup current + queued track files if unused
func (r *RoomState) cleanupFile() {
	if r == nil {
		return
	}

	// collect current + next tracks (max 2)
	tracks := []*state.Track{}
	if r.track != nil {
		tracks = append(tracks, r.track)
	}
	tracks = append(tracks, r.queue...)
	if len(tracks) > 2 {
		tracks = tracks[:2]
	}

	for _, t := range tracks {
		if t == nil || t.ID == "" {
			continue
		}

		roomsMu.RLock()
		used := isTrackUsed(t.ID, r.ID)
		roomsMu.RUnlock()

		if used {
			gologging.DebugF(
				"track still in use, skip delete: %s:%s",
				string(t.Source),
				t.ID,
			)
			continue
		}

		findAndRemove(t)
	}
}

func findAndRemove(track *state.Track) {
	t := "audio"
	if track.Video {
		t = "video"
	}

	files, err := filepath.Glob(filepath.Join("downloads", t+"_"+track.ID+"*"))
	if err != nil {
		return
	}

	for _, f := range files {
		os.Remove(f)
		gologging.DebugF(
			"removed unused file: %s",
			f,
		)
	}
}
