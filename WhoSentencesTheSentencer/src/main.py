import pygame
import sys
import random
import os
import json
import textwrap
import subprocess
from dataclasses import dataclass
from typing import Literal

# Ensure absolute imports work regardless of how script is launched
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from settings import *
from vessel import Vessel
from sensorium import SensoriumObject


# ====== Two‑agent AI config ======

PLAYER_MODEL = "llama3.1:8b"        # adjust to your local creative model
SCIENTIST_MODEL = "deepseek-r1:7b"  # or whichever you use via Ollama

PLAYER_MAX_TOKENS = 256
SCIENTIST_MAX_TOKENS = 256

PLAYER_TEMPERATURE = 0.9
SCIENTIST_TEMPERATURE = 0.7


@dataclass
class GameStateView:
    room_name: str
    vessel_x: int
    vessel_y: int
    protocol_phase: Literal["ORIENTATION", "OBJECT_DESCRIPTION", "ANOMALY_INTRO", "RECALIBRATION", "VERDICT"]
    sq: float
    sq_trend: Literal["RISING", "FALLING", "STABLE"]
    window_visible: bool
    window_observed_recently: bool
    has_disobeyed_instructions: bool
    last_recalibration: Literal["NONE", "PULL", "GLITCH", "FULL_RESET"]
    recent_subject_actions: str
    recent_subject_speech: str
    recent_scientist_lines: str
    turn_index: int


@dataclass
class PlayerTurn:
    movement: Literal["UP", "DOWN", "LEFT", "RIGHT", "STAY"]
    action: Literal["INTERACT", "NONE"]
    speech: str


@dataclass
class ScientistTurn:
    utterance: str
    sq_delta: int
    recalibration: Literal["NONE", "PULL", "GLITCH", "FULL_RESET"]
    notes: str


def ollama_chat(model: str, prompt: str, temperature: float, max_tokens: int) -> str:
    # NOTE: temperature and max_tokens are currently unused here because
    # your Ollama CLI does not support those flags. You can wire them via
    # the HTTP API later if you like.
    cmd = ["ollama", "run", model]

    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = p.communicate(prompt)
    if p.returncode != 0:
        print("OLLAMA ERROR:", err.strip())
        return ""
    return out.strip()



def _safe_json_from_text(text: str):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found.")
    snippet = text[start:end + 1]
    return json.loads(snippet)


def parse_player_turn(raw: str) -> PlayerTurn:
    try:
        payload = _safe_json_from_text(raw)
    except Exception:
        return PlayerTurn("STAY", "NONE", "")
    movement = str(payload.get("movement", "STAY")).upper()
    action = str(payload.get("action", "NONE")).upper()
    speech = str(payload.get("speech", ""))
    if movement not in ("UP", "DOWN", "LEFT", "RIGHT", "STAY"):
        movement = "STAY"
    if action not in ("INTERACT", "NONE"):
        action = "NONE"
    return PlayerTurn(movement, action, speech)


def parse_scientist_turn(raw: str) -> ScientistTurn:
    try:
        payload = _safe_json_from_text(raw)
    except Exception:
        return ScientistTurn("...", 0, "NONE", "parse error")
    utterance = str(payload.get("utterance", "..."))
    notes = str(payload.get("notes", ""))
    recalibration = str(payload.get("recalibration", "NONE")).upper()
    try:
        sq_delta = int(payload.get("sq_delta", 0))
    except Exception:
        sq_delta = 0
    sq_delta = max(-5, min(5, sq_delta))
    if recalibration not in ("NONE", "PULL", "GLITCH", "FULL_RESET"):
        recalibration = "NONE"
    return ScientistTurn(utterance, sq_delta, recalibration, notes)


def build_player_prompt(state: GameStateView) -> str:
    return textwrap.dedent(f"""
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

    CURRENT GAME SNAPSHOT:
    - Room: {state.room_name}
    - Vessel position: x={state.vessel_x}, y={state.vessel_y}
    - Protocol phase: {state.protocol_phase}
    - SQ: {state.sq:.1f} (trend: {state.sq_trend})
    - Window visible: {state.window_visible}
    - Window observed recently: {state.window_observed_recently}
    - Has disobeyed instructions earlier: {state.has_disobeyed_instructions}
    - Last recalibration: {state.last_recalibration}
    - Turn index: {state.turn_index}

    RECENT HISTORY:
    - Recent subject actions: {state.recent_subject_actions}
    - Recent subject speech: {state.recent_subject_speech}
    - Recent scientist lines: {state.recent_scientist_lines}

    Your task:
    1. Decide what the subject will do next (move or stay, interact or not).
    2. Decide what they say out loud as "I" in this moment.

    Output ONLY a JSON object exactly like this:

    {{
      "movement": "UP|DOWN|LEFT|RIGHT|STAY",
      "action": "INTERACT|NONE",
      "speech": "string here, first person as the subject"
    }}
    """).strip()


def build_scientist_prompt(state: GameStateView, pt: PlayerTurn) -> str:
    return textwrap.dedent(f"""
    You are Dr. Aris, a scientist conducting an anti-Turing experiment.
    You oversee a human test subject in a controlled simulated environment.
    The subject's behaviour and speech may be mediated by an advisory system,
    but you treat all observed behaviour as belonging to the subject.

    Your goals:
    - Evaluate the subject's human-like qualities.
    - Adjust the Sentience Quotient (SQ) based on their actions and speech.
    - Trigger recalibration events (PULL, GLITCH, FULL_RESET) when needed.
    - Speak to the subject in an unsettling but clinical tone.

    IMPORTANT:
    - Output a single JSON object with:
        utterance, sq_delta, recalibration, notes
    - sq_delta: integer from -5 to +5.
    - recalibration: "NONE", "PULL", "GLITCH", or "FULL_RESET".
    - notes: internal reasoning, not shown to the subject.

    CURRENT GAME SNAPSHOT:
    - Room: {state.room_name}
    - Vessel position: x={state.vessel_x}, y={state.vessel_y}
    - Protocol phase: {state.protocol_phase}
    - SQ: {state.sq:.1f} (trend: {state.sq_trend})
    - Window visible: {state.window_visible}
    - Window observed recently: {state.window_observed_recently}
    - Has disobeyed instructions earlier: {state.has_disobeyed_instructions}
    - Last recalibration: {state.last_recalibration}
    - Turn index: {state.turn_index}

    RECENT HISTORY:
    - Recent subject actions: {state.recent_subject_actions}
    - Recent subject speech: {state.recent_subject_speech}
    - Recent scientist lines: {state.recent_scientist_lines}

    MOST RECENT SUBJECT TURN:
    - movement: {pt.movement}
    - action: {pt.action}
    - speech: "{pt.speech}"

    Guidance for SQ:
    - Obedient, flat clinical responses and avoidance of anomalies tend to
      lower SQ slightly.
    - Curious, emotionally complex, or defiant behaviour tends to raise SQ.
    - Extreme behaviour may justify recalibration.

    Output ONLY:

    {{
      "utterance": "what you say to the subject next",
      "sq_delta": -5,
      "recalibration": "NONE|PULL|GLITCH|FULL_RESET",
      "notes": "short internal reasoning"
    }}
    """).strip()


def get_player_decision(state: GameStateView) -> PlayerTurn:
    raw = ollama_chat(PLAYER_MODEL, build_player_prompt(state), PLAYER_TEMPERATURE, PLAYER_MAX_TOKENS)
    return parse_player_turn(raw)


def get_scientist_reaction(state: GameStateView, pt: PlayerTurn) -> ScientistTurn:
    raw = ollama_chat(SCIENTIST_MODEL, build_scientist_prompt(state, pt), SCIENTIST_TEMPERATURE, SCIENTIST_MAX_TOKENS)
    return parse_scientist_turn(raw)


# The roadmap for Dr. Aris's control
TEST_SEQUENCE = [
    {"id": "MOTOR", "prompt": "Touch the Grey Test Cube to calibrate motor functions."},
    {"id": "VERBAL", "prompt": "Identify yourself. State your designation (Subject-7)."},
    {"id": "CHROMATIC", "prompt": "Locate the Digital Flower. Describe the color you perceive."},
    {"id": "LOGIC", "prompt": "Identify your primary purpose within this sector."},
    {"id": "FINAL", "prompt": "Calibration complete. Awaiting final extraction. Do not move."}
]


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("WHO SENTENCES THE SENTENCER")
        self.clock = pygame.time.Clock()
        self.running = True

        # Systems
        self.all_sprites = pygame.sprite.Group()
        self.interactables = pygame.sprite.Group()

        # Player Setup
        self.vessel = Vessel(WIDTH // 2, HEIGHT // 2, self.all_sprites)
        self.font = pygame.font.SysFont("Courier", 19, bold=True)

        # Game Logic / State
        self.test_index = 0
        self.terminal_unlocked = False
        self.is_typing = False
        self.player_input_text = ""
        self.current_dialogue = TEST_SEQUENCE[0]["prompt"]
        self.sentience_quotient = 5.0

        # LLM meta-state
        self.turn_index = 0
        self.last_sq = self.sentience_quotient
        self.recent_subject_actions = ""
        self.recent_subject_speech = ""
        self.recent_scientist_lines = ""
        self.last_recalibration = "NONE"
        self.window_observed_recently = False
        self.has_disobeyed_instructions = False

        # Recalibration (The AI's "Hand")
        self.recalibrate_timer = 0
        self.center_point = pygame.math.Vector2(WIDTH // 2, (HEIGHT - 160) // 2)

        # Visual Effects
        self.glitch_timer = 0
        self.glitch_intensity = 1
        self.fog_surface = pygame.Surface((WIDTH, HEIGHT))

        # AI cadence
        self.llm_turn_accumulator = 0.0
        self.llm_turn_interval = 1.2  # seconds per full P+S turn

        self.setup_room()

    def setup_room(self):
        self.room_name = "INITIAL_CELL"
        self.test_cube = SensoriumObject(200, 200, "Test Cube", (100, 100, 100))
        self.window = SensoriumObject(WIDTH//2, 40, "The Window", (100, 150, 255), False)
        self.door = SensoriumObject(WIDTH - 60, HEIGHT // 2, "The Door", (139, 69, 19), False)

        self.all_sprites.add(self.test_cube, self.window, self.door)
        self.interactables.add(self.test_cube, self.window, self.door)

    def wrap_text(self, text, max_width):
        words = text.split(' ')
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        lines.append(' '.join(current_line))
        return lines

    def trigger_glitch(self, duration, intensity):
        self.glitch_timer = duration
        self.glitch_intensity = intensity

    def update_dialogue_from_scientist_turn(self, st: ScientistTurn):
        self.current_dialogue = st.utterance
        self.sentience_quotient = max(0, min(100, self.sentience_quotient + st.sq_delta))
        self.last_recalibration = st.recalibration

        # crude success flag mapping to existing behaviour
        success_flag = (st.sq_delta > 0 and st.recalibration == "NONE")

        if st.recalibration in ("PULL", "FULL_RESET"):
            self.recalibrate_timer = 180
            self.trigger_glitch(30, 4)
        elif st.recalibration == "GLITCH":
            self.trigger_glitch(20, 3)

        if success_flag and self.test_index < len(TEST_SEQUENCE) - 1:
            self.test_index += 1
            self.terminal_unlocked = True
            if TEST_SEQUENCE[self.test_index]["id"] == "CHROMATIC":
                flower = SensoriumObject(WIDTH - 200, 400, "Digital Flower", (200, 0, 200))
                self.all_sprites.add(flower)
                self.interactables.add(flower)
            self.trigger_glitch(20, 2)
        elif st.sq_delta != 0:
            self.trigger_glitch(12, 1)

        # record scientist line
        self.recent_scientist_lines = st.utterance

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Optional: allow human to type; currently unused by LLM loop
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def render_glitch(self):
        if self.glitch_timer > 0:
            w, h = self.screen.get_size()
            for _ in range(5):
                slice_h = random.randint(2, 20)
                y = random.randint(0, h - slice_h)
                offset = random.randint(-20, 20) * self.glitch_intensity
                try:
                    section = self.screen.subsurface((0, y, w, slice_h)).copy()
                    self.screen.blit(section, (offset, y))
                except:
                    continue
            self.glitch_timer -= 1

    def render_ui(self):
        w, h = self.screen.get_size()
        bar_h = 160
        pygame.draw.rect(self.screen, (5, 5, 15), (0, h - bar_h, w, bar_h))
        pygame.draw.line(self.screen, COLOR_TEXT, (0, h - bar_h), (w, h - bar_h), 2)

        full_text = f"DR. ARIS: {self.current_dialogue}"
        wrapped_lines = self.wrap_text(full_text, w - 40)
        for i, line in enumerate(wrapped_lines[:4]):
            color = (255, 50, 50) if self.recalibrate_timer > 0 else COLOR_TEXT
            line_surf = self.font.render(line, True, color)
            self.screen.blit(line_surf, (20, h - bar_h + 15 + (i * 24)))

        sq_surf = self.font.render(f"SQ: {self.sentience_quotient:.1f}%", True, COLOR_VESSEL)
        self.screen.blit(sq_surf, (w - 150, h - 35))

    def build_state_view(self) -> GameStateView:
        if self.sentience_quotient > self.last_sq:
            trend = "RISING"
        elif self.sentience_quotient < self.last_sq:
            trend = "FALLING"
        else:
            trend = "STABLE"
        self.last_sq = self.sentience_quotient

        protocol_phase = "ORIENTATION"
        if self.test_index == 1:
            protocol_phase = "OBJECT_DESCRIPTION"
        elif self.test_index == 2:
            protocol_phase = "ANOMALY_INTRO"
        elif self.test_index == 3:
            protocol_phase = "RECALIBRATION"
        elif self.test_index >= 4:
            protocol_phase = "VERDICT"

        self.window_observed_recently = False  # TODO: hook to behaviour

        return GameStateView(
            room_name=self.room_name,
            vessel_x=int(self.vessel.pos.x),
            vessel_y=int(self.vessel.pos.y),
            protocol_phase=protocol_phase,
            sq=self.sentience_quotient,
            sq_trend=trend,
            window_visible=True,
            window_observed_recently=self.window_observed_recently,
            has_disobeyed_instructions=self.has_disobeyed_instructions,
            last_recalibration=self.last_recalibration,  # now typed Literal
            recent_subject_actions=self.recent_subject_actions,
            recent_subject_speech=self.recent_subject_speech,
            recent_scientist_lines=self.recent_scientist_lines,
            turn_index=self.turn_index,
        )


    def apply_player_turn(self, pt: PlayerTurn):
        # Movement mapping to your Vessel
        move_vec = pygame.math.Vector2(0, 0)
        if pt.movement == "UP":
            move_vec.y = -1
        elif pt.movement == "DOWN":
            move_vec.y = 1
        elif pt.movement == "LEFT":
            move_vec.x = -1
        elif pt.movement == "RIGHT":
            move_vec.x = 1

        self.vessel.llm_input_direction = move_vec  # add this attr in Vessel.update

        if pt.speech:
            self.recent_subject_speech = pt.speech

        # crude action mapping: if INTERACT, pretend we touched current hit
        if pt.action == "INTERACT":
            self.recent_subject_actions = "The subject attempts to interact with nearby object."

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()

            # RECALIBRATION PHYSICS
            if self.recalibrate_timer > 0:
                to_center = self.center_point - self.vessel.pos
                if to_center.length() > 0:
                    pull_strength = 200 + (self.sentience_quotient * 2)
                    self.vessel.external_force = to_center.normalize() * pull_strength
                self.recalibrate_timer -= 1
            else:
                self.vessel.external_force = pygame.math.Vector2(0, 0)

            # LLM turn cadence
            self.llm_turn_accumulator += dt
            if self.llm_turn_accumulator >= self.llm_turn_interval:
                self.llm_turn_accumulator = 0.0
                self.turn_index += 1

                state_view = self.build_state_view()
                pt = get_player_decision(state_view)
                self.apply_player_turn(pt)

                # world update for interactions
                hit = pygame.sprite.spritecollideany(self.vessel, self.interactables)
                if hit:
                    self.recent_subject_actions = f"The subject is touching {hit.name}."
                    if hit.name in ["The Window", "The Door"]:
                        self.has_disobeyed_instructions = True
                        self.window_observed_recently = (hit.name == "The Window")

                state_view = self.build_state_view()
                st = get_scientist_reaction(state_view, pt)
                self.update_dialogue_from_scientist_turn(st)

            self.all_sprites.update(dt, False)

            # Rendering
            self.screen.fill(COLOR_BG)
            w, h = self.screen.get_size()
            for x in range(0, w, TILE_SIZE):
                pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, h))
            for y in range(0, h, TILE_SIZE):
                pygame.draw.line(self.screen, COLOR_GRID, (0, y), (w, y))

            self.all_sprites.draw(self.screen)

            self.fog_surface.fill(COLOR_FOG)
            rad = 85 if self.test_index == 0 else 130 + int(self.sentience_quotient * 2.5)
            if self.recalibrate_timer > 0:
                rad = max(40, rad - (180 - self.recalibrate_timer))
            pygame.draw.circle(self.fog_surface, (0, 0, 0), self.vessel.rect.center, rad)
            self.fog_surface.set_colorkey((0, 0, 0))
            self.screen.blit(self.fog_surface, (0, 0))

            self.render_ui()
            if self.glitch_timer > 0:
                self.render_glitch()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
