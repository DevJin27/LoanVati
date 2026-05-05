/**
 * DemoSlideshow
 *
 * A full-screen popup slideshow showing the LoanVati product flow.
 * Uses static screenshots placed in /public/demo/slide-{n}.png
 *
 * Keyboard: ← → to navigate, Escape to close
 * Closes on backdrop click.
 */

import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

// ─── Slide definitions ────────────────────────────────────────────────────────

const SLIDES = [
  {
    src: "/demo/slide-1.png",
    title: "Your applicant dashboard",
    caption:
      "Every screened applicant in one place. Filter by status, search by name, track outcomes end-to-end.",
  },
  {
    src: "/demo/slide-2.png",
    title: "Simple screening form",
    caption:
      "Enter applicant details in under 2 minutes — income, loan amount, employment, demographics. No complex paperwork.",
  },
  {
    src: "/demo/slide-3.png",
    title: "Smart auto-formatting",
    caption:
      "Numbers format automatically as you type — ₹24,00,000 instead of 2400000. Clear and error-free.",
  },
  {
    src: "/demo/slide-4.png",
    title: "AI processes in seconds",
    caption:
      "Credit scoring, SHAP analysis, and a full lending report — all generated automatically while you wait.",
  },
  {
    src: "/demo/slide-5.png",
    title: "Clear, trustworthy decision",
    caption:
      "Risk percentage, plain-language recommendation, and exactly why the decision was made. No black boxes.",
  },
  {
    src: "/demo/slide-6.png",
    title: "Built-in DSA feedback loop",
    caption:
      "Rate every report and leave notes. Your feedback improves accuracy over time — your expertise trains the model.",
  },
] as const;

// ─── Component ─────────────────────────────────────────────────────────────────

interface DemoSlideshowProps {
  open: boolean;
  onClose: () => void;
  onJoinWaitlist: () => void;
}

export function DemoSlideshow({ open, onClose, onJoinWaitlist }: DemoSlideshowProps): JSX.Element | null {
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
      }, 220);
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

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") prev();
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, next, prev, onClose]);

  // Reset to slide 1 when reopened
  useEffect(() => {
    if (open) setIndex(0);
  }, [open]);

  if (!open) return null;

  const slide = SLIDES[index];

  const slideClass = transitioning
    ? animDir === "left"
      ? "opacity-0 translate-x-8"
      : "opacity-0 -translate-x-8"
    : "opacity-100 translate-x-0";

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal
      aria-label="Product demo"
    >
      {/* Modal shell — stop propagation so clicking inside doesn't close */}
      <div
        className="relative flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">
              Product tour
            </span>
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-600">
              {index + 1} / {total}
            </span>
          </div>
          <button
            id="btn-demo-close"
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
            aria-label="Close demo"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Screenshot */}
        <div className="relative bg-gray-50">
          <div
            className={`transition-all duration-200 ease-in-out ${slideClass}`}
          >
            <img
              key={slide.src}
              src={slide.src}
              alt={slide.title}
              className="w-full object-contain"
              style={{ maxHeight: "56vh" }}
              draggable={false}
            />
          </div>

          {/* Prev arrow */}
          {index > 0 && (
            <button
              id="btn-demo-prev"
              type="button"
              onClick={prev}
              className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full border border-gray-200 bg-white p-2 shadow-sm hover:bg-gray-50 disabled:opacity-40"
              aria-label="Previous slide"
            >
              <ArrowLeft className="h-5 w-5 text-gray-700" />
            </button>
          )}

          {/* Next arrow */}
          {!isLast && (
            <button
              id="btn-demo-next"
              type="button"
              onClick={next}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full border border-gray-200 bg-white p-2 shadow-sm hover:bg-gray-50"
              aria-label="Next slide"
            >
              <ArrowRight className="h-5 w-5 text-gray-700" />
            </button>
          )}
        </div>

        {/* Caption */}
        <div className="px-8 pb-6 pt-5">
          <h3 className="text-lg font-semibold text-gray-950">{slide.title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-gray-600">{slide.caption}</p>

          {/* Dot indicators */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex gap-1.5">
              {SLIDES.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  id={`btn-demo-dot-${i + 1}`}
                  onClick={() => goTo(i, i > index ? "left" : "right")}
                  className={`h-1.5 rounded-full transition-all duration-200 ${i === index ? "w-6 bg-brand" : "w-1.5 bg-gray-200 hover:bg-gray-300"
                    }`}
                  aria-label={`Go to slide ${i + 1}`}
                />
              ))}
            </div>

            {/* CTA on last slide, plain next on others */}
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
