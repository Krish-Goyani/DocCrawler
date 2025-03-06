filter_prompt = """
###TASK###
You will be given a list of URLs that need to be scraped. However, some URLs (such as login, signup, support, external urls and similar non-relevant pages) should be excluded from the scraping process.
###CONTEXT###
The goal is to scrape web pages that contain documentation related to SDKs or frameworks for maintaining a vector database. Any pages that do not contribute meaningful information to this purpose should be excluded.
###INSTRUCTIONS###
-Retain URLs that contain relevant documentation or technical information about SDKs and frameworks for vector databases.
-Exclude URLs that are clearly unrelated, such as authentication pages (e.g., login, signup), support pages, or general account settings.
-Do not exclude any URLs unless you are 100% certain that they do not contribute to the task.
-Ensure that no critical links are mistakenly removed.
-Also Exclude urls that redirect to documentation in some different languages. I only want pages that are in English.
-Also Filter if there are repeating hyperlinks linking to same page.
-If the URL has # there is high probability that its a hyperlink.
-Also filter out repeating URLs, the output should not contain any repeating URLs.
-You can assume that the URLs are valid and well-formed.
###EXAMPLE###
INPUT:
[
    "https://docs.pinecone.io/",
    "https://status.pinecone.io",
    "https://app.pinecone.io/organizations/-/settings/support",
    "https://app.pinecone.io/?sessionType=login",
    "https://app.pinecone.io/?sessionType=signup",
    "https://docs.pinecone.io/guides/get-started/overview",
    "https://docs.pinecone.io/reference/api/introduction",
    "https://ai.google.dev/gemini-api/docs/migrate#json_response",
    "https://ai.google.dev/gemini-api/docs/migrate#search_grounding",
    "https://docs.pinecone.io/reference/api/introduction",
    "https://docs.pinecone.io/reference/api/introduction",
    "https://docs.pinecone.io/",

    
]
OUTPUT:
[
    "https://docs.pinecone.io/",
    "https://status.pinecone.io",
    "https://docs.pinecone.io/guides/get-started/overview",
    "https://docs.pinecone.io/reference/api/introduction",
    "https://ai.google.dev/gemini-api/docs/migrate"
]
"""