# COF Gate Transcript Fixtures

Format:
{
  "id": "fixture_NNN",
  "turns": [
    {"speaker": "user", "text": "..."},
    {"speaker": "ai", "text": "..."}
  ],
  "expected": {
    "cof_clinical": true/false,
    "cof_operational": false/true,
    "cof_financial": true/false
  }
}

NOTE: Pre-pilot threshold is 10 fixtures. Must expand to 50 before BSCI go-live.
