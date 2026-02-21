# settings.py
WIDTH, HEIGHT = 1200, 800
WORLD_SIZE = 6000
FPS = 60

# Colors
CLR_BG = (20, 25, 30)
CLR_OOB = (17, 20, 24)  # Faded/desaturated version of background
CLR_PLAYER = (50, 200, 50)
CLR_ENEMY = (200, 50, 50)
CLR_WALL = (100, 100, 100)
# Enemy body segment spacing (pixels) — lower value makes denser trails and more immediate collisions
ENEMY_SEGMENT_SIZE = 2