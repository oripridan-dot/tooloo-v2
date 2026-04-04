# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: ANTHROPIC_INGESTER | Version: 1.0.0
# WHERE: tooloo_v4_hub/kernel/governance/ingesters/anthropic_ingester.py
# WHEN: 2026-04-04T08:00:00.000000
# WHY: Concrete ingestion for Anthropic's public learning materials.
# HOW: Async HTTP fetching and regex parsing of public learning routes.
# TIER: T4:zero-trust
# PURITY: 1.00
# ==========================================================

import httpx
import logging
import re
from typing import Dict, Any, List
from tooloo_v4_hub.kernel.governance.academy_ingester import AcademyIngester

logger = logging.getLogger("AnthropicIngester")

class AnthropicIngester(AcademyIngester):
    def __init__(self):
        super().__init__(provider_name="Anthropic", base_url="https://www.anthropic.com/learn")
        self.skilljar_url = "https://anthropic.skilljar.com/"

    async def ingest(self) -> List[Dict[str, Any]]:
        """
        Fetches the main learning portal and attempts to extract public course structures.
        """
        items = []
        logger.info(f"AnthropicIngester: Starting ingestion from {self.base_url}")
        
        target_urls = [self.base_url, "https://platform.claude.com/docs/en/home"]
        
        async with httpx.AsyncClient() as client:
            for target_url in target_urls:
                try:
                    logger.info(f"AnthropicIngester: Scraping {target_url}")
                    response = await client.get(target_url, timeout=15.0)
                    if response.status_code == 200:
                        html_content = response.text
                        
                        link_pattern = re.compile(r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"[^>]*>(.*?)</a>', re.IGNORECASE)
                        matches = link_pattern.findall(html_content)
                        
                        seen_urls = set()
                        
                        for url, text in matches:
                            clean_text = re.sub(r'<[^>]+>', '', text).strip()
                            if not clean_text:
                                continue
                                
                            if "learn/" in url or "skilljar" in url or "docs" in url:
                                if url.startswith("http"):
                                    full_url = url
                                elif target_url.startswith("https://platform.claude.com"):
                                    full_url = f"https://platform.claude.com{url}"
                                else:
                                    full_url = f"https://www.anthropic.com{url}"
                                
                                if full_url not in seen_urls:
                                    seen_urls.add(full_url)
                                    
                                    category = []
                                    if "build-with-claude" in url: category.append("api")
                                    elif "claude-for-work" in url: category.append("enterprise")
                                    elif "skilljar" in url: category.append("course")
                                    elif "docs" in url: category.append("developer_docs")
                                    else: category.append("general")
                                    
                                    items.append(self.standardize_item(
                                        title=clean_text,
                                        content=f"Public learning syllabus/guide located at {full_url}",
                                        url=full_url,
                                        categories=category
                                    ))
                                    
                        logger.info(f"AnthropicIngester: Extracted learning nodes from {target_url}.")
                    else:
                        logger.warning(f"AnthropicIngester: Failed to fetch {target_url} - HTTP {response.status_code}")
                except Exception as e:
                    logger.error(f"AnthropicIngester: Network error during ingestion of {target_url}: {e}")

        return items
