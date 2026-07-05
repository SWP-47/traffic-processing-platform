import { useEffect, useRef, useState } from "react";

function useDelayedVisibility(condition: boolean, delay: number): boolean {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (condition) {
      timeoutRef.current = setTimeout(() => {
        setIsVisible(true);
      }, delay);
    } else {
      timeoutRef.current = setTimeout(() => {
        setIsVisible(false);
      }, 0);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [condition, delay]);

  return isVisible;
}

export default useDelayedVisibility;