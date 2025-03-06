import asyncio
import json
import re
import time
import openai
from config.clients import Clients


def extract_hrefs(json_data):
    hrefs = []
    for entry in json_data:
        href = entry.get("href", "")
        hrefs.append(href)
    return hrefs


def fetch_content(json_data, hrefs):
    content_dict = {}
    for entry in json_data:
        href = entry.get("href", "")
        if href in hrefs:
            content = entry.get("content", "")
            content_dict[href] = content
    return content_dict


async def chunk_with_gpt(text, chunk_semaphore):

    async with chunk_semaphore:
        try:
            start_time = time.time()
            try:
                client = Clients.get_openai_client()
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": text}],
                        temperature=0,
                    ),
                    timeout=90,
                )
            except asyncio.TimeoutError:
                return None
            end_time = time.time()
        except openai.OpenAIError as e:
            print(f"OpenAI API Error: {e}")
            return None

        chunk_llm_request_count += 1
        usage = getattr(response, "usage", None)
        if not usage:
            return None

        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens
        chunk_total_input_tokens += input_tokens
        chunk_total_output_tokens += output_tokens

        # Prepare and write log data.
        log_data = {
            "llm_request_count": chunk_llm_request_count,
            "total_input_tokens": chunk_total_input_tokens,
            "total_output_tokens": chunk_total_output_tokens,
            "start_time": start_time,
            "end_time": end_time,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "time_taken": end_time - start_time,
        }

        output_text = response.choices[0].message.content.strip()
        chunks = extract_json_list(output_text)

        return chunks


def extract_json_list(text):
    # Regex to extract the JSON list from the response text.
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))  # Convert string to a Python list
        except json.JSONDecodeError:
            return None  # Handle invalid JSON cases
    return None


async def filter_summary_links(text):
    try:
        start_time = time.time()
        try:
            client = Clients.get_openai_client()
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": text}],
                    temperature=0,
                ),
                timeout=90,
            )
        except asyncio.TimeoutError:
            return None
        end_time = time.time()
    except openai.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return None

    chunk_llm_request_count += 1
    usage = getattr(response, "usage", None)
    if not usage:
        return None

    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens
    chunk_total_input_tokens += input_tokens
    chunk_total_output_tokens += output_tokens

    # Prepare and write log data.
    log_data = {
        "llm_request_count": chunk_llm_request_count,
        "total_input_tokens": chunk_total_input_tokens,
        "total_output_tokens": chunk_total_output_tokens,
        "start_time": start_time,
        "end_time": end_time,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "time_taken": end_time - start_time,
    }


    output_text = response.choices[0].message.content.strip()
    filtered_links = extract_json_list(output_text)

    return filtered_links


async def generate_summary_chunk(text):
    global chunk_llm_request_count, chunk_total_input_tokens, chunk_total_output_tokens
    try:
        start_time = time.time()
        try:
            client = Clients.get_openai_client()
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": text}],
                    temperature=0,
                ),
                timeout=900,
            )
        except asyncio.TimeoutError:
            return None
        end_time = time.time()
    except openai.OpenAIError as e:
        print(f"OpenAI API Error: {e}")
        return None

    chunk_llm_request_count += 1
    usage = getattr(response, "usage", None)
    if not usage:
        return None

    input_tokens = usage.prompt_tokens
    output_tokens = usage.completion_tokens
    chunk_total_input_tokens += input_tokens
    chunk_total_output_tokens += output_tokens

    # Prepare and write log data.
    log_data = {
        "llm_request_count": chunk_llm_request_count,
        "total_input_tokens": chunk_total_input_tokens,
        "total_output_tokens": chunk_total_output_tokens,
        "start_time": start_time,
        "end_time": end_time,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "time_taken": end_time - start_time,
    }

    output_text = response.choices[0].message.content.strip()
    chunks = extract_json_list(output_text)

    return chunks
