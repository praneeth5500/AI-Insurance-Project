"use client";

import { useCallback, useRef } from "react";

/**
 * Return focus to whatever was focused before an overlay opened.
 *
 * The dialog primitive restores focus only when its own `Trigger` component
 * opened it. Sheet and Modal are controlled through `open`/`onOpenChange`
 * instead, so without this a keyboard user is dropped back onto `<body>` and
 * loses their place in the flow — which the responsive rules explicitly ask us
 * to preserve (docs/02_UX_UI_SPEC.md section 15).
 *
 * The element is captured during the render in which `open` flips to true:
 * by the time effects run, the overlay has already moved focus into itself.
 */
export function useReturnFocus(open: boolean): (event: Event) => void {
  const previouslyFocused = useRef<HTMLElement | null>(null);
  const wasOpen = useRef(false);

  if (open && !wasOpen.current && typeof document !== "undefined") {
    previouslyFocused.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
  }
  wasOpen.current = open;

  return useCallback((event: Event) => {
    const target = previouslyFocused.current;
    // Skip if the trigger has since been removed from the document.
    if (target && target.isConnected) {
      event.preventDefault();
      target.focus();
    }
  }, []);
}
