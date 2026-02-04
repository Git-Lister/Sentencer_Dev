import pygame
from settings import *

class Vessel(pygame.sprite.Sprite):
    def __init__(self, x, y, *groups):
        super().__init__(*groups)
        self.image = pygame.Surface((TILE_SIZE - 4, TILE_SIZE - 4))
        self.image.fill(COLOR_VESSEL)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.pos = pygame.math.Vector2(self.rect.topleft)
        self.direction = pygame.math.Vector2()
        self.external_force = pygame.math.Vector2(0, 0) # Dr. Aris's "Hand"
        self.speed = MOVE_SPEED

    def update(self, dt, is_typing):
        # 1. Player Input
        self.direction = pygame.math.Vector2(0, 0)
        if not is_typing:
            keys = pygame.key.get_pressed()
            self.direction.x = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
            self.direction.y = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
            if self.direction.length() > 0:
                self.direction = self.direction.normalize()

        # 2. Combine Player Movement and Recalibration Force
        total_move = (self.direction * self.speed) + self.external_force
        self.pos += total_move * dt
        
        # 3. Stay in bounds
        self.pos.x = max(0, min(self.pos.x, WIDTH - self.rect.width))
        self.pos.y = max(0, min(self.pos.y, HEIGHT - 160 - self.rect.height))
        self.rect.topleft = (int(self.pos.x), int(self.pos.y))