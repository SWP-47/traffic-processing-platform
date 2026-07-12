# Customer Review Transcript

> The meeting audio recording was transcribed using TurboScribe and translated from Russian to English using Qwen3.7-Plus, as reported in [LLM Report](llm-report.md). The final transcript was manually checked by @arinamnova.

**Date**: June 26, 2026

## Participants

* **Project Manager**: @jinseisieko
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln
* **Technical Writer**: @arinamnova
* Customer

## Transcript

**[Technical Writer]** (0:00)\
We still need permission to later publish the transcript in the repository. And we will send the recording to the course team.
The goal of the meeting is to discuss our progress on the first version (MVP v1) that we launched last week, and what feedback we have implemented. Then discuss the current sprint, its goal, and what has already been done. And finally, discuss potential Quality Requirements.

**[Customer]** (0:34)\
Alright. Then let's start with last week, with the first version.

**[Project Manager]** (0:42)\
What was included in the first version? Authorization was included, but for now, users are hardcoded in the configuration. There are two roles: admin and viewer. The admin has access to all channels available on the server. The viewer's access is configured via scope.
Let's say we log in as admin. I have a script prepared to simulate test packets. Right now, three channels are registered on the server. I run the script, and UDP packets are sent. In v1, the server determines the number of packets and packets per second for a specific aggregation time window based on incoming data and sends this via WebSocket. If you run the generation several times in a row, you'll see that the data updates in real-time.

**[Customer]** (2:26)\
Can't it vary the number of sent packets in a random range? So it generates the load with a constant frequency? Does this script generate real packets?

**[Project Manager]** (2:45)\
Yes, it generates real packets to the server. For MVP v1, there's no load randomization yet, but now [Frontend Lead] will show a script with randomized values.

**[Frontend Lead]** (4:43)\
This is the randomized version of the algorithm. If you open the site, it will display random values. Here I interrupted the generation — after a while, the system will notice that the channel is inactive and turn off the indicator.

**[Customer]** (5:03)\
Great. We have no traffic, we can continue. And here you showed the viewer function.

**[Project Manager]** (5:12)\
Yes, I'll log in as viewer. They have access only to certain channels, for example, channel-berlin-01 and channel-peru-01.

**[Customer]** (5:49)\
Clarifying a question: how are the channels themselves generated? What is meant by a channel?

**[Project Manager]** (5:59)\
When the Communication Node (CN) sends a packet, it marks it with a `channel_id`. Each pair of Traffic Processor and CN has its own ID. The server listens to all incoming ones and registers new `channel_id`s. In version v1, they are stored in memory (in-memory).

**[Customer]** (6:29)\
So, if four channels are shown in the web interface, does that mean four TP and CN pairs are running? Can they dynamically appear and disappear?

**[Project Manager]** (7:00)\
Yes. The logic of MVP v1 is this: if there is no activity on the channel for five seconds, it is marked as inactive (no traffic). And within 24 hours, it is removed from the list so as not to clutter the memory.

**[Customer]** (7:31)\
Alright, great. You have two groups of users: administrators see all channels, and regular users see only those written in their scope, and for now, this is hardcoded in the configuration. Is this where the functionality of version 1 ends?
I think I mentioned that you didn't stretch the counters to full screen.

**[Frontend Lead]** (13:17)\
Yes, we'll explain this. Exactly at the last meeting, you advised using OpenAPI libraries for automatic type generation. We implemented this in the frontend, now everything happens automatically. You also mentioned stretching the chart. Regarding the chart, we worked a bit on the dashboard redesign this week. We decided not to touch the old version for now, and instead immediately demonstrate the new version of the design to you.

**[Frontend Lead]** (15:20)\
Regarding the redesign. The previous version of the design looked something like this, but we have already prototyped the second variant. We took your feedback into account: removed the protocols from the dashboard, as you advised, and discussed UI/UX improvements with the team.
We reduced the amount of visual noise and colors. The status indicator, which used to attract a lot of attention, we made smaller and moved it to the channel selection menu. It has states: inactive (not transmitting data), active, and error. Also, a separate icon marks if there are many losses during transmission between CN and CnSS.
Next, the RX/TX diagram. It changed a bit: we moved the numbers lower to place accents. The main goal of this column chart is to see the asymmetry in the network (if more packets are transmitted in one direction than the other).
The line chart shows changes in RX/TX over time. We are starting to collect historical data. Blue lines are received packets, pink ones are sent. You can hover to see detailed statistics.
We also added two tables with a general view of the hosts in our network. The first five options are shown here for a quick view. In the future, we plan to add a separate page for detailed host statistics.
What do you think? Will all these functions be useful for network analysis?

**[Customer]** (17:16)\
Overall, everything is good. I have a few comments. Do I understand correctly that on the left we observe the load at the current moment, and on the right — the load in dynamics?
Tell me, please, why is Active indicated in blue, and not green?

**[Frontend Lead]** (17:23)\
It's just a design color choice, we settled on this blue-purple gradient. But if you want, we can change it to green, since it is usually associated with being online.

**[Customer]** (17:35)\
Alright, okay, we can leave it as an accent color.
Now a question about the left element, the column chart. How is the maximum of these columns calculated?

**[Frontend Lead]** (22:37)\
The maximum is the maximum value from these two graphs (RX and TX). It visually shows how these two indicators differ from each other.

**[Customer]** (22:48)\
So the maximum is common for both directions? And it is taken from the current load of the channel? If both our channels are empty, the maximum will be zero, and the columns will be empty? And if we run a ping that sends one packet per second and gets a pong, the load will be one packet, and will this be considered the maximum load?

**[Frontend Lead]** (24:06)\
This is the first implementation option. I also thought about making a system displaying historical data: if a peak occurs in the network, the maximum will be preserved for some time until the load drops.

**[Customer]** (24:43)\
Good thought. But "some time" is a variable parameter. This leads to the idea that a switch can be introduced at the top right of this element: maximum for 10 seconds, for 30, for a minute.
But there is another observation here. If you have a line chart displayed on the right, the maximum and position in time will already be visible on it. And is it necessary at all to display the maximum on the left chart, or make a dynamic display?
I'm not sure that the visual representation of the rate relative to the maximum is necessary at all. Initially, my comment was to add a switch: one position shows the current widget, and the second — just two numbers (RX and TX). Because the visual representation is on the right, with some delay, but it will be there too.
Look, for example, at the system monitor in KDE or Windows. On one side, just numbers are displayed, and then the state is displayed with a graph. Two numbers are a bit easier to read and understand what the load is. Right now the numbers are small, and it is implied that I should understand the load by the visual size of the columns, and this is difficult. Ideally, the scale should be logarithmic, but this is complicated. Therefore, it is better to make a switch: leave the visualization on one side, and just two numbers on the other.

**[Frontend Lead]** (31:55)\
Okay, we will change this in the next version.

**[Technical Writer]** (32:01)\
Will we have time to change this in this sprint, or leave it as it is?

**[Customer]** (32:05)\
This is design, so it's nice to have. If you don't have time in this sprint — it's not a big deal.
The second global comment regarding the charts: is it possible to make the charts themselves more "rigid"? Right now the lines are very smooth, smoothing is clearly applied. You are making a tool for system administrators, it can look beautiful, but it shouldn't.

**[Project Manager]** (33:12)\
The chart is built on buckets. Smoothing consists in how many points we draw.

**[Customer]** (33:12)\
I understand, but the comment is about the visual style: smoothing is clearly applied here, and it is difficult to understand what it is about. You shouldn't intentionally smooth the chart too much to make it beautiful. If you want a little bit of beauty, add smooth smoothing only for the corners between buckets, so they are not at 90 degrees, but semicircles.

**[Frontend Lead]** (35:59)\
Yes, of course, we'll take it into account.

**[Customer]** (35:58)\
And the third comment regarding the tables below. We should somehow articulate that this is the top 5 results. The way to articulate it is to add a note or a "View all" button at the bottom, which redirects to an adjacent tab with the full list. You don't need to expand the table completely on the current page.
Everything else is great.

**[Project Manager]** (36:03)\
[Frontend Lead], you didn't mention it, but in this table, it will be possible to choose the top 5 by some parameter: by sent packets, by received packets, or by those who were active last.

**[Customer]** (36:03)\
Yes, great. Now let's move on to the current development. You are not working on the second screen (detailed statistics) yet?

**[Frontend Lead]** (36:34)\
Yes, for now we wanted to approve this screen.

**[Project Manager]** (36:36)\
In this sprint, the main goal is to integrate the database into the backend to show historical data, and expand the functionality to provide information about IPs and ports.
I'll launch the current version now. We are using TimescaleDB. pgAdmin is also configured, it can be run in a container next to it. The current version of the backend is backward compatible with the old frontend.
You can see that there is an error on the frontend that the server was turned off, but the channels are saved because they are already in the database.
In addition to the fact that in the current version the structure of UDP packets has changed: now it assumes not just a counter, but a specific list of packets passing per aggregation window. The server processes this and writes all packets to the database.
I did a stress test of the server: emulated packets, reached 6 thousand packets per second in one direction, the server handles this and successfully writes.

**[Customer]** (40:40)\
6 thousand packets per second in one direction? And if we calculate it in megabits? This is roughly multiplying by 1500 bytes (MTU).

**[Project Manager]** (41:00)\
Will it be about 10 megabits? 18 million bytes?

**[Customer]** (41:10)\
No, 6000 * 1500 bytes = 9 million bytes. This is about 72 megabits. If 12 thousand packets in both directions, then about 144 megabits. Let's approximate to 150 megabits. So the server digests this?

**[Project Manager]** (41:30)\
Yes, the server part withstands it, everything is written well to the table.

**[Customer]** (43:00)\
So we can conclude that the server part will withstand working with a 100-megabit channel?

**[Project Manager]** (43:00)\
Yes. If you look in pgAdmin, you can see the latest changes. All the functionality is rewritten to work with the database, and not with local memory, as it was in MVP v1. We no longer control the last activity by a timer in memory, but take the last record about the channel from the DB: if it is older than 50 seconds, we mark the channel as inactive.

**[Customer]** (43:00)\
Great. Are TimescaleDB and everything else deployed on the Innopolis virtual machine? Have you looked at how much traffic is generated in the database? How "thick" does the database get after testing?

**[Project Manager]** (43:30)\
At the peak, there were 186 thousand rows, and the memory on the virtual machine did not increase much.

**[Customer]** (43:45)\
There you need to look at the volume statistics in Docker Compose. Just look at this ratio to have an intuition: for example, 100 thousand rows is how many megabytes. This is for your general development.
So the backend server works, writes everything. Is there already an endpoint for the chart that collects statistics from the DB by buckets (Timescale does this), and outputs an array for the chart?

**[Project Manager]** (45:30)\
Yes. Table updates are also connected: the frontend subscribes via WebSocket, and it is sent a packet responsible for updating the actual information (top 5 hosts).

**[Customer]** (46:30)\
Good question: how to update the chart in real time? What to push through WebSocket — the whole new chart or the delta?

**[Frontend Lead]** (47:42)\
We push the delta. We request the full chart via REST API only if necessary.

**[Project Manager]** (48:01)\
For the full chart, we have a REST request that requires a token. And WebSocket is needed only for information that is displayed in real time. The frontend requests a subscription, the server remembers this and sends the necessary data to all subscribers.

**[Customer]** (48:42)\
Okay, great. Solid. Is your backend in Python?

**[Project Manager]** (48:42)\
Yes, completely in Python. There is a lot of legacy code and in-memory storage left there now. Part of the functionality has moved to the DB. asyncpg is used for asynchronous requests to Postgres.

**[Customer]** (49:20)\
Great that it works. This is all mechanics, the main thing is that the problem of streaming and data processing is solved.

**[Technical Writer]** (49:58)\
Let's move on to Quality Requirements. Let's briefly discuss how we will determine specific values. We need to choose three different requirements that can be checked automatically.

**[Project Manager]** (50:08)\
What Quality Requirements could be implemented in the current architecture? There is a list of possible metrics: speed check, security check. Which of them and where would it be integrated?

**[Customer]** (50:31)\
What do we want to understand as a result of this discussion? Do you want certainty from me on three non-functional metrics?

**[Technical Writer]** (51:12)\
Yes, we have the formulation Quality Requirements, and we will write automatic tests for them, which will check and measure whether the test passes. All the code must meet these qualities.

**[Customer]** (52:06)\
Ah, I see. Non-functional requirements must be accompanied by a metric that measures the fulfillment. For example, "so that it works" is a functional requirement. And "so that it works normally on channels of different speeds" is already closer to non-functional.
If we unfold this formulation, you have several options. Remember, we had a discussion that the monitored channel can be of different speeds: 1 Mbps, 10 Mbps, 100 Mbps, and 1 Gbps.
A non-functional requirement can state that the system must work stably when analyzing a channel at a speed of 1 Mbps (must have), it is highly desirable — 10 Mbps, it is excellent if it turns out to be 100 Mbps, and the highest class is 1 Gbps.

**[Project Manager]** (54:17)\
And will it be enough to simulate traffic for such a speed and check exactly this on the finished version of the server? After all, we need to automate the test.

**[Customer]** (54:22)\
I mean that the entire platform assembled must work at such speeds. Automating the test means writing a CI/CD pipeline that, for example, SSHs into laptops, flashes the board, and runs testing. But I'm not sure how much Quality Requirements should be integrated specifically into CI/CD, or maybe you didn't quite understand the task from the course team.

**[Technical Writer]** (55:33)\
The task says that Quality Requirements must be associated with automated testing.

**[Customer]** (55:39)\
If Quality Requirements imply automated testing, then this could be a test that UDP parsing goes normally, WebSocket parsing works, the frontend can parse data. But "normally" is how? Fast? What is the minimum and maximum speed limit?

**[Core Systems Engineer]** (56:14)\
This is rather a test of whether it works or not, and we need to measure how well it works.

**[Technical Writer]** (56:29)\
I think, perhaps, towards the end of the meeting, it is worth discussing this and determining what we can do. We can just confirm via Telegram that this meets the project requirements. I have a general list of Quality Requirements types: performance, security, etc.

**[Customer]** (58:59)\
The question is how to test all this automatically in CI. Honestly, you can come up with something yourselves. These are more requirements from the course team. If this thing doesn't strongly affect functionality, you can do whatever you want. The main thing is that the requirements are measurable and the tests eventually pass. Choose three that you like and that you can automate.

**[Project Manager]** (59:16)\
Alright, thank you very much.
