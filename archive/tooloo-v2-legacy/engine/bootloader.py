# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.bootloader.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import asyncio
import httpx
import logging
import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin
from typing import List, Set, Dict, Any
from engine.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# The Enhanced SOTA Target Matrix (Roots & Sitemaps)
SOTA_TARGET_MATRIX = {
    "openai": {
        "roots": ["https://academy.openai.com/", "https://cookbook.openai.com/", "https://github.com/openai/openai-python"],
        "sitemaps": ["https://platform.openai.com/docs/sitemap.xml"],
        "whitelist": ["platform.openai.com/docs", "academy.openai.com", "cookbook.openai.com", "github.com/openai"]
    },
    "anthropic": {
        "roots": ["https://www.anthropic.com/learn", "https://github.com/anthropics/anthropic-sdk-python"],
        "sitemaps": ["https://docs.anthropic.com/en/sitemap.xml"],
        "whitelist": ["docs.anthropic.com", "anthropic.com/learn", "github.com/anthropics"]
    },
    "google": {
        "roots": ["https://startup.google.com/programs/ai-academy/", "https://github.com/google-gemini/generative-ai-python"],
        "sitemaps": ["https://ai.google.dev/sitemap.xml", "https://cloud.google.com/vertex-ai/docs/sitemap.xml"],
        "whitelist": ["ai.google.dev", "cloud.google.com/vertex-ai", "startup.google.com", "github.com/google-gemini"]
    },
    "meta": {
        "roots": ["https://ai.meta.com/research/", "https://github.com/meta-llama/llama-stack"],
        "sitemaps": ["https://llama.meta.com/docs/sitemap.xml"],
        "whitelist": ["llama.meta.com/docs", "ai.meta.com/research", "github.com/meta-llama"]
    },
    "deepseek": {
        "roots": ["https://api-docs.deepseek.com/", "https://github.com/deepseek-ai/DeepSeek-Coder"],
        "whitelist": ["api-docs.deepseek.com", "github.com/deepseek-ai"]
    },
    "vercel": {
        "roots": ["https://github.com/vercel/ai-sdk"],
        "sitemaps": ["https://sdk.vercel.ai/sitemap.xml"],
        "whitelist": ["sdk.vercel.ai/docs", "github.com/vercel/ai-sdk"]
    },
    "langchain": {
        "roots": ["https://github.com/langchain-ai/langchain"],
        "sitemaps": ["https://python.langchain.com/sitemap.xml"],
        "whitelist": ["python.langchain.com/docs", "github.com/langchain-ai"]
    }
}

class SOTABootloader:
    """
    Master Ingestion Engine using Hybrid Protocol: 
    - Sitemaps for precise, high-volume crawling.
    - Shallow Discovery for roots without formal sitemaps.
    - Anti-bot evasion via Jina Reader.
    """

    def __init__(self, concurrency: int = 8):
        from pathlib import Path
        self.jina_base_url = "https://r.jina.ai/"
        self.vector_store = get_vector_store()
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = httpx.AsyncClient(timeout=45.0, follow_redirects=True)
        self.progress_file = Path(__file__).resolve().parents[1] / "psyche_bank" / "ingested_urls.json"
        self.ingested_urls: Set[str] = self._load_progress()

    def _load_progress(self) -> Set[str]:
        import json
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load progress: {e}")
        return set()

    def _save_progress(self):
        import json
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.progress_file, "w") as f:
                json.dump(list(self.ingested_urls), f)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")

    async def _checkpoint(self):
        """Persist both progress and vector store."""
        self._save_progress()
        self.vector_store.save()

    # ── Networking ─────────────────────────────────────────────────────────────

    async def fetch_markdown(self, url: str) -> str | None:
        """Fetch clean markdown via Jina Reader with concurrency throttling."""
        if url in self.ingested_urls:
            return None
        
        async with self.semaphore:
            target_url = f"{self.jina_base_url}{url}"
            try:
                logger.info(f"Ingesting: {url}")
                response = await self.client.get(target_url)
                if response.status_code == 200:
                    self.ingested_urls.add(url)
                    return response.text
                else:
                    logger.error(f"Jina error {response.status_code} for {url}")
                    return None
            except Exception as e:
                logger.error(f"Failed to fetch {url}: {e}")
                return None

    # ── Protocol Logic ─────────────────────────────────────────────────────────

    async def parse_sitemap(self, sitemap_url: str) -> List[str]:
        """Fetch and parse a sitemap.xml to extract URLs."""
        try:
            logger.info(f"Parsing Sitemap: {sitemap_url}")
            response = await self.client.get(sitemap_url)
            if response.status_code != 200:
                return []
            
            root = ET.fromstring(response.content)
            # Handle XML namespaces usually found in sitemaps
            urls = []
            for child in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                urls.append(child.text)
            
            # SOTA Filter: Prioritize 2025/2026 content or core technical paths
            return [u for u in urls if any(p in u for p in ["/docs", "/guides", "/cookbook", "/learn"])]
        except Exception as e:
            logger.error(f"Sitemap parsing failed for {sitemap_url}: {e}")
            return []

    def discover_links(self, markdown: str, base_url: str, whitelist: List[str]) -> List[str]:
        """Extract links from markdown that match the provider's whitelist."""
        # Simple regex for markdown links [text](url)
        found = re.findall(r"\[.*?\]\((https?://.*?)\)", markdown)
        valid = []
        for url in found:
            parsed = urlparse(url)
            # Stay within the provider's domain/sub-path
            if any(w in url for w in whitelist):
                valid.append(url)
        return list(set(valid))

    # ── Main Ingestion Loop ────────────────────────────────────────────────────

    async def ingest_targets(self):
        """Execute the Hybrid Protocol across the Full Provider Matrix."""
        logger.info("Initiating Full SOTA Ingestion Protocol...")
        
        all_urls = []
        
        # Phase 1: Sitemap Acquisition
        for provider, config in SOTA_TARGET_MATRIX.items():
            for sitemap in config.get("sitemaps", []):
                urls = await self.parse_sitemap(sitemap)
                # Cap sitemap URLs to 50 highest-value ones per sitemap to prevent bloat
                all_urls.extend(urls[:50])

        # Phase 2: Root Ingestion & Shallow Discovery
        for provider, config in SOTA_TARGET_MATRIX.items():
            roots = config.get("roots", [])
            whitelist = config.get("whitelist", [])
            
            for root in roots:
                if root in self.ingested_urls:
                    continue
                # Ingest root
                markdown = await self.fetch_markdown(root)
                if markdown:
                    await self._process_markdown(root, markdown)
                    # Shallow Discover (Depth 1)
                    sub_urls = self.discover_links(markdown, root, whitelist)
                    all_urls.extend(sub_urls[:10]) # Cap Discovery
                    await self._checkpoint()

        # Phase 3: Distributed Ingestion of discovered URLs (Sliding Window)
        logger.info(f"Queueing {len(all_urls)} high-fidelity URLs for final vectorization.")
        pending_urls = [u for u in all_urls if u not in self.ingested_urls]
        
        # Process in batches to stay within concurrency limits and checkpoint often
        batch_size = 20
        for i in range(0, len(pending_urls), batch_size):
            batch = pending_urls[i:i+batch_size]
            tasks = [self.fetch_and_process(url) for url in batch]
            await asyncio.gather(*tasks)
            await self._checkpoint()

        logger.info(f"Protocol Complete. Ingested {len(self.ingested_urls)} Master Sites.")
        await self._checkpoint()
        return len(self.ingested_urls)

    async def fetch_and_process(self, url: str):
        markdown = await self.fetch_markdown(url)
        if markdown:
            await self._process_markdown(url, markdown)

    async def _process_markdown(self, url: str, markdown: str):
        """Chunk and store markdown into VectorStore."""
        # Simple recursive character splitter
        chunks = self.chunk_text(markdown)
        for i, chunk in enumerate(chunks):
            doc_id = f"sota_{hash(url)}_{i}"
            await self.vector_store.add(
                doc_id=doc_id,
                text=chunk,
                metadata={"source": url, "type": "sota_academy", "chunk": i}
            )

    def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
        """Pure character-based splitting."""
        if not text: return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                last_space = text.rfind("\n", start, end)
                if last_space == -1: last_space = text.rfind(". ", start, end)
                if last_space != -1 and last_space > start + (chunk_size // 2): end = last_space + 1
            chunks.append(text[start:end].strip())
            start = end - overlap
            if start < 0: start = 0
            if end >= len(text): break
        return chunks

    async def close(self):
        await self.client.aclose()

async def run_bootloader():
    bootloader = SOTABootloader()
    try:
        await bootloader.ingest_targets()
    finally:
        await bootloader.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bootloader())
