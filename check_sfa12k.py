#!/usr/bin/python

import os
import sys
import getopt
import tempfile

sys.path.append('/opt/ddn')

#FIXME:
from ddnsfa.clui import SfaShowall

sfa_hostname = None
sfa_port = None
target_dir = None
quiet = False

try:
    opts, args = getopt.gnu_getopt(sys.argv[1:], '', ['sfa=', 'port=', 'dir=', 'quiet'])
except getopt.GetoptError, (err, opt):
    print str(err)
    sys.exit(1)

for key, value in opts:
    if key == '--sfa':
        sfa_hostname = value
    if key == '--port':
        sfa_port = value
    if key == '--dir':
        target_dir = value
    if key == '--quiet':
        quiet = True

if not sfa_hostname:
    print ('You must use --sfa=<hostname>')
    sys.exit(1)

print 'Icinga status: ...'
sys.exit(0)
