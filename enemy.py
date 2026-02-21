import pygame
import random
import math
from settings import *


# simple naming utility for leaderboard/enemies
_ADJECTIVES = ["Flaming", "Shadow", "Steel", "Wild", "Mystic", "Dark", "Fierce", "Swift", "Sunny", "Grim"]
_NOUNS = ["Claw", "Wing", "Scale", "Fang", "Storm", "Blaze", "Roar", "Tail", "Heart", "Spine"]

def random_name():
    """Return a two‑word style name with a two‑digit suffix."""
    return f"{random.choice(_ADJECTIVES)}{random.choice(_NOUNS)}{random.randint(10,99)}"


class Enemy:
    def __init__(self, tier="starter"):
        self.name = random_name()
        self.tier = tier
        self.pos = pygame.Vector2(random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50))
        self.dir = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
        
        # Progression Tiers
        if tier == "mythic":
            self.base_speed = 1.0
            self.color = (150, 0, 80)  # Dark purple
            self.score = random.randint(1500, 2000)
        elif tier == "legendary":
            self.base_speed = 1.5
            self.color = (180, 30, 150)  # Purple-red
            self.score = random.randint(1000, 1500)
        elif tier == "ultra":
            self.base_speed = 2.0
            self.color = (220, 50, 50)  # Dark red
            self.score = random.randint(700, 900)
        elif tier == "high":
            self.base_speed = 2.5
            self.color = (200, 30, 30)
            self.score = random.randint(300, 500)  # High tier starts strong
        elif tier == "medium":
            self.base_speed = 4
            self.color = (230, 120, 30)
            self.score = random.randint(100, 200)  # Medium tier starts moderate
        else: # starter
            self.base_speed = 5.5
            self.color = (200, 200, 50)
            self.score = random.randint(10, 50)  # Starter tier starts low
        
        # Initial length using the square root formula for balanced growth
        self.length = 10 + int(math.sqrt(self.score) * 6)

        self.burst_cooldown = 0
        self.BURST_COST_POINTS = 30
        self.BURST_COST_LENGTH = 5
        self.BURST_DISTANCE = 100 # Slightly shorter than player for fairness
        self.BURST_COOLDOWN_MS = 4000

        # Ensure direction is valid and build an extended trail behind the head
        if self.dir.length() == 0:
            self.dir = pygame.Vector2(1, 0)
        segment_size = ENEMY_SEGMENT_SIZE
        self.trail = [ (self.pos - self.dir * (i * segment_size)).xy for i in range(self.length) ]
    
    def burst(self):
        now = pygame.time.get_ticks()
        if now < self.burst_cooldown or self.score < self.BURST_COST_POINTS + 50 or self.length < 15:
            return False
        
        self.score -= self.BURST_COST_POINTS
        self.length -= self.BURST_COST_LENGTH
        self.pos += self.dir * self.BURST_DISTANCE
        self.trail.insert(0, tuple(self.pos))
        self.burst_cooldown = now + self.BURST_COOLDOWN_MS
        return True
    
    @property
    def speed(self):
        """Speed decreases gradually as length increases, starting to be noticeable at high lengths."""
        return max(0.3, self.base_speed - 0.0006 * self.length)

    def grow(self, amount=3):
        self.length += amount
        self.score += 10

    def update_ai(self, player, other_enemies, obstacles, points):
        """Intelligent behavior: hunt, flee, or search for points based on relative strength."""
        detection_range = 300  # How far to look for targets
        
        # Find nearby threats or prey
        closest_threat = None
        closest_threat_dist = float('inf')
        threat_is_dangerous = False
        
        # Check player
        player_dist = self.pos.distance_to(player.pos)
        if player_dist < detection_range:
            if player.length > self.length * 1.1:  # Player is 10% bigger
                threat_is_dangerous = True
            closest_threat = player.pos
            closest_threat_dist = player_dist
        
        # Check other enemies
        for e in other_enemies:
            e_dist = self.pos.distance_to(e.pos)
            if e_dist < detection_range and e_dist > 0:
                if e.length > self.length * 1.2:  # Enemy is 20% bigger
                    threat_is_dangerous = True
                if e_dist < closest_threat_dist:
                    if e.length < self.length * 0.9:  # This enemy is smaller
                        closest_threat = e.pos
                        closest_threat_dist = e_dist
                        threat_is_dangerous = False
        
        # Decide behavior
        new_dir = self.dir.copy()
        
        if closest_threat and closest_threat_dist < detection_range:
            if threat_is_dangerous:
                # Flee from larger threat
                flee_dir = (self.pos - closest_threat).normalize()
                new_dir = flee_dir.lerp(new_dir, 0.3)
            else:
                # Hunt smaller prey
                hunt_dir = (closest_threat - self.pos).normalize()
                new_dir = hunt_dir.lerp(new_dir, 0.2)
        else:
            # Hunt for points - prioritize higher value points
            closest_point = None
            closest_point_dist = float('inf')
            for pt in points:
                pt_dist = self.pos.distance_to(pt.pos)
                # Prioritize higher value: reduce effective distance for valuable points
                # Higher tier points get a bonus (closer effective distance)
                value_bonus = 1.0
                if pt.tier == "mythic":
                    value_bonus = 0.3  # Mythic points worth 3x more distance
                elif pt.tier == "legendary":
                    value_bonus = 0.5
                elif pt.tier == "rare":
                    value_bonus = 0.7
                
                effective_dist = pt_dist * value_bonus
                if effective_dist < closest_point_dist:
                    closest_point = pt.pos
                    closest_point_dist = effective_dist
            
            if closest_point:
                hunt_dir = (closest_point - self.pos).normalize()
                new_dir = hunt_dir.lerp(new_dir, 0.15)
        
        # --- NEW ENEMY BURST LOGIC ---
        # 1. Fleeing Burst: If a dangerous threat is very close
        self.is_bursting = False
        
        # Burst if close to a threat or closing in on prey
        if (threat_is_dangerous and closest_threat_dist < 150) or \
           (not threat_is_dangerous and closest_threat and closest_threat_dist < 100):
            if self.score > 100 and self.length > 20:
                self.is_bursting = True
        
        # --- POINT STEALING LOGIC ---
        closest_point = None
        closest_point_dist = float('inf')
        
        for pt in points:
            pt_dist = self.pos.distance_to(pt.pos)
            
            # Value-based weighting (Mythic points look "closer" to the AI)
            value_bonus = 0.3 if pt.tier == "mythic" else 0.6 if pt.tier == "legendary" else 1.0
            effective_dist = pt_dist * value_bonus
            
            if effective_dist < closest_point_dist:
                closest_point = pt
                closest_point_dist = pt_dist

        if closest_point:
            # Steering toward the point
            hunt_dir = (closest_point.pos - self.pos).normalize()
            self.dir = hunt_dir.lerp(self.dir, 0.15)
            
            # BURST TO STEAL: If it's a high value point and we are close, dash!
            # The AI is smart: it only bursts if the point is worth the cost.
            if closest_point_dist < 150:
                if closest_point.tier in ["mythic", "legendary", "rare"]:
                    if self.score > 100 and self.length > 20:
                        self.is_bursting = True
        
        # --- DEFENSIVE/OFFENSIVE BURST ---
        # If the player is very close and smaller (prey), dash to cut them off
        if player_dist < 100 and player.length < self.length:
            self.is_bursting = True

        # Obstacle avoidance: detect if next move hits an obstacle
        next_pos = self.pos + new_dir * self.speed
        next_rect = pygame.Rect(next_pos.x, next_pos.y, 20, 20)
        will_hit_obstacle = any(next_rect.colliderect(obs) for obs in obstacles)
        
        if will_hit_obstacle:
            # Try to steer around obstacle by rotating direction
            for angle in [45, -45, 90, -90]:
                test_dir = new_dir.rotate(angle)
                test_pos = self.pos + test_dir * self.speed
                test_rect = pygame.Rect(test_pos.x, test_pos.y, 20, 20)
                if not any(test_rect.colliderect(obs) for obs in obstacles):
                    new_dir = test_dir
                    break
        
        

        self.dir = new_dir.normalize()

    def update(self, world=None):
        current_speed = self.speed
        if getattr(self, 'is_bursting', False):
            current_speed *= 2.0
            self.score -= 0.5
            self.length -= 0.1

            self.score = max(0, self.score)
            self.length = max(5, self.length)

            if world and random.random() < 0.1:
                world.spawn_point(self.trail[-1], "normal")
        
        # Wander AI: Occasionally shift direction
        if random.random() < 0.03:
            self.dir = self.dir.rotate(random.randint(-45, 45))
            
        self.pos += self.dir * current_speed
        
        # Keep enemies inside world bounds (bounce logic)
        if self.pos.x < 0 or self.pos.x > WORLD_SIZE: self.dir.x *= -1
        if self.pos.y < 0 or self.pos.y > WORLD_SIZE: self.dir.y *= -1

        # --- FIXED GROWTH & SPACING ---
        if self.score < 100:
            # Gradual linear growth: starts at 10, reaches 40 at score 100
            target_length = 10 + (self.score * 0.3)
        else:
            # Logarithmic-style tapers off: starts at 40 and grows slowly
            # We use sqrt(score - 100) so the transition is smooth
            target_length = 40 + math.sqrt(self.score - 100) * 5

        self.length = min(450, int(target_length))

        # Spacing reduced to 4
        if not self.trail or self.pos.distance_to(pygame.Vector2(self.trail[0])) > 4:
            self.trail.insert(0, tuple(self.pos))

        if len(self.trail) > int(self.length):
            self.trail = self.trail[:int(self.length)]

    def check_bounds_and_obstacles(self, obstacles, world_size):
        """Check if enemy is out of bounds or hit an obstacle. Returns True if dead."""
        if self.pos.x < 0 or self.pos.x > world_size or self.pos.y < 0 or self.pos.y > world_size:
            return True
        head_rect = self.get_head_rect()
        if any(head_rect.colliderect(obs) for obs in obstacles):
            return True
        return False

    def get_head_rect(self):
        return pygame.Rect(self.pos.x, self.pos.y, 20, 20)

    def get_rects(self):
        # Returns all segments as Rects for collision
        return [pygame.Rect(p[0], p[1], 20, 20) for p in self.trail]