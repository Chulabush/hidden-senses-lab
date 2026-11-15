"""One adapter per lab. Every adapter exposes: await complete(system, prompt, kind) -> Reply."""
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass


@dataclass
class Reply:
    text: str
    in_tokens: int
    out_tokens: int
    model: str


class ProviderError(Exception):
    pass


class Provider:
    kind = ""
    key_vars: tuple[str, ...] = ()

    def __init__(self, name: str, cfg: dict):
        self.name = name
        self.model = cfg.get("model", "")
        self.cfg = cfg
        self.sem = asyncio.Semaphore(int(cfg.get("concurrency", 4)))

    def missing(self) -> str | None:
        """Reason this provider cannot run, or None if it looks ready."""
        if self.key_vars and not any(os.environ.get(v) for v in self.key_vars):
            return " or ".join(self.key_vars) + " not set"
        return None

    async def complete(self, system: str, prompt: str, kind: str = "") -> Reply:
        async with self.sem:
            return await self._call(system, prompt, kind)

    async def _call(self, system, prompt, kind) -> Reply:
        raise NotImplementedError

    async def list_models(self) -> list[str]:
        return []


class AnthropicProvider(Provider):
    kind = "anthropic"
    key_vars = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
    # Models that accept the server-side refusal fallback.
    FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}

    def _client(self):
        import anthropic

        if not hasattr(self, "_c"):
            self._c = anthropic.AsyncAnthropic(max_retries=4)
        return self._c

    async def _call(self, system, prompt, kind):
        import anthropic

        extra = {}
        if self.model in self.FALLBACK_MODELS:
            # If a safety classifier declines, the API re-runs on a fallback model in the same call.
            extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        try:
            resp = await self._client().beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                output_config={"effort": self.cfg.get("effort", "medium")},
                **extra,
            )
        except anthropic.RateLimitError as e:
            raise ProviderError(f"rate limited after retries: {e}") from e
        except anthropic.APIStatusError as e:
            raise ProviderError(f"HTTP {e.status_code}: {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise ProviderError(f"connection failed: {e}") from e
        if resp.stop_reason == "refusal":
            raise ProviderError("request declined (stop_reason=refusal)")
        text = "".join(b.text for b in resp.content if b.type == "text")
        return Reply(text, resp.usage.input_tokens, resp.usage.output_tokens, resp.model)

    async def list_models(self):
        return [m.id async for m in self._client().models.list()]


class OpenAIProvider(Provider):
    kind = "openai"
    key_vars = ("OPENAI_API_KEY",)

    def _client(self):
        import openai

        if not hasattr(self, "_c"):
            self._c = openai.AsyncOpenAI(max_retries=4)
        return self._c

    async def _call(self, system, prompt, kind):
        import openai

        try:
            resp = await self._client().responses.create(
                model=self.model, instructions=system, input=prompt, max_output_tokens=16000
            )
        except openai.RateLimitError as e:
            raise ProviderError(f"rate limited after retries: {e}") from e
        except openai.APIStatusError as e:
            raise ProviderError(f"HTTP {e.status_code}: {e.message}") from e
        except openai.APIConnectionError as e:
            raise ProviderError(f"connection failed: {e}") from e
        usage = resp.usage
        return Reply(
            resp.output_text or "",
            usage.input_tokens if usage else 0,
            usage.output_tokens if usage else 0,
            resp.model,
        )

    async def list_models(self):
        return [m.id async for m in self._client().models.list()]


class GeminiProvider(Provider):
    kind = "gemini"
    key_vars = ("GEMINI_API_KEY", "GOOGLE_API_KEY")

    def _client(self):
        from google import genai

        if not hasattr(self, "_c"):
            self._c = genai.Client()
        return self._c

    async def _call(self, system, prompt, kind):
        from google.genai import errors, types

        try:
            resp = await self._client().aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=16000),
            )
        except errors.APIError as e:
            raise ProviderError(f"HTTP {e.code}: {e.message}") from e
        usage = resp.usage_metadata
        out = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0) if usage else 0
        return Reply(resp.text or "", (usage.prompt_token_count or 0) if usage else 0, out, self.model)

    async def list_models(self):
        pager = await self._client().aio.models.list()
        return [m.name.removeprefix("models/") async for m in pager]


class CommandProvider(Provider):
    """Subscription route: drives a logged-in vendor CLI. Prompt on stdin, reply on stdout.

    Placeholders in `command`: an argument that is exactly "{system}" receives the system prompt
    (otherwise it is prepended to the prompt); "{out}" is a temp file the CLI writes its reply to.
    """

    kind = "command"
    procs: asyncio.Semaphore | None = None  # cap on CLI processes alive at once, shared by all labs

    def __init__(self, name, cfg):
        super().__init__(name, cfg)
        self.command = list(cfg.get("command") or [])
        self.model = f"{self.command[0]} CLI" if self.command else ""

    def missing(self):
        if not self.command:
            return "no `command` configured"
        return None if shutil.which(self.command[0]) else f"`{self.command[0]}` not found on PATH"

    async def _call(self, system, prompt, kind):
        # Run in an empty folder so the CLI's agent has no files to wander into.
        with tempfile.TemporaryDirectory() as work:
            out_file = os.path.join(work, "reply.txt")
            takes_system = "{system}" in self.command
            argv = [system if a == "{system}" else a.replace("{out}", out_file) for a in self.command]
            stdin = prompt if takes_system else f"{system}\n\n---\n\n{prompt}"
            async with self.procs or asyncio.Semaphore(1):
                proc = await asyncio.create_subprocess_exec(
                    *argv, cwd=work,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                try:
                    out, err = await asyncio.wait_for(proc.communicate(stdin.encode()), self.cfg.get("timeout", 900))
                except asyncio.TimeoutError:
                    raise ProviderError(f"{self.command[0]} timed out (not logged in, or no network?)")
                finally:
                    if proc.returncode is None:  # timed out or cancelled: do not leave the tool running
                        proc.kill()
                        await proc.wait()
            if proc.returncode != 0:
                tail = (err or out).decode(errors="replace").strip()[-400:]
                raise ProviderError(f"{self.command[0]} exit {proc.returncode}: {tail}")
            if os.path.exists(out_file):
                text = open(out_file, encoding="utf-8", errors="replace").read().strip()
            else:
                text = out.decode(errors="replace").strip()
        if not text:
            raise ProviderError(f"{self.command[0]} returned an empty reply")
        # CLIs do not report usage; estimate at ~4 characters per token.
        return Reply(text, len(stdin) // 4, len(text) // 4, self.model)


class MockProvider(Provider):
    """Offline stand-in used by --mock to exercise the pipeline without spending anything."""

    kind = "mock"

    async def _call(self, system, prompt, kind):
        await asyncio.sleep(0.001)
        h = int(hashlib.sha256((self.name + kind + prompt).encode()).hexdigest(), 16)
        if kind == "judge":
            keys = ["novelty", "testability", "mechanism", "survives_known_data"]
            scores = {k: 1 + (h >> (8 * i)) % 10 for i, k in enumerate(keys)}
            text = json.dumps({**scores, "one_line": f"mock verdict from {self.name}"})
        else:
            text = f"[mock {self.name} · {kind}] placeholder text standing in for a real model reply."
        return Reply(text, len(prompt) // 4, len(text) // 4, "mock")


KINDS = {c.kind: c for c in (AnthropicProvider, OpenAIProvider, GeminiProvider, CommandProvider)}


def build(cfg: dict, mock: bool = False) -> list[Provider]:
    out = []
    CommandProvider.procs = asyncio.Semaphore(int(cfg.get("run", {}).get("cli_processes", 2)))
    for name, pcfg in cfg["providers"].items():
        if mock:
            out.append(MockProvider(name, pcfg))
            continue
        cls = KINDS.get(pcfg.get("kind"))
        if cls is None:
            raise SystemExit(f"providers.{name}: unknown kind {pcfg.get('kind')!r} (use {', '.join(KINDS)})")
        out.append(cls(name, pcfg))
    return out
