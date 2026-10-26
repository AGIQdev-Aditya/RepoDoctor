"""
RepoDoctor Supervisor Loop with 3-Gate Security Architecture
Connects Google Gemma (via Ollama) to deterministic diagnostic tools.
"""

import sys
import json
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import ollama

from tools import TOOLS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RepoDoctor")

DEFAULT_MODEL = "gemma4:e4b"
MAX_STEPS = 5

# Tool Definitions conforming to Ollama Function Calling JSON Schema
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "get_repo_overview",
            "description": "Calculates high-level repository metrics including total files, lines of code (LOC), language breakdown, comment density, and largest files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the target codebase repository."}
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_security_and_secrets",
            "description": "Audits repository files for leaked API keys, tokens, and dangerous code patterns (eval, exec, command injection, SQL injection). Returns security score and findings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the target codebase repository."}
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "map_architecture_dependencies",
            "description": "Extracts Python AST import structures across all project modules, detects circular dependencies, and returns Mermaid flowchart diagram syntax.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the target codebase repository."}
                },
                "required": ["repo_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_codebase",
            "description": "Performs semantic cosine vector search across repository code chunks using nomic-embed-text to find relevant functions, classes, and logic snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_path": {"type": "string", "description": "Path to the target codebase repository."},
                    "query": {"type": "string", "description": "Natural language or technical code query to search for."},
                    "top_k": {"type": "integer", "description": "Number of top matching code chunks to return (default 3)."}
                },
                "required": ["repo_path", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_test_sandbox",
            "description": "Executes synthesized unit tests inside an isolated temporary sandbox with pytest to verify correctness.",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_code": {"type": "string", "description": "Executable pytest test code."},
                    "target_code": {"type": "string", "description": "Optional target function/module code being tested."}
                },
                "required": ["test_code"]
            }
        }
    }
]


def load_skill_contract() -> str:
    """Load the declarative agent contract from SKILL.md."""
    skill_file = Path(__file__).parent / "SKILL.md"
    if skill_file.exists():
        try:
            return skill_file.read_text(encoding="utf-8")
        except Exception:
            pass
    return "You are RepoDoctor, an autonomous codebase health, security auditing, and architecture diagnostic agent."


# ============================================================================
# 3-GATE SECURITY & VERIFICATION PROTOCOL (KT Workshop Requirement)
# ============================================================================

def gate_1_allowlist_check(tool_name: str) -> Tuple[bool, Optional[str]]:
    """Gate 1: Verify the proposed function exists in the authorized tool allowlist."""
    if tool_name not in TOOLS:
        return False, f"Gate 1 Security Violation: Unauthorized tool '{tool_name}' rejected. Registered tools: {list(TOOLS.keys())}"
    return True, None


def gate_2_argument_check(tool_func: Any, kwargs: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Gate 2: Validate function argument structure, parameter types, and signature binding."""
    try:
        sig = inspect.signature(tool_func)
        sig.bind(**kwargs)
        return True, None
    except TypeError as e:
        return False, f"Gate 2 Validation Error: Invalid argument signature for '{tool_func.__name__}': {str(e)}"


def gate_3_safe_execution(tool_func: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Gate 3: Execute tool inside bounded exception handling with path traversal guards."""
    try:
        result = tool_func(**kwargs)
        return {"status": "success", "result": result}
    except PermissionError as pe:
        return {"status": "error", "error_type": "SecurityTraversalBlocked", "message": str(pe)}
    except Exception as e:
        return {"status": "error", "error_type": "ExecutionException", "message": str(e)}


def dispatch_tool(tool_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Host dispatcher enforcing the sequential 3-Gate Security Chain."""
    logger.info(f"Checking Gate 1 for tool '{tool_name}' with args {list(kwargs.keys())}")
    ok1, err1 = gate_1_allowlist_check(tool_name)
    if not ok1:
        logger.error(err1)
        return {"status": "error", "gate": 1, "message": err1}

    tool_func = TOOLS[tool_name]
    logger.info(f"Checking Gate 2 signature for '{tool_name}'")
    ok2, err2 = gate_2_argument_check(tool_func, kwargs)
    if not ok2:
        logger.error(err2)
        return {"status": "error", "gate": 2, "message": err2}

    logger.info(f"Executing Gate 3 bounded run for '{tool_name}'")
    exec_result = gate_3_safe_execution(tool_func, kwargs)
    return {"status": "success", "gate": 3, "payload": exec_result}


# ============================================================================
# SUPERVISOR MULTI-TURN AGENT LOOP
# ============================================================================

def run_agent_loop(
    user_prompt: str,
    repo_path: str,
    model: str = DEFAULT_MODEL,
    max_steps: int = MAX_STEPS
) -> Dict[str, Any]:
    """
    Executes the autonomous supervisor loop with Gemma and local Ollama dispatch.
    Returns synthesized answer, thinking trace, and full tool execution ledger.
    """
    skill_contract = load_skill_contract()
    system_prompt = (
        f"{skill_contract}\n\n"
        f"TARGET REPOSITORY PATH: {repo_path}\n"
        f"Always use the tools to inspect the repository before answering. "
        f"Never hallucinate file contents or security findings."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    tool_ledger = []
    thinking_traces = []
    step = 0

    while step < max_steps:
        step += 1
        logger.info(f"Agent Loop Step {step}/{max_steps} using model '{model}'")

        try:
            response = ollama.chat(
                model=model,
                messages=messages,
                tools=TOOL_SCHEMAS
            )
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return {
                "status": "error",
                "message": f"Inference error with model '{model}': {str(e)}",
                "tool_ledger": tool_ledger,
                "thinking_trace": "\n".join(thinking_traces)
            }

        msg = response.get("message", {})
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])

        if content and "<think>" in content:
            # Capture thinking trace if model embeds it
            thinking_traces.append(content)

        # Append assistant response to message history
        messages.append(msg)

        # If model did not request any tools, we have reached the final answer
        if not tool_calls:
            logger.info("Supervisor loop complete: Final response synthesized.")
            return {
                "status": "success",
                "final_response": content,
                "tool_ledger": tool_ledger,
                "thinking_trace": "\n".join(thinking_traces),
                "steps_taken": step,
                "model": model
            }

        # Process tool calls
        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "")
            fn_args = fn.get("arguments", {})

            # Ensure repo_path is supplied if tool requires it and model omitted it
            if "repo_path" in fn_args and not fn_args["repo_path"]:
                fn_args["repo_path"] = repo_path
            elif "repo_path" not in fn_args and fn_name in {"get_repo_overview", "scan_security_and_secrets", "map_architecture_dependencies", "search_codebase"}:
                fn_args["repo_path"] = repo_path

            dispatch_report = dispatch_tool(fn_name, fn_args)
            
            tool_ledger.append({
                "step": step,
                "tool_name": fn_name,
                "arguments": fn_args,
                "dispatch_report": dispatch_report
            })

            # Format tool result for Ollama message protocol
            tool_content = json.dumps(dispatch_report.get("payload", {}).get("result", dispatch_report))
            messages.append({
                "role": "tool",
                "content": tool_content
            })

    # If max steps exceeded, request final synthesis
    logger.warning("Max supervisor steps reached. Synthesizing final summary.")
    messages.append({
        "role": "user",
        "content": "Please summarize your findings based on the completed tool executions."
    })
    final_res = ollama.chat(model=model, messages=messages)
    return {
        "status": "success",
        "final_response": final_res.get("message", {}).get("content", "Diagnostic complete."),
        "tool_ledger": tool_ledger,
        "thinking_trace": "\n".join(thinking_traces),
        "steps_taken": step,
        "model": model
    }


if __name__ == "__main__":
    target = str(Path(__file__).parent)
    prompt = "Run a complete security audit and architectural dependency scan on this repository."
    if len(sys.argv) > 1:
        target = sys.argv[1]
    if len(sys.argv) > 2:
        prompt = sys.argv[2]

    print("==================================================")
    print("🩺 REPO-DOCTOR CLI SUPERVISOR")
    print(f"Target: {target}")
    print(f"Prompt: {prompt}")
    print("==================================================")

    res = run_agent_loop(user_prompt=prompt, repo_path=target)
    print("\n--- Tool Execution Ledger ---")
    for entry in res["tool_ledger"]:
        print(f"Step {entry['step']}: Tool '{entry['tool_name']}' -> Gate Status: {entry['dispatch_report']['status']}")

    print("\n--- Final Synthesized Response ---")
    print(res["final_response"])
