import { Car, FileText, HeartPulse } from "lucide-react";
import { ProductCard } from "@/features/home/product-card";
import type { FeatureAvailability } from "@/lib/api/types";

/**
 * The new-user home (docs/02_UX_UI_SPEC.md section 5).
 *
 * Hero and card copy are taken from the specification verbatim. Nothing here
 * claims a capability the product does not have: each card's action appears
 * only once its flow works end to end.
 */
export function NewUserHome({ features }: { features: FeatureAvailability }) {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-3">
        <h1 className="text-hero-mobile font-semibold text-primary sm:text-hero">
          Insurance should make sense before you need it.
        </h1>
        <p className="max-w-prose text-body-lg text-secondary">
          Tell us what matters to you and understand which options fit — or upload the cover you
          already have and see what it really means.
        </p>
      </header>

      <section className="flex flex-col gap-4">
        <h2 className="sr-only">Find insurance</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <ProductCard
            icon={HeartPulse}
            title="Health Insurance"
            description="Find health insurance based on what matters to you."
            actionLabel="Start with health"
            href="/app/recommend/health"
            availability={features.healthRecommendation}
            comingSoonNote="The guided health questions are being built."
          />
          <ProductCard
            icon={Car}
            title="Motor Insurance"
            description="Find cover based on your vehicle, use, and priorities."
            actionLabel="Start with motor"
            href="/app/recommend/motor"
            availability={features.motorRecommendation}
            comingSoonNote="Motor follows once health cover is working well."
          />
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="sr-only">Understand a policy you already have</h2>
        <ProductCard
          icon={FileText}
          title="Already have insurance?"
          description="Understand your existing policy."
          actionLabel="Upload a policy"
          href="/app/policies/upload"
          availability={features.policyDecoder}
          comingSoonNote="Reading uploaded policy documents is being built."
        />
      </section>
    </div>
  );
}
