# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup


def working_hours_parser(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    result = []

    for row in rows:
        day = row.find("td").text.strip()
        hours = (
            row.find("td", attrs={"aria-label": True})
            .find("li")
            .text.strip()
            .replace("\u202f", " ")
        )
        might_differ = (
            "Hours might differ"
            in row.find("td", attrs={"aria-label": True})["aria-label"]
        )

        data = {"day": day, "hours": hours, "might_differ": might_differ}

        result.append(data)

    return result
