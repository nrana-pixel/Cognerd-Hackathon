from typing import Optional, List, Any, Dict

from agno.agent import Agent
from agno.models.openai import OpenAIChat
try:
    from agno.models.ollama import Ollama
except ImportError:
    Ollama = None

from utils.utils import read_markdown_file
from intelliwrite.aeo_blog_engine.tools.custom_duckduckgo import CustomDuckDuckGo
from agno.knowledge.knowledge import Knowledge

from config.settings import Config
from intelliwrite.aeo_blog_engine.knowledge.knowledge_base import get_knowledge_base

# Instantiate the Knowledge object using the shared Vector DB
AEO_GEO_RULEBOOK_KB = Knowledge(vector_db=get_knowledge_base())


# --- Gemini Compatibility Layer ---

class GeminiCompatOpenAIChat(OpenAIChat):
    """
    Subclass of OpenAIChat that sanitizes tool definitions for Google Gemini.
    Gemini's OpenAI-compatible endpoint throws 400 if it sees unknown fields
    like 'requires_confirmation' or 'external_execution' in tool definitions.
    """
    def invoke(self, *args, **kwargs):
        if "tools" in kwargs and kwargs["tools"]:
            import copy
            cleaned_tools = []
            for tool in kwargs["tools"]:
                tool_copy = copy.deepcopy(tool)
                if "function" in tool_copy:
                    fn = tool_copy["function"]
                    fn.pop("requires_confirmation", None)
                    fn.pop("external_execution", None)
                cleaned_tools.append(tool_copy)
            kwargs["tools"] = cleaned_tools

        try:
            return super().invoke(*args, **kwargs)
        except AttributeError as exc:
            message = str(exc)
            if "list" in message and "get" in message:
                raise RuntimeError(
                    "Gemini API returned an unexpected error payload (typically when quota is "
                    "exhausted or the request is rate limited). Please check your Gemini "
                    "usage/quota and retry after the suggested cooldown."
                ) from exc
            raise


# --- Base / Helper Functions ---

def _normalize_model_id(provider: str, model_id: str) -> str:
    if provider == "google":
        return model_id.replace("models/", "")
    return model_id


def get_base_model():
    provider = Config.DEFAULT_LLM_PROVIDER
    model_id = _normalize_model_id(provider, Config.DEFAULT_LLM_MODEL)
    api_key = Config.DEFAULT_LLM_API_KEY

    if provider == "ollama":
        return Ollama(
            id=model_id,
            host=Config.OLLAMA_BASE_URL,
            client_params={"headers": {"ngrok-skip-browser-warning": "true"}}
        )
    elif provider == "google":
        return GeminiCompatOpenAIChat(
            id=model_id,
            api_key=api_key,
            base_url=Config.GEMINI_BASE_URL
        )
    else:  # openrouter or openai
        return GeminiCompatOpenAIChat(
            id=model_id,
            api_key=api_key,
            base_url=Config.OPENROUTER_BASE_URL
        )


def get_model(provider: str, model_id: str, api_key: str, base_url: str, max_tokens: int = None):
    normalized_id = _normalize_model_id(provider, model_id)
    if provider == "ollama":
        if Ollama is None:
            raise RuntimeError(
                "Ollama provider requested but agno's Ollama dependency is not installed. "
                "Please `pip install ollama`."
            )
        # Ollama typically uses num_predict for max tokens, but we'll stick to defaults here
        # or it can be passed in client_params if truly needed.
        return Ollama(
            id=normalized_id,
            host=base_url,
            client_params={"headers": {"ngrok-skip-browser-warning": "true"}}
        )
    else:  # google, openrouter, openai
        kwargs = {
            "id": normalized_id,
            "api_key": api_key,
            "base_url": base_url
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
            
        return GeminiCompatOpenAIChat(**kwargs)


def create_agent(name: str, system_instruction: str, tools: list = None, knowledge=None, model=None, markdown: bool = True) -> Agent:
    final_tools = tools if tools else []

    if knowledge:
        def search_knowledge_base(query: str) -> str:
            """Searches the knowledge base for relevant information.

            Args:
                query (str): The search query.
            """
            try:
                results = knowledge.search(query=query, num_documents=5)
                return str(results)
            except Exception as e:
                return f"Error searching knowledge base: {str(e)}"

        final_tools.append(search_knowledge_base)
        agent_knowledge = None
    else:
        agent_knowledge = None

    agent = Agent(
        name=name,
        model=model if model else get_base_model(),
        instructions=[system_instruction],
        tools=final_tools,
        knowledge=agent_knowledge,
        markdown=markdown,
    )
    return agent


# --- Agents ---

def get_researcher_agent():
    model = get_model(
        Config.RESEARCHER_PROVIDER,
        Config.RESEARCHER_MODEL,
        Config.RESEARCHER_API_KEY,
        Config.RESEARCHER_BASE_URL,
    )
    return create_agent(
        name="Research Agent",
        model=model,
        system_instruction=read_markdown_file('researcher_agent.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
        tools=[CustomDuckDuckGo()],
    )


def get_planner_agent():
    model = get_model(
        Config.PLANNER_PROVIDER,
        Config.PLANNER_MODEL,
        Config.PLANNER_API_KEY,
        Config.PLANNER_BASE_URL,
    )
    return create_agent(
        name="Planner Agent",
        model=model,
        system_instruction=read_markdown_file('planner_agent.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
    )


def get_writer_agent():
    model = get_model(
        Config.WRITER_PROVIDER,
        Config.WRITER_MODEL,
        Config.WRITER_API_KEY,
        Config.WRITER_BASE_URL,
    )
    # NO knowledge/tools on writer — receives all context in the prompt.
    # Giving it a search tool caused the model to emit JSON tool-call syntax instead of blog text.
    return create_agent(
        name="Writer Agent",
        model=model,
        system_instruction=read_markdown_file('writer_agent.md'),
        knowledge=None,
    )


def get_optimizer_agent():
    model = get_model(
        Config.OPTIMIZER_PROVIDER,
        Config.OPTIMIZER_MODEL,
        Config.OPTIMIZER_API_KEY,
        Config.OPTIMIZER_BASE_URL,
    )
    # NO knowledge/tools on optimizer — receives full draft in the prompt.
    return create_agent(
        name="Optimizer Agent",
        model=model,
        system_instruction=read_markdown_file('optimizer_agent.md'),
        knowledge=None,
    )


def get_qa_agent():
    model = get_model(
        Config.QA_PROVIDER,
        Config.QA_MODEL,
        Config.QA_API_KEY,
        Config.QA_BASE_URL,
    )
    # NO knowledge/tools on QA — receives full draft in the prompt.
    return create_agent(
        name="QA Agent",
        model=model,
        system_instruction=read_markdown_file('qa_agent.md'),
        knowledge=None,
    )


def get_reddit_agent():
    model = get_model(
        Config.WRITER_PROVIDER,
        Config.WRITER_MODEL,
        Config.WRITER_API_KEY,
        Config.WRITER_BASE_URL,
    )
    return create_agent(
        name="Reddit Writer Agent",
        model=model,
        system_instruction=read_markdown_file('social_agents.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
    )


def get_linkedin_agent():
    model = get_model(
        Config.WRITER_PROVIDER,
        Config.WRITER_MODEL,
        Config.WRITER_API_KEY,
        Config.WRITER_BASE_URL,
    )
    return create_agent(
        name="LinkedIn Writer Agent",
        model=model,
        system_instruction=read_markdown_file('social_agents.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
    )


def get_twitter_agent():
    model = get_model(
        Config.WRITER_PROVIDER,
        Config.WRITER_MODEL,
        Config.WRITER_API_KEY,
        Config.WRITER_BASE_URL,
    )
    return create_agent(
        name="Twitter Writer Agent",
        model=model,
        system_instruction=read_markdown_file('social_agents.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
    )


def get_social_qa_agent():
    model = get_model(
        Config.QA_PROVIDER,
        Config.QA_MODEL,
        Config.QA_API_KEY,
        Config.QA_BASE_URL,
    )
    return create_agent(
        name="Social Media QA Agent",
        model=model,
        system_instruction=read_markdown_file('social_agents.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
    )


def get_topic_generator_agent():
    model = get_model(
        Config.PLANNER_PROVIDER,
        Config.PLANNER_MODEL,
        Config.PLANNER_API_KEY,
        Config.PLANNER_BASE_URL,
    )
    return create_agent(
        name="Topic Generator Agent",
        model=model,
        system_instruction=read_markdown_file('topic_generator_agent.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
    )


# --- n8n / GEO / AEO Report Agents ---

def get_website_data_agent():
    model = get_model(
        Config.WEBSITE_DATA_PROVIDER,
        Config.WEBSITE_DATA_MODEL,
        Config.WEBSITE_DATA_API_KEY,
        Config.WEBSITE_DATA_BASE_URL,
    )
    return create_agent(
        name="Website Data Analysis Agent",
        model=model,
        system_instruction=read_markdown_file('website_data_agent.md'),
        knowledge=None,
        markdown=False,
    )


def get_aeo_audit_agent():
    model = get_model(
        Config.AEO_AUDIT_PROVIDER,
        Config.AEO_AUDIT_MODEL,
        Config.AEO_AUDIT_API_KEY,
        Config.AEO_AUDIT_BASE_URL,
    )
    return create_agent(
        name="AEO Audit Agent",
        model=model,
        system_instruction=read_markdown_file('aeo_audit_agent.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
        markdown=False,
    )


def get_enhanced_schema_agent():
    model = get_model(
        Config.ENHANCED_SCHEMA_PROVIDER,
        Config.ENHANCED_SCHEMA_MODEL,
        Config.ENHANCED_SCHEMA_API_KEY,
        Config.ENHANCED_SCHEMA_BASE_URL,
    )
    return create_agent(
        name="Enhanced Schema Agent",
        model=model,
        system_instruction=read_markdown_file('enhanced_schema_agent.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
        markdown=False,
    )


def get_pain_points_agent():
    model = get_model(
        Config.PAIN_POINTS_PROVIDER,
        Config.PAIN_POINTS_MODEL,
        Config.PAIN_POINTS_API_KEY,
        Config.PAIN_POINTS_BASE_URL,
    )
    return create_agent(
        name="Pain Points Agent",
        model=model,
        system_instruction=read_markdown_file('pain_points_agent.md'),
        knowledge=None,
        tools=[CustomDuckDuckGo()],
        markdown=False,
    )


def get_files_gen_agent():
    model = get_model(
        Config.FILES_GEN_PROVIDER,
        Config.FILES_GEN_MODEL,
        Config.FILES_GEN_API_KEY,
        Config.FILES_GEN_BASE_URL,
    )
    return create_agent(
        name="Files Generation Agent",
        model=model,
        system_instruction=read_markdown_file('files_gen_agent.md'),
        knowledge=AEO_GEO_RULEBOOK_KB,
        markdown=False,
    )


def get_faqs_agent():
    model = get_model(
        Config.WRITER_PROVIDER,
        Config.WRITER_MODEL,
        Config.WRITER_API_KEY,
        Config.WRITER_BASE_URL,
        max_tokens=8192,
    )
    return create_agent(
        name="FAQ Generator Agent",
        model=model,
        system_instruction=read_markdown_file('faqs_agent.md'),
        knowledge=None,
        markdown=False,
    )


def get_per_page_summary_agent():
    model = get_model(
        Config.PLANNER_PROVIDER,
        Config.PLANNER_MODEL,
        Config.PLANNER_API_KEY,
        Config.PLANNER_BASE_URL,
    )
    return create_agent(
        name="Per Page Summary Agent",
        model=model,
        system_instruction=read_markdown_file('per_page_summary_agent.md'),
        knowledge=None,
        markdown=False,
    )


def get_competitor_urls_extractor_agent():
    model = get_model(
        Config.PLANNER_PROVIDER,
        Config.PLANNER_MODEL,
        Config.PLANNER_API_KEY,
        Config.PLANNER_BASE_URL,
    )
    return create_agent(
        name="Competitor URLs Extractor Agent",
        model=model,
        system_instruction=read_markdown_file('competitor_urls_extractor_agent.md'),
        knowledge=None,
        tools=None,
        markdown=False,
    )
