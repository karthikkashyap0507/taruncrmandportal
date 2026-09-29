from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import json

from app.auth.deps import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

# In-memory conversation store (per conversation_id)
_conversations: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """You are an expert AI career assistant for JobsNexGen, India's most advanced AI-powered job portal.
You help users with:
- Finding and applying for jobs
- Resume writing and optimization
- Interview preparation and tips
- ATS (Applicant Tracking System) usage
- Salary negotiation strategies
- Career growth advice
- Skills development recommendations
- LinkedIn profile tips

Platform features available:
- AI-powered job search with smart matching
- Resume Builder with multiple professional templates
- ATS Pipeline Tracker (Kanban board)
- One-click AI Apply
- Saved Jobs
- Recruiter dashboard with candidate management
- Real-time notifications

Be concise (2-4 sentences), friendly, actionable, and specific. Use emojis sparingly for warmth.
When asked about jobs on the platform, suggest using the /jobs page with AI Recommendations.
When asked about resumes, suggest the /resume-builder page.
When asked about applications, suggest the /ats tracker page."""

STATIC_RESPONSES = {
    "hello": "Hi! I'm your AI career assistant at JobsNexGen 👋 I can help you find jobs, improve your resume, prep for interviews, and more. What can I do for you?",
    "hi": "Hello! Ready to help you land your dream job. Ask me anything about jobs, resumes, or interviews!",
    "hey": "Hey there! I'm here to boost your career. What are you working on today?",
    "help": "I can help you with:\n• 🔍 Job search & AI recommendations\n• 📄 Resume tips & our Resume Builder\n• 🎯 Interview preparation\n• 📊 ATS application tracking\n• 💰 Salary negotiation\n• 🚀 Career growth advice\n\nWhat do you need?",
    "jobs": "Browse jobs at /jobs — use the AI Recommendations button to get matches based on your skills! You can filter by salary, location, employment type, and more. We also pull live jobs from global sources.",
    "apply": "Applying is simple: 1) Go to /jobs, 2) Click a job card, 3) Hit 'AI Apply'. Your application is instantly tracked in the ATS Pipeline at /ats.",
    "resume": "Our Resume Builder (/resume-builder) has 3 professional templates — Modern, Classic, and Executive. It auto-fills from your profile and lets you download a polished PDF in one click!",
    "interview": "Top interview tips: ✅ Research the company's mission & recent news ✅ Use STAR method for behavioral questions ✅ Prepare 3-5 questions for the interviewer ✅ Practice with mock interviews ✅ Send a thank-you email within 24 hours.",
    "ats": "The ATS Tracker (/ats) shows your applications as a Kanban board across stages: Applied → Screening → Interview → Offered. Recruiters can move candidates through stages and you get notified at each step!",
    "salary": "Salary tips: 💡 Research market rates on LinkedIn, Glassdoor & Levels.fyi 💡 Never give the first number 💡 Negotiate the full package (bonus, ESOPs, WFH flexibility) 💡 A 10-20% ask is usually reasonable.",
    "remote": "Filter by 'Remote only' on the /jobs page to see remote-friendly roles. We have positions from companies offering full remote, hybrid, and flexible arrangements!",
    "profile": "A complete profile boosts your visibility to recruiters by 3x. Add your headline, skills, experience, and upload your resume at /profile. The AI matches you to relevant jobs automatically.",
    "skills": "Top in-demand skills in 2024:\n💻 AI/ML, Python, TypeScript\n☁️ AWS, GCP, Azure\n🔒 Cybersecurity\n📊 Data Engineering\n🎨 UI/UX Design\n⚙️ DevOps/MLOps\n\nUse /resume-builder to highlight your skills.",
    "companies": "We have top companies like Google, Microsoft, Amazon, Flipkart, Zomato, CRED, and thousands more. Check /jobs and filter by company name!",
    "recruiter": "Recruiters can post jobs, manage applications via the ATS pipeline, review candidate profiles, and bulk message candidates from the /dashboard/recruiter page.",
    "default": "Great question! I'm your AI career assistant here to help with jobs, resumes, interviews, and career growth. Try asking me about specific topics or use one of our features:\n• 🔍 /jobs — Search jobs\n• 📄 /resume-builder — Build resume\n• 📊 /ats — Track applications",
}


def get_static_response(message: str) -> str:
    msg_lower = message.lower().strip()
    for keyword, response in STATIC_RESPONSES.items():
        if keyword in msg_lower:
            return response
    return STATIC_RESPONSES["default"]


class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: Optional[str] = None
    powered_by: str


@router.post("/message", response_model=ChatResponse)
async def chat(payload: ChatMessage):
    conv_id = payload.conversation_id or "default"

    if settings.OPENAI_API_KEY:
        try:
            import httpx

            # Build conversation history
            history = _conversations.get(conv_id, [])
            history.append({"role": "user", "content": payload.message})
            # Keep last 10 messages to stay within context limits
            recent = history[-10:]

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + recent,
                        "max_tokens": 400,
                        "temperature": 0.7,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    reply = data["choices"][0]["message"]["content"]
                    history.append({"role": "assistant", "content": reply})
                    _conversations[conv_id] = history[-20:]
                    return ChatResponse(reply=reply, conversation_id=conv_id, powered_by="GPT-4o-mini")
        except Exception:
            pass

    reply = get_static_response(payload.message)
    return ChatResponse(reply=reply, conversation_id=conv_id, powered_by="JobsNexGen AI")


@router.delete("/conversation/{conversation_id}")
async def clear_conversation(conversation_id: str):
    _conversations.pop(conversation_id, None)
    return {"message": "Conversation cleared"}
