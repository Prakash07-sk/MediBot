

import os
from dotenv import load_dotenv

class Config:
	def __init__(self):
		# Load .env file from the project root
		load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
		# Backend config
		self.BACKEND_HOST = os.getenv('BACKEND_HOST', '0.0.0.0')
		self.BACKEND_PORT = int(os.getenv('BACKEND_PORT', 4000))
		self.BACKEND_API_ENDPOINT = os.getenv('BACKEND_API_ENDPOINT', '/api')

		# LLM config
		self.LLM_SERVER_MODEL = os.getenv('LLM_SERVER_MODEL', 'gpt-4o-mini')
		self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
		
		# Allowed origins for CORS
		allowed_origins_env = os.getenv('ALLOWED_ORIGINS', '')
		self.ALLOWED_ORIGINS = [origin.strip() for origin in allowed_origins_env.split('.') if origin.strip()] if allowed_origins_env else []

		# External service config
		self.EXTERNAL_SERVICE_URL = os.getenv('EXTERNAL_SERVICE_URL', 'localhost')

		# ChromaDB config
		self.CHROMADB_HOST = os.getenv('CHROMADB_HOST', 'localhost')  # Default to localhost for local development
		self.CHROMADB_PORT = int(os.getenv('CHROMADB_EXTERNAL_PORT', 5001))  # Default to 5001 to match docker-compose mapping
		self.CHROMADB_USER = os.getenv('CHROMADB_USER', 'admin')

		# MCP Server config
		self.MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:3000')

	def get_tools(self):
		return os.path.join(os.path.dirname(__file__), '../prompts/tools.poml')
	
	def get_agent_prompt(self):
		return os.path.join(os.path.dirname(__file__), '../prompts/agent_prompt.poml')
	
	def get_response_agent_prompt(self):
		return """"
			
		"""
		
# Export a single config object
config = Config()

