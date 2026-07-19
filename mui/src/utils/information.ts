export interface FormattedValue {
  value: string;
  unit: string;
}

export function splitFormatBytesPerSecond(bytes: number): FormattedValue {
  if (bytes < 1024) {
    return { value: bytes.toFixed(0), unit: 'B/s' };
  }
  if (bytes < 1024 ** 2) {
    return { value: (bytes / 1024).toFixed(1), unit: 'KB/s' };
  }
  if (bytes < 1024 ** 3) {
    return { value: (bytes / 1024 ** 2).toFixed(2), unit: 'MB/s' };
  }
  return { value: (bytes / 1024 ** 3).toFixed(2), unit: 'GB/s' };
}

export function formatSplit(
  unit: 'packets' | 'bytes',
  value: number,
): FormattedValue {
  if (unit === 'bytes') {
    return splitFormatBytesPerSecond(value);
  }
  return { value: value.toFixed(0), unit: 'pkt/s' };
}

export function formatBytesPerSecond(bytes: number): string {
  const { value, unit } = splitFormatBytesPerSecond(bytes);
  return `${value} ${unit}`;
}