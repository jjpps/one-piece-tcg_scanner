from dataclasses import dataclass

@dataclass
class LocalCard:
    local_imagem:str
    card_image:str
    card_name:str
    card_set_id:str
    exists:bool
    cropped_imagem:str = ""
