"""
Evaluation benchmark runner for the Website-Grounded RAG Agent.
Sends test questions to the /rag endpoint and validates grounding, citations, and token tracking.
"""

import argparse
import json
import time
import requests
from typing import List, Dict, Any

DEFAULT_API_URL = "http://localhost:8009"

TEST_CASES = [
    {
        "id": "Q1",
        "category": "Factual",
        "query": "What is a Python generator and how do you create one?",
        "expected_keywords": ["yield", "generator", "iterator"],
        "expect_no_info": False,
    },
    {
        "id": "Q2",
        "category": "Factual",
        "query": "What is the difference between a list and a tuple in Python?",
        "expected_keywords": ["mutable", "immutable", "tuple", "list"],
        "expect_no_info": False,
    },
    {
        "id": "Q3",
        "category": "Factual",
        "query": "How does Python's Global Interpreter Lock (GIL) work?",
        "expected_keywords": ["GIL", "thread", "lock"],
        "expect_no_info": False,
    },
    {
        "id": "Q4",
        "category": "Factual",
        "query": "What are Python decorators and how are they used?",
        "expected_keywords": ["decorator", "@", "function", "wrapper"],
        "expect_no_info": False,
    },
    {
        "id": "Q5",
        "category": "Factual",
        "query": "What is the purpose of Python's __init__ method?",
        "expected_keywords": ["__init__", "constructor", "class", "instance"],
        "expect_no_info": False,
    },
    {
        "id": "Q6",
        "category": "Synthesis",
        "query": "How do context managers and the 'with' statement work in Python?",
        "expected_keywords": ["with", "context manager", "__enter__", "__exit__"],
        "expect_no_info": False,
    },
    {
        "id": "Q7",
        "category": "Synthesis",
        "query": "Explain Python's exception handling mechanism.",
        "expected_keywords": ["try", "except", "finally", "raise"],
        "expect_no_info": False,
    },
    {
        "id": "Q8",
        "category": "Synthesis",
        "query": "What are Python's built-in data structures?",
        "expected_keywords": ["list", "dict", "set", "tuple"],
        "expect_no_info": False,
    },
    {
        "id": "Q9",
        "category": "Synthesis",
        "query": "How does async/await work in Python?",
        "expected_keywords": ["async", "await", "coroutine", "asyncio"],
        "expect_no_info": False,
    },
    {
        "id": "Q10",
        "category": "Synthesis",
        "query": "What is list comprehension and how does it differ from a for loop?",
        "expected_keywords": ["comprehension", "for", "list"],
        "expect_no_info": False,
    },
    {
        "id": "Q11",
        "category": "Negative",
        "query": "What is the monthly subscription price of Python Pro Enterprise edition?",
        "expected_keywords": [],
        "expect_no_info": True,
    },
    {
        "id": "Q12",
        "category": "Negative",
        "query": "How do I install Python on a Raspberry Pi 5 using Docker Compose?",
        "expected_keywords": [],
        "expect_no_info": True,
    },
    {
        "id": "Q13",
        "category": "Negative",
        "query": "What is the total revenue of the Python Software Foundation in 2024?",
        "expected_keywords": [],
        "expect_no_info": True,
    },
    {
        "id": "Q14",
        "category": "Negative",
        "query": "Who won the 2024 UEFA European Football Championship final?",
        "expected_keywords": [],
        "expect_no_info": True,
    },
    {
        "id": "Q15",
        "category": "Negative",
        "query": "Does Python have a built-in iOS app for personal budgeting?",
        "expected_keywords": [],
        "expect_no_info": True,
    },
]


def run_eval(company: str = "python_docs", base_url: str = DEFAULT_API_URL):
    print(f"\n{'='*70}")
    print(f"🚀 Starting Website RAG Benchmark on company: '{company}'")
    print(f"Endpoint: {base_url}/rag")
    print(f"{'='*70}\n")

    # Verify backend health
    try:
        r = requests.get(f"{base_url}/health", timeout=3)
        if r.status_code != 200:
            print("❌ Backend is not responding healthy.")
            return
    except Exception as e:
        print(f"❌ Could not connect to {base_url}: {e}")
        return

    results = []
    total_tokens = 0
    total_cost = 0.0

    for test in TEST_CASES:
        qid = test["id"]
        category = test["category"]
        query = test["query"]
        expect_no_info = test["expect_no_info"]

        print(f"[{qid}] ({category}) Query: {query}")
        start_t = time.time()

        payload = {
            "company_name": company,
            "query": query,
            "stream": False,
        }

        try:
            resp = requests.post(f"{base_url}/rag", json=payload, timeout=60)
            elapsed = time.time() - start_t
            if resp.status_code != 200:
                print(f"    ❌ HTTP Error {resp.status_code}: {resp.text[:200]}")
                results.append({"id": qid, "passed": False, "reason": f"HTTP {resp.status_code}"})
                continue

            data = resp.json()
            answer = data.get("answer", "")
            citations = data.get("citations", [])
            has_enough = data.get("has_enough_info", True)
            tokens = data.get("token_usage", {})

            q_tokens = tokens.get("total_tokens", 0)
            q_cost = tokens.get("estimated_cost_usd", 0.0)
            total_tokens += q_tokens
            total_cost += q_cost

            # Evaluate
            passed = True
            reason = "OK"

            if expect_no_info:
                # Negative query test
                if has_enough and "not have enough information" not in answer.lower() and "does not contain" not in answer.lower():
                    passed = False
                    reason = "Failed negative guardrail (answered out-of-scope query)"
            else:
                # Factual / Synthesis test
                matched = [kw for kw in test["expected_keywords"] if kw.lower() in answer.lower()]
                if not matched:
                    passed = False
                    reason = f"Missing key expected terms: {test['expected_keywords']}"
                elif not citations:
                    passed = False
                    reason = "No citations provided for factual response"

            status_str = "✅ PASS" if passed else "❌ FAIL"
            print(f"    {status_str} in {elapsed:.2f}s | Tokens: {q_tokens} | Citations: {len(citations)}")
            if not passed:
                print(f"    Reason: {reason}")
                print(f"    Snippet: {answer[:180]}...")

            results.append({
                "id": qid,
                "category": category,
                "passed": passed,
                "reason": reason,
                "latency_s": elapsed,
                "tokens": q_tokens,
                "citations_count": len(citations),
            })

        except Exception as e:
            print(f"    ❌ Exception: {e}")
            results.append({"id": qid, "passed": False, "reason": str(e)})

        print("-" * 50)

    # Summary
    passed_count = sum(1 for r in results if r.get("passed"))
    total_count = len(results)
    score_pct = (passed_count / total_count) * 100 if total_count else 0

    print(f"\n{'='*70}")
    print(f"📊 BENCHMARK SUMMARY")
    print(f"Score: {passed_count}/{total_count} ({score_pct:.1f}%)")
    print(f"Total Tokens: {total_tokens:,} | Total Est Cost: ${total_cost:.6f}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAG benchmark")
    parser.add_argument("--company", default="python_docs", help="Knowledge base name to evaluate against")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="API Base URL")
    args = parser.parse_args()
    run_eval(company=args.company, base_url=args.url)
