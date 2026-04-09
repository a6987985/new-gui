# Status Icon Design Mapping

## Purpose
This note aligns the current runtime status keys with the approved Figma icon set.
Use it as the default reference for future UI polish and design-to-code checks.

## Icon Set
- library: `Lucide`
- style direction: outlined, simple, consistent stroke weight

## Approved Mapping

| Status key | Figma icon | Meaning |
| --- | --- | --- |
| `finish` | `circle-check` | Completed successfully |
| `running` | `circle-play` | Currently in progress |
| `failed` | `circle-x` | Ended with an error |
| `skip` | `circle-minus` | Intentionally skipped |
| `scheduled` | `clock-3` | Planned and scheduled to run |
| `pending` | `circle-dashed` | Waiting, not started yet |

## Notes
- Keep the runtime key name as `scheduled` in code. Do not rename it to `schedule`.
- `scheduled` and `pending` must stay visually distinct:
  - `scheduled` means time or execution has already been arranged
  - `pending` means waiting and not yet active
- Prefer this mapping in both Figma exploration and future code icon replacement work.
