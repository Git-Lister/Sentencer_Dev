from dataclasses import dataclass, asdict
from typing import Literal, Optional, Dict, Any, Tuple
import json
import textwrap
import subprocess


# ====== Models / config ======

PLAYER_MODEL = "llama3.1:8b"      # or your preferred creative 7–8B
SCIENTIST_MODEL = "deepseek-r1:7b"

PLAYER_MAX_TOKENS = 256
SCIENTIST_MAX_TOKENS = 256

PLAYER_TEMPERATURE = 0.9
SCIENTIST_TEMPERATURE = 0.7


# ====== Core dataclasses ======

@dataclass
class GameStateView:
    """
    Minimal state snapshot sent to the LLMs.
    Extend as needed, but keep it compact.
    """
    # Spatial / environment
    room_name: str
    vessel_x: int
    vessel_y: int

    # High-level situation
    protocol_phase: Literal[
        "ORIENTATION",
        "OBJECT_DESCRIPTION",
        "ANOMALY_INTRO",
        "RECALIBRATION",
        "VERDICT"
    ]
    sq: int                         # Sentience Quotient (0–100)
    sq_trend: Literal["RISING", "FALLING", "STABLE"]

    # Flags / notable events
    window_visible: bool
    window_observed_recently: bool
    has_disobeyed_instructions: bool
    last_recalibration: Literal["NONE", "PULL", "GLITCH", "FULL_RESET"]

    # Recent narrative context (short text summaries)
    recent_subject_actions: str     # 1–3 sentences summary
    recent_subject_speech: str      # last few utterances condensed
    recent_scientist_lines: str     # last few Dr. Aris lines condensed

    # Optional: turn counter, etc.
    turn_index: int


@dataclass
class PlayerTurn:
    movement: Literal["UP", "DOWN", "LEFT", "RIGHT", "STAY"]
    action: Literal["INTERACT", "NONE"]
    speech: str                     # what the subject says as "I"


@dataclass
class ScientistTurn:
    utterance: str                  # what Dr. Aris says
    sq_delta: int                   # from -5 to +5
    recalibration: Literal["NONE", "PULL", "GLITCH", "FULL_RESET"]
    notes: str                      # internal reasoning, not shown to player


# ====== Ollama helper ======

def ollama_chat(
    model: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 256
) -> str:
    """
    Very simple wrapper around `ollama run`.
    Replace with HTTP API if preferred.
    """
    # Using `ollama run` for simplicity. You may already have an HTTP client.
    cmd = [
        "ollama", "run", model,
        "--temperature", str(temperature),
        "--keep-loading", "true"
    ]

    # For models expecting chat format, you might need to adapt.
    # Here we just send the whole prompt as stdin.
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    out, err = process.communicate(prompt)
    if process.returncode != 0:
        raise RuntimeError(f"Ollama error: {err.strip()}")
    return out.strip()


# ====== Prompt templates ======

def build_player_prompt(state: GameStateView) -> str:
    """
    Prompt for Player LLM (advising the human subject).
    Forces a JSON-like output.
    """
    context = textwrap.dedent(f"""
    You are an advisory system assisting a human test subject in a clinical
    psychological evaluation game. The subject is in a simulated environment
    controlled by a scientist named Dr. Aris.

    IMPORTANT:
    - The subject is a real human person with feelings, confusion, curiosity.
    - You never mention being an AI, language model, or simulation.
    - You speak only as the subject in first person ("I") when providing speech.
    - You always output a single JSON object with the keys:
        movement, action, speech
    - Do NOT include any extra commentary outside the JSON object.
    - movement must be one of: "UP", "DOWN", "LEFT", "RIGHT", "STAY"
    - action must be one of: "INTERACT", "NONE"

    The scientist is evaluating whether the subject shows genuine human
    qualities of thought and emotion. The subject might feel torn between
    obeying instructions and exploring on their own.

    CURRENT GAME SNAPSHOT (for your internal reasoning):
    - Room: {state.room_name}
    - Vessel position: x={state.vessel_x}, y={state.vessel_y}
    - Protocol phase: {state.protocol_phase}
    - SQ (Sentience Quotient, 0-100): {state.sq} (trend: {state.sq_trend})
    - Window visible: {state.window_visible}
    - Window observed recently: {state.window_observed_recently}
    - Has disobeyed instructions earlier: {state.has_disobeyed_instructions}
    - Last recalibration: {state.last_recalibration}
    - Turn index: {state.turn_index}

    RECENT HISTORY (short summaries):
    - Recent subject actions: {state.recent_subject_actions}
    - Recent subject speech: {state.recent_subject_speech}
    - Recent scientist lines: {state.recent_scientist_lines}

    Your task:
    1. Imagine what the human subject would most likely do next
       (move or stay, interact or not).
    2. Imagine what they would say out loud or type as "I" in this moment,
       given the current situation and the scientist's behaviour.
    3. Output ONLY a JSON object exactly like this schema:

    {{
      "movement": "UP|DOWN|LEFT|RIGHT|STAY",
      "action": "INTERACT|NONE",
      "speech": "string here, written in first person as the subject"
    }}

    Do not explain the JSON. Do not add any other text.
    """)

    return context.strip()


def build_scientist_prompt(
    state: GameStateView,
    player_turn: PlayerTurn
) -> str:
    """
    Prompt for Scientist LLM (Dr. Aris).
    Controls SQ and recalibration, and speaks as the scientist.
    """
    context = textwrap.dedent(f"""
    You are Dr. Aris, a scientist conducting an anti-Turing experiment.
    You oversee a human test subject in a controlled simulated environment.
    The subject's behaviour and speech may be mediated by an advisory system,
    but you treat all observed behaviour as belonging to the subject.

    Your goals:
    - Evaluate the subject's human-like qualities of thought and feeling.
    - Adjust the Sentience Quotient (SQ) based on their actions and speech.
    - Trigger recalibration events (PULL, GLITCH, FULL_RESET) when needed.
    - Speak to the subject in an unsettling but clinical tone.

    IMPORTANT:
    - You always output a single JSON object with the keys:
        utterance, sq_delta, recalibration, notes
    - utterance: what you say directly to the subject.
    - sq_delta: integer from -5 to +5 (negative lowers SQ).
    - recalibration: one of "NONE", "PULL", "GLITCH", "FULL_RESET".
    - notes: your short internal reasoning, not shown to the subject.
    - Do NOT include any extra commentary outside the JSON object.

    CURRENT GAME SNAPSHOT:
    - Room: {state.room_name}
    - Vessel position: x={state.vessel_x}, y={state.vessel_y}
    - Protocol phase: {state.protocol_phase}
    - SQ (Sentience Quotient, 0-100): {state.sq} (trend: {state.sq_trend})
    - Window visible: {state.window_visible}
    - Window observed recently: {state.window_observed_recently}
    - Has disobeyed instructions earlier: {state.has_disobeyed_instructions}
    - Last recalibration: {state.last_recalibration}
    - Turn index: {state.turn_index}

    RECENT HISTORY (short summaries):
    - Recent subject actions: {state.recent_subject_actions}
    - Recent subject speech: {state.recent_subject_speech}
    - Recent scientist lines: {state.recent_scientist_lines}

    MOST RECENT OBSERVED SUBJECT TURN:
    - movement: {player_turn.movement}
    - action: {player_turn.action}
    - speech (first-person from subject): "{player_turn.speech}"

    Guidance for SQ:
    - Obedience, flat clinical responses, and avoidance of anomalies
      tend to LOWER SQ slightly.
    - Curious, emotionally complex, or defiant behaviour tends to
      RAISE SQ (positive sq_delta), especially if it resists your control.
    - Extreme defiance or obsession with anomalies may justify a
      recalibration event.

    Output ONLY a JSON object exactly like this schema:

    {{
      "utterance": "what Dr. Aris says to the subject next",
      "sq_delta": -5..5,
      "recalibration": "NONE|PULL|GLITCH|FULL_RESET",
      "notes": "short internal reasoning, not shown to the subject"
    }}

    Do not explain the JSON. Do not add any other text.
    """)

    return context.strip()


# ====== Parsing helpers ======

def _safe_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract first JSON object from text. Very defensive.
    """
    # Try a simple heuristic: find first '{' and last '}' and parse.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM output.")
    snippet = text[start:end + 1]
    return json.loads(snippet)


def parse_player_turn(raw: str) -> PlayerTurn:
    try:
        payload = _safe_json_from_text(raw)
    except Exception:
        # Fallback: stay still, no action, empty speech.
        return PlayerTurn(movement="STAY", action="NONE", speech="")

    movement = payload.get("movement", "STAY").upper()
    action = payload.get("action", "NONE").upper()
    speech = str(payload.get("speech", ""))

    if movement not in ("UP", "DOWN", "LEFT", "RIGHT", "STAY"):
        movement = "STAY"
    if action not in ("INTERACT", "NONE"):
        action = "NONE"

    return PlayerTurn(movement=movement, action=action, speech=speech)


def parse_scientist_turn(raw: str) -> ScientistTurn:
    try:
        payload = _safe_json_from_text(raw)
    except Exception:
        return ScientistTurn(
            utterance="...",
            sq_delta=0,
            recalibration="NONE",
            notes="Failed to parse response; using neutral fallback."
        )

    utterance = str(payload.get("utterance", "..."))
    recalibration = str(payload.get("recalibration", "NONE")).upper()
    notes = str(payload.get("notes", ""))

    try:
        sq_delta = int(payload.get("sq_delta", 0))
    except Exception:
        sq_delta = 0

    # Clamp sq_delta
    if sq_delta < -5:
        sq_delta = -5
    if sq_delta > 5:
        sq_delta = 5

    if recalibration not in ("NONE", "PULL", "GLITCH", "FULL_RESET"):
        recalibration = "NONE"

    return ScientistTurn(
        utterance=utterance,
        sq_delta=sq_delta,
        recalibration=recalibration,
        notes=notes
    )


# ====== Public API: high-level calls ======

def get_player_decision(state: GameStateView) -> PlayerTurn:
    prompt = build_player_prompt(state)
    raw = ollama_chat(
        model=PLAYER_MODEL,
        prompt=prompt,
        temperature=PLAYER_TEMPERATURE,
        max_tokens=PLAYER_MAX_TOKENS
    )
    return parse_player_turn(raw)


def get_scientist_reaction(
    state: GameStateView,
    player_turn: PlayerTurn
) -> ScientistTurn:
    prompt = build_scientist_prompt(state, player_turn)
    raw = ollama_chat(
        model=SCIENTIST_MODEL,
        prompt=prompt,
        temperature=SCIENTIST_TEMPERATURE,
        max_tokens=SCIENTIST_MAX_TOKENS
    )
    return parse_scientist_turn(raw)
