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


Simple parser for converting LTspice `.asc` files to netlists.  Only a
few LTspice elements are currently supported.

Usage
-----

.. code-block:: python

    import lcapy
    import ltparser

    lt = ltparser.LTspice()
    lt.read('../examples/ltspice/twin-t.asc')
    lt.make_netlist()
    cct=lt.circuit()
    cct.draw(scale=0.5)

produces

.. image:: https://github.com/scottprahl/ltparser/blob/main/docs/twin-t.png?raw=true

Installation
------------

Source code is available at <https://github.com/scottprahl/ltparser> or the module
can be installed using `pip`::

    pip install ltparser

License
-------
ltparser is licensed under the terms of the MIT license.