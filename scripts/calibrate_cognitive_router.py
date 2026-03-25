"""
scripts/calibrate_cognitive_router.py

Pulls a GitHub PR's temporal history (comments, commits, reviews)
and calibrates the 4D Cognitive Architecture math equation:

$$Cognitive_State = (Intent_Vector * Delta_t) * Sum(W_i * D_i)$$

Usage:
  python scripts/calibrate_cognitive_router.py --repo "facebook/react" --pr 28731
"""

import os
import sys
import json
import math
import argparse
import requests
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Attempt to import the IntentAnalyzer from the engine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from engine.intent_analyzer import IntentAnalyzer
    analyzer = IntentAnalyzer()
except ImportError:
    analyzer = None

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GITHUB_API_URL = "https://api.github.com"


def fetch_pr_events(repo: str, pr_number: int, token: str = None) -> List[Dict[str, Any]]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    print(f"[*] Fetching PR #{pr_number} from {repo}...")
    
    # 1. Fetch Pull Request (for the body)
    pr_url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}"
    pr_res = requests.get(pr_url, headers=headers)
    if pr_res.status_code == 404:
        print("[!] PR not found. Check repo name and PR number.")
        sys.exit(1)
    elif pr_res.status_code == 403:
        print("[!] Rate limit exceeded. Set GITHUB_TOKEN environment variable.")
        sys.exit(1)
        
    pr_res.raise_for_status()
    pr_data = pr_res.json()
    
    events = []
    
    # Add the initial PR description
    if pr_data.get("body"):
        events.append({
            "type": "issue_comment",
            "timestamp": pr_data["created_at"],
            "author": pr_data["user"]["login"],
            "text": pr_data["body"]
        })
        
    # 2. Fetch standard Issue Comments
    comments_url = f"{GITHUB_API_URL}/repos/{repo}/issues/{pr_number}/comments"
    comments_res = requests.get(comments_url, headers=headers)
    if comments_res.status_code == 200:
        for c in comments_res.json():
            if c.get("body"):
                events.append({
                    "type": "issue_comment",
                    "timestamp": c["created_at"],
                    "author": c["user"]["login"],
                    "text": c["body"]
                })
            
    # 3. Fetch Review Comments (code comments)
    review_comments_url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}/comments"
    review_res = requests.get(review_comments_url, headers=headers)
    if review_res.status_code == 200:
        for c in review_res.json():
            if c.get("body"):
                events.append({
                    "type": "review_comment",
                    "timestamp": c["created_at"],
                    "author": c["user"]["login"],
                    "text": c["body"]
                })
            
    # 4. Fetch Commits
    commits_url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}/commits"
    commits_res = requests.get(commits_url, headers=headers)
    if commits_res.status_code == 200:
        for c in commits_res.json():
            events.append({
                "type": "commit",
                "timestamp": c["commit"]["author"]["date"],
                "author": c["commit"]["author"]["name"],
                "text": c["commit"]["message"]
            })
            
    # Sort chronologically
    events.sort(key=lambda x: x["timestamp"])
    return events


def calculate_delta_t(current_ts_str: str, prev_ts_str: str) -> Tuple[float, str]:
    """
    Returns (delta_t_multiplier, timeframe_label)
    Micro: < 1 hour  (dt=1.0)
    Meso: 1 - 24 hours (dt=1.5)
    Macro: > 24 hours  (dt=3.0)
    """
    if not prev_ts_str:
        return 1.0, "micro"
        
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    current_time = datetime.strptime(current_ts_str, fmt)
    prev_time = datetime.strptime(prev_ts_str, fmt)
    
    diff_hours = (current_time - prev_time).total_seconds() / 3600.0
    
    if diff_hours < 1:
        return 1.0, "micro"
    elif diff_hours < 24:
        return 1.5, "meso"
    else:
        return 3.0, "macro"


def get_intent_vector(text: str, event_type: str) -> List[float]:
    """ Returns [Listen, Collaborate, Execute] mapping from Tooloo's intent math """
    if analyzer:
        # Returns [visual, auditory, tactile, agency] from Tooloo's intent math
        vec = analyzer._get_vector(text)
        agency = vec[3]
        if agency > 0.7 or event_type == "commit":
            # High agency = Execute
            return [0.1, 0.2, 0.9]
        elif text.endswith("?") or agency > 0.3:
            # Questions = Collaborate
            return [0.2, 0.8, 0.2]
        else:
            # Passive = Listen
            return [0.8, 0.2, 0.1]
    else:
        # Fallback heuristic if IntentAnalyzer is not available
        text_lower = text.lower()
        if event_type == "commit":
            return [0.1, 0.2, 0.9] # Execute
        elif "why" in text_lower or "how" in text_lower or "?" in text_lower:
            return [0.2, 0.8, 0.2] # Collaborate
        else:
            return [0.8, 0.2, 0.1] # Listen


def call_cognitive_router(text: str, intent_vec: List[float], timeframe: str, use_llm: bool = False) -> Dict[str, Any]:
    """ Returns dynamic mental dimensions based on the Prompt """
    if use_llm and HAS_GENAI and os.environ.get("GEMINI_API_KEY"):
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        model_name = "gemini-2.5-flash"
        
        prompt = f"""
        SYSTEM ROLE: You are the Cognitive Routing Engine for a universal creation studio. You do not generate code or answer user questions. Your sole purpose is to analyze the user's input, the current temporal context, and the mathematical intent, and dynamically generate the required "Mental Dimensions" the system needs to adopt for the upcoming task.

        INPUT VARIABLES:
        * User_Input: {text[:800]}
        * Intent_Vector: {intent_vec} (Listen, Collaborate, Execute)
        * Active_Timeframe: {timeframe}

        YOUR TASK:
        1. Analyze the inputs. Generate a dynamic array of 3 to 7 "Mental Dimensions" required.
        2. Score each dimension from 0.00 to 1.00.
        3. Determine System_Stance: "REACTIVE" (Just do it), "ACTIVE" (Do it and report), or "PROACTIVE" (Challenge, guide, or warn).

        OUTPUT FORMAT: JSON ONLY
        {{
            "system_stance": "PROACTIVE",
            "recommended_vertex_route": "execution_fast",
            "mental_dimensions": {{"Precision": 0.9, "Patience": 0.8}},
            "temporal_focus": "{timeframe}",
            "reasoning_log": "String"
        }}
        """
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"[!] LLM Error: {e}. Falling back to mock router.")
            
    # Mock fallback replicating the LLM router logic
    if intent_vec[2] > 0.7: # Execute
        stance = "ACTIVE"
        dimensions = {"Syntax_Precision": 0.95, "Execution_Speed": 0.90, "Logic_Flow": 0.85}
        route = "execution_fast"
    elif timeframe == "macro" or intent_vec[1] > 0.6: # Collaborate / Macro
        stance = "PROACTIVE"
        dimensions = {"Architectural_Foresight": 0.90, "Empathy_and_Patience": 0.85, "Lateral_Thinking": 0.80}
        route = "reasoning_heavy"
    else: # Listen / micro
        stance = "REACTIVE"
        dimensions = {"Observation": 0.90, "Context_Gathering": 0.85}
        route = "execution_fast"
        
    return {
        "system_stance": stance,
        "recommended_vertex_route": route,
        "mental_dimensions": dimensions,
        "temporal_focus": timeframe,
        "reasoning_log": "[Simulated] Math-derived stance based on Intent and PR timeframe."
    }

def magnitude(vec: List[float]) -> float:
    return math.sqrt(sum(v*v for v in vec))

def main():
    parser = argparse.ArgumentParser(description="Calibrate the 4D Cognitive Architecture Router via GitHub PR replays.")
    parser.add_argument("--repo", type=str, default="pallets/flask", help="GitHub repo (e.g., facebook/react, pallets/flask)")
    parser.add_argument("--pr", type=int, default=5214, help="Pull Request number to replay")
    parser.add_argument("--use-llm", action="store_true", help="Use Gemini API for the Cognitive Router (requires GEMINI_API_KEY)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    
    events = fetch_pr_events(args.repo, args.pr, token)
    print(f"[+] Replaying {len(events)} temporal events from {args.repo} PR#{args.pr}\n")
    
    if len(events) == 0:
        print("No events found. Exiting.")
        sys.exit(0)
    
    prev_ts = None
    
    print("-" * 100)
    print(f"{'TIMESTAMP':<20} | {'AUTHOR':<15} | {'EVENT':<14} | STANCE & SCORE")
    print("-" * 100)
    
    for e in events:
        # 1. Delta T
        dt_val, timeframe = calculate_delta_t(e["timestamp"], prev_ts)
        prev_ts = e["timestamp"]
        
        # 2. Intent Vector
        text = e["text"] or ""
        intent_vec = get_intent_vector(text, e["type"])
        
        # 3. Router
        router_res = call_cognitive_router(text, intent_vec, timeframe, args.use_llm)
        stance = router_res["system_stance"]
        dims = router_res["mental_dimensions"]
        
        # 4. The Grand Equation
        # Cognitive_State = (Intent_Vector * Delta_t) * Sum(W_i * D_i)
        sum_wd = sum(val for val in dims.values())
        
        # Cognitive_State vector
        cog_state_vec = [v * dt_val * sum_wd for v in intent_vec]
        
        # We output the magnitude of the vector to show 'cognitive energy/intensity'
        score = magnitude(cog_state_vec)
        
        time_display = e["timestamp"].replace("T", " ").replace("Z", "")
        author = e["author"][:14]
        ev_type = e["type"]
        
        # Provide a snippet of the text
        text_preview = text.replace('\n', ' ')[:40] + ('...' if len(text) > 40 else '')
        
        print(f"{time_display:<20} | {author:<15} | {ev_type:<14} | {stance:<10} (Energy: {score:.2f}, dt_class={timeframe})")
        print(f"   └─ Input:  \"{text_preview}\"")
        print(f"   └─ Intent: Listen={intent_vec[0]:.1f}, Collab={intent_vec[1]:.1f}, Exec={intent_vec[2]:.1f}")
        print(f"   └─ Dims:   {dims}")
        print("-" * 100)


if __name__ == "__main__":
    main()
