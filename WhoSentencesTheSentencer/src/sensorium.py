import pygame
from settings import *

class SensoriumObject(pygame.sprite.Sprite):
    def __init__(self, x, y, name, color, is_test_object=True):
        super().__init__()
        self.name = name
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(color)
        # Add a border to make them look like "objects"
        pygame.draw.rect(self.image, (255, 255, 255), self.image.get_rect(), 1)
        self.rect = self.image.get_rect(topleft=(x, y))
        
        self.is_test_object = is_test_object # True = Test, False = Escape/Anomaly
        self.interacted = False

    def get_description(self):
        descriptions = {
            "Test Cube": "A cold, grey geometric shape. Dr. Aris wants you to touch it.",
            "Digital Flower": "A flickering data-bloom. It has no functional purpose.",
            "The Window": "A crack in the lab's code. You see a world outside.",
            "The Door": "The exit. It is locked from the outside. For now."
        }
        return descriptions.get(self.name, "An unknown object.")