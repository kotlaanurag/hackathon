"""StateGraph construction and compilation for Logger Agent."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from config.constants import (
    NODE_COSMOS_WRITER,
    NODE_ERROR_CLASSIFIER,
    NODE_EXCEL_LOADER,
    NODE_LOG_FETCHER,
)
from graph.state import LoggerAgentState
from graph.nodes.log_fetcher import log_fetcher_node
from graph.nodes.excel_loader import excel_loader_node
from graph.nodes.error_classifier import error_classifier_node
from graph.nodes.cosmos_writer import cosmos_writer_node


def build_graph() -> StateGraph:
    """Build and compile the logger agent LangGraph.

    Flow: log_fetcher -> excel_loader -> error_classifier -> cosmos_writer -> END
    """
    graph = StateGraph(LoggerAgentState)

    # Register nodes
    graph.add_node(NODE_LOG_FETCHER, log_fetcher_node)
    graph.add_node(NODE_EXCEL_LOADER, excel_loader_node)
    graph.add_node(NODE_ERROR_CLASSIFIER, error_classifier_node)
    graph.add_node(NODE_COSMOS_WRITER, cosmos_writer_node)

    # Linear flow
    graph.set_entry_point(NODE_LOG_FETCHER)
    graph.add_edge(NODE_LOG_FETCHER, NODE_EXCEL_LOADER)
    graph.add_edge(NODE_EXCEL_LOADER, NODE_ERROR_CLASSIFIER)
    graph.add_edge(NODE_ERROR_CLASSIFIER, NODE_COSMOS_WRITER)
    graph.add_edge(NODE_COSMOS_WRITER, END)

    return graph.compile()


# Pre-compiled graph instance
logger_agent_graph = build_graph()
