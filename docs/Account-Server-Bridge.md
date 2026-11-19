# Game server account integration

The dedicated engine verifies player identity with the account service and
passes the confirmed account to the game module. Use matching engine and
game modules. Each approved server needs its own credential, stored outside
the repository and protected by operating-system permissions. Clients keep
their own session credentials; a player name or clan tag cannot verify identity.

See [Account service](Account-Service.md) and [Linux setup](Linux-Server-Upload.md).
