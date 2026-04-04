# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: GOOGLE_CLOUD_INGESTER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/governance/ingesters/google_cloud_ingester.py
# WHEN: 2026-04-04T08:00:00.000000
# WHY: Concrete ingestion for Google Cloud/Gemini public learning materials.
# HOW: Async HTTP fetching and parsing of public learning routes.
# TIER: T4:zero-trust
# PURITY: 1.00
# ==========================================================

import httpx
import logging
import re
from typing import Dict, Any, List
from tooloo_v4_hub.kernel.governance.academy_ingester import AcademyIngester

logger = logging.getLogger("GoogleCloudIngester")

class GoogleCloudIngester(AcademyIngester):
    def __init__(self):
        super().__init__(provider_name="GoogleCloud", base_url="https://cloud.google.com/vertex-ai/docs/")

    async def ingest(self) -> List[Dict[str, Any]]:
        items = []
        logger.info(f"GoogleCloudIngester: Starting ingestion from {self.provider_name}")
        
        target_urls = [self.base_url, "https://ai.google.dev/docs"]
        
        async with httpx.AsyncClient() as client:
            for target_url in target_urls:
                try:
                    logger.info(f"GoogleCloudIngester: Scraping {target_url}")
                    response = await client.get(target_url, timeout=15.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    if response.status_code == 200:
                        html_content = response.text
                        
                        link_pattern = re.compile(r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE)
                        matches = link_pattern.findall(html_content)
                        
                        seen_urls = set()
                        
                        for url, text in matches:
                            clean_text = re.sub(r'<[^>]+>', '', text).strip()
                            if not clean_text:
                                continue
                                
                            is_docs = "docs" in url or url.startswith("/vertex-ai/") or url.startswith("/gemini")
                            
                            # Filter logic
                            if is_docs:
                                if url.startswith("http"):
                                    full_url = url
                                elif target_url.startswith("https://cloud.google.com"):
                                    full_url = f"https://cloud.google.com{url}"
                                elif target_url.startswith("https://ai.google.dev"):
                                    full_url = f"https://ai.google.dev{url}"
                                else:
                                    full_url = url
                                
                                if full_url not in seen_urls:
                                    seen_urls.add(full_url)
                                    
                                    category = []
                                    if "api" in full_url: category.append("api")
                                    if "tutorials" in full_url: category.append("course")
                                    if "docs" in full_url: category.append("developer_docs")
                                    if not category: category.append("general")
                                    
                                    items.append(self.standardize_item(
                                        title=clean_text,
                                        content=f"Public learning syllabus/guide located at {full_url}",
                                        url=full_url,
                                        categories=category
                                    ))
                                    
                        logger.info(f"GoogleCloudIngester: Extracted learning nodes from {target_url}.")
                    else:
                        logger.warning(f"GoogleCloudIngester: Failed to fetch {target_url} - HTTP {response.status_code}")
                except Exception as e:
                    logger.error(f"GoogleCloudIngester: Network error during ingestion of {target_url}: {e}")

        return items
