"""cvs2kml.py - convert CSV data to KML
"""
import os
import sys
from argparse import ArgumentParser
from os.path import basename

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
F_FLIGHT_TIME = "F_FLIGHT_TIME",
F_GPS_TS = "F_GPS_TS"
F_GPS_LONG = "F_GPS_LONG"
F_GPS_LAT = "F_GPS_LAT"
F_GPS_ALT = "F_GPS_ALT"

__fields = [F_TICK, F_FLIGHT_TIME, F_GPS_TS, F_GPS_LAT, F_GPS_LONG, F_GPS_ALT]

class _model(object):
    name = ""
    map = None

    def __init__(self, name, aliases, field_map):
        self.map = field_map
        self.name = name
        self.aliases = aliases

__models = [
    _model("Inspire1", ["i1"],
            {F_TICK: 0,
             F_FLIGHT_TIME: 2,
             F_GPS_TS:47,
             F_GPS_LONG:43,
             F_GPS_LAT:44,
             F_GPS_ALT:48}),
    _model("Inspire2", ["i2"],
            {F_TICK: 0,
             F_FLIGHT_TIME: 2,
             F_GPS_TS: 56,
             F_GPS_LONG: 52,
             F_GPS_LAT: 53,
             F_GPS_ALT: 57}),
    _model("Phantom4", ["p4"],
            {F_TICK: 0,
             F_FLIGHT_TIME: 2,
             F_GPS_TS: 56,
             F_GPS_LONG: 52,
             F_GPS_LAT: 53,
             F_GPS_ALT: 57})
]

_default_model = __models[0].name

_model_names = {m.name: m for m in __models}


def __init_aliases():
    global _model_names
    for m in __models:
        if m.aliases:
            for a in m.aliases:
                _model_names[a] = m


#: Map of field constants to data tuple elements
__data_map = {
    F_TICK: 0,
    F_GPS_TS: 1,
    F_GPS_LONG: 2,
    F_GPS_LAT: 3,
    F_GPS_ALT: 4
}

MODE_TRACK="track"
MODE_PLACE="placemark"

ALT_ABSOLUTE=__alt_absolute
ALT_REL_GROUND=__alt_rel_ground

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


def write_kml_footer(kmlf):
    """Write generic KML footer tags.
    """
    close_tag(kmlf, __doc)
    close_tag(kmlf, __kml)


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


def write_track_footer(kmlf):
    """Write a generic track footer closing all tags.
    """
    close_tag(kmlf, __coord)
    close_tag(kmlf, __linestr)
    close_tag(kmlf, __place)
    close_tag(kmlf, __folder)


def write_coords(kmlf, data):
    """Write one line of coordinate data in a LinsString object.
    """
    coord_data = (
        data[F_GPS_LONG],
        data[F_GPS_LAT],
        data[F_GPS_ALT]
    )
    kmlf.write("%s,%s,%s\n" % coord_data)

def process_csv(csvf, kmlf, mode=MODE_TRACK, altitude=ALT_REL_GROUND,
                model=_default_model, thresh=1000):
    """Process one CSV file and write the results to `kmlf`.
    """
    fields = None
    first = True
    csv_data = []
    track = mode == MODE_TRACK

    write_kml_header(kmlf)
    write_style_headers(kmlf)

    # Get model field mapping
    modmap = _model_names[model].map

    last_ts = 0
    # Acquire data points
    for line in csvf:
        if line.startswith("Tick"):
            continue
        f = line.strip().split(',')

        def getfield(field):
            return f[modmap[field]]

        ts = int(getfield(F_FLIGHT_TIME)) if getfield(F_FLIGHT_TIME) else None

        if not ts or (ts - last_ts) < thresh:
            continue

        last_ts = ts

        data = {f: getfield(f) for f in __fields}
        if not data[F_GPS_LONG] or not data[F_GPS_LAT] or not data[F_GPS_ALT]:
            continue
        coords = [data[F_GPS_LONG], data[F_GPS_LAT], data[F_GPS_ALT]]
        if all([d == "0.0" for d in coords]):
            continue
        csv_data.append(data)

    if track:
        write_track_header(kmlf, csv_data, altitude=altitude)
    
    for data in csv_data:
        if not track:
            write_placemark(kmlf, data, None, altitude=altitude)
        else:
            write_coords(kmlf, data)

    if track:     
        write_track_footer(kmlf)

    write_kml_footer(kmlf)
    sync_kml_file(kmlf)


def list_models():
    print("Supported device models:")
    for m in __models:
        sys.stdout.write("Name: %s [" % m.name)
        left = len(m.aliases) - 1
        for a in m.aliases:
            sys.stdout.write("%s%s" % (a, " " if left else ""))
            left -= 1
        sys.stdout.write("]\n")

def main(argv):
    parser = ArgumentParser(prog=basename(argv[0]), description="CSV to KML")
    parser.add_argument("-a", "--absolute", action="store_true",
                        help="Use absolute altitude mode", default=None)
    parser.add_argument("-f", "--file", metavar="INPUT", type=str,
                        help="Input file path", default=None)
    parser.add_argument("-o", "--output", metavar="OUTPUT", type=str,
                        help="Output file path", default=None)
    parser.add_argument("-l", "--list-models", action="store_true",
                        help="List the supported drone models")
    parser.add_argument("-m", "--model", metavar="DRONE", type=str,
                        help="Model of drone CSV data")
    parser.add_argument("-p", "--placemarks", action="store_true",
                        help="Output placemarks instead of track")
    parser.add_argument("-t", "--threshold", type=int, default=1000,
                        help="Time difference threshold for sampling (ms)")

    args = parser.parse_args()

    __init_aliases()

    if args.list_models:
        return list_models()

    mode = MODE_PLACE if args.placemarks else MODE_TRACK
    alt = ALT_ABSOLUTE if args.absolute else ALT_REL_GROUND
    model = args.model if args.model else _default_model

    try:
        kmlf = sys.stdout if not args.output else open(args.output, "w")
    except (IOError, OSError):
        print("Could not open output file: %s" % (args.output or '-'))
        raise

    try:
        csvf = sys.stdin if not args.file else open(args.file, "r")
    except (IOError, OSError):
        print("Could not open input file: %s" % (args.file or '-'))
        raise

    return process_csv(csvf, kmlf, mode=mode, altitude=alt, model=model,
                       thresh=args.threshold)

if __name__ == '__main__':
    try:
        main(sys.argv)
    except Exception as e:
        print(e)
        sys.exit(1)
    sys.exit(0)
