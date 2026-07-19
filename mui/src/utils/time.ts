/**
 * Translates a number of seconds into a human-readable format.
 *
 * @param seconds - The number of seconds to be processed.
 * @returns A string describing the amount of time (e.g., "1 year 2 days 3 hours").
 */
export function secondsToHumanReadable(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds <= 0) {
        return "0s";
    }

    const intervals = [
        { label: "y", seconds: 31536000 },
        { label: "d", seconds: 86400 },
        { label: "h", seconds: 3600 },
        { label: "m", seconds: 60 },
        { label: "s", seconds: 1 },
    ] as const;

    const parts: string[] = [];
    let remainingSeconds = Math.floor(seconds);

    for (const interval of intervals) {
        const count = Math.floor(remainingSeconds / interval.seconds);

        if (count > 0) {
            parts.push(`${count}${interval.label}`);
            remainingSeconds %= interval.seconds;
        }
    }

    return parts.length > 0 ? parts.join(" ") : "0s";
}