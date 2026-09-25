# Audit model

MITRA evaluates evidence in a fixed order:

`REAL -> SYNC -> STAKEABILITY -> COSTS -> DB`

## REAL

Confirms that compared observations refer to the same underlying event and the
same rules. A mismatch is `FAILED`; missing identity evidence is `UNPROVEN`.

## SYNC

Measures source-span and staleness. A hard stale breach is `FAILED`. Timing that
looks good is still `PARTIAL`, because timestamps do not by themselves prove
that all observations were simultaneously executable.

## STAKEABILITY

Separates visible data from executable evidence. Quote availability alone is
not enough to prove acceptance or capacity.

## COSTS

Requires extra costs to be explicit. Missing cost evidence remains `UNPROVEN`.

## DB

Compares the reconstructed evidence with the stored record. Contradictions are
`FAILED`; missing comparison evidence is `UNPROVEN`.

## Fail-closed rule

Missing evidence never becomes `PASS` by default.
