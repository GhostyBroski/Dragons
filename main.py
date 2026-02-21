import pygame
import random
import sys
import os
import json

# Import our custom modules
from settings import *
from player import Dragon
from enemy import Enemy, random_name
from world import World
from camera import Camera

# File used for storing high scores across runs
_HS_FILE = "highscores.json"
# How many segments from the head are considered 'neck' and ignored for lethal collisions
NECK_SKIP = 0
LETHAL_DISTANCE = 14
LETHAL_DOT_SELF = 0.5
LETHAL_DOT_ENEMY = 0.3

def load_high_scores(max_entries=10):
    if os.path.exists(_HS_FILE):
        try:
            with open(_HS_FILE, "r") as f:
                data = json.load(f)
                # ensure sorted and truncated
                data.sort(key=lambda x: x["score"], reverse=True)
                return data[:max_entries]
        except Exception:
            pass
    # no valid file, create some dummy enemy entries
    dummy = []
    for _ in range(max_entries):
        name = random_name()
        score = random.randint(0, 1000)
        dummy.append({"name": name, "score": score})
    dummy.sort(key=lambda x: x["score"], reverse=True)
    save_high_scores(dummy)
    return dummy


def save_high_scores(list_data):
    try:
        with open(_HS_FILE, "w") as f:
            json.dump(list_data, f)
    except Exception:
        pass


def add_high_score(high_scores, name, score, max_entries=10):
    high_scores.append({"name": name, "score": score})
    high_scores.sort(key=lambda x: x["score"], reverse=True)
    if len(high_scores) > max_entries:
        del high_scores[max_entries:]
    save_high_scores(high_scores)
    return high_scores


def build_session_leaderboard(player, enemies):
    """Build current game session leaderboard from living enemies only.
    
    Player appears on the leaderboard only if they rank in the top 5.
    """
    # Start with all living enemies
    session = []
    for e in enemies:
        session.append({"name": e.name, "score": round(e.score, 1)})
    
    # Add player if they have points
    if player.score > 0:
        session.append({"name": "YOU", "score": round(player.score, 1)})
    
    session.sort(key=lambda x: x["score"], reverse=True)
    return session

def main():
    # --- 1. INITIALIZATION ---
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Dragons: Open World")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 24, bold=True)

    # outer loop permits restarting without tearing down the interpreter
    # load or create persistent leaderboard
    high_scores = load_high_scores()

    while True:
        # --- create a fresh game state ---
        world = World()
        enemies = []
        enemies.append(Enemy("mythic"))
        for _ in range(2):
            enemies.append(Enemy("legendary"))
        for _ in range(3):
            enemies.append(Enemy("ultra"))
        for _ in range(5):
            enemies.append(Enemy("high"))
        for _ in range(8):
            enemies.append(Enemy("medium"))
        for _ in range(15):
            enemies.append(Enemy("starter"))

        # spawn the player somewhere safe and give a short grace period
        spawn = world.get_safe_spawn(enemies)
        player = Dragon(spawn)
        camera = Camera()

        game_state = "playing"
        game_over_reason = ""

        # primary loop for a single run
        while game_state == "playing":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            player.handle_input()

            
            world.update_points() 

            # Maintain a minimum population if it gets too empty
            if len(world.points) < 40:
                spawn_pos = (random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50))
                world.spawn_point(spawn_pos, "normal")

            # update
            player.update(world)
            camera.update(player.pos)
            for e in enemies:
                e.update_ai(player, [en for en in enemies if en != e], world.obstacles, world.points)
                e.update(world)

            # collision checks
            p_head = player.get_head_rect()

            # Only enforce death checks if invulnerability has expired
            now = pygame.time.get_ticks()
            if now >= getattr(player, 'invulnerable_until', 0):
                if world.check_bounds(player.pos):
                    game_state = "gameover"
                    game_over_reason = "Out of Bounds!"
                    # push player's final score
                    add_high_score(high_scores, "YOU", player.score)

            if now >= getattr(player, 'invulnerable_until', 0):
                for obs in world.obstacles:
                    if p_head.colliderect(obs):
                        game_state = "gameover"
                        game_over_reason = "Crashed into a wall!"
                        add_high_score(high_scores, "YOU", player.score)

            # point collection
            for pt in world.points[:]:
                collection_radius = 25 if player.is_bursting else 15
                if player.pos.distance_to(pt.pos) < collection_radius:
                    player.length += 3
                    player.score += pt.value
                    world.points.remove(pt)
                    # spawn a random tier point to replace it
                    tier_choice = random.random()
                    if tier_choice < 0.05:
                        new_tier = "mythic"
                    elif tier_choice < 0.15:
                        new_tier = "legendary"
                    elif tier_choice < 0.35:
                        new_tier = "rare"
                    else:
                        new_tier = "normal"
                    world.spawn_point((random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50)), new_tier)

            # Player self-collision disabled: players will not die from hitting their own body.

            # interactions with enemies
            for e in enemies[:]:
                e_head = e.get_head_rect()
                
                # Check if enemy died by going out of bounds or hitting obstacles
                if e.check_bounds_and_obstacles(world.obstacles, WORLD_SIZE):
                    add_high_score(high_scores, e.name, e.score)
                    for i, pos in enumerate(e.trail):
                        if i % 2 == 0:
                            tier_choice = random.random()
                            if tier_choice < 0.05:
                                pt_tier = "mythic"
                            elif tier_choice < 0.15:
                                pt_tier = "legendary"
                            elif tier_choice < 0.35:
                                pt_tier = "rare"
                            else:
                                pt_tier = "normal"
                            world.spawn_point(pos, pt_tier)
                    tier = e.tier
                    # remove and respawn at a safe location away from player and other enemies
                    if e in enemies:
                        enemies.remove(e)
                    spawn_pos = world.get_safe_spawn(enemies + [player])
                    new_e = Enemy(tier)
                    new_e.pos = spawn_pos
                    if new_e.dir.length() == 0:
                        new_e.dir = pygame.Vector2(1, 0)
                    new_e.trail = [ (new_e.pos - new_e.dir * (i * ENEMY_SEGMENT_SIZE)).xy for i in range(new_e.length) ]
                    enemies.append(new_e)
                    continue
                
                # Enemy self-collision disabled: enemies will not die from hitting their own body.
                
                # Immediate collision: enemy body segment hit player's head
                if now >= getattr(player, 'invulnerable_until', 0):
                    for seg_rect in e.get_rects()[1:]:
                        if p_head.colliderect(seg_rect):
                            game_state = "gameover"
                            game_over_reason = "Bit by another Dragon!"
                            add_high_score(high_scores, "YOU", player.score)
                            break
                # enemy hit player body
                if game_state == "gameover":
                    break

                # Immediate collision: enemy head hits player's body segments
                if now >= getattr(player, 'invulnerable_until', 0):
                    for seg_rect in player.get_body_rects():
                        if e_head.colliderect(seg_rect):
                            # record the fallen enemy's score on the leaderboard
                            add_high_score(high_scores, e.name, e.score)
                            for i, pos in enumerate(e.trail):
                                if i % 2 == 0:
                                    tier_choice = random.random()
                                    if tier_choice < 0.05:
                                        pt_tier = "mythic"
                                    elif tier_choice < 0.15:
                                        pt_tier = "legendary"
                                    elif tier_choice < 0.35:
                                        pt_tier = "rare"
                                    else:
                                        pt_tier = "normal"
                                    world.spawn_point(pos, pt_tier)
                            tier = e.tier
                            if e in enemies:
                                enemies.remove(e)
                            spawn_pos = world.get_safe_spawn(enemies + [player])
                            new_e = Enemy(tier)
                            new_e.pos = spawn_pos
                            if new_e.dir.length() == 0:
                                new_e.dir = pygame.Vector2(1, 0)
                            new_e.trail = [ (new_e.pos - new_e.dir * (i * ENEMY_SEGMENT_SIZE)).xy for i in range(new_e.length) ]
                            enemies.append(new_e)
                            player.score += 50
                            break

                # enemies eat points
                for pt in world.points[:]:
                    if e_head.collidepoint(pt.pos):
                        e.grow()
                        e.score += pt.value - 10  # grow() adds 10, so adjust for actual point value
                        world.points.remove(pt)
                        # spawn replacement
                        tier_choice = random.random()
                        if tier_choice < 0.05:
                            new_tier = "mythic"
                        elif tier_choice < 0.15:
                            new_tier = "legendary"
                        elif tier_choice < 0.35:
                            new_tier = "rare"
                        else:
                            new_tier = "normal"
                        world.spawn_point((random.randint(50, WORLD_SIZE-50), random.randint(50, WORLD_SIZE-50)), new_tier)
                
                # Enemy-to-enemy collisions
                if e in enemies:  # Make sure this enemy still exists
                    for other_e in enemies[:]:
                        if other_e == e or other_e not in enemies:
                            continue
                        # Check if e's head hits other_e's body (immediate rect intersection)
                        for seg_rect in other_e.get_rects()[1:]:
                            if e_head.colliderect(seg_rect):
                                # If e is significantly larger, other_e dies
                                if e.length > other_e.length:
                                    add_high_score(high_scores, other_e.name, other_e.score)
                                    for i, pos in enumerate(other_e.trail):
                                        if i % 2 == 0:
                                            tier_choice = random.random()
                                            if tier_choice < 0.05:
                                                pt_tier = "mythic"
                                            elif tier_choice < 0.15:
                                                pt_tier = "legendary"
                                            elif tier_choice < 0.35:
                                                pt_tier = "rare"
                                            else:
                                                pt_tier = "normal"
                                            world.spawn_point(pos, pt_tier)
                                    if other_e in enemies:
                                        enemies.remove(other_e)
                                    # respawn victim at a safe location
                                    spawn_pos = world.get_safe_spawn(enemies + [player])
                                    new_e = Enemy(other_e.tier)
                                    new_e.pos = spawn_pos
                                    if new_e.dir.length() == 0:
                                        new_e.dir = pygame.Vector2(1, 0)
                                    new_e.trail = [ (new_e.pos - new_e.dir * (i * ENEMY_SEGMENT_SIZE)).xy for i in range(new_e.length) ]
                                    enemies.append(new_e)
                                    e.score += 25
                                elif other_e.length > e.length:
                                    # other_e is larger, e dies
                                    add_high_score(high_scores, e.name, e.score)
                                    for i, pos in enumerate(e.trail):
                                        if i % 2 == 0:
                                            tier_choice = random.random()
                                            if tier_choice < 0.05:
                                                pt_tier = "mythic"
                                            elif tier_choice < 0.15:
                                                pt_tier = "legendary"
                                            elif tier_choice < 0.35:
                                                pt_tier = "rare"
                                            else:
                                                pt_tier = "normal"
                                            world.spawn_point(pos, pt_tier)
                                    if e in enemies:
                                        enemies.remove(e)
                                    spawn_pos = world.get_safe_spawn(enemies + [player])
                                    new_e = Enemy(e.tier)
                                    new_e.pos = spawn_pos
                                    if new_e.dir.length() == 0:
                                        new_e.dir = pygame.Vector2(1, 0)
                                    new_e.trail = [ (new_e.pos - new_e.dir * (i * ENEMY_SEGMENT_SIZE)).xy for i in range(new_e.length) ]
                                    enemies.append(new_e)
                                    other_e.score += 25
                                # If equal size, both die (mutual destruction)
                                else:
                                    add_high_score(high_scores, e.name, e.score)
                                    add_high_score(high_scores, other_e.name, other_e.score)
                                    for i, pos in enumerate(e.trail):
                                        if i % 2 == 0:
                                            tier_choice = random.random()
                                            if tier_choice < 0.05:
                                                pt_tier = "mythic"
                                            elif tier_choice < 0.15:
                                                pt_tier = "legendary"
                                            elif tier_choice < 0.35:
                                                pt_tier = "rare"
                                            else:
                                                pt_tier = "normal"
                                            world.spawn_point(pos, pt_tier)
                                    for i, pos in enumerate(other_e.trail):
                                        if i % 2 == 0:
                                            tier_choice = random.random()
                                            if tier_choice < 0.05:
                                                pt_tier = "mythic"
                                            elif tier_choice < 0.15:
                                                pt_tier = "legendary"
                                            elif tier_choice < 0.35:
                                                pt_tier = "rare"
                                            else:
                                                pt_tier = "normal"
                                            world.spawn_point(pos, pt_tier)
                                    if e in enemies:
                                        enemies.remove(e)
                                    if other_e in enemies:
                                        enemies.remove(other_e)
                                    spawn_pos = world.get_safe_spawn(enemies + [player])
                                    new_e1 = Enemy(e.tier)
                                    new_e1.pos = spawn_pos
                                    if new_e1.dir.length() == 0:
                                        new_e1.dir = pygame.Vector2(1, 0)
                                    new_e1.trail = [ (new_e1.pos - new_e1.dir * (i * ENEMY_SEGMENT_SIZE)).xy for i in range(new_e1.length) ]
                                    enemies.append(new_e1)
                                    spawn_pos2 = world.get_safe_spawn(enemies + [player])
                                    new_e2 = Enemy(other_e.tier)
                                    new_e2.pos = spawn_pos2
                                    if new_e2.dir.length() == 0:
                                        new_e2.dir = pygame.Vector2(1, 0)
                                    new_e2.trail = [ (new_e2.pos - new_e2.dir * (i * ENEMY_SEGMENT_SIZE)).xy for i in range(new_e2.length) ]
                                    enemies.append(new_e2)
                                break

            # Dynamic spawning: if player is untouchably strong, spawn competitive rivals
            max_enemy_score = max([e.score for e in enemies], default=0)
            if player.score > max_enemy_score + 500 and player.score > 1500:
                # Spawn a high-tier dragon with stats matching player's tier
                new_enemy = Enemy("high")
                # Boost its score to be close to player's
                new_enemy.score = player.score - random.randint(50, 150)
                new_enemy.length = 10 + int(new_enemy.score * 0.3)
                # place it safely away from player and other enemies
                spawn_pos = world.get_safe_spawn(enemies + [player])
                new_enemy.pos = spawn_pos
                if new_enemy.dir.length() == 0:
                    new_enemy.dir = pygame.Vector2(1, 0)
                new_enemy.trail = [ (new_enemy.pos - new_enemy.dir * (i * ENEMY_SEGMENT_SIZE)).xy for i in range(new_enemy.length) ]
                enemies.append(new_enemy)

            # rendering
            screen.fill(CLR_BG)
            
            # Draw out-of-bounds area around the world boundaries
            # Top out-of-bounds strip
            pygame.draw.rect(screen, CLR_OOB, (0, 0, WIDTH, max(0, camera.offset.y)))
            # Bottom out-of-bounds strip
            bottom_oob_y = camera.offset.y + WORLD_SIZE - HEIGHT
            if bottom_oob_y > 0:
                pygame.draw.rect(screen, CLR_OOB, (0, max(0, HEIGHT - (WORLD_SIZE - camera.offset.y - HEIGHT)), WIDTH, HEIGHT))
            # Left out-of-bounds strip
            pygame.draw.rect(screen, CLR_OOB, (0, 0, max(0, camera.offset.x), HEIGHT))
            # Right out-of-bounds strip
            right_oob_x = camera.offset.x + WORLD_SIZE - WIDTH
            if right_oob_x > 0:
                pygame.draw.rect(screen, CLR_OOB, (max(0, WIDTH - (WORLD_SIZE - camera.offset.x - WIDTH)), 0, WIDTH, HEIGHT))
            
            # Draw border around the playable world
            world_boundary = pygame.Rect(0, 0, WORLD_SIZE, WORLD_SIZE)
            screen_boundary = pygame.draw.rect(screen, (150, 150, 80), (camera.apply((0, 0)), (WORLD_SIZE, WORLD_SIZE)), 3)
            for obs in world.obstacles:
                pygame.draw.rect(screen, CLR_WALL, (camera.apply(obs.topleft), (obs.width, obs.height)))
            for pt in world.points:
                pygame.draw.circle(screen, pt.color, camera.apply(pt.pos), 5)
            for e in enemies:
                for seg in e.trail:
                    pygame.draw.rect(screen, e.color, (*camera.apply(seg), 20, 20))
            for seg in player.trail:
                pygame.draw.rect(screen, CLR_PLAYER, (*camera.apply(seg), 20, 20))

            # Build and draw live session leaderboard in top-left
            session_lb = build_session_leaderboard(player, enemies)
            lb_x = 20
            lb_y = 20
            for idx, entry in enumerate(session_lb[:5], start=1):
                txt = f"{idx}. {entry['name']} {entry['score']}"
                lb_surf = font.render(txt, True, (200, 200, 200))
                screen.blit(lb_surf, (lb_x, lb_y))
                lb_y += 25
            
            # Player score/length display adjacent to leaderboard
            player_info = f"YOUR SCORE: {player.score:.1f} | LENGTH: {player.length:.1f}"
            player_surf = font.render(player_info, True, (100, 255, 100))
            screen.blit(player_surf, (lb_x + 350, 20))

            # mini-map
            m_size = 150
            m_rect = pygame.Rect(WIDTH - m_size - 20, 20, m_size, m_size)
            pygame.draw.rect(screen, (50, 50, 50), m_rect)
            pygame.draw.rect(screen, (255, 255, 255), m_rect, 1)
            
            # Draw obstacles on minimap
            for obs in world.obstacles:
                obs_map_x = m_rect.x + (obs.x / WORLD_SIZE) * m_size
                obs_map_y = m_rect.y + (obs.y / WORLD_SIZE) * m_size
                obs_map_w = max(1, (obs.width / WORLD_SIZE) * m_size)
                obs_map_h = max(1, (obs.height / WORLD_SIZE) * m_size)
                pygame.draw.rect(screen, (100, 100, 100), (obs_map_x, obs_map_y, obs_map_w, obs_map_h))
            
            # Draw session leaderboard on minimap (top 3 rank indicators)
            session_lb = build_session_leaderboard(player, enemies)
            rank_colors = [(255, 215, 0), (192, 192, 192), (205, 127, 50)]  # Gold, Silver, Bronze
            for rank, entry in enumerate(session_lb[:3]):
                # Find if this entry is a player or enemy
                if entry["name"] == "YOU":
                    pos = player.pos
                else:
                    # Find the enemy with this name
                    for e in enemies:
                        if e.name == entry["name"]:
                            pos = e.pos
                            break
                    else:
                        continue
                
                rank_map_x = m_rect.x + (pos.x / WORLD_SIZE) * m_size
                rank_map_y = m_rect.y + (pos.y / WORLD_SIZE) * m_size
                pygame.draw.circle(screen, rank_colors[rank], (int(rank_map_x), int(rank_map_y)), 5)
                # Draw rank number
                rank_txt = font.render(str(rank + 1), True, (0, 0, 0))
                screen.blit(rank_txt, (int(rank_map_x) - 3, int(rank_map_y) - 6))
            
            # Draw player position on minimap
            p_map_x = m_rect.x + (player.pos.x / WORLD_SIZE) * m_size
            p_map_y = m_rect.y + (player.pos.y / WORLD_SIZE) * m_size
            pygame.draw.circle(screen, (255, 255, 0), (int(p_map_x), int(p_map_y)), 3)

            pygame.display.flip()
            clock.tick(FPS)

        # game over screen
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        # break out of both loops to restart
                        break
                    elif event.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()
            else:
                # executed when the inner loop didn't break; continue the loop
                screen.fill(CLR_BG)
                # display the reason if we have one
                title = "GAME OVER!"
                if game_over_reason:
                    title += f" - {game_over_reason}"
                go_surf = font.render(title, True, (255, 255, 255))
                screen.blit(go_surf, (WIDTH//2 - go_surf.get_width()//2, HEIGHT//2 - 60))

                # show the player's last score
                myscore = font.render(f"Your score: {player.score}", True, (255, 255, 255))
                screen.blit(myscore, (WIDTH//2 - myscore.get_width()//2, HEIGHT//2 - 20))

                hint = font.render("Press R to restart or Q to quit", True, (255, 255, 255))
                screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 20))

                # leaderboard (show session leaderboard: living enemies + player if ranked)
                session_lb = build_session_leaderboard(player, enemies)
                y_off = HEIGHT//2 + 60
                for idx, entry in enumerate(session_lb[:5], start=1):
                    txt = f"{idx}. {entry['name']} {entry['score']}"
                    ls = font.render(txt, True, (255, 255, 255))
                    screen.blit(ls, (WIDTH//2 - ls.get_width()//2, y_off))
                    y_off += 30
                pygame.display.flip()
                clock.tick(FPS)
                continue
            # break from outer game over waiting loop
            break

        # outermost while True simply iterates to start a fresh run

if __name__ == "__main__":
    main()
