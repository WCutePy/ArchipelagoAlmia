
# Version

Development and testing was done on a decrypted rom
NTR-YP2E-USA
csr32: 5f520677


# trap ideas

## Bidoof Encounter trap

I have, so far found two (maybe three) potential ways to do this trap (for 1 bidoof so far):

- Detect when a battle starts, and if a bidoof trap (or other pokémon trap) is active, write the bidoof ID to 2 memory addresses. This seems to have a decent margin for the watching code to be "slow", so high chance this can work well
- Freeze those two values to bidoof (idk if this is possible yet, but i know bizhawks debugger supports it), and this WILL cause issues if the ram address is reused
- convert an action replay code that executes loading data at some point to replace more specific data at a different point

The following addresses need to be edited after the battle state gets set at: 
08A3B8	- Game State


22B508	b	h	0	Main RAM	pok 1 battle id 
<br>22B590	b	h	0	Main RAM	pok 1 capture id


# Species notes

The species ID list has 

    {
        "name": "Dummy",
        "label": "DUMMY",
        "species_id": 236,
        "browser_number": 236,
        "field_move": {
            "category": 0,
            "level": 0
        }
    },

This is not usable in the same way I am able to edit the ID of pokémon 1. 
This might become usable, but is highly to require specific scripts.

Wailord can not be loaded in that same way either. -> find a different entry point to load Pokémon
OR wailord also requires a different script to be loaded (look at encounter hacks)