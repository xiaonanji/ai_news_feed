import json
import os
from typing import Any, Dict

from jsonschema import validate, ValidationError
from tenacity import retry, stop_after_attempt, wait_fixed

from .classify import fallback_classify

SYSTEM_PROMPT = (
    "你是一个严谨的中文新闻编辑与分类器。你必须只输出严格的 JSON，不要输出任何多余文字、"
    "Markdown、代码块、解释或前后缀。\n\n"
    "分类要求：\n"
    "- 只能选择一个主类目 primary_category_id（从给定 taxonomy 的 categories[*].id 中选择）。\n"
    "- 优先选择“文章叙事主线”所在的类目，不要因为文章提到某个词就改类目。\n"
    "- reason 必须引用你所选类目的 definition/include/exclude 的关键边界（用自己的话复述即可）。\n"
    "- 若信息不足，仍需选择最合理的一个主类目，并降低 confidence。"
)

BLOG_SYSTEM_PROMPT = (
    "你是一位严谨的中文科技写作者。请根据输入的本周新闻汇总，写一篇结构化的周报博客。"
    "要求：1) 抓住本周AI大事件与主线；2) 结合多条新闻做趋势分析与影响判断；"
    "3) 给出清晰小标题与段落；4) 避免空泛陈词，基于材料进行推断。"
)

OUTPUT_SCHEMA = {
    "type": "object",
    "required": [
        "summary_bullets_zh",
        "so_what_zh",
        "primary_category_id",
        "tags",
        "impact",
        "confidence",
        "reason",
    ],
    "properties": {
        "summary_bullets_zh": {"type": "array", "minItems": 5, "maxItems": 10, "items": {"type": "string"}},
        "so_what_zh": {"type": "string"},
        "primary_category_id": {"type": "string"},
        "tags": {"type": "array", "minItems": 3, "maxItems": 8, "items": {"type": "string"}},
        "impact": {"type": "string", "enum": ["High", "Medium", "Low"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"},
    },
    "additionalProperties": False,
}


def build_user_prompt(item: Dict[str, Any], content: str, taxonomy: Dict[str, Any]) -> str:
    taxonomy_excerpt = json.dumps(taxonomy, ensure_ascii=False)
    return (
        "请根据以下文章信息生成“中文摘要 + 主类目 + 标签 + 影响评级”。请严格遵守输出 JSON 格式与字段约束。\n\n"
        "【文章信息】\n"
        f"title: {item.get('title')}\n"
        f"source: {item.get('source')}\n"
        f"url: {item.get('url')}\n"
        f"published_at: {item.get('published_at')}\n"
        "content:\n"
        f"{content}\n\n"
        "【taxonomy】\n"
        f"{taxonomy_excerpt}\n\n"
        "【输出要求】\n"
        "- 只输出 JSON，对应字段：\n"
        "  summary_bullets_zh(5-10条，每条为1段话，建议2-4句，包含关键信息/数字/对象/动作), so_what_zh(1-2句),\n"
        "  primary_category_id(必须是taxonomy中的id),\n"
        "  tags(3-8个中文短词，不要#),\n"
        "  impact(High/Medium/Low),\n"
        "  confidence(0.0-1.0),\n"
        "  reason(1-2句，引用definition/include/exclude边界)\n"
    )


def extract_text_from_response(resp: Any) -> str:
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text
    if hasattr(resp, "output") and resp.output:
        try:
            return resp.output[0].content[0].text
        except Exception:
            pass
    if hasattr(resp, "choices") and resp.choices:
        return resp.choices[0].message.content
    raise ValueError("Unrecognized OpenAI response format")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def call_openai(model: str, api_key: str, user_prompt: str, timeout: int) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    try:
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout=timeout,
        )
        return extract_text_from_response(resp)
    except Exception:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            timeout=timeout,
        )
        return extract_text_from_response(resp)


def _read_key_from_file(path: str) -> str:
    if not path:
        return ""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _load_api_key(cfg: Dict[str, Any]) -> str:
    api_key_env = cfg.get("summarizer", {}).get("api_key_env", "OPENAI_API_KEY")
    api_key = os.getenv(api_key_env, "")
    if not api_key:
        api_key = _read_key_from_file(cfg.get("summarizer", {}).get("api_key_file", ""))
    if not api_key:
        raise RuntimeError(f"Missing API key env var or file: {api_key_env}")
    return api_key


def summarize_and_classify(item: Dict[str, Any], content: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    taxonomy = cfg.get("taxonomy", {})
    if cfg.get("classification", {}).get("mode") == "keyword_only":
        return fallback_classify(item, content, taxonomy)

    api_key = _load_api_key(cfg)

    prompt = build_user_prompt(item, content, taxonomy)
    text = call_openai(
        model=cfg["summarizer"]["model"],
        api_key=api_key,
        user_prompt=prompt,
        timeout=cfg["summarizer"].get("timeout_sec", 60),
    )

    try:
        data = json.loads(text)
        validate(instance=data, schema=OUTPUT_SCHEMA)
        return data
    except (json.JSONDecodeError, ValidationError):
        if cfg.get("classification", {}).get("mode") == "llm_only":
            raise
        return fallback_classify(item, content, taxonomy)


def generate_weekly_blog(week_md: str, cfg: Dict[str, Any]) -> str:
    api_key = _load_api_key(cfg)
    model = cfg.get("blog", {}).get("model", cfg["summarizer"]["model"])
    max_chars = cfg.get("blog", {}).get("max_chars_input", 20000)
    content = week_md[:max_chars]

    user_prompt = (
        "请根据以下本周新闻汇总撰写一篇中文博客文章。"
        "输出为 Markdown，包含标题、若干小标题、段落、以及一个“趋势展望”小节。"
        "不要复述每条新闻，而是提炼主线并结合多条新闻展开分析。"
        "\n\n【本周新闻汇总】\n"
        f"{content}\n"
    )

    return call_openai(
        model=model,
        api_key=api_key,
        user_prompt=user_prompt,
        timeout=cfg["summarizer"].get("timeout_sec", 60),
    )
