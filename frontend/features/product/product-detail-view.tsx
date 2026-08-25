"use client";

import Link from "next/link";
import { InlineAlert } from "@/components/feedback/inline-alert";
import { buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PolicyFact } from "@/features/product/policy-fact";
import { SaveButton } from "@/features/product/save-button";
import { FitBadge, FitDimension } from "@/features/recommendations/fit-dimension";
import { WatchOut } from "@/features/recommendations/watch-out";
import type { ProductDetail } from "@/lib/api/types";

/**
 * One option in full (`docs/01_PRODUCT_SPEC.md` section 2.8,
 * `docs/02_UX_UI_SPEC.md` section 11).
 *
 * Above the fold: insurer and product, three fit highlights, one trade-off,
 * Compare and Save. The trade-off sits beside the strengths, not below them —
 * `docs/02_UX_UI_SPEC.md` rule 4 is that trust requires discussing
 * disadvantages, and burying the watch-out would defeat it.
 *
 * The primary action is "Compare this policy" (section 11). There is no
 * checkout: `docs/01_PRODUCT_SPEC.md` section 2.9 leaves outbound
 * continuation disabled for the early beta, and
 * `docs/12_BETA_CHECKLIST.md` requires no fake checkout.
 */
export function ProductDetailView({
  product,
  runId,
}: {
  product: ProductDetail;
  /** Where "Compare" goes back to, when the reader arrived from results. */
  runId: string | null;
}) {
  return (
    <div className="flex flex-col gap-8">
      {product.sourceType === "SYNTHETIC" ? (
        <InlineAlert tone="attention" title="Demo product">
          {product.provenance.explanation}
        </InlineAlert>
      ) : null}

      <section className="flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <h1 className="text-h2 font-semibold text-primary sm:text-h1">
            {product.insurerName} · {product.productName}
          </h1>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="flex flex-col gap-3">
            <h2 className="text-h3 font-medium text-primary">Why this matches you</h2>
            <ul className="flex flex-col gap-2">
              {product.highlights.map((highlight) => (
                <li key={highlight.factor} className="flex flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-support font-medium text-primary">{highlight.label}</span>
                    <FitBadge fit={highlight.fit} />
                  </div>
                  <p className="text-support text-secondary">{highlight.note}</p>
                </li>
              ))}
            </ul>
          </Card>

          <div className="flex flex-col gap-3">
            <h2 className="text-h3 font-medium text-primary">What to watch out for</h2>
            <WatchOut text={product.watchOut} />
          </div>
        </div>

        {/* Decision action bar. Compare is primary while evaluating. */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          {runId ? (
            <Link
              href={`/app/recommendations/${runId}`}
              className={buttonClassName({ variant: "secondary" })}
            >
              Compare this policy
            </Link>
          ) : null}
          <SaveButton reference={product.reference} initiallySaved={product.saved} />
        </div>

        <p className="text-meta text-secondary">
          This beta doesn&apos;t sell insurance and doesn&apos;t pass your details to anyone. When
          you&apos;re ready, you would continue with the insurer directly.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-h2 font-semibold text-primary">How it fits you overall</h2>
        <Card className="flex flex-col gap-4">
          {product.fits.map((fit) => (
            <FitDimension key={fit.factor} dimension={fit} />
          ))}
        </Card>
      </section>

      {product.sections.map((section) => (
        <section key={section.key} className="flex flex-col gap-3">
          <h2 className="text-h2 font-semibold text-primary">{section.label}</h2>
          <Card>
            {section.facts.map((fact) => (
              <PolicyFact key={fact.key} fact={fact} />
            ))}
          </Card>
        </section>
      ))}

      <section className="flex flex-col gap-3">
        <h2 className="text-h2 font-semibold text-primary">Policy Details</h2>
        <Card className="flex flex-col gap-2">
          <p className="text-support text-secondary">
            Data source: <span className="text-primary">{product.provenance.sourceType}</span>
          </p>
          <p className="text-support text-secondary">
            Catalogue version:{" "}
            <span className="text-primary">{product.provenance.catalogueVersion}</span>
          </p>
          <p className="text-support text-secondary">
            Verified:{" "}
            <span className="text-primary">
              {product.provenance.verifiedAt ?? "Not verified — demo data"}
            </span>
          </p>
        </Card>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-h2 font-semibold text-primary">Source Documents</h2>
        <Card>
          <p className="text-support text-secondary">{product.sourceDocumentsNote}</p>
        </Card>
      </section>

      {runId ? (
        <Link
          href={`/app/recommendations/${runId}`}
          className="inline-flex min-h-touch items-center self-start text-support text-accent underline"
        >
          Back to your matched options
        </Link>
      ) : null}
    </div>
  );
}
