import mido
import sys

# ==================================================
#  MIDDLEWARE APC40 MK2 → MIDI OUT VIRTUAL
#  - 16 LAYERS (BANKS)
#  - NOTE ON/OFF de la grilla 8x5 → CC expandidos
#  - Control de LEDs por layer con memoria de estado
# ==================================================

# FIXED NEWLINES AND STRING LITERALS
print("=== Puertos MIDI disponibles (IN) ===")
print("Python ejecutándose desde:", sys.executable)

# ==================================================
#  TABLA DE COLORES APC40 MK2
# ==================================================

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

# ==================================================
#  CONSTANTES DE LAYOUT
# ==================================================

NUM_LAYERS = 16          # hasta 16 bancos
NUM_PADS = 40            # 8x5 pads
GRID_NOTES = list(range(NUM_PADS))

# ==================================================
#  SELECCIÓN DE PUERTOS
# ==================================================

# Obtener nombres una sola vez
input_names = mido.get_input_names()
output_names = mido.get_output_names()

print("=== Puertos MIDI disponibles (IN) ===")
for port in input_names:
    print(" -", port)

print("=== Puertos MIDI disponibles (OUT) ===")
for port in output_names:
    print(" -", port)

# Utilidades pequeñas para búsqueda case-insensitive
def _find_input_by_keywords(keywords):
    return next((n for n in input_names if any(k in n.lower() for k in keywords)), None)

def _find_output_by_keywords(keywords):
    return next((n for n in output_names if any(k in n.lower() for k in keywords)), None)

# Entrada desde la APC40 MK2
apc_name_in = _find_input_by_keywords(("apc", "akai"))

# Salida MIDI virtual (loopMIDI u otra) hacia el software
midi_out_name = _find_output_by_keywords(("apc_mw_out",))

# Salida de vuelta a la APC para controlar LEDs
apc_name_out = _find_output_by_keywords(("apc", "akai"))

# Verificar que se encontraron puertos
if not apc_name_in:
    print("Error: no se encontró puerto de entrada APC (APC/Akai).")
    sys.exit(1)

if not midi_out_name:
    print("Error: no se encontró la salida virtual 'APC_MW_OUT'.")
    print("Lista de salidas disponibles:", output_names)
    sys.exit(1)

if not apc_name_out:
    print("Error: no se encontró puerto de salida APC para LEDs (APC/Akai).")
    sys.exit(1)

print(f"✔ Leyendo de APC: {apc_name_in}")
print(f"✔ Enviando a salida MIDI virtual: {midi_out_name}")
print(f"✔ Controlando LEDs en salida APC: {apc_name_out}")

# Apertura de puertos (catch para informar error al abrir)
try:
    inport = mido.open_input(apc_name_in)
    out_to_soft = mido.open_output(midi_out_name)
    out_to_apc = mido.open_output(apc_name_out)
except Exception as e:
    print("Error al abrir puertos MIDI:", e)
    sys.exit(1)

print("✔ Middleware activo: APC40 ⇄ Middleware ⇄ Software")
print("----------------------------------------------------")

# ==================================================
#  ESTADO DE LAYERS Y LEDs
# ==================================================

current_layer = 0  # 0..15
print(f"Layer inicial: {current_layer}")

# Estados de LEDs por layer y pad: layer_states[layer][note] = color (velocity)
layer_states = [
    [APC_COLORS["off"] for _ in range(NUM_PADS)]
    for _ in range(NUM_LAYERS)
]

# Ejemplo: layer 1 arrancar en verde
for n in GRID_NOTES:
    layer_states[1][n] = APC_COLORS["green"]

# Notas de las flechas (navegación de layer)
BANK_UP_NOTE = 94    # Flecha izquierda (layer -1)
BANK_DOWN_NOTE = 95  # Flecha derecha (layer +1)

# ==================================================
#  FUNCIONES DE LED / ESTADO
# ==================================================

def set_pad_raw(note: int, velocity: int) -> None:
    """Envía un note_on directo a la APC en channel 0."""
    msg = mido.Message("note_on", channel=0, note=note, velocity=velocity)
    out_to_apc.send(msg)


def set_layer_led(layer: int, note: int, velocity: int) -> None:
    """Actualiza el estado guardado y, si es el layer activo, refresca el LED."""
    if layer < 0 or layer >= NUM_LAYERS:
        return
    if note < 0 or note >= NUM_PADS:
        return
    layer_states[layer][note] = velocity
    if layer == current_layer:
        set_pad_raw(note, velocity)


def refresh_layer_leds() -> None:
    """Redibuja todos los pads según el layer actual y su estado guardado."""
    for note in GRID_NOTES:
        velocity = layer_states[current_layer][note]
        set_pad_raw(note, velocity)


# Helper: map note+layer → (control, channel)
def note_layer_to_cc_channel(note: int, layer: int) -> tuple[int, int]:
    """
    Convierte note+layer a un pair (control 0..127, channel 0..15).
    Esto permite "expandir" CCs usando múltiples canales si base_cc > 127.
    """
    base_cc = note + layer * NUM_PADS
    control = base_cc % 128
    channel = (base_cc // 128) % 16
    return control, channel


# Primer refresh visual
refresh_layer_leds()

# ==================================================
#  LOOP PRINCIPAL
# ==================================================

try:
    for msg in inport:
        # Mensaje entrante
        print("APC →", msg)

        # ------------------------------
        #  DETECCIÓN DE CAMBIO DE LAYER
        # ------------------------------
        if msg.type == "note_on" and msg.velocity == 127:
            if msg.note == BANK_UP_NOTE:
                prev = current_layer
                current_layer = max(0, current_layer - 1)
                if current_layer != prev:
                    print(f"⬆ LAYER UP → {current_layer}")
                    refresh_layer_leds()
                continue

            if msg.note == BANK_DOWN_NOTE:
                prev = current_layer
                current_layer = min(NUM_LAYERS - 1, current_layer + 1)
                if current_layer != prev:
                    print(f"⬇ LAYER DOWN → {current_layer}")
                    refresh_layer_leds()
                continue

        # -------------------------------------------------
        #  DEMO: TOGGLE DE LED POR PAD EN EL LAYER ACTUAL
        # -------------------------------------------------
        if msg.type == "note_on" and msg.velocity > 0 and getattr(msg, "note", None) in GRID_NOTES:
            # Si el pad está apagado → lo prendemos en verde, si no → lo apagamos
            current_val = layer_states[current_layer][msg.note]
            new_val = APC_COLORS["green"] if current_val == APC_COLORS["off"] else APC_COLORS["off"]
            set_layer_led(current_layer, msg.note, new_val)

        # ------------------------------
        #  CONVERSIÓN NOTE → CC EXPANDIDO
        # ------------------------------
        new_msg = msg

        if msg.type in ("note_on", "note_off") and getattr(msg, "note", None) in GRID_NOTES:
            # Cada layer usa un bloque distinto de CCs:
            # base_cc = nota + layer * NUM_PADS
            cc_value = msg.velocity if msg.type == "note_on" else 0
            control, channel = note_layer_to_cc_channel(msg.note, current_layer)
            new_msg = mido.Message(
                "control_change",
                channel=channel,
                control=control,
                value=cc_value,
            )
            print(
                f" → PAD {msg.note} en LAYER {current_layer} "
                f"→ CC{control} ch{channel} (value {cc_value})"
            )

        # ------------------------------
        #  ENVÍO HACIA EL SOFTWARE
        # ------------------------------
        try:
            out_to_soft.send(new_msg)
        except Exception as e:
            print("Error al enviar mensaje hacia la salida virtual:", e)

except KeyboardInterrupt:
    print("Interrumpido por el usuario.")

except Exception as e:
    print("Error en el loop principal:", e)

finally:
    try:
        inport.close()
        out_to_soft.close()
        out_to_apc.close()
    except Exception:
        pass
    print("Puertos cerrados. Saliendo.")