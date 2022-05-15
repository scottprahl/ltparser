# pylint: disable=invalid-name
# pylint: disable=unused-variable
# pylint: disable=too-many-locals
# pylint: disable=no-member
# pylint: disable=consider-using-f-string
# pylint: disable=attribute-defined-outside-init
"""
Convert the contents of an LTspice .asc file to a netlit for use in lcapy.

Example::
    import ltparser
    >>>> lt = ltparser.LTspice()
    >>>> lt.read('circuit.asc')
    >>>> lt.make_netlist()
    >>>> cct = lt.circuit()
    >>>> cct.draw()
"""

import matplotlib.pyplot as plt
import pyparsing as pp
import lcapy

__all__ = ('ltspice_value_to_number',
           'LTspice',
           )

component_offsets = {
    # each entry has x_off, y_off, and length
    'voltage': [0, 16, 96],
    'cap': [16, 0, 64],
    'res': [16, 16, 96],
    'current': [0, 0, 80],
    'polcap': [16, 0, 64],
    'ind': [16, 16, 96],
}


def node_key(x, y):
    """Cast LTspice x,y location to a key for a dictionary."""
    return "%04d_%04d" % (int(x), int(y))


def the_direction(line):
    """Determine the direction of the two nodes."""
    x1 = int(line[1])
    y1 = int(line[2])
    x2 = int(line[3])
    y2 = int(line[4])

    if x1 == x2:
        if y1 > y2:
            return 'up'
        return 'down'

    if x1 > x2:
        return 'left'

    return 'right'


def ltspice_sine_parser(s):
    number = pp.Combine(pp.Optional('.') + pp.Word(pp.nums) +
                        pp.Optional('.' + pp.Optional(pp.Word(pp.nums))))
    sine = pp.Literal('SINE(') + number * 3 + pp.Literal(')')
    
    parsed = sine.parseString(s)
    dc = float(parsed[1])
    amp = float(parsed[2])
    omega0 = float(parsed[3])
    
    return dc, amp, omega0
    
def ltspice_value_to_number(s):
    """Convert LTspice value 4.7k to 4700."""
#    print("converting ", s)
    # sometimes "" shows up as the value
    empty = pp.Literal('""')
    try:
        empty.parseString(s)
        return ''
    except pp.ParseException:
        pass

    # return things like {R} untouched
    parameter = pp.Combine('{' + pp.restOfLine())
    try:
        parameter.parseString(s)
        return s
    except pp.ParseException:
        pass

    # this does not handle 1e-3
    # this does not handle 1e-3
    number = pp.Combine(pp.Optional('.') + pp.Word(pp.nums) +
                        pp.Optional('.' + pp.Optional(pp.Word(pp.nums))))

    # the SI prefixes
    prefix = pp.CaselessLiteral('MEG') | pp.CaselessLiteral('F') | \
             pp.CaselessLiteral('P') | pp.CaselessLiteral('N') | \
             pp.CaselessLiteral('U') | pp.CaselessLiteral('M') | \
             pp.CaselessLiteral('K') | pp.Literal('µ')

    # use restOfLine to discard possible unwanted units
    lt_number = number + pp.Optional(prefix) + pp.restOfLine()

    try:
        parsed = lt_number.parseString(s)
        x = float(parsed[0])

        # change number based on unit prefix
        if parsed[1] == 'F':
            x *= 1e-15
        elif parsed[1] == 'P':
            x *= 1e-12
        elif parsed[1] == 'N':
            x *= 1e-9
        elif parsed[1] == 'U' or parsed[1] == 'µ':
            x *= 1e-6
        elif parsed[1] == 'M':
            x *= 1e-3
        elif parsed[1] == 'K':
            x *= 1e3
        elif parsed[1] == 'MEG':
            x *= 1e6
        return x
    except pp.ParseException:
        pass

    return s


class LTspice():
    """Class to convert LTspice files to lcapy circuits."""

    def __init__(self):
        """Initialize object variables."""
        self.contents = None
        self.parsed = None
        self.nodes = None
        self.netlist = None
        self.single_ground = True

    def read(self, filename):
        """Read a file as contents."""
        encodings = ['utf-8', 'utf-16-le', 'mac-roman', 'windows-1250'] 
        for e in encodings:
            try:
                with open(filename, 'r', encoding=e) as f:
                    self.contents = f.read()
            except UnicodeError:
                print('got unicode error with %s , trying different encoding' % e)
            else:
                print('opening the file with encoding:  %s ' % e)
                break
        
    def parse(self):
        """Parse LTspice .asc file contents."""
        heading = pp.Group(pp.Keyword("Version") + pp.Literal("4"))
        integer = pp.Combine(pp.Optional(pp.Char('-')) + pp.Word(pp.nums))
        label = pp.Word(pp.alphanums + '_' + 'µ')
        sheet = pp.Group(pp.Keyword("SHEET") + integer * 3)
        rotation = pp.Group(pp.Char("R") + integer)
        wire = pp.Group(pp.Keyword("WIRE") + integer * 4)
        window = pp.Group(pp.Keyword("WINDOW") + pp.restOfLine())
        symbol = pp.Group(pp.Keyword("SYMBOL") + label + integer*2 +
                          rotation)
        attr = pp.Group(pp.Keyword("SYMATTR") + label + pp.White() +
                        pp.restOfLine())
        flag = pp.Group(pp.Keyword("FLAG") + integer * 2 + label)
        iopin = pp.Group(pp.Keyword("IOPIN") + integer * 2 + label)
        text = pp.Group(pp.Keyword("TEXT") + pp.restOfLine())
        line = pp.Group(pp.Keyword("LINE") + pp.restOfLine())
        rect = pp.Group(pp.Keyword("RECTANGLE") + pp.restOfLine())

        component = pp.Group(symbol + pp.Dict(pp.ZeroOrMore(window)) +
                             pp.Dict(pp.ZeroOrMore(attr)))
        linetypes = wire | flag | iopin | component | line | text | rect

        grammar = heading + sheet + pp.Dict(pp.ZeroOrMore(linetypes))
        if self.contents is not None:
            self.parsed = grammar.parseString(self.contents)


    def print_parsed(self):
        """Better visualization of parsed LTspice file."""
        if self.parsed is None:
            print('Nothing parsed yet.')

        for line in self.parsed:
            element = line[0]

            if isinstance(element, pp.ParseResults):
                print(line[0])
                for i in range(1, len(line)):
                    print('    ', line[i])
                continue
            print(element, line[1:])

    def sort_nodes(self):
        """Sorts the notes a dict with nodes sorted."""
        sorted_keys = sorted(self.nodes)

        grounds = 0
        for key in sorted_keys:
            if self.nodes[key] == 0:
                grounds += 1

        count = 1
        for key in sorted_keys:
            if self.nodes[key] != 0:
                self.nodes[key] = count
                count += 1

    def print_nodes(self):
        """Print the notes a dict with nodes sorted."""
        for key in self.nodes:
            print(key, ' : ', self.nodes[key])

    def plot_nodes(self):
        """Plot the nodes with labels."""
        miny = 1e6
        maxy = -1e6
        for key in self.nodes:
            x, y = key.split('_')
            node = self.nodes[key]
            xx = int(x)
            yy = int(y)

            miny = min(yy, miny)
            maxy = max(yy, maxy)
            if node == 0:
                plt.plot([xx], [yy], 'ok', markersize=3)
                plt.text(xx, yy, 'gnd', ha='center', va='top')
            else:
                plt.plot([xx], [yy], 'ob', markersize=3)
                plt.text(xx, yy, self.nodes[key], color='blue', ha='right', va='bottom')

        plt.ylim(maxy+0.1*(maxy-miny), miny-0.1*(maxy-miny))
        plt.show()

    def make_nodes_from_wires(self):
        """
        Produce the dictionary of nodes for all wires and grounds.

        The grounds need to be processed first so that they can all get
        labelled with "0".  Then the end of each wire is examined.  If
        the x,y location has been seen before, it is ignored.  If it has
        not, then it is added to the dictionary of nodes.
        """
        self.nodes = {}
        if self.parsed is None:
            return

        # create all the ground nodes
        for line in self.parsed:
            if line[0] == 'FLAG' and line[3] == '0':
                n1 = node_key(line[1], line[2])
                if n1 not in self.nodes:
                    self.nodes[n1] = 0

        if len(self.nodes) > 1:
            self.single_ground = False

        # now wire nodes
        for line in self.parsed:
            element = line[0]
            if element != 'WIRE':
                continue

            n1 = node_key(line[1], line[2])
            if n1 not in self.nodes:
                self.nodes[n1] = len(self.nodes)+1

            n2 = node_key(line[3], line[4])
            if n2 not in self.nodes:
                self.nodes[n2] = len(self.nodes)+1

    def wire_to_netlist(self, line):
        """Return netlist string for one wire in parsed data."""
        if line[0] != 'WIRE':
            return ''

        n1 = self.nodes[node_key(line[1], line[2])]
        n2 = self.nodes[node_key(line[3], line[4])]

        direction = the_direction(line)

        return 'W %d %d; %s\n' % (n1, n2, direction)

    def symbol_to_netlist(self, line):
        """Return netlist string for symbol in parsed data."""
        first = list(line[0])
        if first[0] != 'SYMBOL':
            return ''

        kind = first[1]
#        print("\nKind==", kind)

        x = int(first[2])
        y = int(first[3])

        rotation = list(first[4])[1]
        if rotation == '0':
            direction = 'down'
        elif rotation == '90':
            direction = 'left'
        elif rotation == '180':
            direction = 'up'
        else:
            direction = 'right'

        name = ''
        value = ''
        for sub_line in line:
            row = list(sub_line)

            if row[0] != 'SYMATTR':
                continue

            if row[1] == 'InstName':
                name = row[3]
                continue

            if row[1] == 'Value':
                value = row[3]
                continue

        node1, node2 = self.match_node(x, y, kind, direction)

        if value != '':
            value = ltspice_value_to_number(value)

        if kind == 'current':
            direction += ', invert'

        if kind == 'current' or kind == 'voltage':
            if not isinstance(value, float):
                try:
                    dc, amp, omega0 = ltspice_sine_parser(value)
                    return '%s %d %d ac %f; %s\n' % (name, node1, node2, amp, direction)
                except pp.ParseException:
                    pass

        if kind == 'polcap':
            direction += ', kind=polar, invert'

        return '%s %d %d %s; %s\n' % (name, node1, node2, value, direction)

    def make_netlist(self):
        """Process parsed LTspice data and create a simple netlist."""
        self.netlist = ''
        if self.parsed is None:
            self.parse()
            if self.parsed is None:
                return

        if self.nodes is None:
            self.make_nodes_from_wires()

        self.sort_nodes()
#        self.print_nodes()

        for line in self.parsed:

            if line[0] == 'WIRE':
                self.netlist += self.wire_to_netlist(line)

            if isinstance(line[0], pp.ParseResults):
                self.netlist += self.symbol_to_netlist(line)

    def match_node(self, x, y, kind, direction):
        """Match ends of simple component to existing nodes."""
        x_off, y_off, length = component_offsets[kind]
#        print("Original %d %d %s x_off=%d y_off=%d length=%d" %
#              (x, y, direction, x_off, y_off, length))

        if direction == 'left':
            key1 = node_key(x-y_off, y+x_off)
            key2 = node_key(x-length, y+x_off)

        elif direction == 'right':
            key1 = node_key(x+y_off, y-x_off)
            key2 = node_key(x+length, y-x_off)

        elif direction == 'down':
            key1 = node_key(x+x_off, y+y_off)
            key2 = node_key(x+x_off, y+length)

        elif direction == 'up':
            key1 = node_key(x-x_off, y-y_off)
            key2 = node_key(x-x_off, y-length)

        if key1 not in self.nodes:
            n1 = '?'
        else:
            n1 = self.nodes[key1]

        if key2 not in self.nodes:
            n2 = '?'
        else:
            n2 = self.nodes[key2]

#        print("pt1 %s ==> %s" % (key1,n1))
#        print("pt2 %s ==> %s" % (key2,n2))

        return n1, n2

    def circuit(self):
        """Create a lcapy circuit."""
        if self.netlist is None:
            return None

        cct = lcapy.Circuit()
        for line in self.netlist.splitlines():
            cct.add(line)
        
        if not self.single_ground:
            cct.add(';autoground=True')
        return cct
