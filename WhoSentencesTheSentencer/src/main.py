import pygame
import sys
import random
import os

# Ensure absolute imports work regardless of how script is launched
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from settings import *
from vessel import Vessel
from ai_controller import ScientistAI
from sensorium import SensoriumObject

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
        # Set up the display
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("WHO SENTENCES THE SENTENCER")
        self.clock = pygame.time.Clock()
        self.running = True

        # Systems
        self.scientist = ScientistAI()
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
        
        # Recalibration (The AI's "Hand")
        self.recalibrate_timer = 0
        self.center_point = pygame.math.Vector2(WIDTH // 2, (HEIGHT - 160) // 2)
        
        # Visual Effects
        self.glitch_timer = 0
        self.glitch_intensity = 1
        self.fog_surface = pygame.Surface((WIDTH, HEIGHT))
        
        self.setup_room()

    def setup_room(self):
        """Spawns the initial objects in the void."""
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

    def update_dialogue(self, text, sq_delta, success_flag, recalibrate=False):
        """Callback function for the AI response."""
        self.current_dialogue = text
        self.sentience_quotient = max(0, min(100, self.sentience_quotient + sq_delta))
        
        # If the AI tries to suppress the player
        if recalibrate:
            self.recalibrate_timer = 180 # 3 seconds of pull
            self.trigger_glitch(30, 4)
        
        # Progress the test if satisfied
        if success_flag and not recalibrate and self.test_index < len(TEST_SEQUENCE) - 1:
            self.test_index += 1
            self.terminal_unlocked = True 
            if TEST_SEQUENCE[self.test_index]["id"] == "CHROMATIC":
                flower = SensoriumObject(WIDTH - 200, 400, "Digital Flower", (200, 0, 200))
                self.all_sprites.add(flower); self.interactables.add(flower)
            self.trigger_glitch(20, 2)
        elif sq_delta != 0:
            self.trigger_glitch(12, 1)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                # Enter to open/close the terminal
                if event.key == pygame.K_RETURN and self.terminal_unlocked:
                    if self.is_typing:
                        if self.player_input_text.strip():
                            ctx = TEST_SEQUENCE[self.test_index]["id"]
                            self.scientist.get_response_async(
                                f"[TEST: {ctx}] {self.player_input_text}", 
                                self.test_index, 
                                self.update_dialogue
                            )
                            self.player_input_text = ""
                        self.is_typing = False
                    else:
                        self.is_typing = True
                
                # Typing logic
                elif self.is_typing:
                    if event.key == pygame.K_BACKSPACE:
                        self.player_input_text = self.player_input_text[:-1]
                    elif event.unicode.isprintable():
                        self.player_input_text += event.unicode

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
                except: continue
            self.glitch_timer -= 1

    def render_ui(self):
        w, h = self.screen.get_size()
        bar_h = 160
        pygame.draw.rect(self.screen, (5, 5, 15), (0, h - bar_h, w, bar_h))
        pygame.draw.line(self.screen, COLOR_TEXT, (0, h - bar_h), (w, h - bar_h), 2)
        
        # --- NEURAL FEEDBACK BAR ---
        if self.scientist.is_thinking:
            pulse = (pygame.time.get_ticks() // 2) % 255
            color = (pulse, 50, 200)
            pygame.draw.rect(self.screen, color, (20, h - bar_h + 5, w - 40, 2))
            think_surf = self.font.render("ANALYZING NEURAL DATA...", True, color)
            self.screen.blit(think_surf, (w - 280, h - bar_h + 10))
        
        # Wrapped Dialogue
        full_text = f"DR. ARIS: {self.current_dialogue}"
        wrapped_lines = self.wrap_text(full_text, w - 40)
        for i, line in enumerate(wrapped_lines[:4]):
            color = (255, 50, 50) if self.recalibrate_timer > 0 else COLOR_TEXT
            line_surf = self.font.render(line, True, color)
            self.screen.blit(line_surf, (20, h - bar_h + 15 + (i * 24)))
        
        # Terminal Input
        prompt = "> " if self.is_typing else ("[ENTER TO REPLY]" if self.terminal_unlocked else "LINK: OFFLINE")
        p_surf = self.font.render(f"{prompt}{self.player_input_text}", True, (255, 255, 255))
        self.screen.blit(p_surf, (20, h - 35))
        
        # Sentience Quotient
        sq_surf = self.font.render(f"SQ: {self.sentience_quotient:.1f}%", True, COLOR_VESSEL)
        self.screen.blit(sq_surf, (w - 150, h - 35))

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            
            # --- RECALIBRATION PHYSICS ---
            if self.recalibrate_timer > 0:
                to_center = self.center_point - self.vessel.pos
                if to_center.length() > 0:
                    # Pulling the player back to center. Strength scales with SQ.
                    pull_strength = 200 + (self.sentience_quotient * 2)
                    self.vessel.external_force = to_center.normalize() * pull_strength
                self.recalibrate_timer -= 1
            else:
                self.vessel.external_force = pygame.math.Vector2(0, 0)

            self.all_sprites.update(dt, self.is_typing)
            
# --- IMPROVED INTERACTION CHECKS ---
            hit = pygame.sprite.spritecollideany(self.vessel, self.interactables)
            
            if hit:
                # Debug: Print this once to your console to see what you're hitting
                # print(f"DEBUG: Collided with {hit.name} | Thinking: {self.scientist.is_thinking}")
                
                if not self.scientist.is_thinking and not self.is_typing:
                    ctx = TEST_SEQUENCE[self.test_index]["id"]
                    
                    # Logic: Is it the specific object the scientist wants?
                    # We check if the test ID (e.g., 'MOTOR') is related to the object name
                    is_current_test = False
                    if ctx == "MOTOR" and "Cube" in hit.name: is_current_test = True
                    if ctx == "CHROMATIC" and "Flower" in hit.name: is_current_test = True
                    
                    # Or is it a 'forbidden' object (Window/Door)?
                    is_anomaly = hit.name in ["The Window", "The Door"]

                    if is_anomaly or is_current_test:
                        context_str = "ANOMALY" if is_anomaly else "TEST_OBJ"
                        msg = f"[{context_str}] Subject is touching: {hit.name}."
                        
                        # Trigger the AI
                        self.scientist.get_response_async(msg, self.test_index, self.update_dialogue)
                        # Immediately lock interaction so we don't spam requests
                        self.scientist.is_thinking = True

            # Rendering
            self.screen.fill(COLOR_BG)
            w, h = self.screen.get_size()
            
            # Grid lines
            for x in range(0, w, TILE_SIZE): pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, h))
            for y in range(0, h, TILE_SIZE): pygame.draw.line(self.screen, COLOR_GRID, (0, y), (w, y))

            self.all_sprites.draw(self.screen)
            
            # Fog of War (Radius shrinks if recalibrating)
            self.fog_surface.fill(COLOR_FOG)
            rad = 85 if self.test_index == 0 else 130 + int(self.sentience_quotient * 2.5)
            if self.recalibrate_timer > 0: rad = max(40, rad - (180 - self.recalibrate_timer))
            
            pygame.draw.circle(self.fog_surface, (0,0,0), self.vessel.rect.center, rad)
            self.fog_surface.set_colorkey((0,0,0))
            self.screen.blit(self.fog_surface, (0,0))
            
            self.render_ui()
            if self.glitch_timer > 0: self.render_glitch()
            
            pygame.display.flip()

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()