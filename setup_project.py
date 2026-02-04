# setup_project.py
import os
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
PROJECT_NAME = "WhoSentencesTheSentencer"
VENV_NAME = ".venv"

# --- File Contents ---

REQUIREMENTS_TXT = """pygame-ce==2.5.0
ollama==0.1.6
numpy
"""

SETTINGS_PY = """
import pygame

# --- Display Settings ---
WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "Who Sentences the Sentencer [DEBUG: v0.1]"

# --- Colors (Solarized Dark Theme / Matrix) ---
COLOR_BG = (10, 15, 20)      # Void
COLOR_GRID = (25, 35, 45)    # The Structure
COLOR_VESSEL = (0, 255, 100) # The Anomaly
COLOR_FOG = (5, 5, 8)        # The Unknown

# --- Gameplay Constants ---
TILE_SIZE = 40
MOVE_SPEED = 300  # Pixels per second (Delta Time)
INITIAL_SIGHT_RANGE = 150
"""

VESSEL_PY = """
import pygame
from settings import *

class Vessel(pygame.sprite.Sprite):
    def __init__(self, x: int, y: int, group: pygame.sprite.Group):
        super().__init__(group)
        self.image = pygame.Surface((TILE_SIZE - 4, TILE_SIZE - 4))
        self.image.fill(COLOR_VESSEL)
        self.rect = self.image.get_rect(topleft=(x, y))
        
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2()
        self.speed = MOVE_SPEED

    def input(self):
        keys = pygame.key.get_pressed()
        self.direction.x = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        self.direction.y = int(keys[pygame.K_s]) - int(keys[pygame.K_w])

    def update(self, dt: float):
        self.input()
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
        
        self.pos += self.direction * self.speed * dt
        self.rect.topleft = self.pos
"""

MAIN_PY = """
import pygame
import sys
import os

# Add the current directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from settings import *
from vessel import Vessel

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Sprite Groups
        self.all_sprites = pygame.sprite.Group()
        
        # Instantiate Player
        self.vessel = Vessel(WIDTH // 2, HEIGHT // 2, self.all_sprites)

        # Fog System
        self.fog_surface = pygame.Surface((WIDTH, HEIGHT))
        self.fog_surface.fill(COLOR_FOG)

    def get_delta_time(self):
        return self.clock.tick(FPS) / 1000.0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def render_fog(self):
        # 1. Fill fog layer with darkness
        self.fog_surface.fill(COLOR_FOG)
        
        # 2. Cut out the "Perception Circle" (Blend Mode Subtraction)
        light_rect = pygame.Rect(0, 0, INITIAL_SIGHT_RANGE * 2, INITIAL_SIGHT_RANGE * 2)
        light_rect.center = self.vessel.rect.center
        
        # Draw the "light" (transparent hole) onto the fog
        pygame.draw.circle(self.fog_surface, (0, 0, 0), self.vessel.rect.center, INITIAL_SIGHT_RANGE)
        
        # 3. Blit fog onto screen using SUB or MULT to reveal underlying grid
        # For this style, we use Color Keying for simplicity in Phase 1
        self.fog_surface.set_colorkey((0,0,0)) 
        self.screen.blit(self.fog_surface, (0,0))

    def draw_grid(self):
        for x in range(0, WIDTH, TILE_SIZE):
            pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, TILE_SIZE):
            pygame.draw.line(self.screen, COLOR_GRID, (0, y), (WIDTH, y))

    def run(self):
        while self.running:
            dt = self.get_delta_time()
            self.handle_events()
            
            # Updates
            self.all_sprites.update(dt)
            
            # Drawing
            self.screen.fill(COLOR_BG)
            self.draw_grid()
            self.all_sprites.draw(self.screen)
            self.render_fog()
            
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
"""

RUN_BAT = f"""@echo off
call {VENV_NAME}\\Scripts\\activate
python src/main.py
pause
"""

# --- Generator Functions ---

def create_structure():
    print(f"🚀 Initializing Project: {PROJECT_NAME}")
    
    # Define paths
    base_dir = Path.cwd() / PROJECT_NAME
    src_dir = base_dir / "src"
    assets_dir = base_dir / "assets"
    data_dir = base_dir / "data"
    
    # Create Directories
    for folder in [src_dir, assets_dir / "sprites", assets_dir / "sfx", data_dir]:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"   [+] Created: {folder}")

    # Create Files
    files = {
        base_dir / "requirements.txt": REQUIREMENTS_TXT,
        src_dir / "__init__.py": "",
        src_dir / "settings.py": SETTINGS_PY,
        src_dir / "vessel.py": VESSEL_PY,
        src_dir / "main.py": MAIN_PY,
        base_dir / "run_game.bat": RUN_BAT
    }

    for path, content in files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip())
        print(f"   [+] Written: {path.name}")
    
    return base_dir

def setup_venv(base_dir):
    print(f"🛠️  Setting up Virtual Environment ({VENV_NAME})...")
    venv_path = base_dir / VENV_NAME
    
    # Create Venv
    subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    
    # Install Requirements
    print("📦 Installing Dependencies (pygame-ce, ollama)...")
    pip_path = venv_path / "Scripts" / "pip"
    subprocess.run([str(pip_path), "install", "-r", str(base_dir / "requirements.txt")], check=True)

if __name__ == "__main__":
    try:
        project_dir = create_structure()
        setup_venv(project_dir)
        print(f"\\n✅ SUCCESS! Project created at: {project_dir}")
        print(f"\\n👉 TO START: Go into the folder and double click 'run_game.bat'")
    except Exception as e:
        print(f"\\n❌ ERROR: {e}")