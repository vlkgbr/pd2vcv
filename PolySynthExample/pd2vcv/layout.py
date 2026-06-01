import math
import re
from typing import List, Tuple, Dict, Optional
from pathlib import Path

from pd2vcv.models import ComponentPos, PatchInfo, HvParam, CustomWidgets, _UI_PREFIXES
from pd2vcv.utils import sanitize_identifier

HP_MM       = 5.08
PANEL_H_MM  = 128.5       # 3U

_STANDARD_HP = [4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32]

def ceil_hp(mm_needed: float) -> int:
    hp = mm_needed / HP_MM
    for s in _STANDARD_HP:
        if s >= hp:
            return s
    result = int(math.ceil(hp / 2) * 2)  # round up to next even HP
    print(f"[layout] WARNING: panel wider than 32 HP standard — using {result} HP")
    return result


def detect_svg_panel_hp(svg_path: Path) -> int:
    """
    Auto-detect panel width in HP from an SVG file's width attribute.
    Supports width="NNNmm" and viewBox-based detection.
    """
    text = svg_path.read_text(errors="replace")
    # Try width="NNNmm" or width="NNN"
    m = re.search(r'width\s*=\s*"([^"]+)"', text)
    if m:
        w_str = m.group(1).replace("mm", "").strip()
        try:
            hp = ceil_hp(float(w_str))
            print(f"[svg]   Detected panel width: {float(w_str):.1f} mm -> {hp} HP")
            return hp
        except ValueError:
            pass
    # Try viewBox
    m = re.search(r'viewBox\s*=\s*"([^"]+)"', text)
    if m:
        parts = m.group(1).split()
        if len(parts) >= 3:
            try:
                hp = ceil_hp(float(parts[2]))
                print(f"[svg]   Detected panel width from viewBox: {float(parts[2]):.1f} mm -> {hp} HP")
                return hp
            except ValueError:
                pass
    print(f"[svg]   WARNING: Cannot detect panel width from {svg_path.name}, using 10 HP default")
    return 10


def apply_layout_overrides(components: List[ComponentPos],
                           layout_data: dict) -> List[ComponentPos]:
    """
    Override auto-layout positions and port types with user-saved values.
    layout_data format: {"positions": {"LABEL": {"x": N, "y": N, "port_type": ".."}}}
    """
    overrides = layout_data.get("positions", {})
    applied_pos = 0
    applied_type = 0
    for c in components:
        if c.label in overrides:
            ov = overrides[c.label]
            if "x" in ov and "y" in ov:
                c.x = float(ov["x"])
                c.y = float(ov["y"])
                applied_pos += 1
            if "port_type" in ov:
                c.port_type = ov["port_type"]
                applied_type += 1
    if applied_pos:
        print(f"[layout] Applied {applied_pos} position override(s)")
    if applied_type:
        print(f"[layout] Applied {applied_type} port type override(s)")
    return components


def _smart_layout(info: PatchInfo, dac_labels: dict) -> Tuple[int, List[ComponentPos]]:
    """
    Smart-naming layout engine.

    Column structure per core_name (all share the same X):
      Y1  base_    knob  (large, RoundHugeBlackKnob)
      Y2  attenv_  knob  (small bipolar, BefacoBipolarKnob)  — if present
          atten_   knob  (small unipolar, RoundSmallBlackKnob) — if present
      Y3  mapped adc~ jack (input)    — if core_name has _adcN suffix
      Y4  mapped dac~ jack (output)   — if [s core_name_dacN @hv_param] exists

    Unmapped adc~/dac~ jacks go in a horizontal row at the bottom.
    Stereo: unmapped adc~ 1+2 -> IN_L/IN_R; unmapped dac~ 1+2 -> OUT_L/OUT_R.
    """
    MARGIN      = 8.0   # mm left/right edge
    COL_SEP     = 22.0  # mm between column centres
    JACK_SEP    = 9.5   # mm between unmapped jacks
    GAP         = 6.0   # mm gap between in/out groups at bottom

    # Y positions within a column (% of panel height)
    Y_BASE       = PANEL_H_MM * 0.22   # top row: base_ knobs
    Y_ATTEN      = PANEL_H_MM * 0.44   # middle row: atten/attenv knobs
    Y_MAPPED_IN  = PANEL_H_MM * 0.62   # mapped adc~ jack
    Y_MAPPED_OUT = PANEL_H_MM * 0.75   # mapped dac~ jack (below input)
    Y_UNMAPPED   = PANEL_H_MM * 0.88   # unmapped I/O row (pushed down to avoid labels)

    in_params  = [p for p in info.params if p.direction != "out"]
    n_ai = info.num_input_channels
    n_ao = info.num_output_channels

    # ── Group by core_name ─────────────────────────────────────────────────
    columns: dict = {}  # core_name -> list of HvParam
    plain_params = []              # params without smart naming
    mapped_adcs  = set()           # adc indices (1-based) claimed by columns
    mapped_dacs  = set()           # dac indices (1-based) claimed by [s] labels

    for p in in_params:
        if p.adc_map > n_ai:
            print(f"[warning] '{p.name}' requests adc~ {p.adc_map}, but patch only has {n_ai} audio input(s)! Ignoring mapping.")
            p.adc_map = 0

        if p.core_name:
            columns.setdefault(p.core_name, []).append(p)
            if p.adc_map > 0:
                mapped_adcs.add(p.adc_map)
        else:
            plain_params.append(p)

    for core, dac_idx in dac_labels.items():
        if dac_idx > n_ao:
            print(f"[warning] '[s {core}_dac{dac_idx}]' requests dac~ {dac_idx}, but patch only has {n_ao} audio output(s)! Ignoring.")
            continue
        columns.setdefault(core, [])   # ensure column exists even if no knobs for this core
        mapped_dacs.add(dac_idx)

    all_adcs    = set(range(1, n_ai + 1))
    all_dacs    = set(range(1, n_ao + 1))
    unmapped_in  = sorted(all_adcs - mapped_adcs)  # 1-based indices
    unmapped_out = sorted(all_dacs - mapped_dacs)   # 1-based indices

    stereo_in  = (unmapped_in[:2] == [1, 2])
    stereo_out = (unmapped_out[:2] == [1, 2])
    info.stereo_in  = stereo_in
    info.stereo_out = stereo_out

    n_out_jacks = len(unmapped_out)

    n_smart_cols = len(columns)
    n_plain      = len(plain_params)
    n_cols_total = n_smart_cols + n_plain

    col_width_mm  = MARGIN * 2 + max(n_cols_total - 1, 0) * COL_SEP
    unmapped_in_w = MARGIN + len(unmapped_in) * JACK_SEP + GAP + max(n_out_jacks, 1) * JACK_SEP + MARGIN
    panel_hp = ceil_hp(max(col_width_mm, unmapped_in_w, 4 * HP_MM))
    W = panel_hp * HP_MM

    total_col_w = max(n_cols_total - 1, 0) * COL_SEP
    x0_cols = (W - total_col_w) / 2

    components: List[ComponentPos] = []
    param_idx  = 0

    seen_labels: dict[str, int] = {}
    def dedup_label(l: str) -> str:
        if l in seen_labels:
            seen_labels[l] += 1
            return f"{l}_{seen_labels[l]}"
        seen_labels[l] = 0
        return l

    for col_i, (core, params_in_col) in enumerate(columns.items()):
        cx = round(x0_cols + col_i * COL_SEP, 2)

        def _sort_key(p: HvParam):
            order = {"base": 0, "atten": 1, "attenv": 1, "button": 2, "trigger": 2, "switch": 2}
            return order.get(p.ui_type, 3)
        params_in_col.sort(key=_sort_key)

        col_adc = next((p.adc_map for p in params_in_col if p.adc_map > 0), 0)
        col_dac = dac_labels.get(core, 0)

        y_cursor = Y_ATTEN
        for p in params_in_col:
            if p.ui_type == "base":
                y = Y_BASE
                kt = _UI_PREFIXES["base"]
            elif p.ui_type in ("atten", "attenv", "button", "trigger", "switch"):
                y = y_cursor
                y_cursor += 14.0
                kt = _UI_PREFIXES.get(p.ui_type, "RoundSmallBlackKnob")
            else:
                y = y_cursor
                y_cursor += 14.0
                kt = "RoundBlackKnob"

            lbl = p.enum_label or sanitize_identifier(p.core_name).upper()
            ui_lbl_clean = lbl.replace("_", " ")

            if p.ui_type in ("atten", "attenv", "button", "trigger", "switch"):
                lbl = lbl + "_" + p.ui_type.upper()

            if p.ui_type in ("button", "trigger", "switch"):
                display_lbl = ui_lbl_clean
            else:
                display_lbl = lbl.replace("_", " ")

            lbl = dedup_label(lbl)
            p.enum_label = lbl
            components.append(ComponentPos(
                kind="param", label=lbl,
                x=cx, y=round(y, 2),
                index=param_idx,
                knob_type=kt,
                ui_label=display_lbl,
            ))
            param_idx += 1

        if col_adc > 0:
            jack_lbl = dedup_label(sanitize_identifier(core).upper() + "_IN")
            components.append(ComponentPos(
                kind="input", label=jack_lbl,
                x=cx, y=round(Y_MAPPED_IN, 2),
                index=col_adc - 1,
                knob_type="",
                ui_label=sanitize_identifier(core).upper().replace("_", " ") + " IN",
            ))

        if col_dac > 0:
            jack_lbl = dedup_label(sanitize_identifier(core).upper() + "_OUT")
            components.append(ComponentPos(
                kind="output", label=jack_lbl,
                x=cx, y=round(Y_MAPPED_OUT, 2),
                index=col_dac - 1,
                knob_type="",
                ui_label=sanitize_identifier(core).upper().replace("_", " ") + " OUT",
            ))

    for plain_i, p in enumerate(plain_params):
        cx = round(x0_cols + (n_smart_cols + plain_i) * COL_SEP, 2)
        lbl = dedup_label(p.safe_name.upper())
        p.enum_label = lbl
        components.append(ComponentPos(
            kind="param", label=lbl,
            x=cx, y=round(Y_BASE, 2),
            index=param_idx,
            knob_type="RoundBlackKnob",
            ui_label=lbl.replace("_", " "),
        ))
        param_idx += 1

    x_in = MARGIN + JACK_SEP / 2
    for rank_i, adc_n in enumerate(unmapped_in):
        if stereo_in and adc_n in (1, 2):
            lbl = "IN_L" if adc_n == 1 else "IN_R"
            ui_lbl = "IN L" if adc_n == 1 else "IN R"
        else:
            lbl = f"IN_{adc_n}"
            ui_lbl = "IN" if (len(unmapped_in) == 1 and adc_n == 1) else f"IN {adc_n}"
        lbl = dedup_label(lbl)
        components.append(ComponentPos(
            kind="input", label=lbl,
            x=round(x_in + rank_i * JACK_SEP, 2),
            y=round(Y_UNMAPPED, 2),
            index=adc_n - 1,
            knob_type="",
            ui_label=ui_lbl,
        ))

    x_out = W - MARGIN - JACK_SEP / 2 - max(n_out_jacks - 1, 0) * JACK_SEP
    for i, dac_n in enumerate(unmapped_out):
        if stereo_out and dac_n in (1, 2):
            lbl = "OUT_L" if dac_n == 1 else "OUT_R"
            ui_lbl = "OUT L" if dac_n == 1 else "OUT R"
        else:
            lbl = f"OUT_{dac_n}"
            ui_lbl = "OUT" if (len(unmapped_out) == 1 and dac_n == 1) else f"OUT {dac_n}"
        lbl = dedup_label(lbl)
        components.append(ComponentPos(
            kind="output", label=lbl,
            x=round(x_out + i * JACK_SEP, 2),
            y=round(Y_UNMAPPED, 2),
            index=dac_n - 1,
            knob_type="",
            ui_label=ui_lbl,
        ))

    return panel_hp, components


def _classic_layout(info: PatchInfo, dac_labels: dict) -> Tuple[int, List[ComponentPos]]:
    """
    Original flat layout: one knob row, audio I/O at bottom.
    Used when no smart naming prefixes are detected.
    Stereo: unmapped adc~ 1+2 -> IN_L/IN_R; dac~ 1+2 -> OUT_L/OUT_R.
    """
    in_params   = [p for p in info.params if p.direction != "out"]
    n_knobs     = len(in_params)
    n_ai        = info.num_input_channels
    n_ao        = info.num_output_channels

    stereo_in  = (n_ai == 2)
    stereo_out = (n_ao == 2)
    info.stereo_in  = stereo_in
    info.stereo_out = stereo_out

    n_out_jacks = n_ao

    JACK_SEP  = 9.5
    KNOB_SEP  = 14.0
    MARGIN    = 7.0
    GAP       = 6.0

    jack_row_mm = (
        MARGIN + max(n_ai, 1) * JACK_SEP + GAP
        + max(n_out_jacks, 1) * JACK_SEP + MARGIN
    )
    knob_row_mm = MARGIN * 2 + max(n_knobs, 1) * KNOB_SEP
    panel_hp = ceil_hp(max(jack_row_mm, knob_row_mm))
    W = panel_hp * HP_MM

    components: List[ComponentPos] = []

    seen_labels: dict[str, int] = {}
    def dedup_label(l: str) -> str:
        if l in seen_labels:
            seen_labels[l] += 1
            return f"{l}_{seen_labels[l]}"
        seen_labels[l] = 0
        return l

    knob_y = PANEL_H_MM * 0.32
    if n_knobs > 0:
        total_w = (n_knobs - 1) * KNOB_SEP
        x0 = (W - total_w) / 2
        for i, p in enumerate(in_params):
            lbl = dedup_label(p.safe_name.upper())
            p.enum_label = lbl
            components.append(ComponentPos(
                kind="param", label=lbl,
                x=round(x0 + i * KNOB_SEP, 2),
                y=round(knob_y, 2), index=i,
                ui_label=lbl.replace("_", " ")
            ))

    in_y = PANEL_H_MM * 0.83
    x0 = MARGIN + JACK_SEP / 2
    for i in range(n_ai):
        adc_n = i + 1
        if stereo_in and adc_n in (1, 2):
            lbl = "IN_L" if adc_n == 1 else "IN_R"
            ui_lbl = "IN L" if adc_n == 1 else "IN R"
        else:
            lbl = f"IN_{adc_n}"
            ui_lbl = "IN" if (n_ai == 1) else f"IN {adc_n}"
        lbl = dedup_label(lbl)
        components.append(ComponentPos(
            kind="input", label=lbl,
            x=round(x0 + i * JACK_SEP, 2),
            y=round(in_y, 2), index=i,
            ui_label=ui_lbl,
        ))

    out_y = PANEL_H_MM * 0.83
    x0 = W - MARGIN - JACK_SEP / 2 - (n_out_jacks - 1) * JACK_SEP
    for i in range(n_ao):
        dac_n = i + 1
        if stereo_out and dac_n in (1, 2):
            lbl = "OUT_L" if dac_n == 1 else "OUT_R"
            ui_lbl = "OUT L" if dac_n == 1 else "OUT R"
        else:
            lbl = f"OUT_{dac_n}"
            ui_lbl = "OUT" if (n_ao == 1) else f"OUT {dac_n}"
        lbl = dedup_label(lbl)
        components.append(ComponentPos(
            kind="output", label=lbl,
            x=round(x0 + i * JACK_SEP, 2),
            y=round(out_y, 2), index=i,
            ui_label=ui_lbl,
        ))

    return panel_hp, components


def run_layout(info: PatchInfo, dac_labels: dict, has_smart: bool) -> Tuple[int, List[ComponentPos]]:
    """Determine layout mode and calculate components."""
    if has_smart:
        return _smart_layout(info, dac_labels)
    else:
        return _classic_layout(info, dac_labels)
