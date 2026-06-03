from typing import List, Optional, Dict, Tuple
from pathlib import Path


from pd2vcv.models import ComponentPos, PatchInfo, HvParam, CustomWidgets, _UI_PREFIXES, HeavyApi
from pd2vcv.utils import _enum_body, _param_label

HP_MM = 5.08
PANEL_H_MM = 128.5
def _resolve_widget(c: ComponentPos, custom_widgets: Optional[CustomWidgets] = None) -> str:
    """Return the C++ widget class name for a component, using custom SVG structs when available."""
    if c.kind == "param" and c.knob_type == "CustomMenuWidget":
        return f"CustomMenuWidget_{c.label}"

    if custom_widgets is None:
        # No custom widgets — use built-in Rack widgets
        if c.kind == "param":
            kt = c.knob_type or "RoundBlackKnob"
            # VCVTrigger is our internal name; Rack only knows VCVButton
            return f"rack::{'VCVButton' if kt == 'VCVTrigger' else kt}"
        return "rack::PJ301MPort"

    if c.kind == "param":
        kt = c.knob_type or "RoundBlackKnob"
        widget_map = {
            "RoundHugeBlackKnob":  ("knob_large",   "CustomLargeKnob"),
            "RoundSmallBlackKnob": ("knob_small",   "CustomSmallKnob"),
            "Trimpot":             ("knob_trim",     "CustomTrimKnob"),
            "RoundBlackKnob":      ("knob_default",  "CustomDefaultKnob"),
            "StepKnob":            ("step_knob",     "CustomStepKnob"),
            "VCVButton":           ("button",        "CustomButton"),
            "VCVTrigger":          ("trigger",       "CustomTrigger"),
            "CKSS":                ("_switch",       "CustomSwitch"),
        }
        if kt in widget_map:
            attr, custom_cls = widget_map[kt]
            if attr == "_switch":
                if custom_widgets.switch_on and custom_widgets.switch_off:
                    return custom_cls
            elif getattr(custom_widgets, attr, False):
                return custom_cls
        # Fallback: VCVTrigger -> VCVButton in Rack
        if kt == "StepKnob": kt = "RoundBlackKnob"
        rack_kt = "VCVButton" if kt == "VCVTrigger" else kt
        return f"rack::{rack_kt}"

    elif c.kind == "input":
        # Port type resolution chain: typed -> generic -> built-in
        if c.port_type in ("cvi",):
            if custom_widgets.port_cv_in:
                return "CustomCvInputPort"
        elif c.port_type in ("audioi", "inl", "inr"):
            if custom_widgets.port_audio_in:
                return "CustomAudioInputPort"
        # Generic fallback
        if custom_widgets.port_in:
            return "CustomInputPort"
        return "rack::PJ301MPort"

    elif c.kind == "output":
        if c.port_type in ("cvo",):
            if custom_widgets.port_cv_out:
                return "CustomCvOutputPort"
        elif c.port_type in ("audioo", "outl", "outr"):
            if custom_widgets.port_audio_out:
                return "CustomAudioOutputPort"
        # Generic fallback
        if custom_widgets.port_out:
            return "CustomOutputPort"
        return "rack::PJ301MPort"

    return "rack::PJ301MPort"


def gen_custom_widget_structs(custom_widgets: Optional[CustomWidgets] = None, menu_entries: Optional[Dict[str, List[str]]] = None) -> str:
    """Generate C++ struct definitions for custom SVG widgets."""
    if custom_widgets is None and not menu_entries:
        return ""

    structs: List[str] = []

    # ── Knobs ──
    if custom_widgets:
        if custom_widgets.knob_large:
            structs.append(
                'struct CustomLargeKnob : rack::app::SvgKnob {\n'
                '    CustomLargeKnob() {\n'
                '        minAngle = -0.83 * M_PI;\n'
                '        maxAngle = 0.83 * M_PI;\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/knob_large.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.knob_small:
            structs.append(
                'struct CustomSmallKnob : rack::app::SvgKnob {\n'
                '    CustomSmallKnob() {\n'
                '        minAngle = -0.83 * M_PI;\n'
                '        maxAngle = 0.83 * M_PI;\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/knob_small.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.knob_trim:
            structs.append(
                'struct CustomTrimKnob : rack::app::SvgKnob {\n'
                '    CustomTrimKnob() {\n'
                '        minAngle = -0.83 * M_PI;\n'
                '        maxAngle = 0.83 * M_PI;\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/knob_trim.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.knob_default:
            structs.append(
                'struct CustomDefaultKnob : rack::app::SvgKnob {\n'
                '    CustomDefaultKnob() {\n'
                '        minAngle = -0.83 * M_PI;\n'
                '        maxAngle = 0.83 * M_PI;\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/knob_default.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.step_knob:
            structs.append(
                'struct CustomStepKnob : rack::app::SvgKnob {\n'
                '    CustomStepKnob() {\n'
                '        minAngle = -0.83 * M_PI;\n'
                '        maxAngle = 0.83 * M_PI;\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/step_knob.svg")));\n'
                '    }\n'
                '};'
            )

        # ── Buttons & triggers ──
        if custom_widgets.button:
            structs.append(
                'struct CustomButton : rack::app::SvgSwitch {\n'
                '    CustomButton() {\n'
                '        momentary = true;\n'
                '        addFrame(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/button.svg")));\n'
                '        addFrame(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/button_pressed.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.trigger:
            structs.append(
                'struct CustomTrigger : rack::app::SvgSwitch {\n'
                '    CustomTrigger() {\n'
                '        momentary = true;\n'
                '        addFrame(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/trigger.svg")));\n'
                '        addFrame(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/trigger_pressed.svg")));\n'
                '    }\n'
                '};'
            )

        # ── Switch ──
        if custom_widgets.switch_on and custom_widgets.switch_off:
            structs.append(
                'struct CustomSwitch : rack::app::SvgSwitch {\n'
                '    CustomSwitch() {\n'
                '        addFrame(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/switch_off.svg")));\n'
                '        addFrame(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/switch_on.svg")));\n'
                '    }\n'
                '};'
            )

        # ── Ports (typed) ──
        if custom_widgets.port_cv_in:
            structs.append(
                'struct CustomCvInputPort : rack::app::SvgPort {\n'
                '    CustomCvInputPort() {\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/port_cv_in.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.port_cv_out:
            structs.append(
                'struct CustomCvOutputPort : rack::app::SvgPort {\n'
                '    CustomCvOutputPort() {\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/port_cv_out.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.port_audio_in:
            structs.append(
                'struct CustomAudioInputPort : rack::app::SvgPort {\n'
                '    CustomAudioInputPort() {\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/port_audio_in.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.port_audio_out:
            structs.append(
                'struct CustomAudioOutputPort : rack::app::SvgPort {\n'
                '    CustomAudioOutputPort() {\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/port_audio_out.svg")));\n'
                '    }\n'
                '};'
            )

        # ── Ports (generic fallback) ──
        if custom_widgets.port_in:
            structs.append(
                'struct CustomInputPort : rack::app::SvgPort {\n'
                '    CustomInputPort() {\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/port_in.svg")));\n'
                '    }\n'
                '};'
            )
        if custom_widgets.port_out:
            structs.append(
                'struct CustomOutputPort : rack::app::SvgPort {\n'
                '    CustomOutputPort() {\n'
                '        setSvg(rack::Svg::load(rack::asset::plugin(pluginInstance, "res/port_out.svg")));\n'
                '    }\n'
                '};'
            )

    if menu_entries:
        base_menu = '''
struct CustomMenuWidget : rack::app::ParamWidget {
    std::vector<std::string> entries;
    
    CustomMenuWidget() {
        box.size = rack::mm2px(rack::Vec(18.0f, 5.0f));
    }

    void draw(const DrawArgs& args) override {
        // Uniform grey appearance, independent of light/dark mode
        NVGcolor bgColor = nvgRGBA(45, 45, 45, 255);
        NVGcolor fgColor = nvgRGBA(230, 230, 230, 255);
        
        nvgBeginPath(args.vg);
        nvgRoundedRect(args.vg, 0, 0, box.size.x, box.size.y, rack::mm2px(0.5f));
        nvgFillColor(args.vg, bgColor);
        nvgFill(args.vg);
        
        nvgStrokeWidth(args.vg, 0.5f);
        nvgStrokeColor(args.vg, nvgRGBA(0, 0, 0, 255));
        nvgStroke(args.vg);
        
        if (!getParamQuantity()) return;
        
        float val = getParamQuantity()->getValue();
        float minVal = getParamQuantity()->getMinValue();
        int idx = std::round(val - minVal);
        if (idx < 0) idx = 0;
        if (idx >= (int)entries.size()) idx = entries.size() - 1;
        
        std::string text = entries.empty() ? "" : entries[idx];
        
        std::shared_ptr<rack::window::Font> font = APP->window->uiFont;
        if (font) {
            nvgFontSize(args.vg, rack::mm2px(2.5f));
            nvgFontFaceId(args.vg, font->handle);
            nvgFillColor(args.vg, fgColor);
            nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_MIDDLE);
            nvgText(args.vg, box.size.x / 2, box.size.y / 2 + 1.0f, text.c_str(), nullptr);
            
            // Draw downward arrow
            nvgBeginPath(args.vg);
            float ax = box.size.x - rack::mm2px(2.5f);
            float ay = box.size.y / 2.0f + 1.0f;
            float aw = rack::mm2px(0.8f);
            float ah = rack::mm2px(0.6f);
            nvgMoveTo(args.vg, ax - aw, ay - ah);
            nvgLineTo(args.vg, ax + aw, ay - ah);
            nvgLineTo(args.vg, ax, ay + ah);
            nvgFillColor(args.vg, fgColor);
            nvgFill(args.vg);
        }
    }

    struct MenuActionItem : rack::ui::MenuItem {
        CustomMenuWidget* widget;
        int index;
        float minVal;
        void onAction(const rack::event::Action& e) override {
            widget->getParamQuantity()->setValue(minVal + index);
        }
    };

    void onButton(const rack::event::Button& e) override {
        if (e.action == GLFW_PRESS && e.button == GLFW_MOUSE_BUTTON_LEFT) {
            e.consume(this);
            rack::ui::Menu* menu = rack::createMenu();
            menu->box.pos = getAbsoluteOffset(rack::Vec(0, box.size.y));
            
            float minVal = getParamQuantity()->getMinValue();
            for (size_t i = 0; i < entries.size(); i++) {
                MenuActionItem* item = new MenuActionItem();
                item->text = entries[i];
                item->widget = this;
                item->index = i;
                item->minVal = minVal;
                item->rightText = rack::string::f(rack::math::clamp(getParamQuantity()->getValue(), minVal, getParamQuantity()->getMaxValue()) == minVal + i ? "✔" : "");
                menu->addChild(item);
            }
        } else {
            ParamWidget::onButton(e);
        }
    }
};'''
        structs.append(base_menu)
        for label, items in menu_entries.items():
            items_c = ", ".join(f'"{i}"' for i in items)
            structs.append(
                f'struct CustomMenuWidget_{label} : CustomMenuWidget {{\n'
                f'    CustomMenuWidget_{label}() {{\n'
                f'        entries = {{{items_c}}};\n'
                f'    }}\n'
                f'}};'
            )

    if not structs:
        return ""

    return (
        "\n// ── Custom SVG Widgets ────────────────────────────────────────────────────\n\n"
        + "\n\n".join(structs) + "\n"
    )



def _addchild_lines(components: List[ComponentPos], mn: str, panel_hp: int,
                    ui_text: str = "yes",
                    custom_widgets: Optional[CustomWidgets] = None) -> str:
    lines = []
    for c in components:
        pos = f"rack::mm2px(rack::Vec({c.x:.2f}f, {c.y:.2f}f))"
        mod = f"{mn}Module"
        widget_cls = _resolve_widget(c, custom_widgets)
        if c.kind == "param":
            lines.append(
                f"        addParam(rack::createParamCentered"
                f"<{widget_cls}>({pos}, module, {mod}::{c.label}_ID));"
            )
        elif c.kind == "input":
            lines.append(
                f"        addInput(rack::createInputCentered"
                f"<{widget_cls}>({pos}, module, {mod}::{c.label}_ID));"
            )
        elif c.kind == "output":
            lines.append(
                f"        addOutput(rack::createOutputCentered"
                f"<{widget_cls}>({pos}, module, {mod}::{c.label}_ID));"
            )
            
        # Add C++ text label via custom TextLabel widget
        if ui_text.lower() in ("yes", "y", "true", "1"):
            kt = c.knob_type or ""
            if kt in ("VCVButton", "VCVTrigger"):
                label_y = c.y + 3.5 + 2.2
            elif kt == "CKSS":
                label_y = c.y + 4.0 + 2.2
            elif c.kind == "param":
                r_for_label = 11.0 if kt == _UI_PREFIXES["base"] else 3.0
                label_y = c.y + r_for_label + 2.0
            else:
                label_y = c.y + 4.5 + 2.2

            if kt != "CustomMenuWidget":
                ui_lbl = c.ui_label or c.label.replace("_", " ")
                if ui_lbl.startswith("ATTENV "): ui_lbl = ui_lbl[7:]
                elif ui_lbl.startswith("ATTEN "): ui_lbl = ui_lbl[6:]
                elif ui_lbl.endswith(" ATTENV"): ui_lbl = ui_lbl[:-7]
                elif ui_lbl.endswith(" ATTEN"): ui_lbl = ui_lbl[:-6]
                font_sz = "2.4f" if c.kind == "param" else "2.0f"
                pos_lbl = f"rack::mm2px(rack::Vec({c.x:.2f}f, {label_y:.2f}f))"
                lines.append(f'        addChild(new TextLabel({pos_lbl}, "{ui_lbl}", {font_sz}));')

    if ui_text.lower() in ("yes", "y", "true", "1"):
        # Add module name at the top center
        w = panel_hp * 5.08
        title_pos = f"rack::mm2px(rack::Vec({w/2:.2f}f, 4.8f))"
        lines.append(f'        addChild(new TextLabel({title_pos}, "{mn}", 3.2f));')

    return "\n".join(lines)



def _send_call(api: HeavyApi, hash_const: str, val_expr: str) -> str:
    """Generate the correct Heavy send call for the detected API variant."""
    if api.send_func == "sendFloat":
        return f"_ctx->sendFloatToReceiver({hash_const}, {val_expr});"
    else:
        # sendMessageToReceiver variant — requires HvMessage stack object
        return (
            f"{{ HvMessage *_msg = HV_MESSAGE_ON_STACK(1);\n"
            f"          msg_initWithFloat(_msg, 0, {val_expr});\n"
            f"          _ctx->sendMessageToReceiver({hash_const}, 0.0, _msg); }}"
        )


def _process_call(api: HeavyApi, n_ai: int, n_ao: int) -> str:
    """Generate the Heavy process() call with the correct pointer type."""
    if api.process_sig == "const_ptr_ptr":
        in_type  = "const float*"
        out_type = "float*"
        cast_in  = "(const float* const*)"
        cast_out = "(float* const*)"
    else:
        in_type  = "float*"
        out_type = "float*"
        cast_in  = "(float**)"
        cast_out = "(float**)"

    in_arr  = f"        {in_type}  _ip[{max(n_ai,  1)}];"
    out_arr = f"        {out_type} _op[{max(n_ao, 1)}];"
    in_fill  = "\n".join(
        f"        _ip[{i}] = _inBuf[{i}];" for i in range(n_ai)
    ) or "        // no audio inputs"
    out_fill = "\n".join(
        f"        _op[{i}] = _outBuf[{i}];" for i in range(n_ao)
    ) or "        // no audio outputs"

    return (
        f"{in_arr}\n"
        f"{out_arr}\n"
        f"{in_fill}\n"
        f"{out_fill}\n"
        f"        _ctx->process({cast_in}_ip, {cast_out}_op, BLOCK);\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# File generators
# ─────────────────────────────────────────────────────────────────────────────

def gen_plugin_hpp(module_name: str) -> str:
    return (
        "#pragma once\n"
        "#include <rack.hpp>\n"
        "\n"
        "extern rack::Plugin *pluginInstance;\n"
        "\n"
        f"extern rack::Model *model{module_name};\n"
    )


def gen_plugin_cpp(plugin_slug: str, plugin_name: str, module_name: str) -> str:
    return (
        '#include "plugin.hpp"\n'
        "\n"
        "rack::Plugin *pluginInstance;\n"
        "\n"
        "#ifdef _WIN32\n"
        "#define EXPORT __declspec(dllexport)\n"
        "#else\n"
        "#define EXPORT\n"
        "#endif\n"
        "\n"
        'extern "C" EXPORT void init(rack::Plugin *p) {\n'
        "    pluginInstance = p;\n"
        f'    p->addModel(model{module_name});\n'
        "}\n"
    )


def gen_module_cpp(info: PatchInfo, panel_hp: int,
                   components: List[ComponentPos],
                   block_size: int,
                   ui_text: str = "yes",
                   polyphony: bool = False,
                   custom_widgets: Optional[CustomWidgets] = None,
                   menu_entries: Optional[Dict[str, List[str]]] = None) -> str:

    mn      = info.name
    api     = info.api
    n_ai    = info.num_input_channels
    n_ao    = info.num_output_channels
    in_p    = [p for p in info.params if p.direction != "out"]
    n_knobs = len(in_p)

    # Component groups — no CV jacks (PD patch handles CV via adc~ inputs)
    param_comps    = [c for c in components if c.kind == "param"]
    audio_in_comps = [c for c in components if c.kind == "input"]
    output_comps   = [c for c in components if c.kind == "output"]
    # Sort inputs by their real Heavy adc~ index so the C++ enum evaluates correctly (0, 1, 2...),
    # but do NOT overwrite c.index so _inBuf mapping remains accurate.
    audio_in_comps.sort(key=lambda c: c.index)
    output_comps.sort(key=lambda c: c.index)

    # Enums
    param_enum  = _enum_body(param_comps,    "NUM_PARAM_IDS")
    input_enum  = _enum_body(audio_in_comps, "NUM_INPUT_IDS")
    output_enum = _enum_body(output_comps,   "NUM_OUTPUT_IDS")

    # Build a map from enum label -> HvParam for smart-named lookups
    def _param_label(p: HvParam) -> str:
        return p.enum_label if p.enum_label else p.safe_name.upper()

    # Hash constants — keyed by the actual C++ hash identifier used in send calls
    hash_block = "\n".join(
        f"    static constexpr uint32_t HASH_{_param_label(p)} = {p.hash_str}u;"
        for p in in_p
    ) or "    // (no Heavy receiver hashes)"

    # configParam / configInput / configOutput
    label_to_param = {_param_label(p): p for p in in_p}

    cfg_lines = []
    for c in param_comps:
        p = label_to_param.get(c.label)
        if p is None:
            # Fallback: try matching by safe_name
            p = next((x for x in in_p if x.safe_name.upper() == c.label), None)
        if p is None:
            cfg_lines.append(f'        configParam({c.label}_ID, 0.0f, 1.0f, 0.5f, "{c.label}");')
        else:
            if getattr(p, "step_size", 0.0) > 0.0:
                cfg_lines.append(
                    f'        configParam<StepQuantity>({c.label}_ID, {p.minimum}f, {p.maximum}f, '
                    f'{p.default}f, "{p.name}")->stepSize = {p.step_size}f;'
                )
            else:
                cfg_lines.append(
                    f'        configParam({c.label}_ID, {p.minimum}f, {p.maximum}f, '
                    f'{p.default}f, "{p.name}");'
                )
    for c in audio_in_comps:
        cfg_lines.append(f'        configInput({c.label}_ID, "{c.label}");')
    for c in output_comps:
        cfg_lines.append(f'        configOutput({c.label}_ID, "{c.label}");')
    config_block = "\n".join(cfg_lines)

    # Previous-param cache (only send on change)
    prev_param_decl = (
        f"    float _prevParam[{max(n_knobs, 1)}] = {{}};"
    )
    prev_param_init = (
        f"        // Initialize _prevParam to an impossible value (-1e9f) so the very first\\n"
        f"        // process block forces a sync of the current VCV knob states to the DSP.\\n"
        f"        for (int i = 0; i < {max(n_knobs, 1)}; i++) _prevParam[i] = -1e9f;"
    )

    if polyphony:
        # Contexts array
        ctx_decl = f"    {info.class_name} *_ctx[16] = {{}};"
        ctx_init = f"        for (int v = 0; v < 16; v++) _ctx[v] = new {info.class_name}(APP->engine->getSampleRate());"
        ctx_del  = f"        for (int v = 0; v < 16; v++) delete _ctx[v];"
        ctx_sr   = f"        for (int v = 0; v < 16; v++) {{\n            auto *next = new {info.class_name}(e.sampleRate);\n            delete _ctx[v];\n            _ctx[v] = next;\n        }}"

        # Polyphonic Block buffers
        inbuf_decl  = (f"    alignas(32) float _inBuf [{max(n_ai, 1)}][16][BLOCK] = {{}};"
                       if n_ai  > 0 else "    // no audio inputs")
        outbuf_decl = (f"    alignas(32) float _outBuf[{max(n_ao, 1)}][16][BLOCK] = {{}};"
                       if n_ao > 0 else "    // no audio outputs")

        # Per-block param logic sends to ALL active contexts
        param_send_lines = []
        sync_lines = []
        for i, p in enumerate(in_p):
            lbl  = _param_label(p)
            hash_const = f"HASH_{lbl}"
            send_call_base = _send_call(api, hash_const, "val")
            send_call = send_call_base.replace("_ctx->", "_ctx[v]->")
            
            # Sync call for wake-up
            sync_call_base = _send_call(api, hash_const, f"_prevParam[{i}]")
            sync_call = sync_call_base.replace("_ctx->", "_ctx[v]->")
            sync_lines.append(f"                    {sync_call};")
            
            is_trigger = getattr(p, "ui_type", "") == "trigger"
            if is_trigger:
                condition = f"val > 0.0f && _prevParam[{i}] == 0.0f"
            else:
                condition = f"std::fabs(val - _prevParam[{i}]) > 1e-6f"

            param_send_lines.append(
                f"            {{\n"
                f"                float val = rack::math::clamp(\n"
                f"                    params[{lbl}_ID].getValue(),\n"
                f"                    {p.minimum}f, {p.maximum}f);\n"
                f"                if ({condition}) {{\n"
                f"                    _prevParam[{i}] = val;\n"
                f"                    for (int v = 0; v < activeVoices; v++) {{\n"
                f"                        {send_call};\n"
                f"                    }}\n"
                f"                }}\n"
                f"                else if (std::fabs(val - _prevParam[{i}]) > 1e-6f) {{\n"
                f"                    _prevParam[{i}] = val;\n"
                f"                }}\n"
                f"            }}"
            )
            
        sync_block = (
            "            if (activeVoices > _prevActiveVoices) {\n"
            "                for (int v = _prevActiveVoices; v < activeVoices; v++) {\n"
            + ("\n".join(sync_lines) if sync_lines else "                    // no params to sync") + "\n"
            "                }\n"
            "            }\n"
            "            _prevActiveVoices = activeVoices;"
        )
        param_send_block = sync_block + "\n\n" + ("\n".join(param_send_lines) if param_send_lines else "            // (no input parameters)")

        # Input fill: Check all inputs for max channels.
        sorted_inputs = sorted(audio_in_comps, key=lambda c: c.index)
        in_fill_lines = "        int activeVoices = 1;\n"
        in_fill_lines += "        for (int i = 0; i < NUM_INPUT_IDS; i++) {\n"
        in_fill_lines += "            int c = inputs[i].getChannels();\n"
        in_fill_lines += "            if (c > activeVoices) activeVoices = c;\n"
        in_fill_lines += "        }\n"
        in_fill_lines += "        for (int v = 0; v < activeVoices; v++) {\n"
        if sorted_inputs:
            in_fill_lines += "\n".join(
                f"            _inBuf[{c.index}][v][_blkPos] = rack::math::clamp(inputs[{c.label}_ID].getPolyVoltage(v), -12.0f, 12.0f);"
                for c in sorted_inputs
            )
        else:
            in_fill_lines += "            // (no audio inputs)"
        in_fill_lines += "\n        }"

        # Process call loop
        process_lines = []
        process_lines.append(f"            for (int v = 0; v < activeVoices; v++) {{")
        if api.process_sig == "float_ptr_ptr":
            if n_ai > 0:
                process_lines.append(f"                float* _ip[{n_ai}];")
                process_lines.append(f"                for (int c = 0; c < {n_ai}; c++) _ip[c] = _inBuf[c][v];")
            else:
                process_lines.append("                float** _ip = nullptr;")
            if n_ao > 0:
                process_lines.append(f"                float* _op[{n_ao}];")
                process_lines.append(f"                for (int c = 0; c < {n_ao}; c++) _op[c] = _outBuf[c][v];")
            else:
                process_lines.append("                float** _op = nullptr;")
            process_lines.append(f"                _ctx[v]->process(_ip, _op, BLOCK);")
        else:
            if n_ai > 0:
                process_lines.append(f"                const float* _ip[{n_ai}];")
                process_lines.append(f"                for (int c = 0; c < {n_ai}; c++) _ip[c] = _inBuf[c][v];")
            else:
                process_lines.append("                const float** _ip = nullptr;")
            if n_ao > 0:
                process_lines.append(f"                float* _op[{n_ao}];")
                process_lines.append(f"                for (int c = 0; c < {n_ao}; c++) _op[c] = _outBuf[c][v];")
            else:
                process_lines.append("                float** _op = nullptr;")
            process_lines.append(f"                _ctx[v]->process((const float* const*)_ip, (float* const*)_op, BLOCK);")
        process_lines.append(f"            }}")
        process_call = "\n".join(process_lines)

        # Output read loop
        sorted_audio_outs = sorted((c for c in output_comps if c.index < n_ao), key=lambda c: c.index)
        out_read_lines = "\n".join(
            f"        outputs[{c.label}_ID].setChannels(activeVoices);"
            for c in sorted_audio_outs
        )
        out_read_lines += "\n        for (int v = 0; v < activeVoices; v++) {\n"
        if sorted_audio_outs:
            out_read_lines += "\n".join(
                f"            outputs[{c.label}_ID].setVoltage(rack::math::clamp(_outBuf[{c.index}][v][_blkPos], -12.0f, 12.0f), v);"
                for c in sorted_audio_outs
            )
        else:
            out_read_lines += "            // (no audio outputs)"
        out_read_lines += "\n        }"
        
        ctx_check = "if (!_ctx[0]) return;"

    else:
        # Mono/Stereo (current behavior)
        ctx_decl = f"    {info.class_name} *_ctx = nullptr;"
        ctx_init = f"        _ctx = new {info.class_name}(APP->engine->getSampleRate());"
        ctx_del  = f"        delete _ctx;"
        ctx_sr   = f"        auto *next = new {info.class_name}(e.sampleRate);\n        delete _ctx;\n        _ctx = next;"

        # Block buffer declarations
        inbuf_decl  = (f"    alignas(32) float _inBuf [{max(n_ai, 1)}][BLOCK] = {{}};"
                       if n_ai  > 0 else "    // no audio inputs")
        outbuf_decl = (f"    alignas(32) float _outBuf[{max(n_ao, 1)}][BLOCK] = {{}};"
                       if n_ao > 0 else "    // no audio outputs")

        # Per-block param logic
        param_send_lines = []
        for i, p in enumerate(in_p):
            lbl  = _param_label(p)
            hash_const = f"HASH_{lbl}"
            send = _send_call(api, hash_const, "val")
            is_trigger = getattr(p, "ui_type", "") == "trigger"
            if is_trigger:
                condition = f"val > 0.0f && _prevParam[{i}] == 0.0f"
            else:
                condition = f"std::fabs(val - _prevParam[{i}]) > 1e-6f"

            param_send_lines.append(
                f"            {{\n"
                f"                float val = rack::math::clamp(\n"
                f"                    params[{lbl}_ID].getValue(),\n"
                f"                    {p.minimum}f, {p.maximum}f);\n"
                f"                if ({condition}) {{\n"
                f"                    _prevParam[{i}] = val;\n"
                f"                    {send}\n"
                f"                }}\n"
                f"                else if (std::fabs(val - _prevParam[{i}]) > 1e-6f) {{\n"
                f"                    _prevParam[{i}] = val;\n"
                f"                }}\n"
                f"            }}"
            )
        param_send_block = "\n".join(param_send_lines) if param_send_lines else "            // (no input parameters)"

        # Input fill
        sorted_inputs = sorted(audio_in_comps, key=lambda c: c.index)
        if info.stereo_in and len(sorted_inputs) >= 2:
            L = sorted_inputs[0]  # IN_L, index 0
            R = sorted_inputs[1]  # IN_R, index 1
            stereo_block = (
                f"        {{\n"
                f"            float _vL = rack::math::clamp(inputs[{L.label}_ID].getVoltage(), -12.0f, 12.0f);\n"
                f"            float _vR = inputs[{R.label}_ID].isConnected()\n"
                f"                      ? rack::math::clamp(inputs[{R.label}_ID].getVoltage(), -12.0f, 12.0f)\n"
                f"                      : _vL;  // mono -> stereo normalization\n"
                f"            _inBuf[{L.index}][_blkPos] = _vL;\n"
                f"            _inBuf[{R.index}][_blkPos] = _vR;\n"
            )
            rest = "\n".join(
                f"        _inBuf[{c.index}][_blkPos] = rack::math::clamp(inputs[{c.label}_ID].getVoltage(), -12.0f, 12.0f);"
                for c in sorted_inputs[2:]
            )
            in_fill_lines = stereo_block + ("\n" + rest if rest else "") + "\n        }"
        else:
            in_fill_lines = "\n".join(
                f"        _inBuf[{c.index}][_blkPos] = rack::math::clamp(inputs[{c.label}_ID].getVoltage(), -12.0f, 12.0f);"
                for c in sorted_inputs
            ) or "        // (no audio inputs)"

        # Process call
        process_call = _process_call(api, n_ai, n_ao)

        # Output read
        sorted_audio_outs = sorted((c for c in output_comps if c.index < n_ao), key=lambda c: c.index)
        out_read_lines = "\n".join(
            f"        outputs[{c.label}_ID].setVoltage(rack::math::clamp(_outBuf[{c.index}][_blkPos], -12.0f, 12.0f));"
            for c in sorted_audio_outs
        ) or "        // (no audio outputs)"

        ctx_check = "if (!_ctx) return;"

    custom_widget_structs = gen_custom_widget_structs(custom_widgets, menu_entries)
    addchild = _addchild_lines(components, mn, panel_hp, ui_text, custom_widgets)

    return f"""\
/**
 * {mn}.cpp  —  VCV Rack 2 module wrapping hvcc patch class '{info.class_name}'
 *
 * Auto-generated by hvcc2rack.py v2.  Re-running will overwrite.
 *
 * Panel      : {panel_hp} HP  ({panel_hp * HP_MM:.1f} mm)
 * Audio      : {n_ai} in / {n_ao} out
 * Params in  : {n_knobs}  ({", ".join(p.name for p in in_p) or "none"})
 * Block size : {block_size} samples
 * Signal flow: 1:1 voltage mapping (1V in Rack = 1.0 in PD). Hard clamped at ±12.0V.
 * Stereo I/O : {"IN_L/IN_R with mono normalization, OUT_L/OUT_R" if info.stereo_in else "flat (IN_1…N, OUT_1…N)"}
 *
 * Detected Heavy API
 *   process sig : {api.process_sig}
 *   send func   : {api.send_func}
 *
 * If the module fails to compile on the first try, the most common fixes are:
 *   1. Add Heavy runtime include path to Makefile FLAGS (see TODO there)
 *   2. Cast process() pointer args — see comment inside process()
 *   3. Swap sendFloatToReceiver for sendMessageToReceiver (or vice-versa)
 */

#include <cmath>
#include <string>
#include "plugin.hpp"
// Heavy context — adjust path if your directory structure differs
#include "{info.header_file}"

// ─────────────────────────────────────────────────────────────────────────────

struct StepQuantity : rack::engine::ParamQuantity {{
    float stepSize = 1.0f;
    void setValue(float v) override {{
        if (stepSize > 0.0f) {{
            float mn = getMinValue();
            v = mn + std::round((v - mn) / stepSize) * stepSize;
        }}
        rack::engine::ParamQuantity::setValue(v);
    }}
}};

struct {mn}Module : rack::Module {{

    // ── Processing block size ─────────────────────────────────────────────────
    // Change this to tune latency vs overhead.
    // BLOCK=1 is functionally correct but very inefficient.
    // BLOCK=64 @ 48kHz ≈ 1.3 ms latency — recommended default.
#ifndef BLOCK_SIZE
    static constexpr int BLOCK = {block_size};
#else
    static constexpr int BLOCK = BLOCK_SIZE;
#endif

    // ── Audio I/O channel counts ──────────────────────────────────────────────
    static constexpr int N_AI = {n_ai};
    static constexpr int N_AO = {n_ao};

    static_assert(BLOCK <= 512,
        "BLOCK > 512 risks stack overflow on some platforms; "
        "use dynamic allocation or reduce block size.");

    // ── Heavy receiver hashes ─────────────────────────────────────────────────
{hash_block}

    // ── Enum IDs ──────────────────────────────────────────────────────────────
    enum ParamId {{
{param_enum}
    }};

    enum InputId {{
{input_enum}
    }};

    enum OutputId {{
{output_enum}
    }};

    enum LightId {{
        NUM_LIGHT_IDS   // extend here if you add LED indicators
    }};

    // ── Heavy context ─────────────────────────────────────────────────────────
{ctx_decl}

    // ── Block processing buffers ──────────────────────────────────────────────
{inbuf_decl}
{outbuf_decl}
    int _blkPos = 0;    // current write/read position within the block
    int _prevActiveVoices = 1; // track polyphony changes for wake-up sync

    // ── Param change detection (only send to Heavy when value changes) ─────────
{prev_param_decl}
    // ─────────────────────────────────────────────────────────────────────────

    {mn}Module() {{
        config(NUM_PARAM_IDS, NUM_INPUT_IDS, NUM_OUTPUT_IDS, NUM_LIGHT_IDS);
{config_block}

{ctx_init}
{prev_param_init}
    }}

    ~{mn}Module() {{
{ctx_del}
    }}

    // onSampleRateChange() is called on the audio thread in Rack 2 —
    // no mutex needed; process() cannot run concurrently with this.
    // NOTE: onSampleRateChange() re-instantiates the Heavy context,
    //       which RESETS all DSP state (delays, envelopes, etc.).
    //       Rack rarely changes sample rate at runtime, but be aware.
    void onSampleRateChange(const SampleRateChangeEvent &e) override {{
{ctx_sr}
{prev_param_init}
    }}

    void process(const ProcessArgs & /*args*/) override {{
        {ctx_check}

        // ── 1. Fill input audio buffer ─────────────────────────────────────
{in_fill_lines}

        // ── 2. Read output audio from previous-block buffer ────────────────
        //       This introduces BLOCK samples of latency (~{(block_size/48000)*1000:.1f} ms @ 48kHz).
{out_read_lines}

        // ── 3. Advance block position; process a full block when ready ──────
        if (++_blkPos >= BLOCK) {{
            _blkPos = 0;

            // ── 3a. Send changed param values to Heavy ─────────────────────
            //        Sent once per block (not per sample) right before process()
            //        so Heavy's input queue is in a stable state.
{param_send_block}

{process_call}
        }}

    }}
}};

// ─────────────────────────────────────────────────────────────────────────────
// Widget — headless (no SVG bundled)
// ─────────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────────
struct TextLabel : rack::widget::TransparentWidget {{
    std::string text;
    float fontSizeMm;
    TextLabel(rack::math::Vec pos, std::string text, float fontSizeMm = 2.4f) {{
        this->box.pos = pos;
        this->box.size = rack::mm2px(rack::math::Vec(20.f, 5.f));
        this->text = text;
        this->fontSizeMm = fontSizeMm;
    }}
    void draw(const rack::widget::Widget::DrawArgs& args) override {{
        std::shared_ptr<rack::window::Font> font = APP->window->uiFont;
        if (font) {{
            nvgFontSize(args.vg, rack::mm2px(fontSizeMm));
            nvgFontFaceId(args.vg, font->handle);
            bool isDark = rack::settings::preferDarkPanels;
            if (isDark) {{
                nvgFillColor(args.vg, nvgRGBA(255, 255, 255, 255));
            }} else {{
                nvgFillColor(args.vg, nvgRGBA(0, 0, 0, 255));
            }}
            nvgTextAlign(args.vg, NVG_ALIGN_CENTER | NVG_ALIGN_TOP);
            nvgText(args.vg, 0, 0, text.c_str(), nullptr);
        }}
    }}
}};
{custom_widget_structs}struct {mn}Widget : rack::ModuleWidget {{
    explicit {mn}Widget({mn}Module *module) {{
        setModule(module);

        // Explicitly set panel size so layout works even without an SVG.
        // (fix: box.size must be set before addParam/addInput/addOutput)
        box.size = rack::Vec({panel_hp} * rack::app::RACK_GRID_WIDTH, rack::app::RACK_GRID_HEIGHT);

        // Rack SDK >= 2.4 supports setting both light and dark panels.
        setPanel(rack::createPanel(
            rack::asset::plugin(pluginInstance, "res/{mn}.svg"),
            rack::asset::plugin(pluginInstance, "res/{mn}-dark.svg")
        ));

        // Corner screws
        addChild(rack::createWidget<rack::ScrewSilver>(
            rack::Vec(rack::app::RACK_GRID_WIDTH, 0)));
        addChild(rack::createWidget<rack::ScrewSilver>(
            rack::Vec(box.size.x - 2 * rack::app::RACK_GRID_WIDTH, 0)));
        addChild(rack::createWidget<rack::ScrewSilver>(
            rack::Vec(rack::app::RACK_GRID_WIDTH, rack::app::RACK_GRID_HEIGHT - rack::app::RACK_GRID_WIDTH)));
        addChild(rack::createWidget<rack::ScrewSilver>(
            rack::Vec(box.size.x - 2 * rack::app::RACK_GRID_WIDTH,
                      rack::app::RACK_GRID_HEIGHT - rack::app::RACK_GRID_WIDTH)));

        // ── Components (mm positions -> pixels via mm2px) ───────────────────
{addchild}
    }}
}};

// ─────────────────────────────────────────────────────────────────────────────

rack::Model *model{mn} =
    rack::createModel<{mn}Module, {mn}Widget>("{mn}");
"""


def gen_makefile(module_name: str, hvcc_src_rel: str, block_size: int, hvcc_dir: Path) -> str:
    runtime_headers_present = any(
        (hvcc_dir / name).exists()
        for name in ("HeavyContext.hpp", "HvLightPipe.h", "HeavyContext.h")
    )
    if runtime_headers_present:
        runtime_flags = f"FLAGS += -I{hvcc_src_rel}"
    else:
        runtime_flags = (
            f"# TODO: Heavy runtime headers (HeavyContext.hpp, HvLightPipe.h, etc.)\n"
            f"# were NOT found in your hvcc output directory.\n"
            f"# You may need to add the path to the hvcc Python package's static/ folder:\n"
            f"#   FLAGS += -I<venv>/lib/pythonX.Y/site-packages/hvcc/generators/ir2c/static/\n"
            f"FLAGS += -I{hvcc_src_rel}"
        )

    return f"""\
# Makefile — VCV Rack 2 plugin (generated by hvcc2rack.py v2)
#
# Prerequisites
# ─────────────
#   export RACK_DIR=/path/to/Rack-SDK-2.x.y
#
# Usage
# ─────
#   make           build .so/.dylib/.dll
#   make clean
#   make dist      create distributable zip (needs plugin.json)
#
# After first generation:
#   1. Copy hvcc C output (Heavy_*.cpp, Heavy_*.h) into ./{hvcc_src_rel}/
#   2. Add Heavy RUNTIME header path to FLAGS below
#   3. Create res/{module_name}.svg (or strip setPanel() from the widget)
#   4. Create plugin.json in this directory
#
# Note on hvcc compiler warnings:
#   If you see "Warning pd2hv: [s core_dacN ...] This object has no inlet
#   connections. It does nothing and will be removed." — THIS IS NORMAL.
#   Output jack labels are purely for the generator. To silence the warning,
#   connect a [loadbang] to the send object in your patch.

RACK_DIR ?= ../Rack-SDK

# ── Plugin sources ────────────────────────────────────────────────────────────
SOURCES += src/plugin.cpp
SOURCES += src/{module_name}.cpp

# ── hvcc-generated sources ────────────────────────────────────────────────────
# hvcc can emit .c (C99) or .cpp depending on -g flag and version.
# Both are included here — the compiler picks based on extension.
SOURCES += $(wildcard {hvcc_src_rel}/*.cpp)
SOURCES += $(wildcard {hvcc_src_rel}/*.c)

# ── Include paths ─────────────────────────────────────────────────────────────
FLAGS += -I{hvcc_src_rel}

{runtime_flags}

# ── Optional: SIMD / release optimisations ────────────────────────────────────
# Uncomment for production builds (requires AVX-capable CPU):
# FLAGS += -DHV_SIMD_AVX -DNDEBUG
#
# Safer default (SSE2 is baseline for x86-64):
# FLAGS += -DHV_SIMD_SSE -DNDEBUG

# ── Block size (must match BLOCK constant in {module_name}.cpp) ───────────────
# You can also pass it here instead of hard-coding in the C++:
# FLAGS += -DBLOCK_SIZE={block_size}

# ── Distributables ────────────────────────────────────────────────────────────
DISTRIBUTABLES += res

# ── Rack SDK (must be last two includes) ─────────────────────────────────────
include $(RACK_DIR)/arch.mk
include $(RACK_DIR)/plugin.mk
"""


# ─────────────────────────────────────────────────────────────────────────────
# SVG panel generator
# ─────────────────────────────────────────────────────────────────────────────

def gen_panel_svg(module_name: str, panel_hp: int,
                  bg_color: str = "#E8E8E8", fg_color: str = "#000000") -> str:
    """
    Generate a blank VCV Rack 2 SVG panel (light or dark).
    No component markers — the actual Rack widgets and TextLabel handle all visuals.
    """
    W = panel_hp * HP_MM
    H = PANEL_H_MM
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     width="{W:.3f}mm" height="{H:.3f}mm"\n'
        f'     viewBox="0 0 {W:.3f} {H:.3f}">\n'
        f'  <rect width="{W:.3f}" height="{H:.3f}" fill="{bg_color}"/>\n'
        f'  <rect x="0" y="0" width="{W:.3f}" height="0.6" fill="{fg_color}"/>\n'
        f'  <rect x="0" y="{H-0.6:.3f}" width="{W:.3f}" height="0.6" fill="{fg_color}"/>\n'
        f'</svg>\n'
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def generate_all(info: PatchInfo, panel_hp: int, components: List[ComponentPos],
                 block_size: int, ui_text: str, polyphony: bool,
                 hvcc_src_rel: str, hvcc_dir: Path, custom_widgets: Optional[CustomWidgets],
                 menu_entries: Optional[Dict[str, List[str]]] = None) -> Dict[str, str]:
    files = {
        "src/plugin.hpp": gen_plugin_hpp(info.name),
        f"src/plugin.cpp": gen_plugin_cpp(info.name, info.name, info.name),
        f"src/{info.name}.cpp": gen_module_cpp(info, panel_hp, components, block_size, ui_text, polyphony, custom_widgets, menu_entries),
        "Makefile": gen_makefile(info.name, hvcc_src_rel, block_size, hvcc_dir),
    }
    
    if not (custom_widgets and custom_widgets.panel):
        files[f"res/{info.name}.svg"] = gen_panel_svg(info.name, panel_hp, bg_color="#E8E8E8", fg_color="#000000")
        files[f"res/{info.name}-dark.svg"] = gen_panel_svg(info.name, panel_hp, bg_color="#1A1A1A", fg_color="#CCCCCC")
        
    return files
