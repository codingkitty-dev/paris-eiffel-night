"""
PARIS - EIFFEL TOWER PIXEL ART NIGHT
====================================
A complete, self-contained, programmatically rendered 8-bit/16-bit pixel art
animation of Paris at night using Python and Pygame.

Controls:
    F / F11  : Toggle fullscreen mode
    SPACE    : Pause / resume animation
    H        : Toggle minimal retro status overlay
    ESC / Q  : Clean exit

Command-line options:
    python paris_eiffel_night.py --fullscreen
    python paris_eiffel_night.py --fps 60
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from dataclasses import dataclass
from typing import List, Tuple

import pygame


# ---------------------------------------------------------------------------
# Configuration & Palette
# ---------------------------------------------------------------------------

BASE_WIDTH = 240
BASE_HEIGHT = 160
DEFAULT_SCALE = 4
DEFAULT_FPS = 60

HORIZON_Y = 104
QUAY_TOP_Y = 104
RIVER_TOP_Y = 112
TOWER_CENTER_X = BASE_WIDTH // 2


class Palette:
    """Curated 8-bit/16-bit nocturnal Paris color palette."""

    # Night sky bands (top -> horizon)
    SKY_BANDS: Tuple[Tuple[int, int, int], ...] = (
        (8, 10, 28),    # Deep void navy
        (13, 15, 42),   # Midnight navy
        (20, 19, 56),   # Deep indigo
        (31, 24, 68),   # Midnight purple
        (44, 30, 74),   # Warm twilight plum
    )

    # Moon & stars
    MOON_CORE = (244, 240, 214)
    MOON_SHADE = (196, 198, 218)
    STAR_DIM = (115, 128, 178)
    STAR_MID = (190, 204, 242)
    STAR_BRIGHT = (255, 250, 228)
    STAR_WARM = (255, 224, 165)

    # Clouds
    CLOUD_FAR_DARK = (24, 22, 54)
    CLOUD_FAR_MID = (34, 30, 68)
    CLOUD_FAR_EDGE = (48, 38, 78)
    CLOUD_NEAR_DARK = (30, 25, 62)
    CLOUD_NEAR_MID = (44, 36, 80)
    CLOUD_NEAR_EDGE = (66, 46, 84)

    # City & buildings
    DISTANT_CITY = (18, 16, 38)
    DISTANT_ROOF = (13, 12, 30)
    BUILDING_WALL_A = (22, 20, 42)
    BUILDING_WALL_B = (28, 24, 48)
    BUILDING_WALL_C = (20, 18, 36)
    BUILDING_TRIM = (42, 36, 64)
    BUILDING_ROOF = (13, 13, 28)
    TREE_DARK = (12, 16, 28)
    TREE_MID = (19, 24, 38)

    # Warm window colors
    WINDOW_COLORS: Tuple[Tuple[int, int, int], ...] = (
        (255, 206, 98),
        (246, 168, 62),
        (255, 228, 142),
        (220, 134, 48),
    )
    WINDOW_DIM = (120, 78, 38)
    WINDOW_OFF = (15, 14, 30)

    # Quay & streetlamps
    QUAY_TOP = (40, 35, 58)
    QUAY_FACE = (24, 22, 40)
    QUAY_SHADOW = (14, 13, 26)
    QUAY_ARCH = (9, 10, 22)
    LAMP_POST = (12, 12, 22)
    LAMP_CORE = (255, 226, 128)
    LAMP_WARM = (255, 172, 64)

    # Eiffel Tower ironwork & golden illumination
    TOWER_SHADOW = (24, 18, 30)
    TOWER_IRON = (46, 32, 38)
    TOWER_GOLD_DARK = (122, 78, 34)
    TOWER_GOLD_MID = (184, 126, 46)
    TOWER_GOLD_BRIGHT = (238, 182, 74)
    TOWER_LIGHT = (255, 224, 118)
    TOWER_SPARKLE = (255, 252, 224)

    # Seine River
    RIVER_TOP = (12, 16, 38)
    RIVER_MID = (15, 20, 48)
    RIVER_DEEP = (9, 12, 30)
    RIVER_RIPPLE_LIGHT = (26, 32, 66)
    RIVER_RIPPLE_DARK = (7, 10, 24)

    # Boats
    BOAT_HULL_DARK = (18, 16, 30)
    BOAT_HULL_TRIM = (42, 38, 60)
    BOAT_CABIN = (28, 26, 46)
    BOAT_WINDOW = (255, 214, 110)
    BOAT_RED = (235, 68, 68)
    BOAT_GREEN = (74, 224, 122)
    BOAT_WAKE = (42, 50, 88)

    # Snow
    SNOW_FAR = (148, 160, 204)
    SNOW_MID = (206, 216, 242)
    SNOW_NEAR = (246, 248, 255)
    SNOW_WARM = (255, 236, 194)


# ---------------------------------------------------------------------------
# Pixel Art Helper Utilities
# ---------------------------------------------------------------------------

def clamp(value: float, low: float, high: float) -> float:
    """Clamp a numeric value to [low, high]."""
    return max(low, min(high, value))


def lerp_color(
    c1: Tuple[int, int, int],
    c2: Tuple[int, int, int],
    t: float,
) -> Tuple[int, int, int]:
    """Linearly interpolate between two RGB colors."""
    t = clamp(t, 0.0, 1.0)
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def create_pixel_glow(
    radius: int,
    color: Tuple[int, int, int],
    max_alpha: int,
    rings: int = 4,
) -> pygame.Surface:
    """Create a quantized concentric pixel-art glow surface (no smooth blur)."""
    diameter = radius * 2 + 1
    surf = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    cx = radius
    cy = radius
    for step in range(rings, 0, -1):
        r = max(1, int(round(radius * (step / rings))))
        falloff = (1.0 - (step - 1) / rings) ** 1.5
        alpha = int(max_alpha * falloff)
        pygame.draw.circle(surf, (*color, alpha), (cx, cy), r)
    return surf


def draw_pixel_ellipse_glow(
    target: pygame.Surface,
    cx: int,
    cy: int,
    rx: int,
    ry: int,
    color: Tuple[int, int, int],
    max_alpha: int,
    steps: int = 4,
) -> None:
    """Draw a stepped elliptical pixel halo onto a surface."""
    glow = pygame.Surface((rx * 2 + 2, ry * 2 + 2), pygame.SRCALPHA)
    for step in range(steps, 0, -1):
        frac = step / steps
        cur_rx = max(1, int(rx * frac))
        cur_ry = max(1, int(ry * frac))
        alpha = int(max_alpha * ((1.0 - (step - 1) / steps) ** 1.6))
        rect = pygame.Rect(
            rx + 1 - cur_rx,
            ry + 1 - cur_ry,
            cur_rx * 2,
            cur_ry * 2,
        )
        pygame.draw.ellipse(glow, (*color, alpha), rect)
    target.blit(glow, (cx - rx - 1, cy - ry - 1))


# ---------------------------------------------------------------------------
# 1. Night Sky & Crescent Moon
# ---------------------------------------------------------------------------

class NightSky:
    """Pre-rendered dithered night sky with subtle ambient Paris horizon glow."""

    def __init__(self, width: int, horizon_y: int) -> None:
        self.width = width
        self.horizon_y = horizon_y
        self.moon_pos = (38, 22)
        self.surface = pygame.Surface((width, horizon_y))
        self.moon_glow = create_pixel_glow(16, (150, 165, 225), max_alpha=26, rings=4)
        self._build_sky()

    def _build_sky(self) -> None:
        """Render banded navy-to-midnight-purple sky with 2x2 pixel dithering."""
        bands = Palette.SKY_BANDS
        num_bands = len(bands)
        band_height = self.horizon_y / num_bands

        for y in range(self.horizon_y):
            exact = y / band_height
            idx = min(int(exact), num_bands - 1)
            frac = exact - idx
            base_col = bands[idx]
            next_col = bands[min(idx + 1, num_bands - 1)]

            pygame.draw.line(self.surface, base_col, (0, y), (self.width - 1, y))

            # Ordered pixel dithering near band borders for authentic 16-bit look
            if idx < num_bands - 1 and frac > 0.68:
                density = (frac - 0.68) / 0.32
                for x in range(self.width):
                    if density > 0.66:
                        use_next = ((x + y) % 2 == 0) or (x % 2 == 0 and y % 2 == 0)
                    elif density > 0.33:
                        use_next = (x + y) % 2 == 0
                    else:
                        use_next = (x % 2 == 0) and (y % 2 == 0)
                    if use_next:
                        self.surface.set_at((x, y), next_col)

        # Warm ambient atmospheric glow behind the Eiffel Tower
        draw_pixel_ellipse_glow(
            self.surface,
            TOWER_CENTER_X,
            self.horizon_y - 6,
            66,
            42,
            (210, 130, 60),
            max_alpha=24,
            steps=5,
        )
        draw_pixel_ellipse_glow(
            self.surface,
            TOWER_CENTER_X,
            self.horizon_y - 16,
            34,
            26,
            (255, 178, 72),
            max_alpha=22,
            steps=4,
        )

        # Crescent pixel moon
        mx, my = self.moon_pos
        self.surface.blit(
            self.moon_glow,
            (mx - self.moon_glow.get_width() // 2, my - self.moon_glow.get_height() // 2),
        )
        moon_pixels = [
            "   ####  ",
            "  ###### ",
            " #####   ",
            " ####    ",
            " ####    ",
            " #####   ",
            "  ###### ",
            "   ####  ",
        ]
        for dy, row in enumerate(moon_pixels):
            for dx, ch in enumerate(row):
                if ch == "#":
                    col = Palette.MOON_SHADE if dx <= 1 or dy in (0, 7) else Palette.MOON_CORE
                    self.surface.set_at((mx - 4 + dx, my - 4 + dy), col)

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        """Blit sky and subtle pulsing atmospheric aura around the tower."""
        target.blit(self.surface, (0, 0))
        pulse = 0.5 + 0.5 * math.sin(elapsed * 1.1)
        alpha = int(10 + 7 * pulse)
        draw_pixel_ellipse_glow(
            target,
            TOWER_CENTER_X,
            self.horizon_y - 24,
            44,
            38,
            (255, 184, 78),
            max_alpha=alpha,
            steps=3,
        )


# ---------------------------------------------------------------------------
# 2. Twinkling Stars
# ---------------------------------------------------------------------------

@dataclass
class Star:
    x: int
    y: int
    phase: float
    speed: float
    tier: int  # 0 = tiny dot, 1 = medium dot, 2 = cross twinkle
    warm: bool


class StarField:
    """Manages naturally twinkling pixel stars across the night sky."""

    def __init__(self, width: int, max_y: int, count: int = 72, seed: int = 42) -> None:
        rng = random.Random(seed)
        self.stars: List[Star] = []
        for _ in range(count):
            x = rng.randint(2, width - 3)
            y = int((rng.random() ** 1.35) * (max_y - 10)) + 2
            if abs(x - 38) < 10 and abs(y - 22) < 10:
                continue
            tier = rng.choices([0, 1, 2], weights=[62, 28, 10])[0]
            self.stars.append(
                Star(
                    x=x,
                    y=y,
                    phase=rng.uniform(0.0, math.tau),
                    speed=rng.uniform(0.9, 2.8),
                    tier=tier,
                    warm=rng.random() < 0.22,
                )
            )

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        for star in self.stars:
            twinkle = 0.5 + 0.5 * math.sin(elapsed * star.speed + star.phase)
            if star.tier == 0:
                if twinkle < 0.28:
                    continue
                col = Palette.STAR_MID if twinkle > 0.72 else Palette.STAR_DIM
                target.set_at((star.x, star.y), col)
            elif star.tier == 1:
                if twinkle > 0.76:
                    col = Palette.STAR_WARM if star.warm else Palette.STAR_BRIGHT
                elif twinkle > 0.35:
                    col = Palette.STAR_MID
                else:
                    col = Palette.STAR_DIM
                target.set_at((star.x, star.y), col)
            else:
                core = Palette.STAR_WARM if star.warm else Palette.STAR_BRIGHT
                if twinkle > 0.78:
                    target.set_at((star.x, star.y), core)
                    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        target.set_at((star.x + ox, star.y + oy), Palette.STAR_DIM)
                elif twinkle > 0.35:
                    target.set_at((star.x, star.y), Palette.STAR_MID)
                else:
                    target.set_at((star.x, star.y), Palette.STAR_DIM)


# ---------------------------------------------------------------------------
# 3. Drifting Pixel Clouds
# ---------------------------------------------------------------------------

class Cloud:
    """Cohesive, billowy retro pixel-art cloud sprite."""

    def __init__(
        self,
        x: float,
        y: int,
        speed: float,
        layer: int,
        rng: random.Random,
    ) -> None:
        self.x = x
        self.y = y
        self.speed = speed
        self.layer = layer
        self.surface = self._generate_sprite(layer, rng)
        self.width = self.surface.get_width()

    @staticmethod
    def _generate_sprite(layer: int, rng: random.Random) -> pygame.Surface:
        width = rng.randint(28, 42) if layer == 0 else rng.randint(36, 52)
        height = rng.randint(10, 13) if layer == 0 else rng.randint(12, 16)
        surf = pygame.Surface((width, height), pygame.SRCALPHA)

        if layer == 0:
            c_dark = (*Palette.CLOUD_FAR_DARK, 175)
            c_mid = (*Palette.CLOUD_FAR_MID, 190)
            c_edge = (*Palette.CLOUD_FAR_EDGE, 165)
        else:
            c_dark = (*Palette.CLOUD_NEAR_DARK, 200)
            c_mid = (*Palette.CLOUD_NEAR_MID, 215)
            c_edge = (*Palette.CLOUD_NEAR_EDGE, 190)

        # Build a dense, cohesive overlapping pixel cloud silhouette
        base_y = height - 2
        # Soft top highlight puffs
        cx_mid = width // 2
        puffs = [
            (width // 4, base_y - 3, max(4, height // 3)),
            (cx_mid - 4, base_y - 4, max(5, height // 2 - 1)),
            (cx_mid + 3, base_y - 4, max(4, height // 2 - 2)),
            ((3 * width) // 4, base_y - 3, max(4, height // 3)),
        ]
        # Fill top rim
        for px, py, pr in puffs:
            pygame.draw.circle(surf, c_mid, (px, py - 1), pr)
        # Solid connected cloud body
        pygame.draw.rect(surf, c_dark, (4, base_y - 4, width - 8, 5))
        pygame.draw.rect(surf, c_dark, (2, base_y - 2, width - 4, 3))
        for px, py, pr in puffs:
            pygame.draw.circle(surf, c_dark, (px, py + 1), max(2, pr - 1))

        # Warm city-glow underside highlight
        pygame.draw.line(surf, c_edge, (4, base_y), (width - 5, base_y))
        return surf

    def update(self, dt: float, world_width: int) -> None:
        self.x += self.speed * dt
        if self.x > world_width + 8:
            self.x = -self.width - 8

    def draw(self, target: pygame.Surface) -> None:
        target.blit(self.surface, (int(round(self.x)), self.y))


class CloudLayer:
    """Two-depth parallax drifting clouds."""

    def __init__(self, width: int, seed: int = 108) -> None:
        rng = random.Random(seed)
        self.width = width
        self.clouds: List[Cloud] = []

        # Far slow clouds
        for i in range(4):
            cx = i * (width / 4) + rng.uniform(-10, 16)
            cy = rng.randint(14, 32)
            self.clouds.append(Cloud(cx, cy, rng.uniform(1.6, 2.8), layer=0, rng=rng))

        # Near slightly faster clouds
        for i in range(3):
            cx = i * (width / 3) + rng.uniform(-8, 18)
            cy = rng.randint(34, 52)
            self.clouds.append(Cloud(cx, cy, rng.uniform(3.2, 4.6), layer=1, rng=rng))

    def update(self, dt: float) -> None:
        for cloud in self.clouds:
            cloud.update(dt, self.width)

    def draw_far(self, target: pygame.Surface) -> None:
        for cloud in self.clouds:
            if cloud.layer == 0:
                cloud.draw(target)

    def draw_near(self, target: pygame.Surface) -> None:
        for cloud in self.clouds:
            if cloud.layer == 1:
                cloud.draw(target)


# ---------------------------------------------------------------------------
# 4. Parisian Haussmann Cityscape, Quay & Streetlamps
# ---------------------------------------------------------------------------

@dataclass
class WindowLight:
    x: int
    y: int
    w: int
    h: int
    color: Tuple[int, int, int]
    lit: bool
    flicker_phase: float
    flicker_speed: float
    can_flicker: bool


class Building:
    """Programmatically drawn Parisian Haussmann building with mansard roof."""

    def __init__(
        self,
        x: int,
        base_y: int,
        width: int,
        height: int,
        wall_color: Tuple[int, int, int],
        rng: random.Random,
    ) -> None:
        self.x = x
        self.base_y = base_y
        self.width = width
        self.height = height
        self.top_y = base_y - height
        self.wall_color = wall_color
        self.roof_height = rng.randint(5, 8)
        self.chimneys: List[Tuple[int, int, int]] = []
        self.windows: List[WindowLight] = []

        num_chimneys = rng.randint(1, 2)
        for _ in range(num_chimneys):
            cx = self.x + rng.randint(3, max(3, self.width - 6))
            ch = rng.randint(3, 5)
            self.chimneys.append((cx, self.top_y - self.roof_height - ch + 1, ch))

        cols = max(2, (self.width - 4) // 5)
        rows = max(2, (self.height - 6) // 7)
        margin_x = (self.width - cols * 5 + 2) // 2
        for r in range(rows):
            wy = self.top_y + 4 + r * 7
            if wy + 3 >= self.base_y - 2:
                continue
            for c in range(cols):
                wx = self.x + margin_x + c * 5
                if wx + 2 >= self.x + self.width - 1:
                    continue
                lit = rng.random() < 0.64
                self.windows.append(
                    WindowLight(
                        x=wx,
                        y=wy,
                        w=2,
                        h=3,
                        color=rng.choice(Palette.WINDOW_COLORS),
                        lit=lit,
                        flicker_phase=rng.uniform(0.0, math.tau),
                        flicker_speed=rng.uniform(1.8, 5.2),
                        can_flicker=lit and (rng.random() < 0.28),
                    )
                )

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        pygame.draw.rect(
            target,
            self.wall_color,
            (self.x, self.top_y, self.width, self.height),
        )
        pygame.draw.line(
            target,
            Palette.BUILDING_TRIM,
            (self.x, self.top_y),
            (self.x, self.base_y - 1),
        )
        pygame.draw.line(
            target,
            Palette.BUILDING_TRIM,
            (self.x, self.top_y),
            (self.x + self.width - 1, self.top_y),
        )
        if self.height > 20:
            balcony_y = self.top_y + 9
            pygame.draw.line(
                target,
                Palette.BUILDING_TRIM,
                (self.x, balcony_y),
                (self.x + self.width - 1, balcony_y),
            )

        roof_poly = [
            (self.x, self.top_y),
            (self.x + 2, self.top_y - self.roof_height),
            (self.x + self.width - 3, self.top_y - self.roof_height),
            (self.x + self.width - 1, self.top_y),
        ]
        pygame.draw.polygon(target, Palette.BUILDING_ROOF, roof_poly)
        pygame.draw.line(
            target,
            Palette.BUILDING_TRIM,
            (self.x + 2, self.top_y - self.roof_height),
            (self.x + self.width - 3, self.top_y - self.roof_height),
        )

        dormer_y = self.top_y - self.roof_height // 2 - 1
        for dx in range(self.x + 4, self.x + self.width - 4, 6):
            target.set_at((dx, dormer_y), Palette.WINDOW_DIM)

        for cx, cy, ch in self.chimneys:
            pygame.draw.rect(target, Palette.BUILDING_ROOF, (cx, cy, 2, ch))
            target.set_at((cx, cy), Palette.BUILDING_TRIM)

        for win in self.windows:
            if not win.lit:
                pygame.draw.rect(target, Palette.WINDOW_OFF, (win.x, win.y, win.w, win.h))
                continue

            col = win.color
            if win.can_flicker:
                wave = 0.5 + 0.5 * math.sin(elapsed * win.flicker_speed + win.flicker_phase)
                if wave < 0.22:
                    col = Palette.WINDOW_DIM
                elif wave > 0.85:
                    col = (255, 236, 165)

            pygame.draw.rect(target, col, (win.x, win.y, win.w, win.h))
            pygame.draw.line(
                target,
                Palette.QUAY_SHADOW,
                (win.x, win.y + win.h),
                (win.x + win.w - 1, win.y + win.h),
            )


class Cityscape:
    """Parisian skyline, Haussmann flanking buildings, trees, quay wall, and lamps."""

    def __init__(self, width: int, horizon_y: int, seed: int = 77) -> None:
        self.width = width
        self.horizon_y = horizon_y
        rng = random.Random(seed)

        self.distant_blocks: List[Tuple[int, int, int, int]] = []
        bx = 0
        while bx < width:
            bw = rng.randint(10, 18)
            bh = rng.randint(10, 22)
            if 82 <= bx <= 154:
                bh = rng.randint(7, 13)
            self.distant_blocks.append((bx, horizon_y - bh, bw, bh))
            bx += bw - 1

        self.distant_dots: List[Tuple[int, int, Tuple[int, int, int]]] = []
        for x, y, w, h in self.distant_blocks:
            for wy in range(y + 3, horizon_y - 3, 4):
                for wx in range(x + 2, x + w - 2, 4):
                    if rng.random() < 0.35:
                        self.distant_dots.append((wx, wy, Palette.WINDOW_DIM))

        wall_choices = [Palette.BUILDING_WALL_A, Palette.BUILDING_WALL_B, Palette.BUILDING_WALL_C]
        self.buildings: List[Building] = []
        left_specs = [
            (0, 22, 44),
            (21, 20, 36),
            (40, 18, 29),
            (57, 16, 22),
        ]
        for x, w, h in left_specs:
            self.buildings.append(Building(x, horizon_y, w, h, rng.choice(wall_choices), rng))

        right_specs = [
            (167, 16, 23),
            (182, 18, 31),
            (199, 20, 38),
            (218, 22, 45),
        ]
        for x, w, h in right_specs:
            self.buildings.append(Building(x, horizon_y, w, h, rng.choice(wall_choices), rng))

        self.trees: List[Tuple[int, int, int]] = [
            (75, horizon_y - 4, 5),
            (83, horizon_y - 3, 4),
            (90, horizon_y - 4, 5),
            (150, horizon_y - 4, 5),
            (157, horizon_y - 3, 4),
            (164, horizon_y - 4, 5),
        ]

        self.lamp_xs: List[int] = [14, 38, 62, 86, 154, 178, 202, 226]
        self.lamp_glow = create_pixel_glow(9, Palette.LAMP_WARM, max_alpha=62, rings=4)
        self.window_glow = create_pixel_glow(6, Palette.LAMP_WARM, max_alpha=24, rings=3)

    def get_glowing_window_positions(self) -> List[Tuple[int, Tuple[int, int, int]]]:
        positions: List[Tuple[int, Tuple[int, int, int]]] = []
        for b in self.buildings:
            for w in b.windows:
                if w.lit:
                    positions.append((w.x + 1, w.color))
        return positions

    def draw_background(self, target: pygame.Surface, elapsed: float) -> None:
        for x, y, w, h in self.distant_blocks:
            pygame.draw.rect(target, Palette.DISTANT_CITY, (x, y, w, h))
            pygame.draw.line(target, Palette.DISTANT_ROOF, (x, y), (x + w - 1, y))
        for wx, wy, col in self.distant_dots:
            target.set_at((wx, wy), col)

        for building in self.buildings:
            building.draw(target, elapsed)

        for building in self.buildings:
            for idx, win in enumerate(building.windows):
                if win.lit and idx % 3 == 0:
                    target.blit(
                        self.window_glow,
                        (
                            win.x - self.window_glow.get_width() // 2 + 1,
                            win.y - self.window_glow.get_height() // 2 + 1,
                        ),
                    )

        for tx, ty, tr in self.trees:
            pygame.draw.circle(target, Palette.TREE_DARK, (tx, ty), tr)
            pygame.draw.circle(target, Palette.TREE_MID, (tx - 1, ty - 1), max(2, tr - 2))

    def draw_quay_and_lamps(self, target: pygame.Surface, elapsed: float) -> None:
        quay_h = RIVER_TOP_Y - QUAY_TOP_Y
        pygame.draw.rect(target, Palette.QUAY_FACE, (0, QUAY_TOP_Y, self.width, quay_h))
        pygame.draw.line(target, Palette.QUAY_TOP, (0, QUAY_TOP_Y), (self.width - 1, QUAY_TOP_Y))
        pygame.draw.line(
            target,
            Palette.QUAY_SHADOW,
            (0, RIVER_TOP_Y - 1),
            (self.width - 1, RIVER_TOP_Y - 1),
        )

        for ax in range(8, self.width - 8, 22):
            pygame.draw.rect(target, Palette.QUAY_ARCH, (ax, QUAY_TOP_Y + 3, 10, quay_h - 3))
            pygame.draw.line(
                target,
                Palette.QUAY_SHADOW,
                (ax + 1, QUAY_TOP_Y + 2),
                (ax + 8, QUAY_TOP_Y + 2),
            )

        for i, lx in enumerate(self.lamp_xs):
            post_top = QUAY_TOP_Y - 6
            pygame.draw.line(target, Palette.LAMP_POST, (lx, post_top), (lx, QUAY_TOP_Y))
            target.set_at((lx - 1, post_top + 1), Palette.LAMP_POST)
            target.set_at((lx + 1, post_top + 1), Palette.LAMP_POST)

            flicker = 0.85 + 0.15 * math.sin(elapsed * 4.2 + i * 1.7)
            glow_copy = self.lamp_glow.copy()
            glow_copy.set_alpha(int(255 * flicker))
            target.blit(
                glow_copy,
                (lx - glow_copy.get_width() // 2, post_top - glow_copy.get_height() // 2),
            )
            target.set_at((lx, post_top), Palette.LAMP_CORE)
            target.set_at((lx, post_top - 1), Palette.LAMP_WARM)


# ---------------------------------------------------------------------------
# 5. Detailed Pixel-Art Eiffel Tower with Golden Illumination & Sparkles
# ---------------------------------------------------------------------------

@dataclass
class SparkleBulb:
    x: int
    y: int
    phase: float
    speed: float
    threshold: float


class EiffelTower:
    """Programmatically rendered 8-bit/16-bit Eiffel Tower with glowing lights."""

    def __init__(self, center_x: int, base_y: int, seed: int = 1889) -> None:
        self.cx = center_x
        self.base_y = base_y
        self.tip_y = 12
        self.summit_y = 20
        self.deck2_y = 56
        self.deck1_y = 79
        self.arch_top_y = 91

        self.surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
        self.warm_lights: List[Tuple[int, int, float]] = []
        self.sparkles: List[SparkleBulb] = []
        self.beacon_glow = create_pixel_glow(13, Palette.TOWER_LIGHT, max_alpha=75, rings=4)

        self._build_structure(random.Random(seed))

    def half_width_at(self, y: int) -> float:
        """Return the Eiffel Tower's iconic exponential outer half-width at row y."""
        if y < self.summit_y:
            return 0.5
        if y <= self.deck2_y:
            t = (y - self.summit_y) / (self.deck2_y - self.summit_y)
            return 2.0 + 4.8 * (t ** 1.45)
        if y <= self.deck1_y:
            t = (y - self.deck2_y) / (self.deck1_y - self.deck2_y)
            return 6.8 + 7.4 * (t ** 1.25)
        t = (y - self.deck1_y) / max(1, (self.base_y - self.deck1_y))
        return 14.2 + 12.8 * (t ** 1.15)

    def inner_arch_half_width(self, y: int) -> float:
        """Return the inner hollow opening width between the base legs."""
        if y < self.deck1_y + 4:
            return 0.0
        if y < self.arch_top_y:
            t = (y - (self.deck1_y + 4)) / max(1, (self.arch_top_y - (self.deck1_y + 4)))
            return 2.5 + 4.5 * t
        arch_h = self.base_y - self.arch_top_y
        dy = (y - self.arch_top_y) / max(1, arch_h)
        arch_curve = math.sqrt(max(0.0, 1.0 - (1.0 - dy) ** 2))
        return 7.0 + 9.5 * arch_curve

    def _build_structure(self, rng: random.Random) -> None:
        """Draw the pixel-art Eiffel Tower iron lattice onto a cached surface."""
        cx = self.cx

        # 1. Antenna spire
        pygame.draw.line(self.surface, Palette.TOWER_GOLD_MID, (cx, self.tip_y), (cx, self.summit_y))
        self.surface.set_at((cx, self.tip_y), Palette.TOWER_SPARKLE)
        self.surface.set_at((cx, self.tip_y + 1), Palette.TOWER_LIGHT)

        # 2. Summit observation cupola
        pygame.draw.rect(self.surface, Palette.TOWER_GOLD_DARK, (cx - 2, self.summit_y, 5, 4))
        pygame.draw.line(
            self.surface, Palette.TOWER_LIGHT, (cx - 3, self.summit_y + 2), (cx + 3, self.summit_y + 2)
        )
        pygame.draw.line(
            self.surface, Palette.TOWER_GOLD_BRIGHT, (cx - 2, self.summit_y + 4), (cx + 2, self.summit_y + 4)
        )

        # 3. Main lattice body from summit to base
        for y in range(self.summit_y + 4, self.base_y):
            outer_hw = int(round(self.half_width_at(y)))
            left_x = cx - outer_hw
            right_x = cx + outer_hw
            inner_hw = int(round(self.inner_arch_half_width(y)))

            if y < self.deck1_y:
                for x in range(left_x, right_x + 1):
                    dx = abs(x - cx)
                    is_edge = dx >= outer_hw - 1
                    is_spine = dx == 0 and y < self.deck2_y
                    is_cross = ((x - cx + y) % 5 == 0) or ((x - cx - y) % 5 == 0)
                    is_horiz = (y % 6 == 0)

                    if is_edge:
                        col = Palette.TOWER_GOLD_BRIGHT if dx == outer_hw else Palette.TOWER_GOLD_MID
                    elif is_cross or is_horiz or is_spine:
                        col = Palette.TOWER_GOLD_DARK if (x + y) % 2 == 0 else Palette.TOWER_GOLD_MID
                    else:
                        col = Palette.TOWER_SHADOW if (x + y) % 2 == 0 else Palette.TOWER_IRON
                    self.surface.set_at((x, y), col)
            else:
                for side in (-1, 1):
                    for dx in range(inner_hw, outer_hw + 1):
                        x = cx + side * dx
                        is_outer = dx >= outer_hw - 1
                        is_inner = dx <= inner_hw + 1
                        is_cross = ((dx + y) % 4 == 0) or ((dx - y) % 4 == 0)
                        if is_outer:
                            col = Palette.TOWER_GOLD_BRIGHT
                        elif is_inner:
                            col = Palette.TOWER_GOLD_MID
                        elif is_cross:
                            col = Palette.TOWER_GOLD_DARK
                        else:
                            col = Palette.TOWER_SHADOW
                        self.surface.set_at((x, y), col)

            if y % 4 == 0 and y > self.summit_y + 4:
                self.warm_lights.append((left_x, y, rng.uniform(0.0, math.tau)))
                self.warm_lights.append((right_x, y, rng.uniform(0.0, math.tau)))

            if y > self.summit_y + 5 and y < self.base_y - 2 and rng.random() < 0.72:
                for _ in range(1 if y < self.deck2_y else 2):
                    if y < self.deck1_y:
                        sx = cx + rng.randint(-max(1, outer_hw - 1), max(1, outer_hw - 1))
                    else:
                        side = rng.choice((-1, 1))
                        if outer_hw > inner_hw + 1:
                            sx = cx + side * rng.randint(inner_hw + 1, outer_hw - 1)
                        else:
                            sx = cx + side * outer_hw
                    self.sparkles.append(
                        SparkleBulb(
                            x=sx,
                            y=y,
                            phase=rng.uniform(0.0, math.tau),
                            speed=rng.uniform(4.5, 9.5),
                            threshold=rng.uniform(0.76, 0.90),
                        )
                    )

        # 4. Ornate semi-circular wrought-iron arch rim beneath Deck 1
        for angle_deg in range(8, 173, 2):
            rad = math.radians(angle_deg)
            ax = int(round(cx + math.cos(rad) * 16.0))
            ay = int(round(self.base_y - math.sin(rad) * 13.0))
            if self.deck1_y + 2 <= ay < self.base_y:
                self.surface.set_at((ax, ay), Palette.TOWER_GOLD_BRIGHT)
                self.surface.set_at((ax, ay - 1), Palette.TOWER_GOLD_MID)

        # 5. Second Observation Deck
        hw2 = int(round(self.half_width_at(self.deck2_y))) + 2
        pygame.draw.rect(
            self.surface, Palette.TOWER_IRON, (cx - hw2, self.deck2_y - 2, hw2 * 2 + 1, 5)
        )
        pygame.draw.line(
            self.surface, Palette.TOWER_LIGHT, (cx - hw2, self.deck2_y - 2), (cx + hw2, self.deck2_y - 2)
        )
        pygame.draw.line(
            self.surface, Palette.TOWER_GOLD_BRIGHT, (cx - hw2, self.deck2_y + 2), (cx + hw2, self.deck2_y + 2)
        )
        for dx in range(-hw2 + 1, hw2, 2):
            self.surface.set_at((cx + dx, self.deck2_y), Palette.TOWER_LIGHT)

        # 6. First Observation Deck
        hw1 = int(round(self.half_width_at(self.deck1_y))) + 3
        pygame.draw.rect(
            self.surface, Palette.TOWER_IRON, (cx - hw1, self.deck1_y - 2, hw1 * 2 + 1, 6)
        )
        pygame.draw.line(
            self.surface, Palette.TOWER_LIGHT, (cx - hw1, self.deck1_y - 2), (cx + hw1, self.deck1_y - 2)
        )
        pygame.draw.line(
            self.surface, Palette.TOWER_GOLD_BRIGHT, (cx - hw1, self.deck1_y + 3), (cx + hw1, self.deck1_y + 3)
        )
        for dx in range(-hw1 + 1, hw1, 3):
            self.surface.set_at((cx + dx, self.deck1_y), Palette.TOWER_LIGHT)
            self.surface.set_at((cx + dx, self.deck1_y + 1), Palette.TOWER_GOLD_MID)

        # 7. Masonry base pedestals
        foot_hw = int(round(self.half_width_at(self.base_y - 1)))
        pygame.draw.rect(self.surface, Palette.TOWER_IRON, (cx - foot_hw - 2, self.base_y - 3, 12, 3))
        pygame.draw.rect(self.surface, Palette.TOWER_IRON, (cx + foot_hw - 9, self.base_y - 3, 12, 3))
        pygame.draw.line(
            self.surface, Palette.TOWER_GOLD_MID, (cx - foot_hw - 2, self.base_y - 3), (cx - foot_hw + 9, self.base_y - 3)
        )
        pygame.draw.line(
            self.surface, Palette.TOWER_GOLD_MID, (cx + foot_hw - 9, self.base_y - 3), (cx + foot_hw + 2, self.base_y - 3)
        )

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        """Render the Eiffel Tower with golden glow, flickering lights, and sparkles."""
        breathe = 0.85 + 0.15 * math.sin(elapsed * 1.8)
        draw_pixel_ellipse_glow(
            target,
            self.cx,
            self.deck1_y,
            24,
            10,
            Palette.TOWER_GOLD_BRIGHT,
            max_alpha=int(34 * breathe),
            steps=3,
        )
        draw_pixel_ellipse_glow(
            target,
            self.cx,
            self.deck2_y,
            15,
            8,
            Palette.TOWER_GOLD_BRIGHT,
            max_alpha=int(30 * breathe),
            steps=3,
        )

        # Rotating summit searchlight beam (warm golden pixel cone)
        beam_cycle = math.sin(elapsed * 1.35)
        if abs(beam_cycle) > 0.18:
            beam_dir = 1 if beam_cycle > 0 else -1
            beam_len = int(20 + 30 * abs(beam_cycle))
            beam_alpha = int(42 * abs(beam_cycle))
            beam_surf = pygame.Surface((BASE_WIDTH, BASE_HEIGHT), pygame.SRCALPHA)
            tip = (self.cx, self.tip_y + 1)
            end_x = self.cx + beam_dir * beam_len
            poly = [tip, (end_x, self.tip_y - 4), (end_x, self.tip_y + 6)]
            pygame.draw.polygon(beam_surf, (255, 224, 124, beam_alpha), poly)
            target.blit(beam_surf, (0, 0))

        target.blit(self.surface, (0, 0))

        # Gently flickering golden structural lights
        for lx, ly, phase in self.warm_lights:
            wave = 0.5 + 0.5 * math.sin(elapsed * 3.1 + phase)
            if wave > 0.65:
                target.set_at((lx, ly), Palette.TOWER_LIGHT)
            elif wave > 0.25:
                target.set_at((lx, ly), Palette.TOWER_GOLD_BRIGHT)
            else:
                target.set_at((lx, ly), Palette.TOWER_GOLD_MID)

        # Iconic Eiffel Tower twinkling sparkle strobes
        for bulb in self.sparkles:
            v = 0.5 + 0.5 * math.sin(elapsed * bulb.speed + bulb.phase)
            if v > bulb.threshold:
                target.set_at((bulb.x, bulb.y), Palette.TOWER_SPARKLE)
                if v > bulb.threshold + 0.08:
                    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        px, py = bulb.x + ox, bulb.y + oy
                        if 0 <= px < BASE_WIDTH and 0 <= py < BASE_HEIGHT:
                            target.set_at((px, py), Palette.TOWER_LIGHT)
            elif v > bulb.threshold - 0.12:
                target.set_at((bulb.x, bulb.y), Palette.TOWER_GOLD_BRIGHT)

        # Pulsing summit beacon
        beacon_pulse = 0.5 + 0.5 * math.sin(elapsed * 2.7)
        glow_copy = self.beacon_glow.copy()
        glow_copy.set_alpha(int(120 + 135 * beacon_pulse))
        target.blit(
            glow_copy,
            (
                self.cx - glow_copy.get_width() // 2,
                self.tip_y - glow_copy.get_height() // 2 + 1,
            ),
        )
        target.set_at((self.cx, self.tip_y), Palette.TOWER_SPARKLE)
        target.set_at((self.cx, self.tip_y + 1), Palette.TOWER_LIGHT)


# ---------------------------------------------------------------------------
# 6. Seine River with Animated Pixel Reflections
# ---------------------------------------------------------------------------

class SeineRiver:
    """Foreground Seine River with shimmering Eiffel Tower and lamp reflections."""

    def __init__(
        self,
        width: int,
        top_y: int,
        height: int,
        tower: EiffelTower,
        lamp_xs: List[int],
        window_positions: List[Tuple[int, Tuple[int, int, int]]],
        seed: int = 2026,
    ) -> None:
        self.width = width
        self.top_y = top_y
        self.height = height
        self.tower = tower
        self.lamp_xs = lamp_xs
        self.window_positions = window_positions

        self.base_surface = pygame.Surface((width, height))
        self._build_base_water()

        rng = random.Random(seed)
        self.ripples: List[Tuple[float, int, int, float, bool]] = []
        for _ in range(38):
            rx = rng.uniform(0, width)
            ry = rng.randint(2, height - 2)
            rw = rng.randint(4, 14)
            speed = rng.uniform(2.0, 5.5) * rng.choice((-1, 1))
            bright = rng.random() < 0.55
            self.ripples.append((rx, ry, rw, speed, bright))

    def _build_base_water(self) -> None:
        for y in range(self.height):
            t = y / max(1, self.height - 1)
            if t < 0.45:
                col = lerp_color(Palette.RIVER_TOP, Palette.RIVER_MID, t / 0.45)
            else:
                col = lerp_color(Palette.RIVER_MID, Palette.RIVER_DEEP, (t - 0.45) / 0.55)
            pygame.draw.line(self.base_surface, col, (0, y), (self.width - 1, y))

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        target.blit(self.base_surface, (0, self.top_y))

        for rx, ry, rw, speed, bright in self.ripples:
            x = int((rx + elapsed * speed) % (self.width + rw)) - rw
            col = Palette.RIVER_RIPPLE_LIGHT if bright else Palette.RIVER_RIPPLE_DARK
            pygame.draw.line(target, col, (x, self.top_y + ry), (x + rw, self.top_y + ry))

        for wx, wcol in self.window_positions:
            if wx < 74 or wx > 166:
                for row in range(1, 18, 3):
                    wave = math.sin(elapsed * 2.4 + row * 0.65 + wx * 0.25)
                    if wave > 0.05:
                        sx = wx + int(round(wave * 1.4))
                        fade = 1.0 - row / 20.0
                        col = lerp_color(Palette.RIVER_MID, wcol, 0.35 * fade)
                        if 0 <= sx < self.width - 1:
                            target.set_at((sx, self.top_y + row), col)

        for i, lx in enumerate(self.lamp_xs):
            for row in range(1, 24, 2):
                wave = math.sin(elapsed * 3.1 + row * 0.55 + i * 1.3)
                sx = lx + int(round(wave * (0.8 + row * 0.08)))
                fade = 1.0 - row / 26.0
                col = lerp_color(Palette.RIVER_MID, Palette.LAMP_WARM, 0.72 * fade)
                span = 1 if row < 10 else 2
                if wave > -0.45:
                    pygame.draw.line(
                        target, col, (sx - span, self.top_y + row), (sx + span, self.top_y + row)
                    )

        cx = self.tower.cx
        max_ref_rows = self.height - 2
        for row in range(1, max_ref_rows):
            frac = row / max_ref_rows
            src_y = int(self.tower.base_y - frac * (self.tower.base_y - self.tower.tip_y))
            hw = self.tower.half_width_at(src_y) * (0.95 - 0.18 * frac)

            shimmer = (
                math.sin(elapsed * 2.8 + row * 0.45) * (1.2 + frac * 2.6)
                + math.sin(elapsed * 4.9 - row * 0.85) * 0.8
            )
            center = cx + int(round(shimmer))
            y = self.top_y + row

            band_wave = math.sin(elapsed * 3.4 - row * 0.75)
            if row % 2 == 0 and band_wave < -0.55:
                continue

            fade = (1.0 - frac * 0.62) * (0.82 + 0.18 * math.sin(elapsed * 2.1 + row * 0.3))
            outer_col = lerp_color(Palette.RIVER_MID, Palette.TOWER_GOLD_DARK, fade)
            mid_col = lerp_color(Palette.RIVER_MID, Palette.TOWER_GOLD_MID, fade)
            core_col = lerp_color(Palette.RIVER_MID, Palette.TOWER_GOLD_BRIGHT, fade)

            span = max(1, int(round(hw)))
            pygame.draw.line(target, outer_col, (center - span, y), (center + span, y))

            inner_span = max(1, int(span * 0.62))
            pygame.draw.line(target, mid_col, (center - inner_span, y), (center + inner_span, y))

            near_deck = abs(src_y - self.tower.deck1_y) < 3 or abs(src_y - self.tower.deck2_y) < 3
            if near_deck or band_wave > 0.35:
                core_span = max(1, int(span * (0.75 if near_deck else 0.35)))
                pygame.draw.line(target, core_col, (center - core_span, y), (center + core_span, y))

            glint = math.sin(elapsed * 7.5 + row * 1.9)
            if glint > 0.92:
                gx = center + int(math.sin(row * 3.1) * max(1, inner_span))
                if 0 <= gx < self.width:
                    target.set_at((gx, y), Palette.TOWER_LIGHT)


# ---------------------------------------------------------------------------
# 7. Slowly Moving Parisian River Boats (Bateaux Mouches)
# ---------------------------------------------------------------------------

class RiverBoat:
    """Small pixel-art Parisian river boat gliding gently across the Seine."""

    def __init__(
        self,
        x: float,
        y: int,
        length: int,
        speed: float,
        direction: int,
    ) -> None:
        self.x = x
        self.y = y
        self.length = length
        self.speed = speed
        self.direction = direction
        self.bob_phase = random.uniform(0.0, math.tau)
        self.lamp_glow = create_pixel_glow(5, Palette.BOAT_WINDOW, max_alpha=42, rings=3)

    def update(self, dt: float, world_width: int) -> None:
        self.x += self.speed * self.direction * dt
        margin = self.length + 18
        if self.direction > 0 and self.x > world_width + margin:
            self.x = -margin
        elif self.direction < 0 and self.x < -margin:
            self.x = world_width + margin

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        bx = int(round(self.x))
        bob = 1 if math.sin(elapsed * 2.2 + self.bob_phase) > 0.65 else 0
        by = self.y + bob
        L = self.length

        stern_x = bx - 2 if self.direction > 0 else bx + L + 1
        for i in range(1, 9, 2):
            wx = stern_x - self.direction * i
            wy = by + 2 + (1 if (i + int(elapsed * 4)) % 4 == 0 else 0)
            if 0 <= wx < BASE_WIDTH and RIVER_TOP_Y <= wy < BASE_HEIGHT:
                target.set_at((wx, wy), Palette.BOAT_WAKE)

        for r in range(1, 6):
            ry = by + 2 + r
            if ry >= BASE_HEIGHT:
                continue
            shift = int(round(math.sin(elapsed * 4.0 + r * 0.9) * 1.0))
            fade = 1.0 - r / 6.5
            rcol = lerp_color(Palette.RIVER_MID, Palette.BOAT_WINDOW, 0.55 * fade)
            pygame.draw.line(
                target,
                rcol,
                (bx + 3 + shift, ry),
                (bx + L - 4 + shift, ry),
            )

        pygame.draw.rect(target, Palette.BOAT_HULL_DARK, (bx + 1, by, L - 2, 2))
        pygame.draw.line(target, Palette.BOAT_HULL_TRIM, (bx, by), (bx + L - 1, by))

        cabin_x = bx + 3
        cabin_w = max(6, L - 6)
        pygame.draw.rect(target, Palette.BOAT_CABIN, (cabin_x, by - 3, cabin_w, 3))
        pygame.draw.line(
            target, Palette.BOAT_HULL_TRIM, (cabin_x + 1, by - 3), (cabin_x + cabin_w - 2, by - 3)
        )

        for wx in range(cabin_x + 1, cabin_x + cabin_w - 1, 2):
            target.set_at((wx, by - 2), Palette.BOAT_WINDOW)
            target.set_at((wx, by - 1), Palette.LAMP_WARM)

        target.blit(
            self.lamp_glow,
            (
                bx + L // 2 - self.lamp_glow.get_width() // 2,
                by - 2 - self.lamp_glow.get_height() // 2,
            ),
        )

        bow_x = bx + L - 1 if self.direction > 0 else bx
        back_x = bx if self.direction > 0 else bx + L - 1
        target.set_at((bow_x, by - 1), Palette.BOAT_GREEN if self.direction > 0 else Palette.BOAT_RED)
        target.set_at((back_x, by - 1), Palette.BOAT_WINDOW)


class BoatManager:
    """Manages multiple Parisian boats moving slowly across the Seine."""

    def __init__(self) -> None:
        self.boats: List[RiverBoat] = [
            RiverBoat(x=34.0, y=121, length=14, speed=4.2, direction=1),
            RiverBoat(x=176.0, y=134, length=18, speed=5.6, direction=-1),
            RiverBoat(x=82.0, y=148, length=22, speed=7.2, direction=1),
        ]

    def update(self, dt: float) -> None:
        for boat in self.boats:
            boat.update(dt, BASE_WIDTH)

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        for boat in self.boats:
            boat.draw(target, elapsed)


# ---------------------------------------------------------------------------
# 8. Multi-Layer Continuous Snowfall
# ---------------------------------------------------------------------------

@dataclass
class Snowflake:
    x: float
    y: float
    speed_y: float
    drift_x: float
    sway_amp: float
    sway_freq: float
    phase: float
    layer: int


class SnowSystem:
    """Continuous multi-depth pixel snowfall with wind sway and warm tower tint."""

    def __init__(self, width: int, height: int, count: int = 96, seed: int = 314) -> None:
        self.width = width
        self.height = height
        rng = random.Random(seed)
        self.flakes: List[Snowflake] = []

        for _ in range(count):
            layer = rng.choices([0, 1, 2], weights=[48, 36, 16])[0]
            if layer == 0:
                speed_y = rng.uniform(7.0, 12.0)
                drift_x = rng.uniform(-3.0, -1.0)
                sway_amp = rng.uniform(1.5, 3.0)
            elif layer == 1:
                speed_y = rng.uniform(13.0, 20.0)
                drift_x = rng.uniform(-5.0, -2.0)
                sway_amp = rng.uniform(2.5, 5.0)
            else:
                speed_y = rng.uniform(21.0, 30.0)
                drift_x = rng.uniform(-7.0, -3.5)
                sway_amp = rng.uniform(3.5, 6.5)

            self.flakes.append(
                Snowflake(
                    x=rng.uniform(0, width),
                    y=rng.uniform(0, height),
                    speed_y=speed_y,
                    drift_x=drift_x,
                    sway_amp=sway_amp,
                    sway_freq=rng.uniform(1.0, 2.4),
                    phase=rng.uniform(0.0, math.tau),
                    layer=layer,
                )
            )

    def update(self, dt: float) -> None:
        for f in self.flakes:
            f.y += f.speed_y * dt
            f.x += f.drift_x * dt
            if f.y >= self.height:
                f.y -= self.height
            if f.x < 0:
                f.x += self.width
            elif f.x >= self.width:
                f.x -= self.width

    def draw(self, target: pygame.Surface, elapsed: float) -> None:
        for f in self.flakes:
            sx = int(round(f.x + math.sin(elapsed * f.sway_freq + f.phase) * f.sway_amp)) % self.width
            sy = int(round(f.y))
            if not (0 <= sy < self.height):
                continue

            near_tower = abs(sx - TOWER_CENTER_X) < 28 and 18 <= sy <= 106
            if f.layer == 0:
                col = Palette.SNOW_FAR
            elif f.layer == 1:
                col = Palette.SNOW_WARM if near_tower else Palette.SNOW_MID
            else:
                col = Palette.SNOW_WARM if near_tower else Palette.SNOW_NEAR

            target.set_at((sx, sy), col)
            if f.layer == 2 and sy + 1 < self.height and sx + 1 < self.width:
                if (int(f.phase * 10) % 3) == 0:
                    target.set_at((sx + 1, sy), Palette.SNOW_MID)


# ---------------------------------------------------------------------------
# 9. Main Application Controller
# ---------------------------------------------------------------------------

class ParisNightApp:
    """Main Pygame application with nearest-neighbor upscaling and fullscreen."""

    def __init__(self, fullscreen: bool = False, target_fps: int = DEFAULT_FPS) -> None:
        pygame.init()
        pygame.display.set_caption("Paris - Eiffel Tower Pixel Art Night")

        self.target_fps = max(30, min(60, target_fps))
        self.fullscreen = fullscreen
        self.paused = False
        self.show_hud = False
        self.running = True
        self.elapsed = 0.0

        self.windowed_size = (BASE_WIDTH * DEFAULT_SCALE, BASE_HEIGHT * DEFAULT_SCALE)
        self.screen = self._create_display(fullscreen=self.fullscreen)

        self.canvas = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 14)

        self.sky = NightSky(BASE_WIDTH, HORIZON_Y)
        self.stars = StarField(BASE_WIDTH, HORIZON_Y - 12, count=74)
        self.clouds = CloudLayer(BASE_WIDTH)
        self.cityscape = Cityscape(BASE_WIDTH, HORIZON_Y)
        self.tower = EiffelTower(TOWER_CENTER_X, HORIZON_Y)
        self.river = SeineRiver(
            width=BASE_WIDTH,
            top_y=RIVER_TOP_Y,
            height=BASE_HEIGHT - RIVER_TOP_Y,
            tower=self.tower,
            lamp_xs=self.cityscape.lamp_xs,
            window_positions=self.cityscape.get_glowing_window_positions(),
        )
        self.boats = BoatManager()
        self.snow = SnowSystem(BASE_WIDTH, BASE_HEIGHT, count=96)

    def _create_display(self, fullscreen: bool) -> pygame.Surface:
        if fullscreen:
            info = pygame.display.Info()
            return pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        return pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.screen = self._create_display(fullscreen=self.fullscreen)

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    self.running = False
                elif event.key in (pygame.K_f, pygame.K_F11):
                    self.toggle_fullscreen()
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_h:
                    self.show_hud = not self.show_hud
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.windowed_size = (max(BASE_WIDTH, event.w), max(BASE_HEIGHT, event.h))
                self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def update(self, dt: float) -> None:
        if self.paused:
            return
        self.elapsed += dt
        self.clouds.update(dt)
        self.boats.update(dt)
        self.snow.update(dt)

    def render_scene(self) -> None:
        """Render the complete low-resolution pixel art scene onto self.canvas."""
        self.sky.draw(self.canvas, self.elapsed)
        self.stars.draw(self.canvas, self.elapsed)
        self.clouds.draw_far(self.canvas)
        self.clouds.draw_near(self.canvas)
        self.cityscape.draw_background(self.canvas, self.elapsed)
        self.tower.draw(self.canvas, self.elapsed)
        self.cityscape.draw_quay_and_lamps(self.canvas, self.elapsed)
        self.river.draw(self.canvas, self.elapsed)
        self.boats.draw(self.canvas, self.elapsed)
        self.snow.draw(self.canvas, self.elapsed)

    def present(self) -> None:
        """Upscale the low-res canvas using nearest-neighbor interpolation."""
        screen_w, screen_h = self.screen.get_size()
        scale = min(screen_w / BASE_WIDTH, screen_h / BASE_HEIGHT)
        int_scale = int(scale)
        if int_scale >= 1 and not self.fullscreen:
            target_w = BASE_WIDTH * int_scale
            target_h = BASE_HEIGHT * int_scale
        else:
            target_w = max(BASE_WIDTH, int(round(BASE_WIDTH * scale)))
            target_h = max(BASE_HEIGHT, int(round(BASE_HEIGHT * scale)))

        # pygame.transform.scale performs nearest-neighbor interpolation (sharp pixels)
        upscaled = pygame.transform.scale(self.canvas, (target_w, target_h))
        self.screen.fill((6, 7, 16))
        offset_x = (screen_w - target_w) // 2
        offset_y = (screen_h - target_h) // 2
        self.screen.blit(upscaled, (offset_x, offset_y))

        if self.show_hud:
            fps = self.clock.get_fps()
            status = "paused" if self.paused else "running"
            hud_text = (
                f"paris_eiffel_night.py  |  {status}  |  {fps:4.1f} fps  |  "
                f"F: fullscreen  SPACE: pause  H: hud  ESC: quit"
            )
            label = self.font.render(hud_text, True, (220, 212, 195))
            bar = pygame.Surface((screen_w, 24), pygame.SRCALPHA)
            bar.fill((10, 10, 22, 185))
            self.screen.blit(bar, (0, screen_h - 24))
            self.screen.blit(label, (10, screen_h - 20))

        pygame.display.flip()

    def cleanup_and_exit(self) -> None:
        """Cleanly shut down Pygame and exit the process."""
        pygame.quit()
        sys.exit(0)

    def run(self) -> None:
        """Execute the main delta-time animation loop."""
        try:
            while self.running:
                # Clamp delta time to prevent jumps if the window is dragged on Windows
                dt = min(self.clock.tick(self.target_fps) / 1000.0, 0.05)
                self.handle_events()
                self.update(dt)
                self.render_scene()
                self.present()
        finally:
            self.cleanup_and_exit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Paris - Eiffel Tower Pixel Art Night (Pygame animation)"
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Start the animation directly in fullscreen mode.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help="Target frame rate between 30 and 60 FPS (default: 60).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = ParisNightApp(fullscreen=args.fullscreen, target_fps=args.fps)
    app.run()


if __name__ == "__main__":
    main()