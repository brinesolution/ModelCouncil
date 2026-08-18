import { LedStatus } from "@/components/industrial/led-status";
import { ProductPitchForm } from "@/components/product-pitch-form";

export default function SimulatePage() {
  return (
    <div className="page">
      <section className="simPageIntro">
        <div>
          <span className="techLabel">Simulation control / product input</span>
          <h1>Configure the consumer council.</h1>
          <p>
            Start with a product pitch and a reproducible population profile. Images, screenshots, PDFs, and document extraction will later feed the same normalized product knowledge layer rather than bypassing the simulation model.
          </p>
        </div>
        <LedStatus label="Engine ready" tone="green" />
      </section>
      <ProductPitchForm />
    </div>
  );
}
