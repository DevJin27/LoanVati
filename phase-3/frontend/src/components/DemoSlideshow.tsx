/**
 * DemoSlideshow — Story Edition
 *
 * Changes from v1:
 * ─ Black-bar fix: 67px OS chrome cropped via margin-top offset (2.22% of width)
 * ─ Journey breadcrumb: labelled progress strip lets viewers orient themselves
 * ─ Richer narrative: chapter number, story body, insight callout per slide
 * ─ Browser frame: wraps each screenshot so it feels "in-product" not raw
 * ─ Smoother transition: scale + fade in addition to translate
 *
 * Keyboard: ← → to navigate · Escape to close · Backdrop click to close
 */

import { ArrowLeft, ArrowRight, Lightbulb, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

// ─── Slide definitions ────────────────────────────────────────────────────────

const SLIDES = [
  {
    src: "/demo/slide-1.png",
    chapter: "01",
    title: "Your command centre",
    subtitle: "Applicant dashboard",
    narrative:
      "Before LoanVati, DSAs juggled spreadsheets, WhatsApp screenshots, and handwritten notes. Now every applicant lives in one searchable dashboard — filtered by status, tracked from first screen to final outcome.",
    insight:
      "DSAs typically manage 50–200 active applications at once. A single missed follow-up can cost weeks and a lost deal.",
  },
  {
    src: "/demo/slide-2.png",
    chapter: "02",
    title: "Two minutes to screen",
    subtitle: "Screening form",
    narrative:
      "The form captures exactly what the credit model needs — no more, no less. Income, loan details, employment, and demographics in a single clean page. No confusing fields, no paperwork, no wasted time.",
    insight:
      "Traditional pre-screening takes 20–40 minutes of back-and-forth calls. LoanVati gets it done in under 2.",
  },
  {
    src: "/demo/slide-3.png",
    chapter: "03",
    title: "No typos, no confusion",
    subtitle: "Smart auto-formatting",
    narrative:
      "₹2400000 becomes ₹24,00,000 as you type. Indian number formatting is built in. The model gets clean data, the DSA sees familiar numbers, and data-entry errors disappear before they cause bad decisions.",
    insight:
      "Input formatting errors are the #1 source of incorrect credit scores. Formatting-as-you-type eliminates the most common mistakes at zero extra cost.",
  },
  {
    src: "/demo/slide-4.png",
    chapter: "04",
    title: "AI does the heavy lifting",
    subtitle: "Processing in seconds",
    narrative:
      "The moment you submit, three things happen automatically: the applicant is scored, SHAP values explain every factor, and a full lending report is generated. What used to take hours now takes seconds.",
    insight:
      "Credit scoring + explainability + report writing — all done while the DSA watches the progress screen. No waiting, no manual calculation.",
  },
  {
    src: "/demo/slide-5.png",
    chapter: "05",
    title: "A decision you can stand behind",
    subtitle: "Trustworthy recommendation",
    narrative:
      "5% risk. APPROVE. High confidence. And crucially — exactly why. Debt-to-income ratio, payment-to-income ratio, employment history. No black box, no guessing. Just clear, defensible reasoning the DSA can explain to any lender.",
    insight:
      "Regulators and lenders increasingly require explainable AI decisions. LoanVati produces audit-ready reports by default — no extra work required.",
  },
  {
    src: "/demo/slide-6.png",
    chapter: "06",
    title: "Your expertise trains the model",
    subtitle: "DSA feedback loop",
    narrative:
      "Every DSA has years of intuition that no model can fully capture — yet. Rate each report, leave a note, push back when the score feels off. Over time, your ground-truth expertise becomes part of the model itself.",
    insight:
      "The best credit models are built on domain expertise. LoanVati is the only tool that systematically turns DSA knowledge into model improvements.",
  },
] as const;

// ─── Component ────────────────────────────────────────────────────────────────

interface DemoSlideshowProps {
  open: boolean;
  onClose: () => void;
  onJoinWaitlist: () => void;
}

export function DemoSlideshow({
  open,
  onClose,
  onJoinWaitlist,
}: DemoSlideshowProps): JSX.Element | null {
  const [index, setIndex] = useState(0);
  const [animDir, setAnimDir] = useState<"left" | "right" | null>(null);
  const [transitioning, setTransitioning] = useState(false);

  const total = SLIDES.length;
  const isLast = index === total - 1;

  const goTo = useCallback(
    (next: number, dir: "left" | "right") => {
      if (transitioning) return;
      setAnimDir(dir);
      setTransitioning(true);
      setTimeout(() => {
        setIndex(next);
        setAnimDir(null);
        setTransitioning(false);
      }, 240);
    },
    [transitioning],
  );

  const prev = useCallback(() => {
    if (index === 0) return;
    goTo(index - 1, "right");
  }, [index, goTo]);

  const next = useCallback(() => {
    if (index === total - 1) return;
    goTo(index + 1, "left");
  }, [index, total, goTo]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, next, prev, onClose]);

  useEffect(() => {
    if (open) setIndex(0);
  }, [open]);

  if (!open) return null;

  const slide = SLIDES[index];

  const slideClass = transitioning
    ? animDir === "left"
      ? "opacity-0 translate-x-8 scale-[0.98]"
      : "opacity-0 -translate-x-8 scale-[0.98]"
    : "opacity-100 translate-x-0 scale-100";

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal
      aria-label="Product demo"
    >
      {/* Modal shell */}
      <div
        className="relative flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >

        {/* ── Header ───────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xs font-bold uppercase tracking-widest text-brand">
              LoanVati
            </span>
            <span className="text-gray-200">·</span>
            <span className="text-xs font-medium text-gray-400">Product story</span>
          </div>
          <button
            id="btn-demo-close"
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
            aria-label="Close demo"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── Journey strip ────────────────────────────────────────────────── */}
        <div className="flex items-stretch gap-px border-b border-gray-100 bg-gray-100">
          {SLIDES.map((s, i) => (
            <button
              key={i}
              id={`btn-demo-step-${i + 1}`}
              type="button"
              onClick={() => goTo(i, i > index ? "left" : "right")}
              className={`group flex flex-1 flex-col items-center gap-1 px-1 py-2.5 transition-colors duration-150 ${i === index ? "bg-white" : "bg-gray-50 hover:bg-white"
                }`}
            >
              <span
                className={`text-[9px] font-bold tracking-widest uppercase transition-colors duration-150 ${i === index ? "text-brand" : "text-gray-400 group-hover:text-gray-600"
                  }`}
              >
                {s.chapter}
              </span>
              <span
                className={`text-[10px] font-medium leading-tight text-center transition-colors duration-150 ${i === index ? "text-gray-800" : "text-gray-400 group-hover:text-gray-600"
                  }`}
              >
                {s.subtitle}
              </span>
              <div
                className={`h-0.5 w-6 rounded-full transition-all duration-300 ${i <= index ? "bg-brand" : "bg-gray-200"
                  }`}
              />
            </button>
          ))}
        </div>

        {/* ── Screenshot ───────────────────────────────────────────────────── */}
        <div className="relative bg-gray-50 px-5 pt-4 pb-0">
          <div className={`transition-all duration-300 ease-in-out ${slideClass}`}>

            {/* Browser chrome */}
            <div className="overflow-hidden rounded-t-lg border border-b-0 border-gray-200 bg-[#f0f0f0]">
              <div className="flex items-center gap-1.5 px-3 py-2">
                <div className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
                <div className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
                <div className="ml-3 flex-1 rounded bg-white/80 px-3 py-0.5 text-[10px] text-gray-400">
                  loanvati.vercel.app
                </div>
              </div>
            </div>

            {/*
              Screenshot container.
              Black bar fix: the OS chrome bar is 67px on a 1964px-tall image
              → 67/3024 ≈ 2.22% of image width. CSS margin-top percentages are
              relative to containing block WIDTH, so `-2.22%` shifts the image
              up by exactly the bar height at any rendered size.
              `overflow-hidden` on this wrapper clips the offset top.
            */}
            <div
              className="overflow-hidden rounded-b-lg border border-gray-200"
              style={{ maxHeight: "42vh" }}
            >
              <img
                key={slide.src}
                src={slide.src}
                alt={slide.title}
                style={{ display: "block", width: "100%", marginTop: "-2.22%" }}
                draggable={false}
              />
            </div>
          </div>

          {/* Prev arrow */}
          {index > 0 && (
            <button
              id="btn-demo-prev"
              type="button"
              onClick={prev}
              className="absolute left-8 top-1/2 -translate-y-1/2 rounded-full border border-gray-200 bg-white/90 p-2 shadow-sm backdrop-blur-sm hover:bg-white"
              aria-label="Previous slide"
            >
              <ArrowLeft className="h-4 w-4 text-gray-700" />
            </button>
          )}

          {/* Next arrow */}
          {!isLast && (
            <button
              id="btn-demo-next"
              type="button"
              onClick={next}
              className="absolute right-8 top-1/2 -translate-y-1/2 rounded-full border border-gray-200 bg-white/90 p-2 shadow-sm backdrop-blur-sm hover:bg-white"
              aria-label="Next slide"
            >
              <ArrowRight className="h-4 w-4 text-gray-700" />
            </button>
          )}
        </div>

        {/* ── Story panel ──────────────────────────────────────────────────── */}
        <div className="px-7 pb-6 pt-5">

          {/* Chapter header */}
          <div className="mb-1 flex items-center gap-2.5">
            <span className="font-mono text-[11px] font-bold tracking-wider text-brand">
              {slide.chapter}
            </span>
            <div className="h-px flex-1 bg-gray-100" />
          </div>

          {/* Title + subtitle */}
          <h3 className="text-lg font-bold leading-tight text-gray-950">{slide.title}</h3>
          <p className="mt-0.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
            {slide.subtitle}
          </p>

          {/* Narrative */}
          <p className="mt-2.5 text-sm leading-relaxed text-gray-600">{slide.narrative}</p>

          {/* Insight callout */}
          <div className="mt-3 flex items-start gap-2.5 rounded-lg border border-brand/10 bg-brand/5 px-4 py-3">
            <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand/70" />
            <p className="text-[12px] leading-relaxed text-brand/75">{slide.insight}</p>
          </div>

          {/* Nav row */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex gap-1.5">
              {SLIDES.map((_, i) => (
                <button
                  key={i}
                  id={`btn-demo-dot-${i + 1}`}
                  type="button"
                  onClick={() => goTo(i, i > index ? "left" : "right")}
                  className={`h-1.5 rounded-full transition-all duration-200 ${i === index
                      ? "w-6 bg-brand"
                      : "w-1.5 bg-gray-200 hover:bg-gray-300"
                    }`}
                  aria-label={`Go to slide ${i + 1}`}
                />
              ))}
            </div>

            {isLast ? (
              <button
                id="btn-demo-join-waitlist"
                type="button"
                onClick={() => {
                  onClose();
                  onJoinWaitlist();
                }}
                className="rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-white hover:bg-brand-hover"
              >
                Join the waitlist →
              </button>
            ) : (
              <button
                id="btn-demo-next-caption"
                type="button"
                onClick={next}
                className="flex items-center gap-1.5 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Next <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}