import httpx
from utils import config
try:
    import tomllib  # Python 3.11+
except ImportError:
    import toml as tomllib  # fallback for older Python

CONFIG_PATH = config.get_tools()

with open(CONFIG_PATH, "rb") as f:
    config = tomllib.load(f)

# tools will already be a list of dicts from [[tools]] blocks
TOOLS = {tool["name"]: tool for tool in config["tools"]}

async def execute_tool(tool_name: str, args: dict):
    if tool_name not in TOOLS:
        return {"error": f"Unknown tool {tool_name}"}

    tool = TOOLS[tool_name]
    url = f"{config.EXTERNAL_SERVICE_URL}{tool['endpoint']}"

    async with httpx.AsyncClient() as client:
        if tool["method"].upper() == "POST":
            res = await client.post(url, json=args)
        elif tool["method"].upper() == "GET":
            res = await client.get(url, params=args)
        else:
            return {"error": "Unsupported method"}
    
    return res.json()
