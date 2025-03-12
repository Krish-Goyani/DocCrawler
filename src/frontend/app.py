import asyncio
import time
from typing import Any, Dict, List

import aiohttp
import streamlit as st


class DocumentCrawlerApp:
    """A Streamlit application for crawling, indexing, and searching documentation websites."""

    def __init__(self):
        """Initialize the application and setup page configuration."""
        self.setup_page_config()
        self.status_container = None
        self.progress_bar = None
        self.status_text = None

    def setup_page_config(self):
        """Configure the Streamlit page settings."""
        st.set_page_config(
            page_title="Document Crawler",
            page_icon=":spider_web:",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    def render_ui(self):
        """Render the user interface with all input fields and status elements."""
        # Header with custom styling
        st.markdown(
            """
            <div style='text-align: center; background-color: #f0f2f6; padding: 1rem; border-radius: 10px; margin-bottom: 2rem;'>
                <h1 style='color: #1E3A8A;'>🕸️ Document Crawler</h1>
                <p style='font-size: 1.2rem;'>Semantic search for documentation websites</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Introduction and instructions
        st.markdown(
            """
            This tool crawls documentation websites and processes them into vector embeddings for semantic search.
            
            ### Instructions:
            1. Enter the URLs you want to crawl (one per line)
            2. Click "Start Crawling" to begin processing
            3. Configure your search parameters and query the indexed documents
            """
        )

        # Main layout with tabs
        tab1, tab2 = st.tabs(["Crawl Documents", "Search Documents"])

        # Crawl Documents Tab
        with tab1:
            st.subheader("URLs to Crawl")
            url_text = st.text_area(
                "Enter URLs (one per line)",
                height=200,
                placeholder="https://docs.example.com\nhttps://api.another-example.com",
                help="Each URL should be on a separate line. The crawler will index all pages it can find starting from these URLs.",
            )
            start_button = st.button(
                "🚀 Start Crawling", type="primary", use_container_width=True
            )

            st.subheader("Status")
            self.status_container = st.container()

        # Search Documents Tab
        with tab2:
            st.subheader("Query Configuration")

            # Search query input
            query = st.text_input(
                "Enter your query",
                placeholder="Enter your query..",
                help="Enter your search query in natural language",
            )

            col1, col2 = st.columns(2)
            with col1:
                alpha = st.slider(
                    "Hybrid Search Alpha",
                    0.0,
                    1.0,
                    0.5,
                    0.1,
                    help="Balance between sparse (0) and dense (1) retrieval",
                )

            with col2:
                top_k = st.number_input(
                    "Top K Results",
                    min_value=1,
                    max_value=100,
                    value=10,
                    help="Number of results to return",
                )

            # Advanced filters in an expandable section
            with st.expander("Metadata Filters"):
                with st.form("metadata_form"):
                    st.subheader("Metadata Filtering")

                    col1, col2 = st.columns(2)
                    with col1:
                        sdk_framework_name = st.text_input(
                            "SDK/Framework Name",
                            help="Filter by specific SDK or framework name",
                        )
                        sdk_framework = st.selectbox(
                            "Type",
                            ["Not Specified", "SDK", "Framework"],
                            index=0,
                        )
                        category = st.text_input(
                            "Category", help="Filter by document category"
                        )

                    with col2:
                        base_url = st.text_input(
                            "Base URL", help="Filter by document source URL"
                        )
                        version = st.text_input(
                            "Version", help="Filter by specific version"
                        )
                        has_code_snippet = st.selectbox(
                            "Has Code Snippet",
                            ["Not Specified", "Yes"],
                            index=0,
                        )

                    col1, col2 = st.columns(2)
                    with col1:
                        top_n = st.number_input(
                            "Top N Documents",
                            min_value=1,
                            max_value=100,
                            value=5,
                            help="Number of documents to retrieve per query",
                        )

                    with col2:
                        is_summary = st.selectbox(
                            "Is Summary",
                            ["Not Specified","Yes"],  # Convert checkbox to dropdown with "Not Specified"
                            index=0,
                        )

                    query_button = st.form_submit_button("🔍 Submit Query")

            # Add a placeholder for query results in the Search Documents tab
            self.query_results_placeholder = st.empty()

        return (
            start_button,
            url_text,
            query,
            alpha,
            str(sdk_framework_name).lower(),
            base_url,
            str(sdk_framework).lower(),
            str(category).lower(),
            str(has_code_snippet).lower(),
            str(version).lower(),
            query_button,
            top_k,
            top_n,
            str(is_summary).lower(),
        )

    def validate_urls(self, url_text: str) -> List[str]:
        """Validate and extract URLs from the input text."""
        urls = [url.strip() for url in url_text.split("\n") if url.strip()]
        # Basic validation - check if URLs start with http:// or https://
        valid_urls = [
            url for url in urls if url.startswith(("http://", "https://"))
        ]

        if len(valid_urls) < len(urls):
            st.warning(
                f"{len(urls) - len(valid_urls)} URL(s) were invalid and will be skipped."
            )

        return valid_urls

    async def call_crawler_api(self, urls: List[str]) -> Dict[str, Any]:
        """Call the crawler API to process the provided URLs."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/", json=urls
            ) as response:
                if response.status == 200:
                    return await response.json()
                raise Exception(
                    f"API call failed with status {response.status}: {await response.text()}"
                )

    async def call_query_api(
        self, query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call the query API to search indexed documents."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8000/query", json=query_data
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return response_data
                else:
                    error_message = await response.text()
                    st.error(f"Backend error: {error_message}")
                    raise Exception(
                        f"API call failed with status {response.status}: {error_message}"
                    )

    # async def call_query_api(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
    #     """Call the query API to search indexed documents."""
    #     async with httpx.AsyncClient() as client:
    #         response = await client.post("http://localhost:8000/query", json=query_data)
    #         print(response)
    #         if response.status_code == 200:
    #             return response.json()
    #         else:
    #             error_message = response.text
    #             raise Exception(f"API call failed with status {response.status_code}: {error_message}")

    async def process_urls(self, urls: List[str]):
        """Process the provided URLs by crawling and indexing them."""
        with self.status_container:
            st.info(f"Processing {len(urls)} URLs...")
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()

            try:
                with st.spinner("Crawling and processing documents..."):
                    self.status_text.text("Crawling and indexing pages...")

                    # Simulate progress while waiting for the API
                    for i in range(100):
                        time.sleep(0.05)
                        self.progress_bar.progress((i + 1) / 100)

                    # Call the actual API
                    response = await self.call_crawler_api(urls)

                    # Display results
                    st.success(f"Successfully processed {len(urls)} URLs")
                    st.json(response)
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    async def process_query(
        self,
        query: str,
        alpha: float,
        metadata: Dict[str, Any],
        top_k: int,
        top_n: int,
    ):
        """Process a search query with the specified parameters."""
        with self.status_container:
            st.info(f"Processing query: {query}")

            try:
                # Convert has_code_snippet from UI selection to boolean
                if "has_code_snippet" in metadata:
                    if metadata["has_code_snippet"] == "yes":
                        metadata["has_code_snippet"] = "true"
                    else:
                        metadata.pop("has_code_snippet", None)

                if "is_summary" in metadata:
                    if metadata["is_summary"] == "yes":
                        metadata["is_summary"] = "true"
                    else:
                        metadata.pop("is_summary", None)

                # Remove sdk_framework if set to "Not Specified"
                if (
                    "sdk_framework" in metadata
                    and metadata["sdk_framework"] == "Not Specified"
                ):
                    metadata.pop("sdk_framework", None)

                # Remove empty metadata fields
                metadata = {
                    k: v
                    for k, v in metadata.items()
                    if v is not None and v != ""
                }

                # Prepare the query data according to the backend's expected structure
                query_data = {
                    "query": query,
                    "alpha": alpha,
                    "filters": metadata,  # Ensure this matches the backend's expected structure
                    "top_k": top_k,
                    "top_n": top_n,
                }
                # Call the query API
                response = await self.call_query_api(query_data)

                # Display results in the query_results_placeholder
                with self.query_results_placeholder.container():
                    st.success("Query Results:")

                    # Display results in a more readable format
                    if "results" in response and response["results"]:
                        for result in response["results"]:
                            with st.expander(
                                f"Result #{result.get('index', 'N/A') + 1}"
                            ):
                                st.markdown(
                                    f"**Relevance Score:** {result.get('relevance_score', 0):.4f}"
                                )
                                st.markdown("**Document Content:**")
                                st.markdown(
                                    result.get("document", {}).get(
                                        "text", "No content available"
                                    )
                                )
                    else:
                        st.info("No results found.")

                    # Also provide the raw JSON for reference
                    with st.expander("Raw API Response"):
                        st.json(response)

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    def run(self):
        """Run the Streamlit application."""
        # Apply custom CSS
        st.markdown(
            """
            <style>
            .stApp {
                max-width: 1200px;
                margin: 0 auto;
            }
            .stButton button {
                font-weight: bold;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Render UI and get user inputs
        (
            start_button,
            url_text,
            query,
            alpha,
            sdk_framework_name,
            base_url,
            sdk_framework,
            category,
            has_code_snippet,
            version,
            query_button,
            top_k,
            top_n,
            is_summary,
        ) = self.render_ui()

        # Handle the crawl button
        if start_button:
            urls = self.validate_urls(url_text)
            if not urls:
                st.error("Please enter at least one valid URL")
                return
            asyncio.run(self.process_urls(urls))

        # Handle the query button
        if query_button:
            if not query:
                st.error("Please enter a query")
                return

            metadata = {
                "SDK_Framework_name": sdk_framework_name,
                "base_url": base_url,
                "sdk_framework": sdk_framework,
                "category": category,
                "has_code_snippet": has_code_snippet,
                "version": version,
                "is_summary": is_summary,
            }
            asyncio.run(
                self.process_query(query, alpha, metadata, top_k, top_n)
            )


def main():
    """Application entry point."""
    app = DocumentCrawlerApp()
    app.run()


if __name__ == "__main__":
    main()
