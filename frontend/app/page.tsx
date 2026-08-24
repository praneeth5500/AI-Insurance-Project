import { apiBaseUrl, getReadiness } from "@/lib/api/client";

// Phase 0 status page. This is NOT the product home screen — the new-user and
// returning-user home in docs/02_UX_UI_SPEC.md sections 5 and 6 is Phase 3
// work. This page deliberately makes no product or insurance claim; it exists
// so the Phase 0 "frontend runs, backend runs, DB connects" wiring is visible.
export const dynamic = "force-dynamic";

export default async function DeveloperStatusPage() {
  const readiness = await getReadiness();

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", lineHeight: 1.6 }}>
      <h1>AI Insurance Decision Platform</h1>
      <p>Phase 0 — repository foundation. No product features are implemented yet.</p>

      <h2>Backend connection</h2>
      <p>
        API base URL: <code>{apiBaseUrl()}</code>
      </p>

      {readiness.status === "success" ? (
        <p>
          API readiness: <strong>ready</strong> (database:{" "}
          <strong>{readiness.data.dependencies.database}</strong>)
        </p>
      ) : (
        <div role="alert">
          <p>
            API readiness: <strong>unavailable</strong>
          </p>
          <p>{readiness.error.message}</p>
          <p>
            Error code: <code>{readiness.error.code}</code>
            {readiness.error.requestId !== null ? (
              <>
                {" · Request ID: "}
                <code>{readiness.error.requestId}</code>
              </>
            ) : null}
          </p>
        </div>
      )}
    </main>
  );
}
