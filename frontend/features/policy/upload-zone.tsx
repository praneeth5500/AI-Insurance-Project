"use client";

import { FileText, Upload, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { Button } from "@/components/ui/button";
import { track } from "@/lib/analytics/track";
import { apiBaseUrl } from "@/lib/api/client";
import type { UploadedPolicy } from "@/lib/api/types";

/**
 * The upload screen (docs/02_UX_UI_SPEC.md section 13).
 *
 * The spec asks for a large but restrained zone showing the supported file
 * type, the filename, the size, a remove control and an analyze action — and
 * a privacy line, "only if implementation supports it". It does: the file
 * goes to private storage, is never publicly readable, and can be deleted.
 *
 * The file input itself stays a real `<input type="file">` rather than being
 * replaced by a div. Drag and drop is added on top of it, not instead of it,
 * so the control remains keyboard-operable and announces itself correctly.
 */

const ACCEPT = "application/pdf,image/png,image/jpeg";
const MAX_BYTES = 20 * 1024 * 1024;

function readableSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} bytes`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadZone() {
  const router = useRouter();

  // Reaching the upload screen is the top of this funnel; the completion
  // event is recorded server-side where the file is actually accepted.
  useEffect(() => {
    track("policy_upload_started", {});
  }, []);

  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);

  function choose(next: File | undefined) {
    setError(undefined);
    if (!next) return;
    // Checked again on the server from the bytes themselves; this is only so
    // the reader finds out immediately rather than after a long upload.
    if (next.size > MAX_BYTES) {
      setError(
        "That file is larger than we can accept. If it is a scan, try exporting it at a lower resolution.",
      );
      return;
    }
    setFile(next);
  }

  async function analyze() {
    if (!file) return;
    setUploading(true);
    setError(undefined);

    const body = new FormData();
    body.append("file", file);

    try {
      const response = await fetch(`${apiBaseUrl()}/api/v1/policies/uploads`, {
        method: "POST",
        credentials: "include",
        body,
      });
      const payload: unknown = await response.json().catch(() => null);

      if (!response.ok) {
        const envelope = (payload as { error?: { message?: string } } | null)?.error;
        setError(envelope?.message ?? "We couldn't upload that file. Please try again.");
        setUploading(false);
        return;
      }

      const policy = payload as UploadedPolicy;
      router.push(`/app/policies/${policy.id}`);
    } catch {
      setError("We couldn't reach the service. Please check your connection and try again.");
      setUploading(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {error ? (
        <InlineAlert tone="critical" title="We couldn't accept that file">
          {error}
        </InlineAlert>
      ) : null}

      {file === null ? (
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            choose(event.dataTransfer.files[0]);
          }}
          className={[
            "flex flex-col items-center gap-3 rounded-card border border-dashed p-8 text-center",
            dragging ? "border-accent bg-accent-soft" : "border-control-border bg-surface",
          ].join(" ")}
        >
          <Upload className="size-6 text-secondary" aria-hidden="true" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-primary">Choose your policy document</p>
            <p className="text-support text-secondary">
              A PDF, or a clear photo or scan in PNG or JPEG. Up to 20 MB.
            </p>
          </div>

          <label className="inline-flex min-h-touch cursor-pointer items-center rounded-control bg-accent px-6 text-body font-medium text-surface">
            Choose a file
            <input
              ref={inputRef}
              type="file"
              accept={ACCEPT}
              className="sr-only"
              onChange={(event) => choose(event.target.files?.[0])}
            />
          </label>
        </div>
      ) : (
        <div className="flex flex-col gap-4 rounded-card border border-control-border bg-surface p-5">
          <div className="flex items-start gap-3">
            <FileText className="mt-0.5 size-5 shrink-0 text-secondary" aria-hidden="true" />
            <div className="flex min-w-0 flex-col">
              <p className="truncate text-body font-medium text-primary">{file.name}</p>
              <p className="text-support text-secondary">{readableSize(file.size)}</p>
            </div>
            <button
              type="button"
              onClick={() => {
                setFile(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
              disabled={uploading}
              className="ml-auto inline-flex min-h-touch min-w-touch items-center justify-center rounded-control text-secondary hover:text-primary disabled:opacity-50"
            >
              <X className="size-4" aria-hidden="true" />
              <span className="sr-only">Remove {file.name}</span>
            </button>
          </div>

          <Button onClick={analyze} disabled={uploading}>
            {uploading ? "Uploading…" : "Analyze this policy"}
          </Button>
        </div>
      )}

      <p className="text-meta text-secondary">
        Your policy is stored privately and is only used to generate your analysis. You can delete
        it at any time, and we never share it.
      </p>
    </div>
  );
}
