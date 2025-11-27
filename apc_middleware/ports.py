"""Utilidades de descubrimiento y apertura de puertos MIDI."""

from __future__ import annotations

from typing import Iterable, Sequence

import mido


def print_ports(input_names: Sequence[str], output_names: Sequence[str]) -> None:
    """Imprime la lista de puertos disponibles."""

    print("=== Puertos MIDI disponibles (IN) ===")
    for port in input_names:
        print(" -", port)

    print("=== Puertos MIDI disponibles (OUT) ===")
    for port in output_names:
        print(" -", port)


def find_port_by_keywords(port_names: Iterable[str], keywords: Iterable[str]) -> str | None:
    """Retorna el primer puerto que contenga alguno de los *keywords* (case-insensitive)."""

    normalized_keywords = [keyword.lower() for keyword in keywords]
    normalized_ports = {name: name.lower() for name in port_names}
    return next(
        (
            name
            for name, lowered in normalized_ports.items()
            if any(keyword in lowered for keyword in normalized_keywords)
        ),
        None,
    )


def open_ports(apc_keywords: Sequence[str], midi_out_keywords: Sequence[str]) -> tuple[str, str, str]:
    """Devuelve los nombres de puerto para la APC (in/out) y la salida virtual."""

    input_names = mido.get_input_names()
    output_names = mido.get_output_names()
    print_ports(input_names, output_names)

    apc_name_in = find_port_by_keywords(input_names, apc_keywords)
    midi_out_name = find_port_by_keywords(output_names, midi_out_keywords)
    apc_name_out = find_port_by_keywords(output_names, apc_keywords)

    if not apc_name_in:
        raise RuntimeError(
            "No se encontró puerto de entrada APC. Ajusta --apc-keywords o conecta el dispositivo."
        )

    if not midi_out_name:
        raise RuntimeError(
            "No se encontró la salida virtual hacia el software. Usa --midi-out-keywords."
        )

    if not apc_name_out:
        raise RuntimeError("No se encontró puerto de salida APC para LEDs.")

    print(f"✔ Leyendo de APC: {apc_name_in}")
    print(f"✔ Enviando a salida MIDI virtual: {midi_out_name}")
    print(f"✔ Controlando LEDs en salida APC: {apc_name_out}")
    return apc_name_in, midi_out_name, apc_name_out
