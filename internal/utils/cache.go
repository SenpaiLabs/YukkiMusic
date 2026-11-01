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

package utils

import (
	"sync"
	"time"
)

const NoExpiry = time.Duration(-1)

type CacheItem[V any] struct {
	Value      V
	Expiration time.Time
}

func (i CacheItem[V]) Expired() bool {
	return !i.Expiration.IsZero() && time.Now().After(i.Expiration)
}

type Cache[K comparable, V any] struct {
	mu         sync.RWMutex
	items      map[K]CacheItem[V]
	defaultTTL time.Duration
}

func NewCache[K comparable, V any](defaultTTL time.Duration) *Cache[K, V] {
	c := &Cache[K, V]{
		items:      make(map[K]CacheItem[V]),
		defaultTTL: defaultTTL,
	}
	if defaultTTL > 0 {
		go func() {
			interval := defaultTTL / 2
			if interval < time.Minute {
				interval = time.Minute
			}
			ticker := time.NewTicker(interval)
			for range ticker.C {
				c.mu.Lock()
				now := time.Now()
				for k, item := range c.items {
					if !item.Expiration.IsZero() && now.After(item.Expiration) {
						delete(c.items, k)
					}
				}
				c.mu.Unlock()
			}
		}()
	}
	return c
}

func (c *Cache[K, V]) Set(key K, value V) {
	var exp time.Time

	if c.defaultTTL > 0 {
		exp = time.Now().Add(c.defaultTTL)
	}

	c.mu.Lock()
	c.items[key] = CacheItem[V]{
		Value:      value,
		Expiration: exp,
	}
	c.mu.Unlock()
}

func (c *Cache[K, V]) Get(key K) (V, bool) {
	c.mu.RLock()
	item, ok := c.items[key]
	c.mu.RUnlock()

	if !ok {
		var zero V
		return zero, false
	}

	if item.Expired() {
		c.mu.Lock()
		delete(c.items, key)
		c.mu.Unlock()

		var zero V
		return zero, false
	}

	return item.Value, true
}

func (c *Cache[K, V]) Delete(key K) {
	c.mu.Lock()
	delete(c.items, key)
	c.mu.Unlock()
}

func (c *Cache[K, V]) LoadAndDelete(key K) (V, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()

	item, ok := c.items[key]
	if !ok {
		var zero V
		return zero, false
	}

	delete(c.items, key)

	if item.Expired() {
		var zero V
		return zero, false
	}

	return item.Value, true
}
