"""

compare speed of blitting tile subsurfaces to plain surfaces

on my system:
 fedora linux 33
 ryzen 3 3800x
 pygame 2.0.0
 python 3.9
subsurface blits are about 72-82% the speed of plain surface blits

"""

import pygame
import time

pygame.init()

screen = pygame.display.set_mode((640, 480))

image0 = pygame.image.load("data/acid3.png")
image0 = image0.convert()

image1 = pygame.image.load("data/acid0.png")
image1 = image1.convert()

image2 = image1.subsurface((16, 16, 16, 16))

buffer = pygame.Surface((128, 128))

times = list()
time.sleep(1)
for i in range(1000):
    [i for i in pygame.event.get()]
    start = time.time_ns()
    for i in range(10000):
        buffer.blit(image0, (0, 0))
    duration = (time.time_ns() - start) / 1000
    times.append(duration)
surface_timing = sum(times) / len(times)
print("plain surf", surface_timing)

times = list()
time.sleep(1)
for i in range(1000):
    [i for i in pygame.event.get()]
    start = time.time_ns()
    for i in range(10000):
        buffer.blit(image2, (0, 0))
    duration = (time.time_ns() - start) / 1000
    times.append(duration)
subsurface_timing = sum(times) / len(times)
print("sub surf  ", subsurface_timing)

print(min((surface_timing, subsurface_timing)) / max(surface_timing, subsurface_timing))
