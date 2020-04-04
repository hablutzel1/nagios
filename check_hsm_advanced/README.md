# Monitor a Safenet ProtectServer HSM
Author: R. van Elst (https://raymii.org)

## hsm.sh

### Usage

    usage: ./hsm.sh options

    This script checks various safenet HSM things and outputs nagios style results.

    OPTIONS:
       -h      Show this message
       -t      Check type: "battery", "RAM", "datetime", "eventlog", "initialized", "hsminfo", "fminfo"
       -n      HSM name for $ET_HSM_NETCLIENT_SERVERLIST.
       -b      ctcheck binary (default: /opt/PTK/bin/ctcheck)

    CHECKS:
       battery          Show HSM Battery status, GOOD (ok) or LOW (crit)
       ram              HSM RAM, (ok) if <75% used, (warn) >75% <85% used, (crit) if >85% used.
       datetime         Local HSM date/time, (crit) if different from host time, host should use ntp in same timezone.
       eventlog         (ok) if eventlog not full, (crit) if eventlog full.
       initialized      (ok) if initialized, (crit) if not. Documentation states that a FALSE could mean a tampered device.
       hsminfo          always (ok), returns general HSM info, model, version, firmware and such.
       fminfo           always (ok), returns Funcrtional Module information.




### Examples

    user@host ~$ ./hsm.sh -n hsm-038 -t ram
    OK: RAM Usage OK: 41% used, ( 10192256 total). HSM: hsm-038.
    user@host ~$ ./hsm.sh -n hsm-038 -t datetime
    OK: HSM: hsm-038 time is the same as local time: 15/04/2013 12:48.
    user@host ~$ ./hsm.sh -n hsm-038 -t eventlog
    OK: HSM: hsm-038 Event Log Count: 11
    user@host ~$ ./hsm.sh -n hsm-038 -t initialized
    OK: HSM: hsm-038 is initialized. All is well.
    user@host ~$ ./hsm.sh -n hsm-038 -t hsminfo
    OK: HSM: hsm-038; Serial Number:[...]; Model: [...]; Device Revision: F; Firmware Revision: [...]; Manufacturing Date: [...]; Device Batch: [...]; PTKC Revision: [...]; Slot Count: [...] Security Mode: [...]; Transport Mode:[...]; Event Log Count: 88.
    user@host ~$ ./hsm.sh -n hsm-038 -t battery
    OK: Battery status is good for HSM: hsm-038

## check_protectserver_appliance_load.sh

**Usage of this plugin is (currently) very dangerous cause several failed attempts to login to the appliance through SSH could potentially lock the 'admin' account permanently, requiring to destroy all HSM objects for recovery.**

- TODO test and confirm if 10 consecutive failed login attempts with 'pseoperator' account could lock permanently the 'admin' account as the documentation isn't totally clear about it: "As a security measure, the admin account is locked out after 10 consecutive failed login attempts using the console". Consider that maybe if the 'pseoperator' user is locked, the 'admin' user could unlock it, which could allow us to remove the warning above.

### Usage

Before the usage of this check plugin it is required to set up a SSH master connection:

```
$ ssh -fNMS "~/.ssh/S.%r@%h:%p" pseoperator@<HSM_IP>
```

Note: When calling the check plugin as a Nagios active check, the previous will require to be executed for the user running the Nagios process, for example, with something like `sudo -u nagios ...`. 

Then the check plugin can be called like this:

```
./check_protectserver_appliance_load.sh <HSM_IP> <WLOAD1> <WLOAD5> <WLOAD10> <CLOAD1> <CLOAD5> <CLOAD10>
```
