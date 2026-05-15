from fastapi import FastAPI, Request, HTTPException, Form, Cookie
from app.core.logging import logger
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import json
from pathlib import Path
from typing import Optional
import os

# Get the absolute path to the app directory
BASE_DIR = Path(__file__).resolve().parent

# Initialize FastAPI app
app = FastAPI(title="Website Analyzer Frontend")

# Setup templates and static files with ABSOLUTE paths
TEMPLATES_DIR = str(BASE_DIR / "templates")
STATIC_DIR = str(BASE_DIR / "static")

# Initialize Jinja2Templates correctly
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Backend API URL

#BACKEND_API = "http://localhost:8000"
BACKEND_API = "http://192.168.1.15:8000"

print(f"✅ Templates directory: {TEMPLATES_DIR}")
print(f"✅ Static directory: {STATIC_DIR}")
print(f"✅ Templates folder exists: {os.path.exists(TEMPLATES_DIR)}")
print(f"✅ Static folder exists: {os.path.exists(STATIC_DIR)}")

# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

async def get_headers(token: str = None):
    """Create headers with authorization token."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ═══════════════════════════════════════════════════════════════
# PUBLIC PAGES (No Auth Required)
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Handle login form."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_API}/api/auth/login",
                data={"username": username, "password": password}
            )
            
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            user = json.dumps(data.get("user", {}))
            
            # Redirect to dashboard with token in cookie
            resp = RedirectResponse(url="/dashboard", status_code=303)
            resp.set_cookie(key="access_token", value=token, max_age=1800)
            resp.set_cookie(key="user", value=user, max_age=1800)
            return resp
        else:
            error = response.json().get("detail", "Login failed")
            return templates.TemplateResponse(request, "login.html", {"error": error})
    except Exception as e:
        return templates.TemplateResponse(request, "login.html", {"error": str(e)})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Register page."""
    return templates.TemplateResponse(request, "register.html", {})


@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    """Handle registration form."""
    print(f"📝 Registration form submitted: {email}")
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"🔗 Sending to backend: {BACKEND_API}/api/auth/register")
            response = await client.post(
                f"{BACKEND_API}/api/auth/register",
                json={"username": username, "email": email, "password": password}
            )
            
        print(f"✅ Backend response status: {response.status_code}")
        print(f"📋 Backend response: {response.text}")
        
        if response.status_code in (200, 201):
            print(f"✅ Registration successful! Redirecting to login...")
            return RedirectResponse(url="/login?registered=true", status_code=303)
        else:
            try:
                error_data = response.json()
                error = error_data.get("detail", "Registration failed")
            except:
                error = f"Registration failed: {response.text}"
            print(f"❌ Error: {error}")
            return templates.TemplateResponse(request, "register.html", {"error": error})
            
    except Exception as e:
        print(f"❌ Exception during registration: {type(e).__name__}: {e}")
        return templates.TemplateResponse(request, "register.html", {"error": f"Error: {str(e)}"})


# ═══════════════════════════════════════════════════════════════
# PROTECTED PAGES (Auth Required)
# ═══════════════════════════════════════════════════════════════

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, access_token: str = Cookie(None)):
    """Dashboard - list of analyses."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        async with httpx.AsyncClient() as client:
            # Fetch analyses
            response = await client.get(
                f"{BACKEND_API}/api/analysis/history",
                headers=await get_headers(access_token),
                params={"skip": 0, "limit": 10}
            )
        
        if response.status_code == 200:
            analyses = response.json()
        else:
            analyses = []
        
        user = json.loads(request.cookies.get("user", "{}"))
        
        return templates.TemplateResponse(
            request, 
            "dashboard.html",
            {"analyses": analyses, "user": user}
        )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"analyses": [], "error": str(e)}
        )


@app.post("/dashboard", response_class=HTMLResponse)
async def submit_analysis(
    request: Request,
    url: str = Form(...),
    access_token: str = Cookie(None)
):
    """Submit a new analysis."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_API}/api/analysis/analyze",
                json={"url": url},
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 202:
            return RedirectResponse(url="/dashboard", status_code=303)
        else:
            error = response.json().get("detail", "Analysis submission failed")
            async with httpx.AsyncClient() as client:
                analyses_response = await client.get(
                    f"{BACKEND_API}/api/analysis/history",
                    headers=await get_headers(access_token),
                    params={"skip": 0, "limit": 10}
                )
            analyses = analyses_response.json() if analyses_response.status_code == 200 else []
            
            return templates.TemplateResponse(
                request,
                "dashboard.html",
                {"analyses": analyses, "error": error}
            )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "dashboard.html",
            {"error": str(e)}
        )


@app.get("/analysis/{analysis_id}", response_class=HTMLResponse)
async def analysis_detail(
    request: Request,
    analysis_id: str,
    access_token: str = Cookie(None)
):
    """Analysis detail page."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_API}/api/analysis/results/{analysis_id}",
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 200:
            analysis = response.json()
            
            # Parse JSON fields
            analysis["seo_strengths"] = json.loads(analysis.get("seo_strengths", "[]"))
            analysis["seo_weaknesses"] = json.loads(analysis.get("seo_weaknesses", "[]"))
            analysis["ux_strengths"] = json.loads(analysis.get("ux_strengths", "[]"))
            analysis["ux_weaknesses"] = json.loads(analysis.get("ux_weaknesses", "[]"))
            
            return templates.TemplateResponse(
                request,
                "analysis_detail.html",
                {"analysis": analysis}
            )
        else:
            return templates.TemplateResponse(
                request,
                "analysis_detail.html",
                {"error": "Analysis not found"}
            )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "analysis_detail.html",
            {"error": str(e)}
        )

@app.get("/api/analysis/{analysis_id}")
async def get_analysis_api(
    request: Request,
    analysis_id: int,
    access_token: str = Cookie(None)
):
    """API endpoint to get single analysis (for polling/auto-update)."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_API}/api/analysis/results/{analysis_id}",
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail="Analysis not found")
    except Exception as e:
        logger.error(f"Error fetching analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    analysis_id: Optional[int] = None,
    session_id: Optional[int] = None,
    access_token: str = Cookie(None)
):
    """Chat interface with sidebar showing sessions filtered by analysis."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        async with httpx.AsyncClient() as client:
            # 🔄 STEP 1: Fetch sessions FILTERED by analysis_id
            params = {}
            if analysis_id is not None:
                params["analysis_id"] = analysis_id
            
            sessions_response = await client.get(
                f"{BACKEND_API}/api/chat/sessions",
                headers=await get_headers(access_token),
                params=params
            )
            
            sessions = sessions_response.json() if sessions_response.status_code == 200 else []
            
            # 🔄 STEP 2: Determine which session to display
            messages = []
            current_session = None
            
            # If explicit session_id provided, use it (user clicked a session)
            if session_id:
                current_session = next((s for s in sessions if s["id"] == session_id), None)
            
            # If no sessions exist, auto-create one
            if not sessions:
                async with httpx.AsyncClient() as client:
                    create_response = await client.post(
                        f"{BACKEND_API}/api/chat/sessions/new",
                        headers=await get_headers(access_token),
                        params={"analysis_id": analysis_id} if analysis_id else {}
                    )
                
                if create_response.status_code == 200:
                    session_data = create_response.json()
                    redirect_url = f"/chat?session_id={session_data['id']}"
                    if analysis_id:
                        redirect_url += f"&analysis_id={analysis_id}"
                    return RedirectResponse(url=redirect_url, status_code=303)
                else:
                    raise Exception("Failed to create session")
            else:
                # Use selected session or fallback to latest
                if not current_session:
                    current_session = sessions[0]
                
                # ✅ NEW: If session_id is not in URL but we have current_session, redirect!
                if not session_id and current_session:
                    redirect_url = f"/chat?session_id={current_session['id']}"
                    if analysis_id:
                        redirect_url += f"&analysis_id={analysis_id}"
                    return RedirectResponse(url=redirect_url, status_code=303)
                
                # Fetch messages from current session
                if current_session:
                    async with httpx.AsyncClient() as client:
                        msg_response = await client.get(
                            f"{BACKEND_API}/api/chat/sessions/{current_session['id']}/messages",
                            headers=await get_headers(access_token)
                        )
                    messages = msg_response.json() if msg_response.status_code == 200 else []
        
        user = json.loads(request.cookies.get("user", "{}"))
        
        return templates.TemplateResponse(
            request,
            "chat.html",
            {
                "sessions": sessions,
                "current_session": current_session,
                "messages": messages,
                "analysis_id": analysis_id,
                "user": user
            }
        )
    except Exception as e:
        logger.error(f"Chat page error: {e}", exc_info=True)
        user = json.loads(request.cookies.get("user", "{}"))
        return templates.TemplateResponse(
            request,
            "chat.html",
            {
                "sessions": [],
                "current_session": None,
                "messages": [],
                "error": str(e),
                "analysis_id": analysis_id,
                "user": user
            }
        )

@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(
    request: Request,
    session_id: int,
    access_token: str = Cookie(None)
):
    """Proxy endpoint: Forward message request to backend."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_API}/api/chat/sessions/{session_id}/messages",
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch messages from backend"
            )
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/new", response_class=HTMLResponse)
async def create_new_chat(
    request: Request,
    analysis_id: Optional[int] = Form(None),
    access_token: str = Cookie(None)
):
    """Create a new chat session and redirect."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_API}/api/chat/sessions/new",
                headers=await get_headers(access_token),
                params={"analysis_id": analysis_id} if analysis_id else {}
            )
        
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data.get("id")
            # Redirect to chat with new session_id
            redirect_url = f"/chat?session_id={session_id}"
            if analysis_id:
                redirect_url += f"&analysis_id={analysis_id}"
            return RedirectResponse(url=redirect_url, status_code=303)
        else:
            error = response.json().get("detail", "Failed to create session")
            return RedirectResponse(url=f"/chat?error={error}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/chat?error={str(e)}", status_code=303)


@app.post("/api/chat/send", response_class=HTMLResponse)
async def send_chat_message(
    request: Request,
    message: str = Form(...),
    session_id: int = Form(...),
    analysis_id: Optional[int] = Form(None),
    access_token: str = Cookie(None)
):
    """Send a chat message and return updated messages in the same session."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        async with httpx.AsyncClient() as client:
            # 🚀 STEP 1: Send message to backend
            response = await client.post(
                f"{BACKEND_API}/api/chat/message",
                json={
                    "message": message,
                    "session_id": session_id,
                    "analysis_id": analysis_id
                },
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 200:
            # 🔄 STEP 2: Fetch updated messages from THIS session
            async with httpx.AsyncClient() as client:
                history_response = await client.get(
                    f"{BACKEND_API}/api/chat/sessions/{session_id}/messages",
                    headers=await get_headers(access_token)
                )
            
            messages = history_response.json() if history_response.status_code == 200 else []
            
            # 🔄 STEP 3: Also fetch all sessions (for sidebar update)
            async with httpx.AsyncClient() as client:
                sessions_response = await client.get(
                    f"{BACKEND_API}/api/chat/sessions",
                    headers=await get_headers(access_token),
                    params={"analysis_id": analysis_id} if analysis_id else {}
                )
            
            sessions = sessions_response.json() if sessions_response.status_code == 200 else []
            current_session = next((s for s in sessions if s["id"] == session_id), None)
            
            user = json.loads(request.cookies.get("user", "{}"))
            
            redirect_url = f"/chat?session_id={session_id}"
            if analysis_id:
                redirect_url += f"&analysis_id={analysis_id}"

            return templates.TemplateResponse(
                request,
                "chat.html",
                {
                    "sessions": sessions,
                    "current_session": current_session,
                    "messages": messages,
                    "analysis_id": analysis_id,
                    "user": user
                }
            )
        else:
            error = response.json().get("detail", "Failed to send message")
            user = json.loads(request.cookies.get("user", "{}"))
            return templates.TemplateResponse(
                request,
                "chat.html",
                {
                    "error": error,
                    "session_id": session_id,
                    "analysis_id": analysis_id,
                    "user": user
                }
            )
    except Exception as e:
        logger.error(f"Chat send error: {e}", exc_info=True)
        user = json.loads(request.cookies.get("user", "{}"))
        return templates.TemplateResponse(
            request,
            "chat.html",
            {
                "error": str(e),
                "session_id": session_id,
                "analysis_id": analysis_id,
                "user": user
            }
        )

#ADD THIS NEW ENDPOINT HERE
@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(
    request: Request,
    session_id: int,
    access_token: str = Cookie(None)
):
    """Proxy endpoint: Forward message request to backend."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_API}/api/chat/sessions/{session_id}/messages",
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to fetch messages from backend"
            )
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(
    request: Request,
    session_id: int,
    access_token: str = Cookie(None)
):
    """Delete a chat session via API."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{BACKEND_API}/api/chat/sessions/{session_id}",
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 200:
            return {"message": "Session deleted"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete session")
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logout")
async def logout():
    """Logout user."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("user")
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)