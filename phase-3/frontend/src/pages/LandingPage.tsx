import { ArrowRight, Zap, BarChart3, Shield, Users } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { DemoSlideshow } from "../components/DemoSlideshow";
import { InputField } from "../components/FormField";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { ApiError } from "../lib/api";


const features = [
  {
    icon: Zap,
    title: "AI-Powered Screening",
    description: "ML models trained on regulatory compliance and risk patterns for accurate pre-screening.",
  },
  {
    icon: BarChart3,
    title: "Explainable Decisions",
    description: "SHAP analysis shows exactly why each applicant received their risk score.",
  },
  {
    icon: Shield,
    title: "Compliance Ready",
    description: "Built with Basel III, RBI guidelines, and SEBI NBFC regulations in mind.",
  },
  {
    icon: Users,
    title: "DSA Friendly",
    description: "Purpose-built for Direct Selling Agents to make faster, smarter lending decisions.",
  },
];

const stats = [
  { label: "Average Processing Time", value: "2 minutes" },
  { label: "Risk Model Accuracy", value: "87%" },
  { label: "Compliance Coverage", value: "100%" },
];

export function LandingPage(): JSX.Element {
  const [demoOpen, setDemoOpen] = useState(false);
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const { notify } = useToast();
  const { register } = useAuth();
  const navigate = useNavigate();

  async function submitWaitlist(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const email = String(data.get("waitlist_email"));
    const full_name = String(data.get("waitlist_name") || "");
    // Generate a secure random password — user gets immediate access via the
    // token; they can set a real password from Settings later.
    const tempPassword = "LV_" + crypto.randomUUID().replace(/-/g, "").slice(0, 20);

    setLoading(true);
    try {
      await register(full_name || email, email, tempPassword);
      notify("You're in! Redirecting to your dashboard...", "success");
      setWaitlistOpen(false);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        notify("Email already registered. Please log in instead.", "error");
      } else {
        notify(error instanceof Error ? error.message : "Unable to create your account.", "error");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-white via-indigo-50 to-white">
      {/* Navigation */}
      <nav className="sticky top-0 z-40 border-b border-gray-200/50 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-4 py-4 md:px-8">
          <div className="flex items-center justify-between">
            <div className="text-2xl font-black tracking-tight text-brand">LoanVati</div>
            <Button
              onClick={() => setDemoOpen(true)}
              className="hidden gap-2 sm:inline-flex"
              variant="primary"
            >
              <span>Product Tour</span>
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="mx-auto max-w-7xl px-4 py-16 md:px-8 md:py-24">
        <div className="mx-auto max-w-3xl">
          {/* Left Column - Text */}
          <div
            className="flex flex-col justify-center"
            data-scroll-animate
            style={{
              animation: "fadeInUp 0.8s ease-out forwards",
              opacity: 0,
            }}
          >
            <div className="mb-4 inline-flex w-fit items-center gap-2 rounded-full bg-indigo-100 px-4 py-2">
              <Zap className="h-4 w-4 text-brand" />
              <span className="text-sm font-medium text-brand">AI-Powered Lending</span>
            </div>

            <h1 className="mt-2 text-4xl font-black tracking-tight text-gray-950 md:text-5xl lg:text-6xl">
              Pre-screen before you submit
            </h1>

            <p className="mt-6 text-lg leading-relaxed text-gray-600">
              LoanVati combines machine learning with regulatory expertise to help Direct Selling Agents
              make smarter lending decisions. Screen applicants in minutes, not days.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button
                onClick={() => document.getElementById("waitlist")?.scrollIntoView({ behavior: "smooth" })}
                className="w-full sm:w-auto"
              >
                Join the Waitlist
              </Button>
              <Button
                variant="secondary"
                onClick={() => setDemoOpen(true)}
                className="w-full sm:w-auto sm:hidden"
              >
                Product Tour
              </Button>
            </div>

            {/* Stats */}
            <div className="mt-12 grid grid-cols-3 gap-4">
              {stats.map((stat) => (
                <div
                  key={stat.label}
                  data-scroll-animate
                  style={{
                    animation: "fadeInUp 0.8s ease-out forwards",
                    opacity: 0,
                  }}
                >
                  <div className="text-2xl font-bold text-brand md:text-3xl">{stat.value}</div>
                  <div className="mt-1 text-xs text-gray-600 md:text-sm">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="border-t border-gray-200/50 bg-white py-16 md:py-24">
        <div className="mx-auto max-w-7xl px-4 md:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-black tracking-tight text-gray-950 md:text-4xl">
              Built for India's lending ecosystem
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Compliance, speed, and accuracy in one platform
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
            {features.map((feature, idx) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  data-scroll-animate
                  className="rounded-xl border border-gray-200 bg-gradient-to-br from-white to-gray-50 p-6 transition-all duration-300 hover:border-brand hover:shadow-lg"
                  style={{
                    animation: `fadeInUp 0.6s ease-out forwards`,
                    opacity: 0,
                    animationDelay: `${idx * 0.1}s`,
                  }}
                >
                  <Icon className="h-8 w-8 text-brand" />
                  <h3 className="mt-4 text-lg font-semibold text-gray-900">{feature.title}</h3>
                  <p className="mt-2 text-sm text-gray-600">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-16 md:py-24">
        <div className="mx-auto max-w-7xl px-4 md:px-8">
          <h2 className="text-center text-3xl font-black tracking-tight text-gray-950 md:text-4xl">
            How LoanVati works
          </h2>

          <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
            {[
              {
                step: "1",
                title: "Enter Details",
                description: "Input applicant information—income, credit amount, family status.",
              },
              {
                step: "2",
                title: "AI Analysis",
                description: "Our model scores risk in seconds using regulatory + market data.",
              },
              {
                step: "3",
                title: "Smart Decision",
                description: "See the decision, SHAP explanation, and coaching tips in one view.",
              },
            ].map((item, idx) => (
              <div
                key={item.step}
                data-scroll-animate
                className="relative rounded-xl border border-gray-200 bg-white p-8"
                style={{
                  animation: `fadeInUp 0.6s ease-out forwards`,
                  opacity: 0,
                  animationDelay: `${idx * 0.15}s`,
                }}
              >
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-brand text-white font-bold">
                  {item.step}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-gray-900">{item.title}</h3>
                <p className="mt-2 text-sm text-gray-600">{item.description}</p>

                {idx < 2 && (
                  <div className="absolute -right-4 top-1/3 hidden h-8 w-8 md:flex">
                    <ArrowRight className="h-8 w-8 text-gray-300" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>


      {/* Waitlist Section */}
      <section id="waitlist" className="border-t border-gray-200/50 bg-gradient-to-br from-indigo-50 via-white to-indigo-50 py-16 md:py-24">
        <div className="mx-auto max-w-2xl px-4 md:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-black tracking-tight text-gray-950 md:text-4xl">
              Ready to pre-screen smarter?
            </h2>
            <p className="mt-4 text-lg text-gray-600">
              Join 100+ DSAs waiting to transform their lending process
            </p>
          </div>

          <form className="mt-8 space-y-4" onSubmit={submitWaitlist}>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <InputField
                label="Full Name"
                name="waitlist_name"
                placeholder="Your name"
              />
              <InputField
                label="Email Address"
                name="waitlist_email"
                type="email"
                placeholder="your@email.com"
                required
              />
            </div>
            <Button
              type="submit"
              loading={loading}
              className="w-full bg-brand text-white hover:bg-brand-hover"
            >
              Join the Waitlist
            </Button>
            <p className="text-center text-xs text-gray-500">
              We'll send you early access and exclusive DSA onboarding tips.
            </p>
          </form>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200/50 bg-white py-8">
        <div className="mx-auto max-w-7xl px-4 md:px-8">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-black text-brand">LoanVati</div>
              <p className="mt-1 text-xs text-gray-500">Pre-screen before you submit.</p>
            </div>
            <p className="text-xs text-gray-500">© 2026 LoanVati. All rights reserved.</p>
          </div>
        </div>
      </footer>

      <DemoSlideshow
        open={demoOpen}
        onClose={() => setDemoOpen(false)}
        onJoinWaitlist={() => {
          document.getElementById("waitlist")?.scrollIntoView({ behavior: "smooth" });
        }}
      />

      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeInRight {
          from {
            opacity: 0;
            transform: translateX(20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        @keyframes float {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-10px);
          }
        }

        [data-scroll-animate].animate-in {
          animation: fadeInUp 0.8s ease-out forwards !important;
          opacity: 1 !important;
        }
      `}</style>
    </div>
  );
}
