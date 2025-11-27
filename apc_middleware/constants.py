"""Constantes y configuraciones comunes para el middleware APC40."""

NUM_LAYERS = 16  # hasta 16 bancos
NUM_PADS = 40  # 8x5 pads
GRID_NOTES = list(range(NUM_PADS))

# Notas de las flechas (navegación de layer)
BANK_UP_NOTE = 94  # Flecha izquierda (layer -1)
BANK_DOWN_NOTE = 95  # Flecha derecha (layer +1)

APC_COLORS = {
    "off": 0,
    # VERDE
    "green": 21,
    "green_blink": 22,
    # ROJO
    "red": 5,
    "red_blink": 6,
    # ÁMBAR
    "amber": 9,
    "amber_blink": 10,
}
