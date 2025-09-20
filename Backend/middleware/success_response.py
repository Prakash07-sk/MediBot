from utils.handling_response import SuccessResponse

class SuccessResponseMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Store messages to process them together
        messages = []
        start_message = [None]  # Use list to make it mutable in nested function
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                start_message[0] = message
                # Don't send immediately, store it
                return
            elif message["type"] == "http.response.body":
                messages.append(message)
                
                # Process all messages together
                if start_message[0]:
                    import json
                    try:
                        # Process the body message
                        body_message = messages[-1]
                        body = json.loads(body_message["body"].decode())
                        
                        # Only wrap if not already in success/error format
                        if (
                            isinstance(body, dict)
                            and ("success" not in body)
                            and start_message[0]["status"] < 400
                        ):
                            wrapped = SuccessResponse(data=body).dict()
                            new_body = json.dumps(wrapped).encode()
                            
                            # Update the start message with correct Content-Length
                            headers = dict(start_message[0].get("headers", []))
                            if "content-length" in headers:
                                headers["content-length"] = str(len(new_body))
                            
                            # Send updated start message
                            updated_start_message = {
                                **start_message[0],
                                "headers": [(k.encode(), v.encode()) for k, v in headers.items()]
                            }
                            await send(updated_start_message)
                            
                            # Send updated body message
                            updated_body_message = {
                                **body_message,
                                "body": new_body
                            }
                            await send(updated_body_message)
                            return
                            
                    except Exception:
                        pass
                    
                    # If no wrapping needed or error occurred, send original messages
                    await send(start_message[0])
                
                # Send the body message
                await send(messages[-1])

        await self.app(scope, receive, send_wrapper)
