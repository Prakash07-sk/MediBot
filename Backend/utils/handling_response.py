class SuccessResponse:
    def __init__(self, data=None, message="Request processed successfully"):
        self.success = True
        self.message = message
        self.data = data

    def dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data
        }

class ErrorResponse:
    def __init__(self, errors=None, message="Validation failed"):
        self.success = False
        self.message = message
        self.errors = errors

    def dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "errors": self.errors
        }
