import { useState, useEffect, useMemo, useRef } from "react";

/**
 * Универсальный хук для стабилизации массива данных с помощью TTL-кэша.
 * 
 * @param incomingItems Новые данные, пришедшие с сервера (или null/undefined, если потока нет)
 * @param ttlSeconds Время жизни элемента в секундах без обновлений
 * @param getKey Функция, возвращающая уникальный ключ элемента (например, IP или порт)
 * @param getTimestamp Функция, возвращающая время последнего обновления элемента
 * @param mergeItem Функция слияния старого и нового элемента. По умолчанию делает shallow merge.
 * @returns Стабилизированный массив элементов
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

  useEffect(() => {
    getKeyRef.current = getKey;
    getTimestampRef.current = getTimestamp;
    mergeItemRef.current = mergeItem;
    resetItemRef.current = resetItem;
  });

  useEffect(() => {
    if (!incomingItems) {
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