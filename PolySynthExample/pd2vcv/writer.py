import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional

from pd2vcv.models import CustomWidgets
from pd2vcv.parser import gather_patch_info, apply_pd_bounds, parse_pd_params, apply_smart_names
from pd2vcv.layout import run_layout, detect_svg_panel_hp, apply_layout_overrides, HP_MM
from pd2vcv.codegen import generate_all

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate VCV Rack 2 C++ wrapper from an hvcc-compiled PD patch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--hvcc-dir",    required=True,
                    help="Path to the hvcc output directory (contains Heavy_*.h)")
    ap.add_argument("--module-name", required=True,
                    help="CamelCase module name  e.g. MyPatch")
    ap.add_argument("--plugin-slug", default="MyPlugin",
                    help="Alphanumeric plugin slug (default: MyPlugin)")
    ap.add_argument("--plugin-name", default=None,
                    help="Human-readable plugin name (defaults to --plugin-slug)")
    ap.add_argument("--out-dir",     default=".",
                    help="Output directory (default: current dir)")
    ap.add_argument("--hvcc-src",    default="hvcc/c",
                    help="Relative path from project root to hvcc C sources (default: hvcc/c)")
    ap.add_argument("--block-size",  type=int, default=64,
                    help="Heavy processing block size in samples (default: 64)")
    ap.add_argument("--pd-file", default=None,
                    help="Path to the original .pd file. When provided, @hv_param "
                         "annotations are parsed to extract real min/max/default "
                         "bounds for each parameter knob.")
    ap.add_argument("--manufacturer", default="MyBrand",
                    help="Brand/manufacturer name written into plugin.json (default: MyBrand)")
    ap.add_argument("--version",      default="2.0.0",
                    help="Plugin version string in plugin.json (default: 2.0.0 — must start with 2. for Rack 2)")
    ap.add_argument("--author",       default=None,
                    help="Author name for plugin.json (defaults to --manufacturer)")

    ap.add_argument("--license",      default="GPL-3.0",
                    help="License identifier in plugin.json (default: GPL-3.0)")
    ap.add_argument("--force-process-sig",
                    choices=["float_ptr_ptr", "const_ptr_ptr"],
                    help="Override auto-detected process() pointer signature")
    ap.add_argument("--force-send-func",
                    choices=["sendFloat", "sendMessage"],
                    help="Override auto-detected Heavy send function variant")
    ap.add_argument("--ui-text",     choices=["yes", "no"], default="yes",
                    help="Generate UI text labels in C++ (default: yes)")
    ap.add_argument("--polyphony",   choices=["yes", "no", "y", "n"], default="no",
                    help="Generate 16-voice polyphonic support (default: no)")
    ap.add_argument("--dump-layout", action="store_true",
                    help="Print auto-layout as JSON to stdout and exit without writing files. "
                         "Used by build.py for interactive placement.")
    ap.add_argument("--layout-file", default=None,
                    help="Path to a .pd2vcv_layout.json file with saved position overrides.")
    ap.add_argument("--res-dir",     default="res",
                    help="Path to the SVG resource folder (default: res/ relative to script). "
                         "Always scanned for custom widget and panel SVGs.")
    args = ap.parse_args()

    hvcc_dir    = Path(args.hvcc_dir).expanduser().resolve()
    out_dir     = Path(args.out_dir).expanduser().resolve()
    plugin_name = args.plugin_name or args.plugin_slug

    if not hvcc_dir.is_dir():
        sys.exit(f"ERROR: --hvcc-dir does not exist: {hvcc_dir}")

    src_dir = out_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "res").mkdir(exist_ok=True)

    info = gather_patch_info(
        hvcc_dir, args.module_name,
        args.force_process_sig, args.force_send_func,
    )

    # ── Overlay real bounds from the PD file if provided ─────────────────────
    dac_labels: dict = {}  # populated from [s name_dacN @hv_param] in PD file
    if args.pd_file:
        pd_path = Path(args.pd_file).expanduser().resolve()
        if not pd_path.is_file():
            print(f"[pd]    WARNING: --pd-file not found: {pd_path}")
        else:
            print(f"[pd]    Parsing: {pd_path}")
            pd_bounds, dac_labels = parse_pd_params(pd_path)
            apply_pd_bounds(info.params, pd_bounds)
    else:
        print("[pd]    No --pd-file supplied — using fallback bounds (0, 1, 0.5).")
        print("        Pass --pd-file path/to/patch.pd for real min/max/default.")

    has_smart = apply_smart_names(info.params)
    panel_hp, components = run_layout(info, dac_labels, has_smart)

    print(f"[layout] {panel_hp} HP  ({panel_hp * HP_MM:.1f} mm)  "
          f"— {len(components)} components")

    # ── Scan res/ folder (always active) ────────────────────────────────────────
    res_dir = Path(args.res_dir).expanduser().resolve()
    if not res_dir.is_absolute():
        res_dir = (Path(__file__).parent / args.res_dir).resolve()
    custom_widgets: Optional[CustomWidgets] = None
    if res_dir.is_dir():
        custom_widgets = CustomWidgets.from_dir(res_dir)
        # Auto-detect panel HP from custom panel SVG
        custom_panel_path = res_dir / "panel.svg"
        if custom_widgets.panel and custom_panel_path.exists():
            panel_hp = detect_svg_panel_hp(custom_panel_path)
            print(f"[layout] Panel HP overridden by custom SVG: {panel_hp} HP")
    else:
        print(f"[res]   res/ folder not found at {res_dir} — using Rack built-in widgets")

    # ── Apply layout overrides if provided ───────────────────────────────────
    if args.layout_file:
        layout_path = Path(args.layout_file).expanduser().resolve()
        if layout_path.exists():
            try:
                layout_data = json.loads(layout_path.read_text())
                components = apply_layout_overrides(components, layout_data)
            except (json.JSONDecodeError, OSError) as e:
                print(f"[layout] WARNING: Could not load layout file: {e}")
        else:
            print(f"[layout] WARNING: --layout-file not found: {layout_path}")

    # ── Override stereo detection from jack types ─────────────────────────────
    has_inl  = any(c.port_type == "inl" for c in components)
    has_inr  = any(c.port_type == "inr" for c in components)
    has_outl = any(c.port_type == "outl" for c in components)
    has_outr = any(c.port_type == "outr" for c in components)
    if has_inl or has_inr:
        info.stereo_in = True
        print("[layout] Stereo input detected from jack type overrides")
    if has_outl or has_outr:
        info.stereo_out = True
        print("[layout] Stereo output detected from jack type overrides")

    # ── Dump layout as JSON and exit (used by build.py for interactive placement)
    if args.dump_layout:
        layout_dump = {
            "version": 2,
            "panel_hp": panel_hp,
            "components": [
                {
                    "label": c.label,
                    "kind": c.kind,
                    "knob_type": c.knob_type,
                    "x": round(c.x, 2),
                    "y": round(c.y, 2),
                    "index": c.index,
                    "ui_label": c.ui_label,
                    "port_type": c.port_type,
                }
                for c in components
            ],
        }
        print(json.dumps(layout_dump, indent=2))
        return

    # ── Generate files ────────────────────────────────────────────────────────
    
    # Panel SVGs: use custom panel.svg if present
    if custom_widgets and custom_widgets.panel and res_dir:
        shutil.copy2(res_dir / "panel.svg", out_dir / "res" / f"{args.module_name}.svg")
        print(f"[res]   Copied panel.svg -> res/{args.module_name}.svg")
        if custom_widgets.panel_dark:
            shutil.copy2(res_dir / "panel-dark.svg", out_dir / "res" / f"{args.module_name}-dark.svg")
            print(f"[res]   Copied panel-dark.svg -> res/{args.module_name}-dark.svg")
        else:
            shutil.copy2(res_dir / "panel.svg", out_dir / "res" / f"{args.module_name}-dark.svg")
            print(f"[res]   No dark panel — using panel.svg for both themes")

    gen_files = generate_all(
        info=info,
        panel_hp=panel_hp,
        components=components,
        block_size=args.block_size,
        ui_text=args.ui_text,
        polyphony=(args.polyphony.lower() in ("yes", "y")),
        hvcc_src_rel=args.hvcc_src,
        hvcc_dir=hvcc_dir,
        custom_widgets=custom_widgets
    )
    
    files = {}
    for k, v in gen_files.items():
        files[out_dir / k] = v


    # Copy widget SVGs from res/ to output res/ folder
    if custom_widgets and res_dir and res_dir.is_dir():
        widget_svgs = [
            "knob_large.svg", "knob_small.svg", "knob_trim.svg", "knob_default.svg",
            "button.svg", "button_pressed.svg",
            "trigger.svg", "trigger_pressed.svg",
            "switch_on.svg", "switch_off.svg",
            "port_cv_in.svg", "port_cv_out.svg",
            "port_audio_in.svg", "port_audio_out.svg",
            "port_in.svg", "port_out.svg",
        ]
        for svg_name in widget_svgs:
            svg_src = res_dir / svg_name
            if svg_src.exists():
                shutil.copy2(svg_src, out_dir / "res" / svg_name)
                print(f"[res]   Copied {svg_name} -> res/{svg_name}")

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        print(f"[wrote]  {path.relative_to(out_dir)}")

    # ── plugin.json ───────────────────────────────────────────────────────────
    plugin_json_data = {
        "slug":    args.plugin_slug,
        "name":    plugin_name,
        "version": args.version,
        "author":  args.author or args.manufacturer,
        "license": args.license,
        "brand":   args.manufacturer,
        "modules": [{"slug": args.module_name, "name": args.module_name}],
    }
    plugin_json_path = out_dir / "plugin.json"
    plugin_json_path.write_text(
        json.dumps(plugin_json_data, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[wrote]  plugin.json")


    print()
    print("─" * 64)
    print("Next steps")
    print("─" * 64)
    print(f"  1. Copy hvcc C output (Heavy_*.cpp, Heavy_*.h)")
    print(f"       -> ./{args.hvcc_src}/")
    print()
    print(f"  2. Add Heavy RUNTIME headers to Makefile FLAGS.")
    print(f"     Find them inside the hvcc Python package:")
    print(f"       <venv>/lib/pythonX.Y/site-packages/hvcc/generators/ir2c/static/")
    print()
    print(f"  3. export RACK_DIR=/path/to/Rack-SDK && make")
    print("─" * 64)


