import math
import os
import random
import pygame

W, H = 960, 640
FPS = 60

PLAYER_R = 16
PLAYER_SPEED = 260
PLAYER_MAX_HP = 100

DASH_DIST = 260
DASH_SPEED = 2200
DASH_HALF_W = 26
MAX_AMMO = 3
RELOAD_TIME = 1.1
HEAL_PER_KILL = 6

FONT_NAME = "sourcesans3"
FONT_FILE = None
BG_FILE = "checkyback.png"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENEMY_R = 15
ENEMY_SPEED = 90
ENEMY_BULLET_SPEED = 320
ENEMY_BULLET_DMG = 10
ENEMY_BULLET_R = 5

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def seg_dist(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - ax, py - ay)
    t = clamp(((px - ax) * dx + (py - ay) * dy) / l2, 0, 1)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

class Enemy:
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.shoot_cd = random.uniform(0.8, 2.0)

    def update(self, dt, player_pos, bullets):
        to_p = player_pos - self.pos
        dist = to_p.length()
        if dist > 0:
            d = to_p / dist
            if dist > 320:
                self.pos += d * ENEMY_SPEED * dt
            elif dist < 200:
                self.pos -= d * ENEMY_SPEED * dt
        self.pos.x = clamp(self.pos.x, ENEMY_R, W - ENEMY_R)
        self.pos.y = clamp(self.pos.y, ENEMY_R, H - ENEMY_R)

        self.shoot_cd -= dt
        if self.shoot_cd <= 0 and dist > 0:
            vel = (to_p / dist) * ENEMY_BULLET_SPEED
            bullets.append([pygame.Vector2(self.pos), vel])
            self.shoot_cd = random.uniform(1.4, 2.4)

def spawn_enemy():
    corner = random.choice([(0, 0), (W, 0), (0, H), (W, H)])
    return Enemy(corner[0] + random.randint(-10, 10), corner[1] + random.randint(-10, 10))

def main():
    global W, H
    pygame.init()
    W, H = pygame.display.get_desktop_sizes()[0]
    screen = pygame.display.set_mode((W, H), pygame.NOFRAME)

    bg = None
    if BG_FILE:
        try:
            bg_path = BG_FILE if os.path.isabs(BG_FILE) else os.path.join(BASE_DIR, BG_FILE)
            img = pygame.image.load(bg_path).convert()
            iw, ih = img.get_size()
            scale = max(W / iw, H / ih)
            img = pygame.transform.smoothscale(img, (int(iw * scale) + 1, int(ih * scale) + 1))
            bg = pygame.Surface((W, H))
            bg.blit(img, ((W - img.get_width()) // 2, (H - img.get_height()) // 2))
        except (pygame.error, FileNotFoundError) as err:
            print("Background failed to load:", err)
            bg = None
    pygame.display.set_caption("Mortis Dash - Simple")
    clock = pygame.time.Clock()
    def make_font(size):
        if FONT_FILE:
            font_path = FONT_FILE if os.path.isabs(FONT_FILE) else os.path.join(BASE_DIR, FONT_FILE)
            return pygame.font.Font(font_path, size)
        return pygame.font.SysFont(FONT_NAME, size, bold=True)

    font = make_font(28)
    big = make_font(64)

    started = False
    paused = False

    btn_w, btn_h, btn_gap = 220, 56, 18
    resume_rect = pygame.Rect(0, 0, btn_w, btn_h)
    resume_rect.center = (W / 2, H / 2)
    restart_rect = pygame.Rect(0, 0, btn_w, btn_h)
    restart_rect.center = (W / 2, H / 2 + btn_h + btn_gap)
    quit_rect = pygame.Rect(0, 0, btn_w, btn_h)
    quit_rect.center = (W / 2, H / 2 + 2 * (btn_h + btn_gap))

    def reset():
        return {
            "pos": pygame.Vector2(W / 2, H / 2),
            "hp": PLAYER_MAX_HP,
            "ammo": float(MAX_AMMO),
            "dashing": False,
            "dash_target": None,
            "hit": set(),
            "enemies": [spawn_enemy() for _ in range(2)],
            "bullets": [],
            "spawn_t": 0.0,
            "score": 0,
            "time": 0.0,
            "aiming": False,
            "dead_t": 0.0,
        }

    s = reset()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000
        mouse = pygame.Vector2(pygame.mouse.get_pos())

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
                continue
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                if not started or s["hp"] <= 0:
                    running = False
                elif paused:
                    paused = False
                else:
                    paused = True
                continue
            if not started:
                if e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    started = True
                continue
            if paused:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    if resume_rect.collidepoint(e.pos):
                        paused = False
                    elif restart_rect.collidepoint(e.pos):
                        s = reset()
                        paused = False
                    elif quit_rect.collidepoint(e.pos):
                        running = False
                continue
            if s["hp"] > 0:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    s["aiming"] = True
                if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and s["aiming"]:
                    s["aiming"] = False
                    if s["ammo"] >= 1 and not s["dashing"]:
                        d = mouse - s["pos"]
                        if d.length() > 0:
                            d = d.normalize()
                            tgt = s["pos"] + d * DASH_DIST
                            tgt.x = clamp(tgt.x, PLAYER_R, W - PLAYER_R)
                            tgt.y = clamp(tgt.y, PLAYER_R, H - PLAYER_R)
                            s["dash_target"] = tgt
                            s["dashing"] = True
                            s["hit"] = set()
                            s["ammo"] -= 1
            elif e.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN) and s["dead_t"] > 0.6:
                s = reset()

        if started and not paused and s["hp"] > 0:
            s["time"] += dt
            pos = s["pos"]

            if s["dashing"]:
                prev = pygame.Vector2(pos)
                to_t = s["dash_target"] - pos
                step = DASH_SPEED * dt
                if to_t.length() <= step:
                    pos.update(s["dash_target"])
                    s["dashing"] = False
                else:
                    pos += to_t.normalize() * step
                for en in s["enemies"][:]:
                    if id(en) in s["hit"]:
                        continue
                    if seg_dist(en.pos, prev, pos) <= ENEMY_R + DASH_HALF_W:
                        s["hit"].add(id(en))
                        s["enemies"].remove(en)
                        s["score"] += 1
                        s["hp"] = min(PLAYER_MAX_HP, s["hp"] + HEAL_PER_KILL)
            else:
                k = pygame.key.get_pressed()
                mv = pygame.Vector2(
                    (k[pygame.K_d] or k[pygame.K_RIGHT]) - (k[pygame.K_a] or k[pygame.K_LEFT]),
                    (k[pygame.K_s] or k[pygame.K_DOWN]) - (k[pygame.K_w] or k[pygame.K_UP]),
                )
                if mv.length() > 0:
                    pos += mv.normalize() * PLAYER_SPEED * dt
                pos.x = clamp(pos.x, PLAYER_R, W - PLAYER_R)
                pos.y = clamp(pos.y, PLAYER_R, H - PLAYER_R)

            if s["ammo"] < MAX_AMMO:
                s["ammo"] = min(MAX_AMMO, s["ammo"] + dt / RELOAD_TIME)

            s["spawn_t"] -= dt
            if s["spawn_t"] <= 0:
                cap = 4 + int(s["time"] // 15)
                if len(s["enemies"]) < cap:
                    s["enemies"].append(spawn_enemy())
                s["spawn_t"] = max(0.8, 2.5 - s["time"] * 0.02)

            for en in s["enemies"]:
                en.update(dt, pos, s["bullets"])

            for b in s["bullets"][:]:
                b[0] += b[1] * dt
                if not (-20 < b[0].x < W + 20 and -20 < b[0].y < H + 20):
                    s["bullets"].remove(b)
                elif b[0].distance_to(pos) < PLAYER_R + ENEMY_BULLET_R:
                    s["bullets"].remove(b)
                    s["hp"] -= ENEMY_BULLET_DMG
        elif started and not paused:
            s["dead_t"] += dt

        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill((28, 30, 38))
        pos = s["pos"]

        if s["aiming"] and s["hp"] > 0:
            d = mouse - pos
            if d.length() > 0:
                d = d.normalize()
                n = pygame.Vector2(-d.y, d.x) * DASH_HALF_W
                end = pos + d * DASH_DIST
                pts = [pos + n, pos - n, end - n, end + n]
                can_attack = s["ammo"] >= 1 and not s["dashing"]
                fill_c = (255, 255, 255, 90) if can_attack else (255, 60, 60, 90)
                line_c = (255, 255, 255, 200) if can_attack else (255, 80, 80, 200)
                ov = pygame.Surface((W, H), pygame.SRCALPHA)
                pygame.draw.polygon(ov, fill_c, pts)
                pygame.draw.polygon(ov, line_c, pts, 2)
                screen.blit(ov, (0, 0))

        for en in s["enemies"]:
            pygame.draw.circle(screen, (220, 70, 70), en.pos, ENEMY_R)
            pygame.draw.circle(screen, (247, 114, 114), en.pos, ENEMY_R, 2)
        for b in s["bullets"]:
            pygame.draw.circle(screen, (220, 70, 70), b[0], ENEMY_BULLET_R)
            pygame.draw.circle(screen, (92, 29, 29), b[0], ENEMY_BULLET_R, 2)
        pygame.draw.circle(screen, (160, 90, 220), pos, PLAYER_R)
        pygame.draw.circle(screen, (202, 148, 247), pos, PLAYER_R, 2)

        pygame.draw.rect(screen, (60, 60, 70), (20, 20, 200, 16))
        pygame.draw.rect(screen, (80, 220, 110), (20, 20, 200 * max(0, s["hp"]) / PLAYER_MAX_HP, 16))
        for i in range(MAX_AMMO):
            fill = clamp(s["ammo"] - i, 0, 1)
            pygame.draw.rect(screen, (60, 60, 70), (20 + i * 70, 44, 64, 12))
            pygame.draw.rect(screen, (255, 140, 60), (20 + i * 70, 44, 64 * fill, 12))
        screen.blit(font.render(f"Score: {s['score']}", True, (230, 230, 240)), (W - 128, 18))

        if s["hp"] <= 0:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            screen.blit(ov, (0, 0))
            t0 = font.render(f"Score: {s['score']}", True, (230, 230, 240))
            screen.blit(t0, t0.get_rect(center=(W / 2, H / 2 - 60)))
            t = big.render("You Died!", True, (255, 90, 90))
            screen.blit(t, t.get_rect(center=(W / 2, H / 2 - 10)))
            t2 = font.render("[press anywhere to play again]", True, (230, 230, 240))
            screen.blit(t2, t2.get_rect(center=(W / 2, H / 2 + 40)))

        if not started:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            screen.blit(ov, (0, 0))
            t = big.render("A game about Slashing", True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=(W / 2, H / 2 - 20)))
            t2 = font.render("[press anywhere to start]", True, (230, 230, 240))
            screen.blit(t2, t2.get_rect(center=(W / 2, H / 2 + 30)))

        if paused:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 160))
            screen.blit(ov, (0, 0))
            t = big.render("Paused", True, (255, 255, 255))
            screen.blit(t, t.get_rect(center=(W / 2, resume_rect.top - 50)))

            for rect, label in ((resume_rect, "Resume"), (restart_rect, "Restart"), (quit_rect, "Quit")):
                hover = rect.collidepoint(mouse)
                pygame.draw.rect(screen, (70, 70, 85) if hover else (45, 45, 55), rect, border_radius=8)
                pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=8)
                lbl = font.render(label, True, (255, 255, 255))
                screen.blit(lbl, lbl.get_rect(center=rect.center))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
