#!/usr/bin/env bash
# The -n argument isn't really used, but it will show up in the command line 
# so we can kill the app easier.
nohup gunicorn -b 0.0.0.0:5123 -w 1 -t 30 \
    affirmative_server:"build_app(debug=True)" \
    --access-logfile ../logs/affirmative.access.log -n AFFIRMATIVEDEVAPP
