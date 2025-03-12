import json
import aiofiles
import os
import uuid
from src.app.config.settings import settings

class BatchAPIUtils:
    async def create_jsonl_file(self, file_path, user_id, chunk_prompt):
        # Define folder structure
        base_folder = "batch_api"
        user_folder = os.path.join(base_folder, str(user_id))
        
        # Ensure directories exist
        os.makedirs(user_folder, exist_ok=True)
        
        # Get existing files to determine the next available index
        existing_files = [f for f in os.listdir(user_folder) if f.endswith(".jsonl")]
        existing_indices = [int(f.split(".")[0]) for f in existing_files if f.split(".")[0].isdigit()]
        next_index = max(existing_indices, default=0) + 1
        
        # Determine the target file (either an existing file or a new one)
        jsonl_file_path = os.path.join(user_folder, f"{next_index}.jsonl")
        if existing_files:
            latest_file = os.path.join(user_folder, f"{max(existing_indices)}.jsonl")
            file_size = os.path.getsize(latest_file) / (1024 * 1024)  # Convert bytes to MB
            line_count = sum(1 for _ in open(latest_file, "r", encoding="utf-8"))
            
            # Check size and line limit
            if file_size < 200 and line_count < 50000:
                jsonl_file_path = latest_file
        
        async with aiofiles.open(file_path, "r") as file:
            data = json.loads(await file.read())
        
        async with aiofiles.open(jsonl_file_path, "a") as jsonl_file:
            for index, item in enumerate(data):
                request_data = {
                    "custom_id": f"{user_id}_{uuid.uuid4().hex}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": settings.OPENAI_MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": f"{chunk_prompt}\n**INPUT:**\n{item}\n**OUTPUT:**"}
                        ]
                    }
                }
                await jsonl_file.write(json.dumps(request_data) + "\n")
        
        return jsonl_file_path