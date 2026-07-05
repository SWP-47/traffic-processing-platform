-- ==============================================================================
-- Atomic Drop Flush Lua Script
-- Atomically reads and resets the dropped_delta counter for a channel.
-- Prevents race conditions between the Reporting Worker and Ingestion Worker.
-- ==============================================================================

-- KEYS[1]: The Redis hash key for channel state (e.g., "channel:state:bridge-01")
local channel_key = KEYS[1]

-- Atomically read the current dropped_delta value
local dropped_delta = redis.call("HGET", channel_key, "dropped_delta")

-- If the field does not exist or is 0, return 0 immediately
if not dropped_delta or dropped_delta == "0" then
    return 0
end

-- Reset the dropped_delta to 0 in the same hash
redis.call("HSET", channel_key, "dropped_delta", 0)

-- Return the read value as a number
return tonumber(dropped_delta)