import re
import sys
import json
from pathlib import Path
from typing import List, Tuple, Optional

from pd2vcv.models import HvParam, HeavyApi, PatchInfo, _UI_PREFIXES
from pd2vcv.utils import sanitize_identifier, deduplicate_safe_names

# ─────────────────────────────────────────────────────────────────────────────
# Regex Constants
# ─────────────────────────────────────────────────────────────────────────────

# Matches [r name @hv_param min max default] — input params (knobs / CV targets)
_PD_PARAM_RE = re.compile(
    r"r\s+(\S+)\s+@hv[._]param"
    r"(?:\s+([+-]?\d+\.?\d*))?"
    r"(?:\s+([+-]?\d+\.?\d*))?"
    r"(?:\s+([+-]?\d+\.?\d*))?",
    re.IGNORECASE,
)

# Matches [s name @hv_param ...] — output label hints, e.g. [s filter_dac1 @hv_param 0 1 0]
_PD_SEND_RE = re.compile(
    r"s\s+(\S+)\s+@hv[._]param"
    r"(?:\s+([+-]?\d+\.?\d*)\s+([+-]?\d+\.?\d*)\s+([+-]?\d+\.?\d*))?",
    re.IGNORECASE,
)

# Strips _dacN suffix from a send name to recover the core column name
_DAC_SUFFIX_RE = re.compile(r"_dac(\d+)$", re.IGNORECASE)

# Suffix pattern: _adc<N>  or  _dac<N>
_ADC_SUFFIX_RE = re.compile(r"_adc(\d+)$", re.IGNORECASE)


# ─────────────────────────────────────────────────────────────────────────────
# Pure Data Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_pd_params(pd_file: Path) -> tuple:
    bounds: dict = {}
    dac_labels: dict = {}
    try:
        text = pd_file.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"[pd]    WARNING: cannot read {pd_file}: {e}")
        return bounds, dac_labels

    for m in _PD_PARAM_RE.finditer(text):
        name    = m.group(1)
        lo      = float(m.group(2)) if m.group(2) else 0.0
        hi      = float(m.group(3)) if m.group(3) else 1.0
        default = float(m.group(4)) if m.group(4) else 0.5
        bounds[name] = (lo, hi, default)
        print(f"[pd]    {name:30s} min={lo}  max={hi}  default={default}")

    mapped_dacs_by_core: dict = {}
    for m in _PD_SEND_RE.finditer(text):
        send_name = m.group(1)
        dac_match = _DAC_SUFFIX_RE.search(send_name)
        if dac_match:
            dac_idx  = int(dac_match.group(1))
            core     = send_name[:dac_match.start()]
            if dac_idx in mapped_dacs_by_core:
                print(f"[pd]    WARNING: dac~ {dac_idx} claimed by both '{mapped_dacs_by_core[dac_idx]}' and '{core}' — using '{core}'")
            mapped_dacs_by_core[dac_idx] = core
            dac_labels[core] = dac_idx
            print(f"[pd]    [s] '{send_name}' -> output label '{core}' -> dac~ {dac_idx}")

    if not bounds:
        print(f"[pd]    WARNING: no @hv_param declarations found in {pd_file.name}")
    return bounds, dac_labels


def apply_pd_bounds(params: List[HvParam], pd_bounds: dict) -> None:
    for p in params:
        match = pd_bounds.get(p.name) or pd_bounds.get(p.safe_name)
        if match is None:
            for k, v in pd_bounds.items():
                if k.lower() == p.name.lower() or k.lower() == p.safe_name.lower():
                    match = v
                    break
        if match:
            p.minimum, p.maximum, p.default = match
        else:
            print(f"[pd]    WARNING: no @hv_param found for '{p.name}' "
                  f"— keeping fallback bounds ({p.minimum}, {p.maximum}, {p.default})")


def parse_smart_name(param: HvParam) -> None:
    name = param.name
    matched_prefix = ""
    for pfx in _UI_PREFIXES:
        if name.startswith(pfx + "_"):
            matched_prefix = pfx
            break
    if not matched_prefix:
        return

    remainder = name[len(matched_prefix) + 1:]
    adc_match = _ADC_SUFFIX_RE.search(remainder)
    adc_num = 0
    if adc_match:
        adc_num = int(adc_match.group(1))
        remainder = remainder[:adc_match.start()]

    core = remainder
    if not core:
        print(f"[smart] WARNING: '{param.name}' has empty core name after prefix strip — treating as plain param")
        return

    param.ui_type   = matched_prefix
    param.core_name = core
    param.adc_map   = adc_num
    param.enum_label = sanitize_identifier(core).upper()
    print(f"[smart] '{param.name}' -> ui={matched_prefix:8s}  core={core:12s}"
          f"  adc_map={adc_num}  enum={param.enum_label}")


def apply_smart_names(params: List[HvParam]) -> bool:
    for p in params:
        parse_smart_name(p)
    return any(p.ui_type for p in params)


# ─────────────────────────────────────────────────────────────────────────────
# hvcc Parsing
# ─────────────────────────────────────────────────────────────────────────────

def find_heavy_header(hvcc_dir: Path) -> Optional[Path]:
    candidates = sorted(hvcc_dir.rglob("Heavy_*.hpp"))
    if not candidates:
        candidates = sorted(hvcc_dir.rglob("Heavy_*.h"))
    if not candidates:
        return None
    for c in candidates:
        if c.parent.name in ("c", "src", "source", "cpp"):
            return c
    return candidates[0]


def find_hvcc_json(hvcc_dir: Path) -> Optional[Path]:
    for name in ("metadata.json", "patch.json", "hvcc.json"):
        p = hvcc_dir / name
        if p.exists():
            return p
    for p in hvcc_dir.rglob("*.json"):
        try:
            data = json.loads(p.read_text())
            if "parameters" in data and isinstance(data["parameters"], dict):
                return p
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _make_param(name: str, hash_str: str,
                minimum: float = 0.0, maximum: float = 1.0,
                default: float = 0.5, direction: str = "in") -> HvParam:
    return HvParam(
        name=name,
        safe_name=sanitize_identifier(name),
        hash_str=hash_str,
        minimum=minimum,
        maximum=maximum,
        default=default,
        direction=direction,
    )


def parse_from_json(json_path: Path) -> Tuple[List[HvParam], int, int]:
    data = json.loads(json_path.read_text())
    params: List[HvParam] = []
    raw = data.get("parameters", {})
    for direction in ("in", "out"):
        for p in raw.get(direction, []):
            attrs = p.get("attributes", p.get("attr", {}))
            params.append(_make_param(
                name=p["name"],
                hash_str=str(p.get("hash", "0x0")),
                minimum=float(attrs.get("min", attrs.get("minimum", 0.0))),
                maximum=float(attrs.get("max", attrs.get("maximum", 1.0))),
                default=float(attrs.get("default", attrs.get("defaultValue", 0.5))),
                direction=direction,
            ))
    sig = data.get("signal", data.get("io", {}))
    n_in  = int(sig.get("numInputChannels",  sig.get("inputs",  2)))
    n_out = int(sig.get("numOutputChannels", sig.get("outputs", 2)))
    return params, n_in, n_out


def parse_from_header(header_path: Path) -> Tuple[List[HvParam], int, int]:
    text = header_path.read_text(errors="replace")
    params: List[HvParam] = []
    seen: set = set()

    def add(raw_name: str, hash_str: str, direction: str = "in") -> None:
        key = raw_name.lower()
        if key not in seen:
            seen.add(key)
            params.append(_make_param(name=key, hash_str=hash_str, direction=direction))

    for m in re.finditer(r"#define\s+HV_\w+_(?:PARAM_)?HASH_(\w+)\s+(0x[0-9A-Fa-f]+)", text, re.IGNORECASE):
        add(m.group(1), m.group(2))

    if not params:
        for m in re.finditer(r"#define\s+HV_HASH_(\w+)\s+(0x[0-9A-Fa-f]+)", text, re.IGNORECASE):
            add(m.group(1), m.group(2))

    if not params:
        for m in re.finditer(r"HASH_(\w+)\s*=\s*(0x[0-9A-Fa-f]+)", text):
            add(m.group(1), m.group(2))

    if not params:
        for m in re.finditer(r'"(\w+)"\s*,\s*(0x[0-9A-Fa-f]+)', text):
            add(m.group(1), m.group(2))

    if not params:
        for m in re.finditer(r"(\w+)\s*=\s*(0x[0-9A-Fa-f]+),\s*//\s*(\w+)", text):
            direction = "in"
            if "out" in m.group(1).lower():
                direction = "out"
            add(m.group(3), m.group(2), direction)

    n_in, n_out = 2, 2
    match_in = re.search(r"getNumInputChannels\s*\(\s*\)[^{]*\{\s*return\s*(\d+)", text)
    if match_in:
        n_in = int(match_in.group(1))
    match_out = re.search(r"getNumOutputChannels\s*\(\s*\)[^{]*\{\s*return\s*(\d+)", text)
    if match_out:
        n_out = int(match_out.group(1))

    return params, n_in, n_out


def detect_heavy_api(header_path: Path) -> HeavyApi:
    text = header_path.read_text(errors="replace")
    api = HeavyApi()
    if re.search(r"process\s*\(\s*const\s+float\s*\*\s*const\s*\*", text):
        api.process_sig = "const_ptr_ptr"
    if "sendFloatToReceiver" in text:
        api.send_func = "sendFloat"
    elif "sendMessageToReceiver" in text:
        api.send_func = "sendMessage"
    return api


def gather_patch_info(hvcc_dir: Path, module_name: str,
                      force_process_sig: Optional[str],
                      force_send_func: Optional[str]) -> PatchInfo:
    header = find_heavy_header(hvcc_dir)
    if header is None:
        sys.exit(
            f"ERROR: No Heavy_*.h found under {hvcc_dir}\n"
            f"       Run hvcc with -g c and point --hvcc-dir at the output folder."
        )

    patch_name = re.sub(r"^Heavy_", "", header.stem)
    class_name = f"Heavy_{patch_name}"

    json_path = find_hvcc_json(hvcc_dir)
    if json_path:
        print(f"[parse] JSON metadata  : {json_path.relative_to(hvcc_dir)}")
        params, n_in, n_out = parse_from_json(json_path)
    else:
        print(f"[parse] No JSON found — parsing header: {header.name}")
        print(f"        NOTE: header parsing is fragile. If params look wrong, "
              f"check {header.name} and add a pattern to parse_from_header().")
        params, n_in, n_out = parse_from_header(header)

    api = detect_heavy_api(header)
    if force_process_sig:
        api.process_sig = force_process_sig
        print(f"[api]   process sig forced to: {force_process_sig}")
    if force_send_func:
        api.send_func = force_send_func
        print(f"[api]   send func forced to: {force_send_func}")

    deduplicate_safe_names(params)

    print(f"[parse] Patch class : {class_name}")
    print(f"[parse] Header      : {header.name}")
    print(f"[parse] Audio I/O   : {n_in} in / {n_out} out")
    print(f"[parse] Parameters  : {len(params)}  "
          f"({[p.name for p in params] or 'none'})")
    print(f"[api]   process sig : {api.process_sig}")
    print(f"[api]   send func   : {api.send_func}")

    return PatchInfo(
        name=module_name,
        class_name=class_name,
        header_file=header.name,
        num_input_channels=n_in,
        num_output_channels=n_out,
        params=params,
        api=api,
        stereo_in=False,
        stereo_out=False,
    )
