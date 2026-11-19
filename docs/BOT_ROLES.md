# Saber Trials bot roles

Role behavior runs entirely on the authoritative game server and uses OpenJK's normal navigation, visibility, team, and CTF goal systems. No external AI service or client download is required. Bots never vote.

## Player votes

Open Call Vote > Bots and choose a role, or use one of these commands:

- `callvote addbot duelist`
- `callvote addbot sentinel`
- `callvote addbot berserker`
- `callvote addbot trickster`
- `callvote addbot defender`
- `callvote addbot flagcatcher`
- `callvote addbot sabermaster`

The normal Call Vote > Kick player list also contains bots. Selecting a bot creates a bot-removal vote; selecting a human keeps the existing staff protection and human kick rules.

Role choices are enforced by the server:

- FFA: Duelist, Sentinel, Berserker, Trickster
- TFFA: Duelist, Sentinel, Berserker
- CTF: Defender, Flag Catcher
- Duel: Saber Master only
- Tournament: unchanged classic bot behavior

Ordinary `addbot` and `bot_minplayers` additions receive a valid role for the current game type, including a random Defender or Flag Catcher in CTF and the Saber Master in Duel. The character/model is selected independently from the installed bot definitions.

## Character dialogue and DLC priority

Bots use the `personality` file named in their model's `.bot` definition for
greetings, kills, deaths, replies and orders. Assigning Duelist, Sentinel,
Berserker or Trickster changes combat behavior, without replacing that voice.
Queued personality remarks now survive contact with an enemy and can be sent
while fighting. The profile's `chatability` and `chatfrequency` still control
its dialogue.

The Trickster's extra combat remarks prefer the personality's optional
`CombatChat` group, then its existing `Hatred` group. If the personality has
dialogue but neither combat group, it speaks at its normal events without
generic Trickster remarks. The original Trickster lines are used only when
the profile has no usable chat at all. Empty, missing and unreadable chat
profiles therefore retain the existing role fallback; assigning another
role does not invent dialogue that it did not have before.

For DLC authors, keep a unique `botfiles/your_character.jkb` in the model PK3
and point the `.bot` definition's `personality` key to it. Retain the usual
`GeneralBotInfo` and other personality settings. After `BEGIN_CHAT_GROUPS`,
add the standard event groups and, optionally:

```text
CombatChat
{
    Your character's combat remark here.
    Show me what you can do, %s!
}
```

Each line is one remark. `%s` inserts the current opponent/subject, `%a` the
secondary subject where the event supplies one, and `%%` a literal percent.
Blank lines and full-line `//` comments are ignored; LF, CRLF and CRCRLF
line endings are accepted. Keep each line and its expanded names below 128
UTF-8 bytes, the chat section below 8192 bytes, and the personality file below
131072 bytes. Overlong remarks are skipped safely. An authored chat profile
with `chatability 0` stays silent rather than receiving generic role lines.

Bot remarks continue through ordinary game chat, including the receiving
player's [universal translator](Universal-Translator.md). A host's menu
language does not disable personality chat. No model packages need editing
when their `.bot` definition already points to their own dialogue.

The source overlay and reproducible checks are in
[`development-source/bot-chat`](../development-source/bot-chat/README.md).

## Roles

### Duelist

Walks with its saber off and looks for a visible opponent who is alive, standing still, not attacking, not already dueling, and also has a saber off. It approaches, faces the opponent, issues a private challenge, waits through the acceptance window, then leaves and tries somebody else after the cooldown. In TFFA it considers opponents only.

### Berserker

Keeps its saber active, runs whenever possible, continues looking for combat, and never accepts a private challenge. TFFA target selection remains enemy-only.

### Sentinel

Uses maximum bot aim and controlled fast turning without gaining bonus health or damage. It reacts only to visible nearby saber attacks, enters the same timed Walk/guard input available to players, and stops attacking while attempting the parry. Outside those moments it mixes walking and running. Each respawn rotates to the next saber class: single, dual wield, or staff, with a random stock hilt.

### Trickster

FFA only. It changes tactics on a cooldown: apparently polite saber-off approaches, close ambushes, circling, hopping attacks, quiet approaches, and deliberately opposing another player's saber-on/off etiquette. Its combat remarks follow the character-dialogue priority above and are rate-limited. It still requires normal visibility and uses ordinary player inputs, damage, and movement.

### Defender

CTF only. It remains in its own team's territory while the home flag is safe. If an opponent takes that flag, it immediately changes to retrieval, pursues the carrier anywhere on the map, and returns to base defense when the flag is recovered. It uses Force Speed through normal server-validated Force controls when moving or pursuing.

### Flag Catcher

CTF only. It uses the enemy flag as its permanent navigation priority until it takes the flag, then returns directly to its own base to score. While carrying, it may briefly defend itself against the most recent nearby attacker but never deliberately leaves the scoring route to seek combat. If another teammate takes the enemy flag first, it actively hunts opposing players. It also uses Force Speed through the normal Force rules when available.

### Saber Master

Duel only. This is the intentionally punishing skill-5 sparring opponent: Sentinel-grade aim and turning, a 12–42 ms visible-attack reaction, very frequent timed guards, earned counterattacks, unpredictable single-saber style cycling, and a rotating single/dual/staff class after every death. It mixes normal, walking, crouching, jumping, short-hop, lateral, back-step, and valid wall-run attack inputs. It receives no bonus health, damage, invulnerability, or impossible movement, so it remains beatable through timing and adaptation. Tournament deliberately keeps classic bots.

## Administrator commands and tuning

- `st_addbot <role> [red|blue] [skill 1-5]` adds a random character with a validated role, including `sabermaster` in Duel. Connected bots do not reuse a character while another installed character profile remains available.
- `st_kickbot <bot name|client number>` removes a bot and refuses human targets.
- `st_botstatus` lists every connected bot's role and team.
- `seta st_botSkill "4"` sets the default skill for role additions.
- `seta st_botDuelCooldown "6000"` sets the Duelist retry delay in milliseconds.
- `seta st_botSentinelReaction "90"` sets the Sentinel's visible-attack reaction delay.
- `seta st_botTricksterChat "12000"` sets the minimum Trickster chat interval.

These controls are intended for beta feedback. Sentinel defense and Trickster timing should be tuned from real matches rather than by granting hidden stat bonuses.
