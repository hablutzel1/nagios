#!/bin/bash
set -eo pipefail
#######
# WARNING: This script relies on a master SSH connection as the appliance 'pseoperator' user, so a possible compromise in the server executing this script could compromise the appliance considering that the 'pseoperator' user has more permissions that the required to execute 'status cpu' and apparently these permissions can't be reduced. Additionally, it seems that it is not possible to create another user more limited than 'pseoperator'.
#######

hsm_hostname=$1
# NOTE that the "PSESH Command Reference Guide > PSESH Commands > status" says the following about the third average: "3.The average CPU load for the previous ten minutes.", but note that this third average in the case of the standard (?) 'uptime' command is for 15 minutes, so maybe there is an error in SafeNet documentation and it is really for 15 minutes here. TODO measure and confirm it. See too https://support.nagios.com/kb/article/load-checks-771.html.
warning=($2 $3 $4)
critical=($5 $6 $7)

# Validating arguments.
for idx in 0 1 2
do
re='^[0-9]+([.][0-9]+)?$'
if ! [[ ${warning[idx]} =~ $re && ${critical[idx]} =~ $re ]] ; then
   echo "Invalid number provided" >&2
   exit 2
fi
done

# TODO IMPORTANT: to avoid locking SSH access to the appliance, if a response of "Account locked due to X failed logins" is received, make all the following attempts to execute this plugin fail prematurely, maybe by writing a lock file that should be removed manually, e.g. /tmp/check_protectserver_appliance_load_locked_<HSM_HOSTNAME>. Check too if there is any possibility to get the status of auth attempts through SSH without attempting to authenticate again yet.
status_cpu_output=$(ssh -S "~/.ssh/S.%r@%h:%p" pseoperator@$hsm_hostname "status cpu")
# TODO research on the 4th output column from "CPU Load Averages", e.g. "0.00 0.00 0.00 1/117 6075".
cpu_load_averages_line=$(echo "$status_cpu_output" | grep -A1 "CPU Load Averages" | tail -n 1)
# TODO look for the cleanest way to introduce the following regex capturing logic in a Bash script.
regex='([0-9.]*) ([0-9.]*) ([0-9.]*).*'
[[ ${cpu_load_averages_line} =~ $regex ]]
# See too nagios-plugins/plugins/check_load.c for a similar logic.
res=0 # OK
for idx in 0 1 2
do
    cur_load_average=${BASH_REMATCH[idx+1]}
    # FIXME if there is any problem with the execution of bc in the following conditionals (e.g. 'bc' not found), the overall result for the script will still be 0 (OK).
    if (( $( echo "$cur_load_average > ${critical[idx]}" | bc -l) )); then
        res=2 # CRITICAL
        break;
    elif (( $( echo "$cur_load_average > ${warning[idx]}" | bc -l) )); then
        res=1 # WARNING
        break;
    fi
done

echo "load average: ${BASH_REMATCH[1]} ${BASH_REMATCH[2]} ${BASH_REMATCH[3]}"
exit ${res}
