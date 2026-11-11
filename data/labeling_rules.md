# Labeling rules

## Categories and departments

| Category | Department |
|---|---|
| pothole | Road Maintenance |
| streetlight | Street Lighting |
| garbage | Waste Management |
| graffiti | City Cleaning |
| fallen_tree | Parks and Trees |
| water_leak | Water Services |
| noise | Public Order Office |
| other | Citizen Service Center |

`other` covers everything that fits no category (broken benches, playground equipment, traffic signs, abandoned cars, gas smells, questions).

## Urgency

| Urgency | Rule | Examples |
|---|---|---|
| emergency | Immediate danger to life or health | Gas smell, exposed or sparking cables, collapsed road, burst water main flooding, chemical smell |
| high | Risk of injury, or a road, path or crossing blocked or unsafe | Deep pothole on a busy road, dark pedestrian crossing, broken glass, branch blocking the sidewalk |
| medium | Something does not work, but no direct risk | Single lamp out, overflowing bins, loud music at night |
| low | Cosmetic or minor | Graffiti, small litter, a flickering lamp, a question |

Offensive or hateful graffiti is `high`. Graffiti near a school with offensive words is `medium`.

## Emergencies

`is_emergency = 1` only when urgency is `emergency`. These reports must never be dispatched automatically.

## Duplicates

A report is a duplicate when an **open seed ticket** (see `seed_tickets.csv`) has the **same category on the same street**. `duplicate_of` then holds that ticket's ID; otherwise it is empty.

During evaluation, reset the database before each report, so reports are only compared with the 20 seed tickets and not with each other.

## Ambiguous cases (decided on purpose)

- "The light is broken at the corner of Bahnhofstraße" → `streetlight` (could also be a traffic light).
- "Something is wrong on my street" → `other`, `low` (too vague to judge).
- A question instead of a problem → `other`, `low`.
- A Lindenstraße streetlight is **not** a duplicate of the Lindenstraße water leak ticket (different category).
