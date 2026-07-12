# Sprint Review Transcript

> The meeting audio recording was transcribed using TurboScribe and translated from Russian to English using Qwen3.7-Plus, as reported in [LLM Report](llm-report.md). The final transcript was manually checked by @arinamnova.

**Date**: July 11, 2026

## Participants

* **Project Manager**: @jinseisieko
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln
* **Technical Writer**: @arinamnova
* Customer

## Transcript

**[Technical Writer]** (0:02)\
The goal of this meeting is to show what we've accomplished this week and discuss the final steps. We will be delivering the final product version (MVP v3) and will show the documentation for your future use. What have we done this week?

**[Project Manager]** (0:19)\
I'll start with the server. First, we've added protocol storage and aggregation to the database. The telemetry table, which aggregates 1-second buckets in real-time, now does so with protocol-level breakdown. We've written a large number of tests to achieve 70% backend coverage, including integration tests. We also created a dedicated module for unified database interaction across all services.

**[Customer]** (0:48)\
How is the 70% backend coverage measured?

**[Project Manager]** (0:52)\
By the number of lines of code covered by the tests.

**[Customer]** (0:56)\
And how many lines of code are there in total?

**[Project Manager]** (1:00)\
Around 25,000, possibly more.

**[Customer]** (1:05)\
Alright, got it.

**[Core Systems Engineer]** (1:34)\
Regarding the testbed: all the issues we had last time are fixed. It now works correctly, including when cables are disconnected and reconnected. You can verify this today. We also have a fix in development for a bug where fragmented packets were being sent during blocking. The fix is written but not yet deployed to the testbed, so the hardware blocking feature won't be demonstrated today.

**[Frontend Lead]** (2:04)\
On the user interface, we've worked on detailed per-host statistics. It doesn't display protocol data yet, but we can already show part of the traffic statistics for a specific host.

**[Technical Writer]** (2:24)\
You can now test the testbed just like you did last time. We've prepared tabs with Wikipedia and online radio to test the system under load.

**[Customer]** (4:07)\
Let me make sure I understand the demo setup correctly. It consists of a user laptop connected via wire to the board, and the traffic seamlessly routes to the router? The second laptop displays the Management User Interface (MUI) in real-time. The third laptop is the CnSS, but as a user, I don't need to interact with it. Do the metrics on the interface reflect real activity?

**[Core Systems Engineer]** (4:25)\
Yes, that's correct.

**[Customer]** (5:28)\
Last time we had speed issues with Wikipedia. Should the images load quickly now?

**[Core Systems Engineer]** (5:28)\
It depends on the university router's load. But the online radio should definitely work well and show stable activity.

**[Customer]** (7:16)\
Let's load the radio and look at the activity. Right now, received traffic is higher than sent. Streaming is implemented over TCP: large data packets go in one direction, and only small ACK packets are sent back. But on the chart, the packet count in both directions looks identical. This is because one large data packet gets one ACK. Is the measurement here strictly in packet count, or is the data volume also recorded?

**[Project Manager]** (9:15)\
Yes, right now the measurement is strictly in packet count.

**[Customer]** (11:47)\
Let's stop the load now. The activity should drop to almost zero. Great, it works. But what are those two packets still flying through? Probably background traffic. Rebooting helps reset the state.

**[Customer]** (11:56)\
Now let's run a stress test. We'll load something heavy. The speed jumps to 30 megabytes per second—that's about 240-250 megabits per second. Look, the system crashed. Apparently, the CnSS or CN can't keep up with processing this volume of data.

**[Core Systems Engineer]** (12:19)\
If it crashed, the queue most likely overflowed. Judging by the logs, it got too large.

**[Customer]** (12:34)\
Judging by the behavior, the CN just hung. Does the system work if we don't push it to the extreme and avoid stress testing? Yes, it works well. We can reboot the CN to clear the queue. By the way, have you determined the maximum traffic speed at which the testbed operates stably?

**[Project Manager]** (23:44)\
We haven't tested the entire testbed under such heavy load.

**[Customer]** (21:34)\
That needs to be done. If in the future the system stops working at 250 megabits, you need to be ready to answer that it's only rated for, say, 100 megabits. But that's a "nice to have" task.

Now for the priority item. Do I understand correctly that the laptop part of the Traffic Processor collects metadata and sends it to the server only in packets per second?

**[Core Systems Engineer]** (23:47)\
Yes.

**[Customer]** (24:04)\
The picture we saw during audio streaming raises questions: the RX and TX charts look identical, even though we're mostly just downloading traffic. It would be much more useful to display statistics in bits or bytes per second. If you store the packet header in the database, it shouldn't be too difficult.

**[Project Manager]** (25:16)\
It's not hard to add this feature in the backend: we just need to sum the sizes of all packets in a bucket and add one field. There are no issues with the amount of information.

**[Customer]** (26:11)\
Globally, this is a more useful enhancement than just per-host details. There should be a toggle between displaying packets and bytes. If it's too difficult, you can just make two separate endpoints or pages. But we should try. Among the less priority items—detailed per-host statistics and the map, for which you probably don't have enough time anymore?

**[Technical Writer]** (27:43)\
Yes, due to the implementation of calculating the size of each packet, most likely only this feature will make it into this sprint.

**[Frontend Lead]** (29:21)\
I can show the first version of the detailed host page. Here you can click to go to the details of a specific host. Right now it's a basic demo version: it shows packet transmission statistics, a chart, and a set of destination addresses.

**[Customer]** (29:58)\
Excellent. So this is the local address and the address where it sends data.

**[Technical Writer]** (30:15)\
As for the final points, we've prepared the handover documents for you. Here is the Handover document. It contains the launch instructions. Take a look, and if anything is missing, we'll add it.

**[Customer]** (30:30)\
At a glance, everything is clear, excellent. We'll need to sit down and figure it out later to see how convenient it is.

**[Project Manager]** (30:45)\
Server deployment is currently quite complex because you have to manually migrate the database tables. I'll likely write a script to simplify this process.

**[Customer]** (31:00)\
Classic problem. You just add a wait for the database to be ready at the end of the startup script, and then run the command to apply migrations. The main thing is that it's clearly documented step-by-step.

**[Technical Writer]** (31:20)\
Next week we'll try to implement packet size calculation, finish the detailed statistics, and fix the last bugs. Thank you, goodbye.
