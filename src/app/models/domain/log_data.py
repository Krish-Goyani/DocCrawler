class LogData:
    def __init__(
        self,
        timestamp: float,
        request_count: int,
        input_tokens: int,
        output_tokens: int,
        total_input_tokens: int,
        total_output_tokens: int,
        time_taken: float,
        request_type: str,
    ):
        self.timestamp: float = timestamp
        self.request_count: int = request_count
        self.input_tokens: int = input_tokens
        self.output_tokens: int = output_tokens
        self.total_input_tokens: int = total_input_tokens
        self.total_output_tokens: int = total_output_tokens
        self.time_taken: float = time_taken
        self.request_type: str = request_type

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "request_count": self.request_count,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "time_taken": self.time_taken,
            "request_type": self.request_type,
        }




