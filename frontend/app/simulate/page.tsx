import { ProductPitchForm } from "@/components/product-pitch-form";

export default function SimulatePage() {
  return (
    <div className="page">
      <section className="hero" style={{ paddingTop: 24, paddingBottom: 36 }}>
        <h1 style={{ fontSize: "clamp(2.8rem, 6vw, 5.2rem)" }}>Configure the first council.</h1>
        <p>
          Start with text input. Product images, screenshots, PDFs, and document extraction are planned as later ingestion layers and will feed the same normalized product knowledge model rather than bypassing it.
        </p>
      </section>
      <ProductPitchForm />
    </div>
  );
}
