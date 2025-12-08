.. |pypi| image:: https://img.shields.io/pypi/v/ltparser?color=68CA66
   :target: https://pypi.org/project/ltparser/
   :alt: pypi

.. |github| image:: https://img.shields.io/github/v/tag/scottprahl/ltparser?label=github&color=68CA66
   :target: https://github.com/scottprahl/ltparser
   :alt: github

.. |conda| image:: https://img.shields.io/conda/vn/conda-forge/ltparser?label=conda&color=68CA66
   :target: https://github.com/conda-forge/ltparser-feedstock
   :alt: conda

.. |doi| image:: https://zenodo.org/badge/116033943.svg
   :target: https://zenodo.org/badge/latestdoi/116033943
   :alt: doi  

.. |license| image:: https://img.shields.io/github/license/scottprahl/ltparser?color=68CA66
   :target: https://github.com/scottprahl/ltparser/blob/main/LICENSE.txt
   :alt: License

.. |test| image:: https://github.com/scottprahl/ltparser/actions/workflows/test.yaml/badge.svg
   :target: https://github.com/scottprahl/ltparser/actions/workflows/test.yaml
   :alt: Testing

.. |docs| image:: https://readthedocs.org/projects/ltparser/badge?color=68CA66
   :target: https://ltparser.readthedocs.io
   :alt: Docs

.. |downloads| image:: https://img.shields.io/pypi/dm/ltparser?color=68CA66
   :target: https://pypi.org/project/ltparser/
   :alt: Downloads


ltparser
========

|pypi| |github| |conda| |doi|

|license| |test| |docs| |downloads|

**ltparser** bridges the gap between LTspice's intuitive visual circuit design and lcapy's powerful symbolic circuit analysis. 

Design circuits visually in LTspice, then automatically convert them to lcapy-compatible netlists for symbolic analysis—no manual netlist writing required!

Why ltparser?
-------------

Creating netlists by hand is tedious and error-prone. **LTspice provides a much better way:**

- **Visual circuit design** - Drag and drop components, wire them together
- **Automatic connectivity** - LTspice handles all the node connections
- **Professional schematic capture** - Industry-standard tool for circuit design
- **Symbolic analysis** - Convert to lcapy for transfer functions, impedance analysis, and more

**ltparser makes this workflow seamless**, converting your LTspice schematics (``.asc`` files) into lcapy-compatible netlists automatically.

What ltparser Does
------------------

ltparser parses LTspice schematic files and:

1. **Extracts circuit topology** - Identifies components, nodes, and connections
2. **Generates lcapy netlists** - Creates properly formatted netlists with correct syntax
3. **Handles complex components** - Supports resistors, capacitors, inductors, sources, and op-amps
4. **Preserves component values** - Automatically converts SI prefixes (k, M, μ, etc.)
5. **Manages ground nodes** - Correctly identifies and numbers ground connections

Supported Components
--------------------

.. list-table::
   :header-rows: 1
   :widths: 20 25 15 40

   * - Component
     - LTspice Symbol
     - Prefix
     - Notes
   * - Resistor
     - res, Res, RES
     - R
     - Values with k, Meg, etc.
   * - Capacitor
     - cap, Cap, CAP
     - C
     - Values with μ, n, p, etc.
   * - Inductor
     - ind, Ind, IND
     - L
     - Values with m, μ, n, etc.
   * - Voltage Source
     - voltage
     - V
     - DC and AC sources
   * - Current Source
     - current
     - I
     - DC and AC sources
   * - Op-Amp (3-pin)
     - opamp
     - E
     - Simple op-amp symbol
   * - Op-Amp (5-pin)
     - UniversalOpamp2
     - E
     - With power supply pins

Quick Start
-----------

Basic Example: RC Low-Pass Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    import lcapy
    import ltparser

    # Read LTspice schematic
    lt = ltparser.LTspice()
    lt.read('tests/examples/passive_filter_band_pass.asc')
    
    # Generate netlist
    netlist = lt.make_netlist()
    print(netlist)
    
    # Create lcapy circuit for analysis
    cct = lt.circuit()
    
    # Calculate transfer function
    H = cct.transfer('V1', 'out', 'ground')
    print(f"Transfer function: {H}")
    
    # Draw the circuit
    cct.draw()

.. image:: https://github.com/scottprahl/ltparser/blob/main/docs/images/passive_filter_band_pass.png?raw=true
   :alt: RC Filter Circuit

Example: Twin-T Notch Filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Twin-T filter is a classic notch filter design—much easier to draw in LTspice than to write out by hand!

.. code-block:: python

    import lcapy
    import ltparser

    lt = ltparser.LTspice()
    lt.read('tests/examples/twin_t.asc')
    netlist = lt.make_netlist()
    cct = lt.circuit()
    cct.draw(scale=0.5)

.. image:: https://github.com/scottprahl/ltparser/blob/main/docs/images/twin_t.png?raw=true
   :alt: Twin-T Notch Filter

Example: Inverting Op-Amp Amplifier
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

ltparser handles operational amplifiers, automatically mapping all pins correctly:

.. code-block:: python

    import lcapy
    import ltparser

    lt = ltparser.LTspice()
    lt.read('tests/examples/inverting_opamp_simple.asc')
    
    # Generate netlist - op-amps use 'E' prefix for lcapy
    netlist = lt.make_netlist()
    print(netlist)
    
    # Perform symbolic analysis
    cct = lt.circuit()
    gain = cct.transfer('Vin', 'Vout', 'ground')
    print(f"Voltage gain: {gain}")

Generates netlist like::

    V1 in 0
    R1 in n1 10k
    R2 n1 out 100k
    E1 out 0 opamp 0 n1

.. image:: https://github.com/scottprahl/ltparser/blob/main/docs/images/inverting_opamp_simple.png?raw=true
   :alt: Inverting Op-Amp Amplifier

Example: Voltage Divider with Analysis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Simple but demonstrates the complete workflow:

.. code-block:: python

    import lcapy
    import ltparser

    lt = ltparser.LTspice()
    lt.read('tests/examples/voltage_divider_6.asc')
    
    cct = lt.circuit()
    
    # Symbolic analysis
    Z_in = cct.impedance('Vin', 'ground')
    V_out = cct['Vout'].V
    
    print(f"Input impedance: {Z_in}")
    print(f"Output voltage: {V_out}")
    
    # Frequency response
    H = cct.transfer('Vin', 'Vout', 'ground')
    H.frequency_response().plot()

.. image:: https://github.com/scottprahl/ltparser/blob/main/docs/images/voltage_divider_6.png?raw=true
   :alt: Voltage Divider

Workflow
--------

The typical workflow is:

1. **Design in LTspice**: Create your circuit using LTspice's schematic editor
2. **Save as .asc**: LTspice saves schematics in text-based ``.asc`` format
3. **Parse with ltparser**: Use ltparser to read the schematic and generate a netlist
4. **Analyze with lcapy**: Use lcapy for symbolic analysis, transfer functions, etc.
5. **Visualize results**: Plot frequency responses, step responses, etc.

Common Analysis Tasks
---------------------

Transfer Functions
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    cct = lt.circuit()
    H = cct.transfer(input_node, output_node, reference_node)
    H.bode_plot()

Input/Output Impedance
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    Z_in = cct.impedance(node1, node2)
    Z_out = cct.impedance(output_node, reference_node)

Node Voltages
^^^^^^^^^^^^^

.. code-block:: python

    V_out = cct[output_node].V
    V_out.frequency_response().plot()

Frequency Response
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    H = cct.transfer('input', 'output', 'ground')
    H.frequency_response().plot((0.1, 100e3))

Features
--------

- **Automatic node numbering** - Handles complex connectivity automatically
- **SI prefix conversion** - Converts k, M, μ, n, p prefixes to numeric values  
- **Multiple ground support** - Correctly handles circuits with separate grounds
- **Component orientation** - Works with components in any rotation
- **Case-insensitive** - Handles res, Res, RES, etc.
- **Graph-based analysis** - Uses NetworkX for robust node identification
- **lcapy integration** - Seamless conversion to lcapy Circuit objects

Limitations
-----------

ltparser focuses on symbolic analysis rather than visual reproduction:

- **No schematic drawing** - Cannot recreate LTspice schematics visually
- **Limited component support** - Only common passive and active components
- **Simplified models** - Uses ideal component models for symbolic analysis
- **No simulation** - For SPICE simulation, use LTspice directly

The tool bridges LTspice's visual design with lcapy's symbolic analysis—use each tool for its strength!

Installation
------------

Install from PyPI::

    pip install ltparser

Or from conda-forge::

    conda install -c conda-forge ltparser

Or install from source::

    git clone https://github.com/scottprahl/ltparser.git
    cd ltparser
    pip install .

Requirements
^^^^^^^^^^^^

- Python ≥ 3.9
- numpy
- matplotlib
- lcapy (for circuit analysis)
- networkx (installed with lcapy)

Documentation
-------------

Full documentation available at https://ltparser.readthedocs.io

- API reference
- Detailed examples
- Component reference
- Troubleshooting guide

Citation
--------

If you use ltparser in research, please cite:

.. code-block:: bibtex

    @software{ltparser,
      author = {Prahl, Scott},
      title = {ltparser: LTspice to lcapy netlist converter},
      url = {https://github.com/scottprahl/ltparser},
      doi = {10.5281/zenodo.116033943}
    }

License
-------

ltparser is licensed under the terms of the MIT license.
