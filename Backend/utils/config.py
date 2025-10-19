

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
		# Automatically detect if running in Docker or locally
		chromadb_host = os.getenv('CHROMADB_HOST', 'localhost')
		chromadb_port_env = os.getenv('CHROMADB_PORT', None)
		
		# If CHROMADB_PORT is not set, determine based on host
		if chromadb_port_env is None:
			# If connecting to localhost, use external port (5001)
			# If connecting to chromadb_server, use internal port (5000)
			if chromadb_host == 'localhost':
				self.CHROMADB_PORT = 5001  # External port for local development
			else:
				self.CHROMADB_PORT = 5000  # Internal port for Docker networking
		else:
			self.CHROMADB_PORT = int(chromadb_port_env)
		
		self.CHROMADB_HOST = chromadb_host
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

