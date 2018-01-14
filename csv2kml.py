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

# Log configuration
_log = logging.getLogger(__name__)

_default_log_level = logging.WARNING
_console_handler = None

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

__fields = [F_TICK, F_FLIGHT_TIME, F_GPS_TS, F_GPS_LAT, F_GPS_LONG, F_GPS_ALT]


#: Map csv2kml field names to DJI column headers
__dji_header_map = {
    F_TICK: "Tick#",
    F_FLIGHT_TIME: "flightTime",
    F_GPS_TS: "GPS:dateTimeStamp",
    F_GPS_LONG: "GPS:Long",
    F_GPS_LAT: "GPS:Lat",
    F_GPS_ALT: "GPS:heightMSL"
}

MODE_TRACK = "track"
MODE_PLACE = "placemark"

ALT_ABSOLUTE = __alt_absolute
ALT_REL_GROUND = __alt_rel_ground


def sync_kml_file(kmlf):
    """Sync file data for the output KML file.
    """
    if not kmlf.isatty():
        os.fsync(kmlf)


def write_tag(kmlf, tag, value=None):
    has_value = value is not None
    kmlf.write("%s%s" % (__xml_open % tag, "" if has_value else "\n"))
    if has_value:
        kmlf.write(value)
        kmlf.write(__xml_close % tag + "\n")


def close_tag(kmlf, tag):
    tag = tag.split()[0]
    kmlf.write(__xml_close % tag + "\n")


def write_kml_header(kmlf):
    """Write generic KML header tags.
    """
    kmlf.write(__xml_header + '\n')
    write_tag(kmlf, __kml)
    write_tag(kmlf, __doc)
    _log_debug("wrote KML headers")


def write_kml_footer(kmlf):
    """Write generic KML footer tags.
    """
    close_tag(kmlf, __doc)
    close_tag(kmlf, __kml)
    _log_debug("wrote KML footers")


def write_placemark(kmlf, data, style, altitude=ALT_REL_GROUND, name=None):
    """Write a placemark with optional style.
    """
    coords = "%s,%s,%s" % (data[F_GPS_LONG], data[F_GPS_LAT], data[F_GPS_ALT])
    name = name if name else data[F_TICK]
    write_tag(kmlf, __place)
    write_tag(kmlf, __name, value=name)
    write_tag(kmlf, __desc, value=data[F_TICK])
    if style:
        write_tag(kmlf, __styleurl, value=style)
    write_tag(kmlf, __point)
    write_tag(kmlf, __coord, value=coords)
    write_tag(kmlf, __altitude, value=altitude)
    write_tag(kmlf, __extrude, value="1")
    close_tag(kmlf, __point)
    close_tag(kmlf, __place)
    _log_debug("wrote placemark (name='%s')" % name)


def write_icon_style(kmlf, icon_id, href):
    """Write an icon style with an image link.
    """
    write_tag(kmlf, __style % icon_id)
    write_tag(kmlf, __iconstyle)
    write_tag(kmlf, __icon)
    write_tag(kmlf, __href, value=href)
    close_tag(kmlf, __icon)
    close_tag(kmlf, __iconstyle)
    close_tag(kmlf, __style)
    _log_debug("wrote icon style (id='%s')" % icon_id)


def write_style_headers(kmlf):
    """Write out line and icon style headers.
    """
    icon_start = "http://www.earthpoint.us/Dots/GoogleEarth/pal2/icon13.png"
    icon_end = "http://www.earthpoint.us/Dots/GoogleEarth/shapes/target.png"
    write_tag(kmlf, __style % "lineStyle1")
    write_tag(kmlf, __linestyle)
    write_tag(kmlf, __color, value="ff00ffff")
    write_tag(kmlf, __width, value="4")
    close_tag(kmlf, __linestyle)
    close_tag(kmlf, __style)
    write_icon_style(kmlf, "iconPathStart", icon_start)
    write_icon_style(kmlf, "iconPathEnd", icon_end)
    _log_debug("wrote style headers")


def write_track_header(kmlf, csv_data, altitude=ALT_REL_GROUND, name=None):
    """Write a track header with a pair of start/end placemarks.
    """
    # Start/end folder
    write_tag(kmlf, __folder)
    # Write start placemark
    write_placemark(kmlf, csv_data[0], " #iconPathStart", altitude=altitude,
                    name="Start")
    # Write end placemark
    write_placemark(kmlf, csv_data[-1], " #iconPathEnd", altitude=altitude,
                    name="End")
    close_tag(kmlf, __folder)
    # Track folder
    write_tag(kmlf, __folder)
    write_tag(kmlf, __place)
    write_tag(kmlf, __name, value=name if name else 'Flight Trace')
    write_tag(kmlf, __desc, value='')
    write_tag(kmlf, __styleurl, value='#lineStyle1')
    write_tag(kmlf, __linestr)
    write_tag(kmlf, __extrude, value="0")
    write_tag(kmlf, __tessellate, value="0")
    write_tag(kmlf, __altitude, value=altitude)
    write_tag(kmlf, __coord)
    _log_debug("wrote track header (name='%s')" % name)


def write_track_footer(kmlf):
    """Write a generic track footer closing all tags.
    """
    close_tag(kmlf, __coord)
    close_tag(kmlf, __linestr)
    close_tag(kmlf, __place)
    close_tag(kmlf, __folder)
    _log_debug("wrote track footer")


def write_coords(kmlf, data):
    """Write one line of coordinate data in a LinsString object.
    """
    coord_data = (
        data[F_GPS_LONG],
        data[F_GPS_LAT],
        data[F_GPS_ALT]
    )
    kmlf.write("%s,%s,%s\n" % coord_data)


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
                thresh=1000, field_map=None):
    """Process one CSV file and write the results to `kmlf`.
    """
    fields = None
    csv_data = []
    track = mode == MODE_TRACK

    _log_info("Processing CSV data from %s" % csvf.name)

    write_kml_header(kmlf)
    write_style_headers(kmlf)

    no_coord_skip = 0
    ts_delta_skip = 0
    ts_none_skip = 0
    last_ts = 0

    # Acquire data points
    for line in csvf:
        if field_map and line.startswith("Tick"):
            _log_debug("skipping header row")
            continue
        # replace with call to is_header_row() if multi-vendor
        elif line.startswith("Tick"):
            _log_debug("parsing field map from header row")
            field_map = make_field_map(line, __dji_header_map)
            _log_debug("field map: %s" % field_map)
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
            continue
            ts_delta_skip += 1

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

    if track:
        write_track_header(kmlf, csv_data, altitude=altitude)

    for data in csv_data:
        if not track:
            write_placemark(kmlf, data, None, altitude=altitude)
        else:
            write_coords(kmlf, data)

    if not track:
        _log_info("wrote placemark data")
    else:
        _log_info("wrote track coordinate data")

    if track:
        write_track_footer(kmlf)

    write_kml_footer(kmlf)
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
    global _console_handler
    level = _default_log_level

    if args.verbose:
        if args.verbose > 1:
            level = logging.DEBUG
        elif args.verbose > 0:
            level = logging.INFO

    formatter = logging.Formatter('%(levelname)s - %(message)s')
    _log.setLevel(level)
    _console_handler = logging.StreamHandler()
    _console_handler.setLevel(level)
    _console_handler.setFormatter(formatter)
    _log.addHandler(_console_handler)


def main(argv):
    parser = ArgumentParser(prog=basename(argv[0]), description="CSV to KML")
    parser.add_argument("-a", "--absolute", action="store_true",
                        help="Use absolute altitude mode", default=None)
    parser.add_argument("-f", "--field-map", type=str, default=None,
                        help="Specify a manual field map")
    parser.add_argument("-F", "--field-file", type=str, default=None,
                        help="Specify a manual field map file")
    parser.add_argument("-i", "--input", metavar="INPUT", type=str,
                        help="Input file path", default=None)
    parser.add_argument("-o", "--output", metavar="OUTPUT", type=str,
                        help="Output file path", default=None)
    parser.add_argument("-p", "--placemarks", action="store_true",
                        help="Output placemarks instead of track")
    parser.add_argument("-t", "--threshold", type=int, default=1000,
                        help="Time difference threshold for sampling (ms)")
    parser.add_argument("-v", "--verbose", action="count",
                        help="Enable verbose output")

    args = parser.parse_args()

    setup_logging(args)

    if not args.input and sys.stdin.isatty():
        parser.print_help()
        raise ValueError("No input file specified.")

    if args.field_file and not args.field_map:
        args.field_map = read_field_map_file(args.field_file)

    field_map = parse_field_map(args.field_map) if args.field_map else None

    mode = MODE_PLACE if args.placemarks else MODE_TRACK
    alt = ALT_ABSOLUTE if args.absolute else ALT_REL_GROUND

    args.output = None if args.output == '-' else args.output
    args.input = None if args.input == '-' else args.input

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
                       thresh=args.threshold, field_map=field_map)

if __name__ == '__main__':
    try:
        main(sys.argv)
    except Exception as e:
        print(e)
        sys.exit(1)
    sys.exit(0)
