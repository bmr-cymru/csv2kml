#!/usr/bin/env python

# Copyright (C) 2018 Bryn M. Reeves <bmr@errorists.org>
#
# csv2kml.py - Convert DGI CSV black box data to KML
#
# This file is part of the csv2kml project.
#
# https://github.com/bmr-cymru/csv2kml
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions
# of the GNU General Public License v.2.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""cvs2kml.py - convert CSV data to KML
"""
import os
import sys
from argparse import ArgumentParser
from os.path import basename
import logging

# debug state
__debug = False
# Log configuration
_log = logging.getLogger(__name__)

_default_log_level = logging.WARNING
_console_handler = None
_file_handler = None

_log_debug = _log.debug
_log_info = _log.info
_log_warn = _log.warning
_log_error = _log.error

# XML document header
__xml_header = '<?xml version="1.0" encoding="UTF-8"?>'

__xml_open = '<%s>'
__xml_close = '</%s>'

__kml = 'kml xmlns="http://earth.google.com/kml/2.0"'
__doc = 'Document'
__place = 'Placemark'
__name = 'name'
__desc = 'description'
__point = 'Point'
__coord = 'coordinates'
__folder = 'Folder'
__style = 'Style id="%s"'
__styleurl = 'styleUrl'
__linestyle = 'LineStyle'
__linestr = 'LineString'
__iconstyle = 'IconStyle'
__icon = 'Icon'
__altitude = 'altitudeMode'
__extrude = 'extrude'
__href = 'href'
__color = 'color'
__width = 'width'
__tessellate = 'tessellate'

# Altitude mode
__alt_rel_ground = 'relativeToGround'
__alt_absolute = 'absolute'

#: Field constants for raw CSV columns
F_TICK = "F_TICK"
F_FLIGHT_TIME = "F_FLIGHT_TIME"
F_GPS_TS = "F_GPS_TS"
F_GPS_LONG = "F_GPS_LONG"
F_GPS_LAT = "F_GPS_LAT"
F_GPS_ALT = "F_GPS_ALT"
F_FLY_STATE = "F_FLY_STATE"

__fields = [
    F_TICK, F_FLIGHT_TIME, F_GPS_TS,
    F_GPS_LAT, F_GPS_LONG, F_GPS_ALT,
    F_FLY_STATE
]

#: Map csv2kml field names to DJI column headers
__dji_header_map = {
    F_TICK: "Tick#",
    F_FLIGHT_TIME: "flightTime",
    F_GPS_TS: "GPS:dateTimeStamp",
    F_GPS_LONG: "GPS:Long",
    F_GPS_LAT: "GPS:Lat",
    F_GPS_ALT: "GPS:heightMSL",
    F_FLY_STATE: "flyCState"
}

#: Fly states
FS_AUTO_LAND = "AutoLanding"
FS_AUTO_TAKEOFF = "AutoTakeoff"
FS_GO_HOME = "GoHome"
FS_GPS_ATTI = "GPS_Atti"
FS_NAVI_GO = "NaviGo"

MODE_TRACK = "track"
MODE_PLACE = "placemark"

ALT_ABSOLUTE = __alt_absolute
ALT_REL_GROUND = __alt_rel_ground

__colors = {
    'red': 'ff0000ff',
    'green': 'ff00ff00',
    'blue' : 'ffff0000',
    'yellow': 'ff00ffff',
    'purple': 'ffff00ff'
}

class _indent(object):
    enable = True
    level = 0

    def __init__(self, enable=True):
        self.enable = enable

    @property
    def indstr(self):
        return "    " * self.level

    def indent(self):
        if not self.enable:
            return
        self.level += 1

    def undent(self):
        if not self.enable:
            return
        self.level -= 1


def sync_kml_file(kmlf):
    """Sync file data for the output KML file.
    """
    if not kmlf.isatty():
        os.fsync(kmlf)


def write_tag(kmlf, tag, indent, value=None):
    nl = "\n"
    has_value = value is not None
    tag_open = "%s%s" % (__xml_open % tag, "" if has_value else nl)
    kmlf.write(indent.indstr + tag_open)

    remaining = 72 - len(tag_open + indent.indstr)
    oneline = has_value and (nl not in value or len(value) < remaining)

    if has_value:
        if not oneline:
            kmlf.write('\n')
            value_end = "\n"
            tag_indent = indent
            indent.indent()
            val_indent = indent
        else:
            value_end = ""
            val_indent = ""
            tag_indent = ""

        kmlf.write(val_indent + value + value_end)

        if not oneline:
            indent.undent()

        kmlf.write(tag_indent + __xml_close % tag + "\n")

    if not oneline:
        indent.indent()


def close_tag(kmlf, tag, indent):
    indent.undent()
    tag = tag.split()[0]
    kmlf.write(indent.indstr + __xml_close % tag + "\n")


def write_kml_header(kmlf, indent):
    """Write generic KML header tags.
    """
    kmlf.write(__xml_header + '\n')
    write_tag(kmlf, __kml, indent)
    write_tag(kmlf, __doc, indent)
    _log_debug("wrote KML headers")


def write_kml_footer(kmlf, indent):
    """Write generic KML footer tags.
    """
    close_tag(kmlf, __doc, indent)
    close_tag(kmlf, __kml, indent)
    _log_debug("wrote KML footers")


def write_placemark(kmlf, data, style, indent,
                    altitude=ALT_REL_GROUND, name=None):
    """Write a placemark with optional style.
    """
    coords = "%s,%s,%s" % (data[F_GPS_LONG], data[F_GPS_LAT], data[F_GPS_ALT])
    name = name if name else data[F_TICK]
    write_tag(kmlf, __place, indent)
    write_tag(kmlf, __name, indent, value=name)
    write_tag(kmlf, __desc, indent, value=data[F_TICK])
    if style:
        write_tag(kmlf, __styleurl, indent, value=style)
    write_tag(kmlf, __point, indent)
    write_tag(kmlf, __coord, indent, value=coords)
    write_tag(kmlf, __altitude, indent, value=altitude)
    write_tag(kmlf, __extrude, indent, value="1")
    close_tag(kmlf, __point, indent)
    close_tag(kmlf, __place, indent)
    _log_debug("wrote placemark (name='%s')" % name)


def write_icon_style(kmlf, icon_id, href, indent):
    """Write an icon style with an image link.
    """
    write_tag(kmlf, __style % icon_id, indent)
    write_tag(kmlf, __iconstyle, indent)
    write_tag(kmlf, __icon, indent)
    write_tag(kmlf, __href, indent, value=href)
    close_tag(kmlf, __icon, indent)
    close_tag(kmlf, __iconstyle, indent)
    close_tag(kmlf, __style, indent)
    _log_debug("wrote icon style (id='%s')" % icon_id)


def write_style_headers(kmlf, width, color, indent):
    """Write out line and icon style headers.
    """
    icon_start = "http://www.earthpoint.us/Dots/GoogleEarth/pal2/icon13.png"
    icon_end = "http://www.earthpoint.us/Dots/GoogleEarth/shapes/target.png"
    write_tag(kmlf, __style % "lineStyle1", indent)
    write_tag(kmlf, __linestyle, indent)
    write_tag(kmlf, __color, indent, value=color)
    write_tag(kmlf, __width, indent, value=str(width))
    close_tag(kmlf, __linestyle, indent)
    close_tag(kmlf, __style, indent)
    write_icon_style(kmlf, "iconPathStart", icon_start, indent)
    write_icon_style(kmlf, "iconPathEnd", icon_end, indent)
    _log_debug("wrote style headers")


def write_state_placemarks(kmlf, csv_data, indent, altitude=ALT_REL_GROUND):
    fly_state = None
    _log_debug("starting state placemarks folder")
    write_tag(kmlf, __folder, indent)
    for data in csv_data:
        new_fly_state = data[F_FLY_STATE]
        if fly_state:
            if new_fly_state != fly_state:
                _log_info("fly state changed from '%s' to '%s'" %
                          (fly_state, new_fly_state))
                name = "%s:%s" % (fly_state, new_fly_state)
                write_placemark(kmlf, data, None, indent,
                                altitude=altitude, name=name)
        fly_state = new_fly_state
    _log_debug("ending state placemarks folder")
    close_tag(kmlf, __folder, indent)


def write_track_header(kmlf, csv_data, indent,
                       altitude=ALT_REL_GROUND, name=None):
    """Write a track header with a pair of start/end placemarks.
    """
    # Start/end folder
    _log_debug("starting track placemarks folder")
    write_tag(kmlf, __folder, indent)
    # Write start placemark
    write_placemark(kmlf, csv_data[0], " #iconPathStart", indent,
                    altitude=altitude, name="Start")
    # Write end placemark
    write_placemark(kmlf, csv_data[-1], " #iconPathEnd", indent,
                    altitude=altitude, name="End")
    _log_debug("ending track placemarks folder")
    close_tag(kmlf, __folder, indent)
    # Track folder
    _log_debug("starting track data folder")
    write_tag(kmlf, __folder, indent)
    write_tag(kmlf, __place, indent)
    write_tag(kmlf, __name, indent, value=name if name else 'Flight Trace')
    write_tag(kmlf, __desc, indent, value='')
    write_tag(kmlf, __styleurl, indent, value='#lineStyle1')
    write_tag(kmlf, __linestr, indent)
    write_tag(kmlf, __extrude, indent, value="0")
    write_tag(kmlf, __tessellate, indent, value="0")
    write_tag(kmlf, __altitude, indent, value=altitude)
    write_tag(kmlf, __coord, indent)
    _log_debug("wrote track header (name='%s')" % name)


def write_track_footer(kmlf, indent):
    """Write a generic track footer closing all tags.
    """
    close_tag(kmlf, __coord, indent)
    close_tag(kmlf, __linestr, indent)
    close_tag(kmlf, __place, indent)
    _log_debug("ending track data folder")
    close_tag(kmlf, __folder, indent)
    _log_debug("wrote track footer")


def write_coords(kmlf, data, indent):
    """Write one line of coordinate data in a LinsString object.
    """
    coord_data = (
        data[F_GPS_LONG],
        data[F_GPS_LAT],
        data[F_GPS_ALT]
    )
    kmlf.write(indent.indstr + "%s,%s,%s\n" % coord_data)


def make_field_map(header, name_map):
    field_map = {}
    names = name_map.keys()
    # Hack to work around models that generate extra header tags.
    headers = [h.split('[')[0] for h in header.strip().split(',')]
    for name in names:
        idx = headers.index(name_map[name])
        _log_debug("mapping field %s to index %d ('%s')" %
                   (name, idx, headers[idx]))
        field_map[name] = idx
    _log_debug("built field map with %d fields" % len(names))
    return field_map


def process_csv(csvf, kmlf, mode=MODE_TRACK, altitude=ALT_REL_GROUND,
                thresh=1000, state_marks=False, indent_kml=True,
                track_width=4, track_color="ff00ffff", field_map=None):
    """Process one CSV file and write the results to `kmlf`.
    """
    fields = None
    csv_data = []
    track = mode == MODE_TRACK

    _log_info("Processing CSV data from %s" % csvf.name)

    indent = _indent(enable=indent_kml)

    write_kml_header(kmlf, indent)
    write_style_headers(kmlf, track_width, track_color, indent)

    no_coord_skip = 0
    ts_delta_skip = 0
    ts_none_skip = 0
    last_ts = 0

    header_read = False
    # Acquire data points
    for line in csvf:
        if not header_read and not line.startswith("Tick"):
            continue
        if field_map and line.startswith("Tick"):
            _log_debug("skipping header row")
            continue
        # replace with call to is_header_row() if multi-vendor
        elif line.startswith("Tick"):
            _log_debug("parsing field map from header row")
            field_map = make_field_map(line, __dji_header_map)
            _log_debug("field map: %s" % field_map)
            header_read = True
            continue
        elif not field_map:
            _log_error("No header found and no field map specified")
            raise Exception("Cannot process data without field map")

        f = line.strip().split(',')

        def getfield(field):
            return f[field_map[field]]

        ts = int(getfield(F_FLIGHT_TIME)) if getfield(F_FLIGHT_TIME) else None

        # Skip row if time delta < threshold
        if not ts:
            ts_none_skip += 1
            continue
        elif (ts - last_ts) < thresh:
            ts_delta_skip += 1
            continue

        last_ts = ts

        # Build field_name -> value dictionary
        data = {f: getfield(f) for f in __fields}

        # Skip row if coordinate data is null or zero
        coords = [data[F_GPS_LONG], data[F_GPS_LAT], data[F_GPS_ALT]]
        if not any(coords) or all([d == "0.0" for d in coords]):
            no_coord_skip += 1
            continue

        csv_data.append(data)

    if ts_none_skip:
        _log_debug("skipped %d rows with null timestamp" % ts_none_skip)
    if ts_delta_skip:
        _log_debug("skipped %d rows with ts_delta < thresh" % ts_delta_skip)
    if no_coord_skip:
        _log_debug("skipped %d rows with null coordinates" % no_coord_skip)

    if len(csv_data):
        _log_info("built CSV data table with %d rows and %d keys" %
                  (len(csv_data), len(csv_data[0].keys())))
    else:
        raise Exception("No non-skipped data rows found")

    _log_info("writing KML data")

    # Write fly state change placemarks
    if state_marks:
        write_state_placemarks(kmlf, csv_data, indent, altitude=altitude)

    if track:
        write_track_header(kmlf, csv_data, indent, altitude=altitude)

    for data in csv_data:
        if not track:
            write_placemark(kmlf, data, None, indent, altitude=altitude)
        else:
            write_coords(kmlf, data, indent)

    if not track:
        _log_info("wrote placemark data")
    else:
        _log_info("wrote track coordinate data")

    if track:
        write_track_footer(kmlf, indent)

    write_kml_footer(kmlf, indent)
    sync_kml_file(kmlf)


def parse_field_map(map_string):
    """Parse a field map string into a field_map dictionary.
        The syntax of the map string is:

         "FIELD1:column1,FIELD2:column2,..."
    """
    field_map = {}

    for key_value in map_string.strip().split(","):
        (key, value) = key_value.split(":")
        if key not in __fields:
            raise ValueError("Unknown field name: %s" % key)
        try:
            int_value = int(value)
        except:
            raise ValueError("Field map values must be integers: %s" % value)
        field_map[key] = int_value
    _log_debug("parsed field map with %d fields" % len(field_map.keys()))
    return field_map


def read_field_map_file(field_file):
    """Read a field map from a file and parse it into a map_string that
        can be further parsed into a field_map by parse_field_map.

        The -F/--field-file syntax uses one field per line with each
        line formatted as "FIELDN:indexN":

          FIELD1:index1
          FIELD2:index2
          ...
          FIELDN:indexN
    """
    map_string = ""
    separator = ""
    fields = 0
    with open(field_file, "r") as f:
        map_lines = f.readlines()
        for line in map_lines:
            map_string += separator + line.strip()
            separator = ","
            fields += 1
    _log_info("read fields from field map file '%s'" % field_file)
    return map_string


def setup_logging(args):
    global _console_handler, _file_handler
    level = _default_log_level

    if args.verbose:
        if args.verbose > 1:
            level = logging.DEBUG
        elif args.verbose > 0:
            level = logging.INFO

    formatter = logging.Formatter('%(levelname)s - %(message)s')
    _log.setLevel(level)
    _console_handler = logging.StreamHandler(sys.stderr)
    _console_handler.setLevel(level)
    _console_handler.setFormatter(formatter)
    _log.addHandler(_console_handler)

    if args.log_file:
        log_file = open(args.log_file, "w")
        _file_handler = logging.StreamHandler(log_file)
        _file_handler.setLevel(level)
        _log.addHandler(_file_handler)


def shutdown_logging():
    if _console_handler:
        _console_handler.close()
    if _file_handler:
        _file_handler.close()


def parse_color(color):
    """Parse a color string or name and return the corresponding hexadecimal
        color string.
    """
    if color in __colors.keys():
        color = __colors[color]

    if len(color) != 6 and len(color) != 8:
        raise ValueError("invalid color string length: %d" % len(color))

    color_chars = map(str, range(0,9)) + ['a','b','c','d','e','f']
    chars_valid = [c in color_chars for c in color]
    if not all(chars_valid):
        raise ValueError("invalid characters in color string: %s" % color)
    return color


def csv2kml(args):
    if not args.input and sys.stdin.isatty():
        parser.print_help()
        raise ValueError("No input file specified.")
    if args.field_file and not args.field_map:
        args.field_map = read_field_map_file(args.field_file)

    field_map = parse_field_map(args.field_map) if args.field_map else None

    mode = MODE_PLACE if args.placemarks else MODE_TRACK
    alt = ALT_ABSOLUTE if args.absolute else ALT_REL_GROUND

    if not args.output and args.input:
        args.output = args.input[0:-4] + ".kml"

    args.output = None if args.output == '-' else args.output
    args.input = None if args.input == '-' else args.input

    indent = not args.no_indent

    track_color = parse_color(args.color)

    try:
        kmlf = sys.stdout if not args.output else open(args.output, "w")
    except (IOError, OSError):
        log_error("Could not open output file: %s" % (args.output or '-'))
        raise

    try:
        csvf = sys.stdin if not args.input else open(args.input, "r")
    except (IOError, OSError):
        log_error("Could not open input file: %s" % (args.input or '-'))
        raise

    return process_csv(csvf, kmlf, mode=mode, altitude=alt,
                       thresh=args.threshold, state_marks=args.state_marks,
                       indent_kml=indent, track_width=args.width,
                       track_color=track_color, field_map=field_map)


def main(argv):
    global __debug
    parser = ArgumentParser(prog=basename(argv[0]), description="CSV to KML")
    parser.add_argument("-a", "--absolute", action="store_true",
                        help="Use absolute altitude mode", default=None)
    parser.add_argument("-c", "--color", type=str, default="yellow",
                        help="Set track color. Available options: red, blue, "
                             "yellow, green, purple or hex color codes. (e.g.: "
                             "red = ff0000ff)")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable Python exception debug output")
    parser.add_argument("-f", "--field-map", type=str, default=None,
                        help="Specify a manual field map")
    parser.add_argument("-F", "--field-file", type=str, default=None,
                        help="Specify a manual field map file")
    parser.add_argument("-i", "--input", metavar="INPUT", type=str,
                        help="Input file path", default=None)
    parser.add_argument("-l", "--log-file", metavar="LOG", default=None,
                        help="File to write log to instead of terminal")
    parser.add_argument("-n", "--no-indent", action="store_true",
                        help="Do not indent KML output")
    parser.add_argument("-o", "--output", metavar="OUTPUT", type=str,
                        help="Output file path", default=None)
    parser.add_argument("-p", "--placemarks", action="store_true",
                        help="Output placemarks instead of track")
    parser.add_argument("-s", "--state-marks", action="store_true",
                        help="Output placemarkers when fly state changes")
    parser.add_argument("-t", "--threshold", type=int, default=1000,
                        help="Time difference threshold for sampling (ms)")
    parser.add_argument("-v", "--verbose", action="count",
                        help="Enable verbose output")
    parser.add_argument("-w", "--width", type=int, default=4,
                        help="Track line width in pixel for track mode.")

    args = parser.parse_args()

    setup_logging(args)

    if args.debug:
        __debug = True

    if __debug:
        csv2kml(args)
        shutdown_logging()
        return 0

    try:
        csv2kml(args)
    except Exception as e:
        print(e)
        return 1
    finally:
        shutdown_logging()
    return 0


if __name__ == '__main__':
    ret = main(sys.argv)
    sys.exit(ret)
