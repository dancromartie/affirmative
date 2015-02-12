#!/usr/bin/env bash

port=$1
if [ -z $1 ]
    then port="5123"
fi

instance=$2
if [ -z $2 ]
    then instance="default"
fi

proc_name=$3
if [ -z $3 ]
    then proc_name="AFFIRMATIVEDEVAPP"
fi

# The -n argument isn't really used, but it will show up in the command line 
# so we can kill the app easier.
gunicorn -b 0.0.0.0:$port -w 1 -t 30 \
    affirmative_server:"build_app(debug=True, instance='$instance')" \
    --access-logfile ../logs/affirmative.access.log -n $proc_name
