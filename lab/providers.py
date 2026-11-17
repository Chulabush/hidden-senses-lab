"""One adapter per lab. Every adapter exposes: await complete(system, prompt, kind) -> Reply."""
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


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


def resolve_command(command):
    executable = shutil.which(command)
    if not executable and os.name == "nt" and "APPDATA" in os.environ:
        executable = shutil.which(command, path=str(Path(os.environ["APPDATA"]) / "npm"))
    return executable


def executable_args(executable):
    """Run standard Windows npm shims through Node without involving cmd.exe."""
    path = Path(executable)
    if os.name != "nt" or path.suffix.lower() not in {".cmd", ".bat"}:
        return [executable]
    packages = {"claude": "@anthropic-ai/claude-code", "codex": "@openai/codex"}
    package = packages.get(path.stem.lower())
    if package:
        root = path.parent / "node_modules" / package
        try:
            entry = json.loads((root / "package.json").read_text(encoding="utf-8"))["bin"]
            entry = entry if isinstance(entry, str) else entry[path.stem.lower()]
        except (OSError, ValueError, KeyError):
            pass
        else:
            target = root / entry
            if target.suffix.lower() == ".exe" and target.is_file():
                return [str(target)]
            node = shutil.which("node")
            if target.suffix.lower() in {".js", ".mjs", ".cjs"} and target.is_file() and node:
                return [node, str(target)]
    raise ProviderError(f"unsupported Windows launcher {path}; install the standard npm package or native executable")


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
        return None if resolve_command(self.command[0]) else f"`{self.command[0]}` not found on PATH"

    async def _call(self, system, prompt, kind):
        # Run in an empty folder so the CLI's agent has no files to wander into.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as work:
            out_file = os.path.join(work, "reply.txt")
            takes_system = "{system}" in self.command
            # As an argument the system prompt goes on one line: Windows command shims break on newlines.
            one_line = " ".join(system.split())
            argv = [one_line if a == "{system}" else a.replace("{out}", out_file) for a in self.command]
            # Use the full path, so Windows finds npm's .cmd launchers.
            argv = executable_args(resolve_command(argv[0]) or argv[0]) + argv[1:]
            if self.name == "codex" and "{out}" not in self.command:
                argv += ["--skip-git-repo-check", "--color", "never", "-o", out_file, "-"]
            elif self.name == "claude" and "--tools" not in self.command:
                argv += ["--tools", "", "--no-session-persistence"]
            stdin = prompt if takes_system else f"{system}\n\n---\n\n{prompt}"
            async with self.procs or asyncio.Semaphore(1):
                proc = await asyncio.create_subprocess_exec(
                    *argv, cwd=work,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                try:
                    out, err = await asyncio.wait_for(proc.communicate(stdin.encode()), self.cfg.get("timeout_seconds", self.cfg.get("timeout", 180)))
                except asyncio.TimeoutError:
                    raise ProviderError(f"{self.command[0]} timed out (not logged in, or no network?)")
                finally:
                    if proc.returncode is None:  # timed out or cancelled: do not leave the tool running
                        proc.kill()
                        await proc.wait()
            if proc.returncode != 0:
                tail = (err + b"\n" + out).decode(errors="replace").strip()[-6000:]
                raise ProviderError(f"{self.command[0]} exit {proc.returncode}: {tail}")
            if os.path.exists(out_file):
                text = open(out_file, encoding="utf-8", errors="replace").read().strip()
            else:
                text = out.decode(errors="replace").strip()
            if "--output-format" in self.command:
                try:
                    data = json.loads(text)
                    if data.get("is_error") or data.get("error"):
                        raise ProviderError(str(data.get("error") or data.get("result") or text))
                    text = data.get("result", data.get("response", ""))
                except (ValueError, AttributeError) as exc:
                    raise ProviderError(f"invalid CLI JSON: {text[-1000:]}") from exc
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
        if kind == "screen":
            text = '{"action":"keep","loophole_class":"B","premise":"Test spin resonance in an existing retinal receptor."}'
        elif kind == "scout":
            text = json.dumps({"potential": h % 101, "hypothesis": "Mock candidate"})
        elif kind == "judge":
            keys = ["novelty", "testability", "mechanism", "survives_known_data"]
            scores = {k: 1 + (h >> (8 * i)) % 10 for i, k in enumerate(keys)}
            text = json.dumps({**scores, "gap_orders": h % 12, "loophole_class": "B", "judge_model": "mock", "one_line": f"mock verdict from {self.name}"})
        else:
            text = f"[mock {self.name} · {kind}] placeholder text standing in for a real model reply."
        return Reply(text, len(prompt) // 4, len(text) // 4, "mock")


KINDS = {c.kind: c for c in (AnthropicProvider, OpenAIProvider, GeminiProvider, CommandProvider)}


def build(cfg: dict, mock: bool = False) -> list[Provider]:
    out = []
    CommandProvider.procs = asyncio.Semaphore(int(cfg.get("run", {}).get("cli_processes", 2)))
    for name, pcfg in cfg["providers"].items():
        if pcfg.get("mode") == "chat_bridge":
            continue
        active = cfg.get("run", {}).get("active_labs")
        if active is not None and name not in active:
            continue
        if name == "gemini" and pcfg.get("kind") == "command":
            raise SystemExit("Gemini CLI is unsupported; use mode = 'chat_bridge'.")
        if mock:
            out.append(MockProvider(name, pcfg))
            continue
        cls = KINDS.get(pcfg.get("kind"))
        if cls is None:
            raise SystemExit(f"providers.{name}: unknown kind {pcfg.get('kind')!r} (use {', '.join(KINDS)})")
        options = {"timeout_seconds": cfg.get("run", {}).get("timeout_seconds", 180), **pcfg}
        out.append(cls(name, options))
    return out
