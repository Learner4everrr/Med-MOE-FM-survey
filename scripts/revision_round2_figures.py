"""Redraw manuscript Figures 2-5 without changing the underlying synthesis.

Run after analyze_foundation_models.py. Requires pandas, Pillow, reportlab and
Poppler's pdftoppm on PATH. Outputs embedded-font vector PDFs and 600-dpi PNG/TIFF.
All sizes are in points at the manuscript's actual 5.85-inch figure width.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

import pandas as pd
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures"
PUB = OUT / "publication_quality"
W = 421.2
N = 90
C = {
    "ink": "#111820", "edge": "#45566A", "grid": "#CDD5DE",
    "neutral": "#EEF1F4", "blue": "#9FC5E3", "green": "#9ECDB6",
    "pink": "#DEA0B3", "purple": "#BCA8D3", "gold": "#E4C788",
    "line": "#81405B", "white": "#FFFFFF",
}
FILES = {
    2: "Figure_1_architecture_to_evidence",
    3: "Figure_2_landscape_and_tasks",
    4: "Figure_3_design_routing",
    5: "Figure_4_evidence_readiness",
}

# These matrices and values are unchanged from the preceding figure scripts.
YEARS = [2022, 2023, 2024, 2025, 2026]
ANNUAL = [1, 0, 16, 40, 33]
CUMULATIVE = [1, 1, 17, 57, 90]
APPS = [
    "FM/LLM platforms", "Diagnosis/prognosis", "Multimodal intelligence",
    "Evaluation/implementation", "Clinical NLP/QA",
    "Treatment/recommendation", "EHR/trajectory/risk",
]
APP_COUNTS = [40, 16, 16, 7, 4, 4, 3]
EXPERT_COLS = ["Adapter", "Clinical\ndomain", "Generic", "Modality",
               "Model /\nscale", "Patient", "Task"]
APP_MATRIX = [
    [9, 3, 3, 11, 4, 7, 3], [5, 1, 1, 5, 1, 1, 2],
    [1, 1, 0, 12, 1, 0, 1], [0, 2, 1, 1, 1, 1, 1],
    [0, 0, 0, 3, 0, 0, 1], [1, 1, 0, 0, 0, 2, 0],
    [0, 0, 1, 1, 0, 0, 1],
]
MODS = ["Medical imaging", "Image-text/VLM", "Omics/molecular",
        "Clinical text", "Physiological signals", "Knowledge resources",
        "Structured EHR"]
MOD_MATRIX = [
    [2, 2, 3, 19, 3, 2, 4], [1, 2, 1, 14, 2, 1, 2],
    [3, 2, 1, 10, 3, 5, 2], [1, 1, 0, 5, 2, 0, 0],
    [4, 0, 0, 3, 0, 1, 1], [3, 0, 2, 2, 1, 1, 0],
    [0, 0, 1, 3, 0, 2, 1],
]
UNITS = ["Modality", "Task", "Feature / patch / voxel", "Token",
         "Decision / model", "Patient / sample", "Not clearly reported"]
UNIT_MATRIX = [
    [1, 0, 0, 18, 0, 0, 0], [1, 0, 0, 4, 0, 0, 8],
    [1, 1, 1, 6, 2, 2, 0], [2, 0, 0, 3, 1, 2, 1],
    [2, 1, 1, 0, 0, 1, 2], [1, 0, 0, 2, 0, 0, 0],
    [10, 7, 4, 10, 4, 7, 1],
]
EVIDENCE = [41, 37, 12]
EVIDENCE_LABELS = ["Benchmark / non-patient", "Internal retrospective",
                   "External or multicenter"]
EVIDENCE_COLORS = [C["blue"], C["pink"], C["green"]]
DETAIL = [("Median completeness", 80.0), ("Routing detail", 74.4),
          ("Expert detail", 65.6)]
SIGNALS = [("External evaluation", 9), ("Multicenter evaluation", 4),
           ("Prospective/workflow", 0), ("Interpretability", 28),
           ("Fairness analysis", 2), ("Clinician/human evaluation", 6),
           ("Code/repository", 19)]
FUNCTIONS = ["Fusion", "Heterogeneity", "Parameter-efficient",
             "Feature/decision", "Conditional computation", "Multi-task",
             "Model collaboration"]
ROLE_MATRIX = [[19, 23, 7], [6, 6, 0], [7, 2, 1], [5, 3, 0],
               [4, 3, 0], [0, 0, 2], [0, 0, 2]]


def register_fonts():
    fonts = Path("C:/Windows/Fonts")
    if (fonts / "times.ttf").exists():
        pdfmetrics.registerFont(TTFont("ReviewTimes", str(fonts / "times.ttf")))
        pdfmetrics.registerFont(TTFont("ReviewTimesBold", str(fonts / "timesbd.ttf")))
        return "ReviewTimes", "ReviewTimesBold"
    # Standard PDF Times family, for reproduction on non-Windows systems.
    return "Times-Roman", "Times-Bold"


REGULAR, BOLD = register_fonts()


def width(text, size=9.25, bold=False):
    return pdfmetrics.stringWidth(str(text), BOLD if bold else REGULAR, size)


def wrap(text, limit, size=9.25, bold=False):
    lines = []
    for paragraph in str(text).split("\n"):
        start = len(lines)
        line = ""
        for word in paragraph.split():
            trial = (line + " " + word).strip()
            if line and width(trial, size, bold) > limit:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
        if len(lines) - start == 2:
            # Balance two-line labels instead of leaving an isolated final word.
            words = paragraph.split()
            splits = [(" ".join(words[:i]), " ".join(words[i:]))
                      for i in range(1, len(words))]
            fits = [s for s in splits if max(width(t, size, bold) for t in s) <= limit]
            if fits:
                best = min(fits, key=lambda s: abs(width(s[0], size, bold)
                                                  - width(s[1], size, bold)))
                lines[start:] = best
    return lines


class Figure:
    def __init__(self, number, height):
        self.number, self.h = number, height
        self.path = PUB / f"Figure_{number}.pdf"
        self.c = canvas.Canvas(str(self.path), pagesize=(W, height),
                               pageCompression=1, initialFontName=REGULAR)
        self.c.setTitle(f"Figure {number}")
        self.bounds = []
        self.min_font = 100

    def text(self, x, y, text, size=9.25, bold=False, align="left", color=None):
        text = str(text)
        tw = width(text, size, bold)
        left = x - tw / 2 if align == "center" else x - tw if align == "right" else x
        self.bounds.append((left, y, left + tw, y + size, text))
        self.min_font = min(self.min_font, size)
        self.c.setFillColor(HexColor(color or C["ink"]))
        self.c.setFont(BOLD if bold else REGULAR, size)
        self.c.drawString(left, self.h - y - size * .82, text)

    def block(self, x, y, text, limit, size=9.25, leading=10.5,
              bold=False, align="left"):
        lines = wrap(text, limit, size, bold)
        for i, line in enumerate(lines):
            self.text(x, y + i * leading, line, size, bold, align)
        return len(lines) * leading

    def centered(self, x, y, w, h, text, size=9.25, bold=False):
        lines = wrap(text, w - 5, size, bold)
        total = len(lines) * (size + 1)
        if total > h + 0.01:
            raise ValueError(f"Figure {self.number}: text exceeds cell height: {text!r}")
        for i, line in enumerate(lines):
            self.text(x + w / 2, y + (h - total) / 2 + i * (size + 1),
                      line, size, bold, "center")

    def rect(self, x, y, w, h, fill=None, border=None, radius=0, lw=.8):
        assert x >= 0 and y >= 0 and x + w <= W + .01 and y + h <= self.h + .01
        self.c.setFillColor(HexColor(fill or C["white"]))
        self.c.setStrokeColor(HexColor(border or C["edge"]))
        self.c.setLineWidth(max(lw, .8))
        if radius:
            self.c.roundRect(x, self.h - y - h, w, h, radius, fill=1, stroke=1)
        else:
            self.c.rect(x, self.h - y - h, w, h, fill=1, stroke=bool(border))

    def line(self, x1, y1, x2, y2, color=None, lw=.85, dash=None):
        self.c.saveState()
        self.c.setStrokeColor(HexColor(color or C["edge"]))
        self.c.setLineWidth(max(lw, .5 if color == C["grid"] else .85))
        if dash:
            self.c.setDash(*dash)
        self.c.line(x1, self.h - y1, x2, self.h - y2)
        self.c.restoreState()

    def arrow(self, x1, y1, x2, y2):
        from math import hypot
        self.line(x1, y1, x2, y2, lw=1)
        d = hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        p = self.c.beginPath()
        p.moveTo(x2, self.h - y2)
        p.lineTo(x2 - 4.0 * ux + 1.8 * uy, self.h - (y2 - 4.0 * uy - 1.8 * ux))
        p.lineTo(x2 - 4.0 * ux - 1.8 * uy, self.h - (y2 - 4.0 * uy + 1.8 * ux))
        p.close()
        self.c.setFillColor(HexColor(C["edge"]))
        self.c.drawPath(p, fill=1, stroke=0)

    def title(self, x, y, key, text, size=11):
        self.text(x, y, f"({key}) {text}", size, True)

    def finish(self):
        bad = [b for b in self.bounds if b[0] < -.01 or b[1] < 0
               or b[2] > W + .01 or b[3] > self.h + .01]
        if bad:
            raise ValueError(f"Figure {self.number} out-of-canvas text: {bad}")
        self.c.save()
        prefix = OUT / FILES[self.number]
        subprocess.run(["pdftoppm", "-singlefile", "-r", "600", "-png",
                        str(self.path), str(prefix)], check=True)
        with Image.open(prefix.with_suffix(".png")) as im:
            im.convert("RGB").save(PUB / f"Figure_{self.number}.tif",
                                   compression="tiff_lzw", dpi=(600, 600))
        shutil.copy2(prefix.with_suffix(".png"), PUB / f"Figure_{self.number}.png")
        return {"figure": self.number, "width_pt": W, "height_pt": self.h,
                "minimum_font_pt_at_manuscript_size": self.min_font,
                "text_bounds_ok": True, "raster_dpi": 600}


def counts(name):
    df = pd.read_csv(ROOT / "analysis" / f"count_{name}.csv")
    return [(str(r.category), int(r.n), float(r.percent)) for r in df.itertuples()]


def bars(f, labels, vals, y, row, label_right, start, length, maximum,
         color, size=9.25, value_right=None, percents=True):
    for i, (label, value) in enumerate(zip(labels, vals)):
        cy = y + i * row
        f.text(label_right, cy - size / 2, label, size, align="right")
        end = start + length * value / maximum
        if value:
            f.rect(start, cy - 4, end - start, 8, color, C["edge"], lw=.5)
        else:
            f.line(start, cy - 4, start, cy + 4)
        val = f"{value} ({value/N*100:.1f}%)" if percents else str(value)
        f.text(value_right if value_right else end + 4, cy - size / 2,
               val, size, align="right" if value_right else "left")


def heatmap(f, top, key, title, rows, values, row_h=19.5):
    f.title(3, top, key, title)
    x0, x1 = 132, 418
    cell = (x1 - x0) / 7
    head, first = top + 21, top + 43
    vmax = max(max(r) for r in values)
    for j, label in enumerate(EXPERT_COLS):
        f.centered(x0 + j * cell, head, cell, 21, label, 9.25)
    for i, label in enumerate(rows):
        cy = first + (i + .5) * row_h
        f.text(x0 - 6, cy - 4.625, label, 9.25, align="right")
        for j, value in enumerate(values[i]):
            ratio = value / vmax
            rgb = tuple(round(start + (end - start) * ratio)
                        for start, end in zip((243, 246, 249), (113, 167, 207)))
            color = "#" + "".join(f"{v:02x}" for v in rgb)
            f.rect(x0 + j * cell, first + i * row_h, cell, row_h,
                   color, C["white"], lw=.7)
            f.text(x0 + (j + .5) * cell, cy - 4.625, value, 9.25, align="center")


def architecture():
    f = Figure(2, 590)
    specs = [
        ("Modality experts", "Image\nText\nOmics", "Shared or\nmodality encoders",
         ["Image expert", "Text expert", "Omics expert"],
         ["Data-source branches", "Availability or modality features",
          "Modality or feature", "Encoder, connector, or fusion block"]),
        ("Task or domain experts", "Clinical\ninput", "Shared\nbackbone",
         ["Task expert", "Domain expert", "Specialty expert"],
         ["Task or knowledge branches", "Task prompt, metadata, or hidden state",
          "Task, token, or feature", "Backbone block, decoder, or head"]),
        ("Adapter or parameter experts", "Clinical\ninput", "Frozen or shared\nbackbone",
         ["Adapter A", "Adapter B", "LoRA module"],
         ["Parameter-efficient modules", "Task, sample, or hidden state",
          "Task, token, or feature", "Adapters inserted across model layers"]),
    ]
    for i, (title, inp, backbone, experts, fields) in enumerate(specs):
        y = 5 + i * 142
        f.title(3, y, "abc"[i], title)
        cy = y + 52
        nodes = [(3, cy - 22, 37, 44, inp, C["neutral"]),
                 (56, cy - 22, 79, 44, backbone, C["blue"]),
                 (152, cy - 18, 45, 36, "Router /\ngate", C["pink"]),
                 (347, cy - 17, 71, 34, "Output", C["purple"])]
        for x, ny, w, h, label, color in nodes:
            f.rect(x, ny, w, h, color, C["edge"], radius=3)
            f.centered(x, ny, w, h, label)
        f.arrow(41, cy, 54, cy)
        f.arrow(136, cy, 150, cy)
        for j, expert in enumerate(experts):
            ey = y + 22 + j * 21
            f.rect(218, ey, 88, 18, C["green"], C["edge"], radius=3)
            f.centered(218, ey, 88, 18, expert)
            f.arrow(198, cy, 216, ey + 9)
            f.line(307, ey + 9, 333, cy)
        f.arrow(333, cy, 345, cy)
        for k, label in enumerate(["Expert type", "Routing signal",
                                   "Routing unit", "Module location"]):
            xx = 3 if k % 2 == 0 else 219
            yy = y + 89 + (k // 2) * 25
            f.text(xx, yy, label, 9.25, True)
            f.block(xx + 74, yy, fields[k], 123, size=9.25, leading=10.5)
    f.title(3, 436, "d", "Architecture fields used in the review")
    # Neutral table colors deliberately carry no component-role semantics.
    columns = [(3, 90), (93, 146), (239, 179)]
    for (x, w), title in zip(columns, ["Dimension", "Question answered", "Examples"]):
        f.rect(x, 452, w, 21, C["neutral"], C["grid"])
        f.centered(x, 452, w, 21, title, 9.25, True)
    rows = [
        ("Expert definition", "What distinguishes the experts?",
         "Modality, task, domain, patient, model, or adapter"),
        ("Routing signal", "What information reaches the router?",
         "Availability, task metadata, uncertainty, or latent features"),
        ("Routing unit", "What entity is assigned or weighted?",
         "Modality, task, sample, token, feature, patch, or model"),
        ("Expert location", "Where are expert modules inserted?",
         "Encoder, connector, backbone block, adapter, decoder, or full model"),
    ]
    for i, row in enumerate(rows):
        for (x, w), label in zip(columns, row):
            f.rect(x, 473 + 28 * i, w, 28, C["white"], C["grid"])
            f.centered(x, 473 + 28 * i, w, 28, label, 9.25)
    return f.finish()


def landscape():
    f = Figure(3, 585)
    f.title(3, 5, "a", "Publication growth")
    f.rect(25, 25, 9, 6, C["blue"], C["edge"])
    f.text(38, 23, "Annual", 9.25)
    f.line(84, 28, 98, 28, C["line"], 1, (3, 2))
    f.text(102, 23, "Cumulative", 9.25)
    x0, y0, bw, bh = 25, 48, 168, 112
    for n in [0, 25, 50, 75, 100]:
        yy = y0 + bh - n / 100 * bh
        f.line(x0, yy, x0 + bw, yy, C["grid"], .4)
        f.text(x0 - 5, yy - 4, n, 9.25, align="right")
    f.text(25, 35, "Studies", 9.25)
    xs = [x0 + 15 + i * 34 for i in range(5)]
    for x, year, value in zip(xs, YEARS, ANNUAL):
        h = value / 100 * bh
        if value:
            f.rect(x - 9, y0 + bh - h, 18, h, C["blue"], C["edge"])
        label_y = y0 + bh - h + 3 if value >= 10 else y0 + bh - h - 11
        f.text(x, label_y, value, 9.25, align="center")
        f.text(x, 165, year, 9.25, align="center")
    pts = [(x, y0 + bh - v / 100 * bh) for x, v in zip(xs, CUMULATIVE)]
    for a, b in zip(pts, pts[1:]):
        f.line(*a, *b, C["line"], 1.1, (3, 2))
    for x, y in pts:
        f.c.setFillColor(HexColor(C["line"]))
        f.c.circle(x, f.h - y, 1.8, fill=1, stroke=0)
    f.text(pts[-1][0] + 5, pts[-1][1] - 9, "90", 9.25)
    f.text(25, 181, "2026 through July 13", 9.25)
    f.title(214, 5, "b", "Applications")
    # This subplot uses a count-only value label; the caption specifies counts.
    for i, (label, value) in enumerate(zip(APPS, APP_COUNTS)):
        yy = 41 + i * 23
        f.text(320, yy - 4.625, label, 9.25, align="right")
        f.rect(326, yy - 4, value / 40 * 70, 8, C["green"], C["edge"])
        f.text(416, yy - 4.625, value, 9.25, align="right")
    heatmap(f, 207, "c", "Application by expert organization", APPS, APP_MATRIX, 19.5)
    heatmap(f, 397, "d", "Modality by expert organization", MODS, MOD_MATRIX, 19.5)
    return f.finish()


def design():
    f = Figure(4, 601)
    experts, roles = counts("expert_specialization"), counts("moe_functional_role")
    density, signal = counts("routing_density"), counts("routing_signal")
    adaptation = counts("adaptation_methods")
    f.title(3, 5, "a", "Expert organization")
    f.title(217, 5, "b", "MoE function")
    bars(f, ["Modality", "Adapter/parameter", "Patient/subpopulation", "Task",
             "Clinical domain", "Model/scale", "Generic/unclear"],
         [v[1] for v in experts], 31, 17, 99, 103, 49, 35,
         C["blue"], value_right=205)
    bars(f, ["Multimodal/data fusion", "Heterogeneity", "Parameter-efficient",
             "Feature/decision", "Conditional computation", "Multi-task",
             "Model collaboration"],
         [v[1] for v in roles], 31, 17, 313, 317, 49, 50,
         C["gold"], value_right=419)
    f.title(3, 153, "c", "Routing density")
    f.title(217, 153, "d", "Router input or signal")
    x = 4
    for (_, value, _), color in zip(density, [C["neutral"], C["purple"], C["green"]]):
        w = 199 * value / N
        f.rect(x, 178, w, 19, color, C["edge"])
        f.text(x + w / 2, 183, value, 9.25, align="center")
        x += w
    for i, ((_, value, pct), label, color) in enumerate(zip(
            density, ["Not clearly reported", "Sparse/selective", "Dense/soft"],
            [C["neutral"], C["purple"], C["green"]])):
        yy = 210 + i * 20
        f.rect(4, yy + 1, 7, 7, color, C["edge"])
        f.text(16, yy, label, 9.25)
        f.text(205, yy, f"{value} ({pct:.1f}%)", 9.25, align="right")
    bars(f, ["Not clearly reported", "Modality", "Task or metadata",
             "Uncertainty/reliability", "Similarity or latent", "Rule-based/fixed",
             "Learned input-dependent"],
         [v[1] for v in signal], 179, 17, 313, 317, 49, 35,
         C["pink"], value_right=419)
    f.title(3, 301, "e", "Training and adaptation")
    bars(f, [v[0] for v in adaptation], [v[1] for v in adaptation],
         326, 13.5, 164, 170, 188, 40, C["green"], value_right=419)
    heatmap(f, 450, "f", "Routing unit by expert organization", UNITS, UNIT_MATRIX, 15)
    return f.finish()


def evidence():
    f = Figure(5, 550)
    f.title(3, 5, "a", "Evidence groups")
    f.title(218, 5, "b", "Reporting detail")
    x = 4
    for value, color in zip(EVIDENCE, EVIDENCE_COLORS):
        w = 199 * value / N
        f.rect(x, 29, w, 22, color, C["edge"])
        f.text(x + w / 2, 36, value, 9.5, align="center")
        x += w
    for i, (label, value, color) in enumerate(zip(EVIDENCE_LABELS, EVIDENCE, EVIDENCE_COLORS)):
        yy = 66 + i * 21
        f.rect(4, yy + 1, 7, 7, color, C["edge"])
        f.text(16, yy, label, 9.5)
        f.text(205, yy, f"{value/N*100:.1f}%", 9.5, align="right")
    for i, ((label, pct), color) in enumerate(zip(DETAIL, [C["blue"], C["purple"], C["green"]])):
        yy = 29 + i * 32
        f.text(219, yy, label, 9.5)
        f.text(418, yy, f"{pct:.1f}%", 9.5, align="right")
        f.rect(219, yy + 14, 199, 8, C["neutral"])
        f.rect(219, yy + 14, 199 * pct / 100, 8, color, C["edge"])
    f.title(3, 146, "c", "Evaluation signals")
    bars(f, [s[0] for s in SIGNALS], [s[1] for s in SIGNALS],
         174, 22, 132, 138, 225, 30, C["pink"], size=9.5, value_right=418)
    f.title(3, 336, "d", "Evidence groups by MoE function")
    f.text(417, 356, "Total", 9.25, align="right")
    for i, (label, values) in enumerate(zip(FUNCTIONS, ROLE_MATRIX)):
        yy = 378 + i * 23
        f.text(126, yy - 4.5, label, 9.5, align="right")
        x = 132
        for value, color in zip(values, EVIDENCE_COLORS):
            if not value:
                continue
            w = 250 * value / 50
            f.rect(x, yy - 6.5, w, 13, color, C["edge"], lw=.5)
            if w < 8:
                f.text(x + w + 4, yy - 4.625, value, 9.25)
            else:
                f.text(x + w / 2, yy - 4.625, value, 9.25, align="center")
            x += w
        f.text(413, yy - 4.5, sum(values), 9.5, align="right")
    for x, label, color in zip([4, 152, 293], EVIDENCE_LABELS, EVIDENCE_COLORS):
        f.rect(x, 537, 7, 7, color, C["edge"])
        f.text(x + 11, 536, label, 9.25)
    return f.finish()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--figures", nargs="+", type=int, default=[2, 3, 4, 5])
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    PUB.mkdir(exist_ok=True)
    assert sum(ANNUAL) == sum(APP_COUNTS) == sum(EVIDENCE) == N
    assert [sum(r) for r in APP_MATRIX] == APP_COUNTS
    assert [sum(r[i] for r in ROLE_MATRIX) for i in range(3)] == EVIDENCE
    assert CUMULATIVE == [sum(ANNUAL[:i+1]) for i in range(len(ANNUAL))]
    for name in ["expert_specialization", "moe_functional_role", "routing_density"]:
        assert sum(r[1] for r in counts(name)) == N
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (ROOT / "analysis").glob("*") if p.is_file()}
    summaries = []
    for n in args.figures:
        summaries.append({2: architecture, 3: landscape, 4: design, 5: evidence}[n]())
        print(f"Figure {n} generated", flush=True)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (ROOT / "analysis").glob("*") if p.is_file()}
    assert before == after
    audit = {"figures": summaries, "included_studies": N,
             "analysis_input_hashes": before, "analysis_inputs_unchanged": before == after,
             "evidence_by_function_column_totals": EVIDENCE,
             "rendering": "600-dpi RGB PNG and LZW TIFF, embedded Times vector PDF"}
    (PUB / "figure_rendering_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
