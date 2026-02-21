import pygame
from settings import *

class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)

    def update(self, target_pos):
        # Center the camera on the target
        self.offset.x = target_pos.x - WIDTH // 2
        self.offset.y = target_pos.y - HEIGHT // 2

    def apply(self, entity_pos):
        # Translates world coords to screen coords
        return (entity_pos[0] - self.offset.x, entity_pos[1] - self.offset.y)