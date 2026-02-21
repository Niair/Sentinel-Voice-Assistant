# Sentinel Voice Assistant - Multi-Agent Security System

**Last Updated:** 2025-02-21  
**Version:** 1.0

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [API Keys & Resources](#3-api-keys--resources)
4. [Multi-Agent System](#4-multi-agent-system)
5. [Current Implementation](#5-current-implementation)
6. [Problem Analysis](#6-problem-analysis)
7. [Solution - Multi-Agent Architecture](#7-solution---multi-agent-architecture)
8. [Security Agent - Qwen2-VL-7B](#8-security-agent---qwen2-vl-7b)
9. [Helper Agent - Notification System](#9-helper-agent---notification-system)
10. [Anti-Spam Logic](#10-anti-spam-logic)
11. [File Structure](#11-file-structure)
12. [Implementation Phases](#12-implementation-phases)
13. [Code Patterns](#13-code-patterns)
14. [Notification Templates](#14-notification-templates)
15. [Testing Checklist](#15-testing-checklist)
16. [Dependencies](#16-dependencies)
17. [Q&A Summary](#17-qa-summary)

---

## 1. Project Overview

**Project Name:** Sentinel Voice Assistant  
**Type:** AI Voice Assistant with Security Monitoring  
**Backend:** Python FastAPI + LangChain/LangGraph  
**Frontend:** Next.js 14 + TypeScript + Tailwind CSS  
**Database:** PostgreSQL with pgvector  

**Core Features:**
- Chat with RAG (document upload)
- Security camera monitoring
- Object detection (YOLO)
- Vision analysis (Gemini/Groq Vision)
- MCP tools (finance/expense tracking)
- Multi-agent orchestration

---

## 2. Architecture

### Current Architecture (Before Multi-Agent)

```
User Chat → Main Agent (Groq Llama) → Tools (Camera, Vision, MCP)
                              ↓
                    Monitoring Worker (YOLO)
                              ↓
                    Gemini Vision (fails - quota)
                              ↓
                    Notifications (spam issue)
```

### Target Architecture (Multi-Agent)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         MULTI-AGENT SECURITY SYSTEM                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  USER CHAT (Frontend)                                                    │
│      │                                                                   │
│      ▼                                                                   │
│  ┌─────────────────────────────────────────┐                             │
│  │         MAIN AGENT (Groq Llama)         │                             │
│  │                                         │                             │
│  │  • Normal conversation                  │                             │
│  │  • Tool calling (MCP, Camera, etc.)   │                               │
│  │  • Routes security questions           │                              │
│  └──────────────┬──────────────────────────┘                             │
│                 │                                                        │
│                 │ Security/Camera Request                                │
│                 ▼                                                        │
│  ┌─────────────────────────────────────────┐                             │
│  │   SECURITY AGENT (Qwen2-VL-7B)          │                             │
│  │           (Local, GPU)                  │                             │
│  │                                         │                             │
│  │  INPUT: Camera frame + Question        │                              │
│  │  OUTPUT: Analysis + Threat Assessment  │                              │
│  └──────────────┬──────────────────────────┘                             │
│                 │                                                        │
│                 │ Analysis Result                                        │
│                 ▼                                                        │
│  ┌─────────────────────────────────────────┐                             │
│  │   HELPER AGENT (NVIDIA/Thinking)         │                            │
│  │     (Smart Categorization)               │                            │
│  │                                         │                             │
│  │  • Categorize: Normal/Caution/Alert  │                                │
│  │  • Smart notification routing           │                             │
│  │  • Anti-spam logic                     │                              │
│  └──────────────┬──────────────────────────┘                             │
│                 │                                                        │
│                 ▼                                                        │
│  ┌─────────────────────────────────────────┐                             │
│  │        NOTIFICATION SYSTEM                │                           │
│  │                                         │                             │
│  │  👤 Normal → Single notification        │                             │
│  │  ⚠️ Caution → Warning notification       │                            │
│  │  🚨 Alert → Interrupt Main Agent        │                             │
│  └─────────────────────────────────────────┘                             │
│                                                                          │
│  BACKGROUND MONITORING (Parallel)                                        │
│      │                                                                   │
│      ▼                                                                   │
│  ┌─────────────────────────────────────────┐                             │
│  │          YOLO (Fast Detection)           │                            │
│  │           (Always Running)               │                            │
│  │                                         │                             │
│  │  Person → Trigger Qwen2 analysis       │                              │
│  │  No person → Skip (save resources)     │                              │
│  └─────────────────────────────────────────┘                             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. API Keys & Resources

| Service | Key Location | Purpose | Status |
|---------|--------------|---------|--------|
| **Groq** | `.env` | Main Agent (chat) | ✅ Working (free tier) |
| **NVIDIA** | `.env` | Helper Agent (thinking) | ✅ Working (free credits) |
| **Google Gemini** | `.env` | Vision (backup) | ❌ Quota exhausted |
| **OpenAI** | `.env` | Vision (optional) | Not configured |

### API Usage Distribution (Recommended)

| Task | API/Model | Why? | Limits |
|------|-----------|------|--------|
| Casual Chat | Groq Llama-3.3-70B | Fast, good for conversation | ✅ Free tier |
| Vision Analysis | Qwen2-VL-7B (Local) | No API limits | ✅ FREE |
| Security Thinking | NVIDIA Thinking | Deep reasoning | ✅ Free credits |
| Document Search | Groq Llama | Fast RAG | ✅ Free tier |
| Web Search | DuckDuckGo | Free, no API needed | ✅ FREE |

---

## 4. Multi-Agent System

### 4.1 Agent Responsibilities

| Agent | Model | Task |
|-------|-------|------|
| **Main Agent** | Groq Llama-3.3-70b-versatile | User conversation, tool routing |
| **Security Agent** | Qwen2-VL-7B (Local) | Vision analysis, threat detection |
| **Helper Agent** | NVIDIA (Thinking) | Categorization, anti-spam, notifications |

### 4.2 Communication Flow

```
User: "How do I look?"
    ↓
Main Agent recognizes camera question → Calls security tool
    ↓
Security Agent (Qwen2):
  - Captures frame
  - Analyzes: "Person wearing blue shirt, casual style, looks relaxed"
    ↓
Helper Agent (NVIDIA):
  - Categorizes: PERSONAL_APPEARANCE
  - Context: User wants fashion feedback
  - No threat detected → Normal notification
    ↓
Main Agent formats response:
  "You look great! Your blue shirt looks nice and casual. You seem relaxed today! 😊"
```

### 4.3 Question Types & Routing

| User Question | Security Agent Task | Helper Agent Role |
|---------------|--------------------|--------------------|
| "How do I look?" | Analyze appearance, outfit, mood | Format as fashion advice |
| "Where's my laptop?" | Search scene for laptop object | Provide location description |
| "Check on the dog" | Find dog, describe activity | Report pet status |
| "Is anyone there?" | Count people, describe them | Provide summary |
| "What's happening?" | Full scene analysis | Provide detailed report |
| "Is it safe?" | Threat assessment | Format as security report |

---

## 5. Current Implementation

### 5.1 Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `backend/app/agents/security_agent.py` | ✅ Created | Qwen2-VL-7B integration |
| `backend/app/agents/__init__.py` | ✅ Created | Agent package init |
| `backend/app/monitoring_worker.py` | ✅ Modified | Anti-spam, Gemini integration |
| `backend/app/vision_tools.py` | ✅ Modified | Gemini migration to google-genai |
| `backend/app/camera_tools.py` | ✅ Modified | Added 8 new tools |
| `backend/app/graph.py` | ✅ Modified | Updated system prompt |
| `backend/pyproject.toml` | ✅ Modified | Added dependencies |
| `_assets/MULTI_AGENT_SECURITY_PLAN.md` | ✅ Created | Initial plan |

### 5.2 Current Tools

**Camera Tools (11):**
- `query_camera_status` - Check if camera is working
- `get_recent_camera_detections` - See recent detections
- `get_camera_alert_summary` - Get statistics
- `capture_current_frame` - Get current frame
- `analyze_current_scene` - Natural scene description
- `check_for_threats` - Security threat analysis
- `get_outfit_advice` - Fashion suggestions
- `what_is_happening` - Complete scene analysis
- `how_do_i_look` - Appearance + emotions
- `detect_emotional_state` - Mood detection
- `what_are_people_doing` - Activity classification

**Vision Tools (8):**
- `analyze_frame_for_threats` - Weapon detection
- `describe_scene` - Scene description
- `analyze_outfit` - Fashion analysis
- `count_people_in_frame` - People counting
- `understand_scene` - Comprehensive scene
- `detect_activity` - Activity classification
- `detect_emotions` - Emotional state
- `analyze_person` - Full personal analysis

---

## 6. Problem Analysis

### 6.1 Issues Encountered

| Problem | Cause | Solution |
|---------|-------|----------|
| **Notification Spam** | Camera status sent every reconnection | Added session tracking flags |
| **Gemini Quota Exhausted** | Free tier very limited (15 req/day) | Switch to local Qwen2-VL |
| **LLM Calls Vision for "hello"** | Tool descriptions too aggressive | Added explicit "ONLY use when..." rules |
| **NumPy Conflict** | NumPy 2.x incompatible with transformers | Downgraded to numpy<2.0 |

### 6.2 Test Results

**Test 1: "hello how are you"**
```
✅ CORRECT: No vision tools called, just replied normally
```

**Test 2: "what's happening?"**
```
✅ CORRECT: Called what_is_happening tool
❌ FAILED: Gemini quota exhausted (429 error)
```

**Test 3: "how do i look?"**
```
✅ CORRECT: Called how_do_i_look tool  
❌ FAILED: Gemini quota exhausted (429 error)
```

---

## 7. Solution - Multi-Agent Architecture

### 7.1 Why Multi-Agent?

| Benefit | Explanation |
|---------|-------------|
| **Separation of Concerns** | Each agent does ONE thing well |
| **Parallel Processing** | Security monitors while Main chats |
| **Smart Routing** | Helper decides what's important |
| **Different Models** | Fast model for security, smart model for decisions |
| **Scalable** | Easy to add more agents later |

### 7.2 Why Qwen2-VL-7B?

| Feature | Qwen2-VL-7B | Moondream2 | Gemini Vision |
|---------|-------------|------------|---------------|
| Size | 4.5GB | 1.7GB | API |
| Weapon Detection | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Situation Analysis | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Cost | FREE | FREE | Limited |
| Privacy | 100% Local | 100% Local | Sent to Google |
| Offline | Yes | Yes | No |

### 7.3 Model Comparison for Security

| Scenario | Qwen2-VL-7B | LLaVA-1.6-7B | Gemini |
|----------|-------------|---------------|--------|
| Person with knife | ✅ Detects | ⚠️ Vague | ✅ Best |
| Monkey entering window | ✅ Detailed | ✅ Correct | ✅ Best |
| Cat biting curtains | ✅ Clear description | ⚠️ Vague | ✅ Best |
| Suspicious mask | ✅ Noted as suspicious | ⚠️ Vague | ✅ Best |

---

## 8. Security Agent - Qwen2-VL-7B

### 8.1 Capabilities

| Capability | Quality | Example |
|------------|---------|---------|
| Object Detection | ⭐⭐⭐⭐ | "What objects are in this image?" |
| Person Counting | ⭐⭐⭐⭐⭐ | "How many people are there?" |
| Activity Recognition | ⭐⭐⭐⭐ | "What is the person doing?" |
| Scene Description | ⭐⭐⭐⭐ | "Describe what's happening" |
| Safety Assessment | ⭐⭐⭐ | "Is this scene safe?" |
| Threat Detection | ⭐⭐⭐ | "Do you see any weapons?" |
| Clothing Description | ⭐⭐⭐⭐ | "What is the person wearing?" |
| Emotion Detection | ⭐⭐⭐ | Basic emotions only |

### 8.2 What It CAN Do Well

- ✅ "Is there a person?" - Accurate person detection
- ✅ "How many people?" - Good at counting
- ✅ "What are they doing?" - Good activity recognition
- ✅ "Describe the scene" - Good descriptions
- ✅ "Any weapons?" - May miss small weapons (use prompt)
- ✅ "What color shirt?" - Good at colors
- ✅ "Wearing mask/hoodie?" - Good detection

### 8.3 What It CANNOT Do Well

- ❌ Fine details ("What brand is that shirt?")
- ❌ Text reading ("What does that sign say?") - hit or miss
- ❌ Tiny objects ("Is there a small knife?") - may miss
- ❌ Complex emotions ("Are they crying?") - basic only

### 8.4 Memory Management

```
┌─────────────────────────────────────────────────────────────┐
│                  GPU Memory (8GB VRAM - User's GPU)          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Default State:                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Qwen2-VL: NOT LOADED (0 MB)                        │   │
│  │  VRAM Available: ~8GB                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  When Person Detected by YOLO:                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Loading Qwen2-VL... (~7GB VRAM)                   │   │
│  │  Analyzing frame... (2-3 seconds)                  │   │
│  │  VRAM Used: ~7GB                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  After 30 seconds of no person:                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Unloading Qwen2-VL... (0 MB)                      │   │
│  │  VRAM Available: ~8GB                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Helper Agent - Notification System

### 9.1 Notification Types

| Icon | Type | When | Action |
|------|------|------|--------|
| 👤 | **Normal** | Person detected, no threat | Background notification |
| ⚠️ | **Caution** | Suspicious activity | Show with warning |
| 🚨 | **Alert** | Threat detected | Interrupt Main Agent, show alert |

### 9.2 Notification Examples

**👤 Normal Notification:**
```
👤 Person Detected

Location: Living Room
Count: 1 person
Activity: Sitting on couch
Time: 2:30 PM
```

**⚠️ Caution Notification:**
```
⚠️ Suspicious Activity Detected

Type: Person with mask
Location: Front door
Activity: Looking around nervously
Time: 3:15 PM
Recommendation: Verify if expected visitor
```

**🚨 Alert Notification:**
```
🚨 THREAT DETECTED

Type: Weapon detected
Location: Back entrance
Details: Person holding knife
Time: 3:45 PM
Action: Contact emergency services immediately
```

---

## 10. Anti-Spam Logic

### 10.1 The Problem

```
Frame 1: Person detected → Alert! 👤
Frame 2: Person detected → Alert! 👤
Frame 3: Person detected → Alert! 👤
...spam every 0.1 seconds!
```

### 10.2 The Solution - Session Tracking

```
Frame 1: Person detected → New session → Alert! 👤
Frame 2: Same person → Session continues → NO alert
Frame 3: Same person → Session continues → NO alert
...
Frame 100: Person leaves → Session ends → Alert! "Person left" 👋

Frame 150: New person enters → New session → Alert! 👤
```

### 10.3 Notification Rules

| Event | Notify? | Example |
|-------|---------|---------|
| Person enters | ✅ YES | "👤 Person detected in living room" |
| Same person stays | ❌ NO | (Silent - no spam) |
| Person count changes | ✅ YES | "👥 Now 2 people detected" |
| New activity | ✅ YES | "Person picked up an object" |
| Person leaves | ✅ YES | "👋 Area is now empty" |
| Threat detected | ✅ ALWAYS | "🚨 THREAT: Weapon detected!" |

### 10.4 SessionTracker Code

```python
class SessionTracker:
    """Prevent notification spam when person is present"""
    
    def __init__(self):
        self.session_active = False
        self.last_person_count = 0
        self.last_activity = ""
        self.session_start_time = None
        self.min_notification_gap = 300  # 5 minutes
    
    def should_notify(self, current_result: dict) -> tuple[bool, str]:
        """Decide if notification should be sent"""
        
        person_count = current_result.get("person_count", 0)
        activity = current_result.get("activity", "")
        
        # Always notify for threats
        if current_result.get("has_threat"):
            return True, "THREAT"
        
        # No person, was active before = person left
        if person_count == 0 and self.session_active:
            self.session_active = False
            return True, "EXIT"
        
        # New person entered
        if person_count > 0 and not self.session_active:
            self.session_active = True
            self.session_start_time = datetime.utcnow()
            self.last_person_count = person_count
            self.last_activity = activity
            return True, "ENTRY"
        
        # Person count changed
        if person_count != self.last_person_count:
            self.last_person_count = person_count
            return True, "COUNT_CHANGE"
        
        # Activity changed significantly
        if activity != self.last_activity and len(activity) > 10:
            self.last_activity = activity
            return True, "ACTIVITY_CHANGE"
        
        # Same situation - don't spam
        return False, "NO_CHANGE"
```

---

## 11. File Structure

### 11.1 Target Structure

```
backend/app/
├── agents/
│   ├── __init__.py              ✅ Already created
│   ├── security_agent.py        ✅ Already created - Qwen2-VL-7B
│   ├── helper_agent.py           ⏳ TO CREATE - NVIDIA categorization
│   └── notification_tool.py      ⏳ TO CREATE - Smart notifications
├── graph.py                      ✅ Modified - Add agent routing
├── multi_agent_graph.py          ⏳ TO CREATE - Agent orchestration
├── monitoring_worker.py         ✅ Modified - Anti-spam, connect Qwen2
├── camera_tools.py               ✅ Modified - Add security agent tools
├── vision_tools.py              ✅ Modified - Legacy support
├── main.py                      ⏳ MODIFY - Add agent initialization
├── detection.py                 ✅ Already exists - YOLO
├── events.py                    ✅ Already exists - Event bus
├── websocket_manager.py        ✅ Already exists - WebSocket
└── mcp.py                       ✅ Already exists - MCP client
```

### 11.2 Implementation Files

| File | Purpose | Status |
|------|---------|--------|
| `agents/security_agent.py` | Qwen2-VL-7B integration | ✅ Created (needs testing) |
| `agents/helper_agent.py` | Categorization + anti-spam | ⏳ To create |
| `agents/notification_tool.py` | Smart notification formatting | ⏳ To create |
| `multi_agent_graph.py` | LangGraph agent orchestration | ⏳ To create |

---

## 12. Implementation Phases

### Phase 1: Qwen2-VL-7B Security Agent ✅ (Partially Complete)
**Goal:** Set up Qwen2-VL-7B for local vision analysis

| Step | Task | Status |
|------|------|--------|
| 1.1 | Add dependencies to pyproject.toml | ✅ Done |
| 1.2 | Create security_agent.py | ✅ Done |
| 1.3 | Create agents/__init__.py | ✅ Done |
| 1.4 | Install dependencies (numpy<2.0) | ✅ Done |
| 1.5 | Test Security Agent loading | 🔄 In Progress |
| 1.6 | Test frame analysis | ⏳ To test |
| 1.7 | Add to camera_tools | ⏳ To create |

### Phase 2: Helper Agent with NVIDIA
**Goal:** Create categorization agent

| Step | Task | Status |
|------|------|--------|
| 2.1 | Create helper_agent.py | ⏳ To create |
| 2.2 | Add notification_tool.py | ⏳ To create |
| 2.3 | Implement anti-spam logic | ⏳ To create |
| 2.4 | Test Helper Agent | ⏳ To test |

### Phase 3: Integration with Main Graph
**Goal:** Connect all agents in LangGraph

| Step | Task | Status |
|------|------|--------|
| 3.1 | Create multi_agent_graph.py | ⏳ To create |
| 3.2 | Add agent routing to graph.py | ⏳ To create |
| 3.3 | Connect monitoring worker | ⏳ To create |
| 3.4 | Test end-to-end | ⏳ To test |

### Phase 4: Background Monitoring Enhancement
**Goal:** Improve continuous monitoring

| Step | Task | Status |
|------|------|--------|
| 4.1 | Add YOLO → Qwen2 trigger | ⏳ To create |
| 4.2 | Smart frame sampling | ⏳ To create |
| 4.3 | Session tracking (anti-spam) | ⏳ To create |
| 4.4 | Test monitoring | ⏳ To test |

---

## 13. Code Patterns

### 13.1 Security Agent Tool (Camera Tools)

```python
@tool
async def analyze_with_security_agent(query: str) -> str:
    """
    Use Security Agent to analyze camera for specific information.
    
    IMPORTANT: Only use when user EXPLICITLY asks about camera.
    NEVER use for casual conversation like "hello".
    
    Args:
        query: What to look for (e.g., "how do I look", "check on dog")
    
    Returns:
        Analysis result from Security Agent + Helper categorization
    """
    # 1. Capture frame
    frame = get_captured_frame()
    if frame is None:
        return "No frame available. Camera may not be active."
    
    # 2. Get Security Agent
    from app.agents.security_agent import get_security_agent
    security_agent = get_security_agent()
    
    # 3. Determine prompt based on query
    if "how do i look" in query.lower():
        prompt = """Analyze this person's appearance. Describe their outfit, 
                   style, mood, and overall look."""
    elif "laptop" in query.lower():
        prompt = "Look for a laptop in this scene. Where is it?"
    elif "dog" in query.lower():
        prompt = "Find any dogs in this scene. What is the dog doing?"
    else:
        prompt = f"Answer: {query}"
    
    # 4. Analyze with Qwen2
    result = await security_agent.analyze(frame, prompt)
    
    if not result.get("success"):
        return f"Analysis failed: {result.get('error', 'Unknown error')}"
    
    # 5. Return formatted result
    return format_security_result(result, query)
```

### 13.2 Helper Agent Categorization

```python
class NotificationType(Enum):
    NORMAL = "normal"      # 👤 - Person detected, no threat
    CAUTION = "caution"  # ⚠️ - Suspicious activity
    ALERT = "alert"      # 🚨 - Threat detected

class HelperAgent:
    def __init__(self):
        self.session_tracker = SessionTracker()
        # NVIDIA API client would go here
    
    async def categorize(self, security_result: dict) -> tuple[NotificationType, str]:
        """Categorize security result"""
        
        # Check for threats first
        if security_result.get("has_weapon"):
            return NotificationType.ALERT, self._format_alert(security_result)
        
        # Check for suspicious activity
        if security_result.get("is_suspicious"):
            return NotificationType.CAUTION, self._format_caution(security_result)
        
        # Normal detection
        return NotificationType.NORMAL, self._format_normal(security_result)
```

### 13.3 Anti-Spam Implementation

```python
async def smart_notify(security_result: dict) -> Optional[dict]:
    """
    Decide whether to send notification based on anti-spam rules.
    """
    # Check session tracker
    should_notify, reason = session_tracker.should_notify(security_result)
    
    if not should_notify:
        return None  # Don't spam!
    
    # Determine notification type
    if security_result.get("has_weapon"):
        notification_type = "alert"
    elif security_result.get("is_suspicious"):
        notification_type = "caution"
    else:
        notification_type = "normal"
    
    # Create notification
    return {
        "type": notification_type,
        "reason": reason,
        "message": format_notification(security_result, notification_type),
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## 14. Notification Templates

### 14.1 Normal Notifications

```json
{
  "type": "normal",
  "icon": "👤",
  "title": "Person Detected",
  "fields": {
    "Location": "Living Room",
    "Count": "1 person",
    "Activity": "Sitting on couch",
    "Time": "2:30 PM"
  }
}
```

### 14.2 Caution Notifications

```json
{
  "type": "caution",
  "icon": "⚠️",
  "title": "Suspicious Activity",
  "fields": {
    "Type": "Person with mask",
    "Location": "Front door",
    "Activity": "Looking around nervously",
    "Time": "3:15 PM"
  },
  "recommendation": "Verify if expected visitor"
}
```

### 14.3 Alert Notifications

```json
{
  "type": "alert",
  "icon": "🚨",
  "title": "THREAT DETECTED",
  "fields": {
    "Type": "Weapon detected",
    "Location": "Back entrance",
    "Details": "Person holding knife",
    "Time": "3:45 PM"
  },
  "action": "Contact emergency services immediately",
  "interrupt_main_agent": true
}
```

---

## 15. Testing Checklist

### Phase 1 - Security Agent
- [ ] Model downloads successfully (~4.5GB)
- [ ] Frame capture works
- [ ] "How do I look?" returns appearance analysis
- [ ] "Check on dog" returns dog description
- [ ] "Is there a person?" returns count
- [ ] Memory management (load/unload) works
- [ ] Analysis completes in < 5 seconds

### Phase 2 - Helper Agent
- [ ] Normal detection categorized correctly
- [ ] Suspicious activity triggers caution
- [ ] Weapon detection triggers alert
- [ ] Anti-spam prevents repeated notifications
- [ ] Person entry/exit detected

### Phase 3 - Integration
- [ ] Main Agent routes camera questions
- [ ] Security Agent called correctly
- [ ] Helper Agent categorizes properly
- [ ] Response returns to user
- [ ] Notifications display correctly

### Phase 4 - Monitoring
- [ ] YOLO triggers Qwen2 on person detection
- [ ] No person = skip Qwen2 (saves resources)
- [ ] Session tracking prevents spam
- [ ] Database stores all alerts

---

## 16. Dependencies

### Current pyproject.toml

```toml
[project]
name = "backend"
version = "0.1.0"
requires-python = ">=3.11,<3.13"
dependencies = [
    "fastapi>=0.128.0",
    "uvicorn>=0.40.0",
    "langchain>=0.3.27",
    "langchain-core>=0.3.74",
    "langchain-community>=0.3.27",
    "langchain-mcp-adapters>=0.1.0",
    "langgraph>=0.6.4",
    "langgraph-checkpoint-postgres>=2.1.1",
    "langchain-google-genai>=2.0.10",
    "google-genai>=1.0.0",
    "langchain-groq>=0.3.7",
    "langchain-text-splitters",
    "python-dotenv>=1.2.1",
    "psycopg[binary]>=3.2.0",
    "asyncpg>=0.29.0",
    "langchain-postgres>=0.0.15",
    "pgvector>=0.3.2",
    "pymupdf>=1.25.0",
    "ddgs>=8.3.1",
    "fastmcp>=2.14.4",
    "faiss-cpu>=1.7.4",
    "langchain-nvidia-ai-endpoints>=1.0.3",
    "voyageai>=0.3.7",
    # Qwen2-VL for Security Agent
    "transformers>=4.40.0",
    "accelerate>=0.30.0",
    "qwen-vl-utils>=0.0.1",
    "pillow>=10.0.0",
    # Important: numpy must be <2.0 for transformers
]
```

### Additional Requirements

```bash
# Critical: numpy must be <2.0 for transformers compatibility
pip install "numpy<2.0"
```

---

## 17. Q&A Summary

### Q1: Do we need YOLO if we have Qwen2?
**Answer:** Yes, keep YOLO for fast detection. YOLO runs at 30+ fps, Qwen2 runs at 0.3 fps (2-3 sec/frame). Use YOLO to filter frames - only send to Qwen2 when person detected.

### Q2: Does Qwen2 need input (prompt) to run?
**Answer:** Yes! Qwen2 needs both the image AND a prompt. Example:
```python
result = qwen2(
    image=frame,
    prompt="Is there a person? What are they doing? Any weapons?"
)
```

### Q3: Do caution results get saved in database?
**Answer:** Yes, all notifications are saved to alert_history.json with severity level (LOW/MEDIUM/HIGH).

### Q4: Groq for Main, NVIDIA for Helper - Good choice?
**Answer:** Yes! Groq is fast for chat, NVIDIA has thinking models for better analysis. Good separation of concerns.

### Q5: Anti-spam for person sitting in front of camera?
**Answer:** Implemented via SessionTracker. Only notifies on: entry, exit, count change, activity change. Does NOT spam while person stays still.

### Q6: Camera tools integration ("how do I look", "where's my laptop")?
**Answer:** Yes! Security Agent handles all camera queries. Main Agent routes camera questions to Security Agent, which analyzes and returns result.

### Q7: Why Qwen2-VL-7B over Moondream2?
**Answer:** Qwen2 is smarter:
- Moondream: "I see a person" (may miss knife)
- Qwen2: "Person holding knife, threat level high" (detailed)

### Q8: User specs for Qwen2?
**Answer:**
- RAM: 16GB ✅
- VRAM: 8GB ✅ (can run Qwen2-VL-7B)
- Docker: Running (need memory management)

### Q9: NumPy conflict issue?
**Answer:** Fixed by downgrading: `pip install "numpy<2.0"`

### Q10: What questions can Security Agent answer?
| Question Type | Example | Security Agent Task |
|---------------|---------|---------------------|
| Appearance | "How do I look?" | Analyze outfit, mood |
| Location | "Where's my laptop?" | Find object in scene |
| Pet | "Check on dog" | Find and describe pet |
| Security | "Is anyone there?" | Count + describe |
| Scene | "What's happening?" | Full scene analysis |
| Threat | "Is it safe?" | Threat assessment |

---

## 🚀 Next Steps (Continue from here)

1. **Test Qwen2-VL-7B loading** - Currently in progress
2. **Complete Security Agent integration** - Add to camera_tools
3. **Create Helper Agent** - helper_agent.py with NVIDIA
4. **Create Notification Tool** - notification_tool.py
5. **Create multi_agent_graph.py** - Agent orchestration
6. **Test end-to-end** - Full integration test
7. **Background monitoring** - YOLO → Qwen2 trigger

---

*This document is the complete reference for the Sentinel Multi-Agent Security System. All future development should reference this plan.*
