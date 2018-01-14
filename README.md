# csv2kml

Simple script to convert DGI black box CSV data to KML

Usage:
```
usage: csv2kml.py [-h] [-a] [-d] [-f FIELD_MAP] [-F FIELD_FILE] [-i INPUT]
                  [-l LOG] [-n] [-o OUTPUT] [-p] [-s] [-t THRESHOLD] [-v]
```
Options:

  * `-a` Use absolute altitude mode
  * '-d' Enable Python exception debug output
  * `-f` Specify a manual field map
  * `-F` Specify a field map file
  * `-h` Show help message and exit
  * `-i` Input file path
  * `-l` File to write log to instead of terminal
  * `-n` Do not indent KML output
  * `-o` Output file path
  * `-p` Output placemarks instead of track
  * `-s` Output placemarkers when fly state changes
  * `-t` Time difference threshold for sampling (ms)
  * `-v` Enable verbose output


Authors:

  Bryn M. Reeves <bmr@errorists.org>

