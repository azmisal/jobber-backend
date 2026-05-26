from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, resume, optimize
from contextlib import asynccontextmanager 
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*50)
    print("🚀 NEXUS CV BACKEND ENGINE IS ONLINE!")
    print("📡 Listening at: http://127.0.0.1:8000")
    print("="*50 + "\n")
    yield
    print("\n🛑 Shutting down server engine...")


app = FastAPI(title="ATS Keyword Tailoring Engine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach Modular Application Router Engines
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(optimize.router)

@app.get("/")
def health_status():
    return {"status": "Online", "msg": "API Layer Live"}