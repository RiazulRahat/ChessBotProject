import pygame

# function to scale and resize image
def scale_and_resize(image, t_size):
    """
    Scale the image to cover the target_size while preserving aspect ratio,
    then crop the center to exactly match target_size.
    
    Parameters:
      image (pygame.Surface): The source image.
      t_size (tuple): The (width, height) target dimensions.
    
    Returns:
      pygame.Surface: The scaled and cropped image.
    """

    t_width, t_height = t_size
    o_width, o_height = image.get_size()

    scale_factor = max(t_width / (2.5 * o_width), t_height / (2.5 * o_height))
    n_width = int(o_width * scale_factor)
    n_height = int(o_height * scale_factor)

    scaled_image = pygame.transform.smoothscale(image, (n_width, n_height))

    # crop_x = (n_width - t_width) // 2
    # crop_y = (n_height - t_height) // 2

    # cropped_image = scaled_image.subsurface((crop_x, crop_y, t_width, t_height)).copy()
    return scaled_image