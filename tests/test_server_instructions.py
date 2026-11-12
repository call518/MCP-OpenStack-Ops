"""Check that the server sends its instructions and exposes no MCP prompts."""

import asyncio

import pytest
from fastmcp import Client

from mcp_openstack_ops.mcp_main import SERVER_INSTRUCTIONS, mcp

# Claude Code cuts server instructions longer than this.
CLAUDE_CODE_INSTRUCTIONS_LIMIT = 4096


def test_instructions_fit_claude_code_limit():
    assert SERVER_INSTRUCTIONS.strip()
    assert len(SERVER_INSTRUCTIONS) <= CLAUDE_CODE_INSTRUCTIONS_LIMIT


@pytest.mark.parametrize("mode", ["legacy", None])
def test_clients_receive_instructions_and_no_prompts(mode):
    async def check():
        client = Client(mcp, mode=mode) if mode else Client(mcp)
        async with client:
            if mode == "legacy":
                instructions = client.initialize_result.instructions
            else:
                instructions = client.instructions
            prompts = await client.list_prompts()
        return instructions, prompts

    instructions, prompts = asyncio.run(check())
    assert instructions == SERVER_INSTRUCTIONS
    assert prompts == []
