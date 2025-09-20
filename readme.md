# MediBot

A sophisticated medical chatbot powered by a multi-agent RAG (Retrieval-Augmented Generation) architecture using LangGraph and FastAPI. MediBot intelligently routes queries to specialized agents for handling medical information, operational tasks, and general inquiries.

## 🏗️ Architecture

MediBot uses a multi-agent system built with LangGraph that routes user queries through specialized agents:

### Agent Flow
```
User Query → Supervisor Agent → [Vector DB Agent | Tools Agent | Fallback Agent] → Response Agent → User
```

### Agents
- **Supervisor Agent**: Main routing agent that analyzes queries and directs them to appropriate specialized agents
- **Vector DB Agent**: Handles queries about hospital details, doctor information, and medical services
- **Tools Agent**: Processes operational queries (fetch, post, delete operations)
- **Fallback Agent**: Manages out-of-domain or unclear queries with helpful guidance
- **Response Agent**: Formats final responses in a user-friendly manner

## 🚀 Features

- **Intelligent Query Routing**: Automatically routes medical queries to the most appropriate agent
- **Conversation History**: Maintains context across conversations for better responses
- **RESTful API**: FastAPI-based backend with comprehensive error handling
- **Configurable LLM**: Supports multiple LLM providers (default: OpenAI GPT-4o-mini)
- **Docker Support**: Containerized deployment ready
- **Medical Domain Focus**: Specialized for healthcare-related queries and operations

## 📁 Project Structure

```
MediBot/
├── Backend/
│   ├── controller/
│   │   └── conversation_controller.py    # Main conversation logic
│   ├── middleware/
│   │   ├── LLM_Middleware.py            # LLM integration middleware
│   │   ├── exception_handling.py        # Error handling
│   │   └── success_response.py          # Response formatting
│   ├── prompts/
│   │   ├── agent_prompt.poml            # Agent definitions and prompts
│   │   └── tools.poml                   # Tool configurations
│   ├── rag_flow/
│   │   ├── Agents/
│   │   │   ├── dynamic_agent.py         # Dynamic agent implementation
│   │   │   └── router_agent.py          # Routing logic
│   │   └── graphs.py                    # LangGraph workflow definition
│   ├── router/
│   │   └── conversation_router.py       # API routes
│   ├── Schema/
│   │   ├── conversation_schema.py       # Pydantic models
│   │   └── source_dir_schema.py         # Additional schemas
│   ├── utils/
│   │   ├── config.py                    # Configuration management
│   │   ├── handling_response.py         # Response utilities
│   │   ├── logger.py                    # Logging setup
│   │   └── tools.py                     # Tool definitions
│   ├── config.yaml                      # Main configuration file
│   ├── main.py                          # FastAPI application entry point
│   ├── requirements.txt                 # Python dependencies
│   └── Dockerfile                       # Container configuration
├── Frontend/                            # (Frontend components - to be implemented)
└── README.md
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+
- OpenAI API key (or other LLM provider credentials)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd MediBot
```

### 2. Environment Setup
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key_here
BACKEND_HOST=localhost
BACKEND_PORT=8000
```

### 3. Install Dependencies
```bash
cd Backend
pip install -r requirements.txt
```

### 4. Configuration
The system uses `config.yaml` for LLM and tool configurations. Default settings:
- **Model**: GPT-4o-mini
- **Provider**: OpenAI
- **Temperature**: 0.2

### 5. Run the Application
```bash
# Development mode
python main.py

# Or using uvicorn directly
uvicorn main:app --host localhost --port 8000 --reload
```

### 6. Docker Deployment (Optional)
```bash
docker build -t medibot .
docker run -p 8000:8000 medibot
```

## 🔌 API Documentation

### Base URL
```
http://localhost:8000
```

### Endpoints

#### POST `/`
Chat with the MediBot

**Request Body:**
```json
{
  "conversation_history": [
    {
      "role": "user",
      "content": "Previous message"
    },
    {
      "role": "assistant", 
      "content": "Previous response"
    }
  ],
  "query": "Tell me about cardiology services"
}
```

**Response:**
```json
{
  "type": "message",
  "data": "Cardiology services information..."
}
```

**Schema Models:**
- `ConversationEntry`: Individual conversation message
  - `role`: string (user/assistant)
  - `content`: string
- `ConversationHistoryPayload`: Complete request payload
  - `conversation_history`: List[ConversationEntry]
  - `query`: string

## 🤖 Agent Configuration

Agents are defined in `prompts/agent_prompt.poml` using TOML format:

```toml
[[agents]]
name = "supervisor_agent"
role = "Supervisor"
description = "Main routing agent..."
prompt = "You are a supervisor routing agent..."
```

### Available Tools
Configured in `config.yaml`:
- `create_appointment`: Book new appointments
- `list_appointments`: Retrieve appointment lists

## 🧪 Usage Examples

### Medical Information Query
```bash
curl -X POST "http://localhost:8000/" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_history": [],
    "query": "What cardiology services do you offer?"
  }'
```

### Appointment Booking
```bash
curl -X POST "http://localhost:8000/" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_history": [],
    "query": "I want to book an appointment with a cardiologist for next Monday"
  }'
```

### General Query
```bash
curl -X POST "http://localhost:8000/" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_history": [],
    "query": "What is the weather like today?"
  }'
```

## 🔧 Development

### Key Dependencies
- **FastAPI**: Web framework
- **LangGraph**: Multi-agent workflow orchestration
- **LangChain**: LLM integration
- **LiteLLM**: Multi-provider LLM support
- **Pydantic**: Data validation
- **PyYAML**: Configuration management

### Adding New Agents
1. Define the agent in `prompts/agent_prompt.poml`
2. Update the routing logic in the supervisor agent
3. Implement agent-specific logic if needed

### Adding New Tools
1. Define tools in `config.yaml`
2. Implement tool functions in `utils/tools.py`
3. Update agent prompts to reference new tools

## 🚦 Middleware & Error Handling

- **Success Response Middleware**: Standardizes successful responses
- **Exception Handling**: Comprehensive error catching and formatting
- **LLM Middleware**: Manages LLM provider interactions

## 📝 Logging

Structured logging is implemented throughout the application for debugging and monitoring purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
- Create an issue in the repository
- Check the logs for detailed error information
- Verify your environment configuration

---

**Note**: This project is designed specifically for medical domain queries. For best results, frame your questions in a medical context.
