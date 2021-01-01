#!/usr/bin/python3
# Copyright (C) 2013 - Remy van Elst

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Mark Ruys <mark.ruys@peercode.nl> - 2015-8-27
# Changelog: - catch openssl parsing errors
#            - clean up temporary file on error
#            - add support for PEM CRL's
#            - fix message when CRL has been expired
#            - pretty print duration

# Jeroen Nijhof <jnijhof@digidentity.eu>
# Changelog: - fixed timezone bug by comparing GMT with GMT
#            - changed hours to minutes for even more precision

# Remy van Elst - raymii.org - 2012
# 05.11.2012
# Changelog: - check with hours instead of dates for more precision,
#            - URL errors are now also catched as nagios exit code.

# Michele Baldessari - Leitner Technologies - 2011
# 23.08.2011

import time
import datetime
import getopt
import os
import pprint
import subprocess
import sys
import tempfile
import urllib.request, urllib.parse, urllib.error

# TODO evaluate to log all errors to some sensitive location.

def check_crl(url, warn, crit):
    # TODO ensure that temp files are always being deleted.
    tmpcrl = tempfile.mktemp(".crl")
    #request = urllib.request.urlretrieve(url, tmpcrl)
    try:
        urllib.request.urlretrieve(url, tmpcrl)
    except Exception as e:
        # TODO evaluate to introduce  an optional argument to enable/disable verbose output including exception traces.
        print("CRITICAL: CRL could not be retrieved: %s. Exception: %s" % (url, e))
        # TODO confirm if in this step the 'tmpcrl' is always expected to point to a valid file even if the previous 'urllib.request.urlretrieve' failed. In that case the following conditional might not be needed at all.
        if os.path.isfile(tmpcrl):
            os.remove(tmpcrl)
        sys.exit(2)

    try:
        # TODO confirm that the following logic allows for PEM and DER input.
        inform = 'DER'
        with open(tmpcrl, "rb") as crlfile:
            firstbyte = crlfile.read()[0]
            if firstbyte != 48: # First byte different than 0x30 (i.e. the start of DER SEQUENCE).
                inform = 'PEM'
        ret = subprocess.check_output(["/usr/bin/openssl", "crl", "-inform", inform, "-noout", "-nextupdate", "-in", tmpcrl], stderr=subprocess.STDOUT)
    except:
        os.remove(tmpcrl)
        # TODO check if UNKNOWN produces a Nagios notification, otherwise maybe a WARNING or CRITICAL would be better.
        print ("UNKNOWN: CRL could not be parsed: %s" % url)
        sys.exit(3)
    finally:
        # TODO should check if 'crlfile' is defined?.
        crlfile.close()

    nextupdate = ret.strip().decode('utf-8').split("=")
    os.remove(tmpcrl)
    eol = time.mktime(time.strptime(nextupdate[1],"%b %d %H:%M:%S %Y GMT"))
    today = time.mktime(datetime.datetime.utcnow().timetuple())
    minutes = (eol - today) / 60
    # TODO check: given that the input is always in minutes evaluate to always output minutes for clarity during calculations, maybe the additional info could be in parenthesis, e.g. days.
    if abs(minutes) < 4 * 60:
        expires = minutes
        unit = "minutes"
    elif abs(minutes) < 2 * 24 * 60:
        expires = minutes / 60
        unit = "hours"
    else:
        expires = minutes / (24 * 60)
        unit = "days"
    gmtstr = time.asctime(time.localtime(eol))
    if minutes < 0:
        msg = "CRITICAL CRL expired %d %s ago (on %s GMT)" % (-expires, unit, gmtstr)
        exitcode = 2
    elif minutes <= crit:
        msg = "CRITICAL CRL expires in %d %s (on %s GMT)" % (expires, unit, gmtstr)
        exitcode = 2
    elif minutes <= warn:
        msg = "WARNING CRL expires in %d %s (on %s GMT)" % (expires, unit, gmtstr)
        exitcode = 1
    else:
        msg = "OK CRL expires in %d %s (on %s GMT)" % (expires, unit, gmtstr)
        exitcode = 0

    print (msg)
    sys.exit(exitcode)

def check_crl_with_overlap(url, overlap):
    # TODO research better on the 'skew' concept and check if EJBCA supports it for CRLs. Note that we are currently hardcoding a 20%.
    # TODO check: if EJBCA supports the skew, allow to receive it as an optional parameter with a sensitive default.
    # TODO check maybe the correct term here would be generation_tolerance_and_skew, because this time represents the skew (exists in EJBCA CRL generation?) and the time allowed for the CA to generate the CRL after the overlap starts, e.g. EJBCA service period which could be 5 minutes or so?. Maybe receive an additional optional tolerance parameter?.
    # NOTE that skew (if exists in EJBCA) would be something like a fixed value, e.g. 10 mins, while 'generation_tolerance' will depend on the CA type (i.e. online or offline), in both cases 10% of the overlap by default could be ok but maybe, for example, for offline a value of several days, e.g. a week would be required and in that case that value should be received as a parameter.
    skew = overlap * 20 / 100
    warn = overlap - skew
    crit = warn / 2
    check_crl(url, warn, crit)

def usage():
    print ("check_crl.py -h|--help -v|--verbose -u|--url=<url> -o|--overlap -w|--warning=<minutes> -c|--critical=<minutes>")
    print ("")
    print ("Example, if you want to get a warning if a CRL expires in 8 hours and a critical if it expires in 6 hours:")
    print ("./check_crl.py -u \"http://domain.tld/url/crl.crl\" -w 480 -c 360")
    print("If you want to monitor a CRL which is being renewed with an overlap of 10 minutes (see \"CRL Overlap Time\" in https://doc.primekey.com/ejbca6152/ejbca-operations/ejbca-concept-guide/certificate-authority-overview/ca-fields#CAFields-CRL_Period):")
    print("./check_crl.py -u \"http://domain.tld/url/crl.crl\" -o 10")

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:o:w:c:", ["help", "url=", "overlap=", "warning=", "critical="])
    except getopt.GetoptError as err:
        usage()
        sys.exit(2)
    url = None
    warning = None
    critical = None
    overlap = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-u", "--url"):
            url = a
        elif o in ("-o", "--overlap"):
            overlap = a
        elif o in ("-w", "--warning"):
            warning = a
        elif o in ("-c", "--critical"):
            critical = a
        else:
            assert False, "unhandled option"
    if overlap != None:
        check_crl_with_overlap(url, int(overlap))
    elif url != None and warning != None and critical != None:
        check_crl(url, int(warning), int(critical))
    else:
        usage()
        sys.exit(2)


if __name__ == "__main__":
    main()
