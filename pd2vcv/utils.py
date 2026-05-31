import re
from typing import List
from pd2vcv.models import HvParam, ComponentPos, HeavyApi, _CPP_RESERVED


def sanitize_identifier(name: str) -> str:
    """
    Convert an arbitrary hvcc receiver name into a valid C++ identifier.
    Rules:
      - Replace any non-alphanumeric char with '_'
      - Ensure first char is a letter or underscore (prepend 'p_' if digit)
      - Append '_' if the result collides with a C++ reserved word
      - Collapse consecutive underscores
    """
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    s = re.sub(r"_+", "_", s).strip("_") or "param"
    if s[0].isdigit():
        s = "p_" + s
    if s in _CPP_RESERVED:
        s = s + "_"
    return s


def deduplicate_safe_names(params: List[HvParam]) -> None:
    seen: dict[str, int] = {}
    for p in params:
        base = p.safe_name
        if base in seen:
            seen[base] += 1
            p.safe_name = f"{base}_{seen[base]}"
        else:
            seen[base] = 0


def _param_label(p: HvParam) -> str:
    return p.enum_label if p.enum_label else p.safe_name.upper()


def _enum_body(items: List[ComponentPos], terminal: str) -> str:
    lines = [f"        {c.label}_ID," for c in items]
    lines.append(f"        {terminal}")
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
