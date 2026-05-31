#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
# build.py  —  pd2vcv master build script
# Usage: python3 build.py [options]
# Run `python3 build.py --help` to see available overrides.
# ─────────────────────────────────────────────────────────────────────────────
import os
import sys
import json
import shutil
import platform
import argparse
import subprocess
from pathlib import Path

# ── Config block (edit these, same as before) ─────────────────────────────────
PD_FILE      = "./pd/mypatch.pd"
MODULE_NAME  = "MyPatch"
PLUGIN_SLUG  = "MyPlugin"
MANUFACTURER = "YourName"
AUTHOR       = "YourName"
VERSION      = "2.0.0"
LICENSE      = "GPL-3.0"
BLOCK_SIZE   = 64
UI_TEXT      = "yes"
POLYPHONY    = "no"
CUSTOM_LAYOUT = "no"
CUSTOM_PORTS  = "yes"
# ─────────────────────────────────────────────────────────────────────────────

def prompt_with_default(prompt_text, default_value):
    val = input(f"{prompt_text} [{default_value}]: ").strip()
    return val if val else default_value

def auto_detect_pd_file(default_file):
    pd_dir = Path("pd")
    if pd_dir.exists() and pd_dir.is_dir():
        pd_files = list(pd_dir.glob("*.pd"))
        if len(pd_files) == 1:
            return str(pd_files[0])
    return default_file


def auto_detect_hvcc_dir(default_dir):
    if Path("output_directory").exists() and Path("output_directory").is_dir():
        return "output_directory"
    if Path("c").exists() and Path("c").is_dir():
        return "c"
    return default_dir

def _interactive_layout(base_cmd, cache_path, script_dir, prompt_positions=True, prompt_ports=True):
    """
    Two-pass layout: run generator with --dump-layout to get auto positions,
    present them to the user for override in two steps, and save to cache file.
    """
    _VALID_PORT_TYPES = {"cvi", "cvo", "audioi", "audioo", "inl", "inr", "outl", "outr"}

    dump_cmd = base_cmd + ["--dump-layout"]
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Generating auto-layout for interactive placement...")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        result = subprocess.run(dump_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Layout dump failed (exit {e.returncode})")
        print(f"  stderr: {e.stderr}")
        sys.exit(1)

    # Find the JSON block in stdout (may be mixed with log lines)
    json_str = ""
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("{"):
            json_start = result.stdout.index(line)
            json_str = result.stdout[json_start:]
            break

    if not json_str:
        print("  ERROR: Could not find layout JSON in generator output.")
        print(f"  stdout was: {result.stdout[:500]}")
        sys.exit(1)

    try:
        layout_data = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"  ERROR: Invalid layout JSON: {e}")
        sys.exit(1)

    components = layout_data.get("components", [])
    panel_hp = layout_data.get("panel_hp", 10)

    controls = [c for c in components if c["kind"] == "param"]
    jacks    = [c for c in components if c["kind"] in ("input", "output")]

    print(f"\n  Panel: {panel_hp} HP  ({panel_hp * 5.08:.1f} mm)")
    print(f"  {len(controls)} control(s), {len(jacks)} jack(s) detected.")

    overrides = {}

    # ── STEP 1: Controls ──────────────────────────────────────────────────────
    if prompt_positions:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  STEP 1: Control Placement (Knobs, Buttons, Switches)")
        print("  Press [Enter] to keep auto-position, or type: x, y")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        for c in controls:
            kt = c.get("knob_type", "").replace("Round", "").replace("Black", "").replace("VCV", "")
            prompt = f"  {c['label']:20s} ({kt:15s}) [{c['x']:.1f}, {c['y']:.1f}]: "
            while True:
                val = input(prompt).strip()
                if not val:
                    break
                try:
                    parts = [float(v.strip()) for v in val.split(",")]
                    if len(parts) >= 2:
                        overrides[c["label"]] = {"x": parts[0], "y": parts[1]}
                        break
                    else:
                        print(f"    ⚠ Needs two numbers separated by comma (e.g. 20, 45). Try again or press Enter to skip.")
                except ValueError:
                    print(f"    ⚠ Invalid format '{val}'. Try again or press Enter to skip.")

    # ── STEP 2: Jacks ──────────────────────────────────────────────────────
    if prompt_ports or prompt_positions:
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if prompt_positions and prompt_ports:
            print("  STEP 2: Jack Placement & Type")
        elif prompt_positions and not prompt_ports:
            print("  STEP 2: Jack Placement")
        else:
            print("  Jack Type Configuration")
            
        if prompt_ports:
            print("  Types:  cvi    = CV Input       cvo    = CV Output")
            print("          audioi = Audio Input     audioo = Audio Output")
            print("          inl    = Audio In Left   inr    = Audio In Right")
            print("          outl   = Audio Out Left  outr   = Audio Out Right")
        
        print("  Press [Enter] to keep defaults.")
        if prompt_ports and prompt_positions:
            print("  Type only (keep position): cvi")
            print("  Position only:             20, 45")
            print("  Both:                      cvi 20, 45")
        elif prompt_ports:
            print("  Type only: cvi")
        elif prompt_positions:
            print("  Position only: 20, 45")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    for c in jacks:
        direction = "Input Jack" if c["kind"] == "input" else "Output Jack"
        prompt = f"  {c['label']:20s} ({direction:12s}) [{c['x']:.1f}, {c['y']:.1f}]: "
        while True:
            val = input(prompt).strip()
            if not val:
                break

            # Parse: could be "cvi", "20, 45", or "cvi 20, 45"
            tokens = val.split()
            first_token = tokens[0].lower()

            if first_token in _VALID_PORT_TYPES and prompt_ports:
                # First token is a type
                rest = val[len(first_token):].strip()
                if rest and prompt_positions:
                    # Type + position: "cvi 20, 45"
                    try:
                        parts = [float(v.strip()) for v in rest.split(",")]
                        if len(parts) >= 2:
                            overrides[c["label"]] = {"x": parts[0], "y": parts[1], "port_type": first_token}
                            break
                        else:
                            print(f"    ⚠ Needs two numbers separated by comma (e.g. 20, 45). Try again or press Enter to skip.")
                    except ValueError:
                        print(f"    ⚠ Invalid coords '{rest}'. Try again or press Enter to skip.")
                else:
                    # Type only: "cvi"
                    overrides[c["label"]] = {"port_type": first_token}
                    if rest and not prompt_positions:
                        print(f"    ⚠ Positions ignored (layout disabled). Type set to {first_token}")
                    break
            elif prompt_positions:
                # No type, just position: "20, 45"
                try:
                    parts = [float(v.strip()) for v in val.split(",")]
                    if len(parts) >= 2:
                        overrides[c["label"]] = {"x": parts[0], "y": parts[1]}
                        break
                    else:
                        print(f"    ⚠ Needs two numbers separated by comma (e.g. 20, 45). Try again or press Enter to skip.")
                except ValueError:
                    print(f"    ⚠ Invalid input '{val}'. Try again or press Enter to skip.")
            else:
                print(f"    ⚠ Invalid type '{val}'. Try again or press Enter to skip.")

    # Save to cache
    cache_data = {
        "version": 2,
        "panel_hp": panel_hp,
        "positions": overrides,
    }
    cache_path.write_text(json.dumps(cache_data, indent=2) + "\n", encoding="utf-8")
    print(f"\n  ✓ Saved {len(overrides)} override(s) to {cache_path.name}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def main():
    # Parse CLI arguments to override config
    parser = argparse.ArgumentParser(description="pd2vcv Master Build Script")
    parser.add_argument("--hvcc-dir", default=None, help="Path to hvcc generated output folder")
    parser.add_argument("--pd-file", default=None, help="Path to original Pure Data patch")
    parser.add_argument("--module-name", default=None, help="CamelCase module name")
    parser.add_argument("--plugin-slug", default=None, help="Unique plugin ID")
    parser.add_argument("--manufacturer", default=None, help="Manufacturer name")
    parser.add_argument("--author", default=None, help="Author name")
    parser.add_argument("--version", default=None, help="Plugin version")
    parser.add_argument("--license", default=None, help="Plugin license")
    parser.add_argument("--block-size", type=int, default=BLOCK_SIZE, 
                        help="Processing block size (default 64). Lower values (1-4) give less latency, better for feedback loops, but higher CPU.")
    parser.add_argument("--ui-text", default=UI_TEXT, choices=["yes", "no", "y", "n"],
                        help="Generate UI text labels in C++ (yes/no).")
    parser.add_argument("--polyphony", default=POLYPHONY, choices=["yes", "no", "y", "n"],
                        help="Enable 16-voice polyphony (yes/no).")
    parser.add_argument("--custom-layout", default=CUSTOM_LAYOUT, choices=["yes", "no", "y", "n"],
                        help="Enable interactive component placement (yes/no).")
    parser.add_argument("--custom-ports", default=CUSTOM_PORTS, choices=["yes", "no", "y", "n"],
                        help="Enable interactive jack type configuration (yes/no).")
    parser.add_argument("--non-interactive", action="store_true", help="Skip interactive prompts and use defaults/CLI flags")
    args = parser.parse_args()

    # Interactive prompts
    pd_file = args.pd_file
    module_name = args.module_name
    plugin_slug = args.plugin_slug
    manufacturer = args.manufacturer
    author = args.author
    version = args.version
    license_str = args.license

    if not args.non_interactive:
        print("─────────────────────────────────────────────────────────────────────────────")
        print("  pd2vcv Configuration")
        print("  Press Enter to accept the default values.")
        print("─────────────────────────────────────────────────────────────────────────────")
        if not args.hvcc_dir:
            auto_hvcc = auto_detect_hvcc_dir("c")
            print("\n  [HVCC_DIR]: The folder containing hvcc generated output (e.g. 'c' or 'output_directory').")
            args.hvcc_dir = prompt_with_default("  HVCC Output Directory", auto_hvcc)
        if not pd_file:
            auto_pd = auto_detect_pd_file(PD_FILE)
            print("\n  [PD_FILE]: The Pure Data patch file to compile.")
            pd_file = prompt_with_default("  Pure Data patch file", auto_pd)
        if not module_name:
            print("\n  [MODULE_NAME]: CamelCase name of your module (e.g. MySynth). No spaces.")
            module_name = prompt_with_default("  Module Name", MODULE_NAME)
        if not plugin_slug:
            print("\n  [PLUGIN_SLUG]: Unique alphanumeric ID for the plugin (e.g. MySynthPlugin).")
            plugin_slug = prompt_with_default("  Plugin Slug", PLUGIN_SLUG)
        if not manufacturer:
            print("\n  [MANUFACTURER]: Your brand name, shows in the VCV Rack browser.")
            manufacturer = prompt_with_default("  Manufacturer", MANUFACTURER)
        if not author:
            print("\n  [AUTHOR]: Your name, added to plugin.json.")
            author = prompt_with_default("  Author", AUTHOR)
        if not version:
            print("\n  [VERSION]: Plugin version. Must start with '2.' for VCV Rack 2.")
            version = prompt_with_default("  Version", VERSION)
        if not license_str:
            print("\n  [LICENSE]: Software license (e.g. GPL-3.0, MIT, etc).")
            license_str = prompt_with_default("  License", LICENSE)
        if args.block_size == BLOCK_SIZE:
            print("\n  [BLOCK_SIZE]: DSP processing block size.")
            print("  - 64 is the recommended default for stable CPU.")
            print("  - 1 provides minimal latency (1 sample), great for feedback loops, but uses much more CPU.")
            val = prompt_with_default("  Block Size", str(BLOCK_SIZE))
            args.block_size = int(val)
        if args.ui_text == UI_TEXT:
            print("\n  [UI_TEXT]: Generate C++ text labels for your panel? (yes / no)")
            print("  - 'yes' automatically draws the module name and port labels in C++.")
            print("  - 'no' keeps the panel blank so you can bake custom text into your SVG later.")
            args.ui_text = prompt_with_default("  UI Text", UI_TEXT)
        if args.polyphony == POLYPHONY:
            print("\n  [POLYPHONY]: Enable 16-voice polyphony? (yes / no)")
            print("  - 'yes' supports up to 16 voices via polyphonic cables. Treats all I/O as polyphonic. Do not use stereo I/O with polyphony.")
            print("  - 'no' generates standard monophonic/stereo code (uses less CPU).")
            args.polyphony = prompt_with_default("  Polyphony", POLYPHONY)
        if args.custom_layout == CUSTOM_LAYOUT:
            print("\n  [CUSTOM_LAYOUT]: Enable interactive component placement? (yes / no)")
            print("  - 'yes' lets you manually position each knob, jack, and button.")
            print("  - 'no' uses the automatic layout engine (recommended for most users).")
            args.custom_layout = prompt_with_default("  Custom Layout", CUSTOM_LAYOUT)
        if args.custom_ports == CUSTOM_PORTS:
            print("\n  [CUSTOM_PORTS]: Customize jack types (audio/cv/stereo)? (yes / no)")
            print("  - 'yes' lets you tag inputs/outputs for correct CV/Audio/Stereo normalization.")
            print("  - 'no' uses generic port types for everything.")
            args.custom_ports = prompt_with_default("  Custom Ports", CUSTOM_PORTS)
        print("─────────────────────────────────────────────────────────────────────────────\n")
    else:
        pd_file = pd_file or PD_FILE
        module_name = module_name or MODULE_NAME
        plugin_slug = plugin_slug or PLUGIN_SLUG
        manufacturer = manufacturer or MANUFACTURER
        author = author or AUTHOR
        version = version or VERSION
        license_str = license_str or LICENSE

    SCRIPT_DIR = Path(__file__).parent.resolve()
    HVCC_DIR = Path(args.hvcc_dir).resolve() if args.hvcc_dir else (SCRIPT_DIR / "c")
    OUT_DIR = SCRIPT_DIR / "rack_plugin"
    HVCC_SRC = "hvcc/c"

    # Rack SDK — absolute path required by the Makefile
    RACK_DIR = SCRIPT_DIR / "Rack-SDK"
    os.environ["RACK_DIR"] = str(RACK_DIR)

    # Auto-detect OS and install destination
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Linux":
        if "aarch64" in machine or "arm" in machine:
            rack_platform = "lin-arm64"
        else:
            rack_platform = "lin-x64"
        install_base = Path.home() / ".local" / "share" / "Rack2" / f"plugins-{rack_platform}"
    elif system == "Darwin":
        if "arm64" in machine:
            rack_platform = "mac-arm64"
        else:
            rack_platform = "mac-x64"
        install_base = Path.home() / "Documents" / "Rack2" / f"plugins-{rack_platform}"
    elif system == "Windows" or "MINGW" in system or "MSYS" in system:
        rack_platform = "win-x64"
        install_base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Rack2" / f"plugins-{rack_platform}"
    else:
        rack_platform = "lin-x64"
        install_base = Path.home() / ".local" / "share" / "Rack2" / f"plugins-{rack_platform}"

    install_dir = install_base / plugin_slug
    
    # SAFETY CHECKS
    if not plugin_slug or plugin_slug.strip() == "" or ".." in plugin_slug:
        print(f"ERROR: Invalid plugin slug '{plugin_slug}'. Aborting to prevent accidental deletion.")
        sys.exit(1)
        
    if install_dir.resolve() == install_base.resolve() or install_dir.resolve() == install_base.parent.resolve():
        print(f"ERROR: Install dir resolved to base directory '{install_dir}'. Aborting.")
        sys.exit(1)
        
    if OUT_DIR.resolve() == SCRIPT_DIR.resolve() or OUT_DIR.resolve() == Path("/").resolve():
        print(f"ERROR: OUT_DIR resolved dangerously to '{OUT_DIR}'. Aborting.")
        sys.exit(1)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  hvcc2rack  —  generating plugin files")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Clean output directory
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run the generator
    generator_cmd = [
        sys.executable, str(SCRIPT_DIR / "hvcc2rack.py"),
        "--hvcc-dir", str(HVCC_DIR),
        "--module-name", module_name,
        "--plugin-slug", plugin_slug,
        "--out-dir", str(OUT_DIR),
        "--pd-file", pd_file,
        "--manufacturer", manufacturer,
        "--author", author,
        "--version", version,
        "--license", license_str,
        "--ui-text", args.ui_text,
        "--polyphony", args.polyphony,
        "--block-size", str(args.block_size)
    ]

    # Always pass res/ folder
    generator_cmd.extend(["--res-dir", str(SCRIPT_DIR / "res")])

    # ── Custom Layout: two-pass generation ─────────────────────────────────────
    layout_cache_path = SCRIPT_DIR / ".pd2vcv_layout.json"
    use_custom_layout = args.custom_layout.lower() in ("yes", "y")
    use_custom_ports  = args.custom_ports.lower() in ("yes", "y")

    if use_custom_layout or use_custom_ports:
        # Check for cached layout
        if layout_cache_path.exists() and not args.non_interactive:
            print(f"\n  Found saved layout ({layout_cache_path.name}).")
            reuse = prompt_with_default("  Use saved layout/types?", "yes")
            if reuse.lower() in ("yes", "y"):
                generator_cmd.extend(["--layout-file", str(layout_cache_path)])
                print("  Using saved layout configurations.\n")
            else:
                # Re-enter interactive mode: dump layout, prompt, save
                _interactive_layout(generator_cmd, layout_cache_path, SCRIPT_DIR, prompt_positions=use_custom_layout, prompt_ports=use_custom_ports)
                generator_cmd.extend(["--layout-file", str(layout_cache_path)])
        elif not layout_cache_path.exists():
            # First time: dump layout, prompt, save
            _interactive_layout(generator_cmd, layout_cache_path, SCRIPT_DIR, prompt_positions=use_custom_layout, prompt_ports=use_custom_ports)
            generator_cmd.extend(["--layout-file", str(layout_cache_path)])
        else:
            # Non-interactive with cache: just use it
            generator_cmd.extend(["--layout-file", str(layout_cache_path)])

    print(f"Running generator: {' '.join(generator_cmd)}\n")
    try:
        subprocess.run(generator_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Generator failed with error code {e.returncode}")
        sys.exit(1)

    # Copy Heavy C sources
    print(f"\n  Copying Heavy C sources -> {OUT_DIR.name}/{HVCC_SRC}/")
    hvcc_dest = OUT_DIR / HVCC_SRC
    hvcc_dest.mkdir(parents=True, exist_ok=True)
    if not HVCC_DIR.exists():
        print(f"ERROR: {HVCC_DIR} does not exist. Did you export your patch from PlugData?")
        sys.exit(1)
        
    actual_c_dir = HVCC_DIR / "c" if (HVCC_DIR / "c").is_dir() else HVCC_DIR

    for item in actual_c_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, hvcc_dest)
        elif item.is_dir():
            shutil.copytree(item, hvcc_dest / item.name, dirs_exist_ok=True)

    # Build
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  make  (RACK_DIR={RACK_DIR})")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    try:
        subprocess.run(["make", "-C", str(OUT_DIR)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Make failed with error code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("ERROR: 'make' command not found. Ensure build tools are installed.")
        sys.exit(1)

    # Install
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Installing -> {install_dir}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    if install_dir.exists():
        shutil.rmtree(install_dir)
    (install_dir / "res").mkdir(parents=True, exist_ok=True)

    # Copy artifacts
    plugin_files = ["plugin.so", "plugin.dylib", "plugin.dll"]
    for pf in plugin_files:
        src_file = OUT_DIR / pf
        if src_file.exists():
            shutil.copy2(src_file, install_dir)
            
    json_src = OUT_DIR / "plugin.json"
    if json_src.exists():
        shutil.copy2(json_src, install_dir)

    # Copy SVG resources
    for res_file in (OUT_DIR / "res").glob("*.svg"):
        shutil.copy2(res_file, install_dir / "res")

    print("\n  ✓ Done. Restart VCV Rack 2 to load plugin.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

if __name__ == "__main__":
    main()
