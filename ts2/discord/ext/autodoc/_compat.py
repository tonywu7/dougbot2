# Original license
#
# Copyright Jason R. Coombs
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import re

from inflect import (ARTICLE_SPECIAL_EU, ARTICLE_SPECIAL_ONCE,
                     ARTICLE_SPECIAL_ONETIME, ARTICLE_SPECIAL_UBA,
                     ARTICLE_SPECIAL_UKR, ARTICLE_SPECIAL_UNIT, CONSONANTS,
                     SPECIAL_A, SPECIAL_ABBREV_A, SPECIAL_ABBREV_AN,
                     SPECIAL_AN, SPECIAL_CAPITALS, VOWELS, A_explicit_a,
                     A_explicit_an, A_ordinal_a, A_ordinal_an, A_y_cons,
                     engine)

A_abbrev = re.compile(
    r"""
^(?! FJO | [HLMNS]Y.  | RY[EO] | SQU
  | ( F[LR]? | [HL] | MN? | N | RH? | S[CHKLMNPTVW]? | X(YL)?) [AEIOU])
[FHLMNRSX][A-Z]
""",
    re.VERBOSE,
)


class engine_(engine):
    def _indef_article(self, word: str, count: int) -> str:
        mycount = self.get_count(count)

        if mycount != 1:
            return f"{count} {word}"

        # HANDLE USER-DEFINED VARIANTS

        value = self.ud_match(word, self.A_a_user_defined)
        if value is not None:
            return f"{value} {word}"

        for regexen, article in (
            # HANDLE ORDINAL FORMS
            (A_ordinal_a, "a"),
            (A_ordinal_an, "an"),
            # HANDLE SPECIAL CASES
            (A_explicit_an, "an"),
            (SPECIAL_AN, "an"),
            (SPECIAL_A, "a"),
            # HANDLE ABBREVIATIONS
            (A_abbrev, "an"),
            (SPECIAL_ABBREV_AN, "an"),
            (SPECIAL_ABBREV_A, "a"),
            # HANDLE CONSONANTS
            (CONSONANTS, "a"),
            # HANDLE SPECIAL VOWEL-FORMS
            (ARTICLE_SPECIAL_EU, "a"),
            (ARTICLE_SPECIAL_ONCE, "a"),
            (ARTICLE_SPECIAL_ONETIME, "a"),
            (ARTICLE_SPECIAL_UNIT, "a"),
            (ARTICLE_SPECIAL_UBA, "a"),
            (ARTICLE_SPECIAL_UKR, "a"),
            (A_explicit_a, "a"),
            # HANDLE SPECIAL CAPITALS
            (SPECIAL_CAPITALS, "a"),
            # HANDLE VOWELS
            (VOWELS, "an"),
            # HANDLE y...
            # (BEFORE CERTAIN CONSONANTS IMPLIES (UNNATURALIZED) "i.." SOUND)
            (A_y_cons, "an"),
        ):
            mo = regexen.search(word)
            if mo:
                return f"{article} {word}"

        # OTHERWISE, GUESS "a"
        return f"a {word}"
