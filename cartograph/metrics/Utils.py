def color_from_code(color_code):
    """Convert an iterable of color components out of 255, and convert them to fractions of 1.0 (i.e. divide each
    component by 255.0)
    :return: a tuple where each element represents a color component as a float between 0.0 and 1.0
    """
    return tuple([float(component) / 255.0 for component in color_code])