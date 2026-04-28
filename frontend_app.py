from fastapi import FastAPI, Request, HTTPException, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import json
from pathlib import Path
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

BACKEND_API = "http://localhost:8000"
#BACKEND_API = "http://192.168.1.15:8000"

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


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    analysis_id: int = None,
    access_token: str = Cookie(None)
):
    """Chat interface."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Fetch chat history
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BACKEND_API}/api/chat/history",
                headers=await get_headers(access_token),
                params={"analysis_id": analysis_id, "limit": 50}
            )
        
        messages = response.json() if response.status_code == 200 else []
        user = json.loads(request.cookies.get("user", "{}"))  # ADDED
        
        return templates.TemplateResponse(
            request,
            "chat.html",
            {"messages": messages, "analysis_id": analysis_id, "user": user}  # ADDED user
        )
    except Exception as e:
        user = json.loads(request.cookies.get("user", "{}"))  # ADDED
        return templates.TemplateResponse(
            request,
            "chat.html",
            {"messages": [], "error": str(e), "analysis_id": analysis_id, "user": user}  # ADDED user
        )


@app.post("/api/chat/send", response_class=HTMLResponse)
async def send_chat_message(
    request: Request,
    message: str = Form(...),
    analysis_id: int = Form(None),
    access_token: str = Cookie(None)
):
    """Send a chat message and return updated messages."""
    if not access_token:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Send message to backend
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_API}/api/chat/message",
                json={"message": message, "analysis_id": analysis_id},
                headers=await get_headers(access_token)
            )
        
        if response.status_code == 200:
            # Fetch updated history
            async with httpx.AsyncClient() as client:
                history_response = await client.get(
                    f"{BACKEND_API}/api/chat/history",
                    headers=await get_headers(access_token),
                    params={"analysis_id": analysis_id, "limit": 50}
                )
            
            messages = history_response.json() if history_response.status_code == 200 else []
            
            return templates.TemplateResponse(
                request,
                "chat.html",
                {"messages": messages, "analysis_id": analysis_id}
            )
        else:
            error = response.json().get("detail", "Failed to send message")
            return templates.TemplateResponse(
                request,
                "chat.html",
                {"error": error, "analysis_id": analysis_id}
            )
    except Exception as e:
        return templates.TemplateResponse(
            request,
            "chat.html",
            {"error": str(e), "analysis_id": analysis_id}
        )


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