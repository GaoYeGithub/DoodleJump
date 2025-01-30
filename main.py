import pygame
import sys
import random
import asyncio
from math import copysign
from pygame.math import Vector2
from pygame.locals import (
    KEYDOWN, KEYUP, K_LEFT, K_RIGHT, K_ESCAPE, K_RETURN, K_SPACE, QUIT
)
from pygame.sprite import collide_rect
from pygame.font import SysFont
import os
import math

pygame.init()

XWIN, YWIN = 600, 800
HALF_XWIN, HALF_YWIN = XWIN/2, YWIN/2
DISPLAY = (XWIN, YWIN)
FLAGS = 0
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
LIGHT_GREEN = (131, 252, 107)
ANDROID_GREEN = (164, 198, 57)
FOREST_GREEN = (87, 189, 68)

PLAYER_SIZE = (25, 35)
PLAYER_COLOR = ANDROID_GREEN
PLAYER_MAX_SPEED = 20
PLAYER_JUMPFORCE = 20
PLAYER_BONUS_JUMPFORCE = 70
GRAVITY = 0.98

PLATFORM_COLOR = FOREST_GREEN
PLATFORM_COLOR_LIGHT = LIGHT_GREEN
PLATFORM_SIZE = (100, 10)
PLATFORM_DISTANCE_GAP = (50, 210)
MAX_PLATFORM_NUMBER = 10
BONUS_SPAWN_CHANCE = 10
BREAKABLE_PLATFORM_CHANCE = 12

BULLET_SIZE = (8, 16)
BULLET_COLOR = ANDROID_GREEN
BULLET_SPEED = -15
BULLET_COOLDOWN = 250

LARGE_FONT = SysFont("", 128)
SMALL_FONT = SysFont("arial", 24)

MONSTER_SIZE = (30, 30)
MONSTER_SPAWN_CHANCE = 15
MONSTER_SPEED = 2

class GameState:
    MENU = "menu"
    PLAYING = "playing"
    GAME_OVER = "game_over"

class Singleton:
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, 'instance'):
            cls.instance = super(Singleton, cls).__new__(cls)
        return cls.instance

class PlayerState:
    IDLE_RIGHT = "right"
    IDLE_LEFT = "left"
    JUMP_RIGHT = "right_jump"
    JUMP_LEFT = "left_jump"
    SHOOT = "shoot"
    SHOOT_JUMP = "shoot_jump"

class MainMenu:
    def __init__(self):
        self.title_font = pygame.font.Font(None, 74)
        self.font = pygame.font.Font(None, 36)
        try:
            self.bg_image = pygame.image.load(os.path.join("assets", "main_menu.png")).convert_alpha()
            self.bg_image = pygame.transform.scale(self.bg_image, (XWIN, YWIN))
        except pygame.error:
            self.bg_image = pygame.Surface(DISPLAY)
            self.bg_image.fill(WHITE)
        self.title = self.title_font.render("Doodle Jump", True, FOREST_GREEN)
        self.start_text = self.font.render("Press ENTER to Start", True, ANDROID_GREEN)
        self.instruction_text = self.font.render("Use arrows to move, SPACE to shoot", True, GRAY)
        self.title_y = YWIN // 4
        self.title_bounce = 0
        self.text_alpha = 255
        self.alpha_direction = -5
        
    def update(self):
        self.title_bounce = math.sin(pygame.time.get_ticks() / 500) * 10
        self.text_alpha += self.alpha_direction
        if self.text_alpha <= 100 or self.text_alpha >= 255:
            self.alpha_direction *= -1
            
    def draw(self, surface):
        surface.blit(self.bg_image, (0, 0))
        title_rect = self.title.get_rect(centerx=HALF_XWIN, centery=self.title_y + self.title_bounce)
        surface.blit(self.title, title_rect)
        start_text_copy = self.start_text.copy()
        start_text_copy.set_alpha(self.text_alpha)
        start_rect = start_text_copy.get_rect(centerx=HALF_XWIN, centery=YWIN * 0.6)
        surface.blit(start_text_copy, start_rect)
        instruction_rect = self.instruction_text.get_rect(centerx=HALF_XWIN, centery=YWIN * 0.7)
        surface.blit(self.instruction_text, instruction_rect)

class GameOverScreen:
    def __init__(self):
        self.font_large = pygame.font.Font(None, 74)
        self.font_small = pygame.font.Font(None, 36)
        self.title_y = YWIN // 3
        self.score = 0
        
    def update(self, score):
        self.score = score
        
    def draw(self, surface):
        gradient = pygame.Surface(DISPLAY)
        for y in range(YWIN):
            color = pygame.Color(255, 255, 255)
            color.hsla = (120, 50, max(0, min(100 - (y / YWIN * 30), 100)), 100)
            pygame.draw.line(gradient, color, (0, y), (XWIN, y))
        surface.blit(gradient, (0, 0))
        game_over_text = self.font_large.render("Game Over!", True, FOREST_GREEN)
        shadow_text = self.font_large.render("Game Over!", True, (0, 0, 0, 128))
        text_rect = game_over_text.get_rect(centerx=HALF_XWIN, centery=self.title_y)
        surface.blit(shadow_text, (text_rect.x + 3, text_rect.y + 3))
        surface.blit(game_over_text, text_rect)
        score_text = self.font_small.render(f"Final Score: {self.score} m", True, ANDROID_GREEN)
        score_rect = score_text.get_rect(centerx=HALF_XWIN, centery=self.title_y + 80)
        surface.blit(score_text, score_rect)
        restart_text = self.font_small.render("Press ENTER to Restart", True, GRAY)
        restart_rect = restart_text.get_rect(centerx=HALF_XWIN, centery=self.title_y + 140)
        surface.blit(restart_text, restart_rect)

class Background:
    def __init__(self):
        try:
            self.image = pygame.image.load(os.path.join("assets", "junglebackground.png")).convert()
            self.image = pygame.transform.scale(self.image, (XWIN, YWIN))
        except pygame.error:
            self.image = pygame.Surface(DISPLAY)
            self.image.fill(WHITE)
        self.rect = self.image.get_rect()
        
    def draw(self, surface, camera_y=0):
        rel_y = camera_y % self.rect.height
        surface.blit(self.image, (0, rel_y - self.rect.height))
        if rel_y < YWIN:
            surface.blit(self.image, (0, rel_y))

class Camera(Singleton):
    def __init__(self, lerp=5, width=XWIN, height=YWIN):
        self.state = pygame.Rect(0, 0, width, height)
        self.lerp = lerp
        self.center = height // 2
        self.maxheight = self.center

    def reset(self):
        self.state.y = 0
        self.maxheight = self.center

    def apply_rect(self, rect):
        return rect.move((0, -self.state.topleft[1]))

    def apply(self, target):
        return self.apply_rect(target.rect)

    def update(self, target):
        if target.y < self.maxheight:
            self.maxheight = target.y
        speed = ((self.state.y + self.center) - self.maxheight) / self.lerp
        self.state.y -= speed

class Sprite:
    def __init__(self, x, y, w, h, color):
        self.__color = color
        self._image = pygame.Surface((w, h))
        self._image.fill(color)
        self._image = self._image.convert()
        self.rect = pygame.Rect(x, y, w, h)
        self.camera_rect = self.rect.copy()

    @property
    def image(self):
        return self._image

    @property
    def color(self):
        return self.__color

    @color.setter
    def color(self, new):
        self.__color = new
        self._image.fill(new)

    def draw(self, surface):
        if Camera.instance:
            self.camera_rect = Camera.instance.apply(self)
            surface.blit(self._image, self.camera_rect)
        else:
            surface.blit(self._image, self.rect)

class Monster(Sprite):
    def __init__(self, x, y, platform_width):
        super().__init__(x, y, *MONSTER_SIZE, ANDROID_GREEN)
        self.platform_width = platform_width
        self.start_x = x
        self.direction = 1
        self.speed = MONSTER_SPEED
        self.dead = False
        try:
            self.normal_image = pygame.image.load(
                os.path.join("assets", "normalmonster", "monster.png")
            ).convert_alpha()
            self.dead_image = pygame.image.load(
                os.path.join("assets", "normalmonster", "dead-monster.png")
            ).convert_alpha()
            self.normal_image = pygame.transform.scale(self.normal_image, MONSTER_SIZE)
            self.dead_image = pygame.transform.scale(self.dead_image, MONSTER_SIZE)
            self._image = self.normal_image
        except pygame.error:
            print("Couldn't load monster images")
    
    def kill(self):
        self.dead = True
        self.death_time = pygame.time.get_ticks()
        self._image = self.dead_image

    def update(self):
        if not self.dead:
            self.rect.x += self.direction * self.speed
            if self.rect.x > self.start_x + self.platform_width - self.rect.width:
                self.direction = -1
            elif self.rect.x < self.start_x:
                self.direction = 1

class Bullet(Sprite):
    def __init__(self, x, y):
        super().__init__(x, y, *BULLET_SIZE, BULLET_COLOR)
        self.velocity = BULLET_SPEED
        self._image = pygame.Surface(BULLET_SIZE, pygame.SRCALPHA)
        pygame.draw.ellipse(self._image, ANDROID_GREEN, (0, 0, *BULLET_SIZE))

    def update(self):
        self.rect.y += self.velocity
        lvl = Level.instance
        if lvl:
            for platform in lvl.platforms:
                if platform.monster and not platform.monster.dead:
                    if collide_rect(self, platform.monster):
                        platform.monster.kill()
                        lvl.remove_bullet(self)
                        return
        if self.camera_rect.y < -50:
            lvl.remove_bullet(self)

class Player(Sprite, Singleton):
    def __init__(self, x, y, w, h, color):
        Sprite.__init__(self, x, y, w, h, color)
        self.__startrect = self.rect.copy()
        self.__maxvelocity = Vector2(PLAYER_MAX_SPEED, 100)
        self.__startspeed = 1.5
        self._velocity = Vector2()
        self._input = 0
        self._jumpforce = PLAYER_JUMPFORCE
        self._bonus_jumpforce = PLAYER_BONUS_JUMPFORCE
        self.gravity = GRAVITY
        self.accel = 0.5
        self.deccel = 0.6
        self.dead = False
        self.facing_right = True
        self.last_shoot_time = 0
        self.images = {}
        image_dir = os.path.join("assets", "player")
        for state in [PlayerState.IDLE_RIGHT, PlayerState.IDLE_LEFT, 
                     PlayerState.JUMP_RIGHT, PlayerState.JUMP_LEFT,
                     PlayerState.SHOOT, PlayerState.SHOOT_JUMP]:
            path = os.path.join(image_dir, f"{state}.png")
            try:
                img = pygame.image.load(path).convert_alpha()
                img = pygame.transform.scale(img, (w, h))
                self.images[state] = img
            except pygame.error:
                print(f"Couldn't load image: {path}")
                self.images[state] = self._image
        self.current_state = PlayerState.IDLE_RIGHT

    def update_state(self):
        shooting = pygame.time.get_ticks() - self.last_shoot_time < 200
        jumping = abs(self._velocity.y) > 0.5
        if shooting:
            self.current_state = PlayerState.SHOOT_JUMP if jumping else PlayerState.SHOOT
        else:
            if self.facing_right:
                self.current_state = PlayerState.JUMP_RIGHT if jumping else PlayerState.IDLE_RIGHT
            else:
                self.current_state = PlayerState.JUMP_LEFT if jumping else PlayerState.IDLE_LEFT

    def _fix_velocity(self):
        self._velocity.y = min(self._velocity.y, self.__maxvelocity.y)
        self._velocity.x = max(min(self._velocity.x, self.__maxvelocity.x), -self.__maxvelocity.x)

    def reset(self):
        self._velocity = Vector2()
        self.rect = self.__startrect.copy()
        self.camera_rect = self.__startrect.copy()
        self.dead = False

    def shoot(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shoot_time >= BULLET_COOLDOWN:
            self.last_shoot_time = current_time
            bullet = Bullet(self.rect.centerx - BULLET_SIZE[0]//2, self.rect.top)
            Level.instance.add_bullet(bullet)

    def handle_event(self, event):
        if event.type == KEYDOWN:
            if event.key == K_LEFT:
                self._velocity.x = -self.__startspeed
                self._input = -1
                self.facing_right = False
            elif event.key == K_RIGHT:
                self._velocity.x = self.__startspeed
                self._input = 1
                self.facing_right = True
            elif event.key == K_SPACE:
                self.shoot()
        elif event.type == KEYUP:
            if (event.key == K_LEFT and self._input == -1) or (event.key == K_RIGHT and self._input == 1):
                self._input = 0

    def jump(self, force=None):
        self._velocity.y = -force if force else -self._jumpforce

    def onCollide(self, obj):
        self.rect.bottom = obj.rect.top
        self.jump()

    def collisions(self):
        lvl = Level.instance
        if not lvl: return
        for platform in lvl.platforms:
            if self._velocity.y > 0.5:
                if platform.bonus and collide_rect(self, platform.bonus):
                    self.onCollide(platform.bonus)
                    self.jump(platform.bonus.force)
                if collide_rect(self, platform):
                    self.onCollide(platform)
                    platform.onCollide()
            if platform.monster and not platform.monster.dead:
                if collide_rect(self, platform.monster):
                    self.dead = True
                    return

    def update(self):
        if self.camera_rect.y > YWIN * 2:
            self.dead = True
            return
        self._velocity.y += self.gravity
        if self._input:
            self._velocity.x += self._input * self.accel
        elif self._velocity.x:
            self._velocity.x -= copysign(1, self._velocity.x) * self.deccel
        self._fix_velocity()
        self.rect.x = (self.rect.x + self._velocity.x) % (XWIN - self.rect.width)
        self.rect.y += self._velocity.y
        self.collisions()

    def draw(self, surface):
        self.update_state()
        if Camera.instance:
            self.camera_rect = Camera.instance.apply(self)
            surface.blit(self.images[self.current_state], self.camera_rect)
        else:
            surface.blit(self.images[self.current_state], self.rect)

def chance(x):
    return not random.randint(0, x)

class Animation:
    def __init__(self, frames, loop=True, frame_duration=100):
        self.frames = frames
        self.loop = loop
        self.frame_duration = frame_duration
        self.current_frame = 0
        self.start_time = pygame.time.get_ticks()
        self.finished = False
        
    def update(self):
        if self.finished and not self.loop:
            return self.frames[-1]
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.start_time
        if self.loop:
            self.current_frame = (elapsed // self.frame_duration) % len(self.frames)
        else:
            self.current_frame = min((elapsed // self.frame_duration), len(self.frames) - 1)
            if self.current_frame == len(self.frames) - 1:
                self.finished = True
        return self.frames[self.current_frame]

class Bonus(Sprite):
    WIDTH = 15
    HEIGHT = 15

    def __init__(self, parent, color=GRAY, force=PLAYER_BONUS_JUMPFORCE):
        x = parent.rect.centerx - self.WIDTH//2
        y = parent.rect.y - self.HEIGHT
        super().__init__(x, y, self.WIDTH, self.HEIGHT, color)
        self.force = force
        self.activated = False
        try:
            trampoline_normal = pygame.image.load(os.path.join("assets", "trampoline", "trampoline.png")).convert_alpha()
            trampoline_active = pygame.image.load(os.path.join("assets", "trampoline", "trampoline-activate.png")).convert_alpha()
            self.trampoline_frames = [
                pygame.transform.scale(trampoline_normal, (self.WIDTH, self.HEIGHT)),
                pygame.transform.scale(trampoline_active, (self.WIDTH, self.HEIGHT))
            ]
        except pygame.error:
            print("Couldn't load trampoline images")
            self.trampoline_frames = [self._image, self._image]
        self.animation = Animation(self.trampoline_frames, loop=False, frame_duration=150)
        
    def activate(self):
        if not self.activated:
            self.activated = True
            self.animation = Animation(self.trampoline_frames, loop=False, frame_duration=150)
            
    def draw(self, surface):
        if Camera.instance:
            self.camera_rect = Camera.instance.apply(self)
            surface.blit(self.animation.update(), self.camera_rect)
        else:
            surface.blit(self.animation.update(), self.rect)

class Platform(Sprite):
    def __init__(self, x, y, width, height, initial_bonus=False, breakable=False):
        color = PLATFORM_COLOR_LIGHT if breakable else PLATFORM_COLOR
        super().__init__(x, y, width, height, color)
        self.breakable = breakable
        self.__level = Level.instance
        self.__bonus = None
        self.breaking = False
        self.monster = None

        if not breakable:
            try:
                normal_img = pygame.image.load(
                    os.path.join("assets", "blocks", "normalblock.png")
                ).convert_alpha()
                self._image = pygame.transform.scale(normal_img, (width, height))
            except pygame.error:
                self._image.fill(color)

        self.break_animation = None
        if breakable:
            try:
                break_frames = []
                for i in range(4):
                    img = pygame.image.load(
                        os.path.join("assets", "blocks", f"breakable-block-{i}.png")
                    ).convert_alpha()
                    break_frames.append(pygame.transform.scale(img, (width, height)))
                self.break_animation = Animation(break_frames, loop=False, frame_duration=50)
                self._image = break_frames[0]
            except pygame.error:
                self.break_animation = None
                self._image.fill(color)

        if not breakable and chance(MONSTER_SPAWN_CHANCE):
            self.monster = Monster(x, y - MONSTER_SIZE[1], width)

        if initial_bonus:
            self.add_bonus(Bonus)

    @property
    def bonus(self):
        return self.__bonus

    def add_bonus(self, bonus_type):
        if not self.breakable:
            self.__bonus = bonus_type(self)

    def remove_bonus(self):
        self.__bonus = None

    def onCollide(self):
        if self.breakable and not self.breaking:
            self.breaking = True
            if self.break_animation:
                self.break_animation = Animation(self.break_animation.frames, loop=False, frame_duration=50)
        if self.__bonus:
            self.__bonus.activate()

    def update(self):
        if self.monster:
            self.monster.update()
            if self.monster.dead:
                current_time = pygame.time.get_ticks()
                if current_time - self.monster.death_time >= 200:
                    self.monster = None

        if self.breaking and self.break_animation and self.break_animation.finished:
            self.__level.remove_platform(self)
            
        if Camera.instance:
            camera_rect = Camera.instance.apply(self)
        else:
            camera_rect = self.rect
        if camera_rect.y + self.rect.height > YWIN:
            self.__level.remove_platform(self)

    def draw(self, surface):
        if self.breakable and self.breaking and self.break_animation:
            current_frame = self.break_animation.update()
        else:
            current_frame = self._image

        if Camera.instance:
            camera_rect = Camera.instance.apply(self)
        else:
            camera_rect = self.rect

        surface.blit(current_frame, camera_rect)

        if self.__bonus:
            self.__bonus.draw(surface)

        if self.monster:
            if Camera.instance:
                monster_camera_rect = Camera.instance.apply(self.monster)
                surface.blit(self.monster._image, monster_camera_rect)
            else:
                surface.blit(self.monster._image, self.monster.rect)

class Level(Singleton):
    def __init__(self):
        self.platform_size = PLATFORM_SIZE
        self.max_platforms = MAX_PLATFORM_NUMBER
        self.distance_min, self.distance_max = PLATFORM_DISTANCE_GAP
        self.bonus_platform_chance = BONUS_SPAWN_CHANCE
        self.breakable_platform_chance = BREAKABLE_PLATFORM_CHANCE
        self.__platforms = []
        self.__bullets = []
        self.__to_remove = []
        self.__base_platform = Platform(
            HALF_XWIN - PLATFORM_SIZE[0]//2,
            HALF_YWIN + YWIN//3,
            *PLATFORM_SIZE
        )

    @property
    def platforms(self):
        return self.__platforms

    def add_bullet(self, bullet):
        self.__bullets.append(bullet)

    def remove_bullet(self, bullet):
        if bullet in self.__bullets:
            self.__to_remove.append(bullet)

    def remove_platform(self, platform):
        if platform in self.__platforms:
            self.__to_remove.append(platform)
            return True
        return False

    async def _generation(self):
        needed = self.max_platforms - len(self.__platforms)
        for _ in range(needed):
            self.create_platform()

    def create_platform(self):
        if self.__platforms:
            offset = random.randint(self.distance_min, self.distance_max)
            x = random.randint(0, XWIN - self.platform_size[0])
            y = self.__platforms[-1].rect.y - offset
            self.__platforms.append(Platform(
                x, y, *self.platform_size,
                initial_bonus=chance(self.bonus_platform_chance),
                breakable=chance(self.breakable_platform_chance)
            ))
        else:
            self.__platforms.append(self.__base_platform)

    def reset(self):
        self.__platforms = [self.__base_platform]
        self.__bullets = []

    async def update(self):
        for p in self.__to_remove:
            if p in self.__platforms:
                self.__platforms.remove(p)
            if p in self.__bullets:
                self.__bullets.remove(p)
        self.__to_remove = []
        for platform in self.__platforms:
            platform.update()
        for bullet in self.__bullets:
            bullet.update()
        await self._generation()

    def draw(self, surface):
        for platform in self.__platforms:
            platform.draw(surface)
        for bullet in self.__bullets:
            bullet.draw(surface)

class Game(Singleton):
    def __init__(self):
        self.__alive = True
        self.window = pygame.display.set_mode(DISPLAY, FLAGS)
        pygame.display.set_caption("Doodle Jump")
        self.clock = pygame.time.Clock()
        self.camera = Camera()
        self.lvl = Level()
        self.player = Player(
            HALF_XWIN - PLAYER_SIZE[0]//2,
            HALF_YWIN + HALF_YWIN//2,
            *PLAYER_SIZE,
            PLAYER_COLOR
        )
        self.background = Background()
        self.main_menu = MainMenu()
        self.game_over_screen = GameOverScreen()
        self.game_state = GameState.MENU
        self.score = 0
        self.score_txt = SMALL_FONT.render("0 m", True, GRAY)
        self.score_pos = Vector2(10, 10)

    def reset(self):
        self.camera.reset()
        self.lvl.reset()
        self.player.reset()
        self.score = 0
        self.score_txt = SMALL_FONT.render("0 m", True, GRAY)
        self.game_state = GameState.PLAYING

    def _event_loop(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.close()
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.close()
                elif event.key == K_RETURN:
                    if self.game_state == GameState.MENU:
                        self.reset()
                    elif self.game_state == GameState.GAME_OVER:
                        self.game_state = GameState.MENU
            if self.game_state == GameState.PLAYING:
                self.player.handle_event(event)

    async def _update_loop(self):
        if self.game_state == GameState.MENU:
            self.main_menu.update()
        elif self.game_state == GameState.PLAYING:
            self.player.update()
            await self.lvl.update()
            if not self.player.dead:
                self.camera.update(self.player.rect)
                self.score = -self.camera.state.y//50
                self.score_txt = SMALL_FONT.render(f"{self.score} m", True, GRAY)
            else:
                self.game_state = GameState.GAME_OVER
                self.game_over_screen.update(self.score)
        elif self.game_state == GameState.GAME_OVER:
            pass

    def _render_loop(self):
        if self.game_state == GameState.MENU:
            self.main_menu.draw(self.window)
        elif self.game_state == GameState.PLAYING:
            self.background.draw(self.window, self.camera.state.y)
            self.lvl.draw(self.window)
            self.player.draw(self.window)
            self.window.blit(self.score_txt, self.score_pos)
        elif self.game_state == GameState.GAME_OVER:
            self.game_over_screen.draw(self.window)
        pygame.display.update()
        self.clock.tick(FPS)

    async def run(self):
        while self.__alive:
            self._event_loop()
            await self._update_loop()
            self._render_loop()
            await asyncio.sleep(0)
        pygame.quit()

async def main():
    game = Game()
    await game.run()

if __name__ == "__main__":
    asyncio.run(main())

