class Error:
    def __init__(self, user_id: str, error_message: str):
        self.user_id: str = user_id
        self.error_message: str = error_message

    def to_dict(self):
        return {"user_id": self.user_id, "error_message": self.error_message}
