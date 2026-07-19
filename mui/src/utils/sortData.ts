/**
 * Resolves the actual data field name for client-side sorting,
 * accounting for the current display unit (packets vs bytes).
 */
export function resolveSortKey(columnId: string, unit: string): string {
  const mapping: Record<string, string> = {
    rx: unit === 'bytes' ? 'rx_bytes_per_sec' : 'rx_per_sec',
    tx: unit === 'bytes' ? 'tx_bytes_per_sec' : 'tx_per_sec',
    received: unit === 'bytes' ? 'received_bytes_per_sec' : 'received_per_sec',
    pps: unit === 'bytes' ? 'bytes_per_sec' : 'packets_per_sec',
  };
  return mapping[columnId] ?? columnId;
}

export function sortData<T>(
  data: T[],
  sortKey: keyof T | string,
  sortDir: 'asc' | 'desc',
  dateKeys: (keyof T | string)[] = []
): T[] {
  return data.toSorted((a, b) => {
    const valA = a[sortKey as keyof T];
    const valB = b[sortKey as keyof T];

    if (valA == null) return 1;
    if (valB == null) return -1;

    if (dateKeys.includes(sortKey)) {
      const dateA = new Date(valA as string | number | Date).getTime();
      const dateB = new Date(valB as string | number | Date).getTime();
      return sortDir === 'asc' ? dateA - dateB : dateB - dateA;
    }

    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortDir === 'asc' ? valA - valB : valB - valA;
    }

    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortDir === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }

    return 0;
  });
}