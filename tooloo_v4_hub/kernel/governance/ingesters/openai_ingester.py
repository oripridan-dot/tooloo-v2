# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: OPENAI_INGESTER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/governance/ingesters/openai_ingester.py
# WHEN: 2026-04-04T08:00:00.000000
# WHY: Concrete ingestion for OpenAI's public learning materials.
# HOW: Async HTTP fetching and parsing of public learning routes.
# TIER: T4:zero-trust
# PURITY: 1.00
# ==========================================================

import httpx
import logging
import re
from typing import Dict, Any, List
from tooloo_v4_hub.kernel.governance.academy_ingester import AcademyIngester

logger = logging.getLogger("OpenAIIngester")

class OpenAIIngester(AcademyIngester):
    def __init__(self):
        super().__init__(provider_name="OpenAI", base_url="https://platform.openai.com/docs/")
        self.cookbook_url = "https://cookbook.openai.com/"

    async def ingest(self) -> List[Dict[str, Any]]:
        items = []
        logger.info(f"OpenAIIngester: Starting ingestion from {self.provider_name}")
        
        target_urls = [self.base_url, self.cookbook_url]
        
        async with httpx.AsyncClient() as client:
            for target_url in target_urls:
                try:
                    logger.info(f"OpenAIIngester: Scraping {target_url}")
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
                                
                            is_docs = "docs/" in url or url.startswith("/docs/")
                            is_cookbook = "cookbook.openai.com" in target_url
                            
                            # Filter logic
                            if is_docs or is_cookbook:
                                if url.startswith("http"):
                                    full_url = url
                                elif target_url.startswith("https://platform.openai.com"):
                                    full_url = f"https://platform.openai.com{url}"
                                elif target_url.startswith("https://cookbook.openai.com"):
                                    full_url = f"https://cookbook.openai.com{url}"
                                else:
                                    full_url = url
                                
                                if full_url not in seen_urls:
                                    seen_urls.add(full_url)
                                    
                                    category = []
                                    if "api" in full_url: category.append("api")
                                    if "guides" in full_url: category.append("developer_docs")
                                    if "examples" in full_url or is_cookbook: category.append("course")
                                    if not category: category.append("general")
                                    
                                    items.append(self.standardize_item(
                                        title=clean_text,
                                        content=f"Public learning syllabus/guide located at {full_url}",
                                        url=full_url,
                                        categories=category
                                    ))
                                    
                        logger.info(f"OpenAIIngester: Extracted learning nodes from {target_url}.")
                    else:
                        logger.warning(f"OpenAIIngester: Failed to fetch {target_url} - HTTP {response.status_code}")
                except Exception as e:
                    logger.error(f"OpenAIIngester: Network error during ingestion of {target_url}: {e}")

        return items
