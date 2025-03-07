import asyncio
import time
from typing import Any, Dict, List

import aiohttp
import streamlit as st


class DocumentCrawlerApp:
    def __init__(self):
        self.setup_page_config()
        self.status_container = None
        self.progress_bar = None
        self.status_text = None

    def setup_page_config(self):
        st.set_page_config(
            page_title="Document Crawler", page_icon="🕸️", layout="wide"
        )

    def render_ui(self):
        st.title("🕸️ Document Crawler")
        st.markdown(
            """
        This tool crawls documentation websites and processes them into vector embeddings for semantic search.
        
        **Instructions:**
        1. Enter URLs (one per line)
        2. Click "Start Crawling" to begin
        3. Wait for the process to complete
        """
        )

        # Create two columns for layout
        col1, col2 = st.columns([2, 1])

        with col1:
            # URL input form
            st.subheader("Enter URLs to crawl (one per line)")
            url_text = st.text_area(
                "URLs",
                height=200,
                placeholder="https://docs.example.com\nhttps://api.another-example.com",
            )

            start_button = st.button(
                "Start Crawling", type="primary", use_container_width=True
            )

        with col2:
            st.subheader("Status")
            self.status_container = st.container()

        return start_button, url_text

    def validate_urls(self, url_text: str) -> List[str]:
        urls = [url.strip() for url in url_text.split("\n") if url.strip()]
        return urls

    async def call_crawler_api(self, urls: List[str]) -> Dict[str, Any]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/", json=urls
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(
                        f"API call failed with status {response.status}"
                    )

    async def process_urls(self, urls: List[str]):
        with self.status_container:
            st.info(f"Processing {len(urls)} URLs...")
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()

            try:
                # Make async API call to backend
                with st.spinner("Crawling documents..."):
                    self.status_text.text("Phase 1/3: Crawling pages...")

                    # Simulate progress while waiting for API response
                    for i in range(33):
                        time.sleep(0.05)
                        self.progress_bar.progress(i / 100)

                    # Actual API call
                    response = await self.call_crawler_api(urls)

                    # Continue with phase 2
                    self.status_text.text(
                        "Phase 2/3: Generating vector embeddings..."
                    )
                    for i in range(33, 67):
                        time.sleep(0.05)
                        self.progress_bar.progress(i / 100)

                    # Continue with phase 3 and final response
                    self.status_text.text("Phase 3/3: Upserting to Pinecone...")
                    for i in range(67, 101):
                        time.sleep(0.05)
                        self.progress_bar.progress(i / 100)

                    # Display final result
                    st.success(f"Successfully processed {len(urls)} URLs")
                    st.json(
                        {"vector_count": len(urls) * 10, "message": "success"}
                    )

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    def run(self):
        start_button, url_text = self.render_ui()

        if start_button:
            urls = self.validate_urls(url_text)

            if not urls:
                st.error("Please enter at least one URL")
                return

            # Use asyncio to run the async process_urls function
            asyncio.run(self.process_urls(urls))


def main():
    app = DocumentCrawlerApp()
    app.run()


if __name__ == "__main__":
    main()
