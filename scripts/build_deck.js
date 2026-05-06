/**
 * build_deck.js — generate docs/people10_poc.pptx from the outline at
 * docs/03_presentation_deck_outline.md.
 *
 * Run: NODE_PATH="$(npm root -g)" node scripts/build_deck.js
 */
const pptxgen = require("pptxgenjs");

// ============================================================================
// Theme
// ============================================================================
const NAVY        = "0F2A52";  // dark navy for body titles
const AZURE       = "0078D4";  // Microsoft Azure accent blue
const AZURE_DARK  = "005A9E";
const INK         = "1F2937";  // body text
const MUTED       = "6B7280";  // captions / footers
const BG_LIGHT    = "F8FAFC";  // subtle off-white for callouts
const BG_PANEL    = "EFF6FC";  // very light azure tint for cards
const RULE        = "E5E7EB";

const FONT_HEAD = "Calibri";
const FONT_BODY = "Calibri";

const FOOTER = "People10 Solutions Lab — Malappa";

// ============================================================================
// Setup
// ============================================================================
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";  // 10" x 5.625"
pres.author = "Malappa";
pres.title = "Cloud-Native Data Platform on Azure";

const W = 10, H = 5.625;

// ----------------------------------------------------------------------------
// Reusable footer + page-number stamp on content slides.
// ----------------------------------------------------------------------------
function addFooter(slide, slideNumber) {
  // bottom-left footer
  slide.addText(FOOTER, {
    x: 0.4, y: H - 0.35, w: 6, h: 0.25,
    fontFace: FONT_BODY, fontSize: 9, color: MUTED, margin: 0,
  });
  // bottom-right slide number
  slide.addText(`${slideNumber} / 9`, {
    x: W - 1.1, y: H - 0.35, w: 0.7, h: 0.25,
    fontFace: FONT_BODY, fontSize: 9, color: MUTED, align: "right", margin: 0,
  });
}

// Adds the standard slide title (top-left) + a thin azure rule below it.
// Avoids "decorative line under title" anti-pattern by keeping the rule
// short (under the title text width) and styled subtly.
function addTitle(slide, text) {
  slide.addText(text, {
    x: 0.5, y: 0.35, w: 9, h: 0.65,
    fontFace: FONT_HEAD, fontSize: 28, bold: true, color: NAVY, margin: 0,
  });
}

// ============================================================================
// Slide 1 — Title (full-bleed azure background)
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  // azure accent block in top-right
  s.addShape(pres.shapes.RECTANGLE, {
    x: W - 1.6, y: 0, w: 1.6, h: H,
    fill: { color: AZURE }, line: { type: "none" },
  });

  // big title
  s.addText("Cloud-Native Data Platform on Azure", {
    x: 0.6, y: 1.6, w: 7.6, h: 1.4,
    fontFace: FONT_HEAD, fontSize: 40, bold: true, color: "FFFFFF", margin: 0,
  });

  // subtitle
  s.addText("People10 Solutions Lab — 3-day take-home", {
    x: 0.6, y: 3.05, w: 7.6, h: 0.5,
    fontFace: FONT_BODY, fontSize: 18, color: "CFE3F8", margin: 0,
  });

  // author
  s.addText("Malappa", {
    x: 0.6, y: 4.55, w: 7.6, h: 0.4,
    fontFace: FONT_BODY, fontSize: 14, italic: true, color: "FFFFFF", margin: 0,
  });

  // tech-stack chips along the bottom
  const chips = ["ADLS Gen2", "Databricks", "Delta Lake", "Synapse"];
  const chipW = 1.2, chipGap = 0.12, chipY = 5.0;
  let chipX = 0.6;
  chips.forEach((c) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: chipX, y: chipY, w: chipW, h: 0.36,
      fill: { color: "FFFFFF", transparency: 80 }, line: { color: "FFFFFF", width: 0.75 },
      rectRadius: 0.06,
    });
    s.addText(c, {
      x: chipX, y: chipY, w: chipW, h: 0.36,
      fontFace: FONT_BODY, fontSize: 10, color: "FFFFFF", align: "center", valign: "middle", margin: 0,
    });
    chipX += chipW + chipGap;
  });

  s.addNotes(
    "Be upfront — this is a take-home in 3 days, the manufacturing context is something I picked for realism, not a real engagement."
  );
}

// ============================================================================
// Slide 2 — The problem the brief asks us to solve
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  addTitle(s, "The problem the brief asks us to solve");

  // Five rows: numbered azure circle + bold key + subtitle
  const items = [
    { n: "1", h: "Unify streaming + batch",      sub: "One platform for both, not two pipelines." },
    { n: "2", h: "Enable real-time insights",    sub: "Sub-minute freshness for the business." },
    { n: "3", h: "Support analytics",            sub: "BI dashboards and ad-hoc SQL." },
    { n: "4", h: "Prepare data for AI/ML",       sub: "Offline + online feature stores." },
    { n: "5", h: "Replace legacy ETL + silos",   sub: "Unblock scalability, agility, cost." },
  ];

  const startY = 1.2;
  const rowH = 0.7;
  items.forEach((it, i) => {
    const y = startY + i * rowH;
    // Azure-tinted circle with the number
    s.addShape(pres.shapes.OVAL, {
      x: 0.6, y: y + 0.05, w: 0.5, h: 0.5,
      fill: { color: AZURE }, line: { type: "none" },
    });
    s.addText(it.n, {
      x: 0.6, y: y + 0.05, w: 0.5, h: 0.5,
      fontFace: FONT_HEAD, fontSize: 18, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", margin: 0,
    });
    // Key text
    s.addText(it.h, {
      x: 1.3, y: y + 0.02, w: 7.5, h: 0.32,
      fontFace: FONT_HEAD, fontSize: 18, bold: true, color: NAVY, margin: 0,
    });
    // Subtitle
    s.addText(it.sub, {
      x: 1.3, y: y + 0.34, w: 7.8, h: 0.3,
      fontFace: FONT_BODY, fontSize: 13, color: MUTED, margin: 0,
    });
  });

  addFooter(s, 2);
  s.addNotes(
    "This is the problem statement straight from the brief. Spend a moment on each — they're the five things every other slide answers."
  );
}

// ============================================================================
// Slide 3 — Architecture (three numbered talking points across the slide)
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  addTitle(s, "Architecture — what to point at on the diagram");

  s.addText(
    "Open docs/01_architecture_diagram.md live. Three things, in this order:",
    {
      x: 0.5, y: 1.05, w: 9, h: 0.35,
      fontFace: FONT_BODY, fontSize: 13, italic: true, color: MUTED, margin: 0,
    }
  );

  const cards = [
    {
      n: "1",
      h: "Both arrows → same Bronze",
      body: "Streaming and batch terminate at the same Bronze table. The unification claim made literal in the storage layer.",
    },
    {
      n: "2",
      h: "Medallion on Delta Lake",
      body: "Bronze → Silver → Gold under Databricks + Delta Lake. ACID concurrent writes, time travel, schema evolution.",
    },
    {
      n: "3",
      h: "Three consumption boxes",
      body: "Real-time · Analytics · AI/ML. One per ask in the brief.",
    },
  ];

  const cardY = 1.55, cardH = 3.4, cardW = 2.95, gap = 0.2;
  let cardX = 0.5;
  cards.forEach((c) => {
    // Card background
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cardX, y: cardY, w: cardW, h: cardH,
      fill: { color: BG_PANEL }, line: { color: AZURE, width: 0.75 },
      rectRadius: 0.08,
    });
    // Number badge
    s.addShape(pres.shapes.OVAL, {
      x: cardX + 0.25, y: cardY + 0.25, w: 0.55, h: 0.55,
      fill: { color: AZURE }, line: { type: "none" },
    });
    s.addText(c.n, {
      x: cardX + 0.25, y: cardY + 0.25, w: 0.55, h: 0.55,
      fontFace: FONT_HEAD, fontSize: 20, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", margin: 0,
    });
    // Header
    s.addText(c.h, {
      x: cardX + 0.25, y: cardY + 0.95, w: cardW - 0.5, h: 0.7,
      fontFace: FONT_HEAD, fontSize: 16, bold: true, color: NAVY, margin: 0,
    });
    // Body
    s.addText(c.body, {
      x: cardX + 0.25, y: cardY + 1.7, w: cardW - 0.5, h: cardH - 1.85,
      fontFace: FONT_BODY, fontSize: 12, color: INK, margin: 0,
    });

    cardX += cardW + gap;
  });

  addFooter(s, 3);
  s.addNotes(
    "I'd open the architecture diagram (docs/01_architecture_diagram.md) live during this slide. Stay on these three points; do not get pulled into a Delta-vs-Iceberg debate yet."
  );
}

// ============================================================================
// Slide 4 — Why Delta Lake makes the medallion work (two-column)
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  addTitle(s, "Why Delta Lake makes the medallion work");

  // Left column — bullet list (4 items)
  const bullets = [
    { text: "Concurrent streaming + batch writes on the same table (ACID)", options: { bullet: { code: "25CF" }, breakLine: true } },
    { text: "Time travel for replay and audit",                              options: { bullet: { code: "25CF" }, breakLine: true } },
    { text: "MERGE and apply_changes for idempotent SCD2",                   options: { bullet: { code: "25CF" }, breakLine: true } },
    { text: "Open format — Synapse Serverless reads Delta natively",         options: { bullet: { code: "25CF" } } },
  ];
  s.addText(bullets, {
    x: 0.5, y: 1.4, w: 5.6, h: 3.0,
    fontFace: FONT_BODY, fontSize: 16, color: INK, paraSpaceAfter: 8,
  });

  // Right column — callout panel: Delta vs Iceberg quick answer
  const calX = 6.4, calY = 1.4, calW = 3.1, calH = 3.4;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: calX, y: calY, w: calW, h: calH,
    fill: { color: BG_PANEL }, line: { color: AZURE, width: 0.75 },
    rectRadius: 0.1,
  });
  s.addText("If asked: Delta vs Iceberg?", {
    x: calX + 0.25, y: calY + 0.25, w: calW - 0.5, h: 0.45,
    fontFace: FONT_HEAD, fontSize: 14, bold: true, color: AZURE_DARK, margin: 0,
  });
  s.addText(
    [
      { text: "Native Databricks + Unity Catalog. Synapse Serverless reads Delta directly — no metastore shim.", options: { breakLine: true } },
      { text: "" , options: { breakLine: true } },
      { text: "At 10× scale on a Trino-led stack I'd reconsider.", options: { italic: true } },
    ],
    {
      x: calX + 0.25, y: calY + 0.8, w: calW - 0.5, h: calH - 1.0,
      fontFace: FONT_BODY, fontSize: 12, color: INK, margin: 0,
    }
  );

  addFooter(s, 4);
  s.addNotes(
    "If asked Delta vs Iceberg: native Databricks + Unity Catalog + Synapse Serverless reads it directly. At 10× scale on a Trino-led stack I'd reconsider."
  );
}

// ============================================================================
// Slide 5 — The PoC: one DLT pipeline, both arrows
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  addTitle(s, "The PoC — one DLT pipeline, both arrows");

  // Code-style file pointer
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.05, w: 9, h: 0.42,
    fill: { color: NAVY }, line: { type: "none" }, rectRadius: 0.05,
  });
  s.addText("📄  poc/databricks/pipelines/unified_medallion_dlt.py", {
    x: 0.7, y: 1.05, w: 8.6, h: 0.42,
    fontFace: "Consolas", fontSize: 13, color: "E2E8F0",
    valign: "middle", margin: 0,
  });

  // Five bullets as the walkthrough
  const items = [
    { k: "bronze_cnc_telemetry",        v: "streaming Kafka source, @dlt.table" },
    { k: "bronze_sap_production_order", v: "batch Auto Loader source, same @dlt.table decorator" },
    { k: "Three expectation tiers",     v: "expect_or_fail / expect_or_drop / expect" },
    { k: "SCD2",                        v: "via apply_changes" },
    { k: "Gold materialised view",      v: "joins streaming-derived rollups with batch-derived dimensions" },
  ];

  const itemY = 1.75, itemH = 0.55;
  items.forEach((it, i) => {
    const y = itemY + i * itemH;
    // small azure dot on the left
    s.addShape(pres.shapes.OVAL, {
      x: 0.55, y: y + 0.18, w: 0.18, h: 0.18,
      fill: { color: AZURE }, line: { type: "none" },
    });
    // key (bold, monospace flavour)
    s.addText(it.k, {
      x: 0.85, y: y, w: 3.9, h: itemH,
      fontFace: "Consolas", fontSize: 13, bold: true, color: NAVY,
      valign: "middle", margin: 0,
    });
    // — separator + value
    s.addText("—  " + it.v, {
      x: 4.75, y: y, w: 4.85, h: itemH,
      fontFace: FONT_BODY, fontSize: 13, color: INK,
      valign: "middle", margin: 0,
    });
  });

  // Footer-style takeaway
  s.addText(
    "This single file is the answer to the brief's core question.",
    {
      x: 0.5, y: 4.7, w: 9, h: 0.35,
      fontFace: FONT_BODY, fontSize: 13, italic: true, color: AZURE_DARK,
      align: "center", margin: 0,
    }
  );

  addFooter(s, 5);
  s.addNotes(
    "This single file is the answer to the brief's core question. I'd open it live and walk the four blocks. Two minutes max."
  );
}

// ============================================================================
// Slide 6 — Two-pattern processing (and why)
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  addTitle(s, "Two-pattern processing — and why I kept both");

  // Two side-by-side cards
  const cardY = 1.2, cardH = 2.05, cardW = 4.45, cardGap = 0.2;

  // Left card: Declarative DLT
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: cardY, w: cardW, h: cardH,
    fill: { color: BG_PANEL }, line: { color: AZURE, width: 0.75 },
    rectRadius: 0.08,
  });
  s.addText("Declarative — DLT", {
    x: 0.7, y: cardY + 0.18, w: cardW - 0.4, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 16, bold: true, color: AZURE_DARK, margin: 0,
  });
  s.addText("For unified streaming + batch flows. Lineage, autoscaling, retries from the framework.", {
    x: 0.7, y: cardY + 0.65, w: cardW - 0.4, h: cardH - 0.85,
    fontFace: FONT_BODY, fontSize: 13, color: INK, margin: 0,
  });

  // Right card: Imperative PySpark
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5 + cardW + cardGap, y: cardY, w: cardW, h: cardH,
    fill: { color: BG_LIGHT }, line: { color: RULE, width: 0.75 },
    rectRadius: 0.08,
  });
  s.addText("Imperative — PySpark + PipelineRun", {
    x: 0.7 + cardW + cardGap, y: cardY + 0.18, w: cardW - 0.4, h: 0.4,
    fontFace: FONT_HEAD, fontSize: 16, bold: true, color: NAVY, margin: 0,
  });
  s.addText("For SAP edge cases needing full PySpark control. PipelineRun chassis = lock + watermark + audit row.", {
    x: 0.7 + cardW + cardGap, y: cardY + 0.65, w: cardW - 0.4, h: cardH - 0.85,
    fontFace: FONT_BODY, fontSize: 13, color: INK, margin: 0,
  });

  // Decision-rule callout
  const calY = 3.55, calH = 1.0;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: calY, w: 9, h: calH,
    fill: { color: NAVY }, line: { type: "none" }, rectRadius: 0.08,
  });
  // Vertical accent bar on left
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: calY, w: 0.12, h: calH,
    fill: { color: AZURE }, line: { type: "none" },
  });
  s.addText("Decision rule", {
    x: 0.85, y: calY + 0.12, w: 8.5, h: 0.3,
    fontFace: FONT_HEAD, fontSize: 12, bold: true, color: AZURE,
    charSpacing: 2, margin: 0,
  });
  s.addText(
    "Can this be expressed as @dlt.table + expects + apply_changes? If yes, write DLT. If no, write a notebook.",
    {
      x: 0.85, y: calY + 0.42, w: 8.5, h: 0.5,
      fontFace: FONT_BODY, fontSize: 14, italic: true, color: "FFFFFF", margin: 0,
    }
  );

  addFooter(s, 6);
  s.addNotes(
    "This is a deliberate choice for the PoC — shows pattern judgment, not just one default. In production I'd probably consolidate to DLT once the team has internalised the framework."
  );
}

// ============================================================================
// Slide 7 — Production readiness (2x2 grid)
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  addTitle(s, "Production-readiness signals");

  const cells = [
    {
      tag: "Lineage",
      body: "Unity Catalog + Purview for AS9100-style audit trails.",
    },
    {
      tag: "Security",
      body: "Managed identities · CMK from Key Vault · Private Endpoints · RLS in Synapse.",
    },
    {
      tag: "CI/CD",
      body: "GitHub Actions: ruff + pytest (cov ≥ 80%) + terraform validate + checkov + gitleaks.",
    },
    {
      tag: "Cost levers",
      body: "ADLS lifecycle · Synapse pause schedule · Photon · spot workers · Serverless for ad-hoc.",
    },
  ];

  // 2x2 layout
  const colW = 4.45, rowH = 1.6, startX = 0.5, startY = 1.2, gap = 0.2;
  cells.forEach((c, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = startX + col * (colW + gap);
    const y = startY + row * (rowH + gap);

    // Card background
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: x, y: y, w: colW, h: rowH,
      fill: { color: BG_LIGHT }, line: { color: RULE, width: 0.75 },
      rectRadius: 0.08,
    });
    // Tag pill (small azure box top-left of the card)
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: x + 0.25, y: y + 0.22, w: 1.4, h: 0.36,
      fill: { color: AZURE }, line: { type: "none" }, rectRadius: 0.05,
    });
    s.addText(c.tag, {
      x: x + 0.25, y: y + 0.22, w: 1.4, h: 0.36,
      fontFace: FONT_HEAD, fontSize: 11, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", margin: 0,
    });
    // Body
    s.addText(c.body, {
      x: x + 0.25, y: y + 0.7, w: colW - 0.5, h: rowH - 0.85,
      fontFace: FONT_BODY, fontSize: 13, color: INK, margin: 0,
    });
  });

  addFooter(s, 7);
  s.addNotes(
    "This slide is about signalling the production-shape thinking, not building everything. Specifically the OIDC federation, environment-promotion via merge requests, and pre-commit hooks are the things I'd dig into if asked."
  );
}

// ============================================================================
// Slide 8 — Trade-offs and what I'd do next
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: "FFFFFF" };

  addTitle(s, "Trade-offs · what I'd do next");

  const items = [
    {
      n: "1",
      h: "Dual-pattern is deliberate",
      body: "DLT + imperative kept on purpose to show pattern judgment. In production I'd consolidate to DLT once the team is comfortable.",
    },
    {
      n: "2",
      h: "Honest gaps",
      body: "Cosmos online feature store · full networking · real Synapse end-to-end · Purview scan config. All listed in TODO.md.",
    },
    {
      n: "3",
      h: "Things I'm uncertain about",
      body: "Wrote them up in TODO.md. Would genuinely like a second opinion from the panel.",
    },
  ];

  const startY = 1.2, rowH = 1.15;
  items.forEach((it, i) => {
    const y = startY + i * rowH;
    // Number badge
    s.addShape(pres.shapes.OVAL, {
      x: 0.55, y: y + 0.05, w: 0.6, h: 0.6,
      fill: { color: AZURE }, line: { type: "none" },
    });
    s.addText(it.n, {
      x: 0.55, y: y + 0.05, w: 0.6, h: 0.6,
      fontFace: FONT_HEAD, fontSize: 22, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", margin: 0,
    });
    // Header
    s.addText(it.h, {
      x: 1.4, y: y, w: 8.1, h: 0.4,
      fontFace: FONT_HEAD, fontSize: 18, bold: true, color: NAVY, margin: 0,
    });
    // Body
    s.addText(it.body, {
      x: 1.4, y: y + 0.4, w: 8.1, h: 0.65,
      fontFace: FONT_BODY, fontSize: 13, color: INK, margin: 0,
    });
  });

  addFooter(s, 8);
  s.addNotes(
    "I'd open the design-doc decision table and TODO.md live. The point of this slide is that I know what's not done and why — and that I have a view on what to discuss."
  );
}

// ============================================================================
// Slide 9 — Q&A (dark bookend matching the title)
// ============================================================================
{
  const s = pres.addSlide();
  s.background = { color: NAVY };

  // azure accent block on the left
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: H,
    fill: { color: AZURE }, line: { type: "none" },
  });

  s.addText("Questions?", {
    x: 0.5, y: 1.6, w: 9, h: 1.4,
    fontFace: FONT_HEAD, fontSize: 56, bold: true, color: "FFFFFF",
    align: "center", margin: 0,
  });

  s.addText(
    "I'd most welcome a question on why I kept both DLT and imperative notebooks — that's the part I'm most curious to get a second opinion on.",
    {
      x: 1.0, y: 3.4, w: 8, h: 1.0,
      fontFace: FONT_BODY, fontSize: 16, italic: true, color: "CFE3F8",
      align: "center", margin: 0,
    }
  );

  s.addText(FOOTER, {
    x: 0.4, y: H - 0.35, w: 6, h: 0.25,
    fontFace: FONT_BODY, fontSize: 9, color: "8FB6DA", margin: 0,
  });
  s.addText("9 / 9", {
    x: W - 1.1, y: H - 0.35, w: 0.7, h: 0.25,
    fontFace: FONT_BODY, fontSize: 9, color: "8FB6DA", align: "right", margin: 0,
  });

  s.addNotes(
    "After this slide, I stop talking and let the panel ask. Do not fill silence — the silence is the point."
  );
}

// ============================================================================
// Write
// ============================================================================
pres.writeFile({ fileName: "docs/people10_poc.pptx" }).then((file) => {
  console.log("Wrote:", file);
});
