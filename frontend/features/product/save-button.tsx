"use client";

import { BookmarkCheck, Bookmark } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { requestJson } from "@/lib/api/client";
import type { ProductDetail } from "@/lib/api/types";

/**
 * Save or unsave an option.
 *
 * Saving is idempotent server-side, so a double click cannot create two
 * saves. On failure the button returns to its previous state rather than
 * pretending the save worked.
 */
export function SaveButton({
  reference,
  initiallySaved,
}: {
  reference: string;
  initiallySaved: boolean;
}) {
  const [saved, setSaved] = useState(initiallySaved);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(false);

  async function toggle() {
    setBusy(true);
    setError(false);
    const next = !saved;

    const result = await requestJson<Pick<ProductDetail, "saved">>(
      `/api/v1/products/${reference}/saved`,
      { method: next ? "PUT" : "DELETE" },
    );
    setBusy(false);

    if (result.status === "error") {
      setError(true);
      return;
    }
    setSaved(result.data.saved);
  }

  return (
    <div className="flex flex-col gap-1">
      <Button variant={saved ? "secondary" : "primary"} onClick={toggle} loading={busy}>
        {saved ? (
          <BookmarkCheck className="size-4" aria-hidden="true" />
        ) : (
          <Bookmark className="size-4" aria-hidden="true" />
        )}
        {saved ? "Saved" : "Save this option"}
      </Button>
      {/* Announced, so a screen reader hears the change too. */}
      <span role="status" className="sr-only">
        {saved ? "Saved" : "Not saved"}
      </span>
      {error ? (
        <p role="alert" className="text-meta text-critical">
          We couldn&apos;t update your saved options. Please try again.
        </p>
      ) : null}
    </div>
  );
}
