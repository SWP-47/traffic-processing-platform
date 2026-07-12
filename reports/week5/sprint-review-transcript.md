# Sprint Review Transcript

> The meeting audio recording was transcribed using TurboScribe and translated from Russian to English using Qwen3.7-Plus, as reported in [LLM Report](llm-report.md). The final transcript was manually checked by @arinamnova.

**Date**: July 4, 2026

## Participants

* **Project Manager**: @jinseisieko
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln
* **Technical Writer**: @arinamnova
* Customer

## Transcript

**[Core Systems Engineer]** (0:39)\
What we wanted to show you is the updated version of the Traffic Processor and Communication Node. Overall, this is implemented in Docker containers, but unfortunately, they don't play very well with the Ubuntu instance running on the testbed right now. So, this is what the assembled testbed looks like in reality, except that the Docker containers aren't being used yet. This is a LAN simulation: the white cable on the board is the local network, and there's a cable coming from a router or another device. The next two cables connect to the device where the CN and TP are located, and the green cable is the WAN. Right now, it's plugged into the router and has access to the university's local network, so there's internet access through the board. Feel free to try finding something or look for something interesting.

**[Customer]** (4:46)\
So, the internet works here as usual?

**[Core Systems Engineer]** (4:55)\
Right now it's working, but we've implemented the first version of blocking—this was the third level of functionality. For now, it's only done via a button on the board itself. If you press Key1 once, the traffic should be blocked. It's currently hardcoded specifically to the IP of this device, and that's exactly what gets blocked. But we plan to expand this feature in the future.

**[Customer]** (5:15)\
So the internet works, but if you press the blocking button, it's gone completely? And it's "not very good" in the sense that it's because of the university? Is this the local network segment?

**[Core Systems Engineer]** (5:30)\
Yes. I tested it on Wikipedia, and it loaded quite fast. I'm not sure about streaming—the issues there aren't on us, unfortunately, it's the university network. But with blocking enabled, the pages shouldn't be visible at all.

**[Technical Writer]** (5:45)\
Today our goal for the meeting is to conduct User Acceptance Testing. You will have a few tasks, and we'll observe how you solve them. Right now, everything is set up specifically with the board, so we'll test everything.

**[Core Systems Engineer]** (5:55)\
I only measured the speed directly through the port, I didn't try it through the board, but it shows pretty good results there.

**[Customer]** (6:05)\
So on Wikipedia everything works fast? If the measurements show 400 megabits, that sounds about right. The only question is how to explain this situation—apparently, something is being actively blocked on Wikipedia?

**[Core Systems Engineer]** (6:15)\
Possibly.

**[Customer]** (6:20)\
This picture weighs, I think, about 10 megabits, so it should download in roughly half a second. What if we try streaming? Where do we have real-time traffic going to the computer? Twitch should work?

**[Core Systems Engineer]** (6:40)\
You can try the first UAT scenario with blocking then. The blocking works simply via the button; there's an LED tied to it so you can see whether traffic is currently allowed or denied. The UAT consists of you pressing the Key1 button, at which point the LED1 located on it should turn off. If it turns off, it means there's no internet on the laptop because this IP is blocked. This needs to be verified.

**[Customer]** (6:50)\
Accordingly, we press the button. So like this we have no internet at all, and like this it activates, right?

**[Core Systems Engineer]** (7:00)\
Contact bounce hasn't been fixed yet.

**[Customer]** (7:10)\
Well, the pictures are loading even faster now. And it's quite responsive, right? Will a live stream actually open somewhere right now? On which sites do live streams work here?

**[Project Manager]** (10:53)\
Well, Twitch should work.

**[Customer]** (11:31)\
And where do we have real-time traffic? Maybe music? It buffers in chunks. Well, video. So, it works like this, right? Something is trying to load there, and it will try infinitely like this. Moreover, as far as I understand, judging by the LEDs, it sees that requests are coming in, but it doesn't send them back to the network?

**[Core Systems Engineer]** (11:45)\
Actually, it does send them, it just happens up to the moment it reaches the IP. So it's just a not very elegant implementation for now.

**[Customer]** (11:55)\
In the sense that it only sends the beginning of the packet? So the router sees a bunch of broken packets. With video, it's a bit harder to see because video has a 10-15-30 second buffer. Okay. If possible, for the next demo, we could prepare just four tabs: some Speedtest, pictures on Wikipedia, just text on some site, or something where traffic is actively flowing. By the way, online radio or online TV has active traffic. We need to find some neutral channel that just plays music.

**[Technical Writer]** (15:19)\
Okay, we'll prepare that. So, maybe we can briefly tell you what we did this week and move on to the UAT.

**[Project Manager]** (15:25)\
A full backend redesign was done, meaning the entire architecture was completely rewritten. I was inspired by your words from the last interview, because there are three logical elements: WebSocket, REST, and receiving UDP packets. I completely separated them into three containers. These containers communicate via Redis; more precisely, all data is buffered before being written to the DB. Also, something important that was added: a new table for users—you can now add users, they are no longer hardcoded as stubs. An Nginx server was also added, which wraps our entire project. The prod version includes an infrastructure layer for secure connections, which redirects requests to the internal Docker networks. Also, for optimization, another table was added that automatically aggregates windows for the last second once a second. This isn't done on all raw data for historical packets, but on a table that already contains aggregated per-second windows. This happens automatically at the Postgres level.

**[Customer]** (16:10)\
Okay, great.

**[Frontend Lead]** (16:15)\
Regarding the user interface: we worked a bit on the main dashboard. As you can see, the design now matches what we showed you last time. You can now toggle the display to numbers if you prefer that. Regarding the tests we prepared for you to execute: when refreshing the page, automatic authorization token refresh isn't implemented yet, so you need to enter your login and password here. This is the admin account, and you can see the main dashboard. First, you need to select a channel using the selector. Right now, it shows the current channel activity. When opened, you can see what's happening here.

The first test is viewing statistics on current channel activity, meaning how many packets are transmitted in both directions. To do this, you need to look at the numbers or the graph to see some asymmetry. As Irina mentioned, on average, about three packets per second are passing through our network right now. These are real data collected by this computer, which is acting as the Communication Node.

The next use case is viewing historical data. On the right, there is a graph showing how the packet transmission rate has changed. It can be scaled and zoomed in. Right now, everything is quite stable; there are minor drops, but overall it's around three packets per second. It doesn't react very actively to changes, unfortunately.

**[Customer]** (17:30)\
It's as if three packets per second is some hardcoded constant.

**[Frontend Lead]** (17:35)\
But actually, it's not.

**[Core Systems Engineer]** (17:45)\
There really was about three packets per second, and when I measured it without the site, it was also three packets per second. You can try enabling the block, and you'll see the graph drop.

**[Frontend Lead]** (17:55)\
It just probably needs some time. The bottom tables aggregate data for the last five minutes, and the top ones should display real-time data. [Project Manager], am I right? Should these top graphs show real-time speed, or is there also some minor aggregation there?

**[Project Manager]** (18:10)\
And these ones are latency per second.

**[Frontend Lead]** (18:15)\
Latency per second. Okay.

**[Customer]** (18:30)\
New packets have stopped coming through, I assume? Meaning it sees that no new data is arriving?

**[Frontend Lead]** (18:40)\
No, if they stopped arriving, the line would drop down on the graph. It updates every second. Ah, well, actually, that's the problem: part of the packet still arrives, and it displays that. If we could somehow increase the packet count, it should be visible on the graph itself.

**[Project Manager]** (19:00)\
Well, the traffic is going monotonously on the server, I'm looking at the blocks...

**[Customer]** (19:10)\
Simply, if I understand correctly, we can compare these two network activity graphs, right? Ideally, let's run it. If we click 'measure' here, the history should be similar, right?

**[Frontend Lead]** (19:30)\
Well, it's displaying something here, of course. We'll work on making the statistics more accurate. The third use case is the tables at the bottom. As you can see, they are needed for analyzing current traffic. Here you can observe the first value in the LAN host—this is exactly the IP address of this computer. It's dynamically taken from this laptop. I think if we disconnect the Ethernet, it should reflect that.

**[Core Systems Engineer]** (21:00)\
Yes, if we connect to [Project Manager]'s laptop, it should show up.

**[Frontend Lead]** (21:10)\
Okay, we disconnected the Ethernet from the board, so it shouldn't transmit any traffic at all.

**[Customer]** (21:30)\
I think one of the system components just got tired from working too long. Alright, let's just restart it, and it will most likely work. But I think we can deal with this a bit later. So, the graph is there, it draws everything, and the host statistics even look somewhat true?

**[Frontend Lead]** (22:00)\
Yes. We haven't filtered out broadcast addresses and so on completely, but in general, it shows the current statistics sent by the CnSS. This was another use case. Next, if you click on the hosts page, you can see a large table here showing all the current hosts our CN has found. It displays them and shows how many packets are transmitted. We also added some basic filtering and sorting. For example, if you type "location: LAN" in this search field, it will display only the IP addresses that are inside the network. We haven't finished this filtering yet, we plan to improve it, but it shows this basic version for now.

**[Customer]** (22:30)\
Well, I assume you already feel how hard it is to work with text fields for filtering?

**[Frontend Lead]** (22:40)\
Yes, yes.

**[Customer]** (22:50)\
This is exactly what I was talking about last time.

**[Frontend Lead]** (23:00)\
I didn't add sidebars, but they can be added literally by changing one line of code. If you want, we can enable them.

**[Customer]** (23:10)\
Well, that's logical because you have sidebars everywhere except the first column.

**[Frontend Lead]** (23:20)\
Unfortunately, a screen for a more detailed view of each host's statistics hasn't been implemented yet.

**[Customer]** (23:30)\
Just one small comment. Here, it's worth adding one more scale division, a very small one, like a minute or five minutes. That is, a minimum duration window so the graph is fully zoomed in, and you can look at it almost in real-time and change things.

**[Technical Writer]** (23:40)\
Alright then. We'll fix the responsiveness next sprint. What else do we have left?

**[Frontend Lead]** (23:45)\
We still need to make detailed statistics for each host on the hosts page. Then, following your recommendation, we can make a host map as an option, and also take into account the current feedback. Overall, what do you say about the usability? Besides filtering, are there any other comments on the current version?

**[Customer]** (23:55)\
Well, regarding real-time, those are bugs. Otherwise, everything seems fine. We need to test it in practice to give more tangible feedback. But at a quick glance, everything seems great.

**[Frontend Lead]** (23:58)\
Okay. Thank you.
