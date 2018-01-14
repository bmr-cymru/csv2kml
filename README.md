# csv2kml

Simple script to convert DGI black box CSV data to KML

Usage:

  csv2kml.py [-h] [-a] [-f INPUT] [-o OUTPUT] [-l] [-m DRONE] [-p]
             [-t THRESHOLD]

Options:

  * -a - Use absolute altitude (default is ground relative)
  * -f - Input CSV file path
  * -o - Output KML file path
  * -l - List supported drone models
  * -m - Specify the drone model to use by name or alias
  * -p - Generate placemarkers instead of a track
  * -t - Time difference threshold for sampling (ms)

Authors:

  Bryn M. Reeves <bmr@errorists.org>

