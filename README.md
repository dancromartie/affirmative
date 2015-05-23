# affirmative
a python webservice for making sure events happen

# Overview

## What it does ##
This isn't monitoring per se, nor testing.  This is kind of a "daily
checklist for technology operations".  For example "make sure that model xyz
seems to be under control" is something that you want to verify every 3 days.
You can either have a person click a button to verify it, or you might have a
script that runs complicated checks and then calls Affirmative's API.  

This is monitoring in a way, but you can't ask it the same question at any time
and expect a reasonable answer to come back, like you often can when you are
monitoring for server connectivity or for responsiveness of some app. 

It's testing in a way, but baked in to your actual operations.  We often feel
good after we test something, but then we don't realize that the thing we were
trying to make happen with our code never happened for reasons outside of our
control.  Even if your code is flawless, another service that you are expecting
to contact your app might stop doing so for a great number of reasons.  Maybe they
changed the frequency of their cron jobs.  Maybe your company stopped getting
customers because a designer broke all the CSS on some page that's far removed
from your app.  No matter what, there are some things that you just want to
_know_ are happening.

That's where these "positive affirmations" come in.  It's not logging an error,
because there was no "error".  You just want to know that sh!t is getting done,
whether it be you writing your one piece of docs for the day, your team pair
programming for an hour, or your daily backup routine finishing and passing all
integrity tests.

## Example Use Cases ##

You can configure a series of "checks" or "events" that have to happen periodically.

A cron like format is used to say when each check is performed.

For instance, you might have a check named "etl_3d3de3et_ran_with_no_problems".
You want to check this at 1am, 7am, and 4pm on weekdays, and each time you
check for it, you want to make sure it happened in the 20 minutes before the
check.  A real system cron can email you when a cron job failed, but this app
tries to stay on top of whether the cron ran at all.  Sometimes a developer
turns off a cronjob accidentally for a few weeks while it breaks something
subtly.

In the language of this app, you would say "run at * 1,7,16 * * 1-5, and each
time, look for 1 event with a lookback of 20 minutes".


Similarly, you might want to make sure that a certain health check completes at
least 4 times every 5 minutes.  You could say event "app_xyz_health_check_good
runs */5 * * * *, requires 4 events with a lookback of 5 minutes".

All of the event data is available via some API urls, so people can do whatever they want with it,
but I've made these basic cron checks out of the box.  If you _only_ want to store raw event data, this is probably a bad tool for that.

## Libraries / Scripts for various languages ##

Right now there is a python module that can be used like:
```python
import affirmative_client

ac = affirmative_client.Client("http://localhost:5123", "prod")
for i in range(1, 100):
    print "sending!"
    ac.affirm_one("that_critical_app_health_check", "good")
```
The second argument is ignored for now, but it's meant to be an arbitrary string in case there's use 
for a little JSON payload or a little discrimination on the client's part when they consume some API endpoints.

And there's a shell script that can be used like:

```
./shell_client.sh localhost:5123 prod machine_learning_model_under_control
```

I hope to add a javascript version too, so that you can record "sign-off" events
from a gui as well, or simply track usage of certain features (from an "is this
broken and theyre just not telling me" kind of perspective - there are probably
other better tools for tracking intricate usage patterns on a UI)

Since I personally deal with a lot of R, or with a lot of people who use R (even for batch jobs), I
might add an R wrapper too.


## Keys ##

Each event name has an associated short, ugly, random "key" that goes along
with it.  I need to think about this better, but the idea is that if you put it
in your code (maybe as a comment) right by the lines of code that log the
events, all of those occurences can be grepped out by a code search tool or
command line.  That will open the door to future stuff like "show me everywhere
I touch this event's statistics" which might improve software quality a
little...  If the definition of what qualifies as the event changes, then
having multiple calls with different ideas of the metric can wreak havoc on
your business processes, and you want to make sure you find them all.  Not sure
how you would get around old production binaries etc, but it would help at
least.


## Technologies ##
This uses Flask and sqlite.  There are plenty of javascript libraries for the
UI, but all the scripts come from CDNs, so the number of dependencies is pretty
low.  The sqlite database is in-memory for the actual event data, but all of
the configuration is stored on disk.  Eventually the in memory database should
dump records to a file on disk periodically to improve resilience.


## Screenshots ##
### Configuration Page ###
![Alt text](/screenshots/config_events.png?raw=true "Optional title")
### Monitoring Page ###
![Alt text](/screenshots/view_events.png?raw=true "Optional title")

# Dev details

## Starting the app
Run ./start_dev.sh.  The start script is pretty simple. Look at it to see the arguments, 
but defaults are provided.

## Running the sample client
Run python run_client_test.py.  This requires that you have the event names referenced in that file 
created already.

## Keeping the checks running
While this tries to wrap a cron like thing, the actual checks are run minutely by a cron 
job.  Setting that job up on your local machine might not be what you want, so I like to do this 
in another terminal tab:

```
for run in {1..1000}; do curl "http://localhost:5123/affirmative/do_minutely_cron_dont_touch_this" && sleep 60; done;
```

This will run the minutely checks for 1000 minutes.  You could set up the cron in your own crontab 
or use Vagrant or something to run this all so you don't muck up your machine.


## Clearing all checks
Restart the server to wipe out the in-memory database.  Hopefully there will be a better way 
in the future.







