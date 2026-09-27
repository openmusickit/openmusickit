# Ideas

This page is for the developer to record vague ideas.

## System Conversion Class

A place to write the logic that would convert a value in one system to another.
Exposes only `convert` method

As there's no existing standard system conversion 
(other than WSMN_Temporal->ClockTime, given a Tempo;
which is not easily reversible for non-quantized clock duration)
any user should be able to build their own conversion function.
Wrapping it in a class provides a portable API,
and a place to bundle whatever complicated logic is needed.

A specific conversion system is a subclass.
A subclass instance provide particular context.
One could write a general WSMN_Temporal<->ClockTime converter,
and instantiate it with a tempo and quantization rules.

Similarly, a Gregorian_Tonal::WSMN_Tonal converter could be instantiated by pitch,
while a Gregorian_Temporal::WSMN_Temporal with a particular rhythmic interpretation.

MIDI::WSMN would need quantization rules (temporal) and enharmonic discrimination (tonal)

## Sync Line

Something with no content of it's own, but which other things can sync to.
Represented as:
- a base node representing the timing origin
- child nodes representing arbitrary durations from the base node, created as needed for 
- SIMULTANEOUS sync edges from nodes in some sequential line

something like

graph.connect_to_sync_line(object, sync_line, point)