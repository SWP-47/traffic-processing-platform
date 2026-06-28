# Customer Review Transcript

> The meeting audio recording was transcribed using TurboScribe and translated from Russian to English using Qwen3.7-Plus, as reported in [LLM Report](llm-report.md). The final transcript was manually checked by @arinamnova.

**Date**: June 17, 2026

## Participants

* **Project Manager**: @jinseisieko
* **Frontend Lead**: @Minnezing
* **Core Systems Engineer**: @Rena-ln
* Customer

## Transcript

**[Project Manager]** (0:00)\
I'd like to ask a question right off the bat: will we be able to publish the transcript in the public repository with names redacted?

**[Customer]** (0:15)\
Yes, that's fine.

**[Project Manager]** (0:20)\
Today we'd like to discuss the development plans for MVP v1: specifically the backlog and what's already been implemented. We'll also go over potential risks and pitfalls with our current implementation, as well as our broader development roadmap.

First, let's go over our implementation plan. Specifically, we're aiming to close three user stories this week: the first, fourth, and second.

We'll have the channel activity indicator properly displayed. The basic stats will cover the number of packets flowing in and out of the channel. The overall architecture will consist of four distinct components communicating with each other.

That's the core scope. We need to clarify the exact plans for each component we're developing. Let's start with this one.

**[Frontend Lead]** (1:40)\
Sure. Right now, we have a brief summary of what we've prepared so far.

For the UI, we've built a mock dashboard page. It currently includes a channel activity indicator and a small bar chart.

Let me show you. *[demonstrates the deployed frontend prototype]* There's no real data hooked up just yet.

It's just a prototype to verify the component layout.

**[Project Manager]** (2:55)\
It's deployed to our server right now, but it's displaying mock data instead of real values.

**[Frontend Lead]** (3:10)\
So, my work ties into the first and second user stories: implementing data fetching from the control server for channel activity with real-time updates, and collecting data on inbound and outbound packets passing through the traffic processor. That covers my part.

**[Project Manager]** (3:50)\
I'll take it from here and talk about the server, which is the second part.

We already have a basic server up and running, capable of deploying [inaudible] for initial testing. We've also set up streamlined deployments for both dev and production environments, along with a full CI pipeline to check all components. That covers my DevOps tasks.

What's planned for the core server?

A status endpoint for all components. Basically, I receive data from the CN and can, for instance, notify the UI that it's active. Plus health checks for the traffic processor to see if it's up and running.

A WebSocket protocol between the UI and the CNSS for real-time telemetry streaming. It'll be a standard WebSocket connection authenticated via an encrypted token in the query parameters.

And a ping-pong mechanism for connection keep-alive checks. During the WebSocket session, ping-pong frames will be exchanged to automatically drop the connection if, say, the UI goes offline or the server hits a snag.

Those are the main features we'll be implementing. The server will also keep basic, real-time state information in memory. Specifically, it'll track the traffic processor's activity status—like whether it's receiving packets from the CN. It'll also buffer the latest packet frames from the CN in memory.

Communication between the CN and CNSS will run over UDP. The protocol uses a time window with a fixed start time and duration, containing traffic stats for that window: the count of inbound and outbound packets. That covers everything planned for the CNSS.

All endpoints will also be secured with a Bearer token, stored in the environment variables across all services. I think that covers the key points. The server itself is built on FastAPI. The token is strictly for the UI to authenticate with the CNSS; the CN doesn't need to know about it, as it's only used on the frontend.

**[Customer]** (8:55)\
I hope you're aware that if you put tokens in the frontend's environment variables, they become publicly exposed.

**[Frontend Lead]** (9:15)\
Yes, I'm aware. You can't store secrets in the UI's environment variables. It's tied to the VM setup. We know, and we'll keep that in mind as we proceed.

**[Customer]** (9:45)\
Just to emphasize that those secrets would be public. But for a practice project, it's fine to do it this way. Later on, you can just swap the hardcoded key for a dynamic variable.

**[Core Systems Engineer]** (10:15)\
Regarding the CN, it's almost fully complete. We have comprehensive API documentation in place, so the only remaining task for the CN is to align it with the agreed-upon JSON payload format. Basically, finalizing exactly how these JSON strings will be structured and what they'll include.

As for the traffic processor, we're actually ahead of schedule. It's already passing packets at the speed the FPGA can handle. The FPGA code is done, and the code for the standalone laptop is ready too. Right now, the laptop is extracting the data points listed here in the traffic processor column. Any feedback on that? You mentioned wanting more port-level details, if feasible for UDP and TCP.

**[Customer]** (11:05)\
That's for the advanced stats in version two.

**[Core Systems Engineer]** (11:15)\
Right. That'll be post-MVP. For now, the traffic processor just detects the packet flow, extracts the relevant data, and sends it all to the CN.

**[Customer]** (11:40)\
Great.

**[Core Systems Engineer]** (11:45)\
The only immediate plan is to consolidate the CN and TP onto a single physical device to eliminate the need for the separate laptop. To do this, we'll likely containerize the CN in Docker so the system can communicate with it internally. This reduces the hardware footprint and helps optimize the testbed setup.

**[Customer]** (12:30)\
Actually, you could probably containerize the entire thing in Docker. You could put the software side of the traffic processor in a container too and just map the physical Ethernet interfaces to it. I'm not a hundred percent sure, but I believe Docker supports that.

**[Core Systems Engineer]** (13:10)\
It definitely allows port mapping for the CN, since the CN receives external data and forwards it to the CNSS.

**[Customer]** (13:30)\
You could also containerize the traffic processor's software and mount the network interfaces into that same container. We'd need to double-check, but it should work. It would make deployment a bit easier: the FPGA part stays as-is, while the TP software and the CN become two separate Docker containers orchestrated by a single docker-compose file. If I remember correctly, that's a pretty neat solution.

**[Project Manager]** (14:25)\
Regarding any deviations between the planned scope and the current state.

**[Customer]** (14:40)\
I also wanted to ask: how are the components distributed among the team? Who's working on what?

**[Frontend Lead]** (14:55)\
I'm handling the UI, UX, and frontend.

**[Core Systems Engineer]** (15:05)\
I'm in charge of the CN, the TP, and the FPGA code overall. @arinamnova is handling our documentation.

**[Project Manager]** (15:25)\
@arinamnova is writing all the technical documentation for the university and compiling the reports.

**[Customer]** (15:40)\
And you're on the CNSS, then.

**[Project Manager]** (15:50)\
Yes.

**[Customer]** (15:55)\
What's the frontend built with?

**[Frontend Lead]** (16:05)\
React and TypeScript.

**[Customer]** (16:15)\
And the CNSS?

**[Project Manager]** (16:20)\
FastAPI.

**[Customer]** (16:25)\
FastAPI generates documentation automatically, have you looked into that? How are you generating the client for the frontend? From the generated OpenAPI spec?

**[Frontend Lead]** (16:50)\
We have the auto-generated docs in Swagger UI.

**[Customer]** (17:00)\
No need to show me that. I'm talking about the fact that your server architecture is a bit non-trivial. The CNSS has two sides, right? One internal side talking to the CN over raw UDP sockets.

**[Project Manager]** (17:35)\
Yes, it just listens on a specific port and ingests the data.

**[Customer]** (17:50)\
Right. And the second side is external, handling WebSockets and REST. For the REST part, FastAPI generates the OpenAPI spec out of the box, right?

**[Project Manager]** (18:20)\
That's a bit redundant for us, since the API was originally fully documented in OpenAPI format from the start.

**[Frontend Lead]** (18:40)\
Yeah, we already have the docs; we wrote them manually in OpenAPI format.

**[Customer]** (18:55)\
You wrote it manually?

**[Project Manager]** (19:00)\
Yes. The requirements specified it had to be written manually.

**[Customer]** (19:10)\
Fair enough. But are you aware that you can generate TypeScript bindings and a fetch wrapper directly from the OpenAPI spec to make API calls much easier? There are code generators for a multitude of languages, going both from code to OpenAPI and from OpenAPI to code. FastAPI actually has one built-in—it generates the OpenAPI spec from your Python code.

Then, as is often done in companies, you take that OpenAPI spec, run it through a generator, and create a TypeScript client. It lets you make POST, GET, and any other requests just by calling a function. If the spec or backend changes, it saves you the hassle of manually updating the TypeScript client—you just regenerate it. Fewer bugs, much simpler workflow. You might want to look into it; I think the libraries are called openapi-fetch and openapi-ts. It's a TypeScript library that does exactly this.

Ideally, it'd be best practice to do this for all your interfaces. Aside from OpenAPI, you have a spec for your JSON messages. The server has that external side with WebSockets pushing data to the frontend, right? Do you have a single source of truth defining what that communication looks like?

**[Project Manager]** (20:25)\
Yes, we have a description of the exact JSON payloads being sent and how the connection is established.

**[Customer]** (20:40)\
In what format? Is it just in the docs?

**[Project Manager]** (20:50)\
It's just documented in text, yes, for now.

**[Customer]** (21:00)\
About half the companies do it just like that. But you could do it a bit better, if you're interested. I don't know of a single silver bullet, but one option is JSON Schema. It's a spec that lets you define the structure of your messages. You can use it to generate clients, the Python server side, and the JS client side. I can't give a blanket recommendation, but it's definitely used in the industry. When you have hundreds of endpoints, managing changes and updating clients via schemas is much easier.

**[Frontend Lead]** (22:15)\
Thanks a lot. We'll definitely look into it.

**[Core Systems Engineer]** (22:25)\
Was that the [inaudible] you wrote, if I'm not mistaken?

**[Customer]** (22:35)\
Well, there was something along those lines. It's just a general best practice: if you have three or four components that need to talk to each other, they need a defined protocol or message interface. At a basic level, you lock that interface down in the documentation. For more complex setups, you can enforce it in code—using either JSON Schema or Protobuf.

Potentially, if you're up for it, you could try swapping the connection between the CN and CNSS to gRPC just for fun. Protobuf is the serialization format, and gRPC runs on top of it. It's a bit more robust than raw UDP.

**[Project Manager]** (23:40)\
I'm not sure how feasible that would be for MVP v1.

**[Customer]** (23:55)\
No, definitely not for MVP v1.

**[Project Manager]** (24:00)\
We'll look into it for future development. If everything for v1 is already written, there's absolutely no need to change it now.

**[Customer]** (24:25)\
Just debug what you have and lock it in. Everything I'm saying about formal specs and interface definitions is just something to research or look into down the line. Google's Protobuf solves the problem of typed messaging over UDP. It's worth checking out, because while it might be overkill for simple use cases, it's definitely worth evaluating for future tasks.

**[Project Manager]** (25:20)\
Any other feedback on the current MVP v1 development? Or are we good at this stage?

**[Customer]** (25:35)\
The only thing I remembered regarding the frontend: v1 will look roughly like this, right?

**[Frontend Lead]** (25:55)\
Yeah, pretty much.

**[Customer]** (26:00)\
Then you could just stretch those two counters across the whole screen to avoid empty space. Make them fill the entire bottom section of the page.

**[Frontend Lead]** (26:25)\
Sounds good.

**[Customer]** (26:30)\
Yeah. That's the only thing that came to mind. Otherwise, it looks great.

**[Core Systems Engineer]** (26:45)\
Regarding future plans: we still need to confirm whether we're on the right track or if we need to adjust our direction.

**[Project Manager]** (27:05)\
We need explicit confirmation that we're doing everything right. 

**[Customer]** (27:15)\
As of right now, yes. But what are your plans moving forward?

**[Project Manager]** (27:25)\
Add support for all the metrics we're collecting.

**[Customer]** (27:35)\
Meaning, version two will be the advanced stats, right?

**[Core Systems Engineer]** (27:45)\
No, it's not even version two. It's just the next step in our workflow, for next week. We haven't even closed out the MVP yet.

**[Project Manager]** (28:10)\
Yeah, we're talking about the immediate next step and implementing the core functionality: packet counts and the activity indicator.

**[Customer]** (28:30)\
The two packet counters and the activity indicator—is that already in place?

**[Project Manager]** (28:45)\
No, that's what we'll be delivering very soon as part of MVP v1.

**[Customer]** (29:00)\
Got it. I was just a bit unclear on what "future" we were referring to.

**[Project Manager]** (29:15)\
The immediate future—MVP v1, which covers the three user stories on the board.

**[Customer]** (29:30)\
Right, yeah, just like we discussed: the counters and the activity indicator.

**[Project Manager]** (29:45)\
Well then, thank you very much for today's meeting.
