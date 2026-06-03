from dataclasses import dataclass, field
from typing import List
from pathlib import Path


@dataclass
class HvParam:
    name: str           # raw name from hvcc
    safe_name: str      # sanitized C++ identifier
    hash_str: str       # "0x3AE704A5"
    minimum: float = 0.0
    maximum: float = 1.0
    default: float = 0.5
    direction: str = "in"   # "in" | "out"
    # Smart naming fields (populated by parse_smart_name if applicable)
    ui_type: str = ""       # "base" | "attenv" | "atten" | "" (plain)
    core_name: str = ""     # shared grouping name, e.g. "cutoff"
    adc_map: int = 0        # >0 means this param's column owns that adc~ input
    step_size: float = 0.0  # >0 means this param snaps to intervals

    enum_label: str = ""    # overridden C++ enum label (stripped of prefix/suffix)


@dataclass
class HeavyApi:
    """Auto-detected or user-overridden Heavy API variant."""
    # NOTE: This is hvcc-specific; RNBO parser will define its own equivalent
    process_sig: str = "float_ptr_ptr"
    # "float_ptr_ptr"   -> process(float**, float**, int)
    # "const_ptr_ptr"   -> process(const float* const*, float* const*, int)
    send_func: str = "sendFloat"
    # "sendFloat"   -> _ctx->sendFloatToReceiver(hash, value)
    # "sendMessage" -> HvMessage stack + _ctx->sendMessageToReceiver(hash, delay, msg)


@dataclass
class PatchInfo:
    name: str               # user-supplied CamelCase module name
    class_name: str         # "Heavy_patchname"
    header_file: str        # "Heavy_patchname.h"
    num_input_channels: int = 2
    num_output_channels: int = 2
    params: List[HvParam] = field(default_factory=list)
    api: HeavyApi = field(default_factory=HeavyApi)
    stereo_in: bool = False    # adc~ 1+2 are an auto-detected stereo pair (-> IN_L/IN_R)
    stereo_out: bool = False   # dac~ 1+2 are an auto-detected stereo pair (-> OUT_L/OUT_R)


@dataclass
class ComponentPos:
    kind: str       # "param" | "input" | "output"
    label: str      # C++ enum member label (already sanitized)
    x: float        # mm from panel left
    y: float        # mm from panel top
    index: int      # enum index within kind
    knob_type: str = "RoundBlackKnob"  # Rack widget class for params
    ui_label: str = "" # display name for the panel (e.g. "IN L", "CUTOFF")
    port_type: str = ""  # "", "cvi", "cvo", "audioi", "audioo", "inl", "inr", "outl", "outr"


@dataclass
class CustomWidgets:
    """Tracks which custom SVG widget files are present in the res/ folder."""
    # Knobs
    knob_large: bool = False      # knob_large.svg -> replaces RoundHugeBlackKnob
    knob_small: bool = False      # knob_small.svg -> replaces RoundSmallBlackKnob
    knob_trim: bool = False       # knob_trim.svg  -> replaces Trimpot
    knob_default: bool = False    # knob_default.svg -> replaces RoundBlackKnob
    step_knob: bool = False       # step_knob.svg -> replaces StepKnob
    # Buttons & switches
    button: bool = False          # button.svg + button_pressed.svg
    trigger: bool = False         # trigger.svg + trigger_pressed.svg
    switch_on: bool = False       # switch_on.svg
    switch_off: bool = False      # switch_off.svg
    # Ports — typed by signal type
    port_cv_in: bool = False      # port_cv_in.svg (light blue ring)
    port_cv_out: bool = False     # port_cv_out.svg (dark blue ring)
    port_audio_in: bool = False   # port_audio_in.svg (silver ring)
    port_audio_out: bool = False  # port_audio_out.svg (black ring)
    port_in: bool = False         # port_in.svg (generic fallback)
    port_out: bool = False        # port_out.svg (generic fallback)
    # Panel
    panel: bool = False           # panel.svg -> replaces auto-generated light panel
    panel_dark: bool = False      # panel-dark.svg -> replaces auto-generated dark panel

    @classmethod
    def from_dir(cls, res_dir: Path) -> 'CustomWidgets':
        """Scan a directory and detect which custom SVGs are present."""
        cw = cls()
        mapping = {
            "knob_large.svg": "knob_large",
            "knob_small.svg": "knob_small",
            "knob_trim.svg": "knob_trim",
            "knob_default.svg": "knob_default",
            "step_knob.svg": "step_knob",
            "button.svg": "button",
            "trigger.svg": "trigger",
            "switch_on.svg": "switch_on",
            "switch_off.svg": "switch_off",
            "port_cv_in.svg": "port_cv_in",
            "port_cv_out.svg": "port_cv_out",
            "port_audio_in.svg": "port_audio_in",
            "port_audio_out.svg": "port_audio_out",
            "port_in.svg": "port_in",
            "port_out.svg": "port_out",
            "panel.svg": "panel",
            "panel-dark.svg": "panel_dark",
        }
        for filename, attr in mapping.items():
            if (res_dir / filename).exists():
                setattr(cw, attr, True)
                print(f"[res]   Found: {filename}")
        return cw


_CPP_RESERVED = {
    "alignas","alignof","and","and_eq","asm","auto","bitand","bitor","bool",
    "break","case","catch","char","char8_t","char16_t","char32_t","class",
    "compl","concept","const","consteval","constexpr","constinit","const_cast",
    "continue","co_await","co_return","co_yield","decltype","default","delete",
    "do","double","dynamic_cast","else","enum","explicit","export","extern",
    "false","float","for","friend","goto","if","inline","int","long","mutable",
    "namespace","new","noexcept","not","not_eq","nullptr","operator","or",
    "or_eq","private","protected","public","register","reinterpret_cast",
    "requires","return","short","signed","sizeof","static","static_assert",
    "static_cast","struct","switch","template","this","thread_local","throw",
    "true","try","typedef","typeid","typename","union","unsigned","using",
    "virtual","void","volatile","wchar_t","while","xor","xor_eq",
}


# Recognised UI prefixes and their Rack widget class
# The widget class string is used directly in createParamCentered<...>.
_UI_PREFIXES = {
    "base":   "RoundHugeBlackKnob",   # large knob (primary value)
    "attenv": "RoundSmallBlackKnob",  # small knob for bipolar attenuverter (-1 -> +1)
    "atten":  "Trimpot",              # tiny trim pot for unipolar attenuator (0 -> 1)
    "button": "VCVButton",            # momentary button (gate: 1.0 while held, 0.0 on release)
    "trigger":"VCVTrigger",           # momentary trigger (sends 1.0 on press, ignores release)
    "switch": "CKSS",                 # 2-position toggle switch (0.0 / 1.0)
    "step_knob": "StepKnob",          # stepped rotary parameter
    "menu": "CustomMenuWidget",       # click to open dropdown menu
}
