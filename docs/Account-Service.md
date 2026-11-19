# Account service

The service handles Discord sign-in, registered player names, sessions and
identity verification for approved game servers. It uses persistent SQLite
storage. Keep OAuth and server credentials in private configuration.

Build the hosting package from the repository root:

```powershell
python -m services.accounts.packaging --output dist/accounts-staging/release
```

The output contains only the files needed to deploy the service. See the [service source](../services/accounts/) for configuration. See the [game-server bridge](Account-Server-Bridge.md) for the role of
server credentials.
