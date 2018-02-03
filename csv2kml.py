#!/usr/bin/env python

# Copyright (C) 2018 Bryn M. Reeves <bmr@errorists.org>
# Co-Progamming and Design: Axel Seedig <axel@endeavoursky.co.uk>
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
__yaw = 'yaw'
__desc = 'description'
__point = 'Point'
__coord = 'coordinates'
__heading = 'heading'
__folder = 'Folder'
__scale = 'scale'
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
F_YAW = "F_YAW"
F_TRAVEL_DIST = "F_TRAVEL_DIST"

__fields = [
    F_TICK, F_FLIGHT_TIME, F_GPS_TS,
    F_GPS_LAT, F_GPS_LONG, F_GPS_ALT,
    F_FLY_STATE, F_YAW, F_TRAVEL_DIST
]

#: Map csv2kml field names to DJI column headers
__dji_header_map = {
    F_TICK: "Tick#",
    F_FLIGHT_TIME: "flightTime",
    F_GPS_TS: "GPS:dateTimeStamp",
    F_GPS_LONG: "GPS:Long",
    F_GPS_LAT: "GPS:Lat",
    F_GPS_ALT: "GPS:heightMSL",
    F_FLY_STATE: "flyCState",
    F_YAW: "Yaw",
    F_TRAVEL_DIST: "distanceTravelled"
}
__dji_key_field = F_TICK

__man_header_map = {
    F_FLIGHT_TIME: "Tick#",
    F_GPS_TS: "Time_Stamp",
    F_TICK: "Tick#",
    F_GPS_LONG: "Target_Lon",
    F_GPS_LAT: "Target_Lat",
    F_GPS_ALT: "Height",
    F_FLY_STATE: "Identify",
    F_YAW: "Bearing",
    F_TRAVEL_DIST: "Distance"
}
__man_key_field = F_GPS_TS

#: Fly states
FS_AUTO_LAND = "AutoLanding"
FS_ASST_TAKEOFF = "AssistedTakeoff"
FS_AUTO_TAKEOFF = "AutoTakeoff"
FS_GO_HOME = "GoHome"
FS_GPS_ATTI = "GPS_Atti"
FS_NAVI_GO = "NaviGo"

#: Map known state aliases to canonical name.
#: ASST_TAKEOFF seems to be an alias for FS_ASST_TAKEOFF, and some state
#: values appear in CSV data with "Assisted" mis-spelled as "Assited".
__fs_aliases = {
    "ASST_TAKEOFF": FS_ASST_TAKEOFF,
    "AssitedTakeoff": FS_ASST_TAKEOFF
}

#: Track mode: create a LineString corresponding to the flight track.
MODE_TRACK = "track"
#: Placemark mode: create a placemark for each CSV data point.
MODE_PLACE = "placemark"

#: Absolute altitude mode: values relative to sea level.
ALT_ABSOLUTE = __alt_absolute
#: Ground relative altitidue mode.
ALT_REL_GROUND = __alt_rel_ground

#: Map color aliases to hex ARGB color values
__colors = {
    'red': 'ff0000ff',
    'green': 'ff00ff00',
    'blue': 'ffff0000',
    'yellow': 'ff00ffff',
    'purple': 'ffff00ff'
}

icon_marker_0_Red = ("http://manager.hampshire4x4response.net/"
                     "Mapping/_SupportFiles/0_Red.png")

class _indent(object):
    """Indentation context: the `_indent` class stores the current
        indentation level and generates a suitable indentation string
        on demand via the `indstr` property.

        The indentation level is increased by callinf the `indent()`
        method, and decreased by calling `undent().

        Indentation may be disabled by calling the initialiser with
        `enable=False`, or by setting the `enable` property at run time.
    """
    #: Enable indentation of KML output
    enable = True
    #: Current indentation level
    level = 0

    def __init__(self, enable=True):
        """Initialise a new `_indent` object with the specified enable
            state.
        """
        self.enable = enable

    @property
    def indstr(self):
        """Return the current indentation as a string suitable for
            terminal or file output.
        """
        if not self.enable:
            return ""
        return "    " * self.level

    def indent(self):
        """Increase indentation by one level.
        """
        if not self.enable:
            return
        self.level += 1

    def undent(self):
        """Decrease indentation by one level.
        """
        if not self.enable:
            return
        self.level -= 1


def sync_kml_file(kmlf):
    """Sync file data for the output KML file.
    """
    if not kmlf.isatty():
        os.fsync(kmlf)


def write_tag(kmlf, tag, indent, value=None):
    """Write a KML tag.

        Write a KML tag, with or without a value. If no tag value is
        given, the tag will be written as a one line '<tag>' with no
        closing tag. The `close_tag()` function should be used to close
        the tag at a later time after writing the tag body.

        If a value is specified, and it appears to fit on a single 80
        character line of output (with the opening and closing tags), it
        will be written as a single '<tag>value</tag>' line.

        Otherwise the tag, value line(s), and closing tag will be
        written on subsequent lines and indented according to the
        current indent state.
    """
    nl = "\n"

    # Use "not None" as "" etc. is a valid tag value
    has_value = value is not None

    # Write opening tag
    tag_open = "%s%s" % (__xml_open % tag, "" if has_value else nl)
    kmlf.write(indent.indstr + tag_open)

    # Check to see if node with value fits on a single line
    remaining = 72 - len(tag_open + indent.indstr)
    oneline = has_value and (nl not in value or len(value) < remaining)

    if has_value:
        if oneline:
            # Output on a single line with no spaces
            value_end = ""
            val_indent = ""
            tag_indent = ""
        else:
            # Write newlines after tag and value, and indent output
            kmlf.write('\n')
            value_end = "\n"
            tag_indent = indent.indstr
            indent.indent()
            val_indent = indent.indstr

        for val_line in value.splitlines():
            kmlf.write(val_indent + val_line + value_end)

        if not oneline:
            indent.undent()

        # Write closing tag after value
        kmlf.write(tag_indent + __xml_close % tag + "\n")

    if not oneline:
        indent.indent()


def close_tag(kmlf, tag, indent):
    """Write a closing XML tag and un-indent.
    """
    # write_tag() has called indent() for a node with a value
    indent.undent()
    # Closing tag only uses the first word of the tag string.
    tag = tag.split()[0]
    # Write closing tag
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


def write_placemark(kmlf, data, style, indent, altitude=ALT_REL_GROUND,
                    icon_marker=None, heading=None, name=None, desc=None):
    """Write a placemark with optional style.
    """
    if style and icon_marker:
        raise ValueError("'style' and 'icon_marker' cannot both beset")

    coords = "%s,%s,%s" % (data[F_GPS_LONG], data[F_GPS_LAT], data[F_GPS_ALT])

    # Use shortened description if no name given
    name = name if name else desc[0:11] if desc else None

    # Use the Tick# for the name unless specified
    name = name if name else "Tick: " + data[F_TICK]

    # Write place, name and description tags
    write_tag(kmlf, __place, indent)
    write_tag(kmlf, __name, indent, value=name)
    write_tag(kmlf, __desc, indent, value=desc)

    # Optional styleUrl tag.
    if style:
        write_tag(kmlf, __styleurl, indent, value=style)

    # Write point, coordinates, altitude mode and extrude mode tags.
    else:
        write_icon_style(kmlf, None, icon_marker, indent, heading=heading)
    write_tag(kmlf, __point, indent)
    write_tag(kmlf, __coord, indent, value=coords)
    write_tag(kmlf, __altitude, indent, value=altitude)
    write_tag(kmlf, __extrude, indent, value="1")

    # Close point & place tags.
    close_tag(kmlf, __point, indent)
    close_tag(kmlf, __place, indent)
    _log_debug("wrote placemark (name='%s')" % name)


def write_icon_style(kmlf, icon_id, href, indent, scale=None, heading=None):
    """Write an icon style with an image link.
    """
    style = __style % icon_id if icon_id else __style.split(' ')[0]
    write_tag(kmlf, style, indent)
    write_tag(kmlf, __iconstyle, indent)
    if scale is not None:
        write_tag(kmlf, __scale, indent, value=scale)
    if heading is not None:
        write_tag(kmlf, __heading, indent, value=heading)
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
    icon_mark = "http://maps.google.com/mapfiles/kml/paddle/D.png"

    write_tag(kmlf, __style % "lineStyle1", indent)
    write_tag(kmlf, __linestyle, indent)
    write_tag(kmlf, __color, indent, value=color)
    write_tag(kmlf, __width, indent, value=str(width))
    close_tag(kmlf, __linestyle, indent)
    close_tag(kmlf, __style, indent)
    write_icon_style(kmlf, "iconPathStart", icon_start, indent)
    write_icon_style(kmlf, "iconPathEnd", icon_end, indent)
    write_icon_style(kmlf, "iconPathMark", icon_mark, indent)
    _log_debug("wrote style headers")


def write_state_placemarks(kmlf, csv_data, indent, altitude=ALT_REL_GROUND):
    icon_marker = icon_marker_0_Red
    """Write placemarks for each flight state change found in the CSV
        data.

        For each row of data, the F_FLY_STATE field is compared to the
        current flight state and a placemark is written if they differ.

        Aliases are supported for FS_* fly states since multiple
        synonyms exist in the raw data (e.g. AssistedTakeoff).

        The name of the placemark is "OldState:NewState". This may be
        made configurable in a future version.
    """
    fly_state = None
    _log_debug("starting state placemarks folder")
    write_tag(kmlf, __folder, indent)
    for data in csv_data:
        new_fly_state = data[F_FLY_STATE]
        # Convert alias to canonical name
        if new_fly_state in __fs_aliases:
            new_fly_state = __fs_aliases[new_fly_state]
        if fly_state:
            if new_fly_state != fly_state:
                _log_info("fly state changed from '%s' to '%s'" %
                          (fly_state, new_fly_state))
                name = "%s:%s" % (fly_state, new_fly_state)
                write_placemark(kmlf, data, None, indent, altitude=altitude,
                                icon_marker=icon_marker, name=name,
                                heading=data[F_YAW])
        # Update current fly state
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

    # Write track tags
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
    """Make a field map for the current CSV file by scanning column
        headers.

        The `header` argument is a string containing a row of CSV
        data with column headers, and `name_map` is a dictionary
        mapping csv2kml field names to CSV column headers, for e.g.
        'F_TICK: "Tick#"'.

        The CSV format header data is split at each ',', and column
        names are canonicalised to remove '[description#]' tags
        present in some model data.

        For each name in `name_map`, the headers list is searched
        for a matching column, and if found, the index of the column
        is taken as the mapping for that field and stored in a new
        `field_map` dictionary.

        On success the field map is returned.
    """
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


def find_model_header_map(headers):
    if headers.startswith(__dji_header_map[__dji_key_field]):
        return __dji_header_map
    elif headers.startswith(__man_header_map[__man_key_field]):
        return __man_header_map


def process_csv(csvf, kmlf, mode=MODE_TRACK, altitude=ALT_REL_GROUND,
                thresh=1000, state_marks=False, indent_kml=True,
                track_width=4, track_color="ff00ffff", field_map=None):
    """Process one CSV file and write the results to `kmlf`.

        Data is read from the input CSV file and stored in a list of
        dictionary objects, indexed by csv2kml field names (F_TICK etc).
        Rows of input data are skipped unless they have a valid time
        stamp, valid coordinates, and occur after the configured sample
        time threshold.

        Flight state change placemarks are then written (if enabled) in
        a new KML folder, followed by a folder containing the track or
        placemark entries for the flight.
    """
    fields = None
    csv_data = []
    track = mode == MODE_TRACK

    _log_info("Processing CSV data from %s" % csvf.name)

    indent = _indent(enable=indent_kml)

    write_kml_header(kmlf, indent)
    write_style_headers(kmlf, track_width, track_color, indent)

    pre_head_skip = 0
    no_coord_skip = 0
    ts_delta_skip = 0
    ts_none_skip = 0
    last_ts = 0

    header_read = False
    # Acquire data points
    for line in csvf:
        # Ignore blank lines, comments etc. before the header row.
        if not header_read and "Tick" not in line:
            pre_head_skip +=1
            continue

        # Skip header if using explicit field map
        if field_map and line.startswith("Tick"):
            _log_debug("skipping header row")
            header_read = True
            continue
        # Detect model headers to parse field mapping: replace with
        # is_header_row() to allow multi-vendor support.
        elif "Tick" in line:
            _log_debug("parsing field map from header row")
            header_map = find_model_header_map(line)
            field_map = make_field_map(line, header_map)
            _log_debug("field map: %s" % field_map)
            header_read = True
            continue
        elif not field_map:
            _log_error("No header found and no field map specified")
            raise Exception("Cannot process data without field map")

        f = line.strip().split(',')

        def getfield(field):
            # Map F_FIELD_NAME -> column index -> column data
            return f[field_map[field]]

        # Convert F_FLIGHT_TIME to an integer for threshold checks
        ts = int(getfield(F_FLIGHT_TIME)) if getfield(F_FLIGHT_TIME) else None

        # Skip row if time delta < threshold
        if not ts and not getfield(F_FLIGHT_TIME):
            ts_none_skip += 1
            continue
        # Skip row if ts_delta < thresh
        elif (ts - last_ts) < thresh:
            ts_delta_skip += 1
            continue

        # Update last_ts
        last_ts = ts

        # Build field_name -> value dictionary
        data = {f: getfield(f) for f in __fields}

        # Skip row if coordinate data is null or zero
        coords = [data[F_GPS_LONG], data[F_GPS_LAT], data[F_GPS_ALT]]
        if not any(coords) or all([d == "0.0" for d in coords]):
            no_coord_skip += 1
            continue

        csv_data.append(data)

    if pre_head_skip:
        _log_debug("skipped %d rows before header" % pre_head_skip)
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

    # Write track headers
    if track:
        write_track_header(kmlf, csv_data, indent, altitude=altitude)

    for data in csv_data:
        if not track:
            # Placemark mode: one mark per row
            write_placemark(kmlf, data, " #iconPathMark", indent, altitude=altitude)
        else:
            # Track mode: write coordinate data inside track tags.
            write_coords(kmlf, data, indent)

    if not track:
        _log_info("wrote placemark data")
    else:
        _log_info("wrote track coordinate data")

    if track:
        # Close track headers
        write_track_footer(kmlf, indent)

    write_kml_footer(kmlf, indent)
    sync_kml_file(kmlf)


def parse_field_map(map_string):
    """Parse a field map string into a field_map dictionary.
        The syntax of the map string is:

         "FIELD1:column1,FIELD2:column2,..."

        ValueError is raised for unknown field names and TypeError
        is raised if the column value cannot be parsed as an integer.

        On success the field map is returned as a dictionary.

    """
    field_map = {}

    for key_value in map_string.strip().split(","):
        (key, value) = key_value.split(":")
        if key not in __fields:
            raise ValueError("Unknown field name: %s" % key)
        try:
            int_value = int(value)
        except:
            raise TypeError("Field map values must be integers: %s" % value)
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

        The file is parsed and the resulting string passed to
        parse_field_map() to create a field map dictionary.
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
    return parse_field_map(map_string)


def setup_logging(args):
    """Set up logging to the terminal and optional log file.
    """
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
    """ Close logging.
    """
    if _console_handler:
        _console_handler.close()
    if _file_handler:
        _file_handler.close()


def parse_color(color):
    """Parse a color string or name and return the corresponding
        hexadecimal color string.

        Raises ValueError if the length of the string is not 6 (RGB),
        or 8 (ARGB), or if non-hexadecimal characters appear in the
        `color` string.
    """
    if color in __colors.keys():
        color = __colors[color]

    if len(color) != 6 and len(color) != 8:
        raise ValueError("invalid color string length: %d" % len(color))

    color_chars = map(str, range(0, 9)) + ['a', 'b', 'c', 'd', 'e', 'f']
    color_chars += ['A', 'B', 'C', 'D', 'E', 'F']
    chars_valid = [c in color_chars for c in color]
    if not all(chars_valid):
        raise ValueError("invalid characters in color string: %s" % color)
    return color


def csv2kml(args):
    """ccs2kml main routine

        Handle all non-debug arguments and defaults, and initialise the
        `csvf` and `kmlf` input and output streams respectively, and
        call `process_csv()` to parse CSV data and generate KML output.

        Raises SystemExit and argument specific exceptions (e.g.
        ValueError) on invalid argument values, and IOError or OSError
        for system errors (permissions, path not found etc.).
    """
    if not args.input and sys.stdin.isatty():
        print("No input file specified")
        raise SystemExit(1)

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
        _log_error("Could not open input file: %s" % (args.input or '-'))
        raise

    return process_csv(csvf, kmlf, mode=mode, altitude=alt,
                       thresh=args.threshold, state_marks=args.state_marks,
                       indent_kml=indent, track_width=args.width,
                       track_color=track_color, field_map=field_map)


def main(argv):
    """main()

        Parse arguments, initialise logging and call `csv2kml()` to
        convert file data.

        Exceptions in csv2kml() are caught and logged to the terminal
        unless debugging is enabled. In this case exceptions are
        never caught and will be caught by the python interpreter or
        debugger.
    """
    parser = ArgumentParser(prog=basename(argv[0]), description="Convert DJI"
                            " CSV files to KML")
    parser.add_argument("-a", "--absolute", action="store_true",
                        help="Use absolute altitude mode", default=None)
    parser.add_argument("-c", "--color", type=str, default="yellow",
                        help="Set track color. Available options: red, blue, "
                             "yellow, green, purple or hex color codes. "
                             "(e.g.: red = ff0000ff)")
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
