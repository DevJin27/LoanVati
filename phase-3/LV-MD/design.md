# LoanVati v3.0 — Design Spec
**For:** Stitch (UI build)  
**Companion doc:** `prd.md` (Codex backend)  
**Product:** Web app for DSAs to pre-screen loan applicants  
**Primary user:** Direct Selling Agents (DSAs) — field agents who source loan applicants for banks and NBFCs, earning commission only on disbursed loans

---

## 1. Design Principles

**Functional over decorative.** DSAs are high-volume, time-pressured users. Every screen should answer "should I submit this applicant?" as fast as possible.

**Trust through transparency.** The SHAP explanations and regulatory citations are the product's moat. Display them prominently — don't bury them in accordions.

**Mobile-first.** DSAs work in the field. Many will use this on a phone while sitting across from an applicant. Every screen must work at 375px width before being considered for desktop.

**Fintech-professional aesthetic.** Clean, white, high-contrast. Minimal color. The risk traffic-light (green/amber/red) should be the most colorful thing on any given screen.

---

## 2. Color System

```
Background:     #FFFFFF (primary), #F8F9FA (secondary surfaces)
Text primary:   #111827
Text secondary: #6B7280
Border:         #E5E7EB (default), #D1D5DB (emphasis)

Risk — Low:     bg #D1FAE5  text #065F46  border #6EE7B7
Risk — Uncertain: bg #FEF3C7  text #92400E  border #FCD34D
Risk — High:    bg #FEE2E2  text #991B1B  border #FCA5A5

Brand accent:   #4F46E5 (indigo — buttons, links, active states)
Brand hover:    #4338CA
```

No gradients. No shadows except `box-shadow: 0 1px 3px rgba(0,0,0,0.08)` on cards.

---

## 3. Typography

```
Font:           Inter (Google Fonts)
Heading 1:      28px / 500 / tracking -0.02em
Heading 2:      20px / 500
Heading 3:      16px / 500
Body:           15px / 400 / line-height 1.6
Caption:        13px / 400 / color #6B7280
Label:          12px / 500 / uppercase / tracking 0.06em / color #9CA3AF
```

---

## 4. Pages & Routes

```
/                   → redirect to /login
/login              → Login page
/register           → Register page
/dashboard          → Applicant pipeline (home screen)
/screen             → New applicant screening form
/applicants/:id     → Applicant detail + report
/billing            → Plan & usage
/settings           → Profile, password
```

---

## 5. Page Specs

---

### 5.1 Login / Register

**Layout:** Centered card, max-width 400px, vertically centered on page.

**Login card:**
- LoanVati wordmark (top, 24px/500 indigo)
- Tagline below: "Pre-screen before you submit." (13px, gray)
- Divider
- Email input
- Password input
- "Sign in" button (full-width, brand indigo)
- "No account? Register →" link below

**Register card:**
- Same wordmark
- Full name, email, password, confirm password inputs
- "Create account" button
- "Already registered? Sign in →" link

**Validation:** Inline, below each field. Red border on invalid. Show error text in red-600 only after first blur.

---

### 5.2 Dashboard — Applicant Pipeline

This is the DSA's home screen. They see all applicants they've screened.

**Header:**
- Left: "LoanVati" wordmark
- Center: nothing
- Right: Plan badge (e.g. "Free — 7 of 10 reports used") + Avatar/initials menu

**Top action bar (sticky below header):**
- Left: "Applicants" h1
- Right: "+ Screen new applicant" button (indigo, filled)

**Filter row (below action bar):**
- Tabs: All | Submitted | Skipped | Outcome pending
- Right of tabs: Search input (search by name or ID)

**Applicant list:**

Each row is a card with:
```
[Risk badge]  [Applicant name or ID]      [Score: 0.72]
              Income ₹1.2L · Credit ₹5L   [Status chip]
                                          [Date]
```

Risk badge = colored pill: Low / Uncertain / High  
Status chip: "Not submitted" (gray) | "Submitted — pending" (blue) | "Approved" (green) | "Rejected" (red)

Clicking any row → `/applicants/:id`

**Empty state:** Illustration-free. Just:  
"No applicants yet. Screen your first applicant to get started."  
"+ Screen new applicant" button centered below.

**Quota warning banner** (shown when free tier user has ≤ 2 reports left):  
Amber banner across top: "You have 2 free reports remaining this month. Upgrade to Growth for unlimited screening."  
[Upgrade now] button in banner.

---

### 5.3 New Applicant Screening Form — `/screen`

This is the most important screen. DSAs fill this out while sitting with an applicant.

**Header:** "← Back" link | "Screen applicant" title

**Form layout:** Single column, mobile-first. No sidebars.

**Fields (in order):**

Section label: APPLICANT DETAILS (12px label style)
- Full name (text) — for DSA's own reference only, not sent to model
- Annual income (₹) — number input, required
- Credit amount requested (₹) — number input, required
- Loan annuity / EMI (₹) — number input, required
- Employment years — number input with decimal, required

Section label: DEMOGRAPHICS
- Age (years) — number, required
- Family size — number (1–10), required
- Education level — select: Secondary | Higher secondary | Higher education | Academic degree | Lower secondary | Incomplete higher
- Income type — select: Working | Commercial associate | Pensioner | State servant | Unemployed | Student | Businessman | Maternity leave
- Housing type — select: House / apartment | Rented apartment | Municipal apartment | With parents | Co-op apartment | Office apartment
- Occupation type — select: (populated from dataset categories)

**Sticky bottom bar (mobile):**
- "Get risk score" button — full-width, indigo, filled
- Keyboard-safe: `padding-bottom: env(safe-area-inset-bottom)`

**Desktop:** Button is full-width at the bottom of the form column, not sticky.

**Validation:** All required fields validated on submit. Do not validate on every keystroke.

**Loading state after submit:**
Replace button with a progress indicator. Show 3 animated steps sequentially:
1. "Scoring applicant..." (0.5s)
2. "Running SHAP analysis..." (1s)
3. "Generating report..." (2–4s, depends on Groq)

On completion → navigate to `/applicants/:id` for the new record.

---

### 5.4 Applicant Detail — `/applicants/:id`

This is the report screen. The most information-dense page.

**Layout (desktop):** 2-column. Left column: ML score + SHAP. Right column: Full AI report. On mobile: single column, ML score first then report.

---

**Left column — ML Scoring Panel**

**Risk score card:**
```
                  RISK SCORE
                    0.72
         ████████████░░░░░ 72%
         
         ┌─────────────────┐
         │   HIGH RISK     │  ← colored badge
         └─────────────────┘
         
         Confidence: 84%
         Model: CatBoost v1.2
```

The score bar is a simple horizontal progress bar. No circular gauges (hard to read on mobile).

**SHAP explanation card:**

Title: "Why this score?" (16px/500)

Horizontal bar chart. Each bar represents one SHAP feature. Bars extend right (red) for risk-increasing features, left (green) for risk-decreasing. Label on left, value on right.

```
CREDIT_INCOME_RATIO  ████████████  +0.18 ↑ risk
EXT_SOURCE_2         ▓▓▓▓         -0.11 ↓ risk
ANNUITY_INCOME_RATIO ██████       +0.09 ↑ risk
DAYS_EMPLOYED        ▓▓           -0.04 ↓ risk
AMT_CREDIT           ███          +0.07 ↑ risk
```

Show top 5 features only. Truncate feature names to max 22 chars with ellipsis.

**Decision actions card:**

```
What did you decide?

[Submit to lender]  [Skip applicant]
```

If DSA clicks "Submit to lender" when risk is High, show a confirmation modal:
"This applicant scored High risk. Are you sure you want to submit?"
[Submit anyway] [Cancel]

If DSA clicks "Submit anyway" → log as `submitted_override`.

After decision is logged, show:
```
Submitted — pending lender decision

[Log outcome]  ← activates after submission
```

**Outcome logging (appears after submission):**
```
What did the lender decide?

○ Approved
○ Rejected — credit risk
○ Rejected — other reason (product mismatch, geography, etc.)

Lender name (optional): [____________]

[Save outcome]
```

---

**Right column — AI Report Panel**

Title: "AI Lending Report" (16px/500) + timestamp

If report not yet generated (ML-only score was run):
- Show "Generate full report" button (secondary style)
- Explain: "Full report takes ~10 seconds and uses 1 report credit."

If report is generating:
- 4-step progress: Profile → Risk analysis → Regulatory lookup → Report draft
- Each step shows a check mark when complete, spinner on current

**Report sections (rendered in order):**

**1. Borrower profile**
Gray background card. Plain prose. Max 150 words.
Label: APPLICANT PROFILE

**2. Risk analysis**
White card. Prose. Includes risk badge (same color system as score card).
Label: RISK ANALYSIS

**3. Decision**
Large colored card. Decision is one of:
- APPROVE — green card, #065F46 text
- MANUAL REVIEW — amber card, #92400E text  
- REJECT — red card, #991B1B text

Text inside: the decision reasoning (2–3 sentences).

**4. Regulatory context**
White card. Label: REGULATORY NOTES (with source citation in gray: "Sources: RBI FPC, Basel III, CIBIL Framework")
Prose. Max 200 words.

**5. Disclaimer**
Very small (13px), gray. Italic. Standard responsible AI disclaimer.

---

**Fix It coaching panel** (below SHAP chart, left column)

Only shown when `risk_class = 'High'` or `'Uncertain'`.

Title: "How to improve this score" (14px/500)

Each tip rendered as:
```
Reduce loan amount
₹5,00,000 → ₹3,80,000

Score improvement: High → Uncertain  (+9 points)
```

Max 3 tips. If no actionable tips exist, hide panel entirely.

---

### 5.5 Billing — `/billing`

**Current plan card:**
```
Growth Plan
₹799/month · Renews 1 Jun 2026

Reports used this month: unlimited
5 team seats: 2 active
```

**Upgrade / change plan section:**
3 plan cards side by side (or stacked on mobile). Featured card (Growth) has an indigo border.

Each plan card:
- Plan name + price
- Features list (plain text, no icons)
- CTA button: "Current plan" (disabled, gray) or "Upgrade" (indigo)

**Pay-per-report option:**
Below plan cards, gray secondary card:
"Need just one more report?  ₹49 per additional report."
[Buy 1 report] button.

Razorpay checkout opens in a modal (use Razorpay's hosted checkout JS).

---

### 5.6 Settings — `/settings`

Simple single-column form:
- Full name (editable)
- Email (read-only, with "contact support to change" note)
- Change password section (current password, new password, confirm)
- [Save changes] button
- Danger zone section: [Delete account] (red text button, confirmation modal)

---

## 6. Component Library

### Risk Badge
```
props: level ('Low' | 'Uncertain' | 'High')

Low:       bg-green-100  text-green-800  border-green-300
Uncertain: bg-amber-100  text-amber-800  border-amber-300  
High:      bg-red-100    text-red-800    border-red-300

Size: px-3 py-1, text-12px/500, uppercase, rounded-full, border 1px
```

### Score Bar
```
props: score (0–1), riskClass

Bar color:
  score < 0.4:  green (#6EE7B7 fill)
  score < 0.6:  amber (#FCD34D fill)
  score >= 0.6: red (#FCA5A5 fill)

Track: gray (#E5E7EB), h-3, rounded-full
Fill: colored, same height, rounded-full, transition: width 0.6s ease
```

### SHAP Bar Chart
```
Render as SVG or div-based bars (not canvas).
Max 5 bars.
Red bars extend right from center axis: risk-increasing features.
Green bars extend left: risk-decreasing.
Feature name: 13px gray, left-aligned.
SHAP value: 13px, right-aligned, color matches bar.
Bar height: 20px, gap: 8px between rows.
```

### Progress Steps (for report generation)
```
4 steps in a column.
Each step: circle indicator (24px) + label (14px)

States:
  pending:    gray circle with gray text
  active:     indigo circle (pulsing animation) + indigo text
  complete:   green circle with checkmark + gray text

No horizontal lines between steps. Just vertical whitespace.
```

### Form Inputs
```
All inputs:
  height: 44px (mobile touch target)
  border: 1px solid #E5E7EB
  border-radius: 8px
  padding: 0 14px
  font-size: 15px
  focus: border-color #4F46E5, box-shadow 0 0 0 3px rgba(79,70,229,0.12)
  error: border-color #EF4444, error text below in #EF4444, 12px

Select dropdowns: same styling, custom chevron icon

Number inputs: no spinners (appearance: textfield)
```

### Buttons
```
Primary (filled):
  bg: #4F46E5  text: white  hover: #4338CA
  height: 44px  padding: 0 20px  border-radius: 8px
  font: 15px/500
  active: scale(0.98)
  loading: spinner replaces text, disabled

Secondary (outlined):
  bg: white  border: 1px #E5E7EB  text: #374151
  hover: bg #F9FAFB

Destructive:
  bg: white  border: 1px #FCA5A5  text: #991B1B
  hover: bg #FEE2E2

Ghost:
  no border  no bg  text: #4F46E5
  hover: bg #EEF2FF

Disabled state: opacity 0.5, cursor not-allowed (all button types)
```

### Modal
```
Overlay: rgba(0,0,0,0.4) full-screen
Card: max-width 400px, centered, bg white, border-radius 12px, p-6
Close: X button top-right, 24px tap target
Animation: fade-in 150ms + scale 0.96→1.0

Always: title (18px/500), body text (15px), action buttons row at bottom
```

---

## 7. Navigation

**Mobile (≤768px):**
Bottom tab bar (fixed):
- Home (dashboard icon)
- Screen (plus icon)
- Settings (gear icon)

Tab bar height: 56px + safe-area-inset-bottom
Active tab: indigo icon + indigo label. Inactive: gray.

**Desktop (>768px):**
Left sidebar, 220px wide, fixed:
- LoanVati wordmark (top, 20px/500)
- Plan badge below wordmark
- Nav items: Dashboard, Screen applicant, Billing, Settings
- Active item: indigo background, rounded-lg, full-width
- Bottom of sidebar: user initials + name + "Sign out" link

---

## 8. Empty & Error States

**Empty list:** Text only. No illustrations. 2-line message + action button if applicable.

**Loading:** Skeleton screens (gray animated bars) for list views. Spinner (24px, indigo, centered) for single-item loads.

**API error:** Toast notification, bottom of screen, 4s duration.
- Error: red background, white text, "Something went wrong. Try again."
- Success: green background, white text, e.g. "Outcome saved."

Toast width: max 320px. Border-radius: 8px.

**Network offline:** Banner at top: "You're offline. Reconnect to screen applicants." — amber, full-width.

---

## 9. Responsive Breakpoints

```
Mobile:  320px–767px   (single column, bottom nav, sticky CTA bar)
Tablet:  768px–1023px  (single column, sidebar nav appears)
Desktop: 1024px+       (2-column layout on applicant detail)
```

---

## 10. API Integration Notes

All API calls go to the FastAPI backend (see `prd.md` for endpoints). Base URL is configurable via environment variable `VITE_API_BASE_URL`.

**Auth:** Store JWT in `localStorage`. Attach as `Authorization: Bearer <token>` on every request. On 401, clear token and redirect to `/login`.

**Quota:** After each `/predict` or `/report` call, refresh plan status by calling `GET /billing/status`. Update the quota badge in the header.

**Report polling:** After calling `POST /report`, the response may take 8–15 seconds. Show the 4-step progress UI while awaiting the response — this is a single long-running HTTP request, not a polling pattern. Set client timeout to 30s.

---

## 11. What Not to Design

- No data visualisation dashboards or analytics (not MVP)
- No admin panel (admin uses the API directly for now)
- No team management UI (DSAs on Team plan share a quota — no seat management needed for MVP)
- No dark mode (defer)
- No native mobile app (responsive web only for MVP)

---

*LoanVati v3.0 Design Spec — May 2026*
