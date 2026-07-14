"""
Test script for LangChain GenericChatAgent.

This script tests that the LangChain implementation properly calls the LLM.

Author: Cavin Otieno
"""

import asyncio
import os
from typing import List, Dict

# Set up test API key
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "sk-test-key"))

from generic_agent.agent import GenericChatAgent, create_generic_chat_agent


async def test_langchain_chat():
    """Test LangChain agent properly calls LLM."""
    print("=" * 60)
    print("Testing LangChain GenericChatAgent...")
    print("=" * 60)

    agent = create_generic_chat_agent(
        provider="openai",
        model_name="gpt-4o-mini",
        streaming=False,
    )

    # Test simple chat
    print("\n1. Testing simple chat...")
    response = await agent.chat(
        user_message="Say 'Hello' in one word",
        system_prompt="You are a helpful assistant."
    )

    print(f"Response: {response[:100] if response else 'None'}...")

    if response and len(response) > 5:
        print("[PASS] LangChain returns actual LLM response")
        return True
    else:
        print("[FAIL] LangChain returned empty response")
        return False


async def test_langchain_stream():
    """Test LangChain streaming works."""
    print("\n" + "=" * 60)
    print("Testing LangChain Streaming...")
    print("=" * 60)

    agent = create_generic_chat_agent(
        provider="openai",
        model_name="gpt-4o-mini",
        streaming=True,
    )

    print("\n1. Testing streaming chat...")
    full_response = ""
    token_count = 0

    async for token in agent.chat_stream(
        user_message="Count from 1 to 3.",
        system_prompt="You are a helpful assistant."
    ):
        full_response += token
        token_count += 1
        print(f"Token: {token}", end="")

    print(f"\n\nTotal tokens: {token_count}")
    print(f"Full response: {full_response[:100]}...")

    if full_response and len(full_response) > 5:
        print("[PASS] LangChain streaming returns actual LLM response")
        return True
    else:
        print("[FAIL] LangChain streaming returned empty response")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("LangChain LLM Integration Test Suite")
    print("=" * 60)

    results = []

    # Run tests
    results.append(await test_langchain_chat())
    results.append(await test_langchain_stream())

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[FAILURE] {total - passed} test(s) failed.")


if __name__ == "__main__":
    asyncio.run(main())
