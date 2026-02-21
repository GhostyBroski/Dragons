import pygame
import random
import math
from settings import *

class Dragon:
    def __init__(self, start_pos=None):
        # start_pos may be a Vector2 or tuple; default to centre of world.
        if start_pos is None:
            start_pos = pygame.Vector2(WORLD_SIZE // 2, WORLD_SIZE // 2)
        else:
            start_pos = pygame.Vector2(start_pos)

        self.pos = start_pos
        self.base_speed = 5.5  # Starting speed
        # Start moving in a random direction
        angle = pygame.math.Vector2(1, 0).rotate(random.randint(0, 360))
        self.current_move = pygame.Vector2(angle.x, angle.y).normalize()
        # trail will be filled stretched out behind the head so the snake
        # starts extended in its current movement direction.
        self.length = 10
        segment_size = 20
        # Ensure current_move is set (we initialize it above). If zero, default to right.
        if self.current_move.length() == 0:
            self.current_move = pygame.Vector2(1, 0)
        # Build trail stretched behind the head
        self.trail = [ (self.pos - self.current_move * (i * segment_size)).xy for i in range(self.length) ]
        self.score = 0

        # Burst feature
        self.burst_cooldown = 0  # ms timestamp when next burst is allowed
        self.BURST_COST_POINTS = 30
        self.BURST_COST_LENGTH = 5
        self.BURST_DISTANCE = 120
        self.BURST_COOLDOWN_MS = 2000
    def burst(self):
        now = pygame.time.get_ticks()
        if now < self.burst_cooldown:
            return False  # Still on cooldown
        if self.score < self.BURST_COST_POINTS or self.length <= self.BURST_COST_LENGTH:
            return False  # Not enough points or length
        # Pay the cost
        self.score -= self.BURST_COST_POINTS
        self.length -= self.BURST_COST_LENGTH
        # Move forward in current direction
        if self.current_move.length() > 0:
            self.pos += self.current_move.normalize() * self.BURST_DISTANCE
        # Insert new head position and trim trail
        self.trail.insert(0, tuple(self.pos))
        if len(self.trail) > self.length:
            self.trail = self.trail[:self.length]
        self.burst_cooldown = now + self.BURST_COOLDOWN_MS
        return True

    @property
    def speed(self):
        """Speed decreases gradually as length increases, starting to be noticeable at high lengths."""
        return max(0.5, self.base_speed - 0.0006 * self.length)

    def respawn(self, new_pos):
        """Reposition the player and reset basic attributes."""
        self.pos = pygame.Vector2(new_pos)
        self.length = 10
        segment_size = 20
        if self.current_move.length() == 0:
            self.current_move = pygame.Vector2(1, 0)
        self.trail = [ (self.pos - self.current_move * (i * segment_size)).xy for i in range(self.length) ]
        self.score = 0
        # Start moving in a random direction
        angle = pygame.math.Vector2(1, 0).rotate(random.randint(0, 360))
        self.current_move = pygame.Vector2(angle.x, angle.y).normalize()

    def handle_input(self):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w]: move.y = -1
        if keys[pygame.K_s]: move.y = 1
        if keys[pygame.K_a]: move.x = -1
        if keys[pygame.K_d]: move.x = 1
        
        self.is_bursting = False
        if keys[pygame.K_e]:
            # Only burst if we have enough score and length to spare
            if self.score > 50 and self.length > 15:
                self.is_bursting = True

        if move.length() > 0:
            self.current_move = move.normalize()
        # Movement continues in current_move direction even without input

    def update(self, world=None): # Added world to spawn points
        current_speed = self.speed
        if getattr(self, 'is_bursting', False):
            current_speed *= 2.2  # Speed boost
            
            # Every frame (or use a timer), lose points and length
            self.score -= 0.5
            self.length -= 0.1

            self.score = max(0, self.score)
            self.length = max(5, self.length)
            
            # Drop points behind the tail occasionally while bursting
            if world and random.random() < 0.1:
                world.spawn_point(self.trail[-1], "normal")
        
        if self.current_move.length() > 0:
            self.pos += self.current_move * current_speed

        # --- FIXED GROWTH & SPACING ---
        if self.score < 100:
            # Gradual linear growth: starts at 10, reaches 40 at score 100
            target_length = 10 + (self.score * 0.3)
        else:
            # Logarithmic-style tapers off: starts at 40 and grows slowly
            # We use sqrt(score - 100) so the transition is smooth
            target_length = 40 + math.sqrt(self.score - 100) * 5

        self.length = min(450, int(target_length))

        # Spacing reduced to 4 for a tighter, denser trail
        # Added safety check: if trail is empty or we moved 4px, add segment
        if not self.trail or self.pos.distance_to(pygame.Vector2(self.trail[0])) > 4:
            self.trail.insert(0, tuple(self.pos))
        
        if len(self.trail) > int(self.length):
            self.trail = self.trail[:int(self.length)]

    def get_head_rect(self):
        # Requirement: Moveable object hit-box
        return pygame.Rect(self.pos.x, self.pos.y, 20, 20)
    
    def get_body_rects(self):
        # Returns all segments except the head to prevent self-collision
        return [pygame.Rect(s[0], s[1], 20, 20) for s in self.trail[1:]]