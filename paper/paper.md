## My Criteria for Music Representation

###  Conceptual Fidelity

The first, most important, non-negotiable principle of music representation,
the requirement form which all other requirements ultimately derive is
the principle of conceptual fidelity.
This principle may be stated tersely as:
Concepts should be represented directly,
not translated into some other concept which is then represented.

The interactive surface of a musical representation,
the available objects and the operations that can be performed on them
--- or, from a computer programming point of view, the API of the representation ---
should correspond as closely as possible
to the mental model or musical conception of the musician-user interacting with the system.
The internal (in-memory or computer-facing) representation that supplies that surface
therefore needs to be, as completely as possible, an implementation of
the explicit and implicit rules and behavior of the musical phenomena they represent.

An example might make this requirement more clear.

A composer may conceive of a pitch named F#.
While the composer may know that there are particular keys on a piano named F#,
and particular fingerings on a particular instrument that correspond to F#,
and may also know the frequency of F# under a particular tuning and temperament system,
and may know the MIDI number for each F#,
and may know how to notate an F# in any octave on a staff with a particular clef,
the composer (if they desire) should be able to specify, interact with, and manipulate
F# as an entity unto itself, 
irrespective of any of these realizations.
The composer should not need to mentally translate F# into (for example)
an integer, a MIDI note, a frequency, a fingering, or a particular piano key before specifying and interacting with it.
Likewise, common operations on that F# (say, transpose up a minor third)
should be available without additional mental arithmetic or the need to hold competing conceptions in mind.

But there's more.
The internal representation of that F# within a musical computer system
(or the system as a whole)
should carry a complete implementation of the ways that F# can be manipulated,
which correspond non-lossily to the mental model of the musician-user.
Suppose we first ask -- what key is F# the third degree of (D major).
Then, we transpose that down a major second to C major.
Next we decide to construct a blues scale on the same tonic.
What is the blue note (flat 5) of this scale?
If the answer to that question (G-flat) cannot meaningfully be distinguished from our starting point (F#),
and requires additional information outside the system to properly interpret,
then the system's representation is incomplete and lossy.

Moreover, additional details tied to a particular realization might be inaccurate.
To assert, for example, that the F# in question is 369.99 Hz assumes a great deal 
--- a specific octave, 12-tone equal temperament, A=440 ---
which may not be warranted.
That's a lot of baggage which either needs to be ignored, corrected, or mentally translated.

What applies to pitch names applies to every other musical concept and phenomena that may be represented:
we should strive to represent the concept or phenomena directly,
not a secondary correlated concept or phenomena.
A quarter note is not a particular number of MIDI clicks or microseconds;
it is, rather, a value which has meaning only in relationship to all the values in the metrical system of which it is a member.
A *ritardando* is not an explicit tempo curve moving from one specific BPM to another BPM;
it is an instruction to a realizing agent, who has interpretive freedom over moment-to-moment tempo choices.
And a Gregorian punctum on Fa is not only *not* a specific MIDI note held for a specific length of clock time, 
it is also *not* a quarter note on F.

There are, at least, three strong reasons to insist on this fundamental principle of conceptual fidelity.

First of all, it is correct.
As musicians, engineers, and scientists, we should seek to be correct,
and to represent whatever we are attempting to represent as accurately as possible.
While I will argue below that there are practical benefits to conceptual fidelity
(as well as serious drawbacks to every compromise away from it),
frankly, we should strive for conceptual fidelity even absent concrete evidence that it has any practical benefit.
We should assume *a priori* that it will have practical benefit,
as a more accurate model of any phenomena we wish to study and interact with inevitably does.

Next,
a musician-user should at all times be able to interact with the music representation
according to their own pre-existing mental model of the musical objects in question.
Sometimes this will indeed be MIDI notes and explicit tempo curves,
and at other times it may indeed be frequencies and waveforms,
but it will also be 
--- perhaps a majority of the time, and certainly with existing literature in the Western canon ---
the objects present on a conventional score.
When Bach wrote an F#, he meant an F#.
He certainly didn't mean the integer `6`, the MIDI note `66`, or the frequency 369.99 Hz.
(Given the variety of both tuning and temperament in his time,
he couldn't possibly have intended *any* specific frequency,
even if he had the capability of measuring it, which he didn't.)

Finally,
and this claim admittedly needs further research to fully support,
we should expect that non-lossy, conceptually faithful representations
provide better data to, and elicit better output from,
computational systems (whether AI/ML-based or conventional)
designed to generate, analyze, or otherwise manipulate and interact with music.

To put all this another way:
An integer (`6`, for example) is a concept just as surely as a pitch (F#, for example) is a concept.
Neither the integer, nor the pitch (nor the MIDI note, nor the frequency) exist inside the computer,
they exist only in our minds or (in the case of frequency) as momentary phenomena in the physical world.
We fool ourselves if we imagine that `6` or `66` or `369.99` are somehow 
more real, more technical, more deserving of computer representation, 
or even more amenable to computer representation than F#.
These are all merely represented in a computer,
and we should represent what we intend to represent,
not some other thing.

It should of course be noted before moving on,
that many musician-users will specifically intend to represent
MIDI notes, integers, or frequencies,
or any number of other things.
One may wish to represent specific audio recordings,
or specific acoustic phenomena.
One may wish to represent music that uses non-Western notation systems,
or no notation system at all.
To one user, discrete microsecond timing is the intentional object of representation,
while another needs to represent the multiple semiologic layers of the Graduale Triplex.
One may even wish to represent many of these things at the same time ---
a note present in a written score *and* the precise acoustic performance of that note in a specific recording;
a performance instruction *and* the MIDI tempo curve that interprets it in a particular digital realization;
a punctum in a chant manuscript *and* the quarter note in a modern transcription.
This wild diversity of representational intention
argues strongly against collapsed, lossy, or secondary representations.
Each user should be able to fully represent precisely what they intend to represent,
without any additional representational baggage. 


