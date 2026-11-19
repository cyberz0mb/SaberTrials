"""Discord authorization-code adapter. Access tokens are used once, never stored."""
import base64
import json
import re
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener


class ProviderError(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def urlopen(request, timeout):
    # Never forward an authorization header to a redirected host.
    return build_opener(NoRedirect()).open(request, timeout=timeout)


class DiscordProvider:
    def __init__(self, client_id, client_secret, callback):
        if not re.fullmatch(r'[1-9][0-9]{16,19}', client_id) or not client_secret:
            raise ValueError('Discord application configuration is required')
        self.client_id, self.client_secret, self.callback = client_id, client_secret, callback

    def authorization_url(self, state):
        return 'https://discord.com/oauth2/authorize?' + urlencode({
            'client_id': self.client_id, 'response_type': 'code', 'scope': 'identify',
            'redirect_uri': self.callback, 'state': state, 'prompt': 'consent'})

    def _json(self, request):
        try:
            with urlopen(request, timeout=10) as response:
                raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError()
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (URLError, OSError, ValueError) as exc:
            raise ProviderError('Discord sign-in is unavailable; start again from the game') from exc

    def identity(self, code):
        if not isinstance(code, str) or not 1 <= len(code) <= 2048:
            raise ProviderError('Invalid Discord callback')
        basic = base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()
        token = self._json(Request('https://discord.com/api/v10/oauth2/token',
            data=urlencode({'grant_type': 'authorization_code', 'code': code,
                            'redirect_uri': self.callback}).encode(), headers={
                'Authorization': 'Basic ' + basic, 'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'SaberTrialsAccounts/1'}))
        access = token.get('access_token')
        if not isinstance(access, str) or not access or '\r' in access or '\n' in access or token.get('token_type', '').lower() != 'bearer' or 'identify' not in token.get('scope', '').split():
            raise ProviderError('Discord did not grant the requested identity scope')
        user = self._json(Request('https://discord.com/api/v10/users/@me', headers={
            'Authorization': 'Bearer ' + access, 'User-Agent': 'SaberTrialsAccounts/1'}))
        user_id = user.get('id')
        if user.get('bot') or not isinstance(user_id, str) or not re.fullmatch(r'[1-9][0-9]{16,19}', user_id):
            raise ProviderError('Discord did not return a player identity')
        return user_id
