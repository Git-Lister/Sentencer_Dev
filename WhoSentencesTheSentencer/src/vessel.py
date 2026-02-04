import pygame
from settings import *


class Vessel(pygame.sprite.Sprite):
    def __init__(self, x, y, *groups):
        super().__init__(*groups)
        self.image = pygame.Surface((TILE_SIZE - 4, TILE_SIZE - 4))
        self.image.fill(COLOR_VESSEL)
        self.rect = self.image.get_rect(topleft=(x, y))

        # Position / movement
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2()
        self.llm_input_direction = pygame.math.Vector2(0, 0)  # from Player LLM
        self.external_force = pygame.math.Vector2(0, 0)       # Dr. Aris's "Hand"
        self.speed = MOVE_SPEED

    def update(self, dt, is_typing):
        # 1. Human input (WASD) if not typing
        human_dir = pygame.math.Vector2(0, 0)
        if not is_typing:
            keys = pygame.key.get_pressed()
            human_dir.x = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
            human_dir.y = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
            if human_dir.length() > 0:
                human_dir = human_dir.normalize()

        # 2. Combine human + LLM directional intent
        combined_dir = human_dir + self.llm_input_direction
        if combined_dir.length() > 0:
            combined_dir = combined_dir.normalize()

        # 3. Apply movement + external force
        total_move = (combined_dir * self.speed) + self.external_force
        self.pos += total_move * dt

        # 4. Stay in bounds
        self.pos.x = max(0, min(self.pos.x, WIDTH - self.rect.width))
        self.pos.y = max(0, min(self.pos.y, HEIGHT - 160 - self.rect.height))
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))
