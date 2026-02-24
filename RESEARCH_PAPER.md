Abstract
Sentinel was built to solve a simple but important problem: most AI assistants forget everything after every conversation. They can't remember what you told them yesterday. They can't see what's happening around you. They just wait for text. Sentinel is different. It has an omnipresent memory that lets it remember past conversations and complete "watch list" tasks. The system uses a multi-agent architecture where each agent runs independently but communicates through an event-driven design. One agent handles the conversation and memory. Another agent watches the camera continuously using YOLOv8 object detection. When something important is detected, it generates an event that flows to an alert processor. This processor filters duplicates, scores severity, and sends notifications to the user in real-time. During testing at a residential home, Sentinel successfully detected a monkey approaching the house and sent an alert to the user's phone within seconds. This shows that the event-driven multi-agent approach can provide immediate feedback for home security. Our contribution is the architecture itself: a framework that combines conversational AI with continuous vision monitoring using LangGraph orchestration and asynchronous event processing.

Keywords: Event-driven architecture, Security monitoring, Agentic AI, LangGraph, Multi-modal AI assistant.

I. Introduction
AI is becoming common in modern homes. People use it for convenience and security. But here's the problem: most AI assistants are stateless. They lose context after every conversation. When you start a new chat, it's like you never talked before. This is fine for simple questions. But for security, this is a problem. An efficient security assistant should remember past incidents. It should learn from them. It should also be able to see, not just read text.

Most existing systems focus on text or voice input. They ignore the visual world. A home needs eyes. It needs something watching all the time. That's the gap we wanted to fill.

We built Sentinel: an event-driven AI architecture that combines conversational intelligence with continuous vision monitoring. The system uses LangGraph to coordinate multiple specialized agents. LangGraph represents conversations as directed workflow graphs. Each node is a reasoning step or tool call. This makes it easier to design and debug complex behaviors.

Our system does three main things. First, it maintains long-term memory across conversations using PostgreSQL and LangGraph's PostgresStore. Second, it continuously monitors the environment using a Vision Sub-Agent with YOLOv8 object detection. Third, it processes security events asynchronously through an event queue, ensuring alerts reach users even when they're not chatting.

The main goal of this project was to create an architecture that can combine real-time surveillance with conversational AI. The system keeps user interaction open while monitoring. It allows dynamic switching between passive and active alert states. And it's built to support future improvements.

This paper explains the motivation behind Sentinel, the research background, the architectural design, how it was implemented, the testing results, and what could be done next.

II. Literature Review
Recent research shows that breaking complex tasks across multiple agents works better than using a single large model. Liu et al. [1] studied prominent LLM-based agent frameworks like LangChain, CrewAI, and AutoGen. They found that feature development and inter-agent collaboration are key to these systems. Similarly, Rasal and Hauer [2] suggest using an LLM as a "conductor" that breaks down difficult problems and sends them to specialized agents. This approach helps avoid token limits and fixed expertise problems that come with single models. In Sentinel, we follow this idea: the Chat Agent delegates vision and tool tasks to specialized sub-agents and external APIs.

Retrieval-Augmented Generation (RAG) is another important trend. Modern assistants can draw on outside knowledge to stay current and reduce hallucinations. RAG techniques retrieve relevant context at runtime by storing text chunks in vector databases. Gao et al. [3] survey these techniques and show that combining dynamic databases with LLM knowledge improves accuracy and credibility. Sentinel uses a RAG pipeline where user documents are stored in Qdrant vector database. This lets the agent answer security-related questions using evidence from uploaded files.

Computer vision has advanced significantly for surveillance. Convolutional Neural Networks and YOLO-based detectors provide accurate recognition in camera streams [4]. Lightweight detection models improve responsiveness and reduce latency in security systems [5]. Combining vision with additional sensors like motion and audio increases detection reliability [6].

Research on AI assistants with grounded memory is also growing. Ocker et al. [13] propose a system where knowledge graphs and vision-language models preserve the assistant's memory of the user's surroundings. Morel et al. [14] survey privacy assistants for IoT and emphasize that AI-driven assistants must respect user preferences and context. Sentinel aligns with these guidelines by using LangGraph to structure memory as a conversation graph and keeping all computation local for privacy.

III. System Architecture
Sentinel uses a layered, modular framework that integrates conversational intelligence with continuous visual monitoring. The key innovation is the event-driven design that lets multiple agents work independently while staying connected.

<INSERT ARCHITECTURE DIAGRAM HERE>
<> Figure 1. Multi-agent event-driven architecture of Sentinel.

The architecture has four main parts:

A. Application Backend Layer
FastAPI handles the execution environment. It provides REST and WebSocket endpoints for user interaction. It also manages background workers and coordinates event loops. This layer ensures that conversational tasks and monitoring processes run independently without blocking each other.

B. Conversational Orchestration Layer (LangGraph Engine)
This is the heart of Sentinel. We use LangGraph to represent conversations as directed workflow graphs. Each node is a reasoning step, tool call, or state transition. The Chat Agent does four things: intent analysis (figuring out what the user wants), context management (remembering the conversation), tool invocation (calling external APIs when needed), and retrieval-augmented generation (searching documents when necessary).

The graph-based design means the system can handle complex workflows. It can make decisions about whether to use tools, whether to search documents, or whether to check the camera.

C. Vision Monitoring Layer (Background Sub-Agent)
While the conversational agent handles user messages, a separate Vision Sub-Agent runs continuously in the background. This is an asynchronous process that is completely decoupled from the chat.

The monitoring works like this: first, it captures frames from the camera. Then it runs YOLOv8 object detection on each frame. If YOLOv8 finds something important (like a person, vehicle, or animal), it creates a structured event with timestamp, label, and confidence score. This event goes into an asynchronous queue. This design ensures that detection does not block the conversational workflow.

D. Event Processing and Notification Layer
Events from the Vision Sub-Agent go to the Alert Processor. This component filters events by severity, removes duplicates (so you don't get ten alerts about the same person), validates confidence levels, and logs everything to the database. Validated events are stored in PostgreSQL and sent to connected clients via WebSocket. This whole system works independently of user interaction. Even if you're not chatting, Sentinel still sends alerts.

IV. Implementation Details
Sentinel uses Python for the backend and TypeScript for the frontend. The backend runs on FastAPI, providing REST and WebSocket APIs. The frontend is a Next.js 14 application with React.

The Chat Agent runs on LangGraph. Each conversation is a stateful graph. Nodes maintain messages, tool outputs, and sub-agent actions. We use Groq's Llama 3.3 70B model for language understanding [15]. Conversation history and agent choices are stored using LangGraph's PostgresStore with PostgreSQL. This enables long-term memory across sessions.

Document search works through Qdrant vector database [18]. User documents are processed into embeddings using Jina AI's jina-embeddings-v2-base-en model [16]. During chat, the agent searches this vector database to find relevant text chunks, then passes them to the LLM as context.

The Vision Sub-Agent is an asyncio task that starts when the server boots. It uses OpenCV to read camera frames at configurable intervals. Each frame goes through YOLOv8 object detection from Ultralytics [17]. When YOLOv8 detects a person or suspicious object, the sub-agent creates an event and publishes it to the queue.

For deeper scene understanding, we optionally use Google Gemini vision model to analyze detected frames. This enables threat assessment, natural language scene description, emotion recognition, and appearance analysis. To control costs, Gemini calls are limited to once per 30 seconds.

The Alert Processor is another background asyncio task. It listens to the same event queue. It ignores duplicate detections within a few seconds. Confirmed alerts are stored in PostgreSQL and broadcast to clients via WebSocket. This enables real-time alerting without user interaction.

The codebase is modular. The graph-based chat agent, the RAG pipeline, and the camera monitor all run at the same time. They communicate through message passing (tools and event queue) rather than direct coupling. This means the camera keeps scanning even when the user is idle, and the chat keeps answering even when vision events are processing.

V. Evaluation and Results
We tested Sentinel through functional validation of the multi-agent architecture and conversational abilities.

A. Architecture Validation
Integration testing confirmed that all major components work as expected. LangGraph properly routes queries to relevant tools based on intent. The RAG pipeline retrieves documents from Qdrant using cosine similarity. Asynchronous communication between vision and chat agents is truly event-driven and does not block. PostgreSQL persistence maintains conversation state across sessions using PostgresStore.

B. Conversational Capability Assessment
We verified the chat agent's multi-turn dialogue with memory persistence. In one test, the user asked: "Good morning, what do you know about my home security?" The agent responded: "Good morning! Based on our previous dialogues, you have a camera monitoring system at your front door. No unusual activity was recorded overnight." The agent tracked context across dialogue turns and combined RAG-retrieved data when relevant documents were available. The system also handles simultaneous tasks efficiently. While the chat agent searches documents or external APIs, the Vision Sub-Agent analyzes camera feeds at the same time.

C. Real-Time Vision Monitoring
In practical testing at a residential setting, the system successfully detected wildlife (monkeys) approaching the house and generated alerts within seconds. This demonstrated that the event-driven architecture can provide immediate feedback for home security scenarios. The YOLOv8-based detection correctly identified the animal, and the alert was delivered to the user interface promptly.

<INSERT RESULTS SCREENSHOTS HERE>
<> Figure 2. Alert notification showing detected activity.
<> Figure 3. Chat interface with conversational interaction.

VI. Conclusion
This paper presented Sentinel, an event-driven multi-agent architecture for AI-powered home security. The system combines LangGraph-based conversational AI with continuous vision monitoring using YOLOv8. The key contribution is the event-driven design that allows multiple agents to work independently while communicating through asynchronous events. This ensures that monitoring continues even when the user is not actively chatting, and that conversational responses are not blocked by vision processing. Future work will include comprehensive evaluation of detection accuracy, false positive rates, and alert latency with extended hardware testing.

References
[1] D. Liu, K. Upadhyay, V. Chhetri, A. Siddique, U. Farooq, P. Martin, and S. Roy, "A Large-Scale Study on the Development and Issues of Multi-Agent AI Systems," IEEE Workshop on Software Engineering for Agentic AI (SEAAI), 2025.

[2] S. Rasal and E. J. Hauer, "Navigating Complexity: Orchestrated Problem Solving with Multi-Agent LLMs," arXiv:2402.16713, 2024.

[3] Y. Gao, Y. Xiong, X. Gao, K. Jia, J. Pan, Y. Bi, Y. Dai, J. Sun, M. Wang, and H. Wang, "Retrieval-Augmented Generation for Large Language Models: A Survey," arXiv:2312.10997v5, 2024.

[4] C. Rojas, C. Bravo, C. Enrique, L. A. Jiménez, B. Weiczorek, and M. Aboy, "Implementing Convolutional Neural Networks to Detect Dangerous Objects in Video Surveillance Systems," Computers, Materials & Continua, vol. 85, no. 2, pp. 405–421, 2025.

[5] S. Ghosh, K. Zaman, D. Das, S. Sharma, S. Roy, and A. Kaushal, "Edge Multi-Agent Intrusion Detection: A Distributed ML Approach for IoT Devices with Cloud Continuum," in Proc. of ICOCI, IEEE, 2024.

[6] T. B. Nguyen, L. Li, S. L. Axon, and D. C. Popescu, "Non-Contact Multimodal Indoor Human Monitoring Systems: A Survey," Information Fusion, vol. 99, pp. 189–227, 2024.

[7] V. Nayak and S. Sur, "A Comprehensive Review on Deep Learning-based Methods for Video Anomaly Detection," Image and Vision Computing, vol. 113, 104177, 2021.

[8] A. Rahim, Y. Zhong, T. Ahmad, S. Ahmad, and M. H. Rehmani, "Enhancing Smart Home Security: Anomaly Detection and Face Recognition in IoT Devices Using Logit-Boosted CNN Models," Appl. Sci., vol. 13, 6487, 2023.

[9] U. De Silva, L. Fernando, B. Lau, Z. Koh, S. Joyce, B. Yuen, and C. Yuen, "Large Language Models for Video Surveillance Applications," in TENCON 2024, IEEE, 2025.

[10] Y. M. Sung, I. Mehta, and J. J. Carey, "A Comprehensive Survey and Guide to Multimodal Large Language Models in Vision-Language Tasks," arXiv:2411.06284v3, 2024.

[11] G. Wölflein, D. Ferber, D. Truhn, O. Arandjelović, and J. N. Kather, "LLM Agents Making Agent Tools," arXiv:2502.11705v2, 2025.

[12] E. Luna, J. C. San Miguel, D. Ortego, and J. M. Martínez, "Abandoned Object Detection in Video-Surveillance: Survey and Comparison," Sensors (Basel), vol. 18, no. 12, 4290, 2018.

[13] F. Ocker, J. Deigmöller, P. Smirnov, and J. Eggert, "A Grounded Memory System for Smart Personal Assistants," in Proc. of LLM-KG@ESWC, 2025.

[14] V. Morel, L. H. Iwaya, and S. Fischer-Hübner, "AI-driven Personalized Privacy Assistants: A Systematic Literature Review," IEEE Access, 2025.

[15] Groq, "Groq Cloud API: Fast AI Inference," https://groq.com, 2024.

[16] Jina AI, "Jina Embeddings v2: 8192 Token Context Length," https://jina.ai/embeddings, 2024.

[17] G. Jocher et al., "Ultralytics YOLOv8," https://github.com/ultralytics/ultralytics, 2023.

[18] Qdrant, "Qdrant Vector Database," https://qdrant.tech, 2024.
