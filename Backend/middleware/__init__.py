
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .exception_handling import add_exception_handlers
from .success_response import SuccessResponseMiddleware
from utils import config

def middleware(app: FastAPI):
	# Skip CORS middleware - handled in main.py

	app.add_middleware(
		CORSMiddleware,
		allow_origins=config.ALLOWED_ORIGINS,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)
	
	# Temporarily disable SuccessResponse middleware to fix Content-Length issue
	# app.add_middleware(SuccessResponseMiddleware)
	
	# Add global exception handlers
	add_exception_handlers(app)
