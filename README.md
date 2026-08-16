# pd2vcv

Convert Pure Data patches to VCV Rack 2 plugins via hvcc.

```
.pd → hvcc → C code → build.py [parser → layout → codegen] → make → plugin.so
```

For ready-to-build examples and step-by-step setup instructions, see [pd2vcv-examples](https://gitlab.com/vlkgbr/pd2vcv-examples).

---

## Requirements

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.8+ | Runs the generator |
| hvcc | 0.16.0+ | Compiles `.pd` to C ([pip install hvcc](https://github.com/Wasted-Audio/hvcc)) |
| VCV Rack SDK | 2.x | Headers + build system ([download](https://vcvrack.com/downloads)) |
| gcc / g++ / make | — | C++ compilation |

Place the unzipped SDK as `Rack-SDK/` in your project root.

---

## Quick Start

```bash
python3 build.py
```

The interactive prompt walks you through everything. For scripted builds, see [CLI Reference](#cli-reference) below.

---

## Smart Naming Convention

Every parameter needs a `[receive]` with `@hv_param`:

```
[r paramName @hv_param <min> <max> <default>]
```

### Prefix table

Encode the **control type** and **column grouping** in the parameter name: `[prefix]_[core_name]`

| Prefix | Widget | Rack Type | Purpose |
|---|---|---|---|
| `base_` | Large knob | `RoundHugeBlackKnob` | Primary value (unipolar) |
| `attenv_` | Small knob | `RoundSmallBlackKnob` | Bipolar attenuverter (−1 → +1) |
| `atten_` | Trim pot | `Trimpot` | Unipolar attenuator (0 → 1) |
| `button_` | Button | `VCVButton` | Gate: 1.0 while held, 0.0 on release |
| `trigger_` | Button | `VCVButton` | Bang: sends 1.0 on press only, ignores release |
| `switch_` | Toggle | `CKSS` | Binary 0.0 / 1.0 |
| `menu_` | Dropdown | `CustomMenuWidget` | Integer selection. Prompts for entry labels during build. |
| `stepN_` | Stepped knob | `StepKnob` | Clicks into discrete values. N = step size. |

> **`attenv_` vs `atten_`:** Same parameter range logic, different physical widget. `attenv_` gives you a knob; `atten_` gives you a screwdriver-style trim pot.

> **`button_` vs `trigger_`:** `button_` sends 1.0 on press AND 0.0 on release (gate). `trigger_` sends 1.0 on press only (bang). Use `trigger_` with `[bang]` receivers to avoid double-firing.

> **`menu_`:** Item count is derived from `@hv_param` min/max. You assign labels interactively (e.g. Sine, Tri, Saw) or via `--menu MODE:Sine,Tri,Saw`.

> **`stepN_`:** `step1_octave @hv_param 1 5 1` → outputs exactly 1, 2, 3, 4, 5. `step3_` → outputs 1, 4, 7... The knob clicks securely into each position.

### Column grouping

Parameters sharing the same `[core_name]` stack vertically:

1. `base_` knob (top)
2. `attenv_` / `atten_` controls
3. `button_` / `switch_` / `menu_` / `stepN_` controls
4. Mapped `adc~` input (via `_adcN` suffix)
5. Mapped `dac~` output (via `[s core_dacN @hv_param]`)

**Example — filter with CV:**
```
[r base_cutoff_adc2 @hv_param 20 20000 2000]   ← large knob + adc~ 2 in CUTOFF column
[r attenv_cutoff    @hv_param -1 1 0]           ← small knob in same column
[s cutoff_dac1      @hv_param 0 1 0]            ← labels dac~ 1 output in same column
```

### Output jack labeling (`_dacN`)

Add `[s core_name_dacN @hv_param 0 1 0]` to place a labeled output jack in a column. The `@hv_param` values are ignored — the annotation only signals the generator. Audio still routes through `[dac~ N]` inside PD.

> **Compiler warning:** hvcc will print `This object has no inlet connections. It does nothing and will be removed.` — this is expected. Connect a dummy `[loadbang]` to suppress it.

### Stereo I/O

If `adc~ 1` and `adc~ 2` are both unmapped, they auto-promote to `IN_L` / `IN_R` with mono normalization. Same for `dac~ 1` / `dac~ 2` → `OUT_L` / `OUT_R`.

---

## Polyphony & Signal Levels

**Polyphony:** Answer `yes` during build to enable 16-voice polyphony. All I/O becomes polyphonic — mono cables broadcast to all voices, poly cables route per-voice. Don't mix stereo I/O with polyphony.

**Signal levels:** Voltages pass 1:1 between VCV Rack and PD. No hidden scaling. Audio ±5V, envelopes 0–10V, V/Oct = 1.0/octave. Hard-clamped at ±12V.

---

<details>
<summary><strong>CLI Reference</strong></summary>

```
python3 build.py [OPTIONS]
```

| Flag | Default | Description |
|---|---|---|
| `--hvcc-dir <path>` | auto-detect | Folder containing hvcc output (`c/` or `output_directory/`) |
| `--pd-file <path>` | — | Pure Data patch file |
| `--module-name <name>` | — | CamelCase module name (e.g. `MySynth`) |
| `--plugin-slug <slug>` | — | Unique alphanumeric plugin ID |
| `--manufacturer <name>` | — | Brand name for VCV browser |
| `--author <name>` | — | Author name for plugin.json |
| `--version <ver>` | `2.0.0` | Must start with `2.` |
| `--license <lic>` | `GPL-3.0` | Software license |
| `--block-size <int>` | `64` | DSP block size (1 = minimal latency) |
| `--ui-text <yes\|no>` | `yes` | Generate C++ text labels on panel |
| `--polyphony <yes\|no>` | `no` | Enable 16-voice polyphony |
| `--custom-layout <yes\|no>` | `no` | Interactive component placement |
| `--custom-ports <yes\|no>` | `yes` | Customize jack types |
| `--menu <string>` | — | Pre-fill menu entries (e.g. `MODE:Sine,Tri;LFO:A,B`) |
| `--non-interactive` | — | Skip all prompts, use defaults |

**Example:**
```bash
python3 build.py --pd-file pd/mypatch.pd --module-name MyPatch --polyphony yes --non-interactive
```

</details>

<details>
<summary><strong>Custom SVG Widgets</strong></summary>

Place SVGs in `res/` next to `build.py`. No CLI flags needed — detected automatically. Missing files fall back to Rack built-ins.

```
res/
├── panel.svg           ← Light theme panel (auto-detects width from SVG)
├── panel-dark.svg      ← Dark theme (optional, light reused if missing)
├── knob_large.svg      ← base_ knob
├── knob_small.svg      ← attenv_ knob
├── knob_trim.svg       ← atten_ trim pot
├── knob_default.svg    ← plain param knob
├── step_knob.svg       ← stepN_ knob
├── button.svg          ← button_ unpressed
├── button_pressed.svg  ← button_ pressed
├── trigger.svg         ← trigger_ unpressed
├── trigger_pressed.svg ← trigger_ pressed
├── switch_off.svg      ← switch_ off
├── switch_on.svg       ← switch_ on
├── port_cv_in.svg      ← CV input
├── port_cv_out.svg     ← CV output
├── port_audio_in.svg   ← Audio input
├── port_audio_out.svg  ← Audio output
├── port_in.svg         ← Generic input fallback
└── port_out.svg        ← Generic output fallback
```

**Knob SVG tip:** VCV Rack's `SvgKnob` rotates around center. Design with indicator at 12 o'clock.

</details>

<details>
<summary><strong>How It Works</strong></summary>

```
.pd → hvcc → C code → build.py → parser.py → layout.py → codegen.py → make → plugin.so
```

| Stage | File | What it does |
|---|---|---|
| Parse | `pd2vcv/parser.py` | Reads `@hv_param` declarations, extracts bounds, smart-name prefixes, `_adcN`/`_dacN` mappings |
| Model | `pd2vcv/models.py` | Data classes for parameters and patch info |
| Layout | `pd2vcv/layout.py` | Calculates panel width (HP), column positions, component coordinates |
| Codegen | `pd2vcv/codegen.py` | Generates `plugin.hpp`, `plugin.cpp`, `Module.cpp`, `panel.svg`, `Makefile`, `plugin.json` |
| Writer | `pd2vcv/writer.py` | Orchestrates the pipeline, handles CLI args, interactive layout, file output |
| Build | `build.py` | Interactive prompts, invokes writer, copies sources, runs `make`, installs plugin |

</details>

---

## Contributing

Pull requests, code reviews, and refactoring are welcome. The smart-naming convention and layout engine are stable; the codegen layer is where most improvements can happen.

---

## License

- **This tool** (pd2vcv): [0BSD](LICENSE.txt) — do whatever you want.
- **Generated plugins** link against the VCV Rack SDK — see [VCV's licensing terms](https://vcvrack.com/manual/PluginDevelopmentTutorial).
- **Heavy-generated C code** carries Enzien Audio / Wasted Audio attribution requirements — see file headers in hvcc output.

---

## Note on AI and Development

I am a musician and a Pure Data patcher, not a C++ or Python programmer. The concept, the smart-naming conventions, the UI layout engine rules, and the signal routing logic are entirely my own design.

To bring this idea to life, I relied heavily on AI coding assistants to write the actual Python and C++ syntax. My goal was simply to bridge a gap between PD and VCV Rack that I desperately wanted for my own music, and I used the tools available to me to build it.

Because I am not a native C++ developer, the codebase might have structural quirks. Pull requests, code reviews, and refactoring are incredibly welcome.

---

## Credits

- **Pure Data** by [Miller Puckette and the PD community](https://puredata.info/)
- **PlugData** by [Timothy Schoen and contributors](https://plugdata.org/)
- **hvcc** by [Wasted Audio](https://github.com/Wasted-Audio/hvcc)
- **VCV Rack SDK** © VCV LLC
