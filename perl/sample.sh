#!/bin/bash

# Usage:   ./honeywell_settmp.sh [-c|-h|-o] [<temp(F)>|schedule]
# Example: ./honeywell_settmp.sh -h 72        # set HEAT: temp=72F
#          ./honeywell_settmp.sh -c schedule  # set COOL: follow shceduled temp
#          ./honeywell_settmp.sh -o           # turn system OFF

######## Settings ########
LOGIN="Me@gmail.com"
PASSWORD="MyPassword!"
DEVICE_ID=1196305      # number at the end of URL of the honeywell control page
##########################

SW=null
STATUS=1
MODE=Heat
FAN=null
NO_SEND=0

function usage {
  echo "usage: $0 [-achofF] [<temp>|schedule]"
  echo "  <temp>:   hold temp until next schedule"
  echo "  shcedule: follow scheduled temp settings"
  echo "options:"
  echo "  -a : set system to AUTO"
  echo "  -c : set system to COOL"
  echo "  -h : set system to HEAT"
  echo "  -o : set system to OFF"
  echo "  -f : set fan to ON"
  echo "  -F : set fan to AUTO"
  echo "  -n : no settings; just read status"
}

while getopts "achofFn" flag; do
  case $flag in
    \?) usage; exit;;
    a) SW=4; TEMP="";;
    c) SW=3; MODE=Cool;;
    h) SW=1;;
    o) SW=2;;
    f) FAN=1;;
    F) FAN=0;;
    n) NO_SEND=1;;
  esac
done
shift $(( $OPTIND - 1 ))

TEMP="$1"
[ "$TEMP" = "" ] && STATUS=null
[ "$TEMP" = "" ] && TEMP=null

[ "$TEMP" = "schedule" ] && STATUS=0
[ "$TEMP" = "schedule" ] && TEMP=null
set -x
# Login
curl -s -c /tmp/honeywell_cookie.dat https://mytotalconnectcomfort.com/portal/ -d UserName="$LOGIN" -d Password="$PASSWORD" -d timeOffset=0 > /dev/null

# Set Temp
if [ "$NO_SEND" = 0 ]; then
  CMD='{"DeviceID":'$DEVICE_ID',"'$MODE'Setpoint":'$TEMP',"SystemSwitch":'$SW',"StatusHeat":'$STATUS',"StatusCool":'$STATUS',"FanMode":'$FAN'}'
echo "$CMD"
  curl -s -b /tmp/honeywell_cookie.dat https://mytotalconnectcomfort.com/portal/Device/SubmitControlScreenChanges  -H 'Content-Type:application/json; charset=UTF-8' -d "$CMD"
  echo
fi

# Get Status
curl -s -b /tmp/honeywell_cookie.dat https://mytotalconnectcomfort.com/portal/Device/CheckDataSession/"$DEVICE_ID" -H X-Requested-With:XMLHttpRequest
echo

rm -f /tmp/honeywell_cookie.dat
