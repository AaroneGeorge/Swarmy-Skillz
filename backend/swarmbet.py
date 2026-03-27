"""
SwarmBet Orchestrator

Chains: parse question → collect data → run MiroFish → extract prediction.
Returns structured JSON output.
"""

import json
import re
import sys
import argparse
from datetime import datetime, timezone

from mirofish_client import MiroFishClient
from data_collector import DataCollector


# --- Question Parsing ---

CRYPTO_KEYWORDS = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "cardano": "cardano", "ada": "cardano",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "xrp": "ripple", "ripple": "ripple",
}


def parse_question(question: str) -> dict:
    """Parse a prediction question into structured components.

    Returns: {
        "question": str,
        "type": "crypto" | "general",
        "coin_id": str | None,
        "target": str | None,
        "deadline": str | None,
        "search_terms": list[str],
    }
    """
    q_lower = question.lower()

    # Detect crypto
    coin_id = None
    for keyword, cg_id in CRYPTO_KEYWORDS.items():
        if keyword in q_lower:
            coin_id = cg_id
            break

    # Extract price target
    target_match = re.search(r'\$[\d,]+(?:\.\d+)?[kKmM]?', question)
    target = target_match.group(0) if target_match else None

    # Extract deadline
    deadline = None
    deadline_patterns = [
        r'by\s+([\w\s]+\d{4})',
        r'before\s+([\w\s]+\d{4})',
        r'in\s+([\w\s]+\d{4})',
        r'(Q[1-4]\s+\d{4})',
        r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
    ]
    for pattern in deadline_patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            deadline = match.group(1).strip()
            break

    # Generate search terms
    search_terms = [question]
    if coin_id:
        search_terms.append(f"{coin_id} price prediction")
    words = [w for w in question.split() if len(w) > 3 and w.lower() not in {"will", "does", "would", "could", "should", "that", "this", "with"}]
    if words:
        search_terms.append(" ".join(words[:5]))

    return {
        "question": question,
        "type": "crypto" if coin_id else "general",
        "coin_id": coin_id,
        "target": target,
        "deadline": deadline,
        "search_terms": search_terms,
    }


# --- Main Orchestrator ---

def run_prediction(question: str, custom_context: str | None = None, verbose: bool = False) -> dict:
    """Full SwarmBet pipeline: parse → collect → simulate → predict.

    Args:
        question: The prediction question.
        custom_context: Optional additional context for seed data.
        verbose: Print progress updates.

    Returns: Structured prediction result dict.
    """
    mirofish = MiroFishClient()
    collector = DataCollector()

    # Step 1: Parse
    if verbose:
        print(f"[1/5] Parsing question...")
    parsed = parse_question(question)

    # Step 2: Collect seed data
    if verbose:
        print(f"[2/5] Collecting seed data (type: {parsed['type']})...")

    if parsed["type"] == "crypto" and parsed["coin_id"]:
        seed_markdown = collector.collect_crypto_seed(
            coin_id=parsed["coin_id"],
            question=question,
            custom_context=custom_context,
        )
    else:
        seed_markdown = collector.collect_general_seed(
            question=question,
            search_terms=parsed["search_terms"],
            custom_context=custom_context,
        )

    # Step 3: Run MiroFish simulation
    if verbose:
        print(f"[3/5] Running MiroFish swarm simulation (this takes 3-7 minutes)...")

    project_name = re.sub(r'[^a-z0-9_]', '_', question.lower()[:50])
    result = mirofish.run_full_simulation(
        name=project_name,
        description=question,
        seed_content=seed_markdown,
    )

    if result.get("error"):
        return {
            "question": question,
            "parsed": parsed,
            "error": result["error"],
            "status": result.get("status"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Step 4: Parse prediction response
    if verbose:
        print(f"[4/5] Extracting prediction from swarm output...")

    # Handle both response formats: {"response": "..."} and {"data": {"response": "..."}}
    prediction_raw = result.get("prediction", {})
    prediction_text = (
        prediction_raw.get("response")
        or (prediction_raw.get("data", {}) or {}).get("response")
        or str(prediction_raw)
    )
    consensus = _extract_consensus(prediction_text)

    # Step 5: Build structured output
    if verbose:
        print(f"[5/5] Building result...")

    output = {
        "question": question,
        "parsed": parsed,
        "consensus_pct": consensus["pct"],
        "consensus_direction": consensus["direction"],
        "confidence": consensus["confidence"],
        "key_insights": consensus["insights"],
        "raw_prediction": prediction_text,
        "report_summary": result["report"].get("summary", ""),
        "simulation_id": result["simulation_id"],
        "project_id": result["project_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if verbose:
        print(f"\nResult: {consensus['pct']}% {consensus['direction']} (confidence: {consensus['confidence']})")

    return output


def _extract_consensus(text: str) -> dict:
    """Extract structured consensus data from MiroFish chat response.

    Best-effort parsing — MiroFish responses vary in format and may contain
    Chinese text (the underlying engine is Chinese-language). This parser
    handles English, Chinese, and mixed-language responses.
    """
    pct = 50  # default
    direction = "UNCERTAIN"
    confidence = "MEDIUM"
    insights = []

    # Try to find percentage — multiple patterns
    pct_patterns = [
        r'(\d{1,3})(?:\.\d+)?\s*%',                    # "68%" or "68.5 %"
        r'(\d{1,3})(?:\.\d+)?\s*percent',               # "68 percent"
        r'YES.*?(\d{1,3})(?:\.\d+)?%',                  # "YES at 68%"
        r'consensus.*?(\d{1,3})(?:\.\d+)?%',             # "consensus is 68%"
        r'(\d{1,3})(?:\.\d+)?%.*?(?:YES|agree|support)', # "68% YES"
        r'(\d{1,3})(?:\.\d+)?%.*?(?:认为|支持|赞成)',      # Chinese: "68% believe/support"
    ]
    for pattern in pct_patterns:
        pct_match = re.search(pattern, text, re.IGNORECASE)
        if pct_match:
            pct = int(pct_match.group(1))
            pct = max(0, min(100, pct))
            break

    # Direction from percentage
    if pct >= 55:
        direction = "YES"
    elif pct <= 45:
        direction = "NO"
    else:
        # 46-54% range: check text for explicit direction cues
        text_lower = text.lower()
        yes_cues = ["lean yes", "favor yes", "likely yes", "positive", "bullish",
                     "支持", "赞成", "看好", "倾向于是"]
        no_cues = ["lean no", "favor no", "likely no", "negative", "bearish",
                    "反对", "不支持", "看空", "倾向于否"]
        if any(cue in text_lower for cue in yes_cues):
            direction = "YES"
        elif any(cue in text_lower for cue in no_cues):
            direction = "NO"

    # Confidence detection — English and Chinese keywords
    text_lower = text.lower()
    high_conf = [
        "high confidence", "strong consensus", "overwhelming", "clear majority",
        "decisively", "firmly", "strongly agree", "near unanimous",
        "高置信", "强烈共识", "压倒性", "明确多数",
    ]
    low_conf = [
        "low confidence", "divided", "split", "uncertain", "unclear",
        "contested", "no consensus", "closely split", "evenly divided",
        "低置信", "分歧", "不确定", "分裂", "无共识",
    ]
    if any(w in text_lower for w in high_conf):
        confidence = "HIGH"
    elif any(w in text_lower for w in low_conf):
        confidence = "LOW"

    # Extract insight sentences — broadened keyword set, handles Chinese
    sentences = re.split(r'[.!?\n。！？]', text)
    insight_keywords = [
        "because", "due to", "driven by", "shifted", "turned", "majority",
        "key factor", "notably", "primarily", "significant", "important",
        "influenced", "suggests", "indicates", "trend", "momentum",
        "risk", "catalyst", "argue", "believe", "reason",
        # Chinese keywords
        "因为", "由于", "驱动", "转变", "多数", "关键因素", "主要",
        "重要", "影响", "表明", "趋势", "风险", "催化", "认为", "原因",
    ]
    for s in sentences:
        s = s.strip()
        if len(s) > 15 and any(k in s.lower() for k in insight_keywords):
            insights.append(s)

    # If no insights found from keywords, take the longest non-trivial sentences
    if not insights:
        candidates = [s.strip() for s in sentences if len(s.strip()) > 30]
        insights = sorted(candidates, key=len, reverse=True)[:3]

    insights = insights[:5]  # cap at 5

    return {
        "pct": pct,
        "direction": direction,
        "confidence": confidence,
        "insights": insights,
    }


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="SwarmBet — Swarm Intelligence Prediction Engine")
    parser.add_argument("question", help="The prediction question to analyze")
    parser.add_argument("--context", help="Additional context to include in seed data", default=None)
    parser.add_argument("--verbose", "-v", action="store_true", help="Print progress updates")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()
    result = run_prediction(args.question, custom_context=args.context, verbose=args.verbose)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result.get("error"):
            print(f"\nError: {result['error']}")
            sys.exit(1)

        print(f"""
┌─────────────────────────────────────────────────┐
│ SwarmBet Prediction Result                      │
├─────────────────────────────────────────────────┤
│ Question:   {result['question'][:40]:<40s}│
│ Consensus:  {result['consensus_pct']}% {result['consensus_direction']:<35s}│
│ Confidence: {result['confidence']:<37s}│
└─────────────────────────────────────────────────┘""")

        if result.get("key_insights"):
            print("\nKey Insights:")
            for i, insight in enumerate(result["key_insights"], 1):
                print(f"  {i}. {insight}")

        print(f"\nSimulation ID: {result['simulation_id']}")


if __name__ == "__main__":
    main()
