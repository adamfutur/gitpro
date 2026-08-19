from services.db_service import save_session, get_session

class SessionStore:
    """
    Drop-in replacement for the old in-memory `token_store = {}` dict, backed by the
    database instead. Every existing call site only ever did `.get(token)` or
    `token_store[jwt_token] = access_token`, so this supports exactly that surface —
    nothing else needed to change.
    """

    def get(self, jwt_token, default=None):
        value = get_session(jwt_token)
        return value if value is not None else default

    def __getitem__(self, jwt_token):
        value = get_session(jwt_token)
        if value is None:
            raise KeyError(jwt_token)
        return value

    def __setitem__(self, jwt_token, github_access_token):
        save_session(jwt_token, github_access_token)

    def __contains__(self, jwt_token):
        return get_session(jwt_token) is not None
