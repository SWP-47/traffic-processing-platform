-- ==============================================================================
-- Atomic Buffer Pop Lua Script
-- Atomically reads all items from a Redis list and then deletes the key.
-- Prevents race conditions where new packets are pushed while the flusher
-- is reading, ensuring no data is lost or duplicated during the DB insert.
-- ==============================================================================

-- KEYS[1]: The Redis list key (e.g., "udp:buffer:bridge-01")
local buffer_key = KEYS[1]

-- Read all items from the list
local items = redis.call('LRANGE', buffer_key, 0, -1)

-- If the list is not empty, delete the key to clear the buffer
if #items > 0 then
    redis.call('DEL', buffer_key)
end

-- Return the array of items (Redis automatically converts Lua tables to arrays)
return items