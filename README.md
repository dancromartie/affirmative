# affirmative
a python webservice for making sure events happen

## Why another one of these? ##
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
because there was no "error".  You just want to know that sh*t is getting done,
whether it be you writing your one piece of docs for the day, your team pair
programming for an hour, or your daily backup routine finishing and passing all
integrity tests.
