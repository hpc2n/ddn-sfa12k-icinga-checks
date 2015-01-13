#!/usr/bin/python

import os
import site
import sys
import getopt

# The DDN python API modules are installed in /lap
site.addsitedir('/lap/python-ddn/lib/python2.7/site-packages')
sys.path.append('/opt/ddn')

from ddn.sfa.api import *

verbose = 0

# Statuses known to Icinga
exitstatus = { 'OK' : 0 , 'WARNING' : 1, 'CRITICAL' : 2 , 'UNKNOWN' : 3}

# Tests to run by default
run_test = 'all'

#### The tests

# Basic health check - returns state and a message
def basic_health(self, args):
    global verbose
    global exitstatus
    msg = ''

    system = args
    status = exitstatus['OK']

    for data in system.getAll():
        try:
            OID = data.OID
        except:
            OID = data.UUID

        try:
            name=data.Name
        except:
            name=''

        HealthState = data.HealthState
        HealthName = SFA_HEALTH_STATES.keys()[SFA_HEALTH_STATES.values().index(HealthState)]

        if verbose > 2:
            print "         %s(%s): %s(%d)" % (self, name, HealthName, HealthState)

        if HealthState == SFA_HEALTH_STATES['HEALTH_NA']:
            msg +='%s %s: Health state is not available - %s\n' % (HealthName, self, OID)
            tmpstatus = exitstatus['UNKNOWN']
        elif HealthState == SFA_HEALTH_STATES['HEALTH_OK']:
            # msg +=' %s: %s - %s %s\n' % (HealthName, self, name, OID)
            tmpstatus = exitstatus['OK']
        elif HealthState == SFA_HEALTH_STATES['HEALTH_NON_CRITICAL']:
            msg +='%s %s - %s\n' % (HealthName, self, OID)
            tmpstatus = exitstatus['WARNING']
        elif HealthState == SFA_HEALTH_STATES['HEALTH_CRITICAL']:
            msg +='%s %s - %s\n' % (HealthName, self, OID)
            tmpstatus = exitstatus['CRITICAL']
        elif HealthState == SFA_HEALTH_STATES['HEALTH_UNKNOWN']:
            msg +='%s %s: Health state is not available - %s\n' % (HealthName, self, OID)
            tmpstatus = exitstatus['UNKNOWN']
        else:
            msg +='%s %s: Unreachable state - %s\n' % (HealthName, self, OID)
            tmpstatus = exitstatus['UNKNOWN']
        if tmpstatus > status:
            status = tmpstatus
    return (status, msg)

def fan_health(self, args):
    global exitstatus
    system = args
    msg=''

    for data in system.getAll():
        if data.Fault:
            msg +=' %s CRITICAL: Fan failure.' % self
            status = exitstatus['CRITICAL']
        elif data.PredictFailure:
            msg += ' %s WARNING: Predicted fan failure.' % self
            status = exitstatus['WARNING']
        else:
            msg=''
            status = exitstatus['OK']

    return(status,msg)

def dummy_check(self, args):
    global exitstatus
    return (exitstatus['OK'], '')

allcomponents = {
    'SFAStorageSystem'      : (SFAStorageSystem, [basic_health]),      # Overall health check
    'SFAController'         : (SFAController, [basic_health]),
    'SFAEnclosure'          : (SFAEnclosure, [basic_health]),
    'SFAExpander'           : (SFAExpander, [basic_health]),
    'SFADiskChannel'        : (SFADiskChannel, [basic_health]),
    'SFAHost'               : (SFADiskChannel, [basic_health]),
    'SFADiskDrive'          : (SFADiskDrive, [basic_health]),
    'SFADiskSlot'           : (SFADiskSlot, [basic_health]),
    'SFAFan'                : (SFAFan, [basic_health, fan_health]),
    # 'SFAHostChannel'        : (SFAHostChannel, []),
    # 'SFAHostChannelErrors'  : (SFAHostChannelErrors, [basic_health]),
    'SFAPowerSupply'        : (SFAPowerSupply, [basic_health]),
    'SFAStoragePool'        : (SFAStoragePool, [basic_health]),
    'SFATemperatureSensor'  : (SFATemperatureSensor, [basic_health]),
    'SFAUnassignedPool'     : (SFAUnassignedPool, [basic_health]),
    'SFAUPS'                : (SFAUPS, [basic_health]),
    'SFAVoltageSensor'      : (SFAVoltageSensor, [basic_health]),
}

def main(argv, environ):
    global verbose

    try:
        opts, args = getopt.gnu_getopt(argv[1:], '', ['sfa=', 'verbose', 'test=',
                                                      'user=', 'password='])
    except getopt.GetoptError, (err, opt):
        print str(err)
        sys.exit(1)

    #FIXME: Get these from the config-file/commandline
    sfa_username = None
    sfa_password = None
    # Don't default to any host
    sfa_hostname = None

    for key, value in opts:
        if key == '--sfa':
            sfa_hostname = value
        if key == '--verbose':
            verbose += 1
        if key == '--test':
            run_test = value
        if key == '--user':
            sfa_username = value
        if key == '--password':
            sfa_password = value

    if not sfa_hostname:
        print ('You must use --sfa=<hostname>')
        sys.exit(97)

    if not sfa_username or not sfa_password:
        print ('Username or password is missing.')
        sys.exit(98)

    if run_test == 'all':
        components = allcomponents
    elif run_test in allcomponents:
        components = dict((key, value) for key, value in allcomponents.items() if key == run_test)
    else:
        print ('CRITICAL: Test %s is not available' % run_test)
        sys.exit(exitstatus['CRITICAL'])

    # Connect to the SFA
    APIConnect('https://%s' % sfa_hostname, auth=(sfa_username, sfa_password))

    if verbose > 0:
        print "Tests: %s\n" % components.keys()

    checks_run = 0
    # Default exit status
    status = exitstatus['OK']
    msg = ''
    for componentname,(method,checks) in components.iteritems():
        if verbose > 0:
            print 'Running %s...' % componentname
        if verbose > 2:
            print ' Method: %s' % method
            print ' Checks: %s' % checks

        for check in checks:
            if verbose > 1:
                print "     Check: %s" % check
            checks_run += 1
            (tmpstatus, tmpmsg) = check(componentname, method)
            msg += tmpmsg
            if tmpstatus > status:
                status = tmpstatus
            if verbose > 2:
                print '     Result: %d, %s' % (status, msg)
    # Done - disconnect
    APIDisconnect()

    #
    if status == exitstatus['CRITICAL']:
        print "CRITICAL: %s" % msg
        sys.exit(exitstatus['CRITICAL'])
    elif status == exitstatus['WARNING']:
        print "WARNING: %s" % msg
        sys.exit(exitstatus['WARNING'])
    elif status == exitstatus['UNKNOWN']:
        print "UNKNOWN: %s" % msg
        sys.exit(exitstatus['UNKNOWN'])
    elif status == exitstatus['OK']:
        msg = "%d checks run %s" % (checks_run, msg)
        print "OK: %s" % msg
        sys.exit(exitstatus['OK'])
    else:
        print 'UNKNOWN: Unreachable state: %s\n' % msg
        status = exitstatus['UNKNOWN']

    # Should never be reached
    sys.exit(99)

if __name__ == "__main__":
    main (sys.argv, os.environ)
