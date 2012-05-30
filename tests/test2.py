#!/usr/bin/python

import pygame
from pytmx import tmxloader

filename = "map.tmx"

pygame.init()
screen = pygame.display.set_mode((320, 200))

print("Loading TMX map '%s'" % filename)

tmx = tmxloader.load_pygame(filename)

print("properties:", tmx.tile_properties)

pygame.quit()
