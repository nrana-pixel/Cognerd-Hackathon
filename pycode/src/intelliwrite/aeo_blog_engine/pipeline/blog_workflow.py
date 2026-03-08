from urllib.parse import urlparse

from utils.log_utils import get_logger
from agents import (
    get_researcher_agent,
    get_planner_agent,
    get_writer_agent,
    get_optimizer_agent,
    get_base_model,
    get_reddit_agent,
    get_linkedin_agent,
    get_twitter_agent,
    get_social_qa_agent,
    get_topic_generator_agent,
)
from agno.agent import Agent
from typing import Optional, Tuple
from intelliwrite.aeo_blog_engine.knowledge.knowledge_base import get_brand_knowledge_base

LOGGER = get_logger(__name__)

try:
    from langfuse import observe, Langfuse
except Exception as langfuse_import_error:
    observe = lambda *args, **kwargs: (lambda func: func)
    Langfuse = None
    LOGGER.warning("Langfuse import failed: %s", langfuse_import_error)

# Initialize Langfuse client
langfuse = None
BRAND_KB = get_brand_knowledge_base()
if Langfuse is not None:
    try:
        langfuse = Langfuse()
    except Exception as langfuse_init_error:
        langfuse = None
        LOGGER.warning("Langfuse disabled: %s", langfuse_init_error)


class AEOBlogPipeline:
    def __init__(self):
        LOGGER.info("Initializing AEO Blog Pipeline with Agno Agents...")

    @staticmethod
    def _is_tool_call_response(text: str) -> bool:
        """Detect when the model emitted a JSON tool-call stub instead of real content.
        This happens when the model enters function-calling mode but has no registered
        callable to execute, so it returns the call schema as raw text."""
        stripped = (text or "").strip()
        # Common patterns: ```json\n{"name": ...}``` or just {"name": ..., "parameters": ...}
        if not stripped:
            return False
        # Strip markdown code fences
        inner = stripped
        if inner.startswith("```"):
            inner = inner.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if inner.startswith("{") and '"name"' in inner and '"parameters"' in inner:
            return True
        return False

    def _build_brand_profile_intro(
        self,
        brand_name: Optional[str] = None,
        brand_url: Optional[str] = None,
        brand_industry: Optional[str] = None,
        brand_location: Optional[str] = None,
    ) -> str:
        lines = []
        if brand_name:
            lines.append(f"- Brand Name: {brand_name}")
        if brand_url:
            lines.append(f"- Brand URL: {brand_url}")
        if brand_industry:
            lines.append(f"- Industry: {brand_industry}")
        if brand_location:
            lines.append(f"- Location: {brand_location}")
        if not lines:
            return ""
        return "Brand Profile:\n" + "\n".join(lines)

    def _summarize_brand_docs(
        self,
        docs,
        brand_name: Optional[str] = None,
        brand_url: Optional[str] = None,
        brand_industry: Optional[str] = None,
        brand_location: Optional[str] = None,
    ) -> str:
        intro = self._build_brand_profile_intro(
            brand_name, brand_url, brand_industry, brand_location
        )
        snippets = []
        for doc in docs[:3]:
            content = (getattr(doc, "content", "") or "").strip()
            if not content:
                continue
            content = content.replace("\r\n", "\n").replace("\r", "\n")
            snippet = " ".join(content.split())
            if len(snippet) > 500:
                snippet = snippet[:500].rstrip() + "\ufffd"
            snippets.append(f"- {snippet}")
        body = "\n".join(snippets) if snippets else ""
        sections = [intro, "Key Brand Knowledge:" if body else "", body]
        return "\n\n".join([section for section in sections if section])

    def _collect_brand_context(
        self,
        topic: str,
        brand_name: Optional[str] = None,
        brand_url: Optional[str] = None,
        brand_industry: Optional[str] = None,
        brand_location: Optional[str] = None,
    ) -> Optional[str]:
        if BRAND_KB is None:
            return None
        filters = {}
        if brand_name:
            filters["brand_name"] = brand_name
        if brand_url:
            filters["brand_url"] = brand_url
        queries = []
        if brand_name:
            queries.append(brand_name)
        if brand_url and brand_url not in queries:
            queries.append(brand_url)
        queries.append(topic)
        for query in queries:
            try:
                docs = BRAND_KB.search(query=query, limit=5, filters=filters or None)
            except Exception as exc:
                LOGGER.warning("Brand KB search failed for '%s': %s", query, exc)
                docs = []
            if docs:
                summary = self._summarize_brand_docs(
                    docs, brand_name, brand_url, brand_industry, brand_location
                )
                if summary:
                    return summary
        return None

    @observe()
    def run(
        self,
        topic: str = None,
        prompt: str = None,
        brand_name: Optional[str] = None,
        brand_url: Optional[str] = None,
        brand_industry: Optional[str] = None,
        brand_location: Optional[str] = None,
    ):
        if not topic and not prompt:
            raise ValueError("Either 'topic' or 'prompt' must be provided.")

        LOGGER.info("--- Starting AEO Blog Generation ---")

        total_input_tokens = 0
        total_output_tokens = 0

        # 0. Topic Generation (if needed)
        topic_gen_response = None
        if prompt and not topic:
            LOGGER.info("[0/5] Generating Topic from Prompt: '%s'...", prompt)
            topic_generator = get_topic_generator_agent()
            topic_gen_response = topic_generator.run(
                f"Generate a blog topic for: {prompt}", stream=False
            )
            topic = topic_gen_response.content.strip()
            LOGGER.info("Generated Topic: %s", topic)

        LOGGER.info("Target Topic: %s", topic)

        brand_context = self._collect_brand_context(
            topic,
            brand_name=brand_name,
            brand_url=brand_url,
            brand_industry=brand_industry,
            brand_location=brand_location,
        )
        brand_intro = self._build_brand_profile_intro(
            brand_name, brand_url, brand_industry, brand_location
        )

        # 1. Research
        LOGGER.info("[1/5] Researching...")

        def _has_research_signal(text: str) -> bool:
            normalized = (text or "").strip().lower()
            if not normalized:
                return False

            failure_markers = [
                "cannot proceed",
                "research was not provided",
                "missing research",
                "need the research",
                "no research",
                "rate limit",
                "temporarily unavailable",
                "quota",
                "i apologize",
                "cannot write the blog",
                "without the research",
                "please provide the research",
                "unavailable right now",
                "try again later",
            ]

            if any(marker in normalized for marker in failure_markers):
                return False

            # Heuristic: very short outputs (e.g., just an apology sentence) are rarely usable research.
            # Require at least ~40 characters and at least 2 sentences/bullets.
            if len(normalized) < 40:
                return False

            signal_delimiters = ["\n-", "\n1.", "\nbullet", "\nâ€¢", "?", ". "]
            delimiter_hits = sum(1 for delim in signal_delimiters if delim in normalized)
            if delimiter_hits == 0:
                return False

            return True

        research_response = None

        if brand_context:
            LOGGER.info("Using brand knowledge base context for research.")
            research_response = None
            research_summary = brand_context or ""
        else:
            researcher = get_researcher_agent()
            research_response = researcher.run(
                f"Research key facts, statistics, and user questions about: {topic}",
                stream=False,
            )
            research_summary = (research_response.content or "").strip()
            LOGGER.debug("[1/5] Research prompt: 'Research key facts... about: %s'", topic)
            LOGGER.debug("[1/5] Research response (%d chars): %.500s", len(research_summary), research_summary)

        if not _has_research_signal(research_summary):
            LOGGER.warning("Research signal missing or insufficient. Falling back to prompt context.")
            research_summary = topic or prompt or ""

        total_input_tokens += getattr(research_response, "input_tokens", 0)
        total_output_tokens += getattr(research_response, "output_tokens", 0)

        # 2. Planning
        LOGGER.info("[2/5] Planning...")
        planner = get_planner_agent()
        plan_prompt_parts = [
            "Create a structured blog outline.",
            f"Topic: {topic}",
            f"Research/Context:\n{research_summary}",
        ]
        if brand_intro:
            plan_prompt_parts.append(f"Brand Info:\n{brand_intro}")
        plan_prompt = "\n\n".join(plan_prompt_parts)
        LOGGER.debug("[2/5] Plan prompt (%.500s)", plan_prompt)
        plan_response = planner.run(plan_prompt, stream=False)
        plan = plan_response.content.strip()
        LOGGER.debug("[2/5] Plan response (%d chars): %.500s", len(plan), plan)
        total_input_tokens += getattr(plan_response, "input_tokens", 0)
        total_output_tokens += getattr(plan_response, "output_tokens", 0)

        # 3. Writing (Draft)
        LOGGER.info("[3/5] Writing Draft...")
        writer = get_writer_agent()
        draft_prompt_parts = [
            "Write a detailed blog post following this outline.",
            f"Topic: {topic}",
            f"Outline:\n{plan}",
        ]
        if brand_intro:
            draft_prompt_parts.append(f"Brand Info:\n{brand_intro}")
        if brand_context:
            draft_prompt_parts.append(f"Brand Knowledge:\n{brand_context}")
        draft_prompt = "\n\n".join(draft_prompt_parts)
        LOGGER.debug("[3/5] Draft prompt (%.500s)", draft_prompt)
        draft_response = writer.run(draft_prompt, stream=False)
        draft = (draft_response.content or "").strip()
        LOGGER.debug("[3/5] Draft response (%d chars): %.500s", len(draft), draft)
        total_input_tokens += getattr(draft_response, "input_tokens", 0)
        total_output_tokens += getattr(draft_response, "output_tokens", 0)

        if self._is_tool_call_response(draft):
            LOGGER.error("[3/5] Writer returned a tool-call stub instead of blog text: %s", draft[:200])
            raise RuntimeError(
                "Writer agent returned tool-call JSON instead of blog content. "
                "Check agent tool configuration."
            )
        LOGGER.info("[3/5] Draft written (%d chars)", len(draft))

        # 4. Optimization / Editing
        LOGGER.info("[4/5] Optimizing Draft...")
        optimizer = get_optimizer_agent()
        optimize_prompt_parts = [
            "Improve the draft for clarity, flow, and brand tone. Maintain details.",
            f"Topic: {topic}",
            f"Draft:\n{draft}",
        ]
        if brand_intro:
            optimize_prompt_parts.append(f"Brand Info:\n{brand_intro}")
        optimize_prompt = "\n\n".join(optimize_prompt_parts)
        LOGGER.debug("[4/5] Optimize prompt (%.500s)", optimize_prompt)
        optimize_response = optimizer.run(optimize_prompt, stream=False)
        optimized_blog = (optimize_response.content or "").strip()
        LOGGER.debug("[4/5] Optimize response (%d chars): %.500s", len(optimized_blog), optimized_blog)
        total_input_tokens += getattr(optimize_response, "input_tokens", 0)
        total_output_tokens += getattr(optimize_response, "output_tokens", 0)

        if self._is_tool_call_response(optimized_blog):
            LOGGER.warning("[4/5] Optimizer returned tool-call stub; keeping original draft.")
            optimized_blog = draft
        else:
            LOGGER.info("[4/5] Optimization done (%d chars)", len(optimized_blog))

        # 5. Final Output
        LOGGER.info("[5/5] Finalizing Blog...")
        LOGGER.info(
            "Token Usage Summary: input=%s, output=%s",
            total_input_tokens,
            total_output_tokens,
        )

        return optimized_blog

    def generate_topic_only(self, prompt: str) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt is required to generate a topic")
        topic_generator = get_topic_generator_agent()
        response = topic_generator.run(
            f"Generate a blog topic for: {prompt}", stream=False
        )
        topic = (response.content or "").strip()
        if not topic:
            raise RuntimeError("Topic generation returned empty response")
        return topic

    @observe()
    def run_social_post(
        self,
        topic: str,
        platform: str,
        brand_name: Optional[str] = None,
        brand_url: Optional[str] = None,
        brand_industry: Optional[str] = None,
        brand_location: Optional[str] = None,
    ) -> str:
        LOGGER.info("Generating social media post", extra={"platform": platform})

        brand_context = self._collect_brand_context(
            topic,
            brand_name=brand_name,
            brand_url=brand_url,
            brand_industry=brand_industry,
            brand_location=brand_location,
        )
        brand_intro = self._build_brand_profile_intro(
            brand_name, brand_url, brand_industry, brand_location
        )

        research_summary = ""
        if not brand_context:
            LOGGER.info("Brand knowledge missing; running lightweight research fallback.")
            try:
                researcher = get_researcher_agent()
                research_response = researcher.run(
                    f"Research quick facts, features, and user benefits about: {topic}",
                    stream=False,
                )
                research_summary = (research_response.content or "").strip()
            except Exception as exc:
                LOGGER.warning("Social post research fallback failed: %s", exc)
                research_summary = ""

        social_kwargs = {
            "topic": topic,
            "brand_name": brand_name,
            "brand_url": brand_url,
        }

        def _safe_social_run(agent_callable):
            try:
                response = agent_callable()
                content = (response.content or "").strip()
                if content:
                    return content
            except Exception as exc:
                LOGGER.error("Social post generation failed via LLM: %s", exc)
            return None

        def _fallback_social_post() -> str:
            brand_bits = []
            if brand_name:
                brand_bits.append(brand_name)
            if brand_url:
                parsed = urlparse(brand_url)
                if parsed.netloc:
                    brand_bits.append(parsed.netloc)
                else:
                    brand_bits.append(brand_url)
            brand_label = " - ".join(brand_bits) if brand_bits else ""
            topic_snippet = topic if len(topic) <= 110 else topic[:107] + "..."

            if platform == "twitter":
                core = f"{topic_snippet}. Style for every vibe"
                hashtags = ["StyleRotation", "Nike"]
                if brand_name and " " not in brand_name:
                    hashtags.insert(0, brand_name)
                tag_block = " " + " ".join(f"#{tag}" for tag in hashtags)
                tweet = f"{core}{tag_block}"
                return tweet[:280]

            if platform == "linkedin":
                parts = [topic_snippet]
                if brand_label:
                    parts.append(brand_label)
                parts.append("â€¢ Highlight one hero piece per style")
                parts.append("â€¢ Keep the copy inclusive")
                parts.append("â€¢ Close with a question to spark saves")
                return "\n\n".join(parts)

            if platform == "reddit":
                return (
                    f"{topic_snippet}\n\n"
                    "Whatâ€™s your go-to Nike fit for city strolls vs. night outs?"
                )

            return topic_snippet

        agent: Optional[Agent] = None
        if platform == "twitter":
            agent = get_twitter_agent()
        elif platform == "linkedin":
            agent = get_linkedin_agent()
        elif platform == "reddit":
            agent = get_reddit_agent()
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        prompt_sections = [
            f"Platform: {platform}",
            f"Topic: {topic}",
        ]
        if brand_intro:
            prompt_sections.append(f"Brand Info:\n{brand_intro}")
        if brand_context:
            prompt_sections.append(f"Brand Knowledge:\n{brand_context}")
        elif research_summary:
            prompt_sections.append(f"Research Summary:\n{research_summary}")
        prompt_sections.append(
            "Guidance: Write a platform-appropriate post using the context above."
            " Never mention missing informationâ€”if details are sparse, deliver the best possible post"
            " using general insights. Keep tone aligned with the platform and encourage engagement."
        )
        prompt = "\n\n".join(section for section in prompt_sections if section)

        llm_output = _safe_social_run(lambda: agent.run(prompt, **social_kwargs))
        if llm_output:
            return llm_output

        LOGGER.warning(
            "LLM social post failed for %s. Returning deterministic fallback message.",
            platform,
        )
        return _fallback_social_post()

    @observe()
    def run_social_qa(
        self,
        topic: str,
        platform: str,
        question: str,
        brand_name: Optional[str] = None,
        brand_url: Optional[str] = None,
        brand_industry: Optional[str] = None,
        brand_location: Optional[str] = None,
    ) -> Tuple[str, str]:
        LOGGER.info("Generating social Q&A", extra={"platform": platform})

        brand_context = self._collect_brand_context(
            topic,
            brand_name=brand_name,
            brand_url=brand_url,
            brand_industry=brand_industry,
            brand_location=brand_location,
        )
        brand_intro = self._build_brand_profile_intro(
            brand_name, brand_url, brand_industry, brand_location
        )

        agent_kwargs = {}
        if platform == "twitter":
            agent = get_twitter_agent()
        elif platform == "linkedin":
            agent = get_linkedin_agent()
        elif platform == "reddit":
            agent = get_reddit_agent()
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        qa_agent = get_social_qa_agent()
        qa_prompt_parts = [
            f"Question: {question}",
            f"Topic Context: {topic}",
        ]
        if brand_context:
            qa_prompt_parts.append(f"Brand Knowledge:\n{brand_context}")
        if brand_intro:
            qa_prompt_parts.append(f"Brand Info:\n{brand_intro}")
        qa_prompt = "\n\n".join(qa_prompt_parts)
        qa_response = qa_agent.run(qa_prompt, **agent_kwargs)
        qa_answer = qa_response.content.strip()

        return question, qa_answer
