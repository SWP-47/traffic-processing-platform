# Sprint Review Transcript

> The meeting audio recording was transcribed using TurboScribe and translated from Russian to English using Qwen3.7-Plus, as reported in [LLM Report](llm-report.md). The final transcript was manually checked by @arinamnova.

**Date**: July 18, 2026

## Participants

* **Project Manager**: @jinseisieko
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln
* **Technical Writer**: @arinamnova
* Customer

## Transcript

**[Frontend Lead]** (00:00:32)\
I didn't add the basic placeholder login values you asked for in the last meeting. Instead, we implemented automatic token refresh. Now, when you refresh the page, the session is preserved and the connection happens automatically.

**[Project Manager]** (00:01:53)\
I can demonstrate the latest changes while the backend is loading.
First of all, we implemented a script to clean up the entire production environment on the server. With a single command, it issues a warning, stops all containers, and removes networks and volumes. Right now, the backend is completely shut down.
We also have an interactive deployment script. We just run `make deploy`, and it starts the containers, runs DB migrations, copies the `.env` file, and generates a random secret key for JWT. Then the script asks if we need to populate test data (create admin and viewer users). After selecting the deployment type (development or production), it launches everything in containers. The backend has successfully started.
There's also an option to add users via the CLI. For example, let's create a new admin: we specify the username and password. The script confirms the creation. There was a slight hiccup connecting to the DB because of the closed network in the production build, but ultimately the user is created. Now we can log in as the new admin.

**[Customer]** (00:06:55)\
Do I understand correctly that there is no difference between users? Are they all administrators?

**[Project Manager]** (00:06:57)\
Yes, all administrators have the same rights. But there is a viewer role, for which you can configure the scope—access specifically to certain channels. Then the channel list for such a user will be limited.

**[Customer]** (00:07:10)\
And this is configured only via the CLI script and the database?

**[Project Manager]** (00:07:12)\
Yes, only through the script.

**[Frontend Lead]** (00:07:24)\
As you can see, we've implemented a toggle to display statistics in packets per second or in bytes (bits, kilobytes, etc.) per second. If you select the active channel connected to the board, you can see the current activity.
We also made the host tables clickable. Now you can click on a specific host to view detailed statistics: Top Destinations and Top Ports.

**[Customer]** (00:07:56)\
I don't quite understand why the IP addresses in the table are jumping around.

**[Project Manager]** (00:08:05)\
Because of the small aggregation interval (1 second), so they update in real time.

**[Frontend Lead]** (00:08:15)\
Yes, regarding aggregation. We have a period selector (for example, the last 10 minutes), but the server itself determines the interval at which to send data points.

**[Customer]** (00:10:16)\
Is the aggregation for the chart and the tables synchronized?

**[Frontend Lead]** (00:10:25)\
They are synchronized. If you hover over a point on the chart, the window size for that point corresponds to the table updates. But this isn't a very convenient system, to be honest. I'd like to discuss how to make it more logical.

**[Customer]** (00:11:00)\
Why is the aggregation time different on the chart and in the tables?

**[Project Manager]** (00:11:15)\
It's not different. The toggles show the period for which we display the chart (e.g., 10 minutes). The server breaks this period into small intervals (the aggregation window). To keep the host table updating in real time, we transmit data specifically for this short aggregation window (1 second). If we synchronized the table with the historical period (10 minutes), it would lose its meaning, as it would just show the average over 10 minutes.

**[Customer]** (00:12:05)\
I agree, it's a non-trivial issue. We could show two different windows in the table: bind the left part (IP addresses and locations) to the long period (10 minutes) so the list of addresses changes rarely, and bind the right part (Unique Destinations, Ports) to real time (1 second). Essentially, this would require two queries.

**[Frontend Lead]** (00:16:25)\
I think it's not too hard, we just need to make changes on the frontend.

**[Project Manager]** (00:17:29)\
We can make it even simpler: maintain the table state on the frontend. Request new data once a second, update the metrics for existing IPs, and if an IP doesn't arrive, zero it out. If an IP hasn't updated for more than 10 minutes, remove it from the table.

**[Customer]** (00:18:30)\
Great idea. It will be much simpler on the frontend. We periodically request new data, update the state, and use the 10-minute timeout to clear outdated records.

**[Core Systems Engineer]** (00:19:11)\
There's a new feature on the board. Previously, the IP address for blocking was hardcoded, which caused issues in the last presentation. Now there's a script that allows you to dynamically set the IP for blocking directly on the board. By default, it's set to `0.0.0.0`, meaning nothing is blocked.

**[Customer]** (00:20:47)\
So `0.0.0.0` isn't treated as a mask, it just blocks a specific address?

**[Core Systems Engineer]** (00:21:04)\
Yes, it's a specific address. But now you can enter any IP you want to block. For example, this laptop's IP. Then the packets from it will drop to zero. This is a good demonstration that the blocking works.

**[Customer]** (00:23:50)\
Will ping (ICMP) be displayed?

**[Project Manager]** (00:23:55)\
Ping packets don't have ports (neither source nor destination). Due to strict typing in our system, if there is no port (null), such packets are currently ignored and don't make it into the port statistics.

**[Customer]** (00:24:28)\
So any protocols without ports are filtered out?

**[Project Manager]** (00:24:40)\
Yes, they are ignored for now. This can be fixed, but it will require a fix at the DB and parsing level.

**[Frontend Lead]** (00:27:53)\
By the way, are we collecting top ports only for outgoing traffic or for both directions?

**[Project Manager]** (00:28:00)\
Only for outgoing.

**[Customer]** (00:28:23)\
Got it. Alright, let's look at the pictures and streaming.

**[Core Systems Engineer]** (00:29:37)\
The laptop lost connection to the router, maybe the network slowed down or we accidentally bumped the cables. Before this, everything was fast.

**[Customer]** (00:30:22)\
Restarting the router probably won't help, it looks like the problem is in the network itself. But it was fast before.

**[Core Systems Engineer]** (00:32:00)\
Getting back to blocking: now IPs can be set dynamically. If you enter the laptop's IP, the traffic is blocked, and the packets drop to zero.

**[Customer]** (00:33:22)\
And is the "inactive" status displayed based on the amount of activity or the fact of connection?

**[Project Manager]** (00:34:59)\
Based on the amount of activity. If there have been no packets for the last 5 seconds, the channel is marked as inactive.

**[Customer]** (00:35:21)\
Look, for the demonstration, you'll need to record a video with the latest functionality.

**[Technical Writer]** (00:35:29)\
We already have a recording from last week, but we'll record a new one with the current setup.

**[Customer]** (00:35:34)\
I think the blocking functionality should be shown at the very end of the demo. You can start with blocking all traffic, and then show point blocking—for example, enter the IP address of a Telegram proxy into the script to show how a specific service is blocked.

**[Technical Writer]** (00:36:21)\
We'll see what's possible, there's very little time to prepare because of other electives. Most likely, we'll take snippets from the previous video.

**[Core Systems Engineer]** (00:37:37)\
Stress testing is still in progress, the traffic generation utility turned out to be the bottleneck. But it's definitely known that today the system withstood 588 Mbps without freezing.

**[Project Manager]** (00:37:59)\
We can just show that the loading works, the chart grows, and nothing freezes, just like last time.

**[Customer]** (00:38:37)\
Okay, great. Show me the changes in the Customer Handover document.

**[Project Manager]** (00:39:09)\
The Customer Handover document now specifies the interactive deployment script for the backend (`make deploy`). There were no other changes.

**[Customer]** (00:39:31)\
I took a look, everything works, the instructions are described. Excellent.

**[Technical Writer]** (00:39:42)\
Do you confirm the product status, that it is ready for independent use?

**[Customer]** (00:39:51)\
Yes, everything works. Excellent.

**[Technical Writer]** (00:40:00)\
Thank you, goodbye.
