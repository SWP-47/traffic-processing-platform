import { useState, useEffect, useMemo, useRef } from "react";

/**
 * Universal hook for stabilizing array data using a TTL (Time-To-Live) cache.
 * 
 * @param incomingItems New data received from the server (or null/undefined if the stream is disconnected)
 * @param ttlSeconds Time-to-live for an item in seconds without updates
 * @param getKey Function returning a unique key for the item (e.g., IP or port)
 * @param getTimestamp Function returning the timestamp of the item's last update
 * @param mergeItem Function to merge old and new items. Defaults to a shallow merge.
 * @param resetItem Optional function to reset an item's state when it's missing from the new update (e.g., zeroing out metrics)
 * @returns Stabilized array of items
 */
export function useTtlArrayCache<T>(
  incomingItems: readonly T[] | null | undefined,
  ttlSeconds: number,
  getKey: (item: T) => string | number,
  getTimestamp: (item: T) => Date,
  mergeItem: (oldItem: T, newItem: T) => T = (oldItem, newItem) => ({ ...oldItem, ...newItem } as T),
  resetItem?: (oldItem: T) => T
): T[] {
  const [cache, setCache] = useState<Map<string | number, T>>(new Map());

  const getKeyRef = useRef(getKey);
  const getTimestampRef = useRef(getTimestamp);
  const mergeItemRef = useRef(mergeItem);
  const resetItemRef = useRef(resetItem);

  // Update refs after every render to keep callbacks fresh without triggering effect re-runs
  useEffect(() => {
    getKeyRef.current = getKey;
    getTimestampRef.current = getTimestamp;
    mergeItemRef.current = mergeItem;
    resetItemRef.current = resetItem;
  });

  useEffect(() => {
    if (!incomingItems) {
      // This is a valid state reset pattern. We only clear the cache when the incoming 
      // data stream is explicitly disconnected (null). The condition guarantees no infinite loop
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCache(new Map());
      return;
    }

    setCache((prevCache) => {
      const newCache = new Map<string | number, T>();
      const incomingKeys = new Set<string | number>();

      for (const newItem of incomingItems) {
        const key = getKeyRef.current(newItem);
        incomingKeys.add(key);
        
        const oldItem = prevCache.get(key);
        newCache.set(key, oldItem ? mergeItemRef.current(oldItem, newItem) : newItem);
      }

      for (const [key, oldItem] of prevCache.entries()) {
        if (!incomingKeys.has(key)) {
          if (resetItemRef.current) {
            newCache.set(key, resetItemRef.current(oldItem));
          } else {
            newCache.set(key, oldItem);
          }
        }
      }

      return newCache;
    });
  }, [incomingItems]);

  // Periodic cleanup of expired items based on TTL
  useEffect(() => {
    const intervalId = setInterval(() => {
      setCache((prevCache) => {
        const now = Date.now();
        const ttlMs = ttlSeconds * 1000;
        const newCache = new Map<string | number, T>();

        for (const [key, item] of prevCache.entries()) {
          const timestamp = getTimestampRef.current(item);
          const itemTimeMs: number = timestamp.getTime();

          if (now - itemTimeMs <= ttlMs) {
            newCache.set(key, item);
          }
        }

        return newCache;
        });
    }, 1000);

    return () => clearInterval(intervalId);
  }, [ttlSeconds]);

  return useMemo(() => Array.from(cache.values()), [cache]);
}