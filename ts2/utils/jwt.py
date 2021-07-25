# jwt.py
# Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

import jwt
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest

from ts2.utils.datetime import utcnow


def gen_token(req: HttpRequest, exp: int | float | datetime | timedelta, sub: str = '', aud: str = '',
              nbf: datetime | timedelta = timedelta(seconds=0), **claims) -> str:
    payload = {f'ts2:{k}': v for k, v in claims.items()}
    now = utcnow()
    payload['iss'] = iss = get_current_site(req).domain
    if sub:
        payload['sub'] = str(sub)
    payload['aud'] = str(aud or iss)
    payload['iat'] = now.timestamp()
    if isinstance(exp, (int, float)):
        exp = timedelta(seconds=exp)
    if isinstance(exp, timedelta):
        exp = now + exp
    payload['exp'] = exp.timestamp()
    if not isinstance(nbf, datetime):
        nbf = now + nbf
    payload['nbf'] = nbf.timestamp()
    payload['jti'] = str(uuid.uuid4())
    return jwt.encode(payload, settings.SECRET_KEY, 'HS256')


def validate_token(req: HttpRequest, token: str, sub=None, aud=None) -> tuple[str, Optional[dict]]:
    iss = get_current_site(req).domain
    aud = str(aud or iss)
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'],
                             issuer=iss, audience=aud)
    except jwt.ExpiredSignatureError:
        return 'expired', None
    except jwt.InvalidTokenError:
        return 'invalid', None
    if sub and decoded.get('sub') != str(sub):
        return 'invalid', None
    decoded = {k.replace('ts2:', ''): v for k, v in decoded.items()}
    return 'valid', decoded
