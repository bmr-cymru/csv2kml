"""cvs2kml.py - convert CSV data to KML
"""
import os
import sys
from argparse import ArgumentParser
from os.path import basename

# XML document header
__xml_header = '<?xml version="1.0" encoding="UTF-8"?>'


# KML node tags
__kml_node = '<kml xmlns="http://earth.google.com/kml/2.0">'
__doc_node = '<Document>'
__place_node = '<Placemark>'
__name_node = '<name>'
__desc_node = '<description>'
__point_node = '<Point>'
__coord_node = '<coordinates>'
__folder_node = '<Folder>'
__style_node = '<Style id="%s">'
__styleurl_node = '<styleUrl>'
__linestyle_node = '<LineStyle>'
__linestr_node = '<LineString>'
__iconstyle_node = '<IconStyle>'
__icon_node = '<Icon>'

__kml_close = '</kml>'
__doc_close = '</Document>'
__place_close = '</Placemark>'
__name_close = '</name>'
__desc_close = '</description>'
__point_close = '</Point>'
__coord_close = '</coordinates>'
__folder_close = '</Folder>'
__style_close = '</Style>'
__styleurl_close = '</styleUrl>'
__linestyle_close = '</LineStyle>'
__linestr_close = '</LineString>'
__iconstyle_close = '</IconStyle>'
__icon_close = '</Icon>'

# Altitude mode
__alt_node = '<altitudeMode>%s</altitudeMode>'
__alt_rel_ground_node = __alt_node % 'relativeToGround'
__alt_abs_node = __alt_node % 'absolute'

# Extrude mode
__ext_node = '<extrude>%s</extrude>'
__ext_0_node = __ext_node % '0'
__ext_1_node = __ext_node % '1'

# Tessellate mode
__tes_0_node = '<tessellate>0</tessellate>'

#: Field constants for raw CSV columns
F_TICK = 0
F_GPS_TS = 47
F_GPS_LONG = 43
F_GPS_LAT = 44
F_GPS_ALT = 48

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

ALT_ABSOLUTE="absolute"
ALT_REL_GROUND="rel_ground"

def dmap(data, field):
    """Map input field positions to output data.
    """
    return data[__data_map[field]]


def sync_kml_file(kmlf):
    """Sync file data for the output KML file.
    """
    if not kmlf.isatty():
        os.fsync(kmlf)


def write_kml_header(kmlf):
    """Write generic KML header tags.
    """
    kmlf.write(__xml_header + '\n')
    kmlf.write(__kml_node + '\n')
    kmlf.write(__doc_node + '\n')
    sync_kml_file(kmlf)


def write_kml_footer(kmlf):
    """Write generic KML footer tags.
    """
    kmlf.write(__doc_close + '\n')
    kmlf.write(__kml_close + '\n')
    sync_kml_file(kmlf)


def write_placemark(kmlf, data, style):
    """Write a placemark with optional style.
    """
    coords = "%s,%s,%s" % (dmap(data, F_GPS_LONG), dmap(data, F_GPS_LAT),
                           dmap(data, F_GPS_ALT))
    kmlf.write(__place_node + '\n')
    kmlf.write(__name_node + dmap(data, F_TICK) + __name_close + '\n')
    kmlf.write(__desc_node + dmap(data, F_TICK) + __desc_close + '\n')
    if style:
        kmlf.write(__styleurl_node + style + __styleurl_close)
    kmlf.write(__point_node)
    kmlf.write(__coord_node + coords + __coord_close + '\n')
    kmlf.write(__alt_rel_ground_node + '\n')
    kmlf.write(__ext_1_node + '\n')
    kmlf.write( __point_close + '\n')
    kmlf.write(__place_close + '\n')
    sync_kml_file(kmlf)


def write_icon_style(kmlf, icon_id, href):
    """Write an icon style with an image link.
    """
    kmlf.write(__style_node % icon_id + '\n')
    kmlf.write(__iconstyle_node + '\n')
    kmlf.write(__icon_node + '\n')
    kmlf.write("<href>%s</href>" % href + '\n')
    kmlf.write(__icon_close + '\n')
    kmlf.write(__iconstyle_close + '\n')
    kmlf.write(__style_close + '\n')


def write_style_headers(kmlf):
    """Write out line and icon style headers.
    """
    icon_start = "http://www.earthpoint.us/Dots/GoogleEarth/pal2/icon13.png"
    icon_end = "http://www.earthpoint.us/Dots/GoogleEarth/shapes/target.png"
    kmlf.write(__style_node % "lineStyle1" + '\n')
    kmlf.write(__linestyle_node + '\n')
    kmlf.write('<color>ff00ffff</color>\n')
    kmlf.write('<width>4</width>\n')
    kmlf.write(__linestyle_close + '\n')
    kmlf.write(__style_close + '\n')
    write_icon_style(kmlf, "iconPathStart", icon_start)
    write_icon_style(kmlf, "iconPathEnd", icon_end)
    sync_kml_file(kmlf)
     
def write_track_header(kmlf, csv_data, altitude=ALT_REL_GROUND):
    """Write a track header with a pair of start/end placemarks.
    """
    # Start/end folder
    kmlf.write(__folder_node)
    # Write start placemark
    write_placemark(kmlf, csv_data[0], " #iconPathStart")
    # Write end placemark
    write_placemark(kmlf, csv_data[-1], " #iconPathEnd")
    kmlf.write(__folder_close)
    # Track folder
    kmlf.write(__folder_node + '\n')
    kmlf.write(__place_node + '\n')
    kmlf.write(__name_node + 'Flight Trace' + __name_close + '\n')
    kmlf.write(__desc_node + __desc_close)
    kmlf.write(__styleurl_node + '#lineStyle1' + __styleurl_close + '\n')
    kmlf.write(__linestr_node + '\n')
    kmlf.write(__ext_0_node + '\n')   
    kmlf.write(__tes_0_node + '\n')
    if altitude == ALT_REL_GROUND:
        kmlf.write(__alt_rel_ground_node + '\n')
    else:
        kmlf.write(__alt_abs_node + '\n')
    kmlf.write(__coord_node + '\n')
    sync_kml_file(kmlf)


def write_track_footer(kmlf):
    """Write a generic track footer closing all tags.
    """
    kmlf.write(__coord_close + '\n')
    kmlf.write(__linestr_close + '\n')
    kmlf.write(__place_close + '\n')
    kmlf.write(__folder_close + '\n')
    sync_kml_file(kmlf)


def write_coords(kmlf, data):
    """Write one line of coordinate data in a LinsString object.
    """
    coord_data = (
        dmap(data, F_GPS_LONG),
        dmap(data, F_GPS_LAT),
        dmap(data, F_GPS_ALT)
    )
    kmlf.write("%s,%s,%s\n" % coord_data)
    sync_kml_file(kmlf)

def process_csv(csvf, kmlf, mode=MODE_TRACK, altitude=ALT_REL_GROUND):
    """Process one CSV file and write the results to `kmlf`.
    """
    fields = None
    first = True
    csv_data = []
    track = mode == MODE_TRACK
    write_kml_header(kmlf)
    write_style_headers(kmlf)
    # Acquire data points
    for line in csvf:
        if line.startswith("Tick"):
            continue
        f = line.strip().split(',')
        data = (
            f[F_TICK], f[F_GPS_TS],
            f[F_GPS_LONG], f[F_GPS_LAT], f[F_GPS_ALT]
        )
        if not data[2] or not data[3] or not data[4]:
            continue
        if all([d == "0.0" for d in data[2:4]]):
            continue
        csv_data.append(data)

    if track:
        write_track_header(kmlf, csv_data, altitude=altitude)
    
    for data in csv_data:
        if not track:
            write_placemark(kmlf, data, None)
        else:
            write_coords(kmlf, data)

    if track:     
        write_track_footer(kmlf)

    write_kml_footer(kmlf)


def main(argv):
    parser = ArgumentParser(prog=basename(argv[0]), description="CSV to KML")
    parser.add_argument("-f", "--file", metavar="INPUT", type=str,
                        help="Input file path", default=None)
    parser.add_argument("-o", "--output", metavar="OUTPUT", type=str,
                        help="Output file path", default=None)
    parser.add_argument("-p", "--placemarks", action="store_true",
                        help="Output placemarks instead of track")
    parser.add_argument("-a", "--absolute", action="store_true",
                        help="Use absolute altitude mode")

    args = parser.parse_args()

    if args.placemarks:
        mode = MODE_PLACE
    else:
        mode = MODE_TRACK

    if args.absolute:
        alt = ALT_ABSOLUTE
    else:
        alt = ALT_REL_GROUND

    try:
        kmlf = sys.stdout if not args.output else open(args.output, "w")
    except OSError:
        print("Could not open output file: %s" % (args.output or '-'))
        raise

    try:
        csvf = sys.stdin if not args.file else open(args.file, "r")
    except OSError:
        print("Could not open input file: %s" % (args.file or '-'))
        raise

    return process_csv(csvf, kmlf, mode=mode, altitude=alt)

if __name__ == '__main__':
    main(sys.argv)
    sys.exit(0)
    try:
        main(sys.argv)
    except:
        sys.exit(1)
    sys.exit(0)
