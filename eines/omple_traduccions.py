#!/usr/bin/env python3
"""Omple les cadenes que falten al paquet amb traducció automàtica.

Agafa les cadenes en anglès de la instal·lació de VS Code i les tradueix amb
el traductor neuronal de Softcatalà (anglès → català). Si el resultat no conserva
els marcadors ({0}, `codi`, $(icona)...), prova amb el traductor Apertium de
Softcatalà a partir del paquet oficial de Microsoft en castellà. Si tampoc no
funciona, la cadena es queda en anglès.

Les cadenes que ja són al paquet no es toquen mai.

Ús:
    uv run python eines/omple_traduccions.py \\
        --vscode "/Applications/Visual Studio Code.app/Contents/Resources/app" \\
        --castella ruta/al/vscode-language-pack-es/extension
"""

import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

NEURONAL = "https://api.softcatala.org/v2/nmt/translate/"
APERTIUM = "https://api.softcatala.org/traductor/v1/translate"
MIDA_LOT = 6000  # caràcters per petició

# Fragments que el traductor no ha de tocar.
PROTEGITS = re.compile(
    r"`[^`\n]*`"            # codi en línia
    r"|\$\([^)\s]*\)"       # icones: $(sync)
    r"|\$\{[^}\n]*\}"       # variables: ${workspaceFolder}
    r"|\]\([^)\s]*\)"       # destí d'un enllaç Markdown
    r"|<[^<>\n]+>"          # etiquetes HTML
    r"|https?://\S+"        # URL
    r"|%[sd]"
)
MARCADORS = re.compile(r"\{[^{}\s]*\}")
PARENTESI_INICIAL = re.compile(r"^\(([^()\n]+)\)\s+(\S.*)$", re.S)


def llegeix(ruta):
    try:
        with open(ruta, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def escriu(ruta, dades):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(dades, f, ensure_ascii=False, indent="\t")
        f.write("\n")


def text(valor):
    return valor["message"] if isinstance(valor, dict) else valor


def empremta(s):
    """Marcadors i fragments protegits que ha de conservar una traducció."""
    return sorted(MARCADORS.findall(s) + PROTEGITS.findall(s)) + [s.count("&&")]


def demana(url, dades, intents=4):
    cos = urllib.parse.urlencode(dades).encode()
    for intent in range(intents):
        try:
            with urllib.request.urlopen(url, cos, timeout=120) as r:
                return json.load(r)["responseData"]["translatedText"]
        except Exception as e:
            if intent == intents - 1:
                print(f"  error de xarxa: {e}", file=sys.stderr)
                return None
            time.sleep(2 ** intent * 3)


def lots(linies):
    lot, mida = [], 0
    for l in linies:
        if lot and mida + len(l) > MIDA_LOT:
            yield lot
            lot, mida = [], 0
        lot.append(l)
        mida += len(l) + 1
    if lot:
        yield lot


def tradueix_linies(linies, url, parametres, separador):
    """Tradueix una llista de línies. Si el lot no torna sencer, línia a línia."""

    def un_lot(lot):
        sortida = demana(url, {**parametres, "q": separador.join(lot)})
        trossos = sortida.split(separador) if sortida is not None else []
        if len(trossos) == len(lot):
            return trossos
        return [demana(url, {**parametres, "q": l}) for l in lot]

    resultat = []
    with ThreadPoolExecutor(max_workers=2) as feina:
        for n, trossos in enumerate(feina.map(un_lot, list(lots(linies))), 1):
            resultat.extend(trossos)
            if n % 20 == 0:
                print(f"  {len(resultat)}/{len(linies)}", file=sys.stderr)
    return resultat


def protegeix(s):
    """Substitueix els fragments protegits per {Pn} i treu els && de drecera."""
    guardats = []

    def guarda(m):
        guardats.append(m.group(0))
        return "{P%d}" % (len(guardats) - 1)

    return PROTEGITS.sub(guarda, s.replace("&&", "")), guardats


def restaura(s, guardats, original):
    for i, g in enumerate(guardats):
        s = s.replace("{P%d}" % i, g, 1)
    if "&&" in original:
        # La drecera de teclat va a la primera lletra de la traducció.
        s = re.sub(r"([^\W\d_])", r"&&\1", s, count=1)
    return s


def per_linies(textos, tradueix):
    """Tradueix textos de diverses línies partint-los i tornant-los a ajuntar."""
    linies, forma = [], []
    for t in textos:
        parts = t.split("\n")
        forma.append(len(parts))
        linies.extend(parts)
    traduides = tradueix(linies)
    sortida, i = [], 0
    for n in forma:
        trossos = traduides[i : i + n]
        sortida.append(None if None in trossos else "\n".join(trossos))
        i += n
    return sortida


def neuronal(textos):
    # El traductor neuronal s'empassa els parèntesis inicials, com ara
    # "(Built-In) ...", així que el parèntesi es tradueix a part.
    parts = [(m.groups() if (m := PARENTESI_INICIAL.match(t)) else (None, t)) for t in textos]
    interiors = [p for p, _ in parts if p]
    traduits = neuronal_simple([r for _, r in parts] + interiors)
    interiors = iter(traduits[len(textos):])
    sortida = []
    for (p, _), r in zip(parts, traduits[: len(textos)]):
        if p:
            i = next(interiors)
            r = None if r is None or i is None else f"({i}) {r}"
        sortida.append(r)
    return sortida


def neuronal_simple(textos):
    preparats = [protegeix(t) for t in textos]

    def tradueix(linies):
        buides = {i for i, l in enumerate(linies) if not l.strip()}
        plenes = [l for l in linies if l.strip()]
        fet = iter(tradueix_linies(
            plenes, NEURONAL, {"langpair": "eng|cat", "savetext": "false"}, "\n"))
        return [l if i in buides else next(fet) for i, l in enumerate(linies)]

    brut = per_linies([p for p, _ in preparats], tradueix)
    return [
        None if b is None else restaura(b, g, t)
        for b, (_, g), t in zip(brut, preparats, textos)
    ]


def apertium(textos):
    def tradueix(linies):
        return tradueix_linies(
            linies, APERTIUM, {"langpair": "es|ca", "markUnknown": "no"}, "\n\n")

    return per_linies(textos, tradueix)


def recull(vscode, castella, paquet):
    """Llista de (fitxer, secció, clau, anglès, castellà) que falten al paquet."""
    feines = []

    claus = llegeix(f"{vscode}/out/nls.keys.json")
    missatges = llegeix(f"{vscode}/out/nls.messages.json")
    ca = llegeix(f"{paquet}/translations/main.i18n.json")["contents"]
    es = llegeix(f"{castella}/translations/main.i18n.json")["contents"]
    i = 0
    for modul, llista in claus:
        for clau in llista:
            if clau not in ca.get(modul, {}):
                feines.append(("main.i18n.json", modul, clau, missatges[i],
                               text(es.get(modul, {}).get(clau, "")) or None))
            i += 1

    for pj in sorted(glob.glob(f"{vscode}/extensions/*/package.json")):
        dades = llegeix(pj)
        ident = f"{dades.get('publisher', 'vscode')}.{dades['name']}"
        fitxer = f"extensions/{ident}.i18n.json"
        ca = (llegeix(f"{paquet}/translations/{fitxer}") or {}).get("contents", {})
        es = (llegeix(f"{castella}/translations/{fitxer}") or {}).get("contents", {})
        nls = llegeix(os.path.join(os.path.dirname(pj), "package.nls.json")) or {}
        for clau, valor in nls.items():
            if clau not in ca.get("package", {}):
                feines.append((fitxer, "package", clau, text(valor),
                               text(es.get("package", {}).get(clau, "")) or None))
        # Les cadenes del codi de les extensions ("bundle") tenen com a clau el
        # text anglès. VS Code no les publica, així que les agafem del castellà.
        for clau, valor in es.get("bundle", {}).items():
            if clau not in ca.get("bundle", {}):
                angles = clau.split("/{Locked")[0]
                feines.append((fitxer, "bundle", clau, angles, text(valor)))
    return feines


def registra_fitxers(paquet):
    """Declara a package.json tots els fitxers de translations/extensions."""
    ruta = f"{paquet}/package.json"
    dades = llegeix(ruta)
    llista = [{"id": "vscode", "path": "./translations/main.i18n.json"}]
    for f in sorted(os.listdir(f"{paquet}/translations/extensions")):
        if f.endswith(".i18n.json"):
            llista.append({"id": f[: -len(".i18n.json")],
                           "path": f"./translations/extensions/{f}"})
    dades["contributes"]["localizations"][0]["translations"] = llista
    escriu(ruta, dades)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--vscode", required=True, help="carpeta app de VS Code")
    ap.add_argument("--castella", required=True, help="carpeta extension del paquet castellà")
    ap.add_argument("--paquet", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--cau", default=".cau/traduccions.json", help="memòria cau de traduccions")
    ap.add_argument("--limit", type=int, help="tradueix només les N primeres (per provar)")
    args = ap.parse_args()

    feines = recull(args.vscode, args.castella, args.paquet)[: args.limit]
    print(f"Cadenes que falten: {len(feines)}", file=sys.stderr)

    cau = llegeix(args.cau) or {"neuronal": {}, "apertium": {}}

    def valida(motor, font, angles, estricte=False):
        r = cau[motor].get(font)
        if not r or empremta(r) != empremta(angles):
            return None
        # Una traducció molt més curta sol haver perdut un tros de l'original.
        if estricte and len(angles) >= 12 and len(r) < 0.6 * len(angles):
            return None
        return r

    for motor, fn, font in (("neuronal", neuronal, 3), ("apertium", apertium, 4)):
        # Apertium només fa de reserva: tradueix el que el neuronal no ha resolt.
        pendents = sorted({
            f[font] for f in feines
            if f[font] and f[font] not in cau[motor]
            and (motor == "neuronal" or not valida("neuronal", f[3], f[3], True))
        })
        print(f"{motor}: {len(pendents)} textos nous", file=sys.stderr)
        for t, r in zip(pendents, fn(pendents)):
            if r is not None:
                cau[motor][t] = r
        escriu(args.cau, cau)

    fitxers, automatiques = {}, {}
    comptes = {"neuronal": 0, "apertium": 0, "sense traduir": 0}
    for fitxer, seccio, clau, angles, castella in feines:
        tria, motor = valida("neuronal", angles, angles, True), "neuronal"
        if tria is None and castella and castella != angles:
            tria, motor = valida("apertium", castella, angles), "apertium"
        if tria is None:
            tria, motor = valida("neuronal", angles, angles), "neuronal"
        if tria is None:
            comptes["sense traduir"] += 1
            continue
        comptes[motor] += 1
        if fitxer not in fitxers:
            fitxers[fitxer] = llegeix(f"{args.paquet}/translations/{fitxer}") or {
                "version": "1.0.0", "contents": {}}
        fitxers[fitxer]["contents"].setdefault(seccio, {})[clau] = tria
        automatiques.setdefault(fitxer, {}).setdefault(seccio, []).append(clau)

    for fitxer, dades in fitxers.items():
        escriu(f"{args.paquet}/translations/{fitxer}", dades)
    ruta = f"{args.paquet}/traduccions-automatiques.json"
    anteriors = llegeix(ruta) or {}
    for fitxer, seccions in automatiques.items():
        for seccio, claus in seccions.items():
            llista = anteriors.setdefault(fitxer, {}).setdefault(seccio, [])
            llista.extend(c for c in claus if c not in llista)
    escriu(ruta, anteriors)
    registra_fitxers(args.paquet)
    print(json.dumps(comptes, ensure_ascii=False), file=sys.stderr)


if __name__ == "__main__":
    main()
