# affirmative
python webservice for making sure events happen.

# Overview

## TL;DR 

Send event "called_customer" to service when you call a customer.
At times specified by "0,30 * * * 1-5", make sure you get between 35 and 90 events in the 45 minutes
preceding the check. 

OR maybe...

Send event "some_app_alive" to service when it is pinged.
At times specified by "*, *, *, *, 1-5", make sure you get between 1 and 1 events in the 1 minute 
preceding the check. 

## What it does ##

This isn't monitoring per se, nor testing.  This is kind of a "checklist for
(technology) operations".  For example "make sure that model xyz seems to be
under control" is something that you want to verify every 3 days.  You can
either have a person click a button to verify it, or you might have a script
that runs complicated checks and then calls Affirmative's API.  

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

That's where these "confirmations"/"heartbeats" come in.  It's not logging an error,
because there was no "error".  You just want to know that stuff is getting done,
whether it be you writing your one piece of docs for the day, your team pair
programming for an hour sometime this week, an app being alive, or your daily backup routine
finishing and passing all integrity tests.

## Example Use Cases ##

You can configure a series of "checks" or "events" that have to happen periodically.

A cron-like format is used to say when each check is performed.

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

All of the event data is available via some API urls, so people can do whatever
they want with it, but I've made these basic cron checks out of the box.  If
you _only_ want to store raw event data, this is probably a bad tool for that.

## Examples for various languages ##

There are two endpoints right now.  "simplest" and "store".  "store" is general purpose, and 
allows for multiple events, setting a specific timestamp (in the case of network slowness, etc), 
and json payloads.  Read the source to figure out how to use "store".  It's a pretty simple JSON 
input.

The endpoint "simplest" takes a POST request with a form parameter of "event_name".  That's all.  
I used to have a client module that would package requests up and set a timeout and cert verification 
preferences and all, but that was dumb.  Just do something like:

```python
import requests

url = "http://localhost:5123/affirmative/simplest"
data = {"event_name": "sometest"}
requests.post(url, data=data, verify=False)
```

The second argument is ignored for now, but it's meant to be an arbitrary
string in case there's use for a little JSON payload or a little discrimination
on the client's part when they consume some API endpoints.


Here's an example in R, showing the more complicated format for "store".  You should be able to 
replicate the "simplest" procedure shown for python in no time, though.

```R
AffirmOne <- function(url, eventName, data){
    time <- as.integer(as.POSIXct( Sys.time() ))
    dataAsObj <- list(events=list(list(name=eventName, time=time, data=data)))
    curlPerform(url = url,
        httpheader=c('Content-Type'= "application/json"),
        postfields=RJSONIO::toJSON(dataAsObj),
        verbose = TRUE
    )
}

affirmativeEndpoint <- "http://localhost:5123/affirmative/store"

AffirmOne(affirmativeEndpoint, "rtest", "ok")
AffirmOne(affirmativeEndpoint, "rtest", "still ok")
AffirmOne(affirmativeEndpoint, "rtest", "yep still ok")
```

For now, you can look at the "trigger page" to see how to implement your own JS client.  That 
code should make it obvious how to trigger events from JS, if you don't already know how to POST 
things from JS.  I think it's simplest to just make your own wrappers here.

## keys vs event names##

Each "cron" that you configure has as associated key (i.e. a random unique id).
For instance, you might have an event "complaint_received", and you want to
make sure that on weekdays you're getting at least 3 complaints a day, but on
weekends you expect at least 1.  You would set up two "cron"s with the same
name, but the _check_ is what has a key.


## Technologies ##
This uses Flask and sqlite.  There are plenty of javascript libraries for the
UI, but those are pretty easy to install or come from CDNs, so installation
should really just require installing Flask and starting the server.

## Why not more?

I am constantly tempted to put complicated things in here like checking against statistical limits, 
looking for spikes and anomalies, checking averages/null proportions/percentiles etc.  Every time 
I've thought about it so far, it just feels forced.  It's hard to make everybody happy with that.
When I think of my employer's data monitoring problems, there aren't so many things that fit into 
a framework neatly.  Some things are hairy and so have analysts combing over charts and timeseries.  
Some things get so segmented and "grouped by" that maintaining these keys would be quite tedious.

My suggestion to get around that is to use this as the alerting infrastructure.  For the metrics 
you really care about, put some checks in a script and run it on a cron.  If your numbers don't 
look good, or if that average looks too high or its a 30% spike from yesterday, don't send your 
this_process_looks_good key to affirmative.  It will alert you as soon as the script finishes if you 
configured your event checked right. If your script failed before it got to send confirmation, 
you'll be investigating the next morning either way!

## Actually sending negative events

Now, there's all this talk about sending positive acknowledgement, but you
don't have to.  One approach is to set a key that allows 0 events every minute,
for example.  If you send an event like "problems_with_my_app", then within a
minute, you should get an alert on that.  In fact, doing this along with the
positive events may be a very strong combination.


## Screenshots ##
### Configuration Page ###
![Alt text](/screenshots/config_events.png?raw=true "Optional title")
### Monitoring Page ###
![Alt text](/screenshots/view_events.png?raw=true "Optional title")

# Dev details

## Starting the app
Run ./start_dev.sh.  The start script is pretty simple. Look at it to see the arguments, 
but defaults are provided.

## Logging some test events
Run python run_client_test.py.  This requires that you have the event names referenced in that file 
created already.

## Logs
Are stored in the logs folder by default.  There is an access log, and error
log for things that are outside of your app's control (syntax errors, gunicorn
couldn't start etc), and everything else is in the plan .log file.

## Keeping the checks running
While this tries to wrap a cron like thing, the actual checks are run minutely by a cron 
job.  Setting that job up on your local machine might not be what you want, so you can use the 
scripts/do_checks.py script.  It will run the checks on a 60 second (or user specified) interval.

For testing, I also like to just put the special check url in my browser bar
and trigger the event with a page refresh if I don't want to wait a minute
between checks.  It shouldn't really be a GET request, but I liked having it be
triggered so simply.
