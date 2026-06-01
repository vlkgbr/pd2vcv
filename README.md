# pd2vcv

**Turn a Pure Data patch into a working VCV Rack 2 plugin — with one command.**

**Known Stable Environment**
> This generator was built and verified working with the following stack:
> - **OS:** Debian GNU/Linux 13 (Trixie) x86_64
> - **OS:** Windows 11 (MSYS2 MINGW64)
> - **hvcc:** v0.16.0
> - **PlugData:** v0.9.3 (Heavy Toolchain v0.8.0)
> - **VCV Rack:** v2.6.6 (SDK)

`build.py` reads your hvcc-compiled PD patch, parses your parameter
declarations, generates C++ wrapper code, builds `plugin.so` (or `.dll`/`.dylib`), and installs
it into VCV Rack automatically.

---

## Table of Contents

- [Quickstart](#quickstart)
- [Usage Instructions](#usage-instructions)
  - [Step 1 — Export your patch to C](#step-1--export-your-patch-to-c)
  - [Step 2 — Run the Generator](#step-2--run-the-generator)
    - [Interactive Mode (Default)](#interactive-mode-default)
    - [Scripting / CLI Mode](#scripting--cli-mode)
  - [Step 3 — Compile and Install](#step-3--compile-and-install)
- [How to structure your project](#how-to-structure-your-project)
- [Prerequisites & Platform Compatibility](#prerequisites--platform-compatibility)
- [Pure Data Naming Conventions](#pure-data-naming-conventions)
  - [Smart naming convention](#smart-naming-convention-recommended)
  - [Output jack labeling](#output-jack-labeling-with-_dacn)
  - [Stereo I/O normalization](#stereo-io-normalization)
- [Custom Component Placement & UI](#custom-component-placement--ui)
- [Custom SVG Widgets](#custom-svg-widgets)
- [Polyphony](#polyphony)
- [Audio and CV signal levels](#audio-and-cv-signal-levels)
- [Troubleshooting](#troubleshooting)
- [Note on AI and Development](#note-on-ai-and-development)
- [Credits](#credits)

---

## Quickstart

If you want to see exactly how your files should be organized, check out the **`BasicVcoExample`** and **`PolySynthExample`** folders! They are ready-to-build templates that demonstrate the correct folder structure.
- **`BasicVcoExample`**: Shows the structure for a **standalone hvcc CLI** export (with `output_directory`).
- **`PolySynthExample`**: Shows the structure for a **PlugData** export (with a flat `c/` directory).

> [!IMPORTANT]
> **Check your Rack-SDK!** The examples in this repository include the **Linux** VCV Rack SDK. If you are building on Windows or macOS, you **must** delete the `Rack-SDK` folder and replace it with the correct SDK for your operating system downloaded from [vcvrack.com/downloads](https://vcvrack.com/downloads). A Linux SDK will fail to compile on Windows/macOS.

To build an example, live-navigate to one of the folders, open a terminal there, and run the generator:
```bash
cd BasicVcoExample/
python3 build.py
```
You will be greeted by an interactive command prompt. Simply press **Enter** to accept the default settings, or type a new value to change them.
*(Note: If you run the PolySynthExample, make sure to type `yes` when asked about Polyphony, as it defaults to `no`!)*

Once the script finishes, restart VCV Rack to see your module!

---

## Usage Instructions

### Step 1 — Export your patch to C

You can use either PlugData or the standalone `hvcc` Python CLI.

**Option A: PlugData (Recommended)**
1. Open your `.pd` file in PlugData.
2. **File → Export → Heavy C Code**
3. Export to a folder inside your project directory (e.g. `c/`). PlugData will generate a flat folder containing all `.c` and `.hpp` files.

**Option B: hvcc CLI**
If you prefer the standard python CLI tool (tested with `v0.16.0`):
```bash
pip install hvcc
hvcc pd/mypatch.pd -n MyPatch -g c -o output_directory/
```
*Note: `hvcc` will create an `output_directory` containing `c/`, `hv/`, and `ir/` subfolders.*

### Step 2 — Run the Generator

Simply run the master build script from your project directory. It automatically handles the differences between PlugData and standalone `hvcc` exports.

#### Interactive Mode (Default)
This is the recommended way to use the generator. It features an interactive command prompt that will guide you through the configuration step-by-step:

```bash
python3 build.py
```
*When prompted for the **HVCC Output Directory**, simply enter the folder you exported to (e.g., `c` or `output_directory`).*

The interactive prompt is where the magic happens. You don't need to memorize any CLI commands! The prompt will ask you if you want to enable **Custom Placement** (for dragging and dropping your jacks/knobs), enable **Polyphony**, or auto-generate text labels.

#### Scripting / CLI Mode
If you prefer scripting or want to bypass the interactive prompts, you can pass arguments directly via CLI. 

Available flags:
- `--hvcc-dir <path>`: Folder containing the hvcc generated output (e.g., `c/` or `output_directory/`)
- `--pd-file <path>`: The Pure Data patch file to compile
- `--module-name <name>`: CamelCase name of your module (e.g., `MySynth`)
- `--plugin-slug <slug>`: Unique alphanumeric ID for the plugin
- `--manufacturer <name>`: Your brand name, shows in the VCV Rack browser
- `--author <name>`: Your name, added to plugin.json
- `--version <version>`: Plugin version. Must start with '2.'
- `--license <license>`: Software license (e.g., `GPL-3.0`)
- `--block-size <int>`: DSP processing block size (default `64`)
- `--ui-text <yes|no>`: Generate C++ text labels for your panel
- `--polyphony <yes|no>`: Enable 16-voice polyphony
- `--custom-layout <yes|no>`: Enable interactive component placement
- `--custom-ports <yes|no>`: Customize jack types
- `--non-interactive`: Skips the interactive prompt entirely. Any arguments you don't specify will fall back to their defaults.

Example:
```bash
python3 build.py --pd-file pd/mypatch.pd --module-name MyPatch --custom-layout yes --polyphony yes --non-interactive
```

### Step 3 — Compile and Install

The `build.py` script automatically copies your C sources, compiles the VCV Rack plugin using `make`, and installs it directly into your VCV Rack `plugins` directory.

Restart VCV Rack 2, and your module will appear in the browser!

---

## How to structure your project

To use `build.py`, your project folder should look like this:

```
my_project/
├── build.py              ← Master build script
├── hvcc2rack.py          ← Generator logic
├── pd2vcv/               ← Internal Python modules
├── pd/
│   └── mypatch.pd        ← Your original Pure Data patch
├── res/                  ← Custom UI SVGs (optional)
├── Rack-SDK/             ← Unzipped VCV Rack 2 Plugin SDK
│
└── [Your HVCC Output Directory] (e.g. c/ or output_directory/)
```

---

## Prerequisites & Platform Compatibility

| Tool | Why | How to get it |
|---|---|---|
| **Python 3.8+** | Runs the generator | Linux: `apt install python3` / Mac: `brew install python` / Windows: Python installer |
| **hvcc** | Compiles `.pd` to C | `pip install hvcc` |
| **VCV Rack 2 SDK** | Headers + build system | [vcvrack.com/downloads](https://vcvrack.com/downloads) → "Plugin SDK" |
| **gcc / g++ / make** | C++ compilation | Linux: `apt install build-essential` / Mac: Xcode / Win: MSYS2 |

### OS & SDK Compatibility

VCV Rack plugins must be compiled using the GNU toolchain (`gcc`, `g++`, and `make`).
- **Linux & macOS:** Works natively. Open your terminal, ensure you have build tools (like `make` and `gcc`) or Xcode installed, and you are ready.
- **Windows:** VCV Rack requires the MinGW64 toolchain. Since this tool is designed for musicians, here is the exact step-by-step to get your Windows PC ready:
  1. Download and install **MSYS2** from [msys2.org](https://www.msys2.org/).
  2. Open your Windows Start Menu and search for **"MSYS2 MinGW x64"** (Look for the **blue** icon! Do not use the purple MSYS icon, and do not use standard Windows PowerShell/CMD).
  3. In the terminal that opens, run this command to update the system (press `Y` when prompted. If the terminal closes, open it again and re-run):
     ```bash
     pacman -Syu
     ```
  4. Finally, install the complete VCV Rack toolchain by copying and pasting this exact command (press `Y` when prompted):
     ```bash
     pacman -Su git wget make tar unzip zip mingw-w64-x86_64-gcc mingw-w64-x86_64-gdb mingw-w64-x86_64-cmake autoconf automake libtool mingw-w64-x86_64-jq python3
     ```
  Once this finishes, you can use this blue terminal to run `python3 build.py` on any of your projects!

**CRITICAL:** You must download the SDK that matches your build platform from the VCV Rack website, unzip it, and place it as a folder named `Rack-SDK/` in your project root (or create a symlink). A Linux SDK will not build Windows plugins.

---

## Pure Data Naming Conventions

Every knob you want in VCV Rack needs a **`[receive]` object** with an
`@hv_param` annotation in your PD patch:

```
[r paramName @hv_param <min> <max> <default>]
```

Example:
```
[r cutoff @hv_param 20 20000 1000]
```

This creates a knob with range 20–20 000, defaulting to 1000.

---

### Smart naming convention (recommended)

Encode the **control type** and **column grouping** in the parameter name:

```
[ui_prefix]_[core_name]
[ui_prefix]_[core_name]_adc[N]
```

| Prefix | Widget in VCV Rack | Rack type | Use for |
|---|---|---|---|
| `base_` | Large knob | `RoundHugeBlackKnob` | Primary value control (unipolar) |
| `attenv_` | Small knob | `RoundSmallBlackKnob` | Bipolar attenuverter (−1 → +1) |
| `atten_` | Tiny trim pot | `Trimpot` | Unipolar attenuator (0 → 1) |
| `button_` | Momentary button | `VCVButton` | Gate behavior (1.0 while held, 0.0 on release) |
| `trigger_` | Momentary button | `VCVButton` | Bang/trigger behavior (Sends 1.0 on press, ignores release) |
| `switch_` | Toggle switch | `CKSS` | Binary mode selection (0.0 / 1.0) |

> **`attenv_` vs `atten_`:** Both produce small controls, but they use different Rack widgets. `attenv_` uses `RoundSmallBlackKnob` (a knob you turn); `atten_` uses `Trimpot` (a smaller screwdriver-style trim pot). The parameter range is set automatically from your `@hv_param` min/max values — set `attenv_` to `-1 1 0` and `atten_` to `0 1 0.5`.

> **`button_` vs `trigger_`:** Both render as the same physical button widget, but behave differently under the hood. 
> - Use `button_` if you want a **Gate** (e.g. holding it down keeps an envelope open). It sends 1.0 when pressed and 0.0 when released.
> - Use `trigger_` if you want a **Bang**. It sends a single 1.0 value on the exact moment you press it and ignores the release. If you connect this to a `[bang]` receiver or a sequencer trigger in PD, it prevents the double-firing issue that happens when releasing a gate.

> **`switch_`:** Produces a 2-position CKSS toggle. The value is `0.0` or `1.0`. Useful for mode selection (sine/square, mono/poly, bypass, etc.).

Parameters sharing the same `[core_name]` are grouped in one **vertical
column** on the panel. Column order (top to bottom):
1. `base_` knob
2. `attenv_` / `atten_` controls
3. `button_` / `switch_` controls
4. Mapped `adc~` input jack (via `_adcN` suffix)
5. Mapped `dac~` output jack (via `[s core_name_dacN @hv_param]`)

The `_adc[N]` suffix maps a specific `adc~` input jack to the bottom of that column.

**Example — filter with CV:**
```
[r base_cutoff_adc2 @hv_param 20 20000 2000]
[r attenv_cutoff    @hv_param -1 1 0]
```

Generates a CUTOFF column:
```
  [Large knob]     ← base_cutoff        (top)
  [Small knob]     ← attenv_cutoff      (middle)
  [□ input jack]   ← adc~ 2 input       (bottom, via _adc2 suffix)

  [□] [□]  [■]     ← unmapped I/O at very bottom of panel
```

Any `adc~` inputs **not** mapped to a column appear as plain audio inputs
in the bottom row. Your PD patch handles all CV routing internally via
those `adc~` inputs — the script does NOT auto-generate CV jacks.

---

### Output jack labeling with `_dac[N]`

To add a labeled audio **output** jack inside a column, add a `[send]` object with the `_dacN` suffix:

```
[s core_name_dac[N] @hv_param 0 1 0]
```

The generator will:
- Place an **output jack** in the `core_name` column, below the input jack
- Label it `CORE_NAME_OUT` on the panel
- Wire it to `dac~ N` from your patch — **audio must still route through `[dac~ N]` inside PD**

The `@hv_param` annotation values (min, max, default) are ignored for output labeling — any values work. The annotation is only a signal to the generator that this `[s]` object declares a panel jack.

> [!NOTE]
> **Compiler Warnings:** Because these `[s]` objects have no inputs, the PlugData / hvcc compiler will print:
> `Warning pd2hv: [s core_dacN ...] This object has no inlet connections. It does nothing and will be removed.`
> **This is completely normal.** The generator reads the label from your patch before the compiler removes it. If you want a perfectly clean build log without warnings, simply connect a dummy `[loadbang]` to these send objects in PureData.

**Example — VCO with per-voice audio output:**
```
[r base_freq_adc2  @hv_param 20 20000 440]
[r attenv_freq     @hv_param -1 1 0]
[s freq_dac1       @hv_param 0 1 0]      ← labels dac~ 1 output in FREQ column
```

Generates:
```
  [Large knob]     ← base_freq        (top)
  [Small knob]     ← attenv_freq      (middle)
  [□ input jack]   ← adc~ 2 (FREQ IN) (row 3)
  [■ output jack]  ← dac~ 1 (FREQ OUT)(row 4)
```

---

### Stereo I/O normalization

If your patch uses **`adc~ 1` and `adc~ 2` and neither is mapped to a column**, the generator automatically promotes them to a stereo pair:
- `IN_1` → **`IN_L`**
- `IN_2` → **`IN_R`**

Standard VCV Rack mono-normalization is applied in the generated C++:
> When only `IN_L` is patched, `IN_R` automatically carries the same signal (mono mode).
> When both are patched, each routes independently to `adc~ 1` and `adc~ 2` in your patch (stereo mode).

Same rule applies to outputs: if your patch produces **`dac~ 1` and `dac~ 2`** and neither is claimed by a `_dacN` label, they are promoted to **`OUT_L` / `OUT_R`**.

> **Note:** If you map `adc~ 2` to a column (e.g. `base_cutoff_adc2`), that input is consumed by the column CV jack, and stereo detection only fires on the remaining unmapped inputs. For example, if only `adc~ 1` remains unmapped, it appears as `IN_1` (not `IN_L`) since a stereo pair requires both `adc~ 1` and `adc~ 2` to be free.

---

## Custom Component Placement & UI

If you want precise control over where every knob, jack, and button appears on your module panel, simply answer `yes` when the interactive prompt asks about **Custom Layout**.

### How it works

1. The auto-layout engine runs first and calculates default positions for all components
2. You see each component with its auto-position and can override it in two steps:

**Step 1: Controls (Knobs, Buttons, Switches)**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 1: Control Placement (Knobs, Buttons, Switches)
  Press [Enter] to keep auto-position, or type: x, y
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PITCH                (HugeKnob       ) [15.2, 28.3]: 
  PITCH_ATTENV         (SmallKnob      ) [15.2, 56.5]: 20, 45
```

**Step 2: Jacks & Port Types**
You can also override the **type** of each jack, which determines its SVG color scheme and stereo normalization logic.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 2: Jack Placement & Type
  Types:  cvi    = CV Input       cvo    = CV Output
          audioi = Audio Input     audioo = Audio Output
          inl    = Audio In Left   inr    = Audio In Right
          outl   = Audio Out Left  outr   = Audio Out Right
  Press [Enter] to keep defaults.
  Type only (keep position): cvi
  Position only:             20, 45
  Both:                      cvi 20, 45
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  IN_L                 (Input Jack  ) [8.8, 113.1]: audioi
  OUT_L                (Output Jack ) [50.8, 113.1]: outl 50, 110
```

3. Press **Enter** to keep the defaults, or type overrides as shown.
4. Data is saved to `.pd2vcv_layout.json` in the project root.

### Customizing Jack Types Only

If you prefer the automatic layout but still want to assign jack types (audio/cv/stereo), answer `no` to Custom Layout but `yes` to Custom Ports in the interactive prompt.
This skips the positioning prompts and only asks you to define your port types.

---

## Custom SVG Widgets

The generator relies on a `res/` folder next to `build.py` which is **always active**. You don't need any CLI flags to enable custom SVGs—simply place them in the `res/` folder and they will be used.

The system supports the following 16 SVG files, all of which are **optional**. Missing files automatically fall back to Rack's built-in widgets.

### Expected folder structure

```
res/
├── panel.svg           ← Light theme panel background
├── panel-dark.svg      ← Dark theme panel background (optional, light is reused if missing)
├── knob_large.svg      ← Replaces base_ knob
├── knob_small.svg      ← Replaces attenv_ knob
├── knob_trim.svg       ← Replaces atten_ trim pot
├── knob_default.svg    ← Replaces plain param knob
├── button.svg          ← Gate button unpressed state (button_ suffix)
├── button_pressed.svg  ← Gate button pressed state
├── trigger.svg         ← Momentary trigger unpressed state (trigger_ suffix)
├── trigger_pressed.svg ← Momentary trigger pressed state
├── switch_off.svg      ← Toggle switch off position
├── switch_on.svg       ← Toggle switch on position
├── port_cv_in.svg      ← CV input (light blue ring)
├── port_cv_out.svg     ← CV output (dark blue ring)
├── port_audio_in.svg   ← Audio input (silver ring)
├── port_audio_out.svg  ← Audio output (black ring)
├── port_in.svg         ← Generic input fallback
└── port_out.svg        ← Generic output fallback
```

### How it works

1. The generator scans the `res/` folder and detects which SVGs you've provided.
2. For each detected SVG, a C++ widget struct is generated that loads it at runtime:
   ```cpp
   struct CustomAudioInputPort : rack::app::SvgPort {
       CustomAudioInputPort() {
           setSvg(APP->window->loadSvg(
               rack::asset::plugin(pluginInstance, "res/port_audio_in.svg")));
       }
   };
   ```
3. Your SVGs are automatically copied to `rack_plugin/res/` during generation.
4. Any widget type you don't provide falls back to generic SVGs or Rack's built-in components.

### Panel SVG

The auto-generated panel is completely blank (only a solid rectangle with top/bottom borders) to avoid drawing component markers under your custom layout. 

If you provide a custom `panel.svg`, the generator:
- **Skips** auto-generating the blank panel
- **Auto-detects** the panel width from the SVG's `width` attribute (in mm)
- Uses your panel for both light and dark themes unless `panel-dark.svg` is also provided

> [!NOTE]
> **SVG design tips for knobs:** VCV Rack's `SvgKnob` rotates your SVG around its center. Design your knob as a circle with an indicator mark pointing straight up (12 o'clock position). The widget handles rotation automatically based on the parameter value.

---

## Polyphony

During the `python3 build.py` interactive prompts, you have the option to enable **16-voice polyphony**.

If you select `yes`, `pd2vcv` modifies the generated C++ wrapper to spin up 16 parallel Heavy contexts. This completely changes how inputs and outputs behave, aligning them with the VCV Rack polyphony standard:

### 1. Polyphonic Broadcasting
You do not need to specify "which" input is polyphonic. If polyphony is enabled, **ALL** inputs and outputs become polyphonic. The plugin will check the number of channels on every connected cable (1 to 16 channels) and automatically activate the highest number of voices.

- **Mono Cables (1 channel):** A mono cable plugged into a polyphonic module (e.g. a single LFO into a filter cutoff) will be broadcast to **all active voices**. This allows global modulation.
- **Poly Cables (2-16 channels):** A polyphonic cable (e.g. 4 channels of V/Oct pitch) will be routed individually. Voice 1 gets Pitch 1, Voice 2 gets Pitch 2, etc.

### 2. Stereo I/O Constraints
When you enable polyphony, the standard VCV Rack "Stereo Normalization" rule (Left/Right outputs) goes out the window, because polyphonic outputs are multiplexed over a single mono-per-voice cable.

**Do not design stereo patches for polyphony!** 
If you want to build a polyphonic synth, your patch should output a **single `dac~ 1`**. The wrapper will automatically take the 16 independent `dac~ 1` outputs from your 16 voices and pack them into a 16-channel polyphonic cable. If you absolutely need stereo polyphony, output `dac~ 1` for Left and `dac~ 2` for Right, and your module will produce two separate 16-channel polyphonic cables.

---

## Audio and CV signal levels

Voltages are passed exactly 1:1 between VCV Rack and Pure Data. There is NO hidden scaling applied by the C++ wrapper. 

| VCV Rack | Heavy (inside patch) |
|---|---|
| +10.0 V | +10.0 |
| +5.0 V | +5.0 |
| +1.0 V | +1.0 |
| −5.0 V | −5.0 |

**What this means for your PD patch:**
*   **Audio & LFOs:** VCV Rack audio standard is ±5V. Expect your `adc~` objects to output signals between -5.0 and +5.0. 
*   **Envelopes:** VCV Rack envelopes are 0 to 10V. Expect your `adc~` to output 0.0 to 10.0.
*   **V/Oct Pitch:** 1V per octave = 1.0 per octave in PD.

If your Pure Data patch strictly expects normalized signals (-1.0 to 1.0 or 0 to 1.0) for things like oscillator frequencies or amplitudes, you must manually scale them down inside the patch (e.g., attach a `[*~ 0.2]` right after your `adc~` to convert ±5V down to ±1.0).

*Safety note: The C++ wrapper hard-clamps all `adc~` inputs and `dac~` outputs at **±12.0V** (Eurorack physical standard) to prevent runaway math from crashing other modules.*

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Plugin version does not match Rack ABI 2` | `VERSION` must start with `2.` |
| `Plugin already loaded` | Delete old folder from `<RACK_USER_DIR>/plugins-<os>-<arch>/` |
| Build error: `Heavy_*.h not found` | Check all hvcc export files are in your chosen `c/` directory |
| `No @hv_param declarations found` | Verify `[r name @hv_param min max default]` in your PD patch |
| Knob range shows 0–1 | Ensure `PD_FILE` path is correct when running `build.py` |

---

## Note on AI and Development

I am a musician and a Pure Data patcher, not a C++ or Python programmer. The concept, the smart-naming conventions, the UI layout engine rules, and the signal routing logic are entirely my own design.
However, to bring this idea to life, I relied heavily on AI coding assistants to write the actual Python and C++ syntax. I am being completely transparent about this because I know the open-source community's feelings on AI can be mixed. My goal was simply to bridge a gap between PD and VCV Rack that I desperately wanted for my own music, and I used the tools available to me to build it.
Because I am not a native C++ developer, the codebase might have structural quirks. Human pull requests, code reviews, and refactoring are incredibly welcome.


## Credits

- **Pure Data** by [Miller Puckette and the PD community](https://puredata.info/)
- **PlugData** by [Timothy Schoen and contributors](https://plugdata.org/)
- **hvcc** by [Wasted Audio](https://github.com/Wasted-Audio/hvcc)
- **VCV Rack SDK** © VCV LLC
- **hvcc2rack.py** included in this folder
