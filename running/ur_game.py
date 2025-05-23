from ursina import *
from direct.actor.Actor import Actor
from random import sample, randint
from itertools import cycle

app = Ursina()

# — Window & lighting
window.title = 'Temple Run Style Game'
window.borderless = False
window.fullscreen = False
window.color = color.black

Sky()
DirectionalLight(y=10, z=10, rotation=(45, -45, 45), shadows=True)

# — Score UI
score = 0
score_text = Text(lambda: f"Score: {score}", position=(-0.85, 0.45), scale=2)

# — Ground illusion
ground = Entity(
    model='plane',
    texture='white_cube',
    color=color.gray,
    scale=(20,1,200),    # extend behind and ahead
    texture_scale=(10,100),
    collider='box',
    y=0, z=0
)

# — Player entity holding a Panda3D Actor
player = Entity()
player.collider = 'box'
player.speed = 15
player.actor = Actor(
    "untitled.glb",
    {"run": "untitled.glb"}
)
player.actor.reparentTo(player)
player.actor.setH(180)
player.actor.loop("run")
player.position = Vec3(0, 0, -10)

# — Obstacles: always leave at least one lane open
lanes = [-4, 0, 4]
obstacles = []

# Load coin textures globally
coin_textures = [load_texture(f'coin{i}.png') for i in range(1, 8)]

# Coin class with animation
class Coin(Entity):
    def __init__(self, position=(0,1,0)):
        super().__init__(
            model='quad',
            texture=coin_textures[0],
            position=position,
            scale=1,
            collider='box',
            double_sided=True
        )
        self.texture_cycle = cycle(coin_textures)
        next(self.texture_cycle)  # skip first texture as already set
        self.animation_speed = 10  # frames per second
        self.time_since_last_frame = 0

    def update(self):
        self.time_since_last_frame += time.dt
        if self.time_since_last_frame > 1 / self.animation_speed:
            self.texture = next(self.texture_cycle)
            self.time_since_last_frame = 0
        # Rotate coin slowly around Y-axis for effect
        self.rotation_y += 100 * time.dt

# List to hold coin entities
coins = []

# Helper to create a wave at z — obstacles + coins
def create_wave(z_pos):
    while True:
        num_obstacles = randint(1, 2)
        obs_lanes = sample(lanes, k=num_obstacles)
        # Ensure at least one of the side lanes has an obstacle or only one obstacle
        if -4 in obs_lanes or 4 in obs_lanes or num_obstacles == 1:
            break
    for lane in obs_lanes:
        obstacles.append(Entity(
            model='cube', color=color.red, scale=2,
            position=(lane,1,z_pos), collider='box'
        ))

    # Spawn coins in lanes without obstacles with 50% chance
    coin_lanes = [l for l in lanes if l not in obs_lanes]
    for lane in coin_lanes:
        if randint(0, 1):
            c = Coin(position=(lane, 1, z_pos))
            coins.append(c)

# Initial spawn
spawn_zs = list(range(10, 200, 20))
def spawn_obstacles():
    obstacles.clear()
    for c in coins:
        destroy(c)
    coins.clear()

    for z in spawn_zs:
        create_wave(z)

spawn_obstacles()

# — Game state & restart UI
game_over = False
restart_button = Button("Restart", scale=(.2,.1), visible=False)
restart_button.on_click = lambda: restart_game()
game_over_text = None

# — Input handling: lane slide, jump, restart
def input(key):
    global game_over
    if game_over and key == 'r':
        restart_game()
        return
    if game_over:
        return

    if key == 'a' and player.x > min(lanes):
        player.animate_x(player.x - 4, duration=0.2, curve=curve.out_expo)
    if key == 'd' and player.x < max(lanes):
        player.animate_x(player.x + 4, duration=0.2, curve=curve.out_expo)

    if key == 'space' and abs(player.y) < 0.01:
        player.actor.stop()
        player.animate_y(3, duration=0.3, curve=curve.out_expo)
        invoke(lambda: [setattr(player, 'y', 0), player.actor.loop("run")], delay=0.6)

# — Main update loop
def update():
    global score, game_over
    if game_over:
        return

    # Move forward illusion
    dist = time.dt * player.speed
    player.z += dist
    ground.z = player.z

    # Camera follow
    camera.position = Vec3(player.x, player.y + 4, player.z - 15)
    camera.rotation_x = 15
    camera.look_at(player.position + Vec3(0,2,0))

    # Recycle obstacles and coins when wave passes behind player
    if obstacles and obstacles[0].z < player.z - 10:
        wave_z = obstacles[0].z
        # Remove obstacles at that wave
        to_remove_obs = [o for o in obstacles if o.z == wave_z]
        for o in to_remove_obs:
            destroy(o)
            obstacles.remove(o)

        # Remove coins at that wave
        to_remove_coins = [c for c in coins if abs(c.z - wave_z) < 0.1]
        for c in to_remove_coins:
            destroy(c)
            coins.remove(c)

        # Spawn new wave further ahead
        new_z = wave_z + len(spawn_zs) * 20
        create_wave(new_z)

    # Collision detection with obstacles
    for o in obstacles:
        if player.intersects(o).hit:
            show_game_over()
            game_over = True
            player.actor.stop()
            return

    # Collision detection with coins
    for c in coins:
        if player.intersects(c).hit:
            global score
            score += 10  # Add 10 points per coin
            destroy(c)
            coins.remove(c)

    score = int(player.z + 10)
    score_text.text = f"Score: {score}"

# — Game over display
def show_game_over():
    global game_over_text
    game_over_text = Text(
        "GAME OVER\n(press R to restart)",
        scale=2, origin=(0,0), background=True, color=color.red
    )
    restart_button.visible = True

# — Restart everything
def restart_game():
    global score, game_over, game_over_text
    game_over = False
    score = 0
    restart_button.visible = False

    if game_over_text:
        destroy(game_over_text)
        game_over_text = None

    player.position = Vec3(0, 0, -10)
    player.actor.setH(180)
    player.actor.loop("run")
    ground.z = player.z

    spawn_obstacles()

app.run()
