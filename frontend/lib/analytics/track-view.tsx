"use client";

import { useEffect } from "react";
import { track, type ClientEvent, type EventProperties } from "@/lib/analytics/track";

/**
 * Fire one event when a screen is rendered.
 *
 * Exists so a *server* component can record that it was viewed without
 * becoming a client component itself. Dropping `"use client"` onto a whole
 * page to add one event would ship its entire tree to the browser, which is
 * a large cost for a measurement.
 *
 * Renders nothing.
 */
export function TrackView({
  event,
  properties = {},
}: {
  event: ClientEvent;
  properties?: EventProperties;
}) {
  const serialised = JSON.stringify(properties);

  useEffect(() => {
    track(event, JSON.parse(serialised) as EventProperties);
    // Keyed on the serialised properties so a new object literal on each
    // render does not re-fire the event.
  }, [event, serialised]);

  return null;
}
