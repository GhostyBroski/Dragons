import pygame
import random
from settings import *

class Point:
    """A collectible point with a value tier and corresponding color."""
    def __init__(self, pos, tier="normal"):
        self.pos = pygame.Vector2(pos)
        self.tier = tier
        self.created_at = pygame.time.get_ticks()
        if tier == "mythic":
            self.value = 50
            self.color = (255, 0, 0)  # Red
            self.lifetime = 25000
        elif tier == "legendary":
            self.value = 30
            self.color = (255, 255, 0)  # Yellow
            self.lifetime = 22000
        elif tier == "rare":
            self.value = 20
            self.color = (200, 0, 255)  # Purple
            self.lifetime = 20000
        else:  # normal
            self.value = 10
            self.color = (0, 0, 255)  # Blue
            self.lifetime = 15000  # ms before point expires

    def is_expired(self):
        return pygame.time.get_ticks() - self.created_at > self.lifetime

class World:
    def __init__(self):
        # Requirement: Un-movable objects (Obstacles)
        self.obstacles = []
        for _ in range(20):
            w, h = random.randint(100, 300), random.randint(100, 300)
            x, y = random.randint(0, WORLD_SIZE-w), random.randint(0, WORLD_SIZE-h)
            self.obstacles.append(pygame.Rect(x, y, w, h))
            
        # Collectible points - spawn much more frequently with varied tiers
        self.points = []
        # Normal points (majority)
        for _ in range(150):
            pos = (random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50))
            self.points.append(Point(pos, "normal"))
        # Rare points
        for _ in range(40):
            pos = (random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50))
            self.points.append(Point(pos, "rare"))
        # Legendary points
        for _ in range(15):
            pos = (random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50))
            self.points.append(Point(pos, "legendary"))
        # Mythic points
        for _ in range(5):
            pos = (random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50))
            self.points.append(Point(pos, "mythic"))

    def spawn_point(self, pos, tier="normal"):
        self.points.append(Point(pos, tier))

    def get_safe_spawn(self, enemies, margin=100):
        """Return a random location well clear of walls, bounds and nearby enemies.

        The margin parameter keeps the player away from world edges so an
        immediate out‑of‑bounds death is unlikely.  We also check each obstacle
        rect and ensure the spawn point doesn't intersect.  Finally we avoid any
        enemy head position by a fixed buffer so the player doesn't appear
        directly on top of an enemy.
        """
        while True:
            pos = pygame.Vector2(
                random.randint(margin, WORLD_SIZE - margin),
                random.randint(margin, WORLD_SIZE - margin)
            )
            # avoid colliding with obstacles
            head_rect = pygame.Rect(pos.x, pos.y, 20, 20)
            if any(head_rect.colliderect(obs) for obs in self.obstacles):
                continue
            # avoid spawning too close to any enemy head
            too_close = False
            for e in enemies:
                if pos.distance_to(e.pos) < 50:
                    too_close = True
                    break
            if too_close:
                continue
            return pos
    
    def update_points(self):
        """Remove points that have been on the map too long."""
        # This list comprehension keeps only points that haven't expired
        self.points = [pt for pt in self.points if not pt.is_expired()]

    def check_bounds(self, pos):
        # Requirement: Die on collision with outer bounds
        if pos.x < 0 or pos.x > WORLD_SIZE or pos.y < 0 or pos.y > WORLD_SIZE:
            return True
        return False
