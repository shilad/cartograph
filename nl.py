#!/usr/bin/python -O

import sys

for i, line in enumerate(sys.stdin):
	sys.stdout.write('%d\t%s' % (i+1, line))
