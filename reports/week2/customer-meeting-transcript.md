# Customer Meeting Transcript

> The meeting audio recording was transcribed using TurboScribe and translated from Russian to English using Qwen3.7-Plus, as reported in [LLM Report](llm-report.md). The final transcript was manually checked by @arinamnova.

**Date**: June 12, 2026

## Participants

* **Project Manager**: @jinseisieko
* **Technical Writer**: @arinamnova
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln
* Customer

## Transcript

**[Technical Writer]**\
Will the transcripts be published in a public repository, or just shared with the course team?

**[Customer]**\
Whatever you prefer.

**[Technical Writer]**\
Great. And just to confirm once again, you agree to the MIT license.

**[Customer]**\
Yes.

**[Technical Writer]**\
Excellent.

**[Project Manager]**\
The goal of today's interview is to validate the user stories.

We have certain users for our system, and we want to understand what their user experience will be. We've put together a list of these stories, and today's goal is to validate them—or ask you questions, answer yours, and discuss these user stories in more detail.

Here's the list of user stories; please take a look. Each one has a unique ID on the left. You can refer to them by these IDs—we'll understand if you just mention the ID number.

**[Technical Writer]**\
We can review the wording in general. If you agree that the required functionality for the product is covered here, we can tweak things and look at the priorities.

**[Project Manager]**\
Yes. As for priorities, we're using the MoSCoW method. "Must" means it absolutely has to be in the project.

"Should" means it's required but could be dropped if, say, we run out of time or for other reasons. It's still an important part of the project. And "Could" is nice to have, but not mandatory.

**[Customer]**\
Okay. Yes, got it.

**[Project Manager]**\
Some of them are pretty basic, while others are more advanced.

**[Technical Writer]**\
Feel free to make any notes, add constraints, or include additional conditions for the user stories, since their current wording is fairly simple, [inaudible].

**[Customer]**\
So, these stories here are for the absolute minimum version, right?

**[Project Manager]**\
Yes, the "musts" represent the bare minimum version we have right now.

**[Customer]**\
So "should" is a slightly more complete version, and "could" is…

**[Project Manager]**\
The fully expanded one.

**[Customer]**\
Right, yeah. The only thing is, regarding filtering, there's a question…

**[Project Manager]**\
About the sixth or the tenth?

**[Customer]**\
Let's see. The sixth one. I mean, if we're looking at the second, more advanced analyzer—which is the second version of the functionality—that's story number six, which talks about IP addresses.

I think we should add ports to it as well, so globally it would be a socket pair. Basically, the user selects a specific connection, or rather, a specific IP address, and then uses the port to select a specific protocol. We could either make this a separate user story or just expand the sixth one.

**[Ira]**\
Does it stay as a "should"?

**[Customer]**\
Yeah, up to you. "Should" is probably better, yeah.

**[Project Manager]**\
Regarding the end user, I should clarify that in this context, "end user" means someone on the same local network where our system is deployed.

**[Customer]**\
Right.

And about the tenth one: filtering traffic by protocol type. By "filtering," do you mean filtering in the UI, filtering for display purposes, or actually modifying the traffic as it passes through?

**[Project Manager]**\
This is about filtering on the dashboard. For analysis and viewing purposes.

**[Customer]**\
Okay, I get it. I just mean that the phrase "filter traffic" is ambiguous, so we should clarify that…

**[Project Manager]**\
Display filtering.

**[Customer]**\
Yes, that it's a display filter for the actual traffic—meaning a specific connection.

Now, what about traffic modification, like enabling channel filtering or tunneling? Did you leave out a story for that?

**[Project Manager]**\
Yeah, they aren't in here yet because we focused strictly on the project MVP.

**[Customer]**\
Okay.

**[Technical Writer]**\
Wait, shouldn't user stories cover all functionality? "Could" isn't mandatory, right. Could we just add them as "could" user stories?

**[Project Manager]**\
Well, yeah, we definitely should add them.

**[Customer]**\
They're definitely "coulds." The question is just whether to include them now or in, like, three weeks.

**[Project Manager]**\
Will they be ready for the very last version of our project?

**[Customer]**\
That depends on what's feasible.

**[Technical Writer]**\
Let's write them down then. That's the whole point of user stories.

**[Egorl]**\
Alright, we'll add them then—the ones about the third model specifically with tunneling and filtering.

**[Customer]**\
Well, those are actually two different "coulds"—one where it can drop part of the traffic, and another where it can allow part of the traffic through tunneling. We'll need to look at priorities later on. Or just decide based on what we want to implement or not. Maybe add something else.

Alright, otherwise everything looks good. Oh, wait, there's one thing I found... ah, in the fifth story—"network user." "End user"—the word "end" is redundant there.

Yeah, otherwise looks good.

**[Project Manager]**\
Are there any other stories we might have missed?

**[Customer]**\
Well, just those two "coulds" about either blocking or allowing traffic.

**[Project Manager]**\
As for prioritization, any questions or additions? Anything that should be in "Must," or anything we should bump up to "Should" or downgrade?

**[Customer]**\
The class prioritization looks about right. You can prioritize the actual implementation later on. You guys will figure that out.

**[Project Manager]**\
Alright, well, if there are no more questions about the user stories, let's move on to—

**[Technical Writer]**\
The first version. We wanted to confirm that the first MVP release will consist exclusively of all the "Must" requirements.

**[Customer]**\
First version. The first minimum viable version, right? What does that entail? It includes the MUI and the server. Automatic updates.

Look, let me share my thoughts, and then you can see how relevant they are to you.

First on the list is the automatic update for the Management User Interface. You've marked it as "Must." I can agree with that, but honestly, it could be a "Should." It's a nice feature, but for the first version, users can just hit F5 to refresh—it won't kill them.

Next, access from anywhere via the internet. That's true—story 14, the second point. Yes, that's definitely a "Must." The only thing is...

**[Project Manager]**\
Yeah, there are some system limitations—we're allocated a server on the Innopolis local network.

**[Customer]**\
We could rephrase this. It's the right point—that interface access should be available from anywhere—but we need to clarify what "anywhere" means. Like, anywhere within the same network. If your server is hosted on the internet, then it's the internet. If it's a local university server, we should rephrase it to... Well, if we're being strict and nitpicking the wording, we could change "access via the internet" to "access via a global network."

Okay, yeah. Next [inaudible]. In the third point of story 9, there are two punctuation marks at the end. Is it like that everywhere?

**[Project Manager]**\
Yeah, it's like that everywhere. It's a formatting glitch.

**[Customer]**\
Right, the third point. "Worked without a noticeable drop in my network speed..." Here's another question: what exactly does "without a noticeable drop in network speed" mean?

**[Project Manager]**\
Well, assuming we're measuring it from the user's perspective.

**[Customer]**\
No, I mean this statement implies some numerical metric.

Like, the connection degrades by 10% or 20%. We could either leave it as is, or use the good second point there—that internet access shouldn't be interrupted. Meaning the traffic analyzer shouldn't affect internet access or access to external resources. So it's all correct. We can tweak the wording a bit, or just leave it.

Okay, "end user, deployment was completely transparent to my routing, internet access wasn't dropping."

Here too, what do you mean by "deployment"? Because deployment basically means inserting something into the channel, and that will always cause interruptions.

**[Project Manager]**\
For this story, we mean that all four of our services are, roughly speaking, loosely coupled.

They aren't directly dependent on each other. Basically, they can keep functioning even if one goes down, though maybe not perfectly. It's specifically about us not having a monolithic system.

**[Customer]**\
Okay. So if some part crashes—anything other than the router or the traffic processor—it's fine.

**[Project Manager]**\
We can swap out individual components if something goes down.

**[Customer]**\
Alright, yeah, good.

Okay, "integrate [inaudible] incrementally." Together, yeah.

Also, "see how many packets and bytes pass through the channel." Packet count is definitely doable since packets are easy to count. Byte count—we can leave it, or we could move byte counting to "Should" as a separate item.

Because the question is what exactly to count. All traffic? Just the payload? Or the actual data inside the protocols? It's not entirely trivial. But packet counting is 100% essential.

**[Project Manager]**\
Based on this story, Irina has a question about accuracy—specifically about timestamps on communication. Is that for the future?

**[Core Systems Engineer]**\
I think that's for later.

**[Customer]**\
Okay, the last one: "I want to see a channel activity indicator." Yeah, good.

So, in short, all the points are accurate. The things I mentioned are just minor tweaks. Overall, in the second story—I think it's the seventh point—byte counting ties in nicely with traffic statistics.

Where was that? Average, minimum, and maximum throughput values. If I understand correctly, we first collect byte count data, and then calculate those three stats for minimum, average, and maximum loads.

So maybe we can roll byte counting into that minimum/average/maximum section. Or just put it right next to it. Anyway, the "Musts" are great. For "Should" and "Could," we can figure that out later, after the MVP is done. Except for byte counting, which we need to think about. If it's simple, we can keep it. Otherwise...

We'll have to see. I can't say for sure. It might be easier to just count packets and multiply by the maximum packet size to get an approximate byte count.

**[Project Manager]**\
Yes, of course. Alright. Let's move on to the next part of the interview since we've wrapped up the user stories. We have a quick diagram we'd like to show you. [Core Systems Engineer], could you please share the diagram?

**[Core Systems Engineer]**\
I'll cover the technical side. Regarding the traffic processor, control node, and CnSS server—this is the rough architecture I'm proposing for the MVP.

There's a proposal to integrate the FPGA right from the start, since we plan to add some payload processing to it later. But initially, we'd use the FPGA for the core traffic processor function—just forwarding packets from port to port.

**[Customer]**\
We have one host on the internal network, right?

**[Core Systems Engineer]**\
Yes.

**[Customer]**\
And one global host on the internet. They're connected.

**[Core Systems Engineer]**\
Yes, connected via the FPGA. Through the traffic processor.

**[Customer]**\
Through the traffic processor, which is the board itself.

**[Core Systems Engineer]**\
I'm suggesting we use the board plus a laptop for now, so packets are processed on the laptop. This essentially creates zero delay for traffic passing through the wire.

**[Customer]**\
That seems like an overcomplication, but alright.

**[Core Systems Engineer]**\
It's necessary for future development.

**[Customer]**\
Fair enough, okay. So the traffic processor itself consists of two devices?

**[Core Systems Engineer]**\
Yes. Basically, the laptop and the traffic processor board.

**[Customer]**\
So the board just passes bytes around.

**[Project Manager]**\
It splits them into two channels. One goes further into the network, and the other gets processed.

**[Customer]**\
Okay, fair enough.

**[Core Systems Engineer]**\
That way, we avoid creating any delay.

**[Customer]**\
That's an interesting approach, actually. Okay. So since you're using a laptop, half of it could act as the traffic processor, and the other half as the control server. Functionally speaking, that works.

**[Core Systems Engineer]**\
Then the testbed from the traffic processor to the CnSS would look roughly like this. Which brings up a question: how critical is the accuracy of timestamps on each packet? Because in this setup, I'm proposing we collect data on the laptop inside the traffic processor—this blue box.

We'd collect the data on this laptop, calculate all the metrics we just agreed on, and send them to the Control Node. Then, on the CN, we'd timestamp batches of packets—or rather, the metrics for each packet. So they'd be timestamped at intervals of, say, half a second or 1.5 seconds. How critical is this? How bad would it be if there are discrepancies in the millisecond range?

**[Project Manager]**\
The timestamp.

**[Core Systems Engineer]**\
Yes.

**[Customer]**\
Well, for the minimal version with just packet counting, it doesn't matter at all. For the future, I can't say—we'll have to test it. We can leave it as is for now and see how critical it becomes.

**[Project Manager]**\
We'll apply it to the actual delay. Because right now, we can't predict what the exact delay will be.

**[Customer]**\
Yeah, it's an open question. It's hard to answer theoretically, so the only way is to try your approach and see.

If it works within acceptable margins, great. If it causes issues or introduces too much inaccuracy, we'll have to figure something out. Right now, I don't think it's a problem. Honestly, I'm not even sure why we need timestamps at this point.

**[Core Systems Engineer]**\
We'll need them for the database later on.

**[Customer]**\
If this were an industrial project, precise timestamps would definitely be necessary. But for an academic project, we can just timestamp at the database write level. Plus or minus 10 seconds is fine. The main thing is that the timestamping delay is consistent. We don't want it to fluctuate—like half a second delay for some data and 10 seconds for others. That would be bad.

If the database applies the timestamps when inserting records, and it's always a 10-second delay, that's not a problem. If you think timestamping at the database level is too far down the line and we can optimize it a bit, that's fine too.

We can try it, I don't mind.

**[Core Systems Engineer]**\
Technically, it's a direct wire connection here, the physical medium, so nothing should cause a delay there. That's what motivated the decision to use the write timestamp.

**[Project Manager]**\
So if the traffic processor and communication node are logically separate components but run on the same laptop, there will be virtually no delay.

**[Customer]**\
Again, what does "virtually no delay" mean, and what are the actual latency requirements? In my current understanding, "virtually no delay" also applies to the mechanism where the database server sets the timestamps.

There might be a half-second delay, but that's still "virtually no delay." It depends on the use case. If this were for industrial applications with strict real-time requirements, even 20 or 200 milliseconds of latency between VMs on the same laptop could be too much. But we don't foresee such scenarios. So in my mind, running it on the database server is "virtually no delay," running it on two separate laptops is "virtually no delay," and even running it as two adjacent programs is fast enough.

**[Core Systems Engineer]**\
Got it.

**[Project Manager]**\
Alright, I think that covers it. Any other questions before we move on? Oh right, the user interface.

**[Frontend Lead]**\
I put together a quick mockup that aligns with the basic MVP. As I see it, the basic MVP has three components. First, channel activity status, which shows whether data is currently flowing.

Then, a graph showing the ratio of inbound and outbound channels from the traffic processor. And finally, time-based statistics. For the first version, since we won't have a database yet, we can implement the time statistics on the frontend. As the server receives data from the CnSS backend, it renders it, and the statistics are stored in the frontend memory until the page is refreshed.

**[Project Manager]**\
Could we store, say, the last 30 minutes of data dynamically on the server instead?

**[Customer]**\
No, no need. Better to keep it on the frontend. If you don't have a database, don't overcomplicate things by storing data dynamically somewhere else. Just collect it in real-time on the frontend, as proposed. What you're showing looks great, but it doesn't look like version one—it looks more like a later release.

I don't know if I can find it... The very first version with counter functionality is just two numbers. You could just have two numbers and maybe two indicator lights on top for on/off.

**[Frontend Lead]**\
That's true, but we have a couple of weeks for development, so I think we can build something a bit more substantial.

**[Customer]**\
I get that, but my point is that the very first version is just two numbers. Display them in real-time—or near real-time if you have to hit F5—showing the two numbers sent from the boards, like packets per second.

Then, yeah, you can iterate to what you're showing later. The only thing is, the current numbers and the stats—the TxRxRate—I'd make them a bit larger or higher contrast. Because right now, the numbers 100 and 150, which are basically the two main metrics, are white on white. Yeah, that looks great.

**[Project Manager]**\
Alright, I think that's everything. We'll wrap up the interview here. Thank you all very much.

> The team continued the discussion with the customer after the recording ended. This discussion informed additional changes made to [User Stories](user-stories.md).
