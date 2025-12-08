"""
Netlist transformations for ltparser.

Handles renumbering, reorientation, and other netlist transformations.
"""


class NetlistTransformer:
    """Handles transformations applied to netlists."""

    @staticmethod
    def convert_named_nodes_to_numbers(netlist, nodes_dict):
        """
        Convert named nodes like '+Vs' and '-Vs' to numbered nodes.

        This helps lcapy's drawing algorithm by avoiding named node clusters.

        Args:
            netlist: Current netlist string
            nodes_dict: Nodes dictionary

        Returns:
            tuple: (updated_netlist, updated_nodes_dict)
        """
        # Find the highest numbered node
        max_node = 0
        for value in nodes_dict.values():
            if isinstance(value, int) and value != 0:
                max_node = max(max_node, value)

        # Find all named nodes (strings that aren't ground)
        named_nodes = {}
        for key, value in nodes_dict.items():
            if isinstance(value, str) and value != "0":
                named_nodes[value] = value

        # Assign numbers to named nodes
        replacements = {}
        next_num = max_node + 1
        for name in named_nodes:
            replacements[name] = str(next_num)
            next_num += 1

        # Replace in netlist
        result = netlist
        for old_name, new_num in replacements.items():
            result = result.replace(f" {old_name};", f" {new_num};")
            result = result.replace(f" {old_name} ", f" {new_num} ")
            result = result.replace(f" {old_name}\n", f" {new_num}\n")

        # Update nodes dictionary
        new_nodes = {}
        for key, value in nodes_dict.items():
            if value in replacements:
                new_nodes[key] = int(replacements[value])
            else:
                new_nodes[key] = value

        return result, new_nodes

    @staticmethod
    def reorient_rlc(netlist):
        """
        Reorient resistors, capacitors, inductors, and wires to only go right or down.

        Components going left become right (with swapped nodes),
        and components going up become down (with swapped nodes).

        Args:
            netlist: Current netlist string

        Returns:
            str: Reoriented netlist
        """
        if not netlist:
            return netlist

        lines = netlist.strip().split("\n")
        reoriented_lines = []

        for line in lines:
            if not line.strip():
                continue

            parts = line.split()
            if len(parts) < 3:
                reoriented_lines.append(line)
                continue

            component_name = parts[0]
            is_rlc = (
                component_name.startswith("W")
                or component_name.startswith("R")
                or component_name.startswith("L")
                or component_name.startswith("C")
            )

            if not is_rlc:
                reoriented_lines.append(line)
                continue

            # Parse the line: "R1 node1 node2 value; direction"
            if ";" in line:
                main_part, direction_part = line.split(";", 1)
                direction = direction_part.strip()

                # Check if we need to reorient
                if direction in ("left", "up"):
                    # Swap nodes
                    main_parts = main_part.split()
                    if len(main_parts) >= 3:
                        # Swap node1 and node2
                        main_parts[1], main_parts[2] = main_parts[2], main_parts[1]

                        # Update direction
                        new_direction = "right" if direction == "left" else "down"

                        # Reconstruct line
                        new_line = " ".join(main_parts) + "; " + new_direction
                        reoriented_lines.append(new_line)
                    else:
                        reoriented_lines.append(line)
                else:
                    # Already right or down
                    reoriented_lines.append(line)
            else:
                # No direction specified
                reoriented_lines.append(line)

        return "\n".join(reoriented_lines) + "\n"

    @staticmethod
    def renumber_grounds(netlist, parsed_data=None):
        """
        Renumber ground nodes based on their locations.

        Determines if grounds are at the same location (single ground) or different
        locations (multiple grounds). Single ground stays as '0', multiple grounds
        get unique IDs '0_1', '0_2', etc.

        Args:
            netlist: Current netlist string
            parsed_data: Optional parsed LTspice data to determine ground locations

        Returns:
            tuple: (updated_netlist, is_single_ground)
        """
        if not netlist:
            return netlist, True

        # Count unique ground locations from parsed data if available
        if parsed_data is not None:
            ground_locations = set()
            for line in parsed_data:
                if isinstance(line, list) and len(line) > 0:
                    # Check for FLAG statements
                    if isinstance(line[0], list) and line[0][0] == "FLAG":
                        name = line[0][3] if len(line[0]) > 3 else None
                        if name == 0 or name == "0":
                            x, y = line[0][1], line[0][2]
                            ground_locations.add((x, y))

            single_ground = len(ground_locations) <= 1
        else:
            # Fallback: count ground occurrences in netlist
            ground_count = netlist.count(" 0;") + netlist.count(" 0 ") + netlist.count(" 0\n")
            single_ground = ground_count <= 1

        result = netlist

        # Mark each ground occurrence with unique ID
        ground_counter = 0
        lines = result.split("\n")
        new_lines = []

        for line in lines:
            if not line.strip():
                new_lines.append(line)
                continue

            parts = line.split()
            if len(parts) < 3:
                new_lines.append(line)
                continue

            comp = parts[0]

            # Determine which positions to check for ground
            # For op-amps: check positions 1, 2, 4, 5
            # For V/I sources: check positions 1, 2 only (position 3 is value!)
            # For other components: check positions 1, 2
            if comp.startswith("E") and len(parts) >= 6:
                positions = [1, 2, 4, 5]
            elif (comp.startswith("V") or comp.startswith("I")) and len(parts) >= 4:
                positions = [1, 2]  # Skip position 3 (value)
            else:
                positions = [1, 2]

            # Replace each ground occurrence
            parts_modified = parts[:]
            for pos in positions:
                if pos < len(parts) and parts[pos].rstrip(";") == "0":
                    ground_counter += 1
                    if parts[pos].endswith(";"):
                        parts_modified[pos] = f"0_{ground_counter}x;"
                    else:
                        parts_modified[pos] = f"0_{ground_counter}x"

            if parts_modified != parts:
                new_line = " ".join(parts_modified)
            else:
                new_line = line

            new_lines.append(new_line)

        result = "\n".join(new_lines)

        # If single ground, convert all 0_Nx to 0x
        if single_ground:
            result = result.replace("0_1x", "0x")
            # Also replace any other ground markers if present
            for i in range(2, ground_counter + 1):
                result = result.replace(f"0_{i}x", "0x")

        return result, single_ground

    @staticmethod
    def renumber_nodes(netlist, skip_grounds=True, nodes_dict=None):
        """
        Renumber non-ground nodes sequentially in order of first appearance.

        Args:
            netlist: Current netlist string (with grounds already marked with 'x')
            skip_grounds: If True, don't renumber ground nodes (they have 'x' already)
            nodes_dict: Optional dict mapping coordinate keys -> node IDs.
                        If provided, any node whose value matches an old ID will
                        be updated to the new ID during renumbering.

        Returns:
            str: Netlist with nodes renumbered sequentially
        """
        if not netlist:
            return netlist

        result = netlist
        next_node_num = 1

        while True:
            found_unmarked = False
            lines = result.split('\n')

            # 1) Find the next unmarked (non-x) node in node positions
            for line in lines:
                if not line.strip():
                    continue

                parts = line.split()
                if len(parts) < 3:
                    continue

                comp = parts[0]

                # Determine which positions are *node* fields
                if comp.startswith('E') and len(parts) >= 6:
                    node_positions = [1, 2, 4, 5]
                elif (comp.startswith('V') or comp.startswith('I')) and len(parts) >= 4:
                    # For sources, parts[3] is value; 1 and 2 are nodes
                    node_positions = [1, 2]
                else:
                    node_positions = [1, 2]

                for pos in node_positions:
                    if pos >= len(parts):
                        continue

                    node = parts[pos].rstrip(';')

                    # Skip if already marked with 'x' or is ground (0 / 0_)
                    if 'x' in node or (skip_grounds and (node == '0' or node.startswith('0_'))):
                        continue

                    # Found an unmarked node!
                    found_unmarked = True
                    new_node = f"{next_node_num}x"

                    # 2) Replace this node throughout the netlist, but only
                    #    in *node* positions (never in values)
                    new_lines = []
                    for check_line in result.split('\n'):
                        if not check_line.strip():
                            new_lines.append(check_line)
                            continue

                        check_parts = check_line.split()
                        if len(check_parts) < 3:
                            new_lines.append(check_line)
                            continue

                        check_comp = check_parts[0]

                        # Replaceable positions for this component type
                        if check_comp.startswith('E') and len(check_parts) >= 6:
                            replaceable_pos = [1, 2, 4, 5]
                        elif (check_comp.startswith('V') or check_comp.startswith('I')) and len(check_parts) >= 4:
                            replaceable_pos = [1, 2]  # do NOT touch value at index 3
                        else:
                            replaceable_pos = [1, 2]

                        modified = False
                        new_parts = check_parts[:]
                        for rpos in replaceable_pos:
                            if rpos < len(new_parts):
                                part_clean = new_parts[rpos].rstrip(';')
                                has_semi = new_parts[rpos].endswith(';')

                                if part_clean == node:
                                    new_parts[rpos] = new_node + (';' if has_semi else '')
                                    modified = True

                        if modified:
                            new_lines.append(' '.join(new_parts))
                        else:
                            new_lines.append(check_line)

                    result = '\n'.join(new_lines)

                    # 3) Update nodes_dict: any coordinate whose value was 'node'
                    #    becomes 'new_node'.
                    if nodes_dict is not None:
                        for k, v in list(nodes_dict.items()):
                            if str(v) == node:
                                nodes_dict[k] = new_node

                    next_node_num += 1
                    break  # Restart scanning lines with updated result

                if found_unmarked:
                    break  # restart outer loop with updated result

            if not found_unmarked:
                break  # No more unmarked nodes

        return result

    @staticmethod
    def renumber_nodes_for_drawing(netlist, nodes_dict=None, parsed_data=None):
        """
        Renumber nodes sequentially with ground handling.

        This calls renumber_grounds() and renumber_nodes() in sequence,
        then removes all 'x' markers from the netlist. If a nodes_dict
        (coordinate -> node_id) mapping is provided, it is updated in-place
        to stay consistent with the renumbered node IDs.

        Backwards compatibility:
            - Old style: renumber_nodes_for_drawing(netlist, parsed_data)
              (second positional is parsed_data, no nodes_dict)
            - New style: renumber_nodes_for_drawing(netlist, nodes_dict=..., parsed_data=...)

        Args:
            netlist: Current netlist string
            nodes_dict: Optional dict mapping coordinate keys -> node IDs
            parsed_data: Optional parsed LTspice data for ground detection

        Returns:
            If nodes_dict is None:
                str: renumbered netlist
            If nodes_dict is not None:
                (str, dict): (renumbered_netlist, updated_nodes_dict)
        """
        # ---- Backwards compatibility shim ----
        # If second positional argument is actually parsed_data (a list-like)
        # rather than a dict of nodes, and parsed_data wasn't given explicitly,
        # treat it as parsed_data.
        if nodes_dict is not None and parsed_data is None and not isinstance(nodes_dict, dict):
            parsed_data = nodes_dict
            nodes_dict = None

        if not netlist:
            if nodes_dict is None:
                return ""
            return "", nodes_dict

        # Step 1: Renumber grounds in the netlist only.
        result, single_ground = NetlistTransformer.renumber_grounds(
            netlist, parsed_data
        )

        # Step 2: Renumber non-ground nodes, updating nodes_dict values as we go
        result = NetlistTransformer.renumber_nodes(
            result,
            skip_grounds=True,
            nodes_dict=nodes_dict,
        )

        # Step 3: Remove all 'x' markers from netlist and nodes_dict
        result = result.replace("x", "")

        if nodes_dict is not None:
            new_nodes = {}
            for k, v in nodes_dict.items():
                # Normalize to string, strip 'x', then try to convert back to int
                if isinstance(v, str):
                    cleaned = v.replace("x", "")
                else:
                    cleaned = str(v).replace("x", "")

                if cleaned.isdigit():
                    new_nodes[k] = int(cleaned)
                else:
                    new_nodes[k] = cleaned

            nodes_dict.clear()
            nodes_dict.update(new_nodes)

            return result, nodes_dict

        # Backwards-compatible behavior: only return the netlist string
        return result
