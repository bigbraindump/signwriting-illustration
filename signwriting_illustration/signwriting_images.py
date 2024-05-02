from pathlib import Path
from typing import Union

from PIL import Image
from signwriting.visualizer.visualize import signwriting_to_image


def signwriting_to_sized_image(fsw: str, output: Union[str, Path], size=512):
    output_im = signwriting_to_image(fsw)

    initial_size = size // 2
    if output_im.width > initial_size or output_im.height > initial_size:
        raise Exception(f"{fsw} is too large (> {initial_size})")

    # Create a 512x512 RGB image with a white background
    img = Image.new('RGB', (initial_size, initial_size), (255, 255, 255))

    # Calculate the position to paste the image so that it's centered
    x_offset = (initial_size - output_im.width) // 2
    y_offset = (initial_size - output_im.height) // 2
    offset = (x_offset, y_offset)

    # Paste the output_im image onto the white background
    img.paste(output_im, offset, output_im)

    # Upscale the image to 512x512
    img = img.resize((size, size), Image.NEAREST)

    img.save(output)
    return img


if __name__ == "__main__":
    FSW = 'AS10020S10028S22b04S22b00S22b04S22b10S22b14S22b10S2fb00' + \
          'M561x534S10028472x500S10020516x469S22b00530x502S22b04515x504' + \
          'S22b04545x504S22b14456x467S22b10472x467S22b10440x467S2fb00493x480'
    signwriting_to_sized_image(FSW, 'test.png')
