"""This script exists since it seems like the push to hub does not work from the training script"""

from diffusers import ControlNetModel

model = ControlNetModel.from_pretrained("/scratch/stariq/models/sd-controlnet-signwriting")

model.push_to_hub("sarahahtee/signwriting-illustration")
