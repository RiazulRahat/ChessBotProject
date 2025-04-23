import pygame

def scale_and_resize(image, target):
    tw, th = target
    ow, oh = image.get_size()
    scale = max(tw / (2.5 * ow), th / (2.5 * oh))
    nw, nh = int(ow * scale), int(oh * scale)
    return pygame.transform.smoothscale(image, (nw, nh))
