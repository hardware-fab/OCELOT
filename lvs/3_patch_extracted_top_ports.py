import argparse


def split_subckt_pins(tokens):
    lowered = [token.lower() for token in tokens]
    for marker in ("parameters", "params:", "param:"):
        if marker in lowered:
            return tokens[:lowered.index(marker)]

    first_param = next((i for i, token in enumerate(tokens) if "=" in token), len(tokens))
    return tokens[:first_param]


def parse_subckt_header(path, top_name):
    with open(path, "r") as file:
        for raw_line in file:
            tokens = raw_line.strip().split()
            if len(tokens) >= 2 and tokens[0].lower() == ".subckt" and tokens[1] == top_name:
                return split_subckt_pins(tokens[2:])
    raise ValueError(f"Could not find .subckt {top_name} in {path}")


def patch_extracted_top_ports(extracted_path, reference_path, top_name):
    pins = parse_subckt_header(reference_path, top_name)

    with open(extracted_path, "r") as file:
        lines = file.read().splitlines()

    patched = False
    output_lines = []
    for line in lines:
        tokens = line.strip().split()
        if len(tokens) >= 2 and tokens[0].lower() == ".subckt" and tokens[1] == top_name:
            output_lines.append(f".subckt {top_name} {' '.join(pins)}".rstrip())
            patched = True
        else:
            output_lines.append(line)

    if not patched:
        raise ValueError(f"Could not find .subckt {top_name} in {extracted_path}")

    with open(extracted_path, "w") as file:
        for line in output_lines:
            file.write(line + "\n")


def main():
    parser = argparse.ArgumentParser(description="Copy top-level LVS pins into a Magic extracted netlist.")
    parser.add_argument("extracted_netlist")
    parser.add_argument("reference_netlist")
    parser.add_argument("top_name")
    args = parser.parse_args()

    patch_extracted_top_ports(args.extracted_netlist, args.reference_netlist, args.top_name)


if __name__ == "__main__":
    main()
