"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI
import openai

from ..config import Config


class CreditExhaustedException(Exception):
    """Raised when the LLM API returns a 402 Payment Required (out of credits)."""
    pass


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            response = self.client.chat.completions.create(**kwargs)
        except openai.APIStatusError as e:
            if e.status_code == 402:
                raise CreditExhaustedException(
                    f"API credits exhausted (402). Top up your OpenRouter balance and click Resume to continue."
                ) from e
            raise
        
        content = response.choices[0].message.content
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send chat request and parse JSON response.

        Uses three fallback strategies for robustness — some LLMs prefix/suffix
        their JSON with explanation text or wrap it in code fences:

          1. Direct json.loads after stripping ```json fences
          2. Extract content between ```json...``` fences anywhere in response
          3. Find outermost {...} or [...] block via brace matching
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )

        # Strategy 1: strip leading/trailing fences and parse
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strategy 2: find the first ```json...``` block anywhere
        fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', response, re.IGNORECASE)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Strategy 3: find the outermost balanced {...} or [...] block
        for open_char, close_char in [('{', '}'), ('[', ']')]:
            start = response.find(open_char)
            if start == -1:
                continue
            depth = 0
            end = -1
            in_str = False
            esc = False
            for i in range(start, len(response)):
                c = response[i]
                if esc:
                    esc = False
                    continue
                if c == '\\':
                    esc = True
                    continue
                if c == '"':
                    in_str = not in_str
                    continue
                if in_str:
                    continue
                if c == open_char:
                    depth += 1
                elif c == close_char:
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
            if end > start:
                candidate = response[start:end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"LLM returned invalid JSON (no parseable structure found): {response[:500]}")

