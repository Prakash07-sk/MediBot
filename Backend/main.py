from fastapi import FastAPI
import uvicorn

from controller import *
from middleware import middleware
from middleware.success_response import SuccessResponseMiddleware
from utils import *
from utils import config

from router import router as main_router

app = FastAPI()

# Add SuccessResponse middleware
app.add_middleware(SuccessResponseMiddleware)

# Add all other middleware (Exception Handlers, etc.)
middleware(app)

# Include the router from the router folder
app.include_router(main_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.BACKEND_HOST, port=config.BACKEND_PORT, reload=True)
