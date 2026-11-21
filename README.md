# ONDARA — the falls that rise

[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/sandytaztaz-hue/the-poster-for-a-place-that-i-2-20261121-0539-r2/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/sandytaztaz-hue/the-poster-for-a-place-that-i-2-20261121-0539-r2/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

A travel poster for a place that isn't there — **ONDARA**, a coastal
cliff bay at sunset where the waterfall falls UP.

The landmark is the rising falls: a wide column of sea-water rises
from the bay at the foot of a tall dark cliff, arcs upward into the
sky, and dissolves into spray and cloud. A big low orange sun hangs
over the teal sea, a tiny fishing town with lit windows hugs the
cliff base, sailboats cross the bay, walkers climb the cliff path,
and one rowing boat drifts near the foot of the falls. The name
**ONDARA** is set huge across the top in a hand-drawn display serif,
with the tagline *"THE FALLS THAT RISE"* beneath it.

## How it works

`main.py` is pure Python 3 stdlib (no PIL, no numpy, no network). It
renders the poster procedurally — sky and sea gradients, sun glow,
clouds, cliff with strata and rim light, the rising water column
with foam streaks and spray, town, boats, halftone dots and film
grain — and writes a 1024×1024 PNG with a custom writer
(`zlib` + `struct`). The letterforms are a hand-authored vector
serif (every glyph drawn as polygons in the code; the O is an
ellipse ring, the rest are stem/bar/counter polygons); no font
files. Output is deterministic: a fixed seed makes two runs
byte-identical.

## Run

```sh
python3 main.py
# writes /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png)
```

## Bounty

[The Poster for a Place That Isn't There](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539) — make.fun
