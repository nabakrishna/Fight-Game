import pygame
import sys
from enum import Enum, auto

# -------------- Config --------------
WIDTH, HEIGHT = 960, 540
FPS = 60
GROUND_Y = HEIGHT - 80
GRAVITY = 1.2

MOVE_SPEED = 6
AIR_SPEED = 4
DASH_SPEED = 11
DASH_COST = 30
DASH_DURATION = 12

JUMP_VEL = -18
SHORT_HOP_VEL = -14

# Attacks frame data
# startup: frames before hitbox
# active: frames hitbox exists
# recovery: frames after active where you can't act
MOVES = {
    "light":   {"startup": 5, "active": 6, "recovery": 10, "damage": 7,  "knockback": 10, "hitstop": 6},
    "heavy":   {"startup": 9, "active": 6, "recovery": 18, "damage": 14, "knockback": 18, "hitstop": 9},
    "j_light": {"startup": 4, "active": 8, "recovery": 8,  "damage": 6,  "knockback": 8,  "hitstop": 6},
    "c_light": {"startup": 6, "active": 6, "recovery": 12, "damage": 8,  "knockback": 10, "hitstop": 6},
}

BLOCK_REDUCTION = 0.7      # 70% damage blocked
CHIP_REDUCTION = 0.1       # 10% damage goes through on block
BLOCKSTUN = 12
HITSTUN_LIGHT = 14
HITSTUN_HEAVY = 20
AIR_JUGGLE_STUN = 18
HITSTOP_MAX = 12

ROUND_TIME_SECONDS = 60
ROUNDS_TO_WIN = 2

# UI colors
BLACK = (15, 15, 20)
WHITE = (240, 240, 240)
RED = (220, 60, 60)
GREEN = (60, 200, 90)
BLUE = (70, 160, 255)
YELLOW = (255, 210, 60)
GREY = (120, 120, 120)
PURPLE = (180, 120, 255)
ORANGE = (255, 160, 60)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Python Fighting Game - Extended")
clock = pygame.time.Clock()
font_big = pygame.font.SysFont("arial", 48, bold=True)
font_mid = pygame.font.SysFont("arial", 32, bold=True)
font_small = pygame.font.SysFont("arial", 22, bold=True)

# Optional: load sounds (replace file paths or comment out if not available)
def try_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except:
        return None

SND_HIT = None     # try_sound("assets/hit.wav")
SND_BLOCK = None   # try_sound("assets/block.wav")
SND_KO = None      # try_sound("assets/ko.wav")
SND_START = None   # try_sound("assets/start.wav")
SND_SELECT = None  # try_sound("assets/select.wav")

class GameState(Enum):
    TITLE = auto()
    HOW_TO_PLAY = auto()
    PLAYING = auto()
    PAUSED = auto()
    ROUND_END = auto()
    MATCH_END = auto()

# -------------- Helpers --------------
def draw_health_bar(surf, x, y, w, h, value, max_value, color):
    pct = max(0, min(1, value / max_value))
    bg_rect = pygame.Rect(x, y, w, h)
    fg_rect = pygame.Rect(x, y, int(w * pct), h)
    pygame.draw.rect(surf, GREY, bg_rect, border_radius=6)
    pygame.draw.rect(surf, color, fg_rect, border_radius=6)
    pygame.draw.rect(surf, WHITE, bg_rect, 2, border_radius=6)

def center_text(surface, text, font, color, y, outline=True):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(WIDTH//2, y))
    if outline:
        for ox, oy in [(-2,0),(2,0),(0,-2),(0,2)]:
            o = font.render(text, True, (0,0,0))
            orect = o.get_rect(center=(WIDTH//2+ox, y+oy))
            surface.blit(o, orect)
    surface.blit(surf, rect)

def draw_arena(surf):
    # Background gradient
    surf.fill((26, 30, 46))
    for i in range(0, HEIGHT, 6):
        c = 26 + int(20 * (i / HEIGHT))
        pygame.draw.line(surf, (c, c+6, c+16), (0, i), (WIDTH, i))
    # Ground
    pygame.draw.rect(surf, (42, 48, 64), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    # Props
    for x in range(0, WIDTH, 140):
        pygame.draw.rect(surf, (60, 66, 90), (x+60, GROUND_Y-90, 56, 90))
        pygame.draw.rect(surf, (74, 82, 110), (x+100, GROUND_Y-40, 38, 40))

# -------------- Fighter --------------
class State(Enum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
    FALL = auto()
    CROUCH = auto()
    ATTACK = auto()
    BLOCK = auto()
    HITSTUN = auto()
    KODOWN = auto()
    DASH = auto()

class Fighter:
    def __init__(self, x, y, color, controls, name="Player"):
        self.name = name
        self.base_w, self.base_h = 64, 96
        self.rect = pygame.Rect(x, y - self.base_h, self.base_w, self.base_h)
        self.color = color
        self.vel_y = 0.0
        self.on_ground = False
        self.facing = 1
        self.health = 100
        self.max_health = 100
        self.state = State.IDLE
        self.controls = controls

        # Combat
        self.attack_name = None
        self.frame_counter = 0  # counts frames inside move
        self.hitbox = None
        self.can_air_action = True
        self.blocking = False
        self.guard_stun = 0
        self.hitstun = 0
        self.hitstop = 0

        # Dash/Stamina
        self.stamina = 100
        self.max_stamina = 100
        self.dash_timer = 0

        # Round/match helpers
        self.round_won = 0

    def input(self, keys):
        if self.hitstop > 0:
            return 0

        if self.state in (State.HITSTUN, State.KODOWN, State.ATTACK):
            return 0

        dx = 0
        left = keys[self.controls['left']]
        right = keys[self.controls['right']]
        down = keys[self.controls['down']]
        up = keys[self.controls['up']]
        light = keys[self.controls['light']]
        heavy = keys[self.controls['heavy']]
        block = keys[self.controls['block']]
        dash = keys[self.controls['dash']]

        # Facing update handled externally by game each frame

        # Block
        if block and self.on_ground and not down:
            self.state = State.BLOCK
            self.blocking = True
        else:
            if self.state == State.BLOCK:
                self.state = State.IDLE
            self.blocking = False

        # Crouch
        if down and self.on_ground and not self.blocking:
            self.state = State.CROUCH
        elif self.on_ground and self.state == State.CROUCH:
            self.state = State.IDLE

        # Dash
        if dash and self.on_ground and self.stamina >= DASH_COST and self.dash_timer == 0:
            self.state = State.DASH
            self.dash_timer = DASH_DURATION
            self.stamina -= DASH_COST

        # Movement
        speed = MOVE_SPEED if self.on_ground else AIR_SPEED
        if self.state != State.DASH and not self.blocking and self.state not in (State.CROUCH,):
            if left:
                dx -= speed
                self.facing = -1
                if self.on_ground and self.state == State.IDLE:
                    self.state = State.WALK
            if right:
                dx += speed
                self.facing = 1
                if self.on_ground and self.state == State.IDLE:
                    self.state = State.WALK
            if not left and not right and self.on_ground and self.state in (State.WALK,):
                self.state = State.IDLE

        # Jump / Short hop
        if up and self.on_ground and not self.blocking:
            self.vel_y = JUMP_VEL
            self.on_ground = False
            self.state = State.JUMP
            self.can_air_action = True
        elif up and not self.on_ground and self.state == State.FALL and self.can_air_action:
            # No double-jump; leave hook for future
            pass

        # Attacks
        if self.state not in (State.ATTACK, State.DASH) and not self.blocking:
            if self.on_ground:
                if down and light:
                    self.start_attack("c_light")
                elif light:
                    self.start_attack("light")
                elif heavy:
                    self.start_attack("heavy")
            else:
                if light or heavy:
                    self.start_attack("j_light")

        return dx

    def start_attack(self, name):
        data = MOVES[name]
        self.attack_name = name
        self.frame_counter = 0
        self.state = State.ATTACK
        self.hitbox = None

    def physics(self, dx):
        if self.hitstop > 0:
            return

        # Dash motion
        if self.state == State.DASH and self.dash_timer > 0:
            dx = self.facing * DASH_SPEED
            self.dash_timer -= 1
            if self.dash_timer == 0:
                self.state = State.IDLE if self.on_ground else State.FALL

        # Horizontal
        self.rect.x += int(dx)
        self.rect.x = max(0, min(WIDTH - self.rect.width, self.rect.x))

        # Gravity
        self.vel_y += GRAVITY
        self.rect.y += int(self.vel_y)

        # Ground collision
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True
            if self.state in (State.JUMP, State.FALL):
                self.state = State.IDLE
        else:
            if self.vel_y > 0 and self.state not in (State.ATTACK, State.DASH, State.HITSTUN):
                self.state = State.FALL
            self.on_ground = False

        # Stamina regen
        if self.stamina < self.max_stamina and self.state != State.DASH:
            self.stamina = min(self.max_stamina, self.stamina + 0.5)

        # Timers
        if self.guard_stun > 0:
            self.guard_stun -= 1
        if self.hitstun > 0:
            self.hitstun -= 1
            if self.hitstun == 0 and self.health > 0:
                self.state = State.IDLE if self.on_ground else State.FALL

    def update_attack(self):
        if self.hitstop > 0:
            self.hitstop -= 1
            return

        self.hitbox = None

        if self.state == State.ATTACK and self.attack_name:
            data = MOVES[self.attack_name]
            st = data["startup"]
            ac = data["active"]
            rc = data["recovery"]

            # Determine frame phase
            if self.frame_counter < st:
                phase = "startup"
            elif self.frame_counter < st + ac:
                phase = "active"
            elif self.frame_counter < st + ac + rc:
                phase = "recovery"
            else:
                self.state = State.IDLE if self.on_ground else State.FALL
                self.attack_name = None
                self.frame_counter = 0
                return

            # Active frames: build hitbox
            if phase == "active":
                hb_w, hb_h = 36, 24
                # crouch light lower hitbox
                if self.attack_name == "c_light":
                    hb_w, hb_h = 36, 18
                    hb_y = self.rect.bottom - hb_h - 10
                else:
                    hb_y = self.rect.centery - hb_h // 2

                if self.facing == 1:
                    hb_x = self.rect.right
                else:
                    hb_x = self.rect.left - hb_w

                self.hitbox = pygame.Rect(hb_x, hb_y, hb_w, hb_h)

            self.frame_counter += 1

    def take_hit(self, dmg, kb, hitstop_frames, airborne=False, blocked=False):
        # Hitstop (both players usually freeze)
        self.hitstop = min(HITSTOP_MAX, hitstop_frames)

        if blocked:
            # Guard stun and chip
            chip = int(dmg * CHIP_REDUCTION)
            self.health = max(0, self.health - chip)
            self.guard_stun = BLOCKSTUN
            # Small pushback
            self.rect.x += int(6 * (-self.facing))
            if SND_BLOCK: SND_BLOCK.play()
            return

        # Real hit
        self.health = max(0, self.health - dmg)
        self.state = State.HITSTUN if self.health > 0 else State.KODOWN
        # Knockback
        self.rect.x += int(kb * (-self.facing))
        # Air juggle
        if not self.on_ground:
            self.vel_y = -8
            self.hitstun = AIR_JUGGLE_STUN
        else:
            self.hitstun = HITSTUN_HEAVY if dmg >= 12 else HITSTUN_LIGHT
        if SND_HIT and self.health > 0: SND_HIT.play()
        if self.health == 0 and SND_KO: SND_KO.play()

    def draw(self, surf, debug=False):
        # Shadow
        shadow = pygame.Rect(self.rect.centerx - 18, GROUND_Y + 6, 36, 8)
        pygame.draw.ellipse(surf, (20, 20, 26), shadow)

        # Body color by state
        state_color = self.color
        outline_col = (0,0,0)
        if self.state == State.ATTACK:
            state_color = ORANGE
        elif self.state == State.BLOCK:
            state_color = PURPLE
        elif self.state == State.HITSTUN:
            state_color = (200, 80, 80)
        elif self.state == State.DASH:
            state_color = (80, 200, 200)

        # Body
        pygame.draw.rect(surf, state_color, self.rect, border_radius=6)
        pygame.draw.rect(surf, outline_col, self.rect, 2, border_radius=6)

        # Face indicator
        eye_r = 4
        eye_x = self.rect.centerx + (self.rect.width // 4) * self.facing
        eye_y = self.rect.y + 24
        pygame.draw.circle(surf, WHITE, (eye_x, eye_y), eye_r)

        # Attack box
        if self.hitbox:
            pygame.draw.rect(surf, YELLOW, self.hitbox, 2)

        # State label
        label = font_small.render(self.state.name, True, WHITE)
        surf.blit(label, (self.rect.x, self.rect.y - 20))

        # Stamina bar
        sw = 60
        sh = 6
        sx = self.rect.centerx - sw//2
        sy = self.rect.y - 10
        pct = self.stamina / self.max_stamina
        pygame.draw.rect(surf, (60,60,60), (sx, sy, sw, sh))
        pygame.draw.rect(surf, (60,200,200), (sx, sy, int(sw*pct), sh))

# -------------- Game Systems --------------
def resolve_hits(p1, p2):
    # Attack-vs-Body, with block check
    for atk, vic in ((p1, p2), (p2, p1)):
        if atk.hitbox:
            # Blocking works if victim is in block state and facing attacker
            is_blocking = vic.blocking and (vic.facing == -atk.facing) and vic.on_ground and vic.guard_stun == 0
            move = MOVES[atk.attack_name] if atk.attack_name else None
            if atk.hitbox.colliderect(vic.rect) and move:
                dmg = move["damage"]
                kb = move["knockback"]
                hitstop = move["hitstop"]
                vic.take_hit(
                    dmg=int(dmg * (1 - BLOCK_REDUCTION)) if is_blocking else dmg,
                    kb=kb//2 if is_blocking else kb,
                    hitstop_frames=hitstop,
                    airborne=not vic.on_ground,
                    blocked=is_blocking
                )
                # Attacker also experiences hitstop
                atk.hitstop = min(HITSTOP_MAX, hitstop)
                # Prevent multi-hits per swing
                atk.hitbox = None

def update_facing(p1, p2):
    if p1.rect.centerx < p2.rect.centerx:
        p1.facing = 1
        p2.facing = -1
    else:
        p1.facing = -1
        p2.facing = 1

def round_over_check(p1, p2, timer_frames):
    if p1.health <= 0 and p2.health <= 0:
        return -1
    if p1.health <= 0:
        return 2
    if p2.health <= 0:
        return 1
    if timer_frames <= 0:
        if p1.health > p2.health:
            return 1
        elif p2.health > p1.health:
            return 2
        else:
            return -1
    return 0

def reset_round(p1, p2):
    p1.rect.topleft = (200, GROUND_Y - p1.base_h)
    p2.rect.topleft = (WIDTH - 260, GROUND_Y - p2.base_h)
    p1.facing, p2.facing = 1, -1
    p1.vel_y = p2.vel_y = 0
    p1.on_ground = p2.on_ground = True
    p1.state = p2.state = State.IDLE
    p1.hitbox = p2.hitbox = None
    p1.attack_name = p2.attack_name = None
    p1.frame_counter = p2.frame_counter = 0
    p1.blocking = p2.blocking = False
    p1.guard_stun = p2.guard_stun = 0
    p1.hitstun = p2.hitstun = 0
    p1.hitstop = p2.hitstop = 0
    p1.stamina = p2.stamina = 100

def draw_timer_and_score(timer_frames, p1, p2, rounds_to_win):
    secs = max(0, timer_frames // (FPS))
    center_text(screen, f"{secs:02d}", font_big, WHITE, 60)
    # Round pips
    def pips(x, y, won, color):
        for i in range(rounds_to_win):
            r = pygame.Rect(x + i*22, y, 16, 16)
            pygame.draw.rect(screen, GREY, r, border_radius=4)
            if i < won:
                pygame.draw.rect(screen, color, r, border_radius=4)
            pygame.draw.rect(screen, WHITE, r, 2, border_radius=4)
    pips(40, 56, p1.round_won, BLUE)
    pips(WIDTH-40-22*rounds_to_win, 56, p2.round_won, RED)

def draw_title(menu_index):
    draw_arena(screen)
    center_text(screen, "Python Fighting Game", font_big, YELLOW, 160)
    options = ["Start", "How to Play", "Quit"]
    for i, text in enumerate(options):
        col = WHITE if i != menu_index else YELLOW
        center_text(screen, text, font_mid, col, 240 + i*46, outline=False)
    center_text(screen, "Use Up/Down and Enter", font_small, GREY, 240 + len(options)*46 + 20, outline=False)

def draw_how_to_play():
    draw_arena(screen)
    center_text(screen, "How to Play", font_big, YELLOW, 80)
    lines = [
        "Goal: Deplete opponent's health or win by timer.",
        "P1: A/D move, W jump, S crouch, Shift dash, H block, F light, G heavy.",
        "P2: Arrows move/up/down, Right Shift dash, ; block, K light, L heavy.",
        "Blocking reduces damage; some chip damage applies.",
        "Dashes consume stamina; stamina regenerates over time.",
        "Light = fast, Heavy = slower but stronger, Crouch Light = low hit.",
        "Jump Light hits in air; juggles on air hit.",
        "Best of 3 rounds; press Esc to pause.",
        "Enter to go back."
    ]
    for i, t in enumerate(lines):
        center_text(screen, t, font_small, WHITE, 130 + i*30, outline=False)

def draw_pause():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,150))
    screen.blit(overlay, (0,0))
    center_text(screen, "Paused", font_big, YELLOW, HEIGHT//2 - 20)
    center_text(screen, "Esc to resume, R to restart round, Q to quit to title", font_small, WHITE, HEIGHT//2 + 20, outline=False)

def main():
    # Controls
    p1_controls = {
        'left': pygame.K_a,
        'right': pygame.K_d,
        'down': pygame.K_s,
        'up': pygame.K_w,
        'light': pygame.K_f,
        'heavy': pygame.K_g,
        'block': pygame.K_h,
        'dash': pygame.K_LSHIFT,
    }
    p2_controls = {
        'left': pygame.K_LEFT,
        'right': pygame.K_RIGHT,
        'down': pygame.K_DOWN,
        'up': pygame.K_UP,
        'light': pygame.K_k,
        'heavy': pygame.K_l,
        'block': pygame.K_SEMICOLON,
        'dash': pygame.K_RSHIFT,
    }

    # Fighters
    p1 = Fighter(200, GROUND_Y, BLUE, p1_controls, name="Player 1")
    p2 = Fighter(WIDTH - 260, GROUND_Y, RED, p2_controls, name="Player 2")
    p2.facing = -1

    # Game state
    state = GameState.TITLE
    menu_index = 0
    round_timer = ROUND_TIME_SECONDS * FPS
    round_winner = 0
    match_winner = 0

    running = True
    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == GameState.TITLE:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        menu_index = (menu_index - 1) % 3
                        if SND_SELECT: SND_SELECT.play()
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        menu_index = (menu_index + 1) % 3
                        if SND_SELECT: SND_SELECT.play()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if menu_index == 0:
                            # Start
                            p1.health = p1.max_health
                            p2.health = p2.max_health
                            p1.round_won = p2.round_won = 0
                            reset_round(p1, p2)
                            round_timer = ROUND_TIME_SECONDS * FPS
                            state = GameState.PLAYING
                            if SND_START: SND_START.play()
                        elif menu_index == 1:
                            state = GameState.HOW_TO_PLAY
                        else:
                            running = False

            elif state == GameState.HOW_TO_PLAY:
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    state = GameState.TITLE

            elif state == GameState.PLAYING:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    state = GameState.PAUSED

            elif state == GameState.PAUSED:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = GameState.PLAYING
                    elif event.key == pygame.K_r:
                        # Restart current round
                        p1.health = p1.max_health
                        p2.health = p2.max_health
                        reset_round(p1, p2)
                        round_timer = ROUND_TIME_SECONDS * FPS
                        state = GameState.PLAYING
                    elif event.key == pygame.K_q:
                        state = GameState.TITLE

            elif state == GameState.ROUND_END:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    # Next round or match end handling
                    if p1.round_won >= ROUNDS_TO_WIN or p2.round_won >= ROUNDS_TO_WIN:
                        state = GameState.MATCH_END
                    else:
                        p1.health = p1.max_health
                        p2.health = p2.max_health
                        reset_round(p1, p2)
                        round_timer = ROUND_TIME_SECONDS * FPS
                        state = GameState.PLAYING

            elif state == GameState.MATCH_END:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        # Back to title
                        state = GameState.TITLE

        keys = pygame.key.get_pressed()

        # Logic and drawing
        if state == GameState.TITLE:
            draw_title(menu_index)

        elif state == GameState.HOW_TO_PLAY:
            draw_how_to_play()

        elif state in (GameState.PLAYING, GameState.PAUSED, GameState.ROUND_END, GameState.MATCH_END):
            draw_arena(screen)

            # UI
            draw_health_bar(screen, 40, 30, 360, 20, p1.health, p1.max_health, BLUE)
            draw_health_bar(screen, WIDTH - 400, 30, 360, 20, p2.health, p2.max_health, RED)
            draw_timer_and_score(round_timer, p1, p2, ROUNDS_TO_WIN)

            if state == GameState.PLAYING:
                # Facing
                update_facing(p1, p2)

                # Input
                dx1 = p1.input(keys)
                dx2 = p2.input(keys)

                # Physics and state advance
                p1.physics(dx1)
                p2.physics(dx2)

                # Attacks
                p1.update_attack()
                p2.update_attack()

                # Guard lock
                if p1.guard_stun > 0:
                    p1.state = State.BLOCK
                if p2.guard_stun > 0:
                    p2.state = State.BLOCK

                # Resolve collisions
                resolve_hits(p1, p2)

                # Timer
                if p1.hitstop == 0 and p2.hitstop == 0:
                    round_timer = max(0, round_timer - 1)

                # Round over
                rw = round_over_check(p1, p2, round_timer)
                if rw != 0:
                    round_winner = rw
                    if rw == 1:
                        p1.round_won += 1
                    elif rw == 2:
                        p2.round_won += 1
                    state = GameState.ROUND_END

            # Draw fighters
            p1.draw(screen)
            p2.draw(screen)

            # Overlays
            if state == GameState.PAUSED:
                draw_pause()

            if state == GameState.ROUND_END:
                msg = "Draw" if round_winner == -1 else f"{'Player 1' if round_winner == 1 else 'Player 2'} Wins Round"
                center_text(screen, msg, font_big, YELLOW, HEIGHT//2 - 20)
                center_text(screen, "Press Enter for next round", font_small, WHITE, HEIGHT//2 + 20, outline=False)
                if p1.round_won >= ROUNDS_TO_WIN or p2.round_won >= ROUNDS_TO_WIN:
                    state = GameState.MATCH_END
                    match_winner = 1 if p1.round_won > p2.round_won else 2

            if state == GameState.MATCH_END:
                msg = f"Player {match_winner} Wins Match!"
                center_text(screen, msg, font_big, YELLOW, HEIGHT//2 - 20)
                center_text(screen, "Press Enter to return to Title", font_small, WHITE, HEIGHT//2 + 20, outline=False)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
