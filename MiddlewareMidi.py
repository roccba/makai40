"""
Middleware para expandir la rejilla de pads de una APC40 MK2 a múltiples
layers de CCs con una salida MIDI virtual.

Mejoras aportadas:
- CLI con parámetros para elegir keywords de búsqueda de puertos y layer inicial.
- Estructura en funciones para facilitar pruebas y lectura.
- Mensajes de logging más claros y con fallback seguro si no se encuentran puertos.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

import mido

from apc_middleware import (
    APC_COLORS,
    BANK_DOWN_NOTE,
    BANK_UP_NOTE,
    GRID_NOTES,
    NUM_LAYERS,
    create_layer_states,
    note_layer_to_cc_channel,
    open_ports,
    print_ports,
    refresh_layer_leds,
    set_layer_led,
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Middleware APC40 MK2 → MIDI virtual. Usa keywords para seleccionar "
            "puertos automáticamente."
        )
    )
    parser.add_argument(
        "--apc-keywords",
        nargs="+",
        default=("apc", "akai"),
        help="Keywords para localizar la APC40 en entrada y salida.",
    )
    parser.add_argument(
        "--midi-out-keywords",
        nargs="+",
        default=("apc_mw_out",),
        help="Keywords para localizar la salida MIDI virtual hacia el software.",
    )
    parser.add_argument(
        "--start-layer",
        type=int,
        default=0,
        choices=range(NUM_LAYERS),
        metavar=f"0-{NUM_LAYERS - 1}",
        help="Layer inicial al iniciar el middleware.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Solo listar puertos disponibles y salir (sin abrir puertos).",
    )
    return parser.parse_args(argv)


def run_event_loop(
    inport: mido.ports.BaseInput,
    out_to_soft: mido.ports.BaseOutput,
    out_to_apc: mido.ports.BaseOutput,
    current_layer: int,
    layer_states: list[list[int]],
) -> None:
    """Bucle principal que procesa eventos y actualiza LEDs."""

    print("✔ Middleware activo: APC40 ⇄ Middleware ⇄ Software")
    print("----------------------------------------------------")

    try:
        for msg in inport:
            print("APC →", msg)

            # DETECCIÓN DE CAMBIO DE LAYER
            if msg.type == "note_on" and msg.velocity == 127:
                if msg.note == BANK_UP_NOTE:
                    prev = current_layer
                    current_layer = max(0, current_layer - 1)
                    if current_layer != prev:
                        print(f"⬆ LAYER UP → {current_layer}")
                        refresh_layer_leds(layer_states, current_layer, out_to_apc)
                    continue

                if msg.note == BANK_DOWN_NOTE:
                    prev = current_layer
                    current_layer = min(len(layer_states) - 1, current_layer + 1)
                    if current_layer != prev:
                        print(f"⬇ LAYER DOWN → {current_layer}")
                        refresh_layer_leds(layer_states, current_layer, out_to_apc)
                    continue

            # DEMO: TOGGLE DE LED POR PAD EN EL LAYER ACTUAL
            if (
                msg.type == "note_on"
                and msg.velocity > 0
                and getattr(msg, "note", None) in GRID_NOTES
            ):
                current_val = layer_states[current_layer][msg.note]
                new_val = (
                    APC_COLORS["green"]
                    if current_val == APC_COLORS["off"]
                    else APC_COLORS["off"]
                )
                set_layer_led(
                    layer_states, current_layer, out_to_apc, current_layer, msg.note, new_val
                )

            # CONVERSIÓN NOTE → CC EXPANDIDO
            new_msg = msg
            if msg.type in ("note_on", "note_off") and getattr(msg, "note", None) in GRID_NOTES:
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

            try:
                out_to_soft.send(new_msg)
            except Exception as exc:  # noqa: BLE001
                print("Error al enviar mensaje hacia la salida virtual:", exc)

    except KeyboardInterrupt:
        print("Interrumpido por el usuario.")
    except Exception as exc:  # noqa: BLE001
        print("Error en el loop principal:", exc)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print("Python ejecutándose desde:", sys.executable)

    input_names = mido.get_input_names()
    output_names = mido.get_output_names()
    print_ports(input_names, output_names)

    if args.list_only:
        return 0

    try:
        apc_name_in, midi_out_name, apc_name_out = open_ports(
            args.apc_keywords, args.midi_out_keywords
        )
    except Exception as exc:  # noqa: BLE001
        print("Error al resolver puertos MIDI:", exc)
        return 1

    try:
        inport = mido.open_input(apc_name_in)
        out_to_soft = mido.open_output(midi_out_name)
        out_to_apc = mido.open_output(apc_name_out)
    except Exception as exc:  # noqa: BLE001
        print("Error al abrir puertos MIDI:", exc)
        return 1

    current_layer = args.start_layer
    print(f"Layer inicial: {current_layer}")
    layer_states = create_layer_states()
    refresh_layer_leds(layer_states, current_layer, out_to_apc)

    try:
        run_event_loop(inport, out_to_soft, out_to_apc, current_layer, layer_states)
    finally:
        try:
            inport.close()
            out_to_soft.close()
            out_to_apc.close()
        except Exception:  # noqa: BLE001
            pass
        print("Puertos cerrados. Saliendo.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
