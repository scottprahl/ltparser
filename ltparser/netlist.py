"""
Netlist generation for ltparser.

Handles conversion of parsed LTspice data to circuit netlists.
"""

import re
import pyparsing as pp
import networkx as nx
from .components import ComponentMatcher, node_key, rotate_point
from .transformations import NetlistTransformer
from .config import COMPONENTS_CONFIG


def apply_netlist_prefix(inst_name, kind):
    """
    Apply netlist prefix substitution based on component configuration.
    
    For components like op-amps where lcapy requires a specific prefix (e.g., 'E'),
    this replaces the LTspice InstName prefix with the configured netlist_prefix.
    
    Args:
        inst_name: Original instance name from LTspice (e.g., "U1")
        kind: Component type/symbol (e.g., "opamp", "Opamps/UniversalOpamp2")
    
    Returns:
        str: Modified instance name with correct prefix (e.g., "E1")
    
    Examples:
        apply_netlist_prefix("U1", "opamp") -> "E1"
        apply_netlist_prefix("U2", "Opamps/UniversalOpamp2") -> "E2"
        apply_netlist_prefix("R1", "res") -> "R1" (no change)
    """
    # Look up the component in config
    components_config = COMPONENTS_CONFIG.get("components", {})
    
    # Special case: simple "opamp" is stored as "Opamps/opamp" in config
    lookup_kind = kind
    if kind == "opamp":
        lookup_kind = "Opamps/opamp"
    
    # Check all component categories
    for category in ["two_terminal", "multi_terminal", "three_terminal"]:
        category_dict = components_config.get(category, {})
        if lookup_kind in category_dict:
            config = category_dict[lookup_kind]
            netlist_prefix = config.get("netlist_prefix")
            
            if netlist_prefix:
                # Extract the numeric suffix from inst_name (e.g., "U1" -> "1")
                match = re.match(r'^[A-Z]+(\d+)$', inst_name)
                if match:
                    number = match.group(1)
                    return f"{netlist_prefix}{number}"
    
    # No prefix substitution needed, return original name
    return inst_name


def ltspice_sine_parser(s):
    """Try and figure out offset, amplitude, and frequency from SINE(...)"""
    number = pp.Combine(
        pp.Optional(".") + pp.Word(pp.nums) + pp.Optional("." + pp.Optional(pp.Word(pp.nums)))
    )
    sine = pp.Literal("SINE(") + pp.Optional(number) * 3 + pp.Literal(")")

    parsed = sine.parseString(s)
    dc = 0.0
    amp = 1.0
    omega = 0.0

    if parsed[1] == ")":
        return dc, amp, omega

    dc = float(parsed[1])

    if parsed[2] == ")":
        return dc, amp, omega

    amp = float(parsed[2])

    if parsed[3] == ")":
        return dc, amp, omega

    omega = float(parsed[3])

    return dc, amp, omega


def _parse_prefixed_value(raw):
    """Parse an LTspice-style value with SI prefixes and optional units.

    Supports:
        - Plain numbers:       '10', '3.3', '1e-3'
        - Prefixes:
            'meg'  -> 1e6
            'k'    -> 1e3
            'm'    -> 1e-3
            'u', 'µ' -> 1e-6
            'n'    -> 1e-9
            'p'    -> 1e-12
            'f'    -> 1e-15
        - Optional units at end: A, V, F, H, Ω, etc. (ignored)

    Examples:
        '1m'   -> 0.001
        '1mA'  -> 0.001
        '3µ'   -> 3e-6
        '3uV'  -> 3e-6
        '2nF'  -> 2e-9
        '5nA'  -> 5e-9
        '10k'  -> 10000.0
        '1Meg' -> 1e6
    Returns:
        float, or None if parsing fails.
    """
    if raw is None:
        return None

    s = str(raw).strip()
    if not s:
        return None

    # Regex: [sign] number [optional exponent] [rest]
    # e.g.  "-3.3e-2mA" -> num_str="-3.3e-2", suffix="mA"
    m = re.match(r"^([+-]?\d*\.?\d*(?:[eE][+-]?\d+)?)(.*)$", s)
    if not m:
        return None

    num_str, suffix = m.groups()
    num_str = num_str.strip()
    suffix = suffix.strip()

    if num_str == "" or num_str in {"+", "-"}:
        return None

    try:
        base = float(num_str)
    except ValueError:
        return None

    # Default: no prefix
    multiplier = 1.0

    # Normalize suffix for prefix detection; keep original for units if you want.
    suffix_lower = suffix.lower()

    # Handle Meg (must come before single-letter prefixes)
    if suffix_lower.startswith("meg"):
        multiplier = 1e6
        # units = suffix[3:]  # ignore units
    elif suffix_lower.startswith("g"):
        multiplier = 1e9
        # units = suffix[1:]
    elif suffix_lower.startswith("k"):
        multiplier = 1e3
        # units = suffix[1:]
    elif suffix and suffix[0] in ("u", "µ"):
        multiplier = 1e-6
        # units = suffix[1:]
    elif suffix_lower.startswith("m"):
        multiplier = 1e-3
        # units = suffix[1:]
    elif suffix_lower.startswith("n"):
        multiplier = 1e-9
        # units = suffix[1:]
    elif suffix_lower.startswith("p"):
        multiplier = 1e-12
        # units = suffix[1:]
    elif suffix_lower.startswith("f"):
        multiplier = 1e-15
        # units = suffix[1:]
    else:
        # No recognized prefix; treat entire thing as just the number
        # (suffix may be empty or pure units like 'A' or 'V', which we ignore)
        pass

    return base * multiplier


class NetlistGenerator:
    """Generates netlists from parsed LTspice data."""

    def __init__(self, nodes_dict, parsed_data):
        """
        Initialize netlist generator.

        Args:
            nodes_dict: Dictionary mapping node keys to node numbers
            parsed_data: Parsed LTspice data
        """
        self.nodes = nodes_dict
        self.parsed = parsed_data
        self.netlist = ""
        self.graph = nx.Graph()
        self.component_matcher = ComponentMatcher(nodes_dict)

        # Configuration flags
        self._include_wire_directions = True
        self._minimal = False
        self._do_reorient_rlc = False
        
        # Component counters for independent numbering
        self.component_counters = {
            'AM': 0,  # Ammeter
            'VM': 0,  # Voltmeter
            'BAT': 0, # Battery
        }
    
    def get_next_component_number(self, prefix):
        """
        Get the next number for a component type that needs independent numbering.
        
        Args:
            prefix: Component prefix (e.g., 'AM', 'VM', 'BAT')
            
        Returns:
            int: Next number for this component type
        """
        if prefix in self.component_counters:
            self.component_counters[prefix] += 1
            return self.component_counters[prefix]
        return None

    def wire_to_netlist(self, line):
        """
        Convert a WIRE line to netlist format.

        Args:
            line: Parsed WIRE line [WIRE, x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = line[1:5]

        # Determine direction
        dx = x2 - x1
        dy = y2 - y1

        if abs(dx) > abs(dy):
            direction = "right" if dx > 0 else "left"
        else:
            direction = "down" if dy > 0 else "up"

        # Get node numbers
        n1 = self.nodes.get(node_key(x1, y1), "?")
        n2 = self.nodes.get(node_key(x2, y2), "?")

        # Make the wires all go right or down
        if direction == "up":
            n1, n2 = n2, n1
            direction = "down"
        if direction == "left":
            n1, n2 = n2, n1
            direction = "right"

        self.graph.add_edge(n1, n2)

        # Include direction hints based on mode
        in_minimal_mode = getattr(self, "_minimal", False)
        include_directions = getattr(self, "_include_wire_directions", False)

        if not in_minimal_mode and not include_directions:
            # Default: include directions in non-minimal mode
            self.netlist += f"W {n1} {n2}; {direction}\n"
        elif include_directions:
            # Explicitly requested directions
            self.netlist += f"W {n1} {n2}; {direction}\n"
        else:
            # Minimal mode or explicitly no directions
            self.netlist += f"W {n1} {n2}\n"

    def symbol_to_netlist(self, line):
        """
        Convert a SYMBOL line to netlist format.

        Args:
            line: Parsed SYMBOL line
        """
        first = list(line[0])
        if first[0] != "SYMBOL":
            return

        # Parse: SYMBOL kind x y direction
        kind = first[1]
        x, y = first[2], first[3]
        direction = first[4] if len(first) > 4 else "down"

        # Normalize direction from LTspice format to readable format
        # LTspice uses: R0=0°, R90=90°, R180=180°, R270=270°
        direction_map = {
            "R": "down",  # R or R0 = 0° = down
            "R0": "down",  # 0° = down
            "R90": "left",  # 90° CCW = left
            "R180": "up",  # 180° = up
            "R270": "right",  # 270° CCW = right
        }
        direction = direction_map.get(direction, direction)

        # Get component attributes
        attributes = {}
        for attr_line in line[1:]:
            if isinstance(attr_line, list) and len(attr_line) >= 2:
                if attr_line[0] == "SYMATTR":
                    attr_name = attr_line[1]
                    attr_value = attr_line[2].strip() if len(attr_line) > 2 else ""
                    attributes[attr_name] = attr_value

        inst_name = attributes.get("InstName", "?")
        value = attributes.get("Value", "")

        # Clean up value - remove unit suffixes like 'V', 'A' for sources
        # but keep 'k', 'M', 'meg' for multipliers
        kind_lower = kind.lower()
        is_voltage_source = (kind_lower.startswith("voltage") or 
                            "battery" in kind_lower)
        is_current_source = kind_lower.startswith("current")
        
        if value and (is_voltage_source or is_current_source):
            # Remove trailing V or A (voltage/current units)
            if value.endswith("V") or value.endswith("v"):
                value = value[:-1]
            elif value.endswith("A") or value.endswith("a"):
                value = value[:-1]

        # Match component nodes
        matched = self.component_matcher.match_node(x, y, kind, direction)

        # Generate netlist based on component type
        if kind == "Opamps/UniversalOpamp2":
            # 5-pin op-amp
            out = matched.get("out", "?")
            vee = matched.get("vee", "?")
            in_plus = matched.get("in_plus", "?")
            in_minus = matched.get("in_minus", "?")

            # Apply netlist prefix (U1 -> E1 for lcapy compatibility)
            inst_name = apply_netlist_prefix(inst_name, kind)
            
            self.netlist += f"{inst_name} {out} {vee} opamp {in_plus} {in_minus}\n"

        elif kind == "opamp":
            # 3-pin op-amp
            out = matched.get("out", "?")
            in_plus = matched.get("in_plus", "?")
            in_minus = matched.get("in_minus", "?")

            # Apply netlist prefix (U1 -> E1 for lcapy compatibility)
            inst_name = apply_netlist_prefix(inst_name, kind)
            
            self.netlist += f"{inst_name} {out} 0 opamp {in_plus} {in_minus}\n"

        elif kind.lower().startswith("res"):
            # Resistor
            n1 = matched.get("pin0", matched.get("n1", "?"))
            n2 = matched.get("pin1", matched.get("n2", "?"))

            # Determine direction for reorientation
            if direction == "left" and self._do_reorient_rlc:
                n1, n2 = n2, n1
                direction = "right"
            elif direction == "up" and self._do_reorient_rlc:
                n1, n2 = n2, n1
                direction = "down"

            mag = _parse_prefixed_value(value)
            if mag is not None:
                value = mag

            if self._minimal:
                self.netlist += f"{inst_name} {n1} {n2} {value}\n"
            else:
                self.netlist += f"{inst_name} {n1} {n2} {value}; {direction}\n"

        elif kind.lower().startswith("cap") or kind.lower().startswith("ind"):
            # Capacitor or Inductor
            prefix = "C" if kind.lower().startswith("cap") else "L"
            n1 = matched.get("pin0", matched.get("n1", "?"))
            n2 = matched.get("pin1", matched.get("n2", "?"))

            # Reorient if needed
            if direction == "left" and self._do_reorient_rlc:
                n1, n2 = n2, n1
                direction = "right"
            elif direction == "up" and self._do_reorient_rlc:
                n1, n2 = n2, n1
                direction = "down"

            mag = _parse_prefixed_value(value)
            if mag is not None:
                value = mag

            if self._minimal:
                self.netlist += f"{inst_name} {n1} {n2} {value}\n"
            else:
                self.netlist += f"{inst_name} {n1} {n2} {value}; {direction}\n"

        elif "battery" in kind.lower():
            # Battery (treated like voltage source but with BAT prefix)
            n1 = matched.get("pin0", matched.get("n1", "?"))
            n2 = matched.get("pin1", matched.get("n2", "?"))

            # Apply netlist prefix (V1 -> BAT1 for batteries)
            inst_name = apply_netlist_prefix(inst_name, kind)

            source_value = value
            ac_value = None

            # 1) Look for "AC <amp>" in Value2
            ac_attr = attributes.get("Value2", "")
            if ac_attr:
                parts = ac_attr.split()
                if parts and parts[0].lower() == "ac" and len(parts) > 1:
                    try:
                        ac_value = float(parts[1])
                    except ValueError:
                        pass

            # 2) If no AC attr, but Value is SINE(...), parse amplitude
            if (
                ac_value is None
                and isinstance(source_value, str)
                and source_value.upper().startswith("SINE(")
            ):
                try:
                    _dc, amp, _freq = ltspice_sine_parser(source_value)
                    ac_value = amp
                except Exception:
                    pass

            # 3) Build final value
            if ac_value is not None:
                # AC source: write as "ac <amp>"
                source_value = f"ac {ac_value:.6f}"
            else:
                # DC source: parse SI-prefixed magnitude, including units like A/V
                mag = _parse_prefixed_value(source_value)
                if mag is not None:
                    source_value = f"{mag:.6g}"

            if self._minimal:
                self.netlist += f"{inst_name} {n1} {n2} {source_value}\n"
            else:
                self.netlist += f"{inst_name} {n1} {n2} {source_value}; {direction}\n"

        elif kind.lower().startswith("voltage") or kind.lower().startswith("current"):
            # Voltage or current source
            n1 = matched.get("pin0", matched.get("n1", "?"))
            n2 = matched.get("pin1", matched.get("n2", "?"))

            source_value = value
            ac_value = None

            # 1) Look for "AC <amp>" in Value2
            ac_attr = attributes.get("Value2", "")
            if ac_attr:
                parts = ac_attr.split()
                if parts and parts[0].lower() == "ac" and len(parts) > 1:
                    try:
                        ac_value = float(parts[1])
                    except ValueError:
                        pass

            # 2) If no AC attr, but Value is SINE(...), parse amplitude
            if (
                ac_value is None
                and isinstance(source_value, str)
                and source_value.upper().startswith("SINE(")
            ):
                try:
                    _dc, amp, _freq = ltspice_sine_parser(source_value)
                    ac_value = amp
                except Exception:
                    pass

            # 3) Build final value
            if ac_value is not None:
                # AC source: write as "ac <amp>"
                source_value = f"ac {ac_value:.6f}"
            else:
                # DC source: parse SI-prefixed magnitude, including units like A/V
                mag = _parse_prefixed_value(source_value)
                if mag is not None:
                    source_value = f"{mag:.6g}"  # or "{mag:g}" if you prefer

            if self._minimal:
                self.netlist += f"{inst_name} {n1} {n2} {source_value}\n"
            else:
                self.netlist += f"{inst_name} {n1} {n2} {source_value}; {direction}\n"

        elif kind.lower() == "ammeter" or kind.lower().startswith("ammeter"):
            # Ammeter
            n1 = matched.get("pin0", matched.get("n1", "?"))
            n2 = matched.get("pin1", matched.get("n2", "?"))

            # Use independent numbering (AM1, AM2, ...)
            num = self.get_next_component_number('AM')
            inst_name = f"AM{num}"

            if self._minimal:
                self.netlist += f"{inst_name} {n1} {n2}\n"
            else:
                self.netlist += f"{inst_name} {n1} {n2}; {direction}\n"

        elif kind.lower() == "voltmeter" or kind.lower().startswith("voltmeter"):
            # Voltmeter
            n1 = matched.get("pin0", matched.get("n1", "?"))
            n2 = matched.get("pin1", matched.get("n2", "?"))

            # Use independent numbering (VM1, VM2, ...)
            num = self.get_next_component_number('VM')
            inst_name = f"VM{num}"

            if self._minimal:
                self.netlist += f"{inst_name} {n1} {n2}\n"
            else:
                self.netlist += f"{inst_name} {n1} {n2}; {direction}\n"

        else:
            # Generic two-terminal component
            n1 = matched.get("pin0", matched.get("n1", "?"))
            n2 = matched.get("pin1", matched.get("n2", "?"))

            if self._minimal:
                self.netlist += f"{inst_name} {n1} {n2} {value}\n"
            else:
                self.netlist += f"{inst_name} {n1} {n2} {value}; {direction}\n"

    def generate(
        self,
        use_named_nodes=True,
        include_wire_directions=True,
        minimal=False,
        use_net_extraction=False,
        reorient_rlc=True,
        renumber_nodes=True,
    ):
        """
        Generate netlist from parsed data.

        Args:
            use_named_nodes: Keep named nodes (True) or convert to numbers (False)
            include_wire_directions: Include direction hints for wires
            minimal: Only include components, no wires
            use_net_extraction: Use NetworkX for net extraction (handled externally)
            reorient_rlc: Reorient R/L/C to go right or down only
            renumber_nodes: Renumber nodes sequentially

        Returns:
            str: Generated netlist
        """
        self.netlist = ""
        self._include_wire_directions = include_wire_directions
        self._minimal = minimal
        self._do_reorient_rlc = reorient_rlc

        # Process parsed data
        for line in self.parsed:
            if line[0] == "WIRE":
                if not minimal:
                    self.wire_to_netlist(line)

            if isinstance(line[0], list):
                self.symbol_to_netlist(line)

        # Apply transformations
        if reorient_rlc and not minimal:
            self.netlist = NetlistTransformer.reorient_rlc(self.netlist)

        if not use_named_nodes:
            self.netlist, self.nodes = NetlistTransformer.convert_named_nodes_to_numbers(
                self.netlist, self.nodes
            )

        if renumber_nodes:
            self.netlist, self.nodes = NetlistTransformer.renumber_nodes_for_drawing(
                self.netlist, nodes_dict=self.nodes, parsed_data=self.parsed
            )

        return self.netlist