# Searching new patches guide

This write up aims to list the minimal knowledge and steps necessary to identify/verify new event triggers that must be patched for a randomizer to function as one would expect.
This describes a way to contribute to the project while still in development.

## Event triggers

The game is filled with different event triggers, these run a set of code when stepping on them (EventRect), or talking to an NPC, or destroying a Targets and such.... 

Some event triggers simply perform an action based on the current chapter and event variable state. Such as being blocked from leaving the forest during the fire.
An event trigger can generally be identified by a cutscene, dialogue, or some other way of temporary losing control of the character.

## Code names

maps = Each map is a continous space in which you can move, seperated by loading zones, such as doors.
	Each map has a map_id and a map name.

map_id = integer index to identify the map, e.g. 0x029 for MARINE_CAVE-NORTH

map name = the map name as it is stord in the rom. Each takes the structure mXXX_YYY, where XXX is the area 	id and YYY the id within that area, e.g. m006_002 for MARINE_CAVE-NORTH
	All maps with their relevant data for the archipelago (this might not be all necessary for 	development are in [regions.json](data/regions.json)

area = mYYY, an area such as m006 for MARINE_CAVE or m001 for RANGER_SCHOOL

EventRect = event rectangle, placed on the game map

Unique_id = Unique identifier for each object instance in the game. Composite of: object_type-map_id-	map_index. Example: 0x100A001

Chapter = internal value used by the game to track where the player is in the story

Event flag = an event flag set or incremented during a chapter. These are reset frequently, and each 	chapter uses the same event flags for different purposes.

Form ID = each species has 1 or more forms, this allows the game to have pokemon of the same species, with 	different strength to exist. This applies to boss fights or pokemon in the capture arena. Species info is listed in [species.json](data/species.json)


## What requires patching

Any event trigger preventing the player from going to an area they have been before that can only be removed by destroying a target / using a fieldmove (or defeating a pokemon (if difficult, e.g. not done for quest 1 miltank)).
 - e.g. the Vien Tribute blocks the player from going places, but these restriction are lifted simply by 	walking around, and therefore not necessary to patch.

Any event trigger that requires a specific pokemon with a specific unique_id, rather than checking specied_id / field move,
 - e.g. to be allowed to move to the fire area during the forest fire, it checks if unique id 0x103B000 is in the party, rather than checking that a blastoise (only pokemon able to use rain dance) is in the party

Any event trigger, that checks strict event flags, when the event trigger setting said trigger can be skipped,
 - e.g. in marine cave, when destroying the red gigaremo it checks if an event flag is set to 7 exactly, rather than 7 or less.

Any targets that can be destroyed before the chapter/moment they are supposed to be destroyed if doing so blocks progression / event triggers down the line
- e.g. entering the crashed ship early, or using surf early

Any event triggers placed before unlocking doduo that crash the game while riding doduo. This will need to be a specific list of their EventRects, to allow patching them to dismount doduo.

A list of known patches (already patched) are listed in [the game docs](docs/en_PokemonRangerSoA.md), with their precise patches, and other randomization changes in the [patch module](patch)

## How to discover?

1. Play the game normally until the point where you want to start testing / searching.
2. Assume the whole game is randomized such that:
 - a. Each pokemon instance (unique id) required to continue the story in vanilla is not the required 	species, 	
    - e.g. 0x103B000 is not a Blastoise
    - e.g. A pokemon with soak 2 is available before destroying the boulder in m006_002
 - b. When moving into a new map / story section, you do not know what pokemon are required until 	interacting with a target / npc / event trigger and will always need to be able to move back to a 	previous map such as ranger road or school.
    - e.g. PUELTOWN-WEST can be entered without clearing PUELTOWN-CENTER by clearing PUELTOWN-EAST and 	taking the center bridge. When there it is impossible to move back without destroying the gate or 	gigaremo units.
3. Take an event trigger to trigger early
 - e.g. Complete mission
4. Make a savestate to
 - a. Return and select a different event trigger later
 - b. Test alternate paths
 - c. Softlock protection
5. Test the minimal path of event triggers required to trigger the event trigger in 3.
 - e.g. The red gigaremo in marine cave can be destroyed on sight
 - e.g. To complete mission 4, upon entry of Pueltown, it is only necessary to destroy the blue 
	gigaremo, green gigaremo and gate in PUELTOWN-EAST and fight dim sun.
6. Verify that most/all events after the event trigger in 3 function as vanilla.
 - a. Only necessary if any event triggers could be skipped to reach the trigger in 3.
 - b. Generally checking to the next chapter is enough. 
    -e.g. After beating dim sun in mission 4, if PUELTOWN-CENTER and PUELTOWN-WEST were not cleared of 	gigaremo, the obstructing pokemon walls stay, with no way to clear manually anymore. These are only 	cleared on official mission 4 complete
    -This does not apply if doing things several chapters earlier 
       - e.g. surfing earlier or entering the crashed ship early.

### Okay but RAM

A watch file is available in the discord with most important addresses. Some of those watch file entries 
are listed here for more clarification, or simply to note that they are relevant for the process.

Room ID = map_id = 2 byte values such as 0x003B

player x = 2 byte value for the player x position

player y = 2 byte value for the player y position

chapter number = 1 byte value

Act Mission ID

event vars = start address of the event vars struct, a set of variables incremented when triggering event 	triggers.

slot 1 id = form ID of the first non partner pokemon in your normal party. The party is a struct of 10 	entries. Land party is one struct of entries, the underwater party is a seperate struct right after 	in memory
	After editing a form ID it only takes effect after opening the party release screen and/or closing 	it. Catching a random pokemon and modifying it into a needed pokemon is the main way to test.

styler level = if you want to be stronger

### How to report such issues

It's similar to how rom changes are reported in [the game docs](docs/en_PokemonRangerSoA.md), any write ups answering what and when are valid enough. Before reporting, confirm reproducability of the issue. The more specific the issue is described the easier it is to verify and patch.

| What                      | When                       | Missions               |
|---------------------------|----------------------------|------------------------|
| Destroying the red gigaremo before triggering events in the top room of Marine cave hard softlocks the game                       | N/A | Mission 2                    |

### I want to fix the scripts myself

This requires identifying the exact script file triggered. At the moment most syscalls are not documented, which scripts heavily rely on. This places patching script files in either the realm of reverse engineering or gambling.

Relevant resources are [prsoa-debug](https://github.com/Chesyon/prsoa-debug) for general debug info, [almiascript-lappy](https://gitlab.com/8011lapras/almiascript-lappy) an improved version on Fexean's wonderful script decompiler, and [ra23mes](https://github.com/SombrAbsol/ra23mes) to convert MES files

Personally I find the workflow of identifying what dialogue line was last triggered before or during a script that does not behave as expected, and then manually finding this number next to a printmsg in one of the script files I would expect.
These are in order, EventRect, map script, area script, chapter script. Other scripts to consider can be npc, target or quest scripts.
