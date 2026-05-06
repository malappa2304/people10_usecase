/**
 * build_deck.js — generate docs/people10_poc.pptx from the outline at
 * docs/03_presentation_deck_outline.md.
 *
 * Run: NODE_PATH="$(npm root -g)" node scripts/build_deck.js
 *
 * Deps: pptxgenjs, react, react-dom, react-icons, sharp (all global).
 */
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const Fa = require("react-icons/fa");

// ============================================================================
// Theme — Azure-aligned, modern, professional
// ============================================================================
const NAVY        = "0F2A52";  // dark navy for body titles + dark slides
const NAVY_DEEP   = "0A1F3D";  // a deeper shade for the title slide background
const AZURE       = "0078D4";  // Microsoft Azure accent
const AZURE_DARK  = "005A9E";
const AZURE_LIGHT = "DEECF9";
const INK         = "1F2937";  // body text
const MUTED       = "6B7280";  // captions / footers
const BG_LIGHT    = "F8FAFC";
const BG_PANEL    = "EFF6FC";
const RULE        = "E5E7EB";

// Typography. Segoe UI is Microsoft's modern sans-serif, native on Windows
// and the default for most enterprise users. Reads cleaner than Calibri
// on a projector.
const FONT_HEAD = "Segoe UI";
const FONT_BODY = "Segoe UI";

const FOOTER = "People10 Solutions Lab — Malappa";

// ============================================================================
// Icon helper — renders a react-icons component to base64 PNG.
// ============================================================================
async function icon(IconComponent, color = AZURE, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + png.toString("base64");
}

// ============================================================================
// Setup
// ============================================================================
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";  // 10" x 5.625"
  pres.author = "Malappa";
  pres.title = "Cloud-Native Data Platform on Azure";

  const W = 10, H = 5.625;

  // Pre-render the icons we need.
  const icons = {
    layers:    await icon(Fa.FaLayerGroup,    "FFFFFF"),
    clock:     await icon(Fa.FaBolt,          "FFFFFF"),
    chart:     await icon(Fa.FaChartLine,     "FFFFFF"),
    brain:     await icon(Fa.FaBrain,         "FFFFFF"),
    unlock:    await icon(Fa.FaUnlockAlt,     "FFFFFF"),
    diamond:   await icon(Fa.FaDatabase,      "FFFFFF"),
    sitemap:   await icon(Fa.FaSitemap,       "FFFFFF"),
    shield:    await icon(Fa.FaShieldAlt,     "FFFFFF"),
    cogs:      await icon(Fa.FaCogs,          "FFFFFF"),
    coins:     await icon(Fa.FaCoins,         "FFFFFF"),
    code:      await icon(Fa.FaFileCode,      "E2E8F0"),
    stream:    await icon(Fa.FaStream,        AZURE),
    server:    await icon(Fa.FaServer,        AZURE),
    bronze:    await icon(Fa.FaCircle,        "B08D57"),
    silver:    await icon(Fa.FaCircle,        "9CA3AF"),
    gold:      await icon(Fa.FaCircle,        "D4A23A"),
  };

  // --------------------------------------------------------------------------
  function addFooter(slide, n) {
    slide.addText(FOOTER, {
      x: 0.4, y: H - 0.35, w: 6, h: 0.25,
      fontFace: FONT_BODY, fontSize: 9, color: MUTED, margin: 0,
    });
    slide.addText(`${n} / 9`, {
      x: W - 1.1, y: H - 0.35, w: 0.7, h: 0.25,
      fontFace: FONT_BODY, fontSize: 9, color: MUTED, align: "right", margin: 0,
    });
  }
  function addTitle(slide, text) {
    slide.addText(text, {
      x: 0.5, y: 0.35, w: 9, h: 0.65,
      fontFace: FONT_HEAD, fontSize: 28, bold: true, color: NAVY, margin: 0,
    });
  }

  // ==========================================================================
  // Slide 1 — Title
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: NAVY_DEEP };

    // Right-side accent column
    s.addShape(pres.shapes.RECTANGLE, {
      x: W - 1.6, y: 0, w: 1.6, h: H,
      fill: { color: AZURE }, line: { type: "none" },
    });

    // Eyebrow tag
    s.addText("PEOPLE10 SOLUTIONS LAB · 3-DAY TAKE-HOME", {
      x: 0.6, y: 1.1, w: 7.6, h: 0.35,
      fontFace: FONT_HEAD, fontSize: 11, bold: true, color: AZURE_LIGHT,
      charSpacing: 4, margin: 0,
    });

    // Title
    s.addText("Cloud-Native Data Platform on Azure", {
      x: 0.6, y: 1.5, w: 7.6, h: 1.5,
      fontFace: FONT_HEAD, fontSize: 40, bold: true, color: "FFFFFF", margin: 0,
    });

    // Subtitle
    s.addText("Unifying streaming and batch on a Databricks Lakehouse", {
      x: 0.6, y: 3.1, w: 7.6, h: 0.5,
      fontFace: FONT_BODY, fontSize: 18, color: AZURE_LIGHT, margin: 0,
    });

    // Author line with rule
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: 4.2, w: 0.4, h: 0.04,
      fill: { color: AZURE }, line: { type: "none" },
    });
    s.addText("Malappa", {
      x: 0.6, y: 4.3, w: 7.6, h: 0.4,
      fontFace: FONT_HEAD, fontSize: 16, bold: true, color: "FFFFFF", margin: 0,
    });
    s.addText("github.com/malappa2304/people10_usecase", {
      x: 0.6, y: 4.65, w: 7.6, h: 0.35,
      fontFace: FONT_BODY, fontSize: 12, color: "8FB6DA", margin: 0,
    });

    // Tech-stack chips
    const chips = ["ADLS Gen2", "Databricks", "Delta Lake", "Synapse"];
    const chipW = 1.35, chipGap = 0.15, chipY = 5.1;
    const totalW = chips.length * chipW + (chips.length - 1) * chipGap;
    let chipX = 0.6;
    chips.forEach((c) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: chipX, y: chipY, w: chipW, h: 0.36,
        fill: { color: "FFFFFF", transparency: 85 }, line: { color: AZURE_LIGHT, width: 0.5 },
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

  // ==========================================================================
  // Slide 2 — The problem (5 numbered rows, each with an icon)
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    addTitle(s, "The problem the brief asks us to solve");

    const items = [
      { ic: icons.layers, h: "Unify streaming + batch",     sub: "One platform for both, not two pipelines." },
      { ic: icons.clock,  h: "Enable real-time insights",   sub: "Sub-minute freshness for the business." },
      { ic: icons.chart,  h: "Support analytics",           sub: "BI dashboards and ad-hoc SQL." },
      { ic: icons.brain,  h: "Prepare data for AI/ML",      sub: "Offline + online feature stores." },
      { ic: icons.unlock, h: "Replace legacy ETL + silos",  sub: "Unblock scalability, agility, and cost." },
    ];

    const startY = 1.2, rowH = 0.7;
    items.forEach((it, i) => {
      const y = startY + i * rowH;
      // Square azure icon tile
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.6, y: y + 0.05, w: 0.55, h: 0.55,
        fill: { color: AZURE }, line: { type: "none" }, rectRadius: 0.05,
      });
      s.addImage({ data: it.ic, x: 0.7, y: y + 0.15, w: 0.35, h: 0.35 });
      // Heading
      s.addText(it.h, {
        x: 1.35, y: y + 0.02, w: 7.5, h: 0.32,
        fontFace: FONT_HEAD, fontSize: 18, bold: true, color: NAVY, margin: 0,
      });
      // Subtitle
      s.addText(it.sub, {
        x: 1.35, y: y + 0.34, w: 7.8, h: 0.3,
        fontFace: FONT_BODY, fontSize: 13, color: MUTED, margin: 0,
      });
    });

    addFooter(s, 2);
    s.addNotes(
      "This is the problem statement straight from the brief. Spend a moment on each — they're the five things every other slide answers."
    );
  }

  // ==========================================================================
  // Slide 3 — Architecture (INLINE DIAGRAM, not just talking points)
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    addTitle(s, "Architecture — streaming + batch into one medallion");

    // Diagram area: y 1.15 to 4.0
    // ----- Source boxes (left) -----
    const srcX = 0.5, srcW = 1.65;
    // Streaming
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: srcX, y: 1.45, w: srcW, h: 0.85,
      fill: { color: BG_PANEL }, line: { color: AZURE, width: 1 }, rectRadius: 0.06,
    });
    s.addText("⚡ Streaming", {
      x: srcX, y: 1.5, w: srcW, h: 0.32,
      fontFace: FONT_HEAD, fontSize: 13, bold: true, color: AZURE_DARK, align: "center", margin: 0,
    });
    s.addText("Event Hubs (Kafka)\nCNC telemetry", {
      x: srcX, y: 1.82, w: srcW, h: 0.5,
      fontFace: FONT_BODY, fontSize: 10, color: INK, align: "center", margin: 0,
    });
    // Batch
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: srcX, y: 2.7, w: srcW, h: 0.85,
      fill: { color: BG_PANEL }, line: { color: AZURE, width: 1 }, rectRadius: 0.06,
    });
    s.addText("📦 Batch", {
      x: srcX, y: 2.75, w: srcW, h: 0.32,
      fontFace: FONT_HEAD, fontSize: 13, bold: true, color: AZURE_DARK, align: "center", margin: 0,
    });
    s.addText("Auto Loader\nSAP / MES files", {
      x: srcX, y: 3.07, w: srcW, h: 0.5,
      fontFace: FONT_BODY, fontSize: 10, color: INK, align: "center", margin: 0,
    });

    // Both source arrows -> Bronze
    // (lines are drawn as thin rectangles + arrow tip OVAL since pptxgenjs LINE
    // does not include arrow heads natively in all versions)
    function arrow(x1, y1, x2, y2, color = NAVY) {
      // line
      s.addShape(pres.shapes.LINE, {
        x: x1, y: y1, w: x2 - x1, h: y2 - y1,
        line: { color, width: 1.5, endArrowType: "triangle" },
      });
    }
    // Sources -> Bronze
    arrow(srcX + srcW, 1.87, 2.85, 2.40);  // streaming -> bronze
    arrow(srcX + srcW, 3.12, 2.85, 2.6);   // batch -> bronze

    // ----- Medallion boxes (centre) -----
    const medY = 2.2, medH = 0.85, medW = 1.25;
    const bronzeX = 2.85, silverX = 4.4, goldX = 5.95;
    function medallionBox(x, label, accent) {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: x, y: medY, w: medW, h: medH,
        fill: { color: "FFFFFF" }, line: { color: accent, width: 1.5 },
        rectRadius: 0.08,
        shadow: { type: "outer", blur: 6, offset: 1, color: "000000", angle: 90, opacity: 0.08 },
      });
      // Top accent strip
      s.addShape(pres.shapes.RECTANGLE, {
        x: x, y: medY, w: medW, h: 0.08,
        fill: { color: accent }, line: { type: "none" },
      });
      s.addText(label, {
        x: x, y: medY + 0.1, w: medW, h: 0.42,
        fontFace: FONT_HEAD, fontSize: 14, bold: true, color: NAVY, align: "center", valign: "middle", margin: 0,
      });
      s.addText("Delta", {
        x: x, y: medY + 0.5, w: medW, h: 0.28,
        fontFace: FONT_BODY, fontSize: 10, italic: true, color: MUTED, align: "center", margin: 0,
      });
    }
    medallionBox(bronzeX, "Bronze", "B08D57");
    medallionBox(silverX, "Silver", "9CA3AF");
    medallionBox(goldX,   "Gold",   "D4A23A");

    // Medallion arrows
    arrow(bronzeX + medW, medY + medH / 2, silverX, medY + medH / 2);
    arrow(silverX + medW, medY + medH / 2, goldX,   medY + medH / 2);

    // Big "Databricks Lakehouse on Delta Lake" wrapper label
    s.addText("Databricks Lakehouse on Delta Lake", {
      x: bronzeX, y: 3.2, w: goldX + medW - bronzeX, h: 0.28,
      fontFace: FONT_BODY, fontSize: 10, italic: true, color: MUTED, align: "center", margin: 0,
    });

    // ----- Consumer boxes (right) -----
    const consX = 7.7, consW = 1.85;
    const consumers = [
      { label: "Real-time", sub: "Power BI live tiles", y: 1.25 },
      { label: "Analytics", sub: "Synapse Serverless / Dedicated", y: 2.2 },
      { label: "AI / ML",   sub: "Offline + online feature store", y: 3.15 },
    ];
    consumers.forEach((c) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: consX, y: c.y, w: consW, h: 0.85,
        fill: { color: BG_PANEL }, line: { color: AZURE, width: 1 }, rectRadius: 0.06,
      });
      s.addText(c.label, {
        x: consX, y: c.y + 0.05, w: consW, h: 0.32,
        fontFace: FONT_HEAD, fontSize: 13, bold: true, color: AZURE_DARK, align: "center", margin: 0,
      });
      s.addText(c.sub, {
        x: consX, y: c.y + 0.37, w: consW, h: 0.45,
        fontFace: FONT_BODY, fontSize: 10, color: INK, align: "center", margin: 0,
      });
      // Gold -> consumer arrow
      arrow(goldX + medW, medY + medH / 2, consX, c.y + 0.42);
    });

    // ----- Three numbered talking-point pills under the diagram -----
    const tipY = 4.45, tipH = 0.55, tipW = 2.95, tipGap = 0.225;
    const tips = [
      "Both arrows → same Bronze. Unification at the storage layer.",
      "Bronze → Silver → Gold on Delta Lake. ACID, time travel.",
      "Three consumers — one per ask in the brief.",
    ];
    let tipX = 0.5;
    tips.forEach((t, i) => {
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: tipX, y: tipY, w: tipW, h: tipH,
        fill: { color: BG_LIGHT }, line: { color: RULE, width: 0.5 }, rectRadius: 0.06,
      });
      s.addShape(pres.shapes.OVAL, {
        x: tipX + 0.15, y: tipY + 0.13, w: 0.3, h: 0.3,
        fill: { color: AZURE }, line: { type: "none" },
      });
      s.addText(String(i + 1), {
        x: tipX + 0.15, y: tipY + 0.13, w: 0.3, h: 0.3,
        fontFace: FONT_HEAD, fontSize: 12, bold: true, color: "FFFFFF",
        align: "center", valign: "middle", margin: 0,
      });
      s.addText(t, {
        x: tipX + 0.55, y: tipY + 0.05, w: tipW - 0.65, h: tipH - 0.1,
        fontFace: FONT_BODY, fontSize: 10, color: INK, valign: "middle", margin: 0,
      });
      tipX += tipW + tipGap;
    });

    addFooter(s, 3);
    s.addNotes(
      "I'd open the architecture diagram (docs/01_architecture_diagram.md) live during this slide. Stay on these three points; do not get pulled into a Delta-vs-Iceberg debate yet."
    );
  }

  // ==========================================================================
  // Slide 4 — Why Delta Lake (bullets + callout)
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    addTitle(s, "Why Delta Lake makes the medallion work");

    // Left column — 4 bullets, each with a small accent square
    const bulletX = 0.55, bulletStartY = 1.4;
    const bullets = [
      "Concurrent streaming + batch writes on the same table (ACID)",
      "Time travel for replay and audit",
      "MERGE and apply_changes for idempotent SCD2",
      "Open format — Synapse Serverless reads Delta natively",
    ];
    bullets.forEach((b, i) => {
      const y = bulletStartY + i * 0.7;
      s.addShape(pres.shapes.RECTANGLE, {
        x: bulletX, y: y + 0.16, w: 0.18, h: 0.18,
        fill: { color: AZURE }, line: { type: "none" },
      });
      s.addText(b, {
        x: bulletX + 0.32, y: y, w: 5.4, h: 0.55,
        fontFace: FONT_BODY, fontSize: 15, color: INK, valign: "middle", margin: 0,
      });
    });

    // Right column — callout panel: Delta vs Iceberg quick answer
    const calX = 6.4, calY = 1.4, calW = 3.1, calH = 3.4;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: calX, y: calY, w: calW, h: calH,
      fill: { color: BG_PANEL }, line: { color: AZURE, width: 1 }, rectRadius: 0.1,
    });
    // Header pill
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: calX + 0.25, y: calY + 0.25, w: 1.7, h: 0.35,
      fill: { color: AZURE }, line: { type: "none" }, rectRadius: 0.05,
    });
    s.addText("IF ASKED", {
      x: calX + 0.25, y: calY + 0.25, w: 1.7, h: 0.35,
      fontFace: FONT_HEAD, fontSize: 9, bold: true, color: "FFFFFF",
      align: "center", valign: "middle", charSpacing: 3, margin: 0,
    });
    s.addText("Delta vs Iceberg?", {
      x: calX + 0.25, y: calY + 0.7, w: calW - 0.5, h: 0.4,
      fontFace: FONT_HEAD, fontSize: 16, bold: true, color: AZURE_DARK, margin: 0,
    });
    s.addText(
      [
        { text: "Native Databricks + Unity Catalog. Synapse Serverless reads Delta directly — no metastore shim.", options: { breakLine: true } },
        { text: "", options: { breakLine: true } },
        { text: "At 10× scale on a Trino-led stack I'd reconsider.", options: { italic: true, color: MUTED } },
      ],
      {
        x: calX + 0.25, y: calY + 1.2, w: calW - 0.5, h: calH - 1.4,
        fontFace: FONT_BODY, fontSize: 12, color: INK, margin: 0,
      }
    );

    addFooter(s, 4);
    s.addNotes(
      "If asked Delta vs Iceberg: native Databricks + Unity Catalog + Synapse Serverless reads it directly. At 10× scale on a Trino-led stack I'd reconsider."
    );
  }

  // ==========================================================================
  // Slide 5 — The PoC (file pointer + 5 walkthrough rows)
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    addTitle(s, "The PoC — one DLT pipeline, both arrows");

    // Code-style file pointer
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y: 1.05, w: 9, h: 0.45,
      fill: { color: NAVY }, line: { type: "none" }, rectRadius: 0.05,
    });
    s.addImage({ data: icons.code, x: 0.65, y: 1.16, w: 0.22, h: 0.22 });
    s.addText("poc/databricks/pipelines/unified_medallion_dlt.py", {
      x: 0.95, y: 1.05, w: 8.5, h: 0.45,
      fontFace: "Consolas", fontSize: 13, color: "E2E8F0",
      valign: "middle", margin: 0,
    });

    // Five walkthrough items
    const items = [
      { k: "bronze_cnc_telemetry",         v: "streaming Kafka source · @dlt.table" },
      { k: "bronze_sap_production_order",  v: "batch Auto Loader · same @dlt.table decorator" },
      { k: "Three expectation tiers",      v: "expect_or_fail · expect_or_drop · expect" },
      { k: "SCD2",                          v: "via apply_changes" },
      { k: "Gold materialised view",       v: "joins streaming-derived rollups with batch-derived dimensions" },
    ];

    const itemY = 1.78, itemH = 0.55;
    items.forEach((it, i) => {
      const y = itemY + i * itemH;
      // Index pill
      s.addShape(pres.shapes.OVAL, {
        x: 0.55, y: y + 0.13, w: 0.3, h: 0.3,
        fill: { color: AZURE }, line: { type: "none" },
      });
      s.addText(String(i + 1), {
        x: 0.55, y: y + 0.13, w: 0.3, h: 0.3,
        fontFace: FONT_HEAD, fontSize: 11, bold: true, color: "FFFFFF",
        align: "center", valign: "middle", margin: 0,
      });
      // key
      s.addText(it.k, {
        x: 1.0, y: y, w: 4.0, h: itemH,
        fontFace: "Consolas", fontSize: 13, bold: true, color: NAVY,
        valign: "middle", margin: 0,
      });
      // value
      s.addText(it.v, {
        x: 5.05, y: y, w: 4.55, h: itemH,
        fontFace: FONT_BODY, fontSize: 13, color: INK,
        valign: "middle", margin: 0,
      });
    });

    // Footer takeaway
    s.addText("This single file is the answer to the brief's core question.", {
      x: 0.5, y: 4.7, w: 9, h: 0.35,
      fontFace: FONT_BODY, fontSize: 13, italic: true, color: AZURE_DARK,
      align: "center", margin: 0,
    });

    addFooter(s, 5);
    s.addNotes(
      "This single file is the answer to the brief's core question. I'd open it live and walk the four blocks. Two minutes max."
    );
  }

  // ==========================================================================
  // Slide 6 — Two-pattern processing
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    addTitle(s, "Two-pattern processing — and why I kept both");

    const cardY = 1.2, cardH = 2.0, cardW = 4.45, cardGap = 0.2;

    // Left card: DLT
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y: cardY, w: cardW, h: cardH,
      fill: { color: BG_PANEL }, line: { color: AZURE, width: 1 }, rectRadius: 0.08,
    });
    // Top accent strip
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: cardY, w: cardW, h: 0.08,
      fill: { color: AZURE }, line: { type: "none" },
    });
    s.addText("Declarative — DLT", {
      x: 0.7, y: cardY + 0.22, w: cardW - 0.4, h: 0.4,
      fontFace: FONT_HEAD, fontSize: 17, bold: true, color: AZURE_DARK, margin: 0,
    });
    s.addText(
      "Unified streaming + batch. Lineage, autoscaling, retries from the framework. Inline expectations and apply_changes.",
      {
        x: 0.7, y: cardY + 0.7, w: cardW - 0.4, h: cardH - 0.85,
        fontFace: FONT_BODY, fontSize: 13, color: INK, margin: 0,
      }
    );

    // Right card: Imperative
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5 + cardW + cardGap, y: cardY, w: cardW, h: cardH,
      fill: { color: BG_LIGHT }, line: { color: RULE, width: 1 }, rectRadius: 0.08,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5 + cardW + cardGap, y: cardY, w: cardW, h: 0.08,
      fill: { color: NAVY }, line: { type: "none" },
    });
    s.addText("Imperative — PySpark + PipelineRun", {
      x: 0.7 + cardW + cardGap, y: cardY + 0.22, w: cardW - 0.4, h: 0.4,
      fontFace: FONT_HEAD, fontSize: 17, bold: true, color: NAVY, margin: 0,
    });
    s.addText(
      "SAP edge cases needing full PySpark control. PipelineRun chassis = lock + watermark + structured audit row.",
      {
        x: 0.7 + cardW + cardGap, y: cardY + 0.7, w: cardW - 0.4, h: cardH - 0.85,
        fontFace: FONT_BODY, fontSize: 13, color: INK, margin: 0,
      }
    );

    // Decision-rule callout (dark band)
    const calY = 3.55, calH = 1.0;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.5, y: calY, w: 9, h: calH,
      fill: { color: NAVY }, line: { type: "none" }, rectRadius: 0.08,
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: calY, w: 0.12, h: calH,
      fill: { color: AZURE }, line: { type: "none" },
    });
    s.addText("DECISION RULE", {
      x: 0.85, y: calY + 0.15, w: 8.5, h: 0.3,
      fontFace: FONT_HEAD, fontSize: 10, bold: true, color: AZURE,
      charSpacing: 4, margin: 0,
    });
    s.addText(
      "Can this be expressed as @dlt.table + expects + apply_changes?  If yes → DLT.  If no → notebook.",
      {
        x: 0.85, y: calY + 0.45, w: 8.5, h: 0.5,
        fontFace: FONT_BODY, fontSize: 14, italic: true, color: "FFFFFF", margin: 0,
      }
    );

    addFooter(s, 6);
    s.addNotes(
      "This is a deliberate choice for the PoC — shows pattern judgment, not just one default. In production I'd probably consolidate to DLT once the team has internalised the framework."
    );
  }

  // ==========================================================================
  // Slide 7 — Production readiness (2x2 grid with icons)
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    addTitle(s, "Production-readiness signals");

    const cells = [
      { ic: icons.sitemap, tag: "Lineage",     body: "Unity Catalog + Purview for AS9100-style audit trails." },
      { ic: icons.shield,  tag: "Security",    body: "Managed identities · CMK from Key Vault · Private Endpoints · RLS in Synapse." },
      { ic: icons.cogs,    tag: "CI/CD",       body: "GitHub Actions: ruff + pytest (cov ≥ 80%) + terraform validate + checkov + gitleaks." },
      { ic: icons.coins,   tag: "Cost levers", body: "ADLS lifecycle · Synapse pause schedule · Photon · spot workers · Serverless for ad-hoc." },
    ];

    const colW = 4.45, rowH = 1.6, startX = 0.5, startY = 1.2, gap = 0.2;
    cells.forEach((c, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const x = startX + col * (colW + gap);
      const y = startY + row * (rowH + gap);

      // Card
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x, y, w: colW, h: rowH,
        fill: { color: BG_LIGHT }, line: { color: RULE, width: 1 }, rectRadius: 0.08,
      });
      // Icon tile
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: x + 0.25, y: y + 0.25, w: 0.55, h: 0.55,
        fill: { color: AZURE }, line: { type: "none" }, rectRadius: 0.06,
      });
      s.addImage({ data: c.ic, x: x + 0.35, y: y + 0.35, w: 0.35, h: 0.35 });
      // Tag (text label, no separate pill — cleaner)
      s.addText(c.tag, {
        x: x + 0.95, y: y + 0.3, w: colW - 1.1, h: 0.45,
        fontFace: FONT_HEAD, fontSize: 17, bold: true, color: NAVY, valign: "middle", margin: 0,
      });
      // Body
      s.addText(c.body, {
        x: x + 0.25, y: y + 0.92, w: colW - 0.5, h: rowH - 1.05,
        fontFace: FONT_BODY, fontSize: 12.5, color: INK, margin: 0,
      });
    });

    addFooter(s, 7);
    s.addNotes(
      "This slide is about signalling the production-shape thinking, not building everything. Specifically the OIDC federation, environment-promotion via merge requests, and pre-commit hooks are the things I'd dig into if asked."
    );
  }

  // ==========================================================================
  // Slide 8 — Trade-offs and what I'd do next (beefier content)
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: "FFFFFF" };
    addTitle(s, "Trade-offs · what I'd do next");

    const items = [
      {
        n: "1",
        h: "Dual-pattern is a deliberate choice",
        body: "DLT + imperative kept on purpose to show pattern judgment. In production I'd consolidate to DLT once the team has internalised the framework — keep PySpark only for genuine SAP edge cases.",
      },
      {
        n: "2",
        h: "Honest gaps",
        body: "Cosmos online feature store (designed, not provisioned) · full networking module · real Synapse end-to-end run · Purview scan config. All listed in TODO.md with effort estimates.",
      },
      {
        n: "3",
        h: "Things I'm uncertain about",
        body: "Whether 32 Event Hubs partitions is right at the cost we'd actually run at. Whether apply_changes plays well with the audit chassis. Whether to retire the imperative path entirely. Would genuinely like a panel opinion.",
      },
    ];

    const startY = 1.2, rowH = 1.15;
    items.forEach((it, i) => {
      const y = startY + i * rowH;
      s.addShape(pres.shapes.OVAL, {
        x: 0.55, y: y + 0.05, w: 0.6, h: 0.6,
        fill: { color: AZURE }, line: { type: "none" },
      });
      s.addText(it.n, {
        x: 0.55, y: y + 0.05, w: 0.6, h: 0.6,
        fontFace: FONT_HEAD, fontSize: 22, bold: true, color: "FFFFFF",
        align: "center", valign: "middle", margin: 0,
      });
      s.addText(it.h, {
        x: 1.4, y: y, w: 8.1, h: 0.4,
        fontFace: FONT_HEAD, fontSize: 17, bold: true, color: NAVY, margin: 0,
      });
      s.addText(it.body, {
        x: 1.4, y: y + 0.4, w: 8.1, h: 0.7,
        fontFace: FONT_BODY, fontSize: 13, color: INK, margin: 0,
      });
    });

    addFooter(s, 8);
    s.addNotes(
      "I'd open the design-doc decision table and TODO.md live. The point of this slide is that I know what's not done and why — and that I have a view on what to discuss."
    );
  }

  // ==========================================================================
  // Slide 9 — Q&A bookend
  // ==========================================================================
  {
    const s = pres.addSlide();
    s.background = { color: NAVY_DEEP };

    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 0.18, h: H,
      fill: { color: AZURE }, line: { type: "none" },
    });

    s.addText("Questions?", {
      x: 0.5, y: 1.6, w: 9, h: 1.4,
      fontFace: FONT_HEAD, fontSize: 60, bold: true, color: "FFFFFF",
      align: "center", margin: 0,
    });

    // Decorative azure rule under the title
    s.addShape(pres.shapes.RECTANGLE, {
      x: 4.6, y: 3.05, w: 0.8, h: 0.05,
      fill: { color: AZURE }, line: { type: "none" },
    });

    s.addText(
      "I'd most welcome a question on why I kept both DLT and imperative notebooks — that's the part I'm most curious to get a second opinion on.",
      {
        x: 1.0, y: 3.4, w: 8, h: 1.0,
        fontFace: FONT_BODY, fontSize: 16, italic: true, color: AZURE_LIGHT,
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

  // --------------------------------------------------------------------------
  await pres.writeFile({ fileName: "docs/people10_poc.pptx" });
  console.log("Wrote docs/people10_poc.pptx");
}

build().catch((err) => {
  console.error(err);
  process.exit(1);
});
