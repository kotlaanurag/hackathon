"""StateGraph construction and compilation."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from config.constants import (
    NODE_CONTEXT_ASSEMBLER,
    NODE_DATA_ROUTER,
    NODE_EXCEL_MAPPER,
    NODE_INTAKE,
    NODE_JIRA_FETCHER,
    NODE_MD_GENERATOR,
    NODE_REPO_PARSER,
)
from graph.state import AgentState
from graph.nodes.intake import intake_node
from graph.nodes.data_router import data_router_node, route_sources
from graph.nodes.repo_parser import repo_parser_node
from graph.nodes.jira_fetcher import jira_fetcher_node
from graph.nodes.excel_mapper import excel_mapper_node
from graph.nodes.context_assembler import context_assembler_node
from graph.nodes.md_generator import md_generator_node


def build_graph() -> StateGraph:
    """Build and compile the prompt-generator LangGraph."""
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node(NODE_INTAKE, intake_node)
    graph.add_node(NODE_DATA_ROUTER, data_router_node)
    graph.add_node(NODE_REPO_PARSER, repo_parser_node)
    graph.add_node(NODE_JIRA_FETCHER, jira_fetcher_node)
    graph.add_node(NODE_EXCEL_MAPPER, excel_mapper_node)
    graph.add_node(NODE_CONTEXT_ASSEMBLER, context_assembler_node)
    graph.add_node(NODE_MD_GENERATOR, md_generator_node)

    # Edges
    graph.set_entry_point(NODE_INTAKE)
    graph.add_edge(NODE_INTAKE, NODE_DATA_ROUTER)

    # Conditional fan-out from data_router
    graph.add_conditional_edges(
        NODE_DATA_ROUTER,
        route_sources,
        {
            "repo": NODE_REPO_PARSER,
            "jira": NODE_JIRA_FETCHER,
            "excel": NODE_EXCEL_MAPPER,
            "assemble": NODE_CONTEXT_ASSEMBLER,
        },
    )

    # All source nodes converge to context assembler
    graph.add_edge(NODE_REPO_PARSER, NODE_CONTEXT_ASSEMBLER)
    graph.add_edge(NODE_JIRA_FETCHER, NODE_CONTEXT_ASSEMBLER)
    graph.add_edge(NODE_EXCEL_MAPPER, NODE_CONTEXT_ASSEMBLER)

    # Assembler -> Generator -> END
    graph.add_edge(NODE_CONTEXT_ASSEMBLER, NODE_MD_GENERATOR)
    graph.add_edge(NODE_MD_GENERATOR, END)

    return graph.compile()


# Pre-compiled graph instance
prompt_generator_graph = build_graph()
