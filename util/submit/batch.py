#!/usr/bin/env python

#
# Copyright (C) 2016, BMW Car IT GmbH
#
# Author: Sebastian Mattheis <sebastian.mattheis@bmw-carit.de>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in
# writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
#

__author__ = "sebastian.mattheis@bmw-carit.de"
__copyright__ = "Copyright 2016 BMW Car IT GmbH"
__license__ = "Apache-2.0"

import optparse
import json
import random
import socket
import os
import sys

parser = optparse.OptionParser("batch.py [options]")
parser.add_option("--host", dest="host", help="IP address of matcher.")
parser.add_option("--port", type="int", dest="port", help="Port of matcher.")
parser.add_option("--input_file_name", dest="input_file_name", help="JSON file with sample data.")
parser.add_option("--id", dest="id", help="Object id.")
parser.add_option("--zone", dest="zone", default="+0000", help="Time zone in '(+/-)HHMM' format.")
parser.add_option("--format", dest="format", default="geojson", help="Output format: geojson (default) | slimjson | debug")
parser.add_option("--output_file_name", dest="output_file_name", help="Map-matching output file name")

(options, args) = parser.parse_args()

if options.input_file_name is None or options.output_file_name is None or options.host is None or options.port is None:
    parser.print_help()
    exit(1)

if options.format not in ["geojson", "slimjson", "debug"]:
    parser.print_help()
    exit(1)

with open(options.input_file_name) as jsonfile:
    samples = json.load(jsonfile)

previous = None

for sample in samples:
    if options.id is not None:
        sample["id"] = options.id

tmp = "batch-%s" % random.randint(0, sys.maxint)
file = open(tmp, "w")

# Stores the results of map-matching to file
mapmatched_file = open(options.output_file_name, 'w+')

try:
    try:
        file.write(
            "{\"format\": \"%s\", \"request\": %s}\n" %
            (options.format, json.dumps(samples))
        )
    finally:
        file.close()

    output = ''

    s = socket.create_connection((options.host, options.port))
    try:
        with open(tmp) as f:
            s.sendall(f.read())
        s.shutdown(socket.SHUT_WR)
        buf = s.recv(4096)
        while buf:
            if len(output) < 16:
                output += buf
            sys.stdout.write(buf)
            mapmatched_file.write(buf)
            buf = s.recv(4096)
    finally:
        s.close()
finally:
    os.remove(tmp)
    mapmatched_file.close()

if not output.startswith('SUCCESS\n'):
    sys.exit(1)
