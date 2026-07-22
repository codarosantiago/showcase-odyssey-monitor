#!/usr/bin/env python3
"""Check Showcase once and alert when an IMAX date on/after 2026-08-06 appears."""

from __future__ import annotations

import argparse
import os
import re
import sys
import warnings
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


URL = "https://entradas.todoshowcase.com/showcase/boleteria_plus.aspx?filmid=5875"
DEFAULT_THRESHOLD = date(2026, 8, 6)
DEFAULT_CINEMA_ID = "18"  # IMAX Theatre (Norcenter)
SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


@dataclass(frozen=True)
class Option:
    value: str
    text: str
    selected: bool


class FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hidden: dict[str, str] = {}
        self.selects: dict[str, list[Option]] = {}
        self.selected_values: dict[str, str] = {}
        self._select_name: str | None = None
        self._option_value = ""
        self._option_selected = False
        self._option_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "input" and values.get("type", "").lower() == "hidden" and values.get("name"):
            self.hidden[values["name"]] = values.get("value", "")
        elif tag == "select" and values.get("name"):
            self._select_name = values["name"]
            self.selects[self._select_name] = []
        elif tag == "option" and self._select_name:
            self._option_value = values.get("value", "")
            self._option_selected = "selected" in values
            self._option_text = []

    def handle_data(self, data: str) -> None:
        if self._select_name:
            self._option_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "option" and self._select_name:
            text = " ".join("".join(self._option_text).split())
            option = Option(self._option_value, text, self._option_selected)
            self.selects[self._select_name].append(option)
            if option.selected:
                self.selected_values[self._select_name] = option.value
            self._option_text = []
        elif tag == "select":
            self._select_name = None


def parse_form(html: str) -> FormParser:
    parser = FormParser()
    parser.feed(html)
    return parser


def postback(session: requests.Session, html: str, target: str, value: str) -> str:
    form = parse_form(html)
    data = {**form.hidden, **form.selected_values}
    data.update({"__EVENTTARGET": target, "__EVENTARGUMENT": "", target: value})
    response = session.post(URL, data=data, timeout=(10, 30))
    response.raise_for_status()
    return response.text


def real_options(parser: FormParser, name: str) -> list[Option]:
    return [option for option in parser.selects.get(name, []) if option.value and not option.text.startswith("Seleccione")]


def parse_spanish_date(label: str) -> date | None:
    match = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", label.lower())
    if not match or match.group(2) not in SPANISH_MONTHS:
        return None
    return date(int(match.group(3)), SPANISH_MONTHS[match.group(2)], int(match.group(1)))


def fetch_dates(cinema_id: str) -> list[tuple[str, date]]:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Showcase-Date-Monitor/1.0 (+https://github.com/codarosantiago/showcase-odyssey-monitor)",
        "Accept-Language": "es-AR,es;q=0.9",
    })
    session.mount("https://", HTTPAdapter(max_retries=retry))

    response = session.get(URL, timeout=(10, 30))
    response.raise_for_status()
    cinema_html = postback(session, response.text, "ctl00$Contenido$lstCinema", cinema_id)
    formats = real_options(parse_form(cinema_html), "ctl00$Contenido$lstFormat")
    if not formats:
        raise RuntimeError(f"Showcase no devolvió formatos para el cine {cinema_id}; el sitio puede haber cambiado")

    found: set[tuple[str, date]] = set()
    for movie_format in formats:
        format_html = postback(session, cinema_html, "ctl00$Contenido$lstFormat", movie_format.value)
        for day in real_options(parse_form(format_html), "ctl00$Contenido$lstDays"):
            parsed = parse_spanish_date(day.text)
            if parsed:
                found.add((movie_format.text, parsed))
    return sorted(found, key=lambda item: (item[1], item[0]))


def set_action_output(name: str, value: str) -> None:
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with Path(output_file).open("a", encoding="utf-8") as output:
            output.write(f"{name}={value}\n")


def notify(topic: str, matches: list[tuple[str, date]]) -> None:
    details = ", ".join(f"{movie_format} — {day:%d/%m/%Y}" for movie_format, day in matches)
    response = requests.post(
        f"https://ntfy.sh/{topic}",
        data=f"¡Ya hay funciones desde el 6 de agosto! {details}. Comprá acá: {URL}".encode(),
        headers={
            "Title": "La Odisea: nuevas funciones",
            "Click": URL,
            "Priority": "urgent",
            "Tags": "movie_camera,ticket",
        },
        timeout=(10, 30),
    )
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=date.fromisoformat, default=DEFAULT_THRESHOLD)
    parser.add_argument("--cinema-id", default=DEFAULT_CINEMA_ID)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    set_action_output("alerted", "false")
    dates = fetch_dates(args.cinema_id)
    matches = [(movie_format, day) for movie_format, day in dates if day >= args.threshold]
    print(f"Fechas encontradas: {', '.join(sorted({day.isoformat() for _, day in dates}))}")
    print(f"Umbral: {args.threshold.isoformat()} | coincidencias: {len(matches)}")

    if args.dry_run:
        print("PRUEBA OK" if matches else "Sin coincidencias")
        return 0
    if not matches:
        return 0

    topic = os.getenv("NTFY_TOPIC")
    if not topic:
        raise RuntimeError("Falta el secret NTFY_TOPIC")
    notify(topic, matches)
    set_action_output("alerted", "true")
    print("Alerta enviada; el workflow se desactivará para evitar duplicados")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
