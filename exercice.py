#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import struct
import math
from collections import namedtuple


SAMPLING_FREQ = 44100  # Hertz, taux d'échantillonnage standard des CD
SAMPLE_BITS = 16
SAMPLE_WIDTH = SAMPLE_BITS // 8
MAX_SAMPLE_VALUE = 2 ** (SAMPLE_BITS - 1) - 1

# Les formats d'encodage (struct) pour les sous-entêtes.
RIFF_HEADER_STRUCT = "4sI 4s"
FORMAT_HEADER_STRUCT = "4sI HHIIHH"
DATA_HEADER_STRUCT = "4sI"
# Le format d'encodage pour les entêtes.
WAVE_FILE_HEADERS_STRUCT = (
    "<" + RIFF_HEADER_STRUCT + FORMAT_HEADER_STRUCT + DATA_HEADER_STRUCT
)


# Contient tous les champs des entêtes d'un fichier WAVE.
WaveFileHeaders = namedtuple(
    "WaveFileHeaders",
    """
    riff_id,
    file_size,
    wave,
    fmt_id,
    fmt_size,
    wav_type,
    num_channels,
    sampling_freq,
    bytes_per_second,
    bytes_per_sample,
    sample_bits,
    data_id,
    data_size
    """,
)


def merge_channels(channels):
    final_list = []
    for values in zip(*channels):
        final_list += values

    return final_list


def separate_channels(samples, num_channels):
    final_list = [[] for _ in range(num_channels)]
    for i in range(len(samples) // num_channels):
        for j in range(num_channels):
            final_list[j].append(samples[num_channels * i + j])

    return final_list


def sine_gen(freq, amplitude, duration_seconds):
    # Générer une onde sinusoïdale à partir de la fréquence et de l'amplitude donnée, sur le temps
    # demandé et considérant le taux d'échantillonnage.
    # Les échantillons sont des nombres réels entre -1 et 1.
    # Formule de la valeur y d'une onde sinusoïdale à l'angle x en fonction de sa fréquence F et de son amplitude A :
    # y = A * sin(F * x), où x est en radian.
    # Si on veut le x qui correspond au moment t, on peut dire que 2π représente une seconde, donc x = t * 2π.
    # Or t est en secondes, donc t = i / nb_échantillons_par_secondes, où i est le numéro d'échantillon.
    for i in range(int(SAMPLING_FREQ * duration_seconds)):
        yield amplitude * math.sin(freq * (i / SAMPLING_FREQ) * 2 * math.pi)


def create_headers(num_samples):
    data_size = num_samples * SAMPLE_WIDTH
    riff_file_size = struct.calcsize(WAVE_FILE_HEADERS_STRUCT) - 8 + data_size

    return WaveFileHeaders(
        riff_id=b"RIFF",
        file_size=riff_file_size,
        wave=b"WAVE",
        fmt_id=b"fmt ",
        fmt_size=struct.calcsize(FORMAT_HEADER_STRUCT) - 8,
        wav_type=1,
        num_channels=2,
        sampling_freq=SAMPLING_FREQ,
        bytes_per_second=SAMPLING_FREQ * SAMPLE_WIDTH,
        bytes_per_sample=SAMPLE_WIDTH,
        sample_bits=SAMPLE_BITS,
        data_id=b"data",
        data_size=data_size,
    )


def convert_to_bytes(samples):
    # Convertir les échantillons en tableau de bytes en les convertissant en entiers 16 bits.
    # Les échantillons en entrée sont entre -1 et 1, nous voulons les mettre entre -MAX_SAMPLE_VALUE et MAX_SAMPLE_VALUE
    int_samples = [int(sample * MAX_SAMPLE_VALUE) for sample in samples]
    sample_struct = struct.Struct(f"<{len(samples)}h")
    return sample_struct.pack(*int_samples)


def write_wave_file(filename, samples):
    # Créer les entêtes à encoder à l'aide de create_headers, les encoder en octets avec le format
    # d'encodage donné dans la constante WAVE_FILE_HEADERS_STRUCT.
    headers_struct = struct.Struct(WAVE_FILE_HEADERS_STRUCT)
    headers = create_headers(len(samples))
    headers_bytes = headers_struct.pack(*headers)
    # Convertir les échantillons en octets avec la fonction convert_to_bytes.
    data_bytes = convert_to_bytes(samples)
    # Ouvrir le fichier donné en écriture binaire et écrire les octets d'entêtes suivis les octets de données.
    with open(filename, "wb") as out_file:
        out_file.write(headers_bytes)
        out_file.write(data_bytes)


def convert_to_samples(sample_bytes):
    return [float(value) / MAX_SAMPLE_VALUE for value in sample_bytes]


def read_wave_file(filename):
    with open(filename, "rb") as in_file:
        header_data = in_file.read(struct.calcsize(WAVE_FILE_HEADERS_STRUCT))
        headers_struct = struct.Struct(WAVE_FILE_HEADERS_STRUCT)
        header_data = WaveFileHeaders(*headers_struct.unpack(header_data))

        sample_count = header_data.data_size // 2
        data_unpacker = struct.Struct(f"<{sample_count}h")
        raw_bytes = in_file.read(sample_count * 2)
        sample_bytes = list(data_unpacker.unpack(raw_bytes))
        return header_data, convert_to_samples(sample_bytes)
    # Lire les octets des entêtes.
    # Ouvrir le fichier en mode lecture binaire.
    # Décoder les entêtes en octets avec le format d'encodage donné dans la constante WAVE_FILE_HEADERS_STRUCT.
    # Lire les octets de données à partir de la fin des entête. Le nombre d'octets à lire est donné par data_size des entêtes.
    # Décoder les octets de données en échantillons réel avec la fonction convert_to_samples en se positionnant au début des données (après les octets).
    # Retourner les entêtes décodés (sous la forme d'un WaveFileHeaders) et la liste d'échantillons réel en deux valeurs.


def main():
    if not os.path.exists("output"):
        os.mkdir("output")

    # Si on veut juste tester l'encodage des échantillons, on peut appeler convert_to_bytes avec quelques échantillons, écrire les octets directement dans un fichier binaire sans entête et les importer comme «Raw data» dans Audacity.
    with open("output/test.bin", "wb") as out_file:
        data = convert_to_bytes([0.8, -0.8, 0.5, -0.5, 0.2, -0.2])
        out_file.write(data)

    # Exemple simple avec quelques échantillons pour tester le fonctionnement de l'écriture.
    write_wave_file("output/test.wav", [0.8, -0.8, 0.5, -0.5, 0.2, -0.2])

    # On génére un la3 (220 Hz), un do#4, un mi4 et un la4 (intonnation juste).
    sine_a3 = sine_gen(220, 0.5, 5.0)
    sine_cs4 = sine_gen(220 * (5 / 4), 0.4, 5.0)
    sine_e4 = sine_gen(220 * (3 / 2), 0.35, 5.0)
    sine_a4 = sine_gen(220 * 2, 0.3, 5.0)

    # On met les samples dans des channels séparés (la et do# à gauche, mi et la à droite)
    merged = merge_channels(
        [
            (sum(elems) for elems in zip(sine_a3, sine_cs4)),
            (sum(elems) for elems in zip(sine_e4, sine_a4)),
        ]
    )
    write_wave_file("output/major_chord.wav", merged)

    _, samples = read_wave_file("data/kinship_maj.wav")
    # On réduit le volume (on pourrait faire n'importe quoi avec les samples à ce stade)
    samples = [s * 0.2 for s in samples]
    write_wave_file("output/kinship_mod.wav", samples)


if __name__ == "__main__":
    main()
