"""Funciones de layers y mapeo de notas a CCs."""

from __future__ import annotations

from typing import Sequence

import mido

from .constants import APC_COLORS, GRID_NOTES, NUM_LAYERS, NUM_PADS


def note_layer_to_cc_channel(note: int, layer: int) -> tuple[int, int]:
    """Convierte note+layer a un pair (control 0..127, channel 0..15)."""

    base_cc = note + layer * NUM_PADS
    control = base_cc % 128
    channel = (base_cc // 128) % 16
    return control, channel


def set_pad_raw(out_port: mido.ports.BaseOutput, note: int, velocity: int) -> None:
    """Envía un note_on directo a la APC en channel 0."""

    msg = mido.Message("note_on", channel=0, note=note, velocity=velocity)
    out_port.send(msg)


def set_layer_led(
    layer_states: list[list[int]],
    current_layer: int,
    out_port: mido.ports.BaseOutput,
    layer: int,
    note: int,
    velocity: int,
) -> None:
    """Actualiza el estado guardado y refresca el LED si aplica."""

    if layer < 0 or layer >= NUM_LAYERS:
        return
    if note < 0 or note >= NUM_PADS:
        return
    layer_states[layer][note] = velocity
    if layer == current_layer:
        set_pad_raw(out_port, note, velocity)


def refresh_layer_leds(
    layer_states: Sequence[Sequence[int]],
    current_layer: int,
    out_port: mido.ports.BaseOutput,
) -> None:
    """Redibuja todos los pads según el layer actual y su estado guardado."""

    for note in GRID_NOTES:
        velocity = layer_states[current_layer][note]
        set_pad_raw(out_port, note, velocity)


def create_layer_states() -> list[list[int]]:
    """Genera la matriz de estados por layer y pad, con layer 1 en verde por defecto."""

    layer_states = [
        [APC_COLORS["off"] for _ in range(NUM_PADS)]
        for _ in range(NUM_LAYERS)
    ]
    for note in GRID_NOTES:
        layer_states[1][note] = APC_COLORS["green"]
    return layer_states
