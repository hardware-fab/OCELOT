import argparse
import ast
import math
import operator
import re
from dataclasses import dataclass


# Dictionary to map component types to new models
model_map = {
    'nch':     'sky130_fd_pr__nfet_01v8',
    'pch':     'sky130_fd_pr__pfet_01v8',
    'nch_lvt': 'sky130_fd_pr__nfet_01v8_lvt',
    'pch_lvt': 'sky130_fd_pr__pfet_01v8_lvt',
    'cap':     'sky130_fd_pr__cap_mim_m3_2',
    'rgen':    'sky130_fd_pr__res_generic_l1',
    'rpoly':   'sky130_fd_pr__res_generic_po',

    'ne':    'sky130_fd_pr__nfet_01v8',
    'pe':    'sky130_fd_pr__pfet_01v8',
    'nel':   'sky130_fd_pr__nfet_01v8_lvt',
    'pel':   'sky130_fd_pr__pfet_01v8_lvt',
    'cmm5t': 'sky130_fd_pr__cap_mim_m3_2',
    'rnli1':  'sky130_fd_pr__res_generic_l1',
    'rnp1':  'sky130_fd_pr__res_generic_po',

    'sky130_fd_pr__nfet_01v8':      'sky130_fd_pr__nfet_01v8',
    'sky130_fd_pr__pfet_01v8':      'sky130_fd_pr__pfet_01v8',
    'sky130_fd_pr__nfet_01v8_lvt':  'sky130_fd_pr__nfet_01v8_lvt',
    'sky130_fd_pr__pfet_01v8_lvt':  'sky130_fd_pr__pfet_01v8_lvt',
    'sky130_fd_pr__cap_mim_m3_2':   'sky130_fd_pr__cap_mim_m3_2',
    'sky130_fd_pr__res_generic_l1': 'sky130_fd_pr__res_generic_l1',
    'sky130_fd_pr__res_generic_po': 'sky130_fd_pr__res_generic_po',
    'sky130_fd_pr__res_xhigh_po_5p73':   'sky130_fd_pr__res_xhigh_po_5p73',
    'sky130_fd_pr__cap_mim_m3_1':   'sky130_fd_pr__cap_mim_m3_1',
}


SPICE_MULTIPLIERS = {
    't': 1e12,
    'g': 1e9,
    'meg': 1e6,
    'k': 1e3,
    'm': 1e-3,
    'u': 1e-6,
    'n': 1e-9,
    'p': 1e-12,
    'f': 1e-15,
}


SAFE_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
SAFE_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}
SAFE_FUNCTIONS = {
    'abs': abs,
    'min': min,
    'max': max,
    'round': round,
    'int': int,
    'float': float,
    'ceil': math.ceil,
    'floor': math.floor,
}


def split_tokens(line):
    """Split a SPICE line while stripping inline comments."""
    line = line.split(';', 1)[0]
    tokens = []
    token = []
    brace_depth = 0
    quote = None

    for char in line.strip():
        if quote:
            token.append(char)
            if char == quote:
                quote = None
            continue

        if char in ("'", '"'):
            quote = char
            token.append(char)
            continue

        if char == '{':
            brace_depth += 1
            token.append(char)
            continue

        if char == '}':
            brace_depth = max(0, brace_depth - 1)
            token.append(char)
            continue

        if char.isspace() and brace_depth == 0:
            if token:
                tokens.append(''.join(token))
                token = []
            continue

        token.append(char)

    if token:
        tokens.append(''.join(token))

    return tokens


@dataclass
class Subckt:
    name: str
    pins: list
    params: list
    body: list


def split_params(tokens):
    first_param = next((i for i, token in enumerate(tokens) if '=' in token), len(tokens))
    return tokens[:first_param], tokens[first_param:]


def split_subckt_pins_params(tokens):
    """Split .subckt header tokens into pins and SPICE-style parameter assignments."""
    lowered = [token.lower() for token in tokens]
    for marker in ('parameters', 'params:', 'param:'):
        if marker in lowered:
            idx = lowered.index(marker)
            return tokens[:idx], tokens[idx + 1:]

    return split_params(tokens)


def parse_value(value):
    value = normalize_expression(value)
    match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)([a-zA-Z]+)?', value)
    if not match:
        return None

    number, suffix = match.groups()
    multiplier = 1.0
    if suffix:
        multiplier = SPICE_MULTIPLIERS.get(suffix.lower())
        if multiplier is None:
            return None

    return float(number) * multiplier


def normalize_expression(value):
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    if len(value) >= 2 and value[0] == '{' and value[-1] == '}':
        value = value[1:-1].strip()
    return value


def replace_engineering_literals(expr):
    number = r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
    suffixes = '|'.join(sorted((re.escape(key) for key in SPICE_MULTIPLIERS), key=len, reverse=True))
    pattern = re.compile(rf'(?<![A-Za-z0-9_])({number})({suffixes})\b', re.IGNORECASE)

    def repl(match):
        return repr(float(match.group(1)) * SPICE_MULTIPLIERS[match.group(2).lower()])

    return pattern.sub(repl, expr)


def resolve_value(value, values, stack=None):
    direct = parse_value(value)
    if direct is not None:
        return direct

    expr = replace_engineering_literals(normalize_expression(value))
    stack = stack or set()
    tree = ast.parse(expr, mode='eval')

    def eval_node(node):
        if isinstance(node, ast.Expression):
            return eval_node(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant in expression '{expr}'")
        if isinstance(node, ast.Name):
            key = node.id.lower()
            if key not in values or key in stack:
                raise ValueError(f"Unknown parameter '{node.id}' in expression '{expr}'")
            return resolve_value(values[key], values, stack | {key})
        if isinstance(node, ast.BinOp) and type(node.op) in SAFE_BINARY_OPS:
            return SAFE_BINARY_OPS[type(node.op)](eval_node(node.left), eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_UNARY_OPS:
            return SAFE_UNARY_OPS[type(node.op)](eval_node(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.func.id](*[eval_node(arg) for arg in node.args])
        raise ValueError(f"Unsupported expression '{expr}'")

    return eval_node(tree)


def format_numeric(value):
    return f"{value:.12g}"


def format_dimension(value):
    numeric = parse_value(value)
    if numeric is None:
        return value
    return f"{numeric * 1e6:.3f}"


def param_dict(params):
    parsed = {}
    for param in params:
        if '=' not in param:
            continue
        key, value = param.split('=', 1)
        parsed[key.lower()] = value
    return parsed


def substitute_params(params, values):
    substituted = []
    for param in params:
        if '=' not in param:
            continue
        key, value = param.split('=', 1)
        try:
            value = format_numeric(resolve_value(value, values))
        except (SyntaxError, ValueError):
            value = values.get(normalize_expression(value).lower(), value)
        substituted.append(f"{key}={value}")
    return substituted


def render_params(params, convert_dimensions=False):
    rendered = []
    for param in params:
        if '=' not in param:
            continue
        key, value = param.split('=', 1)
        if convert_dimensions and key.lower() in {'l', 'w'}:
            value = format_dimension(value)
        rendered.append(f"{key}={value}")
    return rendered


def parse_subckt(tokens):
    name = tokens[1]
    pins, params = split_subckt_pins_params(tokens[2:])
    return name, pins, params


def convert_mos(tokens):
    if len(tokens) < 7:
        return []

    name = tokens[0]
    nets = tokens[1:5]
    model = model_map.get(tokens[5], tokens[5])
    params = tokens[6:]
    params_by_name = param_dict(params)
    nf = params_by_name.get('nf', '1')

    numeric_nf = parse_value(nf)
    if numeric_nf is None or not numeric_nf.is_integer():
        instance_name = 'X' + name[1:]
        return [f"{instance_name} {' '.join(nets)} {model} " + ' '.join(render_params(params, convert_dimensions=True))]

    converted_params = [param for param in render_params(params, convert_dimensions=True) if not param.lower().startswith('nf=')]
    for param in converted_params:
        if param.lower().startswith('w'):
            param_key, param_value = param.split('=', 1)
            numeric_value = parse_value(param_value)
            param_value_str = str(numeric_value/numeric_nf) if numeric_value is not None else param_value
            converted_params[converted_params.index(param)] = f"{param_key}={param_value_str}"
            i = 0
    return [
        f"X{name[1:]}_{nf_itr} {' '.join(nets)} {model} " + ' '.join(converted_params)
        for nf_itr in range(int(numeric_nf))
    ]


def convert_cap(tokens, cap_index):
    head, params = split_params(tokens[1:])
    if len(head) < 3:
        return None

    nets = head[:-1]
    model = model_map.get(head[-1], head[-1])
    return f"X{cap_index} {' '.join(nets)} {model} " + ' '.join(render_params(params, convert_dimensions=True))


def convert_res(tokens):
    head, params = split_params(tokens[1:])
    if len(head) < 3:
        return None

    nets = head[:-1]
    model = model_map.get(head[-1], head[-1])
    return f"{tokens[0]} {' '.join(nets)} {model} " + ' '.join(params)


def convert_subckt_instance(tokens):
    head, params = split_params(tokens[1:])
    if len(head) < 1:
        return None

    nets = head[:-1]
    model = head[-1]
    line = f"{tokens[0]} {' '.join(nets)} {model}"
    if params:
        line += " " + ' '.join(params)
    return line


def sanitize_name(name):
    return re.sub(r'[^A-Za-z0-9_$]+', '_', name)


def load_netlist(input_file_path):
    with open(input_file_path, "r") as file:
        raw_lines = file.read().splitlines()

    lines = []
    for raw_line in raw_lines:
        stripped = raw_line.strip()
        if stripped.startswith('+') and lines:
            lines[-1] += ' ' + stripped[1:].strip()
        else:
            lines.append(raw_line)

    return lines


def parse_netlist(netlist):
    subckts = {}
    order = []
    current = None

    for raw_line in netlist:
        tokens = split_tokens(raw_line)
        if not tokens or tokens[0].startswith('*'):
            continue

        keyword = tokens[0].lower()
        if keyword == '.subckt':
            name, pins, params = parse_subckt(tokens)
            current = Subckt(name, pins, params, [])
            subckts[name] = current
            order.append(name)
        elif keyword == '.ends':
            current = None
        elif current is not None:
            current.body.append(tokens)

    return subckts, order


def resolve_net(net, pin_map, path):
    if net in pin_map:
        return pin_map[net]
    if net == '0':
        return net
    return f"{path}_{sanitize_name(net)}"


def prefix_instance_name(name, path):
    prefixed = f"{path}_{sanitize_name(name)}"
    if name.startswith('M'):
        return 'M' + prefixed
    if name.startswith('C'):
        return 'C' + prefixed
    if name.startswith('R'):
        return 'R' + prefixed
    if name.startswith('X'):
        return 'X' + prefixed
    return prefixed


def flatten_subckt(subckt_name, subckts, pin_map, param_values, path):
    subckt = subckts[subckt_name]
    flattened = []

    values = param_dict(subckt.params)
    values.update(param_values)

    for tokens in subckt.body:
        name = tokens[0]
        if name.startswith('M'):
            flattened_tokens = [prefix_instance_name(name, path)]
            flattened_tokens.extend(resolve_net(net, pin_map, path) for net in tokens[1:5])
            flattened_tokens.append(tokens[5])
            flattened_tokens.extend(substitute_params(tokens[6:], values))
            flattened.extend(convert_mos(flattened_tokens))
        elif name.startswith('C'):
            head, params = split_params(tokens[1:])
            if len(head) < 3:
                continue
            flattened_tokens = [prefix_instance_name(name, path)]
            flattened_tokens.extend(resolve_net(net, pin_map, path) for net in head[:-1])
            flattened_tokens.append(head[-1])
            flattened_tokens.extend(substitute_params(params, values))
            converted = convert_cap(flattened_tokens, prefix_instance_name(name, path)[1:])
            if converted:
                flattened.append(converted)
        elif name.startswith('XR') or name.startswith('R'):
            head, params = split_params(tokens[1:])
            if len(head) < 3:
                continue
            flattened_tokens = [prefix_instance_name(name, path)]
            flattened_tokens.extend(resolve_net(net, pin_map, path) for net in head[:-1])
            flattened_tokens.append(head[-1])
            flattened_tokens.extend(substitute_params(params, values))
            converted = convert_res(flattened_tokens)
            if converted:
                flattened.append(converted)
        elif name.startswith('X'):
            head, params = split_params(tokens[1:])
            if len(head) < 1:
                continue

            nets = head[:-1]
            model = head[-1]
            flattened_nets = [resolve_net(net, pin_map, path) for net in nets]
            instance_params = param_dict(substitute_params(params, values))

            if model in subckts:
                child = subckts[model]
                child_pin_map = {
                    pin: flattened_nets[idx]
                    for idx, pin in enumerate(child.pins)
                    if idx < len(flattened_nets)
                }
                child_path = f"{path}_{sanitize_name(name)}"
                flattened.extend(flatten_subckt(model, subckts, child_pin_map, instance_params, child_path))
            else:
                flattened_tokens = [prefix_instance_name(name, path)]
                flattened_tokens.extend(flattened_nets)
                flattened_tokens.append(model)
                flattened_tokens.extend(substitute_params(params, values))
                converted = convert_subckt_instance(flattened_tokens)
                if converted:
                    flattened.append(converted)

    return flattened


def process_file(input_file_path, output_file_path, output_top_name=None):
    output_lines = ["* Created from sp2lvs.py"]

    netlist = load_netlist(input_file_path)
    subckts, order = parse_netlist(netlist)
    if not order:
        raise ValueError(f"No subckt found in {input_file_path}")

    top = subckts[order[-1]]
    top_name = output_top_name or top.name
    line = f".subckt {top_name} {' '.join(top.pins)}".rstrip()
    if top.params:
        line += " " + ' '.join(top.params)
    output_lines.append(line)
    top_pin_map = {pin: pin for pin in top.pins}
    output_lines.extend(flatten_subckt(top.name, subckts, top_pin_map, {}, sanitize_name(top.name)))
    output_lines.append(".ends")

    with open(output_file_path, "w") as output_file:
        for line in output_lines:
            output_file.write(line + "\n")


def main():
    parser = argparse.ArgumentParser(description="Process a SPECTRE netlist file and prepares it for LVS.")
    parser.add_argument("input_file", help="The input SPECTRE netlist file")
    parser.add_argument("output_file", help="The output LVS netlist file")
    parser.add_argument("--top-name", help="Optional output subckt name")
    args = parser.parse_args()

    process_file(args.input_file, args.output_file, args.top_name)


if __name__ == "__main__":
    main()
